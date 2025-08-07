"""
Progressive Document Indexing - Task 2.2.3
Background indexing pipeline for documents with incremental updates and health monitoring
"""

import concurrent.futures
import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Empty, PriorityQueue
from typing import Any, Optional


class IndexPriority(Enum):
    """Priority levels for indexing operations"""

    CRITICAL = 1  # New uploads, user-requested
    HIGH = 2  # Recently accessed documents
    NORMAL = 3  # Regular maintenance
    LOW = 4  # Background optimization


class IndexStatus(Enum):
    """Status of indexing operations"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REINDEXING = "reindexing"


@dataclass
class IndexTask:
    """Represents a document indexing task"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    document_path: str = ""
    priority: IndexPriority = IndexPriority.NORMAL
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: IndexStatus = IndexStatus.PENDING
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    progress: float = 0.0

    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value


@dataclass
class IndexHealth:
    """Health metrics for the indexing system"""

    total_documents: int = 0
    indexed_documents: int = 0
    pending_tasks: int = 0
    failed_tasks: int = 0
    processing_tasks: int = 0
    avg_processing_time: float = 0.0
    error_rate: float = 0.0
    last_health_check: datetime = field(default_factory=datetime.now)
    index_freshness_score: float = 100.0  # 0-100 score


class ProgressiveDocumentIndexer:
    """
    Progressive document indexing system with background processing,
    incremental updates, and health monitoring
    """

    def __init__(self, db_path: str = "progressive_index.db", max_workers: int = 4):
        self.db_path = db_path
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)

        # Threading and async
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = PriorityQueue()
        self.processing_tasks: dict[str, IndexTask] = {}
        self.completed_tasks: dict[str, IndexTask] = {}
        self.failed_tasks: dict[str, IndexTask] = {}

        # Control flags
        self.running = False
        self.worker_threads: list[threading.Thread] = []
        self.health_monitor_thread: Optional[threading.Thread] = None

        # Performance tracking
        self.performance_metrics = {
            "total_processed": 0,
            "total_time": 0.0,
            "avg_time_per_doc": 0.0,
            "errors": 0,
            "retries": 0,
            "cache_hits": 0,
        }

        # Index state tracking
        self.document_index: dict[str, dict] = {}  # document_id -> index_info
        self.content_hashes: dict[str, str] = {}  # document_id -> content_hash
        self.last_indexed: dict[str, datetime] = {}  # document_id -> timestamp

        # Health monitoring
        self.health_check_interval = 300  # 5 minutes
        self.health_metrics: IndexHealth = IndexHealth()

        # Initialize database
        self.init_database()
        self.load_existing_index()

    def init_database(self):
        """Initialize the progressive indexing database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS index_tasks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        document_path TEXT,
                        priority INTEGER,
                        content_hash TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        status TEXT,
                        error_message TEXT,
                        retry_count INTEGER,
                        progress REAL
                    )
                """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_index (
                        document_id TEXT PRIMARY KEY,
                        content_hash TEXT,
                        last_indexed TIMESTAMP,
                        index_data TEXT,
                        metadata TEXT,
                        access_count INTEGER DEFAULT 0,
                        last_accessed TIMESTAMP
                    )
                """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS health_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_documents INTEGER,
                        indexed_documents INTEGER,
                        pending_tasks INTEGER,
                        failed_tasks INTEGER,
                        processing_tasks INTEGER,
                        avg_processing_time REAL,
                        error_rate REAL,
                        index_freshness_score REAL
                    )
                """
                )

                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON index_tasks(status)")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_priority ON index_tasks(priority)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_document_hash ON document_index(content_hash)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_document_accessed ON document_index(last_accessed)"
                )

                conn.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise

    def load_existing_index(self):
        """Load existing index data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load document index
                cursor = conn.execute(
                    """
                    SELECT document_id, content_hash, last_indexed, index_data, access_count
                    FROM document_index
                """
                )

                for row in cursor.fetchall():
                    doc_id, content_hash, last_indexed, index_data, access_count = row
                    self.content_hashes[doc_id] = content_hash
                    self.last_indexed[doc_id] = (
                        datetime.fromisoformat(last_indexed) if last_indexed else None
                    )

                    if index_data:
                        self.document_index[doc_id] = json.loads(index_data)

                # Load pending tasks
                cursor = conn.execute(
                    """
                    SELECT * FROM index_tasks
                    WHERE status IN ('pending', 'processing')
                    ORDER BY priority, created_at
                """
                )

                for row in cursor.fetchall():
                    task = self._row_to_task(row)
                    if task.status == IndexStatus.PROCESSING:
                        # Reset processing tasks to pending on startup
                        task.status = IndexStatus.PENDING
                    self.task_queue.put(task)

                self.logger.info(
                    f"Loaded {len(self.document_index)} documents and {self.task_queue.qsize()} pending tasks"
                )

        except sqlite3.Error as e:
            self.logger.error(f"Error loading existing index: {e}")

    def start(self):
        """Start the progressive indexing system"""
        if self.running:
            return

        self.running = True

        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop, name=f"IndexWorker-{i}", daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)

        # Start health monitor
        self.health_monitor_thread = threading.Thread(
            target=self._health_monitor_loop, name="IndexHealthMonitor", daemon=True
        )
        self.health_monitor_thread.start()

        self.logger.info(f"Started progressive indexer with {self.max_workers} workers")

    def stop(self):
        """Stop the progressive indexing system"""
        self.running = False

        # Wait for workers to finish current tasks
        for worker in self.worker_threads:
            if worker.is_alive():
                worker.join(timeout=10)

        if self.health_monitor_thread and self.health_monitor_thread.is_alive():
            self.health_monitor_thread.join(timeout=5)

        self.executor.shutdown(wait=True)
        self.logger.info("Progressive indexer stopped")

    def submit_document(
        self,
        document_id: str,
        document_path: str,
        priority: IndexPriority = IndexPriority.NORMAL,
        metadata: Optional[dict] = None,
    ) -> str:
        """Submit a document for indexing"""

        # Calculate content hash
        content_hash = self._calculate_content_hash(document_path)

        # Check if document needs reindexing
        if not self._needs_indexing(document_id, content_hash):
            self.logger.debug(f"Document {document_id} already indexed with current hash")
            self.performance_metrics["cache_hits"] += 1
            return None

        # Create indexing task
        task = IndexTask(
            document_id=document_id,
            document_path=document_path,
            priority=priority,
            content_hash=content_hash,
            metadata=metadata or {},
        )

        # Add to queue
        self.task_queue.put(task)

        # Persist to database
        self._save_task_to_db(task)

        self.logger.info(f"Submitted document {document_id} for {priority.name} priority indexing")
        return task.id

    def reindex_document(
        self, document_id: str, priority: IndexPriority = IndexPriority.HIGH
    ) -> str:
        """Force reindexing of a document"""

        if document_id not in self.content_hashes:
            raise ValueError(f"Document {document_id} not found in index")

        # Find original document path (this would need to be stored or passed)
        document_path = self._get_document_path(document_id)

        task = IndexTask(
            document_id=document_id,
            document_path=document_path,
            priority=priority,
            content_hash=self._calculate_content_hash(document_path),
            status=IndexStatus.REINDEXING,
            metadata={"force_reindex": True},
        )

        self.task_queue.put(task)
        self._save_task_to_db(task)

        self.logger.info(f"Submitted document {document_id} for reindexing")
        return task.id

    def get_task_status(self, task_id: str) -> Optional[IndexTask]:
        """Get the status of an indexing task"""

        # Check active tasks first
        if task_id in self.processing_tasks:
            return self.processing_tasks[task_id]

        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]

        if task_id in self.failed_tasks:
            return self.failed_tasks[task_id]

        # Check database
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM index_tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_task(row)
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving task status: {e}")

        return None

    def get_document_index_info(self, document_id: str) -> Optional[dict]:
        """Get indexing information for a document"""
        return self.document_index.get(document_id)

    def get_health_metrics(self) -> IndexHealth:
        """Get current health metrics"""
        self._update_health_metrics()
        return self.health_metrics

    def get_queue_stats(self) -> dict[str, int]:
        """Get current queue statistics"""
        return {
            "pending": self.task_queue.qsize(),
            "processing": len(self.processing_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "total_processed": self.performance_metrics["total_processed"],
        }

    def cleanup_old_tasks(self, older_than_days: int = 30):
        """Clean up old completed tasks from database"""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM index_tasks
                    WHERE status IN ('completed', 'failed')
                    AND completed_at < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                self.logger.info(f"Cleaned up {deleted_count} old tasks")

        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up old tasks: {e}")

    # Private methods

    def _worker_loop(self):
        """Main worker loop for processing indexing tasks"""
        while self.running:
            try:
                # Get task with timeout
                try:
                    task = self.task_queue.get(timeout=1.0)
                except Empty:
                    continue

                # Process the task
                self._process_task(task)

            except Exception as e:
                self.logger.error(f"Worker error: {e}")

    def _process_task(self, task: IndexTask):
        """Process a single indexing task"""

        # Mark as processing
        task.status = IndexStatus.PROCESSING
        task.started_at = datetime.now()
        self.processing_tasks[task.id] = task
        self._update_task_in_db(task)

        try:
            self.logger.info(f"Processing task {task.id} for document {task.document_id}")

            # Perform the actual indexing
            index_result = self._index_document(task)

            # Store results
            self._store_index_result(task, index_result)

            # Mark as completed
            task.status = IndexStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0

            # Move to completed tasks
            del self.processing_tasks[task.id]
            self.completed_tasks[task.id] = task

            # Update performance metrics
            processing_time = (task.completed_at - task.started_at).total_seconds()
            self.performance_metrics["total_processed"] += 1
            self.performance_metrics["total_time"] += processing_time
            self.performance_metrics["avg_time_per_doc"] = (
                self.performance_metrics["total_time"] / self.performance_metrics["total_processed"]
            )

            self.logger.info(f"Completed indexing task {task.id} in {processing_time:.2f}s")

        except Exception as e:
            self._handle_task_error(task, str(e))

        finally:
            self._update_task_in_db(task)

    def _index_document(self, task: IndexTask) -> dict[str, Any]:
        """Perform the actual document indexing"""

        # This would integrate with existing document processing systems
        # For now, we'll simulate the indexing process

        document_path = task.document_path

        # Update progress
        task.progress = 10.0

        # Read document content (simulate)
        # In real implementation, this would use existing file processors
        content = self._read_document_content(document_path)
        task.progress = 30.0

        # Extract features/embeddings (simulate)
        features = self._extract_features(content)
        task.progress = 60.0

        # Build search index (simulate)
        search_index = self._build_search_index(content, features)
        task.progress = 90.0

        # Create final index result
        index_result = {
            "content_hash": task.content_hash,
            "content_length": len(content) if content else 0,
            "features": features,
            "search_index": search_index,
            "indexed_at": datetime.now().isoformat(),
            "indexer_version": "1.0.0",
            "metadata": task.metadata,
        }

        task.progress = 100.0
        return index_result

    def _read_document_content(self, document_path: str) -> str:
        """Read document content (placeholder implementation)"""
        try:
            # This would integrate with existing file processors
            # For now, just read as text if possible
            with open(document_path, encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            self.logger.warning(f"Could not read document {document_path}: {e}")
            return ""

    def _extract_features(self, content: str) -> dict[str, Any]:
        """Extract features from document content (placeholder)"""
        if not content:
            return {}

        # Simulate feature extraction
        return {
            "word_count": len(content.split()),
            "char_count": len(content),
            "line_count": len(content.split("\n")),
            "language": "en",  # Would be detected
            "key_terms": content.split()[:10],  # First 10 words as key terms
        }

    def _build_search_index(self, content: str, features: dict) -> dict[str, Any]:
        """Build search index (placeholder)"""
        if not content:
            return {}

        # Simulate building a search index
        words = content.lower().split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        return {
            "word_frequencies": word_freq,
            "total_words": len(words),
            "unique_words": len(word_freq),
            "tf_idf_ready": True,
        }

    def _store_index_result(self, task: IndexTask, index_result: dict[str, Any]):
        """Store indexing results in the database"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update or insert document index
                conn.execute(
                    """
                    INSERT OR REPLACE INTO document_index
                    (document_id, content_hash, last_indexed, index_data, metadata, access_count, last_accessed)
                    VALUES (?, ?, ?, ?, ?, COALESCE((SELECT access_count FROM document_index WHERE document_id = ?), 0), ?)
                """,
                    (
                        task.document_id,
                        task.content_hash,
                        datetime.now().isoformat(),
                        json.dumps(index_result),
                        json.dumps(task.metadata),
                        task.document_id,
                        datetime.now().isoformat(),
                    ),
                )

                conn.commit()

                # Update in-memory structures
                self.document_index[task.document_id] = index_result
                self.content_hashes[task.document_id] = task.content_hash
                self.last_indexed[task.document_id] = datetime.now()

        except sqlite3.Error as e:
            self.logger.error(f"Error storing index result: {e}")
            raise

    def _handle_task_error(self, task: IndexTask, error_message: str):
        """Handle task processing errors"""

        task.error_message = error_message
        task.retry_count += 1

        if task.retry_count <= task.max_retries:
            # Retry with lower priority
            task.status = IndexStatus.PENDING
            task.priority = IndexPriority.LOW
            self.task_queue.put(task)
            self.performance_metrics["retries"] += 1
            self.logger.warning(
                f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries}): {error_message}"
            )
        else:
            # Mark as failed
            task.status = IndexStatus.FAILED
            task.completed_at = datetime.now()

            # Move to failed tasks
            if task.id in self.processing_tasks:
                del self.processing_tasks[task.id]
            self.failed_tasks[task.id] = task

            self.performance_metrics["errors"] += 1
            self.logger.error(
                f"Task {task.id} failed permanently after {task.max_retries} retries: {error_message}"
            )

    def _needs_indexing(self, document_id: str, content_hash: str) -> bool:
        """Check if a document needs indexing"""

        # Not indexed yet
        if document_id not in self.content_hashes:
            return True

        # Content changed
        if self.content_hashes[document_id] != content_hash:
            return True

        # Check if index is too old (optional freshness check)
        if document_id in self.last_indexed:
            age = datetime.now() - self.last_indexed[document_id]
            if age > timedelta(days=30):  # Reindex monthly
                return True

        return False

    def _calculate_content_hash(self, document_path: str) -> str:
        """Calculate hash of document content"""
        try:
            with open(document_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not hash document {document_path}: {e}")
            return str(time.time())  # Fallback to timestamp

    def _get_document_path(self, document_id: str) -> str:
        """Get document path from document ID (placeholder)"""
        # This would integrate with the existing document storage system
        return f"uploads/{document_id}"

    def _health_monitor_loop(self):
        """Health monitoring loop"""
        while self.running:
            try:
                self._update_health_metrics()
                self._save_health_metrics()
                time.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")

    def _update_health_metrics(self):
        """Update health metrics"""

        total_docs = len(self.document_index)
        indexed_docs = len([d for d in self.document_index.values() if d])

        self.health_metrics.total_documents = total_docs
        self.health_metrics.indexed_documents = indexed_docs
        self.health_metrics.pending_tasks = self.task_queue.qsize()
        self.health_metrics.processing_tasks = len(self.processing_tasks)
        self.health_metrics.failed_tasks = len(self.failed_tasks)
        self.health_metrics.avg_processing_time = self.performance_metrics["avg_time_per_doc"]

        # Calculate error rate
        total_processed = self.performance_metrics["total_processed"]
        if total_processed > 0:
            self.health_metrics.error_rate = (
                self.performance_metrics["errors"] / total_processed
            ) * 100

        # Calculate index freshness score
        if total_docs > 0:
            fresh_docs = sum(
                1
                for doc_id in self.last_indexed
                if (datetime.now() - self.last_indexed[doc_id]).days < 7
            )
            self.health_metrics.index_freshness_score = (fresh_docs / total_docs) * 100

        self.health_metrics.last_health_check = datetime.now()

    def _save_health_metrics(self):
        """Save health metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO health_metrics
                    (total_documents, indexed_documents, pending_tasks, failed_tasks,
                     processing_tasks, avg_processing_time, error_rate, index_freshness_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.health_metrics.total_documents,
                        self.health_metrics.indexed_documents,
                        self.health_metrics.pending_tasks,
                        self.health_metrics.failed_tasks,
                        self.health_metrics.processing_tasks,
                        self.health_metrics.avg_processing_time,
                        self.health_metrics.error_rate,
                        self.health_metrics.index_freshness_score,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error saving health metrics: {e}")

    def _save_task_to_db(self, task: IndexTask):
        """Save task to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO index_tasks
                    (id, document_id, document_path, priority, content_hash, metadata,
                     created_at, started_at, completed_at, status, error_message, retry_count, progress)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        task.id,
                        task.document_id,
                        task.document_path,
                        task.priority.value,
                        task.content_hash,
                        json.dumps(task.metadata),
                        task.created_at.isoformat(),
                        task.started_at.isoformat() if task.started_at else None,
                        task.completed_at.isoformat() if task.completed_at else None,
                        task.status.value,
                        task.error_message,
                        task.retry_count,
                        task.progress,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Error saving task to DB: {e}")

    def _update_task_in_db(self, task: IndexTask):
        """Update existing task in database"""
        self._save_task_to_db(task)

    def _row_to_task(self, row) -> IndexTask:
        """Convert database row to IndexTask object"""
        return IndexTask(
            id=row[0],
            document_id=row[1],
            document_path=row[2] or "",
            priority=IndexPriority(row[3]) if row[3] else IndexPriority.NORMAL,
            content_hash=row[4] or "",
            metadata=json.loads(row[5]) if row[5] else {},
            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            started_at=datetime.fromisoformat(row[7]) if row[7] else None,
            completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            status=IndexStatus(row[9]) if row[9] else IndexStatus.PENDING,
            error_message=row[10] or "",
            retry_count=row[11] if row[11] is not None else 0,
            progress=row[12] if row[12] is not None else 0.0,
        )


# Global indexer instance
progressive_indexer = None


def get_progressive_indexer(
    db_path: str = "progressive_index.db", max_workers: int = 4
) -> ProgressiveDocumentIndexer:
    """Get or create the global progressive indexer"""
    global progressive_indexer
    if progressive_indexer is None:
        progressive_indexer = ProgressiveDocumentIndexer(db_path, max_workers)
        progressive_indexer.start()
    return progressive_indexer


# Flask integration helper functions
def init_progressive_indexing(app, db_path: str = None, max_workers: int = 4):
    """Initialize progressive indexing for Flask app"""
    if db_path is None:
        db_path = app.config.get("PROGRESSIVE_INDEX_DB", "progressive_index.db")

    indexer = get_progressive_indexer(db_path, max_workers)
    app.progressive_indexer = indexer
    return indexer


def shutdown_progressive_indexing():
    """Shutdown the progressive indexer"""
    global progressive_indexer
    if progressive_indexer:
        progressive_indexer.stop()
        progressive_indexer = None
