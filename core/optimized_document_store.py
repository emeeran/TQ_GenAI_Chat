"""
Optimized Document Store Module - Task 1.1.1
Enhanced document storage with connection pooling, async support, and performance optimizations.
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Optional

from config.settings import BASE_DIR

logger = logging.getLogger(__name__)


@dataclass
class DocumentSearchResult:
    """Document search result with relevance scoring"""

    id: str
    title: str
    content: str
    metadata: dict[str, Any]
    file_path: Optional[str]
    timestamp: int
    type: str
    user_id: Optional[str]
    relevance_score: float = 0.0


class ConnectionPool:
    """SQLite connection pool for improved concurrent access"""

    def __init__(self, db_path: str, pool_size: int = 10):
        """
        Initialize connection pool

        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of connections in pool
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0
        self._initialized = False

        # Initialize database with WAL mode (only once)
        self._initialize_database()

        # Pre-populate pool with initial connections
        for _ in range(min(2, pool_size)):
            self._pool.put(self._create_connection())
            self._created_connections += 1

    def _initialize_database(self):
        """Initialize database settings (WAL mode, etc.) - only called once"""
        if self._initialized:
            return

        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            # Set WAL mode and other settings (only once per database)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
            conn.commit()
            self._initialized = True
        finally:
            conn.close()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection (without WAL mode setup)"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow sharing between threads
            timeout=30.0,  # 30 second timeout
        )

        # Only set connection-specific settings (not WAL mode)
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")

        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        try:
            # Try to get existing connection from pool
            try:
                conn = self._pool.get_nowait()
            except Empty:
                # Pool is empty, create new connection if under limit
                with self._lock:
                    if self._created_connections < self.pool_size:
                        conn = self._create_connection()
                        self._created_connections += 1
                    else:
                        # Wait for connection to become available
                        conn = self._pool.get(timeout=10.0)

            yield conn

        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            # Return connection to pool if it's still valid
            if conn:
                try:
                    # Test connection is still valid
                    conn.execute("SELECT 1")
                    self._pool.put_nowait(conn)
                except (sqlite3.Error, Empty):
                    # Connection is bad or pool is full, close it
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._created_connections -= 1

    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except (Empty, sqlite3.Error):
                break
        self._created_connections = 0


