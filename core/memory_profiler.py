"""
Memory Profiling System (Task 3.2.1)

This module implements comprehensive memory monitoring for the TQ GenAI Chat application,
including real-time tracking, leak detection, garbage collection optimization, and alerts.
"""

import gc
import logging
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""

    timestamp: datetime
    process_memory_mb: float
    system_memory_percent: float
    rss_memory_mb: float
    vms_memory_mb: float
    heap_size_mb: float
    gc_objects: int
    active_threads: int
    file_descriptors: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "process_memory_mb": self.process_memory_mb,
            "system_memory_percent": self.system_memory_percent,
            "rss_memory_mb": self.rss_memory_mb,
            "vms_memory_mb": self.vms_memory_mb,
            "heap_size_mb": self.heap_size_mb,
            "gc_objects": self.gc_objects,
            "active_threads": self.active_threads,
            "file_descriptors": self.file_descriptors,
        }


@dataclass
class MemoryLeak:
    """Detected memory leak information."""

    object_type: str
    count_growth: int
    size_growth_mb: float
    detection_time: datetime
    stack_trace: list[str] = field(default_factory=list)
    severity: str = "low"  # low, medium, high, critical

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "object_type": self.object_type,
            "count_growth": self.count_growth,
            "size_growth_mb": self.size_growth_mb,
            "detection_time": self.detection_time.isoformat(),
            "stack_trace": self.stack_trace,
            "severity": self.severity,
        }


