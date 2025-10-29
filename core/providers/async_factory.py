"""Async provider factory with connection pooling"""

from core.cache import CacheManager

from .async_base import AsyncAIProviderInterface
from .async_openai_provider import AsyncOpenAIProvider
from .async_moonshot_provider import AsyncMoonshotProvider


class AsyncProviderFactory:
    """Factory for creating and managing async AI providers"""

    def __init__(self):
        self._providers: dict[str, AsyncAIProviderInterface] = {}
        self._provider_pool: dict[str, list[AsyncAIProviderInterface]] = {}
        self.cache_manager = CacheManager()
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available providers"""
        available_providers = [
            AsyncOpenAIProvider(),
            AsyncMoonshotProvider(),
        ]

        for provider in available_providers:
            if provider.is_available():
                self._providers[provider.name] = provider
                # Create provider pool for connection reuse
                self._provider_pool[provider.name] = [provider]

    async def get_provider(self, name: str) -> AsyncAIProviderInterface | None:
        """Get provider by name with connection pooling"""
        if name not in self._providers:
            return None

        # Return provider from pool if available
        if name in self._provider_pool and self._provider_pool[name]:
            provider = self._provider_pool[name][0]
            async with provider:
                return provider

        return self._providers[name]

    def get_available_providers(self) -> list[str]:
        """Get list of available provider names"""
        return list(self._providers.keys())

    async def get_models_for_provider(self, provider_name: str) -> list[str]:
        """Get models for specific provider"""
        provider = await self.get_provider(provider_name)
        if provider:
            return await provider.get_models()
        return []

    async def get_all_models(self) -> dict[str, list[str]]:
        """Get all models grouped by provider"""
        result = {}
        for name in self._providers.keys():
            models = await self.get_models_for_provider(name)
            if models:
                result[name] = models
        return result

    def get_provider_stats(self) -> dict[str, dict[str, float]]:
        """Get performance statistics for all providers"""
        stats = {}
        for name, provider in self._providers.items():
            stats[name] = {
                "average_response_time": provider.average_response_time,
                "request_count": provider._request_count,
            }
        return stats
