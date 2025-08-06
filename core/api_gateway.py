"""
API Gateway with advanced routing, rate limiting, authentication, and monitoring.
Provides centralized entry point for all API requests with comprehensive controls.
"""

import asyncio
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp
import redis.asyncio as redis
from flask import Flask, g, jsonify, request

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""

    requests: int
    window_seconds: int
    burst_limit: int = None
    scope: str = "global"  # global, user, ip, api_key

    def __post_init__(self):
        if self.burst_limit is None:
            self.burst_limit = self.requests * 2


@dataclass
class Route:
    """API route configuration."""

    path: str
    methods: list[str]
    target: str
    rate_limits: list[RateLimitRule] = field(default_factory=list)
    auth_required: bool = True
    timeout: int = 30
    retries: int = 3
    circuit_breaker: bool = True
    cache_ttl: int = 0  # 0 = no caching


@dataclass
class ApiKey:
    """API key configuration."""

    key: str
    name: str
    permissions: set[str]
    rate_limits: list[RateLimitRule] = field(default_factory=list)
    expires_at: datetime | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket."""
        now = time.time()

        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class CircuitBreaker:
    """Circuit breaker for upstream service protection."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == "closed":
            return True

        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                return True
            return False

        # half-open state
        return True

    def record_success(self):
        """Record successful request."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class RateLimiter:
    """Advanced rate limiter with multiple strategies."""

    def __init__(self, redis_client: redis.Redis = None):
        self.redis_client = redis_client
        self.token_buckets: dict[str, TokenBucket] = {}
        self.sliding_windows: dict[str, list[float]] = {}

    async def check_rate_limit(self, key: str, rule: RateLimitRule) -> tuple[bool, dict]:
        """Check if request is within rate limit."""
        now = time.time()

        if self.redis_client:
            return await self._check_redis_rate_limit(key, rule, now)
        else:
            return self._check_memory_rate_limit(key, rule, now)

    async def _check_redis_rate_limit(
        self, key: str, rule: RateLimitRule, now: float
    ) -> tuple[bool, dict]:
        """Redis-based sliding window rate limiting."""
        window_key = f"rate_limit:{key}:{rule.window_seconds}"

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(window_key, 0, now - rule.window_seconds)

        # Count current requests
        pipe.zcard(window_key)

        # Add current request
        pipe.zadd(window_key, {str(now): now})

        # Set expiration
        pipe.expire(window_key, rule.window_seconds + 1)

        results = await pipe.execute()
        current_requests = results[1]

        headers = {
            "X-RateLimit-Limit": str(rule.requests),
            "X-RateLimit-Remaining": str(max(0, rule.requests - current_requests)),
            "X-RateLimit-Reset": str(int(now + rule.window_seconds)),
        }

        if current_requests <= rule.requests:
            return True, headers
        else:
            headers["Retry-After"] = str(rule.window_seconds)
            return False, headers

    def _check_memory_rate_limit(
        self, key: str, rule: RateLimitRule, now: float
    ) -> tuple[bool, dict]:
        """Memory-based token bucket rate limiting."""
        bucket_key = f"{key}:{rule.window_seconds}"

        if bucket_key not in self.token_buckets:
            # Create new token bucket
            refill_rate = rule.requests / rule.window_seconds
            self.token_buckets[bucket_key] = TokenBucket(rule.requests, refill_rate)

        bucket = self.token_buckets[bucket_key]
        can_proceed = bucket.consume(1)

        headers = {
            "X-RateLimit-Limit": str(rule.requests),
            "X-RateLimit-Remaining": str(int(bucket.tokens)),
            "X-RateLimit-Reset": str(int(now + rule.window_seconds)),
        }

        if not can_proceed:
            headers["Retry-After"] = str(rule.window_seconds)

        return can_proceed, headers


class AuthManager:
    """Authentication and authorization manager."""

    def __init__(self):
        self.api_keys: dict[str, ApiKey] = {}
        self.jwt_secret = secrets.token_urlsafe(32)

    def add_api_key(self, api_key: ApiKey):
        """Add API key to manager."""
        self.api_keys[api_key.key] = api_key
        logger.info(f"Added API key: {api_key.name}")

    def validate_api_key(self, key: str) -> ApiKey | None:
        """Validate API key and return key info."""
        api_key = self.api_keys.get(key)

        if not api_key:
            return None

        if not api_key.is_active:
            return None

        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            return None

        return api_key

    def check_permission(self, api_key: ApiKey, permission: str) -> bool:
        """Check if API key has required permission."""
        return permission in api_key.permissions or "admin" in api_key.permissions

    def generate_api_key(self, name: str, permissions: set[str]) -> ApiKey:
        """Generate new API key."""
        key = secrets.token_urlsafe(32)
        api_key = ApiKey(key=key, name=name, permissions=permissions)
        self.add_api_key(api_key)
        return api_key


class RequestRouter:
    """Intelligent request routing with load balancing."""

    def __init__(self):
        self.routes: list[Route] = []
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.response_cache: dict[str, tuple] = {}  # (response, timestamp)

    def add_route(self, route: Route):
        """Add route to router."""
        self.routes.append(route)

        if route.circuit_breaker:
            self.circuit_breakers[route.target] = CircuitBreaker()

        logger.info(f"Added route: {route.path} -> {route.target}")

    def find_route(self, path: str, method: str) -> Route | None:
        """Find matching route for request."""
        for route in self.routes:
            if self._match_path(route.path, path) and method in route.methods:
                return route
        return None

    def _match_path(self, pattern: str, path: str) -> bool:
        """Match path pattern with wildcards."""
        # Simple wildcard matching
        if "*" in pattern:
            parts = pattern.split("*")
            return path.startswith(parts[0]) and path.endswith(parts[-1])
        return pattern == path

    async def route_request(self, route: Route, request_data: dict) -> dict:
        """Route request to target service."""
        target = route.target

        # Check circuit breaker
        if route.circuit_breaker and target in self.circuit_breakers:
            circuit_breaker = self.circuit_breakers[target]
            if not circuit_breaker.can_execute():
                raise Exception("Circuit breaker is open")

        # Check cache
        if route.cache_ttl > 0:
            cache_key = self._generate_cache_key(route, request_data)
            cached_response = self._get_cached_response(cache_key, route.cache_ttl)
            if cached_response:
                return cached_response

        # Make request with retries
        for attempt in range(route.retries + 1):
            try:
                response = await self._make_request(target, request_data, route.timeout)

                # Record success for circuit breaker
                if route.circuit_breaker and target in self.circuit_breakers:
                    self.circuit_breakers[target].record_success()

                # Cache response
                if route.cache_ttl > 0:
                    cache_key = self._generate_cache_key(route, request_data)
                    self._cache_response(cache_key, response)

                return response

            except Exception as e:
                # Record failure for circuit breaker
                if route.circuit_breaker and target in self.circuit_breakers:
                    self.circuit_breakers[target].record_failure()

                if attempt == route.retries:
                    raise e

                # Exponential backoff
                await asyncio.sleep(2**attempt)

        raise Exception("Max retries exceeded")

    async def _make_request(self, target: str, request_data: dict, timeout: int) -> dict:
        """Make HTTP request to target service."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.post(target, json=request_data) as response:
                response.raise_for_status()
                return await response.json()

    def _generate_cache_key(self, route: Route, request_data: dict) -> str:
        """Generate cache key for request."""
        key_data = f"{route.path}:{json.dumps(request_data, sort_keys=True)}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()  # nosec B324

    def _get_cached_response(self, cache_key: str, ttl: int) -> dict | None:
        """Get cached response if still valid."""
        if cache_key in self.response_cache:
            response, timestamp = self.response_cache[cache_key]
            if time.time() - timestamp < ttl:
                return response
            else:
                del self.response_cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, response: dict):
        """Cache response with timestamp."""
        self.response_cache[cache_key] = (response, time.time())


