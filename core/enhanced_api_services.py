"""
Enhanced API Services with Timeout Support

This module enhances the existing API services with comprehensive timeout
and cancellation support implementing Task 1.2.4.

Features:
- Per-provider timeout configuration
- Request cancellation on client disconnect
- Graceful degradation and fallback strategies
- Comprehensive error handling and user feedback
- Metrics for timeout occurrences

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import logging
import time
from typing import Any, Optional

from .api_services import APIServices
from .timeout_api_client import TimeoutAwareProviderClient, get_timeout_client
from .timeout_manager import TimeoutReason, get_timeout_manager

logger = logging.getLogger(__name__)


class EnhancedAPIServices(APIServices):
    """Enhanced API services with timeout and cancellation support"""

    def __init__(self):
        super().__init__()
        self.timeout_manager = get_timeout_manager()
        self.fallback_strategies = self._initialize_fallback_strategies()

    def _initialize_fallback_strategies(self) -> dict[str, list[str]]:
        """Initialize fallback provider strategies"""
        return {
            "openai": ["groq", "mistral"],
            "groq": ["openai", "deepseek"],
            "anthropic": ["openai", "groq"],
            "mistral": ["groq", "openai"],
            "xai": ["groq", "openai"],
            "deepseek": ["groq", "openai"],
        }

    async def generate_response_with_timeout(
        self, provider: str, model: str, messages: list[dict[str, str]], **kwargs
    ) -> dict[str, Any]:
        """Generate response with timeout support and fallback strategies"""

        # Try to get timeout-aware client first
        timeout_client = get_timeout_client(provider)
        if timeout_client:
            return await self._generate_with_timeout_client(
                timeout_client, provider, model, messages, **kwargs
            )

        # Fallback to enhanced legacy method with timeout tracking
        return await self._generate_with_timeout_tracking(provider, model, messages, **kwargs)

    async def _generate_with_timeout_client(
        self,
        client: TimeoutAwareProviderClient,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        **kwargs,
    ) -> dict[str, Any]:
        """Generate response using timeout-aware client"""

        try:
            logger.debug(f"Using timeout-aware client for {provider}:{model}")

            # Make the request with full timeout support
            response = await client.chat_completion_async(messages=messages, model=model, **kwargs)

            # Validate and return response
            return self._validate_and_format_response(provider, response)

        except asyncio.TimeoutError:
            logger.warning(f"Timeout occurred for {provider}:{model}")
            return await self._handle_timeout_with_fallback(provider, model, messages, **kwargs)

        except asyncio.CancelledError:
            logger.info(f"Request cancelled for {provider}:{model}")
            raise

        except Exception as e:
            logger.error(f"Error with timeout client {provider}: {str(e)}")
            return await self._handle_error_with_fallback(provider, model, messages, e, **kwargs)

    async def _generate_with_timeout_tracking(
        self, provider: str, model: str, messages: list[dict[str, str]], **kwargs
    ) -> dict[str, Any]:
        """Generate response with timeout tracking (fallback method)"""

        config = self.timeout_manager.get_provider_config(provider)
        start_time = time.time()

        try:
            # Use existing API service methods with timeout
            async with asyncio.timeout(config.request_timeout):
                if provider == "openai":
                    response = await self._generate_openai(model, messages, **kwargs)
                elif provider == "groq":
                    response = await self._generate_groq(model, messages, **kwargs)
                elif provider == "anthropic":
                    response = await self._generate_anthropic(model, messages, **kwargs)
                elif provider == "mistral":
                    response = await self._generate_mistral(model, messages, **kwargs)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")

                return response

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.timeout_manager.metrics.record_timeout(
                provider, TimeoutReason.PROVIDER_TIMEOUT, duration
            )
            logger.warning(f"Provider {provider} timed out after {duration:.2f}s")
            return await self._handle_timeout_with_fallback(provider, model, messages, **kwargs)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error with provider {provider} after {duration:.2f}s: {str(e)}")
            return await self._handle_error_with_fallback(provider, model, messages, e, **kwargs)

    async def _handle_timeout_with_fallback(
        self, failed_provider: str, model: str, messages: list[dict[str, str]], **kwargs
    ) -> dict[str, Any]:
        """Handle timeout with graceful fallback to alternative providers"""

        fallback_providers = self.fallback_strategies.get(failed_provider, [])

        for fallback_provider in fallback_providers:
            try:
                logger.info(f"Attempting fallback from {failed_provider} to {fallback_provider}")

                # Check if fallback provider has API key
                if not self.api_keys.get(fallback_provider):
                    logger.warning(f"No API key for fallback provider {fallback_provider}")
                    continue

                # Use a shorter timeout for fallback attempts
                config = self.timeout_manager.get_provider_config(fallback_provider)
                fallback_timeout = min(config.request_timeout, 30.0)  # Max 30s for fallback

                async with asyncio.timeout(fallback_timeout):
                    # Get fallback model (use default for the provider)
                    fallback_model = self._get_fallback_model(fallback_provider, model)

                    # Make fallback request
                    response = await self._generate_with_timeout_tracking(
                        fallback_provider, fallback_model, messages, **kwargs
                    )

                    # Add fallback metadata
                    if isinstance(response, dict):
                        response["fallback_info"] = {
                            "original_provider": failed_provider,
                            "fallback_provider": fallback_provider,
                            "fallback_model": fallback_model,
                            "reason": "timeout",
                        }

                    logger.info(
                        f"Successfully failed over from {failed_provider} to {fallback_provider}"
                    )
                    return response

            except Exception as e:
                logger.warning(f"Fallback to {fallback_provider} also failed: {str(e)}")
                continue

        # All fallbacks failed
        raise Exception(
            f"Provider {failed_provider} timed out and all fallback providers failed. "
            f"Please try again or select a different provider."
        )

    async def _handle_error_with_fallback(
        self,
        failed_provider: str,
        model: str,
        messages: list[dict[str, str]],
        error: Exception,
        **kwargs,
    ) -> dict[str, Any]:
        """Handle error with graceful fallback"""

        # Check if this is a timeout-related error
        error_str = str(error).lower()
        is_timeout_error = any(
            keyword in error_str
            for keyword in [
                "timeout",
                "time out",
                "timed out",
                "connection timeout",
                "read timeout",
            ]
        )

        if is_timeout_error:
            return await self._handle_timeout_with_fallback(
                failed_provider, model, messages, **kwargs
            )

        # For non-timeout errors, still attempt fallback but with different logic
        fallback_providers = self.fallback_strategies.get(failed_provider, [])

        if fallback_providers:
            logger.info(f"Attempting fallback from {failed_provider} due to error: {str(error)}")

            try:
                fallback_provider = fallback_providers[0]  # Try first fallback
                if self.api_keys.get(fallback_provider):
                    fallback_model = self._get_fallback_model(fallback_provider, model)

                    response = await self._generate_with_timeout_tracking(
                        fallback_provider, fallback_model, messages, **kwargs
                    )

                    # Add fallback metadata
                    if isinstance(response, dict):
                        response["fallback_info"] = {
                            "original_provider": failed_provider,
                            "fallback_provider": fallback_provider,
                            "fallback_model": fallback_model,
                            "reason": "error",
                            "original_error": str(error),
                        }

                    return response
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")

        # Re-raise original error if no fallback worked
        raise error

    def _get_fallback_model(self, provider: str, original_model: str) -> str:
        """Get appropriate fallback model for a provider"""
        # Provider default models (from API_CONFIGS)
        defaults = {
            "openai": "gpt-4o-mini",
            "groq": "deepseek-r1-distill-llama-70b",
            "anthropic": "claude-3-5-sonnet-latest",
            "mistral": "codestral-latest",
            "xai": "grok-2-latest",
            "deepseek": "deepseek-chat",
        }

        return defaults.get(provider, original_model)

    def _validate_and_format_response(
        self, provider: str, response: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate and format API response"""

        if not isinstance(response, dict):
            raise ValueError(f"Invalid response format from {provider}")

        # Provider-specific validation
        if provider == "anthropic":
            if "content" not in response:
                raise ValueError(f"Missing content in {provider} response")

            # Convert Anthropic format to standard format
            if isinstance(response["content"], list) and response["content"]:
                content = response["content"][0]
                if isinstance(content, dict) and "text" in content:
                    return {
                        "choices": [{"message": {"content": content["text"], "role": "assistant"}}],
                        "provider": provider,
                        "raw_response": response,
                    }
        else:
            # Standard OpenAI format validation
            if "choices" not in response or not response["choices"]:
                raise ValueError(f"Missing choices in {provider} response")

        # Add provider metadata
        if "provider" not in response:
            response["provider"] = provider

        return response

    def get_timeout_metrics(self) -> dict[str, Any]:
        """Get comprehensive timeout and performance metrics"""
        base_metrics = self.timeout_manager.get_metrics()

        # Add provider-specific metrics
        provider_performance = {}
        for provider in self.api_keys.keys():
            config = self.timeout_manager.get_provider_config(provider)
            provider_performance[provider] = {
                "configured_timeout": config.request_timeout,
                "fast_fail_threshold": config.fast_fail_threshold,
                "max_retries": config.max_retries,
                "has_api_key": bool(self.api_keys.get(provider)),
                "fallback_providers": self.fallback_strategies.get(provider, []),
            }

        return {
            **base_metrics,
            "provider_performance": provider_performance,
            "fallback_strategies": self.fallback_strategies,
        }

    def configure_provider_timeout(
        self,
        provider: str,
        request_timeout: float,
        connection_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
    ):
        """Configure timeout settings for a specific provider"""

        from .timeout_manager import ProviderTimeoutConfig

        config = ProviderTimeoutConfig(
            provider_name=provider,
            request_timeout=request_timeout,
            connection_timeout=connection_timeout or (request_timeout * 0.2),
            read_timeout=read_timeout or (request_timeout * 0.8),
        )

        self.timeout_manager.configure_provider(provider, config)
        logger.info(f"Updated timeout configuration for {provider}: {request_timeout}s")


# Initialize enhanced API services
def create_enhanced_api_services() -> EnhancedAPIServices:
    """Create and return enhanced API services instance"""
    return EnhancedAPIServices()


# Flask integration
def init_enhanced_api_services(app):
    """Initialize enhanced API services for Flask app"""

    if not hasattr(app, "enhanced_api_services"):
        app.enhanced_api_services = create_enhanced_api_services()
        logger.info("Initialized enhanced API services with timeout support")

    return app.enhanced_api_services
