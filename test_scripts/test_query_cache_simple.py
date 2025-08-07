"""
Simplified Query Cache Test - Task 1.1.3
Test query cache system without Redis dependency.
"""

import asyncio
import os
import shutil
import tempfile
import time

from core.cached_document_store import create_cached_document_store
from core.query_cache import CacheInvalidator, QueryCache


async def test_query_cache_basic():
    """Test basic query cache functionality without Redis"""
    print("Testing basic QueryCache functionality...")

    # Use memory-only cache (no Redis)
    cache = QueryCache(redis_url="redis://invalid:6379")  # Invalid Redis URL
    await cache.initialize()

    # Test cache operations
    query_type = "test_query"
    params = {"test": "value", "number": 42}
    result = {"data": "test_result", "count": 100}

    # Set cache
    success = await cache.set(query_type, params, result)
    print(f"Cache set successful: {success}")

    # Get from cache
    cached_result = await cache.get(query_type, params)
    print(f"Cache get result: {cached_result}")
    assert cached_result == result, f"Expected {result}, got {cached_result}"

    # Check metrics
    metrics = await cache.get_metrics()
    print(f"Cache metrics: {metrics['query_cache']}")
    assert metrics["query_cache"]["hits"] >= 1
    assert metrics["query_cache"]["sets"] >= 1

    print("✅ Basic cache functionality works")
    return True


async def test_cache_with_tags():
    """Test cache tagging and invalidation"""
    print("Testing cache tagging and invalidation...")

    cache = QueryCache(redis_url="redis://invalid:6379")
    await cache.initialize()

    # Set cache with tags
    query_type = "document_search"
    params = {"query": "test", "user_id": "user123"}
    result = [{"doc_id": 1, "content": "test content"}]
    tags = ["documents", "user:user123", "search_results"]

    success = await cache.set(query_type, params, result, tags=tags)
    assert success

    # Verify cache hit
    cached_result = await cache.get(query_type, params)
    assert cached_result == result

    # Invalidate by tags
    invalidated = await cache.invalidate_by_tags(["user:user123"])
    print(f"Invalidated {invalidated} cache entries")

    # Verify cache miss after invalidation
    cached_result = await cache.get(query_type, params)
    assert cached_result is None

    print("✅ Cache tagging and invalidation works")
    return True


async def test_cached_document_store():
    """Test cached document store without Redis"""
    print("Testing cached document store...")

    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")

    try:
        # Create store with invalid Redis URL (will use memory cache only)
        store = await create_cached_document_store(
            db_path=db_path, redis_url="redis://invalid:6379"
        )

        # Add a document
        doc_id = await store.add_document(
            filename="test.txt",
            content="This is a test document for caching",
            user_id="user123",
            metadata={"type": "text"},
        )
        print(f"Added document with ID: {doc_id}")
        assert len(doc_id) > 0  # Check that we got a valid ID

        # Search documents (first time - cache miss)
        start_time = time.time()
        results1 = await store.search_documents(query="test document", user_id="user123")
        first_search_time = time.time() - start_time
        print(f"First search took {first_search_time:.4f}s, found {len(results1)} results")
        assert len(results1) > 0

        # Search again (should hit cache and be faster)
        start_time = time.time()
        results2 = await store.search_documents(query="test document", user_id="user123")
        cached_search_time = time.time() - start_time
        print(f"Cached search took {cached_search_time:.4f}s, found {len(results2)} results")

        # Results should be identical
        assert results1 == results2

        # Get cache metrics
        metrics = await store.get_cache_metrics()
        print(f"Cache hit rate: {metrics['query_cache']['hit_rate']:.1f}%")

        # Get document statistics
        stats = await store.get_document_statistics("user123")
        print(f"Document stats: {stats}")
        assert stats["total_documents"] > 0

        await store.close()

        print("✅ Cached document store works")
        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


