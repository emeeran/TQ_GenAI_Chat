"""
Optimized API client with connection pooling and advanced error handling.
"""

import asyncio
import logging
import time
from typing import Any

import aiohttp
from aiohttp import ClientTimeout, TCPConnector

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for API resilience."""

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker opened due to {self.failure_count} failures"
                )

            raise e


class OptimizedAPIClient:
    """
    High-performance API client with connection pooling, circuit breaker,
    and intelligent retry logic.
    """

    def __init__(self):
        self.session = None
        self.circuit_breakers = {}
        self.rate_limits = {}
        self._lock = asyncio.Lock()

        # Connection pool configuration
        self.connector = TCPConnector(
            limit=100,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=60,
            enable_cleanup_closed=True,
            limit_per_host=30,
        )

        self.timeout = ClientTimeout(total=60, connect=10, sock_read=50)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize the HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                connector=self.connector, timeout=self.timeout
            )
        return self.session

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

    def _get_circuit_breaker(self, endpoint: str) -> CircuitBreaker:
        """Get or create circuit breaker for endpoint."""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker()
        return self.circuit_breakers[endpoint]

    async def _check_rate_limit(self, endpoint: str) -> bool:
        """Check and update rate limits."""
        now = time.time()
        if endpoint not in self.rate_limits:
            self.rate_limits[endpoint] = []

        # Clean old requests
        self.rate_limits[endpoint] = [
            t for t in self.rate_limits[endpoint] if t > now - 60
        ]

        if len(self.rate_limits[endpoint]) >= 60:
            return False

        self.rate_limits[endpoint].append(now)
        return True

    async def make_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] = None,
        json_data: dict[str, Any] = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic and circuit breaker.
        """
        if not self.session:
            await self.start()

        circuit_breaker = self._get_circuit_breaker(url)

        async def _make_request():
            # Check rate limits
            if not await self._check_rate_limit(url):
                await asyncio.sleep(1)  # Brief backoff
                if not await self._check_rate_limit(url):
                    raise Exception("Rate limit exceeded")

            async with self.session.request(
                method=method, url=url, headers=headers or {}, json=json_data
            ) as response:
                if response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise Exception("Rate limit response")

                response.raise_for_status()
                return await response.json()

        # Execute with circuit breaker and retry logic
        retry_count = 0
        while retry_count < max_retries:
            try:
                return await circuit_breaker.call(_make_request)
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(
                        f"Request failed after {max_retries} retries: {str(e)}"
                    )
                    raise

                # Exponential backoff
                await asyncio.sleep(2**retry_count)
                logger.warning(
                    f"Retrying request {retry_count}/{max_retries}: {str(e)}"
                )


# Global instance
_api_client = None


async def get_api_client() -> OptimizedAPIClient:
    """Get or create global API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = OptimizedAPIClient()
        await _api_client.start()
    return _api_client


async def cleanup_api_client():
    """Cleanup global API client."""
    global _api_client
    if _api_client:
        await _api_client.close()
        _api_client = None