class MetricsCollector:
    """Collect and aggregate API gateway metrics."""

    def __init__(self):
        self.request_counts: dict[str, int] = {}
        self.response_times: dict[str, list[float]] = {}
        self.error_counts: dict[str, int] = {}
        self.status_codes: dict[str, dict[int, int]] = {}

    def record_request(self, route: str, response_time: float, status_code: int):
        """Record request metrics."""
        # Request count
        self.request_counts[route] = self.request_counts.get(route, 0) + 1

        # Response time
        if route not in self.response_times:
            self.response_times[route] = []
        self.response_times[route].append(response_time)

        # Keep only last 1000 response times
        if len(self.response_times[route]) > 1000:
            self.response_times[route] = self.response_times[route][-1000:]

        # Status codes
        if route not in self.status_codes:
            self.status_codes[route] = {}
        self.status_codes[route][status_code] = self.status_codes[route].get(status_code, 0) + 1

        # Error count
        if status_code >= 400:
            self.error_counts[route] = self.error_counts.get(route, 0) + 1

    def get_metrics(self) -> dict:
        """Get aggregated metrics."""
        metrics = {
            "total_requests": sum(self.request_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "routes": {},
        }

        for route in self.request_counts:
            route_metrics = {
                "requests": self.request_counts.get(route, 0),
                "errors": self.error_counts.get(route, 0),
                "status_codes": self.status_codes.get(route, {}),
            }

            # Calculate response time statistics
            if route in self.response_times and self.response_times[route]:
                times = self.response_times[route]
                route_metrics["response_time"] = {
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "p95": (
                        sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times)
                    ),
                }

            metrics["routes"][route] = route_metrics

        return metrics


