"""Provider factory for managing AI providers"""

from .anthropic_provider import AnthropicProvider
from .base import AIProviderInterface
from .openai_provider import OpenAIProvider
from .perplexity_provider import PerplexityProvider


class ProviderFactory:
    """Factory for creating and managing AI providers"""

    def __init__(self):
        self._providers = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available providers"""
        providers = [
            OpenAIProvider(),
            AnthropicProvider(),
            PerplexityProvider(),
        ]

        for provider in providers:
            if provider.is_available():
                self._providers[provider.name] = provider

    def get_provider(self, name: str) -> AIProviderInterface | None:
        """Get provider by name"""
        return self._providers.get(name)

    def get_available_providers(self) -> list[str]:
        """Get list of available provider names"""
        return list(self._providers.keys())

    def get_models_for_provider(self, provider_name: str) -> list[str]:
        """Get models for specific provider"""
        provider = self.get_provider(provider_name)
        return provider.get_models() if provider else []

    def get_all_models(self) -> dict[str, list[str]]:
        """Get all models grouped by provider"""
        return {name: provider.get_models() for name, provider in self._providers.items()}
