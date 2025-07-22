import asyncio
import time
from functools import lru_cache

import aiohttp
from aiohttp import ClientTimeout


class RequestManager:
    """Optimized request handling with connection pooling"""

    def __init__(self):
        self.timeout = ClientTimeout(total=60, connect=10, sock_read=50)
        self.session = None
        self.rate_limits = {}

        # Initialize connection pool
        self.pool = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(
                limit=100,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
        )

    @lru_cache(maxsize=100)
    async def make_request(self, endpoint: str, headers: dict, payload: dict) -> dict:
        """Make API request with caching and retries"""
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # Check rate limits
                if not self._check_rate_limit(endpoint):
                    raise Exception("Rate limit exceeded")

                async with self.pool.post(
                    endpoint,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 60))
                        await asyncio.sleep(retry_after)
                        retry_count += 1
                        continue

                    response.raise_for_status()
                    return await response.json()

            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise e
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff

    def _check_rate_limit(self, endpoint: str) -> bool:
        """Check and update rate limits"""
        now = time.time()
        if endpoint not in self.rate_limits:
            self.rate_limits[endpoint] = []

        # Clean old requests
        self.rate_limits[endpoint] = [
            t for t in self.rate_limits[endpoint]
            if t > now - 60
        ]

        if len(self.rate_limits[endpoint]) >= 60:
            return False

        self.rate_limits[endpoint].append(now)
        return True

    async def close(self):
        """Clean up resources"""
        if self.pool:
            await self.pool.close()

# Initialize global request manager
request_manager = RequestManager()
