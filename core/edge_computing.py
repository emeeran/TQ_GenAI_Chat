"""
Edge Computing framework for TQ GenAI Chat application.
Provides edge deployment strategies, distributed processing, and edge-specific optimizations.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    import docker

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

try:
    from kubernetes import client, config

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

logger = logging.getLogger(__name__)


class EdgeLocation(Enum):
    """Edge computing locations."""

    NORTH_AMERICA_EAST = "na-east"
    NORTH_AMERICA_WEST = "na-west"
    EUROPE_WEST = "eu-west"
    EUROPE_CENTRAL = "eu-central"
    ASIA_PACIFIC = "ap-southeast"
    ASIA_NORTHEAST = "ap-northeast"
    SOUTH_AMERICA = "sa-east"
    AFRICA = "af-south"
    AUSTRALIA = "au-southeast"


class DeploymentStrategy(Enum):
    """Edge deployment strategies."""

    REGIONAL_CLUSTERS = "regional_clusters"
    CDN_WORKERS = "cdn_workers"
    IOT_GATEWAYS = "iot_gateways"
    MOBILE_EDGE = "mobile_edge"
    HYBRID_CLOUD = "hybrid_cloud"


class EdgeNodeType(Enum):
    """Types of edge nodes."""

    FULL_NODE = "full_node"  # Complete application stack
    COMPUTE_NODE = "compute_node"  # Processing-only node
    CACHE_NODE = "cache_node"  # Caching and content delivery
    GATEWAY_NODE = "gateway_node"  # API gateway and routing
    STORAGE_NODE = "storage_node"  # Distributed storage


@dataclass
class EdgeNode:
    """Edge node configuration and status."""

    id: str
    name: str
    location: EdgeLocation
    node_type: EdgeNodeType
    cpu_cores: int
    memory_mb: int
    storage_gb: int
    network_bandwidth_mbps: int
    public_ip: str = ""
    private_ip: str = ""
    status: str = "unknown"
    last_heartbeat: datetime | None = None
    services: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location.value,
            "node_type": self.node_type.value,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "storage_gb": self.storage_gb,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "public_ip": self.public_ip,
            "private_ip": self.private_ip,
            "status": self.status,
            "last_heartbeat": (self.last_heartbeat.isoformat() if self.last_heartbeat else None),
            "services": self.services,
            "metadata": self.metadata,
        }


@dataclass
class EdgeService:
    """Edge service configuration."""

    name: str
    image: str
    version: str
    port: int
    replicas: int
    resource_requirements: dict[str, Any]
    environment: dict[str, str] = field(default_factory=dict)
    volumes: list[dict[str, Any]] = field(default_factory=list)
    health_check: dict[str, Any] = field(default_factory=dict)
    auto_scaling: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "image": self.image,
            "version": self.version,
            "port": self.port,
            "replicas": self.replicas,
            "resource_requirements": self.resource_requirements,
            "environment": self.environment,
            "volumes": self.volumes,
            "health_check": self.health_check,
            "auto_scaling": self.auto_scaling,
        }


@dataclass
class WorkloadDistribution:
    """Workload distribution configuration."""

    id: str
    name: str
    strategy: str
    rules: list[dict[str, Any]]
    fallback_location: EdgeLocation
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "strategy": self.strategy,
            "rules": self.rules,
            "fallback_location": self.fallback_location.value,
            "created_at": self.created_at.isoformat(),
        }


class EdgeNodeManager:
    """Manages edge nodes and their status."""

    def __init__(self):
        self.nodes: dict[str, EdgeNode] = {}
        self.node_health_check_interval = 60  # seconds
        self.health_check_task = None

    def register_node(self, node: EdgeNode) -> bool:
        """Register a new edge node."""
        try:
            self.nodes[node.id] = node
            node.last_heartbeat = datetime.utcnow()
            logger.info(f"Registered edge node: {node.name} ({node.location.value})")
            return True
        except Exception as e:
            logger.error(f"Failed to register edge node {node.id}: {e}")
            return False

    def deregister_node(self, node_id: str) -> bool:
        """Deregister an edge node."""
        try:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                del self.nodes[node_id]
                logger.info(f"Deregistered edge node: {node.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to deregister edge node {node_id}: {e}")
            return False

    def get_nodes_by_location(self, location: EdgeLocation) -> list[EdgeNode]:
        """Get all nodes in a specific location."""
        return [node for node in self.nodes.values() if node.location == location]

    def get_nodes_by_type(self, node_type: EdgeNodeType) -> list[EdgeNode]:
        """Get all nodes of a specific type."""
        return [node for node in self.nodes.values() if node.node_type == node_type]

    def get_healthy_nodes(self) -> list[EdgeNode]:
        """Get all healthy nodes."""
        return [node for node in self.nodes.values() if node.status == "healthy"]

    def find_optimal_node(
        self, requirements: dict[str, Any], preferred_location: EdgeLocation = None
    ) -> EdgeNode | None:
        """Find optimal node for deployment based on requirements."""
        candidate_nodes = self.get_healthy_nodes()

        # Filter by location preference
        if preferred_location:
            location_nodes = [n for n in candidate_nodes if n.location == preferred_location]
            if location_nodes:
                candidate_nodes = location_nodes

        # Filter by resource requirements
        cpu_req = requirements.get("cpu_cores", 1)
        memory_req = requirements.get("memory_mb", 512)
        storage_req = requirements.get("storage_gb", 1)

        suitable_nodes = []
        for node in candidate_nodes:
            if (
                node.cpu_cores >= cpu_req
                and node.memory_mb >= memory_req
                and node.storage_gb >= storage_req
            ):
                suitable_nodes.append(node)

        if not suitable_nodes:
            return None

        # Score nodes based on available resources
        def score_node(node: EdgeNode) -> float:
            cpu_score = (node.cpu_cores - cpu_req) / node.cpu_cores
            memory_score = (node.memory_mb - memory_req) / node.memory_mb
            storage_score = (node.storage_gb - storage_req) / node.storage_gb
            return (cpu_score + memory_score + storage_score) / 3

        return max(suitable_nodes, key=score_node)

    async def start_health_monitoring(self):
        """Start continuous health monitoring of nodes."""
        if self.health_check_task is None:
            self.health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_monitoring(self):
        """Stop health monitoring."""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None

    async def _health_check_loop(self):
        """Continuous health check loop."""
        while True:
            try:
                await self._check_all_nodes_health()
                await asyncio.sleep(self.node_health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)

    async def _check_all_nodes_health(self):
        """Check health of all registered nodes."""
        health_check_tasks = []
        for node in self.nodes.values():
            task = asyncio.create_task(self._check_node_health(node))
            health_check_tasks.append(task)

        if health_check_tasks:
            await asyncio.gather(*health_check_tasks, return_exceptions=True)

    async def _check_node_health(self, node: EdgeNode):
        """Check health of a specific node."""
        try:
            if not node.public_ip:
                node.status = "unknown"
                return

            # Simple HTTP health check
            import aiohttp

            health_url = f"http://{node.public_ip}:8080/health"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_url, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        node.status = "healthy"
                        node.last_heartbeat = datetime.utcnow()
                    else:
                        node.status = "unhealthy"

        except Exception as e:
            logger.debug(f"Health check failed for node {node.id}: {e}")
            node.status = "unhealthy"

            # Mark as offline if no heartbeat for 5 minutes
            if node.last_heartbeat and datetime.utcnow() - node.last_heartbeat > timedelta(
                minutes=5
            ):
                node.status = "offline"


class EdgeOrchestrator:
    """Orchestrates edge computing deployments and workload distribution."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.node_manager = EdgeNodeManager()
        self.services: dict[str, EdgeService] = {}
        self.workload_distributions: dict[str, WorkloadDistribution] = {}

        # Initialize based on configuration
        self.strategy = DeploymentStrategy(config.get("deployment_strategy", "regional_clusters"))
        self.auto_scaling_enabled = config.get("auto_scaling_enabled", True)
        self.load_balancing_strategy = config.get("load_balancing_strategy", "round_robin")

    async def start(self):
        """Start the edge orchestrator."""
        await self.node_manager.start_health_monitoring()
        logger.info("Edge orchestrator started")

    async def stop(self):
        """Stop the edge orchestrator."""
        await self.node_manager.stop_health_monitoring()
        logger.info("Edge orchestrator stopped")

    def register_service(self, service: EdgeService) -> bool:
        """Register a new edge service."""
        try:
            self.services[service.name] = service
            logger.info(f"Registered edge service: {service.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register service {service.name}: {e}")
            return False

    async def deploy_service(
        self, service_name: str, target_locations: list[EdgeLocation] = None
    ) -> bool:
        """Deploy a service to edge locations."""
        if service_name not in self.services:
            logger.error(f"Service {service_name} not found")
            return False

        service = self.services[service_name]
        deployment_success = True

        # Determine target locations
        if not target_locations:
            target_locations = list(EdgeLocation)

        # Deploy to each location
        for location in target_locations:
            success = await self._deploy_service_to_location(service, location)
            if not success:
                deployment_success = False
                logger.error(f"Failed to deploy {service_name} to {location.value}")
            else:
                logger.info(f"Successfully deployed {service_name} to {location.value}")

        return deployment_success

    async def _deploy_service_to_location(
        self, service: EdgeService, location: EdgeLocation
    ) -> bool:
        """Deploy a service to a specific edge location."""
        try:
            # Find suitable node
            requirements = service.resource_requirements
            node = self.node_manager.find_optimal_node(requirements, location)

            if not node:
                logger.warning(f"No suitable node found for {service.name} in {location.value}")
                return False

            # Deploy based on node type and deployment strategy
            if self.strategy == DeploymentStrategy.REGIONAL_CLUSTERS:
                return await self._deploy_to_kubernetes_cluster(service, node)
            elif self.strategy == DeploymentStrategy.CDN_WORKERS:
                return await self._deploy_to_cdn_worker(service, node)
            elif self.strategy == DeploymentStrategy.IOT_GATEWAYS:
                return await self._deploy_to_iot_gateway(service, node)
            else:
                return await self._deploy_to_container(service, node)

        except Exception as e:
            logger.error(f"Deployment failed for {service.name} to {location.value}: {e}")
            return False

    async def _deploy_to_kubernetes_cluster(self, service: EdgeService, node: EdgeNode) -> bool:
        """Deploy service to Kubernetes cluster."""
        if not KUBERNETES_AVAILABLE:
            logger.error("Kubernetes client not available")
            return False

        try:
            # Generate Kubernetes manifest
            manifest = self._generate_k8s_manifest(service, node)

            # Apply manifest
            config.load_incluster_config()  # or load_kube_config() for local
            v1 = client.AppsV1Api()

            # Create deployment
            v1.create_namespaced_deployment(body=manifest, namespace="edge-services")

            # Add service to node's service list
            node.services.append(service.name)

            return True

        except Exception as e:
            logger.error(f"Kubernetes deployment failed: {e}")
            return False

    async def _deploy_to_container(self, service: EdgeService, node: EdgeNode) -> bool:
        """Deploy service as Docker container."""
        if not DOCKER_AVAILABLE:
            logger.error("Docker client not available")
            return False

        try:
            client = docker.from_env()

            # Pull image
            client.images.pull(f"{service.image}:{service.version}")

            # Create container
            container = client.containers.run(
                image=f"{service.image}:{service.version}",
                name=f"{service.name}-{node.id}",
                ports={f"{service.port}/tcp": service.port},
                environment=service.environment,
                detach=True,
                restart_policy={"Name": "always"},
            )

            # Add service to node's service list
            node.services.append(service.name)

            logger.info(f"Container {container.id} started for service {service.name}")
            return True

        except Exception as e:
            logger.error(f"Container deployment failed: {e}")
            return False

    async def _deploy_to_cdn_worker(self, service: EdgeService, node: EdgeNode) -> bool:
        """Deploy service as CDN edge worker."""
        # This would integrate with CDN providers like Cloudflare Workers, AWS Lambda@Edge
        logger.info(f"Deploying {service.name} as CDN worker to {node.location.value}")

        # Simulate CDN worker deployment
        try:
            # Generate worker script
            # worker_script = self._generate_cdn_worker_script(service)  # pylint: disable=unused-variable

            # Deploy to CDN (placeholder implementation)
            # In real implementation, this would use CDN provider APIs
            logger.info(f"CDN worker script generated for {service.name}")

            node.services.append(service.name)
            return True

        except Exception as e:
            logger.error(f"CDN worker deployment failed: {e}")
            return False

    async def _deploy_to_iot_gateway(self, service: EdgeService, node: EdgeNode) -> bool:
        """Deploy service to IoT gateway."""
        logger.info(f"Deploying {service.name} to IoT gateway {node.name}")

        try:
            # Generate lightweight deployment configuration
            # config = {  # pylint: disable=unused-variable
            #     'service_name': service.name,
            #     'image': f"{service.image}:{service.version}",
            #     'port': service.port,
            #     'resources': {
            #         'cpu_limit': '500m',
            #         'memory_limit': '256Mi'
            #     },
            #     'environment': service.environment
            # }

            # Deploy via SSH or edge agent (placeholder)
            logger.info(f"IoT gateway deployment configured for {service.name}")

            node.services.append(service.name)
            return True

        except Exception as e:
            logger.error(f"IoT gateway deployment failed: {e}")
            return False

    def _generate_k8s_manifest(self, service: EdgeService, node: EdgeNode) -> dict[str, Any]:
        """Generate Kubernetes deployment manifest."""
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"{service.name}-{node.location.value}",
                "namespace": "edge-services",
                "labels": {
                    "app": service.name,
                    "location": node.location.value,
                    "edge-node": node.id,
                },
            },
            "spec": {
                "replicas": service.replicas,
                "selector": {
                    "matchLabels": {
                        "app": service.name,
                        "location": node.location.value,
                    }
                },
                "template": {
                    "metadata": {"labels": {"app": service.name, "location": node.location.value}},
                    "spec": {
                        "containers": [
                            {
                                "name": service.name,
                                "image": f"{service.image}:{service.version}",
                                "ports": [{"containerPort": service.port}],
                                "env": [
                                    {"name": k, "value": v} for k, v in service.environment.items()
                                ],
                                "resources": service.resource_requirements,
                            }
                        ]
                    },
                },
            },
        }

    def _generate_cdn_worker_script(self, service: EdgeService) -> str:
        """Generate CDN worker script."""
        return f"""
// Edge worker for {service.name}
addEventListener('fetch', event => {{
    event.respondWith(handleRequest(event.request))
}})

async function handleRequest(request) {{
    const url = new URL(request.url)

    // Route to appropriate handler
    if (url.pathname.startsWith('/api/chat')) {{
        return await handleChatRequest(request)
    }} else if (url.pathname.startsWith('/api/files')) {{
        return await handleFileRequest(request)
    }}

    return new Response('Not Found', {{ status: 404 }})
}}

async function handleChatRequest(request) {{
    // Chat processing logic
    const response = await fetch('https://api.openai.com/v1/chat/completions', {{
        method: 'POST',
        headers: request.headers,
        body: request.body
    }})

    return response
}}

async function handleFileRequest(request) {{
    // File processing logic
    return new Response(JSON.stringify({{
        message: 'File processed at edge',
        location: '{service.name}'
    }}), {{
        headers: {{ 'Content-Type': 'application/json' }}
    }})
}}
"""

    async def scale_service(
        self, service_name: str, location: EdgeLocation, new_replicas: int
    ) -> bool:
        """Scale a service at specific location."""
        try:
            nodes = self.node_manager.get_nodes_by_location(location)

            for node in nodes:
                if service_name in node.services:
                    # Scale based on deployment type
                    if self.strategy == DeploymentStrategy.REGIONAL_CLUSTERS:
                        success = await self._scale_k8s_deployment(
                            service_name, location, new_replicas
                        )
                    else:
                        success = await self._scale_container_deployment(
                            service_name, node, new_replicas
                        )

                    if success:
                        logger.info(
                            f"Scaled {service_name} to {new_replicas} replicas in {location.value}"
                        )
                        return True

            return False

        except Exception as e:
            logger.error(f"Failed to scale service {service_name}: {e}")
            return False

    async def _scale_k8s_deployment(
        self, service_name: str, location: EdgeLocation, replicas: int
    ) -> bool:
        """Scale Kubernetes deployment."""
        try:
            if not KUBERNETES_AVAILABLE:
                return False

            config.load_incluster_config()
            v1 = client.AppsV1Api()

            # Patch deployment
            body = {"spec": {"replicas": replicas}}
            v1.patch_namespaced_deployment_scale(
                name=f"{service_name}-{location.value}",
                namespace="edge-services",
                body=body,
            )

            return True

        except Exception as e:
            logger.error(f"Kubernetes scaling failed: {e}")
            return False

    async def _scale_container_deployment(
        self, service_name: str, node: EdgeNode, replicas: int
    ) -> bool:
        """Scale container deployment."""
        try:
            if not DOCKER_AVAILABLE:
                return False

            docker_client = docker.from_env()

            # Get existing containers
            containers = docker_client.containers.list(
                filters={"name": f"{service_name}-{node.id}"}
            )

            current_replicas = len(containers)

            if replicas > current_replicas:
                # Scale up
                service = self.services[service_name]
                for i in range(replicas - current_replicas):
                    docker_client.containers.run(
                        image=f"{service.image}:{service.version}",
                        name=f"{service_name}-{node.id}-{current_replicas + i}",
                        ports={f"{service.port}/tcp": service.port + i},
                        environment=service.environment,
                        detach=True,
                    )
            elif replicas < current_replicas:
                # Scale down
                containers_to_remove = containers[replicas:]
                for container in containers_to_remove:
                    container.stop()
                    container.remove()

            return True

        except Exception as e:
            logger.error(f"Container scaling failed: {e}")
            return False

    def create_workload_distribution(self, distribution: WorkloadDistribution) -> bool:
        """Create a workload distribution rule."""
        try:
            self.workload_distributions[distribution.id] = distribution
            logger.info(f"Created workload distribution: {distribution.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create workload distribution: {e}")
            return False

    def get_optimal_location_for_request(self, request_metadata: dict[str, Any]) -> EdgeLocation:
        """Determine optimal edge location for a request."""
        # client_ip = request_metadata.get('client_ip', '')  # pylint: disable=unused-variable
        user_location = request_metadata.get("user_location", "")
        # service_type = request_metadata.get('service_type', '')  # pylint: disable=unused-variable

        # Simple geolocation-based routing (in production, use GeoIP services)
        if "US" in user_location or "CA" in user_location:
            if "west" in user_location.lower():
                return EdgeLocation.NORTH_AMERICA_WEST
            else:
                return EdgeLocation.NORTH_AMERICA_EAST
        elif any(country in user_location for country in ["GB", "FR", "DE", "ES", "IT"]):
            return EdgeLocation.EUROPE_WEST
        elif any(country in user_location for country in ["PL", "CZ", "HU", "AT"]):
            return EdgeLocation.EUROPE_CENTRAL
        elif any(country in user_location for country in ["JP", "KR", "TW"]):
            return EdgeLocation.ASIA_NORTHEAST
        elif any(country in user_location for country in ["SG", "TH", "MY", "ID"]):
            return EdgeLocation.ASIA_PACIFIC
        elif any(country in user_location for country in ["BR", "AR", "CL"]):
            return EdgeLocation.SOUTH_AMERICA
        elif any(country in user_location for country in ["ZA", "NG", "EG"]):
            return EdgeLocation.AFRICA
        elif "AU" in user_location or "NZ" in user_location:
            return EdgeLocation.AUSTRALIA

        # Default fallback
        return EdgeLocation.NORTH_AMERICA_EAST

    async def get_edge_metrics(self) -> dict[str, Any]:
        """Get comprehensive edge computing metrics."""
        total_nodes = len(self.node_manager.nodes)
        healthy_nodes = len(self.node_manager.get_healthy_nodes())

        # Node distribution by location
        location_distribution = {}
        for location in EdgeLocation:
            nodes = self.node_manager.get_nodes_by_location(location)
            location_distribution[location.value] = len(nodes)

        # Service distribution
        service_distribution = {}
        for service_name in self.services.keys():
            service_distribution[service_name] = sum(
                1 for node in self.node_manager.nodes.values() if service_name in node.services
            )

        # Resource utilization (placeholder - would come from monitoring)
        total_cpu = sum(node.cpu_cores for node in self.node_manager.nodes.values())
        total_memory = sum(node.memory_mb for node in self.node_manager.nodes.values())
        total_storage = sum(node.storage_gb for node in self.node_manager.nodes.values())

        return {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "node_health_percentage": (
                (healthy_nodes / total_nodes * 100) if total_nodes > 0 else 0
            ),
            "location_distribution": location_distribution,
            "service_distribution": service_distribution,
            "resource_summary": {
                "total_cpu_cores": total_cpu,
                "total_memory_mb": total_memory,
                "total_storage_gb": total_storage,
            },
            "deployment_strategy": self.strategy.value,
            "auto_scaling_enabled": self.auto_scaling_enabled,
        }


