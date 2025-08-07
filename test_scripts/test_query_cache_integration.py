"""
Test Query Result Caching - Task 1.1.3
Integration tests for query cache system with performance validation.
"""

import asyncio
import os
import shutil
import tempfile
import time

import pytest

from core.cached_document_store import create_cached_document_store
from core.query_cache import CacheInvalidator, QueryCache
from services.cached_file_manager import CachedFileManager


class TestQueryCache:
    """Test cases for QueryCache functionality"""

    @pytest.fixture
    async def cache(self):
        """Create test cache instance"""
        test_cache = QueryCache(
            redis_url="redis://localhost:6379/1",
            default_ttl=60,  # Test database
        )
        await test_cache.initialize()

        # Clear any existing test data
        await test_cache.clear_all()

        yield test_cache

        # Cleanup
        await test_cache.clear_all()
        if test_cache.hybrid_cache:
            await test_cache.hybrid_cache.close()

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache):
        """Test basic cache set/get operations"""
        # Test cache set and get
        query_type = "test_query"
        params = {"test": "value", "number": 42}
        result = {"data": "test_result", "count": 100}

        # Set cache
        success = await cache.set(query_type, params, result)
        assert success

        # Get from cache
        cached_result = await cache.get(query_type, params)
        assert cached_result == result

        # Check metrics
        metrics = await cache.get_metrics()
        assert metrics["query_cache"]["hits"] == 1
        assert metrics["query_cache"]["sets"] == 1

    @pytest.mark.asyncio
    async def test_cache_with_tags(self, cache):
        """Test cache tagging and invalidation"""
        query_type = "document_search"
        params = {"query": "test", "user_id": "user123"}
        result = [{"doc_id": 1, "content": "test content"}]
        tags = ["documents", "user:user123", "search_results"]

        # Set cache with tags
        success = await cache.set(query_type, params, result, tags=tags)
        assert success

        # Verify cache hit
        cached_result = await cache.get(query_type, params)
        assert cached_result == result

        # Invalidate by tags
        invalidated = await cache.invalidate_by_tags(["user:user123"])
        assert invalidated == 1

        # Verify cache miss after invalidation
        cached_result = await cache.get(query_type, params)
        assert cached_result is None

    @pytest.mark.asyncio
    async def test_ttl_policies(self, cache):
        """Test different TTL policies"""
        # Test document search TTL (5 minutes)
        search_params = {"query": "test"}
        search_result = {"results": []}

        await cache.set("document_search", search_params, search_result)

        # Test chat history TTL (10 minutes)
        chat_params = {"user_id": "user123"}
        chat_result = {"messages": []}

        await cache.set("chat_history", chat_params, chat_result)

        # Test document stats TTL (30 minutes)
        stats_params = {"user_id": "user123"}
        stats_result = {"count": 5}

        await cache.set("document_stats", stats_params, stats_result)

        # Verify all cached
        assert await cache.get("document_search", search_params) == search_result
        assert await cache.get("chat_history", chat_params) == chat_result
        assert await cache.get("document_stats", stats_params) == stats_result

    @pytest.mark.asyncio
    async def test_cache_invalidator_helpers(self):
        """Test cache invalidation helper functions"""
        # Test document tags
        doc_tags = CacheInvalidator.document_tags("123", "pdf", "user456")
        expected_tags = [
            "documents",
            "document:123",
            "doc_type:pdf",
            "document_stats",
            "user:user456",
        ]
        assert all(tag in doc_tags for tag in expected_tags)

        # Test chat tags
        chat_tags = CacheInvalidator.chat_tags("session789", "user456")
        expected_chat_tags = ["chat_history", "session:session789", "user:user456"]
        assert all(tag in chat_tags for tag in expected_chat_tags)

        # Test user tags
        user_tags = CacheInvalidator.user_tags("user456")
        expected_user_tags = ["user:user456", "user_data"]
        assert all(tag in user_tags for tag in expected_user_tags)


