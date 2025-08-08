# AI Models Configuration Utilities
from typing import Any

from .models import model_manager


def get_all_models() -> dict[str, list[str]]:
    """Get all models from the model manager"""
    return model_manager.get_all_models()


# Default models for each provider
DEFAULT_MODELS = {
    "cerebras": "llama-3.3-70b",
    "openai": "gpt-4o-mini",
    "groq": "deepseek-r1-distill-llama-70b",
    "anthropic": "claude-3-5-haiku-latest",
    "mistral": "mistral-large-latest",
    "xai": "grok-2-latest",
    "deepseek": "deepseek-chat",
    "cohere": "command-r",
    "gemini": "gemini-2.5-flash",
    "alibaba": "qwen3-235b-a22b-instruct",
    "openrouter": "google/gemini-2.5-pro-preview",
    "huggingface": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "moonshot": "moonshot-v1-32k",
}

# Fallback models in case default is not available
FALLBACK_MODELS = {
    "cerebras": "deepseek-r1-distill-llama-70b",
    "openai": "gpt-3.5-turbo",
    "groq": "mixtral-8x7b-32768",
    "anthropic": "claude-3-haiku-20240307",
    "mistral": "mistral-small-latest",
    "xai": "grok-beta",
    "deepseek": "deepseek-coder",
    "cohere": "command",
    "gemini": "gemini-2.5-flash-lite-preview",
    "alibaba": "qwen3-235b-a22b-instruct",
    "openrouter": "anthropic/claude-3.5-sonnet",
    "huggingface": "moonshotai/Kimi-K2-Instruct",
    "moonshot": "moonshot-v1-128k",
}

# API endpoints for providers
API_ENDPOINTS = {
    "cerebras": "https://api.cerebras.ai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "xai": "https://api.x.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "cohere": "https://api.cohere.ai/v1/generate",
    "gemini": "https://generativelanguage.googleapis.com/v1/models/",
    "alibaba": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "huggingface": "https://api-inference.huggingface.co/models/",
    "moonshot": "https://api.moonshot.ai/v1/chat/completions",
}


def get_models(provider: str) -> list[dict[str, Any]]:
    """
    Get all models for a provider

    Args:
        provider: The provider name (openai, groq, etc.)

    Returns:
        List of model configurations
    """
    models = model_manager.get_models(provider)
    return [{"id": model_id, "provider": provider} for model_id in models]


def get_default_model(provider: str) -> str:
    """
    Get the default model for a provider

    Args:
        provider: The provider name

    Returns:
        Default model ID
    """
    return DEFAULT_MODELS.get(provider, "")


def get_fallback_model(provider: str) -> str:
    """
    Get the fallback model for a provider

    Args:
        provider: The provider name

    Returns:
        Fallback model ID
    """
    return FALLBACK_MODELS.get(provider, "")


def get_model_info(provider: str, model_id: str) -> dict[str, Any] | None:
    """
    Get detailed information about a specific model

    Args:
        provider: The provider name
        model_id: The model identifier

    Returns:
        Model configuration or None if not found
    """
    if model_manager.is_model_available(provider, model_id):
        return {"id": model_id, "provider": provider}
    return None


def get_available_providers() -> list[str]:
    """
    Get list of all available providers

    Returns:
        List of provider names
    """
    return list(model_manager.get_all_models().keys())


def get_api_endpoint(provider: str) -> str:
    """
    Get the API endpoint URL for a provider

    Args:
        provider: The provider name

    Returns:
        API endpoint URL
    """
    return API_ENDPOINTS.get(provider, "")
