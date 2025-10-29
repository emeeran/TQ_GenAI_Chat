"""Metadata structures for document chunking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .types import ChunkType


@dataclass
class ChunkMetadata:
    """Describes a chunk's identity, context, and quality metrics."""

    chunk_id: str
    document_id: str
    chunk_type: ChunkType
    chunk_index: int
    start_position: int
    end_position: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    heading_level: Optional[int] = None
    language: Optional[str] = None
    confidence_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    parent_section_id: Optional[str] = None
    word_count: int = 0
    character_count: int = 0
    sentence_count: int = 0
    references: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    readability_score: Optional[float] = None
    coherence_score: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable view of the metadata."""

        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "chunk_type": self.chunk_type.value,
            "chunk_index": self.chunk_index,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "heading_level": self.heading_level,
            "language": self.language,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "previous_chunk_id": self.previous_chunk_id,
            "next_chunk_id": self.next_chunk_id,
            "parent_section_id": self.parent_section_id,
            "word_count": self.word_count,
            "character_count": self.character_count,
            "sentence_count": self.sentence_count,
            "references": self.references,
            "cross_references": self.cross_references,
            "entities": self.entities,
            "readability_score": self.readability_score,
            "coherence_score": self.coherence_score,
        }


__all__ = ["ChunkMetadata"]
