"""
API Services Module
Provides a unified interface for interacting with various AI API providers.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from functools import lru_cache
from typing import Any

import requests

from config.settings import CONNECT_TIMEOUT, MAX_RETRIES, RATE_LIMIT, READ_TIMEOUT

# Create module-level logger
logger = logging.getLogger(__name__)

# Lazy import for anthropic to avoid import errors
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class APIServices:
    """
    Unified API service for multiple AI providers
    Handles authentication, rate limiting, and response formatting
    """

    def __init__(self):
        """Initialize API connections and validate API keys"""
        # Load API keys
        self.api_keys = {
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "groq": os.getenv("GROQ_API_KEY", ""),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "mistral": os.getenv("MISTRAL_API_KEY", ""),
        }

        # Validate required API keys
        for provider in ["openai", "groq"]:
            if not self.api_keys[provider]:
                logger.warning(f"{provider.upper()}_API_KEY not set.")

        # Configure endpoints
        self.endpoints = {
            "openai": "https://api.openai.com/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "anthropic": "https://api.anthropic.com/v1/messages",
            "mistral": "https://api.mistral.ai/v1/chat/completions",
        }

        # Rate limiting trackers
        self.request_times = {provider: [] for provider in self.endpoints}
        self._rate_limit_lock = asyncio.Lock()

        # Configure session with retry strategy
        self.session = self._create_request_session()

    def _create_request_session(self) -> requests.Session:
        """Create and configure a requests session with retry handling"""
        retry_strategy = requests.packages.urllib3.util.retry.Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    async def _enforce_rate_limit(self, provider: str) -> None:
        """Enforce rate limiting for API calls"""
        async with self._rate_limit_lock:
            # Remove timestamps older than 60 seconds
            current_time = time.time()
            self.request_times[provider] = [
                t for t in self.request_times[provider] if current_time - t < 60
            ]

            # Check if we've hit the rate limit
            if len(self.request_times[provider]) >= RATE_LIMIT:
                # Calculate sleep time based on oldest request
                sleep_time = 60 - (current_time - self.request_times[provider][0])
                if sleep_time > 0:
                    logger.warning(
                        f"Rate limit hit for {provider}, sleeping for {sleep_time:.2f}s"
                    )
                    await asyncio.sleep(sleep_time)

                # Clear old entries after sleeping
                self.request_times[provider] = [
                    t for t in self.request_times[provider] if current_time - t < 60
                ]

            # Add current request time
            self.request_times[provider].append(current_time)

    @lru_cache(maxsize=100)
    def _get_request_hash(self, provider: str, model: str, messages: str, **kwargs) -> str:
        """Generate a hash for request caching"""
        key_str = f"{provider}|{model}|{messages}|{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()  # nosec B324

    async def generate_completion(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Generate a completion from the specified provider and model

        Args:
            provider: The API provider to use (openai, groq, etc.)
            model: The specific model to use
            messages: List of message objects with role and content
            max_tokens: Maximum tokens to generate
            temperature: Temperature parameter for generation
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict containing the completion and metadata
        """
        # Validate provider and model
        if provider not in self.endpoints:
            raise ValueError(f"Unsupported provider: {provider}")

        if not self.api_keys.get(provider):
            raise ValueError(f"API key not configured for {provider}")

        # Apply rate limiting
        await self._enforce_rate_limit(provider)

        # Generate based on provider
        if provider == "openai":
            return await self._generate_openai(model, messages, max_tokens, temperature, **kwargs)
        elif provider == "groq":
            return await self._generate_groq(model, messages, max_tokens, temperature, **kwargs)
        elif provider == "anthropic":
            return await self._generate_anthropic(
                model, messages, max_tokens, temperature, **kwargs
            )
        elif provider == "mistral":
            return await self._generate_mistral(model, messages, max_tokens, temperature, **kwargs)
        else:
            raise ValueError(f"Provider {provider} implementation not available")

    async def _generate_openai(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a completion using OpenAI's API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_keys['openai']}",
        }

        # Configure request payload
        payload = {"model": model, "messages": messages, "temperature": temperature}

        # Add max_tokens if specified
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Add additional parameters
        for key, value in kwargs.items():
            payload[key] = value

        try:
            response = self.session.post(
                self.endpoints["openai"],
                headers=headers,
                json=payload,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            response.raise_for_status()
            result = response.json()

            # Extract and return the response content
            if "choices" in result and result["choices"]:
                return {
                    "content": result["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "openai",
                    "raw_response": result,
                }
            else:
                raise ValueError("Unexpected response format from OpenAI API")

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise ValueError(f"OpenAI API request failed: {str(e)}")

    async def _generate_groq(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a completion using Groq's API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_keys['groq']}",
        }

        # Configure request payload
        payload = {"model": model, "messages": messages, "temperature": temperature}

        # Add max_tokens if specified
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Add additional parameters
        for key, value in kwargs.items():
            payload[key] = value

        try:
            response = self.session.post(
                self.endpoints["groq"],
                headers=headers,
                json=payload,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            response.raise_for_status()
            result = response.json()

            # Extract and return the response content
            if "choices" in result and result["choices"]:
                return {
                    "content": result["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "groq",
                    "raw_response": result,
                }
            else:
                raise ValueError("Unexpected response format from Groq API")

        except requests.exceptions.RequestException as e:
            logger.error(f"Groq API request failed: {str(e)}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise ValueError(f"Groq API request failed: {str(e)}")

    async def _generate_anthropic(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a completion using Anthropic's API"""
        # Check if Anthropic is available
        if not ANTHROPIC_AVAILABLE or anthropic is None:
            raise ImportError(
                "Anthropic package is not installed. Install it with: pip install anthropic"
            )

        # Create Anthropic client
        client = anthropic.Anthropic(api_key=self.api_keys["anthropic"])

        # Convert messages format if needed
        anthropic_messages = []
        system_prompt = ""

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append(msg)

        try:
            # Build parameters dictionary
            params = {
                "model": model,
                "messages": anthropic_messages,
                "temperature": temperature,
            }

            # Add system prompt if provided
            if system_prompt:
                params["system"] = system_prompt

            # Add max_tokens if specified
            if max_tokens is not None:
                params["max_tokens"] = max_tokens

            # Add additional parameters
            for key, value in kwargs.items():
                if key not in [
                    "model",
                    "messages",
                    "system",
                    "temperature",
                    "max_tokens",
                ]:
                    params[key] = value

            # Make the API call
            result = client.messages.create(**params)

            return {
                "content": result.content[0].text,
                "model": model,
                "provider": "anthropic",
                "raw_response": result.model_dump(),
            }

        except Exception as e:
            logger.error(f"Anthropic API request failed: {str(e)}")
            raise ValueError(f"Anthropic API request failed: {str(e)}")

    async def _generate_mistral(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate a completion using Mistral's API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_keys['mistral']}",
        }

        # Configure request payload
        payload = {"model": model, "messages": messages, "temperature": temperature}

        # Add max_tokens if specified
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Add additional parameters
        for key, value in kwargs.items():
            payload[key] = value

        try:
            response = self.session.post(
                self.endpoints["mistral"],
                headers=headers,
                json=payload,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            response.raise_for_status()
            result = response.json()

            # Extract and return the response content
            if "choices" in result and result["choices"]:
                return {
                    "content": result["choices"][0]["message"]["content"],
                    "model": model,
                    "provider": "mistral",
                    "raw_response": result,
                }
            else:
                raise ValueError("Unexpected response format from Mistral API")

        except requests.exceptions.RequestException as e:
            logger.error(f"Mistral API request failed: {str(e)}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response: {e.response.text}")
            raise ValueError(f"Mistral API request failed: {str(e)}")

    def get_available_models(self, provider: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """
        Get available models for the specified provider or all providers

        Args:
            provider: Optional provider name to filter models

        Returns:
            Dictionary of provider -> list of models
        """
        from ai_models import (
            ANTHROPIC_MODELS,
            GROQ_MODELS,
            MISTRAL_MODELS,
            OPENAI_MODELS,
            XAI_MODELS,
        )

        all_models = {
            "openai": list(OPENAI_MODELS.values()),
            "groq": list(GROQ_MODELS.values()),
            "anthropic": list(ANTHROPIC_MODELS.values()),
            "mistral": list(MISTRAL_MODELS.values()),
            "xai": list(XAI_MODELS.values()),
        }

        if provider:
            if provider in all_models:
                return {provider: all_models[provider]}
            else:
                return {}
        else:
            return all_models
