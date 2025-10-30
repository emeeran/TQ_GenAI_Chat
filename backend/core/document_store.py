"""Document storage backed by SQLite with modular chunk management."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from config.settings import BASE_DIR

from .chunking import ChunkMetadata, ChunkType, DocumentChunk, DocumentChunkerManager


@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    title: str
    content: str
    metadata_json: str
    file_path: str | None
    timestamp: int
    doc_type: str
    user_id: str | None


class DocumentStore:
    """SQLite-based document storage system with caching and indexing"""

    def __init__(
        self,
        db_path: str | None = None,
        chunk_manager: DocumentChunkerManager | None = None,
    ):
        """
        Initialize the document store

        Args:
            db_path: Path to SQLite database file, defaults to BASE_DIR/documents.db
        """
        self.db_path = db_path or str(BASE_DIR / "documents.db")
        self.chunk_manager = chunk_manager or DocumentChunkerManager()
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create documents table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                file_path TEXT,
                timestamp INTEGER NOT NULL,
                type TEXT NOT NULL,
                user_id TEXT,
                embedding_id TEXT
            )
        """
        )

        # Create embeddings table for vector search
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                embedding BLOB,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """
        )

        # Create chunks table for document segments
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                metadata TEXT,
                embedding_id TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """
        )

        # Create indices for faster lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON documents (type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks (document_id)")

        conn.commit()
        conn.close()

    def add_document(
        self,
        content: str,
        title: str | None = None,
        file_path: str | None = None,
        doc_type: str = "text",
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> str:
        """
        Add a document to the store

        Args:
            content: Document content
            title: Document title
            file_path: Source file path
            doc_type: Document type (text, pdf, docx, etc.)
            metadata: Additional metadata
            user_id: User identifier

        Returns:
            Document ID
        """
        if not content:
            raise ValueError("Document content cannot be empty")

        doc_id, resolved_title, timestamp = self._prepare_document_identity(content, title)
        metadata_payload = metadata or {}
        metadata_json = json.dumps(metadata_payload)

        record = DocumentRecord(
            doc_id=doc_id,
            title=resolved_title,
            content=content,
            metadata_json=metadata_json,
            file_path=file_path,
            timestamp=timestamp,
            doc_type=doc_type,
            user_id=user_id,
        )

        try:
            self._insert_document_record(record)
        except sqlite3.Error as exc:
            logging.getLogger(__name__).error("Database error adding document: %s", exc)
            raise

        self._process_chunks(doc_id, content, doc_type, metadata_payload)
        return doc_id

    def _process_chunks(
        self,
        doc_id: str,
        content: str,
        doc_type: str,
        metadata: dict[str, Any],
    ) -> None:
        """Chunk the document using the modular strategy package and persist results."""

        if not content.strip():
            return

        file_type = metadata.get("file_extension") or doc_type
        chunks: list[DocumentChunk] = []
        try:
            chunks = self.chunk_manager.chunk_document(content, doc_id, file_type)
        except Exception as exc:  # noqa: BLE001 - ensure we persist base content even on failure
            logging.getLogger(__name__).exception("Chunking failed for %s: %s", doc_id, exc)

        if not chunks:
            chunks = [self._create_fallback_chunk(doc_id, content, file_type)]

        self.chunk_manager.register_chunks(doc_id, chunks, file_type)
        self._store_chunks(chunks)

    def _store_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Persist a collection of chunks in a single transaction."""

        if not chunks:
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            rows = [
                (
                    chunk.chunk_id,
                    chunk.metadata.document_id,
                    chunk.content,
                    chunk.metadata.chunk_index,
                    json.dumps(chunk.metadata.to_dict()),
                )
                for chunk in chunks
            ]
            cursor.executemany(
                """
                INSERT INTO chunks
                (id, document_id, content, chunk_index, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            logging.getLogger(__name__).error("Database error adding chunks: %s", exc)
            raise
        finally:
            conn.close()

    def _create_fallback_chunk(
        self, doc_id: str, content: str, file_type: str | None
    ) -> DocumentChunk:
        """Create a minimal chunk when strategy filtering results in no output."""

        chunk_id = f"{doc_id}_chunk_0000"
        chunk_type = ChunkType.TABLE if (file_type or "").lower() == "csv" else ChunkType.TEXT
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=doc_id,
            chunk_type=chunk_type,
            chunk_index=0,
            start_position=0,
            end_position=len(content),
            language="unknown",
        )
        chunk = DocumentChunk(content=content, metadata=metadata)
        chunk.calculate_metrics()
        logging.getLogger(__name__).debug(
            "Using fallback chunk for document %s with file type %s", doc_id, file_type
        )
        return chunk

    @staticmethod
    def _prepare_document_identity(content: str, title: str | None) -> tuple[str, str, int]:
        timestamp = int(time.time())
        resolved_title = title or content[:50] + ("..." if len(content) > 50 else "")
        doc_id = DocumentStore._generate_document_id(content, timestamp)
        return doc_id, resolved_title, timestamp

    @staticmethod
    def _generate_document_id(content: str, timestamp: int) -> str:
        doc_hash = hashlib.md5(
            f"{content[:1000]}{timestamp}".encode(), usedforsecurity=False
        ).hexdigest()  # nosec B324
        return f"doc_{doc_hash}"

    def _insert_document_record(self, record: DocumentRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO documents
                (id, title, content, metadata, file_path, timestamp, type, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.doc_id,
                    record.title,
                    record.content,
                    record.metadata_json,
                    record.file_path,
                    record.timestamp,
                    record.doc_type,
                    record.user_id,
                ),
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if not row:
                return None
            doc = dict(row)
            if doc.get("metadata"):
                doc["metadata"] = json.loads(doc["metadata"])
            else:
                doc["metadata"] = {}
            return doc
        except sqlite3.Error as e:
            logging.getLogger(__name__).error(f"Database error retrieving document: {str(e)}")
            return None
        finally:
            conn.close()

    def search_documents(self, query: str, doc_type: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        results = []
        try:
            # Prepare search parameters
            search_term = f"%{query}%"
            if doc_type:
                cursor.execute(
                    "SELECT * FROM documents WHERE (title LIKE ? OR content LIKE ?) AND type = ? ORDER BY timestamp DESC LIMIT ?",
                    (search_term, search_term, doc_type, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM documents WHERE title LIKE ? OR content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                    (search_term, search_term, limit),
                )
            for row in cursor.fetchall():
                doc = dict(row)
                if doc.get("metadata"):
                    doc["metadata"] = json.loads(doc["metadata"])
                else:
                    doc["metadata"] = {}
                results.append(doc)
            return results
        except sqlite3.Error as e:
            logging.getLogger(__name__).error(f"Database error searching documents: {str(e)}")
            return []
        finally:
            conn.close()

    def delete_document(self, doc_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # First delete associated chunks
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
            # Then delete embeddings if any
            cursor.execute("DELETE FROM embeddings WHERE document_id = ?", (doc_id,))
            # Finally delete the document itself
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            logging.getLogger(__name__).error(f"Database error deleting document: {str(e)}")
            return False
        finally:
            conn.close()

    def get_recent_documents(self, limit: int = 10, doc_type: str = None) -> list[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if doc_type:
                cursor.execute(
                    "SELECT * FROM documents WHERE type = ? ORDER BY timestamp DESC LIMIT ?",
                    (doc_type, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM documents ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            results = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc.get("metadata"):
                    doc["metadata"] = json.loads(doc["metadata"])
                else:
                    doc["metadata"] = {}
                results.append(doc)
            return results
        except Exception as e:
            logging.getLogger(__name__).error(f"Database error retrieving recent documents: {str(e)}")
            return []
        finally:
            conn.close()

    def get_statistics(self) -> dict[str, Any]:
    # Get database statistics
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Count total documents
            cursor.execute("SELECT COUNT(*) as total_documents FROM documents")
            total_documents = cursor.fetchone()["total_documents"]

            # Calculate total file size (from metadata or content length fallback)
            cursor.execute("SELECT metadata, content FROM documents")
            total_size = 0
            for row in cursor.fetchall():
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                if "file_size" in metadata:
                    total_size += metadata["file_size"]
                else:
                    total_size += len(row["content"]) if row["content"] else 0

            # Get document types
            cursor.execute("SELECT type, COUNT(*) as count FROM documents GROUP BY type")
            types = {row["type"]: row["count"] for row in cursor.fetchall()}

            # Get recent activity (last 24 hours)
            recent_threshold = int(time.time()) - (24 * 60 * 60)
            cursor.execute(
                "SELECT COUNT(*) as recent_count FROM documents WHERE timestamp > ?",
                (recent_threshold,),
            )
            recent_documents = cursor.fetchone()["recent_count"]

            return {
                "total_documents": total_documents,
                "total_size": total_size,
                "document_types": types,
                "recent_documents": recent_documents,
            }

        except sqlite3.Error as e:
            logging.getLogger(__name__).error(f"Database error getting statistics: {str(e)}")
            return {
                "total_documents": 0,
                "total_size": 0,
                "document_types": {},
                "recent_documents": 0,
            }
        finally:
            conn.close()
