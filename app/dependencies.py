"""
Dependency injection for FastAPI application.
"""

from services.file_manager import FileManager

# Global instances
_file_manager: FileManager | None = None


async def get_file_manager() -> FileManager:
    """Get or create file manager instance."""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager
