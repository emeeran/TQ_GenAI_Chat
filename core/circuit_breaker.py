"""
Circuit Breaker Pattern Implementation (Task 2.3.3)

This module implements the circuit breaker pattern for automatic failure detection
and isolation of AI providers. It provides resilience against cascading failures
and improves system reliability through intelligent fallback mechanisms.

Key Features:
- Automatic failure detection and isolation
- Configurable failure thresholds and timeouts
- Gradual recovery mechanism with half-open state
- Real-time circuit breaker status monitoring
- Intelligent fallback provider routing
- Comprehensive metrics and alerting

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import logging
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure state, requests blocked
    HALF_OPEN = "half_open"  # Recovery testing, limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Failure detection settings
    failure_threshold: int = 5  # Consecutive failures to open circuit
    success_threshold: int = 3  # Consecutive successes to close circuit
    timeout_duration: int = 60  # Time in seconds before attempting recovery

    # Monitoring window settings
    monitoring_window: int = 300  # Time window for failure rate calculation (seconds)
    failure_rate_threshold: float = 0.5  # Failure rate (0.0-1.0) to open circuit
    minimum_requests: int = 10  # Minimum requests in window before rate calculation

    # Recovery settings
    half_open_max_requests: int = 3  # Max requests allowed in half-open state
    recovery_timeout: int = 30  # Timeout for half-open state (seconds)

    # Advanced settings
    exponential_backoff: bool = True  # Use exponential backoff for timeout
    max_timeout: int = 3600  # Maximum timeout duration (1 hour)
    jitter: bool = True  # Add random jitter to timeout

    # Monitoring settings
    enable_metrics: bool = True
    metrics_retention_period: int = 86400  # 24 hours in seconds


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker operations."""

    provider_name: str
    current_state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    state_changed_at: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    circuit_open_count: int = 0
    circuit_half_open_count: int = 0

    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.total_failures / self.total_requests

    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage."""
        if self.total_requests == 0:
            return 100.0
        return (self.total_successes / self.total_requests) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary for serialization."""
        return {
            "provider_name": self.provider_name,
            "current_state": self.current_state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "last_success_time": self.last_success_time.isoformat()
            if self.last_success_time
            else None,
            "state_changed_at": self.state_changed_at.isoformat(),
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "failure_rate": self.failure_rate,
            "uptime_percentage": self.uptime_percentage,
            "circuit_open_count": self.circuit_open_count,
            "circuit_half_open_count": self.circuit_half_open_count,
        }


class RequestRecord:
    """Record of a request attempt."""

    def __init__(
        self, timestamp: datetime, success: bool, response_time: float = 0.0, error: str = ""
    ):
        self.timestamp = timestamp
        self.success = success
        self.response_time = response_time
        self.error = error


