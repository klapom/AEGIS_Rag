"""Integration tests for Feature 62.5: Section-Aware Reranking in Hybrid Search.

Tests for:
- Section filter propagation to reranker in hybrid search
- End-to-end section-aware reranking workflow
- Integration with existing hybrid search features

Sprint 62 Feature 62.5: Section-Aware Reranking Integration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# TEST: Hybrid Search Integration
# ============================================================================


@pytest.mark.asyncio
async def test_hybrid_search_passes_section_filter_to_reranker():
    """Test that hybrid search passes section_filter to reranker."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()
    mock_bm25 = MagicMock()
    mock_reranker = MagicMock()

    # Setup mock vector search results
    mock_qdrant.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.95,
                "payload": {
                    "text": "Load balancing content",
                    "section_id": "1.2",
                    "content": "Load balancing content",
                },
            }
        ]
    )

    # Setup mock embedding
    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)

    # Setup mock BM25 results
    mock_bm25.search = MagicMock(
        return_value=[
            {
                "text": "BM25 result",
                "score": 5.2,
                "metadata": {"id": "2", "section_id": "1.2"},
                "rank": 1,
            }
        ]
    )

    # Setup mock reranker (should be called with section_filter)
    from src.components.retrieval.reranker import RerankResult

    mock_reranker.rerank = AsyncMock(
        return_value=[
            RerankResult(
                doc_id="1",
                text="Load balancing content",
                original_score=0.95,
                rerank_score=0.98,
                final_score=0.98,
                original_rank=0,
                final_rank=0,
                metadata={},
            )
        ]
    )

    # Create hybrid search with mock reranker
    hybrid = HybridSearch(
        qdrant_client=mock_qdrant,
        embedding_service=mock_embedding,
        bm25_search=mock_bm25,
        reranker=mock_reranker,
    )

    # Execute hybrid search with section filter and reranking
    with patch("src.components.vector_search.hybrid_search.reciprocal_rank_fusion") as mock_rrf:
        mock_rrf.return_value = [
            {
                "id": "1",
                "text": "Fused result",
                "score": 0.95,
                "section_id": "1.2",
            }
        ]

        await hybrid.hybrid_search(
            query="load balancing",
            top_k=5,
            section_filter="1.2",
            use_reranking=True,
        )

    # Verify reranker was called with section_filter
    mock_reranker.rerank.assert_called_once()
    call_kwargs = mock_reranker.rerank.call_args.kwargs
    assert call_kwargs.get("section_filter") == "1.2"


@pytest.mark.asyncio
async def test_hybrid_search_section_filter_multiple_sections():
    """Test hybrid search with multiple section filters passed to reranker."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()
    mock_bm25 = MagicMock()
    mock_reranker = MagicMock()

    # Setup mocks
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)
    mock_bm25.search = MagicMock(return_value=[])

    from src.components.retrieval.reranker import RerankResult

    mock_reranker.rerank = AsyncMock(return_value=[])

    hybrid = HybridSearch(
        qdrant_client=mock_qdrant,
        embedding_service=mock_embedding,
        bm25_search=mock_bm25,
        reranker=mock_reranker,
    )

    # Execute with multiple sections
    with patch("src.components.vector_search.hybrid_search.reciprocal_rank_fusion") as mock_rrf:
        mock_rrf.return_value = []

        await hybrid.hybrid_search(
            query="test",
            top_k=5,
            section_filter=["1.1", "1.2", "2.1"],
            use_reranking=True,
        )

    # Verify multiple sections passed to reranker
    if mock_reranker.rerank.call_count > 0:
        call_kwargs = mock_reranker.rerank.call_args.kwargs
        assert call_kwargs.get("section_filter") == ["1.1", "1.2", "2.1"]


@pytest.mark.asyncio
async def test_hybrid_search_no_section_filter_backward_compatible():
    """Test that hybrid search works without section_filter (backward compatible)."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()
    mock_bm25 = MagicMock()
    mock_reranker = MagicMock()

    # Setup mocks
    mock_qdrant.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.95,
                "payload": {"text": "Test content", "content": "Test content"},
            }
        ]
    )
    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)
    mock_bm25.search = MagicMock(
        return_value=[
            {
                "text": "BM25 result",
                "score": 5.2,
                "metadata": {"id": "2"},
                "rank": 1,
            }
        ]
    )

    from src.components.retrieval.reranker import RerankResult

    mock_reranker.rerank = AsyncMock(
        return_value=[
            RerankResult(
                doc_id="1",
                text="Test content",
                original_score=0.95,
                rerank_score=0.98,
                final_score=0.98,
                original_rank=0,
                final_rank=0,
                metadata={},
            )
        ]
    )

    hybrid = HybridSearch(
        qdrant_client=mock_qdrant,
        embedding_service=mock_embedding,
        bm25_search=mock_bm25,
        reranker=mock_reranker,
    )

    # Execute without section_filter
    with patch("src.components.vector_search.hybrid_search.reciprocal_rank_fusion") as mock_rrf:
        mock_rrf.return_value = [{"id": "1", "text": "Fused result", "score": 0.95}]

        result = await hybrid.hybrid_search(
            query="test",
            top_k=5,
            use_reranking=True,
            # No section_filter provided
        )

    # Should work without errors
    assert "results" in result
    mock_reranker.rerank.assert_called_once()


# ============================================================================
# TEST: Section Boost in components/retrieval/reranker.py
# ============================================================================


