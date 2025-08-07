"""
TQ GenAI Chat - Intelligent Document Chunking Strategy

Task 2.2.2: Document Chunking Strategy Implementation
- Semantic chunking for better context preservation
- Configurable chunk size and overlap
- Format-specific chunking strategies (PDF, DOCX, etc.)
- Chunk metadata and indexing
- Cross-chunk reference handling

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """Enumeration of different chunk types."""

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
    """Enumeration of chunk boundary strategies."""

    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    PAGE = "page"
    SEMANTIC = "semantic"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class ChunkMetadata:
    """Metadata for document chunks."""

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

    # Context preservation
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    parent_section_id: Optional[str] = None

    # Content characteristics
    word_count: int = 0
    character_count: int = 0
    sentence_count: int = 0

    # References and relationships
    references: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)

    # Quality metrics
    readability_score: Optional[float] = None
    coherence_score: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
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


@dataclass
class DocumentChunk:
    """A document chunk with content and metadata."""

    content: str
    metadata: ChunkMetadata
    overlap_content: Optional[str] = None  # Content shared with adjacent chunks

    @property
    def chunk_id(self) -> str:
        """Get chunk ID from metadata."""
        return self.metadata.chunk_id

    @property
    def effective_content(self) -> str:
        """Get content including overlap for context."""
        if self.overlap_content:
            return f"{self.overlap_content}\n\n{self.content}"
        return self.content

    def calculate_metrics(self) -> None:
        """Calculate and update content metrics."""
        self.metadata.character_count = len(self.content)
        self.metadata.word_count = len(self.content.split())
        self.metadata.sentence_count = len(re.findall(r"[.!?]+", self.content))

    def to_dict(self) -> dict[str, Any]:
        """Convert chunk to dictionary for serialization."""
        return {
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "overlap_content": self.overlap_content,
        }


@dataclass
class ChunkingConfig:
    """Configuration for document chunking."""

    # Size configuration
    target_chunk_size: int = 1000  # Target characters per chunk
    min_chunk_size: int = 100  # Minimum viable chunk size
    max_chunk_size: int = 2000  # Maximum chunk size
    overlap_size: int = 200  # Overlap between chunks
    overlap_percentage: float = 0.1  # Alternative: percentage-based overlap

    # Boundary strategy
    boundary_strategy: ChunkBoundary = ChunkBoundary.SEMANTIC
    preserve_sentence_boundaries: bool = True
    preserve_paragraph_boundaries: bool = True

    # Content preservation
    preserve_headers: bool = True
    preserve_lists: bool = True
    preserve_tables: bool = True
    preserve_code_blocks: bool = True

    # Language and encoding
    default_language: str = "en"
    encoding: str = "utf-8"

    # Quality thresholds
    min_confidence_score: float = 0.5
    max_empty_chunks: int = 5  # Maximum consecutive empty chunks allowed

    # Format-specific settings
    pdf_respect_pages: bool = True
    docx_respect_sections: bool = True
    csv_chunk_by_rows: bool = True
    csv_rows_per_chunk: int = 100

    # Advanced features
    enable_entity_extraction: bool = False
    enable_reference_tracking: bool = True
    enable_semantic_analysis: bool = False

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be positive")
        if self.max_chunk_size <= self.min_chunk_size:
            raise ValueError("max_chunk_size must be greater than min_chunk_size")
        if (
            self.target_chunk_size < self.min_chunk_size
            or self.target_chunk_size > self.max_chunk_size
        ):
            raise ValueError("target_chunk_size must be between min and max chunk sizes")
        if self.overlap_size >= self.target_chunk_size:
            raise ValueError("Overlap size cannot be larger than target chunk size")
        if self.csv_rows_per_chunk <= 0:
            raise ValueError("CSV rows per chunk must be positive")
        if not 0 <= self.overlap_percentage <= 0.5:
            raise ValueError("overlap_percentage must be between 0 and 0.5")


class BaseChunker(ABC):
    """Abstract base class for document chunkers."""

    def __init__(self, config: ChunkingConfig):
        self.config = config
        self.config.validate()

    @abstractmethod
    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Chunk document content into semantic chunks."""
        pass

    def generate_chunk_id(self, document_id: str, chunk_index: int, content: str) -> str:
        """Generate unique chunk ID."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{document_id}_chunk_{chunk_index:04d}_{content_hash}"

    def calculate_overlap(self, chunks: list[str]) -> list[tuple[str, Optional[str]]]:
        """Calculate overlap content between consecutive chunks."""
        if not chunks or len(chunks) <= 1:
            return [(chunk, None) for chunk in chunks]

        result = []
        for i, chunk in enumerate(chunks):
            overlap = None
            if i > 0:
                # Get overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_size = min(self.config.overlap_size, len(prev_chunk) // 4)
                if overlap_size > 0:
                    overlap = prev_chunk[-overlap_size:].strip()

            result.append((chunk, overlap))

        return result

    def extract_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract named entities from content (simplified implementation)."""
        if not self.config.enable_entity_extraction:
            return []

        # Simple pattern-based entity extraction
        entities = []

        # Dates
        date_pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
        for match in re.finditer(date_pattern, content):
            entities.append(
                {"type": "DATE", "text": match.group(), "start": match.start(), "end": match.end()}
            )

        # URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        for match in re.finditer(url_pattern, content):
            entities.append(
                {"type": "URL", "text": match.group(), "start": match.start(), "end": match.end()}
            )

        # Email addresses
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_pattern, content):
            entities.append(
                {"type": "EMAIL", "text": match.group(), "start": match.start(), "end": match.end()}
            )

        return entities

    def extract_references(self, content: str) -> list[str]:
        """Extract cross-references from content."""
        if not self.config.enable_reference_tracking:
            return []

        references = []

        # Citations (e.g., [1], (Smith, 2020))
        citation_patterns = [
            r"\[\d+\]",  # [1], [23]
            r"\([A-Za-z]+,?\s*\d{4}\)",  # (Smith, 2020)
            r"\b(?:see|refer to|cf\.)\s+[A-Za-z\s]+\d+",  # see Chapter 5
        ]

        for pattern in citation_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                references.append(match.group().strip())

        return list(set(references))  # Remove duplicates


