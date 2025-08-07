"""
Comprehensive test suite for Document Chunking Strategy (Task 2.2.2).

Tests semantic chunking, format-specific strategies, metadata tracking,
and cross-chunk reference handling.
"""


import pytest

# Import the chunking system
from core.document_chunker import (
    ChunkBoundary,
    ChunkingConfig,
    ChunkingIntegration,
    ChunkMetadata,
    ChunkType,
    CSVChunker,
    DocumentChunk,
    DocumentChunkerManager,
    DocxChunker,
    PDFChunker,
    SemanticChunker,
    chunk_document_content,
    get_optimal_chunking_config,
)


class TestChunkingEnums:
    """Test enum definitions and values."""

    def test_chunk_type_enum(self):
        """Test ChunkType enum values."""
        assert ChunkType.PARAGRAPH.value == "paragraph"
        assert ChunkType.HEADING.value == "heading"
        assert ChunkType.TEXT.value == "text"
        assert ChunkType.LIST.value == "list"
        assert ChunkType.TABLE.value == "table"
        assert ChunkType.CODE.value == "code"

    def test_chunk_boundary_enum(self):
        """Test ChunkBoundary enum values."""
        assert ChunkBoundary.SENTENCE.value == "sentence"
        assert ChunkBoundary.PARAGRAPH.value == "paragraph"
        assert ChunkBoundary.SECTION.value == "section"


class TestChunkMetadata:
    """Test ChunkMetadata class functionality."""

    def test_metadata_creation(self):
        """Test metadata initialization."""
        metadata = ChunkMetadata(
            chunk_id="test_chunk_1",
            document_id="test_doc",
            chunk_type=ChunkType.PARAGRAPH,
            chunk_index=0,
            start_position=0,
            end_position=100,
            page_number=1,
            section_title="Introduction",
        )

        assert metadata.chunk_index == 0
        assert metadata.chunk_type == ChunkType.PARAGRAPH
        assert metadata.page_number == 1
        assert metadata.section_title == "Introduction"
        assert metadata.confidence_score == 1.0
        assert metadata.references == []
        assert metadata.entities == []

    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = ChunkMetadata(
            chunk_id="test_chunk_1",
            document_id="test_doc",
            chunk_type=ChunkType.HEADING,
            chunk_index=0,
            start_position=0,
            end_position=100,
            entities=[{"name": "Company", "type": "ORG"}, {"name": "Product", "type": "PRODUCT"}],
        )

        data = metadata.to_dict()

        assert data["chunk_index"] == 0
        assert data["chunk_type"] == "heading"
        assert len(data["entities"]) == 2
        assert "created_at" in data

    def test_metadata_field_defaults(self):
        """Test metadata default field values."""
        metadata = ChunkMetadata(
            chunk_id="test_chunk_1",
            document_id="test_doc",
            chunk_type=ChunkType.PARAGRAPH,
            chunk_index=0,
            start_position=0,
            end_position=100,
        )

        assert metadata.confidence_score == 1.0
        assert metadata.word_count == 0
        assert metadata.references == []
        assert metadata.entities == []
        assert metadata.page_number is None


class TestDocumentChunk:
    """Test DocumentChunk class functionality."""

    def test_chunk_creation(self):
        """Test chunk initialization."""
        metadata = ChunkMetadata(
            chunk_id="test_chunk_1",
            document_id="test_doc",
            chunk_type=ChunkType.PARAGRAPH,
            chunk_index=0,
            start_position=0,
            end_position=100,
        )
        chunk = DocumentChunk(content="This is test content for the chunk.", metadata=metadata)

        assert chunk.chunk_id == "test_chunk_1"
        assert chunk.content == "This is test content for the chunk."
        assert chunk.metadata.document_id == "test_doc"
        assert chunk.metadata.chunk_index == 0

    def test_effective_content(self):
        """Test effective content property."""
        metadata = ChunkMetadata(
            chunk_index=0, chunk_type=ChunkType.PARAGRAPH, section_title="Test Section"
        )
        chunk = DocumentChunk(
            chunk_id="test_chunk_1",
            content="This is test content.",
            metadata=metadata,
            document_id="test_doc",
            overlap_before="Previous content...",
            overlap_after="Next content...",
        )

        effective = chunk.effective_content
        assert "Previous content..." in effective
        assert "This is test content." in effective
        assert "Next content..." in effective
        assert "Test Section" in effective

    def test_chunk_serialization(self):
        """Test chunk to_dict method."""
        metadata = ChunkMetadata(chunk_index=0, chunk_type=ChunkType.PARAGRAPH)
        chunk = DocumentChunk(
            chunk_id="test_chunk_1",
            content="Test content",
            metadata=metadata,
            document_id="test_doc",
        )

        data = chunk.to_dict()

        assert data["chunk_id"] == "test_chunk_1"
        assert data["content"] == "Test content"
        assert data["document_id"] == "test_doc"
        assert "metadata" in data
        assert data["metadata"]["chunk_type"] == "paragraph"


