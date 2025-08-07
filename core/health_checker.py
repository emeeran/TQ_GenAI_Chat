"""
Health Check Automation System (Task 4.1.3)

This module implements comprehensive automated health monitoring for the TQ GenAI Chat application,
including provider availability, database health, cache system monitoring, and automated failover triggers.
"""

import asyncio
import json
import logging
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import psutil
import redis
import requests

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "error": self.error,
        }


@dataclass
class HealthThresholds:
    """Health check thresholds configuration."""

    # Response time thresholds (milliseconds)
    response_time_warning: float = 1000
    response_time_critical: float = 5000

    # Database thresholds
    db_max_connections: int = 100
    db_max_query_time_ms: float = 1000

    # Memory thresholds
    memory_warning_percent: float = 80
    memory_critical_percent: float = 90

    # Cache thresholds
    cache_hit_rate_warning: float = 0.7
    cache_hit_rate_critical: float = 0.5

    # Provider thresholds
    provider_timeout_seconds: float = 10
    provider_consecutive_failures: int = 3


class BaseHealthChecker:
    """Base class for health checkers."""

    def __init__(self, name: str, check_interval: int = 30):
        self.name = name
        self.check_interval = check_interval
        self.last_check_time = None
        self.last_result = None
        self.enabled = True

    async def check_health(self) -> HealthCheckResult:
        """Perform health check. Override in subclasses."""
        raise NotImplementedError

    def should_check(self) -> bool:
        """Check if health check should be performed."""
        if not self.enabled:
            return False

        if self.last_check_time is None:
            return True

        return (datetime.now() - self.last_check_time).total_seconds() >= self.check_interval

    async def run_check(self) -> Optional[HealthCheckResult]:
        """Run health check if needed."""
        if not self.should_check():
            return self.last_result

        start_time = time.time()
        try:
            result = await self.check_health()
            result.response_time_ms = (time.time() - start_time) * 1000
            self.last_result = result
            self.last_check_time = datetime.now()
            return result
        except Exception as e:
            error_result = HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
            self.last_result = error_result
            self.last_check_time = datetime.now()
            return error_result


class DatabaseHealthChecker(BaseHealthChecker):
    """Health checker for database systems."""

    def __init__(self, db_path: str = "documents.db", thresholds: HealthThresholds = None):
        super().__init__("database", check_interval=30)
        self.db_path = db_path
        self.thresholds = thresholds or HealthThresholds()

    async def check_health(self) -> HealthCheckResult:
        """Check database health."""
        details = {}

        try:
            # Test basic connectivity
            start_time = time.time()
            conn = sqlite3.connect(self.db_path, timeout=5)

            # Test simple query
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            query_time = (time.time() - start_time) * 1000

            details["table_count"] = table_count
            details["query_time_ms"] = query_time

            # Check database size
            import os

            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)
                details["database_size_mb"] = db_size / 1024 / 1024

            # Check for recent activity
            cursor.execute("PRAGMA database_list")
            db_info = cursor.fetchall()
            details["database_info"] = [{"name": row[1], "file": row[2]} for row in db_info]

            conn.close()

            # Determine status
            if query_time > self.thresholds.db_max_query_time_ms:
                status = HealthStatus.DEGRADED
                message = f"Database queries slow ({query_time:.1f}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database operational ({table_count} tables)"

            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                details=details,
            )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                timestamp=datetime.now(),
                error=str(e),
            )


