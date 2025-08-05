"""
Modern Configuration Management
Replaces scattered configuration with centralized, type-safe config
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///documents.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30


@dataclass
class CacheConfig:
    """Cache configuration."""
    type: str = "memory"  # memory, redis, file
    redis_url: str = "redis://localhost:6379/0" 
    ttl: int = 3600
    max_size: int = 1000


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = os.getenv("SECRET_KEY", "dev-key-change-in-production")
    jwt_expiry: int = 86400  # 24 hours
    rate_limit_per_minute: int = 60
    max_file_size: int = 64 * 1024 * 1024  # 64MB
    allowed_origins: list[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["*"]


@dataclass
class AIProviderConfig:
    """AI Provider configuration."""
    name: str
    api_key: str
    endpoint: str
    default_model: str
    fallback_model: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit: int = 60  # requests per minute
    
    @property
    def is_available(self) -> bool:
        """Check if provider is properly configured."""
        return bool(self.api_key and self.api_key != "")


@dataclass
class AppConfig:
    """Main application configuration."""
    debug: bool = False
    testing: bool = False
    host: str = "0.0.0.0"
    port: int = 5000
    workers: int = 4
    
    # Directories
    upload_dir: Path = Path("uploads")
    export_dir: Path = Path("exports") 
    save_dir: Path = Path("saved_chats")
    temp_dir: Path = Path("uploads/temp")
    
    # Performance
    request_timeout: int = 30
    max_content_length: int = 64 * 1024 * 1024
    max_files_per_upload: int = 10
    
    def __post_init__(self):
        # Ensure directories exist
        for directory in [self.upload_dir, self.export_dir, self.save_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """Centralized configuration management."""
    
    def __init__(self, env: str = None):
        self.env = env or os.getenv("FLASK_ENV", "development")
        self._providers: Dict[str, AIProviderConfig] = {}
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment variables."""
        # Load AI providers
        self._load_ai_providers()
    
    def _load_ai_providers(self):
        """Load AI provider configurations from environment."""
        providers = {
            "openai": {
                "endpoint": "https://api.openai.com/v1/chat/completions",
                "default_model": "gpt-4o-mini",
                "fallback_model": "gpt-3.5-turbo"
            },
            "groq": {
                "endpoint": "https://api.groq.com/openai/v1/chat/completions", 
                "default_model": "mixtral-8x7b-32768",
                "fallback_model": "llama3-8b-8192"
            },
            "anthropic": {
                "endpoint": "https://api.anthropic.com/v1/messages",
                "default_model": "claude-3-haiku-20240307",
                "fallback_model": "claude-3-haiku-20240307"
            },
            "mistral": {
                "endpoint": "https://api.mistral.ai/v1/chat/completions",
                "default_model": "mistral-small-latest", 
                "fallback_model": "mistral-tiny"
            },
            "xai": {
                "endpoint": "https://api.x.ai/v1/chat/completions",
                "default_model": "grok-beta",
                "fallback_model": "grok-beta"
            },
            "deepseek": {
                "endpoint": "https://api.deepseek.com/v1/chat/completions",
                "default_model": "deepseek-coder",
                "fallback_model": "deepseek-chat"
            },
            "gemini": {
                "endpoint": "https://generativelanguage.googleapis.com/v1/models/",
                "default_model": "gemini-2.5-flash-lite-preview",
                "fallback_model": "gemini-pro"
            },
            "cohere": {
                "endpoint": "https://api.cohere.ai/v1/generate",
                "default_model": "command",
                "fallback_model": "command-light"
            },
            "alibaba": {
                "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                "default_model": "qwen3-235b-a22b-instruct",
                "fallback_model": "qwen-turbo"
            },
            "openrouter": {
                "endpoint": "https://openrouter.ai/api/v1/chat/completions", 
                "default_model": "anthropic/claude-3.5-sonnet",
                "fallback_model": "meta-llama/llama-3-8b-instruct"
            },
            "huggingface": {
                "endpoint": "https://api-inference.huggingface.co/models/",
                "default_model": "moonshotai/Kimi-K2-Instruct",
                "fallback_model": "microsoft/DialoGPT-medium"
            },
            "moonshot": {
                "endpoint": "https://api.moonshot.ai/v1/chat/completions",
                "default_model": "moonshot-v1-128k",
                "fallback_model": "moonshot-v1-32k"
            },
            "perplexity": {
                "endpoint": "https://api.perplexity.ai/chat/completions",
                "default_model": "llama-3.1-sonar-small-128k-online",
                "fallback_model": "llama-3.1-sonar-small-128k-chat"
            }
        }
        
        for name, config in providers.items():
            api_key = os.getenv(f"{name.upper()}_API_KEY", "")
            
            self._providers[name] = AIProviderConfig(
                name=name,
                api_key=api_key,
                endpoint=config["endpoint"],
                default_model=config["default_model"],
                fallback_model=config["fallback_model"]
            )
    
    @property
    def app(self) -> AppConfig:
        """Get application configuration."""
        return AppConfig(
            debug=self.env == "development",
            testing=self.env == "testing",
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "5000")),
            workers=int(os.getenv("WORKERS", "4"))
        )
    
    @property 
    def database(self) -> DatabaseConfig:
        """Get database configuration."""
        return DatabaseConfig(
            url=os.getenv("DATABASE_URL", "sqlite:///documents.db"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30"))
        )
    
    @property
    def cache(self) -> CacheConfig:
        """Get cache configuration."""
        return CacheConfig(
            type=os.getenv("CACHE_TYPE", "memory"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            ttl=int(os.getenv("CACHE_TTL", "3600")),
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000"))
        )
    
    @property
    def security(self) -> SecurityConfig:
        """Get security configuration."""
        origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
        return SecurityConfig(
            secret_key=os.getenv("SECRET_KEY", "dev-key-change-in-production"),
            jwt_expiry=int(os.getenv("JWT_EXPIRY", "86400")),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT", "60")),
            max_file_size=int(os.getenv("MAX_FILE_SIZE", "67108864")),  # 64MB
            allowed_origins=origins if origins != ["*"] else ["*"]
        )
    
    def get_provider(self, name: str) -> Optional[AIProviderConfig]:
        """Get AI provider configuration."""
        return self._providers.get(name)
    
    def get_available_providers(self) -> Dict[str, AIProviderConfig]:
        """Get all available (configured) providers."""
        return {
            name: config for name, config in self._providers.items()
            if config.is_available
        }
    
    def validate_configuration(self) -> list[str]:
        """Validate configuration and return any errors."""
        errors = []
        
        # Check critical environment variables
        if self.security.secret_key == "dev-key-change-in-production" and self.env == "production":
            errors.append("SECRET_KEY must be set in production")
        
        # Check that at least one AI provider is configured
        if not self.get_available_providers():
            errors.append("At least one AI provider API key must be configured")
        
        # Validate Redis URL if using Redis cache
        if self.cache.type == "redis":
            try:
                parsed = urlparse(self.cache.redis_url)
                if not parsed.hostname:
                    errors.append("Invalid REDIS_URL format")
            except Exception:
                errors.append("Invalid REDIS_URL format")
        
        return errors


# Global configuration instance
config_manager = ConfigManager()


# Flask configuration classes for compatibility
class BaseConfig:
    """Base configuration class."""
    
    def __init__(self):
        self.config = config_manager
        
        # Flask settings
        self.SECRET_KEY = self.config.security.secret_key
        self.MAX_CONTENT_LENGTH = self.config.security.max_file_size
        self.JSON_SORT_KEYS = False
        
        # Application settings
        self.UPLOAD_FOLDER = str(self.config.app.upload_dir)
        self.EXPORT_FOLDER = str(self.config.app.export_dir)
        self.SAVE_FOLDER = str(self.config.app.save_dir)


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    
    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.TESTING = False


class ProductionConfig(BaseConfig):
    """Production configuration."""
    
    def __init__(self):
        super().__init__()
        self.DEBUG = False
        self.TESTING = False


class TestingConfig(BaseConfig):
    """Testing configuration."""
    
    def __init__(self):
        super().__init__()
        self.DEBUG = True
        self.TESTING = True
        self.WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig(),
    'production': ProductionConfig(), 
    'testing': TestingConfig(),
    'default': DevelopmentConfig()
}
