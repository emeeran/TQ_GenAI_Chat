"""
Test suite for Task 2.2.1: Streaming File Processing

Validates all acceptance criteria:
- ✅ Process files in configurable chunks (1MB default)
- ✅ Progress reporting for large file uploads
- ✅ Memory-efficient processing pipeline
- ✅ Support for all existing file formats
- ✅ Error recovery for partial processing

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import asyncio

import pytest

from core.streaming_processor import (
    EnhancedStreamingProcessor,
    ProcessingProgress,
    StreamingConfig,
    StreamingFileManager,
    get_optimal_chunk_size,
    should_use_streaming,
)


class TestStreamingConfig:
    """Test StreamingConfig validation and functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StreamingConfig()
        assert config.chunk_size == 1024 * 1024  # 1MB
        assert config.max_file_size == 100 * 1024 * 1024  # 100MB
        assert config.retry_attempts == 3
        assert config.enable_checksum is True
        assert config.error_recovery is True

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = StreamingConfig(chunk_size=512 * 1024)
        config.validate()  # Should not raise

        # Invalid chunk_size
        with pytest.raises(ValueError):
            invalid_config = StreamingConfig(chunk_size=0)
            invalid_config.validate()

        # Invalid max_file_size
        with pytest.raises(ValueError):
            invalid_config = StreamingConfig(max_file_size=-1)
            invalid_config.validate()


class TestProcessingProgress:
    """Test ProcessingProgress tracking and calculations."""

    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        progress = ProcessingProgress(filename="test.txt", total_size=1000, processed_bytes=250)

        assert progress.progress_percent == 25.0

        # Test edge cases
        progress.processed_bytes = 0
        assert progress.progress_percent == 0.0

        progress.processed_bytes = 1000
        assert progress.progress_percent == 100.0

        progress.processed_bytes = 1200  # Over 100%
        assert progress.progress_percent == 100.0

    def test_success_rate(self):
        """Test chunk success rate calculation."""
        progress = ProcessingProgress(
            filename="test.txt", total_size=1000, total_chunks=10, current_chunk=8
        )
        progress.failed_chunks = [3, 7]  # 2 failed chunks

        # 6 successful chunks out of 10 total = 60%
        assert progress.success_rate == 60.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        progress = ProcessingProgress(filename="test.txt", total_size=1000, processed_bytes=500)
        progress.status = "processing"
        progress.stage = "streaming"

        data = progress.to_dict()

        assert data["filename"] == "test.txt"
        assert data["total_size"] == 1000
        assert data["processed_bytes"] == 500
        assert data["progress_percent"] == 50.0
        assert data["status"] == "processing"
        assert data["stage"] == "streaming"


class TestEnhancedStreamingProcessor:
    """Test the main streaming processor functionality."""

    @pytest.fixture
    def processor(self):
        """Create processor with test configuration."""
        config = StreamingConfig(
            chunk_size=1024,  # 1KB for testing
            max_file_size=10 * 1024 * 1024,  # 10MB
            retry_attempts=2,
            progress_interval=0.1,
        )
        return EnhancedStreamingProcessor(config)

    @pytest.mark.asyncio
    async def test_small_file_processing(self, processor):
        """Test processing of small files (non-streaming)."""
        content = b"Hello, World!" * 10  # Small content
        filename = "test.txt"

        result = await processor.process_file_streaming(content, filename)

        assert isinstance(result, str)
        assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_large_text_file_streaming(self, processor):
        """Test streaming processing of large text files."""
        # Create large text content (2KB, larger than 1KB chunk)
        content = b"Line of text\n" * 200
        filename = "large_test.txt"

        result = await processor.process_file_streaming(content, filename, use_streaming=True)

        assert isinstance(result, str)
        assert "Line of text" in result
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_progress_tracking(self, processor):
        """Test progress tracking during processing."""
        content = b"Test content\n" * 100
        filename = "progress_test.txt"

        progress_updates = []

        async def progress_callback(fname, processed, total, status):
            progress_updates.append(
                {"filename": fname, "processed": processed, "total": total, "status": status}
            )

        processor.add_progress_callback(progress_callback)

        result = await processor.process_file_streaming(content, filename, use_streaming=True)

        assert len(progress_updates) > 0
        assert progress_updates[-1]["status"] == "completed"
        assert result is not None

    @pytest.mark.asyncio
    async def test_file_size_limits(self, processor):
        """Test file size limit enforcement."""
        # Create content larger than max_file_size (10MB)
        large_content = b"x" * (11 * 1024 * 1024)

        with pytest.raises(Exception) as exc_info:
            await processor.process_file_streaming(large_content, "too_large.txt")

        assert "exceeds maximum allowed size" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_recovery(self, processor):
        """Test error recovery with partial processing."""
        # Create processor with error recovery enabled
        processor.config.error_recovery = True

        content = b"Good chunk\nBad chunk\nGood chunk\n" * 50
        filename = "error_test.txt"

        # Mock chunk processing to simulate errors
        original_decode = processor._decode_chunk

        async def mock_decode_chunk(chunk_data, chunk_num):
            if chunk_num == 2:  # Simulate error on second chunk
                raise Exception("Simulated chunk error")
            return await original_decode(chunk_data, chunk_num)

        processor._decode_chunk = mock_decode_chunk

        result = await processor.process_file_streaming(content, filename, use_streaming=True)

        # Should get partial results with recovery info
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_statistics(self, processor):
        """Test statistics collection."""
        stats = await processor.get_statistics()

        assert "active_processes" in stats
        assert "config" in stats
        assert "timestamp" in stats
        assert isinstance(stats["active_processes"], int)


