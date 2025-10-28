"""Unit tests for ChunkingService.

Sprint 16 Feature 16.1 - Unified Chunking Service
Tests for src/core/chunking_service.py
"""

import pytest

from src.core.chunk import Chunk, ChunkStrategy
from src.core.chunking_service import ChunkingService, get_chunking_service, reset_chunking_service


class TestChunkingServiceInitialization:
    """Test ChunkingService initialization and configuration."""

    def test_default_initialization(self):
        """Test service initializes with default adaptive strategy."""
        service = ChunkingService()
        assert service.strategy.method == "adaptive"
        assert service.strategy.chunk_size == 512
        assert service.strategy.overlap == 128

    def test_custom_strategy_initialization(self):
        """Test service initializes with custom strategy."""
        strategy = ChunkStrategy(method="fixed", chunk_size=1024, overlap=256)
        service = ChunkingService(strategy=strategy)

        assert service.strategy.method == "fixed"
        assert service.strategy.chunk_size == 1024
        assert service.strategy.overlap == 256

    def test_singleton_pattern(self):
        """Test get_chunking_service returns singleton."""
        reset_chunking_service()

        service1 = get_chunking_service()
        service2 = get_chunking_service()

        assert service1 is service2

    def test_singleton_with_custom_strategy_returns_new_instance(self):
        """Test custom strategy bypasses singleton."""
        reset_chunking_service()

        service1 = get_chunking_service()
        custom_strategy = ChunkStrategy(method="fixed", chunk_size=1024)
        service2 = get_chunking_service(strategy=custom_strategy)

        assert service1 is not service2
        assert service2.strategy.method == "fixed"


class TestChunkingServiceFixed:
    """Test fixed strategy (tiktoken-based) chunking."""

    def test_fixed_strategy_simple_text(self):
        """Test fixed chunking with simple text."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=50)
        )

        text = "This is a sample document. " * 20  # ~140 words
        chunks = service.chunk_document("doc_001", text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all(chunk.document_id == "doc_001" for chunk in chunks)
        assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))

    def test_fixed_strategy_chunk_ids_unique(self):
        """Test fixed strategy generates unique chunk_ids."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=50)
        )

        text = "Sample text. " * 50
        chunks = service.chunk_document("doc_001", text)

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))  # All unique

    def test_fixed_strategy_chunk_ids_deterministic(self):
        """Test fixed strategy generates same chunk_ids for same input."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=50)
        )

        text = "Deterministic test text. " * 20

        chunks1 = service.chunk_document("doc_001", text)
        chunks2 = service.chunk_document("doc_001", text)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
            assert c1.content == c2.content

    def test_fixed_strategy_respects_chunk_size(self):
        """Test fixed strategy respects token chunk_size limit."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=40)
        )

        text = "Word " * 500  # Lots of tokens
        chunks = service.chunk_document("doc_001", text)

        # All chunks should be <= chunk_size tokens (except possibly last)
        for chunk in chunks[:-1]:  # All but last
            assert chunk.token_count <= 200

    def test_fixed_strategy_with_metadata(self):
        """Test fixed strategy preserves metadata."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=50)
        )

        text = "Sample text with metadata. " * 10
        metadata = {"source": "test.md", "author": "test"}

        chunks = service.chunk_document("doc_001", text, metadata=metadata)

        assert all(chunk.metadata == metadata for chunk in chunks)


class TestChunkingServiceAdaptive:
    """Test adaptive strategy (sentence-aware) chunking."""

    def test_adaptive_strategy_simple_text(self):
        """Test adaptive chunking with simple text."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="adaptive", chunk_size=512, overlap=128)
        )

        text = "First sentence. Second sentence. Third sentence. " * 20
        chunks = service.chunk_document("doc_002", text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert all(chunk.document_id == "doc_002" for chunk in chunks)

    def test_adaptive_strategy_respects_sentence_boundaries(self):
        """Test adaptive strategy respects sentence boundaries."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="adaptive", chunk_size=200, overlap=50)
        )

        # Short sentences, should not split mid-sentence
        text = "Sentence one. Sentence two. Sentence three. Sentence four."
        chunks = service.chunk_document("doc_002", text)

        # Check that sentences are not split
        for chunk in chunks:
            # Each sentence should end with a period or be complete
            assert chunk.content.strip()[-1] in [".", "?", "!"] or chunk == chunks[-1]

    def test_adaptive_strategy_with_long_sentence(self):
        """Test adaptive strategy handles very long sentences."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="adaptive", chunk_size=200, overlap=50)
        )

        # One very long sentence
        text = "This is a very long sentence " * 50 + "."
        chunks = service.chunk_document("doc_002", text)

        # Should still chunk despite being one sentence
        assert len(chunks) > 1