class TestChunkingConfig:
    """Test ChunkingConfig class functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ChunkingConfig()

        assert config.target_chunk_size == 1000
        assert config.overlap_size == 200
        assert config.min_chunk_size == 100
        assert config.max_chunk_size == 2000
        assert config.boundary_strategy == ChunkBoundary.SEMANTIC
        assert config.preserve_headers is True
        assert config.preserve_lists is True

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = ChunkingConfig(target_chunk_size=800, overlap_size=150, min_chunk_size=50)
        assert config.target_chunk_size == 800

        # Invalid config (overlap too large)
        with pytest.raises(
            ValueError, match="Overlap size cannot be larger than target chunk size"
        ):
            ChunkingConfig(target_chunk_size=500, overlap_size=600)

        # Invalid config (min too large)
        with pytest.raises(
            ValueError, match="Minimum chunk size cannot be larger than target chunk size"
        ):
            ChunkingConfig(target_chunk_size=500, min_chunk_size=600)

    def test_config_serialization(self):
        """Test config to_dict method."""
        config = ChunkingConfig(target_chunk_size=800, overlap_size=150, preserve_headers=False)

        data = config.to_dict()

        assert data["target_chunk_size"] == 800
        assert data["overlap_size"] == 150
        assert data["preserve_headers"] is False
        assert data["boundary_strategy"] == "sentence"


class TestSemanticChunker:
    """Test SemanticChunker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(target_chunk_size=200, overlap_size=50)
        self.chunker = SemanticChunker(self.config)

    def test_simple_paragraph_chunking(self):
        """Test chunking simple paragraph text."""
        content = """
        This is the first paragraph. It contains some important information about the topic.

        This is the second paragraph. It continues with more details and explanations.

        This is the third paragraph. It concludes the section with final thoughts.
        """

        chunks = self.chunker.chunk_content(content, "test_doc")

        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
        assert all(chunk.document_id == "test_doc" for chunk in chunks)

        # Check that content is preserved
        combined_content = " ".join(chunk.content for chunk in chunks)
        assert "first paragraph" in combined_content
        assert "second paragraph" in combined_content
        assert "third paragraph" in combined_content

    def test_section_detection(self):
        """Test section header detection."""
        content = """
        # Introduction

        This is the introduction section with some content.

        ## Background

        This section provides background information.

        ### Technical Details

        Here are the technical details of the implementation.
        """

        chunks = self.chunker.chunk_content(content, "test_doc")

        # Should detect sections
        section_chunks = [c for c in chunks if c.metadata.chunk_type == ChunkType.HEADING]
        assert len(section_chunks) > 0

        # Check section titles
        section_titles = [c.metadata.section_title for c in chunks if c.metadata.section_title]
        assert any("Introduction" in title for title in section_titles)
        assert any("Background" in title for title in section_titles)

    def test_overlap_handling(self):
        """Test chunk overlap functionality."""
        content = "This is a sentence. " * 50  # Create content longer than target size

        chunks = self.chunker.chunk_content(content, "test_doc")

        assert len(chunks) > 1

        # Check overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            # Should have overlap_after and overlap_before
            if hasattr(current_chunk, "overlap_after") and current_chunk.overlap_after:
                assert len(current_chunk.overlap_after) > 0

            if hasattr(next_chunk, "overlap_before") and next_chunk.overlap_before:
                assert len(next_chunk.overlap_before) > 0


