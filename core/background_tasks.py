"""
Background task processing with Celery for file processing and AI operations.
"""

import asyncio
import logging
import time
from typing import Any

try:
    from celery import Celery
    from celery.result import AsyncResult
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    crontab = None

from core.streaming_processor import StreamingFileProcessor
from core.websocket_handler import get_websocket_handler

logger = logging.getLogger(__name__)

# Celery configuration
if CELERY_AVAILABLE:
    celery_app = Celery('tq_chat')
    celery_app.conf.update(
        broker_url='redis://localhost:6379/0',
        result_backend='redis://localhost:6379/0',
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_disable_rate_limits=False,
        task_default_rate_limit='100/m',
    )


class TaskManager:
    """
    Manages background tasks for file processing and AI operations.
    """

    def __init__(self):
        self.active_tasks: dict[str, Any] = {}
        self.task_status: dict[str, dict[str, Any]] = {}

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get status of a background task."""
        if not CELERY_AVAILABLE:
            return {'status': 'error', 'message': 'Celery not available'}

        if task_id in self.task_status:
            return self.task_status[task_id]

        try:
            result = AsyncResult(task_id, app=celery_app)
            status = {
                'task_id': task_id,
                'status': result.status,
                'progress': 0,
                'message': ''
            }

            if result.state == 'PENDING':
                status['message'] = 'Task is waiting to be processed'
            elif result.state == 'PROGRESS':
                if result.info:
                    status.update(result.info)
            elif result.state == 'SUCCESS':
                status['progress'] = 100
                status['result'] = result.result
            elif result.state == 'FAILURE':
                status['message'] = str(result.info)
                status['error'] = True

            self.task_status[task_id] = status
            return status

        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {'status': 'error', 'message': str(e)}

    async def submit_file_processing_task(
        self,
        file_data: bytes,
        filename: str,
        user_id: str
    ) -> str:
        """Submit file processing task to background queue."""
        if not CELERY_AVAILABLE:
            raise Exception("Celery not available for background processing")

        task = process_file_background.delay(file_data, filename, user_id)
        self.active_tasks[task.id] = {
            'type': 'file_processing',
            'user_id': user_id,
            'filename': filename,
            'started_at': time.time()
        }

        logger.info(f"Submitted file processing task {task.id} for {filename}")
        return task.id

    async def submit_ai_chat_task(
        self,
        message: str,
        provider: str,
        model: str,
        user_id: str,
        context: dict[str, Any] = None
    ) -> str:
        """Submit AI chat task to background queue."""
        if not CELERY_AVAILABLE:
            raise Exception("Celery not available for background processing")

        task = process_ai_chat_background.delay(
            message, provider, model, user_id, context or {}
        )
        self.active_tasks[task.id] = {
            'type': 'ai_chat',
            'user_id': user_id,
            'provider': provider,
            'model': model,
            'started_at': time.time()
        }

        logger.info(f"Submitted AI chat task {task.id} for user {user_id}")
        return task.id

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a background task."""
        if not CELERY_AVAILABLE:
            return False

        try:
            celery_app.control.revoke(task_id, terminate=True)
            self.active_tasks.pop(task_id, None)
            self.task_status.pop(task_id, None)
            logger.info(f"Cancelled task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

    def get_user_tasks(self, user_id: str) -> list[dict[str, Any]]:
        """Get all active tasks for a user."""
        user_tasks = []
        for task_id, task_info in self.active_tasks.items():
            if task_info.get('user_id') == user_id:
                status = self.get_task_status(task_id)
                user_tasks.append({
                    'task_id': task_id,
                    'task_info': task_info,
                    'status': status
                })
        return user_tasks

    def cleanup_completed_tasks(self) -> int:
        """Clean up completed tasks older than 1 hour."""
        cleaned_count = 0
        current_time = time.time()
        task_ids_to_remove = []

        for task_id, task_info in self.active_tasks.items():
            if current_time - task_info.get('started_at', 0) > 3600:  # 1 hour
                status = self.get_task_status(task_id)
                if status.get('status') in ['SUCCESS', 'FAILURE']:
                    task_ids_to_remove.append(task_id)

        for task_id in task_ids_to_remove:
            self.active_tasks.pop(task_id, None)
            self.task_status.pop(task_id, None)
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} completed tasks")

        return cleaned_count


# Global task manager instance
task_manager = TaskManager()


