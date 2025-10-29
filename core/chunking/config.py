"""Chunking configuration schema and validation."""

from __future__ import annotations

from dataclasses import dataclass

from .types import ChunkBoundary


@dataclass(slots=True)
class ChunkingConfig:
    """Tune chunk sizes, semantic boundaries, and analysis features."""

    target_chunk_size: int = 1000
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    overlap_size: int = 200
    overlap_percentage: float = 0.1
    boundary_strategy: ChunkBoundary = ChunkBoundary.SEMANTIC
    preserve_sentence_boundaries: bool = True
    preserve_paragraph_boundaries: bool = True
    preserve_headers: bool = True
    preserve_lists: bool = True
    preserve_tables: bool = True
    preserve_code_blocks: bool = True
    default_language: str = "en"
    encoding: str = "utf-8"
    min_confidence_score: float = 0.5
    max_empty_chunks: int = 5
    pdf_respect_pages: bool = True
    docx_respect_sections: bool = True
    csv_chunk_by_rows: bool = True
    csv_rows_per_chunk: int = 100
    enable_entity_extraction: bool = False
    enable_reference_tracking: bool = True
    enable_semantic_analysis: bool = False

    def validate(self) -> None:
        """Ensure configuration values fall within acceptable bounds."""

        if self.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be positive")
        if self.max_chunk_size <= self.min_chunk_size:
            raise ValueError("max_chunk_size must be greater than min_chunk_size")
        if not self.min_chunk_size <= self.target_chunk_size <= self.max_chunk_size:
            raise ValueError("target_chunk_size must be between min and max chunk sizes")
        if self.overlap_size >= self.target_chunk_size:
            raise ValueError("overlap_size cannot be larger than target chunk size")
        if self.csv_rows_per_chunk <= 0:
            raise ValueError("csv_rows_per_chunk must be positive")
        if not 0 <= self.overlap_percentage <= 0.5:
            raise ValueError("overlap_percentage must be between 0 and 0.5")


__all__ = ["ChunkingConfig"]
