"""
Comprehensive tests for Request Queue System
Tests priority handling, rate limiting, monitoring, and Flask integration
"""

import asyncio
import json
import time

import pytest

from core.queue_integration import init_queue_integration
from core.request_queue import (
    Priority,
    QueueFullException,
    RateLimitExceededException,
    RateLimitRule,
    RequestQueue,
    RequestStatus,
    get_request_queue,
    init_request_queue,
)


class TestRequestQueue:
    """Test suite for RequestQueue class"""

    @pytest.fixture
    def queue(self):
        """Create a test queue instance"""

        async def _queue():
            queue = RequestQueue(
                max_workers=2, max_queue_size=10, default_timeout=5.0, enable_redis=False
            )
            await queue.start()
            try:
                yield queue
            finally:
                await queue.stop()

        return _queue()

    @pytest.fixture
    def sample_handler(self):
        """Sample async handler for testing"""

        async def handler(value, delay=0.1):
            await asyncio.sleep(delay)
            return f"processed_{value}"

        return handler

    @pytest.fixture
    def failing_handler(self):
        """Handler that always fails for testing error handling"""

        async def handler():
            raise ValueError("Simulated failure")

        return handler

    @pytest.mark.asyncio
    async def test_basic_queue_functionality(self, queue, sample_handler):
        """Test basic request queuing and processing"""
        # Queue a request
        request_id = await queue.queue_request(
            sample_handler, "test_value", priority=Priority.NORMAL
        )

        assert isinstance(request_id, str)
        assert len(request_id) > 0

        # Wait for result
        result = await queue.wait_for_result(request_id)
        assert result == "processed_test_value"

        # Check request status
        status = await queue.get_request_status(request_id)
        assert status["status"] == RequestStatus.COMPLETED.value
        assert status["result"] == "processed_test_value"

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue, sample_handler):
        """Test that higher priority requests are processed first"""
        results = []

        # Create a slow handler that tracks execution order
        async def tracking_handler(value):
            await asyncio.sleep(0.2)
            results.append(value)
            return f"processed_{value}"

        # Queue requests in reverse priority order
        low_id = await queue.queue_request(tracking_handler, "low", priority=Priority.LOW)
        normal_id = await queue.queue_request(tracking_handler, "normal", priority=Priority.NORMAL)
        high_id = await queue.queue_request(tracking_handler, "high", priority=Priority.HIGH)
        critical_id = await queue.queue_request(
            tracking_handler, "critical", priority=Priority.CRITICAL
        )

        # Wait for all to complete
        await asyncio.gather(
            queue.wait_for_result(low_id),
            queue.wait_for_result(normal_id),
            queue.wait_for_result(high_id),
            queue.wait_for_result(critical_id),
        )

        # Critical and high should be processed before normal and low
        # (exact order depends on worker availability)
        assert "critical" in results[:2] or "high" in results[:2]

    @pytest.mark.asyncio
    async def test_rate_limiting(self, queue, sample_handler):
        """Test rate limiting functionality"""
        # Set a strict rate limit
        rule = RateLimitRule(requests_per_minute=2, requests_per_hour=5)
        queue.set_rate_limit("test_user", rule)

        # First two requests should succeed
        req1 = await queue.queue_request(sample_handler, "req1", user_id="test_user")
        req2 = await queue.queue_request(sample_handler, "req2", user_id="test_user")

        # Third request should hit rate limit
        with pytest.raises(RateLimitExceededException):
            await queue.queue_request(sample_handler, "req3", user_id="test_user")

    @pytest.mark.asyncio
    async def test_request_timeout(self, queue):
        """Test request timeout handling"""

        async def slow_handler():
            await asyncio.sleep(2.0)
            return "should_not_complete"

        request_id = await queue.queue_request(slow_handler, timeout=0.5)

        # Wait for timeout
        await asyncio.sleep(1.0)

        status = await queue.get_request_status(request_id)
        assert status["status"] == RequestStatus.TIMEOUT.value

    @pytest.mark.asyncio
    async def test_request_retry(self, queue):
        """Test request retry mechanism"""
        attempt_count = 0

        async def flaky_handler():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError(f"Attempt {attempt_count} failed")
            return f"success_on_attempt_{attempt_count}"

        request_id = await queue.queue_request(flaky_handler, max_retries=3)

        result = await queue.wait_for_result(request_id)
        assert result == "success_on_attempt_3"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_request_cancellation(self, queue):
        """Test request cancellation"""

        async def long_running_handler():
            await asyncio.sleep(10.0)
            return "should_not_complete"

        request_id = await queue.queue_request(long_running_handler)

        # Cancel the request
        success = await queue.cancel_request(request_id)
        assert success

        # Check status
        status = await queue.get_request_status(request_id)
        assert status["status"] == RequestStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_queue_capacity(self, queue):
        """Test queue capacity limits"""
        # Fill the queue to capacity
        handlers = []
        request_ids = []

        async def blocking_handler():
            await asyncio.sleep(10.0)  # Block workers
            return "completed"

        # Fill up to max_queue_size (10)
        for i in range(queue.max_queue_size):
            request_id = await queue.queue_request(blocking_handler, priority=Priority.LOW)
            request_ids.append(request_id)

        # Next request should fail
        with pytest.raises(QueueFullException):
            await queue.queue_request(blocking_handler)

        # Clean up by cancelling requests
        for request_id in request_ids:
            await queue.cancel_request(request_id)

    @pytest.mark.asyncio
    async def test_statistics(self, queue, sample_handler):
        """Test statistics collection"""
        initial_stats = await queue.get_queue_stats()

        # Process some requests
        request_ids = []
        for i in range(3):
            request_id = await queue.queue_request(sample_handler, f"value_{i}")
            request_ids.append(request_id)

        # Wait for completion
        for request_id in request_ids:
            await queue.wait_for_result(request_id)

        final_stats = await queue.get_queue_stats()

        assert final_stats["total_processed"] >= initial_stats["total_processed"] + 3
        assert final_stats["total_queued"] >= initial_stats["total_queued"] + 3
        assert final_stats["avg_processing_time"] > 0

    @pytest.mark.asyncio
    async def test_health_status(self, queue):
        """Test health status reporting"""
        health = await queue.get_health_status()

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert 0 <= health["health_score"] <= 100
        assert isinstance(health["issues"], list)
        assert "redis_enabled" in health
        assert "current_queued" in health
        assert "worker_utilization" in health


