"""
AI Provider Management Module

Handles all AI provider integrations with standardized interfaces.
Eliminates code duplication and provides consistent error handling.
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import CONNECT_TIMEOUT, READ_TIMEOUT

# Modern type aliases (Python 3.10+ compatible)
ProviderMap = dict[str, "BaseProvider"]
ModelList = list[str]
RequestHeaders = dict[str, str]
RequestPayload = dict[str, Any]


class ProviderType(Enum):
    """Provider type enumeration for better categorization"""

    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"


@runtime_checkable
class Configurable(Protocol):
    """Protocol for configurable providers"""

    def is_configured(self) -> bool:
        ...


class TQChatError(Exception):
    """Base exception for TQ Chat application"""

    pass


class ProviderError(TQChatError):
    """Provider-related errors with enhanced context"""

    def __init__(self, provider: str, message: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"{provider}: {message}")


class RateLimitError(ProviderError):
    """Rate limiting errors for better handling"""

    pass


@dataclass
class ProviderConfig:
    """Enhanced configuration for AI providers with validation"""

    endpoint: str
    key: str
    default_model: str
    fallback_model: str
    provider_type: ProviderType = ProviderType.OPENAI_COMPATIBLE
    timeout: int = READ_TIMEOUT
    max_retries: int = 3

    @property
    def is_configured(self) -> bool:
        """Check if provider is properly configured"""
        return bool(self.key.strip() and self.endpoint.strip())

    def validate(self) -> bool:
        """Validate configuration parameters"""
        if not self.is_configured:
            return False
        if self.timeout <= 0 or self.max_retries < 0:
            return False
        return True


@dataclass
class APIResponse:
    """Standardized API response with enhanced metadata"""

    text: str
    metadata: dict[str, Any]
    success: bool = True
    error: str | None = None
    usage: dict[str, Any] | None = None

    @property
    def is_successful(self) -> bool:
        """Check if response was successful"""
        return self.success and not self.error

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "success": self.success,
            "error": self.error,
            "usage": self.usage,
        }


class BaseProvider(ABC):
    """Enhanced base class for all AI providers with modern patterns"""

    def __init__(self, config: ProviderConfig):
        if not config.validate():
            raise ValueError(f"Invalid configuration for {self.provider_name}")

        self.config = config
        self.session = self._create_session()
        self._request_count = 0
        self._error_count = 0

    def _create_session(self) -> requests.Session:
        """Create HTTP session with enhanced retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],  # Modern urllib3 parameter
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _create_metadata(
        self, model: str, response_time: float, fallback_used: bool = False
    ) -> dict[str, Any]:
        """Create standardized metadata with additional metrics"""
        return {
            "provider": self.provider_name,
            "model": model,
            "response_time": f"{response_time:.3f}s",
            "fallback_used": fallback_used,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "success_rate": (self._request_count - self._error_count) / max(self._request_count, 1),
        }

    def _handle_http_error(self, error: requests.HTTPError) -> str:
        """Enhanced HTTP error handling with specific status codes"""
        status_code = error.response.status_code

        match status_code:
            case 401:
                return "Authentication failed - check API key"
            case 403:
                return "Access forbidden - insufficient permissions"
            case 429:
                return "Rate limit exceeded - please try again later"
            case 500 | 502 | 503 | 504:
                return f"Server error ({status_code}) - provider temporarily unavailable"
            case _:
                return f"HTTP {status_code}: {str(error)}"

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier"""
        pass

    @abstractmethod
    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, RequestHeaders, RequestPayload]:
        """Prepare request parameters with type hints"""
        pass

    @abstractmethod
    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        """Extract text from provider-specific response format"""
        pass

    def generate_response(
        self,
        model: str,
        message: str,
        persona: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> APIResponse:
        """Generate response with enhanced fallback strategy and error handling"""
        models_to_try = [model]
        if self.config.fallback_model and self.config.fallback_model != model:
            models_to_try.append(self.config.fallback_model)

        last_error = None

        for i, model_to_use in enumerate(models_to_try):
            self._request_count += 1

            try:
                endpoint, headers, payload = self._prepare_request(
                    model_to_use, message, persona, temperature, max_tokens
                )

                start_time = time.time()
                response = self.session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=(CONNECT_TIMEOUT, self.config.timeout),
                )
                response_time = time.time() - start_time

                response.raise_for_status()
                result = response.json()

                return self._extract_response(result, model_to_use, response_time, i > 0)

            except requests.HTTPError as e:
                self._error_count += 1
                last_error = self._handle_http_error(e)

                # Don't retry on authentication errors
                if e.response.status_code == 401:
                    break

            except requests.Timeout:
                self._error_count += 1
                last_error = f"Request timed out after {self.config.timeout}s"

            except requests.RequestException as e:
                self._error_count += 1
                last_error = f"Request failed: {str(e)}"

            except (KeyError, ValueError, TypeError) as e:
                self._error_count += 1
                last_error = f"Response parsing error: {str(e)}"

            except Exception as e:
                self._error_count += 1
                last_error = f"Unexpected error: {str(e)}"

        return APIResponse(
            text="",
            metadata=self._create_metadata(model, 0.0, len(models_to_try) > 1),
            success=False,
            error=f"All attempts failed. Last error: {last_error}",
        )


class OpenAICompatibleProvider(BaseProvider):
    """Enhanced provider for OpenAI-compatible APIs with better error handling"""

    def __init__(self, config: ProviderConfig, provider_name: str):
        super().__init__(config)
        self._provider_name = provider_name

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, RequestHeaders, RequestPayload]:
        """Prepare OpenAI-compatible request with validation"""
        headers: RequestHeaders = {
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

        # Build messages with persona if provided
        messages = []
        if persona.strip():
            messages.append({"role": "system", "content": persona.strip()})
        messages.append({"role": "user", "content": message})

        payload: RequestPayload = {
            "model": model,
            "messages": messages,
            "temperature": max(0.0, min(2.0, temperature)),  # Clamp temperature
            "max_tokens": max(1, min(8192, max_tokens)),  # Clamp max_tokens
        }

        return self.config.endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        """Extract response with enhanced error checking"""
        try:
            # Validate response structure
            if not isinstance(result, dict):
                raise TypeError("Response is not a dictionary")

            if "choices" not in result or not result["choices"]:
                raise KeyError("No choices in response")

            choice = result["choices"][0]
            if "message" not in choice or "content" not in choice["message"]:
                raise KeyError("Invalid message structure")

            text = choice["message"]["content"]
            if not isinstance(text, str):
                raise TypeError("Response text is not a string")

            # Extract usage information if available
            usage = result.get("usage", {})

            return APIResponse(
                text=text,
                metadata=self._create_metadata(model, response_time, fallback_used),
                usage=usage,
            )

        except (KeyError, IndexError, TypeError) as e:
            return APIResponse(
                text="",
                metadata=self._create_metadata(model, response_time, fallback_used),
                success=False,
                error=f"Invalid {self.provider_name} response structure: {str(e)}",
            )


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider"""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        headers = {
            "x-api-key": self.config.key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": model,
            "system": persona,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": max_tokens,
        }

        return self.config.endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            if "content" in result and result["content"]:
                text = result["content"][0]["text"]
                return APIResponse(
                    text=text,
                    metadata=self._create_metadata(model, response_time, fallback_used),
                )
        except (KeyError, IndexError, TypeError):
            pass

        return APIResponse(
            text="",
            metadata={},
            success=False,
            error="Invalid Anthropic response structure",
        )