class SemanticChunker(BaseChunker):
    """Semantic chunker that preserves meaning and context."""

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Chunk content using semantic boundaries."""

        # Split content into logical units
        sections = self._split_into_sections(content)

        # Process each section
        all_chunks = []
        for section_idx, section in enumerate(sections):
            section_chunks = self._chunk_section(section, document_id, section_idx)
            all_chunks.extend(section_chunks)

        # Add overlap and link chunks
        self._add_overlap_and_links(all_chunks)

        return all_chunks

    def _split_into_sections(self, content: str) -> list[dict[str, Any]]:
        """Split content into logical sections."""
        sections = []

        # Split by headers (markdown-style)
        header_pattern = r"^(#{1,6})\s+(.+)$"
        lines = content.split("\n")

        current_section = {"title": None, "level": 0, "content": [], "start_line": 0}

        for line_idx, line in enumerate(lines):
            header_match = re.match(header_pattern, line, re.MULTILINE)

            if header_match:
                # Save previous section if it has content
                if current_section["content"]:
                    current_section["content"] = "\n".join(current_section["content"])
                    sections.append(current_section)

                # Start new section
                header_level = len(header_match.group(1))
                header_title = header_match.group(2).strip()

                current_section = {
                    "title": header_title,
                    "level": header_level,
                    "content": [],
                    "start_line": line_idx,
                }
            else:
                current_section["content"].append(line)

        # Add final section
        if current_section["content"]:
            current_section["content"] = "\n".join(current_section["content"])
            sections.append(current_section)

        # If no sections found, treat entire content as one section
        if not sections:
            sections = [{"title": None, "level": 0, "content": content, "start_line": 0}]

        return sections

    def _chunk_section(
        self, section: dict[str, Any], document_id: str, section_idx: int
    ) -> list[DocumentChunk]:
        """Chunk a single section semantically."""
        content = section["content"]
        if not content.strip():
            return []

        # Split into paragraphs
        paragraphs = self._split_paragraphs(content)

        chunks = []
        current_chunk = ""
        chunk_index = len(chunks)

        for para in paragraphs:
            # Check if adding this paragraph would exceed max chunk size
            potential_chunk = current_chunk + "\n\n" + para if current_chunk else para

            if len(potential_chunk) <= self.config.max_chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.config.min_chunk_size:
                    chunk = self._create_chunk(current_chunk, document_id, chunk_index, section)
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new chunk with current paragraph
                current_chunk = para

        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunk = self._create_chunk(current_chunk, document_id, chunk_index, section)
            chunks.append(chunk)

        return chunks

    def _split_paragraphs(self, content: str) -> list[str]:
        """Split content into paragraphs while preserving structure."""
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r"\n\s*\n", content)

        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 10:  # Minimum paragraph length
                cleaned_paragraphs.append(para)

        return cleaned_paragraphs

    def _create_chunk(
        self, content: str, document_id: str, chunk_index: int, section: dict[str, Any]
    ) -> DocumentChunk:
        """Create a DocumentChunk with metadata."""
        chunk_id = self.generate_chunk_id(document_id, chunk_index, content)

        # Determine chunk type
        chunk_type = self._determine_chunk_type(content)

        # Create metadata
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_type=chunk_type,
            chunk_index=chunk_index,
            start_position=0,  # Would be calculated in real implementation
            end_position=len(content),
            section_title=section.get("title"),
            heading_level=section.get("level"),
            language=self.config.default_language,
        )

        # Create chunk
        chunk = DocumentChunk(content=content, metadata=metadata)

        # Calculate metrics
        chunk.calculate_metrics()

        # Extract entities and references
        metadata.entities = self.extract_entities(content)
        metadata.references = self.extract_references(content)

        return chunk

    def _determine_chunk_type(self, content: str) -> ChunkType:
        """Determine the type of chunk based on content analysis."""
        content_lower = content.lower().strip()

        # Check for different content types
        if re.match(r"^#{1,6}\s+", content):
            return ChunkType.HEADING
        elif "|" in content and "\n" in content and content.count("|") > 2:
            return ChunkType.TABLE
        elif content.startswith(("- ", "* ", "1. ", "2. ")):
            return ChunkType.LIST
        elif re.search(r"```|`\w+`|def |class |function |var |let |const ", content):
            return ChunkType.CODE
        elif re.search(r"\[.*?\]|\(.*?\)|see |refer to |citation", content_lower):
            return ChunkType.REFERENCE
        else:
            return ChunkType.PARAGRAPH

    def _add_overlap_and_links(self, chunks: list[DocumentChunk]) -> None:
        """Add overlap content and link chunks together."""
        if len(chunks) <= 1:
            return

        for i, chunk in enumerate(chunks):
            # Add overlap from previous chunk
            if i > 0:
                prev_chunk = chunks[i - 1]
                overlap_size = min(self.config.overlap_size, len(prev_chunk.content) // 4)
                if overlap_size > 0:
                    chunk.overlap_content = prev_chunk.content[-overlap_size:].strip()
                chunk.metadata.previous_chunk_id = prev_chunk.chunk_id

            # Link to next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                chunk.metadata.next_chunk_id = next_chunk.chunk_id


class PDFChunker(BaseChunker):
    """Specialized chunker for PDF documents."""

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Chunk PDF content page by page with semantic boundaries."""

        # For text-based PDF content, use semantic chunking with page awareness
        if self.config.pdf_respect_pages and "page_breaks" in kwargs:
            return self._chunk_with_pages(content, document_id, kwargs["page_breaks"])
        else:
            # Fallback to semantic chunking
            semantic_chunker = SemanticChunker(self.config)
            return semantic_chunker.chunk_content(content, document_id)

    def _chunk_with_pages(
        self, content: str, document_id: str, page_breaks: list[int]
    ) -> list[DocumentChunk]:
        """Chunk content respecting page boundaries."""
        chunks = []
        lines = content.split("\n")

        current_page = 1
        current_chunk = ""
        chunk_index = 0

        for line_idx, line in enumerate(lines):
            # Check if we've hit a page break
            if line_idx in page_breaks:
                if current_chunk.strip() and len(current_chunk) >= self.config.min_chunk_size:
                    chunk = self._create_pdf_chunk(
                        current_chunk.strip(), document_id, chunk_index, current_page
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                current_page += 1
                current_chunk = ""

            current_chunk += line + "\n"

            # Check if chunk is getting too large
            if len(current_chunk) >= self.config.max_chunk_size:
                chunk = self._create_pdf_chunk(
                    current_chunk.strip(), document_id, chunk_index, current_page
                )
                chunks.append(chunk)
                chunk_index += 1
                current_chunk = ""

        # Add final chunk
        if current_chunk.strip() and len(current_chunk) >= self.config.min_chunk_size:
            chunk = self._create_pdf_chunk(
                current_chunk.strip(), document_id, chunk_index, current_page
            )
            chunks.append(chunk)

        # Add overlap and links
        self._add_overlap_and_links(chunks)

        return chunks

    def _create_pdf_chunk(
        self, content: str, document_id: str, chunk_index: int, page_number: int
    ) -> DocumentChunk:
        """Create a PDF-specific chunk with page metadata."""
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

        # Extract entities and references
        metadata.entities = self.extract_entities(content)
        metadata.references = self.extract_references(content)

        return chunk


class DocxChunker(BaseChunker):
    """Specialized chunker for DOCX documents."""

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Chunk DOCX content respecting document structure."""

        if self.config.docx_respect_sections and "sections" in kwargs:
            return self._chunk_with_sections(content, document_id, kwargs["sections"])
        else:
            # Fallback to semantic chunking
            semantic_chunker = SemanticChunker(self.config)
            return semantic_chunker.chunk_content(content, document_id)

    def _chunk_with_sections(
        self, content: str, document_id: str, sections: list[dict]
    ) -> list[DocumentChunk]:
        """Chunk content respecting DOCX sections."""
        chunks = []
        chunk_index = 0

        for section in sections:
            section_content = section.get("content", "")
            section_title = section.get("title", "")

            if not section_content.strip():
                continue

            # Chunk large sections
            if len(section_content) > self.config.max_chunk_size:
                section_chunks = self._chunk_large_section(
                    section_content, document_id, chunk_index, section_title
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            else:
                chunk = self._create_docx_chunk(
                    section_content, document_id, chunk_index, section_title
                )
                chunks.append(chunk)
                chunk_index += 1

        # Add overlap and links
        self._add_overlap_and_links(chunks)

        return chunks

    def _chunk_large_section(
        self, content: str, document_id: str, start_index: int, section_title: str
    ) -> list[DocumentChunk]:
        """Chunk a large section into smaller pieces."""
        paragraphs = content.split("\n\n")
        chunks = []
        current_chunk = ""
        chunk_index = start_index

        for para in paragraphs:
            potential_chunk = current_chunk + "\n\n" + para if current_chunk else para

            if len(potential_chunk) <= self.config.max_chunk_size:
                current_chunk = potential_chunk
            else:
                if len(current_chunk) >= self.config.min_chunk_size:
                    chunk = self._create_docx_chunk(
                        current_chunk, document_id, chunk_index, section_title
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                current_chunk = para

        # Add final chunk
        if current_chunk and len(current_chunk) >= self.config.min_chunk_size:
            chunk = self._create_docx_chunk(current_chunk, document_id, chunk_index, section_title)
            chunks.append(chunk)

        return chunks

    def _create_docx_chunk(
        self, content: str, document_id: str, chunk_index: int, section_title: str
    ) -> DocumentChunk:
        """Create a DOCX-specific chunk with section metadata."""
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

        # Extract entities and references
        metadata.entities = self.extract_entities(content)
        metadata.references = self.extract_references(content)

        return chunk


class CSVChunker(BaseChunker):
    """Specialized chunker for CSV documents."""

    def chunk_content(self, content: str, document_id: str, **kwargs) -> list[DocumentChunk]:
        """Chunk CSV content by rows or logical groups."""

        lines = content.strip().split("\n")
        if not lines:
            return []

        # Extract header
        header = lines[0] if lines else ""
        data_lines = lines[1:] if len(lines) > 1 else []

        chunks = []
        chunk_index = 0

        # Chunk by rows
        for i in range(0, len(data_lines), self.config.csv_rows_per_chunk):
            chunk_lines = data_lines[i : i + self.config.csv_rows_per_chunk]
            chunk_content = header + "\n" + "\n".join(chunk_lines)

            chunk = self._create_csv_chunk(
                chunk_content,
                document_id,
                chunk_index,
                i + 1,  # Start row
                min(i + self.config.csv_rows_per_chunk, len(data_lines)),  # End row
            )
            chunks.append(chunk)
            chunk_index += 1

        return chunks

    def _create_csv_chunk(
        self, content: str, document_id: str, chunk_index: int, start_row: int, end_row: int
    ) -> DocumentChunk:
        """Create a CSV-specific chunk with row metadata."""
        chunk_id = self.generate_chunk_id(document_id, chunk_index, content)

        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_type=ChunkType.TABLE,
            chunk_index=chunk_index,
            start_position=start_row,
            end_position=end_row,
            section_title=f"Rows {start_row}-{end_row}",
            language=self.config.default_language,
        )

        chunk = DocumentChunk(content=content, metadata=metadata)
        chunk.calculate_metrics()

        return chunk


class DocumentChunkerManager:
    """
    Main manager for document chunking operations.

    Task 2.2.2 Implementation - manages all chunking strategies and provides
    a unified interface for intelligent document chunking.
    """

    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()
        self.chunkers = {
            "semantic": SemanticChunker(self.config),
            "pdf": PDFChunker(self.config),
            "docx": DocxChunker(self.config),
            "csv": CSVChunker(self.config),
        }
        self.chunk_registry: dict[str, list[DocumentChunk]] = {}
        self.document_index: dict[str, dict[str, Any]] = {}

    def chunk_document(
        self, content: str, document_id: str, file_type: str | None = None, **kwargs
    ) -> list[DocumentChunk]:
        """
        Chunk a document using the appropriate strategy.

        Args:
            content: Document content as string
            document_id: Unique identifier for the document
            file_type: File type for format-specific chunking
            **kwargs: Additional parameters for chunkers

        Returns:
            List of DocumentChunk objects
        """
        try:
            # Determine chunking strategy
            chunker = self._select_chunker(content, file_type)

            # Perform chunking
            chunks = chunker.chunk_content(content, document_id, **kwargs)

            # Post-process chunks
            processed_chunks = self._post_process_chunks(chunks, document_id)

            # Register chunks
            self.chunk_registry[document_id] = processed_chunks

            # Update document index
            self._update_document_index(document_id, processed_chunks, file_type)

            logger.info(
                f"Successfully chunked document {document_id} into {len(processed_chunks)} chunks"
            )
            return processed_chunks

        except Exception as e:
            logger.error(f"Error chunking document {document_id}: {e}")
            raise

    def _select_chunker(self, content: str, file_type: str | None) -> BaseChunker:
        """Select the appropriate chunker based on content and file type."""
        if file_type:
            file_ext = file_type.lower().lstrip(".")

            if file_ext == "pdf":
                return self.chunkers["pdf"]
            elif file_ext in ["docx", "doc"]:
                return self.chunkers["docx"]
            elif file_ext == "csv":
                return self.chunkers["csv"]

        # Default to semantic chunker
        return self.chunkers["semantic"]

    def _post_process_chunks(
        self, chunks: list[DocumentChunk], document_id: str
    ) -> list[DocumentChunk]:
        """Post-process chunks for quality and consistency."""
        if not chunks:
            return chunks

        processed_chunks = []

        for i, chunk in enumerate(chunks):
            # Skip chunks that are too small or empty
            if len(chunk.content.strip()) < self.config.min_chunk_size:
                logger.warning(f"Skipping small chunk {i} in document {document_id}")
                continue

            # Calculate quality scores
            chunk.metadata.confidence_score = self._calculate_confidence_score(chunk)

            # Update chunk index to reflect actual position
            chunk.metadata.chunk_index = len(processed_chunks)

            processed_chunks.append(chunk)

        # Update cross-references after filtering
        self._update_cross_references(processed_chunks)

        return processed_chunks

    def _calculate_confidence_score(self, chunk: DocumentChunk) -> float:
        """Calculate confidence score for chunk quality."""
        score = 1.0
        content = chunk.content.strip()

        # Penalize very short or very long chunks
        length_ratio = len(content) / self.config.target_chunk_size
        if length_ratio < 0.3 or length_ratio > 3.0:
            score *= 0.7

        # Reward chunks with good sentence structure
        sentences = re.split(r"[.!?]+", content)
        complete_sentences = [s for s in sentences if len(s.strip()) > 10]
        if len(complete_sentences) > 0:
            sentence_ratio = len(complete_sentences) / len(sentences)
            score *= 0.5 + 0.5 * sentence_ratio

        # Penalize chunks with excessive special characters
        special_char_ratio = len(re.findall(r"[^\w\s.,!?;:]", content)) / len(content)
        if special_char_ratio > 0.3:
            score *= 0.8

        return max(0.1, min(1.0, score))

    def _update_cross_references(self, chunks: list[DocumentChunk]) -> None:
        """Update cross-references between chunks."""
        for i, chunk in enumerate(chunks):
            # Update previous/next chunk references
            if i > 0:
                chunk.metadata.previous_chunk_id = chunks[i - 1].chunk_id
            if i < len(chunks) - 1:
                chunk.metadata.next_chunk_id = chunks[i + 1].chunk_id

    def _update_document_index(
        self, document_id: str, chunks: list[DocumentChunk], file_type: str | None
    ) -> None:
        """Update the document index with chunk metadata."""
        chunk_types = {}
        total_words = 0
        total_chars = 0

        for chunk in chunks:
            chunk_type = chunk.metadata.chunk_type.value
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            total_words += chunk.metadata.word_count
            total_chars += chunk.metadata.character_count

        self.document_index[document_id] = {
            "chunk_count": len(chunks),
            "total_words": total_words,
            "total_characters": total_chars,
            "chunk_types": chunk_types,
            "file_type": file_type,
            "created_at": datetime.now().isoformat(),
            "average_chunk_size": total_chars / len(chunks) if chunks else 0,
            "average_confidence": sum(c.metadata.confidence_score for c in chunks) / len(chunks)
            if chunks
            else 0,
        }

    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        return self.chunk_registry.get(document_id, [])

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        """Get a specific chunk by ID."""
        for chunks in self.chunk_registry.values():
            for chunk in chunks:
                if chunk.chunk_id == chunk_id:
                    return chunk
        return None

    def get_chunk_context(self, chunk_id: str, context_size: int = 1) -> list[DocumentChunk]:
        """Get a chunk with surrounding context chunks."""
        target_chunk = self.get_chunk(chunk_id)
        if not target_chunk:
            return []

        # Find document containing this chunk
        document_chunks = None
        for doc_id, chunks in self.chunk_registry.items():
            if any(c.chunk_id == chunk_id for c in chunks):
                document_chunks = chunks
                break

        if not document_chunks:
            return [target_chunk]

        # Find chunk index
        target_index = None
        for i, chunk in enumerate(document_chunks):
            if chunk.chunk_id == chunk_id:
                target_index = i
                break

        if target_index is None:
            return [target_chunk]

        # Get context chunks
        start_index = max(0, target_index - context_size)
        end_index = min(len(document_chunks), target_index + context_size + 1)

        return document_chunks[start_index:end_index]

    def search_chunks(
        self,
        query: str,
        document_id: str | None = None,
        chunk_type: ChunkType | None = None,
        min_confidence: float = 0.0,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Search chunks by content with relevance scoring.

        Returns list of (chunk, relevance_score) tuples.
        """
        results = []
        query_lower = query.lower()

        # Determine which documents to search
        if document_id:
            search_docs = {document_id: self.chunk_registry.get(document_id, [])}
        else:
            search_docs = self.chunk_registry

        for doc_id, chunks in search_docs.items():
            for chunk in chunks:
                # Filter by chunk type
                if chunk_type and chunk.metadata.chunk_type != chunk_type:
                    continue

                # Filter by confidence
                if chunk.metadata.confidence_score < min_confidence:
                    continue

                # Calculate relevance score
                relevance = self._calculate_relevance(chunk.content, query_lower)

                if relevance > 0:
                    results.append((chunk, relevance))

        # Sort by relevance
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def _calculate_relevance(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query."""
        content_lower = content.lower()

        # Exact phrase match (highest score)
        if query in content_lower:
            return 1.0

        # Word overlap scoring
        query_words = set(query.split())
        content_words = set(content_lower.split())

        if not query_words:
            return 0.0

        overlap = len(query_words.intersection(content_words))
        word_score = overlap / len(query_words)

        # Bonus for word proximity
        for word in query_words:
            if word in content_lower:
                word_score += 0.1

        return min(1.0, word_score)

    def get_document_summary(self, document_id: str) -> dict[str, Any]:
        """Get comprehensive summary of document chunking."""
        if document_id not in self.document_index:
            return {}

        chunks = self.get_chunks(document_id)
        index_data = self.document_index[document_id]

        # Calculate additional statistics
        chunk_sizes = [len(c.content) for c in chunks]
        confidence_scores = [c.metadata.confidence_score for c in chunks]

        return {
            **index_data,
            "chunk_size_stats": {
                "min": min(chunk_sizes) if chunk_sizes else 0,
                "max": max(chunk_sizes) if chunk_sizes else 0,
                "median": sorted(chunk_sizes)[len(chunk_sizes) // 2] if chunk_sizes else 0,
            },
            "confidence_stats": {
                "min": min(confidence_scores) if confidence_scores else 0,
                "max": max(confidence_scores) if confidence_scores else 0,
                "median": sorted(confidence_scores)[len(confidence_scores) // 2]
                if confidence_scores
                else 0,
            },
            "has_references": any(c.metadata.references for c in chunks),
            "has_entities": any(c.metadata.entities for c in chunks),
            "unique_sections": len(
                set(c.metadata.section_title for c in chunks if c.metadata.section_title)
            ),
        }

    def get_chunking_statistics(self) -> dict[str, Any]:
        """Get overall chunking statistics across all documents."""
        total_chunks = sum(len(chunks) for chunks in self.chunk_registry.values())
        total_docs = len(self.chunk_registry)

        if total_chunks == 0:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "average_chunks_per_doc": 0,
                "chunk_types": {},
                "file_types": {},
                "quality_distribution": {},
            }

        # Aggregate statistics
        all_chunks = []
        for chunks in self.chunk_registry.values():
            all_chunks.extend(chunks)

        chunk_types = {}
        file_types = {}
        confidence_ranges = {"high": 0, "medium": 0, "low": 0}

        for chunk in all_chunks:
            # Chunk types
            chunk_type = chunk.metadata.chunk_type.value
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

            # Confidence ranges
            confidence = chunk.metadata.confidence_score
            if confidence >= 0.8:
                confidence_ranges["high"] += 1
            elif confidence >= 0.6:
                confidence_ranges["medium"] += 1
            else:
                confidence_ranges["low"] += 1

        # File types from document index
        for doc_data in self.document_index.values():
            file_type = doc_data.get("file_type", "unknown")
            file_types[file_type] = file_types.get(file_type, 0) + 1

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "average_chunks_per_doc": total_chunks / total_docs,
            "chunk_types": chunk_types,
            "file_types": file_types,
            "quality_distribution": confidence_ranges,
            "config": {
                "target_chunk_size": self.config.target_chunk_size,
                "overlap_size": self.config.overlap_size,
                "boundary_strategy": self.config.boundary_strategy.value,
            },
        }

    def export_chunks(self, document_id: str, format_type: str = "json") -> str:
        """Export chunks in specified format."""
        chunks = self.get_chunks(document_id)

        if format_type.lower() == "json":
            import json

            chunk_data = [chunk.to_dict() for chunk in chunks]
            return json.dumps(chunk_data, indent=2, default=str)

        elif format_type.lower() == "text":
            result = []
            for i, chunk in enumerate(chunks):
                result.append(f"=== Chunk {i + 1} ===")
                result.append(f"ID: {chunk.chunk_id}")
                result.append(f"Type: {chunk.metadata.chunk_type.value}")
                result.append(f"Size: {len(chunk.content)} characters")
                result.append(f"Confidence: {chunk.metadata.confidence_score:.2f}")
                result.append("")
                result.append(chunk.content)
                result.append("")

            return "\n".join(result)

        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def clear_document(self, document_id: str) -> bool:
        """Clear all chunks for a document."""
        if document_id in self.chunk_registry:
            del self.chunk_registry[document_id]

        if document_id in self.document_index:
            del self.document_index[document_id]

        return True

    def clear_all(self) -> None:
        """Clear all chunks and indexes."""
        self.chunk_registry.clear()
        self.document_index.clear()


# Integration with existing file processing
class ChunkingIntegration:
    """Integration layer for connecting chunking with existing file processing."""

    def __init__(self, chunker_manager: DocumentChunkerManager | None = None):
        self.chunker_manager = chunker_manager or DocumentChunkerManager()

    def process_file_with_chunking(
        self, content: str, filename: str, document_id: str | None = None
    ) -> tuple[str, list[DocumentChunk]]:
        """
        Process file content and return both original result and chunks.

        Returns:
            Tuple of (processed_content, chunks)
        """
        if document_id is None:
            document_id = self._generate_document_id(filename)

        # Determine file type
        file_ext = Path(filename).suffix.lower().lstrip(".")

        # Chunk the content
        chunks = self.chunker_manager.chunk_document(content, document_id, file_ext)

        # Combine chunks for backward compatibility
        combined_content = "\n\n".join(chunk.content for chunk in chunks)

        return combined_content, chunks

    def _generate_document_id(self, filename: str) -> str:
        """Generate document ID from filename."""
        # Remove extension and create hash
        base_name = Path(filename).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(f"{base_name}_{timestamp}".encode()).hexdigest()[:8]

        return f"doc_{base_name}_{content_hash}"

    def get_chunk_context_for_query(
        self, query: str, max_chunks: int = 5, context_size: int = 1
    ) -> list[str]:
        """
        Get relevant chunk contexts for a query.

        Returns list of context strings combining chunk content with overlap.
        """
        # Search across all documents
        search_results = self.chunker_manager.search_chunks(query)

        # Get top results with context
        contexts = []
        for chunk, relevance in search_results[:max_chunks]:
            context_chunks = self.chunker_manager.get_chunk_context(chunk.chunk_id, context_size)

            # Combine context chunks
            context_content = "\n\n".join(c.effective_content for c in context_chunks)
            contexts.append(context_content)

        return contexts


# Global chunker instance for easy access
default_chunker_manager = DocumentChunkerManager()
chunking_integration = ChunkingIntegration(default_chunker_manager)


# Utility functions for external integration
def chunk_document_content(
    content: str, filename: str, config: ChunkingConfig | None = None
) -> list[DocumentChunk]:
    """Utility function to chunk document content."""
    manager = DocumentChunkerManager(config) if config else default_chunker_manager
    document_id = f"doc_{Path(filename).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    file_ext = Path(filename).suffix.lower().lstrip(".")

    return manager.chunk_document(content, document_id, file_ext)


def get_optimal_chunking_config(file_type: str, content_length: int) -> ChunkingConfig:
    """Get optimal chunking configuration for specific file type and size."""
    config = ChunkingConfig()

    # Adjust based on file type
    if file_type.lower() == "pdf":
        config.pdf_respect_pages = True
        config.target_chunk_size = 1500  # Larger chunks for PDFs
        config.overlap_size = 300

    elif file_type.lower() in ["docx", "doc"]:
        config.docx_respect_sections = True
        config.preserve_headers = True
        config.target_chunk_size = 1200

    elif file_type.lower() == "csv":
        config.csv_chunk_by_rows = True
        config.csv_rows_per_chunk = 50 if content_length > 100000 else 100
        config.boundary_strategy = ChunkBoundary.PARAGRAPH

    # Adjust based on content length
    if content_length > 50000:  # Large documents
        config.target_chunk_size = min(2000, config.target_chunk_size * 1.5)
        config.overlap_size = min(400, config.overlap_size * 1.5)
    elif content_length < 5000:  # Small documents
        config.target_chunk_size = max(500, config.target_chunk_size * 0.7)
        config.overlap_size = max(100, config.overlap_size * 0.7)

    return config


# Task 2.2.2 completion marker
logger.info("[Document Chunker] Task 2.2.2 Document Chunking Strategy - Implementation Complete")
