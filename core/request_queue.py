"""
Request Queuing System for TQ GenAI Chat
Implements priority-based request queuing with rate limiting and timeout support
"""

import asyncio
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Request priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class RequestStatus(Enum):
    """Request processing status"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class QueuedRequest:
    """Represents a queued request"""

    request_id: str
    handler: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    timeout: float = 30.0
    max_retries: int = 3
    retry_count: int = 0
    status: RequestStatus = RequestStatus.QUEUED
    result: Any = None
    error: Optional[Exception] = None
    processing_started_at: Optional[float] = None


@dataclass
class RateLimitRule:
    """Rate limiting configuration"""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_allowance: int = 10
    window_size: int = 60  # seconds


class RequestQueue:
    """
    High-performance request queuing system with priority handling,
    rate limiting, and comprehensive monitoring
    """

    def __init__(
        self,
        max_workers: int = 10,
        max_queue_size: int = 1000,
        default_timeout: float = 30.0,
        enable_redis: bool = False,
        redis_config: Optional[dict] = None,
    ):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout

        # Priority queues for different request types
        self.queues: dict[Priority, deque] = {
            Priority.CRITICAL: deque(),
            Priority.HIGH: deque(),
            Priority.NORMAL: deque(),
            Priority.LOW: deque(),
        }

        # Request tracking
        self.requests: dict[str, QueuedRequest] = {}
        self.processing: dict[str, QueuedRequest] = {}

        # Rate limiting
        self.rate_limits: dict[str, RateLimitRule] = {}
        self.user_requests: dict[str, deque] = defaultdict(deque)
        self.ip_requests: dict[str, deque] = defaultdict(deque)

        # Workers and synchronization
        self.workers: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        self.queue_lock = asyncio.Lock()
        self.stats_lock = threading.Lock()

        # Statistics
        self.stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_timeout": 0,
            "avg_processing_time": 0.0,
            "queue_sizes": {p: 0 for p in Priority},
            "worker_utilization": 0.0,
        }

        # Redis support for distributed queuing
        self.redis_client = None
        self.enable_redis = enable_redis
        if enable_redis:
            self.init_redis(redis_config or {})

        # Start background tasks
        self.started = False
        self.background_tasks = []

    def init_redis(self, redis_config: dict):
        """Initialize Redis connection for distributed queuing"""
        try:
            self.redis_client = redis.Redis(
                host=redis_config.get("host", "localhost"),
                port=redis_config.get("port", 6379),
                db=redis_config.get("db", 0),
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
                max_connections=20,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for request queuing")
        except Exception as e:
            logger.warning(f"Redis connection failed, using local queuing: {e}")
            self.redis_client = None
            self.enable_redis = False

    async def start(self):
        """Start the request queue system"""
        if self.started:
            return

        self.started = True
        logger.info(f"Starting request queue with {self.max_workers} workers")

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # Start background maintenance tasks
        cleanup_task = asyncio.create_task(self._cleanup_task())
        stats_task = asyncio.create_task(self._stats_task())
        rate_limit_task = asyncio.create_task(self._rate_limit_cleanup_task())

        self.background_tasks.extend([cleanup_task, stats_task, rate_limit_task])

        logger.info("Request queue system started successfully")

    async def stop(self):
        """Stop the request queue system gracefully"""
        logger.info("Stopping request queue system...")

        self.shutdown_event.set()

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for workers to finish current requests
        await asyncio.gather(*self.workers, *self.background_tasks, return_exceptions=True)

        # Cancel remaining queued requests
        async with self.queue_lock:
            total_cancelled = 0
            for priority_queue in self.queues.values():
                while priority_queue:
                    req = priority_queue.popleft()
                    req.status = RequestStatus.CANCELLED
                    total_cancelled += 1

        logger.info(f"Request queue stopped. Cancelled {total_cancelled} pending requests")
        self.started = False

    def set_rate_limit(self, identifier: str, rule: RateLimitRule):
        """Set rate limiting rule for user or IP"""
        self.rate_limits[identifier] = rule

    def get_default_rate_limit(self) -> RateLimitRule:
        """Get default rate limiting rule"""
        return RateLimitRule(requests_per_minute=60, requests_per_hour=1000, burst_allowance=10)

    async def queue_request(
        self,
        handler: Callable,
        *args,
        priority: Priority = Priority.NORMAL,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs,
    ) -> str:
        """
        Queue a request for processing

        Args:
            handler: Function to execute
            *args: Arguments for the handler
            priority: Request priority level
            user_id: User identifier for rate limiting
            ip_address: IP address for rate limiting
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            **kwargs: Keyword arguments for the handler

        Returns:
            Request ID for tracking

        Raises:
            QueueFullException: When queue is at capacity
            RateLimitExceededException: When rate limit is exceeded
        """

        # Check rate limits
        if user_id:
            await self._check_rate_limit(user_id, "user")
        if ip_address:
            await self._check_rate_limit(ip_address, "ip")

        # Check queue capacity
        total_queued = sum(len(q) for q in self.queues.values())
        if total_queued >= self.max_queue_size:
            raise QueueFullException(f"Queue at capacity: {total_queued}/{self.max_queue_size}")

        # Create request
        request_id = str(uuid.uuid4())
        request = QueuedRequest(
            request_id=request_id,
            handler=handler,
            args=args,
            kwargs=kwargs,
            priority=priority,
            user_id=user_id,
            ip_address=ip_address,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries,
        )

        async with self.queue_lock:
            # Add to appropriate priority queue
            self.queues[priority].append(request)
            self.requests[request_id] = request

            # Update rate limiting tracking
            current_time = time.time()
            if user_id:
                self.user_requests[user_id].append(current_time)
            if ip_address:
                self.ip_requests[ip_address].append(current_time)

            # Update statistics
            with self.stats_lock:
                self.stats["total_queued"] += 1
                self.stats["queue_sizes"][priority] += 1

        logger.debug(f"Queued request {request_id} with priority {priority.name}")
        return request_id

    async def get_request_status(self, request_id: str) -> Optional[dict]:
        """Get request status and details"""
        request = self.requests.get(request_id) or self.processing.get(request_id)
        if not request:
            return None

        return {
            "request_id": request_id,
            "status": request.status.value,
            "priority": request.priority.name,
            "created_at": request.created_at,
            "processing_started_at": request.processing_started_at,
            "timeout": request.timeout,
            "retry_count": request.retry_count,
            "max_retries": request.max_retries,
            "user_id": request.user_id,
            "ip_address": request.ip_address,
            "result": request.result if request.status == RequestStatus.COMPLETED else None,
            "error": str(request.error) if request.error else None,
        }

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a queued or processing request"""
        async with self.queue_lock:
            # Check if request is queued
            for priority, queue in self.queues.items():
                for i, request in enumerate(queue):
                    if request.request_id == request_id:
                        request.status = RequestStatus.CANCELLED
                        del queue[i]
                        del self.requests[request_id]

                        with self.stats_lock:
                            self.stats["total_cancelled"] += 1
                            self.stats["queue_sizes"][priority] -= 1

                        logger.info(f"Cancelled queued request {request_id}")
                        return True

            # Check if request is being processed
            if request_id in self.processing:
                request = self.processing[request_id]
                request.status = RequestStatus.CANCELLED
                logger.info(f"Marked processing request {request_id} for cancellation")
                return True

        return False

    async def wait_for_result(self, request_id: str, timeout: Optional[float] = None) -> Any:
        """Wait for request completion and return result"""
        timeout = timeout or self.default_timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            request = self.requests.get(request_id) or self.processing.get(request_id)
            if not request:
                raise RequestNotFoundException(f"Request {request_id} not found")

            if request.status == RequestStatus.COMPLETED:
                return request.result
            elif request.status == RequestStatus.FAILED:
                raise RequestFailedException(f"Request failed: {request.error}")
            elif request.status == RequestStatus.CANCELLED:
                raise RequestCancelledException(f"Request {request_id} was cancelled")
            elif request.status == RequestStatus.TIMEOUT:
                raise RequestTimeoutException(f"Request {request_id} timed out")

            await asyncio.sleep(0.1)

        raise RequestTimeoutException(f"Timeout waiting for request {request_id}")

    async def get_queue_stats(self) -> dict:
        """Get comprehensive queue statistics"""
        with self.stats_lock:
            stats = self.stats.copy()

        # Add current queue sizes
        async with self.queue_lock:
            total_queued = sum(len(q) for q in self.queues.values())
            for priority in Priority:
                stats["queue_sizes"][priority] = len(self.queues[priority])

            stats["current_queued"] = total_queued
            stats["currently_processing"] = len(self.processing)
            stats["worker_utilization"] = len(self.processing) / self.max_workers

        return stats

    async def get_health_status(self) -> dict:
        """Get system health status"""
        stats = await self.get_queue_stats()

        # Determine health based on various metrics
        health_score = 100
        issues = []

        # Check queue capacity
        queue_utilization = stats["current_queued"] / self.max_queue_size
        if queue_utilization > 0.8:
            health_score -= 30
            issues.append(f"Queue utilization high: {queue_utilization:.1%}")

        # Check worker utilization
        worker_util = stats["worker_utilization"]
        if worker_util > 0.9:
            health_score -= 20
            issues.append(f"Worker utilization high: {worker_util:.1%}")

        # Check error rates
        total_requests = stats["total_processed"] + stats["total_failed"]
        if total_requests > 0:
            error_rate = stats["total_failed"] / total_requests
            if error_rate > 0.1:
                health_score -= 25
                issues.append(f"Error rate high: {error_rate:.1%}")

        # Check Redis connectivity
        if self.enable_redis and not self._check_redis_health():
            health_score -= 15
            issues.append("Redis connection issues")

        status = (
            "healthy" if health_score > 80 else "degraded" if health_score > 50 else "unhealthy"
        )

        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "redis_enabled": self.enable_redis,
            "redis_healthy": self._check_redis_health() if self.enable_redis else None,
            **stats,
        }

    # Private methods

    async def _worker(self, worker_name: str):
        """Worker coroutine that processes queued requests"""
        logger.debug(f"Worker {worker_name} started")

        while not self.shutdown_event.is_set():
            try:
                # Get next request from priority queues
                request = await self._get_next_request()
                if not request:
                    await asyncio.sleep(0.1)
                    continue

                # Move to processing
                async with self.queue_lock:
                    self.processing[request.request_id] = request
                    request.status = RequestStatus.PROCESSING
                    request.processing_started_at = time.time()

                # Process request
                await self._process_request(request, worker_name)

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}", exc_info=True)

        logger.debug(f"Worker {worker_name} stopped")

    async def _get_next_request(self) -> Optional[QueuedRequest]:
        """Get the next highest priority request from queues"""
        async with self.queue_lock:
            # Check priority queues in order
            for priority in [Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
                if self.queues[priority]:
                    request = self.queues[priority].popleft()

                    with self.stats_lock:
                        self.stats["queue_sizes"][priority] -= 1

                    return request

            return None

    async def _process_request(self, request: QueuedRequest, worker_name: str):
        """Process a single request"""
        start_time = time.time()

        try:
            # Check for cancellation
            if request.status == RequestStatus.CANCELLED:
                return

            # Execute handler with timeout
            if asyncio.iscoroutinefunction(request.handler):
                result = await asyncio.wait_for(
                    request.handler(*request.args, **request.kwargs), timeout=request.timeout
                )
            else:
                # Run sync function in thread pool
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: request.handler(*request.args, **request.kwargs)
                    ),
                    timeout=request.timeout,
                )

            request.result = result
            request.status = RequestStatus.COMPLETED

            processing_time = time.time() - start_time

            with self.stats_lock:
                self.stats["total_processed"] += 1
                # Update rolling average processing time
                prev_avg = self.stats["avg_processing_time"]
                total_processed = self.stats["total_processed"]
                self.stats["avg_processing_time"] = (
                    prev_avg * (total_processed - 1) + processing_time
                ) / total_processed

            logger.debug(
                f"Request {request.request_id} completed in {processing_time:.2f}s by {worker_name}"
            )

        except asyncio.TimeoutError:
            request.status = RequestStatus.TIMEOUT
            request.error = Exception(f"Request timeout after {request.timeout}s")

            with self.stats_lock:
                self.stats["total_timeout"] += 1

            logger.warning(f"Request {request.request_id} timed out after {request.timeout}s")

        except asyncio.CancelledError:
            request.status = RequestStatus.CANCELLED
            logger.debug(f"Request {request.request_id} cancelled during processing")

        except Exception as e:
            request.error = e

            # Retry logic
            if request.retry_count < request.max_retries:
                request.retry_count += 1
                request.status = RequestStatus.QUEUED

                # Re-queue with exponential backoff
                await asyncio.sleep(2**request.retry_count)
                async with self.queue_lock:
                    self.queues[request.priority].append(request)

                logger.info(
                    f"Retrying request {request.request_id} (attempt {request.retry_count + 1})"
                )
                return
            else:
                request.status = RequestStatus.FAILED

                with self.stats_lock:
                    self.stats["total_failed"] += 1

                logger.error(f"Request {request.request_id} failed: {e}", exc_info=True)

        finally:
            # Remove from processing
            async with self.queue_lock:
                self.processing.pop(request.request_id, None)

    async def _check_rate_limit(self, identifier: str, limit_type: str):
        """Check if request exceeds rate limits"""
        rule = self.rate_limits.get(identifier) or self.get_default_rate_limit()
        current_time = time.time()

        requests_deque = (
            self.user_requests[identifier] if limit_type == "user" else self.ip_requests[identifier]
        )

        # Clean old requests outside the window
        while requests_deque and current_time - requests_deque[0] > 3600:  # 1 hour
            requests_deque.popleft()

        # Check hourly limit
        requests_last_hour = len(requests_deque)
        if requests_last_hour >= rule.requests_per_hour:
            raise RateLimitExceededException(f"Hourly rate limit exceeded for {identifier}")

        # Check minute limit
        requests_last_minute = sum(
            1 for req_time in requests_deque if current_time - req_time <= 60
        )
        if requests_last_minute >= rule.requests_per_minute:
            raise RateLimitExceededException(f"Per-minute rate limit exceeded for {identifier}")

    async def _cleanup_task(self):
        """Background task to clean up completed requests"""
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                cleanup_age = 300  # 5 minutes

                async with self.queue_lock:
                    to_remove = []
                    for request_id, request in self.requests.items():
                        if (
                            request.status
                            in [
                                RequestStatus.COMPLETED,
                                RequestStatus.FAILED,
                                RequestStatus.CANCELLED,
                                RequestStatus.TIMEOUT,
                            ]
                            and current_time - request.created_at > cleanup_age
                        ):
                            to_remove.append(request_id)

                    for request_id in to_remove:
                        self.requests.pop(request_id, None)
                        logger.debug(f"Cleaned up old request {request_id}")

                await asyncio.sleep(60)  # Clean up every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(60)

    async def _stats_task(self):
        """Background task to update statistics"""
        while not self.shutdown_event.is_set():
            try:
                # Log periodic statistics
                stats = await self.get_queue_stats()
                logger.info(
                    f"Queue stats - Queued: {stats['current_queued']}, "
                    f"Processing: {stats['currently_processing']}, "
                    f"Processed: {stats['total_processed']}, "
                    f"Failed: {stats['total_failed']}, "
                    f"Worker utilization: {stats['worker_utilization']:.1%}"
                )

                await asyncio.sleep(300)  # Log every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats task error: {e}")
                await asyncio.sleep(300)

    async def _rate_limit_cleanup_task(self):
        """Background task to clean up old rate limiting data"""
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()

                # Clean user requests
                for user_id, requests_deque in self.user_requests.items():
                    while requests_deque and current_time - requests_deque[0] > 3600:
                        requests_deque.popleft()

                # Clean IP requests
                for ip, requests_deque in self.ip_requests.items():
                    while requests_deque and current_time - requests_deque[0] > 3600:
                        requests_deque.popleft()

                await asyncio.sleep(600)  # Clean up every 10 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limit cleanup error: {e}")
                await asyncio.sleep(600)

    def _check_redis_health(self) -> bool:
        """Check Redis connectivity"""
        if not self.redis_client:
            return False

        try:
            self.redis_client.ping()
            return True
        except:
            return False


# Exception classes
class QueueException(Exception):
    """Base exception for queue-related errors"""

    pass


class QueueFullException(QueueException):
    """Raised when queue is at capacity"""

    pass


class RateLimitExceededException(QueueException):
    """Raised when rate limit is exceeded"""

    pass


class RequestNotFoundException(QueueException):
    """Raised when request is not found"""

    pass


class RequestFailedException(QueueException):
    """Raised when request processing fails"""

    pass


class RequestCancelledException(QueueException):
    """Raised when request is cancelled"""

    pass


class RequestTimeoutException(QueueException):
    """Raised when request times out"""

    pass


# Global queue instance
_request_queue: Optional[RequestQueue] = None


def get_request_queue() -> RequestQueue:
    """Get the global request queue instance"""
    global _request_queue
    if _request_queue is None:
        raise RuntimeError("Request queue not initialized. Call init_request_queue() first.")
    return _request_queue


def init_request_queue(**kwargs) -> RequestQueue:
    """Initialize the global request queue"""
    global _request_queue
    _request_queue = RequestQueue(**kwargs)
    return _request_queue
