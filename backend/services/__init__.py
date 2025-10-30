"""
Services module for TQ GenAI Chat application.
Contains service classes for external API integrations and file management.
"""

__version__ = "2.0.0"
__author__ = "TQ GenAI Chat Team"

from .file_manager import FileManager
from .xai_service import XAIService

__all__ = ["FileManager", "XAIService"]
