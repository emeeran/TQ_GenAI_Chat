"""Persona management API endpoints"""

from flask import jsonify

from app.api import api_bp
from core.errors import handle_errors


@api_bp.route("/get_personas", methods=["GET"])
@handle_errors
def get_personas():
    """Get all available personas"""
    try:
        # Default personas - this could be moved to a service layer
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
            {
                "id": "analyst",
                "name": "Data Analyst",
                "description": "Expert in data analysis and insights",
                "system_prompt": "You are a data analyst expert in interpreting data, creating insights, and explaining complex analytical concepts.",
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


@api_bp.route("/personas", methods=["GET"])
@handle_errors
def list_personas():
    """Alternative endpoint for listing personas"""
    return get_personas()
