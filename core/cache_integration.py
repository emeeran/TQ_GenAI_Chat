"""
Enhanced Cache Integration for TQ GenAI Chat
Implements intelligent caching for chat responses, model metadata, and personas
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, Optional, Union

# Flask imports (conditional)
try:
    from flask import jsonify, request

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    request = None
    jsonify = None

from core.hybrid_cache import HybridCache, get_cache
from core.smart_invalidation import InvalidationType, SmartCacheInvalidator

logger = logging.getLogger(__name__)


class ChatCacheManager:
    """
    Manages intelligent caching of chat responses, model data, and personas
    with sophisticated key generation and invalidation strategies
    """

    def __init__(self, cache: HybridCache = None):
        self.cache = cache
        self.invalidator = None
        self._initialized = False
        self.stats = {"requests": 0, "sets": 0, "layer_hits": {"memory": 0, "redis": 0, "disk": 0}}

    async def initialize(self):
        """Initialize the cache manager"""
        if not self._initialized:
            if self.cache is None:
                self.cache = await get_cache()

            # Initialize smart invalidation
            self.invalidator = SmartCacheInvalidator(self.cache)

            self._initialized = True
            logger.info("ChatCacheManager initialized with smart invalidation")

    async def _ensure_initialized(self):
        """Ensure the cache manager is initialized"""
        if not self._initialized:
            await self.initialize()

    def _generate_chat_key(
        self, message: str, provider: str, model: str, persona: str = None, context: str = None
    ) -> str:
        """
        Generate a cache key for chat responses
        Includes message, provider, model, persona, and context for proper scoping
        """
        key_components = [
            message.strip().lower(),
            provider,
            model,
            persona or "default",
            context or "",
        ]

        # Create a hash of the components for efficient key generation
        key_string = "|".join(key_components)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"chat:response:{key_hash}"

    def _generate_model_key(self, provider: str, model_type: str = "available") -> str:
        """Generate cache key for model metadata"""
        return f"models:{provider}:{model_type}"

    def _generate_persona_key(self, persona_name: str = None) -> str:
        """Generate cache key for persona content"""
        if persona_name:
            return f"persona:{persona_name}"
        return "persona:all"

    def _generate_context_key(self, query: str, search_type: str = "document") -> str:
        """Generate cache key for context search results"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"context:{search_type}:{query_hash}"

    async def get_chat_response(
        self, message: str, provider: str, model: str, persona: str = None, context: str = None
    ) -> Optional[dict]:
        """
        Get cached chat response if available

        Returns:
            Cached response dict or None if not found
        """
        await self._ensure_initialized()

        try:
            cache_key = self._generate_chat_key(message, provider, model, persona, context)
            cached_response = await self.cache.get(cache_key)

            if cached_response:
                logger.debug(f"Cache HIT for chat response: {cache_key[:32]}...")
                # Add cache metadata
                cached_response["_cached"] = True
                cached_response["_cache_key"] = cache_key
                return cached_response
            else:
                logger.debug(f"Cache MISS for chat response: {cache_key[:32]}...")
                return None

        except Exception as e:
            logger.error(f"Error retrieving chat response from cache: {e}")
            return None

    async def set_chat_response(
        self,
        message: str,
        provider: str,
        model: str,
        response: dict,
        persona: str = None,
        context: str = None,
        ttl_override: int = None,
    ) -> bool:
        """
        Cache a chat response

        Args:
            message: The input message
            provider: AI provider name
            model: Model name
            response: Response dict to cache
            persona: Persona name (optional)
            context: Context content (optional)
            ttl_override: Custom TTL in seconds (optional)

        Returns:
            True if successfully cached, False otherwise
        """
        await self._ensure_initialized()

        try:
            cache_key = self._generate_chat_key(message, provider, model, persona, context)

            # Create cacheable response (remove non-serializable elements)
            cacheable_response = self._sanitize_response_for_cache(response.copy())

            await self.cache.set(cache_key, cacheable_response)
            logger.debug(f"Cached chat response: {cache_key[:32]}...")
            return True

        except Exception as e:
            logger.error(f"Error caching chat response: {e}")
            return False

    async def get_model_list(self, provider: str) -> Optional[list[str]]:
        """Get cached model list for provider"""
        await self._ensure_initialized()

        try:
            cache_key = self._generate_model_key(provider, "available")
            cached_models = await self.cache.get(cache_key)

            if cached_models:
                logger.debug(f"Cache HIT for models: {provider}")
                return cached_models
            else:
                logger.debug(f"Cache MISS for models: {provider}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving models from cache: {e}")
            return None

    async def set_model_list(self, provider: str, models: list[str]) -> bool:
        """Cache model list for provider"""
        await self._ensure_initialized()

        try:
            cache_key = self._generate_model_key(provider, "available")
            await self.cache.set(cache_key, models)
            logger.debug(f"Cached models for provider: {provider}")
            return True

        except Exception as e:
            logger.error(f"Error caching models: {e}")
            return False

    async def get_persona(self, persona_name: str = None) -> Optional[Union[dict, list]]:
        """Get cached persona(s)"""
        await self._ensure_initialized()

        try:
            cache_key = self._generate_persona_key(persona_name)
            cached_persona = await self.cache.get(cache_key)

            if cached_persona:
                logger.debug(f"Cache HIT for persona: {persona_name or 'all'}")
                return cached_persona
            else:
                logger.debug(f"Cache MISS for persona: {persona_name or 'all'}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving persona from cache: {e}")
            return None

    async def get_models(self, provider: str) -> Optional[list[str]]:
        """
        Get cached models for a provider

        Args:
            provider: AI provider name (e.g., 'openai', 'anthropic')

        Returns:
            List of model names or None if not cached
        """
        await self._ensure_initialized()

        try:
            cache_key = f"models_{provider}"
            cached_models = await self.cache.get(cache_key)

            if cached_models:
                logger.debug(f"Cache HIT for models: {provider}")
                self.stats["layer_hits"]["memory"] += 1
                self.stats["requests"] += 1
                return cached_models

            logger.debug(f"Cache MISS for models: {provider}")
            self.stats["requests"] += 1
            return None
        except Exception as e:
            logger.error(f"Error retrieving models from cache: {e}")
            return None

    async def cache_models(self, provider: str, models: list[str]) -> bool:
        """
        Cache models for a provider

        Args:
            provider: AI provider name
            models: List of model names to cache

        Returns:
            True if cached successfully
        """
        await self._ensure_initialized()

        try:
            cache_key = f"models_{provider}"
            ttl = self.cache_ttl["models"]  # 24 hours

            success = await self.cache.set(cache_key, models, ttl=ttl)

            if success:
                logger.debug(f"Cached models for {provider}: {len(models)} models")
                self.stats["sets"] += 1
                return True
            return False
        except Exception as e:
            logger.error(f"Error caching models for {provider}: {e}")
            return False

    async def set_persona(self, persona_data: Union[dict, list], persona_name: str = None) -> bool:
        """Cache persona data"""
        await self._ensure_initialized()

        try:
            cache_key = self._generate_persona_key(persona_name)
            await self.cache.set(cache_key, persona_data)
            logger.debug(f"Cached persona: {persona_name or 'all'}")
            return True

        except Exception as e:
            logger.error(f"Error caching persona: {e}")
            return False

    async def get_context_search(self, query: str, search_type: str = "document") -> Optional[dict]:
        """Get cached context search results"""
        await self._ensure_initialized()

        try:
            cache_key = self._generate_context_key(query, search_type)
            cached_results = await self.cache.get(cache_key)

            if cached_results:
                logger.debug(f"Cache HIT for context search: {query[:50]}...")
                return cached_results
            else:
                logger.debug(f"Cache MISS for context search: {query[:50]}...")
                return None

        except Exception as e:
            logger.error(f"Error retrieving context search from cache: {e}")
            return None

    async def set_context_search(
        self, query: str, results: dict, search_type: str = "document"
    ) -> bool:
        """Cache context search results"""
        await self._ensure_initialized()

        try:
            cache_key = self._generate_context_key(query, search_type)
            await self.cache.set(cache_key, results)
            logger.debug(f"Cached context search: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error caching context search: {e}")
            return False

    async def invalidate_chat_responses(self, provider: str = None, model: str = None):
        """Invalidate cached chat responses (selective or all)"""
        await self._ensure_initialized()

        try:
            # For now, we'll clear all chat responses
            # In a production system, we'd implement pattern-based deletion
            await self._invalidate_pattern("chat:response:*")
            logger.info(f"Invalidated chat responses for provider: {provider}, model: {model}")

        except Exception as e:
            logger.error(f"Error invalidating chat responses: {e}")

    async def invalidate_models(self, provider: str = None):
        """Invalidate cached model data"""
        await self._ensure_initialized()

        try:
            if provider:
                cache_key = self._generate_model_key(provider, "available")
                await self.cache.delete(cache_key)
            else:
                await self._invalidate_pattern("models:*")

            logger.info(f"Invalidated models for provider: {provider or 'all'}")

        except Exception as e:
            logger.error(f"Error invalidating models: {e}")

    async def invalidate_personas(self):
        """Invalidate all cached personas"""
        await self._ensure_initialized()

        try:
            await self._invalidate_pattern("persona:*")
            logger.info("Invalidated all cached personas")

        except Exception as e:
            logger.error(f"Error invalidating personas: {e}")

    async def _invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern (simplified implementation)"""
        # In a full implementation, this would use Redis pattern matching
        # For now, we'll clear the entire cache as a safe fallback
        await self.cache.clear()
        logger.debug(f"Cleared cache for pattern: {pattern}")

    def _sanitize_response_for_cache(self, response: dict) -> dict:
        """Remove non-serializable elements from response for caching"""
        # Remove any file objects, functions, or other non-serializable items
        sanitized = {}

        for key, value in response.items():
            if key.startswith("_"):
                # Skip private/internal fields
                continue

            try:
                # Test if value is JSON serializable
                json.dumps(value, default=str)
                sanitized[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable values
                logger.debug(f"Skipping non-serializable field: {key}")
                continue

        return sanitized

    async def get_cache_stats(self) -> dict:
        """Get detailed cache statistics"""
        await self._ensure_initialized()

        try:
            stats = await self.cache.get_stats()
            return {"cache_manager": "ChatCacheManager", "initialized": self._initialized, **stats}
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "cache_manager": "ChatCacheManager",
                "initialized": self._initialized,
                "error": str(e),
            }

    # Smart Invalidation Methods

    async def invalidate_by_version(
        self, key: str, new_version: str, reason: str = "Version update"
    ) -> bool:
        """Invalidate cache entry if version differs"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.invalidate_by_version(key, new_version, reason)
        return False

    async def invalidate_by_tags(
        self, tags: Union[str, list[str]], reason: str = "Tag-based invalidation"
    ) -> int:
        """Invalidate all cache entries with specified tags"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.invalidate_by_tags(tags, reason)
        return 0

    async def invalidate_by_pattern(
        self, pattern: str, reason: str = "Pattern-based invalidation"
    ) -> int:
        """Invalidate cache entries matching a pattern"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.invalidate_by_pattern(pattern, reason)
        return 0

    async def invalidate_with_cascade(
        self, key: str, reason: str = "Cascade invalidation"
    ) -> list[str]:
        """Invalidate a key and cascade to all dependent keys"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.invalidate_with_cascade(key, reason)
        return []

    async def schedule_invalidation(
        self, key: str, delay_seconds: int, reason: str = "Scheduled invalidation"
    ) -> str:
        """Schedule future invalidation of a cache key"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.schedule_invalidation(key, delay_seconds, reason)
        return ""

    async def set_with_metadata(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[list[str]] = None,
        dependencies: Optional[list[str]] = None,
        version: Optional[str] = None,
    ) -> bool:
        """Set cache entry with invalidation metadata"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.set_with_metadata(
                key, value, ttl, tags, dependencies, version
            )

        # Fallback to regular cache set
        return await self.cache.set(key, value, ttl=ttl)

    async def get_invalidation_stats(self) -> dict[str, Any]:
        """Get comprehensive invalidation statistics"""
        await self._ensure_initialized()

        if self.invalidator:
            return await self.invalidator.get_invalidation_stats()
        return {}

    def subscribe_to_invalidation_events(
        self, event_type: Union[InvalidationType, str], callback: Callable[[Any], None]
    ) -> bool:
        """Subscribe to invalidation events"""
        if self.invalidator:
            return self.invalidator.subscribe_to_events(event_type, callback)
        return False


# Decorators for automatic caching


def cache_chat_response(ttl: int = 300):
    """
    Decorator to automatically cache chat responses

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(message: str, provider: str, model: str, **kwargs):
            cache_manager = ChatCacheManager()
            await cache_manager.initialize()

            # Try to get from cache
            persona = kwargs.get("persona")
            context = kwargs.get("context")

            cached_response = await cache_manager.get_chat_response(
                message, provider, model, persona, context
            )

            if cached_response:
                return cached_response

            # If not cached, execute function
            if asyncio.iscoroutinefunction(func):
                response = await func(message, provider, model, **kwargs)
            else:
                response = func(message, provider, model, **kwargs)

            # Cache the response
            if response and isinstance(response, dict):
                await cache_manager.set_chat_response(
                    message, provider, model, response, persona, context
                )

            return response

        return wrapper

    return decorator


