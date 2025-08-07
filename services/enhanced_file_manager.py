"""
Enhanced File Manager - Task 1.1.3
Optimized file management service using CachedDocumentStore with query result caching.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from werkzeug.utils import secure_filename

from config.settings import ALLOWED_EXTENSIONS, EXPORT_DIR, SAVE_DIR, UPLOAD_DIR
from core.cached_document_store import CachedDocumentStore, create_cached_document_store

logger = logging.getLogger(__name__)


class EnhancedFileManager:
    """
    Enhanced file management with cached document store

    Features:
    - Cached document search and retrieval
    - File upload and processing
    - Chat history management
    - Export functionality
    - Performance monitoring with cache metrics
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize enhanced file manager with caching

        Args:
            redis_url: Redis connection URL for caching
        """
        self.redis_url = redis_url
        self._document_store: Optional[CachedDocumentStore] = None

        # Create necessary directories
        for directory in [UPLOAD_DIR, SAVE_DIR, EXPORT_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

        # Usage stats
        self.file_upload_count = 0
        self.search_count = 0
        self.error_count = 0

    async def initialize(self) -> bool:
        """Initialize the file manager and document store"""
        try:
            self._document_store = await create_cached_document_store(redis_url=self.redis_url)
            logger.info("Enhanced file manager with caching initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize file manager: {e}")
            return False

    @property
    def document_store(self) -> Optional[CachedDocumentStore]:
        """Get document store instance"""
        return self._document_store

    # Document operations (enhanced with caching)

    async def add_document(
        self,
        filename: str,
        content: str,
        doc_type: str = "text",
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Add a document to the document store

        Args:
            filename: Document filename/title
            content: Document content
            doc_type: Document type
            metadata: Additional metadata
            user_id: User identifier

        Returns:
            Document ID
        """
        try:
            return self._document_store.add_document(
                content=content,
                title=filename,
                doc_type=doc_type,
                metadata=metadata,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Error adding document {filename}: {e}")
            raise

    def get_document(self, filename: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a document by filename (backward compatibility)

        Args:
            filename: Document filename/title

        Returns:
            Document data or None
        """
        try:
            # Search by title for backward compatibility
            results = self._document_store.search_documents(query=filename, limit=1)

            if results:
                result = results[0]
                # Convert to format expected by existing code
                return {
                    "id": result.id,
                    "title": result.title,
                    "content": result.content,
                    "metadata": result.metadata,
                    "file_path": result.file_path,
                    "timestamp": result.timestamp,
                    "type": result.type,
                    "user_id": result.user_id,
                }

            return None

        except Exception as e:
            logger.error(f"Error retrieving document {filename}: {e}")
            return None

    def search_documents(
        self, query: str, limit: int = 10, doc_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Search documents with enhanced relevance scoring

        Args:
            query: Search query
            limit: Maximum results
            doc_type: Filter by document type

        Returns:
            List of document dictionaries
        """
        try:
            results = self._document_store.search_documents(
                query=query, limit=limit, doc_type=doc_type
            )

            # Convert to format expected by existing code
            return [
                {
                    "id": result.id,
                    "title": result.title,
                    "content": result.content,
                    "metadata": result.metadata,
                    "file_path": result.file_path,
                    "timestamp": result.timestamp,
                    "type": result.type,
                    "user_id": result.user_id,
                    "relevance_score": result.relevance_score,
                }
                for result in results
            ]

        except Exception as e:
            logger.error(f"Error searching documents with query '{query}': {e}")
            return []

    def get_all_documents(
        self, limit: int = 50, offset: int = 0, doc_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Get all documents with pagination

        Args:
            limit: Maximum results per page
            offset: Results offset
            doc_type: Filter by document type

        Returns:
            List of document dictionaries
        """
        try:
            results = self._document_store.get_all_documents(
                limit=limit, offset=offset, doc_type=doc_type
            )

            # Convert to format expected by existing code
            return [
                {
                    "id": result.id,
                    "title": result.title,
                    "content": result.content,
                    "metadata": result.metadata,
                    "file_path": result.file_path,
                    "timestamp": result.timestamp,
                    "type": result.type,
                    "user_id": result.user_id,
                }
                for result in results
            ]

        except Exception as e:
            logger.error(f"Error getting all documents: {e}")
            return []

    def get_document_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive document statistics

        Returns:
            Statistics dictionary
        """
        try:
            return self._document_store.get_document_statistics()
        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            # Return default stats for backward compatibility
            return {
                "total_documents": 0,
                "by_type": {},
                "recent_documents": 0,
                "total_size_bytes": 0,
                "most_accessed": [],
            }

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID

        Args:
            doc_id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            return self._document_store.delete_document(doc_id)
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    # File system operations (preserved for backward compatibility)

    def save_file(self, file, filename: str) -> str:
        """
        Save uploaded file to filesystem

        Args:
            file: File object from request
            filename: Target filename

        Returns:
            Saved file path
        """
        try:
            filename = secure_filename(filename)
            filepath = UPLOAD_DIR / filename

            # Ensure upload directory exists
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

            file.save(str(filepath))
            logger.info(f"File saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving file {filename}: {e}")
            raise

    def get_file_info(self, filename: str) -> Optional[dict[str, Any]]:
        """
        Get file information from filesystem

        Args:
            filename: Filename to check

        Returns:
            File info dictionary or None
        """
        try:
            filepath = UPLOAD_DIR / secure_filename(filename)

            if not filepath.exists():
                return None

            stat = filepath.stat()
            return {
                "filename": filename,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(filepath),
            }

        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {e}")
            return None

    def list_files(self, directory: str = "uploads") -> list[str]:
        """
        List files in a directory

        Args:
            directory: Directory name ("uploads", "exports", "saves")

        Returns:
            List of filenames
        """
        try:
            if directory == "uploads":
                dir_path = UPLOAD_DIR
            elif directory == "exports":
                dir_path = EXPORT_DIR
            elif directory == "saves":
                dir_path = SAVE_DIR
            else:
                logger.warning(f"Unknown directory: {directory}")
                return []

            if not dir_path.exists():
                return []

            return [f.name for f in dir_path.iterdir() if f.is_file()]

        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []

    def delete_file(self, filename: str, directory: str = "uploads") -> bool:
        """
        Delete a file from filesystem

        Args:
            filename: Filename to delete
            directory: Directory name

        Returns:
            True if deleted, False otherwise
        """
        try:
            filename = secure_filename(filename)

            if directory == "uploads":
                filepath = UPLOAD_DIR / filename
            elif directory == "exports":
                filepath = EXPORT_DIR / filename
            elif directory == "saves":
                filepath = SAVE_DIR / filename
            else:
                logger.warning(f"Unknown directory: {directory}")
                return False

            if filepath.exists():
                filepath.unlink()
                logger.info(f"File deleted: {filepath}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False

    # Chat operations (enhanced)

    def save_chat_history(self, chat_data: dict[str, Any]) -> str:
        """
        Save chat history with enhanced metadata

        Args:
            chat_data: Chat history data

        Returns:
            Saved file path
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chat_id = chat_data.get("id", f"chat_{timestamp}")
            filename = f"chat_{chat_id}_{timestamp}.json"

            # Ensure saves directory exists
            SAVE_DIR.mkdir(parents=True, exist_ok=True)

            filepath = SAVE_DIR / filename

            # Add metadata
            enhanced_data = {
                "id": chat_id,
                "timestamp": timestamp,
                "saved_at": datetime.now().isoformat(),
                "message_count": len(chat_data.get("history", [])),
                "providers_used": list(
                    set(
                        msg.get("provider", "unknown")
                        for msg in chat_data.get("history", [])
                        if isinstance(msg, dict)
                    )
                ),
                **chat_data,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False)

            # Also save to document store for searchability
            content = json.dumps(chat_data.get("history", []), indent=2)
            self.add_document(
                filename=f"Chat: {chat_id}",
                content=content,
                doc_type="chat",
                metadata={
                    "chat_id": chat_id,
                    "message_count": enhanced_data["message_count"],
                    "providers_used": enhanced_data["providers_used"],
                    "file_path": str(filepath),
                },
            )

            logger.info(f"Chat history saved: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
            raise

    def get_saved_chats(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get list of saved chat histories

        Args:
            limit: Maximum number of chats to return

        Returns:
            List of chat metadata
        """
        try:
            chats = []

            if SAVE_DIR.exists():
                # Get from filesystem
                for filepath in sorted(
                    SAVE_DIR.glob("chat_*.json"), key=lambda x: x.stat().st_mtime, reverse=True
                ):
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            data = json.load(f)

                        chats.append(
                            {
                                "id": data.get("id", filepath.stem),
                                "filename": filepath.name,
                                "timestamp": data.get("timestamp", ""),
                                "saved_at": data.get("saved_at", ""),
                                "message_count": data.get("message_count", 0),
                                "providers_used": data.get("providers_used", []),
                                "path": str(filepath),
                            }
                        )

                        if len(chats) >= limit:
                            break

                    except Exception as e:
                        logger.warning(f"Error reading chat file {filepath}: {e}")
                        continue

            return chats

        except Exception as e:
            logger.error(f"Error getting saved chats: {e}")
            return []

    def export_chat(self, chat_data: dict[str, Any], export_format: str = "md") -> str:
        """
        Export chat history in specified format

        Args:
            chat_data: Chat history data
            export_format: Export format ("md", "txt", "json")

        Returns:
            Exported file path
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_export_{timestamp}.{export_format}"

            # Ensure exports directory exists
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)

            filepath = EXPORT_DIR / filename

            if export_format.lower() == "md":
                content = self._export_to_markdown(chat_data)
            elif export_format.lower() == "txt":
                content = self._export_to_text(chat_data)
            elif export_format.lower() == "json":
                content = json.dumps(chat_data, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Chat exported: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error exporting chat: {e}")
            raise

    def _export_to_markdown(self, chat_data: dict[str, Any]) -> str:
        """Convert chat data to Markdown format"""
        content = [f"# Chat Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]

        history = chat_data.get("history", [])
        for i, message in enumerate(history, 1):
            if isinstance(message, dict):
                role = message.get("role", "unknown")
                text = message.get("content", message.get("text", ""))
                provider = message.get("provider", "")

                if role == "user":
                    content.append(f"## Message {i} - User\n\n{text}\n")
                elif role == "assistant":
                    provider_info = f" ({provider})" if provider else ""
                    content.append(f"## Message {i} - Assistant{provider_info}\n\n{text}\n")
                else:
                    content.append(f"## Message {i} - {role.title()}\n\n{text}\n")

        return "\n".join(content)

    def _export_to_text(self, chat_data: dict[str, Any]) -> str:
        """Convert chat data to plain text format"""
        content = [f"Chat Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
        content.append("=" * 50 + "\n")

        history = chat_data.get("history", [])
        for i, message in enumerate(history, 1):
            if isinstance(message, dict):
                role = message.get("role", "unknown")
                text = message.get("content", message.get("text", ""))
                provider = message.get("provider", "")

                if role == "user":
                    content.append(f"[{i}] User:\n{text}\n")
                elif role == "assistant":
                    provider_info = f" ({provider})" if provider else ""
                    content.append(f"[{i}] Assistant{provider_info}:\n{text}\n")
                else:
                    content.append(f"[{i}] {role.title()}:\n{text}\n")

                content.append("-" * 30 + "\n")

        return "\n".join(content)

    # Properties for backward compatibility

    @property
    def total_documents(self) -> int:
        """Get total document count (backward compatibility)"""
        try:
            stats = self.get_document_statistics()
            return stats.get("total_documents", 0)
        except Exception:
            return 0

    # Async methods (for integration with async infrastructure)

    async def add_document_async(self, *args, **kwargs) -> str:
        """Async version of add_document"""
        return await self._document_store.add_document_async(*args, **kwargs)

    async def search_documents_async(self, *args, **kwargs) -> list[dict[str, Any]]:
        """Async version of search_documents"""
        results = await self._document_store.search_documents_async(*args, **kwargs)

        # Convert to expected format
        return [
            {
                "id": result.id,
                "title": result.title,
                "content": result.content,
                "metadata": result.metadata,
                "file_path": result.file_path,
                "timestamp": result.timestamp,
                "type": result.type,
                "user_id": result.user_id,
                "relevance_score": result.relevance_score,
            }
            for result in results
        ]

    async def get_document_statistics_async(self) -> dict[str, Any]:
        """Async version of get_document_statistics"""
        return await self._document_store.get_document_statistics_async()

    # Maintenance operations

    def cleanup_old_documents(self, days_old: int = 365) -> int:
        """
        Clean up old unused documents

        Args:
            days_old: Documents older than this many days

        Returns:
            Number of documents cleaned up
        """
        try:
            return self._document_store.cleanup_old_documents(days_old)
        except Exception as e:
            logger.error(f"Error cleaning up old documents: {e}")
            return 0

    def validate_file_extension(self, filename: str) -> bool:
        """
        Validate file extension against allowed types

        Args:
            filename: Filename to validate

        Returns:
            True if allowed, False otherwise
        """
        if not filename or "." not in filename:
            return False

        extension = filename.rsplit(".", 1)[1].lower()
        return extension in ALLOWED_EXTENSIONS

    def get_storage_info(self) -> dict[str, Any]:
        """
        Get storage usage information

        Returns:
            Storage info dictionary
        """
        try:
            stats = self.get_document_statistics()

            # Add filesystem storage info
            upload_size = (
                sum(f.stat().st_size for f in UPLOAD_DIR.rglob("*") if f.is_file())
                if UPLOAD_DIR.exists()
                else 0
            )
            export_size = (
                sum(f.stat().st_size for f in EXPORT_DIR.rglob("*") if f.is_file())
                if EXPORT_DIR.exists()
                else 0
            )
            save_size = (
                sum(f.stat().st_size for f in SAVE_DIR.rglob("*") if f.is_file())
                if SAVE_DIR.exists()
                else 0
            )

            return {
                "database_size_bytes": stats.get("total_size_bytes", 0),
                "upload_files_bytes": upload_size,
                "export_files_bytes": export_size,
                "save_files_bytes": save_size,
                "total_storage_bytes": stats.get("total_size_bytes", 0)
                + upload_size
                + export_size
                + save_size,
                "document_count": stats.get("total_documents", 0),
                "upload_file_count": len(self.list_files("uploads")),
                "export_file_count": len(self.list_files("exports")),
                "save_file_count": len(self.list_files("saves")),
            }

        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                "database_size_bytes": 0,
                "upload_files_bytes": 0,
                "export_files_bytes": 0,
                "save_files_bytes": 0,
                "total_storage_bytes": 0,
                "document_count": 0,
                "upload_file_count": 0,
                "export_file_count": 0,
                "save_file_count": 0,
            }

    def close(self):
        """Close the file manager and clean up resources"""
        if hasattr(self, "_document_store"):
            self._document_store.close()
        logger.info("EnhancedFileManager closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Backward compatibility alias
FileManager = EnhancedFileManager


def create_file_manager(db_path: Optional[str] = None, pool_size: int = 10) -> EnhancedFileManager:
    """
    Create an enhanced file manager instance

    Args:
        db_path: Database path (not used, for compatibility)
        pool_size: Connection pool size (not used, for compatibility)

    Returns:
        EnhancedFileManager instance
    """
    return EnhancedFileManager()