@dataclass
class MemoryAlert:
    """Memory alert configuration and trigger."""

    alert_type: str  # 'high_usage', 'rapid_growth', 'leak_detected', 'gc_pressure'
    threshold: float
    message: str
    severity: str = "warning"  # info, warning, error, critical
    callback: Optional[Callable] = None
    triggered_count: int = 0
    last_triggered: Optional[datetime] = None

    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should be triggered."""
        if current_value >= self.threshold:
            # Implement cooldown to prevent spam
            if self.last_triggered is None or datetime.now() - self.last_triggered > timedelta(
                minutes=5
            ):
                return True
        return False

    def trigger(self):
        """Trigger the alert."""
        self.triggered_count += 1
        self.last_triggered = datetime.now()
        logger.warning(f"Memory alert triggered: {self.message}")

        if self.callback:
            try:
                self.callback(self)
            except Exception as e:
                logger.error(f"Error in memory alert callback: {e}")


class MemoryTracker:
    """Track memory allocations and deallocations."""

    def __init__(self):
        self.allocations: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "total_size": 0, "peak_count": 0, "peak_size": 0}
        )
        self.stack_traces: dict[str, list[str]] = {}
        self.enabled = False

    def start_tracking(self):
        """Start memory tracking."""
        if not self.enabled:
            tracemalloc.start()
            self.enabled = True
            logger.info("Memory tracking started")

    def stop_tracking(self):
        """Stop memory tracking."""
        if self.enabled:
            tracemalloc.stop()
            self.enabled = False
            logger.info("Memory tracking stopped")

    def take_snapshot(self) -> dict[str, Any]:
        """Take a memory snapshot."""
        if not self.enabled:
            return {}

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")

        return {
            "total_memory_mb": sum(stat.size for stat in top_stats) / 1024 / 1024,
            "top_allocations": [
                {
                    "file": stat.traceback.format()[0] if stat.traceback.format() else "unknown",
                    "size_mb": stat.size / 1024 / 1024,
                    "count": stat.count,
                }
                for stat in top_stats[:10]
            ],
        }

    def get_allocation_stats(self) -> dict[str, Any]:
        """Get allocation statistics."""
        return dict(self.allocations)


class GarbageCollectionOptimizer:
    """Optimize garbage collection for better performance."""

    def __init__(self):
        self.gc_stats = deque(maxlen=1000)
        self.auto_tune = True
        self.last_optimization = None

    def collect_stats(self):
        """Collect garbage collection statistics."""
        before_counts = gc.get_count()
        before_time = time.time()

        # Force garbage collection and measure
        collected = gc.collect()

        after_time = time.time()
        after_counts = gc.get_count()

        stats = {
            "timestamp": datetime.now(),
            "collection_time_ms": (after_time - before_time) * 1000,
            "objects_collected": collected,
            "before_counts": before_counts,
            "after_counts": after_counts,
            "total_objects": sum(after_counts),
        }

        self.gc_stats.append(stats)
        return stats

    def optimize_thresholds(self):
        """Optimize GC thresholds based on collected stats."""
        if not self.auto_tune or len(self.gc_stats) < 10:
            return

        # Analyze recent GC performance
        recent_stats = list(self.gc_stats)[-10:]
        avg_time = sum(s["collection_time_ms"] for s in recent_stats) / len(recent_stats)
        avg_collected = sum(s["objects_collected"] for s in recent_stats) / len(recent_stats)

        # Adjust thresholds if GC is too frequent or taking too long
        if avg_time > 50:  # GC taking more than 50ms on average
            thresholds = gc.get_threshold()
            new_thresholds = (
                int(thresholds[0] * 1.2),  # Increase gen0 threshold
                int(thresholds[1] * 1.1),  # Slight increase gen1
                thresholds[2],  # Keep gen2 same
            )
            gc.set_threshold(*new_thresholds)
            logger.info(f"Adjusted GC thresholds: {thresholds} -> {new_thresholds}")
            self.last_optimization = datetime.now()

        elif avg_collected < 10:  # Very few objects collected
            thresholds = gc.get_threshold()
            new_thresholds = (
                max(100, int(thresholds[0] * 0.8)),  # Decrease gen0 threshold
                max(10, int(thresholds[1] * 0.9)),  # Slight decrease gen1
                thresholds[2],  # Keep gen2 same
            )
            gc.set_threshold(*new_thresholds)
            logger.info(f"Adjusted GC thresholds: {thresholds} -> {new_thresholds}")
            self.last_optimization = datetime.now()

    def get_gc_stats(self) -> dict[str, Any]:
        """Get garbage collection statistics."""
        if not self.gc_stats:
            return {}

        recent_stats = list(self.gc_stats)[-100:]  # Last 100 collections

        return {
            "total_collections": len(self.gc_stats),
            "average_time_ms": sum(s["collection_time_ms"] for s in recent_stats)
            / len(recent_stats),
            "average_collected": sum(s["objects_collected"] for s in recent_stats)
            / len(recent_stats),
            "current_thresholds": gc.get_threshold(),
            "current_counts": gc.get_count(),
            "last_optimization": self.last_optimization.isoformat()
            if self.last_optimization
            else None,
        }


class MemoryLeakDetector:
    """Detect potential memory leaks."""

    def __init__(self, analysis_window: int = 100):
        self.object_history = defaultdict(lambda: deque(maxlen=analysis_window))
        self.leak_threshold_growth = 1.5  # 50% growth considered potential leak
        self.leak_threshold_size = 10  # 10MB growth considered significant
        self.detected_leaks: list[MemoryLeak] = []

    def analyze_objects(self) -> list[MemoryLeak]:
        """Analyze object counts for potential leaks."""
        current_objects = {}

        # Get current object counts by type
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            current_objects[obj_type] = current_objects.get(obj_type, 0) + 1

        new_leaks = []

        for obj_type, count in current_objects.items():
            self.object_history[obj_type].append(
                {
                    "timestamp": datetime.now(),
                    "count": count,
                    "estimated_size": self._estimate_object_size(obj_type, count),
                }
            )

            # Analyze trend for potential leaks
            if len(self.object_history[obj_type]) >= 10:
                leak = self._detect_leak_trend(obj_type, self.object_history[obj_type])
                if leak:
                    new_leaks.append(leak)
                    self.detected_leaks.append(leak)

        return new_leaks

    def _detect_leak_trend(self, obj_type: str, history: deque) -> Optional[MemoryLeak]:
        """Detect if object type shows leak pattern."""
        if len(history) < 10:
            return None

        # Compare first and last periods
        early_avg = sum(h["count"] for h in list(history)[:5]) / 5
        recent_avg = sum(h["count"] for h in list(history)[-5:]) / 5

        early_size = sum(h["estimated_size"] for h in list(history)[:5]) / 5
        recent_size = sum(h["estimated_size"] for h in list(history)[-5:]) / 5

        growth_ratio = recent_avg / early_avg if early_avg > 0 else float("inf")
        size_growth_mb = (recent_size - early_size) / 1024 / 1024

        # Determine severity
        severity = "low"
        if growth_ratio > 3 or size_growth_mb > 50:
            severity = "critical"
        elif growth_ratio > 2 or size_growth_mb > 20:
            severity = "high"
        elif growth_ratio > self.leak_threshold_growth or size_growth_mb > self.leak_threshold_size:
            severity = "medium"
        else:
            return None  # No leak detected

        return MemoryLeak(
            object_type=obj_type,
            count_growth=int(recent_avg - early_avg),
            size_growth_mb=size_growth_mb,
            detection_time=datetime.now(),
            severity=severity,
        )

    def _estimate_object_size(self, obj_type: str, count: int) -> int:
        """Estimate total size of objects of given type."""
        # Basic size estimation based on common object types
        size_estimates = {
            "str": 50,  # bytes per string
            "dict": 200,  # bytes per dict
            "list": 100,  # bytes per list
            "int": 28,  # bytes per int
            "float": 24,  # bytes per float
            "function": 100,  # bytes per function
            "method": 80,  # bytes per method
        }

        estimated_size_per_obj = size_estimates.get(obj_type, 100)  # Default 100 bytes
        return count * estimated_size_per_obj

    def get_leak_summary(self) -> dict[str, Any]:
        """Get summary of detected leaks."""
        if not self.detected_leaks:
            return {"total_leaks": 0, "leaks_by_severity": {}}

        leaks_by_severity = defaultdict(int)
        for leak in self.detected_leaks:
            leaks_by_severity[leak.severity] += 1

        return {
            "total_leaks": len(self.detected_leaks),
            "leaks_by_severity": dict(leaks_by_severity),
            "recent_leaks": [leak.to_dict() for leak in self.detected_leaks[-5:]],
        }


class MemoryProfiler:
    """Main memory profiling system."""

    def __init__(self, monitoring_interval: int = 30):
        self.monitoring_interval = monitoring_interval
        self.snapshots = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.alerts: list[MemoryAlert] = []
        self.tracker = MemoryTracker()
        self.gc_optimizer = GarbageCollectionOptimizer()
        self.leak_detector = MemoryLeakDetector()

        self.monitoring_active = False
        self.monitor_thread = None

        # Setup default alerts
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """Setup default memory alerts."""
        self.alerts = [
            MemoryAlert(
                alert_type="high_usage",
                threshold=80.0,  # 80% system memory
                message="High system memory usage detected",
                severity="warning",
            ),
            MemoryAlert(
                alert_type="process_memory",
                threshold=500.0,  # 500MB process memory
                message="High process memory usage detected",
                severity="warning",
            ),
            MemoryAlert(
                alert_type="rapid_growth",
                threshold=50.0,  # 50MB growth in 5 minutes
                message="Rapid memory growth detected",
                severity="error",
            ),
        ]

    def start_monitoring(self):
        """Start continuous memory monitoring."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.tracker.start_tracking()
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Memory profiling started")

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring_active = False
        self.tracker.stop_tracking()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Memory profiling stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Take memory snapshot
                snapshot = self._take_snapshot()
                self.snapshots.append(snapshot)

                # Check alerts
                self._check_alerts(snapshot)

                # Analyze for leaks periodically
                if len(self.snapshots) % 10 == 0:  # Every 10 snapshots
                    self.leak_detector.analyze_objects()

                # Optimize GC periodically
                if len(self.snapshots) % 20 == 0:  # Every 20 snapshots
                    self.gc_optimizer.collect_stats()
                    self.gc_optimizer.optimize_thresholds()

                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                time.sleep(self.monitoring_interval)

    def _take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot."""
        process = psutil.Process()
        memory_info = process.memory_info()

        # Get heap size estimate
        heap_size = sum(gc.get_count()) * 100  # Rough estimate

        return MemorySnapshot(
            timestamp=datetime.now(),
            process_memory_mb=memory_info.rss / 1024 / 1024,
            system_memory_percent=psutil.virtual_memory().percent,
            rss_memory_mb=memory_info.rss / 1024 / 1024,
            vms_memory_mb=memory_info.vms / 1024 / 1024,
            heap_size_mb=heap_size / 1024 / 1024,
            gc_objects=sum(gc.get_count()),
            active_threads=threading.active_count(),
            file_descriptors=process.num_fds() if hasattr(process, "num_fds") else 0,
        )

    def _check_alerts(self, snapshot: MemorySnapshot):
        """Check if any alerts should be triggered."""
        for alert in self.alerts:
            value = 0

            if alert.alert_type == "high_usage":
                value = snapshot.system_memory_percent
            elif alert.alert_type == "process_memory":
                value = snapshot.process_memory_mb
            elif alert.alert_type == "rapid_growth":
                if len(self.snapshots) >= 10:
                    old_snapshot = self.snapshots[-10]
                    value = snapshot.process_memory_mb - old_snapshot.process_memory_mb

            if alert.should_trigger(value):
                alert.trigger()

    def force_garbage_collection(self) -> dict[str, Any]:
        """Force garbage collection and return stats."""
        return self.gc_optimizer.collect_stats()

    def get_memory_stats(self) -> dict[str, Any]:
        """Get comprehensive memory statistics."""
        if not self.snapshots:
            return {}

        latest = self.snapshots[-1]

        # Calculate trends
        trend_data = {}
        if len(self.snapshots) >= 10:
            old_snapshot = self.snapshots[-10]
            trend_data = {
                "memory_trend_mb": latest.process_memory_mb - old_snapshot.process_memory_mb,
                "objects_trend": latest.gc_objects - old_snapshot.gc_objects,
            }

        return {
            "current_snapshot": latest.to_dict(),
            "trend_data": trend_data,
            "gc_stats": self.gc_optimizer.get_gc_stats(),
            "leak_summary": self.leak_detector.get_leak_summary(),
            "allocation_stats": self.tracker.get_allocation_stats(),
            "alert_summary": {
                "total_alerts": len(self.alerts),
                "triggered_alerts": sum(1 for a in self.alerts if a.triggered_count > 0),
            },
        }

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get data formatted for dashboard display."""
        if not self.snapshots:
            return {}

        # Get recent snapshots for charts
        recent_snapshots = list(self.snapshots)[-50:]  # Last 50 snapshots

        return {
            "memory_usage_chart": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "process_memory_mb": s.process_memory_mb,
                    "system_memory_percent": s.system_memory_percent,
                }
                for s in recent_snapshots
            ],
            "gc_objects_chart": [
                {"timestamp": s.timestamp.isoformat(), "gc_objects": s.gc_objects}
                for s in recent_snapshots
            ],
            "current_stats": self.get_memory_stats(),
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "message": a.message,
                    "triggered_count": a.triggered_count,
                    "last_triggered": a.last_triggered.isoformat() if a.last_triggered else None,
                }
                for a in self.alerts
            ],
        }

    def add_alert(self, alert: MemoryAlert):
        """Add a custom memory alert."""
        self.alerts.append(alert)

    def remove_alert(self, alert_type: str):
        """Remove alerts of specific type."""
        self.alerts = [a for a in self.alerts if a.alert_type != alert_type]


