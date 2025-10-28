"""Unit tests for Unified Ingestion Pipeline.

Sprint 16: Coverage improvement - 0% → 70%

Tests cover:
- Pipeline initialization
- Qdrant-only ingestion
- Neo4j-only ingestion
- Parallel ingestion (Qdrant + Neo4j)
- Error handling
- PPTX support (Feature 16.5)
- Optimized LightRAG integration (Feature 16.6)
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.components.shared.unified_ingestion import (
    UnifiedIngestionPipeline,
    IngestionResult,
    get_unified_pipeline,
)


class TestUnifiedIngestionPipeline:
    """Test UnifiedIngestionPipeline initialization and configuration."""

    def test_initialization_defaults(self):
        """Test pipeline initializes with default settings."""
        pipeline = UnifiedIngestionPipeline()

        assert pipeline.allowed_base_path is None
        assert pipeline.enable_qdrant is True
        assert pipeline.enable_neo4j is True
        assert pipeline.qdrant_pipeline is not None

    def test_initialization_with_base_path(self):
        """Test pipeline initializes with custom base path."""
        base_path = "/data/documents"
        pipeline = UnifiedIngestionPipeline(allowed_base_path=base_path)

        assert pipeline.allowed_base_path == Path(base_path)

    def test_initialization_qdrant_only(self):
        """Test pipeline with Neo4j disabled."""
        pipeline = UnifiedIngestionPipeline(enable_neo4j=False)

        assert pipeline.enable_qdrant is True
        assert pipeline.enable_neo4j is False

    def test_initialization_neo4j_only(self):
        """Test pipeline with Qdrant disabled."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=False)

        assert pipeline.enable_qdrant is False
        assert pipeline.enable_neo4j is True


class TestIngestionResult:
    """Test IngestionResult Pydantic model."""

    def test_ingestion_result_creation(self):
        """Test IngestionResult can be created with all fields."""
        result = IngestionResult(
            total_documents=10,
            qdrant_indexed=10,
            bm25_indexed=10,
            neo4j_entities=42,
            neo4j_relationships=35,
            errors=[],
            duration_seconds=5.2,
        )

        assert result.total_documents == 10
        assert result.qdrant_indexed == 10
        assert result.bm25_indexed == 10
        assert result.neo4j_entities == 42
        assert result.neo4j_relationships == 35
        assert result.errors == []
        assert result.duration_seconds == 5.2

    def test_ingestion_result_with_errors(self):
        """Test IngestionResult with error messages."""
        result = IngestionResult(
            total_documents=10,
            qdrant_indexed=8,
            bm25_indexed=8,
            neo4j_entities=30,
            neo4j_relationships=25,
            errors=["Document 9 failed to index", "Document 10 failed to index"],
            duration_seconds=6.5,
        )

        assert len(result.errors) == 2
        assert "Document 9" in result.errors[0]


class TestQdrantIngestion:
    """Test Qdrant indexing functionality."""

    @pytest.mark.asyncio
    async def test_index_to_qdrant_success(self):
        """Test successful Qdrant indexing."""
        pipeline = UnifiedIngestionPipeline()

        # Mock DocumentIngestionPipeline.index_documents
        mock_stats = {
            "documents_loaded": 5,
            "points_indexed": 5,
            "chunks_created": 25,
        }
        pipeline.qdrant_pipeline.index_documents = AsyncMock(return_value=mock_stats)

        result = await pipeline._index_to_qdrant("data/test_docs")

        assert result["documents_loaded"] == 5
        assert result["points_indexed"] == 5
        assert result["chunks_created"] == 25
        pipeline.qdrant_pipeline.index_documents.assert_called_once_with(
            input_dir="data/test_docs"
        )

    @pytest.mark.asyncio
    async def test_index_to_qdrant_empty_directory(self):
        """Test Qdrant indexing with empty directory."""
        pipeline = UnifiedIngestionPipeline()

        mock_stats = {
            "documents_loaded": 0,
            "points_indexed": 0,
            "chunks_created": 0,
        }
        pipeline.qdrant_pipeline.index_documents = AsyncMock(return_value=mock_stats)

        result = await pipeline._index_to_qdrant("data/empty")

        assert result["documents_loaded"] == 0
        assert result["points_indexed"] == 0


