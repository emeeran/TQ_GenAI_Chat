"""
Advanced monitoring and analytics dashboard for TQ GenAI Chat application.
Provides real-time metrics, performance insights, and system health monitoring.
"""

import asyncio
import json
import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import plotly.graph_objs as go
    import plotly.offline as pyo

    PLOTLY_AVAILABLE = True
except ImportError:
    go = None
    pyo = None
    PLOTLY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""

    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    metric: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    duration: int  # seconds
    severity: str = "warning"  # "info", "warning", "error", "critical"
    enabled: bool = True


class TimeSeriesBuffer:
    """Efficient time series data buffer with automatic cleanup."""

    def __init__(self, max_points: int = 10000, retention_seconds: int = 86400):
        self.max_points = max_points
        self.retention_seconds = retention_seconds
        self.data = deque(maxlen=max_points)
        self._lock = threading.RLock()

    def add_point(self, timestamp: float, value: float, labels: dict[str, str] = None):
        """Add a metric point to the buffer."""
        with self._lock:
            point = MetricPoint(timestamp, value, labels or {})
            self.data.append(point)
            self._cleanup_old_data()

    def get_points(self, start_time: float = None, end_time: float = None) -> list[MetricPoint]:
        """Get points within time range."""
        with self._lock:
            if not start_time and not end_time:
                return list(self.data)

            result = []
            for point in self.data:
                if start_time and point.timestamp < start_time:
                    continue
                if end_time and point.timestamp > end_time:
                    break
                result.append(point)

            return result

    def get_latest(self, count: int = 1) -> list[MetricPoint]:
        """Get latest N points."""
        with self._lock:
            return list(self.data)[-count:] if self.data else []

    def aggregate(self, start_time: float, end_time: float, function: str = "avg") -> float | None:
        """Aggregate points within time range."""
        points = self.get_points(start_time, end_time)
        if not points:
            return None

        values = [p.value for p in points]

        if function == "avg":
            return statistics.mean(values)
        elif function == "sum":
            return sum(values)
        elif function == "min":
            return min(values)
        elif function == "max":
            return max(values)
        elif function == "count":
            return len(values)
        elif function == "p95":
            return statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values)
        elif function == "p99":
            return statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        else:
            return statistics.mean(values)

    def _cleanup_old_data(self):
        """Remove old data points."""
        if not self.data:
            return

        cutoff_time = time.time() - self.retention_seconds
        while self.data and self.data[0].timestamp < cutoff_time:
            self.data.popleft()


