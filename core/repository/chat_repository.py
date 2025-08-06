"""Chat history repository implementation"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from .base import BaseRepository


class ChatHistoryRepository(BaseRepository):
    """Repository for chat history management"""

    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    model TEXT,
                    provider TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                )
            """
            )

    def save(self, data: dict[str, Any]) -> str:
        """Save chat session"""
        session_id = data.get("id", self._generate_id())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO chat_sessions
                (id, title, metadata, updated_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    session_id,
                    data.get("title", "New Chat"),
                    json.dumps(data.get("metadata", {})),
                    datetime.now(),
                ),
            )

        return session_id

    def save_message(self, session_id: str, message: dict[str, Any]) -> str:
        """Save individual message"""
        message_id = self._generate_id()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_messages
                (id, session_id, role, content, model, provider)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    message_id,
                    session_id,
                    message["role"],
                    message["content"],
                    message.get("model", ""),
                    message.get("provider", ""),
                ),
            )

        return message_id

    def find_by_id(self, session_id: str) -> dict[str, Any] | None:
        """Find chat session by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get session
            session = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if not session:
                return None

            # Get messages
            messages = conn.execute(
                """
                SELECT role, content, model, provider, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at
            """,
                (session_id,),
            ).fetchall()

            return {
                "id": session["id"],
                "title": session["title"],
                "created_at": session["created_at"],
                "updated_at": session["updated_at"],
                "metadata": json.loads(session["metadata"]),
                "messages": [dict(msg) for msg in messages],
            }

    def find_all(self) -> list[dict[str, Any]]:
        """Find all chat sessions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sessions = conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
            """
            ).fetchall()

            return [dict(session) for session in sessions]

    def delete(self, session_id: str) -> bool:
        """Delete chat session and its messages"""
        with sqlite3.connect(self.db_path) as conn:
            # Delete messages first
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            # Delete session
            result = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return result.rowcount > 0

    def _generate_id(self) -> str:
        """Generate unique ID"""
        import uuid

        return str(uuid.uuid4())
