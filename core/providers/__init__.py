"""AI Provider module initialization"""
from .anthropic_provider import AnthropicProvider
from .base import AIProviderInterface, ChatMessage, ChatRequest, ChatResponse
from .factory import ProviderFactory
from .openai_provider import OpenAIProvider

# Import the provider manager from the main providers module
try:
    # Import from the parent core directory
    import sys
    from pathlib import Path

    # Get the core directory path
    core_dir = Path(__file__).parent.parent
    providers_file = core_dir / 'providers.py'

    if providers_file.exists():
        # Import the provider_manager from core.providers module
        import importlib.util
        spec = importlib.util.spec_from_file_location("core.providers", providers_file)
        providers_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(providers_module)
        provider_manager = providers_module.provider_manager
    else:
        raise ImportError("providers.py not found")

except ImportError:
    # Fallback: create a minimal provider manager for compatibility
    class MinimalProviderManager:
        def is_provider_available(self, provider: str) -> bool:
            return provider in ['openai', 'groq', 'anthropic', 'gemini', 'mistral', 'cohere', 'xai', 'deepseek', 'alibaba', 'openrouter', 'huggingface', 'moonshot', 'perplexity']

        def list_providers(self) -> list[str]:
            return ['openai', 'groq', 'anthropic', 'gemini', 'mistral', 'cohere', 'xai', 'deepseek', 'alibaba', 'openrouter', 'huggingface', 'moonshot', 'perplexity']

        def get_provider(self, provider: str):
            return None

    provider_manager = MinimalProviderManager()

__all__ = [
    "AIProviderInterface",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage",
    "ProviderFactory",
    "OpenAIProvider",
    "AnthropicProvider",
    "provider_manager"
]