class SystemMonitor:
    """System resource monitoring."""

    def __init__(self):
        self.cpu_buffer = TimeSeriesBuffer()
        self.memory_buffer = TimeSeriesBuffer()
        self.disk_buffer = TimeSeriesBuffer()
        self.network_buffer = TimeSeriesBuffer()
        self.monitoring = False
        self.monitor_task = None

    async def start_monitoring(self, interval: float = 5.0):
        """Start system monitoring."""
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not available - system monitoring disabled")
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("System monitoring started")

    async def stop_monitoring(self):
        """Stop system monitoring."""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")

    async def _monitor_loop(self, interval: float):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                now = time.time()

                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self.cpu_buffer.add_point(now, cpu_percent)

                # Memory usage
                memory = psutil.virtual_memory()
                self.memory_buffer.add_point(now, memory.percent)

                # Disk usage
                disk = psutil.disk_usage("/")
                disk_percent = (disk.used / disk.total) * 100
                self.disk_buffer.add_point(now, disk_percent)

                # Network I/O
                network = psutil.net_io_counters()
                network_total = network.bytes_sent + network.bytes_recv
                self.network_buffer.add_point(now, network_total)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(interval)

    def get_current_stats(self) -> dict[str, Any]:
        """Get current system statistics."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not available"}

        stats = {
            "cpu": {
                "percent": psutil.cpu_percent(),
                "count": psutil.cpu_count(),
                "load_avg": (psutil.getloadavg() if hasattr(psutil, "getloadavg") else None),
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict(),
            "network": psutil.net_io_counters()._asdict(),
        }

        return stats


class ApplicationMonitor:
    """Application-specific monitoring."""

    def __init__(self):
        self.request_buffer = TimeSeriesBuffer()
        self.response_time_buffer = TimeSeriesBuffer()
        self.error_buffer = TimeSeriesBuffer()
        self.user_activity_buffer = TimeSeriesBuffer()

        # Provider-specific metrics
        self.provider_metrics = defaultdict(
            lambda: {
                "requests": TimeSeriesBuffer(),
                "response_times": TimeSeriesBuffer(),
                "errors": TimeSeriesBuffer(),
            }
        )

        # File processing metrics
        self.file_processing_buffer = TimeSeriesBuffer()

        # Custom counters
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)

    def record_request(
        self,
        path: str,
        method: str,
        status_code: int,
        response_time: float,
        provider: str = None,
    ):
        """Record HTTP request metrics."""
        now = time.time()

        # General request metrics
        self.request_buffer.add_point(
            now, 1, {"path": path, "method": method, "status": str(status_code)}
        )

        self.response_time_buffer.add_point(
            now, response_time, {"path": path, "status": str(status_code)}
        )

        # Error tracking
        if status_code >= 400:
            self.error_buffer.add_point(now, 1, {"path": path, "status": str(status_code)})

        # Provider-specific metrics
        if provider:
            metrics = self.provider_metrics[provider]
            metrics["requests"].add_point(now, 1)
            metrics["response_times"].add_point(now, response_time)

            if status_code >= 400:
                metrics["errors"].add_point(now, 1)

    def record_user_activity(self, user_id: str, action: str):
        """Record user activity."""
        now = time.time()
        self.user_activity_buffer.add_point(now, 1, {"user_id": user_id, "action": action})

    def record_file_processing(
        self, filename: str, size_bytes: int, processing_time: float, success: bool
    ):
        """Record file processing metrics."""
        now = time.time()
        self.file_processing_buffer.add_point(
            now,
            processing_time,
            {"filename": filename, "size": str(size_bytes), "success": str(success)},
        )

    def increment_counter(self, name: str, value: int = 1, labels: dict[str, str] = None):
        """Increment a counter metric."""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self.counters[key] += value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] = None):
        """Set a gauge metric."""
        key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
        self.gauges[key] = value

    def get_summary_stats(self, duration_minutes: int = 60) -> dict[str, Any]:
        """Get summary statistics for the last N minutes."""
        now = time.time()
        start_time = now - (duration_minutes * 60)

        stats = {
            "requests": {
                "total": len(self.request_buffer.get_points(start_time, now)),
                "rate_per_minute": self.request_buffer.aggregate(start_time, now, "count") or 0,
            },
            "response_time": {
                "avg": self.response_time_buffer.aggregate(start_time, now, "avg"),
                "p95": self.response_time_buffer.aggregate(start_time, now, "p95"),
                "p99": self.response_time_buffer.aggregate(start_time, now, "p99"),
            },
            "errors": {
                "total": len(self.error_buffer.get_points(start_time, now)),
                "rate": self.error_buffer.aggregate(start_time, now, "count") or 0,
            },
            "providers": {},
        }

        # Provider statistics
        for provider, metrics in self.provider_metrics.items():
            stats["providers"][provider] = {
                "requests": metrics["requests"].aggregate(start_time, now, "count") or 0,
                "avg_response_time": metrics["response_times"].aggregate(start_time, now, "avg"),
                "errors": metrics["errors"].aggregate(start_time, now, "count") or 0,
            }

        return stats


class AlertManager:
    """Alert management system."""

    def __init__(self):
        self.rules: list[AlertRule] = []
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.checking = False
        self.check_task = None

    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")

    async def start_checking(self, interval: float = 30.0):
        """Start alert checking."""
        self.checking = True
        self.check_task = asyncio.create_task(self._check_loop(interval))
        logger.info("Alert checking started")

    async def stop_checking(self):
        """Stop alert checking."""
        self.checking = False
        if self.check_task:
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert checking stopped")

    async def _check_loop(self, interval: float):
        """Main alert checking loop."""
        while self.checking:
            try:
                await self._check_all_rules()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Alert checking error: {e}")
                await asyncio.sleep(interval)

    async def _check_all_rules(self):
        """Check all alert rules."""
        now = time.time()

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                # This is a simplified check - in a real implementation,
                # you would evaluate the rule against actual metrics
                await self._check_rule(rule, now)
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")

    async def _check_rule(self, rule: AlertRule, now: float):
        """Check individual alert rule."""
        # Placeholder for rule evaluation logic
        # In a real implementation, this would:
        # 1. Query the metric value
        # 2. Apply the condition
        # 3. Check duration threshold
        # 4. Fire or resolve alerts
        pass

    def fire_alert(self, rule: AlertRule, value: float, message: str = None):
        """Fire an alert."""
        alert_id = f"{rule.name}:{int(time.time())}"
        alert = {
            "id": alert_id,
            "rule": rule.name,
            "severity": rule.severity,
            "value": value,
            "message": message or f"{rule.metric} {rule.condition} {rule.threshold}",
            "timestamp": time.time(),
            "status": "firing",
        }

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        logger.warning(f"Alert fired: {alert['message']}")

    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert["status"] = "resolved"
            alert["resolved_at"] = time.time()

            del self.active_alerts[alert_id]
            self.alert_history.append(alert)

            logger.info(f"Alert resolved: {alert['message']}")


class DashboardGenerator:
    """Generate monitoring dashboard visualizations."""

    def __init__(self, system_monitor: SystemMonitor, app_monitor: ApplicationMonitor):
        self.system_monitor = system_monitor
        self.app_monitor = app_monitor

    def generate_system_dashboard(self) -> dict[str, Any]:
        """Generate system monitoring dashboard data."""
        if not PLOTLY_AVAILABLE:
            return {"error": "Plotly not available for dashboard generation"}

        now = time.time()
        last_hour = now - 3600

        # CPU usage chart
        cpu_points = self.system_monitor.cpu_buffer.get_points(last_hour, now)
        cpu_times = [datetime.fromtimestamp(p.timestamp) for p in cpu_points]
        cpu_values = [p.value for p in cpu_points]

        cpu_chart = {
            "data": [
                {
                    "x": cpu_times,
                    "y": cpu_values,
                    "type": "scatter",
                    "name": "CPU Usage (%)",
                    "line": {"color": "#1f77b4"},
                }
            ],
            "layout": {
                "title": "CPU Usage (Last Hour)",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Usage (%)"},
            },
        }

        # Memory usage chart
        memory_points = self.system_monitor.memory_buffer.get_points(last_hour, now)
        memory_times = [datetime.fromtimestamp(p.timestamp) for p in memory_points]
        memory_values = [p.value for p in memory_points]

        memory_chart = {
            "data": [
                {
                    "x": memory_times,
                    "y": memory_values,
                    "type": "scatter",
                    "name": "Memory Usage (%)",
                    "line": {"color": "#ff7f0e"},
                }
            ],
            "layout": {
                "title": "Memory Usage (Last Hour)",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Usage (%)"},
            },
        }

        return {
            "cpu_chart": cpu_chart,
            "memory_chart": memory_chart,
            "current_stats": self.system_monitor.get_current_stats(),
        }

    def generate_application_dashboard(self) -> dict[str, Any]:
        """Generate application monitoring dashboard data."""
        now = time.time()
        last_hour = now - 3600

        # Request rate chart
        request_points = self.app_monitor.request_buffer.get_points(last_hour, now)

        # Group requests by 5-minute intervals
        interval_requests = defaultdict(int)
        for point in request_points:
            interval = int(point.timestamp // 300) * 300
            interval_requests[interval] += 1

        request_times = [datetime.fromtimestamp(t) for t in sorted(interval_requests.keys())]
        request_rates = [interval_requests[t] for t in sorted(interval_requests.keys())]

        request_chart = {
            "data": [
                {
                    "x": request_times,
                    "y": request_rates,
                    "type": "bar",
                    "name": "Requests per 5min",
                    "marker": {"color": "#2ca02c"},
                }
            ],
            "layout": {
                "title": "Request Rate (Last Hour)",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Requests per 5min"},
            },
        }

        # Response time chart
        response_points = self.app_monitor.response_time_buffer.get_points(last_hour, now)
        response_times = [datetime.fromtimestamp(p.timestamp) for p in response_points]
        response_values = [p.value * 1000 for p in response_points]  # Convert to ms

        response_chart = {
            "data": [
                {
                    "x": response_times,
                    "y": response_values,
                    "type": "scatter",
                    "mode": "markers",
                    "name": "Response Time (ms)",
                    "marker": {"color": "#d62728", "size": 4},
                }
            ],
            "layout": {
                "title": "Response Times (Last Hour)",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Response Time (ms)"},
            },
        }

        return {
            "request_chart": request_chart,
            "response_chart": response_chart,
            "summary_stats": self.app_monitor.get_summary_stats(60),
        }


class MonitoringSystem:
    """Main monitoring system coordinator."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

        self.system_monitor = SystemMonitor()
        self.app_monitor = ApplicationMonitor()
        self.alert_manager = AlertManager()
        self.dashboard = DashboardGenerator(self.system_monitor, self.app_monitor)

        # Redis for persistence (optional)
        self.redis_client = None

        # Setup default alert rules
        self._setup_default_alerts()

    async def start(self):
        """Start monitoring system."""
        # Connect to Redis if configured
        redis_url = self.config.get("redis_url")
        if redis_url and REDIS_AVAILABLE:
            self.redis_client = redis.from_url(redis_url)
            logger.info("Connected to Redis for monitoring data persistence")

        # Start components
        await self.system_monitor.start_monitoring(
            interval=self.config.get("system_monitor_interval", 5.0)
        )

        await self.alert_manager.start_checking(
            interval=self.config.get("alert_check_interval", 30.0)
        )

        logger.info("Monitoring system started")

    async def stop(self):
        """Stop monitoring system."""
        await self.system_monitor.stop_monitoring()
        await self.alert_manager.stop_checking()

        if self.redis_client:
            await self.redis_client.close()

        logger.info("Monitoring system stopped")

    def _setup_default_alerts(self):
        """Setup default alert rules."""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                metric="cpu_percent",
                condition="gt",
                threshold=80.0,
                duration=300,
                severity="warning",
            ),
            AlertRule(
                name="high_memory_usage",
                metric="memory_percent",
                condition="gt",
                threshold=85.0,
                duration=300,
                severity="warning",
            ),
            AlertRule(
                name="high_error_rate",
                metric="error_rate",
                condition="gt",
                threshold=5.0,
                duration=180,
                severity="error",
            ),
            AlertRule(
                name="slow_response_time",
                metric="response_time_p95",
                condition="gt",
                threshold=2.0,
                duration=300,
                severity="warning",
            ),
        ]

        for rule in default_rules:
            self.alert_manager.add_rule(rule)

    def get_health_status(self) -> dict[str, Any]:
        """Get overall system health status."""
        current_stats = self.system_monitor.get_current_stats()
        app_stats = self.app_monitor.get_summary_stats(10)  # Last 10 minutes

        # Determine health status
        health = "healthy"
        issues = []

        if PSUTIL_AVAILABLE and current_stats.get("cpu", {}).get("percent", 0) > 90:
            health = "warning"
            issues.append("High CPU usage")

        if PSUTIL_AVAILABLE and current_stats.get("memory", {}).get("percent", 0) > 90:
            health = "critical"
            issues.append("High memory usage")

        if app_stats["errors"]["rate"] > 10:
            health = "warning"
            issues.append("High error rate")

        return {
            "status": health,
            "issues": issues,
            "system": current_stats,
            "application": app_stats,
            "active_alerts": len(self.alert_manager.active_alerts),
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Convenience methods for external use
    def record_request(self, *args, **kwargs):
        """Record request metrics."""
        return self.app_monitor.record_request(*args, **kwargs)

    def record_user_activity(self, *args, **kwargs):
        """Record user activity."""
        return self.app_monitor.record_user_activity(*args, **kwargs)

    def record_file_processing(self, *args, **kwargs):
        """Record file processing metrics."""
        return self.app_monitor.record_file_processing(*args, **kwargs)

    def increment_counter(self, *args, **kwargs):
        """Increment counter metric."""
        return self.app_monitor.increment_counter(*args, **kwargs)

    def set_gauge(self, *args, **kwargs):
        """Set gauge metric."""
        return self.app_monitor.set_gauge(*args, **kwargs)


# Global monitoring instance
_monitoring_system = None


def get_monitoring_system(config: dict[str, Any] = None) -> MonitoringSystem:
    """Get or create the global monitoring system instance."""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem(config)
    return _monitoring_system


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create monitoring system
        config = {
            "redis_url": "redis://localhost:6379/2",
            "system_monitor_interval": 2.0,
            "alert_check_interval": 15.0,
        }

        monitoring = get_monitoring_system(config)
        await monitoring.start()

        # Simulate some activity
        for _i in range(10):
            monitoring.record_request(
                path="/api/chat",
                method="POST",
                status_code=200,
                response_time=0.5,
                provider="openai",
            )

            monitoring.record_user_activity("user123", "chat_message")

            await asyncio.sleep(1)

        # Get dashboard data
        monitoring.dashboard.generate_system_dashboard()
        monitoring.dashboard.generate_application_dashboard()
        monitoring.get_health_status()

        await monitoring.stop()

    asyncio.run(main())
