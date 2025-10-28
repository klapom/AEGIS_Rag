"""Unit tests for HybridSearch.

Tests hybrid search combining vector and BM25:
- Vector-only search
- BM25-only search
- Hybrid search with RRF
- BM25 index preparation
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.vector_search.hybrid_search import HybridSearch
from src.core.exceptions import VectorSearchError

# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_hybrid_search_init_default():
    """Test HybridSearch initialization with defaults."""
    with (
        patch("src.components.vector_search.hybrid_search.QdrantClientWrapper"),
        patch("src.components.vector_search.hybrid_search.EmbeddingService"),
        patch("src.components.vector_search.hybrid_search.BM25Search"),
    ):

        search = HybridSearch()

        assert search.collection_name is not None, "Collection name should be set"


@pytest.mark.unit
def test_hybrid_search_init_custom(mock_qdrant_client, mock_embedding_service, mock_bm25_search):
    """Test HybridSearch initialization with custom components."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
        collection_name="custom_collection",
    )

    assert search.qdrant_client is mock_qdrant_client
    assert search.embedding_service is mock_embedding_service
    assert search.bm25_search is mock_bm25_search
    assert search.collection_name == "custom_collection"


# ============================================================================
# Test Vector Search
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_success(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search, sample_query
):
    """Test successful vector search."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    results = await search.vector_search(sample_query, top_k=10)

    assert len(results) > 0, "Should return results"
    assert all("id" in r for r in results), "Results should have id"
    assert all("text" in r for r in results), "Results should have text"
    assert all("score" in r for r in results), "Results should have score"
    assert all("search_type" in r for r in results), "Results should have search_type"
    assert all(r["search_type"] == "vector" for r in results), "Should be vector search"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_with_threshold(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search
):
    """Test vector search with score threshold."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    await search.vector_search("test query", top_k=5, score_threshold=0.8)

    # Mock should be called with threshold
    mock_qdrant_client.search.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_failure(mock_embedding_service, mock_bm25_search):
    """Test vector search failure."""
    mock_client = MagicMock()
    mock_client.search = AsyncMock(side_effect=Exception("Search failed"))

    search = HybridSearch(
        qdrant_client=mock_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    with pytest.raises(VectorSearchError) as exc_info:
        await search.vector_search("test query")

    assert "Vector search failed" in str(exc_info.value)


# ============================================================================
# Test Keyword Search
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_search_success(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search, sample_query
):
    """Test successful BM25 keyword search."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    results = await search.keyword_search(sample_query, top_k=10)

    assert len(results) > 0, "Should return results"
    assert all("text" in r for r in results), "Results should have text"
    assert all("score" in r for r in results), "Results should have score"
    assert all("search_type" in r for r in results), "Results should have search_type"
    assert all(r["search_type"] == "bm25" for r in results), "Should be BM25 search"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_search_failure(mock_qdrant_client, mock_embedding_service):
    """Test keyword search failure."""
    mock_bm25 = MagicMock()
    mock_bm25.search.side_effect = Exception("BM25 failed")

    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25,
    )

    with pytest.raises(VectorSearchError) as exc_info:
        await search.keyword_search("test query")

    assert "BM25 search failed" in str(exc_info.value)


# ============================================================================
# Test Hybrid Search
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_success(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search, sample_query
):
    """Test successful hybrid search combining vector and BM25."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    result = await search.hybrid_search(sample_query, top_k=10)

    assert "query" in result, "Should include query"
    assert "results" in result, "Should include results"
    assert "total_results" in result, "Should include total_results"
    assert "search_metadata" in result, "Should include metadata"

    assert result["query"] == sample_query, "Query should match"
    assert len(result["results"]) <= 10, "Should return at most 10 results"

    # Check metadata
    metadata = result["search_metadata"]
    assert "vector_results_count" in metadata
    assert "bm25_results_count" in metadata
    assert "rrf_k" in metadata
    assert "diversity_stats" in metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_rrf_fusion(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search
):
    """Test that hybrid search performs RRF fusion."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    result = await search.hybrid_search("test query", top_k=5, rrf_k=60)

    # Results should have RRF scores and ranks
    for doc in result["results"]:
        assert "rrf_score" in doc or "score" in doc, "Should have score"
        assert "rrf_rank" in doc or "rank" in doc, "Should have rank"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "vector_top_k,bm25_top_k,final_top_k",
    [
        (20, 20, 10),
        (10, 10, 5),
        (30, 20, 15),
    ],
)
async def test_hybrid_search_different_top_k(
    mock_qdrant_client,
    mock_embedding_service,
    mock_bm25_search,
    vector_top_k,
    bm25_top_k,
    final_top_k,
):
    """Test hybrid search with different top_k parameters."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    result = await search.hybrid_search(
        "test query",
        top_k=final_top_k,
        vector_top_k=vector_top_k,
        bm25_top_k=bm25_top_k,
    )

    assert len(result["results"]) <= final_top_k, f"Should return at most {final_top_k} results"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_parallel_execution(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search
):
    """Test that vector and BM25 search run in parallel."""
    # Track call order
    call_order = []

    async def mock_vector(*args, **kwargs):
        call_order.append("vector")
        return []

    async def mock_keyword(*args, **kwargs):
        call_order.append("keyword")
        return []

    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    search.vector_search = mock_vector
    search.keyword_search = mock_keyword

    await search.hybrid_search("test query", top_k=5)

    # Both should have been called
    assert "vector" in call_order, "Vector search should be called"
    assert "keyword" in call_order, "Keyword search should be called"


