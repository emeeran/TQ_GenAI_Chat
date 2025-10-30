"""Coordinator for chunking strategies and downstream indexing."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from .config import ChunkingConfig
from .csv import CSVChunker
from .docx import DocxChunker
from .models import DocumentChunk
from .pdf import PDFChunker
from .semantic import SemanticChunker
from .types import ChunkType

logger = logging.getLogger(__name__)


class DocumentChunkerManager:
    """Dispatch documents to the appropriate chunking strategy."""

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
        self,
        content: str,
        document_id: str,
        file_type: str | None = None,
        **kwargs: Any,
    ) -> list[DocumentChunk]:
        """Chunk a document and register the resulting metadata."""

        try:
            chunker = self._select_chunker(file_type)
            raw_chunks = chunker.chunk_content(content, document_id, **kwargs)
            processed_chunks = self._post_process_chunks(raw_chunks, document_id)
            self.register_chunks(document_id, processed_chunks, file_type)
            logger.info("Chunked document %s into %s chunks", document_id, len(processed_chunks))
            return processed_chunks
        except Exception as exc:  # noqa: BLE001 - we rethrow after logging
            logger.exception("Error chunking document %s", document_id)
            raise exc

    def _select_chunker(self, file_type: str | None) -> SemanticChunker:
        if file_type:
            file_ext = file_type.lower().lstrip(".")
            if file_ext == "pdf":
                return self.chunkers["pdf"]
            if file_ext in {"doc", "docx"}:
                return self.chunkers["docx"]
            if file_ext == "csv":
                return self.chunkers["csv"]
        return self.chunkers["semantic"]

    def _post_process_chunks(self, chunks: list[DocumentChunk], document_id: str) -> list[DocumentChunk]:
        if not chunks:
            return []

        processed: list[DocumentChunk] = []
        for chunk in chunks:
            if len(chunk.content.strip()) < self.config.min_chunk_size:
                logger.debug("Skipping small chunk in %s", document_id)
                continue
            chunk.metadata.confidence_score = self._calculate_confidence_score(chunk)
            chunk.metadata.chunk_index = len(processed)
            processed.append(chunk)

        self._update_cross_references(processed)
        return processed

    def _calculate_confidence_score(self, chunk: DocumentChunk) -> float:
        score = 1.0
        content = chunk.content.strip()
        length_ratio = len(content) / self.config.target_chunk_size
        if length_ratio < 0.3 or length_ratio > 3.0:
            score *= 0.7

        sentences = re.split(r"[.!?]+", content)
        complete = [sentence for sentence in sentences if len(sentence.strip()) > 10]
        if complete:
            score *= 0.5 + 0.5 * (len(complete) / len(sentences))

        special_ratio = len(re.findall(r"[^\w\s.,!?;:]", content)) / max(len(content), 1)
        if special_ratio > 0.3:
            score *= 0.8

        return max(0.1, min(1.0, score))

    def _update_cross_references(self, chunks: list[DocumentChunk]) -> None:
        for index, chunk in enumerate(chunks):
            if index > 0:
                chunk.metadata.previous_chunk_id = chunks[index - 1].chunk_id
            if index < len(chunks) - 1:
                chunk.metadata.next_chunk_id = chunks[index + 1].chunk_id

    def _update_document_index(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        file_type: str | None,
    ) -> None:
        chunk_types: dict[str, int] = {}
        total_words = 0
        total_chars = 0

        for chunk in chunks:
            chunk_type = chunk.metadata.chunk_type.value
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            total_words += chunk.metadata.word_count
            total_chars += chunk.metadata.character_count

        average_confidence = (
            sum(chunk.metadata.confidence_score for chunk in chunks) / len(chunks)
            if chunks
            else 0
        )

        self.document_index[document_id] = {
            "chunk_count": len(chunks),
            "total_words": total_words,
            "total_characters": total_chars,
            "chunk_types": chunk_types,
            "file_type": file_type,
            "created_at": datetime.now().isoformat(),
            "average_chunk_size": total_chars / len(chunks) if chunks else 0,
            "average_confidence": average_confidence,
        }

    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        return self.chunk_registry.get(document_id, [])

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        for chunks in self.chunk_registry.values():
            for chunk in chunks:
                if chunk.chunk_id == chunk_id:
                    return chunk
        return None

    def get_chunk_context(self, chunk_id: str, context_size: int = 1) -> list[DocumentChunk]:
        target = self.get_chunk(chunk_id)
        if not target:
            return []

        document_chunks = self._find_document_chunks(chunk_id)
        if not document_chunks:
            return [target]

        target_index = next((idx for idx, chunk in enumerate(document_chunks) if chunk.chunk_id == chunk_id), None)
        if target_index is None:
            return [target]

        start = max(0, target_index - context_size)
        end = min(len(document_chunks), target_index + context_size + 1)
        return document_chunks[start:end]

    def search_chunks(
        self,
        query: str,
        document_id: str | None = None,
        chunk_type: ChunkType | None = None,
        min_confidence: float = 0.0,
    ) -> list[tuple[DocumentChunk, float]]:
        results: list[tuple[DocumentChunk, float]] = []
        query_lower = query.lower()

        documents = {document_id: self.chunk_registry.get(document_id, [])} if document_id else self.chunk_registry

        for chunks in documents.values():
            for chunk in chunks:
                if chunk_type and chunk.metadata.chunk_type != chunk_type:
                    continue
                if chunk.metadata.confidence_score < min_confidence:
                    continue

                relevance = self._calculate_relevance(chunk.content, query_lower)
                if relevance > 0:
                    results.append((chunk, relevance))

        results.sort(key=lambda pair: pair[1], reverse=True)
        return results

    def _calculate_relevance(self, content: str, query_lower: str) -> float:
        content_lower = content.lower()
        if query_lower in content_lower:
            return 1.0

        query_words = set(query_lower.split())
        if not query_words:
            return 0.0

        content_words = set(content_lower.split())
        overlap = len(query_words.intersection(content_words))
        word_score = overlap / len(query_words)
        for word in query_words:
            if word in content_lower:
                word_score += 0.1
        return min(1.0, word_score)

    def get_document_summary(self, document_id: str) -> dict[str, Any]:
        if document_id not in self.document_index:
            return {}

        chunks = self.get_chunks(document_id)
        index_data = self.document_index[document_id]

        return {
            **index_data,
            "chunk_size_stats": self._calculate_size_stats(chunks),
            "confidence_stats": self._calculate_confidence_stats(chunks),
            "has_references": any(chunk.metadata.references for chunk in chunks),
            "has_entities": any(chunk.metadata.entities for chunk in chunks),
            "unique_sections": len({chunk.metadata.section_title for chunk in chunks if chunk.metadata.section_title}),
        }

    def get_chunking_statistics(self) -> dict[str, Any]:
        total_chunks = sum(len(chunks) for chunks in self.chunk_registry.values())
        total_documents = len(self.chunk_registry)
        if total_chunks == 0:
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "average_chunks_per_doc": 0,
                "chunk_types": {},
                "file_types": {},
                "quality_distribution": {},
            }

        all_chunks = [chunk for chunks in self.chunk_registry.values() for chunk in chunks]
        chunk_types = self._aggregate_chunk_types(all_chunks)
        quality_distribution = self._calculate_quality_distribution(all_chunks)
        file_types = self._aggregate_file_types()

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "average_chunks_per_doc": total_chunks / total_documents,
            "chunk_types": chunk_types,
            "file_types": file_types,
            "quality_distribution": quality_distribution,
            "config": {
                "target_chunk_size": self.config.target_chunk_size,
                "overlap_size": self.config.overlap_size,
                "boundary_strategy": self.config.boundary_strategy.value,
            },
        }

    def export_chunks(self, document_id: str, format_type: str = "json") -> str:
        chunks = self.get_chunks(document_id)
        if format_type.lower() == "json":
            import json

            return json.dumps([chunk.to_dict() for chunk in chunks], indent=2, default=str)
        if format_type.lower() == "text":
            lines: list[str] = []
            for index, chunk in enumerate(chunks):
                lines.append(f"=== Chunk {index + 1} ===")
                lines.append(f"ID: {chunk.chunk_id}")
                lines.append(f"Type: {chunk.metadata.chunk_type.value}")
                lines.append(f"Size: {len(chunk.content)} characters")
                lines.append(f"Confidence: {chunk.metadata.confidence_score:.2f}")
                lines.append("")
                lines.append(chunk.content)
                lines.append("")
            return "\n".join(lines)

        raise ValueError(f"Unsupported export format: {format_type}")

    def clear_document(self, document_id: str) -> bool:
        if document_id in self.chunk_registry:
            del self.chunk_registry[document_id]
        if document_id in self.document_index:
            del self.document_index[document_id]
        return True

    def clear_all(self) -> None:
        self.chunk_registry.clear()
        self.document_index.clear()

    def _find_document_chunks(self, chunk_id: str) -> list[DocumentChunk] | None:
        for chunks in self.chunk_registry.values():
            if any(chunk.chunk_id == chunk_id for chunk in chunks):
                return chunks
        return None

    def _calculate_size_stats(self, chunks: list[DocumentChunk]) -> dict[str, int]:
        if not chunks:
            return {"min": 0, "max": 0, "median": 0}

        sizes = sorted(len(chunk.content) for chunk in chunks)
        median = sizes[len(sizes) // 2]
        return {"min": sizes[0], "max": sizes[-1], "median": median}

    def _calculate_confidence_stats(self, chunks: list[DocumentChunk]) -> dict[str, float]:
        if not chunks:
            return {"min": 0.0, "max": 0.0, "median": 0.0}

        scores = sorted(chunk.metadata.confidence_score for chunk in chunks)
        median = scores[len(scores) // 2]
        return {"min": scores[0], "max": scores[-1], "median": median}

    def _aggregate_chunk_types(self, chunks: list[DocumentChunk]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for chunk in chunks:
            chunk_type = chunk.metadata.chunk_type.value
            counts[chunk_type] = counts.get(chunk_type, 0) + 1
        return counts

    def _calculate_quality_distribution(self, chunks: list[DocumentChunk]) -> dict[str, int]:
        distribution = {"high": 0, "medium": 0, "low": 0}
        for chunk in chunks:
            confidence = chunk.metadata.confidence_score
            if confidence >= 0.8:
                distribution["high"] += 1
            elif confidence >= 0.6:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        return distribution

    def _aggregate_file_types(self) -> dict[str, int]:
        file_types: dict[str, int] = {}
        for index_entry in self.document_index.values():
            file_type = index_entry.get("file_type", "unknown")
            file_types[file_type] = file_types.get(file_type, 0) + 1
        return file_types

    def register_chunks(
        self,
        document_id: str,
        chunks: list[DocumentChunk],
        file_type: str | None = None,
    ) -> None:
        """Persist an externally computed chunk list in the in-memory registries."""

        if not chunks:
            self.chunk_registry.pop(document_id, None)
            self.document_index.pop(document_id, None)
            return

        for index, chunk in enumerate(chunks):
            chunk.metadata.chunk_index = index

        self._update_cross_references(chunks)
        self.chunk_registry[document_id] = chunks
        self._update_document_index(document_id, chunks, file_type)


__all__ = ["DocumentChunkerManager"]
