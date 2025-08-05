"""Provider factory for managing AI providers"""
from typing import Dict, List, Optional
from .base import AIProviderInterface
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


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
        ]
        
        for provider in providers:
            if provider.is_available():
                self._providers[provider.name] = provider
    
    def get_provider(self, name: str) -> Optional[AIProviderInterface]:
        """Get provider by name"""
        return self._providers.get(name)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self._providers.keys())
    
    def get_models_for_provider(self, provider_name: str) -> List[str]:
        """Get models for specific provider"""
        provider = self.get_provider(provider_name)
        return provider.get_models() if provider else []
    
    def get_all_models(self) -> Dict[str, List[str]]:
        """Get all models grouped by provider"""
        return {
            name: provider.get_models() 
            for name, provider in self._providers.items()
        }