if CELERY_AVAILABLE:
    @celery_app.task(bind=True)
    def process_file_background(self, file_data: bytes, filename: str, user_id: str):
        """
        Background task for file processing.
        """
        try:
            # Update task status
            self.update_state(
                state='PROGRESS',
                meta={'progress': 10, 'message': 'Starting file processing'}
            )

            # Initialize processor
            processor = StreamingFileProcessor()

            # Process file with progress updates
            def progress_callback(progress: int):
                self.update_state(
                    state='PROGRESS',
                    meta={'progress': progress, 'message': f'Processing file: {progress}%'}
                )

            # Determine processing method based on file size
            file_size = len(file_data)
            if file_size > 10 * 1024 * 1024:  # 10MB
                # Use streaming processing for large files
                import io
                file_stream = io.BytesIO(file_data)
                
                # Since we can't use async in Celery task, we need to run in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content = loop.run_until_complete(
                        processor.process_large_file(file_stream, filename, progress_callback)
                    )
                finally:
                    loop.close()
            else:
                # Use regular processing
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    content = loop.run_until_complete(
                        processor._process_regular_file(file_data, filename, progress_callback)
                    )
                finally:
                    loop.close()

            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'progress': 90, 'message': 'Storing processed content'}
            )

            # Store in document store
            from services.file_manager import FileManager
            file_manager = FileManager()
            doc_id = file_manager.add_document(
                filename=filename,
                content=content,
                metadata={'user_id': user_id, 'file_size': file_size}
            )

            # Notify user via WebSocket
            async def notify_user():
                websocket_handler = get_websocket_handler()
                await websocket_handler.notify_file_processing(
                    user_id=user_id,
                    filename=filename,
                    status='complete',
                    progress=100
                )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(notify_user())
            finally:
                loop.close()

            return {
                'filename': filename,
                'content_length': len(content),
                'document_id': doc_id,
                'processing_time': time.time()
            }

        except Exception as error:
            logger.error(f"File processing task failed: {error}")
            error_msg = str(error)
            
            # Notify user of error
            async def notify_error():
                websocket_handler = get_websocket_handler()
                await websocket_handler.notify_file_processing(
                    user_id=user_id,
                    filename=filename,
                    status='error',
                    error=error_msg
                )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(notify_error())
            finally:
                loop.close()

            raise


    @celery_app.task(bind=True)
    def process_ai_chat_background(
        self,
        message: str,
        provider: str,
        model: str,
        user_id: str,
        context: dict[str, Any]
    ):
        """
        Background task for AI chat processing.
        """
        try:
            # Update task status
            self.update_state(
                state='PROGRESS',
                meta={'progress': 10, 'message': 'Initializing AI request'}
            )

            # Import here to avoid circular imports
            from core.optimized_api_client import get_api_client

            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'progress': 30, 'message': 'Sending request to AI provider'}
            )

            # Process AI request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                api_client = loop.run_until_complete(get_api_client())

                # Prepare request data based on provider
                if provider == 'openai':
                    endpoint = "https://api.openai.com/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {context.get('api_key', '')}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": message}],
                        "stream": False
                    }
                elif provider == 'anthropic':
                    endpoint = "https://api.anthropic.com/v1/messages"
                    headers = {
                        "x-api-key": context.get('api_key', ''),
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    }
                    payload = {
                        "model": model,
                        "max_tokens": 4000,
                        "messages": [{"role": "user", "content": message}]
                    }
                else:
                    raise ValueError(f"Unsupported provider: {provider}")

                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={'progress': 60, 'message': 'Processing AI response'}
                )

                # Make API request
                response = loop.run_until_complete(
                    api_client.make_request(
                        method='POST',
                        url=endpoint,
                        headers=headers,
                        json_data=payload
                    )
                )

                # Extract response content
                if provider == 'openai':
                    ai_response = response['choices'][0]['message']['content']
                elif provider == 'anthropic':
                    ai_response = response['content'][0]['text']

                # Update progress
                self.update_state(
                    state='PROGRESS',
                    meta={'progress': 90, 'message': 'Sending response to user'}
                )

                # Send response via WebSocket
                async def send_response():
                    websocket_handler = get_websocket_handler()
                    await websocket_handler.notify_ai_response_stream(
                        user_id=user_id,
                        response_chunk=ai_response,
                        is_complete=True
                    )

                loop.run_until_complete(send_response())

                return {
                    'message': message,
                    'response': ai_response,
                    'provider': provider,
                    'model': model,
                    'processing_time': time.time()
                }

            finally:
                loop.close()

        except Exception as exc:
            logger.error(f"AI chat task failed: {exc}")
            error_msg = str(exc)

            # Notify user of error
            async def notify_error():
                websocket_handler = get_websocket_handler()
                await websocket_handler.send_to_user(user_id, {
                    'type': 'ai_error',
                    'message': error_msg,
                    'timestamp': time.time()
                })

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(notify_error())
            finally:
                loop.close()

            raise


    @celery_app.task
    def cleanup_tasks():
        """Periodic task to clean up completed tasks."""
        cleaned_count = task_manager.cleanup_completed_tasks()
        logger.info(f"Cleanup task completed, removed {cleaned_count} old tasks")
        return cleaned_count


    # Configure periodic task
    if CELERY_AVAILABLE and crontab:
        celery_app.conf.beat_schedule = {
            'cleanup-completed-tasks': {
                'task': 'core.background_tasks.cleanup_tasks',
                'schedule': crontab(minute=0),  # Run every hour
            },
        }

else:
    # Fallback implementations when Celery is not available
    def process_file_background(*args, **kwargs):
        raise NotImplementedError("Celery not available for background processing")

    def process_ai_chat_background(*args, **kwargs):
        raise NotImplementedError("Celery not available for background processing")

    def cleanup_tasks():
        return 0
