"""
Centralized configuration management for TQ GenAI Chat.

This module consolidates all configuration from app.py, config/models.py, and ai_models.py
into a single, well-organized configuration management system.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""

    endpoint: str
    api_key: str
    default_model: str
    fallback_model: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit: int | None = None
    custom_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ModelCapabilities:
    """Model capability information."""

    context_window: int
    max_output_tokens: int
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = True
    supports_system_messages: bool = True


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    name: str
    display_name: str
    provider: str
    capabilities: ModelCapabilities
    cost_per_token: float | None = None
    deprecated: bool = False
    description: str | None = None
    specialization: str | None = None


@dataclass
class AppConfig:
    """General application configuration."""

    debug: bool = False
    secret_key: str = "dev-key-change-in-production"
    max_content_length: int = 64 * 1024 * 1024  # 64MB
    upload_folder: str = "uploads"
    max_files: int = 10
    json_sort_keys: bool = False
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class CacheConfig:
    """Caching configuration."""

    enabled: bool = True
    default_ttl: int = 300  # 5 minutes
    max_size: int = 1000
    redis_url: str | None = None
    file_cache_dir: str = "cache"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str | None = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class ConfigManager:
    """
    Centralized configuration manager.

    This class consolidates all configuration from various sources and provides
    a single interface for accessing application settings.
    """

    def __init__(self, env_file: str | None = None):
        """
        Initialize configuration manager.

        Args:
            env_file: Optional path to environment file
        """
        if env_file:
            from dotenv import load_dotenv

            load_dotenv(env_file)

        self._providers: dict[str, ProviderConfig] = {}
        self._models: dict[str, ModelConfig] = {}
        self._app_config: AppConfig | None = None
        self._cache_config: CacheConfig | None = None
        self._logging_config: LoggingConfig | None = None

        self._load_configurations()

    def _load_configurations(self) -> None:
        """Load all configurations from environment and defaults."""
        self._load_provider_configs()
        self._load_model_configs()
        self._load_app_config()
        self._load_cache_config()
        self._load_logging_config()

    def _load_provider_configs(self) -> None:
        """Load provider configurations."""
        # OpenAI
        self._providers["openai"] = ProviderConfig(
            endpoint="https://api.openai.com/v1/chat/completions",
            api_key=os.getenv("OPENAI_API_KEY", ""),
            default_model="gpt-4o-mini",
            fallback_model="gpt-3.5-turbo",
            rate_limit=60,  # requests per minute
        )

        # Anthropic
        self._providers["anthropic"] = ProviderConfig(
            endpoint="https://api.anthropic.com/v1/messages",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            default_model="claude-3-5-sonnet-latest",
            fallback_model="claude-3-sonnet-20240229",
            custom_headers={"anthropic-version": "2023-06-01"},
        )

        # Groq
        self._providers["groq"] = ProviderConfig(
            endpoint="https://api.groq.com/openai/v1/chat/completions",
            api_key=os.getenv("GROQ_API_KEY", ""),
            default_model="deepseek-r1-distill-llama-70b",
            fallback_model="mixtral-8x7b-32768",
        )

        # Mistral
        self._providers["mistral"] = ProviderConfig(
            endpoint="https://api.mistral.ai/v1/chat/completions",
            api_key=os.getenv("MISTRAL_API_KEY", ""),
            default_model="codestral-latest",
            fallback_model="mistral-small-latest",
        )

        # XAI (Grok)
        self._providers["xai"] = ProviderConfig(
            endpoint="https://api.x.ai/v1/chat/completions",
            api_key=os.getenv("XAI_API_KEY", ""),
            default_model="grok-2-latest",
            fallback_model="grok-2",
        )

        # DeepSeek
        self._providers["deepseek"] = ProviderConfig(
            endpoint="https://api.deepseek.com/v1/chat/completions",
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            default_model="deepseek-chat",
            fallback_model="deepseek-chat",
        )

        # Gemini
        self._providers["gemini"] = ProviderConfig(
            endpoint="https://generativelanguage.googleapis.com/v1/models/",
            api_key=os.getenv("GEMINI_API_KEY", ""),
            default_model="gemini-1.5-flash",
            fallback_model="gemini-1.5-flash",
        )

        # Cohere
        self._providers["cohere"] = ProviderConfig(
            endpoint="https://api.cohere.com/v2/chat",
            api_key=os.getenv("COHERE_API_KEY", ""),
            default_model="command-r-plus-08-2024",
            fallback_model="command-r-08-2024",
        )

        # Alibaba (Qwen)
        self._providers["alibaba"] = ProviderConfig(
            endpoint="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            api_key=os.getenv("DASHSCOPE_API_KEY", ""),
            default_model="qwen-plus",
            fallback_model="qwen-turbo",
        )

        # OpenRouter
        self._providers["openrouter"] = ProviderConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            default_model="moonshot/moonshot-v1-32k",
            fallback_model="moonshot/moonshot-v1-8k",
        )

        # Hugging Face
        self._providers["huggingface"] = ProviderConfig(
            endpoint="https://api-inference.huggingface.co/models/",
            api_key=os.getenv("HF_API_KEY", ""),
            default_model="meta-llama/Llama-2-70b-chat-hf",
            fallback_model="microsoft/DialoGPT-large",
        )

        # Moonshot
        self._providers["moonshot"] = ProviderConfig(
            endpoint="https://api.moonshot.ai/v1/chat/completions",
            api_key=os.getenv("MOONSHOT_API_KEY", ""),
            default_model="moonshot-v1-32k",
            fallback_model="moonshot-v1-128k",
        )

    def _load_model_configs(self) -> None:
        """Load model configurations."""
        # OpenAI Models
        openai_models = {
            "gpt-4o": ModelConfig(
                name="gpt-4o",
                display_name="GPT-4o",
                provider="openai",
                capabilities=ModelCapabilities(
                    context_window=128000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "gpt-4.1": ModelConfig(
                name="gpt-4.1",
                display_name="GPT-4.1",
                provider="openai",
                capabilities=ModelCapabilities(
                    context_window=128000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "gpt-4o-mini": ModelConfig(
                name="gpt-4o-mini",
                display_name="GPT-4o Mini",
                provider="openai",
                capabilities=ModelCapabilities(
                    context_window=128000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "gpt-3.5-turbo": ModelConfig(
                name="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                provider="openai",
                capabilities=ModelCapabilities(
                    context_window=16000,
                    max_output_tokens=4096,
                    supports_vision=False,
                    supports_function_calling=True,
                ),
            ),
            "gpt-4-turbo": ModelConfig(
                name="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider="openai",
                capabilities=ModelCapabilities(
                    context_window=128000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
        }

        # Anthropic Models
        anthropic_models = {
            "claude-3-opus": ModelConfig(
                name="claude-3-opus",
                display_name="Claude 3 Opus",
                provider="anthropic",
                capabilities=ModelCapabilities(
                    context_window=200000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "claude-3-sonnet": ModelConfig(
                name="claude-3-sonnet",
                display_name="Claude 3 Sonnet",
                provider="anthropic",
                capabilities=ModelCapabilities(
                    context_window=200000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "claude-3-haiku": ModelConfig(
                name="claude-3-haiku",
                display_name="Claude 3 Haiku",
                provider="anthropic",
                capabilities=ModelCapabilities(
                    context_window=200000,
                    max_output_tokens=4096,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "claude-3-5-sonnet": ModelConfig(
                name="claude-3-5-sonnet",
                display_name="Claude 3.5 Sonnet",
                provider="anthropic",
                capabilities=ModelCapabilities(
                    context_window=200000,
                    max_output_tokens=8192,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
            "claude-3-5-haiku": ModelConfig(
                name="claude-3-5-haiku",
                display_name="Claude 3.5 Haiku",
                provider="anthropic",
                capabilities=ModelCapabilities(
                    context_window=200000,
                    max_output_tokens=8192,
                    supports_vision=True,
                    supports_function_calling=True,
                ),
            ),
        }

        # Groq Models
        groq_models = {
            "deepseek-r1-distill-llama-70b": ModelConfig(
                name="deepseek-r1-distill-llama-70b",
                display_name="DeepSeek R1 Distill Llama 70B",
                provider="groq",
                capabilities=ModelCapabilities(context_window=128000, max_output_tokens=32768),
            ),
            "mixtral-8x7b-32768": ModelConfig(
                name="mixtral-8x7b-32768",
                display_name="Mixtral 8x7B",
                provider="groq",
                capabilities=ModelCapabilities(context_window=32768, max_output_tokens=32768),
            ),
            "llama-3-70b": ModelConfig(
                name="llama-3-70b",
                display_name="Llama 3 70B",
                provider="groq",
                capabilities=ModelCapabilities(context_window=128000, max_output_tokens=32768),
            ),
        }

        # Mistral Models
        mistral_models = {
            "codestral-latest": ModelConfig(
                name="codestral-latest",
                display_name="Codestral Latest",
                provider="mistral",
                capabilities=ModelCapabilities(context_window=256000, max_output_tokens=8192),
                specialization="coding",
            ),
            "mistral-small-latest": ModelConfig(
                name="mistral-small-latest",
                display_name="Mistral Small Latest",
                provider="mistral",
                capabilities=ModelCapabilities(context_window=128000, max_output_tokens=8192),
            ),
        }

        # Combine all models
        self._models.update(openai_models)
        self._models.update(anthropic_models)
        self._models.update(groq_models)
        self._models.update(mistral_models)

    def _load_app_config(self) -> None:
        """Load application configuration."""
        self._app_config = AppConfig(
            debug=os.getenv("FLASK_DEBUG", "False").lower() == "true",
            secret_key=os.getenv("SECRET_KEY", "dev-key-change-in-production"),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", str(64 * 1024 * 1024))),
            upload_folder=os.getenv("UPLOAD_FOLDER", "uploads"),
            max_files=int(os.getenv("MAX_FILES", "10")),
            json_sort_keys=os.getenv("JSON_SORT_KEYS", "False").lower() == "true",
            cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        )

    def _load_cache_config(self) -> None:
        """Load cache configuration."""
        self._cache_config = CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "True").lower() == "true",
            default_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "300")),
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
            redis_url=os.getenv("REDIS_URL"),
            file_cache_dir=os.getenv("FILE_CACHE_DIR", "cache"),
        )

    def _load_logging_config(self) -> None:
        """Load logging configuration."""
        self._logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file_path=os.getenv("LOG_FILE_PATH"),
            max_bytes=int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        )

    # Provider methods
    def get_provider_config(self, provider: str) -> ProviderConfig | None:
        """Get configuration for a specific provider."""
        return self._providers.get(provider)

    def get_all_providers(self) -> dict[str, ProviderConfig]:
        """Get all provider configurations."""
        return self._providers.copy()

    def get_available_providers(self) -> list[str]:
        """Get list of providers with valid API keys."""
        return [name for name, config in self._providers.items() if config.api_key]

    # Model methods
    def get_model_config(self, model: str) -> ModelConfig | None:
        """Get configuration for a specific model."""
        return self._models.get(model)

    def get_models_by_provider(self, provider: str) -> list[ModelConfig]:
        """Get all models for a specific provider."""
        return [model for model in self._models.values() if model.provider == provider]

    def get_all_models(self) -> dict[str, ModelConfig]:
        """Get all model configurations."""
        return self._models.copy()

    def get_available_models(self) -> list[ModelConfig]:
        """Get models for providers with valid API keys."""
        available_providers = self.get_available_providers()
        return [model for model in self._models.values() if model.provider in available_providers]

    # Configuration properties
    @property
    def app(self) -> AppConfig:
        """Get application configuration."""
        return self._app_config

    @property
    def cache(self) -> CacheConfig:
        """Get cache configuration."""
        return self._cache_config

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        return self._logging_config

    def validate_configuration(self) -> list[str]:
        """
        Validate all configurations and return list of errors.

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate providers
        for name, config in self._providers.items():
            if not config.api_key:
                errors.append(f"Missing API key for provider: {name}")
            if not config.endpoint:
                errors.append(f"Missing endpoint for provider: {name}")
            if not config.default_model:
                errors.append(f"Missing default model for provider: {name}")

        # Validate models
        for name, config in self._models.items():
            if config.provider not in self._providers:
                errors.append(f"Model {name} references unknown provider: {config.provider}")
            if config.capabilities.context_window <= 0:
                errors.append(f"Invalid context window for model: {name}")
            if config.capabilities.max_output_tokens <= 0:
                errors.append(f"Invalid max output tokens for model: {name}")

        # Validate app config
        if self._app_config.max_content_length <= 0:
            errors.append("Invalid max content length")
        if self._app_config.max_files <= 0:
            errors.append("Invalid max files")

        return errors

    def get_environment_info(self) -> dict[str, Any]:
        """Get environment information for debugging."""
        return {
            "available_providers": self.get_available_providers(),
            "total_models": len(self._models),
            "available_models": len(self.get_available_models()),
            "cache_enabled": self._cache_config.enabled,
            "debug_mode": self._app_config.debug,
            "validation_errors": self.validate_configuration(),
        }


