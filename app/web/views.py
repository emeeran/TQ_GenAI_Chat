"""Web interface views."""

from flask import render_template, jsonify
from app.web import web_bp
from core.services import get_service
from core.errors import handle_errors


@web_bp.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html')


# Legacy API routes for frontend compatibility
@web_bp.route('/get_models/<provider>', methods=['GET'])
@handle_errors
def get_models_legacy(provider):
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


@web_bp.route('/documents/list', methods=['GET'])
@handle_errors
def list_documents_legacy():
    """List all uploaded documents (legacy route)"""
    try:
        return jsonify({
            'success': True,
            'documents': [],
            'total': 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to list documents: {str(e)}'
        }), 500


@web_bp.route('/get_personas', methods=['GET'])
@handle_errors
def get_personas_legacy():
    """Get all available personas (legacy route)"""
    try:
        personas = [
            {
                'id': 'default',
                'name': 'Default Assistant',
                'description': 'A helpful AI assistant',
                'system_prompt': 'You are a helpful AI assistant.'
            },
            {
                'id': 'creative',
                'name': 'Creative Writer',
                'description': 'Focused on creative writing and storytelling',
                'system_prompt': 'You are a creative writer skilled in storytelling, poetry, and creative content.'
            },
            {
                'id': 'technical',
                'name': 'Technical Expert',
                'description': 'Specialized in technical discussions and coding',
                'system_prompt': 'You are a technical expert specializing in programming, software development, and technical problem-solving.'
            }
        ]
        
        return jsonify({
            'success': True,
            'personas': personas,
            'default': 'default'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get personas: {str(e)}',
            'personas': []
        }), 500