class ApiGateway:
    """Main API Gateway class."""

    def __init__(self, config: dict = None):
        self.config = config or {}

        # Initialize components
        self.redis_client = None
        self.rate_limiter = RateLimiter()
        self.auth_manager = AuthManager()
        self.router = RequestRouter()
        self.metrics = MetricsCollector()

        # Default configuration
        self.default_rate_limits = [
            RateLimitRule(requests=100, window_seconds=60, scope="ip"),
            RateLimitRule(requests=1000, window_seconds=3600, scope="api_key"),
        ]

    async def start(self):
        """Initialize API Gateway."""
        # Initialize Redis if configured
        redis_url = self.config.get("redis_url")
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
            self.rate_limiter.redis_client = self.redis_client
            logger.info("Connected to Redis for rate limiting")

        # Load configuration
        await self._load_configuration()

        logger.info("API Gateway started")

    async def stop(self):
        """Cleanup API Gateway."""
        if self.redis_client:
            await self.redis_client.close()
        logger.info("API Gateway stopped")

    async def _load_configuration(self):
        """Load gateway configuration."""
        # Add default routes
        self.router.add_route(
            Route(
                path="/api/chat",
                methods=["POST"],
                target="http://localhost:5000/chat",
                rate_limits=[RateLimitRule(requests=60, window_seconds=60)],
            )
        )

        self.router.add_route(
            Route(
                path="/api/upload",
                methods=["POST"],
                target="http://localhost:5000/upload",
                rate_limits=[RateLimitRule(requests=10, window_seconds=60)],
            )
        )

        # Add admin API key
        admin_key = self.auth_manager.generate_api_key(
            name="admin", permissions={"admin", "read", "write"}
        )
        logger.info(f"Generated admin API key: {admin_key.key}")

    def create_flask_middleware(self, app: Flask):
        """Create Flask middleware for the gateway."""

        @app.before_request
        async def gateway_middleware():
            """Process request through API gateway."""
            start_time = time.time()

            try:
                # Find matching route
                route = self.router.find_route(request.path, request.method)
                if not route:
                    return jsonify({"error": "Route not found"}), 404

                # Authenticate request
                if route.auth_required:
                    api_key = await self._authenticate_request()
                    if not api_key:
                        return jsonify({"error": "Authentication required"}), 401
                    g.api_key = api_key

                # Check rate limits
                rate_limit_key = self._get_rate_limit_key(route)
                for rule in route.rate_limits + self.default_rate_limits:
                    allowed, headers = await self.rate_limiter.check_rate_limit(
                        rate_limit_key, rule
                    )

                    # Add rate limit headers to response
                    for key, value in headers.items():
                        g.setdefault("response_headers", {})[key] = value

                    if not allowed:
                        return jsonify({"error": "Rate limit exceeded"}), 429, headers

                # Store route for later processing
                g.route = route
                g.start_time = start_time

            except Exception as e:
                logger.error(f"Gateway middleware error: {e}")
                return jsonify({"error": "Gateway error"}), 500

        @app.after_request
        def after_request(response):
            """Record metrics after request."""
            if hasattr(g, "route") and hasattr(g, "start_time"):
                response_time = time.time() - g.start_time
                self.metrics.record_request(g.route.path, response_time, response.status_code)

            # Add response headers
            if hasattr(g, "response_headers"):
                for key, value in g.response_headers.items():
                    response.headers[key] = value

            return response

        # Add gateway endpoints
        @app.route("/gateway/metrics")
        async def get_metrics():
            """Get gateway metrics."""
            api_key = g.get("api_key")
            if not api_key or not self.auth_manager.check_permission(api_key, "read"):
                return jsonify({"error": "Insufficient permissions"}), 403

            return jsonify(self.metrics.get_metrics())

        @app.route("/gateway/health")
        async def health_check():
            """Gateway health check."""
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "routes": len(self.router.routes),
                }
            )

    async def _authenticate_request(self) -> ApiKey | None:
        """Authenticate API request."""
        # Check API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return self.auth_manager.validate_api_key(api_key)

        # Check API key in query parameter
        api_key = request.args.get("api_key")
        if api_key:
            return self.auth_manager.validate_api_key(api_key)

        return None

    def _get_rate_limit_key(self, route: Route) -> str:
        """Generate rate limit key based on scope."""
        api_key = g.get("api_key")

        if api_key:
            return f"api_key:{api_key.key}"
        else:
            return f"ip:{request.remote_addr}"


# Global gateway instance
_gateway = None


def get_gateway(config: dict = None) -> ApiGateway:
    """Get or create the global gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = ApiGateway(config)
    return _gateway


# Example usage
if __name__ == "__main__":
    import asyncio

    from flask import Flask

    async def main():
        # Create gateway
        config = {"redis_url": "redis://localhost:6379/0"}

        gateway = get_gateway(config)
        await gateway.start()

        # Create Flask app
        app = Flask(__name__)
        gateway.create_flask_middleware(app)

        # Add sample route
        @app.route("/api/test")
        def test():
            return jsonify({"message": "Hello from API Gateway!"})

        # In production, you would run:
        # app.run(host='0.0.0.0', port=8080)

        await gateway.stop()

    asyncio.run(main())
