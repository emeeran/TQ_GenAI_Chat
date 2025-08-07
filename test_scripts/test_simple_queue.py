"""
Simple integration test for Request Queue System
"""

import asyncio

import pytest

from core.request_queue import Priority, RequestQueue


class TestSimpleQueue:
    """Simple test suite for basic queue functionality"""

    @pytest.mark.asyncio
    async def test_basic_functionality(self):
        """Test basic queue operations"""
        # Create and start queue
        queue = RequestQueue(max_workers=2, max_queue_size=5, enable_redis=False)
        await queue.start()

        try:
            # Simple handler
            async def test_handler(value):
                await asyncio.sleep(0.1)
                return f"processed_{value}"

            # Queue a request
            request_id = await queue.queue_request(test_handler, "test", priority=Priority.NORMAL)

            # Verify request is queued
            assert request_id is not None
            assert isinstance(request_id, str)

            # Get initial status
            status = await queue.get_request_status(request_id)
            assert status is not None
            assert status["request_id"] == request_id

            # Wait for result
            result = await queue.wait_for_result(request_id, timeout=5.0)
            assert result == "processed_test"

            # Check final status
            final_status = await queue.get_request_status(request_id)
            assert final_status["status"] == "completed"
            assert final_status["result"] == "processed_test"

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_queue_stats(self):
        """Test queue statistics"""
        queue = RequestQueue(max_workers=1, max_queue_size=5, enable_redis=False)
        await queue.start()

        try:
            # Get initial stats
            initial_stats = await queue.get_queue_stats()
            assert "total_queued" in initial_stats
            assert "total_processed" in initial_stats

            # Simple handler
            async def counter_handler():
                await asyncio.sleep(0.1)
                return "done"

            # Queue and process a request
            request_id = await queue.queue_request(counter_handler)
            await queue.wait_for_result(request_id)

            # Check updated stats
            final_stats = await queue.get_queue_stats()
            assert final_stats["total_processed"] > initial_stats["total_processed"]

        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health status"""
        queue = RequestQueue(max_workers=2, max_queue_size=10, enable_redis=False)
        await queue.start()

        try:
            health = await queue.get_health_status()
            assert "status" in health
            assert "health_score" in health
            assert health["status"] in ["healthy", "degraded", "unhealthy"]
            assert 0 <= health["health_score"] <= 100

        finally:
            await queue.stop()


if __name__ == "__main__":
    # Run tests directly
    import subprocess

    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
