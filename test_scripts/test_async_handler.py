"""
Test Suite for Task 1.2.1: ThreadPoolExecutor Implementation

This test file validates the AsyncHandler ThreadPoolExecutor implementation
including performance under concurrent load, proper error handling, and
integration with Flask routes.

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import threading
import time

import pytest

from core.app_async_wrappers import (
    AsyncAppPerformanceMonitor,
    async_chat_route,
    async_file_operation,
    process_files_batch,
)
from core.async_handler import (
    AsyncHandler,
    AsyncHandlerConfig,
    AsyncHandlerStats,
    OperationContext,
    async_operation,
    run_sync,
)


class TestAsyncHandlerCore:
    """Test core AsyncHandler functionality"""

    def test_async_handler_initialization(self):
        """Test AsyncHandler initializes with correct configuration"""
        config = AsyncHandlerConfig(max_workers=16, thread_name_prefix="Test", default_timeout=30.0)

        handler = AsyncHandler(config)
        assert handler.config.max_workers == 16
        assert handler.config.thread_name_prefix == "Test"
        assert handler.config.default_timeout == 30.0
        assert handler.executor is not None

    def test_operation_context(self):
        """Test operation context tracking"""
        context = OperationContext("test_op", "test_type", 60.0)

        assert context.operation_id == "test_op"
        assert context.operation_type == "test_type"
        assert context.timeout == 60.0
        assert context.cancelled is False
        assert context.elapsed_time() >= 0

    def test_async_handler_stats(self):
        """Test statistics tracking"""
        stats = AsyncHandlerStats()

        # Record operations
        stats.record_operation_start("test_op")
        stats.record_operation_complete("test_op", 1.5, success=True)

        current_stats = stats.get_stats()
        assert current_stats["total_operations"] == 1
        assert current_stats["completed_operations"] == 1
        assert current_stats["success_rate"] == 1.0
        assert current_stats["avg_execution_time"] == 1.5


class TestAsyncHandlerOperations:
    """Test AsyncHandler operation execution"""

    @pytest.mark.asyncio
    async def test_run_in_executor_success(self):
        """Test successful operation execution"""
        handler = AsyncHandler()

        def blocking_operation(x, y):
            time.sleep(0.1)  # Simulate work
            return x + y

        result = await handler.run_in_executor(
            blocking_operation, 5, 3, operation_type="test_math", timeout=5.0
        )

        assert result == 8

    @pytest.mark.asyncio
    async def test_run_in_executor_timeout(self):
        """Test operation timeout handling"""
        handler = AsyncHandler()

        def slow_operation():
            time.sleep(2.0)  # Longer than timeout
            return "completed"

        with pytest.raises(TimeoutError):
            await handler.run_in_executor(slow_operation, operation_type="slow_test", timeout=0.5)

    @pytest.mark.asyncio
    async def test_run_in_executor_error(self):
        """Test operation error handling"""
        handler = AsyncHandler()

        def failing_operation():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await handler.run_in_executor(failing_operation, operation_type="error_test")

    def test_run_sync_operation(self):
        """Test synchronous operation execution"""
        handler = AsyncHandler()

        def blocking_operation(x):
            return x * 2

        result = handler.run_sync(blocking_operation, 5, operation_type="sync_test", timeout=5.0)

        assert result == 10

    @pytest.mark.asyncio
    async def test_run_multiple_operations(self):
        """Test concurrent multiple operations"""
        handler = AsyncHandler()

        def math_operation(x, y, op):
            if op == "add":
                return x + y
            elif op == "multiply":
                return x * y
            else:
                return 0

        operations = [
            {
                "func": math_operation,
                "args": (5, 3),
                "kwargs": {"op": "add"},
                "operation_type": "batch_math",
            },
            {
                "func": math_operation,
                "args": (5, 3),
                "kwargs": {"op": "multiply"},
                "operation_type": "batch_math",
            },
        ]

        results = await handler.run_multiple(operations, max_concurrent=2)

        assert results[0] == 8  # 5 + 3
        assert results[1] == 15  # 5 * 3


class TestConcurrentPerformance:
    """Test performance under concurrent load"""

    @pytest.mark.asyncio
    async def test_concurrent_load_50_operations(self):
        """Test handling 50+ concurrent operations (Task 1.2.1 requirement)"""
        handler = AsyncHandler(AsyncHandlerConfig(max_workers=16))

        def cpu_intensive_task(n):
            # Simulate CPU-bound work
            result = 0
            for i in range(n * 1000):
                result += i
            return result

        # Create 55 concurrent operations
        tasks = []
        start_time = time.time()

        for i in range(55):
            task = handler.run_in_executor(
                cpu_intensive_task, i + 1, operation_type="concurrent_test", timeout=30.0
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify all operations completed successfully
        assert len(results) == 55
        assert all(isinstance(result, int) for result in results)

        # Check performance metrics
        total_time = end_time - start_time
        operations_per_second = 55 / total_time

        print("Concurrent test results:")
        print("- Operations: 55")
        print(f"- Total time: {total_time:.2f}s")
        print(f"- Ops/second: {operations_per_second:.2f}")

        # Verify performance improvement (should handle 50+ ops in reasonable time)
        assert total_time < 60, f"Too slow: {total_time:.2f}s for 55 operations"
        assert operations_per_second > 1, f"Too slow: {operations_per_second:.2f} ops/sec"

        # Check handler statistics
        stats = handler.get_stats()
        assert stats["total_operations"] >= 55
        assert stats["success_rate"] > 0.95

    def test_thread_pool_stress(self):
        """Test ThreadPoolExecutor under stress with sync operations"""
        handler = AsyncHandler(AsyncHandlerConfig(max_workers=8))

        def stress_operation(duration):
            start = time.time()
            while time.time() - start < duration:
                # Simulate work
                sum(range(1000))
            return duration

        # Run 30 operations concurrently using threads
        results = []
        threads = []

        def run_operation():
            try:
                result = handler.run_sync(
                    stress_operation, 0.1, operation_type="stress_test", timeout=5.0
                )
                results.append(result)
            except Exception as e:
                results.append(f"Error: {e}")

        start_time = time.time()

        # Launch threads
        for _ in range(30):
            thread = threading.Thread(target=run_operation)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.time()

        # Verify results
        successful_ops = sum(1 for r in results if isinstance(r, float))
        success_rate = successful_ops / len(results)

        assert success_rate > 0.90, f"Success rate too low: {success_rate:.2%}"
        assert end_time - start_time < 15, "Stress test took too long"


class TestFlaskIntegration:
    """Test Flask app integration with AsyncHandler"""

    def test_async_chat_route_decorator(self):
        """Test chat route decorator functionality"""

        @async_chat_route(timeout=30.0)
        def mock_chat_route():
            time.sleep(0.1)  # Simulate processing
            return {"response": "Hello from async chat!"}

        result = mock_chat_route()
        assert result["response"] == "Hello from async chat!"

    def test_async_file_operation_decorator(self):
        """Test file operation decorator"""

        @async_file_operation("test_file", timeout=10.0)
        def mock_file_process(filename):
            return f"Processed {filename}"

        # Test sync version
        result = mock_file_process("test.txt")
        assert result == "Processed test.txt"

    def test_performance_monitoring(self):
        """Test performance monitoring functionality"""
        monitor = AsyncAppPerformanceMonitor()

        # Log some requests
        monitor.log_request(1.5)
        monitor.log_request(2.0)
        monitor.log_request(1.0)

        stats = monitor.get_current_stats()

        assert stats["app_stats"]["total_requests"] == 3
        assert stats["app_stats"]["avg_processing_time"] == 1.5
        assert "async_stats" in stats

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test batch processing capabilities"""

        def mock_file_process(filename, size):
            return {"filename": filename, "size": size}

        operations = [
            {
                "func": mock_file_process,
                "args": (f"file_{i}.txt", i * 100),
                "operation_type": "batch_test",
            }
            for i in range(10)
        ]

        results = await process_files_batch(operations)

        assert len(results) == 10
        assert all("filename" in r and "size" in r for r in results)


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_queue_limit(self):
        """Test operation queue size limit"""
        config = AsyncHandlerConfig(max_queue_size=5)
        handler = AsyncHandler(config)

        def slow_task():
            time.sleep(0.5)
            return "done"

        # Fill up the queue
        tasks = []
        for i in range(5):
            task = handler.run_in_executor(slow_task, operation_type="queue_test")
            tasks.append(task)

        # This should raise an error due to queue limit
        with pytest.raises(RuntimeError, match="Operation queue full"):
            await handler.run_in_executor(slow_task, operation_type="queue_test")

        # Clean up
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_operation_cancellation(self):
        """Test operation cancellation"""
        handler = AsyncHandler()

        def long_running_task():
            time.sleep(10)  # Long task
            return "completed"

        # Start operation
        task = asyncio.create_task(
            handler.run_in_executor(long_running_task, operation_type="cancel_test")
        )

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Cancel the operation
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown handling"""
        handler = AsyncHandler()

        def quick_task():
            time.sleep(0.1)
            return "done"

        # Start some operations
        tasks = [
            handler.run_in_executor(quick_task, operation_type="shutdown_test") for _ in range(3)
        ]

        # Wait a bit then shutdown
        await asyncio.sleep(0.05)
        await handler.shutdown(wait=True, timeout=5.0)

        # Operations should complete or be cancelled
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 3


class TestDecorators:
    """Test decorator functionality"""

    @pytest.mark.asyncio
    async def test_async_operation_decorator(self):
        """Test @async_operation decorator"""

        @async_operation("decorated_test", timeout=10.0)
        async def decorated_function(x, y):
            return x * y

        result = await decorated_function(6, 7)
        assert result == 42

    def test_convenience_functions(self):
        """Test convenience functions"""

        def simple_calc(a, b):
            return a + b

        # Test sync function
        result = run_sync(simple_calc, 10, 20, operation_type="convenience_test")
        assert result == 30


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    @pytest.mark.asyncio
    async def test_mixed_workload_simulation(self):
        """Simulate mixed chat + file + database workload"""
        handler = AsyncHandler()

        def chat_processing(message_count):
            # Simulate API calls and text processing
            time.sleep(0.1 * message_count)
            return f"Processed {message_count} messages"

        def file_processing(file_size):
            # Simulate file parsing
            time.sleep(0.05 * file_size)
            return f"Processed {file_size}MB file"

        def database_operation(record_count):
            # Simulate database writes
            time.sleep(0.02 * record_count)
            return f"Saved {record_count} records"

        # Create mixed workload
        operations = []

        # 20 chat operations
        for i in range(20):
            operations.append(
                {
                    "func": chat_processing,
                    "args": (i + 1,),
                    "operation_type": "mixed_chat",
                    "timeout": 30.0,
                }
            )

        # 10 file operations
        for i in range(10):
            operations.append(
                {
                    "func": file_processing,
                    "args": (i + 1,),
                    "operation_type": "mixed_file",
                    "timeout": 60.0,
                }
            )

        # 15 database operations
        for i in range(15):
            operations.append(
                {
                    "func": database_operation,
                    "args": ((i + 1) * 10,),
                    "operation_type": "mixed_database",
                    "timeout": 15.0,
                }
            )

        # Execute mixed workload
        start_time = time.time()
        results = await handler.run_multiple(operations, max_concurrent=12, return_exceptions=True)
        end_time = time.time()

        # Verify results
        successful_ops = sum(
            1 for r in results if isinstance(r, str) and "Processed" in r or "Saved" in r
        )
        success_rate = successful_ops / len(results)

        print("Mixed workload results:")
        print(f"- Total operations: {len(operations)}")
        print(f"- Successful: {successful_ops}")
        print(f"- Success rate: {success_rate:.2%}")
        print(f"- Total time: {end_time - start_time:.2f}s")

        assert success_rate > 0.95
        assert end_time - start_time < 30  # Should complete within 30 seconds


if __name__ == "__main__":
    # Run basic performance test
    import asyncio

    async def quick_performance_test():
        """Quick test to verify ThreadPoolExecutor is working"""
        print("🚀 Testing ThreadPoolExecutor Implementation...")

        handler = AsyncHandler()

        def cpu_work(n):
            result = sum(range(n * 1000))
            return result

        # Test 25 concurrent operations
        tasks = []
        start_time = time.time()

        for i in range(25):
            task = handler.run_in_executor(cpu_work, i + 1, operation_type="quick_test")
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        end_time = time.time()

        print(f"✅ Processed {len(results)} operations in {end_time - start_time:.2f}s")
        print(f"📊 Handler stats: {handler.get_stats()}")

        await handler.shutdown()
        print("🎉 ThreadPoolExecutor test completed successfully!")

    asyncio.run(quick_performance_test())
