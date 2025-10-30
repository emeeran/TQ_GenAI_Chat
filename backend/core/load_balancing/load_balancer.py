"""
Load balancing and auto-scaling system for TQ GenAI Chat application.
Provides intelligent request distribution and dynamic scaling capabilities.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import aiohttp

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """Represents a service instance in the load balancer."""

    id: str
    host: str
    port: int
    weight: int = 1
    health_score: float = 1.0
    last_health_check: float = 0
    active_connections: int = 0
    response_times: deque = None
    error_count: int = 0

    def __post_init__(self):
        if self.response_times is None:
            self.response_times = deque(maxlen=100)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def average_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def is_healthy(self) -> bool:
        return self.health_score > 0.5 and self.error_count < 10


class HealthChecker:
    """Health monitoring for service instances."""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.running = False
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        """Start the health checker."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))
        self.running = True
        asyncio.create_task(self._health_check_loop())
        logger.info("Health checker started")

    async def stop(self):
        """Stop the health checker."""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Health checker stopped")

    async def check_instance_health(self, instance: ServiceInstance) -> float:
        """Check health of a single instance. Returns health score 0.0-1.0."""
        try:
            start_time = time.time()

            async with self.session.get(
                f"{instance.url}/health", timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                response_time = time.time() - start_time

                if response.status == 200:
                    # Update response time metrics
                    instance.response_times.append(response_time)
                    instance.last_health_check = time.time()

                    # Calculate health score based on response time
                    if response_time < 0.1:  # Very fast
                        health_score = 1.0
                    elif response_time < 0.5:  # Fast
                        health_score = 0.9
                    elif response_time < 1.0:  # Acceptable
                        health_score = 0.7
                    elif response_time < 2.0:  # Slow
                        health_score = 0.5
                    else:  # Very slow
                        health_score = 0.3

                    # Adjust for error rate
                    if instance.error_count > 0:
                        health_score *= max(0.1, 1.0 - (instance.error_count / 50))

                    instance.health_score = health_score
                    instance.error_count = max(0, instance.error_count - 1)  # Decay errors

                    return health_score
                else:
                    instance.error_count += 1
                    instance.health_score = 0.1
                    return 0.1

        except Exception as e:
            logger.warning(f"Health check failed for {instance.url}: {e}")
            instance.error_count += 2
            instance.health_score = 0.0
            return 0.0

    async def _health_check_loop(self):
        """Continuous health checking loop."""
        while self.running:
            # This will be called by the load balancer with instances
            await asyncio.sleep(self.check_interval)


class LoadBalancingStrategy:
    """Base class for load balancing strategies."""

    def select_instance(
        self, instances: list[ServiceInstance], request_context: dict = None
    ) -> ServiceInstance | None:
        raise NotImplementedError


class RoundRobinStrategy(LoadBalancingStrategy):
    """Simple round-robin load balancing."""

    def __init__(self):
        self.current_index = 0

    def select_instance(
        self, instances: list[ServiceInstance], request_context: dict = None
    ) -> ServiceInstance | None:
        healthy_instances = [inst for inst in instances if inst.is_healthy]
        if not healthy_instances:
            return None

        instance = healthy_instances[self.current_index % len(healthy_instances)]
        self.current_index += 1
        return instance


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Weighted round-robin considering instance weights."""

    def __init__(self):
        self.current_weights = {}

    def select_instance(
        self, instances: list[ServiceInstance], request_context: dict = None
    ) -> ServiceInstance | None:
        healthy_instances = [inst for inst in instances if inst.is_healthy]
        if not healthy_instances:
            return None

        # Update current weights
        for instance in healthy_instances:
            if instance.id not in self.current_weights:
                self.current_weights[instance.id] = 0
            self.current_weights[instance.id] += instance.weight

        # Select instance with highest current weight
        selected = max(healthy_instances, key=lambda inst: self.current_weights[inst.id])

        # Reduce selected instance's current weight
        total_weight = sum(inst.weight for inst in healthy_instances)
        self.current_weights[selected.id] -= total_weight

        return selected


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Route to instance with fewest active connections."""

    def select_instance(
        self, instances: list[ServiceInstance], request_context: dict = None
    ) -> ServiceInstance | None:
        healthy_instances = [inst for inst in instances if inst.is_healthy]
        if not healthy_instances:
            return None

        return min(healthy_instances, key=lambda inst: inst.active_connections)


class ResponseTimeStrategy(LoadBalancingStrategy):
    """Route to instance with best response time."""

    def select_instance(
        self, instances: list[ServiceInstance], request_context: dict = None
    ) -> ServiceInstance | None:
        healthy_instances = [inst for inst in instances if inst.is_healthy]
        if not healthy_instances:
            return None

        # Prefer instances with good response times and low connections
        def score_instance(instance):
            avg_response = instance.average_response_time or 0.5
            connections_factor = 1 + (instance.active_connections * 0.1)
            health_factor = instance.health_score
            return (avg_response * connections_factor) / health_factor

        return min(healthy_instances, key=score_instance)


class ConsistentHashStrategy(LoadBalancingStrategy):
    """Consistent hashing for session affinity."""

    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_instance(self, instance: ServiceInstance):
        """Add instance to the hash ring."""
        for i in range(self.replicas):
            replica_key = f"{instance.id}:{i}"
            hash_value = self._hash(replica_key)
            self.ring[hash_value] = instance

        self.sorted_keys = sorted(self.ring.keys())

    def remove_instance(self, instance: ServiceInstance):
        """Remove instance from the hash ring."""
        for i in range(self.replicas):
            replica_key = f"{instance.id}:{i}"
            hash_value = self._hash(replica_key)
            if hash_value in self.ring:
                del self.ring[hash_value]

        self.sorted_keys = sorted(self.ring.keys())

    def select_instance(
        self, instances: list[ServiceInstance], request_context: dict = None
    ) -> ServiceInstance | None:
        if not instances or not request_context:
            return None

        # Use user_id or session_id for consistent routing
        routing_key = (
            request_context.get("user_id") or request_context.get("session_id") or "default"
        )
        hash_value = self._hash(routing_key)

        # Find the first instance clockwise on the ring
        for key in self.sorted_keys:
            if key >= hash_value:
                instance = self.ring[key]
                if instance.is_healthy:
                    return instance

        # Wrap around to the beginning
        if self.sorted_keys:
            instance = self.ring[self.sorted_keys[0]]
            if instance.is_healthy:
                return instance

        return None


class LoadBalancer:
    """
    Advanced load balancer with multiple strategies and health checking.
    """

    def __init__(self, strategy: str = "response_time", redis_client=None):
        self.instances: dict[str, ServiceInstance] = {}
        self.health_checker = HealthChecker()
        self.redis_client = redis_client

        # Initialize strategy
        strategies = {
            "round_robin": RoundRobinStrategy(),
            "weighted_round_robin": WeightedRoundRobinStrategy(),
            "least_connections": LeastConnectionsStrategy(),
            "response_time": ResponseTimeStrategy(),
            "consistent_hash": ConsistentHashStrategy(),
        }

        self.strategy = strategies.get(strategy, ResponseTimeStrategy())

        # Metrics
        self.request_count = 0
        self.total_response_time = 0.0
        self.error_count = 0

        # Circuit breaker
        self.circuit_breaker_threshold = 10
        self.circuit_breaker_timeout = 60
        self.failed_instances = {}

    async def start(self):
        """Start the load balancer."""
        await self.health_checker.start()

        # Start health check loop for instances
        asyncio.create_task(self._health_check_instances())

        logger.info(f"Load balancer started with {type(self.strategy).__name__} strategy")

    async def stop(self):
        """Stop the load balancer."""
        await self.health_checker.stop()
        logger.info("Load balancer stopped")

    def add_instance(self, instance_id: str, host: str, port: int, weight: int = 1):
        """Add a service instance."""
        instance = ServiceInstance(id=instance_id, host=host, port=port, weight=weight)

        self.instances[instance_id] = instance

        # Add to consistent hash ring if using that strategy
        if isinstance(self.strategy, ConsistentHashStrategy):
            self.strategy.add_instance(instance)

        logger.info(f"Added instance {instance_id} at {host}:{port}")

    def remove_instance(self, instance_id: str):
        """Remove a service instance."""
        if instance_id in self.instances:
            instance = self.instances[instance_id]

            # Remove from consistent hash ring if using that strategy
            if isinstance(self.strategy, ConsistentHashStrategy):
                self.strategy.remove_instance(instance)

            del self.instances[instance_id]
            logger.info(f"Removed instance {instance_id}")

    async def route_request(self, request_context: dict = None) -> ServiceInstance | None:
        """Route a request to an appropriate instance."""
        instances = list(self.instances.values())

        # Filter out circuit-broken instances
        current_time = time.time()
        available_instances = []

        for instance in instances:
            if instance.id in self.failed_instances:
                if current_time - self.failed_instances[instance.id] > self.circuit_breaker_timeout:
                    # Try to recover the instance
                    del self.failed_instances[instance.id]
                    available_instances.append(instance)
                # else: instance is still in circuit breaker timeout
            else:
                available_instances.append(instance)

        if not available_instances:
            logger.error("No available instances for routing")
            return None

        # Use strategy to select instance
        selected_instance = self.strategy.select_instance(available_instances, request_context)

        if selected_instance:
            selected_instance.active_connections += 1
            self.request_count += 1

        return selected_instance

    async def complete_request(
        self, instance: ServiceInstance, response_time: float, success: bool
    ):
        """Mark request as completed and update metrics."""
        if instance:
            instance.active_connections = max(0, instance.active_connections - 1)
            instance.response_times.append(response_time)

            self.total_response_time += response_time

            if not success:
                instance.error_count += 1
                self.error_count += 1

                # Circuit breaker logic
                if instance.error_count > self.circuit_breaker_threshold:
                    self.failed_instances[instance.id] = time.time()
                    logger.warning(f"Instance {instance.id} circuit breaker activated")

    async def _health_check_instances(self):
        """Periodically check health of all instances."""
        while True:
            try:
                for instance in self.instances.values():
                    await self.health_checker.check_instance_health(instance)

                # Update metrics in Redis if available
                if self.redis_client:
                    await self._update_metrics_in_redis()

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10)

    async def _update_metrics_in_redis(self):
        """Update load balancer metrics in Redis."""
        try:
            metrics = {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "average_response_time": self.total_response_time / max(1, self.request_count),
                "active_instances": len([i for i in self.instances.values() if i.is_healthy]),
                "total_instances": len(self.instances),
                "timestamp": time.time(),
            }

            await self.redis_client.setex(
                "load_balancer:metrics",
                300,
                json.dumps(metrics),  # 5 minutes TTL
            )

        except Exception as e:
            logger.error(f"Failed to update metrics in Redis: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """Get load balancer statistics."""
        healthy_instances = [i for i in self.instances.values() if i.is_healthy]

        return {
            "strategy": type(self.strategy).__name__,
            "total_instances": len(self.instances),
            "healthy_instances": len(healthy_instances),
            "failed_instances": len(self.failed_instances),
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count),
            "average_response_time": self.total_response_time / max(1, self.request_count),
            "active_connections": sum(i.active_connections for i in self.instances.values()),
            "instance_details": [
                {
                    "id": instance.id,
                    "url": instance.url,
                    "health_score": instance.health_score,
                    "active_connections": instance.active_connections,
                    "average_response_time": instance.average_response_time,
                    "error_count": instance.error_count,
                }
                for instance in self.instances.values()
            ],
        }


class AutoScaler:
    """
    Auto-scaling system for dynamic instance management.
    """

    def __init__(
        self,
        load_balancer: LoadBalancer,
        min_instances: int = 2,
        max_instances: int = 10,
    ):
        self.load_balancer = load_balancer
        self.min_instances = min_instances
        self.max_instances = max_instances

        # Scaling thresholds
        self.cpu_scale_up_threshold = 70.0  # CPU %
        self.cpu_scale_down_threshold = 30.0
        self.response_time_threshold = 2.0  # seconds
        self.error_rate_threshold = 0.05  # 5%

        # Scaling policies
        self.scale_up_cooldown = 180  # 3 minutes
        self.scale_down_cooldown = 300  # 5 minutes
        self.last_scale_up = 0
        self.last_scale_down = 0

        # Instance management
        self.next_instance_id = 1
        self.running = False

    async def start(self):
        """Start the auto-scaler."""
        self.running = True
        asyncio.create_task(self._scaling_loop())
        logger.info("Auto-scaler started")

    async def stop(self):
        """Stop the auto-scaler."""
        self.running = False
        logger.info("Auto-scaler stopped")

    async def _scaling_loop(self):
        """Main auto-scaling loop."""
        while self.running:
            try:
                await self._evaluate_scaling_decision()
                await asyncio.sleep(60)  # Evaluate every minute
            except Exception as e:
                logger.error(f"Error in auto-scaling loop: {e}")
                await asyncio.sleep(30)

    async def _evaluate_scaling_decision(self):
        """Evaluate whether to scale up or down."""
        stats = self.load_balancer.get_statistics()
        current_instances = stats["healthy_instances"]
        current_time = time.time()

        # Check if we should scale up
        should_scale_up = (
            current_instances < self.max_instances
            and current_time - self.last_scale_up > self.scale_up_cooldown
            and (
                stats["average_response_time"] > self.response_time_threshold
                or stats["error_rate"] > self.error_rate_threshold
                or await self._check_cpu_usage() > self.cpu_scale_up_threshold
            )
        )

        # Check if we should scale down
        should_scale_down = (
            current_instances > self.min_instances
            and current_time - self.last_scale_down > self.scale_down_cooldown
            and stats["average_response_time"] < self.response_time_threshold * 0.5
            and stats["error_rate"] < self.error_rate_threshold * 0.5
            and await self._check_cpu_usage() < self.cpu_scale_down_threshold
        )

        if should_scale_up:
            await self._scale_up()
        elif should_scale_down:
            await self._scale_down()

    async def _check_cpu_usage(self) -> float:
        """Check average CPU usage across instances."""
        # This would integrate with your monitoring system
        # For now, simulate based on load
        stats = self.load_balancer.get_statistics()

        # Estimate CPU usage based on response time and connections
        base_cpu = 20.0  # Base CPU usage
        response_time_factor = min(50.0, stats["average_response_time"] * 25)
        connection_factor = min(30.0, stats["active_connections"] * 2)

        estimated_cpu = base_cpu + response_time_factor + connection_factor
        return min(100.0, estimated_cpu)

    async def _scale_up(self):
        """Add a new instance."""
        try:
            instance_id = f"instance-{self.next_instance_id}"

            # In a real implementation, this would launch a new container/VM
            # For this example, we'll simulate adding an instance
            await self._launch_new_instance(instance_id)

            self.next_instance_id += 1
            self.last_scale_up = time.time()

            logger.info(f"Scaled up: added {instance_id}")

        except Exception as e:
            logger.error(f"Failed to scale up: {e}")

    async def _scale_down(self):
        """Remove an instance."""
        try:
            # Find the least busy healthy instance to remove
            instances = [i for i in self.load_balancer.instances.values() if i.is_healthy]

            if len(instances) <= self.min_instances:
                return

            # Select instance with lowest load
            instance_to_remove = min(instances, key=lambda i: i.active_connections)

            # Graceful shutdown: wait for active connections to finish
            await self._graceful_shutdown(instance_to_remove)

            self.load_balancer.remove_instance(instance_to_remove.id)
            self.last_scale_down = time.time()

            logger.info(f"Scaled down: removed {instance_to_remove.id}")

        except Exception as e:
            logger.error(f"Failed to scale down: {e}")

    async def _launch_new_instance(self, instance_id: str):
        """Launch a new service instance."""
        # In a real implementation, this would:
        # 1. Launch a new container/VM
        # 2. Wait for it to be ready
        # 3. Add it to the load balancer

        # For simulation, add a new instance on a different port
        base_port = 8000
        port = base_port + self.next_instance_id

        # Simulate instance startup
        await asyncio.sleep(2)

        self.load_balancer.add_instance(
            instance_id=instance_id,
            host="localhost",  # In production, this would be the actual host
            port=port,
            weight=1,
        )

    async def _graceful_shutdown(self, instance: ServiceInstance):
        """Gracefully shutdown an instance."""
        # Wait for active connections to finish (with timeout)
        timeout = 30  # 30 seconds
        start_time = time.time()

        while instance.active_connections > 0 and (time.time() - start_time) < timeout:
            await asyncio.sleep(1)

        if instance.active_connections > 0:
            logger.warning(
                f"Force shutting down {instance.id} with {instance.active_connections} active connections"
            )


# Global instances
_load_balancer = None
_auto_scaler = None


def get_load_balancer(strategy: str = "response_time", redis_client=None) -> LoadBalancer:
    """Get or create the global load balancer instance."""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(strategy, redis_client)
    return _load_balancer


def get_auto_scaler(
    load_balancer: LoadBalancer = None, min_instances: int = 2, max_instances: int = 10
) -> AutoScaler:
    """Get or create the global auto-scaler instance."""
    global _auto_scaler
    if _auto_scaler is None:
        lb = load_balancer or get_load_balancer()
        _auto_scaler = AutoScaler(lb, min_instances, max_instances)
    return _auto_scaler


# Flask middleware for load balancing
class LoadBalancerMiddleware:
    """Flask middleware for load balancing requests."""

    def __init__(self, app, load_balancer: LoadBalancer):
        self.app = app
        self.load_balancer = load_balancer
        self.wsgi_app = app.wsgi_app
        app.wsgi_app = self

    def __call__(self, environ, start_response):
        """WSGI middleware entry point."""
        # Route request through load balancer if needed
        # This is a simplified example - full implementation would
        # proxy requests to other instances
        return self.wsgi_app(environ, start_response)


# Example usage and configuration
async def setup_load_balancing_example():
    """Example setup for load balancing system."""

    # Create load balancer with response time strategy
    lb = get_load_balancer("response_time")

    # Add initial instances
    lb.add_instance("instance-1", "localhost", 8001, weight=1)
    lb.add_instance("instance-2", "localhost", 8002, weight=1)
    lb.add_instance("instance-3", "localhost", 8003, weight=2)  # Higher weight

    # Start load balancer
    await lb.start()

    # Create auto-scaler
    scaler = get_auto_scaler(lb, min_instances=2, max_instances=8)
    await scaler.start()

    logger.info("Load balancing system ready")

    return lb, scaler


if __name__ == "__main__":
    import asyncio

    async def main():
        lb, scaler = await setup_load_balancing_example()

        # Simulate some requests
        for i in range(10):
            instance = await lb.route_request({"user_id": f"user_{i}"})
            if instance:
                # Simulate request completion
                import random

                response_time = random.uniform(0.1, 2.0)
                success = random.random() > 0.1  # 90% success rate

                await lb.complete_request(instance, response_time, success)

        # Print statistics
        lb.get_statistics()

        await lb.stop()
        await scaler.stop()

    asyncio.run(main())