class CircuitBreaker:
    """
    Circuit breaker implementation for provider failure isolation.

    Implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation, all requests allowed
    - OPEN: Failure state, all requests blocked
    - HALF_OPEN: Recovery testing, limited requests allowed
    """

    def __init__(self, provider_name: str, config: CircuitBreakerConfig):
        self.provider_name = provider_name
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats(provider_name, CircuitState.CLOSED)

        # Request tracking
        self.request_history: deque[RequestRecord] = deque(maxlen=1000)
        self.half_open_requests = 0

        # Timing
        self.last_failure_time: datetime | None = None
        self.timeout_end: datetime | None = None
        self.current_timeout = config.timeout_duration

        # Thread safety
        self._lock = threading.RLock()

        logger.info(f"Circuit breaker initialized for provider: {provider_name}")

    def _cleanup_old_requests(self):
        """Clean up old request records outside monitoring window."""
        cutoff_time = datetime.now() - timedelta(seconds=self.config.monitoring_window)

        while self.request_history and self.request_history[0].timestamp < cutoff_time:
            self.request_history.popleft()

    def _calculate_failure_rate(self) -> float:
        """Calculate failure rate within monitoring window."""
        self._cleanup_old_requests()

        if len(self.request_history) < self.config.minimum_requests:
            return 0.0

        failures = sum(1 for record in self.request_history if not record.success)
        return failures / len(self.request_history)

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset from OPEN to HALF_OPEN."""
        if self.state != CircuitState.OPEN:
            return False

        if not self.timeout_end:
            return False

        return datetime.now() >= self.timeout_end

    def _update_timeout(self):
        """Update timeout duration with exponential backoff."""
        if self.config.exponential_backoff:
            self.current_timeout = min(self.current_timeout * 2, self.config.max_timeout)

        # Add jitter if enabled
        if self.config.jitter:
            jitter = secrets.SystemRandom().uniform(0.8, 1.2)
            self.current_timeout = int(self.current_timeout * jitter)

        self.timeout_end = datetime.now() + timedelta(seconds=self.current_timeout)

    def _transition_to_open(self, error: str = ""):
        """Transition circuit to OPEN state."""
        if self.state == CircuitState.OPEN:
            return

        previous_state = self.state
        self.state = CircuitState.OPEN
        self.stats.current_state = CircuitState.OPEN
        self.stats.state_changed_at = datetime.now()
        self.stats.circuit_open_count += 1

        self._update_timeout()

        logger.warning(
            f"Circuit breaker OPENED for {self.provider_name}. "
            f"Previous state: {previous_state.value}, Error: {error}, "
            f"Timeout until: {self.timeout_end}"
        )

    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        if self.state == CircuitState.HALF_OPEN:
            return

        previous_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.stats.current_state = CircuitState.HALF_OPEN
        self.stats.state_changed_at = datetime.now()
        self.stats.circuit_half_open_count += 1
        self.half_open_requests = 0

        logger.info(
            f"Circuit breaker transitioned to HALF_OPEN for {self.provider_name}. "
            f"Previous state: {previous_state.value}"
        )

    def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        if self.state == CircuitState.CLOSED:
            return

        previous_state = self.state
        self.state = CircuitState.CLOSED
        self.stats.current_state = CircuitState.CLOSED
        self.stats.state_changed_at = datetime.now()

        # Reset counters and timeout
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self.current_timeout = self.config.timeout_duration
        self.timeout_end = None

        logger.info(
            f"Circuit breaker CLOSED for {self.provider_name}. "
            f"Previous state: {previous_state.value}"
        )

    def can_execute(self) -> bool:
        """Check if request can be executed based on circuit state."""
        with self._lock:
            # Check if circuit should attempt reset
            if self._should_attempt_reset():
                self._transition_to_half_open()

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                return False

            if self.state == CircuitState.HALF_OPEN:
                return self.half_open_requests < self.config.half_open_max_requests

            return False

    def record_success(self, response_time: float = 0.0):
        """Record a successful request."""
        with self._lock:
            now = datetime.now()

            # Add to request history
            self.request_history.append(RequestRecord(now, True, response_time))

            # Update stats
            self.stats.total_requests += 1
            self.stats.total_successes += 1
            self.stats.success_count += 1
            self.stats.last_success_time = now

            if self.state == CircuitState.HALF_OPEN:
                self.half_open_requests += 1

                # Check if we should close the circuit
                if self.stats.success_count >= self.config.success_threshold:
                    self._transition_to_closed()

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.stats.failure_count = 0

            logger.debug(
                f"Success recorded for {self.provider_name}, response_time: {response_time}s"
            )

    def record_failure(self, error: str = "", response_time: float = 0.0):
        """Record a failed request."""
        with self._lock:
            now = datetime.now()

            # Add to request history
            self.request_history.append(RequestRecord(now, False, response_time, error))

            # Update stats
            self.stats.total_requests += 1
            self.stats.total_failures += 1
            self.stats.failure_count += 1
            self.stats.last_failure_time = now
            self.last_failure_time = now

            # Check if circuit should open
            should_open = False

            if self.state == CircuitState.CLOSED:
                # Check consecutive failures
                if self.stats.failure_count >= self.config.failure_threshold:
                    should_open = True

                # Check failure rate within monitoring window
                failure_rate = self._calculate_failure_rate()
                if (
                    len(self.request_history) >= self.config.minimum_requests
                    and failure_rate >= self.config.failure_rate_threshold
                ):
                    should_open = True

            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens circuit
                should_open = True

            if should_open:
                self._transition_to_open(error)

            logger.warning(f"Failure recorded for {self.provider_name}: {error}")

    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics."""
        with self._lock:
            return self.stats

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"Manually resetting circuit breaker for {self.provider_name}")
            self._transition_to_closed()

    def force_open(self, reason: str = "Manual intervention"):
        """Manually force circuit breaker to OPEN state."""
        with self._lock:
            logger.warning(f"Manually opening circuit breaker for {self.provider_name}: {reason}")
            self._transition_to_open(reason)


