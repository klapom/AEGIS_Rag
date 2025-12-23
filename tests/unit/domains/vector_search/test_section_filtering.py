"""Unit Tests for Feature 62.2: Multi-Section Metadata in Vector Search.

Tests for:
- Section filtering in Qdrant vector search
- Section filtering in BM25 keyword search
- Section filtering in hybrid search (vector + BM25 + RRF)
- Multi-section queries
- Backward compatibility (chunks without section metadata)

Sprint 62 Feature 62.2: Multi-Section Metadata in Vector Search
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

# ============================================================================
# TEST: Qdrant Section Filtering
# ============================================================================


@pytest.mark.asyncio
async def test_qdrant_search_single_section_filter():
    """Test vector search with single section filter."""
    from src.components.vector_search.qdrant_client import QdrantClient

    client = QdrantClient()

    # Mock async_client.search
    mock_search_result = [
        MagicMock(
            id="1",
            score=0.95,
            payload={
                "text": "Content from section 1.2",
                "section_id": "1.2",
                "section_headings": ["Introduction", "Overview"],
            },
        )
    ]

    client._async_client = MagicMock()
    client._async_client.search = AsyncMock(return_value=mock_search_result)

    # Execute search with single section filter
    results = await client.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        limit=10,
        section_filter="1.2",
    )

    # Verify search was called with section filter
    client._async_client.search.assert_called_once()
    call_args = client._async_client.search.call_args

    # Check that section filter was built correctly
    query_filter = call_args.kwargs.get("query_filter")
    assert query_filter is not None
    assert len(query_filter.must) == 1
    assert query_filter.must[0].key == "section_id"
    assert query_filter.must[0].match.value == "1.2"

    # Verify results
    assert len(results) == 1
    assert results[0]["payload"]["section_id"] == "1.2"


@pytest.mark.asyncio
async def test_qdrant_search_multiple_section_filter():
    """Test vector search with multiple section filters."""
    from src.components.vector_search.qdrant_client import QdrantClient

    client = QdrantClient()

    # Mock async_client.search
    mock_search_result = [
        MagicMock(
            id="1",
            score=0.95,
            payload={"text": "Content from section 1.1", "section_id": "1.1"},
        ),
        MagicMock(
            id="2",
            score=0.92,
            payload={"text": "Content from section 1.2", "section_id": "1.2"},
        ),
    ]

    client._async_client = MagicMock()
    client._async_client.search = AsyncMock(return_value=mock_search_result)

    # Execute search with multiple section filters
    results = await client.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        limit=10,
        section_filter=["1.1", "1.2", "2.1"],
    )

    # Verify search was called with section filter
    client._async_client.search.assert_called_once()
    call_args = client._async_client.search.call_args

    # Check that section filter was built correctly (MatchAny)
    query_filter = call_args.kwargs.get("query_filter")
    assert query_filter is not None
    assert len(query_filter.must) == 1
    assert query_filter.must[0].key == "section_id"
    assert query_filter.must[0].match.any == ["1.1", "1.2", "2.1"]

    # Verify results
    assert len(results) == 2


@pytest.mark.asyncio
async def test_qdrant_search_section_filter_with_existing_filter():
    """Test that section filter combines with existing metadata filters."""
    from src.components.vector_search.qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = QdrantClient()

    # Create existing filter (e.g., document_id filter)
    existing_filter = Filter(
        must=[
            FieldCondition(
                key="document_id",
                match=MatchValue(value="doc123"),
            )
        ]
    )

    # Mock async_client.search
    mock_search_result = [
        MagicMock(
            id="1",
            score=0.95,
            payload={
                "text": "Content",
                "section_id": "1.2",
                "document_id": "doc123",
            },
        )
    ]

    client._async_client = MagicMock()
    client._async_client.search = AsyncMock(return_value=mock_search_result)

    # Execute search with both filters
    results = await client.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        limit=10,
        query_filter=existing_filter,
        section_filter="1.2",
    )

    # Verify search was called
    client._async_client.search.assert_called_once()
    call_args = client._async_client.search.call_args

    # Check that filters were combined (AND logic)
    query_filter = call_args.kwargs.get("query_filter")
    assert query_filter is not None
    assert len(query_filter.must) == 2  # Both filters present

    # Verify both filters are present
    filter_keys = [condition.key for condition in query_filter.must]
    assert "document_id" in filter_keys
    assert "section_id" in filter_keys


@pytest.mark.asyncio
async def test_qdrant_search_no_section_filter_backward_compatible():
    """Test that search works without section filter (backward compatible)."""
    from src.components.vector_search.qdrant_client import QdrantClient

    client = QdrantClient()

    # Mock async_client.search
    mock_search_result = [
        MagicMock(
            id="1",
            score=0.95,
            payload={"text": "Content without section metadata"},
        )
    ]

    client._async_client = MagicMock()
    client._async_client.search = AsyncMock(return_value=mock_search_result)

    # Execute search WITHOUT section filter
    results = await client.search(
        collection_name="test_collection",
        query_vector=[0.1] * 1024,
        limit=10,
    )

    # Verify search was called WITHOUT section filter
    client._async_client.search.assert_called_once()
    call_args = client._async_client.search.call_args
    query_filter = call_args.kwargs.get("query_filter")
    assert query_filter is None  # No filter applied

    # Verify results
    assert len(results) == 1


# ============================================================================
# TEST: BM25 Section Filtering
# ============================================================================


def test_bm25_search_single_section_filter():
    """Test BM25 search with single section filter."""
    from src.components.vector_search.bm25_search import BM25Search

    bm25 = BM25Search()

    # Fit with documents containing section metadata
    documents = [
        {
            "text": "Load balancing strategies for web servers",
            "section_id": "1.2",
            "section_headings": ["Load Balancing"],
        },
        {
            "text": "Database optimization techniques",
            "section_id": "2.1",
            "section_headings": ["Database"],
        },
        {
            "text": "Caching mechanisms for performance",
            "section_id": "1.3",
            "section_headings": ["Caching"],
        },
    ]

    bm25.fit(documents, text_field="text")

    # Search with section filter
    results = bm25.search(
        query="load balancing",
        top_k=10,
        section_filter="1.2",
    )

    # Should only return results from section 1.2
    assert len(results) >= 1
    for result in results:
        assert result["metadata"]["section_id"] == "1.2"


def test_bm25_search_multiple_section_filter():
    """Test BM25 search with multiple section filters."""
    from src.components.vector_search.bm25_search import BM25Search

    bm25 = BM25Search()

    # Fit with documents
    documents = [
        {"text": "Content A", "section_id": "1.1"},
        {"text": "Content B", "section_id": "1.2"},
        {"text": "Content C", "section_id": "2.1"},
        {"text": "Content D", "section_id": "2.2"},
    ]

    bm25.fit(documents, text_field="text")

    # Search with multiple section filters
    results = bm25.search(
        query="content",
        top_k=10,
        section_filter=["1.1", "1.2"],
    )

    # Should only return results from sections 1.1 and 1.2
    assert len(results) >= 2
    for result in results:
        assert result["metadata"]["section_id"] in ["1.1", "1.2"]


def test_bm25_search_no_section_filter_backward_compatible():
    """Test BM25 search without section filter (backward compatible)."""
    from src.components.vector_search.bm25_search import BM25Search

    bm25 = BM25Search()

    # Fit with documents WITHOUT section metadata
    documents = [
        {"text": "Content A", "id": "1"},
        {"text": "Content B", "id": "2"},
    ]

    bm25.fit(documents, text_field="text")

    # Search without section filter
    results = bm25.search(query="content", top_k=10)

    # Should return all matching results
    assert len(results) == 2


# ============================================================================
# TEST: Hybrid Search Section Filtering
# ============================================================================


@pytest.mark.asyncio
async def test_hybrid_search_with_section_filter():
    """Test hybrid search with section filter."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()
    mock_bm25 = MagicMock()

    # Setup mock vector search results
    mock_qdrant.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.95,
                "payload": {
                    "text": "Vector result from section 1.2",
                    "section_id": "1.2",
                    "section_headings": ["Load Balancing"],
                },
            }
        ]
    )

    # Setup mock embedding
    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)

    # Setup mock BM25 search results
    mock_bm25.search = MagicMock(
        return_value=[
            {
                "text": "BM25 result from section 1.2",
                "score": 5.2,
                "metadata": {
                    "id": "2",
                    "section_id": "1.2",
                    "section_headings": ["Load Balancing"],
                },
                "rank": 1,
            }
        ]
    )

    # Create hybrid search instance
    hybrid = HybridSearch(
        qdrant_client=mock_qdrant,
        embedding_service=mock_embedding,
        bm25_search=mock_bm25,
    )

    # Execute hybrid search with section filter
    with patch("src.components.vector_search.hybrid_search.reciprocal_rank_fusion") as mock_rrf:
        mock_rrf.return_value = [
            {
                "id": "1",
                "text": "Fused result",
                "score": 0.95,
                "section_id": "1.2",
            }
        ]

        results = await hybrid.hybrid_search(
            query="load balancing",
            top_k=5,
            section_filter="1.2",
        )

    # Verify section_filter was passed to vector_search
    mock_qdrant.search.assert_called_once()
    assert mock_qdrant.search.call_args.kwargs.get("section_filter") == "1.2"

    # Verify section_filter was passed to BM25 search
    mock_bm25.search.assert_called_once()
    assert mock_bm25.search.call_args.kwargs.get("section_filter") == "1.2"


