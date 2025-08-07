"""
TQ GenAI Chat - Streaming File Processing Integration

Integration module for Task 2.2.1: Streaming File Processing
- Flask endpoint integration
- Progress reporting endpoints
- Status tracking and management
- Error recovery handling

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio
import logging
from typing import Any

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from core.streaming_processor import StreamingConfig, streaming_file_manager

logger = logging.getLogger(__name__)

# Create Flask blueprint for streaming endpoints
streaming_bp = Blueprint("streaming", __name__, url_prefix="/api/streaming")


@streaming_bp.route("/config", methods=["GET"])
def get_streaming_config() -> dict[str, Any]:
    """Get current streaming configuration."""
    config = streaming_file_manager.config
    return jsonify(
        {
            "chunk_size": config.chunk_size,
            "max_file_size": config.max_file_size,
            "max_memory_usage": config.max_memory_usage,
            "retry_attempts": config.retry_attempts,
            "retry_delay": config.retry_delay,
            "enable_checksum": config.enable_checksum,
            "progress_interval": config.progress_interval,
            "error_recovery": config.error_recovery,
        }
    )


@streaming_bp.route("/config", methods=["POST"])
def update_streaming_config() -> dict[str, Any]:
    """Update streaming configuration."""
    try:
        data = request.get_json() or {}

        # Create new config with updated values
        current_config = streaming_file_manager.config
        new_config = StreamingConfig(
            chunk_size=data.get("chunk_size", current_config.chunk_size),
            max_file_size=data.get("max_file_size", current_config.max_file_size),
            max_memory_usage=data.get("max_memory_usage", current_config.max_memory_usage),
            retry_attempts=data.get("retry_attempts", current_config.retry_attempts),
            retry_delay=data.get("retry_delay", current_config.retry_delay),
            enable_checksum=data.get("enable_checksum", current_config.enable_checksum),
            progress_interval=data.get("progress_interval", current_config.progress_interval),
            error_recovery=data.get("error_recovery", current_config.error_recovery),
        )

        # Validate new config
        new_config.validate()

        # Update the global manager
        streaming_file_manager.config = new_config
        streaming_file_manager.streaming_processor.config = new_config

        return jsonify(
            {
                "status": "success",
                "message": "Configuration updated successfully",
                "config": {
                    "chunk_size": new_config.chunk_size,
                    "max_file_size": new_config.max_file_size,
                    "max_memory_usage": new_config.max_memory_usage,
                    "retry_attempts": new_config.retry_attempts,
                    "retry_delay": new_config.retry_delay,
                    "enable_checksum": new_config.enable_checksum,
                    "progress_interval": new_config.progress_interval,
                    "error_recovery": new_config.error_recovery,
                },
            }
        )

    except ValueError as e:
        return jsonify({"status": "error", "message": f"Invalid configuration: {e}"}), 400
    except Exception as e:
        logger.error(f"Config update error: {e}")
        return jsonify({"status": "error", "message": f"Failed to update configuration: {e}"}), 500


@streaming_bp.route("/process", methods=["POST"])
def process_file_streaming() -> dict[str, Any]:
    """Process a file using streaming approach."""
    try:
        # Check if file is present
        if "file" not in request.files:
            raise BadRequest("No file provided")

        file = request.files["file"]
        if not file or not file.filename:
            raise BadRequest("Invalid file")

        # Get processing options
        use_streaming = request.form.get("use_streaming")
        if use_streaming is not None:
            use_streaming = use_streaming.lower() in ("true", "1", "yes")

        # Read file content
        file_content = file.read()
        if len(file_content) == 0:
            raise BadRequest("Empty file")

        # Check file size limits
        config = streaming_file_manager.config
        if len(file_content) > config.max_file_size:
            raise RequestEntityTooLarge(
                f"File size ({len(file_content):,} bytes) exceeds maximum "
                f"allowed size ({config.max_file_size:,} bytes)"
            )

        # Process file asynchronously
        async def process_async():
            return await streaming_file_manager.process_file_optimized(
                file_content, file.filename, use_streaming
            )

        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(process_async())
        finally:
            loop.close()

        return jsonify(
            {
                "status": "success",
                "filename": file.filename,
                "size": len(file_content),
                "processing_method": "streaming" if use_streaming else "standard",
                "content": result[:1000] + "..." if len(result) > 1000 else result,
                "full_length": len(result),
            }
        )

    except (BadRequest, RequestEntityTooLarge) as e:
        return jsonify({"status": "error", "message": str(e)}), e.code
    except Exception as e:
        logger.error(f"File processing error: {e}")
        return jsonify({"status": "error", "message": f"Processing failed: {e}"}), 500


@streaming_bp.route("/status/<filename>", methods=["GET"])
def get_processing_status(filename: str) -> dict[str, Any]:
    """Get processing status for a specific file."""
    try:

        async def get_status_async():
            return await streaming_file_manager.get_processing_status(filename)

        # Run async status check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            status = loop.run_until_complete(get_status_async())
        finally:
            loop.close()

        if status is None:
            return (
                jsonify(
                    {"status": "not_found", "message": f"No processing status found for {filename}"}
                ),
                404,
            )

        return jsonify({"status": "success", "processing_status": status})

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"status": "error", "message": f"Failed to get status: {e}"}), 500


@streaming_bp.route("/active", methods=["GET"])
def list_active_processing() -> dict[str, Any]:
    """List all active processing operations."""
    try:

        async def get_active_async():
            return await streaming_file_manager.list_active_processing()

        # Run async active list
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            active_processes = loop.run_until_complete(get_active_async())
        finally:
            loop.close()

        return jsonify(
            {
                "status": "success",
                "active_processes": active_processes,
                "count": len(active_processes),
            }
        )

    except Exception as e:
        logger.error(f"Active list error: {e}")
        return jsonify({"status": "error", "message": f"Failed to list active processes: {e}"}), 500


@streaming_bp.route("/cancel/<filename>", methods=["POST"])
def cancel_processing(filename: str) -> dict[str, Any]:
    """Cancel an active processing operation."""
    try:

        async def cancel_async():
            return await streaming_file_manager.cancel_processing(filename)

        # Run async cancellation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            cancelled = loop.run_until_complete(cancel_async())
        finally:
            loop.close()

        if not cancelled:
            return (
                jsonify(
                    {"status": "not_found", "message": f"No active processing found for {filename}"}
                ),
                404,
            )

        return jsonify({"status": "success", "message": f"Processing cancelled for {filename}"})

    except Exception as e:
        logger.error(f"Cancellation error: {e}")
        return jsonify({"status": "error", "message": f"Failed to cancel processing: {e}"}), 500


@streaming_bp.route("/statistics", methods=["GET"])
def get_processing_statistics() -> dict[str, Any]:
    """Get comprehensive processing statistics."""
    try:

        async def get_stats_async():
            return await streaming_file_manager.get_statistics()

        # Run async statistics
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            stats = loop.run_until_complete(get_stats_async())
        finally:
            loop.close()

        return jsonify({"status": "success", "statistics": stats})

    except Exception as e:
        logger.error(f"Statistics error: {e}")
        return jsonify({"status": "error", "message": f"Failed to get statistics: {e}"}), 500


@streaming_bp.route("/info", methods=["POST"])
def get_file_info() -> dict[str, Any]:
    """Get file information without processing."""
    try:
        # Check if file is present
        if "file" not in request.files:
            raise BadRequest("No file provided")

        file = request.files["file"]
        if not file or not file.filename:
            raise BadRequest("Invalid file")

        # Read file content
        file_content = file.read()
        if len(file_content) == 0:
            raise BadRequest("Empty file")

        # Get file info asynchronously
        async def get_info_async():
            return await streaming_file_manager.get_file_info(file_content, file.filename)

        # Run async info retrieval
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            info = loop.run_until_complete(get_info_async())
        finally:
            loop.close()

        return jsonify({"status": "success", "file_info": info})

    except (BadRequest, RequestEntityTooLarge) as e:
        return jsonify({"status": "error", "message": str(e)}), e.code
    except Exception as e:
        logger.error(f"File info error: {e}")
        return jsonify({"status": "error", "message": f"Failed to get file info: {e}"}), 500


# Integration functions for app.py
def register_streaming_endpoints(app):
    """Register streaming endpoints with Flask app."""
    app.register_blueprint(streaming_bp)
    logger.info("Streaming file processing endpoints registered")


def setup_streaming_callbacks(app):
    """Setup streaming progress callbacks for WebSocket or SSE."""
    # This would integrate with WebSocket or Server-Sent Events
    # for real-time progress updates

    def progress_callback(filename: str, processed: int, total: int, status: str):
        """Progress callback for real-time updates."""
        # This would send updates via WebSocket/SSE
        # For now, just log progress
        percent = (processed / total * 100) if total > 0 else 0
        logger.info(f"Processing {filename}: {percent:.1f}% ({status})")

    streaming_file_manager.add_progress_callback(progress_callback)
    logger.info("Streaming progress callbacks configured")


# Utility functions for direct integration
async def process_file_content_streaming(
    content: bytes, filename: str, use_streaming: bool | None = None
) -> str:
    """
    Direct function to process file content with streaming.

    Args:
        content: File content as bytes
        filename: Name of the file
        use_streaming: Force streaming mode (None = auto-detect)

    Returns:
        Processed content as string
    """
    return await streaming_file_manager.process_file_optimized(content, filename, use_streaming)


def should_use_streaming_for_file(content: bytes, filename: str) -> bool:
    """
    Determine if streaming should be used for a file.

    Args:
        content: File content
        filename: File name

    Returns:
        True if streaming is recommended
    """
    from core.streaming_processor import should_use_streaming

    return should_use_streaming(len(content), filename)


def get_optimal_processing_config(file_size: int, file_type: str) -> StreamingConfig:
    """
    Get optimal configuration for processing a specific file.

    Args:
        file_size: Size of the file in bytes
        file_type: File extension or type

    Returns:
        Optimized StreamingConfig
    """
    from core.streaming_processor import get_optimal_chunk_size

    chunk_size = get_optimal_chunk_size(file_size, file_type)

    return StreamingConfig(
        chunk_size=chunk_size,
        max_file_size=max(100 * 1024 * 1024, file_size + 10 * 1024 * 1024),  # Add 10MB buffer
        retry_attempts=3 if file_size > 50 * 1024 * 1024 else 2,  # More retries for large files
        error_recovery=True,
        enable_checksum=file_size > 10 * 1024 * 1024,  # Checksum for large files
    )


logger.info("[Streaming Integration] Task 2.2.1 Integration module loaded")