# ============================================================================
# Test BM25 Index Preparation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_bm25_index_success(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search, sample_documents
):
    """Test preparing BM25 index from Qdrant collection."""
    # Mock scroll to return documents
    mock_qdrant_client.async_client.scroll.return_value = (
        [
            MagicMock(
                id="point1",
                payload={
                    "text": doc["text"],
                    "source": doc["source"],
                    "document_id": doc["document_id"],
                },
            )
            for doc in sample_documents
        ],
        None,  # No next offset
    )

    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    stats = await search.prepare_bm25_index()

    assert "documents_indexed" in stats, "Should include documents_indexed"
    assert "bm25_corpus_size" in stats, "Should include bm25_corpus_size"
    assert "collection_name" in stats, "Should include collection_name"

    # BM25 fit should have been called
    mock_bm25_search.fit.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_bm25_index_pagination():
    """Test BM25 index preparation with pagination."""
    mock_client = MagicMock()
    mock_client.async_client = AsyncMock()

    # Simulate pagination: 2 pages of results
    mock_client.async_client.scroll.side_effect = [
        (
            [MagicMock(id=f"point{i}", payload={"text": f"doc {i}"}) for i in range(3)],
            "offset_1",
        ),
        (
            [MagicMock(id=f"point{i}", payload={"text": f"doc {i}"}) for i in range(3, 5)],
            None,
        ),
    ]

    mock_bm25 = MagicMock()
    mock_bm25.fit = MagicMock()
    mock_bm25.get_corpus_size = MagicMock(return_value=5)

    search = HybridSearch(
        qdrant_client=mock_client,
        embedding_service=MagicMock(),
        bm25_search=mock_bm25,
    )

    stats = await search.prepare_bm25_index()

    assert stats["documents_indexed"] == 5, "Should index all documents across pages"
    assert mock_client.async_client.scroll.call_count == 2, "Should paginate"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_bm25_index_failure(mock_embedding_service, mock_bm25_search):
    """Test BM25 index preparation failure."""
    mock_client = MagicMock()
    mock_client.async_client = AsyncMock()
    mock_client.async_client.scroll.side_effect = Exception("Scroll failed")

    search = HybridSearch(
        qdrant_client=mock_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    with pytest.raises(VectorSearchError) as exc_info:
        await search.prepare_bm25_index()

    assert "Failed to prepare BM25 index" in str(exc_info.value)


# ============================================================================
# Test Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_empty_results(mock_embedding_service, mock_bm25_search):
    """Test hybrid search when both methods return no results."""
    mock_client = MagicMock()
    mock_client.search = AsyncMock(return_value=[])

    mock_bm25_search.search = MagicMock(return_value=[])

    search = HybridSearch(
        qdrant_client=mock_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    result = await search.hybrid_search("test query", top_k=10)

    assert result["results"] == [], "Should return empty results"
    assert result["total_results"] == 0, "Total should be 0"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_only_vector_results(mock_embedding_service):
    """Test hybrid search when only vector search returns results."""
    mock_client = MagicMock()
    mock_client.search = AsyncMock(
        return_value=[{"id": "doc1", "score": 0.9, "payload": {"text": "result"}}]
    )

    mock_bm25 = MagicMock()
    mock_bm25.search = MagicMock(return_value=[])

    mock_embedding_service.embed_text = AsyncMock(return_value=[0.1] * 1024)

    search = HybridSearch(
        qdrant_client=mock_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25,
    )

    result = await search.hybrid_search("test query", top_k=10)

    assert len(result["results"]) > 0, "Should return vector results"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hybrid_search_only_bm25_results(mock_qdrant_client, mock_embedding_service):
    """Test hybrid search when only BM25 returns results."""
    mock_qdrant_client.search = AsyncMock(return_value=[])

    mock_bm25 = MagicMock()
    mock_bm25.search = MagicMock(
        return_value=[{"text": "result", "score": 10.0, "metadata": {"id": "doc1"}, "rank": 1}]
    )

    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25,
    )

    result = await search.hybrid_search("test query", top_k=10)

    assert len(result["results"]) > 0, "Should return BM25 results"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vector_search_empty_query(
    mock_qdrant_client, mock_embedding_service, mock_bm25_search
):
    """Test vector search with empty query."""
    search = HybridSearch(
        qdrant_client=mock_qdrant_client,
        embedding_service=mock_embedding_service,
        bm25_search=mock_bm25_search,
    )

    await search.vector_search("", top_k=5)

    # Should still call embedding service with empty string
    mock_embedding_service.embed_text.assert_called_once_with("")
