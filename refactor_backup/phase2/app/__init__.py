"""
TQ GenAI Chat Application Factory

Modern Flask application with dependency injection and modular architecture.
"""

from pathlib import Path

from flask import Flask
from flask_cors import CORS

# Import when we create proper config
# from config.settings import config


def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory pattern implementation.

    Args:
        config_name: Configuration environment ('development', 'production', 'testing')

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent.parent / 'templates'),
        static_folder=str(Path(__file__).parent.parent / 'static')
    )

    # Basic configuration for now
    app.config.update({
        'JSON_SORT_KEYS': False,
        'MAX_CONTENT_LENGTH': 64 * 1024 * 1024,  # 64MB
    })

    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Import and register blueprints
    from app.api import api_bp
    from app.web import web_bp

    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_bp)

    return app
