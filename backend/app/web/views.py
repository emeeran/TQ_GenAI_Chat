"""Web interface views."""

import asyncio

from flask import jsonify, render_template

from app.web import web_bp
from core.errors import handle_errors


@web_bp.route("/")
def index():
    """Main chat interface."""
    return render_template("index.html")


# Legacy API routes for frontend compatibility
@web_bp.route("/get_models/<provider>", methods=["GET"])
@handle_errors
def get_models_legacy(provider):
    """Get available models for a specific provider (legacy route) - now uses dynamic fetching"""
    try:
        from core.dynamic_model_fetcher import model_fetcher
        from core.model_utils import DEFAULT_MODELS

        # Check if provider is supported
        supported_providers = [
            "openai",
            "anthropic",
            "gemini",
            "deepseek",
            "mistral",
            "cohere",
            "openrouter",
            "huggingface",
            "xai",
            "groq",
            "alibaba",
        ]

        if provider.lower() not in supported_providers:
            return (
                jsonify({"error": f"Provider {provider} not available", "models": []}),
                404,
            )

        # Dynamically fetch models from the provider's API
        models, is_dynamic = run_async(model_fetcher.fetch_models_for_provider(provider))

        if not models:
            return (
                jsonify(
                    {
                        "error": f"No models available for {provider}",
                        "models": [],
                        "is_dynamic": is_dynamic,
                    }
                ),
                500,
            )

        # Get default model
        default_model = DEFAULT_MODELS.get(provider.lower())

        return jsonify(
            {
                "provider": provider,
                "models": models,
                "default": default_model,
                "is_dynamic": is_dynamic,
                "data_source": "Live API" if is_dynamic else "Fallback Configuration",
                "count": len(models),
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "error": f"Failed to get models for {provider}: {str(e)}",
                    "models": [],
                }
            ),
            500,
        )


@web_bp.route("/documents/list", methods=["GET"])
@handle_errors
def list_documents_legacy():
    """List all uploaded documents (legacy route)"""
    try:
        return jsonify({"success": True, "documents": [], "total": 0})

    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Failed to list documents: {str(e)}"}),
            500,
        )


@web_bp.route("/get_personas", methods=["GET"])
@handle_errors
def get_personas_legacy():
    """Get all available personas (legacy route)"""
    try:
        personas = [
            {
                "id": "default",
                "name": "Default Assistant",
                "description": "A helpful AI assistant",
                "system_prompt": "You are a helpful AI assistant.",
            },
            {
                "id": "creative",
                "name": "Creative Writer",
                "description": "Focused on creative writing and storytelling",
                "system_prompt": "You are a creative writer skilled in storytelling, poetry, and creative content.",
            },
            {
                "id": "technical",
                "name": "Technical Expert",
                "description": "Specialized in technical discussions and coding",
                "system_prompt": "You are a technical expert specializing in programming, software development, and technical problem-solving.",
            },
        ]

        return jsonify({"success": True, "personas": personas, "default": "default"})

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to get personas: {str(e)}",
                    "personas": [],
                }
            ),
            500,
        )


def run_async(coro):
    """Helper to run async code in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@web_bp.route("/update_models/<provider>", methods=["POST"])
@handle_errors
def update_models_legacy(provider):
    """Update/refresh models for a specific provider dynamically from API (legacy route)"""
    try:
        from core.dynamic_model_fetcher import model_fetcher
        from core.model_utils import DEFAULT_MODELS

        # Check if provider is supported
        supported_providers = [
            "openai",
            "anthropic",
            "gemini",
            "deepseek",
            "mistral",
            "cohere",
            "openrouter",
            "huggingface",
            "xai",
            "groq",
            "alibaba",
            "moonshot",
        ]

        if provider.lower() not in supported_providers:
            return (
                jsonify({"success": False, "error": f"Provider {provider} not supported"}),
                404,
            )

        # Dynamically fetch models from the provider's API
        models, is_dynamic = run_async(model_fetcher.fetch_models_for_provider(provider))

        if not models:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"No models available for {provider} or API request failed",
                        "is_dynamic": is_dynamic,
                    }
                ),
                500,
            )

        # Categorize models to provide better information to frontend
        preview_models = [model for model in models if "preview" in model.lower()]
        stable_models = [model for model in models if "preview" not in model.lower()]

        # Get default model
        default_model = DEFAULT_MODELS.get(provider.lower())

        # Return comprehensive model information
        return jsonify(
            {
                "success": True,
                "message": f"Models {'dynamically fetched' if is_dynamic else 'loaded from fallback'} for {provider} (including preview models)",
                "models": models,  # ALL models including preview
                "count": len(models),
                "preview_models": preview_models,
                "stable_models": stable_models,
                "preview_count": len(preview_models),
                "stable_count": len(stable_models),
                "provider": provider,
                "default": default_model,
                "has_preview_models": len(preview_models) > 0,
                "is_dynamic": is_dynamic,
                "data_source": "Live API" if is_dynamic else "Fallback Configuration",
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to update models for {provider}: {str(e)}",
                }
            ),
            500,
        )
