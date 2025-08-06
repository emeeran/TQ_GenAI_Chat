"""Async chat service with performance optimizations"""

from typing import Any

from core.background_tasks import submit_background_task
from core.cache import CacheManager
from core.context import ContextManager
from core.performance import monitor_performance, perf_monitor
from core.providers.async_base import ChatMessage, ChatRequest
from core.providers.async_factory import AsyncProviderFactory
from core.validation import ChatRequestValidator


class AsyncChatService:
    """High-performance async service for handling chat operations"""

    def __init__(self):
        self.provider_factory = AsyncProviderFactory()
        self.context_manager = ContextManager()
        self.validator = ChatRequestValidator()
        self.cache_manager = CacheManager()

    @monitor_performance("chat_request")
    async def process_chat_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process chat request with caching and performance monitoring"""
        try:
            # Validate request
            validation_result = self.validator.validate(data)
            if not validation_result.is_valid:
                perf_monitor.increment_counter("chat_validation_error")
                return {"success": False, "error": f"Invalid request: {validation_result.errors}"}

            # Check cache first
            cache_key = self.cache_manager.get_cache_key_for_chat_request(data)
            cached_response = await self.cache_manager.get(cache_key)

            if cached_response:
                perf_monitor.increment_counter("chat_cache_hit")
                cached_response["cached"] = True
                return cached_response

            perf_monitor.increment_counter("chat_cache_miss")

            # Get provider
            provider_name = data.get("provider", "openai")
            provider = await self.provider_factory.get_provider(provider_name)
            if not provider:
                return {"success": False, "error": f"Provider {provider_name} not available"}

            # Build chat request
            messages = await self._build_messages(data)

            chat_request = ChatRequest(
                messages=messages,
                model=data.get("model", (await provider.get_models())[0]),
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens"),
                stream=data.get("stream", False),
            )

            # Process request
            response = await provider.chat_completion(chat_request)

            result = {
                "success": True,
                "content": response.content,
                "model": response.model,
                "provider": response.provider,
                "usage": response.usage,
                "response_time": response.response_time,
                "cached": False,
            }

            # Cache the response (async background task)
            await submit_background_task(
                "cache_response", self.cache_manager.set, cache_key, result
            )

            perf_monitor.increment_counter("chat_success")
            return result

        except Exception as e:
            perf_monitor.increment_counter("chat_error")
            return {"success": False, "error": str(e), "provider": data.get("provider", "unknown")}

    async def _build_messages(self, data: dict[str, Any]) -> list[ChatMessage]:
        """Build messages from request data with context injection"""
        messages = []

        # Add persona/system message
        if data.get("persona"):
            messages.append(ChatMessage(role="system", content=data["persona"]))

        # Add chat history
        for msg in data.get("history", []):
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))

        # Inject context if available (async)
        current_message = data.get("message", "")
        if current_message and self.context_manager.has_context():
            context = self.context_manager.get_relevant_context(current_message)
            if context:
                messages.append(ChatMessage(role="system", content=f"Context: {context}"))

        # Add current message
        if current_message:
            messages.append(ChatMessage(role="user", content=current_message))

        return messages

    async def get_available_providers(self) -> list[str]:
        """Get list of available providers"""
        return self.provider_factory.get_available_providers()

    async def get_models_for_provider(self, provider: str) -> list[str]:
        """Get models for specific provider"""
        return await self.provider_factory.get_models_for_provider(provider)

    async def get_provider_stats(self) -> dict[str, dict[str, float]]:
        """Get provider performance statistics"""
        return self.provider_factory.get_provider_stats()

    async def get_performance_metrics(self) -> dict[str, Any]:
        """Get service performance metrics"""
        return perf_monitor.get_all_metrics()
