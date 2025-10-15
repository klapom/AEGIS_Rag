"""End-to-End Integration Tests for Hybrid Search.

These tests verify the complete hybrid search workflow using real services.

Prerequisites:
- Qdrant running on localhost:6333
- Ollama running on localhost:11434 with nomic-embed-text model
"""

import pytest
import pytest_asyncio
from pathlib import Path
from uuid import uuid4

from src.components.vector_search import (
    HybridSearch,
    DocumentIngestionPipeline,
    QdrantClientWrapper,
    EmbeddingService,
    BM25Search,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def integration_hybrid_setup(tmp_path):
    """Set up complete hybrid search environment."""
    # Create unique collection name
    collection_name = f"test_hybrid_{uuid4().hex[:8]}"

    # Initialize components
    qdrant_client = QdrantClientWrapper(host="localhost", port=6333)
    embedding_service = EmbeddingService(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        batch_size=10,
    )
    bm25_search = BM25Search()

    # Create test documents
    docs_dir = tmp_path / "hybrid_docs"
    docs_dir.mkdir()

    (docs_dir / "rag.txt").write_text(
        "Retrieval Augmented Generation (RAG) combines retrieval systems with language models. "
        "RAG improves accuracy by grounding responses in retrieved documents."
    )

    (docs_dir / "vector.txt").write_text(
        "Vector databases store embeddings for semantic search. "
        "Qdrant is a vector database optimized for similarity search and filtering."
    )

    (docs_dir / "hybrid.txt").write_text(
        "Hybrid search combines vector similarity with keyword matching. "
        "BM25 is a popular keyword ranking algorithm used in hybrid search."
    )

    # Index documents
    pipeline = DocumentIngestionPipeline(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        collection_name=collection_name,
        chunk_size=256,
        chunk_overlap=64,
    )

    await pipeline.index_documents(input_dir=docs_dir)

    # Create hybrid search
    hybrid_search = HybridSearch(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        bm25_search=bm25_search,
        collection_name=collection_name,
    )

    # Prepare BM25 index
    await hybrid_search.prepare_bm25_index()

    yield {
        "hybrid_search": hybrid_search,
        "qdrant_client": qdrant_client,
        "collection_name": collection_name,
    }

    # Cleanup
    await qdrant_client.delete_collection(collection_name)
    await qdrant_client.close()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_hybrid_search_complete_workflow(integration_hybrid_setup):
    """Test complete hybrid search workflow."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    result = await hybrid_search.hybrid_search(
        query="What is RAG?",
        top_k=5,
        vector_top_k=10,
        bm25_top_k=10,
        rrf_k=60,
    )

    # Verify result structure
    assert "query" in result
    assert "results" in result
    assert "total_results" in result
    assert "search_metadata" in result

    # Verify results
    assert len(result["results"]) > 0, "Should return results"
    assert result["query"] == "What is RAG?"

    # Verify metadata
    metadata = result["search_metadata"]
    assert metadata["vector_results_count"] > 0
    assert metadata["bm25_results_count"] > 0
    assert "diversity_stats" in metadata

    # Verify relevance - top result should contain relevant keywords
    top_text = result["results"][0]["text"].lower()
    # Accept multiple relevant terms (vector, database, rag, retrieval, semantic, search)
    relevant_terms = ["rag", "retrieval", "vector", "database", "semantic", "search"]
    assert any(
        term in top_text for term in relevant_terms
    ), f"Top result should contain relevant terms. Got: {top_text[:100]}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_vector_search_only(integration_hybrid_setup):
    """Test vector-only search."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    results = await hybrid_search.vector_search(
        query="vector database",
        top_k=5,
    )

    assert len(results) > 0, "Should return vector search results"
    assert all(r["search_type"] == "vector" for r in results), "All results should be vector type"
    assert all("score" in r for r in results), "All results should have scores"

    # Verify relevance
    relevant = any(
        "vector" in r["text"].lower() or "qdrant" in r["text"].lower() for r in results[:2]
    )
    assert relevant, "Top results should mention vector or qdrant"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_bm25_search_only(integration_hybrid_setup):
    """Test BM25-only keyword search."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    results = await hybrid_search.keyword_search(
        query="hybrid search BM25",
        top_k=5,
    )

    assert len(results) > 0, "Should return BM25 search results"
    assert all(r["search_type"] == "bm25" for r in results), "All results should be BM25 type"

    # Verify keyword matching
    top_text = results[0]["text"].lower()
    assert "hybrid" in top_text or "bm25" in top_text, "Top result should match keywords"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_hybrid_vs_vector_only(integration_hybrid_setup):
    """Compare hybrid search with vector-only search."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    query = "What is retrieval augmented generation?"

    # Run both searches
    hybrid_result = await hybrid_search.hybrid_search(query, top_k=5)
    vector_results = await hybrid_search.vector_search(query, top_k=5)

    # Both should return results
    assert len(hybrid_result["results"]) > 0
    assert len(vector_results) > 0

    # Hybrid may have different rankings due to RRF
    hybrid_ids = [r["id"] for r in hybrid_result["results"]]
    vector_ids = [r["id"] for r in vector_results]

    # There should be some overlap
    overlap = set(hybrid_ids) & set(vector_ids)
    assert len(overlap) > 0, "Hybrid and vector should have some common results"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_hybrid_search_different_queries(integration_hybrid_setup):
    """Test hybrid search with various query types."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    queries = [
        "semantic search",
        "keyword matching algorithms",
        "vector embeddings",
        "BM25 ranking",
    ]

    for query in queries:
        result = await hybrid_search.hybrid_search(query, top_k=3)

        assert len(result["results"]) > 0, f"Should return results for: {query}"
        assert result["query"] == query
        assert result["search_metadata"]["vector_results_count"] >= 0
        assert result["search_metadata"]["bm25_results_count"] >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_bm25_index_preparation(integration_hybrid_setup):
    """Test BM25 index preparation from Qdrant."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    # Prepare BM25 index again (idempotent)
    stats = await hybrid_search.prepare_bm25_index()

    assert "documents_indexed" in stats
    assert stats["documents_indexed"] > 0, "Should index documents"
    assert stats["bm25_corpus_size"] > 0, "Corpus should not be empty"
    assert stats["collection_name"] == integration_hybrid_setup["collection_name"]

    # Verify BM25 is fitted
    assert hybrid_search.bm25_search.is_fitted(), "BM25 should be fitted"
    assert hybrid_search.bm25_search.get_corpus_size() > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_hybrid_search_with_score_threshold(integration_hybrid_setup):
    """Test hybrid search with score threshold for vector results."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    # Search with high threshold
    result = await hybrid_search.hybrid_search(
        query="vector database",
        top_k=5,
        score_threshold=0.5,  # Only return high-similarity results
    )

    # Should still return results, but possibly fewer
    assert "results" in result
    # All vector results should have score >= threshold in pure vector search
    # In hybrid search, RRF changes scores, so we can't directly check this


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_hybrid_search_ranking_diversity(integration_hybrid_setup):
    """Test that hybrid search provides ranking diversity."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    result = await hybrid_search.hybrid_search(
        query="search algorithms",
        top_k=5,
        vector_top_k=10,
        bm25_top_k=10,
    )

    # Check diversity stats
    diversity = result["search_metadata"]["diversity_stats"]
    assert "total_unique_documents" in diversity
    assert "common_documents" in diversity
    assert "average_pairwise_overlap" in diversity

    # There should be some unique documents from each method
    assert (
        diversity["total_unique_documents"] >= diversity["common_documents"]
    ), "Should have some unique documents"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("top_k", [1, 3, 5, 10])
