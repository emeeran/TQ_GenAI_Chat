"""
Monitoring and Metrics Module for TQ GenAI Chat
Implements comprehensive monitoring, logging, and metrics collection
"""

import logging
import time
import psutil
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from flask import Flask, request, g
import redis


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str] = None


class MetricsCollector:
    """Collect and store application metrics"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.hincrby("metrics:counters", key, value)
                except Exception as e:
                    logging.error(f"Error storing counter metric: {e}")
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.hset("metrics:gauges", key, value)
                except Exception as e:
                    logging.error(f"Error storing gauge metric: {e}")
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            
            # Keep only last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.lpush(f"metrics:histogram:{key}", value)
                    self.redis_client.ltrim(f"metrics:histogram:{key}", 0, 999)
                except Exception as e:
                    logging.error(f"Error storing histogram metric: {e}")
    
    def add_metric_point(self, name: str, value: float, labels: Dict[str, str] = None):
        """Add a time-series metric point"""
        with self._lock:
            key = self._make_key(name, labels)
            point = MetricPoint(timestamp=time.time(), value=value, labels=labels)
            self.metrics[key].append(point)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self._lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {k: list(v) for k, v in self.histograms.items()},
                'timeseries': {k: [(p.timestamp, p.value) for p in v] for k, v in self.metrics.items()}
            }
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key with labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class PerformanceMonitor:
    """Monitor application performance"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.request_times = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.active_requests = 0
        self._lock = threading.Lock()
    
    def start_request(self):
        """Mark start of request processing"""
        with self._lock:
            self.active_requests += 1
            self.metrics.set_gauge("active_requests", self.active_requests)
        
        g.request_start_time = time.time()
    
    def end_request(self, status_code: int):
        """Mark end of request processing"""
        if not hasattr(g, 'request_start_time'):
            return
        
        duration = time.time() - g.request_start_time
        
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
            self.request_times.append(duration)
            
            if status_code >= 400:
                self.error_counts[status_code] += 1
        
        # Update metrics
        self.metrics.set_gauge("active_requests", self.active_requests)
        self.metrics.record_histogram("request_duration", duration, {"status": str(status_code)})
        self.metrics.increment_counter("requests_total", labels={"status": str(status_code)})
        
        if status_code >= 400:
            self.metrics.increment_counter("errors_total", labels={"status": str(status_code)})
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            if not self.request_times:
                return {
                    'avg_response_time': 0,
                    'p95_response_time': 0,
                    'p99_response_time': 0,
                    'active_requests': self.active_requests,
                    'error_counts': dict(self.error_counts)
                }
            
            sorted_times = sorted(self.request_times)
            count = len(sorted_times)
            
            return {
                'avg_response_time': sum(sorted_times) / count,
                'p95_response_time': sorted_times[int(count * 0.95)] if count > 0 else 0,
                'p99_response_time': sorted_times[int(count * 0.99)] if count > 0 else 0,
                'active_requests': self.active_requests,
                'error_counts': dict(self.error_counts)
            }


class SystemMonitor:
    """Monitor system resources"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: int = 30):
        """Start system monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics.set_gauge("system_cpu_percent", cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.metrics.set_gauge("system_memory_percent", memory.percent)
                self.metrics.set_gauge("system_memory_used_bytes", memory.used)
                self.metrics.set_gauge("system_memory_available_bytes", memory.available)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.metrics.set_gauge("system_disk_percent", disk.percent)
                self.metrics.set_gauge("system_disk_used_bytes", disk.used)
                self.metrics.set_gauge("system_disk_free_bytes", disk.free)
                
                # Network I/O
                network = psutil.net_io_counters()
                self.metrics.set_gauge("system_network_bytes_sent", network.bytes_sent)
                self.metrics.set_gauge("system_network_bytes_recv", network.bytes_recv)
                
                # Process info
                process = psutil.Process()
                self.metrics.set_gauge("process_memory_rss", process.memory_info().rss)
                self.metrics.set_gauge("process_memory_vms", process.memory_info().vms)
                self.metrics.set_gauge("process_cpu_percent", process.cpu_percent())
                self.metrics.set_gauge("process_num_threads", process.num_threads())
                
                time.sleep(interval)
                
            except Exception as e:
                logging.error(f"Error in system monitoring: {e}")
                time.sleep(interval)


class ApplicationLogger:
    """Enhanced application logging"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.request_logs = deque(maxlen=1000)
        self.error_logs = deque(maxlen=1000)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize logging for Flask app"""
        self.app = app
        
        # Configure structured logging
        @app.before_request
        def log_request_start():
            self._log_request_start()
        
        @app.after_request
        def log_request_end(response):
            self._log_request_end(response)
            return response
        
        @app.errorhandler(Exception)
        def log_exception(error):
            self._log_exception(error)
            return {"error": "Internal server error"}, 500
    
    def _log_request_start(self):
        """Log request start"""
        request_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_length': request.content_length
        }
        
        self.request_logs.append(request_data)
        g.request_log_data = request_data
    
    def _log_request_end(self, response):
        """Log request end"""
        if hasattr(g, 'request_log_data'):
            g.request_log_data['response_status'] = response.status_code
            g.request_log_data['response_size'] = len(response.get_data())
            
            if hasattr(g, 'request_start_time'):
                g.request_log_data['duration'] = time.time() - g.request_start_time
            
            # Log to file/external system
            logging.info(f"Request completed: {json.dumps(g.request_log_data)}")
    
    def _log_exception(self, error):
        """Log exceptions"""
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'path': request.path if request else 'unknown',
            'method': request.method if request else 'unknown',
            'remote_addr': request.remote_addr if request else 'unknown'
        }
        
        self.error_logs.append(error_data)
        logging.error(f"Application error: {json.dumps(error_data)}")
    
    def get_recent_logs(self, log_type: str = 'request', limit: int = 100) -> List[Dict]:
        """Get recent logs"""
        if log_type == 'request':
            return list(self.request_logs)[-limit:]
        elif log_type == 'error':
            return list(self.error_logs)[-limit:]
        else:
            return []