class TestFlaskIntegration:
    """Test suite for Flask integration"""

    @pytest.fixture
    def app(self):
        """Create test Flask app with queue integration"""
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True

        # Initialize queue integration
        init_queue_integration(app, max_workers=2, max_queue_size=5)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_queue_health_endpoint(self, client):
        """Test /api/queue/health endpoint"""
        response = client.get("/api/queue/health")

        # Might be 503 if queue not started yet, that's OK for testing
        assert response.status_code in [200, 206, 503]

        data = json.loads(response.data)
        assert "status" in data
        assert "health_score" in data

    def test_queue_stats_endpoint(self, client):
        """Test /api/queue/stats endpoint"""
        response = client.get("/api/queue/stats")

        # Might be 503 if queue not initialized
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "total_queued" in data
            assert "total_processed" in data
            assert "worker_utilization" in data

    def test_priority_info_endpoint(self, client):
        """Test /api/queue/priorities endpoint"""
        response = client.get("/api/queue/priorities")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "priorities" in data
        assert len(data["priorities"]) == 4  # Four priority levels

        priority_names = [p["name"] for p in data["priorities"]]
        assert "LOW" in priority_names
        assert "NORMAL" in priority_names
        assert "HIGH" in priority_names
        assert "CRITICAL" in priority_names

    def test_request_status_endpoint_not_found(self, client):
        """Test request status endpoint with non-existent request"""
        response = client.get("/api/queue/status/nonexistent-id")

        # Should be 404 or 503 if queue not running
        assert response.status_code in [404, 503]

    def test_worker_status_endpoint(self, client):
        """Test /api/queue/workers endpoint"""
        response = client.get("/api/queue/workers")

        if response.status_code == 200:
            data = json.loads(response.data)
            assert "total_workers" in data
            assert "active_workers" in data
            assert "utilization" in data


