"""
Circuit Breaker Pattern Tests

Comprehensive test suite for the circuit breaker implementation.
Tests all aspects of circuit breaker functionality including state transitions,
failure detection, recovery mechanisms, and fallback routing.

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import threading
import time
from datetime import datetime

import pytest

from core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerDecorator,
    CircuitBreakerManager,
    CircuitBreakerStats,
    CircuitState,
    RequestRecord,
    circuit_breaker,
    get_circuit_manager,
    initialize_circuit_breaker,
)


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_duration == 60
        assert config.monitoring_window == 300
        assert config.failure_rate_threshold == 0.5
        assert config.minimum_requests == 10
        assert config.half_open_max_requests == 3
        assert config.recovery_timeout == 30
        assert config.exponential_backoff is True
        assert config.max_timeout == 3600
        assert config.jitter is True
        assert config.enable_metrics is True
        assert config.metrics_retention_period == 86400

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=5,
            timeout_duration=120,
            failure_rate_threshold=0.8,
            exponential_backoff=False,
            jitter=False,
        )

        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.timeout_duration == 120
        assert config.failure_rate_threshold == 0.8
        assert config.exponential_backoff is False
        assert config.jitter is False


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""

    def test_initial_stats(self):
        """Test initial statistics values."""
        stats = CircuitBreakerStats("test_provider", CircuitState.CLOSED)

        assert stats.provider_name == "test_provider"
        assert stats.current_state == CircuitState.CLOSED
        assert stats.failure_count == 0
        assert stats.success_count == 0
        assert stats.total_requests == 0
        assert stats.total_failures == 0
        assert stats.total_successes == 0
        assert stats.failure_rate == 0.0
        assert stats.uptime_percentage == 100.0

    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        stats = CircuitBreakerStats("test_provider", CircuitState.CLOSED)

        # No requests
        assert stats.failure_rate == 0.0

        # Some requests
        stats.total_requests = 10
        stats.total_failures = 3
        assert stats.failure_rate == 0.3

        # All failures
        stats.total_failures = 10
        assert stats.failure_rate == 1.0

    def test_uptime_percentage(self):
        """Test uptime percentage calculation."""
        stats = CircuitBreakerStats("test_provider", CircuitState.CLOSED)

        # No requests
        assert stats.uptime_percentage == 100.0

        # Some successes
        stats.total_requests = 10
        stats.total_successes = 8
        assert stats.uptime_percentage == 80.0

        # All successes
        stats.total_successes = 10
        assert stats.uptime_percentage == 100.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = CircuitBreakerStats("test_provider", CircuitState.CLOSED)
        stats.total_requests = 10
        stats.total_failures = 2
        stats.total_successes = 8

        result = stats.to_dict()

        assert result["provider_name"] == "test_provider"
        assert result["current_state"] == "closed"
        assert result["total_requests"] == 10
        assert result["total_failures"] == 2
        assert result["total_successes"] == 8
        assert result["failure_rate"] == 0.2
        assert result["uptime_percentage"] == 80.0


class TestRequestRecord:
    """Test request record functionality."""

    def test_success_record(self):
        """Test successful request record."""
        timestamp = datetime.now()
        record = RequestRecord(timestamp, True, 0.5)

        assert record.timestamp == timestamp
        assert record.success is True
        assert record.response_time == 0.5
        assert record.error == ""

    def test_failure_record(self):
        """Test failure request record."""
        timestamp = datetime.now()
        record = RequestRecord(timestamp, False, 1.0, "Connection timeout")

        assert record.timestamp == timestamp
        assert record.success is False
        assert record.response_time == 1.0
        assert record.error == "Connection timeout"


class TestCircuitBreaker:
    """Test circuit breaker core functionality."""

    def test_initialization(self):
        """Test circuit breaker initialization."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test_provider", config)

        assert breaker.provider_name == "test_provider"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.provider_name == "test_provider"
        assert breaker.stats.current_state == CircuitState.CLOSED

    def test_can_execute_closed_state(self):
        """Test can_execute in CLOSED state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test_provider", config)

        assert breaker.can_execute() is True

    def test_record_success_in_closed_state(self):
        """Test recording success in CLOSED state."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test_provider", config)

        breaker.record_success(0.5)

        assert breaker.stats.total_requests == 1
        assert breaker.stats.total_successes == 1
        assert breaker.stats.success_count == 1
        assert breaker.stats.failure_count == 0
        assert breaker.state == CircuitState.CLOSED

    def test_record_failure_in_closed_state(self):
        """Test recording failure in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test_provider", config)

        # Record failures below threshold
        for i in range(2):
            breaker.record_failure(f"Error {i}")

        assert breaker.stats.total_requests == 2
        assert breaker.stats.total_failures == 2
        assert breaker.stats.failure_count == 2
        assert breaker.state == CircuitState.CLOSED

        # Record failure that exceeds threshold
        breaker.record_failure("Final error")

        assert breaker.stats.total_requests == 3
        assert breaker.stats.total_failures == 3
        assert breaker.stats.failure_count == 3
        assert breaker.state == CircuitState.OPEN

    def test_transition_to_open_state(self):
        """Test transition to OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker("test_provider", config)

        # Trigger failures to open circuit
        breaker.record_failure("Error 1")
        breaker.record_failure("Error 2")

        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False
        assert breaker.timeout_end is not None

    def test_exponential_backoff(self):
        """Test exponential backoff timeout calculation."""
        config = CircuitBreakerConfig(
            failure_threshold=1, timeout_duration=10, exponential_backoff=True, jitter=False
        )
        breaker = CircuitBreaker("test_provider", config)

        # First failure
        breaker.record_failure("Error 1")
        first_timeout = breaker.current_timeout

        # Second failure (should double)
        breaker.record_failure("Error 2")
        second_timeout = breaker.current_timeout

        assert second_timeout >= first_timeout * 2

    def test_half_open_state_transition(self):
        """Test transition to HALF_OPEN state."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            timeout_duration=1,
            jitter=False,  # 1 second timeout
        )
        breaker = CircuitBreaker("test_provider", config)

        # Open the circuit
        breaker.record_failure("Error")
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout and check transition
        time.sleep(1.1)
        assert breaker.can_execute() is False  # First call transitions to HALF_OPEN

        # Now should be in half-open state
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute() is True

    def test_half_open_success_recovery(self):
        """Test successful recovery from HALF_OPEN state."""
        config = CircuitBreakerConfig(
            failure_threshold=1, success_threshold=2, timeout_duration=1, jitter=False
        )
        breaker = CircuitBreaker("test_provider", config)

        # Open the circuit
        breaker.record_failure("Error")

        # Wait and transition to half-open
        time.sleep(1.1)
        breaker.can_execute()  # Triggers transition

        assert breaker.state == CircuitState.HALF_OPEN

        # Record successes to close circuit
        breaker.record_success()
        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.failure_count == 0

    def test_half_open_failure_reopens(self):
        """Test that failure in HALF_OPEN state reopens circuit."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_duration=1, jitter=False)
        breaker = CircuitBreaker("test_provider", config)

        # Open the circuit
        breaker.record_failure("Error 1")

        # Wait and transition to half-open
        time.sleep(1.1)
        breaker.can_execute()  # Triggers transition

        assert breaker.state == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        breaker.record_failure("Error 2")

        assert breaker.state == CircuitState.OPEN

    def test_failure_rate_threshold(self):
        """Test failure rate based circuit opening."""
        config = CircuitBreakerConfig(
            failure_threshold=100,  # High threshold to test rate-based opening
            failure_rate_threshold=0.5,
            minimum_requests=10,
            monitoring_window=300,
        )
        breaker = CircuitBreaker("test_provider", config)

        # Add requests that exceed failure rate
        for i in range(10):
            if i < 6:  # 60% failure rate
                breaker.record_failure(f"Error {i}")
            else:
                breaker.record_success()

        assert breaker.state == CircuitState.OPEN

    def test_manual_reset(self):
        """Test manual circuit reset."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker("test_provider", config)

        # Open the circuit
        breaker.record_failure("Error")
        assert breaker.state == CircuitState.OPEN

        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.failure_count == 0

    def test_manual_force_open(self):
        """Test manual force open."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test_provider", config)

        assert breaker.state == CircuitState.CLOSED

        # Force open
        breaker.force_open("Maintenance mode")
        assert breaker.state == CircuitState.OPEN

    def test_request_history_cleanup(self):
        """Test cleanup of old request records."""
        config = CircuitBreakerConfig(monitoring_window=1)  # 1 second window
        breaker = CircuitBreaker("test_provider", config)

        # Add some requests
        breaker.record_success()
        breaker.record_failure("Error")

        assert len(breaker.request_history) == 2

        # Wait for window to expire
        time.sleep(1.1)

        # Trigger cleanup
        breaker._cleanup_old_requests()

        assert len(breaker.request_history) == 0

    def test_thread_safety(self):
        """Test thread safety of circuit breaker operations."""
        config = CircuitBreakerConfig()
        breaker = CircuitBreaker("test_provider", config)

        def worker():
            for _ in range(100):
                breaker.record_success()
                breaker.record_failure("Error")

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify final state consistency
        expected_total = 5 * 100 * 2  # 5 threads * 100 iterations * 2 operations
        assert breaker.stats.total_requests == expected_total
        assert breaker.stats.total_successes == expected_total // 2
        assert breaker.stats.total_failures == expected_total // 2


