"""Unit tests for Chunk model.

Sprint 16 Feature 16.1 - Unified Chunking Service
Tests for src/core/models/chunk.py
"""

import pytest
from pydantic import ValidationError

from src.core.chunk import Chunk, ChunkStrategy


class TestChunkStrategy:
    """Test ChunkStrategy configuration model."""

    def test_default_strategy(self):
        """Test default strategy configuration."""
        strategy = ChunkStrategy()
        assert strategy.method == "adaptive"
        assert strategy.chunk_size == 512
        assert strategy.overlap == 128
        assert strategy.separator == "\n\n"

    def test_custom_strategy(self):
        """Test custom strategy configuration."""
        strategy = ChunkStrategy(
            method="fixed",
            chunk_size=1024,
            overlap=256,
            separator="\n",
        )
        assert strategy.method == "fixed"
        assert strategy.chunk_size == 1024
        assert strategy.overlap == 256
        assert strategy.separator == "\n"

    def test_strategy_validation_chunk_size_too_small(self):
        """Test chunk_size validation (min 128)."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkStrategy(chunk_size=100)
        assert "chunk_size" in str(exc_info.value)

    def test_strategy_validation_chunk_size_too_large(self):
        """Test chunk_size validation (max 2048)."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkStrategy(chunk_size=3000)
        assert "chunk_size" in str(exc_info.value)

    def test_strategy_validation_overlap_too_large(self):
        """Test overlap validation (max 512)."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkStrategy(overlap=600)
        assert "overlap" in str(exc_info.value)

    def test_strategy_validation_overlap_gte_chunk_size(self):
        """Test overlap must be less than chunk_size."""
        with pytest.raises(ValidationError) as exc_info:
            ChunkStrategy(chunk_size=512, overlap=512)
        assert "overlap" in str(exc_info.value).lower()

    def test_strategy_method_values(self):
        """Test all supported chunking methods."""
        for method in ["fixed", "adaptive", "paragraph", "sentence"]:
            strategy = ChunkStrategy(method=method)
            assert strategy.method == method

    def test_strategy_invalid_method(self):
        """Test invalid chunking method raises error."""
        with pytest.raises(ValidationError):
            ChunkStrategy(method="invalid_method")


class TestChunk:
    """Test Chunk model."""

    def test_create_chunk(self):
        """Test creating a valid chunk."""
        chunk = Chunk(
            chunk_id="abc123def4567890",  # 16 chars minimum
            document_id="doc_001",
            chunk_index=0,
            content="Sample chunk content",
            start_char=0,
            end_char=20,
            metadata={"source": "test.md"},
            token_count=4,
            overlap_tokens=0,
        )

        assert chunk.chunk_id == "abc123def4567890"
        assert chunk.document_id == "doc_001"
        assert chunk.chunk_index == 0
        assert chunk.content == "Sample chunk content"
        assert chunk.start_char == 0
        assert chunk.end_char == 20
        assert chunk.metadata == {"source": "test.md"}
        assert chunk.token_count == 4
        assert chunk.overlap_tokens == 0

    def test_chunk_validation_empty_content(self):
        """Test chunk validation rejects empty content."""
        with pytest.raises(ValidationError) as exc_info:
            Chunk(
                chunk_id="abc123def4567890",
                document_id="doc_001",
                chunk_index=0,
                content="",
                start_char=0,
                end_char=0,
            )
        assert "content" in str(exc_info.value)

    def test_chunk_validation_negative_chunk_index(self):
        """Test chunk_index must be non-negative."""
        with pytest.raises(ValidationError):
            Chunk(
                chunk_id="abc123def4567890",
                document_id="doc_001",
                chunk_index=-1,
                content="Sample",
                start_char=0,
                end_char=6,
            )

    def test_chunk_validation_end_char_before_start_char(self):
        """Test end_char must be >= start_char."""
        with pytest.raises(ValidationError) as exc_info:
            Chunk(
                chunk_id="abc123def4567890",
                document_id="doc_001",
                chunk_index=0,
                content="Sample",
                start_char=100,
                end_char=50,
            )
        assert "end_char" in str(exc_info.value)

    def test_chunk_validation_short_chunk_id(self):
        """Test chunk_id minimum length validation."""
        with pytest.raises(ValidationError):
            Chunk(
                chunk_id="short",  # Too short (< 16 chars)
                document_id="doc_001",
                chunk_index=0,
                content="Sample",
                start_char=0,
                end_char=6,
            )

    def test_chunk_validation_empty_document_id(self):
        """Test document_id cannot be empty."""
        with pytest.raises(ValidationError):
            Chunk(
                chunk_id="abc123def4567890",
                document_id="",
                chunk_index=0,
                content="Sample",
                start_char=0,
                end_char=6,
            )

    def test_generate_chunk_id(self):
        """Test deterministic chunk_id generation."""
        chunk_id_1 = Chunk.generate_chunk_id("doc_001", 0, "Sample text")
        chunk_id_2 = Chunk.generate_chunk_id("doc_001", 0, "Sample text")

        # Same inputs should generate same chunk_id
        assert chunk_id_1 == chunk_id_2
        assert len(chunk_id_1) == 16  # SHA-256 prefix

        # Different inputs should generate different chunk_ids
        chunk_id_3 = Chunk.generate_chunk_id("doc_001", 1, "Sample text")
        assert chunk_id_1 != chunk_id_3

        chunk_id_4 = Chunk.generate_chunk_id("doc_002", 0, "Sample text")
        assert chunk_id_1 != chunk_id_4

        chunk_id_5 = Chunk.generate_chunk_id("doc_001", 0, "Different text")
        assert chunk_id_1 != chunk_id_5

    def test_to_qdrant_payload(self):
        """Test conversion to Qdrant payload format."""
        chunk = Chunk(
            chunk_id="abc123def4567890",
            document_id="doc_001",
            chunk_index=2,
            content="Sample chunk content",
            start_char=100,
            end_char=120,
            metadata={"source": "test.md", "section": "intro"},
            token_count=4,
            overlap_tokens=2,
        )

        payload = chunk.to_qdrant_payload()

        assert payload["chunk_id"] == "abc123def456"
        assert payload["document_id"] == "doc_001"
        assert payload["chunk_index"] == 2
        assert payload["text"] == "Sample chunk content"
        assert payload["start_char"] == 100
        assert payload["end_char"] == 120
        assert payload["token_count"] == 4
        assert payload["source"] == "test.md"
        assert payload["section"] == "intro"

    def test_to_bm25_document(self):
        """Test conversion to BM25 document format."""
        chunk = Chunk(
            chunk_id="abc123def4567890",
            document_id="doc_001",
            chunk_index=1,
            content="Sample chunk for BM25",
            start_char=50,
            end_char=72,
            metadata={"category": "technical"},
            token_count=5,
            overlap_tokens=1,
        )

        bm25_doc = chunk.to_bm25_document()

        assert bm25_doc["text"] == "Sample chunk for BM25"
        assert bm25_doc["chunk_id"] == "abc123def456"
        assert bm25_doc["document_id"] == "doc_001"
        assert bm25_doc["chunk_index"] == 1
        assert bm25_doc["token_count"] == 5
        assert bm25_doc["category"] == "technical"

    def test_to_lightrag_format(self):
        """Test conversion to LightRAG format for Neo4j."""
        chunk = Chunk(
            chunk_id="abc123def4567890",
            document_id="doc_001",
            chunk_index=3,
            content="Sample chunk for LightRAG",
            start_char=200,
            end_char=226,
            metadata={"author": "test"},
            token_count=5,
            overlap_tokens=2,
        )

        lightrag_chunk = chunk.to_lightrag_format()

        assert lightrag_chunk["chunk_id"] == "abc123def456"
        assert lightrag_chunk["text"] == "Sample chunk for LightRAG"
        assert lightrag_chunk["document_id"] == "doc_001"
        assert lightrag_chunk["chunk_index"] == 3
        assert lightrag_chunk["tokens"] == 5
        assert lightrag_chunk["start_char"] == 200
        assert lightrag_chunk["end_char"] == 226

    def test_chunk_defaults(self):
        """Test chunk with default values."""
        chunk = Chunk(
            chunk_id="abc123def4567890",
            document_id="doc_001",
            chunk_index=0,
            content="Sample",
            start_char=0,
            end_char=6,
        )

        assert chunk.metadata == {}
        assert chunk.token_count == 0
        assert chunk.overlap_tokens == 0

    def test_chunk_json_serialization(self):
        """Test chunk can be serialized to JSON."""
        chunk = Chunk(
            chunk_id="abc123def4567890",
            document_id="doc_001",
            chunk_index=0,
            content="Sample",
            start_char=0,
            end_char=6,
            metadata={"key": "value"},
        )

        # Should not raise
        json_str = chunk.model_dump_json()
        assert "abc123def456" in json_str
        assert "doc_001" in json_str

    def test_chunk_from_dict(self):
        """Test chunk can be created from dictionary."""
        chunk_dict = {
            "chunk_id": "abc123def456",
            "document_id": "doc_001",
            "chunk_index": 0,
            "content": "Sample",
            "start_char": 0,
            "end_char": 6,
            "metadata": {},
            "token_count": 1,
            "overlap_tokens": 0,
        }

        chunk = Chunk(**chunk_dict)
        assert chunk.chunk_id == "abc123def456"
        assert chunk.document_id == "doc_001"