class EdgeOptimizedCache:
    """Edge-optimized caching system."""

    def __init__(self, max_size_mb: int = 100):
        self.max_size_mb = max_size_mb
        self.cache: dict[str, dict[str, Any]] = {}
        self.access_times: dict[str, datetime] = {}
        self.current_size_mb = 0

    def put(self, key: str, value: Any, size_mb: float = 0.1, ttl_seconds: int = 3600):
        """Store item in edge cache."""
        # Evict if necessary
        while self.current_size_mb + size_mb > self.max_size_mb and self.cache:
            self._evict_lru()

        # Store item
        expire_time = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self.cache[key] = {
            "value": value,
            "size_mb": size_mb,
            "expire_time": expire_time,
        }
        self.access_times[key] = datetime.utcnow()
        self.current_size_mb += size_mb

    def get(self, key: str) -> Any:
        """Retrieve item from edge cache."""
        if key not in self.cache:
            return None

        item = self.cache[key]

        # Check expiration
        if datetime.utcnow() > item["expire_time"]:
            self._remove_item(key)
            return None

        # Update access time
        self.access_times[key] = datetime.utcnow()
        return item["value"]

    def invalidate(self, key: str):
        """Invalidate cache item."""
        if key in self.cache:
            self._remove_item(key)

    def _evict_lru(self):
        """Evict least recently used item."""
        if not self.access_times:
            return

        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_item(lru_key)

    def _remove_item(self, key: str):
        """Remove item from cache."""
        if key in self.cache:
            self.current_size_mb -= self.cache[key]["size_mb"]
            del self.cache[key]
            del self.access_times[key]

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_items": len(self.cache),
            "current_size_mb": self.current_size_mb,
            "max_size_mb": self.max_size_mb,
            "utilization_percent": (
                (self.current_size_mb / self.max_size_mb * 100) if self.max_size_mb > 0 else 0
            ),
        }


