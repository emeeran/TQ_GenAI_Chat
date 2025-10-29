"""Domain models that pair chunk content with metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from .metadata import ChunkMetadata


@dataclass(slots=True)
class DocumentChunk:
    """Represents a chunk of text plus optional overlap for context."""

    content: str
    metadata: ChunkMetadata
    overlap_content: Optional[str] = None

    @property
    def chunk_id(self) -> str:
        """Expose the chunk identifier from the metadata."""

        return self.metadata.chunk_id

    @property
    def effective_content(self) -> str:
        """Return content augmented with overlap, when present."""

        if self.overlap_content:
            return f"{self.overlap_content}\n\n{self.content}"
        return self.content

    def calculate_metrics(self) -> None:
        """Populate derived metadata metrics for analytics."""

        self.metadata.character_count = len(self.content)
        self.metadata.word_count = len(self.content.split())
        self.metadata.sentence_count = len(re.findall(r"[.!?]+", self.content))

    def to_dict(self) -> dict[str, Any]:
        """Provide a serializable representation of the chunk."""

        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "overlap_content": self.overlap_content,
        }


__all__ = ["DocumentChunk"]
