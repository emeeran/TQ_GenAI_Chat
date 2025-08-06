"""
Database optimizations including connection pooling, query optimization,
and efficient document storage for the TQ GenAI Chat application.
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue
from typing import Any

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    SQLite connection pool for managing database connections efficiently.
    """

    def __init__(self, database_path: str, pool_size: int = 10):
        self.database_path = database_path
        self.pool_size = pool_size
        self.pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self.active_connections = 0
        self.lock = threading.Lock()
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool."""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            if conn:
                self.pool.put(conn)

    def _create_connection(self) -> sqlite3.Connection | None:
        """Create a new database connection with optimizations."""
        try:
            conn = sqlite3.connect(
                self.database_path,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None,  # Enable autocommit mode
            )

            # Enable SQLite optimizations
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster but still safe
            conn.execute("PRAGMA cache_size=10000")  # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
            conn.execute("PRAGMA optimize")  # Auto-optimize on connection

            # Custom row factory for better performance
            conn.row_factory = sqlite3.Row

            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            # Try to get a connection from the pool
            try:
                conn = self.pool.get(timeout=5.0)
            except Empty:
                # Pool is empty, create a new connection
                with self.lock:
                    if self.active_connections < self.pool_size * 2:
                        conn = self._create_connection()
                        if conn:
                            self.active_connections += 1
                    else:
                        # Wait longer for a connection
                        conn = self.pool.get(timeout=10.0)

            if not conn:
                raise Exception("Could not obtain database connection")

            yield conn

        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool
                    self.pool.put_nowait(conn)
                except:
                    # Pool is full, close the connection
                    conn.close()
                    with self.lock:
                        self.active_connections -= 1

    def close_all(self):
        """Close all connections in the pool."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break
        self.active_connections = 0


