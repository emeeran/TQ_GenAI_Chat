"""
Model Configuration Module

Centralized model definitions and caching for all AI providers.
"""

import json
import logging
from pathlib import Path

# Default model configurations
DEFAULT_MODELS = {
    "cerebras": [
        "llama-3.3-70b",
        "deepseek-r1-distill-llama-70b",
        "gpt-oss-120b",
        "llama-4-maverick-17b-128e-instruct",
        "llama-4-scout-17b-16e-instruct",
        "llama3.1-8b",
        "qwen-3-235b-a22b-instruct-2507",
        "qwen-3-235b-a22b-thinking-2507",
        "qwen-3-32b",
        "qwen-3-coder-480b",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4.1",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4o-realtime-preview",
        "gpt-4o-audio-preview",
    ],
    "gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite-preview",
        "gemini-2.5-flash-native-audio",
        "gemini-2.5-flash-preview-tts",
        "gemini-2.5-pro-preview-tts",
        "gemini-2.0-flash",
        "gemini-2.0-flash-preview-image-generation",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ],
    "anthropic": [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768",
        "mistral-saba-24b",
        "qwen/qwen3-32b",
        "moonshotai/kimi-k2-instruct",
    ],
    "mistral": [
        "mistral-large-latest",
        "mistral-saba-24b",
        "codestral-latest",
        "mistral-small-latest",
        "pixtral-large-latest",
    ],
    "xai": ["grok-4", "grok-4-latest", "grok-3", "grok-3-mini"],
    "deepseek": ["deepseek-r1-distill-llama-70b", "deepseek-chat", "deepseek-reasoner"],
    "cohere": [
        "command-a-03-2025",
        "command-r7b-12-2024",
        "command-r-plus",
        "command-r",
        "command",
        "command-light",
    ],
    "alibaba": [
        "qwen3-32b",
        "qwen-2.5-72b-instruct",
        "qwen-2.5-32b-instruct",
        "qwen-2.5-14b-instruct",
        "qwen-2.5-7b-instruct",
        "qwen-2.5-coder-32b-instruct",
        "qwen-2.5-math-72b-instruct",
    ],
    "openrouter": [
        "kimi-k2-0711-preview",
        "kimi-latest",
        "kimi-thinking-preview",
        "moonshot-v1-128k",
        "moonshot-v1-128k-vision-preview",
        "moonshot-v1-32k",
        "moonshot-v1-32k-vision-preview",
        "moonshot-v1-8k",
        "moonshot-v1-8k-vision-preview",
        "moonshot-v1-auto",
        "google/gemini-2.5-pro-preview",
        "openai/gpt-4o",
        "moonshotai/kimi-k2-instruct",
        "meta-llama/llama-3.3-70b-versatile",
        "qwen/qwen3-32b",
    ],
    "huggingface": ["Qwen/Qwen3-Coder-480B-A35B-Instruct"],
    "moonshot": [
        "kimi-k2-0711-preview",
        "kimi-latest",
        "kimi-thinking-preview",
        "moonshot-v1-128k",
        "moonshot-v1-128k-vision-preview",
        "moonshot-v1-32k",
        "moonshot-v1-32k-vision-preview",
        "moonshot-v1-8k",
        "moonshot-v1-8k-vision-preview",
        "moonshot-v1-auto",
    ],
    "perplexity": ["sonar-small", "sonar-medium", "sonar-large", "sonar-pro"],
}


class ModelManager:
    """Manages model configurations and caching"""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path(__file__).parent.parent
        self.models_cache_file = self.cache_dir / "models_cache.json"
        self.defaults_cache_file = self.cache_dir / "defaults_cache.json"
        self.models = DEFAULT_MODELS.copy()
        self.defaults = {}
        self.load_cached_models()
        self.load_defaults_cache()

    def load_cached_models(self):
        """Load cached models and defaults"""
        try:
            # Load models cache
            if self.models_cache_file.exists():
                with open(self.models_cache_file) as f:
                    models_cache = json.load(f)

                for provider, data in models_cache.items():
                    if provider in self.models and "models" in data:
                        self.models[provider] = data["models"]
                        logging.getLogger(__name__).info(
                            f"Loaded {len(data['models'])} cached models for {provider}"
                        )

        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load cached models: {str(e)}")

    def save_models_cache(self, provider: str, models: list[str]):
        """Save models to cache"""
        try:
            cache_data = {}
            if self.models_cache_file.exists():
                with open(self.models_cache_file) as f:
                    cache_data = json.load(f)

            cache_data[provider] = {"models": models}

            with open(self.models_cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            # Update in-memory cache
            self.models[provider] = models

        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to save models cache: {str(e)}")

    def get_models(self, provider: str) -> list[str]:
        """Get models for a provider"""
        return self.models.get(provider, [])

    def update_models(self, provider: str, models: list[str]):
        """Update models for a provider"""
        self.models[provider] = models
        self.save_models_cache(provider, models)

    def get_all_models(self) -> dict[str, list[str]]:
        """Get all models"""
        return self.models.copy()

    def is_model_available(self, provider: str, model: str) -> bool:
        """Check if a model is available for a provider"""
        return model in self.models.get(provider, [])

    def load_defaults_cache(self):
        """Load cached default models"""
        try:
            if self.defaults_cache_file.exists():
                with open(self.defaults_cache_file) as f:
                    self.defaults = json.load(f)
            else:
                self.defaults = {}
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load defaults cache: {str(e)}")
            self.defaults = {}

    def save_defaults_cache(self):
        """Save default models to cache"""
        try:
            with open(self.defaults_cache_file, "w") as f:
                json.dump(self.defaults, f, indent=2)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to save defaults cache: {str(e)}")

    def set_default_model(self, provider: str, model: str):
        """Set default model for a provider"""
        if not hasattr(self, "defaults"):
            self.load_defaults_cache()

        if not self.is_model_available(provider, model):
            raise ValueError(f"Model {model} not available for provider {provider}")

        self.defaults[provider] = model
        self.save_defaults_cache()

    def get_default_model(self, provider: str) -> str | None:
        """Get default model for a provider"""
        if not hasattr(self, "defaults"):
            self.load_defaults_cache()

        return self.defaults.get(provider)


# Global model manager instance
model_manager = ModelManager()