class TestNeo4jIngestion:
    """Test Neo4j indexing functionality."""

    @pytest.mark.asyncio
    async def test_index_to_neo4j_success(self):
        """Test successful Neo4j indexing via LightRAG.

        Sprint 16 Feature 16.6: Tests optimized LightRAG integration.
        """
        pipeline = UnifiedIngestionPipeline()

        # Mock SimpleDirectoryReader
        with patch("src.components.shared.unified_ingestion.SimpleDirectoryReader") as mock_reader_class:
            # Mock documents
            mock_doc1 = MagicMock()
            mock_doc1.text = "Klaus Pommer works at Pommer IT-Consulting."
            mock_doc1.metadata = {"source": "doc1.txt"}
            mock_doc1.doc_id = "doc1"

            mock_doc2 = MagicMock()
            mock_doc2.text = "AEGIS RAG is a hybrid RAG system."
            mock_doc2.metadata = {"source": "doc2.txt"}
            mock_doc2.doc_id = "doc2"

            mock_reader = MagicMock()
            mock_reader.load_data.return_value = [mock_doc1, mock_doc2]
            mock_reader_class.return_value = mock_reader

            # Mock LightRAG wrapper
            with patch(
                "src.components.shared.unified_ingestion.get_lightrag_wrapper_async"
            ) as mock_get_lightrag:
                mock_lightrag = MagicMock()
                mock_lightrag.insert_documents_optimized = AsyncMock()
                mock_lightrag.get_stats = AsyncMock(
                    return_value={"entity_count": 10, "relationship_count": 8}
                )
                mock_get_lightrag.return_value = mock_lightrag

                result = await pipeline._index_to_neo4j("data/test_docs")

                # Verify results
                assert result["entity_count"] == 10
                assert result["relationship_count"] == 8

                # Verify SimpleDirectoryReader was called with PPTX support
                mock_reader_class.assert_called_once()
                call_kwargs = mock_reader_class.call_args[1]
                assert ".pptx" in call_kwargs["required_exts"]  # Sprint 16 Feature 16.5

                # Verify insert_documents_optimized was called (Sprint 16 Feature 16.6)
                mock_lightrag.insert_documents_optimized.assert_called_once()
                call_args = mock_lightrag.insert_documents_optimized.call_args[0][0]
                assert len(call_args) == 2
                assert call_args[0]["text"] == "Klaus Pommer works at Pommer IT-Consulting."
                assert call_args[0]["id"] == "doc1"  # Document ID for provenance

    @pytest.mark.asyncio
    async def test_index_to_neo4j_empty_directory(self):
        """Test Neo4j indexing with no documents."""
        pipeline = UnifiedIngestionPipeline()

        with patch("src.components.shared.unified_ingestion.SimpleDirectoryReader") as mock_reader_class:
            mock_reader = MagicMock()
            mock_reader.load_data.return_value = []
            mock_reader_class.return_value = mock_reader

            result = await pipeline._index_to_neo4j("data/empty")

            assert result["entity_count"] == 0
            assert result["relationship_count"] == 0

    @pytest.mark.asyncio
    async def test_index_to_neo4j_with_pptx_support(self):
        """Test Neo4j indexing includes PPTX files.

        Sprint 16 Feature 16.5: Verify PPTX support in Neo4j ingestion.
        """
        pipeline = UnifiedIngestionPipeline()

        with patch("src.components.shared.unified_ingestion.SimpleDirectoryReader") as mock_reader_class:
            # Mock PPTX document
            mock_pptx_doc = MagicMock()
            mock_pptx_doc.text = "Slide 1: Introduction\nSlide 2: Architecture"
            mock_pptx_doc.metadata = {"source": "presentation.pptx"}
            mock_pptx_doc.doc_id = "pptx_001"

            mock_reader = MagicMock()
            mock_reader.load_data.return_value = [mock_pptx_doc]
            mock_reader_class.return_value = mock_reader

            with patch(
                "src.components.shared.unified_ingestion.get_lightrag_wrapper_async"
            ) as mock_get_lightrag:
                mock_lightrag = MagicMock()
                mock_lightrag.insert_documents_optimized = AsyncMock()
                mock_lightrag.get_stats = AsyncMock(
                    return_value={"entity_count": 3, "relationship_count": 2}
                )
                mock_get_lightrag.return_value = mock_lightrag

                result = await pipeline._index_to_neo4j("data/presentations")

                # Verify PPTX was processed
                assert result["entity_count"] == 3
                mock_lightrag.insert_documents_optimized.assert_called_once()
                call_args = mock_lightrag.insert_documents_optimized.call_args[0][0]
                assert call_args[0]["text"] == "Slide 1: Introduction\nSlide 2: Architecture"