class CircuitBreakerManager:
    """
    Manages circuit breakers for multiple providers.

    Provides centralized management, monitoring, and fallback routing
    for all provider circuit breakers.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.fallback_chains: dict[str, list[str]] = {}
        self._lock = threading.RLock()

        logger.info("Circuit breaker manager initialized")

    def register_provider(
        self, provider_name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """Register a new provider with circuit breaker."""
        with self._lock:
            if provider_name in self.circuit_breakers:
                logger.warning(f"Provider {provider_name} already registered")
                return self.circuit_breakers[provider_name]

            breaker_config = config or self.config
            circuit_breaker = CircuitBreaker(provider_name, breaker_config)
            self.circuit_breakers[provider_name] = circuit_breaker

            logger.info(f"Registered circuit breaker for provider: {provider_name}")
            return circuit_breaker

    def unregister_provider(self, provider_name: str):
        """Unregister a provider and remove its circuit breaker."""
        with self._lock:
            if provider_name in self.circuit_breakers:
                del self.circuit_breakers[provider_name]
                logger.info(f"Unregistered circuit breaker for provider: {provider_name}")

    def get_circuit_breaker(self, provider_name: str) -> CircuitBreaker | None:
        """Get circuit breaker for a provider."""
        return self.circuit_breakers.get(provider_name)

    def set_fallback_chain(self, primary_provider: str, fallback_providers: list[str]):
        """Set fallback chain for a primary provider."""
        with self._lock:
            self.fallback_chains[primary_provider] = fallback_providers
            logger.info(f"Set fallback chain for {primary_provider}: {fallback_providers}")

    def get_available_provider(self, preferred_provider: str) -> str | None:
        """
        Get available provider considering circuit breaker states.

        Returns the preferred provider if available, otherwise tries fallbacks.
        """
        with self._lock:
            # Check preferred provider first
            circuit_breaker = self.circuit_breakers.get(preferred_provider)
            if circuit_breaker and circuit_breaker.can_execute():
                return preferred_provider

            # Try fallback providers
            fallback_providers = self.fallback_chains.get(preferred_provider, [])
            for fallback_provider in fallback_providers:
                fallback_circuit = self.circuit_breakers.get(fallback_provider)
                if fallback_circuit and fallback_circuit.can_execute():
                    logger.info(
                        f"Using fallback provider {fallback_provider} for {preferred_provider}"
                    )
                    return fallback_provider

            # If no providers available, return None
            logger.error(f"No available providers for {preferred_provider}")
            return None

    def record_success(self, provider_name: str, response_time: float = 0.0):
        """Record successful request for a provider."""
        circuit_breaker = self.circuit_breakers.get(provider_name)
        if circuit_breaker:
            circuit_breaker.record_success(response_time)

    def record_failure(self, provider_name: str, error: str = "", response_time: float = 0.0):
        """Record failed request for a provider."""
        circuit_breaker = self.circuit_breakers.get(provider_name)
        if circuit_breaker:
            circuit_breaker.record_failure(error, response_time)

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get statistics for all registered providers."""
        with self._lock:
            return {name: breaker.get_stats() for name, breaker in self.circuit_breakers.items()}

    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health metrics."""
        with self._lock:
            stats = self.get_all_stats()

            total_providers = len(stats)
            healthy_providers = sum(
                1 for stat in stats.values() if stat.current_state == CircuitState.CLOSED
            )
            degraded_providers = sum(
                1 for stat in stats.values() if stat.current_state == CircuitState.HALF_OPEN
            )
            failed_providers = sum(
                1 for stat in stats.values() if stat.current_state == CircuitState.OPEN
            )

            overall_health = (
                "healthy"
                if failed_providers == 0
                else "degraded"
                if healthy_providers > 0
                else "critical"
            )

            return {
                "overall_health": overall_health,
                "total_providers": total_providers,
                "healthy_providers": healthy_providers,
                "degraded_providers": degraded_providers,
                "failed_providers": failed_providers,
                "provider_stats": {name: stat.to_dict() for name, stat in stats.items()},
                "timestamp": datetime.now().isoformat(),
            }

    def reset_all(self):
        """Reset all circuit breakers to CLOSED state."""
        with self._lock:
            for breaker in self.circuit_breakers.values():
                breaker.reset()
            logger.info("Reset all circuit breakers")

    def reset_provider(self, provider_name: str):
        """Reset specific provider circuit breaker."""
        circuit_breaker = self.circuit_breakers.get(provider_name)
        if circuit_breaker:
            circuit_breaker.reset()
            logger.info(f"Reset circuit breaker for {provider_name}")


class CircuitBreakerDecorator:
    """
    Decorator for wrapping functions with circuit breaker logic.

    Usage:
        @CircuitBreakerDecorator("openai", circuit_manager)
        async def make_api_call():
            # API call implementation
            pass
    """

    def __init__(self, provider_name: str, circuit_manager: CircuitBreakerManager):
        self.provider_name = provider_name
        self.circuit_manager = circuit_manager

    def __call__(self, func: Callable):
        if asyncio.iscoroutinefunction(func):
            return self._wrap_async(func)
        else:
            return self._wrap_sync(func)

    def _wrap_async(self, func: Callable):
        async def wrapper(*args, **kwargs):
            circuit_breaker = self.circuit_manager.get_circuit_breaker(self.provider_name)
            if not circuit_breaker:
                # Register provider if not exists
                circuit_breaker = self.circuit_manager.register_provider(self.provider_name)

            if not circuit_breaker.can_execute():
                raise Exception(f"Circuit breaker OPEN for {self.provider_name}")

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time
                circuit_breaker.record_success(response_time)
                return result
            except Exception as e:
                response_time = time.time() - start_time
                circuit_breaker.record_failure(str(e), response_time)
                raise

        return wrapper

    def _wrap_sync(self, func: Callable):
        def wrapper(*args, **kwargs):
            circuit_breaker = self.circuit_manager.get_circuit_breaker(self.provider_name)
            if not circuit_breaker:
                # Register provider if not exists
                circuit_breaker = self.circuit_manager.register_provider(self.provider_name)

            if not circuit_breaker.can_execute():
                raise Exception(f"Circuit breaker OPEN for {self.provider_name}")

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time
                circuit_breaker.record_success(response_time)
                return result
            except Exception as e:
                response_time = time.time() - start_time
                circuit_breaker.record_failure(str(e), response_time)
                raise

        return wrapper


# Global circuit breaker manager instance
circuit_manager: CircuitBreakerManager | None = None


def get_circuit_manager() -> CircuitBreakerManager | None:
    """Get the global circuit breaker manager."""
    return circuit_manager


def initialize_circuit_breaker(config: CircuitBreakerConfig = None) -> CircuitBreakerManager:
    """Initialize the global circuit breaker manager."""
    global circuit_manager

    if config is None:
        config = CircuitBreakerConfig()

    circuit_manager = CircuitBreakerManager(config)
    return circuit_manager


def circuit_breaker(provider_name: str):
    """
    Decorator for applying circuit breaker to functions.

    Usage:
        @circuit_breaker("openai")
        async def openai_api_call():
            # Implementation
            pass
    """

    def decorator(func):
        if not circuit_manager:
            raise RuntimeError("Circuit breaker manager not initialized")
        return CircuitBreakerDecorator(provider_name, circuit_manager)(func)

    return decorator


# Export main components
__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitBreakerDecorator",
    "initialize_circuit_breaker",
    "get_circuit_manager",
    "circuit_breaker",
]

# Task 2.3.3 completion marker
logger.info("[Circuit Breaker] Task 2.3.3 Circuit Breaker Pattern - Implementation Complete")