# ============================================================================
# TEST: Section Metadata Preservation in Results
# ============================================================================


@pytest.mark.asyncio
async def test_vector_search_preserves_section_metadata():
    """Test that vector search results include section metadata."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()

    # Setup mock with section metadata
    mock_qdrant.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.95,
                "payload": {
                    "text": "Test content",
                    "section_id": "1.2",
                    "section_headings": ["Load Balancing", "Caching"],
                    "primary_section": "Load Balancing",
                },
            }
        ]
    )

    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)

    hybrid = HybridSearch(
        qdrant_client=mock_qdrant,
        embedding_service=mock_embedding,
    )

    # Execute vector search
    results = await hybrid.vector_search(query="test", top_k=5)

    # Verify section metadata is preserved in results
    assert len(results) == 1
    result = results[0]

    assert result["section_id"] == "1.2"
    assert result["section_headings"] == ["Load Balancing", "Caching"]
    assert result["primary_section"] == "Load Balancing"

    # Also verify in metadata dict
    assert result["metadata"]["section_id"] == "1.2"
    assert result["metadata"]["section_headings"] == ["Load Balancing", "Caching"]


# ============================================================================
# TEST: Backward Compatibility
# ============================================================================


@pytest.mark.asyncio
async def test_search_backward_compatible_without_section_metadata():
    """Test that search works with chunks that don't have section metadata."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()

    # Setup mock WITHOUT section metadata (old format)
    mock_qdrant.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.95,
                "payload": {
                    "text": "Old chunk without section metadata",
                    # No section_id, section_headings, etc.
                },
            }
        ]
    )

    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)

    hybrid = HybridSearch(
        qdrant_client=mock_qdrant,
        embedding_service=mock_embedding,
    )

    # Execute search - should not fail
    results = await hybrid.vector_search(query="test", top_k=5)

    # Verify results have empty section metadata (backward compatible)
    assert len(results) == 1
    result = results[0]

    assert result["section_id"] == ""
    assert result["section_headings"] == []
    assert result["primary_section"] == ""