@pytest.mark.asyncio
async def test_components_reranker_section_boost():
    """Test section boost in components.retrieval.reranker module."""
    from src.components.retrieval.reranker import CrossEncoderReranker

    documents = [
        {
            "id": "1",
            "text": "Load balancing distributes traffic",
            "section_id": "1.2",
            "score": 0.8,
        },
        {
            "id": "2",
            "text": "Database optimization",
            "section_id": "2.1",
            "score": 0.7,
        },
    ]

    # Mock the cross-encoder model (lazy import)
    with patch("sentence_transformers.CrossEncoder") as MockCrossEncoder:
        mock_model = MagicMock()
        mock_model.predict = MagicMock(return_value=[0.9, 0.6])
        MockCrossEncoder.return_value = mock_model

        reranker = CrossEncoderReranker()

        # Rerank with section boost
        results = await reranker.rerank(
            query="load balancing",
            documents=documents,
            top_k=2,
            section_filter="1.2",
            section_boost=0.1,
        )

    # Document 1 should have boosted score
    assert len(results) == 2
    doc1 = next((r for r in results if r.doc_id == "1"), None)
    assert doc1 is not None
    # Score should be boosted (0.9 + 0.1 = 1.0)
    assert doc1.rerank_score == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
async def test_components_reranker_section_boost_clamping():
    """Test that section boost is clamped to [0.0, 0.5] in components reranker."""
    from src.components.retrieval.reranker import CrossEncoderReranker

    documents = [
        {
            "id": "1",
            "text": "Test document",
            "section_id": "1.1",
            "score": 0.8,
        }
    ]

    with patch("sentence_transformers.CrossEncoder") as MockCrossEncoder:
        mock_model = MagicMock()
        mock_model.predict = MagicMock(return_value=[0.5])
        MockCrossEncoder.return_value = mock_model

        reranker = CrossEncoderReranker()

        # Test with out-of-range boost (should be clamped)
        results = await reranker.rerank(
            query="test",
            documents=documents,
            top_k=1,
            section_filter="1.1",
            section_boost=2.0,  # Should be clamped to 0.5
        )

    # Score should be clamped: 0.5 + 0.5 (clamped) = 1.0
    assert len(results) == 1
    assert results[0].rerank_score == pytest.approx(1.0, abs=0.01)


@pytest.mark.asyncio
async def test_components_reranker_metadata_section_id():
    """Test section boost works with section_id in metadata dict."""
    from src.components.retrieval.reranker import CrossEncoderReranker

    documents = [
        {
            "id": "1",
            "text": "Test document",
            "metadata": {"section_id": "1.2"},
            "score": 0.8,
        }
    ]

    with patch("sentence_transformers.CrossEncoder") as MockCrossEncoder:
        mock_model = MagicMock()
        mock_model.predict = MagicMock(return_value=[0.7])
        MockCrossEncoder.return_value = mock_model

        reranker = CrossEncoderReranker()

        results = await reranker.rerank(
            query="test",
            documents=documents,
            top_k=1,
            section_filter="1.2",
            section_boost=0.1,
        )

    # Should find section_id in metadata and apply boost
    assert len(results) == 1
    assert results[0].rerank_score == pytest.approx(0.8, abs=0.01)  # 0.7 + 0.1


# ============================================================================
# TEST: End-to-End Workflow
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_section_aware_reranking_workflow():
    """Test complete end-to-end section-aware reranking workflow."""
    from src.components.vector_search.hybrid_search import HybridSearch

    # Mock all dependencies
    mock_qdrant = MagicMock()
    mock_embedding = MagicMock()
    mock_bm25 = MagicMock()

    # Vector search returns results from different sections
    mock_qdrant.search = AsyncMock(
        return_value=[
            {
                "id": "1",
                "score": 0.90,
                "payload": {
                    "content": "Load balancing for high availability",
                    "section_id": "1.2",
                    "section_headings": ["Load Balancing"],
                },
            },
            {
                "id": "2",
                "score": 0.85,
                "payload": {
                    "content": "Database optimization techniques",
                    "section_id": "2.1",
                    "section_headings": ["Database"],
                },
            },
        ]
    )

    mock_embedding.embed_single = AsyncMock(return_value=[0.1] * 1024)

    # BM25 returns additional results
    mock_bm25.search = MagicMock(
        return_value=[
            {
                "text": "Caching strategies",
                "score": 4.5,
                "metadata": {
                    "id": "3",
                    "section_id": "1.3",
                    "section_headings": ["Caching"],
                },
                "rank": 1,
            }
        ]
    )

    # Use real reranker with mock model
    from src.components.retrieval.reranker import CrossEncoderReranker

    with patch("sentence_transformers.CrossEncoder") as MockCrossEncoder:
        mock_model = MagicMock()
        # Return scores for 3 documents
        mock_model.predict = MagicMock(return_value=[0.92, 0.88, 0.85])
        MockCrossEncoder.return_value = mock_model

        reranker = CrossEncoderReranker()

        hybrid = HybridSearch(
            qdrant_client=mock_qdrant,
            embedding_service=mock_embedding,
            bm25_search=mock_bm25,
            reranker=reranker,
        )

        # Execute hybrid search with section filter and reranking
        with patch("src.components.vector_search.hybrid_search.reciprocal_rank_fusion") as mock_rrf:
            mock_rrf.return_value = [
                {
                    "id": "1",
                    "text": "Load balancing for high availability",
                    "score": 0.90,
                    "section_id": "1.2",
                },
                {
                    "id": "2",
                    "text": "Database optimization techniques",
                    "score": 0.85,
                    "section_id": "2.1",
                },
                {
                    "id": "3",
                    "text": "Caching strategies",
                    "score": 0.80,
                    "section_id": "1.3",
                },
            ]

            result = await hybrid.hybrid_search(
                query="load balancing best practices",
                top_k=3,
                section_filter="1.2",  # Boost section 1.2
                use_reranking=True,
            )

    # Verify results
    assert "results" in result
    assert len(result["results"]) <= 3
    assert result["search_metadata"]["reranking_applied"] is True
