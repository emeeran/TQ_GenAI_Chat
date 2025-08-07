"""
Async Handler for TQ GenAI Chat

This module provides ThreadPoolExecutor-based async handling for CPU-bound operations,
implementing Task 1.2.1: ThreadPoolExecutor Implementation.

Features:
- Configurable ThreadPoolExecutor pool for CPU-bound operations
- Async wrappers for blocking operations (file processing, API calls, database operations)
- Proper error handling and timeout support
- Graceful shutdown procedures
- Performance monitoring and resource management
- Request cancellation support

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import concurrent.futures
import functools
import logging
import threading
import time
import weakref
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, TypeVar

# Type definitions
T = TypeVar("T")
logger = logging.getLogger(__name__)


class AsyncHandlerConfig:
    """Configuration for AsyncHandler"""

    def __init__(
        self,
        max_workers: int = None,
        thread_name_prefix: str = "TQGenAI",
        default_timeout: float = 60.0,
        enable_monitoring: bool = True,
        monitoring_interval: float = 30.0,
        max_queue_size: int = 1000,
        enable_graceful_shutdown: bool = True,
    ):
        """
        Initialize AsyncHandler configuration

        Args:
            max_workers: Maximum number of threads (default: min(32, os.cpu_count() + 4))
            thread_name_prefix: Prefix for thread names
            default_timeout: Default timeout for operations in seconds
            enable_monitoring: Enable performance monitoring
            monitoring_interval: Monitoring statistics collection interval
            max_queue_size: Maximum size of pending operations queue
            enable_graceful_shutdown: Enable graceful shutdown on app termination
        """
        import os

        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.thread_name_prefix = thread_name_prefix
        self.default_timeout = default_timeout
        self.enable_monitoring = enable_monitoring
        self.monitoring_interval = monitoring_interval
        self.max_queue_size = max_queue_size
        self.enable_graceful_shutdown = enable_graceful_shutdown


class OperationContext:
    """Context for tracking async operations"""

    def __init__(self, operation_id: str, operation_type: str, timeout: float):
        self.operation_id = operation_id
        self.operation_type = operation_type
        self.timeout = timeout
        self.start_time = time.time()
        self.cancelled = False
        self.future: concurrent.futures.Future | None = None

    def cancel(self) -> bool:
        """Cancel the operation if possible"""
        self.cancelled = True
        if self.future and not self.future.done():
            return self.future.cancel()
        return False

    def elapsed_time(self) -> float:
        """Get elapsed time since operation started"""
        return time.time() - self.start_time

    def is_timed_out(self) -> bool:
        """Check if operation has timed out"""
        return self.elapsed_time() > self.timeout


class AsyncHandlerStats:
    """Statistics tracking for AsyncHandler"""

    def __init__(self):
        self.total_operations = 0
        self.completed_operations = 0
        self.failed_operations = 0
        self.cancelled_operations = 0
        self.timeout_operations = 0
        self.total_execution_time = 0.0
        self.max_execution_time = 0.0
        self.min_execution_time = float("inf")
        self.active_operations = 0
        self.queue_size = 0
        self.operation_types: dict[str, int] = {}
        self.lock = threading.Lock()

    def record_operation_start(self, operation_type: str):
        """Record operation start"""
        with self.lock:
            self.total_operations += 1
            self.active_operations += 1
            self.operation_types[operation_type] = self.operation_types.get(operation_type, 0) + 1

    def record_operation_complete(
        self, operation_type: str, execution_time: float, success: bool = True
    ):
        """Record operation completion"""
        with self.lock:
            self.active_operations = max(0, self.active_operations - 1)
            self.total_execution_time += execution_time
            self.max_execution_time = max(self.max_execution_time, execution_time)
            if self.min_execution_time == float("inf"):
                self.min_execution_time = execution_time
            else:
                self.min_execution_time = min(self.min_execution_time, execution_time)

            if success:
                self.completed_operations += 1
            else:
                self.failed_operations += 1

    def record_operation_cancelled(self):
        """Record operation cancellation"""
        with self.lock:
            self.cancelled_operations += 1
            self.active_operations = max(0, self.active_operations - 1)

    def record_operation_timeout(self):
        """Record operation timeout"""
        with self.lock:
            self.timeout_operations += 1
            self.active_operations = max(0, self.active_operations - 1)

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics"""
        with self.lock:
            avg_execution_time = (
                self.total_execution_time / self.completed_operations
                if self.completed_operations > 0
                else 0.0
            )

            success_rate = (
                self.completed_operations / self.total_operations
                if self.total_operations > 0
                else 0.0
            )

            return {
                "total_operations": self.total_operations,
                "completed_operations": self.completed_operations,
                "failed_operations": self.failed_operations,
                "cancelled_operations": self.cancelled_operations,
                "timeout_operations": self.timeout_operations,
                "active_operations": self.active_operations,
                "queue_size": self.queue_size,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "max_execution_time": self.max_execution_time,
                "min_execution_time": self.min_execution_time
                if self.min_execution_time != float("inf")
                else 0.0,
                "operation_types": dict(self.operation_types),
            }