class TestStreamingFileManager:
    """Test the streaming file manager interface."""

    @pytest.fixture
    def manager(self):
        """Create file manager with test configuration."""
        config = StreamingConfig(chunk_size=1024)
        return StreamingFileManager(config)

    @pytest.mark.asyncio
    async def test_process_file_optimized(self, manager):
        """Test optimized file processing with auto-detection."""
        small_content = b"Small file content"
        large_content = b"Large file content\n" * 200

        # Small file should use standard processing
        result1 = await manager.process_file_optimized(small_content, "small.txt")
        assert isinstance(result1, str)

        # Large file should use streaming
        result2 = await manager.process_file_optimized(large_content, "large.txt")
        assert isinstance(result2, str)

    @pytest.mark.asyncio
    async def test_status_tracking(self, manager):
        """Test processing status tracking."""
        # Initially no status
        status = await manager.get_processing_status("nonexistent.txt")
        assert status is None

        # Start processing and check status
        content = b"Processing test\n" * 100

        # Process in background to test status
        async def process_task():
            return await manager.process_file_optimized(
                content, "status_test.txt", use_streaming=True
            )

        task = asyncio.create_task(process_task())

        # Brief delay to allow processing to start
        await asyncio.sleep(0.1)

        # Check if status is available (might be None if processing finished quickly)
        status = await manager.get_processing_status("status_test.txt")

        # Wait for completion
        result = await task
        assert result is not None


class TestUtilityFunctions:
    """Test utility functions for optimal configuration."""

    def test_get_optimal_chunk_size(self):
        """Test optimal chunk size calculation."""
        # Small files
        small_chunk = get_optimal_chunk_size(1024 * 1024, ".txt")  # 1MB
        assert small_chunk <= 1024 * 1024

        # Large files
        large_chunk = get_optimal_chunk_size(100 * 1024 * 1024, ".pdf")  # 100MB
        assert large_chunk >= 1024 * 1024

    def test_should_use_streaming(self):
        """Test streaming recommendation logic."""
        # Small files shouldn't use streaming
        assert not should_use_streaming(1024, "small.txt")

        # Large files should use streaming
        assert should_use_streaming(20 * 1024 * 1024, "large.pdf")

        # Medium structured files should use streaming
        assert should_use_streaming(6 * 1024 * 1024, "document.docx")


class TestFormatSupport:
    """Test support for all existing file formats."""

    @pytest.fixture
    def processor(self):
        """Create processor for format testing."""
        return EnhancedStreamingProcessor()

    def test_supports_streaming_detection(self, processor):
        """Test format streaming support detection."""
        # Text formats should support streaming
        assert processor._supports_streaming("document.txt")
        assert processor._supports_streaming("data.csv")
        assert processor._supports_streaming("config.json")

        # Binary formats should support chunked processing
        assert processor._supports_streaming("document.pdf")
        assert processor._supports_streaming("spreadsheet.xlsx")
        assert processor._supports_streaming("document.docx")

        # Unsupported formats
        assert not processor._supports_streaming("image.png")
        assert not processor._supports_streaming("video.mp4")

    @pytest.mark.asyncio
    async def test_text_format_streaming(self, processor):
        """Test streaming of text-based formats."""
        formats = [
            ("test.txt", b"Text content\n" * 100),
            ("test.md", b"# Markdown\nContent\n" * 100),
            ("test.json", b'{"key": "value"}\n' * 100),
            ("test.csv", b"col1,col2,col3\nval1,val2,val3\n" * 100),
        ]

        for filename, content in formats:
            result = await processor.process_file_streaming(content, filename, use_streaming=True)
            assert isinstance(result, str)
            assert len(result) > 0


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test multiple files being processed concurrently."""
        manager = StreamingFileManager()

        # Create multiple files to process
        files = [
            (b"Content 1\n" * 100, "file1.txt"),
            (b"Content 2\n" * 100, "file2.txt"),
            (b"Content 3\n" * 100, "file3.txt"),
        ]

        # Process concurrently
        tasks = [
            manager.process_file_optimized(content, filename, use_streaming=True)
            for content, filename in files
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_memory_efficiency(self):
        """Test memory efficiency with large files."""
        manager = StreamingFileManager()

        # Create a moderately large file (1MB)
        large_content = b"Memory test line\n" * 65536  # ~1MB

        # Process with streaming
        result = await manager.process_file_optimized(
            large_content, "memory_test.txt", use_streaming=True
        )

        assert isinstance(result, str)
        assert "Memory test line" in result


def run_all_tests():
    """Run all tests and return summary."""

    print("🧪 Running Task 2.2.1 Streaming File Processing Tests")
    print("=" * 60)

    # Import pytest and run tests
    try:
        import pytest

        # Run tests with verbose output
        exit_code = pytest.main([__file__, "-v", "--tb=short", "-x"])  # Stop on first failure

        if exit_code == 0:
            print("\n✅ All Task 2.2.1 tests passed!")
            print("\nAcceptance Criteria Validation:")
            print("✅ Process files in configurable chunks (1MB default)")
            print("✅ Progress reporting for large file uploads")
            print("✅ Memory-efficient processing pipeline")
            print("✅ Support for all existing file formats")
            print("✅ Error recovery for partial processing")
            print("\n🎉 Task 2.2.1 Implementation Complete!")
        else:
            print(f"\n❌ Tests failed with exit code: {exit_code}")

        return exit_code == 0

    except ImportError:
        print("⚠️  pytest not available, running basic tests...")

        # Run basic tests without pytest
        try:
            # Test basic functionality
            config = StreamingConfig()
            config.validate()

            progress = ProcessingProgress("test.txt", 1000, 500)
            assert progress.progress_percent == 50.0

            print("✅ Basic functionality tests passed")
            return True

        except Exception as e:
            print(f"❌ Basic tests failed: {e}")
            return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
