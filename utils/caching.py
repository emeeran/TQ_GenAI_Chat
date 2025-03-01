from collections import OrderedDict
from typing import Any, Optional
import time

class LRUCache:
    """Thread-safe LRU cache with TTL support"""

    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        if key not in self.cache:
            return False

        if self._is_expired(key):
            self._remove(key)
            return False

        return True

    def get(self, key: str, default: Any = None) -> Any:
        """Get item from cache"""
        if key not in self:
            return default

        value = self.cache[key]
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """Add item to cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        self.timestamps[key] = time.time()

        if len(self.cache) > self.maxsize:
            oldest = next(iter(self.cache))
            self._remove(oldest)

    def _is_expired(self, key: str) -> bool:
        """Check if key is expired"""
        timestamp = self.timestamps.get(key, 0)
        return time.time() - timestamp > self.ttl

    def _remove(self, key: str) -> None:
        """Remove item from cache"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)

    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        self.timestamps.clear()
