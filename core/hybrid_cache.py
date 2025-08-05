"""
Multi-tier hybrid caching system with Memory, Redis, and Disk layers.
"""

import asyncio
import hashlib
import json
import logging
import pickle
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self._lock = asyncio.Lock()

    async def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        async with self._lock:
            if key not in self.cache:
                return False

            if self._is_expired(key):
                self._remove(key)
                return False

            return True

    async def get(self, key: str, default: Any = None) -> Any:
        """Get item from cache."""
        async with self._lock:
            if key not in self.cache:
                return default

            if self._is_expired(key):
                self._remove(key)
                return default

            value = self.cache[key]
            self.cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any) -> None:
        """Add item to cache."""
        async with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            self.timestamps[key] = time.time()

            if len(self.cache) > self.maxsize:
                oldest = next(iter(self.cache))
                self._remove(oldest)

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired."""
        timestamp = self.timestamps.get(key, 0)
        return time.time() - timestamp > self.ttl

    def _remove(self, key: str) -> None:
        """Remove item from cache."""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)

    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            self.cache.clear()
            self.timestamps.clear()

    async def stats(self) -> dict:
        """Get cache statistics."""
        async with self._lock:
            expired_count = sum(1 for key in self.cache if self._is_expired(key))
            return {
                "size": len(self.cache),
                "max_size": self.maxsize,
                "expired_items": expired_count,
                "ttl": self.ttl,
            }


class RedisCache:
    """Redis-based cache layer."""

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 3600):
        self.redis_url = redis_url
        self.ttl = ttl
        self.redis_client = None
        self._lock = asyncio.Lock()

    async def connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, skipping Redis cache")
            return False

        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis cache")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False

    async def get(self, key: str) -> Any:
        """Get item from Redis cache."""
        if not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(f"cache:{key}")
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
        return None

    async def set(self, key: str, value: Any) -> None:
        """Set item in Redis cache."""
        if not self.redis_client:
            return

        try:
            serialized_value = json.dumps(value, default=str)
            await self.redis_client.setex(f"cache:{key}", self.ttl, serialized_value)
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete item from Redis cache."""
        if not self.redis_client:
            return

        try:
            await self.redis_client.delete(f"cache:{key}")
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")

    async def clear(self) -> None:
        """Clear all cache items."""
        if not self.redis_client:
            return

        try:
            keys = await self.redis_client.keys("cache:*")
            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


