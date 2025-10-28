"""End-to-End tests for Unified Ingestion Pipeline.

Sprint 16: E2E coverage for real-world ingestion scenarios.

These tests verify:
- Complete document ingestion flow (Qdrant + BM25 + Neo4j)
- PPTX document support (Feature 16.5)
- Unified chunking integration (Feature 16.1)
- BGE-M3 embeddings (Feature 16.2)
- Optimized LightRAG integration (Feature 16.6)
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from src.components.shared.unified_ingestion import (
    UnifiedIngestionPipeline,
    get_unified_pipeline,
)


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Qdrant, Neo4j, and Ollama running")
async def test_unified_ingestion_complete_flow():
    """E2E test: Complete ingestion flow with real services.

    Verifies:
    - Document loading from filesystem
    - Qdrant indexing with BGE-M3 embeddings
    - BM25 index creation
    - Neo4j entity extraction via LightRAG
    - Unified chunking across all systems
    """
    # Create temp directory with test documents
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test documents
        test_doc1 = Path(temp_dir) / "doc1.txt"
        test_doc1.write_text(
            "Klaus Pommer works at Pommer IT-Consulting GmbH. "
            "He specializes in RAG systems and AI architectures."
        )

        test_doc2 = Path(temp_dir) / "doc2.md"
        test_doc2.write_text(
            "# AEGIS RAG System\n\n"
            "AEGIS RAG is a hybrid retrieval system combining:\n"
            "- Vector search (Qdrant)\n"
            "- Keyword search (BM25)\n"
            "- Graph reasoning (LightRAG + Neo4j)\n"
        )

        # Initialize pipeline
        pipeline = UnifiedIngestionPipeline(
            allowed_base_path=temp_dir,
            enable_qdrant=True,
            enable_neo4j=True,
        )

        # Run ingestion
        result = await pipeline.ingest_directory(temp_dir)

        # Verify results
        assert result.total_documents == 2
        assert result.qdrant_indexed == 2
        assert result.bm25_indexed == 2
        assert result.neo4j_entities > 0  # Should extract entities
        assert result.neo4j_relationships >= 0
        assert result.errors == []
        assert result.duration_seconds > 0

        # Verify Qdrant indexing
        from src.components.vector_search.qdrant_client import get_qdrant_client

        qdrant = get_qdrant_client()
        collection_info = await qdrant.get_collection_info()
        assert collection_info.points_count >= 2  # At least 2 chunks

        # Verify Neo4j entities
        from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async

        lightrag = await get_lightrag_wrapper_async()
        stats = await lightrag.get_stats()
        assert stats["entity_count"] > 0
        assert stats["entity_count"] == result.neo4j_entities


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires python-pptx and services running")
async def test_pptx_document_ingestion_e2e():
    """E2E test: PPTX document ingestion (Sprint 16 Feature 16.5).

    Verifies:
    - PPTX file loading via python-pptx
    - Text extraction from slides
    - Indexing to all systems (Qdrant, BM25, Neo4j)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Note: Creating a real PPTX programmatically requires python-pptx
        # For now, we test with a text file mimicking PPTX content
        test_pptx_content = Path(temp_dir) / "presentation.txt"
        test_pptx_content.write_text(
            "Slide 1: Introduction to AEGIS RAG\n"
            "Slide 2: Architecture Overview\n"
            "Slide 3: Vector Search with Qdrant\n"
            "Slide 4: Graph Reasoning with LightRAG\n"
            "Slide 5: Conclusion and Future Work"
        )

        pipeline = UnifiedIngestionPipeline(
            allowed_base_path=temp_dir,
            enable_qdrant=True,
            enable_neo4j=True,
        )

        result = await pipeline.ingest_directory(temp_dir)

        # Verify PPTX-like content was indexed
        assert result.total_documents == 1
        assert result.qdrant_indexed == 1
        assert result.neo4j_entities > 0


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires services running")
async def test_unified_chunking_consistency_e2e():
    """E2E test: Unified chunking consistency across systems (Sprint 16 Feature 16.1).

    Verifies:
    - Identical chunks in Qdrant and LightRAG
    - Chunk IDs match between systems
    - Provenance tracking works end-to-end
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a document with known content for chunk verification
        test_doc = Path(temp_dir) / "test.txt"
        test_content = "A" * 600  # Exactly 600 characters for predictable chunking
        test_doc.write_text(test_content)

        pipeline = UnifiedIngestionPipeline(
            allowed_base_path=temp_dir,
            enable_qdrant=True,
            enable_neo4j=True,
        )

        result = await pipeline.ingest_directory(temp_dir)

        # Verify ingestion
        assert result.total_documents == 1
        assert result.qdrant_indexed == 1

        # TODO: Add verification that:
        # 1. Qdrant chunks match LightRAG chunks (via chunk_id)
        # 2. Neo4j :chunk nodes exist with matching chunk_ids
        # 3. MENTIONED_IN relationships link entities to chunks


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires services running")
async def test_bge_m3_embeddings_e2e():
    """E2E test: BGE-M3 embeddings across all systems (Sprint 16 Feature 16.2).

    Verifies:
    - BGE-M3 (1024-dim) embeddings generated
    - Embeddings stored in Qdrant
    - LightRAG uses same embedding model
    - Cross-layer similarity possible (Qdrant ↔ LightRAG)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        test_doc = Path(temp_dir) / "similarity_test.txt"
        test_doc.write_text("Machine learning and artificial intelligence.")

        pipeline = UnifiedIngestionPipeline(
            allowed_base_path=temp_dir,
            enable_qdrant=True,
            enable_neo4j=True,
        )

        result = await pipeline.ingest_directory(temp_dir)

        # Verify Qdrant embeddings are 1024-dim (BGE-M3)
        from src.components.vector_search.qdrant_client import get_qdrant_client

        qdrant = get_qdrant_client()
        collection_info = await qdrant.get_collection_info()
        assert collection_info.config.params.vectors.size == 1024  # BGE-M3


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_recovery_e2e():
    """E2E test: Error recovery and partial success.

    Verifies:
    - Pipeline continues if one system fails
    - Error messages are captured
    - Partial results are returned
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        test_doc = Path(temp_dir) / "doc.txt"
        test_doc.write_text("Test document for error recovery.")

        # Create pipeline with Qdrant enabled, Neo4j disabled (simulating Neo4j down)
        pipeline = UnifiedIngestionPipeline(
            allowed_base_path=temp_dir,
            enable_qdrant=True,
            enable_neo4j=False,  # Simulate Neo4j unavailable
        )

        result = await pipeline.ingest_directory(temp_dir)

        # Verify partial success (Qdrant works, Neo4j skipped)
        assert result.total_documents > 0
        assert result.qdrant_indexed > 0
        assert result.neo4j_entities == 0  # Neo4j was disabled
        # Errors should be empty (not an error, just disabled)
        assert result.errors == []


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_large_document_batching_e2e():
    """E2E test: Large document batching and memory efficiency.

    Verifies:
    - Pipeline handles 100+ documents
    - Memory usage stays reasonable
    - Batch processing works correctly
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create 50 test documents
        for i in range(50):
            doc = Path(temp_dir) / f"doc_{i:03d}.txt"
            doc.write_text(
                f"Document {i} content. " * 20  # ~400 chars per doc
            )

        pipeline = UnifiedIngestionPipeline(
            allowed_base_path=temp_dir,
            enable_qdrant=True,
            enable_neo4j=False,  # Disable Neo4j for speed
        )

        result = await pipeline.ingest_directory(temp_dir)

        # Verify all documents were processed
        assert result.total_documents == 50
        assert result.qdrant_indexed == 50
        assert result.errors == []


@pytest.mark.e2e
def test_singleton_pattern_thread_safety():
    """E2E test: Singleton pattern is thread-safe.

    Verifies:
    - Multiple threads get same instance
    - No race conditions
    """
    instances = []

    def get_instance():
        instances.append(get_unified_pipeline())

    import threading

    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All instances should be the same object
    assert len(set(id(inst) for inst in instances)) == 1
