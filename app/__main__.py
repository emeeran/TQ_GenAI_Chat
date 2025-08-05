"""
Main entry point for the application.
Run with: python -m app
"""

from app import create_app

if __name__ == "__main__":
    import os

    app = create_app()
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(debug=debug_mode, host=host, port=port)
