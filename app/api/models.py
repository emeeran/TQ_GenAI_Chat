"""Model API endpoints."""

import asyncio

from flask import jsonify

from app.api import api_bp
from core.errors import handle_errors


def run_async(coro):
    """Helper to run async code in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@api_bp.route("/models", methods=["GET"])
@handle_errors
def get_all_models():
    """Get all available models grouped by provider."""
    from core.model_utils import ALL_MODELS, DEFAULT_MODELS

    # Convert the model configuration to the expected format
    models_response = {}
    for provider, provider_models in ALL_MODELS.items():
        models_response[provider] = {
            "models": list(provider_models.keys()) if provider_models else [],
            "default": DEFAULT_MODELS.get(provider),
        }

    return jsonify({"success": True, "models": models_response})


@api_bp.route("/models/<provider>", methods=["GET"])
@handle_errors
def get_models_for_provider(provider):
    """Get available models for a specific provider - REST API style route"""
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


# Legacy route compatibility for frontend
@api_bp.route("/get_models/<provider>", methods=["GET"])
@handle_errors
def get_models_by_provider(provider):
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
            "moonshot",
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


@api_bp.route("/update_models/<provider>", methods=["POST"])
@handle_errors
def update_models_by_provider(provider):
    """Update/refresh models for a specific provider dynamically from API"""
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


@api_bp.route("/update_all_models", methods=["POST"])
@handle_errors
def update_all_models():
    """Update/refresh models for all providers dynamically from their APIs"""
    try:
        from core.dynamic_model_fetcher import model_fetcher

        # Fetch models for all providers
        results = run_async(model_fetcher.fetch_all_models())

        # Count totals
        total_models = sum(result["count"] for result in results.values())
        total_preview = sum(result["preview_count"] for result in results.values())
        total_stable = sum(result["stable_count"] for result in results.values())
        providers_with_errors = [p for p, r in results.items() if "error" in r]

        return jsonify(
            {
                "success": True,
                "message": f"Updated models for all {len(results)} providers",
                "providers": results,
                "summary": {
                    "total_providers": len(results),
                    "total_models": total_models,
                    "total_preview_models": total_preview,
                    "total_stable_models": total_stable,
                    "providers_with_errors": providers_with_errors,
                    "error_count": len(providers_with_errors),
                },
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to update all models: {str(e)}",
                }
            ),
            500,
        )


@api_bp.route("/test_dynamic_fetch/<provider>", methods=["GET"])
@handle_errors
def test_dynamic_fetch(provider):
    """Test endpoint to demonstrate dynamic vs static model fetching"""
    try:
        from core.dynamic_model_fetcher import model_fetcher
        from core.model_utils import ALL_MODELS

        # Get static models
        static_models = list(ALL_MODELS.get(provider, {}).keys())

        # Try dynamic fetch
        dynamic_models, is_dynamic = run_async(model_fetcher.fetch_models_for_provider(provider))

        # Check API key status
        api_key_status = bool(model_fetcher.api_keys.get(provider.lower()))

        return jsonify(
            {
                "success": True,
                "provider": provider,
                "api_key_configured": api_key_status,
                "static_models": {
                    "models": static_models,
                    "count": len(static_models),
                    "source": "ai_models.py configuration",
                },
                "dynamic_models": {
                    "models": dynamic_models,
                    "count": len(dynamic_models),
                    "source": "Live API" if is_dynamic else "Fallback configuration",
                    "is_dynamic": is_dynamic,
                },
                "comparison": {
                    "models_match": set(static_models) == set(dynamic_models),
                    "static_only": list(set(static_models) - set(dynamic_models)),
                    "dynamic_only": list(set(dynamic_models) - set(static_models)),
                },
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to test dynamic fetch for {provider}: {str(e)}",
                }
            ),
            500,
        )
