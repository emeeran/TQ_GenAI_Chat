"""Enumerations for chunking domain."""

from __future__ import annotations

from enum import Enum


class ChunkType(Enum):
    """Enumeration of supported chunk categories."""

    TEXT = "text"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"
    METADATA = "metadata"
    REFERENCE = "reference"


class ChunkBoundary(Enum):
    """Strategies that govern chunk boundary detection."""

    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    PAGE = "page"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"


__all__ = ["ChunkType", "ChunkBoundary"]
