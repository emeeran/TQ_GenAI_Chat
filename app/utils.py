"""
Utility functions for the FastAPI application.
"""

import re


def secure_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe for filesystem use.

    This is a simplified version of werkzeug's secure_filename.
    It removes any characters that might be problematic in filenames.

    Args:
        filename: The original filename

    Returns:
        A sanitized filename safe for use in filesystem operations
    """
    # Remove any non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')

    # Replace spaces and other separators with underscores
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[-\s]+', '_', filename)

    # Remove leading/trailing dots and underscores
    filename = filename.strip('._')

    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'

    return filename
