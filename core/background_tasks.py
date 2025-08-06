"""Background task processing system"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackgroundTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Callable | None = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: float = 0.0


class BackgroundTaskManager:
    """High-performance background task processing"""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.tasks: dict[str, BackgroundTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.workers: list[asyncio.Task] = []
        self.running = False
        self.logger = logging.getLogger(__name__)

    async def start(self):
        """Start background task processing"""
        if self.running:
            return

        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker-{i}")) for i in range(self.max_workers)
        ]
        self.logger.info(f"Started {self.max_workers} background workers")

    async def stop(self):
        """Stop background task processing"""
        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        self.logger.info("Stopped all background workers")

    def get_status(self) -> dict:
        """Get the current status of the task manager"""
        return {
            "running": self.running,
            "workers": len(self.workers),
            "queue_size": (self.task_queue.qsize() if hasattr(self.task_queue, "qsize") else 0),
            "total_tasks": len(self.tasks),
        }

    async def submit_task(self, name: str, func: Callable, *args, **kwargs) -> str:
        """Submit a task for background processing"""
        task = BackgroundTask(name=name, func=func, args=args, kwargs=kwargs)

        self.tasks[task.id] = task
        await self.task_queue.put(task)

        self.logger.info(f"Submitted task: {name} ({task.id})")
        return task.id

    def get_task_status(self, task_id: str) -> BackgroundTask | None:
        """Get task status by ID"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[BackgroundTask]:
        """Get all tasks"""
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> list[BackgroundTask]:
        """Get tasks by status"""
        return [task for task in self.tasks.values() if task.status == status]

    async def _worker(self, worker_name: str):
        """Background worker process"""
        self.logger.info(f"Worker {worker_name} started")

        while self.running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                await self._execute_task(task, worker_name)

            except TimeoutError:
                # No tasks available, continue
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_name} error: {e}")

        self.logger.info(f"Worker {worker_name} stopped")

    async def _execute_task(self, task: BackgroundTask, worker_name: str):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        self.logger.info(f"Worker {worker_name} executing task: {task.name} ({task.id})")

        try:
            if asyncio.iscoroutinefunction(task.func):
                # Async function
                task.result = await task.func(*task.args, **task.kwargs)
            else:
                # Sync function - run in thread pool
                loop = asyncio.get_event_loop()
                task.result = await loop.run_in_executor(
                    None, lambda: task.func(*task.args, **task.kwargs)
                )

            task.status = TaskStatus.COMPLETED
            task.progress = 100.0

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.logger.error(f"Task {task.name} ({task.id}) failed: {e}")

        task.completed_at = datetime.now()

        # Clean up old completed tasks (keep last 100)
        await self._cleanup_old_tasks()

    async def _cleanup_old_tasks(self):
        """Clean up old completed tasks"""
        completed_tasks = self.get_tasks_by_status(TaskStatus.COMPLETED)
        failed_tasks = self.get_tasks_by_status(TaskStatus.FAILED)

        all_finished = completed_tasks + failed_tasks
        all_finished.sort(key=lambda t: t.completed_at or datetime.now(), reverse=True)

        # Keep only last 100 finished tasks
        if len(all_finished) > 100:
            tasks_to_remove = all_finished[100:]
            for task in tasks_to_remove:
                if task.id in self.tasks:
                    del self.tasks[task.id]


# Global task manager instance
task_manager = BackgroundTaskManager()


async def submit_background_task(name: str, func: Callable, *args, **kwargs) -> str:
    """Submit a background task"""
    return await task_manager.submit_task(name, func, *args, **kwargs)


def get_task_status(task_id: str) -> BackgroundTask | None:
    """Get task status"""
    return task_manager.get_task_status(task_id)