class TestCircuitBreakerManager:
    """Test circuit breaker manager functionality."""

    def test_initialization(self):
        """Test manager initialization."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        assert len(manager.circuit_breakers) == 0
        assert len(manager.fallback_chains) == 0

    def test_register_provider(self):
        """Test provider registration."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        breaker = manager.register_provider("test_provider")

        assert "test_provider" in manager.circuit_breakers
        assert breaker.provider_name == "test_provider"

    def test_register_provider_twice(self):
        """Test registering the same provider twice."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        breaker1 = manager.register_provider("test_provider")
        breaker2 = manager.register_provider("test_provider")

        assert breaker1 is breaker2
        assert len(manager.circuit_breakers) == 1

    def test_unregister_provider(self):
        """Test provider unregistration."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        manager.register_provider("test_provider")
        assert "test_provider" in manager.circuit_breakers

        manager.unregister_provider("test_provider")
        assert "test_provider" not in manager.circuit_breakers

    def test_get_circuit_breaker(self):
        """Test getting circuit breaker for provider."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        # Non-existent provider
        assert manager.get_circuit_breaker("test_provider") is None

        # Existing provider
        manager.register_provider("test_provider")
        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker is not None
        assert breaker.provider_name == "test_provider"

    def test_set_fallback_chain(self):
        """Test setting fallback chain."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        manager.set_fallback_chain("primary", ["fallback1", "fallback2"])

        assert "primary" in manager.fallback_chains
        assert manager.fallback_chains["primary"] == ["fallback1", "fallback2"]

    def test_get_available_provider_primary_available(self):
        """Test getting available provider when primary is available."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        manager.register_provider("primary")
        manager.register_provider("fallback")

        # Primary is available
        available = manager.get_available_provider("primary")
        assert available == "primary"

    def test_get_available_provider_fallback(self):
        """Test getting available provider using fallback."""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = CircuitBreakerManager(config)

        # Register providers
        primary_breaker = manager.register_provider("primary")
        manager.register_provider("fallback")

        # Set fallback chain
        manager.set_fallback_chain("primary", ["fallback"])

        # Break primary provider
        primary_breaker.record_failure("Error")

        # Should return fallback
        available = manager.get_available_provider("primary")
        assert available == "fallback"

    def test_get_available_provider_none_available(self):
        """Test when no providers are available."""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = CircuitBreakerManager(config)

        # Register providers
        primary_breaker = manager.register_provider("primary")
        fallback_breaker = manager.register_provider("fallback")

        # Set fallback chain
        manager.set_fallback_chain("primary", ["fallback"])

        # Break both providers
        primary_breaker.record_failure("Error")
        fallback_breaker.record_failure("Error")

        # Should return None
        available = manager.get_available_provider("primary")
        assert available is None

    def test_record_success_and_failure(self):
        """Test recording success and failure through manager."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        manager.register_provider("test_provider")

        # Record success
        manager.record_success("test_provider", 0.5)
        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker.stats.total_successes == 1

        # Record failure
        manager.record_failure("test_provider", "Error", 1.0)
        assert breaker.stats.total_failures == 1

    def test_get_all_stats(self):
        """Test getting all provider statistics."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)

        manager.register_provider("provider1")
        manager.register_provider("provider2")

        stats = manager.get_all_stats()

        assert len(stats) == 2
        assert "provider1" in stats
        assert "provider2" in stats
        assert isinstance(stats["provider1"], CircuitBreakerStats)

    def test_get_system_health(self):
        """Test getting system health metrics."""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = CircuitBreakerManager(config)

        # Register providers
        healthy_breaker = manager.register_provider("healthy")
        failed_breaker = manager.register_provider("failed")

        # Break one provider
        failed_breaker.record_failure("Error")

        health = manager.get_system_health()

        assert health["total_providers"] == 2
        assert health["healthy_providers"] == 1
        assert health["failed_providers"] == 1
        assert health["degraded_providers"] == 0
        assert health["overall_health"] == "degraded"
        assert "provider_stats" in health
        assert "timestamp" in health

    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = CircuitBreakerManager(config)

        # Register and break providers
        breaker1 = manager.register_provider("provider1")
        breaker2 = manager.register_provider("provider2")

        breaker1.record_failure("Error")
        breaker2.record_failure("Error")

        assert breaker1.state == CircuitState.OPEN
        assert breaker2.state == CircuitState.OPEN

        # Reset all
        manager.reset_all()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED

    def test_reset_provider(self):
        """Test resetting specific provider."""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = CircuitBreakerManager(config)

        # Register and break provider
        breaker = manager.register_provider("test_provider")
        breaker.record_failure("Error")

        assert breaker.state == CircuitState.OPEN

        # Reset specific provider
        manager.reset_provider("test_provider")

        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator functionality."""

    def test_sync_function_success(self):
        """Test decorator with successful sync function."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)
        decorator = CircuitBreakerDecorator("test_provider", manager)

        @decorator
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker.stats.total_successes == 1

    def test_sync_function_failure(self):
        """Test decorator with failing sync function."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)
        decorator = CircuitBreakerDecorator("test_provider", manager)

        @decorator
        def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_function()

        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker.stats.total_failures == 1

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with successful async function."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)
        decorator = CircuitBreakerDecorator("test_provider", manager)

        @decorator
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"

        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker.stats.total_successes == 1

    @pytest.mark.asyncio
    async def test_async_function_failure(self):
        """Test decorator with failing async function."""
        config = CircuitBreakerConfig()
        manager = CircuitBreakerManager(config)
        decorator = CircuitBreakerDecorator("test_provider", manager)

        @decorator
        async def test_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await test_function()

        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker.stats.total_failures == 1

    def test_circuit_open_blocks_execution(self):
        """Test that open circuit blocks function execution."""
        config = CircuitBreakerConfig(failure_threshold=1)
        manager = CircuitBreakerManager(config)
        decorator = CircuitBreakerDecorator("test_provider", manager)

        @decorator
        def test_function():
            return "success"

        # Break the circuit
        breaker = manager.get_circuit_breaker("test_provider")
        if not breaker:
            breaker = manager.register_provider("test_provider")
        breaker.record_failure("Error")

        # Function should be blocked
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            test_function()


