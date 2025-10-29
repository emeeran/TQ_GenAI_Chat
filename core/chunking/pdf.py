"""PDF-specific chunking strategy."""

from __future__ import annotations

from .base import BaseChunker
from .config import ChunkingConfig
from .metadata import ChunkMetadata
from .models import DocumentChunk
from .types import ChunkType


class PDFChunker(BaseChunker):
    """Chunk PDF text while respecting page breaks when available."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        if self.config.pdf_respect_pages and "page_breaks" in kwargs:
            page_breaks: list[int] = kwargs["page_breaks"]
            return self._chunk_with_pages(content, document_id, page_breaks)

        from .semantic import SemanticChunker  # Local import to avoid cycles

        return SemanticChunker(self.config).chunk_content(content, document_id)

    def _chunk_with_pages(self, content: str, document_id: str, page_breaks: list[int]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        lines = content.split("\n")
        current_page = 1
        current_chunk = ""
        chunk_index = 0

        for line_index, line in enumerate(lines):
            if line_index in page_breaks:
                if current_chunk.strip() and len(current_chunk) >= self.config.min_chunk_size:
                    chunks.append(
                        self._create_pdf_chunk(current_chunk.strip(), document_id, chunk_index, current_page)
                    )
                    chunk_index += 1
                current_page += 1
                current_chunk = ""

            current_chunk += f"{line}\n"

            if len(current_chunk) >= self.config.max_chunk_size:
                chunks.append(
                    self._create_pdf_chunk(current_chunk.strip(), document_id, chunk_index, current_page)
                )
                chunk_index += 1
                current_chunk = ""

        if current_chunk.strip() and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(self._create_pdf_chunk(current_chunk.strip(), document_id, chunk_index, current_page))

        self._add_overlap_and_links(chunks)
        return chunks

    def _create_pdf_chunk(
        self,
        content: str,
        document_id: str,
        chunk_index: int,
        page_number: int,
    ) -> DocumentChunk:
        chunk_id = self.generate_chunk_id(document_id, chunk_index, content)
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_type=ChunkType.TEXT,
            chunk_index=chunk_index,
            start_position=0,
            end_position=len(content),
            page_number=page_number,
            language=self.config.default_language,
        )

        chunk = DocumentChunk(content=content, metadata=metadata)
        chunk.calculate_metrics()
        metadata.entities = self.extract_entities(content)
        metadata.references = self.extract_references(content)
        return chunk


__all__ = ["PDFChunker"]