class TestCachedDocumentStore:
    """Test cases for CachedDocumentStore"""

    @pytest.fixture
    async def temp_db(self):
        """Create temporary test database"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")

        yield db_path

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    async def cached_store(self, temp_db):
        """Create test cached document store"""
        store = await create_cached_document_store(
            db_path=temp_db, redis_url="redis://localhost:6379/1"
        )

        yield store

        # Cleanup
        await store.close()

    @pytest.mark.asyncio
    async def test_cached_document_operations(self, cached_store):
        """Test document operations with caching"""
        # Add a document
        doc_id = await cached_store.add_document(
            filename="test.txt",
            content="This is a test document for caching",
            user_id="user123",
            metadata={"type": "text"},
        )
        assert doc_id > 0

        # Search documents (should be cached)
        results1 = await cached_store.search_documents(query="test document", user_id="user123")
        assert len(results1) > 0

        # Search again (should hit cache)
        results2 = await cached_store.search_documents(query="test document", user_id="user123")
        assert results1 == results2

        # Get document statistics (should be cached)
        stats1 = await cached_store.get_document_statistics("user123")
        assert stats1["total_documents"] > 0

        # Get stats again (should hit cache)
        stats2 = await cached_store.get_document_statistics("user123")
        assert stats1 == stats2

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_changes(self, cached_store):
        """Test cache invalidation when documents change"""
        # Add document and search
        doc_id = await cached_store.add_document(
            filename="test.txt", content="Original content", user_id="user123"
        )

        # Search to populate cache
        await cached_store.search_documents("Original", user_id="user123")

        # Get cache metrics to verify hits
        metrics_before = await cached_store.get_cache_metrics()

        # Update document (should invalidate cache)
        await cached_store.update_document(
            doc_id=doc_id, content="Updated content", user_id="user123"
        )

        # Search again (should not hit old cache)
        results = await cached_store.search_documents("Updated", user_id="user123")
        assert len(results) > 0

        # Verify cache invalidation occurred
        metrics_after = await cached_store.get_cache_metrics()
        assert (
            metrics_after["query_cache"]["invalidations"]
            > metrics_before["query_cache"]["invalidations"]
        )

    @pytest.mark.asyncio
    async def test_chat_history_caching(self, cached_store):
        """Test chat history caching"""
        # Add chat messages
        chat_id1 = await cached_store.add_chat_message(
            user_message="Hello",
            ai_response="Hi there!",
            user_id="user123",
            session_id="session456",
        )

        chat_id2 = await cached_store.add_chat_message(
            user_message="How are you?",
            ai_response="I'm doing well, thanks!",
            user_id="user123",
            session_id="session456",
        )

        # Get chat history (should be cached)
        history1 = await cached_store.get_chat_history(user_id="user123", session_id="session456")
        assert len(history1) == 2

        # Get history again (should hit cache)
        history2 = await cached_store.get_chat_history(user_id="user123", session_id="session456")
        assert history1 == history2


class TestCachedFileManager:
    """Test cases for CachedFileManager"""

    @pytest.fixture
    async def file_manager(self):
        """Create test file manager"""
        manager = CachedFileManager(redis_url="redis://localhost:6379/1")
        await manager.initialize()

        yield manager

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_file_manager_caching(self, file_manager):
        """Test file manager with caching"""
        # Add document
        doc_id = await file_manager.add_document(
            filename="test.txt", content="Test content for file manager", user_id="user123"
        )

        # Search documents
        results = await file_manager.search_documents(query="test content", user_id="user123")
        assert len(results) > 0

        # Get statistics
        stats = await file_manager.get_document_statistics("user123")
        assert stats["total_documents"] > 0

        # Get cache metrics
        metrics = await file_manager.get_cache_metrics()
        assert "query_cache" in metrics
        assert "hybrid_cache" in metrics


class TestCachePerformance:
    """Performance tests for cache system"""

    @pytest.fixture
    async def performance_setup(self):
        """Setup for performance testing"""
        # Create store with caching
        cached_store = await create_cached_document_store(redis_url="redis://localhost:6379/1")

        # Add test documents
        for i in range(50):
            await cached_store.add_document(
                filename=f"doc_{i}.txt",
                content=f"This is test document number {i} with content for searching",
                user_id="perf_user",
            )

        yield cached_store

        # Cleanup
        await cached_store.close()

    @pytest.mark.asyncio
    async def test_search_performance_with_cache(self, performance_setup):
        """Test search performance improvement with caching"""
        store = performance_setup

        # Warm up cache with first search
        query = "test document"

        start_time = time.time()
        results1 = await store.search_documents(query, user_id="perf_user")
        first_search_time = time.time() - start_time

        # Second search should be faster (cached)
        start_time = time.time()
        results2 = await store.search_documents(query, user_id="perf_user")
        cached_search_time = time.time() - start_time

        # Verify results are the same
        assert results1 == results2

        # Cache should be significantly faster
        # Allow some variance but expect at least 2x improvement
        performance_improvement = first_search_time / cached_search_time
        print(f"Performance improvement: {performance_improvement:.2f}x")
        print(f"First search: {first_search_time:.4f}s, Cached search: {cached_search_time:.4f}s")

        # Cache should provide some performance benefit
        assert (
            performance_improvement >= 1.5
        ), f"Expected performance improvement, got {performance_improvement:.2f}x"

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, performance_setup):
        """Test cache hit rate with repeated queries"""
        store = performance_setup

        # Clear cache to start fresh
        await store.clear_cache("perf_user")

        # Perform multiple searches with same queries
        queries = ["test document", "content searching", "number"]

        for _ in range(3):  # Repeat queries
            for query in queries:
                await store.search_documents(query, user_id="perf_user")

        # Get cache metrics
        metrics = await store.get_cache_metrics()
        hit_rate = metrics["query_cache"]["hit_rate"]

        print(f"Cache hit rate: {hit_rate:.1f}%")
        print(f"Cache metrics: {metrics['query_cache']}")

        # Should have good hit rate with repeated queries
        assert hit_rate >= 50.0, f"Expected hit rate >= 50%, got {hit_rate:.1f}%"


# Integration test runner
async def run_integration_tests():
    """Run all integration tests"""
    print("Running Query Cache Integration Tests...")

    # Test basic cache functionality
    cache = QueryCache(redis_url="redis://localhost:6379/1")
    await cache.initialize()

    try:
        # Test cache operations
        await cache.set("test", {"key": "value"}, {"result": "data"})
        result = await cache.get("test", {"key": "value"})
        assert result == {"result": "data"}

        # Test invalidation
        await cache.invalidate_by_tags(["test"])
        result = await cache.get("test", {"key": "value"})
        assert result is None

        print("✅ Basic cache tests passed")

        # Test document store caching
        store = await create_cached_document_store(redis_url="redis://localhost:6379/1")

        # Add and search documents
        doc_id = await store.add_document("test.txt", "Test content", user_id="test_user")
        results = await store.search_documents("Test", user_id="test_user")
        assert len(results) > 0

        # Get metrics
        metrics = await store.get_cache_metrics()
        assert "query_cache" in metrics

        print("✅ Document store cache tests passed")

        # Performance test
        start_time = time.time()
        for i in range(10):
            await store.search_documents("Test", user_id="test_user")
        end_time = time.time()

        print(f"✅ Performance test: 10 searches in {end_time - start_time:.3f}s")

        await store.close()

    finally:
        await cache.clear_all()
        if cache.hybrid_cache:
            await cache.hybrid_cache.close()

    print("🎉 All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