class TestChunkingServiceParagraph:
    """Test paragraph strategy (semantic boundaries) chunking."""

    def test_paragraph_strategy_simple_text(self):
        """Test paragraph chunking with simple text."""
        service = ChunkingService(
            strategy=ChunkStrategy(
                method="paragraph", chunk_size=512, overlap=128, separator="\n\n"
            )
        )

        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        chunks = service.chunk_document("doc_003", text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

    def test_paragraph_strategy_custom_separator(self):
        """Test paragraph strategy with custom separator."""
        service = ChunkingService(
            strategy=ChunkStrategy(
                method="paragraph", chunk_size=512, overlap=128, separator="\n---\n"
            )
        )

        text = "Section one.\n---\nSection two.\n---\nSection three."
        chunks = service.chunk_document("doc_003", text)

        assert len(chunks) > 0


class TestChunkingServiceSentence:
    """Test sentence strategy (regex-based) chunking."""

    def test_sentence_strategy_simple_text(self):
        """Test sentence chunking with simple text."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="sentence", chunk_size=200, overlap=50)
        )

        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = service.chunk_document("doc_004", text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

    def test_sentence_strategy_respects_sentence_boundaries(self):
        """Test sentence strategy respects sentence endings."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="sentence", chunk_size=200, overlap=40)
        )

        text = "Question one? Statement two. Exclamation three!"
        chunks = service.chunk_document("doc_004", text)

        # Each chunk should contain complete sentences
        for chunk in chunks:
            content = chunk.content.strip()
            if content:
                # Should end with sentence terminator
                assert content[-1] in [".", "?", "!"]


class TestChunkingServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content_raises_error(self):
        """Test chunking empty content raises ValueError."""
        service = ChunkingService()

        with pytest.raises(ValueError, match="Content cannot be empty"):
            service.chunk_document("doc_001", "")

    def test_whitespace_only_content_raises_error(self):
        """Test chunking whitespace-only content raises ValueError."""
        service = ChunkingService()

        with pytest.raises(ValueError, match="Content cannot be empty"):
            service.chunk_document("doc_001", "   \n\n   ")

    def test_single_word_content(self):
        """Test chunking single word content."""
        service = ChunkingService()

        chunks = service.chunk_document("doc_001", "Hello")

        assert len(chunks) == 1
        assert chunks[0].content.strip() == "Hello"
        assert chunks[0].chunk_index == 0

    def test_very_long_document(self):
        """Test chunking very long document."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=512, overlap=128)
        )

        # Generate large document (10K words)
        text = ("Word " * 100 + ". ") * 100

        chunks = service.chunk_document("doc_large", text)

        assert len(chunks) > 10  # Should produce many chunks
        assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))

    def test_invalid_strategy_method_raises_error(self):
        """Test invalid chunking method raises error."""
        service = ChunkingService()
        service.strategy.method = "invalid_method"

        with pytest.raises(ValueError, match="Unknown chunking method"):
            service.chunk_document("doc_001", "Sample text")

    def test_unicode_content(self):
        """Test chunking with unicode content."""
        service = ChunkingService()

        text = "Hello 世界! Γειά σου κόσμε! مرحبا بالعالم!"
        chunks = service.chunk_document("doc_unicode", text)

        assert len(chunks) > 0
        assert any("世界" in chunk.content for chunk in chunks)

    def test_special_characters_content(self):
        """Test chunking with special characters."""
        service = ChunkingService()

        text = "Special chars: @#$%^&*() <html> {json: 'value'} [array]"
        chunks = service.chunk_document("doc_special", text)

        assert len(chunks) > 0
        assert any("@#$%^&*()" in chunk.content for chunk in chunks)


class TestChunkingServiceMetadata:
    """Test metadata handling."""

    def test_metadata_preserved_in_chunks(self):
        """Test metadata is preserved in all chunks."""
        service = ChunkingService()

        metadata = {
            "source": "test.md",
            "author": "test_user",
            "tags": ["test", "chunking"],
            "version": 1,
        }

        text = "Sample text. " * 100
        chunks = service.chunk_document("doc_meta", text, metadata=metadata)

        for chunk in chunks:
            assert chunk.metadata["source"] == "test.md"
            assert chunk.metadata["author"] == "test_user"
            assert chunk.metadata["tags"] == ["test", "chunking"]
            assert chunk.metadata["version"] == 1

    def test_no_metadata_defaults_to_empty_dict(self):
        """Test chunks without metadata have empty dict."""
        service = ChunkingService()

        text = "Sample text without metadata."
        chunks = service.chunk_document("doc_no_meta", text)

        for chunk in chunks:
            assert chunk.metadata == {}


class TestChunkingServiceConversions:
    """Test chunk format conversions."""

    def test_chunks_convert_to_qdrant_format(self):
        """Test chunks can be converted to Qdrant format."""
        service = ChunkingService()

        text = "Sample text for Qdrant conversion."
        chunks = service.chunk_document("doc_qdrant", text, metadata={"key": "value"})

        for chunk in chunks:
            payload = chunk.to_qdrant_payload()
            assert "text" in payload
            assert "chunk_id" in payload
            assert "document_id" in payload
            assert "chunk_index" in payload
            assert payload["key"] == "value"

    def test_chunks_convert_to_bm25_format(self):
        """Test chunks can be converted to BM25 format."""
        service = ChunkingService()

        text = "Sample text for BM25 conversion."
        chunks = service.chunk_document("doc_bm25", text)

        for chunk in chunks:
            bm25_doc = chunk.to_bm25_document()
            assert "text" in bm25_doc
            assert "chunk_id" in bm25_doc
            assert "document_id" in bm25_doc

    def test_chunks_convert_to_lightrag_format(self):
        """Test chunks can be converted to LightRAG format."""
        service = ChunkingService(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=40)
        )

        text = "Sample text for LightRAG conversion."
        chunks = service.chunk_document("doc_lightrag", text)

        for chunk in chunks:
            lightrag_chunk = chunk.to_lightrag_format()
            assert "text" in lightrag_chunk
            assert "chunk_id" in lightrag_chunk
            assert "document_id" in lightrag_chunk
            assert "tokens" in lightrag_chunk


class TestChunkingServicePrometheusMetrics:
    """Test Prometheus metrics collection."""

    def test_metrics_recorded_on_chunking(self):
        """Test chunking records Prometheus metrics."""
        from src.core.chunking_service import (
            chunks_created_total,
            documents_chunked_total,
        )

        service = ChunkingService()

        # Get initial metric values
        initial_chunks = chunks_created_total.labels(strategy="adaptive")._value._value
        initial_docs = documents_chunked_total.labels(strategy="adaptive")._value._value

        # Chunk a document
        text = "Sample text for metrics testing. " * 10
        chunks = service.chunk_document("doc_metrics", text)

        # Verify metrics increased
        final_chunks = chunks_created_total.labels(strategy="adaptive")._value._value
        final_docs = documents_chunked_total.labels(strategy="adaptive")._value._value

        assert final_chunks > initial_chunks
        assert final_docs > initial_docs
        assert final_chunks - initial_chunks == len(chunks)
        assert final_docs - initial_docs == 1


class TestChunkingServicePerformance:
    """Test chunking performance and benchmarks."""

    def test_chunking_completes_in_reasonable_time(self):
        """Test chunking completes within acceptable time."""
        import time

        service = ChunkingService()

        # Large document (5K words)
        text = ("Word " * 50 + ". ") * 100

        start = time.time()
        chunks = service.chunk_document("doc_perf", text)
        duration = time.time() - start

        # Should complete within 1 second for 5K words
        assert duration < 1.0
        assert len(chunks) > 0

    def test_multiple_documents_chunking_performance(self):
        """Test chunking multiple documents in sequence."""
        import time

        service = ChunkingService()

        texts = [f"Document {i} text. " * 100 for i in range(10)]

        start = time.time()
        for i, text in enumerate(texts):
            chunks = service.chunk_document(f"doc_{i}", text)
            assert len(chunks) > 0
        duration = time.time() - start

        # Should complete within 2 seconds for 10 documents
        assert duration < 2.0
