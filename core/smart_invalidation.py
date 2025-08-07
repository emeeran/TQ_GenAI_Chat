"""
Smart Cache Invalidation System

This module provides intelligent cache invalidation strategies for the TQ GenAI Chat
application, including version-based, tag-based, time-based, and event-based invalidation
with cascade capabilities.

Key Features:
- Version-based cache invalidation with content versioning
- Tag-based cache grouping for efficient bulk invalidation
- Time-based and event-based invalidation triggers
- Cascade invalidation for related data dependencies
- Comprehensive invalidation logging and analytics
- Event-driven invalidation with publish/subscribe patterns

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Union

# Internal imports
from core.hybrid_cache import HybridCache


class InvalidationType(Enum):
    """Types of cache invalidation"""

    VERSION = "version"  # Content version changed
    TAG = "tag"  # Tag-based group invalidation
    TIME = "time"  # Time-based expiration
    EVENT = "event"  # Event-triggered invalidation
    CASCADE = "cascade"  # Cascade from related data
    MANUAL = "manual"  # Manual invalidation
    DEPENDENCY = "dependency"  # Dependency chain invalidation


@dataclass
class InvalidationEvent:
    """Represents a cache invalidation event"""

    event_id: str
    event_type: InvalidationType
    timestamp: datetime = field(default_factory=datetime.now)
    cache_keys: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    cascade_level: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "cache_keys": self.cache_keys,
            "tags": self.tags,
            "reason": self.reason,
            "metadata": self.metadata,
            "cascade_level": self.cascade_level,
        }


@dataclass
class CacheEntry:
    """Enhanced cache entry with invalidation metadata"""

    key: str
    value: Any
    version: str = ""
    tags: set[str] = field(default_factory=set)
    dependencies: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None

    def is_expired(self) -> bool:
        """Check if entry is expired based on TTL"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl


