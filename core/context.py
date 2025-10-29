"""Enhanced context manager for document processing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.chunking.models import DocumentChunk
from core.document_store import DocumentStore


class ContextManager:
    """Manages document context and retrieval via the shared document store."""

    def __init__(
        self,
        document_store: DocumentStore | None = None,
        context_horizon: int = 1,
    ) -> None:
        self.document_store = document_store or DocumentStore()
        self.context_horizon = max(0, context_horizon)

    def add_document(self, filename: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Add document content to the centralized store with chunk registration."""

        if not content:
            raise ValueError("Document content cannot be empty")

        metadata = metadata or {}
        file_extension = metadata.get("file_extension") or Path(filename).suffix.lstrip(".").lower()
        doc_type = file_extension or metadata.get("doc_type", "text")

        return self.document_store.add_document(
            content=content,
            title=filename,
            file_path=None,
            doc_type=doc_type,
            metadata=metadata,
            user_id=metadata.get("user_id"),
        )

    def get_relevant_context(self, query: str, limit: int = 3) -> str | None:
        """Retrieve a textual context summary for a query from indexed chunks."""

        if not query:
            return None

        chunk_contexts = self._collect_chunk_contexts(query, limit)
        if chunk_contexts:
            return "\n\n---\n\n".join(chunk_contexts)

        fallback_contexts = self._collect_document_snippets(query, limit)
        if fallback_contexts:
            return "\n\n".join(fallback_contexts)

        return None

    def has_context(self) -> bool:
        """Return True when the document store has indexed content."""

        return bool(self.document_store.chunk_manager.chunk_registry)

    def _collect_chunk_contexts(self, query: str, limit: int) -> list[str]:
        """Gather chunk-based context snippets for a query."""

        search_results = self.document_store.chunk_manager.search_chunks(query)
        if not search_results:
            return []

        context_parts: list[str] = []
        seen_documents: set[str] = set()

        for chunk, _score in search_results:
            document_id = chunk.metadata.document_id
            if document_id in seen_documents:
                continue

            seen_documents.add(document_id)
            context_entry = self._build_chunk_context_entry(chunk)
            if not context_entry:
                continue

            context_parts.append(context_entry)
            if len(context_parts) >= limit:
                break

        return context_parts

    def _collect_document_snippets(self, query: str, limit: int) -> list[str]:
        """Fallback to direct document search when chunk search is empty."""

        documents = self.document_store.search_documents(query, limit=limit)
        if not documents:
            return []

        snippets: list[str] = []
        for doc in documents[:limit]:
            content = doc.get("content", "")
            if not content:
                continue
            snippet = content[:500] + "..." if len(content) > 500 else content
            title = doc.get("title") or doc.get("id")
            snippets.append(f"From {title}: {snippet}")

        return snippets

    def _build_chunk_context_entry(self, chunk: DocumentChunk) -> str | None:
        """Compose a human-readable context entry for a chunk result."""

        document_id = chunk.metadata.document_id
        document = self.document_store.get_document(document_id) or {}
        title = document.get("title") or document_id
        context_chunks = self.document_store.chunk_manager.get_chunk_context(
            chunk.chunk_id, context_size=self.context_horizon
        )
        if not context_chunks:
            return None

        snippet = "\n\n".join(context_chunk.effective_content for context_chunk in context_chunks)
        return f"From {title}:\n{snippet}" if snippet else None


__all__ = ["ContextManager"]
