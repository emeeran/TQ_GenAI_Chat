"""
Common Flask utilities and decorators.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Optional

from flask import jsonify, request

logger = logging.getLogger(__name__)


def handle_errors(f: Callable) -> Callable:
    """Decorator for consistent error handling across routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error in {f.__name__}: {e}")
            return jsonify({"error": str(e)}), 400
        except FileNotFoundError as e:
            logger.warning(f"File not found in {f.__name__}: {e}")
            return jsonify({"error": "Resource not found"}), 404
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    return decorated_function


def validate_json_request(required_fields: Optional[list] = None) -> Callable:
    """Decorator to validate JSON request data."""

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return (
                        jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}),
                        400,
                    )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def rate_limit(requests_per_minute: int = 60) -> Callable:
    """Simple in-memory rate limiting decorator."""
    request_counts: dict[str, dict[str, int]] = {}

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import time

            client_ip = request.remote_addr or "unknown"
            current_minute = int(time.time() // 60)

            if client_ip not in request_counts:
                request_counts[client_ip] = {}

            # Clean old entries
            request_counts[client_ip] = {
                minute: count
                for minute, count in request_counts[client_ip].items()
                if minute >= current_minute - 1
            }

            # Check current minute
            current_count = request_counts[client_ip].get(current_minute, 0)
            if current_count >= requests_per_minute:
                return jsonify({"error": "Rate limit exceeded"}), 429

            # Increment counter
            request_counts[client_ip][current_minute] = current_count + 1

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def log_request_info(f: Callable) -> Callable:
    """Decorator to log request information."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"Request to {f.__name__}: {request.method} {request.path}")
        if request.is_json:
            logger.debug(
                f"Request data keys: {list(request.get_json().keys()) if request.get_json() else []}"
            )
        return f(*args, **kwargs)

    return decorated_function
