"""Integration helpers tying chunking into the broader file pipeline."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path

from .config import ChunkingConfig
from .manager import DocumentChunkerManager
from .models import DocumentChunk

logger = logging.getLogger(__name__)


def _generate_document_id(filename: str) -> str:
    base_name = Path(filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_suffix = hashlib.md5(f"{base_name}_{timestamp}".encode(), usedforsecurity=False).hexdigest()[:8]
    return f"doc_{base_name}_{hash_suffix}"


class ChunkingIntegration:
    """Bridge between file ingestion and the chunking manager."""

    def __init__(self, chunker_manager: DocumentChunkerManager | None = None):
        self.chunker_manager = chunker_manager or DocumentChunkerManager()

    def process_file_with_chunking(
        self,
        content: str,
        filename: str,
        document_id: str | None = None,
    ) -> tuple[str, list[DocumentChunk]]:
        document_id = document_id or _generate_document_id(filename)
        file_ext = Path(filename).suffix.lower().lstrip(".")
        chunks = self.chunker_manager.chunk_document(content, document_id, file_ext)
        combined_content = "\n\n".join(chunk.content for chunk in chunks)
        return combined_content, chunks

    def get_chunk_context_for_query(
        self,
        query: str,
        max_chunks: int = 5,
        context_size: int = 1,
    ) -> list[str]:
        search_results = self.chunker_manager.search_chunks(query)
        contexts: list[str] = []
        for chunk, _score in search_results[:max_chunks]:
            context_chunks = self.chunker_manager.get_chunk_context(chunk.chunk_id, context_size)
            contexts.append("\n\n".join(context_chunk.effective_content for context_chunk in context_chunks))
        return contexts


def chunk_document_content(content: str, filename: str, config: ChunkingConfig | None = None) -> list[DocumentChunk]:
    manager = DocumentChunkerManager(config) if config else default_chunker_manager
    document_id = _generate_document_id(filename)
    file_ext = Path(filename).suffix.lower().lstrip(".")
    return manager.chunk_document(content, document_id, file_ext)


def get_optimal_chunking_config(file_type: str, content_length: int) -> ChunkingConfig:
    config = ChunkingConfig()
    file_type_lower = file_type.lower()

    if file_type_lower == "pdf":
        config.pdf_respect_pages = True
        config.target_chunk_size = 1500
        config.overlap_size = 300
    elif file_type_lower in {"docx", "doc"}:
        config.docx_respect_sections = True
        config.preserve_headers = True
        config.target_chunk_size = 1200
    elif file_type_lower == "csv":
        config.csv_chunk_by_rows = True
        config.csv_rows_per_chunk = 50 if content_length > 100000 else 100

    if content_length > 50000:
        config.target_chunk_size = min(2000, int(config.target_chunk_size * 1.5))
        config.overlap_size = min(400, int(config.overlap_size * 1.5))
    elif content_length < 5000:
        config.target_chunk_size = max(500, int(config.target_chunk_size * 0.7))
        config.overlap_size = max(100, int(config.overlap_size * 0.7))

    return config


default_chunker_manager = DocumentChunkerManager()
chunking_integration = ChunkingIntegration(default_chunker_manager)

logger.info("[Document Chunker] Chunking integration initialized")


__all__ = [
    "ChunkingIntegration",
    "chunk_document_content",
    "get_optimal_chunking_config",
    "default_chunker_manager",
    "chunking_integration",
]
