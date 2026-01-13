"""Unit tests for MultiVectorHybridSearch.

Sprint Context: Sprint 87 (2026-01-13) - Feature 87.5: Hybrid Retrieval with Query API

Tests the multi-vector hybrid search implementation using Qdrant Query API
with server-side RRF fusion.

Test Coverage:
    - hybrid_search: Server-side RRF fusion with dense + sparse
    - dense_only_search: Fallback when sparse unavailable
    - sparse_only_search: Testing sparse vector functionality
    - _format_results: Result formatting and metadata handling
    - Namespace filtering
    - Error handling and fallbacks
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from qdrant_client.models import ScoredPoint

from src.components.vector_search.multi_vector_search import (
    MultiVectorHybridSearch,
    get_multi_vector_search,
    reset_multi_vector_search,
)


@pytest.fixture
def mock_qdrant_client():
    """Create mock Qdrant client."""
    client = MagicMock()
    client.async_client = AsyncMock()
    return client


@pytest.fixture
def mock_embedding_service():
    """Create mock FlagEmbedding service."""
    service = MagicMock()
    # Mock embed_single to return dense + sparse
    service.embed_single = Mock(
        return_value={
            "dense": [0.1] * 1024,  # 1024D dense vector
            "sparse": {123: 0.8, 456: 0.6, 789: 0.4},  # Sparse dict
        }
    )
    # Mock embed_single_dense for fallback
    service.embed_single_dense = Mock(return_value=[0.1] * 1024)
    return service


@pytest.fixture
def multi_vector_search(mock_qdrant_client, mock_embedding_service):
    """Create MultiVectorHybridSearch instance with mocked dependencies."""
    with patch(
        "src.components.vector_search.multi_vector_search.get_flag_embedding_service",
        return_value=mock_embedding_service,
    ):
        search = MultiVectorHybridSearch(
            qdrant_client=mock_qdrant_client,
            collection_name="test_collection",
        )
        return search


@pytest.fixture
def mock_qdrant_results():
    """Create mock Qdrant query results."""
    points = [
        ScoredPoint(
            id="1",
            version=1,
            score=0.95,
            payload={
                "content": "RAG is a technique for retrieval augmented generation.",
                "document_path": "docs/rag.pdf",
                "document_id": "doc_123",
                "namespace_id": "default",
                "section_id": "1.1",
                "section_headings": ["Introduction", "RAG Overview"],
                "primary_section": "RAG Overview",
            },
        ),
        ScoredPoint(
            id="2",
            version=1,
            score=0.88,
            payload={
                "content": "Hybrid search combines vector and keyword methods.",
                "document_path": "docs/search.pdf",
                "document_id": "doc_456",
                "namespace_id": "default",
                "section_id": "2.3",
                "section_headings": ["Hybrid Search"],
                "primary_section": "Hybrid Search",
            },
        ),
    ]

    # Mock QueryResponse-like object
    mock_response = MagicMock()
    mock_response.points = points
    return mock_response


class TestMultiVectorHybridSearch:
    """Test cases for MultiVectorHybridSearch class."""

    def test_initialization(self, multi_vector_search):
        """Test MultiVectorHybridSearch initialization."""
        assert multi_vector_search is not None
        assert multi_vector_search.collection_name == "test_collection"
        assert multi_vector_search.qdrant_client is not None
        assert multi_vector_search.embedding_service is not None

    @pytest.mark.asyncio
    async def test_hybrid_search_success(
        self, multi_vector_search, mock_qdrant_results, mock_embedding_service
    ):
        """Test successful hybrid search with server-side RRF."""
        # Setup mock response
        multi_vector_search.qdrant_client.async_client.query_points.return_value = (
            mock_qdrant_results
        )

        # Execute search
        results = await multi_vector_search.hybrid_search(
            query="What is RAG?",
            top_k=10,
            prefetch_limit=50,
            namespace_filter="default",
        )

        # Verify embedding service called
        mock_embedding_service.embed_single.assert_called_once_with("What is RAG?")

        # Verify Qdrant query_points called
        assert multi_vector_search.qdrant_client.async_client.query_points.called
        call_kwargs = (
            multi_vector_search.qdrant_client.async_client.query_points.call_args.kwargs
        )
        assert call_kwargs["collection_name"] == "test_collection"
        assert call_kwargs["limit"] == 10
        assert len(call_kwargs["prefetch"]) == 2  # Dense + sparse

        # Verify results format
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[0]["rank"] == 1
        assert results[0]["search_type"] == "hybrid"
        assert results[0]["text"] == "RAG is a technique for retrieval augmented generation."
        assert results[0]["score"] == 0.95
        assert results[0]["namespace_id"] == "default"
        assert results[0]["section_headings"] == ["Introduction", "RAG Overview"]

    @pytest.mark.asyncio
    async def test_hybrid_search_with_namespace_filter(self, multi_vector_search, mock_qdrant_results):
        """Test hybrid search with namespace filtering."""
        multi_vector_search.qdrant_client.async_client.query_points.return_value = (
            mock_qdrant_results
        )

        results = await multi_vector_search.hybrid_search(
            query="What is RAG?",
            top_k=10,
            namespace_filter="ragas_phase2",
        )

        # Verify namespace filter applied
        call_kwargs = (
            multi_vector_search.qdrant_client.async_client.query_points.call_args.kwargs
        )
        assert call_kwargs["prefetch"][0].filter is not None
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_hybrid_search_fallback_to_dense(
        self, multi_vector_search, mock_embedding_service
    ):
        """Test fallback to dense-only when hybrid search fails."""
        # Mock query_points to fail
        multi_vector_search.qdrant_client.async_client.query_points.side_effect = Exception(
            "Query API not supported"
        )

        # Mock dense-only search to succeed
        mock_search_results = [
            ScoredPoint(
                id="1",
                version=1,
                score=0.90,
                payload={"content": "Test content", "namespace_id": "default"},
            )
        ]
        multi_vector_search.qdrant_client.async_client.search.return_value = mock_search_results

        # Execute search (should fallback)
        results = await multi_vector_search.hybrid_search(query="test query", top_k=10)

        # Verify fallback to dense-only
        assert multi_vector_search.qdrant_client.async_client.search.called
        assert len(results) == 1
        assert results[0]["search_type"] == "dense_only"

    @pytest.mark.asyncio
    async def test_dense_only_search(self, multi_vector_search, mock_embedding_service):
        """Test dense-only search fallback."""
        # Mock search results
        mock_results = [
            ScoredPoint(
                id="1",
                version=1,
                score=0.92,
                payload={
                    "content": "Dense search result",
                    "document_path": "test.pdf",
                    "namespace_id": "default",
                },
            )
        ]
        multi_vector_search.qdrant_client.async_client.search.return_value = mock_results

        # Execute dense-only search
        results = await multi_vector_search.dense_only_search(
            query="test query",
            top_k=10,
            namespace_filter="default",
        )

        # Verify embedding service called (dense-only)
        mock_embedding_service.embed_single_dense.assert_called_once()

        # Verify search called with dense vector
        assert multi_vector_search.qdrant_client.async_client.search.called
        call_kwargs = multi_vector_search.qdrant_client.async_client.search.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_collection"
        assert call_kwargs["limit"] == 10

        # Verify results
        assert len(results) == 1
        assert results[0]["search_type"] == "dense_only"
        assert results[0]["text"] == "Dense search result"

    @pytest.mark.asyncio
    async def test_sparse_only_search(self, multi_vector_search, mock_embedding_service):
        """Test sparse-only search for testing."""
        # Mock search results
        mock_results = [
            ScoredPoint(
                id="1",
                version=1,
                score=0.85,
                payload={
                    "content": "Sparse search result",
                    "document_path": "test.pdf",
                    "namespace_id": "default",
                },
            )
        ]
        multi_vector_search.qdrant_client.async_client.search.return_value = mock_results

        # Execute sparse-only search
        results = await multi_vector_search.sparse_only_search(
            query="test query",
            top_k=10,
            namespace_filter="default",
        )

        # Verify embedding service called
        mock_embedding_service.embed_single.assert_called()

        # Verify search called
        assert multi_vector_search.qdrant_client.async_client.search.called

        # Verify results
        assert len(results) == 1
        assert results[0]["search_type"] == "sparse_only"

    def test_format_results(self, multi_vector_search):
        """Test result formatting."""
        points = [
            ScoredPoint(
                id="1",
                version=1,
                score=0.95,
                payload={
                    "content": "Test content",
                    "document_path": "docs/test.pdf",
                    "document_id": "doc_123",
                    "namespace_id": "test_namespace",
                    "section_id": "1.1",
                    "section_headings": ["Section 1"],
                    "primary_section": "Section 1",
                    "format": "pdf",
                    "page": 5,
                },
            ),
            ScoredPoint(
                id="2",
                version=1,
                score=0.88,
                payload={
                    "text": "Alternative text field",  # Test 'text' fallback
                    "source": "docs/alt.pdf",  # Test 'source' fallback
                    "document_id": "doc_456",
                    "namespace_id": "default",
                },
            ),
        ]

        results = multi_vector_search._format_results(points, "test query", "hybrid")

        # Verify first result
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[0]["text"] == "Test content"
        assert results[0]["score"] == 0.95
        assert results[0]["source"] == "docs/test.pdf"
        assert results[0]["document_id"] == "doc_123"
        assert results[0]["namespace_id"] == "test_namespace"
        assert results[0]["rank"] == 1
        assert results[0]["search_type"] == "hybrid"
        assert results[0]["section_id"] == "1.1"
        assert results[0]["section_headings"] == ["Section 1"]
        assert results[0]["metadata"]["format"] == "pdf"
        assert results[0]["metadata"]["page"] == 5

        # Verify second result (test fallbacks)
        assert results[1]["text"] == "Alternative text field"
        assert results[1]["source"] == "docs/alt.pdf"
        assert results[1]["rank"] == 2

    @pytest.mark.asyncio
    async def test_singleton_factory(self, mock_qdrant_client, mock_embedding_service):
        """Test singleton factory pattern."""
        # Reset singleton
        reset_multi_vector_search()

        with patch(
            "src.components.vector_search.multi_vector_search.get_flag_embedding_service",
            return_value=mock_embedding_service,
        ):
            # Get first instance
            search1 = get_multi_vector_search(
                qdrant_client=mock_qdrant_client, collection_name="test1"
            )

            # Get second instance (should be same)
            search2 = get_multi_vector_search(
                qdrant_client=None, collection_name="test2"  # Config ignored
            )

            assert search1 is search2
            assert search1.collection_name == "test1"  # First config used

            # Reset and verify new instance
            reset_multi_vector_search()
            search3 = get_multi_vector_search(collection_name="test3")
            assert search3 is not search1
            assert search3.collection_name == "test3"


class TestMultiVectorSearchEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_results(self, multi_vector_search):
        """Test handling of empty search results."""
        # Mock empty results
        mock_response = MagicMock()
        mock_response.points = []
        multi_vector_search.qdrant_client.async_client.query_points.return_value = mock_response

        results = await multi_vector_search.hybrid_search(query="no match query", top_k=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_missing_payload_fields(self, multi_vector_search):
        """Test handling of missing payload fields."""
        # Mock results with minimal payload
        points = [
            ScoredPoint(
                id="1",
                version=1,
                score=0.80,
                payload={},  # Empty payload
            )
        ]
        mock_response = MagicMock()
        mock_response.points = points
        multi_vector_search.qdrant_client.async_client.query_points.return_value = mock_response

        results = await multi_vector_search.hybrid_search(query="test", top_k=10)

        # Verify defaults applied
        assert len(results) == 1
        assert results[0]["text"] == ""  # Default for missing content
        assert results[0]["source"] == "unknown"  # Default for missing source
        assert results[0]["namespace_id"] == "default"  # Default namespace
        assert results[0]["section_headings"] == []  # Default empty list

    @pytest.mark.asyncio
    async def test_large_prefetch_limit(self, multi_vector_search):
        """Test hybrid search with large prefetch limit."""
        mock_response = MagicMock()
        mock_response.points = []
        multi_vector_search.qdrant_client.async_client.query_points.return_value = mock_response

        # Use large prefetch limit (should not fail)
        results = await multi_vector_search.hybrid_search(
            query="test",
            top_k=10,
            prefetch_limit=1000,  # Large prefetch
        )

        # Verify prefetch limit passed correctly
        call_kwargs = (
            multi_vector_search.qdrant_client.async_client.query_points.call_args.kwargs
        )
        assert call_kwargs["prefetch"][0].limit == 1000
        assert call_kwargs["prefetch"][1].limit == 1000