class AsyncHandler:
    """
    ThreadPoolExecutor-based async handler for CPU-bound operations

    Provides async wrappers for blocking operations with proper error handling,
    timeout support, and performance monitoring.
    """

    def __init__(self, config: AsyncHandlerConfig | None = None):
        """Initialize AsyncHandler with configuration"""
        self.config = config or AsyncHandlerConfig()
        self.executor: ThreadPoolExecutor | None = None
        self.stats = AsyncHandlerStats()
        self.active_operations: dict[str, OperationContext] = {}
        self.operation_counter = 0
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        self.monitoring_task: asyncio.Task | None = None
        self._weakref_cleanup = weakref.finalize(self, self._cleanup)

        # Initialize executor
        self._initialize_executor()

        # Start monitoring if enabled
        if self.config.enable_monitoring:
            self._start_monitoring()

    def _initialize_executor(self):
        """Initialize the ThreadPoolExecutor"""
        try:
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.max_workers,
                thread_name_prefix=self.config.thread_name_prefix,
            )
            logger.info(f"AsyncHandler initialized with {self.config.max_workers} workers")
        except Exception as e:
            logger.error(f"Failed to initialize ThreadPoolExecutor: {e}")
            raise

    def _start_monitoring(self):
        """Start background monitoring task"""
        try:
            loop = asyncio.get_event_loop()
            self.monitoring_task = loop.create_task(self._monitoring_loop())
        except RuntimeError:
            # No event loop running, monitoring will start when operations begin
            pass

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while not self.shutdown_event.is_set():
            try:
                await self._cleanup_completed_operations()
                await self._check_timeouts()
                await self._update_queue_stats()

                # Log periodic statistics
                stats = self.stats.get_stats()
                logger.debug(f"AsyncHandler stats: {stats}")

                await asyncio.sleep(self.config.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _cleanup_completed_operations(self):
        """Clean up completed operations"""
        completed_ops = []

        with self.lock:
            for op_id, context in list(self.active_operations.items()):
                if context.future and context.future.done():
                    completed_ops.append(op_id)

        for op_id in completed_ops:
            with self.lock:
                if op_id in self.active_operations:
                    del self.active_operations[op_id]

    async def _check_timeouts(self):
        """Check for timed out operations"""
        timed_out_ops = []

        with self.lock:
            for op_id, context in list(self.active_operations.items()):
                if context.is_timed_out() and not context.cancelled:
                    timed_out_ops.append((op_id, context))

        for op_id, context in timed_out_ops:
            logger.warning(f"Operation {op_id} timed out after {context.elapsed_time():.2f}s")
            context.cancel()
            self.stats.record_operation_timeout()

    async def _update_queue_stats(self):
        """Update queue size statistics"""
        if self.executor:
            # Get approximate queue size (pending futures)
            queue_size = len(self.active_operations)
            self.stats.queue_size = queue_size

    def _generate_operation_id(self) -> str:
        """Generate unique operation ID"""
        with self.lock:
            self.operation_counter += 1
            return f"op_{self.operation_counter}_{int(time.time() * 1000)}"

    async def run_in_executor[T](
        self,
        func: Callable[..., T],
        *args,
        operation_type: str = "generic",
        timeout: float | None = None,
        **kwargs,
    ) -> T:
        """
        Run a function in the thread pool executor

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            operation_type: Type of operation for monitoring
            timeout: Timeout in seconds (uses default if None)
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function execution

        Raises:
            asyncio.TimeoutError: If operation times out
            Exception: Any exception raised by the function
        """
        if not self.executor:
            raise RuntimeError("AsyncHandler not properly initialized")

        # Check queue size limit
        if len(self.active_operations) >= self.config.max_queue_size:
            raise RuntimeError(f"Operation queue full (max: {self.config.max_queue_size})")

        timeout = timeout or self.config.default_timeout
        operation_id = self._generate_operation_id()

        # Create operation context
        context = OperationContext(operation_id, operation_type, timeout)

        with self.lock:
            self.active_operations[operation_id] = context

        self.stats.record_operation_start(operation_type)

        try:
            # Prepare function with arguments
            if kwargs:
                wrapped_func = functools.partial(func, *args, **kwargs)
            else:
                wrapped_func = functools.partial(func, *args) if args else func

            # Submit to executor
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(self.executor, wrapped_func)
            context.future = future

            # Wait with timeout
            try:
                result = await asyncio.wait_for(future, timeout=timeout)

                # Record successful completion
                execution_time = context.elapsed_time()
                self.stats.record_operation_complete(operation_type, execution_time, success=True)

                return result

            except TimeoutError:
                logger.warning(
                    f"Operation {operation_id} ({operation_type}) timed out after {timeout}s"
                )
                context.cancel()
                self.stats.record_operation_timeout()
                raise

        except Exception as e:
            # Record failed operation
            execution_time = context.elapsed_time()
            self.stats.record_operation_complete(operation_type, execution_time, success=False)
            logger.error(f"Operation {operation_id} ({operation_type}) failed: {e}")
            raise

        finally:
            # Clean up operation context
            with self.lock:
                if operation_id in self.active_operations:
                    del self.active_operations[operation_id]

    def run_sync[T](
        self,
        func: Callable[..., T],
        *args,
        operation_type: str = "generic",
        timeout: float | None = None,
        **kwargs,
    ) -> T:
        """
        Run a function synchronously in the thread pool (for non-async contexts)

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            operation_type: Type of operation for monitoring
            timeout: Timeout in seconds (uses default if None)
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function execution
        """
        if not self.executor:
            raise RuntimeError("AsyncHandler not properly initialized")

        timeout = timeout or self.config.default_timeout
        operation_id = self._generate_operation_id()

        self.stats.record_operation_start(operation_type)
        start_time = time.time()

        try:
            # Prepare function with arguments
            if kwargs:
                wrapped_func = functools.partial(func, *args, **kwargs)
            else:
                wrapped_func = functools.partial(func, *args) if args else func

            # Submit and wait
            future = self.executor.submit(wrapped_func)
            result = future.result(timeout=timeout)

            # Record successful completion
            execution_time = time.time() - start_time
            self.stats.record_operation_complete(operation_type, execution_time, success=True)

            return result

        except concurrent.futures.TimeoutError:
            logger.warning(
                f"Sync operation {operation_id} ({operation_type}) timed out after {timeout}s"
            )
            self.stats.record_operation_timeout()
            raise TimeoutError(f"Operation timed out after {timeout}s") from None

        except Exception as e:
            # Record failed operation
            execution_time = time.time() - start_time
            self.stats.record_operation_complete(operation_type, execution_time, success=False)
            logger.error(f"Sync operation {operation_id} ({operation_type}) failed: {e}")
            raise

    async def run_multiple(
        self,
        operations: list[dict[str, Any]],
        max_concurrent: int | None = None,
        return_exceptions: bool = False,
    ) -> list[Any]:
        """
        Run multiple operations concurrently

        Args:
            operations: List of operation dictionaries with keys:
                       'func', 'args', 'kwargs', 'operation_type', 'timeout'
            max_concurrent: Maximum concurrent operations (default: executor max_workers)
            return_exceptions: Include exceptions in results instead of raising

        Returns:
            List of results in the same order as operations
        """
        max_concurrent = max_concurrent or self.config.max_workers

        async def run_operation(op_dict):
            """Run a single operation from the operation dictionary"""
            func = op_dict["func"]
            args = op_dict.get("args", ())
            kwargs = op_dict.get("kwargs", {})
            operation_type = op_dict.get("operation_type", "batch")
            timeout = op_dict.get("timeout")

            return await self.run_in_executor(
                func, *args, operation_type=operation_type, timeout=timeout, **kwargs
            )

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def limited_operation(op_dict):
            """Run operation with concurrency limit"""
            async with semaphore:
                return await run_operation(op_dict)

        # Execute all operations
        tasks = [limited_operation(op) for op in operations]

        if return_exceptions:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = await asyncio.gather(*tasks)

        return results

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel a specific operation

        Args:
            operation_id: ID of operation to cancel

        Returns:
            True if operation was cancelled, False if not found or already completed
        """
        with self.lock:
            if operation_id in self.active_operations:
                context = self.active_operations[operation_id]
                success = context.cancel()
                if success:
                    self.stats.record_operation_cancelled()
                return success
        return False

    def cancel_all_operations(self) -> int:
        """
        Cancel all active operations

        Returns:
            Number of operations cancelled
        """
        cancelled_count = 0

        with self.lock:
            operation_ids = list(self.active_operations.keys())

        for op_id in operation_ids:
            if self.cancel_operation(op_id):
                cancelled_count += 1

        return cancelled_count

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics"""
        stats = self.stats.get_stats()

        # Add executor information
        if self.executor:
            stats.update(
                {
                    "executor_max_workers": self.config.max_workers,
                    "executor_thread_name_prefix": self.config.thread_name_prefix,
                    "default_timeout": self.config.default_timeout,
                    "max_queue_size": self.config.max_queue_size,
                }
            )

        return stats

    def get_active_operations(self) -> dict[str, dict[str, Any]]:
        """Get information about active operations"""
        with self.lock:
            return {
                op_id: {
                    "operation_type": context.operation_type,
                    "elapsed_time": context.elapsed_time(),
                    "timeout": context.timeout,
                    "cancelled": context.cancelled,
                    "is_timed_out": context.is_timed_out(),
                }
                for op_id, context in self.active_operations.items()
            }

    async def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """
        Gracefully shutdown the AsyncHandler

        Args:
            wait: Whether to wait for pending operations
            timeout: Maximum time to wait for shutdown
        """
        logger.info("Starting AsyncHandler shutdown...")

        # Signal shutdown
        self.shutdown_event.set()

        # Cancel monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        # Handle pending operations
        if wait and self.active_operations:
            logger.info(
                f"Waiting for {len(self.active_operations)} active operations to complete..."
            )

            # Wait for operations with timeout
            start_time = time.time()
            while self.active_operations and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.1)

            # Cancel remaining operations
            remaining = self.cancel_all_operations()
            if remaining > 0:
                logger.warning(f"Cancelled {remaining} remaining operations during shutdown")

        # Shutdown executor
        if self.executor:
            self.executor.shutdown(wait=wait)
            self.executor = None

        logger.info("AsyncHandler shutdown completed")

    def _cleanup(self):
        """Cleanup method called by weakref finalizer"""
        if self.executor:
            try:
                self.executor.shutdown(wait=False)
            except Exception:
                logger.debug("Exception during cleanup", exc_info=True)

    @asynccontextmanager
    async def operation_context(self, operation_type: str = "context"):
        """
        Context manager for grouping related operations

        Args:
            operation_type: Type identifier for the context

        Example:
            async with handler.operation_context("file_processing"):
                result1 = await handler.run_in_executor(process_file, file1)
                result2 = await handler.run_in_executor(process_file, file2)
        """
        context_start = time.time()
        logger.debug(f"Starting operation context: {operation_type}")

        try:
            yield self
        finally:
            context_time = time.time() - context_start
            logger.debug(f"Operation context {operation_type} completed in {context_time:.2f}s")