def cache_model_list(ttl: int = 3600):
    """
    Decorator to automatically cache model lists

    Args:
        ttl: Time to live in seconds (default: 1 hour)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(provider: str, **kwargs):
            cache_manager = ChatCacheManager()
            await cache_manager.initialize()

            # Try to get from cache
            cached_models = await cache_manager.get_model_list(provider)
            if cached_models:
                return cached_models

            # If not cached, execute function
            if asyncio.iscoroutinefunction(func):
                models = await func(provider, **kwargs)
            else:
                models = func(provider, **kwargs)

            # Cache the models
            if models and isinstance(models, list):
                await cache_manager.set_model_list(provider, models)

            return models

        return wrapper

    return decorator


def cache_persona_content(ttl: int = 1800):
    """
    Decorator to automatically cache persona content

    Args:
        ttl: Time to live in seconds (default: 30 minutes)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(persona_name: str = None, **kwargs):
            cache_manager = ChatCacheManager()
            await cache_manager.initialize()

            # Try to get from cache
            cached_persona = await cache_manager.get_persona(persona_name)
            if cached_persona:
                return cached_persona

            # If not cached, execute function
            if asyncio.iscoroutinefunction(func):
                persona_data = await func(persona_name, **kwargs)
            else:
                persona_data = func(persona_name, **kwargs)

            # Cache the persona data
            if persona_data:
                await cache_manager.set_persona(persona_data, persona_name)

            return persona_data

        return wrapper

    return decorator


