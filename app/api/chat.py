"""Chat API endpoints with modern architecture."""

from flask import jsonify, request

from app.api import api_bp
from core.errors import ValidationError, handle_errors
from core.services import get_service


@api_bp.route("/chat", methods=["POST"])
@handle_errors
def chat():
    """Main chat endpoint using service layer."""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            raise ValidationError("No JSON data provided")

        # Get chat service from dependency injection container
        chat_service = get_service("chat_service")

        # Process chat request
        result = chat_service.process_chat_request(data)

        if result["success"]:
            return jsonify(
                {
                    "success": True,
                    "response": result["content"],
                    "model": result["model"],
                    "provider": result["provider"],
                    "usage": result.get("usage", {}),
                    """
                }
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
def get_providers():
    """Get available AI providers."""
    chat_service = get_service("chat_service")
    providers = chat_service.get_available_providers()

    return jsonify({"success": True, "providers": providers})


@api_bp.route("/models/<provider>", methods=["GET"])
@handle_errors
def get_models(provider: str):
    """Get models for specific provider."""
    chat_service = get_service("chat_service")
    models = chat_service.get_models_for_provider(provider)

    if models:
        return jsonify({"success": True, "models": models, "provider": provider})
    else:
        return (
            jsonify({"success": False, "error": f"Provider {provider} not available"}),
            404,
        )
