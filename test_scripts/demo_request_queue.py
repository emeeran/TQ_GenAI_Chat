"""
Request Queue Integration Demo
Demonstrates how to integrate the request queue system into the TQ GenAI Chat app
"""

import asyncio
import logging

from flask import Flask, jsonify, request

from core.queue_integration import init_queue_integration, queue_request
from core.request_queue import Priority

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_demo_app():
    """Create a demo Flask app with request queue integration"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "demo-secret-key"

    # Initialize request queue with reasonable defaults
    init_queue_integration(
        app,
        max_workers=5,
        max_queue_size=100,
        default_timeout=30.0,
        enable_redis=False,  # Set to True if Redis is available
    )

    # Demo endpoints showing how to integrate with existing chat functionality

    @app.route("/demo/chat", methods=["POST"])
    async def demo_chat():
        """Demo endpoint showing queued chat processing"""
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "Message required"}), 400

        # Example: Queue a chat request with high priority for premium users
        user_id = data.get("user_id", "anonymous")
        is_premium = data.get("is_premium", False)
        priority = Priority.HIGH if is_premium else Priority.NORMAL

        try:
            # This would integrate with your existing chat processing
            queue = init_queue_integration.queue  # Get queue instance
            request_id = await queue.queue_request(
                process_chat_message,
                data["message"],
                priority=priority,
                user_id=user_id,
                ip_address=request.remote_addr,
                timeout=30.0,
                provider=data.get("provider", "openai"),
                model=data.get("model", "gpt-4o-mini"),
            )

            return jsonify(
                {
                    "request_id": request_id,
                    "message": "Chat request queued",
                    "priority": priority.name,
                    "estimated_wait": "Processing...",
                }
            )

        except Exception as e:
            logger.error(f"Error queuing chat request: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/demo/file-upload", methods=["POST"])
    async def demo_file_upload():
        """Demo endpoint showing queued file processing"""
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400

        try:
            # Queue file processing with normal priority
            queue = init_queue_integration.queue
            request_id = await queue.queue_request(
                process_uploaded_file,
                file.filename,
                file.read(),
                priority=Priority.NORMAL,
                user_id=request.form.get("user_id", "anonymous"),
                ip_address=request.remote_addr,
                timeout=120.0,  # Longer timeout for file processing
            )

            return jsonify(
                {
                    "request_id": request_id,
                    "message": "File upload queued for processing",
                    "filename": file.filename,
                }
            )

        except Exception as e:
            logger.error(f"Error queuing file upload: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/demo/batch-export", methods=["POST"])
    async def demo_batch_export():
        """Demo endpoint showing queued batch operations"""
        data = request.get_json()
        if not data or "chat_ids" not in data:
            return jsonify({"error": "Chat IDs required"}), 400

        try:
            # Queue export with low priority (background task)
            queue = init_queue_integration.queue
            request_id = await queue.queue_request(
                export_chat_history,
                data["chat_ids"],
                priority=Priority.LOW,
                user_id=data.get("user_id", "anonymous"),
                ip_address=request.remote_addr,
                timeout=300.0,  # 5 minute timeout
                export_format=data.get("format", "json"),
            )

            return jsonify(
                {
                    "request_id": request_id,
                    "message": "Export queued for processing",
                    "chat_count": len(data["chat_ids"]),
                }
            )

        except Exception as e:
            logger.error(f"Error queuing export: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/demo/status")
    def demo_status():
        """Demo endpoint showing application status"""
        try:
            # This endpoint is synchronous, just returns current state
            return jsonify(
                {
                    "status": "running",
                    "queue_enabled": True,
                    "demo_endpoints": [
                        "/demo/chat",
                        "/demo/file-upload",
                        "/demo/batch-export",
                        "/api/queue/health",
                        "/api/queue/stats",
                    ],
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


# Example request handlers that would integrate with existing TQ GenAI Chat functionality


async def process_chat_message(
    message: str, provider: str = "openai", model: str = "gpt-4o-mini"
) -> dict:
    """
    Example chat processing handler
    This would integrate with your existing chat processing logic from app.py
    """
    # Simulate chat processing time
    await asyncio.sleep(1.0)

    logger.info(f"Processing chat message with {provider}/{model}")

    # This would call your actual chat processing logic
    # Example integration with existing code:
    # from your_app import process_chat_request
    # result = await process_chat_request({
    #     'message': message,
    #     'provider': provider,
    #     'model': model
    # })

    return {
        "response": f"Processed message: '{message[:50]}...' using {provider}/{model}",
        "provider": provider,
        "model": model,
        "tokens_used": 150,  # Example
        "processing_time": 1.0,
    }


async def process_uploaded_file(filename: str, file_content: bytes) -> dict:
    """
    Example file processing handler
    This would integrate with your existing file processing from services/
    """
    # Simulate file processing time
    await asyncio.sleep(2.0)

    logger.info(f"Processing uploaded file: {filename}")

    # This would call your actual file processing logic
    # Example integration:
    # from services.file_manager import FileManager
    # from core.file_processor import FileProcessor
    #
    # result = await FileProcessor.process_file(file_content, filename)
    # file_manager.add_document(filename, result)

    return {
        "filename": filename,
        "size": len(file_content),
        "processed": True,
        "document_id": f"doc_{hash(filename)}",
        "content_type": "text/plain",  # Would be detected
    }


async def export_chat_history(chat_ids: list, export_format: str = "json") -> dict:
    """
    Example batch export handler
    This would integrate with your existing export functionality
    """
    # Simulate export processing time
    await asyncio.sleep(5.0)

    logger.info(f"Exporting {len(chat_ids)} chats in {export_format} format")

    # This would call your actual export logic
    # Example integration:
    # from your_export_module import export_chats
    # export_path = await export_chats(chat_ids, export_format)

    return {
        "chat_ids": chat_ids,
        "format": export_format,
        "export_url": f"/downloads/export_{hash(str(chat_ids))}.{export_format}",
        "file_size": len(chat_ids) * 1024,  # Simulated size
        "created_at": "2025-01-06T22:30:00Z",
    }


# Example of using the queue decorator for automatic queuing
@queue_request(priority=Priority.HIGH, timeout=60.0)
async def priority_task(data: dict) -> dict:
    """Example of a function that's automatically queued"""
    await asyncio.sleep(1.0)
    return {"processed": data, "timestamp": "2025-01-06T22:30:00Z"}


if __name__ == "__main__":
    # Create and run the demo app
    app = create_demo_app()

    print("Starting Request Queue Integration Demo")
    print("Available endpoints:")
    print("  POST /demo/chat - Queue chat message processing")
    print("  POST /demo/file-upload - Queue file processing")
    print("  POST /demo/batch-export - Queue batch export")
    print("  GET  /demo/status - Application status")
    print("  GET  /api/queue/health - Queue health status")
    print("  GET  /api/queue/stats - Queue statistics")
    print("  GET  /api/queue/workers - Worker status")

    app.run(host="0.0.0.0", port=5001, debug=True)
