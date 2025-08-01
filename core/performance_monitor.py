"""
Comprehensive performance monitoring system for TQ GenAI Chat application.
Tracks metrics, provides real-time monitoring, and generates performance reports.
"""

import json
import logging
import psutil
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Data structure for storing metric information."""
    name: str
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    response_times: dict[str, float] = field(default_factory=dict)
    error_rates: dict[str, float] = field(default_factory=dict)
    custom_metrics: dict[str, float] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and stores various performance metrics.
    """

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: dict[str, float] = defaultdict(float)
        self.histograms: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()

    def record_metric(self, name: str, value: float, labels: dict[str, str] = None, unit: str = ""):
        """Record a metric value."""
        with self.lock:
            metric = MetricData(
                name=name,
                value=value,
                timestamp=time.time(),
                labels=labels or {},
                unit=unit
            )
            self.metrics[name].append(metric)

    def increment_counter(self, name: str, value: float = 1.0):
        """Increment a counter metric."""
        with self.lock:
            self.counters[name] += value
            self.record_metric(f"{name}_total", self.counters[name], unit="count")

    def record_histogram(self, name: str, value: float):
        """Record a value in a histogram."""
        with self.lock:
            self.histograms[name].append(value)
            # Calculate percentiles
            sorted_values = sorted(self.histograms[name])
            count = len(sorted_values)
            if count > 0:
                p50 = sorted_values[int(count * 0.5)]
                p95 = sorted_values[int(count * 0.95)]
                p99 = sorted_values[int(count * 0.99)]
                
                self.record_metric(f"{name}_p50", p50, unit="seconds")
                self.record_metric(f"{name}_p95", p95, unit="seconds")
                self.record_metric(f"{name}_p99", p99, unit="seconds")

    def get_metric_history(self, name: str, limit: int = 100) -> list[MetricData]:
        """Get history of a metric."""
        with self.lock:
            if name in self.metrics:
                return list(self.metrics[name])[-limit:]
            return []

    def get_latest_metrics(self) -> dict[str, MetricData]:
        """Get latest value for all metrics."""
        with self.lock:
            latest = {}
            for name, history in self.metrics.items():
                if history:
                    latest[name] = history[-1]
            return latest

    def get_counter_value(self, name: str) -> float:
        """Get current counter value."""
        with self.lock:
            return self.counters.get(name, 0.0)


