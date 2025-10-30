"""DOCX-specific chunking strategy."""

from __future__ import annotations

from .base import BaseChunker
from .config import ChunkingConfig
from .metadata import ChunkMetadata
from .models import DocumentChunk
from .types import ChunkType


class DocxChunker(BaseChunker):
    """Chunk DOCX content while respecting section metadata."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        if self.config.docx_respect_sections and "sections" in kwargs:
            sections: list[dict] = kwargs["sections"]
            return self._chunk_with_sections(content, document_id, sections)

        from .semantic import SemanticChunker  # Local import to avoid cycles

        return SemanticChunker(self.config).chunk_content(content, document_id)

    def _chunk_with_sections(self, content: str, document_id: str, sections: list[dict]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section in sections:
            section_content = section.get("content", "")
            section_title = section.get("title", "")
            if not section_content.strip():
                continue

            if len(section_content) > self.config.max_chunk_size:
                section_chunks = self._chunk_large_section(section_content, document_id, chunk_index, section_title)
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            else:
                chunks.append(self._create_docx_chunk(section_content, document_id, chunk_index, section_title))
                chunk_index += 1

        self._add_overlap_and_links(chunks)
        return chunks

    def _chunk_large_section(self, content: str, document_id: str, start_index: int, section_title: str) -> list[DocumentChunk]:
        paragraphs = content.split("\n\n")
        chunks: list[DocumentChunk] = []
        current_chunk = ""
        chunk_index = start_index

        for paragraph in paragraphs:
            candidate = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph
            if len(candidate) <= self.config.max_chunk_size:
                current_chunk = candidate
                continue

            if len(current_chunk) >= self.config.min_chunk_size:
                chunks.append(self._create_docx_chunk(current_chunk, document_id, chunk_index, section_title))
                chunk_index += 1
            current_chunk = paragraph

        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunks.append(self._create_docx_chunk(current_chunk, document_id, chunk_index, section_title))

        return chunks

    def _create_docx_chunk(self, content: str, document_id: str, chunk_index: int, section_title: str) -> DocumentChunk:
        chunk_id = self.generate_chunk_id(document_id, chunk_index, content)
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_type=ChunkType.PARAGRAPH,
            chunk_index=chunk_index,
            start_position=0,
            end_position=len(content),
            section_title=section_title,
            language=self.config.default_language,
        )

        chunk = DocumentChunk(content=content, metadata=metadata)
        chunk.calculate_metrics()
        metadata.entities = self.extract_entities(content)
        metadata.references = self.extract_references(content)
        return chunk


__all__ = ["DocxChunker"]
