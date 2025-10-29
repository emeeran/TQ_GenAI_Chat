"""Abstract base class and shared helpers for chunking strategies."""

from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .config import ChunkingConfig
from .models import DocumentChunk

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """Provide core utilities and contracts for concrete chunkers."""

    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.config.validate()

    @abstractmethod
    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Split raw content into ordered chunks."""

    def generate_chunk_id(self, document_id: str, chunk_index: int, content: str) -> str:
        """Create a deterministic chunk identifier."""

        content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:8]
        return f"{document_id}_chunk_{chunk_index:04d}_{content_hash}"

    def calculate_overlap(self, segments: Iterable[str]) -> list[tuple[str, str | None]]:
        """Pair each segment with overlap text from the previous segment."""

        segment_list = list(segments)
        if len(segment_list) <= 1:
            return [(segment, None) for segment in segment_list]
        result: list[tuple[str, str | None]] = []
        for index, segment in enumerate(segment_list):
            overlap = None
            if index > 0:
                previous = segment_list[index - 1]
                overlap_size = min(self.config.overlap_size, len(previous) // 4)
                if overlap_size > 0:
                    overlap = previous[-overlap_size:].strip()
            result.append((segment, overlap))
        return result

    def extract_entities(self, content: str) -> list[dict[str, Any]]:
        """Perform lightweight entity extraction when enabled."""

        if not self.config.enable_entity_extraction:
            return []

        entities: list[dict[str, Any]] = []

        date_pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
        url_pattern = r"https?://[^\s<>\"{}|\\^`\[\]]+"
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

        for pattern, entity_type in ((date_pattern, "DATE"), (url_pattern, "URL"), (email_pattern, "EMAIL")):
            for match in re.finditer(pattern, content):
                entities.append(
                    {
                        "type": entity_type,
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        return entities

    def extract_references(self, content: str) -> list[str]:
        """Identify cross-references and citations within the content."""

        if not self.config.enable_reference_tracking:
            return []

        citation_patterns = [
            r"\[\d+\]",
            r"\([A-Za-z]+,?\s*\d{4}\)",
            r"\b(?:see|refer to|cf\.)\s+[A-Za-z\s]+\d+",
        ]

        references: set[str] = set()
        for pattern in citation_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                references.add(match.group().strip())

        return sorted(references)

    def _add_overlap_and_links(self, chunks: list[DocumentChunk]) -> None:
        """Populate overlap content and previous/next relationships."""

        if len(chunks) <= 1:
            return

        for index, chunk in enumerate(chunks):
            if index > 0:
                previous = chunks[index - 1]
                overlap_size = min(self.config.overlap_size, len(previous.content) // 4)
                if overlap_size > 0:
                    chunk.overlap_content = previous.content[-overlap_size:].strip()
                chunk.metadata.previous_chunk_id = previous.chunk_id

            if index < len(chunks) - 1:
                chunk.metadata.next_chunk_id = chunks[index + 1].chunk_id


__all__ = ["BaseChunker"]
