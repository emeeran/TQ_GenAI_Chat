"""
Microservices Architecture framework for TQ GenAI Chat application.
Provides service decomposition, inter-service communication, and distributed system patterns.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid
import aiohttp
import socket

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import consul
    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service health states."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """Service instance metadata."""
    service_id: str
    service_name: str
    host: str
    port: int
    version: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    health_check_url: str = ""
    tags: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    state: ServiceState = ServiceState.UNKNOWN
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class Message:
    """Inter-service message."""
    id: str
    type: str
    service_from: str
    service_to: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""
    reply_to: str = ""
    ttl: int = 300  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'service_from': self.service_from,
            'service_to': self.service_to,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to,
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        return cls(
            id=data['id'],
            type=data['type'],
            service_from=data['service_from'],
            service_to=data['service_to'],
            payload=data['payload'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            correlation_id=data.get('correlation_id', ''),
            reply_to=data.get('reply_to', ''),
            ttl=data.get('ttl', 300)
        )


class ServiceDiscovery(ABC):
    """Abstract service discovery interface."""
    
    @abstractmethod
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        pass
    
    @abstractmethod
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance."""
        pass
    
    @abstractmethod
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover instances of a service."""
        pass
    
    @abstractmethod
    async def health_check(self, service_id: str) -> ServiceState:
        """Check health of a service instance."""
        pass


class InMemoryServiceDiscovery(ServiceDiscovery):
    """In-memory service discovery for development."""
    
    def __init__(self):
        self.services: Dict[str, ServiceInstance] = {}
        self.service_names: Dict[str, List[str]] = {}
    
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        try:
            self.services[instance.service_id] = instance
            
            if instance.service_name not in self.service_names:
                self.service_names[instance.service_name] = []
            
            if instance.service_id not in self.service_names[instance.service_name]:
                self.service_names[instance.service_name].append(instance.service_id)
            
            logger.info(f"Registered service: {instance.service_name} ({instance.service_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {instance.service_id}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance."""
        try:
            if service_id in self.services:
                instance = self.services[service_id]
                del self.services[service_id]
                
                if instance.service_name in self.service_names:
                    if service_id in self.service_names[instance.service_name]:
                        self.service_names[instance.service_name].remove(service_id)
                    
                    if not self.service_names[instance.service_name]:
                        del self.service_names[instance.service_name]
                
                logger.info(f"Deregistered service: {service_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover instances of a service."""
        instances = []
        
        if service_name in self.service_names:
            for service_id in self.service_names[service_name]:
                if service_id in self.services:
                    instances.append(self.services[service_id])
        
        return instances
    
    async def health_check(self, service_id: str) -> ServiceState:
        """Check health of a service instance."""
        if service_id not in self.services:
            return ServiceState.UNKNOWN
        
        instance = self.services[service_id]
        
        try:
            if instance.health_check_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        instance.health_check_url,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            instance.state = ServiceState.HEALTHY
                            instance.last_heartbeat = datetime.utcnow()
                            return ServiceState.HEALTHY
                        else:
                            instance.state = ServiceState.UNHEALTHY
                            return ServiceState.UNHEALTHY
            else:
                # Simple connectivity check
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((instance.host, instance.port))
                sock.close()
                
                if result == 0:
                    instance.state = ServiceState.HEALTHY
                    instance.last_heartbeat = datetime.utcnow()
                    return ServiceState.HEALTHY
                else:
                    instance.state = ServiceState.UNHEALTHY
                    return ServiceState.UNHEALTHY
                    
        except Exception as e:
            logger.error(f"Health check failed for {service_id}: {e}")
            instance.state = ServiceState.UNHEALTHY
            return ServiceState.UNHEALTHY


class ConsulServiceDiscovery(ServiceDiscovery):
    """Consul-based service discovery."""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        if not CONSUL_AVAILABLE:
            raise ImportError("python-consul package required for Consul service discovery")
        
        self.consul = consul.Consul(host=consul_host, port=consul_port)
    
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance with Consul."""
        try:
            check = None
            if instance.health_check_url:
                check = consul.Check.http(
                    instance.health_check_url,
                    interval="10s",
                    timeout="5s"
                )
            
            self.consul.agent.service.register(
                name=instance.service_name,
                service_id=instance.service_id,
                address=instance.host,
                port=instance.port,
                tags=instance.tags,
                check=check,
                meta=instance.metadata
            )
            
            logger.info(f"Registered service with Consul: {instance.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service with Consul: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance from Consul."""
        try:
            self.consul.agent.service.deregister(service_id)
            logger.info(f"Deregistered service from Consul: {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deregister service from Consul: {e}")
            return False
    
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover service instances from Consul."""
        try:
            _, services = self.consul.health.service(service_name, passing=True)
            instances = []
            
            for service in services:
                service_info = service['Service']
                instance = ServiceInstance(
                    service_id=service_info['ID'],
                    service_name=service_info['Service'],
                    host=service_info['Address'],
                    port=service_info['Port'],
                    version=service_info.get('Meta', {}).get('version', '1.0.0'),
                    metadata=service_info.get('Meta', {}),
                    tags=service_info.get('Tags', [])
                )
                instances.append(instance)
            
            return instances
            
        except Exception as e:
            logger.error(f"Failed to discover services from Consul: {e}")
            return []
    
    async def health_check(self, service_id: str) -> ServiceState:
        """Check service health via Consul."""
        try:
            _, checks = self.consul.health.checks(service_id)
            
            if not checks:
                return ServiceState.UNKNOWN
            
            for check in checks:
                if check['Status'] == 'passing':
                    return ServiceState.HEALTHY
                elif check['Status'] == 'warning':
                    return ServiceState.DEGRADED
                elif check['Status'] == 'critical':
                    return ServiceState.UNHEALTHY
            
            return ServiceState.UNKNOWN
            
        except Exception as e:
            logger.error(f"Failed to check service health via Consul: {e}")
            return ServiceState.UNKNOWN


class MessageBroker(ABC):
    """Abstract message broker interface."""
    
    @abstractmethod
    async def publish(self, channel: str, message: Message) -> bool:
        """Publish a message to a channel."""
        pass
    
    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[Message], None]) -> bool:
        """Subscribe to a channel with callback."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from a channel."""
        pass


class RedisMessageBroker(MessageBroker):
    """Redis-based message broker."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package required for Redis message broker")
        
        self.redis_url = redis_url
        self.redis_client = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.pubsub = None
        self.listening = False
        self.listen_task = None
    
    async def start(self):
        """Start the message broker."""
        self.redis_client = redis.from_url(self.redis_url)
        self.pubsub = self.redis_client.pubsub()
        logger.info("Redis message broker started")
    
    async def stop(self):
        """Stop the message broker."""
        self.listening = False
        
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Redis message broker stopped")
    
    async def publish(self, channel: str, message: Message) -> bool:
        """Publish a message to a channel."""
        try:
            if not self.redis_client:
                return False
            
            message_data = json.dumps(message.to_dict())
            await self.redis_client.publish(channel, message_data)
            
            logger.debug(f"Published message to {channel}: {message.type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            return False
    
    async def subscribe(self, channel: str, callback: Callable[[Message], None]) -> bool:
        """Subscribe to a channel with callback."""
        try:
            if not self.redis_client:
                return False
            
            if channel not in self.subscribers:
                self.subscribers[channel] = []
                await self.pubsub.subscribe(channel)
            
            self.subscribers[channel].append(callback)
            
            # Start listening if not already started
            if not self.listening:
                self.listening = True
                self.listen_task = asyncio.create_task(self._listen_loop())
            
            logger.info(f"Subscribed to channel: {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False
    
    async def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from a channel."""
        try:
            if channel in self.subscribers:
                del self.subscribers[channel]
                await self.pubsub.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {channel}: {e}")
            return False
    
    async def _listen_loop(self):
        """Main message listening loop."""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = message['data'].decode('utf-8')
                    
                    try:
                        message_dict = json.loads(data)
                        msg = Message.from_dict(message_dict)
                        
                        # Call all callbacks for this channel
                        if channel in self.subscribers:
                            for callback in self.subscribers[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(msg)
                                    else:
                                        callback(msg)
                                except Exception as e:
                                    logger.error(f"Callback error for {channel}: {e}")
                                    
                    except Exception as e:
                        logger.error(f"Failed to process message from {channel}: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Message listening stopped")
        except Exception as e:
            logger.error(f"Message listening error: {e}")


class ServiceBase(ABC):
    """Base class for microservices."""
    
    def __init__(self, service_name: str, host: str = "localhost", port: int = 8000,
                 version: str = "1.0.0", discovery: ServiceDiscovery = None,
                 message_broker: MessageBroker = None):
        self.service_name = service_name
        self.host = host
        self.port = port
        self.version = version
        self.service_id = f"{service_name}-{uuid.uuid4().hex[:8]}"
        
        self.discovery = discovery or InMemoryServiceDiscovery()
        self.message_broker = message_broker
        
        self.instance = ServiceInstance(
            service_id=self.service_id,
            service_name=service_name,
            host=host,
            port=port,
            version=version,
            health_check_url=f"http://{host}:{port}/health"
        )
        
        self.running = False
        self.health_status = ServiceState.UNKNOWN
        
    async def start(self):
        """Start the service."""
        try:
            # Register with service discovery
            await self.discovery.register_service(self.instance)
            
            # Start message broker if available
            if self.message_broker and hasattr(self.message_broker, 'start'):
                await self.message_broker.start()
            
            # Subscribe to service-specific channels
            await self._setup_message_handlers()
            
            # Initialize service-specific components
            await self._initialize()
            
            self.running = True
            self.health_status = ServiceState.HEALTHY
            
            logger.info(f"Service {self.service_name} started on {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to start service {self.service_name}: {e}")
            self.health_status = ServiceState.UNHEALTHY
            raise
    
    async def stop(self):
        """Stop the service."""
        try:
            self.running = False
            self.health_status = ServiceState.UNHEALTHY
            
            # Cleanup service-specific components
            await self._cleanup()
            
            # Stop message broker
            if self.message_broker and hasattr(self.message_broker, 'stop'):
                await self.message_broker.stop()
            
            # Deregister from service discovery
            await self.discovery.deregister_service(self.service_id)
            
            logger.info(f"Service {self.service_name} stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop service {self.service_name}: {e}")
    
    async def send_message(self, target_service: str, message_type: str, 
                          payload: Dict[str, Any], correlation_id: str = "") -> bool:
        """Send a message to another service."""
        if not self.message_broker:
            logger.warning("No message broker configured")
            return False
        
        message = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            service_from=self.service_name,
            service_to=target_service,
            payload=payload,
            correlation_id=correlation_id
        )
        
        channel = f"service.{target_service}"
        return await self.message_broker.publish(channel, message)
    
    async def broadcast_message(self, message_type: str, payload: Dict[str, Any]) -> bool:
        """Broadcast a message to all services."""
        if not self.message_broker:
            return False
        
        message = Message(
            id=str(uuid.uuid4()),
            type=message_type,
            service_from=self.service_name,
            service_to="*",
            payload=payload
        )
        
        return await self.message_broker.publish("service.broadcast", message)
    
    async def call_service(self, service_name: str, endpoint: str, 
                          data: Dict[str, Any] = None, timeout: int = 30) -> Dict[str, Any]:
        """Make a direct HTTP call to another service."""
        instances = await self.discovery.discover_services(service_name)
        
        if not instances:
            raise Exception(f"No instances found for service: {service_name}")
        
        # Use first healthy instance (could implement load balancing here)
        instance = instances[0]
        url = f"{instance.url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=data or {},
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Failed to call {service_name}{endpoint}: {e}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "service_name": self.service_name,
            "service_id": self.service_id,
            "status": self.health_status.value,
            "running": self.running,
            "timestamp": datetime.utcnow().isoformat(),
            "version": self.version,
            "host": self.host,
            "port": self.port
        }
    
    async def _setup_message_handlers(self):
        """Setup message handlers for this service."""
        if not self.message_broker:
            return
        
        # Subscribe to service-specific messages
        await self.message_broker.subscribe(
            f"service.{self.service_name}",
            self._handle_message
        )
        
        # Subscribe to broadcast messages
        await self.message_broker.subscribe(
            "service.broadcast",
            self._handle_broadcast_message
        )
    
    async def _handle_message(self, message: Message):
        """Handle incoming service-specific messages."""
        try:
            await self.handle_message(message)
        except Exception as e:
            logger.error(f"Error handling message {message.type}: {e}")
    
    async def _handle_broadcast_message(self, message: Message):
        """Handle incoming broadcast messages."""
        try:
            await self.handle_broadcast_message(message)
        except Exception as e:
            logger.error(f"Error handling broadcast message {message.type}: {e}")
    
    @abstractmethod
    async def handle_message(self, message: Message):
        """Handle incoming service-specific messages."""
        pass
    
    @abstractmethod
    async def handle_broadcast_message(self, message: Message):
        """Handle incoming broadcast messages."""
        pass
    
    @abstractmethod
    async def _initialize(self):
        """Initialize service-specific components."""
        pass
    
    @abstractmethod
    async def _cleanup(self):
        """Cleanup service-specific components."""
        pass


