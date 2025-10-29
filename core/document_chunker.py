"""Compatibility wrapper for the modular chunking subsystem."""

from __future__ import annotations

import logging

from .chunking import (
    ChunkBoundary,
    ChunkMetadata,
    ChunkType,
    ChunkingConfig,
    ChunkingIntegration,
    DocumentChunk,
    DocumentChunkerManager,
    chunk_document_content,
    chunking_integration,
    default_chunker_manager,
    get_optimal_chunking_config,
)

logger = logging.getLogger(__name__)
logger.debug("core.document_chunker imported; using modular chunking package")

__all__ = [
    "ChunkBoundary",
    "ChunkType",
    "ChunkMetadata",
    "DocumentChunk",
    "ChunkingConfig",
    "DocumentChunkerManager",
    "ChunkingIntegration",
    "chunk_document_content",
    "get_optimal_chunking_config",
    "default_chunker_manager",
    "chunking_integration",
]