class CacheHealthChecker(BaseHealthChecker):
    """Health checker for cache systems (Redis)."""

    def __init__(self, redis_config: dict[str, Any] = None, thresholds: HealthThresholds = None):
        super().__init__("cache", check_interval=30)
        self.redis_config = redis_config or {"host": "localhost", "port": 6379, "db": 0}
        self.thresholds = thresholds or HealthThresholds()

    async def check_health(self) -> HealthCheckResult:
        """Check cache system health."""
        details = {}

        try:
            # Connect to Redis
            r = redis.Redis(**self.redis_config, socket_timeout=5)

            # Test basic operations
            start_time = time.time()
            r.ping()
            ping_time = (time.time() - start_time) * 1000

            # Get cache statistics
            info = r.info()
            details.update(
                {
                    "ping_time_ms": ping_time,
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_mb": info.get("used_memory", 0) / 1024 / 1024,
                    "used_memory_peak_mb": info.get("used_memory_peak", 0) / 1024 / 1024,
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                }
            )

            # Calculate hit rate
            hits = details["keyspace_hits"]
            misses = details["keyspace_misses"]
            total_requests = hits + misses
            hit_rate = hits / total_requests if total_requests > 0 else 0
            details["hit_rate"] = hit_rate

            # Test write/read operations
            test_key = f"health_check_{datetime.now().timestamp()}"
            r.set(test_key, "test_value", ex=60)
            test_value = r.get(test_key)
            r.delete(test_key)

            if test_value != b"test_value":
                raise Exception("Cache read/write test failed")

            # Determine status
            if hit_rate < self.thresholds.cache_hit_rate_critical:
                status = HealthStatus.UNHEALTHY
                message = f"Cache hit rate critically low ({hit_rate:.2%})"
            elif hit_rate < self.thresholds.cache_hit_rate_warning:
                status = HealthStatus.DEGRADED
                message = f"Cache hit rate low ({hit_rate:.2%})"
            else:
                status = HealthStatus.HEALTHY
                message = f"Cache operational (hit rate: {hit_rate:.2%})"

            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                details=details,
            )

        except redis.ConnectionError:
            # Redis not available - fall back to memory cache
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.DEGRADED,
                message="Redis unavailable, using memory cache fallback",
                timestamp=datetime.now(),
                details={"fallback_mode": True},
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Cache system error: {str(e)}",
                timestamp=datetime.now(),
                error=str(e),
            )


class ProviderHealthChecker(BaseHealthChecker):
    """Health checker for AI providers."""

    def __init__(
        self, provider_configs: dict[str, dict[str, Any]], thresholds: HealthThresholds = None
    ):
        super().__init__("providers", check_interval=60)
        self.provider_configs = provider_configs
        self.thresholds = thresholds or HealthThresholds()
        self.failure_counts = {provider: 0 for provider in provider_configs}

    async def check_health(self) -> HealthCheckResult:
        """Check AI provider health."""
        provider_results = {}
        overall_status = HealthStatus.HEALTHY
        healthy_providers = 0
        total_providers = len(self.provider_configs)

        for provider_name, config in self.provider_configs.items():
            try:
                result = await self._check_provider(provider_name, config)
                provider_results[provider_name] = result

                if result["status"] == HealthStatus.HEALTHY.value:
                    healthy_providers += 1
                    self.failure_counts[provider_name] = 0
                else:
                    self.failure_counts[provider_name] += 1

            except Exception as e:
                provider_results[provider_name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(e),
                    "response_time_ms": 0,
                }
                self.failure_counts[provider_name] += 1

        # Determine overall status
        healthy_ratio = healthy_providers / total_providers
        if healthy_ratio == 0:
            overall_status = HealthStatus.UNHEALTHY
            message = "All providers unavailable"
        elif healthy_ratio < 0.5:
            overall_status = HealthStatus.DEGRADED
            message = f"Only {healthy_providers}/{total_providers} providers healthy"
        else:
            overall_status = HealthStatus.HEALTHY
            message = f"{healthy_providers}/{total_providers} providers healthy"

        return HealthCheckResult(
            component=self.name,
            status=overall_status,
            message=message,
            timestamp=datetime.now(),
            details={
                "providers": provider_results,
                "healthy_count": healthy_providers,
                "total_count": total_providers,
                "failure_counts": self.failure_counts.copy(),
            },
        )

    async def _check_provider(self, provider_name: str, config: dict[str, Any]) -> dict[str, Any]:
        """Check individual provider health."""
        # Simple availability check - attempt to reach the endpoint
        endpoint = config.get("endpoint", "")
        api_key = config.get("key", "")

        if not endpoint or not api_key:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": "Missing endpoint or API key",
                "response_time_ms": 0,
            }

        try:
            start_time = time.time()

            # Create a minimal test request
            headers = {"Authorization": f"Bearer {api_key}"}

            # Use a HEAD request to avoid consuming quota
            response = requests.head(
                endpoint, headers=headers, timeout=self.thresholds.provider_timeout_seconds
            )

            response_time = (time.time() - start_time) * 1000

            # Check response
            if response.status_code in [200, 401, 403]:  # 401/403 means endpoint is up
                if response_time > self.thresholds.response_time_critical:
                    status = HealthStatus.DEGRADED
                else:
                    status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.UNHEALTHY

            return {
                "status": status.value,
                "response_time_ms": response_time,
                "status_code": response.status_code,
            }

        except requests.exceptions.Timeout:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": "Request timeout",
                "response_time_ms": self.thresholds.provider_timeout_seconds * 1000,
            }
        except Exception as e:
            return {"status": HealthStatus.UNHEALTHY.value, "error": str(e), "response_time_ms": 0}


