"""
Query Result Caching System - Task 1.1.3
Implements Redis-based caching for document store queries with intelligent invalidation.
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Optional

from core.hybrid_cache import HybridCache

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache performance metrics"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    invalidations: int = 0
    errors: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with calculated metrics"""
        return {
            **asdict(self),
            "hit_rate": self.hit_rate,
            "total_requests": self.hits + self.misses,
        }


class QueryCache:
    """
    Specialized cache for document store queries with TTL and invalidation

    Features:
    - Multiple TTL policies for different query types
    - Tag-based cache invalidation
    - Performance metrics tracking
    - Automatic key generation from query parameters
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", default_ttl: int = 300):
        """
        Initialize query cache

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
        """
        self.hybrid_cache = HybridCache(
            memory_maxsize=1000,
            memory_ttl=60,  # Short memory TTL for frequent queries
            redis_url=redis_url,
            redis_ttl=default_ttl,
            disk_cache_dir="cache/queries",
            disk_ttl=3600,  # Longer disk TTL for persistence
        )

        # TTL policies for different query types
        self.ttl_policies = {
            "document_search": 300,  # 5 minutes
            "chat_history": 600,  # 10 minutes
            "document_stats": 1800,  # 30 minutes
            "user_documents": 900,  # 15 minutes
            "file_info": 1200,  # 20 minutes
        }

        # Track cache tags for invalidation
        self.cache_tags: dict[str, set[str]] = {}
        self.tag_keys: dict[str, set[str]] = {}

        # Performance metrics
        self.metrics = CacheMetrics()

        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the cache system"""
        try:
            await self.hybrid_cache.start()
            self._initialized = True
            logger.info("QueryCache initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize QueryCache: {e}")
            return False

    def _generate_cache_key(
        self, query_type: str, params: dict[str, Any], user_id: Optional[str] = None
    ) -> str:
        """
        Generate a unique cache key from query parameters

        Args:
            query_type: Type of query (search, stats, etc.)
            params: Query parameters
            user_id: Optional user ID for user-specific caching

        Returns:
            Unique cache key
        """
        # Create a deterministic key from parameters
        key_data = {"type": query_type, "params": params, "user_id": user_id}

        # Sort keys for consistency
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"query:{query_type}:{key_hash[:16]}"

    async def get(
        self, query_type: str, params: dict[str, Any], user_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached query result

        Args:
            query_type: Type of query
            params: Query parameters
            user_id: Optional user ID

        Returns:
            Cached result or None if not found
        """
        if not self._initialized:
            return None

        try:
            cache_key = self._generate_cache_key(query_type, params, user_id)
            result = await self.hybrid_cache.get(cache_key)

            if result is not None:
                self.metrics.hits += 1
                logger.debug(f"Cache hit for {query_type}: {cache_key}")
                return result
            else:
                self.metrics.misses += 1
                logger.debug(f"Cache miss for {query_type}: {cache_key}")
                return None

        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache get error for {query_type}: {e}")
            return None

    async def set(
        self,
        query_type: str,
        params: dict[str, Any],
        result: Any,
        user_id: Optional[str] = None,
        ttl: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """
        Set cached query result with optional tags

        Args:
            query_type: Type of query
            params: Query parameters
            result: Query result to cache
            user_id: Optional user ID
            ttl: Custom TTL (uses policy default if None)
            tags: Cache tags for invalidation

        Returns:
            True if successful
        """
        if not self._initialized:
            return False

        try:
            cache_key = self._generate_cache_key(query_type, params, user_id)

            # Use TTL from policy or custom value
            if ttl is None:
                ttl = self.ttl_policies.get(query_type, 300)

            # Set TTL for all cache layers
            self.hybrid_cache.redis_cache.ttl = ttl
            self.hybrid_cache.disk_cache.ttl = ttl

            await self.hybrid_cache.set(cache_key, result)

            # Track cache tags
            if tags:
                await self._add_cache_tags(cache_key, tags)

            self.metrics.sets += 1
            logger.debug(f"Cache set for {query_type}: {cache_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache set error for {query_type}: {e}")
            return False

    async def _add_cache_tags(self, cache_key: str, tags: list[str]) -> None:
        """Add cache key to tag groups"""
        for tag in tags:
            if tag not in self.tag_keys:
                self.tag_keys[tag] = set()
            self.tag_keys[tag].add(cache_key)

            if cache_key not in self.cache_tags:
                self.cache_tags[cache_key] = set()
            self.cache_tags[cache_key].add(tag)

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """
        Invalidate cache entries by tags

        Args:
            tags: List of tags to invalidate

        Returns:
            Number of entries invalidated
        """
        if not self._initialized:
            return 0

        invalidated_count = 0

        try:
            cache_keys_to_invalidate = set()

            # Collect all cache keys with any of the specified tags
            for tag in tags:
                if tag in self.tag_keys:
                    cache_keys_to_invalidate.update(self.tag_keys[tag])

            # Invalidate each key
            for cache_key in cache_keys_to_invalidate:
                await self.hybrid_cache.delete(cache_key)

                # Clean up tag mappings
                if cache_key in self.cache_tags:
                    for tag in self.cache_tags[cache_key]:
                        if tag in self.tag_keys:
                            self.tag_keys[tag].discard(cache_key)
                    del self.cache_tags[cache_key]

                invalidated_count += 1

            self.metrics.invalidations += invalidated_count
            logger.info(f"Invalidated {invalidated_count} cache entries for tags: {tags}")

        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache invalidation error: {e}")

        return invalidated_count

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern

        Args:
            pattern: Pattern to match (supports wildcards)

        Returns:
            Number of entries invalidated
        """
        # This would require Redis SCAN for pattern matching
        # For now, implement basic tag-based invalidation
        logger.warning(f"Pattern invalidation not implemented: {pattern}")
        return 0

    async def clear_all(self) -> bool:
        """Clear all cached queries"""
        try:
            await self.hybrid_cache.clear()
            self.cache_tags.clear()
            self.tag_keys.clear()
            logger.info("All query cache cleared")
            return True
        except Exception as e:
            self.metrics.errors += 1
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive cache metrics"""
        try:
            hybrid_stats = await self.hybrid_cache.get_stats()

            return {
                "query_cache": self.metrics.to_dict(),
                "hybrid_cache": hybrid_stats,
                "cache_tags": {
                    "total_tags": len(self.tag_keys),
                    "total_tagged_keys": len(self.cache_tags),
                },
                "ttl_policies": self.ttl_policies,
            }
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return {"query_cache": self.metrics.to_dict(), "error": str(e)}


# Cache invalidation helpers
class CacheInvalidator:
    """Helper class for cache invalidation strategies"""

    @staticmethod
    def document_tags(doc_id: str, doc_type: str, user_id: Optional[str] = None) -> list[str]:
        """Generate tags for document-related cache entries"""
        tags = ["documents", f"document:{doc_id}", f"doc_type:{doc_type}", "document_stats"]

        if user_id:
            tags.append(f"user:{user_id}")

        return tags

    @staticmethod
    def chat_tags(session_id: Optional[str] = None, user_id: Optional[str] = None) -> list[str]:
        """Generate tags for chat-related cache entries"""
        tags = ["chat_history"]

        if session_id:
            tags.append(f"session:{session_id}")

        if user_id:
            tags.append(f"user:{user_id}")

        return tags

    @staticmethod
    def user_tags(user_id: str) -> list[str]:
        """Generate tags for user-specific cache entries"""
        return [f"user:{user_id}", "user_data"]


# Global cache instance
_query_cache: Optional[QueryCache] = None


async def get_query_cache(redis_url: str = "redis://localhost:6379") -> QueryCache:
    """Get or create global query cache instance"""
    global _query_cache

    if _query_cache is None:
        _query_cache = QueryCache(redis_url=redis_url)
        await _query_cache.initialize()

    return _query_cache


# Convenience decorators for automatic caching
def cache_query(query_type: str, ttl: Optional[int] = None, tags_func: Optional[callable] = None):
    """
    Decorator for automatic query result caching

    Args:
        query_type: Type of query for cache key generation
        ttl: Custom TTL in seconds
        tags_func: Function to generate cache tags from function args
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = await get_query_cache()

            # Generate cache key from function arguments
            params = {"args": args, "kwargs": kwargs}

            # Try to get from cache first
            cached_result = await cache.get(query_type, params)
            if cached_result is not None:
                return cached_result

            # Call original function
            result = await func(*args, **kwargs)

            # Cache the result
            tags = None
            if tags_func:
                try:
                    tags = tags_func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Error generating cache tags: {e}")

            await cache.set(query_type, params, result, ttl=ttl, tags=tags)

            return result

        return wrapper

    return decorator
