"""
Core module for TQ GenAI Chat application.
Contains optimized and consolidated functionality for file processing,
API management, and utility functions.
"""

__version__ = "2.0.0"
__author__ = "TQ GenAI Chat Team"

from .api_services import APIServices
from .document_store import DocumentStore
from .file_processor import ProcessingStatus, ProcessingError
from .model_utils import (
    get_models, get_default_model, get_fallback_model,
    get_model_info, get_available_providers, get_api_endpoint
)

__all__ = [
    "APIServices",
    "DocumentStore", 
    "ProcessingStatus",
    "ProcessingError",
    "get_models",
    "get_default_model",
    "get_fallback_model",
    "get_model_info", 
    "get_available_providers",
    "get_api_endpoint"
]