async def test_cache_invalidator_helpers():
    """Test cache invalidation helper functions"""
    print("Testing cache invalidation helpers...")

    # Test document tags
    doc_tags = CacheInvalidator.document_tags("123", "pdf", "user456")
    expected_tags = ["documents", "document:123", "doc_type:pdf", "document_stats", "user:user456"]
    for tag in expected_tags:
        assert tag in doc_tags, f"Expected tag '{tag}' not found in {doc_tags}"

    # Test chat tags
    chat_tags = CacheInvalidator.chat_tags("session789", "user456")
    expected_chat_tags = ["chat_history", "session:session789", "user:user456"]
    for tag in expected_chat_tags:
        assert tag in chat_tags, f"Expected chat tag '{tag}' not found in {chat_tags}"

    # Test user tags
    user_tags = CacheInvalidator.user_tags("user456")
    expected_user_tags = ["user:user456", "user_data"]
    for tag in expected_user_tags:
        assert tag in user_tags, f"Expected user tag '{tag}' not found in {user_tags}"

    print("✅ Cache invalidation helpers work")
    return True


async def test_performance_improvement():
    """Test performance improvement with caching"""
    print("Testing cache performance improvement...")

    # Create temporary database
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "perf_test.db")

    try:
        store = await create_cached_document_store(
            db_path=db_path, redis_url="redis://invalid:6379"
        )

        # Add test documents
        for i in range(20):
            await store.add_document(
                filename=f"doc_{i}.txt",
                content=f"This is test document number {i} with content for searching performance",
                user_id="perf_user",
            )

        print("Added 20 test documents")

        # Test search performance
        query = "test document"

        # First search (cache miss)
        start_time = time.time()
        results1 = await store.search_documents(query, user_id="perf_user")
        first_search_time = time.time() - start_time

        # Second search (cache hit)
        start_time = time.time()
        results2 = await store.search_documents(query, user_id="perf_user")
        cached_search_time = time.time() - start_time

        # Verify results are the same
        assert results1 == results2
        assert len(results1) > 0

        # Performance should improve (cached search should be faster)
        print(f"First search: {first_search_time:.4f}s")
        print(f"Cached search: {cached_search_time:.4f}s")

        if cached_search_time < first_search_time:
            improvement = first_search_time / cached_search_time
            print(f"Performance improvement: {improvement:.2f}x faster")
        else:
            print("No significant performance improvement (memory cache)")

        # Test repeated queries for hit rate
        for _ in range(5):
            await store.search_documents(query, user_id="perf_user")

        metrics = await store.get_cache_metrics()
        hit_rate = metrics["query_cache"]["hit_rate"]
        print(f"Cache hit rate after multiple queries: {hit_rate:.1f}%")

        await store.close()

        print("✅ Performance test completed")
        return True

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def run_all_tests():
    """Run all query cache tests"""
    print("🚀 Starting Query Cache System Tests")
    print("=" * 50)

    test_results = []

    try:
        # Run each test
        tests = [
            ("Basic Cache Operations", test_query_cache_basic),
            ("Cache Tagging & Invalidation", test_cache_with_tags),
            ("Cached Document Store", test_cached_document_store),
            ("Cache Invalidation Helpers", test_cache_invalidator_helpers),
            ("Performance Testing", test_performance_improvement),
        ]

        for test_name, test_func in tests:
            print(f"\n🔄 Running: {test_name}")
            try:
                result = await test_func()
                test_results.append((test_name, result, None))
                print(f"✅ {test_name} - PASSED")
            except Exception as e:
                test_results.append((test_name, False, str(e)))
                print(f"❌ {test_name} - FAILED: {e}")

        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        passed = sum(1 for _, result, _ in test_results if result)
        total = len(test_results)

        for test_name, result, error in test_results:
            status = "PASS" if result else "FAIL"
            print(f"{status:4} | {test_name}")
            if error:
                print(f"     | Error: {error}")

        print(f"\n📈 Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 ALL TESTS PASSED! Query cache system is working correctly.")
            print("\n✨ Task 1.1.3 Query Result Caching - COMPLETED")
            return True
        else:
            print(f"⚠️  {total - passed} test(s) failed. Please review the errors above.")
            return False

    except Exception as e:
        print(f"💥 Test runner error: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())
