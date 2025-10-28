"""End-to-End Integration Tests for Document Indexing.

These tests use real Qdrant and Ollama services running locally.
They test the complete indexing workflow from documents to searchable vectors.

Prerequisites:
- Qdrant running on localhost:6333
- Ollama running on localhost:11434 with nomic-embed-text model
"""

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from src.components.vector_search import (
    DocumentIngestionPipeline,
    EmbeddingService,
    QdrantClientWrapper,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def integration_qdrant_client():
    """Create Qdrant client for integration tests."""
    client = QdrantClientWrapper(
        host="localhost",
        port=6333,
        prefer_grpc=True,
    )

    yield client

    await client.close()


@pytest.fixture
def integration_embedding_service():
    """Create embedding service for integration tests."""
    service = EmbeddingService(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        batch_size=10,
        enable_cache=True,
    )

    return service


@pytest.fixture
def integration_collection_name():
    """Generate unique collection name for integration test."""
    return f"test_e2e_{uuid4().hex[:8]}"


@pytest.fixture
def integration_test_docs(tmp_path: Path) -> Path:
    """Create test documents for integration testing."""
    docs_dir = tmp_path / "integration_docs"
    docs_dir.mkdir()

    # Create sample documents
    (docs_dir / "doc1.txt").write_text(
        "AEGIS RAG is a multi-agent retrieval augmented generation system. "
        "It combines vector search, graph reasoning, temporal memory, and tool integration."
    )

    (docs_dir / "doc2.txt").write_text(
        "The vector search component uses Qdrant for storing embeddings. "
        "It implements hybrid search combining semantic vector similarity with BM25 keyword matching."
    )

    (docs_dir / "doc3.md").write_text(
        "# Graph Reasoning\n\n"
        "Graph reasoning is powered by LightRAG and Neo4j. "
        "It enables multi-hop reasoning across knowledge graphs for complex queries."
    )

    return docs_dir


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_document_indexing_complete_pipeline(
    integration_qdrant_client,
    integration_embedding_service,
    integration_collection_name,
    integration_test_docs,
):
    """Test complete E2E indexing pipeline with real services."""
    # Create ingestion pipeline
    pipeline = DocumentIngestionPipeline(
        qdrant_client=integration_qdrant_client,
        embedding_service=integration_embedding_service,
        collection_name=integration_collection_name,
        chunk_size=256,
        chunk_overlap=64,
    )

    try:
        # Run complete indexing
        stats = await pipeline.index_documents(
            input_dir=integration_test_docs,
            batch_size=50,
        )

        # Verify statistics
        assert stats["documents_loaded"] == 3, "Should load 3 documents"
        assert stats["chunks_created"] > 0, "Should create chunks"
        assert stats["embeddings_generated"] > 0, "Should generate embeddings"
        assert stats["points_indexed"] > 0, "Should index points"
        assert stats["collection_name"] == integration_collection_name

        # Verify collection was created
        collection_info = await integration_qdrant_client.get_collection_info(
            integration_collection_name
        )
        assert collection_info is not None, "Collection should exist"
        assert collection_info.points_count > 0, "Should have points"

    finally:
        # Cleanup: delete test collection
        await integration_qdrant_client.delete_collection(integration_collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_indexing_and_search(
    integration_qdrant_client,
    integration_embedding_service,
    integration_collection_name,
    integration_test_docs,
):
    """Test indexing followed by search."""
    pipeline = DocumentIngestionPipeline(
        qdrant_client=integration_qdrant_client,
        embedding_service=integration_embedding_service,
        collection_name=integration_collection_name,
        chunk_size=256,
        chunk_overlap=64,
    )

    try:
        # Index documents
        await pipeline.index_documents(input_dir=integration_test_docs)

        # Generate query embedding
        query = "What is AEGIS RAG?"
        query_embedding = await integration_embedding_service.embed_text(query)

        # Search
        results = await integration_qdrant_client.search(
            collection_name=integration_collection_name,
            query_vector=query_embedding,
            limit=5,
        )

        # Verify search results
        assert len(results) > 0, "Should return search results"
        assert "id" in results[0], "Results should have ID"
        assert "score" in results[0], "Results should have score"
        assert "payload" in results[0], "Results should have payload"
        assert "text" in results[0]["payload"], "Payload should have text"

        # Verify relevance (top result should mention AEGIS or RAG)
        top_text = results[0]["payload"]["text"].lower()
        assert "aegis" in top_text or "rag" in top_text, "Top result should be relevant to query"

    finally:
        await integration_qdrant_client.delete_collection(integration_collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_batch_embedding(integration_embedding_service):
    """Test batch embedding with real Ollama service."""
    texts = [
        "This is the first test document.",
        "This is the second test document.",
        "This is the third test document.",
        "This is the fourth test document.",
        "This is the fifth test document.",
    ]

    embeddings = await integration_embedding_service.embed_batch(texts)

    assert len(embeddings) == len(texts), "Should return embedding for each text"
    assert all(len(emb) == 1024 for emb in embeddings), "All embeddings should be 1024-dimensional"
    assert all(isinstance(emb[0], float) for emb in embeddings), "Embeddings should be floats"

    # Verify embeddings are different
    assert embeddings[0] != embeddings[1], "Different texts should have different embeddings"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_embedding_cache(integration_embedding_service):
    """Test that embedding cache works with real service."""
    text = "Test document for caching"

    # Clear cache first
    integration_embedding_service.clear_cache()
    assert integration_embedding_service.get_cache_size() == 0

    # First call - cache miss
    embedding1 = await integration_embedding_service.embed_text(text)
    assert integration_embedding_service.get_cache_size() == 1, "Should cache embedding"

    # Second call - cache hit (should be faster)
    embedding2 = await integration_embedding_service.embed_text(text)

    assert embedding1 == embedding2, "Cached embedding should match"
    assert integration_embedding_service.get_cache_size() == 1, "Cache size should remain 1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_collection_lifecycle(integration_qdrant_client, integration_collection_name):
    """Test complete collection lifecycle: create, verify, delete."""
    # Create collection
    created = await integration_qdrant_client.create_collection(
        collection_name=integration_collection_name,
        vector_size=1024,
    )
    assert created is True, "Collection should be created"

    # Verify collection exists
    info = await integration_qdrant_client.get_collection_info(integration_collection_name)
    assert info is not None, "Collection should exist"
    assert info.points_count == 0, "New collection should be empty"

    # Delete collection
    deleted = await integration_qdrant_client.delete_collection(integration_collection_name)
    assert deleted is True, "Collection should be deleted"

    # Verify deletion
    info_after = await integration_qdrant_client.get_collection_info(integration_collection_name)
    assert info_after is None, "Collection should not exist after deletion"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_health_check(integration_qdrant_client):
    """Test Qdrant health check with real service."""
    healthy = await integration_qdrant_client.health_check()
    assert healthy is True, "Qdrant should be healthy"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_indexing_large_documents(
    integration_qdrant_client,
    integration_embedding_service,
    integration_collection_name,
    tmp_path,
):
    """Test indexing larger documents to verify chunking."""
    docs_dir = tmp_path / "large_docs"
    docs_dir.mkdir()

    # Create a large document (will be chunked)
    large_text = " ".join([f"This is sentence number {i} in a large document." for i in range(100)])
    (docs_dir / "large.txt").write_text(large_text)

    pipeline = DocumentIngestionPipeline(
        qdrant_client=integration_qdrant_client,
        embedding_service=integration_embedding_service,
        collection_name=integration_collection_name,
        chunk_size=128,  # Small chunk size to force multiple chunks
        chunk_overlap=32,
    )

    try:
        stats = await pipeline.index_documents(input_dir=docs_dir)

        assert stats["documents_loaded"] == 1, "Should load 1 document"
        assert stats["chunks_created"] > 1, "Large document should be chunked"
        assert stats["points_indexed"] == stats["chunks_created"], "All chunks should be indexed"

    finally:
        await integration_qdrant_client.delete_collection(integration_collection_name)


# ============================================================================
# Skip Integration Tests if Services Unavailable
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def check_integration_services():
    """Check if integration test services are available."""
    import socket

    def is_service_available(host, port):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (TimeoutError, OSError):
            return False

    qdrant_available = is_service_available("localhost", 6333)
    ollama_available = is_service_available("localhost", 11434)

    if not qdrant_available:
        pytest.skip(
            "Qdrant service not available on localhost:6333. "
            "Start Qdrant with: docker run -p 6333:6333 qdrant/qdrant",
            allow_module_level=True,
        )

    if not ollama_available:
        pytest.skip(
            "Ollama service not available on localhost:11434. "
            "Start Ollama and pull model with: ollama pull nomic-embed-text",
            allow_module_level=True,
        )