class OptimizedDocumentStore:
    """
    Optimized document storage with indexing and caching.
    """

    def __init__(self, database_path: str = "documents.db", redis_url: str = None):
        self.database_path = database_path
        self.pool = ConnectionPool(database_path)
        self.redis_client = None

        # Initialize Redis if available
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis connected for document caching")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None

        self._initialize_database()

    def _initialize_database(self):
        """Initialize database schema with optimizations."""
        with self.pool.get_connection() as conn:
            # Main documents table with optimized schema
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    file_size INTEGER,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    embedding_vector BLOB,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Optimized indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_last_accessed ON documents(last_accessed)"
            )

            # Full-text search table
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    filename, content,
                    content='documents',
                    content_rowid='id'
                )
            """
            )

            # Triggers to keep FTS in sync
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(rowid, filename, content)
                    VALUES (new.id, new.filename, new.content);
                END
            """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, filename, content)
                    VALUES('delete', old.id, old.filename, old.content);
                END
            """
            )

            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, filename, content)
                    VALUES('delete', old.id, old.filename, old.content);
                    INSERT INTO documents_fts(rowid, filename, content)
                    VALUES (new.id, new.filename, new.content);
                END
            """
            )

            # Chat history table with partitioning by date
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time_ms INTEGER,
                    token_count INTEGER,
                    metadata TEXT
                )
            """
            )

            # Chat history indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_history(timestamp)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_provider ON chat_history(provider)"
            )

            logger.info("Database schema initialized with optimizations")

    def add_document(self, filename: str, content: str, metadata: dict = None) -> int:
        """Add a document with deduplication and caching."""
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check cache first
        if self.redis_client:
            cached_id = self.redis_client.get(f"doc_hash:{content_hash}")
            if cached_id:
                logger.info(f"Document with hash {content_hash} found in cache")
                return int(cached_id)

        # Check database for existing document
        with self.pool.get_connection() as conn:
            result = conn.execute(
                "SELECT id FROM documents WHERE content_hash = ?", (content_hash,)
            ).fetchone()

            if result:
                doc_id = result["id"]
                # Update last accessed time
                conn.execute(
                    "UPDATE documents SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                    (doc_id,),
                )

                # Cache the result
                if self.redis_client:
                    self.redis_client.setex(f"doc_hash:{content_hash}", 3600, doc_id)

                logger.info(
                    f"Document with hash {content_hash} already exists with ID {doc_id}"
                )
                return doc_id

            # Insert new document
            cursor = conn.execute(
                """
                INSERT INTO documents (filename, content, content_hash, file_size, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    filename,
                    content,
                    content_hash,
                    len(content),
                    json.dumps(metadata) if metadata else None,
                ),
            )

            doc_id = cursor.lastrowid

            # Cache the new document
            if self.redis_client:
                self.redis_client.setex(f"doc_hash:{content_hash}", 3600, doc_id)
                self.redis_client.setex(
                    f"doc:{doc_id}",
                    1800,
                    json.dumps(
                        {
                            "filename": filename,
                            "content": content[:1000],  # Cache preview only
                            "metadata": metadata,
                        }
                    ),
                )

            logger.info(f"Added new document {filename} with ID {doc_id}")
            return doc_id

    def search_documents(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search documents using full-text search with caching."""
        cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}:{limit}"

        # Check cache first
        if self.redis_client:
            cached_results = self.redis_client.get(cache_key)
            if cached_results:
                return json.loads(cached_results)

        # Perform database search
        with self.pool.get_connection() as conn:
            # Use FTS5 for fast full-text search
            results = conn.execute(
                """
                SELECT d.id, d.filename, d.content, d.upload_date, d.metadata,
                       rank as relevance_score
                FROM documents_fts
                JOIN documents d ON documents_fts.rowid = d.id
                WHERE documents_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """,
                (query, limit),
            ).fetchall()

            # Convert to list of dictionaries
            documents = []
            for row in results:
                doc = {
                    "id": row["id"],
                    "filename": row["filename"],
                    "content": (
                        row["content"][:500] + "..."
                        if len(row["content"]) > 500
                        else row["content"]
                    ),
                    "upload_date": row["upload_date"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "relevance_score": row["relevance_score"],
                }
                documents.append(doc)

            # Cache results
            if self.redis_client:
                self.redis_client.setex(
                    cache_key, 300, json.dumps(documents)
                )  # 5 min cache

            return documents

    def get_document(self, doc_id: int) -> dict[str, Any] | None:
        """Get a document by ID with caching."""
        cache_key = f"doc:{doc_id}"

        # Check cache first
        if self.redis_client:
            cached_doc = self.redis_client.get(cache_key)
            if cached_doc:
                return json.loads(cached_doc)

        # Get from database
        with self.pool.get_connection() as conn:
            result = conn.execute(
                """
                SELECT id, filename, content, upload_date, metadata, file_size
                FROM documents
                WHERE id = ?
            """,
                (doc_id,),
            ).fetchone()

            if not result:
                return None

            document = {
                "id": result["id"],
                "filename": result["filename"],
                "content": result["content"],
                "upload_date": result["upload_date"],
                "metadata": (
                    json.loads(result["metadata"]) if result["metadata"] else {}
                ),
                "file_size": result["file_size"],
            }

            # Update last accessed
            conn.execute(
                "UPDATE documents SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (doc_id,),
            )

            # Cache the document
            if self.redis_client:
                self.redis_client.setex(cache_key, 1800, json.dumps(document))

            return document

    def add_chat_history(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        provider: str,
        model: str,
        response_time_ms: int = None,
        token_count: int = None,
        metadata: dict = None,
    ) -> int:
        """Add chat history entry with optimized insertion."""
        with self.pool.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO chat_history
                (session_id, user_message, ai_response, provider, model,
                 response_time_ms, token_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    user_message,
                    ai_response,
                    provider,
                    model,
                    response_time_ms,
                    token_count,
                    json.dumps(metadata) if metadata else None,
                ),
            )

            return cursor.lastrowid

    def get_chat_history(
        self, session_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get chat history for a session with caching."""
        cache_key = f"chat_history:{session_id}:{limit}"

        # Check cache first
        if self.redis_client:
            cached_history = self.redis_client.get(cache_key)
            if cached_history:
                return json.loads(cached_history)

        # Get from database
        with self.pool.get_connection() as conn:
            results = conn.execute(
                """
                SELECT id, user_message, ai_response, provider, model,
                       timestamp, response_time_ms, token_count, metadata
                FROM chat_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (session_id, limit),
            ).fetchall()

            history = []
            for row in results:
                entry = {
                    "id": row["id"],
                    "user_message": row["user_message"],
                    "ai_response": row["ai_response"],
                    "provider": row["provider"],
                    "model": row["model"],
                    "timestamp": row["timestamp"],
                    "response_time_ms": row["response_time_ms"],
                    "token_count": row["token_count"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                }
                history.append(entry)

            # Cache results
            if self.redis_client:
                self.redis_client.setex(
                    cache_key, 600, json.dumps(history)
                )  # 10 min cache

            return history

    def cleanup_old_data(self, days: int = 30) -> dict[str, int]:
        """Clean up old data to maintain performance."""
        cutoff_date = time.time() - (days * 24 * 60 * 60)

        with self.pool.get_connection() as conn:
            # Clean up old chat history
            chat_deleted = conn.execute(
                """
                DELETE FROM chat_history
                WHERE timestamp < datetime(?, 'unixepoch')
            """,
                (cutoff_date,),
            ).rowcount

            # Clean up unused documents (not accessed in specified days)
            docs_deleted = conn.execute(
                """
                DELETE FROM documents
                WHERE last_accessed < datetime(?, 'unixepoch')
                AND id NOT IN (
                    SELECT DISTINCT d.id
                    FROM documents d
                    JOIN chat_history ch ON ch.metadata LIKE '%"document_id":' || d.id || '%'
                    WHERE ch.timestamp > datetime(?, 'unixepoch')
                )
            """,
                (cutoff_date, cutoff_date),
            ).rowcount

            # Optimize database
            conn.execute("VACUUM")
            conn.execute("ANALYZE")

            # Clear related cache entries
            if self.redis_client:
                # Clear document caches
                for key in self.redis_client.scan_iter(match="doc:*"):
                    self.redis_client.delete(key)
                for key in self.redis_client.scan_iter(match="search:*"):
                    self.redis_client.delete(key)

            logger.info(
                f"Cleanup completed: {chat_deleted} chat entries, {docs_deleted} documents removed"
            )

            return {
                "chat_entries_deleted": chat_deleted,
                "documents_deleted": docs_deleted,
            }

    def get_statistics(self) -> dict[str, Any]:
        """Get database statistics."""
        with self.pool.get_connection() as conn:
            stats = {}

            # Document statistics
            doc_stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_documents,
                    SUM(file_size) as total_size,
                    AVG(file_size) as avg_size,
                    MIN(upload_date) as first_upload,
                    MAX(upload_date) as last_upload
                FROM documents
            """
            ).fetchone()

            stats["documents"] = dict(doc_stats)

            # Chat history statistics
            chat_stats = conn.execute(
                """
                SELECT
                    COUNT(*) as total_chats,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    AVG(response_time_ms) as avg_response_time,
                    MIN(timestamp) as first_chat,
                    MAX(timestamp) as last_chat
                FROM chat_history
            """
            ).fetchone()

            stats["chat_history"] = dict(chat_stats)

            # Provider usage
            provider_stats = conn.execute(
                """
                SELECT provider, COUNT(*) as usage_count
                FROM chat_history
                GROUP BY provider
                ORDER BY usage_count DESC
            """
            ).fetchall()

            stats["provider_usage"] = {
                row["provider"]: row["usage_count"] for row in provider_stats
            }

            # Database size
            db_size = (
                Path(self.database_path).stat().st_size
                if Path(self.database_path).exists()
                else 0
            )
            stats["database_size_bytes"] = db_size

            return stats

    def close(self):
        """Close all database connections."""
        self.pool.close_all()
        if self.redis_client:
            self.redis_client.close()


# Global instance
_document_store = None


def get_document_store(
    database_path: str = "documents.db", redis_url: str = None
) -> OptimizedDocumentStore:
    """Get or create the global document store instance."""
    global _document_store
    if _document_store is None:
        _document_store = OptimizedDocumentStore(database_path, redis_url)
    return _document_store


# Database maintenance functions
async def schedule_maintenance():
    """Schedule regular database maintenance tasks."""
    while True:
        try:
            # Run cleanup every 24 hours
            await asyncio.sleep(24 * 60 * 60)

            store = get_document_store()
            cleanup_results = store.cleanup_old_data(days=30)

            logger.info(f"Scheduled maintenance completed: {cleanup_results}")

        except Exception as e:
            logger.error(f"Maintenance task failed: {e}")
            await asyncio.sleep(60 * 60)  # Retry in 1 hour


def initialize_database_optimizations():
    """Initialize database with performance optimizations."""
    store = get_document_store()
    logger.info("Database optimizations initialized")

    # Start maintenance task
    asyncio.create_task(schedule_maintenance())

    return store