class ChatService(ServiceBase):
    """Chat service implementation."""
    
    def __init__(self, **kwargs):
        super().__init__("chat-service", **kwargs)
        self.active_sessions = {}
        self.message_history = {}
    
    async def _initialize(self):
        """Initialize chat service components."""
        logger.info("Chat service initialized")
    
    async def _cleanup(self):
        """Cleanup chat service components."""
        self.active_sessions.clear()
        self.message_history.clear()
        logger.info("Chat service cleaned up")
    
    async def handle_message(self, message: Message):
        """Handle chat service messages."""
        if message.type == "chat_request":
            await self._handle_chat_request(message)
        elif message.type == "session_update":
            await self._handle_session_update(message)
    
    async def handle_broadcast_message(self, message: Message):
        """Handle broadcast messages."""
        if message.type == "system_maintenance":
            logger.info("Received system maintenance notification")
    
    async def _handle_chat_request(self, message: Message):
        """Handle chat request."""
        payload = message.payload
        user_id = payload.get("user_id")
        user_message = payload.get("message")
        
        # Process chat request (simplified)
        response = f"Echo: {user_message}"
        
        # Send response back
        if message.reply_to:
            await self.send_message(
                message.reply_to,
                "chat_response",
                {
                    "user_id": user_id,
                    "response": response,
                    "correlation_id": message.correlation_id
                }
            )
    
    async def _handle_session_update(self, message: Message):
        """Handle session update."""
        payload = message.payload
        user_id = payload.get("user_id")
        session_data = payload.get("session_data")
        
        self.active_sessions[user_id] = session_data
        logger.info(f"Updated session for user: {user_id}")


