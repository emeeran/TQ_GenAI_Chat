"""
Flask integration for Request Queue System
Provides endpoints for queue monitoring and management
"""

import asyncio
import logging
from functools import wraps

from flask import Blueprint, jsonify, request

from .request_queue import (
    Priority,
    QueueFullException,
    RateLimitExceededException,
    RequestCancelledException,
    RequestFailedException,
    RequestNotFoundException,
    RequestTimeoutException,
    get_request_queue,
)

logger = logging.getLogger(__name__)

# Create Blueprint for queue endpoints
queue_bp = Blueprint("queue", __name__, url_prefix="/api/queue")


def async_endpoint(f):
    """Decorator to handle async functions in Flask"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If loop is already running, create a task
            return asyncio.create_task(f(*args, **kwargs))
        else:
            return loop.run_until_complete(f(*args, **kwargs))

    return wrapper


def queue_required(f):
    """Decorator to ensure queue is available"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            get_request_queue()
            return f(*args, **kwargs)
        except RuntimeError as e:
            return jsonify({"error": "Queue not initialized", "message": str(e)}), 503

    return wrapper


@queue_bp.route("/health", methods=["GET"])
@queue_required
@async_endpoint
async def queue_health():
    """Get queue system health status"""
    try:
        queue = get_request_queue()
        health_status = await queue.get_health_status()

        status_code = 200
        if health_status["status"] == "degraded":
            status_code = 206
        elif health_status["status"] == "unhealthy":
            status_code = 503

        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"Error getting queue health: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@queue_bp.route("/stats", methods=["GET"])
@queue_required
@async_endpoint
async def queue_stats():
    """Get detailed queue statistics"""
    try:
        queue = get_request_queue()
        stats = await queue.get_queue_stats()
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/status/<request_id>", methods=["GET"])
@queue_required
@async_endpoint
async def request_status(request_id: str):
    """Get status of specific request"""
    try:
        queue = get_request_queue()
        status = await queue.get_request_status(request_id)

        if status is None:
            return jsonify({"error": "Request not found", "request_id": request_id}), 404

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting request status: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/cancel/<request_id>", methods=["POST"])
@queue_required
@async_endpoint
async def cancel_request(request_id: str):
    """Cancel a queued or processing request"""
    try:
        queue = get_request_queue()
        success = await queue.cancel_request(request_id)

        if not success:
            return (
                jsonify(
                    {"error": "Request not found or cannot be cancelled", "request_id": request_id}
                ),
                404,
            )

        return jsonify({"message": "Request cancelled successfully", "request_id": request_id})

    except Exception as e:
        logger.error(f"Error cancelling request: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/submit", methods=["POST"])