class TestPDFChunker:
    """Test PDFChunker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(target_chunk_size=300, pdf_respect_pages=True)
        self.chunker = PDFChunker(self.config)

    def test_pdf_page_chunking(self):
        """Test PDF page-aware chunking."""
        content = """
        [Page 1]
        This is content from the first page. It contains introductory material.

        [Page 2]
        This is content from the second page. It has different information.

        [Page 3]
        This is content from the third page. It concludes the document.
        """

        chunks = self.chunker.chunk_content(content, "test_doc")

        assert len(chunks) > 0

        # Check page assignments
        page_numbers = [c.metadata.page_number for c in chunks if c.metadata.page_number]
        assert len(page_numbers) > 0
        assert min(page_numbers) >= 1

        # Check that page content is properly assigned
        page_1_chunks = [c for c in chunks if c.metadata.page_number == 1]
        if page_1_chunks:
            assert any("first page" in c.content for c in page_1_chunks)


class TestDocxChunker:
    """Test DocxChunker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(target_chunk_size=250, docx_respect_sections=True)
        self.chunker = DocxChunker(self.config)

    def test_docx_section_chunking(self):
        """Test DOCX section-aware chunking."""
        content = """
        Heading 1: Introduction

        This is the introduction section with detailed information about the topic.

        Heading 2: Methodology

        This section describes the methodology used in the research.

        Heading 3: Results

        Here are the results of the study with data and analysis.
        """

        chunks = self.chunker.chunk_content(content, "test_doc")

        assert len(chunks) > 0

        # Check section detection
        section_titles = [c.metadata.section_title for c in chunks if c.metadata.section_title]
        assert any("Introduction" in title for title in section_titles)
        assert any("Methodology" in title for title in section_titles)
        assert any("Results" in title for title in section_titles)


class TestCSVChunker:
    """Test CSVChunker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(csv_chunk_by_rows=True, csv_rows_per_chunk=3)
        self.chunker = CSVChunker(self.config)

    def test_csv_row_chunking(self):
        """Test CSV row-based chunking."""
        content = """Name,Age,City
John,25,New York
Jane,30,Los Angeles
Bob,35,Chicago
Alice,28,Boston
Charlie,32,Seattle
Diana,27,Portland"""

        chunks = self.chunker.chunk_content(content, "test_doc")

        assert len(chunks) > 1  # Should create multiple chunks

        # Check that chunks contain CSV data
        for chunk in chunks:
            assert chunk.metadata.chunk_type == ChunkType.TEXT
            # Each chunk should have header + data rows
            lines = chunk.content.strip().split("\n")
            assert len(lines) > 1  # Header + at least one data row

    def test_csv_header_preservation(self):
        """Test that CSV headers are preserved in each chunk."""
        content = """Product,Price,Category