# --- App-wide constants for file management ---
ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "csv", "md", "txt", "jpg", "jpeg", "png"}

BASE_DIR = Path(__file__).parent.parent
SAVE_DIR = BASE_DIR / "saved_chats"
EXPORT_DIR = BASE_DIR / "exports"
UPLOAD_DIR = BASE_DIR / "uploads"


# Flask configuration classes
class BaseConfig:
    """Base configuration class."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64MB
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_FILES = int(os.getenv("MAX_FILES", "10"))

    # Add other config options as needed
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///documents.db")

    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Cache configuration
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))

    # CORS configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    LOG_LEVEL = "DEBUG"

    # Development-specific settings
    TEMPLATES_AUTO_RELOAD = True
    EXPLAIN_TEMPLATE_LOADING = False


class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG = False
    TESTING = False

    # Production-specific settings
    SECRET_KEY = os.getenv("SECRET_KEY")  # Must be set in production

    # Enhanced security headers
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Logging to file in production
    LOG_FILE = os.getenv("LOG_FILE", "app.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


class TestingConfig(BaseConfig):
    """Testing configuration."""

    DEBUG = True
    TESTING = True

    # Testing-specific settings
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = "/tmp/test_uploads"
    DATABASE_URL = "sqlite:///:memory:"

    # Disable caching in tests
    CACHE_TYPE = "null"


# Configuration mapping
config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(
    config_name: str | None = None,
) -> BaseConfig | DevelopmentConfig | ProductionConfig | TestingConfig:
    """
    Get configuration class based on environment.

    Args:
        config_name: Configuration name (development, production, testing)

    Returns:
        Configuration class instance
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    return config_map.get(config_name, config_map["default"])