class GeminiProvider(BaseProvider):
    """Google Gemini provider"""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        endpoint = f"{self.config.endpoint}{model}:generateContent?key={self.config.key}"
        headers = {"Content-Type": "application/json"}

        payload = {"contents": [{"role": "user", "parts": [{"text": f"{persona}\n{message}"}]}]}

        return endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            candidates = result.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    text = parts[0]["text"]
                    return APIResponse(
                        text=text,
                        metadata=self._create_metadata(model, response_time, fallback_used),
                    )
        except (KeyError, IndexError, TypeError):
            pass

        return APIResponse(
            text="",
            metadata={},
            success=False,
            error="Invalid Gemini response structure",
        )


class CohereProvider(BaseProvider):
    """Cohere provider"""

    @property
    def provider_name(self) -> str:
        return "cohere"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        headers = {
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        return self.config.endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            text = result["message"]["content"][0]["text"]
            return APIResponse(
                text=text,
                metadata=self._create_metadata(model, response_time, fallback_used),
            )
        except (KeyError, IndexError, TypeError):
            return APIResponse(
                text="",
                metadata={},
                success=False,
                error="Invalid Cohere response structure",
            )


class HuggingFaceProvider(BaseProvider):
    """Hugging Face Inference API provider"""

    @property
    def provider_name(self) -> str:
        return "huggingface"

    def _prepare_request(
        self,
        model: str,
        message: str,
        persona: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, dict, dict]:
        # Hugging Face uses model-specific endpoints
        endpoint = f"{self.config.endpoint}{model}"
        headers = {
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

        # Build the prompt with persona if provided
        prompt = f"{persona}\n{message}" if persona.strip() else message

        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        return endpoint, headers, payload

    def _extract_response(
        self, result: dict, model: str, response_time: float, fallback_used: bool
    ) -> APIResponse:
        try:
            # Hugging Face returns different formats depending on the model
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    text = result[0]["generated_text"]
                elif "text" in result[0]:
                    text = result[0]["text"]
                else:
                    text = str(result[0])
            elif isinstance(result, dict):
                if "generated_text" in result:
                    text = result["generated_text"]
                elif "text" in result:
                    text = result["text"]
                else:
                    text = str(result)
            else:
                text = str(result)

            return APIResponse(
                text=text,
                metadata=self._create_metadata(model, response_time, fallback_used),
            )
        except (KeyError, IndexError, TypeError) as e:
            return APIResponse(
                text="",
                metadata={},
                success=False,
                error=f"Invalid Hugging Face response structure: {str(e)}",
            )


class ProviderManager:
    """Enhanced centralized provider management with factory pattern"""

    def __init__(self, custom_configs: dict[str, ProviderConfig] | None = None):
        self.providers: ProviderMap = {}
        self._provider_configs = custom_configs or self._get_default_configs()
        self._initialize_providers()

    def _get_default_configs(self) -> dict[str, ProviderConfig]:
        """Get default provider configurations from environment"""
        return {
            "cerebras": ProviderConfig(
                endpoint="https://api.cerebras.ai/v1/chat/completions",
                key=os.getenv("CEREBRAS_API_KEY", ""),
                default_model="llama-3.3-70b",
                fallback_model="deepseek-r1-distill-llama-70b",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "openai": ProviderConfig(
                endpoint="https://api.openai.com/v1/chat/completions",
                key=os.getenv("OPENAI_API_KEY", ""),
                default_model="gpt-4o-mini",
                fallback_model="gpt-3.5-turbo",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "groq": ProviderConfig(
                endpoint="https://api.groq.com/openai/v1/chat/completions",
                key=os.getenv("GROQ_API_KEY", ""),
                default_model="deepseek-r1-distill-llama-70b",
                fallback_model="mixtral-8x7b-32768",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "mistral": ProviderConfig(
                endpoint="https://api.mistral.ai/v1/chat/completions",
                key=os.getenv("MISTRAL_API_KEY", ""),
                default_model="codestral-latest",
                fallback_model="mistral-small-latest",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "anthropic": ProviderConfig(
                endpoint="https://api.anthropic.com/v1/messages",
                key=os.getenv("ANTHROPIC_API_KEY", ""),
                default_model="claude-3-5-sonnet-latest",
                fallback_model="claude-3-sonnet-20240229",
                provider_type=ProviderType.ANTHROPIC,
            ),
            "gemini": ProviderConfig(
                endpoint="https://generativelanguage.googleapis.com/v1/models/",
                key=os.getenv("GEMINI_API_KEY", ""),
                default_model="gemini-1.5-flash",
                fallback_model="gemini-1.5-flash",
                provider_type=ProviderType.GEMINI,
            ),
            "cohere": ProviderConfig(
                endpoint="https://api.cohere.com/v2/chat",
                key=os.getenv("COHERE_API_KEY", ""),
                default_model="command-r-plus-08-2024",
                fallback_model="command-r-08-2024",
                provider_type=ProviderType.COHERE,
            ),
            "xai": ProviderConfig(
                endpoint="https://api.x.ai/v1/chat/completions",
                key=os.getenv("XAI_API_KEY", ""),
                default_model="grok-4",
                fallback_model="grok-3",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "deepseek": ProviderConfig(
                endpoint="https://api.deepseek.com/v1/chat/completions",
                key=os.getenv("DEEPSEEK_API_KEY", ""),
                default_model="deepseek-chat",
                fallback_model="deepseek-reasoner",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "alibaba": ProviderConfig(
                endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                key=os.getenv("ALIBABA_API_KEY", ""),
                default_model="qwen-2.5-72b-instruct",
                fallback_model="qwen-2.5-32b-instruct",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "openrouter": ProviderConfig(
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                key=os.getenv("OPENROUTER_API_KEY", ""),
                default_model="openai/gpt-4o",
                fallback_model="meta-llama/llama-3.3-70b-versatile",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "huggingface": ProviderConfig(
                endpoint="https://api-inference.huggingface.co/models/",
                key=os.getenv("HUGGINGFACE_API_KEY", ""),
                default_model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
                fallback_model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
                provider_type=ProviderType.HUGGINGFACE,
            ),
            "moonshot": ProviderConfig(
                endpoint="https://api.moonshot.cn/v1/chat/completions",
                key=os.getenv("MOONSHOT_API_KEY", ""),
                default_model="moonshot-v1-128k",
                fallback_model="moonshot-v1-32k",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
            "perplexity": ProviderConfig(
                endpoint="https://api.perplexity.ai/chat/completions",
                key=os.getenv("PERPLEXITY_API_KEY", ""),
                default_model="pplx-70b-chat",
                fallback_model="pplx-7b-chat",
                provider_type=ProviderType.OPENAI_COMPATIBLE,
            ),
        }

    def _create_provider(self, name: str, config: ProviderConfig) -> BaseProvider:
        """Factory method to create providers based on type"""
        match config.provider_type:
            case ProviderType.ANTHROPIC:
                return AnthropicProvider(config)
            case ProviderType.GEMINI:
                return GeminiProvider(config)
            case ProviderType.COHERE:
                return CohereProvider(config)
            case ProviderType.HUGGINGFACE:
                return HuggingFaceProvider(config)
            case ProviderType.OPENAI_COMPATIBLE:
                return OpenAICompatibleProvider(config, name)
            case _:  # Default fallback
                return OpenAICompatibleProvider(config, name)

    def _initialize_providers(self):
        """Initialize all configured providers with error handling"""
        for name, config in self._provider_configs.items():
            try:
                if config.is_configured and config.validate():
                    provider = self._create_provider(name, config)
                    self.providers[name] = provider
                else:
                    pass
            except Exception:
                pass

    def get_provider(self, name: str) -> BaseProvider | None:
        """Get provider by name with None safety"""
        return self.providers.get(name)

    def list_providers(self) -> ModelList:
        """List available provider names"""
        return list(self.providers.keys())

    def is_provider_available(self, name: str) -> bool:
        """Check if provider is available and configured"""
        return name in self.providers

    def get_provider_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all providers"""
        return {
            name: {
                "request_count": provider._request_count,
                "error_count": provider._error_count,
                "success_rate": (provider._request_count - provider._error_count)
                / max(provider._request_count, 1),
                "provider_type": provider.config.provider_type.value,
            }
            for name, provider in self.providers.items()
        }

    def add_provider(self, name: str, config: ProviderConfig) -> bool:
        """Dynamically add a new provider"""
        try:
            if config.validate():
                provider = self._create_provider(name, config)
                self.providers[name] = provider
                return True
        except Exception:
            pass
        return False

    def remove_provider(self, name: str) -> bool:
        """Remove a provider"""
        return self.providers.pop(name, None) is not None


# Global provider manager instance
provider_manager = ProviderManager()
