"""Tests for unified ingestion pipeline."""

import pytest
from pathlib import Path
from src.components.shared.unified_ingestion import UnifiedIngestionPipeline


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unified_ingestion_e2e(tmp_path):
    """Test end-to-end unified ingestion.

    Note: Tests Qdrant/BM25 indexing. Neo4j indexing is optional due to
    LightRAG threading limitations in test environment.
    Requires: Qdrant and Ollama services running.
    """
    # Create test documents
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()

    (doc_dir / "test1.txt").write_text("AEGIS RAG uses LangGraph for orchestration.")
    (doc_dir / "test2.txt").write_text("LangGraph provides state management.")

    # Ingest (only Qdrant for reliable testing)
    pipeline = UnifiedIngestionPipeline(
        allowed_base_path=str(tmp_path),
        enable_qdrant=True,
        enable_neo4j=False,  # Disable Neo4j to avoid threading issues in tests
    )
    result = await pipeline.ingest_directory(str(doc_dir))

    # Verify Qdrant indexing succeeded
    assert result.total_documents >= 2
    assert result.qdrant_indexed >= 2
    assert result.bm25_indexed >= 2
    # Neo4j was disabled, so no errors expected
    assert len(result.errors) == 0
    assert result.neo4j_entities == 0
    assert result.neo4j_relationships == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parallel_indexing_performance(tmp_path):
    """Test that parallel indexing completes successfully.

    Note: Tests Qdrant/BM25 indexing. Neo4j disabled due to threading issues.
    Requires: Qdrant and Ollama services running.
    """
    import time

    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()

    # Create 10 test documents
    for i in range(10):
        (doc_dir / f"test{i}.txt").write_text(f"Document {i} content with meaningful text.")

    # Measure unified pipeline (only Qdrant for reliable testing)
    pipeline = UnifiedIngestionPipeline(
        allowed_base_path=str(tmp_path),
        enable_qdrant=True,
        enable_neo4j=False,  # Disable Neo4j to avoid threading issues in tests
    )
    start = time.time()
    result = await pipeline.ingest_directory(str(doc_dir))
    parallel_duration = time.time() - start

    # Verify completion
    assert result.total_documents == 10
    assert result.qdrant_indexed == 10
    assert parallel_duration < 60  # Should complete in < 1 minute
    assert len(result.errors) == 0
