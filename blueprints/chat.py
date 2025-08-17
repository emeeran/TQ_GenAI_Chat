
from flask import Blueprint, request, jsonify
from utils.auth import require_auth
from core.chat_handler import create_chat_handler
from services.file_manager import FileManager
from core.providers import provider_manager
from core.models import model_manager
from persona import PERSONAS


file_manager = FileManager()
chat_handler = create_chat_handler(file_manager)
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")

# Main chat endpoint
@chat_bp.route("/", methods=["POST"])
@require_auth
def chat():
    data = request.get_json()
    response = chat_handler.process_chat_request(data)
    return jsonify(response)

# Persona endpoints
@chat_bp.route("/get_personas", methods=["GET"])
def get_personas():
    personas_list = []
    for persona_id, persona_content in PERSONAS.items():
        display_name = persona_id.replace("_", " ").title()
        if isinstance(persona_content, dict):
            personas_list.append({
                "id": persona_id,
                "name": persona_content.get("name", display_name),
                "content": persona_content.get("system_prompt", "")
            })
        else:
            personas_list.append({
                "id": persona_id,
                "name": display_name,
                "content": persona_content
            })
    return jsonify({"personas": personas_list})

@chat_bp.route("/get_persona_content/<persona_key>", methods=["GET"])
def get_persona_content(persona_key):
    content = PERSONAS.get(persona_key, "")
    return jsonify({"content": content})

# Model management endpoints
@chat_bp.route("/get_models/<provider>", methods=["GET"])
def get_models(provider):
    try:
        if not provider_manager.is_provider_available(provider):
            return jsonify({"error": f"Provider {provider} not available"}), 404
        models = model_manager.get_models(provider)
        provider_instance = provider_manager.get_provider(provider)
        default_model = provider_instance.config.default_model if provider_instance else None
        return jsonify({"models": models, "default": default_model})
    except Exception as e:
        return jsonify({"error": "Failed to get models"}), 500

@chat_bp.route("/update_models/<provider>", methods=["POST"])
def update_models(provider):
    try:
        if not provider_manager.is_provider_available(provider):
            return jsonify({"error": f"Provider {provider} not available"}), 404
        from scripts.update_models_from_providers import fetch_provider_models
        new_models = fetch_provider_models(provider)
        if not new_models:
            return jsonify({"error": f"Failed to fetch models for {provider}"}), 500
        model_manager.update_models(provider, new_models)
        provider_instance = provider_manager.get_provider(provider)
        default_model = provider_instance.config.default_model if provider_instance else None
        return jsonify({
            "success": True,
            "message": f"Successfully updated {len(new_models)} models for {provider}",
            "models": new_models,
            "default": default_model,
            "count": len(new_models),
        })
    except Exception as e:
        return jsonify({"error": f"Failed to update models: {str(e)}"}), 500

@chat_bp.route("/set_default_model/<provider>", methods=["POST"])
def set_default_model(provider):
    try:
        if not provider_manager.is_provider_available(provider):
            return jsonify({"error": f"Provider {provider} not available"}), 404
        data = request.get_json()
        if not data or "model" not in data:
            return jsonify({"error": "Model is required"}), 400
        model = data["model"]
        if not model_manager.is_model_available(provider, model):
            return jsonify({"error": f"Model {model} not available for {provider}"}), 400
        model_manager.set_default_model(provider, model)
        return jsonify({
            "success": True,
            "message": f"Set {model} as default for {provider}",
            "provider": provider,
            "model": model,
        })
    except Exception as e:
        return jsonify({"error": f"Failed to set default model: {str(e)}"}), 500