class OptimizedDocumentStore:
    """
    Optimized document store with connection pooling and enhanced performance

    Key improvements over DocumentStore:
    - Connection pooling for concurrent access
    - Optimized queries using indexes from Task 1.1.2
    - Async support integration
    - Enhanced search with relevance scoring
    - Better error handling and timeouts
    """

    def __init__(
        self, db_path: Optional[str] = None, pool_size: int = 10, enable_async: bool = True
    ):
        """
        Initialize optimized document store

        Args:
            db_path: Path to SQLite database file
            pool_size: Connection pool size
            enable_async: Enable async operations support
        """
        self.db_path = db_path or str(BASE_DIR / "documents.db")
        self.pool_size = pool_size
        self.enable_async = enable_async

        # Initialize connection pool
        self.pool = ConnectionPool(self.db_path, pool_size)

        # Initialize async executor if enabled
        if self.enable_async:
            self.executor = ThreadPoolExecutor(
                max_workers=min(pool_size, 8), thread_name_prefix="OptDocStore"
            )

        # Ensure tables exist with optimizations
        self._create_optimized_tables()

        logger.info(f"OptimizedDocumentStore initialized with pool_size={pool_size}")

    def _create_optimized_tables(self):
        """Create database tables with optimizations from Task 1.1.2"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Create documents table (enhanced version)
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
                    last_accessed INTEGER DEFAULT 0,
                    access_count INTEGER DEFAULT 0,
                    content_hash TEXT,
                    size_bytes INTEGER DEFAULT 0
                )
            """
            )

            # Create optimized indexes (from Task 1.1.2)
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_documents_timestamp ON documents(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title)",
                "CREATE INDEX IF NOT EXISTS idx_documents_last_accessed ON documents(last_accessed DESC)",
                # Composite indexes for common query patterns
                "CREATE INDEX IF NOT EXISTS idx_documents_type_timestamp ON documents(type, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_documents_user_type ON documents(user_id, type)",
                "CREATE INDEX IF NOT EXISTS idx_documents_title_type ON documents(title, type)",
                # Full-text search support
                "CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash)",
            ]

            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                except sqlite3.Error as e:
                    logger.warning(f"Index creation warning: {e}")

            # Create document statistics table for caching
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS document_stats (
                    stat_key TEXT PRIMARY KEY,
                    stat_value TEXT NOT NULL,
                    last_updated INTEGER NOT NULL
                )
            """
            )

            conn.commit()
            logger.info("Optimized database schema created/verified")

    def add_document(
        self,
        content: str,
        title: Optional[str] = None,
        file_path: Optional[str] = None,
        doc_type: str = "text",
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Add a document to the store with optimizations

        Args:
            content: Document content
            title: Document title
            file_path: Source file path
            doc_type: Document type
            metadata: Additional metadata
            user_id: User identifier

        Returns:
            Document ID
        """
        if not content:
            raise ValueError("Document content cannot be empty")

        # Generate optimized document metadata
        timestamp = int(time.time())
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        size_bytes = len(content.encode("utf-8"))

        if not title:
            title = content[:50] + ("..." if len(content) > 50 else "")

        # Create unique document ID
        doc_id = f"doc_{content_hash[:16]}_{timestamp}"

        metadata_json = json.dumps(metadata or {})

        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT INTO documents
                    (id, title, content, metadata, file_path, timestamp, type,
                     user_id, last_accessed, access_count, content_hash, size_bytes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        doc_id,
                        title,
                        content,
                        metadata_json,
                        file_path,
                        timestamp,
                        doc_type,
                        user_id,
                        timestamp,
                        1,
                        content_hash,
                        size_bytes,
                    ),
                )

                conn.commit()

                # Invalidate cached statistics
                self._invalidate_stats_cache(conn)

                logger.info(f"Document added: {doc_id} ({size_bytes} bytes)")
                return doc_id

            except sqlite3.IntegrityError as e:
                logger.warning(f"Document already exists or constraint violation: {e}")
                # Return existing document ID if content hash matches
                cursor.execute("SELECT id FROM documents WHERE content_hash = ?", (content_hash,))
                result = cursor.fetchone()
                if result:
                    return result["id"]
                raise

    def search_documents(
        self,
        query: str,
        limit: int = 10,
        doc_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[DocumentSearchResult]:
        """
        Search documents with optimized query and relevance scoring

        Args:
            query: Search query
            limit: Maximum results to return
            doc_type: Filter by document type
            user_id: Filter by user ID

        Returns:
            List of search results with relevance scores
        """
        if not query.strip():
            return []

        # Prepare search terms for ranking
        search_terms = query.lower().split()

        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Build optimized search query using indexes
            base_query = """
                SELECT id, title, content, metadata, file_path, timestamp, type, user_id,
                       last_accessed, access_count
                FROM documents
                WHERE (title LIKE ? OR content LIKE ?)
            """

            params = [f"%{query}%", f"%{query}%"]

            # Add filters using indexed columns
            if doc_type:
                base_query += " AND type = ?"
                params.append(doc_type)

            if user_id:
                base_query += " AND user_id = ?"
                params.append(user_id)

            # Order by relevance (access count and recency)
            base_query += """
                ORDER BY
                    (CASE
                        WHEN title LIKE ? THEN 10
                        WHEN content LIKE ? THEN 5
                        ELSE 1
                    END) * (access_count + 1) *
                    (CASE
                        WHEN timestamp > ? THEN 2
                        ELSE 1
                    END) DESC
                LIMIT ?
            """

            # Add parameters for relevance scoring
            recent_threshold = int(time.time()) - (7 * 24 * 3600)  # 7 days ago
            params.extend([f"%{query}%", f"%{query}%", recent_threshold, limit])

            cursor.execute(base_query, params)
            results = []

            for row in cursor.fetchall():
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(row, search_terms, query)

                # Parse metadata
                try:
                    metadata = json.loads(row["metadata"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    metadata = {}

                result = DocumentSearchResult(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"][:500],  # Truncate for performance
                    metadata=metadata,
                    file_path=row["file_path"],
                    timestamp=row["timestamp"],
                    type=row["type"],
                    user_id=row["user_id"],
                    relevance_score=relevance_score,
                )
                results.append(result)

                # Update access statistics
                self._update_access_stats(conn, row["id"])

            conn.commit()
            return sorted(results, key=lambda x: x.relevance_score, reverse=True)

    def _calculate_relevance_score(
        self, row: sqlite3.Row, search_terms: list[str], query: str
    ) -> float:
        """Calculate relevance score for search result"""
        score = 0.0
        title = row["title"].lower()
        content = row["content"].lower()

        # Title match scoring
        if query.lower() in title:
            score += 10.0

        for term in search_terms:
            if term in title:
                score += 5.0

        # Content match scoring
        if query.lower() in content:
            score += 3.0

        for term in search_terms:
            content_count = content.count(term)
            score += content_count * 0.5

        # Recency bonus
        days_old = (time.time() - row["timestamp"]) / (24 * 3600)
        if days_old < 7:
            score *= 1.5
        elif days_old < 30:
            score *= 1.2

        # Access count bonus
        score *= 1 + row["access_count"] * 0.1

        return score

    def _update_access_stats(self, conn: sqlite3.Connection, doc_id: str):
        """Update document access statistics"""
        cursor = conn.cursor()
        current_time = int(time.time())

        cursor.execute(
            """
            UPDATE documents
            SET last_accessed = ?, access_count = access_count + 1
            WHERE id = ?
        """,
            (current_time, doc_id),
        )

    def get_document(self, doc_id: str) -> Optional[DocumentSearchResult]:
        """Get a specific document by ID"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, title, content, metadata, file_path, timestamp, type, user_id,
                       last_accessed, access_count
                FROM documents
                WHERE id = ?
            """,
                (doc_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Update access statistics
            self._update_access_stats(conn, doc_id)
            conn.commit()

            # Parse metadata
            try:
                metadata = json.loads(row["metadata"] or "{}")
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            return DocumentSearchResult(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                metadata=metadata,
                file_path=row["file_path"],
                timestamp=row["timestamp"],
                type=row["type"],
                user_id=row["user_id"],
                relevance_score=1.0,
            )

    def get_all_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        doc_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[DocumentSearchResult]:
        """Get all documents with pagination and filtering"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Build query with optional filters
            query = "SELECT id, title, content, metadata, file_path, timestamp, type, user_id FROM documents"
            params = []
            conditions = []

            if doc_type:
                conditions.append("type = ?")
                params.append(doc_type)

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            results = []

            for row in cursor.fetchall():
                try:
                    metadata = json.loads(row["metadata"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    metadata = {}

                result = DocumentSearchResult(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"][:200],  # Truncate for listing
                    metadata=metadata,
                    file_path=row["file_path"],
                    timestamp=row["timestamp"],
                    type=row["type"],
                    user_id=row["user_id"],
                    relevance_score=0.0,
                )
                results.append(result)

            return results

    def get_document_statistics(self) -> dict[str, Any]:
        """Get cached document statistics with optimization"""
        cache_key = "document_stats"
        cache_ttl = 300  # 5 minutes

        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Check for cached stats
            cursor.execute(
                """
                SELECT stat_value, last_updated
                FROM document_stats
                WHERE stat_key = ?
            """,
                (cache_key,),
            )

            cached = cursor.fetchone()
            current_time = int(time.time())

            if cached and (current_time - cached["last_updated"]) < cache_ttl:
                try:
                    return json.loads(cached["stat_value"])
                except json.JSONDecodeError:
                    pass

            # Calculate fresh statistics using optimized queries
            stats = {}

            # Total documents
            cursor.execute("SELECT COUNT(*) as total FROM documents")
            stats["total_documents"] = cursor.fetchone()["total"]

            # Documents by type
            cursor.execute(
                """
                SELECT type, COUNT(*) as count
                FROM documents
                GROUP BY type
                ORDER BY count DESC
            """
            )
            stats["by_type"] = {row["type"]: row["count"] for row in cursor.fetchall()}

            # Recent documents (last 7 days)
            week_ago = current_time - (7 * 24 * 3600)
            cursor.execute(
                "SELECT COUNT(*) as recent FROM documents WHERE timestamp > ?", (week_ago,)
            )
            stats["recent_documents"] = cursor.fetchone()["recent"]

            # Storage size
            cursor.execute("SELECT SUM(size_bytes) as total_size FROM documents")
            result = cursor.fetchone()
            stats["total_size_bytes"] = result["total_size"] or 0

            # Most active documents
            cursor.execute(
                """
                SELECT title, access_count
                FROM documents
                WHERE access_count > 0
                ORDER BY access_count DESC
                LIMIT 5
            """
            )
            stats["most_accessed"] = [
                {"title": row["title"], "count": row["access_count"]} for row in cursor.fetchall()
            ]

            # Cache the results
            stats_json = json.dumps(stats)
            cursor.execute(
                """
                INSERT OR REPLACE INTO document_stats (stat_key, stat_value, last_updated)
                VALUES (?, ?, ?)
            """,
                (cache_key, stats_json, current_time),
            )

            conn.commit()
            return stats

    def _invalidate_stats_cache(self, conn: sqlite3.Connection):
        """Invalidate cached statistics"""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM document_stats WHERE stat_key = ?", ("document_stats",))

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            deleted = cursor.rowcount > 0

            if deleted:
                self._invalidate_stats_cache(conn)
                conn.commit()
                logger.info(f"Document deleted: {doc_id}")

            return deleted

    def cleanup_old_documents(self, days_old: int = 365) -> int:
        """Clean up documents older than specified days"""
        cutoff_time = int(time.time()) - (days_old * 24 * 3600)

        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM documents
                WHERE timestamp < ? AND access_count = 0
            """,
                (cutoff_time,),
            )

            deleted_count = cursor.rowcount

            if deleted_count > 0:
                self._invalidate_stats_cache(conn)
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} old documents")

            return deleted_count

    # Async methods for integration with async infrastructure
    async def add_document_async(self, *args, **kwargs) -> str:
        """Async version of add_document"""
        if not self.enable_async:
            return self.add_document(*args, **kwargs)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.add_document, *args, **kwargs)

    async def search_documents_async(self, *args, **kwargs) -> list[DocumentSearchResult]:
        """Async version of search_documents"""
        if not self.enable_async:
            return self.search_documents(*args, **kwargs)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.search_documents, *args, **kwargs)

    async def get_document_statistics_async(self) -> dict[str, Any]:
        """Async version of get_document_statistics"""
        if not self.enable_async:
            return self.get_document_statistics()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.get_document_statistics)

    def close(self):
        """Close the document store and clean up resources"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)

        if hasattr(self, "pool"):
            self.pool.close_all()

        logger.info("OptimizedDocumentStore closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton instance for app-wide use
_optimized_document_store = None
_store_lock = threading.Lock()


def get_optimized_document_store(
    db_path: Optional[str] = None, pool_size: int = 10, force_new: bool = False
) -> OptimizedDocumentStore:
    """
    Get singleton OptimizedDocumentStore instance

    Args:
        db_path: Database path (only used for first initialization)
        pool_size: Connection pool size (only used for first initialization)
        force_new: Force creation of new instance

    Returns:
        OptimizedDocumentStore instance
    """
    global _optimized_document_store

    with _store_lock:
        if _optimized_document_store is None or force_new:
            if _optimized_document_store and force_new:
                _optimized_document_store.close()

            _optimized_document_store = OptimizedDocumentStore(
                db_path=db_path, pool_size=pool_size, enable_async=True
            )

            logger.info("OptimizedDocumentStore singleton created")

        return _optimized_document_store
