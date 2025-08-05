"""
Web Blueprint - Web interface routes.
"""

from flask import Blueprint

web_bp = Blueprint("web", __name__)

# Import routes to register them
from app.web import views  # noqa: F401