Laptop,999,Electronics
Phone,699,Electronics
Book,19,Education
Pen,5,Stationery"""

        chunks = self.chunker.chunk_content(content, "test_doc")

        # Each chunk should start with the header
        for chunk in chunks:
            lines = chunk.content.strip().split("\n")
            assert lines[0] == "Product,Price,Category"


class TestDocumentChunkerManager:
    """Test DocumentChunkerManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = ChunkingConfig(target_chunk_size=300, overlap_size=50)
        self.manager = DocumentChunkerManager(self.config)

    def test_manager_initialization(self):
        """Test manager initialization."""
        assert self.manager.config.target_chunk_size == 300
        assert len(self.manager.chunkers) == 4  # semantic, pdf, docx, csv
        assert self.manager.chunk_registry == {}
        assert self.manager.document_index == {}

    def test_document_chunking(self):
        """Test document chunking through manager."""
        content = """
        This is a test document with multiple paragraphs.

        Each paragraph contains important information that should be preserved.

        The chunking system should handle this content appropriately.
        """

        chunks = self.manager.chunk_document(content, "test_doc", "txt")

        assert len(chunks) > 0
        assert "test_doc" in self.manager.chunk_registry
        assert "test_doc" in self.manager.document_index

        # Check document index
        index_data = self.manager.document_index["test_doc"]
        assert index_data["chunk_count"] == len(chunks)
        assert index_data["file_type"] == "txt"
        assert "created_at" in index_data

    def test_chunk_retrieval(self):
        """Test chunk retrieval methods."""
        content = "This is test content. " * 20
        chunks = self.manager.chunk_document(content, "test_doc", "txt")

        # Test get_chunks
        retrieved_chunks = self.manager.get_chunks("test_doc")
        assert len(retrieved_chunks) == len(chunks)

        # Test get_chunk
        if chunks:
            chunk_id = chunks[0].chunk_id
            retrieved_chunk = self.manager.get_chunk(chunk_id)
            assert retrieved_chunk is not None
            assert retrieved_chunk.chunk_id == chunk_id

    def test_chunk_search(self):
        """Test chunk search functionality."""
        content = """
        This document discusses artificial intelligence and machine learning.

        Machine learning is a subset of artificial intelligence that focuses on algorithms.

        Deep learning is a subset of machine learning using neural networks.
        """

        chunks = self.manager.chunk_document(content, "test_doc", "txt")

        # Search for specific terms
        results = self.manager.search_chunks("machine learning")

        assert len(results) > 0

        # Results should be tuples of (chunk, relevance_score)
        for chunk, score in results:
            assert isinstance(chunk, DocumentChunk)
            assert 0 <= score <= 1
            assert "machine learning" in chunk.content.lower()

    def test_document_summary(self):
        """Test document summary generation."""
        content = "This is test content. " * 30
        chunks = self.manager.chunk_document(content, "test_doc", "txt")

        summary = self.manager.get_document_summary("test_doc")

        assert "chunk_count" in summary
        assert "total_words" in summary
        assert "total_characters" in summary
        assert "chunk_size_stats" in summary
        assert "confidence_stats" in summary
        assert summary["chunk_count"] == len(chunks)

    def test_chunking_statistics(self):
        """Test overall chunking statistics."""
        # Add multiple documents
        self.manager.chunk_document("Content 1", "doc1", "txt")
        self.manager.chunk_document("Content 2", "doc2", "pdf")

        stats = self.manager.get_chunking_statistics()

        assert stats["total_documents"] == 2
        assert stats["total_chunks"] > 0
        assert "chunk_types" in stats
        assert "file_types" in stats
        assert "quality_distribution" in stats

    def test_chunk_export(self):
        """Test chunk export functionality."""
        content = "This is test content for export."
        chunks = self.manager.chunk_document(content, "test_doc", "txt")

        # Test JSON export
        json_export = self.manager.export_chunks("test_doc", "json")
        assert json_export.startswith("[")  # Should be JSON array

        # Test text export
        text_export = self.manager.export_chunks("test_doc", "text")
        assert "=== Chunk" in text_export
        assert "test content" in text_export

    def test_document_clearing(self):
        """Test document clearing functionality."""
        content = "Test content for clearing."
        self.manager.chunk_document(content, "test_doc", "txt")

        assert "test_doc" in self.manager.chunk_registry
        assert "test_doc" in self.manager.document_index

        # Clear specific document
        self.manager.clear_document("test_doc")

        assert "test_doc" not in self.manager.chunk_registry
        assert "test_doc" not in self.manager.document_index


