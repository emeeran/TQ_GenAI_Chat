"""Enhanced context manager for document processing"""

import json
import sqlite3
from typing import Any


class ContextManager:
    """Manages document context and retrieval"""

    def __init__(self, db_path: str = "documents.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize context database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def add_document(
        self, filename: str, content: str, metadata: dict[str, Any] = None
    ):
        """Add document to context"""
        doc_id = self._generate_id()
        metadata = metadata or {}

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO documents (id, filename, content, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (doc_id, filename, content, json.dumps(metadata)),
            )

        return doc_id

    def get_relevant_context(self, query: str, limit: int = 3) -> str | None:
        """Get relevant context for query"""
        with sqlite3.connect(self.db_path) as conn:
            # Simple text search - could be enhanced with vector similarity
            docs = conn.execute(
                """
                SELECT filename, content FROM documents
                WHERE content LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (f"%{query}%", limit),
            ).fetchall()

            if not docs:
                return None

            context_parts = []
            for filename, content in docs:
                # Take first 500 chars of relevant content
                snippet = content[:500] + "..." if len(content) > 500 else content
                context_parts.append(f"From {filename}: {snippet}")

            return "\n\n".join(context_parts)

    def has_context(self) -> bool:
        """Check if any documents are available"""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            return count > 0

    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid

        return str(uuid.uuid4())
