"""
ThreadPoolExecutor Integration for app.py

This module provides wrappers for CPU-bound operations in app.py to implement
Task 1.2.1: ThreadPoolExecutor Implementation. This integrates the AsyncHandler
for better performance under concurrent load.

Features:
- Wraps chat processing with ThreadPoolExecutor
- Async file processing with proper resource management
- Database operations optimization
- TTS processing with timeout handling
- Graceful error handling and monitoring

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import functools
import logging
import time
from typing import Any

from core.async_handler import AsyncHandlerConfig, get_async_handler

logger = logging.getLogger(__name__)


def init_async_app_handler():
    """Initialize AsyncHandler for the Flask app with optimal configuration"""

    # Configure AsyncHandler for Flask app workload
    config = AsyncHandlerConfig(
        max_workers=32,  # Optimal for mixed I/O and CPU work
        thread_name_prefix="TQGenAI-App",
        default_timeout=120.0,  # 2 minutes for chat requests
        enable_monitoring=True,
        monitoring_interval=60.0,  # Monitor every minute
        max_queue_size=500,  # Large queue for high traffic
        enable_graceful_shutdown=True,
    )

    handler = get_async_handler(config)
    logger.info("AsyncHandler initialized for Flask app")
    return handler


def async_chat_route(timeout: float = 120.0):
    """
    Decorator to wrap chat processing in ThreadPoolExecutor

    Args:
        timeout: Timeout for chat processing operations

    Usage:
        @app.route("/chat", methods=["POST"])
        @async_chat_route(timeout=60.0)
        def chat():
            # This will run in thread pool
            return process_chat_logic()
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_async_handler()

            try:
                # Get or create event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Run chat processing in thread pool
                result = loop.run_until_complete(
                    handler.run_in_executor(
                        func, *args, operation_type="chat_processing", timeout=timeout, **kwargs
                    )
                )

                return result

            except Exception as e:
                logger.error(f"Async chat processing failed: {e}")
                raise
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        return wrapper

    return decorator


def async_file_operation(operation_type: str = "file_processing", timeout: float = 300.0):
    """
    Decorator for file processing operations

    Args:
        operation_type: Type of file operation for monitoring
        timeout: Timeout for file operations (5 minutes default)

    Usage:
        @async_file_operation("file_upload", timeout=180.0)
        def process_uploaded_file(file_path):
            # Heavy file processing
            return result
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            handler = get_async_handler()
            return await handler.run_in_executor(
                func, *args, operation_type=operation_type, timeout=timeout, **kwargs
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            handler = get_async_handler()
            return handler.run_sync(
                func, *args, operation_type=operation_type, timeout=timeout, **kwargs
            )

        # Return async version if possible, sync otherwise
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def async_database_operation(timeout: float = 30.0):
    """
    Decorator for database operations

    Args:
        timeout: Timeout for database operations

    Usage:
        @async_database_operation(timeout=15.0)
        def save_chat_to_db(chat_data):
            # Database save operation
            return result
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_async_handler()

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    handler.run_in_executor(
                        func, *args, operation_type="database_operation", timeout=timeout, **kwargs
                    )
                )

                return result

            except Exception as e:
                logger.error(f"Async database operation failed: {e}")
                raise
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        return wrapper

    return decorator


def async_tts_processing(timeout: float = 60.0):
    """
    Decorator for TTS processing operations

    Args:
        timeout: Timeout for TTS operations

    Usage:
        @async_tts_processing(timeout=30.0)
        def generate_speech(text, voice):
            # TTS generation
            return audio_data
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_async_handler()

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    handler.run_in_executor(
                        func, *args, operation_type="tts_processing", timeout=timeout, **kwargs
                    )
                )

                return result

            except Exception as e:
                logger.error(f"Async TTS processing failed: {e}")
                raise
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        return wrapper

    return decorator


def async_context_search(timeout: float = 45.0):
    """
    Decorator for context search operations

    Args:
        timeout: Timeout for search operations

    Usage:
        @async_context_search(timeout=30.0)
        def search_documents(query):
            # Document search with vector similarity
            return results
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            handler = get_async_handler()

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                result = loop.run_until_complete(
                    handler.run_in_executor(
                        func, *args, operation_type="context_search", timeout=timeout, **kwargs
                    )
                )

                return result

            except Exception as e:
                logger.error(f"Async context search failed: {e}")
                raise
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        return wrapper

    return decorator


