"""
Cached Document Store Implementation
"""

import logging

from .hybrid_cache import HybridCache
from .optimized_document_store import OptimizedDocumentStore
from .query_cache import QueryCache

logger = logging.getLogger(__name__)


class CachedDocumentStore:
    """Cached wrapper around OptimizedDocumentStore"""

    def __init__(self, store: OptimizedDocumentStore, cache: HybridCache = None):
        self.store = store
        self.cache = cache
        self.query_cache = QueryCache(cache) if cache else None

    async def initialize(self):
        if self.store:
            await self.store.initialize()
        if self.cache:
            await self.cache.initialize()

    async def close(self):
        if self.store:
            await self.store.close()
        if self.cache:
            await self.cache.close()

    async def add_document(
        self,
        title: str,
        content: str,
        file_path: str,
        metadata: dict = None,
        user_id: str = None,
        doc_type: str = "text",
    ) -> str:
        if not self.store:
            raise RuntimeError("Document store not initialized")

        doc_id = self.store.add_document(
            content=content,
            title=title,
            file_path=file_path,
            metadata=metadata,
            user_id=user_id,
            doc_type=doc_type,
        )

        if self.cache and self.query_cache:
            tags = ["documents", "search_results"]
            if user_id:
                tags.append(f"user:{user_id}")
            await self.query_cache.invalidate_by_tags(tags)

        return doc_id

    async def search_documents(self, query: str, top_k: int = 10, user_id: str = None) -> list:
        if not self.store:
            raise RuntimeError("Document store not initialized")

        if not self.cache or not self.query_cache:
            results = self.store.search_documents(query=query, limit=top_k, user_id=user_id)
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "metadata": r.metadata,
                    "file_path": r.file_path,
                    "timestamp": r.timestamp,
                    "type": r.type,
                    "user_id": r.user_id,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ]

        try:
            # Try cache first
            cached_result = await self.query_cache.get(
                query_type="document_search",
                params={"query": query, "top_k": top_k, "user_id": user_id},
                user_id=user_id,
            )

            if cached_result is not None:
                return cached_result

            results = self.store.search_documents(query=query, limit=top_k, user_id=user_id)

            dict_results = [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "metadata": r.metadata,
                    "file_path": r.file_path,
                    "timestamp": r.timestamp,
                    "type": r.type,
                    "user_id": r.user_id,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ]

            # Cache the results
            await self.query_cache.set(
                query_type="document_search",
                params={"query": query, "top_k": top_k, "user_id": user_id},
                result=dict_results,
                user_id=user_id,
                tags=["documents", "search_results", f"user:{user_id}" if user_id else "anonymous"],
            )

            return dict_results

        except Exception as e:
            logger.error(f"Error in cached search: {e}")
            results = self.store.search_documents(query=query, limit=top_k, user_id=user_id)
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "metadata": r.metadata,
                    "file_path": r.file_path,
                    "timestamp": r.timestamp,
                    "type": r.type,
                    "user_id": r.user_id,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ]


def create_cached_document_store() -> CachedDocumentStore:
    """Factory function to create a cached document store"""
    from .optimized_document_store import create_optimized_document_store

    # Create the base store
    base_store = create_optimized_document_store()

    # Create cached wrapper
    cached_store = CachedDocumentStore(base_store)

    return cached_store