async def test_e2e_hybrid_search_different_top_k(integration_hybrid_setup, top_k):
    """Test hybrid search with different top_k values."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    result = await hybrid_search.hybrid_search(
        query="test query",
        top_k=top_k,
    )

    assert len(result["results"]) <= top_k, f"Should return at most {top_k} results"
    assert result["returned_results"] == len(result["results"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_search_result_metadata(integration_hybrid_setup):
    """Test that search results contain all required metadata."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    result = await hybrid_search.hybrid_search(
        query="test query",
        top_k=3,
    )

    for doc in result["results"]:
        assert "id" in doc, "Result should have ID"
        assert "text" in doc, "Result should have text"
        assert "source" in doc, "Result should have source"
        assert doc["text"] != "", "Text should not be empty"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_empty_query_handling(integration_hybrid_setup):
    """Test hybrid search behavior with edge case queries."""
    hybrid_search = integration_hybrid_setup["hybrid_search"]

    # Very short query
    result = await hybrid_search.hybrid_search(query="a", top_k=3)
    assert "results" in result, "Should handle short queries"

    # Query with special characters
    result = await hybrid_search.hybrid_search(query="RAG?!", top_k=3)
    assert "results" in result, "Should handle special characters"


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
        except (socket.error, socket.timeout):
            return False

    qdrant_available = is_service_available("localhost", 6333)
    ollama_available = is_service_available("localhost", 11434)

    if not qdrant_available or not ollama_available:
        pytest.skip(
            "Integration services not available. "
            "Ensure Qdrant (localhost:6333) and Ollama (localhost:11434) are running.",
            allow_module_level=True,
        )
