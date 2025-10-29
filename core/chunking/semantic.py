"""Semantic chunking strategy that preserves document structure."""

from __future__ import annotations

import logging
import re
from typing import Any

from .base import BaseChunker
from .config import ChunkingConfig
from .metadata import ChunkMetadata
from .models import DocumentChunk
from .types import ChunkType

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """Chunk text using semantic boundaries such as sections and paragraphs."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Chunk payload into semantically meaningful blocks."""

        sections = self._split_into_sections(content)
        all_chunks: list[DocumentChunk] = []
        for section_index, section in enumerate(sections):
            section_chunks = self._chunk_section(section, document_id, section_index)
            all_chunks.extend(section_chunks)

        self._add_overlap_and_links(all_chunks)
        return all_chunks

    def _split_into_sections(self, content: str) -> list[dict[str, Any]]:
        """Split documents at Markdown-style headings to retain hierarchy."""

        if not content.strip():
            return [{"title": None, "level": 0, "content": "", "start_line": 0}]

        sections: list[dict[str, Any]] = []
        header_pattern = r"^(#{1,6})\s+(.+)$"
        lines = content.split("\n")
        current_section = {"title": None, "level": 0, "content": [], "start_line": 0}

        for line_index, line in enumerate(lines):
            header_match = re.match(header_pattern, line, re.MULTILINE)
            if header_match:
                if current_section["content"]:
                    current_section["content"] = "\n".join(current_section["content"])
                    sections.append(current_section)

                header_level = len(header_match.group(1))
                header_title = header_match.group(2).strip()
                current_section = {
                    "title": header_title,
                    "level": header_level,
                    "content": [],
                    "start_line": line_index,
                }
            else:
                current_section["content"].append(line)

        if current_section["content"]:
            current_section["content"] = "\n".join(current_section["content"])
            sections.append(current_section)

        if not sections:
            sections = [{"title": None, "level": 0, "content": content, "start_line": 0}]

        return sections

    def _chunk_section(self, section: dict[str, Any], document_id: str, section_index: int) -> list[DocumentChunk]:
        """Convert a section to chunks while respecting size constraints."""

        content = section["content"]
        if not content.strip():
            return []

        paragraphs = self._split_paragraphs(content)
        chunks: list[DocumentChunk] = []
        current_chunk = ""
        chunk_index = len(chunks)

        for paragraph in paragraphs:
            candidate = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph
            if len(candidate) <= self.config.max_chunk_size:
                current_chunk = candidate
                continue

            if len(current_chunk) >= self.config.min_chunk_size:
                chunk = self._create_chunk(current_chunk, document_id, chunk_index, section)
                chunks.append(chunk)
                chunk_index += 1
            current_chunk = paragraph

        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunk = self._create_chunk(current_chunk, document_id, chunk_index, section)
            chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, content: str) -> list[str]:
        """Split content into paragraphs, trimming short fragments."""

        paragraphs = re.split(r"\n\s*\n", content)
        return [paragraph.strip() for paragraph in paragraphs if paragraph.strip() and len(paragraph) > 10]

    def _create_chunk(self, content: str, document_id: str, chunk_index: int, section: dict[str, Any]) -> DocumentChunk:
        """Instantiate a chunk with calculated metadata."""

        chunk_id = self.generate_chunk_id(document_id, chunk_index, content)
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_type=self._determine_chunk_type(content),
            chunk_index=chunk_index,
            start_position=0,
            end_position=len(content),
            section_title=section.get("title"),
            heading_level=section.get("level"),
            language=self.config.default_language,
        )

        chunk = DocumentChunk(content=content, metadata=metadata)
        chunk.calculate_metrics()
        metadata.entities = self.extract_entities(content)
        metadata.references = self.extract_references(content)
        return chunk

    def _determine_chunk_type(self, content: str) -> ChunkType:
        """Infer chunk type from structural cues in the text."""

        normalized = content.lower().strip()
        if re.match(r"^#{1,6}\s+", content):
            return ChunkType.HEADING
        if "|" in content and "\n" in content and content.count("|") > 2:
            return ChunkType.TABLE
        if content.startswith(("- ", "* ", "1. ", "2. ")):
            return ChunkType.LIST
        if re.search(r"```|`\w+`|def |class |function |var |let |const ", content):
            return ChunkType.CODE
        if re.search(r"\[.*?\]|\(.*?\)|see |refer to |citation", normalized):
            return ChunkType.REFERENCE
        return ChunkType.PARAGRAPH


__all__ = ["SemanticChunker"]
