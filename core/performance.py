"""Performance monitoring and metrics collection"""
import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import psutil


@dataclass
class PerformanceMetric:
    name: str
    value: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Comprehensive performance monitoring system"""

    def __init__(self, retention_hours: int = 24):
        import logging

        self.logger = logging.getLogger(__name__)
        self.retention_hours = retention_hours
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timers: dict[str, float] = {}
        self.counters: dict[str, int] = defaultdict(int)
        self.system_stats_task: asyncio.Task | None = None
        self._monitoring = False

    def start_monitoring(self):
        """Start performance monitoring (non-async entry point)"""
        if self._monitoring:
            return

        self._monitoring = True

        # Start system stats collection in background thread
        def _start_background_monitoring():
            """Start monitoring in a background thread with its own event loop"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._start_async_monitoring())
            except Exception as e:
                self.logger.error(f"Error starting background monitoring: {e}")
            finally:
                loop.close()

        import threading

        self.monitor_thread = threading.Thread(target=_start_background_monitoring, daemon=True)
        self.monitor_thread.start()

        self.logger.info("Performance monitoring started in background thread")

    async def _start_async_monitoring(self):
        """Start async monitoring tasks"""
        self.system_stats_task = asyncio.create_task(self._collect_system_stats())

    def stop_monitoring(self):
        """Stop system monitoring"""
        self._monitoring = False
        if self.system_stats_task and not self.system_stats_task.done():
            self.system_stats_task.cancel()

    def start_timer(self, name: str) -> str:
        """Start a performance timer"""
        timer_key = f"{name}_{time.time()}"
        self.timers[timer_key] = time.time()
        return timer_key

    def end_timer(self, timer_key: str) -> float:
        """End a performance timer and record the metric"""
        if timer_key in self.timers:
            duration = time.time() - self.timers[timer_key]
            del self.timers[timer_key]

            # Extract metric name from timer key
            metric_name = timer_key.rsplit("_", 1)[0]
            self.record_metric(f"{metric_name}_duration", duration)
            return duration
        return 0.0

    def record_metric(self, name: str, value: float, metadata: dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name, value=value, timestamp=datetime.now(), metadata=metadata or {}
        )

        self.metrics[name].append(metric)
        self._cleanup_old_metrics()

    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter metric"""
        self.counters[name] += value
        self.record_metric(f"{name}_count", self.counters[name])

    def get_metric_stats(self, name: str) -> dict[str, float]:
        """Get statistics for a metric"""
        if name not in self.metrics:
            return {}

        values = [m.value for m in self.metrics[name]]
        if not values:
            return {}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "latest": values[-1],
        }

    def get_all_metrics(self) -> dict[str, dict[str, float]]:
        """Get all metric statistics"""
        return {name: self.get_metric_stats(name) for name in self.metrics.keys()}

    def get_system_health(self) -> dict[str, Any]:
        """Get current system health metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "active_connections": len(psutil.net_connections()),
            "process_count": len(psutil.pids()),
            "timestamp": datetime.now().isoformat(),
        }

    async def _collect_system_stats(self):
        """Collect system statistics periodically"""
        while self._monitoring:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric("system_cpu_percent", cpu_percent)

                # Memory metrics
                memory = psutil.virtual_memory()
                self.record_metric("system_memory_percent", memory.percent)
                self.record_metric("system_memory_used_gb", memory.used / (1024**3))

                # Disk metrics
                disk = psutil.disk_usage("/")
                self.record_metric("system_disk_percent", disk.percent)

                # Network metrics
                net_io = psutil.net_io_counters()
                self.record_metric("system_bytes_sent", net_io.bytes_sent)
                self.record_metric("system_bytes_received", net_io.bytes_recv)

                await asyncio.sleep(30)  # Collect every 30 seconds

            except Exception:
                await asyncio.sleep(60)  # Wait longer on error

    def _cleanup_old_metrics(self):
        """Clean up metrics older than retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)

        for _name, metric_queue in self.metrics.items():
            # Remove old metrics (deque handles max size automatically)
            while metric_queue and metric_queue[0].timestamp < cutoff_time:
                metric_queue.popleft()

    def export_metrics(self) -> dict[str, Any]:
        """Export all metrics for external monitoring systems"""
        return {
            "metrics": self.get_all_metrics(),
            "counters": dict(self.counters),
            "system_health": self.get_system_health(),
            "export_timestamp": datetime.now().isoformat(),
        }


# Global performance monitor instance
perf_monitor = PerformanceMonitor()


def monitor_performance(func_name: str = None):
    """Decorator for monitoring function performance"""

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            timer_key = perf_monitor.start_timer(name)

            try:
                result = await func(*args, **kwargs)
                perf_monitor.increment_counter(f"{name}_success")
                return result
            except Exception:
                perf_monitor.increment_counter(f"{name}_error")
                raise
            finally:
                perf_monitor.end_timer(timer_key)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = func_name or f"{func.__module__}.{func.__name__}"
            timer_key = perf_monitor.start_timer(name)

            try:
                result = func(*args, **kwargs)
                perf_monitor.increment_counter(f"{name}_success")
                return result
            except Exception:
                perf_monitor.increment_counter(f"{name}_error")
                raise
            finally:
                perf_monitor.end_timer(timer_key)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