class AsyncAppPerformanceMonitor:
    """Performance monitoring for async operations in the app"""

    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.total_processing_time = 0.0
        self.last_stats_log = time.time()

    def log_request(self, processing_time: float):
        """Log a completed request"""
        self.request_count += 1
        self.total_processing_time += processing_time

        # Log stats every 5 minutes
        now = time.time()
        if now - self.last_stats_log > 300:
            self.log_performance_stats()
            self.last_stats_log = now

    def log_performance_stats(self):
        """Log current performance statistics"""
        handler = get_async_handler()
        async_stats = handler.get_stats()

        uptime = time.time() - self.start_time
        avg_processing_time = (
            self.total_processing_time / self.request_count if self.request_count > 0 else 0.0
        )

        logger.info(
            f"""
        === TQ GenAI Chat Performance Stats ===
        Uptime: {uptime:.1f}s
        Total Requests: {self.request_count}
        Avg Processing Time: {avg_processing_time:.2f}s

        AsyncHandler Stats:
        - Total Operations: {async_stats.get('total_operations', 0)}
        - Success Rate: {async_stats.get('success_rate', 0.0):.2%}
        - Active Operations: {async_stats.get('active_operations', 0)}
        - Avg Execution Time: {async_stats.get('avg_execution_time', 0.0):.2f}s
        - Max Workers: {async_stats.get('executor_max_workers', 0)}

        Operation Types:
        {async_stats.get('operation_types', {})}
        ========================================
        """
        )

    def get_current_stats(self) -> dict[str, Any]:
        """Get current performance statistics"""
        handler = get_async_handler()
        async_stats = handler.get_stats()

        uptime = time.time() - self.start_time
        avg_processing_time = (
            self.total_processing_time / self.request_count if self.request_count > 0 else 0.0
        )

        return {
            "app_stats": {
                "uptime": uptime,
                "total_requests": self.request_count,
                "avg_processing_time": avg_processing_time,
                "requests_per_second": self.request_count / uptime if uptime > 0 else 0.0,
            },
            "async_stats": async_stats,
        }


# Global performance monitor
app_monitor = AsyncAppPerformanceMonitor()


def get_app_performance_stats() -> dict[str, Any]:
    """Get comprehensive app performance statistics"""
    return app_monitor.get_current_stats()


# Batch processing utilities for multiple operations


async def process_files_batch(file_operations: list[dict[str, Any]]) -> list[Any]:
    """
    Process multiple files concurrently using AsyncHandler

    Args:
        file_operations: List of file operation dictionaries

    Returns:
        List of processing results
    """
    handler = get_async_handler()

    # Add operation type for monitoring
    for op in file_operations:
        op.setdefault("operation_type", "batch_file_processing")
        op.setdefault("timeout", 300.0)  # 5 minute timeout for files

    return await handler.run_multiple(
        file_operations,
        max_concurrent=8,  # Limit concurrent file processing
        return_exceptions=True,
    )


async def process_chat_requests_batch(chat_operations: list[dict[str, Any]]) -> list[Any]:
    """
    Process multiple chat requests concurrently

    Args:
        chat_operations: List of chat operation dictionaries

    Returns:
        List of chat results
    """
    handler = get_async_handler()

    # Add operation type for monitoring
    for op in chat_operations:
        op.setdefault("operation_type", "batch_chat_processing")
        op.setdefault("timeout", 120.0)  # 2 minute timeout for chat

    return await handler.run_multiple(
        chat_operations,
        max_concurrent=16,
        return_exceptions=True,  # Higher concurrency for chat
    )


def monitor_performance():
    """Decorator to monitor route performance"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                processing_time = time.time() - start_time
                app_monitor.log_request(processing_time)
                return result
            except Exception:
                processing_time = time.time() - start_time
                app_monitor.log_request(processing_time)
                raise

        return wrapper

    return decorator


# Context managers for async operations


class AsyncOperationContext:
    """Context manager for tracking async operations"""

    def __init__(self, operation_type: str = "app_operation"):
        self.operation_type = operation_type
        self.start_time = None
        self.handler = get_async_handler()

    async def __aenter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting async operation: {self.operation_type}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type:
            logger.error(
                f"Async operation {self.operation_type} failed after {duration:.2f}s: {exc_val}"
            )
        else:
            logger.debug(f"Async operation {self.operation_type} completed in {duration:.2f}s")


# Route integration helpers


def wrap_route_with_async(route_func, operation_type: str = "route", timeout: float = 60.0):
    """
    Wrap a Flask route function with AsyncHandler

    Args:
        route_func: Flask route function to wrap
        operation_type: Type of operation for monitoring
        timeout: Timeout for the operation

    Returns:
        Wrapped function that runs in ThreadPoolExecutor
    """

    @functools.wraps(route_func)
    def wrapper(*args, **kwargs):
        handler = get_async_handler()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                handler.run_in_executor(
                    route_func, *args, operation_type=operation_type, timeout=timeout, **kwargs
                )
            )

            return result

        except Exception as e:
            logger.error(f"Async route {operation_type} failed: {e}")
            raise
        finally:
            try:
                loop.close()
            except Exception:
                pass

    return wrapper
