# AI Models Configuration Utilities
from typing import Dict, Any, Optional, List

from ai_models import (
    OPENAI_MODELS, GROQ_MODELS, ANTHROPIC_MODELS, MISTRAL_MODELS, 
    XAI_MODELS, DEEPSEEK_MODELS, COHERE_MODELS
)

# Consolidated model lookup structure
ALL_MODELS = {
    'openai': OPENAI_MODELS,
    'groq': GROQ_MODELS,
    'anthropic': ANTHROPIC_MODELS,
    'mistral': MISTRAL_MODELS,
    'xai': XAI_MODELS,
    'deepseek': DEEPSEEK_MODELS,
    'cohere': COHERE_MODELS
}

# Default models for each provider
DEFAULT_MODELS = {
    'openai': 'gpt-4o-mini',
    'groq': 'deepseek-r1-distill-llama-70b',
    'anthropic': 'claude-3-5-haiku-latest',
    'mistral': 'mistral-large-latest',
    'xai': 'grok-2-latest',
    'deepseek': 'deepseek-chat',
    'cohere': 'command-r'
}

# Fallback models in case default is not available
FALLBACK_MODELS = {
    'openai': 'gpt-3.5-turbo',
    'groq': 'mixtral-8x7b-32768',
    'anthropic': 'claude-3-haiku-20240307',
    'mistral': 'mistral-small-latest',
    'xai': 'grok-beta',
    'deepseek': 'deepseek-coder',
    'cohere': 'command'
}

# API endpoints for providers
API_ENDPOINTS = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'groq': 'https://api.groq.com/openai/v1/chat/completions',
    'anthropic': 'https://api.anthropic.com/v1/messages',
    'mistral': 'https://api.mistral.ai/v1/chat/completions',
    'xai': 'https://api.x.ai/v1/chat/completions',
    'deepseek': 'https://api.deepseek.com/v1/chat/completions',
    'cohere': 'https://api.cohere.ai/v1/generate'
}

def get_models(provider: str) -> List[Dict[str, Any]]:
    """
    Get all models for a provider
    
    Args:
        provider: The provider name (openai, groq, etc.)
        
    Returns:
        List of model configurations
    """
    models_dict = ALL_MODELS.get(provider, {})
    return [
        {"id": model_id, **model_info} 
        for model_id, model_info in models_dict.items()
    ]

def get_default_model(provider: str) -> str:
    """
    Get the default model for a provider
    
    Args:
        provider: The provider name
        
    Returns:
        Default model ID
    """
    return DEFAULT_MODELS.get(provider, '')

def get_fallback_model(provider: str) -> str:
    """
    Get the fallback model for a provider
    
    Args:
        provider: The provider name
        
    Returns:
        Fallback model ID
    """
    return FALLBACK_MODELS.get(provider, '')

def get_model_info(provider: str, model_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific model
    
    Args:
        provider: The provider name
        model_id: The model identifier
        
    Returns:
        Model configuration or None if not found
    """
    provider_models = ALL_MODELS.get(provider, {})
    if model_id in provider_models:
        return {
            "id": model_id,
            "provider": provider,
            **provider_models[model_id]
        }
    return None

def get_available_providers() -> List[str]:
    """
    Get list of all available providers
    
    Returns:
        List of provider names
    """
    return list(ALL_MODELS.keys())

def get_api_endpoint(provider: str) -> str:
    """
    Get the API endpoint URL for a provider
    
    Args:
        provider: The provider name
        
    Returns:
        API endpoint URL
    """
    return API_ENDPOINTS.get(provider, '')