class TQGenAIEdgeManager:
    """Complete edge computing management for TQ GenAI Chat."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.orchestrator = EdgeOrchestrator(config)
        self.edge_cache = EdgeOptimizedCache(max_size_mb=config.get("cache_size_mb", 100))

        # Initialize edge services
        self._setup_edge_services()

    def _setup_edge_services(self):
        """Setup TQ GenAI Chat edge services."""
        # Chat service - lightweight version for edge
        chat_service = EdgeService(
            name="tq-chat-edge",
            image="tq-genai-chat/chat-edge",
            version="latest",
            port=8080,
            replicas=2,
            resource_requirements={
                "requests": {"cpu": "200m", "memory": "256Mi"},
                "limits": {"cpu": "500m", "memory": "512Mi"},
            },
            environment={
                "EDGE_MODE": "true",
                "CACHE_ENABLED": "true",
                "LOG_LEVEL": "INFO",
            },
            health_check={
                "path": "/health",
                "initial_delay_seconds": 30,
                "period_seconds": 10,
            },
            auto_scaling={
                "min_replicas": 1,
                "max_replicas": 5,
                "target_cpu_utilization": 70,
            },
        )

        # File processing service
        file_service = EdgeService(
            name="tq-file-edge",
            image="tq-genai-chat/file-edge",
            version="latest",
            port=8081,
            replicas=1,
            resource_requirements={
                "requests": {"cpu": "300m", "memory": "512Mi"},
                "limits": {"cpu": "1000m", "memory": "1Gi"},
            },
            environment={"EDGE_MODE": "true", "MAX_FILE_SIZE": "10MB"},
        )

        # API Gateway - edge routing
        gateway_service = EdgeService(
            name="tq-gateway-edge",
            image="tq-genai-chat/gateway-edge",
            version="latest",
            port=80,
            replicas=2,
            resource_requirements={
                "requests": {"cpu": "100m", "memory": "128Mi"},
                "limits": {"cpu": "300m", "memory": "256Mi"},
            },
            environment={
                "UPSTREAM_CHAT_SERVICE": "tq-chat-edge:8080",
                "UPSTREAM_FILE_SERVICE": "tq-file-edge:8081",
            },
        )

        # Register services
        self.orchestrator.register_service(chat_service)
        self.orchestrator.register_service(file_service)
        self.orchestrator.register_service(gateway_service)

    async def deploy_to_all_edges(self) -> bool:
        """Deploy TQ GenAI Chat to all edge locations."""
        try:
            # Deploy core services to major regions
            core_locations = [
                EdgeLocation.NORTH_AMERICA_EAST,
                EdgeLocation.NORTH_AMERICA_WEST,
                EdgeLocation.EUROPE_WEST,
                EdgeLocation.ASIA_PACIFIC,
            ]

            success = True
            for service_name in ["tq-chat-edge", "tq-file-edge", "tq-gateway-edge"]:
                deployment_success = await self.orchestrator.deploy_service(
                    service_name, core_locations
                )
                if not deployment_success:
                    success = False

            return success

        except Exception as e:
            logger.error(f"Edge deployment failed: {e}")
            return False

    async def route_request(self, request_metadata: dict[str, Any]) -> dict[str, Any]:
        """Route request to optimal edge location."""
        # Determine optimal location
        optimal_location = self.orchestrator.get_optimal_location_for_request(request_metadata)

        # Find healthy nodes at that location
        nodes = self.orchestrator.node_manager.get_nodes_by_location(optimal_location)
        healthy_nodes = [n for n in nodes if n.status == "healthy"]

        if not healthy_nodes:
            # Fallback to any healthy node
            healthy_nodes = self.orchestrator.node_manager.get_healthy_nodes()
            if healthy_nodes:
                optimal_location = healthy_nodes[0].location

        # Generate routing information
        return {
            "target_location": optimal_location.value,
            "endpoint": f"https://{optimal_location.value}.tq-genai.edge.com",
            "cache_enabled": True,
            "routing_metadata": {
                "latency_optimized": True,
                "edge_node_count": len(healthy_nodes),
            },
        }

    async def cache_response(self, key: str, response: Any, cache_duration: int = 300) -> bool:
        """Cache response at edge."""
        try:
            # Estimate response size (simplified)
            response_size = len(str(response)) / (1024 * 1024)  # MB

            self.edge_cache.put(
                key=key,
                value=response,
                size_mb=response_size,
                ttl_seconds=cache_duration,
            )

            return True

        except Exception as e:
            logger.error(f"Edge caching failed: {e}")
            return False

    async def get_cached_response(self, key: str) -> Any:
        """Get cached response from edge."""
        return self.edge_cache.get(key)

    async def get_edge_status(self) -> dict[str, Any]:
        """Get comprehensive edge status."""
        orchestrator_metrics = await self.orchestrator.get_edge_metrics()
        cache_stats = self.edge_cache.get_stats()

        return {
            "orchestrator": orchestrator_metrics,
            "cache": cache_stats,
            "deployment_status": {
                "services_deployed": len(self.orchestrator.services),
                "total_deployments": sum(
                    len(node.services) for node in self.orchestrator.node_manager.nodes.values()
                ),
            },
            "global_coverage": {
                "active_locations": len(
                    {node.location for node in self.orchestrator.node_manager.get_healthy_nodes()}
                ),
                "total_locations": len(EdgeLocation),
            },
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        # Configuration
        config = {
            "deployment_strategy": "regional_clusters",
            "auto_scaling_enabled": True,
            "load_balancing_strategy": "latency_based",
            "cache_size_mb": 500,
        }

        # Initialize edge manager
        edge_manager = TQGenAIEdgeManager(config)

        # Register some sample edge nodes
        nodes = [
            EdgeNode(
                id="edge-us-east-1",
                name="US East Edge Node",
                location=EdgeLocation.NORTH_AMERICA_EAST,
                node_type=EdgeNodeType.FULL_NODE,
                cpu_cores=8,
                memory_mb=16384,
                storage_gb=500,
                network_bandwidth_mbps=1000,
                public_ip="203.0.113.10",
            ),
            EdgeNode(
                id="edge-eu-west-1",
                name="EU West Edge Node",
                location=EdgeLocation.EUROPE_WEST,
                node_type=EdgeNodeType.FULL_NODE,
                cpu_cores=6,
                memory_mb=12288,
                storage_gb=300,
                network_bandwidth_mbps=500,
                public_ip="203.0.113.20",
            ),
        ]

        for node in nodes:
            edge_manager.orchestrator.node_manager.register_node(node)

        # Start orchestrator
        await edge_manager.orchestrator.start()

        # Test request routing
        request_metadata = {
            "client_ip": "203.0.113.100",
            "user_location": "US-NY",
            "service_type": "chat",
        }

        await edge_manager.route_request(request_metadata)

        # Test edge caching
        cache_key = "chat_response_12345"
        test_response = {"message": "Hello from edge!", "provider": "openai"}

        await edge_manager.cache_response(cache_key, test_response)
        await edge_manager.get_cached_response(cache_key)

        # Get edge status
        await edge_manager.get_edge_status()

        # Stop orchestrator
        await edge_manager.orchestrator.stop()

    asyncio.run(main())