class TestGlobalFunctions:
    """Test global circuit breaker functions."""

    def test_initialize_circuit_breaker(self):
        """Test global circuit breaker initialization."""
        config = CircuitBreakerConfig()
        manager = initialize_circuit_breaker(config)

        assert manager is not None
        assert get_circuit_manager() is manager

    def test_initialize_with_default_config(self):
        """Test initialization with default config."""
        manager = initialize_circuit_breaker()

        assert manager is not None
        assert get_circuit_manager() is manager

    def test_circuit_breaker_decorator_function(self):
        """Test global circuit breaker decorator function."""
        # Initialize global manager
        initialize_circuit_breaker()

        @circuit_breaker("test_provider")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

        manager = get_circuit_manager()
        breaker = manager.get_circuit_breaker("test_provider")
        assert breaker.stats.total_successes == 1

    def test_circuit_breaker_decorator_without_manager(self):
        """Test decorator without initialized manager."""
        # Reset global manager
        import core.circuit_breaker

        core.circuit_breaker.circuit_manager = None

        with pytest.raises(RuntimeError, match="Circuit breaker manager not initialized"):

            @circuit_breaker("test_provider")
            def test_function():
                return "success"


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_api_provider_failover_scenario(self):
        """Test realistic API provider failover scenario."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout_duration=2, jitter=False)
        manager = CircuitBreakerManager(config)

        # Register providers with fallback chain
        manager.register_provider("openai")
        manager.register_provider("anthropic")
        manager.register_provider("groq")

        manager.set_fallback_chain("openai", ["anthropic", "groq"])

        # Simulate API calls
        def make_api_call(provider):
            available_provider = manager.get_available_provider(provider)
            if not available_provider:
                raise Exception("No providers available")

            # Simulate API response
            if available_provider == "openai":
                # OpenAI is having issues
                manager.record_failure("openai", "API rate limit exceeded")
                raise Exception("OpenAI rate limit")
            elif available_provider == "anthropic":
                # Anthropic works
                manager.record_success("anthropic", 0.8)
                return f"Response from {available_provider}"
            else:
                # Groq works
                manager.record_success("groq", 0.3)
                return f"Response from {available_provider}"

        # First few calls fail on OpenAI
        for _ in range(3):
            try:
                result = make_api_call("openai")
                raise AssertionError("Should have failed")
            except Exception as e:
                if "Should have failed" in str(e):
                    raise
                # Expected failure, continue

        # Circuit should be open for OpenAI, should fallback to Anthropic
        result = make_api_call("openai")
        assert "anthropic" in result.lower()

        # Verify circuit states
        openai_breaker = manager.get_circuit_breaker("openai")
        anthropic_breaker = manager.get_circuit_breaker("anthropic")

        assert openai_breaker.state == CircuitState.OPEN
        assert anthropic_breaker.state == CircuitState.CLOSED

    def test_gradual_recovery_scenario(self):
        """Test gradual recovery after failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2, success_threshold=3, timeout_duration=1, jitter=False
        )
        breaker = CircuitBreaker("test_provider", config)

        # Break the circuit
        breaker.record_failure("Error 1")
        breaker.record_failure("Error 2")
        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Should transition to half-open
        assert breaker.can_execute() is False  # First call transitions
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute() is True

        # Gradual recovery with successes
        breaker.record_success(0.5)
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.record_success(0.4)
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.record_success(0.3)
        assert breaker.state == CircuitState.CLOSED

        # Circuit should be fully recovered
        assert breaker.can_execute() is True
        assert breaker.stats.failure_count == 0

    def test_concurrent_access_scenario(self):
        """Test concurrent access from multiple threads."""
        config = CircuitBreakerConfig(failure_threshold=10)
        manager = CircuitBreakerManager(config)
        manager.register_provider("concurrent_provider")

        results = []

        def worker(worker_id):
            for i in range(50):
                try:
                    available = manager.get_available_provider("concurrent_provider")
                    if available:
                        if i % 4 == 0:  # 25% failure rate
                            manager.record_failure(
                                "concurrent_provider", f"Worker {worker_id} error {i}"
                            )
                        else:
                            manager.record_success("concurrent_provider", 0.5)
                            results.append(f"Worker {worker_id} success {i}")
                except Exception as e:
                    results.append(f"Worker {worker_id} exception: {e}")

        # Start multiple workers
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        breaker = manager.get_circuit_breaker("concurrent_provider")
        assert breaker.stats.total_requests == 250  # 5 workers * 50 requests
        assert len(results) > 0

        # Check that some successes were recorded
        success_count = len([r for r in results if "success" in r])
        assert success_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