class TestParallelIngestion:
    """Test parallel ingestion to Qdrant and Neo4j."""

    @pytest.mark.asyncio
    async def test_ingest_directory_both_enabled(self):
        """Test parallel ingestion to both Qdrant and Neo4j."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=True, enable_neo4j=True)

        # Mock Qdrant indexing
        pipeline._index_to_qdrant = AsyncMock(
            return_value={
                "documents_loaded": 3,
                "points_indexed": 3,
                "chunks_created": 15,
            }
        )

        # Mock Neo4j indexing
        pipeline._index_to_neo4j = AsyncMock(
            return_value={"entity_count": 12, "relationship_count": 10}
        )

        result = await pipeline.ingest_directory("data/test_docs")

        # Verify both systems were called
        pipeline._index_to_qdrant.assert_called_once_with("data/test_docs")
        pipeline._index_to_neo4j.assert_called_once_with("data/test_docs")

        # Verify result
        assert result.total_documents == 3
        assert result.qdrant_indexed == 3
        assert result.bm25_indexed == 3
        assert result.neo4j_entities == 12
        assert result.neo4j_relationships == 10
        assert result.errors == []
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_ingest_directory_qdrant_only(self):
        """Test ingestion with Neo4j disabled."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=True, enable_neo4j=False)

        pipeline._index_to_qdrant = AsyncMock(
            return_value={
                "documents_loaded": 5,
                "points_indexed": 5,
                "chunks_created": 25,
            }
        )

        result = await pipeline.ingest_directory("data/test_docs")

        # Verify only Qdrant was called
        pipeline._index_to_qdrant.assert_called_once()
        assert result.total_documents == 5
        assert result.neo4j_entities == 0
        assert result.neo4j_relationships == 0

    @pytest.mark.asyncio
    async def test_ingest_directory_neo4j_only(self):
        """Test ingestion with Qdrant disabled."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=False, enable_neo4j=True)

        pipeline._index_to_neo4j = AsyncMock(
            return_value={"entity_count": 20, "relationship_count": 18}
        )

        result = await pipeline.ingest_directory("data/test_docs")

        # Verify only Neo4j was called
        pipeline._index_to_neo4j.assert_called_once()
        assert result.neo4j_entities == 20
        assert result.neo4j_relationships == 18
        assert result.total_documents == 0  # No Qdrant stats


class TestErrorHandling:
    """Test error handling in unified ingestion."""

    @pytest.mark.asyncio
    async def test_qdrant_error_handling(self):
        """Test graceful handling of Qdrant indexing errors."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=True, enable_neo4j=False)

        # Mock Qdrant failure
        pipeline._index_to_qdrant = AsyncMock(
            side_effect=Exception("Qdrant connection failed")
        )

        result = await pipeline.ingest_directory("data/test_docs")

        # Verify error was captured
        assert len(result.errors) == 1
        assert "Qdrant indexing failed" in result.errors[0]
        assert result.total_documents == 0

    @pytest.mark.asyncio
    async def test_neo4j_error_handling(self):
        """Test graceful handling of Neo4j indexing errors."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=False, enable_neo4j=True)

        # Mock Neo4j failure
        pipeline._index_to_neo4j = AsyncMock(
            side_effect=Exception("Neo4j connection refused")
        )

        result = await pipeline.ingest_directory("data/test_docs")

        # Verify error was captured
        assert len(result.errors) == 1
        assert "Neo4j indexing failed" in result.errors[0]
        assert result.neo4j_entities == 0

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """Test partial failure (Qdrant succeeds, Neo4j fails)."""
        pipeline = UnifiedIngestionPipeline(enable_qdrant=True, enable_neo4j=True)

        # Mock Qdrant success
        pipeline._index_to_qdrant = AsyncMock(
            return_value={
                "documents_loaded": 5,
                "points_indexed": 5,
                "chunks_created": 25,
            }
        )

        # Mock Neo4j failure
        pipeline._index_to_neo4j = AsyncMock(
            side_effect=Exception("Neo4j timeout")
        )

        result = await pipeline.ingest_directory("data/test_docs")

        # Verify partial success
        assert result.total_documents == 5
        assert result.qdrant_indexed == 5
        assert result.neo4j_entities == 0
        assert len(result.errors) == 1
        assert "Neo4j" in result.errors[0]


class TestSingletonPattern:
    """Test singleton pattern for UnifiedIngestionPipeline."""

    def test_get_unified_pipeline_singleton(self):
        """Test get_unified_pipeline returns same instance."""
        # Reset singleton
        import src.components.shared.unified_ingestion as module

        module._unified_pipeline = None

        instance1 = get_unified_pipeline()
        instance2 = get_unified_pipeline()

        assert instance1 is instance2
        assert isinstance(instance1, UnifiedIngestionPipeline)
