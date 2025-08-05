"""Model API endpoints."""

from flask import jsonify

from app.api import api_bp
from core.errors import handle_errors
from core.services import get_service


@api_bp.route('/models', methods=['GET'])
@handle_errors
def get_all_models():
    """Get all available models grouped by provider."""
    provider_factory = get_service("provider_factory")
    all_models = provider_factory.get_all_models()

    return jsonify({
        "success": True,
        "models": all_models
    })


# Legacy route compatibility for frontend
@api_bp.route('/get_models/<provider>', methods=['GET'])
@handle_errors
def get_models_by_provider(provider):
    """Get available models for a specific provider (legacy route)"""
    try:
        provider_factory = get_service("provider_factory")

        # Get the provider instance
        provider_instance = provider_factory.get_provider(provider)
        if not provider_instance:
            return jsonify({
                'error': f'Provider {provider} not available',
                'models': []
            }), 404

        # Get models from the provider
        models = provider_instance.get_models()

        return jsonify({
            'provider': provider,
            'models': models,
            'default': models[0] if models else None
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to get models for {provider}: {str(e)}',
            'models': []
        }), 500
