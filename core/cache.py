"""Redis-based caching with fallback to memory"""

import hashlib
import json
import time
from typing import Any

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheManager:
    """High-performance caching with Redis and memory fallback"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: redis.Redis | None = None
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes default TTL
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection if available"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            except Exception:
                self.redis_client = None

    def _generate_cache_key(self, prefix: str, data: dict[str, Any]) -> str:
        """Generate consistent cache key from request data"""
        # Create deterministic hash from request data
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode(), usedforsecurity=False)  # nosec B324
        return f"{prefix}:{hash_obj.hexdigest()}"

    async def get(self, key: str) -> Any | None:
        """Get cached value"""
        try:
            if self.redis_client:
                # Try Redis first
                cached = await self.redis_client.get(key)
                if cached:
                    return json.loads(cached)

            # Fallback to memory cache
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                if time.time() < cache_entry["expires_at"]:
                    return cache_entry["data"]
                else:
                    # Clean expired entry
                    del self.memory_cache[key]

            return None

        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set cached value"""
        ttl = ttl or self.cache_ttl

        try:
            if self.redis_client:
                # Store in Redis
                await self.redis_client.setex(key, ttl, json.dumps(value))

            # Always store in memory cache as backup
            self.memory_cache[key] = {"data": value, "expires_at": time.time() + ttl}

            return True

        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)

            if key in self.memory_cache:
                del self.memory_cache[key]

            return True

        except Exception:
            return False

    async def clear_all(self) -> bool:
        """Clear all cached values"""
        try:
            if self.redis_client:
                await self.redis_client.flushdb()

            self.memory_cache.clear()
            return True

        except Exception:
            return False

    def get_cache_key_for_chat_request(self, request_data: dict[str, Any]) -> str:
        """Generate cache key for chat requests"""
        # Remove timestamp and other non-deterministic fields
        cache_data = {k: v for k, v in request_data.items() if k not in ["timestamp", "request_id"]}
        return self._generate_cache_key("chat", cache_data)

    async def cleanup_expired(self):
        """Clean up expired memory cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.memory_cache.items() if current_time >= entry["expires_at"]
        ]

        for key in expired_keys:
            del self.memory_cache[key]

        return len(expired_keys)
