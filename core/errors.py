"""Enhanced error handling system"""

import logging
import traceback
from functools import wraps
from typing import Any

from flask import jsonify


class APIError(Exception):
    """Base API exception"""

    def __init__(self, message: str, status_code: int = 500, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationError(APIError):
    """Validation error"""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, 400, details)


class ProviderError(APIError):
    """AI Provider error"""

    def __init__(self, message: str, provider: str, details: dict | None = None):
        super().__init__(message, 503, details)
        self.provider = provider


class RateLimitError(APIError):
    """Rate limit error"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429)


class ErrorHandler:
    """Centralized error handling"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle_api_error(self, error: APIError) -> dict[str, Any]:
        """Handle API errors"""
        self.logger.error(f"API Error: {error.message}", extra=error.details)

        return {
            "success": False,
            "error": error.message,
            "status_code": error.status_code,
            "details": error.details,
        }

    def handle_unexpected_error(self, error: Exception) -> dict[str, Any]:
        """Handle unexpected errors"""
        self.logger.exception("Unexpected error occurred")

        return {
            "success": False,
            "error": "An unexpected error occurred",
            "status_code": 500,
            "details": {
                "type": type(error).__name__,
                "traceback": (
                    traceback.format_exc() if self.logger.level <= logging.DEBUG else None
                ),
            },
        }


def handle_errors(func):
    """Decorator for consistent error handling"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            error_handler = ErrorHandler()
            return jsonify(error_handler.handle_api_error(e)), e.status_code
        except Exception as e:
            error_handler = ErrorHandler()
            return jsonify(error_handler.handle_unexpected_error(e)), 500

    return wrapper


def setup_logging(app):
    """Setup application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )

    # Set Flask logger level
    app.logger.setLevel(logging.INFO)