class FileService(ServiceBase):
    """File processing service implementation."""
    
    def __init__(self, **kwargs):
        super().__init__("file-service", **kwargs)
        self.processing_queue = asyncio.Queue()
        self.processor_task = None
    
    async def _initialize(self):
        """Initialize file service components."""
        self.processor_task = asyncio.create_task(self._process_files())
        logger.info("File service initialized")
    
    async def _cleanup(self):
        """Cleanup file service components."""
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        logger.info("File service cleaned up")
    
    async def handle_message(self, message: Message):
        """Handle file service messages."""
        if message.type == "file_upload":
            await self._handle_file_upload(message)
        elif message.type == "file_process_request":
            await self.processing_queue.put(message)
    
    async def handle_broadcast_message(self, message: Message):
        """Handle broadcast messages."""
        if message.type == "system_maintenance":
            logger.info("File service entering maintenance mode")
    
    async def _handle_file_upload(self, message: Message):
        """Handle file upload."""
        payload = message.payload
        filename = payload.get("filename")
        user_id = payload.get("user_id")
        
        # Simulate file processing
        await asyncio.sleep(1)
        
        # Notify completion
        await self.send_message(
            "chat-service",
            "file_processed",
            {
                "filename": filename,
                "user_id": user_id,
                "status": "completed"
            }
        )
    
    async def _process_files(self):
        """Background file processing loop."""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                await self._handle_file_upload(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"File processing error: {e}")


