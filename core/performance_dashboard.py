"""
Performance Metrics Dashboard - Real-time monitoring and analytics
Implements Task 4.1.1: Performance Metrics Dashboard
"""

import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psutil


@dataclass
class MetricData:
    """Represents a single metric data point"""

    timestamp: float
    value: float
    metadata: dict[str, Any] = None


class PerformanceDashboard:
    """Comprehensive performance monitoring and dashboard system"""

    def __init__(self, retention_hours: int = 24, db_path: str = "performance_metrics.db"):
        self.retention_hours = retention_hours
        self.db_path = db_path

        # In-memory metrics storage for real-time data
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.alerts = []
        self.thresholds = {}

        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()

        # Provider tracking
        self.provider_stats = defaultdict(
            lambda: {
                "requests": 0,
                "failures": 0,
                "avg_response_time": 0,
                "last_error": None,
                "sla_breaches": 0,
            }
        )

        # User experience metrics
        self.user_metrics = defaultdict(
            lambda: {"sessions": 0, "avg_session_duration": 0, "bounce_rate": 0, "error_rate": 0}
        )

        self._init_database()
        self._set_default_thresholds()

    def _init_database(self):
        """Initialize SQLite database for persistent metrics storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    value REAL NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    threshold_value REAL NOT NULL,
                    actual_value REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_sla (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    date DATE NOT NULL,
                    uptime_percentage REAL NOT NULL,
                    avg_response_time REAL NOT NULL,
                    total_requests INTEGER NOT NULL,
                    failed_requests INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp ON metrics(metric_name, timestamp)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_provider_sla_date ON provider_sla(provider, date)"
            )

    def _set_default_thresholds(self):
        """Set default alert thresholds"""
        self.thresholds = {
            "response_time": {"warning": 2.0, "critical": 5.0},
            "memory_usage": {"warning": 80.0, "critical": 95.0},
            "cpu_usage": {"warning": 80.0, "critical": 95.0},
            "error_rate": {"warning": 1.0, "critical": 5.0},
            "cache_hit_rate": {"warning": 70.0, "critical": 50.0},
            "disk_usage": {"warning": 85.0, "critical": 95.0},
            "active_connections": {"warning": 100, "critical": 200},
        }

    def start_monitoring(self):
        """Start background performance monitoring"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop background performance monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.is_monitoring:
            try:
                self._collect_system_metrics()
                self._check_alerts()
                self._cleanup_old_data()
                time.sleep(10)  # Collect metrics every 10 seconds
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error

    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        timestamp = time.time()

        # System metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Record metrics
        self.record_metric("cpu_usage", cpu_percent, timestamp)
        self.record_metric("memory_usage", memory.percent, timestamp)
        self.record_metric("disk_usage", disk.percent, timestamp)
        self.record_metric("memory_available_mb", memory.available / 1024 / 1024, timestamp)

        # Network metrics if available
        try:
            network = psutil.net_io_counters()
            self.record_metric("network_bytes_sent", network.bytes_sent, timestamp)
            self.record_metric("network_bytes_recv", network.bytes_recv, timestamp)
        except Exception as e:
            logging.warning(f"Network metrics unavailable: {e}")

    def record_metric(
        self,
        metric_name: str,
        value: float,
        timestamp: float | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Record a metric value"""
        if timestamp is None:
            timestamp = time.time()

        metric_data = MetricData(timestamp, value, metadata)

        with self.lock:
            self.metrics[metric_name].append(metric_data)

        # Persist to database (async to avoid blocking)
        threading.Thread(
            target=self._persist_metric, args=(metric_name, metric_data), daemon=True
        ).start()

    def _persist_metric(self, metric_name: str, metric_data: MetricData):
        """Persist metric to database"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                metadata_json = json.dumps(metric_data.metadata) if metric_data.metadata else None
                conn.execute(
                    "INSERT INTO metrics (metric_name, timestamp, value, metadata) VALUES (?, ?, ?, ?)",
                    (metric_name, metric_data.timestamp, metric_data.value, metadata_json),
                )
        except Exception as e:
            logging.error(f"Error persisting metric {metric_name}: {e}")

    def record_provider_request(
        self, provider: str, response_time: float, success: bool, error: str = None
    ):
        """Record provider request metrics"""
        with self.lock:
            stats = self.provider_stats[provider]
            stats["requests"] += 1

            if not success:
                stats["failures"] += 1
                stats["last_error"] = error

            # Update rolling average
            current_avg = stats["avg_response_time"]
            total_requests = stats["requests"]
            stats["avg_response_time"] = (
                (current_avg * (total_requests - 1)) + response_time
            ) / total_requests

            # Check SLA breach (>5 seconds)
            if response_time > 5.0:
                stats["sla_breaches"] += 1

        # Record individual metrics
        self.record_metric(f"provider_{provider}_response_time", response_time)
        self.record_metric(f"provider_{provider}_success", 1 if success else 0)

    def record_user_session(self, session_id: str, duration: float, pages_viewed: int, errors: int):
        """Record user experience metrics"""
        with self.lock:
            metrics = self.user_metrics[session_id]
            metrics["sessions"] += 1
            metrics["avg_session_duration"] = duration
            metrics["bounce_rate"] = 1 if pages_viewed <= 1 else 0
            metrics["error_rate"] = errors / max(pages_viewed, 1) * 100

        self.record_metric("session_duration", duration)
        self.record_metric("pages_per_session", pages_viewed)
        self.record_metric("session_error_rate", errors / max(pages_viewed, 1) * 100)

    def _check_alerts(self):
        """Check metrics against thresholds and generate alerts"""
        current_time = time.time()

        with self.lock:
            for metric_name, threshold_config in self.thresholds.items():
                if metric_name not in self.metrics:
                    continue

                recent_metrics = [
                    m for m in self.metrics[metric_name] if current_time - m.timestamp < 300
                ]  # Last 5 minutes

                if not recent_metrics:
                    continue

                # Get average of recent values
                avg_value = sum(m.value for m in recent_metrics) / len(recent_metrics)

                # Check thresholds
                alert_type = None
                threshold_value = None

                if avg_value >= threshold_config.get("critical", float("inf")):
                    alert_type = "critical"
                    threshold_value = threshold_config["critical"]
                elif avg_value >= threshold_config.get("warning", float("inf")):
                    alert_type = "warning"
                    threshold_value = threshold_config["warning"]

                if alert_type:
                    self._create_alert(
                        metric_name, alert_type, threshold_value, avg_value, current_time
                    )

    def _create_alert(
        self,
        metric_name: str,
        alert_type: str,
        threshold_value: float,
        actual_value: float,
        timestamp: float,
    ):
        """Create and store an alert"""
        alert = {
            "metric_name": metric_name,
            "alert_type": alert_type,
            "threshold_value": threshold_value,
            "actual_value": actual_value,
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
        }

        self.alerts.append(alert)

        # Persist alert to database
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                conn.execute(
                    "INSERT INTO alerts (metric_name, alert_type, threshold_value, actual_value, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (metric_name, alert_type, threshold_value, actual_value, timestamp),
                )
        except Exception as e:
            logging.error(f"Error persisting alert: {e}")

        # Keep only recent alerts in memory
        cutoff_time = timestamp - 3600  # Last hour
        self.alerts = [a for a in self.alerts if a["timestamp"] > cutoff_time]

    def _cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        cutoff_time = time.time() - (self.retention_hours * 3600)

        # Clean up in-memory data
        with self.lock:
            for metric_name in self.metrics:
                self.metrics[metric_name] = deque(
                    [m for m in self.metrics[metric_name] if m.timestamp > cutoff_time], maxlen=1000
                )

        # Clean up database periodically (every hour)
        if hasattr(self, "_last_cleanup") and time.time() - self._last_cleanup < 3600:
            return

        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_time,))
                conn.execute(
                    "DELETE FROM alerts WHERE timestamp < ? AND resolved = TRUE", (cutoff_time,)
                )
            self._last_cleanup = time.time()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get comprehensive dashboard data"""
        with self.lock:
            current_time = time.time()

            # Real-time metrics (last 5 minutes)
            realtime_metrics = {}
            for metric_name, metric_list in self.metrics.items():
                recent = [m for m in metric_list if current_time - m.timestamp < 300]
                if recent:
                    realtime_metrics[metric_name] = {
                        "current": recent[-1].value,
                        "average": sum(m.value for m in recent) / len(recent),
                        "min": min(m.value for m in recent),
                        "max": max(m.value for m in recent),
                        "trend": self._calculate_trend(recent),
                    }

            # Provider health summary
            provider_health = {}
            for provider, stats in self.provider_stats.items():
                uptime = ((stats["requests"] - stats["failures"]) / max(stats["requests"], 1)) * 100
                provider_health[provider] = {
                    "uptime_percentage": uptime,
                    "avg_response_time": stats["avg_response_time"],
                    "total_requests": stats["requests"],
                    "failed_requests": stats["failures"],
                    "sla_breaches": stats["sla_breaches"],
                    "status": self._get_provider_status(uptime, stats["avg_response_time"]),
                }

            # Recent alerts
            recent_alerts = [a for a in self.alerts if current_time - a["timestamp"] < 3600]

            return {
                "realtime_metrics": realtime_metrics,
                "provider_health": provider_health,
                "recent_alerts": recent_alerts,
                "system_status": self._get_system_status(realtime_metrics),
                "timestamp": current_time,
                "monitoring_active": self.is_monitoring,
            }

    def _calculate_trend(self, metrics: list[MetricData]) -> str:
        """Calculate trend direction for metrics"""
        if len(metrics) < 2:
            return "stable"

        recent_half = metrics[len(metrics) // 2 :]
        older_half = metrics[: len(metrics) // 2]

        recent_avg = sum(m.value for m in recent_half) / len(recent_half)
        older_avg = sum(m.value for m in older_half) / len(older_half)

        change_pct = ((recent_avg - older_avg) / max(older_avg, 0.001)) * 100

        if change_pct > 5:
            return "increasing"
        elif change_pct < -5:
            return "decreasing"
        else:
            return "stable"

    def _get_provider_status(self, uptime: float, avg_response_time: float) -> str:
        """Determine provider status based on metrics"""
        if uptime >= 99.5 and avg_response_time < 2.0:
            return "excellent"
        elif uptime >= 99.0 and avg_response_time < 3.0:
            return "good"
        elif uptime >= 95.0 and avg_response_time < 5.0:
            return "degraded"
        else:
            return "critical"

    def _get_system_status(self, metrics: dict[str, Any]) -> str:
        """Determine overall system status"""
        critical_metrics = ["cpu_usage", "memory_usage", "disk_usage"]

        for metric_name in critical_metrics:
            if metric_name in metrics:
                current_value = metrics[metric_name]["current"]
                if current_value >= self.thresholds.get(metric_name, {}).get("critical", 100):
                    return "critical"
                elif current_value >= self.thresholds.get(metric_name, {}).get("warning", 100):
                    return "warning"

        return "healthy"

    def get_historical_data(self, metric_name: str, hours: int = 24) -> list[dict[str, Any]]:
        """Get historical data for a specific metric"""
        cutoff_time = time.time() - (hours * 3600)

        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.execute(
                    "SELECT timestamp, value, metadata FROM metrics WHERE metric_name = ? AND timestamp > ? ORDER BY timestamp",
                    (metric_name, cutoff_time),
                )

                results = []
                for row in cursor:
                    timestamp, value, metadata_json = row
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    results.append(
                        {
                            "timestamp": timestamp,
                            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
                            "value": value,
                            "metadata": metadata,
                        }
                    )

                return results
        except Exception as e:
            logging.error(f"Error getting historical data: {e}")
            return []

    def set_threshold(self, metric_name: str, warning: float = None, critical: float = None):
        """Set custom alert thresholds"""
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}

        if warning is not None:
            self.thresholds[metric_name]["warning"] = warning
        if critical is not None:
            self.thresholds[metric_name]["critical"] = critical

    def get_sla_report(self, provider: str | None = None, days: int = 7) -> dict[str, Any]:
        """Generate SLA report for providers"""
        try:
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                if provider:
                    cursor = conn.execute(
                        "SELECT * FROM provider_sla WHERE provider = ? AND date >= date('now', ? || ' days')",
                        (provider, f"-{days}"),
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM provider_sla WHERE date >= date('now', ? || ' days')",
                        (f"-{days}",),
                    )

                results = []
                for row in cursor:
                    results.append(
                        {
                            "provider": row[1],
                            "date": row[2],
                            "uptime_percentage": row[3],
                            "avg_response_time": row[4],
                            "total_requests": row[5],
                            "failed_requests": row[6],
                        }
                    )

                return {"sla_data": results, "period_days": days}
        except Exception as e:
            logging.error(f"Error generating SLA report: {e}")
            return {"sla_data": [], "period_days": days}


# Global dashboard instance
dashboard = PerformanceDashboard()