@queue_required
@async_endpoint
async def submit_request():
    """Submit a request to the queue for processing"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Extract request parameters
        handler_name = data.get("handler")
        if not handler_name:
            return jsonify({"error": "Handler name required"}), 400

        # Map handler name to actual function
        handler = get_handler_by_name(handler_name)
        if not handler:
            return jsonify({"error": f"Unknown handler: {handler_name}"}), 400

        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        priority = Priority[data.get("priority", "NORMAL").upper()]
        timeout = data.get("timeout", 30.0)
        max_retries = data.get("max_retries", 3)

        # Get user info for rate limiting
        user_id = data.get("user_id")
        ip_address = request.remote_addr

        queue = get_request_queue()
        request_id = await queue.queue_request(
            handler,
            *args,
            priority=priority,
            user_id=user_id,
            ip_address=ip_address,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

        return jsonify(
            {
                "request_id": request_id,
                "message": "Request queued successfully",
                "priority": priority.name,
                "estimated_position": await estimate_queue_position(priority),
            }
        )

    except QueueFullException as e:
        return jsonify({"error": "Queue at capacity", "message": str(e)}), 503

    except RateLimitExceededException as e:
        return jsonify({"error": "Rate limit exceeded", "message": str(e)}), 429

    except Exception as e:
        logger.error(f"Error submitting request: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/wait/<request_id>", methods=["GET"])
@queue_required
@async_endpoint
async def wait_for_result(request_id: str):
    """Wait for request completion and return result"""
    try:
        timeout = request.args.get("timeout", type=float, default=30.0)

        queue = get_request_queue()
        result = await queue.wait_for_result(request_id, timeout)

        return jsonify({"request_id": request_id, "result": result, "status": "completed"})

    except RequestNotFoundException as e:
        return jsonify({"error": "Request not found", "message": str(e)}), 404

    except RequestTimeoutException as e:
        return jsonify({"error": "Request timeout", "message": str(e)}), 408

    except RequestCancelledException as e:
        return jsonify({"error": "Request cancelled", "message": str(e)}), 410

    except RequestFailedException as e:
        return jsonify({"error": "Request failed", "message": str(e)}), 500

    except Exception as e:
        logger.error(f"Error waiting for result: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/workers", methods=["GET"])
@queue_required
@async_endpoint
async def worker_status():
    """Get worker status information"""
    try:
        queue = get_request_queue()
        stats = await queue.get_queue_stats()

        worker_info = {
            "total_workers": queue.max_workers,
            "active_workers": stats["currently_processing"],
            "idle_workers": queue.max_workers - stats["currently_processing"],
            "utilization": stats["worker_utilization"],
            "average_processing_time": stats["avg_processing_time"],
        }

        return jsonify(worker_info)

    except Exception as e:
        logger.error(f"Error getting worker status: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/priorities", methods=["GET"])
def priority_info():
    """Get information about available priorities"""
    return jsonify(
        {
            "priorities": [
                {"name": p.name, "value": p.value, "description": get_priority_description(p)}
                for p in Priority
            ]
        }
    )


# Admin endpoints (require authentication in production)
@queue_bp.route("/admin/reset-stats", methods=["POST"])
@queue_required
def reset_stats():
    """Reset queue statistics (admin only)"""
    try:
        queue = get_request_queue()
        # Reset statistics
        with queue.stats_lock:
            queue.stats.update(
                {
                    "total_queued": 0,
                    "total_processed": 0,
                    "total_failed": 0,
                    "total_cancelled": 0,
                    "total_timeout": 0,
                    "avg_processing_time": 0.0,
                }
            )

        return jsonify({"message": "Statistics reset successfully"})

    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        return jsonify({"error": str(e)}), 500


@queue_bp.route("/admin/configure", methods=["POST"])
@queue_required
def configure_queue():
    """Configure queue parameters (admin only)"""
    try:
        data = request.get_json()
        queue = get_request_queue()

        # Update configurable parameters
        if "max_workers" in data:
            # This would require restarting workers - simplified for now
            logger.info(f"Max workers change requested: {data['max_workers']}")

        if "default_timeout" in data:
            queue.default_timeout = data["default_timeout"]

        if "max_queue_size" in data:
            queue.max_queue_size = data["max_queue_size"]

        return jsonify(
            {
                "message": "Configuration updated successfully",
                "config": {
                    "max_workers": queue.max_workers,
                    "default_timeout": queue.default_timeout,
                    "max_queue_size": queue.max_queue_size,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error configuring queue: {e}")
        return jsonify({"error": str(e)}), 500


# Helper functions
async def estimate_queue_position(priority: Priority) -> int:
    """Estimate position in queue based on priority"""
    try:
        queue = get_request_queue()
        position = 0

        # Count requests with higher or equal priority
        for p in Priority:
            if p.value >= priority.value:
                position += len(queue.queues[p])
            if p == priority:
                break

        return max(1, position)
    except Exception:
        return 1


def get_priority_description(priority: Priority) -> str:
    """Get human-readable priority description"""
    descriptions = {
        Priority.LOW: "Low priority - processed when resources available",
        Priority.NORMAL: "Normal priority - standard processing order",
        Priority.HIGH: "High priority - expedited processing",
        Priority.CRITICAL: "Critical priority - immediate processing",
    }
    return descriptions.get(priority, "Unknown priority")


def get_handler_by_name(handler_name: str):
    """Map handler names to actual functions"""
    # This would be customized based on your application's handlers
    handlers = {
        "chat_request": handle_chat_request,
        "file_upload": handle_file_upload,
        "model_inference": handle_model_inference,
        "data_export": handle_data_export,
        # Add more handlers as needed
    }
    return handlers.get(handler_name)


# Example handlers (to be customized for your application)
async def handle_chat_request(*args, **kwargs):
    """Example chat request handler"""
    # This would integrate with your existing chat processing
    await asyncio.sleep(1)  # Simulate processing
    return {"response": "Chat processed successfully"}


async def handle_file_upload(*args, **kwargs):
    """Example file upload handler"""
    # This would integrate with your file processing system
    await asyncio.sleep(2)  # Simulate processing
    return {"status": "File uploaded and processed"}


async def handle_model_inference(*args, **kwargs):
    """Example AI model inference handler"""
    # This would integrate with your AI providers
    await asyncio.sleep(3)  # Simulate inference
    return {"prediction": "Model inference completed"}


async def handle_data_export(*args, **kwargs):
    """Example data export handler"""
    # This would handle data export operations
    await asyncio.sleep(5)  # Simulate export
    return {"export_url": "/downloads/export_123.json"}


# Integration helper for existing Flask app
def init_queue_integration(app, **queue_config):
    """Initialize request queue integration with Flask app"""
    from .request_queue import init_request_queue

    # Initialize queue
    queue = init_request_queue(**queue_config)

    # Start queue when app starts
    @app.before_first_request
    def start_queue():
        asyncio.create_task(queue.start())

    # Stop queue when app stops
    @app.teardown_appcontext
    def stop_queue(error):
        if error:
            logger.error(f"App context teardown with error: {error}")
        # Note: In production, you'd want a more graceful shutdown

    # Register blueprint
    app.register_blueprint(queue_bp)

    logger.info("Request queue integration initialized")
    return queue


# Decorator for queuing requests automatically
def queue_request(priority=Priority.NORMAL, timeout=30.0, max_retries=3):
    """Decorator to automatically queue function calls"""

    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            queue = get_request_queue()
            request_id = await queue.queue_request(
                f, *args, priority=priority, timeout=timeout, max_retries=max_retries, **kwargs
            )
            return await queue.wait_for_result(request_id, timeout)

        return wrapper

    return decorator


# Context manager for batch requests
class QueueBatch:
    """Context manager for submitting multiple requests as a batch"""

    def __init__(self, priority=Priority.NORMAL, timeout=30.0):
        self.priority = priority
        self.timeout = timeout
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Wait for all requests to complete
            results = await asyncio.gather(
                *[self._wait_for_request(req_id) for req_id in self.requests],
                return_exceptions=True,
            )
            return results

    async def add_request(self, handler, *args, **kwargs):
        """Add request to batch"""
        queue = get_request_queue()
        request_id = await queue.queue_request(
            handler, *args, priority=self.priority, timeout=self.timeout, **kwargs
        )
        self.requests.append(request_id)
        return request_id

    async def _wait_for_request(self, request_id):
        """Wait for individual request result"""
        try:
            queue = get_request_queue()
            return await queue.wait_for_result(request_id, self.timeout)
        except Exception as e:
            return e