class SystemHealthChecker(BaseHealthChecker):
    """Health checker for system resources."""

    def __init__(self, thresholds: HealthThresholds = None):
        super().__init__("system", check_interval=30)
        self.thresholds = thresholds or HealthThresholds()

    async def check_health(self) -> HealthCheckResult:
        """Check system resource health."""
        details = {}

        try:
            # Memory usage
            memory = psutil.virtual_memory()
            details["memory_percent"] = memory.percent
            details["memory_available_mb"] = memory.available / 1024 / 1024
            details["memory_used_mb"] = memory.used / 1024 / 1024

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            details["cpu_percent"] = cpu_percent
            details["cpu_count"] = psutil.cpu_count()

            # Disk usage
            disk = psutil.disk_usage("/")
            details["disk_percent"] = (disk.used / disk.total) * 100
            details["disk_free_gb"] = disk.free / 1024 / 1024 / 1024

            # Network
            net_io = psutil.net_io_counters()
            details["network_bytes_sent"] = net_io.bytes_sent
            details["network_bytes_recv"] = net_io.bytes_recv

            # Process count
            details["process_count"] = len(psutil.pids())

            # Load average (Unix only)
            try:
                load_avg = psutil.getloadavg()
                details["load_average_1m"] = load_avg[0]
                details["load_average_5m"] = load_avg[1]
                details["load_average_15m"] = load_avg[2]
            except AttributeError:
                pass  # Windows doesn't have load average

            # Determine status
            if memory.percent > self.thresholds.memory_critical_percent:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory usage ({memory.percent:.1f}%)"
            elif memory.percent > self.thresholds.memory_warning_percent:
                status = HealthStatus.DEGRADED
                message = f"High memory usage ({memory.percent:.1f}%)"
            elif cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High CPU usage ({cpu_percent:.1f}%)"
            else:
                status = HealthStatus.HEALTHY
                message = f"System resources normal (CPU: {cpu_percent:.1f}%, Memory: {memory.percent:.1f}%)"

            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                timestamp=datetime.now(),
                details=details,
            )

        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"System monitoring error: {str(e)}",
                timestamp=datetime.now(),
                error=str(e),
            )