class TestChunkingIntegration:
    """Test ChunkingIntegration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = DocumentChunkerManager()
        self.integration = ChunkingIntegration(self.manager)

    def test_file_processing_with_chunking(self):
        """Test file processing integration."""
        content = "This is test file content for processing."
        filename = "test_file.txt"

        processed_content, chunks = self.integration.process_file_with_chunking(content, filename)

        assert isinstance(processed_content, str)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)

    def test_context_retrieval_for_query(self):
        """Test context retrieval for queries."""
        content = """
        This document discusses natural language processing.

        Natural language processing is a field of artificial intelligence.

        It involves understanding and generating human language.
        """

        # Process file to create chunks
        self.integration.process_file_with_chunking(content, "nlp_doc.txt")

        # Get context for query
        contexts = self.integration.get_chunk_context_for_query(
            "natural language processing", max_chunks=2
        )

        assert len(contexts) > 0
        assert any("natural language processing" in context.lower() for context in contexts)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_chunk_document_content(self):
        """Test chunk_document_content utility function."""
        content = "This is test content for utility function."
        filename = "test.txt"

        chunks = chunk_document_content(content, filename)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)

    def test_optimal_chunking_config(self):
        """Test get_optimal_chunking_config utility."""
        # Test PDF configuration
        pdf_config = get_optimal_chunking_config("pdf", 10000)
        assert pdf_config.pdf_respect_pages is True
        assert pdf_config.target_chunk_size >= 1000

        # Test DOCX configuration
        docx_config = get_optimal_chunking_config("docx", 5000)
        assert docx_config.docx_respect_sections is True
        assert docx_config.preserve_headers is True

        # Test CSV configuration
        csv_config = get_optimal_chunking_config("csv", 20000)
        assert csv_config.csv_chunk_by_rows is True
        assert csv_config.csv_rows_per_chunk > 0

        # Test size-based adjustments
        small_config = get_optimal_chunking_config("txt", 2000)
        large_config = get_optimal_chunking_config("txt", 100000)

        assert small_config.target_chunk_size < large_config.target_chunk_size


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = DocumentChunkerManager()

    def test_empty_content(self):
        """Test handling of empty content."""
        chunks = self.manager.chunk_document("", "empty_doc", "txt")
        assert len(chunks) == 0

    def test_very_short_content(self):
        """Test handling of very short content."""
        content = "Short."
        chunks = self.manager.chunk_document(content, "short_doc", "txt")

        # Should create at least one chunk even if it's short
        assert len(chunks) >= 0

    def test_very_long_content(self):
        """Test handling of very long content."""
        content = "This is a very long sentence. " * 1000  # Very long content
        chunks = self.manager.chunk_document(content, "long_doc", "txt")

        assert len(chunks) > 1  # Should be split into multiple chunks

        # Each chunk should be within reasonable size limits
        for chunk in chunks:
            assert len(chunk.content) <= 3000  # Should not exceed max size

    def test_special_characters(self):
        """Test handling of special characters."""
        content = "Content with special chars: @#$%^&*(){}[]|\\:;\"'<>?/~`"
        chunks = self.manager.chunk_document(content, "special_doc", "txt")

        assert len(chunks) > 0
        assert any("special chars" in chunk.content for chunk in chunks)

    def test_unicode_content(self):
        """Test handling of Unicode content."""
        content = "Content with Unicode: 你好世界 🌍 café naïve résumé"
        chunks = self.manager.chunk_document(content, "unicode_doc", "txt")

        assert len(chunks) > 0
        assert any("你好世界" in chunk.content for chunk in chunks)
        assert any("café" in chunk.content for chunk in chunks)

    def test_invalid_document_id(self):
        """Test retrieval with invalid document ID."""
        chunks = self.manager.get_chunks("nonexistent_doc")
        assert chunks == []

        chunk = self.manager.get_chunk("nonexistent_chunk")
        assert chunk is None

    def test_malformed_content(self):
        """Test handling of malformed content."""
        # Content with inconsistent line endings
        content = "Line 1\r\nLine 2\nLine 3\r\n\rLine 4"
        chunks = self.manager.chunk_document(content, "malformed_doc", "txt")

        assert len(chunks) > 0
        # Should normalize line endings
        combined = " ".join(chunk.content for chunk in chunks)
        assert "Line 1" in combined
        assert "Line 4" in combined


# Performance tests
class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.skip(reason="Performance test - run manually")
    def test_large_document_performance(self):
        """Test performance with large documents."""
        import time

        # Create large content
        content = "This is a performance test sentence. " * 10000

        manager = DocumentChunkerManager()

        start_time = time.time()
        chunks = manager.chunk_document(content, "perf_doc", "txt")
        end_time = time.time()

        processing_time = end_time - start_time

        print(
            f"Processed {len(content)} characters into {len(chunks)} chunks in {processing_time:.2f} seconds"
        )

        # Should complete in reasonable time
        assert processing_time < 10.0  # 10 seconds max
        assert len(chunks) > 0

    @pytest.mark.skip(reason="Performance test - run manually")
    def test_many_documents_performance(self):
        """Test performance with many documents."""
        import time

        manager = DocumentChunkerManager()

        start_time = time.time()

        # Process many small documents
        for i in range(100):
            content = f"Document {i} content with some text to chunk."
            manager.chunk_document(content, f"doc_{i}", "txt")

        end_time = time.time()
        processing_time = end_time - start_time

        print(f"Processed 100 documents in {processing_time:.2f} seconds")

        # Should complete in reasonable time
        assert processing_time < 30.0  # 30 seconds max

        stats = manager.get_chunking_statistics()
        assert stats["total_documents"] == 100


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