class SmartCacheInvalidator:
    """
    Advanced cache invalidation system with multiple strategies

    Provides intelligent cache invalidation with:
    - Version-based invalidation for content changes
    - Tag-based grouping for bulk operations
    - Time-based automatic expiration
    - Event-driven invalidation
    - Dependency cascade invalidation
    - Comprehensive logging and analytics
    """

    def __init__(self, cache: HybridCache, logger: Optional[logging.Logger] = None):
        self.cache = cache
        self.logger = logger or logging.getLogger(__name__)

        # Invalidation tracking
        self.invalidation_events: list[InvalidationEvent] = []
        self.max_event_history = 1000

        # Tag mappings: tag -> set of cache keys
        self.tag_mappings: dict[str, set[str]] = defaultdict(set)

        # Dependency mappings: key -> set of dependent keys
        self.dependency_mappings: dict[str, set[str]] = defaultdict(set)

        # Version tracking: key -> version hash
        self.version_mappings: dict[str, str] = {}

        # Event subscribers: event_type -> list of callback functions
        self.event_subscribers: dict[str, list[Callable]] = defaultdict(list)

        # Invalidation statistics
        self.stats = {
            "total_invalidations": 0,
            "invalidations_by_type": defaultdict(int),
            "cascaded_invalidations": 0,
            "last_cleanup": datetime.now(),
        }

        # Configuration
        self.config = {
            "max_cascade_depth": 5,
            "event_history_retention_hours": 24,
            "cleanup_interval_minutes": 60,
            "enable_dependency_tracking": True,
            "enable_cascade_invalidation": True,
        }

        self.logger.info("SmartCacheInvalidator initialized")

    async def set_with_metadata(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[list[str]] = None,
        dependencies: Optional[list[str]] = None,
        version: Optional[str] = None,
    ) -> bool:
        """
        Set cache entry with invalidation metadata

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: List of tags for grouping
            dependencies: List of dependency keys
            version: Version identifier for content

        Returns:
            True if successfully cached
        """
        try:
            # Generate version if not provided
            if version is None:
                version = self._generate_version(value)

            # Set in underlying cache
            success = await self.cache.set(key, value, ttl=ttl)

            if success:
                # Update metadata mappings
                await self._update_metadata(key, tags or [], dependencies or [], version)

                self.logger.debug(
                    f"Cached with metadata: {key}, tags: {tags}, deps: {dependencies}"
                )

            return success

        except Exception as e:
            self.logger.error(f"Error setting cache with metadata: {e}")
            return False

    async def invalidate_by_version(
        self, key: str, new_version: str, reason: str = "Version update"
    ) -> bool:
        """
        Invalidate cache entry if version differs

        Args:
            key: Cache key to check
            new_version: New version to compare
            reason: Reason for invalidation

        Returns:
            True if invalidated, False if version matches or key not found
        """
        try:
            current_version = self.version_mappings.get(key)

            if current_version and current_version != new_version:
                event = InvalidationEvent(
                    event_id=self._generate_event_id(),
                    event_type=InvalidationType.VERSION,
                    cache_keys=[key],
                    reason=reason,
                    metadata={"old_version": current_version, "new_version": new_version},
                )

                return await self._execute_invalidation(event)

            return False

        except Exception as e:
            self.logger.error(f"Error in version invalidation: {e}")
            return False

    async def invalidate_by_tags(
        self, tags: Union[str, list[str]], reason: str = "Tag-based invalidation"
    ) -> int:
        """
        Invalidate all cache entries with specified tags

        Args:
            tags: Tag or list of tags to invalidate
            reason: Reason for invalidation

        Returns:
            Number of entries invalidated
        """
        try:
            if isinstance(tags, str):
                tags = [tags]

            # Collect all keys with these tags
            keys_to_invalidate = set()
            for tag in tags:
                keys_to_invalidate.update(self.tag_mappings.get(tag, set()))

            if not keys_to_invalidate:
                return 0

            event = InvalidationEvent(
                event_id=self._generate_event_id(),
                event_type=InvalidationType.TAG,
                cache_keys=list(keys_to_invalidate),
                tags=tags,
                reason=reason,
            )

            success = await self._execute_invalidation(event)
            return len(keys_to_invalidate) if success else 0

        except Exception as e:
            self.logger.error(f"Error in tag invalidation: {e}")
            return 0

    async def invalidate_by_pattern(
        self, pattern: str, reason: str = "Pattern-based invalidation"
    ) -> int:
        """
        Invalidate cache entries matching a pattern

        Args:
            pattern: Key pattern (supports wildcards)
            reason: Reason for invalidation

        Returns:
            Number of entries invalidated
        """
        try:
            # Get all cache keys and filter by pattern
            all_keys = await self._get_all_cache_keys()
            matching_keys = self._filter_keys_by_pattern(all_keys, pattern)

            if not matching_keys:
                return 0

            event = InvalidationEvent(
                event_id=self._generate_event_id(),
                event_type=InvalidationType.MANUAL,
                cache_keys=matching_keys,
                reason=reason,
                metadata={"pattern": pattern},
            )

            success = await self._execute_invalidation(event)
            return len(matching_keys) if success else 0

        except Exception as e:
            self.logger.error(f"Error in pattern invalidation: {e}")
            return 0

    async def invalidate_with_cascade(
        self, key: str, reason: str = "Cascade invalidation", max_depth: Optional[int] = None
    ) -> list[str]:
        """
        Invalidate a key and cascade to all dependent keys

        Args:
            key: Root key to invalidate
            reason: Reason for invalidation
            max_depth: Maximum cascade depth

        Returns:
            List of all invalidated keys
        """
        try:
            max_depth = max_depth or self.config["max_cascade_depth"]
            invalidated_keys = []

            # Perform cascade invalidation
            await self._cascade_invalidate(key, reason, invalidated_keys, 0, max_depth)

            return invalidated_keys

        except Exception as e:
            self.logger.error(f"Error in cascade invalidation: {e}")
            return []

    async def schedule_invalidation(
        self, key: str, delay_seconds: int, reason: str = "Scheduled invalidation"
    ) -> str:
        """
        Schedule future invalidation of a cache key

        Args:
            key: Cache key to invalidate
            delay_seconds: Delay before invalidation
            reason: Reason for invalidation

        Returns:
            Event ID for the scheduled invalidation
        """
        try:
            event_id = self._generate_event_id()

            # Schedule the invalidation
            asyncio.create_task(self._delayed_invalidation(key, delay_seconds, reason, event_id))

            self.logger.info(f"Scheduled invalidation for {key} in {delay_seconds}s")
            return event_id

        except Exception as e:
            self.logger.error(f"Error scheduling invalidation: {e}")
            return ""

    def subscribe_to_events(
        self,
        event_type: Union[InvalidationType, str],
        callback: Callable[[InvalidationEvent], None],
    ) -> bool:
        """
        Subscribe to invalidation events

        Args:
            event_type: Type of events to subscribe to
            callback: Function to call when event occurs

        Returns:
            True if successfully subscribed
        """
        try:
            event_key = event_type.value if isinstance(event_type, InvalidationType) else event_type
            self.event_subscribers[event_key].append(callback)

            self.logger.debug(f"Subscribed to {event_key} events")
            return True

        except Exception as e:
            self.logger.error(f"Error subscribing to events: {e}")
            return False

    async def get_invalidation_stats(self) -> dict[str, Any]:
        """Get comprehensive invalidation statistics"""
        try:
            # Recent events analysis
            recent_events = [
                e
                for e in self.invalidation_events
                if (datetime.now() - e.timestamp).total_seconds() < 3600  # Last hour
            ]

            return {
                "total_invalidations": self.stats["total_invalidations"],
                "invalidations_by_type": dict(self.stats["invalidations_by_type"]),
                "cascaded_invalidations": self.stats["cascaded_invalidations"],
                "recent_events_count": len(recent_events),
                "event_history_size": len(self.invalidation_events),
                "tag_mappings_count": len(self.tag_mappings),
                "dependency_mappings_count": len(self.dependency_mappings),
                "version_mappings_count": len(self.version_mappings),
                "subscribers_count": sum(len(subs) for subs in self.event_subscribers.values()),
                "last_cleanup": self.stats["last_cleanup"].isoformat(),
                "config": self.config.copy(),
            }

        except Exception as e:
            self.logger.error(f"Error getting invalidation stats: {e}")
            return {}

    async def cleanup_expired_metadata(self) -> int:
        """Clean up expired metadata and old events"""
        try:
            cleaned_count = 0

            # Clean up old events
            cutoff_time = datetime.now() - timedelta(
                hours=self.config["event_history_retention_hours"]
            )

            original_count = len(self.invalidation_events)
            self.invalidation_events = [
                e for e in self.invalidation_events if e.timestamp > cutoff_time
            ]
            cleaned_count += original_count - len(self.invalidation_events)

            # Clean up orphaned tag mappings
            all_cache_keys = set(await self._get_all_cache_keys())
            for tag, keys in list(self.tag_mappings.items()):
                valid_keys = keys.intersection(all_cache_keys)
                if valid_keys:
                    self.tag_mappings[tag] = valid_keys
                else:
                    del self.tag_mappings[tag]
                    cleaned_count += 1

            # Clean up orphaned dependency mappings
            for key in list(self.dependency_mappings.keys()):
                if key not in all_cache_keys:
                    del self.dependency_mappings[key]
                    cleaned_count += 1

            # Clean up orphaned version mappings
            for key in list(self.version_mappings.keys()):
                if key not in all_cache_keys:
                    del self.version_mappings[key]
                    cleaned_count += 1

            self.stats["last_cleanup"] = datetime.now()

            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} expired metadata entries")

            return cleaned_count

        except Exception as e:
            self.logger.error(f"Error cleaning up metadata: {e}")
            return 0

    # Private helper methods

    async def _execute_invalidation(self, event: InvalidationEvent) -> bool:
        """Execute an invalidation event"""
        try:
            invalidated_count = 0

            # Invalidate each key
            for key in event.cache_keys:
                success = await self.cache.delete(key)
                if success:
                    invalidated_count += 1
                    await self._remove_key_metadata(key)

            # Update statistics
            self.stats["total_invalidations"] += invalidated_count
            self.stats["invalidations_by_type"][event.event_type.value] += invalidated_count

            if event.cascade_level > 0:
                self.stats["cascaded_invalidations"] += invalidated_count

            # Record event
            self.invalidation_events.append(event)

            # Trim event history if needed
            if len(self.invalidation_events) > self.max_event_history:
                self.invalidation_events = self.invalidation_events[-self.max_event_history :]

            # Notify subscribers
            await self._notify_subscribers(event)

            self.logger.info(
                f"Invalidation executed: {event.event_type.value}, "
                f"keys: {invalidated_count}/{len(event.cache_keys)}, "
                f"reason: {event.reason}"
            )

            return invalidated_count > 0

        except Exception as e:
            self.logger.error(f"Error executing invalidation: {e}")
            return False

    async def _cascade_invalidate(
        self, key: str, reason: str, invalidated_keys: list[str], current_depth: int, max_depth: int
    ):
        """Recursively invalidate dependent keys"""
        if current_depth >= max_depth:
            return

        if key in invalidated_keys:
            return  # Already invalidated

        # Invalidate the current key
        success = await self.cache.delete(key)
        if success:
            invalidated_keys.append(key)

            # Create invalidation event
            event = InvalidationEvent(
                event_id=self._generate_event_id(),
                event_type=InvalidationType.CASCADE,
                cache_keys=[key],
                reason=reason,
                cascade_level=current_depth,
            )

            # Record the event
            self.invalidation_events.append(event)
            await self._notify_subscribers(event)

            # Find and invalidate dependent keys
            dependent_keys = self.dependency_mappings.get(key, set())
            for dep_key in dependent_keys:
                await self._cascade_invalidate(
                    dep_key, reason, invalidated_keys, current_depth + 1, max_depth
                )

            # Clean up metadata
            await self._remove_key_metadata(key)

    async def _delayed_invalidation(self, key: str, delay_seconds: int, reason: str, event_id: str):
        """Execute delayed invalidation"""
        try:
            await asyncio.sleep(delay_seconds)

            event = InvalidationEvent(
                event_id=event_id,
                event_type=InvalidationType.TIME,
                cache_keys=[key],
                reason=reason,
                metadata={"delay_seconds": delay_seconds},
            )

            await self._execute_invalidation(event)

        except asyncio.CancelledError:
            self.logger.info(f"Scheduled invalidation cancelled for {key}")
        except Exception as e:
            self.logger.error(f"Error in delayed invalidation: {e}")

    async def _update_metadata(
        self, key: str, tags: list[str], dependencies: list[str], version: str
    ):
        """Update metadata mappings for a cache key"""
        # Update tag mappings
        for tag in tags:
            self.tag_mappings[tag].add(key)

        # Update dependency mappings
        if dependencies:
            self.dependency_mappings[key] = set(dependencies)

        # Update version mapping
        if version:
            self.version_mappings[key] = version

    async def _remove_key_metadata(self, key: str):
        """Remove all metadata for a cache key"""
        # Remove from tag mappings
        for tag, keys in self.tag_mappings.items():
            keys.discard(key)

        # Remove from dependency mappings
        self.dependency_mappings.pop(key, None)

        # Remove from version mappings
        self.version_mappings.pop(key, None)

    async def _notify_subscribers(self, event: InvalidationEvent):
        """Notify event subscribers"""
        try:
            # Notify type-specific subscribers
            subscribers = self.event_subscribers.get(event.event_type.value, [])

            # Notify general subscribers
            subscribers.extend(self.event_subscribers.get("all", []))

            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    self.logger.warning(f"Error in event subscriber callback: {e}")

        except Exception as e:
            self.logger.error(f"Error notifying subscribers: {e}")

    def _generate_version(self, value: Any) -> str:
        """Generate version hash for a value"""
        try:
            # Create a hash of the value
            content = json.dumps(value, sort_keys=True, default=str)
            return hashlib.sha256(content.encode()).hexdigest()[:16]
        except Exception:
            # Fallback to timestamp-based version
            return str(int(time.time() * 1000))

    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return f"inv_{int(time.time() * 1000)}_{hash(time.time()) % 1000000:06d}"

    async def _get_all_cache_keys(self) -> list[str]:
        """Get all cache keys from the underlying cache"""
        try:
            # This would need to be implemented based on the HybridCache interface
            # For now, return empty list as placeholder
            return []
        except Exception:
            return []

    def _filter_keys_by_pattern(self, keys: list[str], pattern: str) -> list[str]:
        """Filter keys by pattern (simple wildcard support)"""
        import fnmatch

        return [key for key in keys if fnmatch.fnmatch(key, pattern)]


# Export main components
__all__ = ["SmartCacheInvalidator", "InvalidationType", "InvalidationEvent", "CacheEntry"]