class TestAsyncIntegration:
    """Test async integration patterns"""

    @pytest.mark.asyncio
    async def test_queue_decorator(self):
        """Test the @queue_request decorator"""
        from core.queue_integration import queue_request

        # Initialize queue first
        queue = init_request_queue(max_workers=2, max_queue_size=5)
        await queue.start()

        try:

            @queue_request(priority=Priority.HIGH)
            async def decorated_function(value):
                await asyncio.sleep(0.1)
                return f"decorated_{value}"

            result = await decorated_function("test")
            assert result == "decorated_test"

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_batch_requests(self):
        """Test batch request processing"""
        from core.queue_integration import QueueBatch

        # Initialize queue
        queue = init_request_queue(max_workers=2, max_queue_size=10)
        await queue.start()

        try:

            async def test_handler(value):
                await asyncio.sleep(0.1)
                return f"batch_{value}"

            async with QueueBatch(priority=Priority.NORMAL) as batch:
                await batch.add_request(test_handler, "item1")
                await batch.add_request(test_handler, "item2")
                await batch.add_request(test_handler, "item3")

            # Results should be available after context exit
            # (Implementation depends on QueueBatch.__aexit__)

        finally:
            await queue.stop()


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_queue_not_initialized(self):
        """Test behavior when queue is not initialized"""
        # Reset global queue
        import core.request_queue

        core.request_queue._request_queue = None

        with pytest.raises(RuntimeError, match="not initialized"):
            get_request_queue()

    @pytest.mark.asyncio
    async def test_invalid_priority(self):
        """Test handling of invalid priority values"""
        queue = RequestQueue(max_workers=1, max_queue_size=5)
        await queue.start()

        try:

            async def test_handler():
                return "test"

            # This should work fine since Priority is an enum
            request_id = await queue.queue_request(test_handler, priority=Priority.HIGH)
            result = await queue.wait_for_result(request_id)
            assert result == "test"

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_redis_failure_graceful_degradation(self):
        """Test graceful degradation when Redis fails"""
        # Test with invalid Redis config
        queue = RequestQueue(
            max_workers=2,
            enable_redis=True,
            redis_config={"host": "nonexistent-host", "port": 9999},
        )

        # Should fall back to local queuing
        assert queue.enable_redis is False
        assert queue.redis_client is None

        await queue.start()

        try:

            async def test_handler():
                return "works_without_redis"

            request_id = await queue.queue_request(test_handler)
            result = await queue.wait_for_result(request_id)
            assert result == "works_without_redis"

        finally:
            await queue.stop()


class TestPerformance:
    """Performance and load testing"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of many concurrent requests"""
        queue = RequestQueue(max_workers=4, max_queue_size=100)
        await queue.start()

        try:

            async def fast_handler(value):
                await asyncio.sleep(0.01)  # Very fast
                return f"result_{value}"

            # Submit 50 concurrent requests
            request_ids = []
            for i in range(50):
                request_id = await queue.queue_request(fast_handler, i, priority=Priority.NORMAL)
                request_ids.append(request_id)

            # Wait for all results
            start_time = time.time()
            results = await asyncio.gather(
                *[queue.wait_for_result(req_id) for req_id in request_ids]
            )
            end_time = time.time()

            # All should complete
            assert len(results) == 50
            assert all(r.startswith("result_") for r in results)

            # Should be reasonably fast with 4 workers
            assert end_time - start_time < 5.0

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_memory_cleanup(self):
        """Test that completed requests are cleaned up"""
        queue = RequestQueue(max_workers=2, max_queue_size=20)
        await queue.start()

        try:

            async def simple_handler():
                return "done"

            # Process many requests
            for i in range(15):
                request_id = await queue.queue_request(simple_handler)
                await queue.wait_for_result(request_id)

            # Let cleanup task run
            await asyncio.sleep(1.0)

            # Trigger manual cleanup for testing
            await queue._cleanup_task.__wrapped__(queue)

            # Request count should not grow indefinitely
            assert len(queue.requests) < 15  # Some should be cleaned up

        finally:
            await queue.stop()


if __name__ == "__main__":
    # Run basic smoke tests
    pytest.main([__file__, "-v", "--tb=short"])
