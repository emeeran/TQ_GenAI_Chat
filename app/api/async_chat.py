"""Async API endpoints with performance optimizations"""

import asyncio

from flask import jsonify, request

from app.api import api_bp
from core.background_tasks import task_manager
from core.errors import ValidationError, handle_errors
from core.performance import monitor_performance, perf_monitor
from core.services.async_chat_service import AsyncChatService

# Global async service instance
chat_service = AsyncChatService()


@api_bp.route("/chat", methods=["POST"])
@handle_errors
@monitor_performance("api_chat")
def chat():
    """Main chat endpoint using async service layer."""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            raise ValidationError("No JSON data provided")

        # Run async service in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(chat_service.process_chat_request(data))
        finally:
            loop.close()

        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "response": result["content"],
                    "model": result["model"],
                    "provider": result["provider"],
                    "usage": result.get("usage", {}),
                    "response_time": result.get("response_time", 0),
                    "cached": result.get("cached", False),
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result["error"],
                        "provider": result.get("provider", "unknown"),
                    }
                ),
                400,
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/providers", methods=["GET"])
@handle_errors
@monitor_performance("api_providers")
def get_providers():
    """Get available AI providers."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        providers = loop.run_until_complete(chat_service.get_available_providers())
    finally:
        loop.close()

    return jsonify({"success": True, "providers": providers})


@api_bp.route("/models/<provider>", methods=["GET"])
@handle_errors
@monitor_performance("api_models")
def get_models(provider: str):
    """Get models for specific provider."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        models = loop.run_until_complete(chat_service.get_models_for_provider(provider))
    finally:
        loop.close()

    if models:
        return jsonify({"success": True, "models": models, "provider": provider})
    else:
        return (
            jsonify({"success": False, "error": f"Provider {provider} not available"}),
            404,
        )


@api_bp.route("/performance/metrics", methods=["GET"])
@handle_errors
def get_performance_metrics():
    """Get performance metrics."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        metrics = loop.run_until_complete(chat_service.get_performance_metrics())
        provider_stats = loop.run_until_complete(chat_service.get_provider_stats())
    finally:
        loop.close()

    return jsonify(
        {
            "success": True,
            "metrics": metrics,
            "provider_stats": provider_stats,
            "system_health": perf_monitor.get_system_health(),
        }
    )


@api_bp.route("/performance/tasks", methods=["GET"])
@handle_errors
def get_background_tasks():
    """Get background task status."""
    tasks = task_manager.get_all_tasks()

    return jsonify(
        {
            "success": True,
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "status": task.status.value,
                    "progress": task.progress,
                    "created_at": (task.created_at.isoformat() if task.created_at else None),
                    "completed_at": (task.completed_at.isoformat() if task.completed_at else None),
                    "error": task.error,
                }
                for task in tasks
            ],
        }
    )


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint with system metrics."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": perf_monitor.get_system_health()["timestamp"],
            "system": perf_monitor.get_system_health(),
            "version": "3.0.0-optimized",
        }
    )