class SystemMonitor:
    """
    Monitors system-level performance metrics.
    """

    def __init__(self, metrics_collector: MetricsCollector, interval: float = 1.0):
        self.metrics_collector = metrics_collector
        self.interval = interval
        self.running = False
        self.thread = None
        self._last_disk_io = None
        self._last_network_io = None

    def start(self):
        """Start monitoring system metrics."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("System monitoring started")

    def stop(self):
        """Stop monitoring system metrics."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("System monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(self.interval)

    def _collect_system_metrics(self):
        """Collect system performance metrics."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)
        self.metrics_collector.record_metric("system_cpu_percent", cpu_percent, unit="percent")

        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics_collector.record_metric("system_memory_percent", memory.percent, unit="percent")
        self.metrics_collector.record_metric("system_memory_used_mb", memory.used / 1024 / 1024, unit="MB")
        self.metrics_collector.record_metric("system_memory_available_mb", memory.available / 1024 / 1024, unit="MB")

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io and self._last_disk_io:
            read_mb_delta = (disk_io.read_bytes - self._last_disk_io.read_bytes) / 1024 / 1024
            write_mb_delta = (disk_io.write_bytes - self._last_disk_io.write_bytes) / 1024 / 1024
            
            self.metrics_collector.record_metric("system_disk_read_mb_per_sec", read_mb_delta / self.interval, unit="MB/s")
            self.metrics_collector.record_metric("system_disk_write_mb_per_sec", write_mb_delta / self.interval, unit="MB/s")
        
        self._last_disk_io = disk_io

        # Network I/O
        network_io = psutil.net_io_counters()
        if network_io and self._last_network_io:
            sent_mb_delta = (network_io.bytes_sent - self._last_network_io.bytes_sent) / 1024 / 1024
            recv_mb_delta = (network_io.bytes_recv - self._last_network_io.bytes_recv) / 1024 / 1024
            
            self.metrics_collector.record_metric("system_network_sent_mb_per_sec", sent_mb_delta / self.interval, unit="MB/s")
            self.metrics_collector.record_metric("system_network_recv_mb_per_sec", recv_mb_delta / self.interval, unit="MB/s")
        
        self._last_network_io = network_io

        # Process-specific metrics
        process = psutil.Process()
        self.metrics_collector.record_metric("process_cpu_percent", process.cpu_percent(), unit="percent")
        
        memory_info = process.memory_info()
        self.metrics_collector.record_metric("process_memory_mb", memory_info.rss / 1024 / 1024, unit="MB")
        
        # File descriptors (Unix-like systems)
        try:
            num_fds = process.num_fds()
            self.metrics_collector.record_metric("process_file_descriptors", num_fds, unit="count")
        except (AttributeError, OSError):
            pass  # Not available on all platforms

        # Thread count
        self.metrics_collector.record_metric("process_threads", process.num_threads(), unit="count")


class RequestTracker:
    """
    Tracks HTTP request performance and patterns.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.active_requests: dict[str, float] = {}
        self.lock = threading.Lock()

    def start_request(self, request_id: str, endpoint: str, method: str = "GET"):
        """Start tracking a request."""
        with self.lock:
            self.active_requests[request_id] = {
                'start_time': time.time(),
                'endpoint': endpoint,
                'method': method
            }
        
        self.metrics_collector.increment_counter(f"http_requests_{method.lower()}")
        self.metrics_collector.increment_counter("http_requests_total")

    def end_request(self, request_id: str, status_code: int = 200, error: str = None):
        """End tracking a request."""
        with self.lock:
            if request_id not in self.active_requests:
                return

            request_info = self.active_requests.pop(request_id)
            duration = time.time() - request_info['start_time']

            # Record response time
            endpoint = request_info['endpoint']
            self.metrics_collector.record_histogram(f"http_request_duration_{endpoint}", duration)
            self.metrics_collector.record_histogram("http_request_duration_all", duration)

            # Record status codes
            self.metrics_collector.increment_counter(f"http_status_{status_code}")
            
            if status_code >= 400:
                self.metrics_collector.increment_counter("http_errors_total")
                self.metrics_collector.increment_counter(f"http_errors_{endpoint}")

            # Record errors
            if error:
                self.metrics_collector.increment_counter("http_errors_with_exception")
                logger.warning(f"Request {request_id} failed with error: {error}")

    def get_active_request_count(self) -> int:
        """Get number of currently active requests."""
        with self.lock:
            return len(self.active_requests)