class HealthMonitor:
    """Main health monitoring system."""

    def __init__(self, thresholds: HealthThresholds = None):
        self.thresholds = thresholds or HealthThresholds()
        self.checkers: list[BaseHealthChecker] = []
        self.monitoring_active = False
        self.monitor_thread = None
        self.check_interval = 30

        # Health history
        self.health_history = []
        self.max_history = 1000

        # Callbacks for health changes
        self.health_callbacks: list[Callable] = []

        # Failover triggers
        self.failover_triggers: dict[str, Callable] = {}

    def add_checker(self, checker: BaseHealthChecker):
        """Add a health checker."""
        self.checkers.append(checker)
        logger.info(f"Added health checker: {checker.name}")

    def add_health_callback(self, callback: Callable):
        """Add callback for health status changes."""
        self.health_callbacks.append(callback)

    def add_failover_trigger(self, component: str, trigger: Callable):
        """Add failover trigger for specific component."""
        self.failover_triggers[component] = trigger

    def start_monitoring(self):
        """Start health monitoring."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Health monitoring started")

    def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Health monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                asyncio.run(self._run_health_checks())
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(self.check_interval)

    async def _run_health_checks(self):
        """Run all health checks."""
        tasks = []
        for checker in self.checkers:
            if checker.enabled:
                tasks.append(checker.run_check())

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, HealthCheckResult):
                    self._process_health_result(result)
                elif isinstance(result, Exception):
                    logger.error(f"Health check error: {result}")

    def _process_health_result(self, result: HealthCheckResult):
        """Process health check result."""
        # Store in history
        if len(self.health_history) >= self.max_history:
            self.health_history.pop(0)
        self.health_history.append(result)

        # Log significant status changes
        if result.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]:
            logger.warning(f"Health issue detected - {result.component}: {result.message}")

        # Trigger callbacks
        for callback in self.health_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in health callback: {e}")

        # Check for failover triggers
        if result.status == HealthStatus.UNHEALTHY and result.component in self.failover_triggers:
            try:
                self.failover_triggers[result.component](result)
                logger.info(f"Triggered failover for component: {result.component}")
            except Exception as e:
                logger.error(f"Error in failover trigger for {result.component}: {e}")

    async def get_current_health(self) -> dict[str, Any]:
        """Get current health status of all components."""
        tasks = []
        for checker in self.checkers:
            if checker.enabled:
                tasks.append(checker.run_check())

        if not tasks:
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "message": "No health checkers configured",
                "components": {},
                "timestamp": datetime.now().isoformat(),
            }

        results = await asyncio.gather(*tasks, return_exceptions=True)

        components = {}
        statuses = []

        for result in results:
            if isinstance(result, HealthCheckResult):
                components[result.component] = result.to_dict()
                statuses.append(result.status)
            else:
                logger.error(f"Health check failed: {result}")

        # Determine overall status
        if not statuses:
            overall_status = HealthStatus.UNKNOWN
        elif HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        healthy_components = sum(1 for s in statuses if s == HealthStatus.HEALTHY)
        total_components = len(statuses)

        return {
            "overall_status": overall_status.value,
            "message": f"{healthy_components}/{total_components} components healthy",
            "components": components,
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self.monitoring_active,
        }

    def get_health_history(self, component: str = None, hours: int = 24) -> list[dict[str, Any]]:
        """Get health history for analysis."""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_history = [
            result
            for result in self.health_history
            if result.timestamp >= cutoff_time
            and (component is None or result.component == component)
        ]

        return [result.to_dict() for result in filtered_history]

    def get_health_summary(self) -> dict[str, Any]:
        """Get health summary statistics."""
        if not self.health_history:
            return {}

        recent_results = [
            r for r in self.health_history if r.timestamp >= datetime.now() - timedelta(hours=1)
        ]

        component_stats = {}
        for result in recent_results:
            if result.component not in component_stats:
                component_stats[result.component] = {
                    "healthy": 0,
                    "degraded": 0,
                    "unhealthy": 0,
                    "total": 0,
                    "avg_response_time": 0,
                }

            stats = component_stats[result.component]
            stats["total"] += 1
            stats["avg_response_time"] += result.response_time_ms

            if result.status == HealthStatus.HEALTHY:
                stats["healthy"] += 1
            elif result.status == HealthStatus.DEGRADED:
                stats["degraded"] += 1
            elif result.status == HealthStatus.UNHEALTHY:
                stats["unhealthy"] += 1

        # Calculate averages and percentages
        for component, stats in component_stats.items():
            if stats["total"] > 0:
                stats["avg_response_time"] /= stats["total"]
                stats["health_percentage"] = (stats["healthy"] / stats["total"]) * 100

        return {
            "summary_period_hours": 1,
            "total_checks": len(recent_results),
            "component_stats": component_stats,
            "last_updated": datetime.now().isoformat(),
        }


# Global health monitor instance
_health_monitor = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def initialize_health_monitoring(
    provider_configs: dict[str, dict[str, Any]] = None,
    redis_config: dict[str, Any] = None,
    db_path: str = "documents.db",
):
    """Initialize health monitoring with default checkers."""
    monitor = get_health_monitor()

    # Add system health checker
    monitor.add_checker(SystemHealthChecker())

    # Add database health checker
    monitor.add_checker(DatabaseHealthChecker(db_path))

    # Add cache health checker
    if redis_config:
        monitor.add_checker(CacheHealthChecker(redis_config))

    # Add provider health checker
    if provider_configs:
        monitor.add_checker(ProviderHealthChecker(provider_configs))

    return monitor


def start_health_monitoring():
    """Start health monitoring."""
    monitor = get_health_monitor()
    monitor.start_monitoring()


def stop_health_monitoring():
    """Stop health monitoring."""
    monitor = get_health_monitor()
    monitor.stop_monitoring()


async def get_current_health() -> dict[str, Any]:
    """Get current health status."""
    monitor = get_health_monitor()
    return await monitor.get_current_health()


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        # Initialize health monitoring
        provider_configs = {
            "openai": {"endpoint": "https://api.openai.com/v1/chat/completions", "key": "test-key"}
        }

        monitor = initialize_health_monitoring(
            provider_configs=provider_configs,
            redis_config={"host": "localhost", "port": 6379, "db": 0},
        )

        # Start monitoring
        monitor.start_monitoring()

        # Get health status
        health = await monitor.get_current_health()
        print("Current Health Status:")
        print(json.dumps(health, indent=2))

        # Wait a bit for some checks
        await asyncio.sleep(5)

        # Get summary
        summary = monitor.get_health_summary()
        print("\nHealth Summary:")
        print(json.dumps(summary, indent=2))

        monitor.stop_monitoring()

    asyncio.run(main())
