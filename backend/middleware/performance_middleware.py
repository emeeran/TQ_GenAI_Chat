"""
Performance Middleware - Zero Risk Enhancement

FastAPI middleware for automatic performance tracking.
All tracking is additive and doesn't modify response behavior.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from monitoring.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)


class PerformanceTrackingMiddleware(BaseHTTPMiddleware):
    """
    Zero-risk performance tracking middleware.

    Automatically tracks:
    - Request/response times
    - Status codes
    - Request counts
    - Error rates
    - User agents

    Does not modify responses or interfere with existing functionality.
    """

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",  # Exclude health checks from performance tracking
            "/metrics",  # Exclude metrics endpoints themselves
            "/favicon.ico",
        ]
        self.performance_monitor = get_performance_monitor()
        logger.info("Performance tracking middleware initialized - zero risk mode")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and track performance metrics.
        Zero-risk: always passes through the original call_next().
        """
        start_time = time.time()
        method = request.method
        path = request.url.path

        # Skip tracking for excluded paths
        if path in self.exclude_paths:
            return await call_next(request)

        # Get user agent for tracking
        user_agent = request.headers.get("user-agent", "")[:100]  # Limit length

        try:
            # Process the request normally
            response = await call_next(request)

            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000

            # Record performance metrics (additive, no side effects)
            self.performance_monitor.record_api_call(
                endpoint=path,
                method=method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                user_agent=user_agent,
            )

            # Log slow requests for awareness
            if response_time_ms > 5000:  # 5 second threshold
                logger.warning(
                    f"Slow request detected: {method} {path} - "
                    f"{response_time_ms:.2f}ms - {response.status_code}"
                )

            return response

        except Exception as e:
            # Calculate response time even for exceptions
            response_time_ms = (time.time() - start_time) * 1000

            # Record the error
            self.performance_monitor.record_api_call(
                endpoint=path,
                method=method,
                status_code=500,  # Internal server error
                response_time_ms=response_time_ms,
                user_agent=user_agent,
            )

            logger.error(f"Request failed with exception: {method} {path} - {str(e)}")
            raise  # Re-raise the original exception to maintain existing behavior
