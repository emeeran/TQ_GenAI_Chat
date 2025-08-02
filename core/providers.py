"""
AI Provider Management Module

Handles all AI provider integrations with standardized interfaces.
Eliminates code duplication and provides consistent error handling.
"""

import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import (
    CONNECT_TIMEOUT, READ_TIMEOUT, MAX_RETRIES
)


@dataclass
class ProviderConfig:
    """Configuration for AI providers"""
    endpoint: str
    key: str
    default_model: str
    fallback_model: str
    
    @property
    def is_configured(self) -> bool:
        return bool(self.key.strip())


@dataclass
class APIResponse:
    """Standardized API response format"""
    text: str
    metadata: dict[str, Any]
    success: bool = True
    error: str | None = None


class BaseProvider(ABC):
    """Base class for all AI providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session
    
    def _create_metadata(self, model: str, response_time: float, 
                        fallback_used: bool = False) -> dict[str, Any]:
        """Create standardized metadata"""
        return {
            'provider': self.provider_name,
            'model': model,
            'response_time': f"{response_time}s",
            'fallback_used': fallback_used
        }
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier"""
        pass
    
    @abstractmethod
    def _prepare_request(self, model: str, message: str, persona: str,
                        temperature: float, max_tokens: int) -> tuple[str, dict, dict]:
        """Prepare request parameters (endpoint, headers, payload)"""
        pass
    
    @abstractmethod
    def _extract_response(self, result: dict, model: str, 
                         response_time: float, fallback_used: bool) -> APIResponse:
        """Extract text from provider-specific response format"""
        pass
    
    def generate_response(self, model: str, message: str, persona: str = '',
                         temperature: float = 0.7, max_tokens: int = 4000) -> APIResponse:
        """Generate response with automatic fallback"""
        models_to_try = [model]
        if self.config.fallback_model and self.config.fallback_model != model:
            models_to_try.append(self.config.fallback_model)
        
        last_error = None
        
        for i, model_to_use in enumerate(models_to_try):
            try:
                endpoint, headers, payload = self._prepare_request(
                    model_to_use, message, persona, temperature, max_tokens
                )
                
                start_time = time.time()
                response = self.session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
                )
                response_time = time.time() - start_time
                
                response.raise_for_status()
                result = response.json()
                
                return self._extract_response(
                    result, model_to_use, response_time, i > 0
                )
                
            except requests.HTTPError as e:
                last_error = f"HTTP {e.response.status_code}: {str(e)}"
            except requests.Timeout:
                last_error = f"Request timed out after {READ_TIMEOUT}s"
            except requests.RequestException as e:
                last_error = f"Request failed: {str(e)}"
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
        
        return APIResponse(
            text="", 
            metadata={}, 
            success=False, 
            error=f"All attempts failed. Last error: {last_error}"
        )


