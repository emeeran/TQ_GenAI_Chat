"""
Advanced Analytics framework for TQ GenAI Chat application.
Provides user behavior analysis, A/B testing, performance metrics, and business intelligence.
"""

import asyncio
import json
import logging
import statistics
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    import numpy as np
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import sqlite3

    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of analytics events."""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CHAT_STARTED = "chat_started"
    CHAT_MESSAGE = "chat_message"
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    PROVIDER_SWITCHED = "provider_switched"
    ERROR_OCCURRED = "error_occurred"
    PAGE_VIEW = "page_view"
    FEATURE_USED = "feature_used"
    SESSION_TIMEOUT = "session_timeout"
    API_CALL = "api_call"


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class ABTestStatus(Enum):
    """A/B test status."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class AnalyticsEvent:
    """Analytics event structure."""

    id: str
    event_type: EventType
    user_id: str
    session_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "properties": self.properties,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalyticsEvent":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            event_type=EventType(data["event_type"]),
            user_id=data["user_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            properties=data.get("properties", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Metric:
    """Metric data point."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


@dataclass
class ABTestVariant:
    """A/B test variant configuration."""

    id: str
    name: str
    description: str
    weight: float  # 0.0 to 1.0
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "config": self.config,
        }


@dataclass
class ABTest:
    """A/B test configuration."""

    id: str
    name: str
    description: str
    status: ABTestStatus
    variants: list[ABTestVariant]
    start_date: datetime | None = None
    end_date: datetime | None = None
    target_metric: str = ""
    sample_size: int = 0
    confidence_level: float = 0.95
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "variants": [v.to_dict() for v in self.variants],
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "target_metric": self.target_metric,
            "sample_size": self.sample_size,
            "confidence_level": self.confidence_level,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class UserSegment:
    """User segment definition."""

    id: str
    name: str
    description: str
    criteria: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def matches_user(self, user_properties: dict[str, Any]) -> bool:
        """Check if user matches segment criteria."""
        for key, expected_value in self.criteria.items():
            if key not in user_properties:
                return False

            user_value = user_properties[key]

            if isinstance(expected_value, dict):
                # Handle operators like {"gte": 25} for age >= 25
                for operator, value in expected_value.items():
                    if operator == "gte" and user_value < value:
                        return False
                    elif operator == "lte" and user_value > value:
                        return False
                    elif operator == "eq" and user_value != value:
                        return False
                    elif operator == "in" and user_value not in value:
                        return False
            else:
                # Direct equality check
                if user_value != expected_value:
                    return False

        return True


class EventStore(ABC):
    """Abstract event store interface."""

    @abstractmethod
    async def store_event(self, event: AnalyticsEvent) -> bool:
        """Store an analytics event."""
        pass

    @abstractmethod
    async def get_events(
        self,
        user_id: str = None,
        event_type: EventType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000,
    ) -> list[AnalyticsEvent]:
        """Retrieve events with filters."""
        pass

    @abstractmethod
    async def get_event_count(
        self, event_type: EventType = None, start_time: datetime = None, end_time: datetime = None
    ) -> int:
        """Get count of events matching criteria."""
        pass


class InMemoryEventStore(EventStore):
    """In-memory event store for development."""

    def __init__(self):
        self.events: list[AnalyticsEvent] = []

    async def store_event(self, event: AnalyticsEvent) -> bool:
        """Store an analytics event."""
        try:
            self.events.append(event)
            return True
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
            return False

    async def get_events(
        self,
        user_id: str = None,
        event_type: EventType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000,
    ) -> list[AnalyticsEvent]:
        """Retrieve events with filters."""
        filtered_events = self.events

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        # Sort by timestamp descending and limit
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered_events[:limit]

    async def get_event_count(
        self, event_type: EventType = None, start_time: datetime = None, end_time: datetime = None
    ) -> int:
        """Get count of events matching criteria."""
        events = await self.get_events(
            event_type=event_type, start_time=start_time, end_time=end_time, limit=999999
        )
        return len(events)


class SQLiteEventStore(EventStore):
    """SQLite-based event store for production."""

    def __init__(self, db_path: str = "analytics.db"):
        if not SQLITE_AVAILABLE:
            raise ImportError("sqlite3 required for SQLite event store")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                properties TEXT,
                metadata TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)
        """
        )

        conn.commit()
        conn.close()

    async def store_event(self, event: AnalyticsEvent) -> bool:
        """Store an analytics event."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO events (id, event_type, user_id, session_id, timestamp, properties, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.id,
                    event.event_type.value,
                    event.user_id,
                    event.session_id,
                    event.timestamp.isoformat(),
                    json.dumps(event.properties),
                    json.dumps(event.metadata),
                ),
            )

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Failed to store event in SQLite: {e}")
            return False

    async def get_events(
        self,
        user_id: str = None,
        event_type: EventType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000,
    ) -> list[AnalyticsEvent]:
        """Retrieve events with filters."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                event = AnalyticsEvent(
                    id=row[0],
                    event_type=EventType(row[1]),
                    user_id=row[2],
                    session_id=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    properties=json.loads(row[5]) if row[5] else {},
                    metadata=json.loads(row[6]) if row[6] else {},
                )
                events.append(event)

            conn.close()
            return events

        except Exception as e:
            logger.error(f"Failed to get events from SQLite: {e}")
            return []

    async def get_event_count(
        self, event_type: EventType = None, start_time: datetime = None, end_time: datetime = None
    ) -> int:
        """Get count of events matching criteria."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT COUNT(*) FROM events WHERE 1=1"
            params = []

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())

            cursor.execute(query, params)
            count = cursor.fetchone()[0]

            conn.close()
            return count

        except Exception as e:
            logger.error(f"Failed to get event count from SQLite: {e}")
            return 0


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self):
        self.metrics: list[Metric] = []
        self.counters: dict[str, float] = {}
        self.gauges: dict[str, float] = {}
        self.histograms: dict[str, list[float]] = {}
        self.timers: dict[str, list[float]] = {}

    def increment_counter(self, name: str, value: float = 1.0, tags: dict[str, str] = None):
        """Increment a counter metric."""
        key = self._get_metric_key(name, tags or {})
        self.counters[key] = self.counters.get(key, 0) + value

        metric = Metric(
            name=name, value=self.counters[key], metric_type=MetricType.COUNTER, tags=tags or {}
        )
        self.metrics.append(metric)

    def set_gauge(self, name: str, value: float, tags: dict[str, str] = None):
        """Set a gauge metric."""
        key = self._get_metric_key(name, tags or {})
        self.gauges[key] = value

        metric = Metric(name=name, value=value, metric_type=MetricType.GAUGE, tags=tags or {})
        self.metrics.append(metric)

    def record_histogram(self, name: str, value: float, tags: dict[str, str] = None):
        """Record a histogram value."""
        key = self._get_metric_key(name, tags or {})
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)

        metric = Metric(name=name, value=value, metric_type=MetricType.HISTOGRAM, tags=tags or {})
        self.metrics.append(metric)

    def record_timer(self, name: str, duration: float, tags: dict[str, str] = None):
        """Record a timer value in seconds."""
        key = self._get_metric_key(name, tags or {})
        if key not in self.timers:
            self.timers[key] = []
        self.timers[key].append(duration)

        metric = Metric(name=name, value=duration, metric_type=MetricType.TIMER, tags=tags or {})
        self.metrics.append(metric)

    def get_histogram_stats(self, name: str, tags: dict[str, str] = None) -> dict[str, float]:
        """Get statistics for a histogram."""
        key = self._get_metric_key(name, tags or {})
        values = self.histograms.get(key, [])

        if not values:
            return {}

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99),
        }

    def get_timer_stats(self, name: str, tags: dict[str, str] = None) -> dict[str, float]:
        """Get statistics for a timer."""
        return self.get_histogram_stats(name, tags)

    def _get_metric_key(self, name: str, tags: dict[str, str]) -> str:
        """Generate a unique key for metric with tags."""
        if not tags:
            return name

        sorted_tags = sorted(tags.items())
        tag_string = ",".join(f"{k}={v}" for k, v in sorted_tags)
        return f"{name}#{tag_string}"

    def _percentile(self, values: list[float], percentile: float) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]


class UserBehaviorAnalyzer:
    """Analyzes user behavior patterns."""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    async def get_user_activity_summary(self, user_id: str, days: int = 30) -> dict[str, Any]:
        """Get user activity summary for the past N days."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        events = await self.event_store.get_events(
            user_id=user_id, start_time=start_time, end_time=end_time, limit=10000
        )

        if not events:
            return {
                "user_id": user_id,
                "period_days": days,
                "total_events": 0,
                "active_days": 0,
                "avg_session_duration": 0,
                "top_features": [],
                "event_breakdown": {},
            }

        # Calculate metrics
        event_breakdown = {}
        feature_usage = {}
        daily_activity = {}

        for event in events:
            # Event type breakdown
            event_type = event.event_type.value
            event_breakdown[event_type] = event_breakdown.get(event_type, 0) + 1

            # Feature usage tracking
            if "feature" in event.properties:
                feature = event.properties["feature"]
                feature_usage[feature] = feature_usage.get(feature, 0) + 1

            # Daily activity
            day = event.timestamp.date()
            if day not in daily_activity:
                daily_activity[day] = []
            daily_activity[day].append(event)

        # Calculate session durations
        session_durations = []
        for day_events in daily_activity.values():
            if len(day_events) >= 2:
                day_events.sort(key=lambda e: e.timestamp)
                duration = (day_events[-1].timestamp - day_events[0].timestamp).total_seconds()
                session_durations.append(duration)

        avg_session_duration = statistics.mean(session_durations) if session_durations else 0

        # Top features
        top_features = sorted(feature_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(events),
            "active_days": len(daily_activity),
            "avg_session_duration": avg_session_duration,
            "top_features": [{"feature": f, "usage_count": c} for f, c in top_features],
            "event_breakdown": event_breakdown,
        }

    async def get_user_segments(
        self, segment_definitions: list[UserSegment]
    ) -> dict[str, list[str]]:
        """Segment users based on behavior."""
        # Get recent user activity
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=30)

        events = await self.event_store.get_events(
            start_time=start_time, end_time=end_time, limit=50000
        )

        # Build user profiles
        user_profiles = {}
        for event in events:
            user_id = event.user_id
            if user_id not in user_profiles:
                user_profiles[user_id] = {
                    "total_events": 0,
                    "event_types": set(),
                    "features_used": set(),
                    "first_seen": event.timestamp,
                    "last_seen": event.timestamp,
                }

            profile = user_profiles[user_id]
            profile["total_events"] += 1
            profile["event_types"].add(event.event_type.value)
            profile["last_seen"] = max(profile["last_seen"], event.timestamp)
            profile["first_seen"] = min(profile["first_seen"], event.timestamp)

            if "feature" in event.properties:
                profile["features_used"].add(event.properties["feature"])

        # Convert sets to counts and calculate derived metrics
        for user_id, profile in user_profiles.items():
            profile["unique_event_types"] = len(profile["event_types"])
            profile["unique_features_used"] = len(profile["features_used"])
            profile["days_active"] = (profile["last_seen"] - profile["first_seen"]).days + 1
            profile["avg_events_per_day"] = profile["total_events"] / profile["days_active"]

            # Convert sets to lists for JSON serialization
            profile["event_types"] = list(profile["event_types"])
            profile["features_used"] = list(profile["features_used"])

        # Apply segment definitions
        segments = {}
        for segment in segment_definitions:
            segments[segment.name] = []

            for user_id, profile in user_profiles.items():
                if segment.matches_user(profile):
                    segments[segment.name].append(user_id)

        return segments

    async def calculate_retention_rates(self, cohort_period: str = "weekly") -> dict[str, Any]:
        """Calculate user retention rates."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=90)  # Look at 90 days of data

        events = await self.event_store.get_events(
            start_time=start_time, end_time=end_time, limit=100000
        )

        # Group users by first activity date (cohort)
        user_first_activity = {}
        user_activity_dates = {}

        for event in events:
            user_id = event.user_id
            activity_date = event.timestamp.date()

            if user_id not in user_first_activity:
                user_first_activity[user_id] = activity_date
                user_activity_dates[user_id] = set()

            user_first_activity[user_id] = min(user_first_activity[user_id], activity_date)
            user_activity_dates[user_id].add(activity_date)

        # Calculate retention by cohort
        cohorts = {}
        for user_id, first_date in user_first_activity.items():
            # Determine cohort period
            if cohort_period == "weekly":
                cohort_key = first_date.strftime("%Y-W%U")
            else:  # monthly
                cohort_key = first_date.strftime("%Y-%m")

            if cohort_key not in cohorts:
                cohorts[cohort_key] = {"users": set(), "retention": {}}

            cohorts[cohort_key]["users"].add(user_id)

        # Calculate retention rates for each cohort
        for cohort_key, cohort_data in cohorts.items():
            total_users = len(cohort_data["users"])

            # Check retention at different periods
            for period in [7, 14, 30, 60, 90]:  # days
                retained_users = 0

                for user_id in cohort_data["users"]:
                    first_date = user_first_activity[user_id]
                    target_date = first_date + timedelta(days=period)

                    # Check if user was active around target date (±3 days)
                    for check_date in [target_date + timedelta(days=d) for d in range(-3, 4)]:
                        if check_date in user_activity_dates[user_id]:
                            retained_users += 1
                            break

                retention_rate = retained_users / total_users if total_users > 0 else 0
                cohort_data["retention"][f"day_{period}"] = {
                    "retained_users": retained_users,
                    "total_users": total_users,
                    "retention_rate": retention_rate,
                }

        return {
            "cohort_period": cohort_period,
            "cohorts": {
                k: {"total_users": len(v["users"]), "retention": v["retention"]}
                for k, v in cohorts.items()
            },
            "analysis_period": {
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat(),
            },
        }


class ABTestManager:
    """Manages A/B tests and experiments."""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.tests: dict[str, ABTest] = {}
        self.user_assignments: dict[str, dict[str, str]] = {}  # user_id -> {test_id: variant_id}

    def create_test(self, test: ABTest) -> bool:
        """Create a new A/B test."""
        try:
            # Validate test configuration
            if not test.variants:
                raise ValueError("Test must have at least one variant")

            total_weight = sum(v.weight for v in test.variants)
            if abs(total_weight - 1.0) > 0.001:
                raise ValueError("Variant weights must sum to 1.0")

            self.tests[test.id] = test
            logger.info(f"Created A/B test: {test.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create A/B test: {e}")
            return False

    def assign_user_to_variant(self, user_id: str, test_id: str) -> str | None:
        """Assign user to a test variant."""
        if test_id not in self.tests:
            return None

        test = self.tests[test_id]

        # Check if user already assigned
        if user_id in self.user_assignments and test_id in self.user_assignments[user_id]:
            return self.user_assignments[user_id][test_id]

        # Check if test is running
        if test.status != ABTestStatus.RUNNING:
            return None

        # Assign based on user ID hash for consistency
        import hashlib

        hash_input = f"{user_id}:{test_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        random_value = (hash_value % 10000) / 10000.0  # 0.0 to 1.0

        # Select variant based on weights
        cumulative_weight = 0.0
        for variant in test.variants:
            cumulative_weight += variant.weight
            if random_value <= cumulative_weight:
                # Assign user to this variant
                if user_id not in self.user_assignments:
                    self.user_assignments[user_id] = {}
                self.user_assignments[user_id][test_id] = variant.id

                logger.debug(f"Assigned user {user_id} to variant {variant.id} in test {test_id}")
                return variant.id

        # Fallback to first variant
        variant_id = test.variants[0].id
        if user_id not in self.user_assignments:
            self.user_assignments[user_id] = {}
        self.user_assignments[user_id][test_id] = variant_id

        return variant_id

    def start_test(self, test_id: str) -> bool:
        """Start an A/B test."""
        if test_id not in self.tests:
            return False

        test = self.tests[test_id]
        test.status = ABTestStatus.RUNNING
        test.start_date = datetime.utcnow()

        logger.info(f"Started A/B test: {test.name}")
        return True

    def stop_test(self, test_id: str) -> bool:
        """Stop an A/B test."""
        if test_id not in self.tests:
            return False

        test = self.tests[test_id]
        test.status = ABTestStatus.COMPLETED
        test.end_date = datetime.utcnow()

        logger.info(f"Stopped A/B test: {test.name}")
        return True

    async def get_test_results(self, test_id: str) -> dict[str, Any]:
        """Get A/B test results and statistics."""
        if test_id not in self.tests:
            return {}

        test = self.tests[test_id]

        # Get events for users in this test
        user_ids_in_test = []
        variant_assignments = {}

        for user_id, assignments in self.user_assignments.items():
            if test_id in assignments:
                user_ids_in_test.append(user_id)
                variant_assignments[user_id] = assignments[test_id]

        # Analyze conversion and metrics for each variant
        variant_results = {}

        for variant in test.variants:
            variant_users = [uid for uid, vid in variant_assignments.items() if vid == variant.id]

            if not variant_users:
                variant_results[variant.id] = {
                    "name": variant.name,
                    "users": 0,
                    "conversions": 0,
                    "conversion_rate": 0.0,
                    "avg_session_duration": 0.0,
                }
                continue

            # Get events for variant users
            variant_events = []
            for user_id in variant_users:
                user_events = await self.event_store.get_events(
                    user_id=user_id, start_time=test.start_date, end_time=test.end_date, limit=10000
                )
                variant_events.extend(user_events)

            # Calculate metrics
            conversions = len([e for e in variant_events if e.event_type == EventType.CHAT_MESSAGE])

            # Calculate session durations
            user_sessions = {}
            for event in variant_events:
                if event.user_id not in user_sessions:
                    user_sessions[event.user_id] = []
                user_sessions[event.user_id].append(event.timestamp)

            session_durations = []
            for user_id, timestamps in user_sessions.items():
                if len(timestamps) >= 2:
                    timestamps.sort()
                    duration = (timestamps[-1] - timestamps[0]).total_seconds()
                    session_durations.append(duration)

            avg_session_duration = statistics.mean(session_durations) if session_durations else 0

            variant_results[variant.id] = {
                "name": variant.name,
                "users": len(variant_users),
                "conversions": conversions,
                "conversion_rate": conversions / len(variant_users) if variant_users else 0,
                "avg_session_duration": avg_session_duration,
            }

        return {
            "test_id": test_id,
            "test_name": test.name,
            "status": test.status.value,
            "start_date": test.start_date.isoformat() if test.start_date else None,
            "end_date": test.end_date.isoformat() if test.end_date else None,
            "total_users": len(user_ids_in_test),
            "variants": variant_results,
        }


class AnalyticsDashboard:
    """Generates analytics dashboards and reports."""

    def __init__(self, event_store: EventStore, metrics_collector: MetricsCollector):
        self.event_store = event_store
        self.metrics = metrics_collector
        self.behavior_analyzer = UserBehaviorAnalyzer(event_store)

    async def get_real_time_metrics(self) -> dict[str, Any]:
        """Get real-time system metrics."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Event counts
        events_last_hour = await self.event_store.get_event_count(start_time=hour_ago)
        events_last_day = await self.event_store.get_event_count(start_time=day_ago)

        # Active users
        recent_events = await self.event_store.get_events(start_time=hour_ago, limit=10000)
        active_users_hour = len({e.user_id for e in recent_events})

        recent_events_day = await self.event_store.get_events(start_time=day_ago, limit=50000)
        active_users_day = len({e.user_id for e in recent_events_day})

        # Error rate
        error_events_hour = await self.event_store.get_event_count(
            event_type=EventType.ERROR_OCCURRED, start_time=hour_ago
        )
        error_rate = (error_events_hour / events_last_hour * 100) if events_last_hour > 0 else 0

        return {
            "timestamp": now.isoformat(),
            "events_last_hour": events_last_hour,
            "events_last_day": events_last_day,
            "active_users_hour": active_users_hour,
            "active_users_day": active_users_day,
            "error_rate_percent": error_rate,
            "system_metrics": {
                "response_time_p95": self.metrics.get_histogram_stats("response_time").get(
                    "p95", 0
                ),
                "request_rate": self.metrics.counters.get("http_requests", 0),
            },
        }

    async def generate_usage_report(self, days: int = 7) -> dict[str, Any]:
        """Generate comprehensive usage report."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)

        events = await self.event_store.get_events(
            start_time=start_time, end_time=end_time, limit=100000
        )

        # Daily breakdown
        daily_stats = {}
        feature_usage = {}
        provider_usage = {}

        for event in events:
            day = event.timestamp.date().isoformat()

            if day not in daily_stats:
                daily_stats[day] = {
                    "total_events": 0,
                    "unique_users": set(),
                    "chat_messages": 0,
                    "file_uploads": 0,
                }

            daily_stats[day]["total_events"] += 1
            daily_stats[day]["unique_users"].add(event.user_id)

            if event.event_type == EventType.CHAT_MESSAGE:
                daily_stats[day]["chat_messages"] += 1
            elif event.event_type == EventType.FILE_UPLOADED:
                daily_stats[day]["file_uploads"] += 1

            # Feature usage
            if "feature" in event.properties:
                feature = event.properties["feature"]
                feature_usage[feature] = feature_usage.get(feature, 0) + 1

            # Provider usage
            if "provider" in event.properties:
                provider = event.properties["provider"]
                provider_usage[provider] = provider_usage.get(provider, 0) + 1

        # Convert sets to counts
        for day_stats in daily_stats.values():
            day_stats["unique_users"] = len(day_stats["unique_users"])

        # Top features and providers
        top_features = sorted(feature_usage.items(), key=lambda x: x[1], reverse=True)[:10]
        top_providers = sorted(provider_usage.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "period": {
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat(),
                "days": days,
            },
            "summary": {
                "total_events": len(events),
                "unique_users": len({e.user_id for e in events}),
                "avg_events_per_user": len(events) / len({e.user_id for e in events})
                if events
                else 0,
            },
            "daily_breakdown": daily_stats,
            "top_features": [{"feature": f, "usage_count": c} for f, c in top_features],
            "top_providers": [{"provider": p, "usage_count": c} for p, c in top_providers],
        }


class AdvancedAnalyticsManager:
    """Main analytics manager orchestrating all analytics components."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

        # Initialize event store
        store_type = config.get("store_type", "memory")
        if store_type == "sqlite":
            self.event_store = SQLiteEventStore(config.get("db_path", "analytics.db"))
        else:
            self.event_store = InMemoryEventStore()

        # Initialize components
        self.metrics = MetricsCollector()
        self.behavior_analyzer = UserBehaviorAnalyzer(self.event_store)
        self.ab_test_manager = ABTestManager(self.event_store)
        self.dashboard = AnalyticsDashboard(self.event_store, self.metrics)

        # User segments
        self.user_segments = self._create_default_segments()

    def _create_default_segments(self) -> list[UserSegment]:
        """Create default user segments."""
        return [
            UserSegment(
                id="power_users",
                name="Power Users",
                description="Users with high activity",
                criteria={"total_events": {"gte": 100}, "unique_features_used": {"gte": 5}},
            ),
            UserSegment(
                id="new_users",
                name="New Users",
                description="Users active for less than 7 days",
                criteria={"days_active": {"lte": 7}},
            ),
            UserSegment(
                id="at_risk",
                name="At Risk Users",
                description="Users with declining activity",
                criteria={"avg_events_per_day": {"lte": 2}, "days_active": {"gte": 14}},
            ),
        ]

    async def track_event(
        self,
        event_type: EventType,
        user_id: str,
        session_id: str,
        properties: dict[str, Any] = None,
        metadata: dict[str, Any] = None,
    ) -> bool:
        """Track an analytics event."""
        event = AnalyticsEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            properties=properties or {},
            metadata=metadata or {},
        )

        success = await self.event_store.store_event(event)

        if success:
            # Update real-time metrics
            self.metrics.increment_counter("events_total", tags={"type": event_type.value})
            logger.debug(f"Tracked event: {event_type.value} for user {user_id}")

        return success

    async def get_user_insights(self, user_id: str) -> dict[str, Any]:
        """Get comprehensive user insights."""
        # User activity summary
        activity = await self.behavior_analyzer.get_user_activity_summary(user_id)

        # Check which segments user belongs to
        user_segments = await self.behavior_analyzer.get_user_segments(self.user_segments)
        user_segment_names = []
        for segment_name, user_list in user_segments.items():
            if user_id in user_list:
                user_segment_names.append(segment_name)

        return {
            "user_id": user_id,
            "activity_summary": activity,
            "segments": user_segment_names,
            "recommendations": self._generate_user_recommendations(activity, user_segment_names),
        }

    def _generate_user_recommendations(
        self, activity: dict[str, Any], segments: list[str]
    ) -> list[str]:
        """Generate personalized recommendations for user."""
        recommendations = []

        if "new_users" in segments:
            recommendations.append("Try uploading a document to enhance your chat experience")
            recommendations.append("Explore different AI providers to find your preferred style")

        if "at_risk" in segments:
            recommendations.append("Check out our new features to re-engage with the platform")
            recommendations.append("Consider setting up automated workflows")

        if activity["avg_session_duration"] < 300:  # Less than 5 minutes
            recommendations.append("Spend more time exploring advanced features")

        if not activity["top_features"]:
            recommendations.append("Try using file upload and chat export features")

        return recommendations

    async def create_ab_test(
        self,
        name: str,
        description: str,
        variants: list[dict[str, Any]],
        target_metric: str = "conversion_rate",
    ) -> str:
        """Create a new A/B test."""
        test_id = str(uuid.uuid4())

        test_variants = []
        for i, variant_config in enumerate(variants):
            variant = ABTestVariant(
                id=f"{test_id}_variant_{i}",
                name=variant_config["name"],
                description=variant_config["description"],
                weight=variant_config["weight"],
                config=variant_config.get("config", {}),
            )
            test_variants.append(variant)

        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            status=ABTestStatus.DRAFT,
            variants=test_variants,
            target_metric=target_metric,
        )

        if self.ab_test_manager.create_test(test):
            return test_id
        else:
            raise ValueError("Failed to create A/B test")

    async def get_analytics_summary(self) -> dict[str, Any]:
        """Get comprehensive analytics summary."""
        # Real-time metrics
        real_time = await self.dashboard.get_real_time_metrics()

        # Usage report
        usage_report = await self.dashboard.generate_usage_report(days=7)

        # User segments
        segments = await self.behavior_analyzer.get_user_segments(self.user_segments)
        segment_summary = {name: len(users) for name, users in segments.items()}

        # Retention analysis
        retention = await self.behavior_analyzer.calculate_retention_rates()

        return {
            "real_time_metrics": real_time,
            "usage_report": usage_report,
            "user_segments": segment_summary,
            "retention_analysis": retention,
            "active_ab_tests": len(
                [t for t in self.ab_test_manager.tests.values() if t.status == ABTestStatus.RUNNING]
            ),
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        # Configuration
        config = {"store_type": "memory", "db_path": "analytics.db"}  # or 'sqlite'

        # Initialize analytics manager
        analytics = AdvancedAnalyticsManager(config)

        # Simulate some events
        user_id = "user123"
        session_id = "session456"

        # Track various events
        await analytics.track_event(
            EventType.USER_LOGIN, user_id, session_id, properties={"login_method": "email"}
        )

        await analytics.track_event(
            EventType.CHAT_MESSAGE,
            user_id,
            session_id,
            properties={"provider": "openai", "feature": "basic_chat"},
        )

        await analytics.track_event(
            EventType.FILE_UPLOADED,
            user_id,
            session_id,
            properties={"file_type": "pdf", "file_size": 1024000},
        )

        # Get user insights
        await analytics.get_user_insights(user_id)

        # Create A/B test
        await analytics.create_ab_test(
            name="Chat Interface Test",
            description="Test different chat interfaces",
            variants=[
                {"name": "Control", "description": "Current interface", "weight": 0.5},
                {"name": "New Design", "description": "Updated interface", "weight": 0.5},
            ],
        )

        # Get analytics summary
        await analytics.get_analytics_summary()

    asyncio.run(main())
