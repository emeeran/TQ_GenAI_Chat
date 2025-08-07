"""
Object Pooling Implementation - Task 3.2.2
High-performance object pools for frequent allocations including
connection pooling, response objects, and document processing reuse
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

T = TypeVar("T")


class PoolStrategy(Enum):
    """Pool allocation strategies"""

    LIFO = "lifo"  # Last In, First Out (stack-like)
    FIFO = "fifo"  # First In, First Out (queue-like)
    ROUND_ROBIN = "round_robin"  # Distribute evenly


@dataclass
class PoolMetrics:
    """Pool performance and usage metrics"""

    total_created: int = 0
    total_acquired: int = 0
    total_released: int = 0
    total_destroyed: int = 0
    current_size: int = 0
    current_active: int = 0
    peak_size: int = 0
    peak_active: int = 0
    avg_acquisition_time: float = 0.0
    cache_hit_rate: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)


class PoolableObject(ABC):
    """Base class for objects that can be pooled"""

    def __init__(self):
        self._in_pool = False
        self._created_at = datetime.now()
        self._last_used = datetime.now()
        self._use_count = 0

    @abstractmethod
    def reset(self) -> bool:
        """
        Reset object state for reuse.
        Returns True if object can be reused, False if it should be discarded.
        """
        pass

    def is_valid(self) -> bool:
        """Check if object is still valid for use"""
        return True

    def on_acquire(self):
        """Called when object is acquired from pool"""
        self._last_used = datetime.now()
        self._use_count += 1
        self._in_pool = False

    def on_release(self):
        """Called when object is returned to pool"""
        self._in_pool = True


class ObjectPool(Generic[T]):
    """
    Generic object pool with configurable strategies and monitoring
    """

    def __init__(
        self,
        factory: Callable[[], T],
        min_size: int = 2,
        max_size: int = 20,
        max_idle_time: int = 300,  # 5 minutes
        strategy: PoolStrategy = PoolStrategy.LIFO,
        validation_interval: int = 60,  # 1 minute
        enable_metrics: bool = True,
    ):
        self.factory = factory
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.strategy = strategy
        self.validation_interval = validation_interval
        self.enable_metrics = enable_metrics

        # Pool storage
        self._pool: deque = deque()
        self._active: dict[int, T] = {}
        self._lock = threading.RLock()

        # Round robin counter
        self._rr_counter = 0

        # Metrics
        self.metrics = PoolMetrics()
        self._metrics_lock = threading.Lock()

        # Background maintenance
        self._maintenance_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        self.logger = logging.getLogger(__name__)

        # Initialize pool
        self._initialize_pool()
        self._start_maintenance()

    def _initialize_pool(self):
        """Pre-populate pool with minimum objects"""
        with self._lock:
            for _ in range(self.min_size):
                try:
                    obj = self._create_object()
                    self._pool.append(obj)
                except Exception as e:
                    self.logger.error(f"Failed to initialize pool object: {e}")

    def _create_object(self) -> T:
        """Create a new object for the pool"""
        obj = self.factory()

        if self.enable_metrics:
            with self._metrics_lock:
                self.metrics.total_created += 1
                self.metrics.current_size += 1
                self.metrics.peak_size = max(self.metrics.peak_size, self.metrics.current_size)

        return obj

    def _start_maintenance(self):
        """Start background maintenance thread"""
        if self._maintenance_thread is None or not self._maintenance_thread.is_alive():
            self._maintenance_thread = threading.Thread(
                target=self._maintenance_loop, name="ObjectPoolMaintenance", daemon=True
            )
            self._maintenance_thread.start()

    def _maintenance_loop(self):
        """Background thread for pool maintenance"""
        while not self._shutdown_event.is_set():
            try:
                self._validate_objects()
                self._cleanup_idle_objects()
                time.sleep(self.validation_interval)
            except Exception as e:
                self.logger.error(f"Pool maintenance error: {e}")

    def _validate_objects(self):
        """Validate objects in pool and remove invalid ones"""
        with self._lock:
            valid_objects = []

            while self._pool:
                obj = self._pool.popleft()

                # Check if object implements validation
                if hasattr(obj, "is_valid") and not obj.is_valid():
                    self._destroy_object(obj)
                    continue

                # Check idle time
                if hasattr(obj, "_last_used"):
                    idle_time = (datetime.now() - obj._last_used).total_seconds()
                    if idle_time > self.max_idle_time:
                        self._destroy_object(obj)
                        continue

                valid_objects.append(obj)

            # Add valid objects back to pool
            self._pool.extend(valid_objects)

    def _cleanup_idle_objects(self):
        """Remove excess idle objects"""
        with self._lock:
            # Keep at least min_size objects
            excess_count = len(self._pool) - self.min_size

            if excess_count > 0:
                for _ in range(min(excess_count, len(self._pool) - self.min_size)):
                    if self._pool:
                        obj = self._pool.pop()
                        self._destroy_object(obj)

    def _destroy_object(self, obj: T):
        """Destroy an object and update metrics"""
        try:
            if hasattr(obj, "close"):
                obj.close()
            elif hasattr(obj, "cleanup"):
                obj.cleanup()
        except Exception as e:
            self.logger.warning(f"Error destroying object: {e}")

        if self.enable_metrics:
            with self._metrics_lock:
                self.metrics.total_destroyed += 1
                self.metrics.current_size -= 1

    @contextmanager
    def acquire(self, timeout: float = 30.0):
        """
        Context manager to acquire an object from the pool

        Usage:
            with pool.acquire() as obj:
                # use obj
                pass
        """
        start_time = time.time()
        obj = None

        try:
            obj = self._acquire_object(timeout)
            yield obj
        finally:
            if obj is not None:
                self._release_object(obj)

            # Update acquisition time metric
            if self.enable_metrics:
                acquisition_time = time.time() - start_time
                with self._metrics_lock:
                    # Exponential moving average
                    alpha = 0.1
                    self.metrics.avg_acquisition_time = (
                        alpha * acquisition_time + (1 - alpha) * self.metrics.avg_acquisition_time
                    )

    def _acquire_object(self, timeout: float) -> T:
        """Acquire an object from the pool"""
        end_time = time.time() + timeout

        while time.time() < end_time:
            with self._lock:
                # Try to get from pool
                if self._pool:
                    obj = self._get_from_pool()

                    # Validate object
                    if hasattr(obj, "is_valid") and not obj.is_valid():
                        self._destroy_object(obj)
                        continue

                    # Reset object state
                    if hasattr(obj, "reset") and not obj.reset():
                        self._destroy_object(obj)
                        continue

                    # Track active object
                    self._active[id(obj)] = obj

                    # Call acquire callback
                    if hasattr(obj, "on_acquire"):
                        obj.on_acquire()

                    # Update metrics
                    if self.enable_metrics:
                        with self._metrics_lock:
                            self.metrics.total_acquired += 1
                            self.metrics.current_active += 1
                            self.metrics.peak_active = max(
                                self.metrics.peak_active, self.metrics.current_active
                            )
                            # Calculate cache hit rate
                            hit_rate = (
                                self.metrics.total_acquired - self.metrics.total_created
                            ) / max(1, self.metrics.total_acquired)
                            self.metrics.cache_hit_rate = max(0, hit_rate)

                    return obj

                # Create new object if under max size
                elif self.metrics.current_size < self.max_size:
                    try:
                        obj = self._create_object()
                        self._active[id(obj)] = obj

                        if hasattr(obj, "on_acquire"):
                            obj.on_acquire()

                        if self.enable_metrics:
                            with self._metrics_lock:
                                self.metrics.total_acquired += 1
                                self.metrics.current_active += 1
                                self.metrics.peak_active = max(
                                    self.metrics.peak_active, self.metrics.current_active
                                )

                        return obj
                    except Exception as e:
                        self.logger.error(f"Failed to create new object: {e}")

            # Wait a bit before retrying
            time.sleep(0.01)

        raise TimeoutError(f"Could not acquire object within {timeout} seconds")

    def _get_from_pool(self) -> T:
        """Get object from pool based on strategy"""
        if not self._pool:
            raise RuntimeError("Pool is empty")

        if self.strategy == PoolStrategy.LIFO:
            return self._pool.pop()
        elif self.strategy == PoolStrategy.FIFO:
            return self._pool.popleft()
        elif self.strategy == PoolStrategy.ROUND_ROBIN:
            # Simple round-robin (not perfect but good enough)
            index = self._rr_counter % len(self._pool)
            self._rr_counter += 1
            # Convert deque to list temporarily for indexing
            pool_list = list(self._pool)
            obj = pool_list[index]
            self._pool.remove(obj)
            return obj
        else:
            return self._pool.pop()

    def _release_object(self, obj: T):
        """Release an object back to the pool"""
        with self._lock:
            # Remove from active tracking
            obj_id = id(obj)
            if obj_id in self._active:
                del self._active[obj_id]

            # Call release callback
            if hasattr(obj, "on_release"):
                obj.on_release()

            # Add back to pool if space available
            if len(self._pool) < self.max_size:
                self._pool.append(obj)
            else:
                # Pool is full, destroy the object
                self._destroy_object(obj)

            # Update metrics
            if self.enable_metrics:
                with self._metrics_lock:
                    self.metrics.total_released += 1
                    self.metrics.current_active -= 1

    def get_metrics(self) -> PoolMetrics:
        """Get current pool metrics"""
        with self._metrics_lock:
            # Update current metrics
            with self._lock:
                self.metrics.current_size = len(self._pool) + len(self._active)
                self.metrics.current_active = len(self._active)

            return self.metrics

    def reset_metrics(self):
        """Reset pool metrics"""
        with self._metrics_lock:
            self.metrics = PoolMetrics()

    def shutdown(self, timeout: int = 30):
        """Shutdown the pool and cleanup resources"""
        self.logger.info("Shutting down object pool...")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for maintenance thread
        if self._maintenance_thread and self._maintenance_thread.is_alive():
            self._maintenance_thread.join(timeout=timeout)

        # Cleanup all objects
        with self._lock:
            # Destroy pool objects
            while self._pool:
                obj = self._pool.popleft()
                self._destroy_object(obj)

            # Destroy active objects (if possible)
            for obj in list(self._active.values()):
                self._destroy_object(obj)

            self._active.clear()

        self.logger.info("Object pool shutdown complete")


class HTTPConnectionPool(ObjectPool[requests.Session]):
    """Specialized pool for HTTP connections"""

    def __init__(
        self,
        max_size: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        **kwargs,
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize

        super().__init__(factory=self._create_session, max_size=max_size, **kwargs)

    def _create_session(self) -> requests.Session:
        """Create a configured requests session"""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            backoff_factor=self.backoff_factor,
        )

        # Configure adapters with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session


class ResponseObjectPool:
    """Pool for response objects to reduce allocation overhead"""

    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self._pool: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @contextmanager
    def get_response_dict(self):
        """Get a reusable response dictionary"""
        response_dict = None

        with self._lock:
            if self._pool:
                response_dict = self._pool.pop()
            else:
                response_dict = {}

        try:
            # Clear the dict for reuse
            response_dict.clear()
            yield response_dict
        finally:
            # Return to pool if space available
            with self._lock:
                if len(self._pool) < self.max_size:
                    self._pool.append(response_dict)


class DocumentProcessor(PoolableObject):
    """Example poolable document processor"""

    def __init__(self):
        super().__init__()
        self.processed_count = 0
        self.current_document = None
        self.temp_data = {}

    def reset(self) -> bool:
        """Reset processor state for reuse"""
        self.current_document = None
        self.temp_data.clear()

        # Don't reset processed_count to track lifetime usage
        return True

    def is_valid(self) -> bool:
        """Check if processor is still valid"""
        # Example: invalidate after processing too many documents
        return self.processed_count < 1000

    def process_document(self, document: str) -> dict[str, Any]:
        """Process a document (placeholder implementation)"""
        self.current_document = document
        self.processed_count += 1

        # Simulate processing
        result = {
            "length": len(document),
            "words": len(document.split()),
            "processed_at": datetime.now().isoformat(),
            "processor_id": id(self),
        }

        return result


class DocumentProcessorPool(ObjectPool[DocumentProcessor]):
    """Specialized pool for document processors"""

    def __init__(self, **kwargs):
        super().__init__(factory=DocumentProcessor, **kwargs)


# Global pool instances
_http_pool: Optional[HTTPConnectionPool] = None
_response_pool: Optional[ResponseObjectPool] = None
_document_pool: Optional[DocumentProcessorPool] = None


def get_http_pool() -> HTTPConnectionPool:
    """Get the global HTTP connection pool"""
    global _http_pool
    if _http_pool is None:
        _http_pool = HTTPConnectionPool(max_size=20)
    return _http_pool


def get_response_pool() -> ResponseObjectPool:
    """Get the global response object pool"""
    global _response_pool
    if _response_pool is None:
        _response_pool = ResponseObjectPool(max_size=50)
    return _response_pool


def get_document_pool() -> DocumentProcessorPool:
    """Get the global document processor pool"""
    global _document_pool
    if _document_pool is None:
        _document_pool = DocumentProcessorPool(max_size=10)
    return _document_pool


def shutdown_all_pools():
    """Shutdown all global pools"""
    global _http_pool, _response_pool, _document_pool

    if _http_pool:
        _http_pool.shutdown()
        _http_pool = None

    if _document_pool:
        _document_pool.shutdown()
        _document_pool = None

    # Response pool doesn't need explicit shutdown
    _response_pool = None


# Flask integration helpers
def init_object_pools(app):
    """Initialize object pools for Flask app"""
    # Get pools to initialize them
    get_http_pool()
    get_response_pool()
    get_document_pool()

    # Add to app for access
    app.http_pool = get_http_pool()
    app.response_pool = get_response_pool()
    app.document_pool = get_document_pool()

    # Register shutdown handler
    @app.teardown_appcontext
    def cleanup_pools(error):
        # Pools are long-lived, no per-request cleanup needed
        pass

    # Register app shutdown
    import atexit

    atexit.register(shutdown_all_pools)


# Usage examples and decorators
def with_http_session(func):
    """Decorator to automatically use pooled HTTP session"""

    def wrapper(*args, **kwargs):
        pool = get_http_pool()
        with pool.acquire() as session:
            return func(session, *args, **kwargs)

    return wrapper


def with_document_processor(func):
    """Decorator to automatically use pooled document processor"""

    def wrapper(*args, **kwargs):
        pool = get_document_pool()
        with pool.acquire() as processor:
            return func(processor, *args, **kwargs)

    return wrapper


@with_http_session
def make_api_request(session: requests.Session, url: str, **kwargs) -> dict[str, Any]:
    """Example function using pooled HTTP session"""
    response = session.get(url, **kwargs)
    return response.json()


@with_document_processor
def process_document_content(processor: DocumentProcessor, content: str) -> dict[str, Any]:
    """Example function using pooled document processor"""
    return processor.process_document(content)
