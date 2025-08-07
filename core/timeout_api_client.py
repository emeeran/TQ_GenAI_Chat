"""
Timeout-Aware API Client for TQ GenAI Chat

This module provides timeout and cancellation support for API requests,
implementing Flask integration for Task 1.2.4.

Features:
- Provider-specific timeout configurations
- Request cancellation on client disconnect
- Comprehensive error handling and user feedback
- Performance metrics and monitoring
- Graceful degradation strategies

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import json
import logging
import time
from typing import Any, Optional

import aiohttp
import requests
from flask import current_app, g, has_request_context

from .timeout_manager import TimeoutManager, TimeoutReason, get_timeout_manager

logger = logging.getLogger(__name__)


class TimeoutAwareAPIClient:
    """API client with comprehensive timeout and cancellation support"""

    def __init__(self, timeout_manager: Optional[TimeoutManager] = None):
        self.timeout_manager = timeout_manager or get_timeout_manager()
        self._session: Optional[requests.Session] = None
        self._aio_session: Optional[aiohttp.ClientSession] = None

    @property
    def session(self) -> requests.Session:
        """Get or create requests session"""
        if self._session is None:
            self._session = self._create_session()
        return self._session

    @property
    def aio_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._aio_session is None:
            self._aio_session = self._create_aio_session()
        return self._aio_session

    def _create_session(self) -> requests.Session:
        """Create configured requests session"""
        session = requests.Session()

        # Configure retry strategy
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )

        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _create_aio_session(self) -> aiohttp.ClientSession:
        """Create configured aiohttp session"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        return aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "TQ-GenAI-Chat/1.0"},
        )

    async def make_request_async(
        self,
        provider: str,
        method: str,
        url: str,
        headers: Optional[dict[str, str]] = None,
        data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make an async HTTP request with timeout and cancellation support"""

        async with self.timeout_manager.request_context(
            provider=provider, operation_name=f"{method.upper()} {url}"
        ) as context:
            if not context:
                # Timeout manager disabled, fallback to simple request
                return await self._make_simple_async_request(method, url, headers, data, **kwargs)

            config = context.config
            client_id = context.client_id

            # Set up timeouts
            timeout = aiohttp.ClientTimeout(
                total=config.request_timeout,
                connect=config.connection_timeout,
                sock_read=config.read_timeout,
            )

            try:
                # Check for early cancellation
                if context.is_cancelled():
                    raise asyncio.CancelledError("Request was cancelled before starting")

                logger.debug(
                    f"Making async request to {provider}: {method} {url} "
                    f"(timeout: {config.request_timeout}s, client: {client_id})"
                )

                # Prepare request
                request_kwargs = {"timeout": timeout, "headers": headers or {}, **kwargs}

                if data:
                    if method.upper() in ["POST", "PUT", "PATCH"]:
                        request_kwargs["json"] = data
                    else:
                        request_kwargs["params"] = data

                # Make the request with cancellation support
                async with self.aio_session.request(method, url, **request_kwargs) as response:
                    # Check for cancellation during request
                    if context.is_cancelled():
                        raise asyncio.CancelledError("Request was cancelled during execution")

                    # Check for fast-fail conditions
                    elapsed = time.time() - context.start_time
                    if elapsed > config.fast_fail_threshold and response.status >= 400:
                        logger.warning(
                            f"Fast-failing request to {provider} after {elapsed:.2f}s "
                            f"(status: {response.status})"
                        )
                        context.cancel(TimeoutReason.PROVIDER_TIMEOUT)
                        raise aiohttp.ClientError(f"Fast-fail timeout for {provider}")

                    # Read response
                    response_text = await response.text()

                    # Final cancellation check
                    if context.is_cancelled():
                        raise asyncio.CancelledError("Request was cancelled after completion")

                    # Handle response
                    if response.status >= 400:
                        error_msg = f"HTTP {response.status}: {response_text}"
                        logger.error(f"API error from {provider}: {error_msg}")
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=error_msg,
                        )

                    # Parse JSON response
                    try:
                        result = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON response from {provider}: {str(e)}")
                        raise ValueError(f"Invalid JSON response from {provider}")

                    logger.debug(
                        f"Successful request to {provider} completed in "
                        f"{time.time() - context.start_time:.2f}s"
                    )

                    return result

            except asyncio.TimeoutError:
                logger.warning(f"Request to {provider} timed out after {config.request_timeout}s")
                context.cancel(TimeoutReason.PROVIDER_TIMEOUT)
                raise

            except asyncio.CancelledError:
                logger.info(
                    f"Request to {provider} was cancelled (reason: {context.cancel_reason})"
                )
                raise

            except Exception as e:
                logger.error(f"Request to {provider} failed: {str(e)}")
                # Record as timeout if it took longer than expected
                if time.time() - context.start_time > config.request_timeout:
                    context.cancel(TimeoutReason.PROVIDER_TIMEOUT)
                raise

    def make_request_sync(
        self,
        provider: str,
        method: str,
        url: str,
        headers: Optional[dict[str, str]] = None,
        data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make a synchronous HTTP request with timeout support"""

        config = self.timeout_manager.get_provider_config(provider)
        start_time = time.time()

        # Configure timeouts
        timeout = (config.connection_timeout, config.read_timeout)

        try:
            logger.debug(
                f"Making sync request to {provider}: {method} {url} "
                f"(timeout: {config.request_timeout}s)"
            )

            # Prepare request
            request_kwargs = {"timeout": timeout, "headers": headers or {}, **kwargs}

            if data:
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    request_kwargs["json"] = data
                else:
                    request_kwargs["params"] = data

            # Make the request
            response = self.session.request(method, url, **request_kwargs)

            # Handle response
            elapsed = time.time() - start_time

            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"API error from {provider}: {error_msg}")

                # Record timeout if applicable
                if elapsed > config.request_timeout:
                    self.timeout_manager.metrics.record_timeout(
                        provider, TimeoutReason.PROVIDER_TIMEOUT, elapsed
                    )

                raise requests.RequestException(error_msg)

            # Parse JSON response
            try:
                result = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from {provider}: {str(e)}")
                raise ValueError(f"Invalid JSON response from {provider}")

            logger.debug(f"Successful sync request to {provider} completed in {elapsed:.2f}s")

            return result

        except requests.Timeout:
            elapsed = time.time() - start_time
            logger.warning(f"Sync request to {provider} timed out after {elapsed:.2f}s")
            self.timeout_manager.metrics.record_timeout(
                provider, TimeoutReason.PROVIDER_TIMEOUT, elapsed
            )
            raise

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Sync request to {provider} failed after {elapsed:.2f}s: {str(e)}")

            # Record as timeout if it took longer than expected
            if elapsed > config.request_timeout:
                self.timeout_manager.metrics.record_timeout(
                    provider, TimeoutReason.PROVIDER_TIMEOUT, elapsed
                )
            raise

    async def _make_simple_async_request(
        self,
        method: str,
        url: str,
        headers: Optional[dict[str, str]],
        data: Optional[dict[str, Any]],
        **kwargs,
    ) -> dict[str, Any]:
        """Fallback simple async request when timeout manager is disabled"""
        request_kwargs = {"headers": headers or {}, **kwargs}

        if data:
            if method.upper() in ["POST", "PUT", "PATCH"]:
                request_kwargs["json"] = data
            else:
                request_kwargs["params"] = data

        async with self.aio_session.request(method, url, **request_kwargs) as response:
            response.raise_for_status()
            return await response.json()

    def close(self):
        """Close all sessions"""
        if self._session:
            self._session.close()
            self._session = None

        if self._aio_session and not self._aio_session.closed:
            # Note: aiohttp session should be closed in an async context
            # This is a synchronous cleanup, may not be ideal
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._aio_session.close())
                else:
                    loop.run_until_complete(self._aio_session.close())
            except Exception as e:
                logger.warning(f"Error closing aiohttp session: {str(e)}")
            finally:
                self._aio_session = None

    def __del__(self):
        """Cleanup on deletion"""
        self.close()