class DiskCache:
    """Disk-based cache layer."""

    def __init__(self, cache_dir: str = "cache", ttl: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    async def get(self, key: str) -> Any:
        """Get item from disk cache."""
        cache_path = self._get_cache_path(key)

        async with self._lock:
            if not cache_path.exists():
                return None

            try:
                # Check if file is expired
                if time.time() - cache_path.stat().st_mtime > self.ttl:
                    cache_path.unlink()
                    return None

                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Disk cache get error: {e}")
                return None

    async def set(self, key: str, value: Any) -> None:
        """Set item in disk cache."""
        cache_path = self._get_cache_path(key)

        async with self._lock:
            try:
                with open(cache_path, "wb") as f:
                    pickle.dump(value, f)
            except Exception as e:
                logger.warning(f"Disk cache set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete item from disk cache."""
        cache_path = self._get_cache_path(key)

        async with self._lock:
            try:
                if cache_path.exists():
                    cache_path.unlink()
            except Exception as e:
                logger.warning(f"Disk cache delete error: {e}")

    async def clear(self) -> None:
        """Clear all cache items."""
        async with self._lock:
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
            except Exception as e:
                logger.warning(f"Disk cache clear error: {e}")

    async def cleanup_expired(self) -> int:
        """Remove expired cache files."""
        removed_count = 0
        current_time = time.time()

        async with self._lock:
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    if current_time - cache_file.stat().st_mtime > self.ttl:
                        cache_file.unlink()
                        removed_count += 1
            except Exception as e:
                logger.warning(f"Disk cache cleanup error: {e}")

        return removed_count


class HybridCache:
    """
    Multi-tier caching system with Memory (L1), Redis (L2), and Disk (L3) layers.
    """

    def __init__(
        self,
        memory_maxsize: int = 1000,
        memory_ttl: int = 300,
        redis_url: str = "redis://localhost:6379",
        redis_ttl: int = 3600,
        disk_cache_dir: str = "cache",
        disk_ttl: int = 86400,
    ):
        self.memory_cache = LRUCache(maxsize=memory_maxsize, ttl=memory_ttl)
        self.redis_cache = RedisCache(redis_url=redis_url, ttl=redis_ttl)
        self.disk_cache = DiskCache(cache_dir=disk_cache_dir, ttl=disk_ttl)
        self.stats = {"hits": {"memory": 0, "redis": 0, "disk": 0}, "misses": 0, "sets": 0}

    async def start(self):
        """Initialize cache layers."""
        await self.redis_cache.connect()
        logger.info("Hybrid cache system initialized")

    async def get(self, key: str) -> Any:
        """Get item from cache with L1 -> L2 -> L3 fallback."""

        # L1: Memory cache (fastest)
        if await key in self.memory_cache:
            value = await self.memory_cache.get(key)
            if value is not None:
                self.stats["hits"]["memory"] += 1
                return value

        # L2: Redis cache (fast)
        value = await self.redis_cache.get(key)
        if value is not None:
            self.stats["hits"]["redis"] += 1
            # Populate L1 cache
            await self.memory_cache.set(key, value)
            return value

        # L3: Disk cache (fallback)
        value = await self.disk_cache.get(key)
        if value is not None:
            self.stats["hits"]["disk"] += 1
            # Populate L1 and L2 caches
            await self.memory_cache.set(key, value)
            await self.redis_cache.set(key, value)
            return value

        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any) -> None:
        """Set item in all cache layers."""
        self.stats["sets"] += 1

        # Set in all layers
        await asyncio.gather(
            self.memory_cache.set(key, value),
            self.redis_cache.set(key, value),
            self.disk_cache.set(key, value),
            return_exceptions=True,
        )

    async def delete(self, key: str) -> None:
        """Delete item from all cache layers."""
        await asyncio.gather(
            self.memory_cache.clear(),  # Remove from memory
            self.redis_cache.delete(key),
            self.disk_cache.delete(key),
            return_exceptions=True,
        )

    async def clear(self) -> None:
        """Clear all cache layers."""
        await asyncio.gather(
            self.memory_cache.clear(),
            self.redis_cache.clear(),
            self.disk_cache.clear(),
            return_exceptions=True,
        )

    async def get_stats(self) -> dict:
        """Get comprehensive cache statistics."""
        memory_stats = await self.memory_cache.stats()

        total_hits = sum(self.stats["hits"].values())
        total_requests = total_hits + self.stats["misses"]
        hit_ratio = total_hits / total_requests if total_requests > 0 else 0

        return {
            "requests": {
                "total": total_requests,
                "hits": total_hits,
                "misses": self.stats["misses"],
                "hit_ratio": hit_ratio,
            },
            "layer_hits": self.stats["hits"],
            "memory_cache": memory_stats,
            "sets": self.stats["sets"],
        }

    async def cleanup(self) -> dict:
        """Cleanup expired items and return statistics."""
        disk_removed = await self.disk_cache.cleanup_expired()
        return {"disk_items_removed": disk_removed}

    async def close(self):
        """Close all cache connections."""
        await self.redis_cache.close()


# Global cache instance
_hybrid_cache = None


async def get_cache() -> HybridCache:
    """Get or create global cache instance."""
    global _hybrid_cache
    if _hybrid_cache is None:
        _hybrid_cache = HybridCache()
        await _hybrid_cache.start()
    return _hybrid_cache


async def cleanup_cache():
    """Cleanup global cache instance."""
    global _hybrid_cache
    if _hybrid_cache:
        await _hybrid_cache.close()
        _hybrid_cache = None