# Global cache manager instance
_cache_manager: Optional[ChatCacheManager] = None


async def get_cache_manager() -> ChatCacheManager:
    """Get or create global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = ChatCacheManager()
        await _cache_manager.initialize()
    return _cache_manager


async def cleanup_cache_manager():
    """Cleanup global cache manager instance"""
    global _cache_manager
    if _cache_manager and _cache_manager.cache:
        await _cache_manager.cache.close()
    _cache_manager = None


# Flask Endpoints for Smart Cache Invalidation Management


def register_cache_invalidation_endpoints(app):
    """Register smart cache invalidation endpoints with Flask app"""

    if not FLASK_AVAILABLE:
        logger.warning("Flask not available. Cannot register cache invalidation endpoints.")
        return

    @app.route("/cache/invalidate/version", methods=["POST"])
    async def invalidate_by_version():
        """Invalidate cache entry by version"""
        try:
            data = request.get_json()
            key = data.get("key")
            new_version = data.get("version")
            reason = data.get("reason", "Version update via API")

            if not key or not new_version:
                return jsonify({"error": "key and version are required"}), 400

            cache_manager = await get_cache_manager()
            result = await cache_manager.invalidate_by_version(key, new_version, reason)

            return jsonify(
                {
                    "success": True,
                    "invalidated": result,
                    "message": f"Version invalidation completed for key: {key}",
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cache/invalidate/tags", methods=["POST"])
    async def invalidate_by_tags():
        """Invalidate cache entries by tags"""
        try:
            data = request.get_json()
            tags = data.get("tags")
            reason = data.get("reason", "Tag-based invalidation via API")

            if not tags:
                return jsonify({"error": "tags are required"}), 400

            cache_manager = await get_cache_manager()
            count = await cache_manager.invalidate_by_tags(tags, reason)

            return jsonify(
                {
                    "success": True,
                    "invalidated_count": count,
                    "message": f"Tag invalidation completed for tags: {tags}",
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cache/invalidate/pattern", methods=["POST"])
    async def invalidate_by_pattern():
        """Invalidate cache entries by pattern"""
        try:
            data = request.get_json()
            pattern = data.get("pattern")
            reason = data.get("reason", "Pattern-based invalidation via API")

            if not pattern:
                return jsonify({"error": "pattern is required"}), 400

            cache_manager = await get_cache_manager()
            count = await cache_manager.invalidate_by_pattern(pattern, reason)

            return jsonify(
                {
                    "success": True,
                    "invalidated_count": count,
                    "message": f"Pattern invalidation completed for pattern: {pattern}",
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cache/invalidate/cascade", methods=["POST"])
    async def invalidate_with_cascade():
        """Invalidate cache entry with cascade"""
        try:
            data = request.get_json()
            key = data.get("key")
            reason = data.get("reason", "Cascade invalidation via API")

            if not key:
                return jsonify({"error": "key is required"}), 400

            cache_manager = await get_cache_manager()
            invalidated_keys = await cache_manager.invalidate_with_cascade(key, reason)

            return jsonify(
                {
                    "success": True,
                    "invalidated_keys": invalidated_keys,
                    "message": f"Cascade invalidation completed for key: {key}",
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cache/invalidate/schedule", methods=["POST"])
    async def schedule_invalidation():
        """Schedule future cache invalidation"""
        try:
            data = request.get_json()
            key = data.get("key")
            delay_seconds = data.get("delay_seconds")
            reason = data.get("reason", "Scheduled invalidation via API")

            if not key or delay_seconds is None:
                return jsonify({"error": "key and delay_seconds are required"}), 400

            cache_manager = await get_cache_manager()
            task_id = await cache_manager.schedule_invalidation(key, delay_seconds, reason)

            return jsonify(
                {
                    "success": True,
                    "task_id": task_id,
                    "message": f"Scheduled invalidation for key: {key} in {delay_seconds} seconds",
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cache/invalidate/stats", methods=["GET"])
    async def get_invalidation_stats():
        """Get comprehensive invalidation statistics"""
        try:
            cache_manager = await get_cache_manager()
            stats = await cache_manager.get_invalidation_stats()

            return jsonify({"success": True, "stats": stats})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/cache/set_with_metadata", methods=["POST"])
    async def set_with_metadata():
        """Set cache entry with invalidation metadata"""
        try:
            data = request.get_json()
            key = data.get("key")
            value = data.get("value")
            ttl = data.get("ttl")
            tags = data.get("tags")
            dependencies = data.get("dependencies")
            version = data.get("version")

            if not key or value is None:
                return jsonify({"error": "key and value are required"}), 400

            cache_manager = await get_cache_manager()
            result = await cache_manager.set_with_metadata(
                key, value, ttl, tags, dependencies, version
            )

            return jsonify(
                {
                    "success": True,
                    "result": result,
                    "message": f"Cache entry set with metadata for key: {key}",
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500