class TimeoutAwareProviderClient:
    """Provider-specific client with timeout support"""

    def __init__(self, provider: str, api_config: dict[str, Any]):
        self.provider = provider
        self.api_config = api_config
        self.client = TimeoutAwareAPIClient()
        self.timeout_manager = get_timeout_manager()

        # Provider-specific configurations
        self.endpoint = api_config.get("endpoint", "")
        self.api_key = api_config.get("key", "")
        self.default_model = api_config.get("default", "")
        self.fallback_model = api_config.get("fallback", "")

    def _get_headers(self) -> dict[str, str]:
        """Get provider-specific headers"""
        headers = {"Content-Type": "application/json"}

        if self.provider == "anthropic":
            headers.update({"x-api-key": self.api_key, "anthropic-version": "2023-06-01"})
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def chat_completion_async(
        self, messages: list[dict[str, str]], model: Optional[str] = None, **kwargs
    ) -> dict[str, Any]:
        """Make async chat completion request with timeout support"""

        model = model or self.default_model
        headers = self._get_headers()

        # Prepare payload based on provider
        if self.provider == "anthropic":
            # Anthropic uses different format
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            user_messages = [msg for msg in messages if msg.get("role") != "system"]

            payload = {
                "model": model,
                "messages": user_messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
                **kwargs,
            }

            if system_messages:
                payload["system"] = system_messages[0]["content"]
        else:
            # Standard OpenAI format
            payload = {"model": model, "messages": messages, **kwargs}

        return await self.client.make_request_async(
            provider=self.provider, method="POST", url=self.endpoint, headers=headers, data=payload
        )

    def chat_completion_sync(
        self, messages: list[dict[str, str]], model: Optional[str] = None, **kwargs
    ) -> dict[str, Any]:
        """Make synchronous chat completion request with timeout support"""

        model = model or self.default_model
        headers = self._get_headers()

        # Prepare payload (same logic as async)
        if self.provider == "anthropic":
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            user_messages = [msg for msg in messages if msg.get("role") != "system"]

            payload = {
                "model": model,
                "messages": user_messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
                **kwargs,
            }

            if system_messages:
                payload["system"] = system_messages[0]["content"]
        else:
            payload = {"model": model, "messages": messages, **kwargs}

        return self.client.make_request_sync(
            provider=self.provider, method="POST", url=self.endpoint, headers=headers, data=payload
        )

    async def get_models_async(self) -> dict[str, Any]:
        """Get available models with timeout support"""
        headers = self._get_headers()

        # Different endpoints for different providers
        if self.provider == "openai":
            url = "https://api.openai.com/v1/models"
        elif self.provider == "anthropic":
            # Anthropic doesn't have a models endpoint, return static list
            return {
                "data": [
                    {"id": "claude-3-5-sonnet-latest", "object": "model"},
                    {"id": "claude-3-sonnet-20240229", "object": "model"},
                    {"id": "claude-3-haiku-20240307", "object": "model"},
                ]
            }
        else:
            # Fallback to standard models endpoint
            url = f"{self.endpoint.replace('/chat/completions', '/models')}"

        return await self.client.make_request_async(
            provider=self.provider, method="GET", url=url, headers=headers
        )

    def close(self):
        """Close the client"""
        self.client.close()


# Flask integration helpers
def init_timeout_aware_clients(app):
    """Initialize timeout-aware clients for Flask app"""
    from config.settings import API_CONFIGS

    if not hasattr(app, "timeout_clients"):
        app.timeout_clients = {}

    # Initialize clients for each provider
    for provider, config in API_CONFIGS.items():
        if config.get("key"):  # Only if API key is available
            app.timeout_clients[provider] = TimeoutAwareProviderClient(provider, config)

    logger.info(f"Initialized timeout-aware clients for {len(app.timeout_clients)} providers")


def get_timeout_client(provider: str) -> Optional[TimeoutAwareProviderClient]:
    """Get timeout-aware client for a provider"""
    if has_request_context() and hasattr(current_app, "timeout_clients"):
        return current_app.timeout_clients.get(provider)
    return None


def handle_client_disconnect():
    """Handle client disconnect - cancel all requests for this client"""
    if has_request_context():
        client_id = getattr(g, "client_id", None)
        if client_id:
            manager = get_timeout_manager()
            cancelled_count = manager.cancel_client_requests(client_id)
            if cancelled_count > 0:
                logger.info(
                    f"Cancelled {cancelled_count} requests for disconnected client {client_id}"
                )