# Global profiler instance
_profiler_instance = None


def get_memory_profiler() -> MemoryProfiler:
    """Get the global memory profiler instance."""
    global _profiler_instance
    if _profiler_instance is None:
        _profiler_instance = MemoryProfiler()
    return _profiler_instance


def start_memory_monitoring():
    """Start memory monitoring."""
    profiler = get_memory_profiler()
    profiler.start_monitoring()


def stop_memory_monitoring():
    """Stop memory monitoring."""
    profiler = get_memory_profiler()
    profiler.stop_monitoring()


def get_memory_dashboard_data() -> dict[str, Any]:
    """Get memory dashboard data."""
    profiler = get_memory_profiler()
    return profiler.get_dashboard_data()


if __name__ == "__main__":
    # Example usage
    profiler = get_memory_profiler()
    profiler.start_monitoring()

    try:
        # Simulate some memory usage
        data = []
        for i in range(1000):
            data.append(f"String {i} " * 100)
            time.sleep(0.01)

        # Get stats
        stats = profiler.get_memory_stats()
        print("Memory Stats:")
        print(f"Process Memory: {stats['current_snapshot']['process_memory_mb']:.2f} MB")
        print(f"GC Objects: {stats['current_snapshot']['gc_objects']}")

        # Force GC
        gc_stats = profiler.force_garbage_collection()
        print(
            f"GC collected {gc_stats['objects_collected']} objects in {gc_stats['collection_time_ms']:.2f}ms"
        )

    finally:
        profiler.stop_monitoring()