@pytest.mark.asyncio
async def test_ingest_adaptive_chunks_includes_section_id():
    """Test that ingestion includes section_id in payload."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.components.retrieval.chunking import AdaptiveChunk

    # Create chunk with section_id in metadata
    chunk = AdaptiveChunk(
        text="Test content",
        token_count=100,
        section_headings=["Load Balancing"],
        section_pages=[1],
        section_bboxes=[{"l": 0, "t": 0, "r": 100, "b": 100}],
        primary_section="Load Balancing",
        metadata={
            "section_id": "1.2",
            "source": "doc.pdf",
        },
    )

    # Mock embedding service
    with patch("src.components.shared.embedding_service.get_embedding_service") as mock_get_svc:
        mock_embedding = MagicMock()
        mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)
        mock_get_svc.return_value = mock_embedding

        from src.components.vector_search.qdrant_client import QdrantClient

        client = QdrantClient()

        # Capture upserted points
        captured_points = []

        async def mock_upsert(collection_name, points, batch_size):
            captured_points.extend(points)
            return True

        client.upsert_points = mock_upsert

        # Ingest chunk
        await client.ingest_adaptive_chunks([chunk], "test_collection")

        # Verify section_id is in payload
        assert len(captured_points) == 1
        point = captured_points[0]

        assert "section_id" in point.payload
        assert point.payload["section_id"] == "1.2"
