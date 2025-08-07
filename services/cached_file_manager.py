"""
Cached File Manager - Task 1.1.3
Enhanced file management service using CachedDocumentStore with query result caching.
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional

from werkzeug.utils import secure_filename

from config.settings import ALLOWED_EXTENSIONS, EXPORT_DIR, SAVE_DIR, UPLOAD_DIR
from core.cached_document_store import CachedDocumentStore, create_cached_document_store

logger = logging.getLogger(__name__)


class CachedFileManager:
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
        Initialize cached file manager

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
            logger.info("Cached file manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize cached file manager: {e}")
            return False

    @property
    def document_store(self) -> Optional[CachedDocumentStore]:
        """Get document store instance"""
        return self._document_store

    # Document operations (cached)

    async def add_document(
        self,
        filename: str,
        content: str,
        doc_type: str = "text",
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> int:
        """
        Add a document to the document store with caching

        Args:
            filename: Name of the document
            content: Document content
            doc_type: Type of document
            metadata: Additional metadata
            user_id: User ID for user-specific documents

        Returns:
            Document ID
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata.update(
                {"type": doc_type, "upload_time": datetime.now().isoformat(), "filename": filename}
            )

            # Add to cached document store
            doc_id = await self._document_store.add_document(
                filename=filename, content=content, user_id=user_id, metadata=doc_metadata
            )

            self.file_upload_count += 1
            logger.info(f"Added document {filename} with ID {doc_id}")
            return doc_id

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error adding document {filename}: {e}")
            raise

    async def search_documents(
        self, query: str, top_k: int = 5, user_id: Optional[str] = None, threshold: float = 0.1
    ) -> list[dict[str, Any]]:
        """
        Search documents with caching

        Args:
            query: Search query
            top_k: Number of results to return
            user_id: User ID for user-specific search
            threshold: Similarity threshold

        Returns:
            List of matching documents
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            self.search_count += 1
            results = await self._document_store.search_documents(
                query=query, top_k=top_k, user_id=user_id, threshold=threshold
            )

            logger.debug(f"Search for '{query[:50]}...' returned {len(results)} results")
            return results

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error searching documents: {e}")
            raise

    async def get_document_statistics(self, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get document statistics with caching

        Args:
            user_id: User ID for user-specific statistics

        Returns:
            Document statistics
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            stats = await self._document_store.get_document_statistics(user_id)

            # Add file manager specific stats
            stats.update(
                {
                    "file_upload_count": self.file_upload_count,
                    "search_count": self.search_count,
                    "error_count": self.error_count,
                }
            )

            return stats

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error getting document statistics: {e}")
            raise

    async def get_user_documents(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get user documents with caching

        Args:
            user_id: User ID
            limit: Maximum number of documents
            offset: Offset for pagination

        Returns:
            List of user documents
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            documents = await self._document_store.get_user_documents(
                user_id=user_id, limit=limit, offset=offset
            )

            logger.debug(f"Retrieved {len(documents)} documents for user {user_id}")
            return documents

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error getting user documents: {e}")
            raise

    async def get_document_info(
        self, doc_id: int, user_id: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Get document info with caching

        Args:
            doc_id: Document ID
            user_id: User ID for access control

        Returns:
            Document information or None
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            info = await self._document_store.get_document_info(doc_id, user_id)
            return info

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error getting document info for {doc_id}: {e}")
            raise

    async def delete_document(self, doc_id: int, user_id: Optional[str] = None) -> bool:
        """
        Delete document with cache invalidation

        Args:
            doc_id: Document ID
            user_id: User ID for access control

        Returns:
            True if successful
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            success = await self._document_store.delete_document(doc_id, user_id)

            if success:
                logger.info(f"Deleted document {doc_id}")
            else:
                logger.warning(f"Failed to delete document {doc_id}")

            return success

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error deleting document {doc_id}: {e}")
            raise

    # Chat operations (cached)

    async def add_chat_message(
        self,
        user_message: str,
        ai_response: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Add chat message with cache invalidation

        Args:
            user_message: User's message
            ai_response: AI's response
            user_id: User ID
            session_id: Session ID
            metadata: Additional metadata

        Returns:
            Chat message ID
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            chat_id = await self._document_store.add_chat_message(
                user_message=user_message,
                ai_response=ai_response,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
            )

            logger.debug(f"Added chat message {chat_id}")
            return chat_id

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error adding chat message: {e}")
            raise

    async def get_chat_history(
        self, user_id: Optional[str] = None, session_id: Optional[str] = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Get chat history with caching

        Args:
            user_id: User ID
            session_id: Session ID
            limit: Maximum number of messages

        Returns:
            List of chat messages
        """
        if not self._document_store:
            raise RuntimeError("Document store not initialized")

        try:
            history = await self._document_store.get_chat_history(
                user_id=user_id, session_id=session_id, limit=limit
            )

            logger.debug(f"Retrieved {len(history)} chat messages")
            return history

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error getting chat history: {e}")
            raise

    # File operations

    def save_file(self, file, upload_dir: str = UPLOAD_DIR) -> str:
        """
        Save uploaded file to disk

        Args:
            file: File object
            upload_dir: Directory to save file

        Returns:
            Saved filename
        """
        try:
            filename = secure_filename(file.filename)

            if not self.is_allowed_file(filename):
                raise ValueError(f"File type not allowed: {filename}")

            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

            logger.info(f"Saved file: {filename}")
            return filename

        except Exception as e:
            self.error_count += 1
            logger.error(f"Error saving file: {e}")
            raise

    def is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def get_file_info(self, filename: str) -> Optional[dict[str, Any]]:
        """Get file information from disk"""
        try:
            file_path = os.path.join(UPLOAD_DIR, filename)

            if not os.path.exists(file_path):
                return None

            stat = os.stat(file_path)

            return {
                "filename": filename,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": file_path,
            }

        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {e}")
            return None

    def list_files(self, directory: str = UPLOAD_DIR) -> list[str]:
        """List files in directory"""
        try:
            if not os.path.exists(directory):
                return []

            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

            return sorted(files)

        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []

    # Cache management

    async def clear_cache(self, user_id: Optional[str] = None) -> bool:
        """Clear cache entries"""
        if not self._document_store:
            return True

        try:
            success = await self._document_store.clear_cache(user_id)
            logger.info(f"Cache cleared for user: {user_id if user_id else 'all'}")
            return success

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    async def get_cache_metrics(self) -> dict[str, Any]:
        """Get comprehensive cache performance metrics"""
        if not self._document_store:
            return {"error": "Document store not available"}

        try:
            return await self._document_store.get_cache_metrics()
        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return {"error": str(e)}

    # Health monitoring

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check"""
        health = {
            "file_manager": {
                "initialized": self._document_store is not None,
                "upload_count": self.file_upload_count,
                "search_count": self.search_count,
                "error_count": self.error_count,
            }
        }

        if self._document_store:
            try:
                store_health = await self._document_store.health_check()
                health.update(store_health)
            except Exception as e:
                health["store_error"] = str(e)

        return health

    async def close(self) -> None:
        """Close connections"""
        if self._document_store:
            await self._document_store.close()
            logger.info("Cached file manager closed")


# Global instance
_cached_file_manager: Optional[CachedFileManager] = None


async def get_cached_file_manager(redis_url: str = "redis://localhost:6379") -> CachedFileManager:
    """Get or create global cached file manager instance"""
    global _cached_file_manager

    if _cached_file_manager is None:
        _cached_file_manager = CachedFileManager(redis_url=redis_url)
        await _cached_file_manager.initialize()

    return _cached_file_manager


# Backward compatibility
EnhancedFileManager = CachedFileManager
get_enhanced_file_manager = get_cached_file_manager