# Legacy compatibility - maintain existing API configurations
API_CONFIGS = {
    "openai": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "key": os.getenv("OPENAI_API_KEY", ""),
        "default": "gpt-4o-mini",
        "fallback": "gpt-3.5-turbo",
    },
    "groq": {
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.getenv("GROQ_API_KEY", ""),
        "default": "deepseek-r1-distill-llama-70b",
        "fallback": "mixtral-8x7b-32768",
    },
    "mistral": {
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "key": os.getenv("MISTRAL_API_KEY", ""),
        "default": "codestral-latest",
        "fallback": "mistral-small-latest",
    },
    "anthropic": {
        "endpoint": "https://api.anthropic.com/v1/messages",
        "key": os.getenv("ANTHROPIC_API_KEY", ""),
        "default": "claude-3-5-sonnet-latest",
        "fallback": "claude-3-sonnet-20240229",
    },
    "xai": {
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "key": os.getenv("XAI_API_KEY", ""),
        "default": "grok-2-latest",
        "fallback": "grok-2",
    },
    "deepseek": {
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "key": os.getenv("DEEPSEEK_API_KEY", ""),
        "default": "deepseek-chat",
        "fallback": "deepseek-chat",
    },
    "gemini": {
        "endpoint": "https://generativelanguage.googleapis.com/v1/models/",
        "key": os.getenv("GEMINI_API_KEY", ""),
        "default": "gemini-1.5-flash",
        "fallback": "gemini-1.5-flash",
    },
    "cohere": {
        "endpoint": "https://api.cohere.com/v2/chat",
        "key": os.getenv("COHERE_API_KEY", ""),
        "default": "command-r-plus-08-2024",
        "fallback": "command-r-08-2024",
    },
    "alibaba": {
        "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
        "key": os.getenv("DASHSCOPE_API_KEY", ""),
        "default": "qwen-plus",
        "fallback": "qwen-turbo",
    },
    "openrouter": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "key": os.getenv("OPENROUTER_API_KEY", ""),
        "default": "moonshot/moonshot-v1-32k",
        "fallback": "moonshot/moonshot-v1-8k",
    },
    "huggingface": {
        "endpoint": "https://api-inference.huggingface.co/models/",
        "key": os.getenv("HF_API_KEY", ""),
        "default": "meta-llama/Llama-2-70b-chat-hf",
        "fallback": "microsoft/DialoGPT-large",
    },
    "moonshot": {
        "endpoint": "https://api.moonshot.ai/v1/chat/completions",
        "key": os.getenv("MOONSHOT_API_KEY", ""),
        "default": "moonshot-v1-32k",
        "fallback": "moonshot-v1-128k",
    },
    "perplexity": {
        "endpoint": "https://api.perplexity.ai/chat/completions",
        "key": os.getenv("PERPLEXITY_API_KEY", ""),
        "default": "pplx-70b-chat",
        "fallback": "pplx-7b-chat",
    },
}

# Legacy compatibility - maintain existing model configurations
MODEL_CONFIGS = {
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
    "perplexity": ["pplx-70b-chat", "pplx-7b-chat"],
}

# Legacy compatibility - timeout and connection settings
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "50"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))

# API Pool configuration
API_POOL_CONFIG = {
    "pool_connections": int(os.getenv("API_POOL_CONNECTIONS", "10")),
    "pool_maxsize": int(os.getenv("API_POOL_MAXSIZE", "10")),
    "max_retries": MAX_RETRIES,
    "pool_block": False,
}

# Base directory for the application
BASE_DIR = Path(__file__).parent.parent

# Global configuration instance
config = ConfigManager()