class MicroservicesOrchestrator:
    """Orchestrates multiple microservices."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.services: Dict[str, ServiceBase] = {}
        self.discovery = None
        self.message_broker = None
        
        self._setup_infrastructure()
    
    def _setup_infrastructure(self):
        """Setup service discovery and message broker."""
        # Setup service discovery
        discovery_type = self.config.get('discovery_type', 'memory')
        
        if discovery_type == 'consul':
            self.discovery = ConsulServiceDiscovery(
                consul_host=self.config.get('consul_host', 'localhost'),
                consul_port=self.config.get('consul_port', 8500)
            )
        else:
            self.discovery = InMemoryServiceDiscovery()
        
        # Setup message broker
        broker_type = self.config.get('broker_type', 'redis')
        
        if broker_type == 'redis' and REDIS_AVAILABLE:
            self.message_broker = RedisMessageBroker(
                redis_url=self.config.get('redis_url', 'redis://localhost:6379')
            )
    
    async def start(self):
        """Start the orchestrator and all services."""
        try:
            # Start message broker
            if self.message_broker and hasattr(self.message_broker, 'start'):
                await self.message_broker.start()
            
            # Start all services
            for service in self.services.values():
                await service.start()
            
            logger.info("Microservices orchestrator started")
            
        except Exception as e:
            logger.error(f"Failed to start orchestrator: {e}")
            raise
    
    async def stop(self):
        """Stop all services and the orchestrator."""
        try:
            # Stop all services
            for service in self.services.values():
                await service.stop()
            
            # Stop message broker
            if self.message_broker and hasattr(self.message_broker, 'stop'):
                await self.message_broker.stop()
            
            logger.info("Microservices orchestrator stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop orchestrator: {e}")
    
    def add_service(self, service: ServiceBase):
        """Add a service to the orchestrator."""
        service.discovery = self.discovery
        service.message_broker = self.message_broker
        self.services[service.service_name] = service
        logger.info(f"Added service: {service.service_name}")
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services."""
        health_status = {
            "orchestrator": "healthy",
            "services": {}
        }
        
        for service_name, service in self.services.items():
            health_status["services"][service_name] = service.get_health_status()
        
        return health_status
    
    async def scale_service(self, service_name: str, instances: int):
        """Scale a service to N instances (placeholder)."""
        # This would integrate with container orchestration (Docker, Kubernetes)
        logger.info(f"Scaling {service_name} to {instances} instances")
        # Implementation would depend on deployment platform


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Create orchestrator
        config = {
            'discovery_type': 'memory',  # or 'consul'
            'broker_type': 'redis',
            'redis_url': 'redis://localhost:6379'
        }
        
        orchestrator = MicroservicesOrchestrator(config)
        
        # Add services
        chat_service = ChatService(port=8001)
        file_service = FileService(port=8002)
        
        orchestrator.add_service(chat_service)
        orchestrator.add_service(file_service)
        
        try:
            # Start orchestrator
            await orchestrator.start()
            
            # Simulate some inter-service communication
            await asyncio.sleep(1)
            
            await chat_service.send_message(
                "file-service",
                "file_upload",
                {
                    "filename": "test.pdf",
                    "user_id": "user123"
                }
            )
            
            # Wait a bit for processing
            await asyncio.sleep(3)
            
            # Get health status
            health = await orchestrator.get_service_health()
            print("Health status:", json.dumps(health, indent=2, default=str))
            
        finally:
            await orchestrator.stop()
    
    asyncio.run(main())