# Global async handler instance
_global_async_handler: AsyncHandler | None = None
_handler_lock = threading.Lock()


def get_async_handler(config: AsyncHandlerConfig | None = None) -> AsyncHandler:
    """
    Get or create the global AsyncHandler instance

    Args:
        config: Configuration for new handler (only used if handler doesn't exist)

    Returns:
        Global AsyncHandler instance
    """
    global _global_async_handler

    with _handler_lock:
        if _global_async_handler is None:
            _global_async_handler = AsyncHandler(config)
        return _global_async_handler


def shutdown_async_handler():
    """Shutdown the global AsyncHandler instance"""
    global _global_async_handler

    with _handler_lock:
        if _global_async_handler:
            # For synchronous shutdown
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule shutdown for later
                    loop.create_task(_global_async_handler.shutdown())
                else:
                    # Run shutdown immediately
                    loop.run_until_complete(_global_async_handler.shutdown())
            except RuntimeError:
                # No event loop, use sync shutdown
                if _global_async_handler.executor:
                    _global_async_handler.executor.shutdown(wait=True)

            _global_async_handler = None


# Convenience decorators and functions


def async_operation(operation_type: str = "decorated", timeout: float | None = None):
    """
    Decorator to automatically run function in AsyncHandler

    Args:
        operation_type: Type identifier for monitoring
        timeout: Timeout for the operation

    Example:
        @async_operation("file_processing", timeout=30.0)
        async def process_file(file_path):
            # This will run in thread pool
            return expensive_file_operation(file_path)
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            handler = get_async_handler()
            return await handler.run_in_executor(
                func, *args, operation_type=operation_type, timeout=timeout, **kwargs
            )

        return wrapper

    return decorator


async def run_in_executor[T](
    func: Callable[..., T],
    *args,
    operation_type: str = "generic",
    timeout: float | None = None,
    **kwargs,
) -> T:
    """
    Convenience function to run operation in global AsyncHandler

    Args:
        func: Function to execute
        *args: Positional arguments
        operation_type: Type identifier for monitoring
        timeout: Timeout for the operation
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    handler = get_async_handler()
    return await handler.run_in_executor(
        func, *args, operation_type=operation_type, timeout=timeout, **kwargs
    )