class OpenAICompatibleProvider(BaseProvider):
    """Provider for OpenAI-compatible APIs (OpenAI, Groq, Mistral, etc.)"""
    
    def __init__(self, config: ProviderConfig, provider_name: str):
        super().__init__(config)
        self._provider_name = provider_name
    
    @property
    def provider_name(self) -> str:
        return self._provider_name
    
    def _prepare_request(self, model: str, message: str, persona: str,
                        temperature: float, max_tokens: int) -> tuple[str, dict, dict]:
        headers = {
            'Authorization': f'Bearer {self.config.key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': persona},
                {'role': 'user', 'content': message}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        return self.config.endpoint, headers, payload
    
    def _extract_response(self, result: dict, model: str, 
                         response_time: float, fallback_used: bool) -> APIResponse:
        try:
            if 'choices' in result and result['choices']:
                text = result['choices'][0]['message']['content']
                return APIResponse(
                    text=text,
                    metadata=self._create_metadata(model, response_time, fallback_used)
                )
        except (KeyError, IndexError, TypeError):
            pass
        
        return APIResponse(
            text="", 
            metadata={}, 
            success=False, 
            error="Invalid response structure"
        )


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider"""
    
    @property
    def provider_name(self) -> str:
        return 'anthropic'
    
    def _prepare_request(self, model: str, message: str, persona: str,
                        temperature: float, max_tokens: int) -> tuple[str, dict, dict]:
        headers = {
            'x-api-key': self.config.key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        payload = {
            'model': model,
            'system': persona,
            'messages': [{'role': 'user', 'content': message}],
            'max_tokens': max_tokens
        }
        
        return self.config.endpoint, headers, payload
    
    def _extract_response(self, result: dict, model: str, 
                         response_time: float, fallback_used: bool) -> APIResponse:
        try:
            if 'content' in result and result['content']:
                text = result['content'][0]['text']
                return APIResponse(
                    text=text,
                    metadata=self._create_metadata(model, response_time, fallback_used)
                )
        except (KeyError, IndexError, TypeError):
            pass
        
        return APIResponse(
            text="", 
            metadata={}, 
            success=False, 
            error="Invalid Anthropic response structure"
        )


class GeminiProvider(BaseProvider):
    """Google Gemini provider"""
    
    @property
    def provider_name(self) -> str:
        return 'gemini'
    
    def _prepare_request(self, model: str, message: str, persona: str,
                        temperature: float, max_tokens: int) -> tuple[str, dict, dict]:
        endpoint = f"{self.config.endpoint}{model}:generateContent?key={self.config.key}"
        headers = {'Content-Type': 'application/json'}
        
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": f"{persona}\n{message}"}]
            }]
        }
        
        return endpoint, headers, payload
    
    def _extract_response(self, result: dict, model: str, 
                         response_time: float, fallback_used: bool) -> APIResponse:
        try:
            candidates = result.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                if parts and 'text' in parts[0]:
                    text = parts[0]['text']
                    return APIResponse(
                        text=text,
                        metadata=self._create_metadata(model, response_time, fallback_used)
                    )
        except (KeyError, IndexError, TypeError):
            pass
        
        return APIResponse(
            text="", 
            metadata={}, 
            success=False, 
            error="Invalid Gemini response structure"
        )


class CohereProvider(BaseProvider):
    """Cohere provider"""
    
    @property
    def provider_name(self) -> str:
        return 'cohere'
    
    def _prepare_request(self, model: str, message: str, persona: str,
                        temperature: float, max_tokens: int) -> tuple[str, dict, dict]:
        headers = {
            'Authorization': f'Bearer {self.config.key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': message}],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        return self.config.endpoint, headers, payload
    
    def _extract_response(self, result: dict, model: str, 
                         response_time: float, fallback_used: bool) -> APIResponse:
        try:
            text = result["message"]["content"][0]["text"]
            return APIResponse(
                text=text,
                metadata=self._create_metadata(model, response_time, fallback_used)
            )
        except (KeyError, IndexError, TypeError):
            return APIResponse(
                text="", 
                metadata={}, 
                success=False, 
                error="Invalid Cohere response structure"
            )


class ProviderManager:
    """Centralized provider management"""
    
    def __init__(self):
        self.providers: dict[str, BaseProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        # Provider configurations
        configs = {
            'openai': ProviderConfig(
                endpoint="https://api.openai.com/v1/chat/completions",
                key=os.getenv("OPENAI_API_KEY", ""),
                default_model="gpt-4o-mini",
                fallback_model="gpt-3.5-turbo"
            ),
            'groq': ProviderConfig(
                endpoint="https://api.groq.com/openai/v1/chat/completions",
                key=os.getenv("GROQ_API_KEY", ""),
                default_model="deepseek-r1-distill-llama-70b",
                fallback_model="mixtral-8x7b-32768"
            ),
            'mistral': ProviderConfig(
                endpoint="https://api.mistral.ai/v1/chat/completions",
                key=os.getenv("MISTRAL_API_KEY", ""),
                default_model="codestral-latest",
                fallback_model="mistral-small-latest"
            ),
            'anthropic': ProviderConfig(
                endpoint="https://api.anthropic.com/v1/messages",
                key=os.getenv("ANTHROPIC_API_KEY", ""),
                default_model="claude-3-5-sonnet-latest",
                fallback_model="claude-3-sonnet-20240229"
            ),
            'gemini': ProviderConfig(
                endpoint="https://generativelanguage.googleapis.com/v1/models/",
                key=os.getenv("GEMINI_API_KEY", ""),
                default_model="gemini-1.5-flash",
                fallback_model="gemini-1.5-flash"
            ),
            'cohere': ProviderConfig(
                endpoint="https://api.cohere.com/v2/chat",
                key=os.getenv("COHERE_API_KEY", ""),
                default_model="command-r-plus-08-2024",
                fallback_model="command-r-08-2024"
            )
        }
        
        # Initialize providers
        for name, config in configs.items():
            if config.is_configured:
                if name == 'anthropic':
                    self.providers[name] = AnthropicProvider(config)
                elif name == 'gemini':
                    self.providers[name] = GeminiProvider(config)
                elif name == 'cohere':
                    self.providers[name] = CohereProvider(config)
                else:
                    self.providers[name] = OpenAICompatibleProvider(config, name)
    
    def get_provider(self, name: str) -> BaseProvider | None:
        """Get provider by name"""
        return self.providers.get(name)
    
    def list_providers(self) -> list[str]:
        """List available providers"""
        return list(self.providers.keys())
    
    def is_provider_available(self, name: str) -> bool:
        """Check if provider is available"""
        return name in self.providers


# Global provider manager instance
provider_manager = ProviderManager()