class AIProviderMonitor:
    """
    Monitors AI provider performance and usage.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector

    def record_ai_request(
        self,
        provider: str,
        model: str,
        response_time: float,
        token_count: int = None,
        error: str = None,
        cost: float = None
    ):
        """Record an AI provider request."""
        labels = {"provider": provider, "model": model}
        
        # Response time
        self.metrics_collector.record_histogram("ai_request_duration", response_time)
        self.metrics_collector.record_metric(
            "ai_request_duration",
            response_time,
            labels=labels,
            unit="seconds"
        )
        
        # Request count
        self.metrics_collector.increment_counter(f"ai_requests_{provider}")
        self.metrics_collector.increment_counter("ai_requests_total")
        
        # Token usage
        if token_count:
            self.metrics_collector.record_metric(
                "ai_tokens_used", 
                token_count, 
                labels=labels, 
                unit="tokens"
            )
            self.metrics_collector.increment_counter("ai_tokens_total", token_count)
        
        # Cost tracking
        if cost:
            self.metrics_collector.record_metric(
                "ai_request_cost", 
                cost, 
                labels=labels, 
                unit="USD"
            )
            self.metrics_collector.increment_counter("ai_cost_total", cost)
        
        # Error tracking
        if error:
            self.metrics_collector.increment_counter(f"ai_errors_{provider}")
            self.metrics_collector.increment_counter("ai_errors_total")
            self.metrics_collector.record_metric(
                "ai_error_rate", 
                1.0, 
                labels=labels, 
                unit="rate"
            )


class PerformanceMonitor:
    """
    Main performance monitoring system that coordinates all monitoring components.
    """

    def __init__(self, redis_url: str = None):
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.request_tracker = RequestTracker(self.metrics_collector)
        self.ai_monitor = AIProviderMonitor(self.metrics_collector)
        
        # Redis for distributed metrics (optional)
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis connected for performance metrics")
            except Exception as e:
                logger.warning(f"Redis connection failed for metrics: {e}")

        # Performance alerts
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'response_time_p95': 5.0,  # 5 seconds
            'error_rate': 0.1  # 10%
        }
        
        self.alert_callbacks: list[Callable] = []

    def start(self):
        """Start all monitoring components."""
        self.system_monitor.start()
        logger.info("Performance monitoring started")

    def stop(self):
        """Stop all monitoring components."""
        self.system_monitor.stop()
        logger.info("Performance monitoring stopped")

    def add_alert_callback(self, callback: Callable[[str, float, float], None]):
        """Add a callback for performance alerts."""
        self.alert_callbacks.append(callback)

    def check_alerts(self):
        """Check for performance alert conditions."""
        latest_metrics = self.metrics_collector.get_latest_metrics()
        
        for metric_name, threshold in self.alert_thresholds.items():
            if metric_name in latest_metrics:
                value = latest_metrics[metric_name].value
                if value > threshold:
                    self._trigger_alert(metric_name, value, threshold)

    def _trigger_alert(self, metric_name: str, value: float, threshold: float):
        """Trigger performance alert."""
        message = f"Performance alert: {metric_name} = {value:.2f} exceeds threshold {threshold:.2f}"
        logger.warning(message)
        
        for callback in self.alert_callbacks:
            try:
                callback(metric_name, value, threshold)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def get_performance_snapshot(self) -> PerformanceSnapshot:
        """Get current performance snapshot."""
        latest_metrics = self.metrics_collector.get_latest_metrics()
        
        def get_metric_value(name: str, default: float = 0.0) -> float:
            return latest_metrics.get(name, MetricData(name, default, time.time())).value

        return PerformanceSnapshot(
            timestamp=time.time(),
            cpu_percent=get_metric_value("system_cpu_percent"),
            memory_percent=get_metric_value("system_memory_percent"),
            memory_mb=get_metric_value("system_memory_used_mb"),
            disk_io_read_mb=get_metric_value("system_disk_read_mb_per_sec"),
            disk_io_write_mb=get_metric_value("system_disk_write_mb_per_sec"),
            network_sent_mb=get_metric_value("system_network_sent_mb_per_sec"),
            network_recv_mb=get_metric_value("system_network_recv_mb_per_sec"),
            active_connections=self.request_tracker.get_active_request_count(),
            response_times={
                'p50': get_metric_value("http_request_duration_all_p50"),
                'p95': get_metric_value("http_request_duration_all_p95"),
                'p99': get_metric_value("http_request_duration_all_p99"),
            },
            error_rates={
                'http_total': self._calculate_error_rate('http'),
                'ai_total': self._calculate_error_rate('ai'),
            },
            custom_metrics={
                'ai_requests_total': self.metrics_collector.get_counter_value('ai_requests_total'),
                'ai_tokens_total': self.metrics_collector.get_counter_value('ai_tokens_total'),
                'ai_cost_total': self.metrics_collector.get_counter_value('ai_cost_total'),
            }
        )

    def _calculate_error_rate(self, prefix: str) -> float:
        """Calculate error rate for a metric prefix."""
        total_requests = self.metrics_collector.get_counter_value(f'{prefix}_requests_total')
        total_errors = self.metrics_collector.get_counter_value(f'{prefix}_errors_total')
        
        if total_requests > 0:
            return total_errors / total_requests
        return 0.0

    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        latest_metrics = self.metrics_collector.get_latest_metrics()
        
        for name, metric in latest_metrics.items():
            # Convert to Prometheus format
            prometheus_name = name.replace('-', '_').replace('.', '_')
            
            if metric.labels:
                labels_str = ','.join([f'{k}="{v}"' for k, v in metric.labels.items()])
                line = f'{prometheus_name}{{{labels_str}}} {metric.value} {int(metric.timestamp * 1000)}'
            else:
                line = f'{prometheus_name} {metric.value} {int(metric.timestamp * 1000)}'
            
            lines.append(line)
        
        return '\n'.join(lines)

    def generate_performance_report(self, hours: int = 24) -> dict[str, Any]:
        """Generate comprehensive performance report."""
        current_time = time.time()
        start_time = current_time - (hours * 3600)
        
        # Get recent metrics
        all_metrics = {}
        for name in self.metrics_collector.metrics.keys():
            history = self.metrics_collector.get_metric_history(name)
            recent_metrics = [m for m in history if m.timestamp >= start_time]
            if recent_metrics:
                all_metrics[name] = recent_metrics

        # Calculate statistics
        report = {
            'report_period_hours': hours,
            'generated_at': current_time,
            'summary': {},
            'system_performance': {},
            'ai_usage': {},
            'errors_and_alerts': {},
            'recommendations': []
        }

        # System performance summary
        if 'system_cpu_percent' in all_metrics:
            cpu_values = [m.value for m in all_metrics['system_cpu_percent']]
            report['system_performance']['cpu'] = {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            }

        if 'system_memory_percent' in all_metrics:
            memory_values = [m.value for m in all_metrics['system_memory_percent']]
            report['system_performance']['memory'] = {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            }

        # AI usage summary
        ai_requests = self.metrics_collector.get_counter_value('ai_requests_total')
        ai_cost = self.metrics_collector.get_counter_value('ai_cost_total')
        
        report['ai_usage'] = {
            'total_requests': ai_requests,
            'total_cost_usd': ai_cost,
            'requests_per_hour': ai_requests / hours if hours > 0 else 0,
            'cost_per_request': ai_cost / ai_requests if ai_requests > 0 else 0
        }

        # Error analysis
        http_errors = self.metrics_collector.get_counter_value('http_errors_total')
        ai_errors = self.metrics_collector.get_counter_value('ai_errors_total')
        
        report['errors_and_alerts'] = {
            'http_errors': http_errors,
            'ai_errors': ai_errors,
            'total_errors': http_errors + ai_errors
        }

        # Performance recommendations
        snapshot = self.get_performance_snapshot()
        if snapshot.cpu_percent > 70:
            report['recommendations'].append("High CPU usage detected. Consider scaling or optimizing CPU-intensive operations.")
        
        if snapshot.memory_percent > 80:
            report['recommendations'].append("High memory usage detected. Consider optimizing memory usage or adding more RAM.")
        
        if snapshot.response_times.get('p95', 0) > 3.0:
            report['recommendations'].append("Slow response times detected. Consider optimizing database queries or API calls.")

        return report

    def save_report(self, report: dict[str, Any], filename: str = None):
        """Save performance report to file."""
        if not filename:
            timestamp = int(time.time())
            filename = f"performance_report_{timestamp}.json"
        
        report_path = Path("reports") / filename
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Performance report saved to {report_path}")
        return str(report_path)


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor(redis_url: str = None) -> PerformanceMonitor:
    """Get or create the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(redis_url)
    return _performance_monitor


# Context managers for easy request tracking
class request_timer:
    """Context manager for timing requests."""
    
    def __init__(self, endpoint: str, method: str = "GET", monitor: PerformanceMonitor = None):
        self.endpoint = endpoint
        self.method = method
        self.monitor = monitor or get_performance_monitor()
        self.request_id = f"{endpoint}_{time.time()}_{threading.get_ident()}"
        
    def __enter__(self):
        self.monitor.request_tracker.start_request(self.request_id, self.endpoint, self.method)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        status_code = 500 if exc_type else 200
        error = str(exc_val) if exc_val else None
        self.monitor.request_tracker.end_request(self.request_id, status_code, error)


class ai_request_timer:
    """Context manager for timing AI requests."""
    
    def __init__(self, provider: str, model: str, monitor: PerformanceMonitor = None):
        self.provider = provider
        self.model = model
        self.monitor = monitor or get_performance_monitor()
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            error = str(exc_val) if exc_val else None
            self.monitor.ai_monitor.record_ai_request(
                self.provider, 
                self.model, 
                duration, 
                error=error
            )