def run_sync[T](
    func: Callable[..., T],
    *args,
    operation_type: str = "generic",
    timeout: float | None = None,
    **kwargs,
) -> T:
    """
    Convenience function to run operation synchronously in global AsyncHandler

    Args:
        func: Function to execute
        *args: Positional arguments
        operation_type: Type identifier for monitoring
        timeout: Timeout for the operation
        **kwargs: Keyword arguments

    Returns:
        Function result
    """
    handler = get_async_handler()
    return handler.run_sync(func, *args, operation_type=operation_type, timeout=timeout, **kwargs)


def async_route(timeout: float = 60.0):
    """
    Decorator to convert synchronous Flask route to async processing

    Usage:
        @app.route("/api/endpoint", methods=["POST"])
        @async_route(timeout=30.0)
        def my_endpoint():
            # This will run in thread pool
            return {"result": "success"}
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get async handler
            handler = get_async_handler()

            # Create event loop if not exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run function in thread pool
            return loop.run_until_complete(
                handler.run_in_executor(func, *args, timeout=timeout, **kwargs)
            )

        return wrapper

    return decorator


async def cleanup_async_handler():
    """Cleanup global async handler"""
    global _global_async_handler
    if _global_async_handler:
        await _global_async_handler.shutdown()
        _global_async_handler = None
