"""
Document Store Module
Handles document storage, retrieval, and management with SQLite backend.
"""

import hashlib
import json
import sqlite3
import time
from typing import Any

from flask import current_app

from config.settings import BASE_DIR


class DocumentStore:
    """SQLite-based document storage system with caching and indexing"""

    def __init__(self, db_path: str | None = None):
        """
        Initialize the document store

        Args:
            db_path: Path to SQLite database file, defaults to BASE_DIR/documents.db
        """
        self.db_path = db_path or str(BASE_DIR / "documents.db")
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

        # Generate document ID based on content and timestamp
        timestamp = int(time.time())
        if not title:
            # Generate title from content (first 50 chars or less)
            title = content[:50] + ("..." if len(content) > 50 else "")

        # Create unique document ID
        doc_hash = hashlib.md5(
            f"{content[:1000]}{timestamp}".encode(), usedforsecurity=False
        ).hexdigest()  # nosec B324
        doc_id = f"doc_{doc_hash}"

        metadata_json = json.dumps(metadata or {})

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
                    doc_id,
                    title,
                    content,
                    metadata_json,
                    file_path,
                    timestamp,
                    user_id,
                ),
            )
            conn.commit()

            # Process document into chunks
            self._process_chunks(doc_id, content, metadata or {})

            return doc_id

        except sqlite3.Error as e:
            conn.rollback()
            current_app.logger.error(f"Database error adding document: {str(e)}")
            raise
        finally:
            conn.close()

    def _process_chunks(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any],
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> None:
        """
        Process document into overlapping chunks for better retrieval

        Args:
            doc_id: Document ID
            content: Document content
            metadata: Document metadata
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
        """
        if len(content) <= chunk_size:
            # Document is smaller than chunk size, store as single chunk
            chunk_id = f"{doc_id}_chunk_0"
            self._add_chunk(chunk_id, doc_id, content, 0, metadata)
            return

        # Split into overlapping chunks
        chunks = []
        for i in range(0, len(content), chunk_size - overlap):
            chunk_content = content[i : i + chunk_size]
            if chunk_content:
                chunk_index = len(chunks)
                chunk_id = f"{doc_id}_chunk_{chunk_index}"
                chunks.append((chunk_id, doc_id, chunk_content, chunk_index, metadata))

        # Bulk insert chunks
        conn = self._get_connection()
        conn.cursor()

        try:
            for chunk_id, doc_id, chunk_content, chunk_index, metadata in chunks:
                self._add_chunk(chunk_id, doc_id, chunk_content, chunk_index, metadata)
        except sqlite3.Error as e:
            conn.rollback()
            current_app.logger.error(f"Database error processing chunks: {str(e)}")
            raise
        finally:
            conn.close()

    def _add_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        content: str,
        chunk_index: int,
        metadata: dict[str, Any],
    ) -> None:
        """Add a document chunk to the database"""
        metadata_json = json.dumps(metadata)

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO chunks
                (id, document_id, content, chunk_index, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chunk_id, doc_id, content, chunk_index, metadata_json),
            )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            current_app.logger.error(f"Database error adding chunk: {str(e)}")
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
            current_app.logger.error(f"Database error retrieving document: {str(e)}")
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
            current_app.logger.error(f"Database error searching documents: {str(e)}")
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
            current_app.logger.error(f"Database error deleting document: {str(e)}")
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
            current_app.logger.error(f"Database error retrieving recent documents: {str(e)}")
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
            current_app.logger.error(f"Database error getting statistics: {str(e)}")
            return {
                "total_documents": 0,
                "total_size": 0,
                "document_types": {},
                "recent_documents": 0,
            }
        finally:
            conn.close()
