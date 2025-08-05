"""
API Blueprint - REST API endpoints.
"""

from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import routes to register them
from app.api import chat, documents, files, models, personas  # noqa: F401
