"""
TQ GenAI Chat Application Factory

Modern Flask application with dependency injection and modular architecture.
"""

import asyncio
from pathlib import Path

from flask import Flask
from flask_cors import CORS

# Import new architectural components
from core.background_tasks import task_manager
from core.errors import setup_logging
from core.performance import perf_monitor
from core.services import get_service


def create_app(config_name: str = "development") -> Flask:
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
        template_folder=str(Path(__file__).parent.parent / "templates"),
        static_folder=str(Path(__file__).parent.parent / "static"),
    )

    # Basic configuration for now
    app.config.update(
        {
            "JSON_SORT_KEYS": False,
            "MAX_CONTENT_LENGTH": 64 * 1024 * 1024,  # 64MB
        }
    )

    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Setup logging
    setup_logging(app)

    # Start performance monitoring
    perf_monitor.start_monitoring()

    # Start background services in a separate thread
    def start_background_services():
        """Start background services in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(task_manager.start())
        except Exception as e:
            app.logger.error(f"Error starting background services: {e}")
        finally:
            pass  # Keep loop for background tasks

    import threading

    bg_thread = threading.Thread(target=start_background_services, daemon=True)
    bg_thread.start()

    # Initialize services (dependency injection)
    with app.app_context():
        # Pre-initialize core services
        get_service("provider_factory")
        get_service("chat_service")
        app.logger.info("Core services initialized")

    # Import and register blueprints
    from app.api import api_bp
    from app.web import web_bp

    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(web_bp)

    return app
