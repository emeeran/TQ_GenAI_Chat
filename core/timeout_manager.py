"""
Timeout and Cancellation Manager for TQ GenAI Chat

This module implements Task 1.2.4: Timeout and Cancellation Support
- Per-provider timeout configuration
- Request cancellation on client disconnect
- Timeout error handling and user feedback
- Metrics for timeout occurrences
- Graceful degradation on timeouts

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TypeVar
from uuid import uuid4

from flask import g, has_request_context, request

T = TypeVar("T")
logger = logging.getLogger(__name__)


class TimeoutReason(Enum):
    """Reasons for timeout occurrence"""

    PROVIDER_TIMEOUT = "provider_timeout"
    CLIENT_DISCONNECT = "client_disconnect"
    SYSTEM_TIMEOUT = "system_timeout"
    USER_CANCELLED = "user_cancelled"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class ProviderTimeoutConfig:
    """Timeout configuration for individual providers"""

    provider_name: str
    request_timeout: float = 60.0  # Seconds for API request
    connection_timeout: float = 10.0  # Seconds for connection establishment
    read_timeout: float = 50.0  # Seconds for reading response
    retry_timeout: float = 180.0  # Total timeout including retries
    max_retries: int = 3
    backoff_factor: float = 1.5
    fast_fail_threshold: float = 5.0  # Fail fast if response time > threshold

    def __post_init__(self):
        """Validate configuration values"""
        if self.connection_timeout >= self.request_timeout:
            raise ValueError("Connection timeout must be less than request timeout")
        if self.read_timeout >= self.request_timeout:
            raise ValueError("Read timeout must be less than request timeout")


@dataclass
class TimeoutMetrics:
    """Metrics tracking for timeout occurrences"""

    total_requests: int = 0
    timed_out_requests: int = 0
    cancelled_requests: int = 0
    timeout_by_reason: dict[TimeoutReason, int] = field(default_factory=dict)
    timeout_by_provider: dict[str, int] = field(default_factory=dict)
    avg_timeout_duration: float = 0.0
    max_timeout_duration: float = 0.0
    last_timeout_time: Optional[float] = None

    def record_timeout(self, provider: str, reason: TimeoutReason, duration: float):
        """Record a timeout occurrence"""
        self.timed_out_requests += 1
        self.timeout_by_reason[reason] = self.timeout_by_reason.get(reason, 0) + 1
        self.timeout_by_provider[provider] = self.timeout_by_provider.get(provider, 0) + 1
        self.max_timeout_duration = max(self.max_timeout_duration, duration)

        # Update average (running average)
        if self.timed_out_requests == 1:
            self.avg_timeout_duration = duration
        else:
            self.avg_timeout_duration = (
                self.avg_timeout_duration * (self.timed_out_requests - 1) + duration
            ) / self.timed_out_requests

        self.last_timeout_time = time.time()

    def record_cancellation(self):
        """Record a request cancellation"""
        self.cancelled_requests += 1

    def record_request(self):
        """Record a new request"""
        self.total_requests += 1

    @property
    def timeout_rate(self) -> float:
        """Calculate timeout rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.timed_out_requests / self.total_requests) * 100

    @property
    def cancellation_rate(self) -> float:
        """Calculate cancellation rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.cancelled_requests / self.total_requests) * 100


class RequestTracker:
    """Track active requests for cancellation support"""

    def __init__(self):
        self.active_requests: dict[str, "TimeoutContext"] = {}
        self.lock = threading.RLock()

    def register(self, context: "TimeoutContext"):
        """Register a new request context"""
        with self.lock:
            self.active_requests[context.request_id] = context

    def unregister(self, request_id: str):
        """Unregister a completed request"""
        with self.lock:
            self.active_requests.pop(request_id, None)

    def cancel_all_for_client(self, client_id: str) -> int:
        """Cancel all requests for a specific client"""
        cancelled_count = 0
        with self.lock:
            for context in list(self.active_requests.values()):
                if context.client_id == client_id:
                    if context.cancel(TimeoutReason.CLIENT_DISCONNECT):
                        cancelled_count += 1
        return cancelled_count

    def get_active_count(self) -> int:
        """Get number of active requests"""
        with self.lock:
            return len(self.active_requests)

    def cleanup_completed(self):
        """Remove completed requests from tracking"""
        with self.lock:
            completed = [
                req_id
                for req_id, context in self.active_requests.items()
                if context.is_completed() or context.is_cancelled()
            ]
            for req_id in completed:
                self.active_requests.pop(req_id, None)


class TimeoutContext:
    """Context manager for tracking request timeouts and cancellation"""

    def __init__(
        self,
        provider: str,
        config: ProviderTimeoutConfig,
        metrics: TimeoutMetrics,
        tracker: RequestTracker,
        operation_name: str = "request",
        client_id: Optional[str] = None,
    ):
        self.request_id = str(uuid4())
        self.provider = provider
        self.config = config
        self.metrics = metrics
        self.tracker = tracker
        self.operation_name = operation_name
        self.client_id = client_id or self._get_client_id()

        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.cancelled = False
        self.cancel_reason: Optional[TimeoutReason] = None
        self.exception: Optional[Exception] = None
        self.result: Any = None

        # Async cancellation support
        self.cancel_event = asyncio.Event()
        self.timeout_task: Optional[asyncio.Task] = None

    def _get_client_id(self) -> str:
        """Get client ID from Flask request context"""
        if has_request_context():
            return getattr(g, "client_id", request.remote_addr or "unknown")
        return "background"

    def __enter__(self) -> "TimeoutContext":
        """Enter context - register for tracking"""
        self.tracker.register(self)
        self.metrics.record_request()

        # Set up signal handling for client disconnect detection
        if has_request_context():
            self._setup_disconnect_detection()

        logger.debug(
            f"Timeout context started for {self.provider}:{self.operation_name} "
            f"(timeout: {self.config.request_timeout}s, id: {self.request_id[:8]})"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - cleanup and record metrics"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        # Clean up timeout task
        if self.timeout_task and not self.timeout_task.done():
            self.timeout_task.cancel()

        # Record metrics
        if self.cancelled:
            self.metrics.record_cancellation()
            if self.cancel_reason:
                self.metrics.record_timeout(self.provider, self.cancel_reason, duration)
        elif exc_type is asyncio.TimeoutError:
            self.metrics.record_timeout(self.provider, TimeoutReason.PROVIDER_TIMEOUT, duration)

        # Unregister from tracker
        self.tracker.unregister(self.request_id)

        logger.debug(
            f"Timeout context completed for {self.provider}:{self.operation_name} "
            f"(duration: {duration:.2f}s, cancelled: {self.cancelled}, id: {self.request_id[:8]})"
        )

    def _setup_disconnect_detection(self):
        """Set up client disconnect detection"""
        # This would integrate with Flask-SocketIO or similar for real-time disconnect detection
        # For now, we'll use a simple approach checking if the request is still valid
        pass

    def cancel(self, reason: TimeoutReason = TimeoutReason.USER_CANCELLED) -> bool:
        """Cancel the request"""
        if self.cancelled or self.is_completed():
            return False

        self.cancelled = True
        self.cancel_reason = reason
        self.cancel_event.set()

        logger.info(
            f"Request cancelled: {self.provider}:{self.operation_name} "
            f"(reason: {reason.value}, id: {self.request_id[:8]})"
        )
        return True

    def is_cancelled(self) -> bool:
        """Check if request is cancelled"""
        return self.cancelled

    def is_completed(self) -> bool:
        """Check if request is completed"""
        return self.end_time is not None

    def is_timed_out(self) -> bool:
        """Check if request has timed out"""
        if self.is_completed():
            return False
        return (time.time() - self.start_time) > self.config.request_timeout

    def remaining_time(self) -> float:
        """Get remaining time before timeout"""
        if self.is_completed():
            return 0.0
        elapsed = time.time() - self.start_time
        return max(0.0, self.config.request_timeout - elapsed)

    async def wait_for_completion_or_cancellation(self):
        """Wait for either completion or cancellation"""
        try:
            await asyncio.wait_for(self.cancel_event.wait(), timeout=self.remaining_time())
        except asyncio.TimeoutError:
            self.cancel(TimeoutReason.PROVIDER_TIMEOUT)
            raise


class TimeoutManager:
    """Central manager for timeout and cancellation support"""

    def __init__(self):
        self.provider_configs: dict[str, ProviderTimeoutConfig] = {}
        self.metrics = TimeoutMetrics()
        self.tracker = RequestTracker()
        self.enabled = True

        # Load default configurations
        self._load_default_configs()

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()

    def _load_default_configs(self):
        """Load default timeout configurations for providers"""
        default_configs = {
            "openai": ProviderTimeoutConfig(
                provider_name="openai",
                request_timeout=60.0,
                connection_timeout=10.0,
                read_timeout=50.0,
                fast_fail_threshold=5.0,
            ),
            "groq": ProviderTimeoutConfig(
                provider_name="groq",
                request_timeout=30.0,  # Groq is typically faster
                connection_timeout=5.0,
                read_timeout=25.0,
                fast_fail_threshold=3.0,
            ),
            "anthropic": ProviderTimeoutConfig(
                provider_name="anthropic",
                request_timeout=90.0,  # Claude can be slower for complex responses
                connection_timeout=10.0,
                read_timeout=80.0,
                fast_fail_threshold=8.0,
            ),
            "mistral": ProviderTimeoutConfig(
                provider_name="mistral",
                request_timeout=45.0,
                connection_timeout=8.0,
                read_timeout=37.0,
                fast_fail_threshold=4.0,
            ),
            "xai": ProviderTimeoutConfig(
                provider_name="xai",
                request_timeout=75.0,
                connection_timeout=10.0,
                read_timeout=65.0,
                fast_fail_threshold=6.0,
            ),
            "deepseek": ProviderTimeoutConfig(
                provider_name="deepseek",
                request_timeout=50.0,
                connection_timeout=8.0,
                read_timeout=42.0,
                fast_fail_threshold=5.0,
            ),
        }

        self.provider_configs.update(default_configs)

    def configure_provider(self, provider: str, config: ProviderTimeoutConfig):
        """Configure timeout settings for a specific provider"""
        self.provider_configs[provider] = config
        logger.info(f"Configured timeout settings for provider: {provider}")

    def get_provider_config(self, provider: str) -> ProviderTimeoutConfig:
        """Get timeout configuration for a provider"""
        return self.provider_configs.get(
            provider,
            ProviderTimeoutConfig(provider_name=provider),  # Default config
        )

    @asynccontextmanager
    async def request_context(
        self, provider: str, operation_name: str = "request", client_id: Optional[str] = None
    ):
        """Create a timeout context for a request"""
        if not self.enabled:
            yield None
            return

        config = self.get_provider_config(provider)
        context = TimeoutContext(
            provider=provider,
            config=config,
            metrics=self.metrics,
            tracker=self.tracker,
            operation_name=operation_name,
            client_id=client_id,
        )

        with context:
            try:
                yield context
            except Exception as e:
                context.exception = e
                logger.error(f"Exception in timeout context {provider}:{operation_name}: {str(e)}")
                raise

    def cancel_client_requests(self, client_id: str) -> int:
        """Cancel all requests for a specific client"""
        return self.tracker.cancel_all_for_client(client_id)

    def get_metrics(self) -> dict[str, Any]:
        """Get timeout and cancellation metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "timed_out_requests": self.metrics.timed_out_requests,
            "cancelled_requests": self.metrics.cancelled_requests,
            "timeout_rate": self.metrics.timeout_rate,
            "cancellation_rate": self.metrics.cancellation_rate,
            "avg_timeout_duration": self.metrics.avg_timeout_duration,
            "max_timeout_duration": self.metrics.max_timeout_duration,
            "timeout_by_reason": {k.value: v for k, v in self.metrics.timeout_by_reason.items()},
            "timeout_by_provider": dict(self.metrics.timeout_by_provider),
            "active_requests": self.tracker.get_active_count(),
            "last_timeout_time": self.metrics.last_timeout_time,
        }

    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = TimeoutMetrics()
        logger.info("Timeout metrics reset")

    def _start_cleanup_task(self):
        """Start background cleanup task"""

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(30)  # Cleanup every 30 seconds
                    self.tracker.cleanup_completed()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")

        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop running, cleanup will be manual
            pass

    def shutdown(self):
        """Shutdown the timeout manager"""
        self.enabled = False

        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

        # Cancel all active requests
        with self.tracker.lock:
            for context in self.tracker.active_requests.values():
                context.cancel(TimeoutReason.SYSTEM_TIMEOUT)

        logger.info("Timeout manager shutdown completed")


# Global timeout manager instance
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager() -> TimeoutManager:
    """Get the global timeout manager instance"""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager


def init_timeout_manager(app=None) -> TimeoutManager:
    """Initialize timeout manager for Flask app"""
    manager = get_timeout_manager()

    if app:
        # Register cleanup on app teardown
        @app.teardown_appcontext
        def cleanup_timeout_context(error):
            # Cleanup any request-specific timeout contexts
            pass

        # Add timeout manager to app
        app.timeout_manager = manager

    return manager


# Decorator for adding timeout support to functions
def with_timeout(provider: str, operation_name: str = None):
    """Decorator to add timeout support to a function"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def async_wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            manager = get_timeout_manager()

            async with manager.request_context(provider, op_name) as context:
                if context and context.is_cancelled():
                    raise asyncio.CancelledError("Request was cancelled")
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            manager = get_timeout_manager()

            # For sync functions, we'll use a simple timeout context
            config = manager.get_provider_config(provider)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if duration > config.request_timeout:
                    manager.metrics.record_timeout(
                        provider, TimeoutReason.PROVIDER_TIMEOUT, duration
                    )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