class HealthChecker:
    """Application health checking"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.checks = {}
        self.last_check_time = None
        self.last_check_results = {}
    
    def add_check(self, name: str, check_func, critical: bool = True):
        """Add a health check"""
        self.checks[name] = {
            'func': check_func,
            'critical': critical
        }
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        overall_healthy = True
        
        for name, check_config in self.checks.items():
            try:
                start_time = time.time()
                check_result = check_config['func']()
                duration = time.time() - start_time
                
                if isinstance(check_result, bool):
                    check_healthy = check_result
                    check_message = "OK" if check_result else "Failed"
                elif isinstance(check_result, dict):
                    check_healthy = check_result.get('healthy', False)
                    check_message = check_result.get('message', 'Unknown')
                else:
                    check_healthy = bool(check_result)
                    check_message = str(check_result)
                
                results['checks'][name] = {
                    'healthy': check_healthy,
                    'message': check_message,
                    'duration': duration,
                    'critical': check_config['critical']
                }
                
                if not check_healthy and check_config['critical']:
                    overall_healthy = False
                    
            except Exception as e:
                results['checks'][name] = {
                    'healthy': False,
                    'message': f"Check failed: {str(e)}",
                    'duration': 0,
                    'critical': check_config['critical']
                }
                
                if check_config['critical']:
                    overall_healthy = False
        
        results['status'] = 'healthy' if overall_healthy else 'unhealthy'
        
        self.last_check_time = time.time()
        self.last_check_results = results
        
        return results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        if not self.last_check_results or (time.time() - self.last_check_time) > 60:
            return self.run_checks()
        
        return self.last_check_results


# Default health checks
def check_redis_connection():
    """Check Redis connection"""
    try:
        import redis
        r = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        r.ping()
        return True
    except:
        return False


def check_disk_space():
    """Check available disk space"""
    try:
        disk_usage = psutil.disk_usage('/')
        free_percent = (disk_usage.free / disk_usage.total) * 100
        
        if free_percent < 10:
            return {'healthy': False, 'message': f'Low disk space: {free_percent:.1f}% free'}
        elif free_percent < 20:
            return {'healthy': True, 'message': f'Disk space warning: {free_percent:.1f}% free'}
        else:
            return {'healthy': True, 'message': f'Disk space OK: {free_percent:.1f}% free'}
    except:
        return False


def check_memory_usage():
    """Check memory usage"""
    try:
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            return {'healthy': False, 'message': f'High memory usage: {memory.percent:.1f}%'}
        elif memory.percent > 80:
            return {'healthy': True, 'message': f'Memory usage warning: {memory.percent:.1f}%'}
        else:
            return {'healthy': True, 'message': f'Memory usage OK: {memory.percent:.1f}%'}
    except:
        return False


# Global monitoring instances
metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor(metrics_collector)
system_monitor = SystemMonitor(metrics_collector)
application_logger = ApplicationLogger()
health_checker = HealthChecker()

# Add default health checks
health_checker.add_check('redis', check_redis_connection, critical=False)
health_checker.add_check('disk_space', check_disk_space, critical=True)
health_checker.add_check('memory_usage', check_memory_usage, critical=True)