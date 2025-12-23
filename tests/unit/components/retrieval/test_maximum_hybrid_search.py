"""Unit tests for Maximum Hybrid Search.

Sprint 51 - Feature 51.7: Maximum Hybrid Search Foundation

Tests for 4-signal hybrid search combining Qdrant, BM25, and LightRAG local/global.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.maximum_hybrid_search import (
    _bm25_search,
    _lightrag_global_search,
    _lightrag_local_search,
    _qdrant_search,
    maximum_hybrid_search,
)


class TestMaximumHybridSearch:
    """Tests for maximum_hybrid_search() main function."""

    @pytest.mark.asyncio
    async def test_maximum_hybrid_search_all_signals(self):
        """Test maximum hybrid search executes all 4 signals in parallel."""
        # Mock all 4 retrieval channels
        mock_qdrant_result = {
            "results": [
                {"id": "chunk1", "text": "Amsterdam", "score": 0.9, "rank": 1},
                {"id": "chunk2", "text": "Netherlands", "score": 0.8, "rank": 2},
            ],
            "latency_ms": 50.0,
        }

        mock_bm25_result = {
            "results": [
                {"id": "chunk2", "text": "Netherlands", "score": 15.0, "rank": 1},
                {"id": "chunk3", "text": "Europe", "score": 12.0, "rank": 2},
            ],
            "latency_ms": 30.0,
        }

        mock_local_context = """# Entities
- Amsterdam: Capital city of Netherlands
- Netherlands: Country in Europe
"""

        mock_global_context = """## Community 1
- Theme: European Geography
- Entities: Amsterdam, Netherlands, Europe
"""

        with (
            patch(
                "src.components.retrieval.maximum_hybrid_search._qdrant_search",
                return_value=mock_qdrant_result,
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._bm25_search",
                return_value=mock_bm25_result,
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_local_search",
                return_value={"context": mock_local_context, "latency_ms": 100.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_global_search",
                return_value={"context": mock_global_context, "latency_ms": 120.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search.cross_modal_fusion"
            ) as mock_fusion,
        ):
            # Mock cross_modal_fusion to return input unchanged
            mock_fusion.side_effect = lambda chunk_ranking, **kwargs: chunk_ranking

            result = await maximum_hybrid_search(
                query="What is Amsterdam?",
                top_k=5,
            )

            # Verify all signals were queried
            assert result.qdrant_results_count == 2
            assert result.bm25_results_count == 2
            assert result.lightrag_local_entities_count == 2
            assert result.lightrag_global_communities_count == 1

            # Verify RRF fusion happened (combined chunks)
            assert result.total_results > 0
            assert len(result.results) <= 5  # top_k limit

            # Verify latencies recorded
            assert result.qdrant_latency_ms > 0
            assert result.bm25_latency_ms > 0
            assert result.total_latency_ms > 0

    @pytest.mark.asyncio
    async def test_maximum_hybrid_search_cross_modal_fusion(self):
        """Test that cross-modal fusion is applied when enabled."""
        mock_chunks = [{"id": "chunk1", "rrf_score": 0.8, "rank": 1}]

        with (
            patch(
                "src.components.retrieval.maximum_hybrid_search._qdrant_search",
                return_value={"results": mock_chunks, "latency_ms": 50.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._bm25_search",
                return_value={"results": [], "latency_ms": 30.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_local_search",
                return_value={
                    "context": "# Entities\n- Amsterdam: Capital",
                    "latency_ms": 100.0,
                },
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_global_search",
                return_value={"context": "", "latency_ms": 0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search.cross_modal_fusion"
            ) as mock_fusion,
        ):
            # Mock fusion adds entity_boost
            mock_fusion.return_value = [
                {
                    **mock_chunks[0],
                    "entity_boost": 0.1,
                    "final_score": 0.9,
                    "cross_modal_boosted": True,
                }
            ]

            result = await maximum_hybrid_search(
                query="What is Amsterdam?",
                top_k=5,
                use_cross_modal_fusion=True,
            )

            # Verify cross-modal fusion was called
            mock_fusion.assert_called_once()
            assert result.chunks_boosted_count == 1
            assert result.boost_percentage == 100.0

    @pytest.mark.asyncio
    async def test_maximum_hybrid_search_disable_fusion(self):
        """Test maximum hybrid search with cross-modal fusion disabled."""
        with (
            patch(
                "src.components.retrieval.maximum_hybrid_search._qdrant_search",
                return_value={"results": [{"id": "chunk1", "rrf_score": 0.8}], "latency_ms": 50.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._bm25_search",
                return_value={"results": [], "latency_ms": 30.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_local_search",
                return_value={"context": "# Entities\n- Amsterdam: Capital", "latency_ms": 100.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_global_search",
                return_value={"context": "", "latency_ms": 0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search.cross_modal_fusion"
            ) as mock_fusion,
        ):
            result = await maximum_hybrid_search(
                query="What is Amsterdam?",
                use_cross_modal_fusion=False,
            )

            # Verify cross-modal fusion was NOT called
            mock_fusion.assert_not_called()
            assert result.chunks_boosted_count == 0

    @pytest.mark.asyncio
    async def test_maximum_hybrid_search_handles_errors(self):
        """Test graceful error handling when signals fail."""
        # Qdrant fails, others succeed
        with (
            patch(
                "src.components.retrieval.maximum_hybrid_search._qdrant_search",
                side_effect=Exception("Qdrant connection failed"),
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._bm25_search",
                return_value={"results": [{"id": "chunk1", "score": 10.0}], "latency_ms": 30.0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_local_search",
                return_value={"context": "", "latency_ms": 0},
            ),
            patch(
                "src.components.retrieval.maximum_hybrid_search._lightrag_global_search",
                return_value={"context": "", "latency_ms": 0},
            ),
            patch("src.components.retrieval.maximum_hybrid_search.cross_modal_fusion"),
        ):
            result = await maximum_hybrid_search(query="test", use_cross_modal_fusion=False)

            # Should still return results from BM25
            assert result.qdrant_results_count == 0  # Failed signal
            assert result.bm25_results_count == 1  # Succeeded


class TestQdrantSearch:
    """Tests for _qdrant_search() helper function."""

    @pytest.mark.asyncio
    async def test_qdrant_search_success(self):
        """Test successful Qdrant search."""
        mock_hybrid_search = MagicMock()
        mock_hybrid_search.vector_search = AsyncMock(
            return_value=[
                {"id": "chunk1", "text": "Amsterdam", "score": 0.9, "metadata": {}},
                {"id": "chunk2", "text": "Netherlands", "score": 0.8, "metadata": {}},
            ]
        )

        result = await _qdrant_search(
            hybrid_search=mock_hybrid_search,
            query="Amsterdam",
            top_k=10,
        )

        assert result["results"] == [
            {"id": "chunk1", "text": "Amsterdam", "score": 0.9, "metadata": {}},
            {"id": "chunk2", "text": "Netherlands", "score": 0.8, "metadata": {}},
        ]
        assert result["latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_qdrant_search_handles_error(self):
        """Test error handling in Qdrant search."""
        mock_hybrid_search = MagicMock()
        mock_hybrid_search.vector_search = AsyncMock(side_effect=Exception("Connection failed"))

        result = await _qdrant_search(
            hybrid_search=mock_hybrid_search,
            query="test",
            top_k=10,
        )

        assert result["results"] == []
        assert result["latency_ms"] == 0


class TestBM25Search:
    """Tests for _bm25_search() helper function."""

    @pytest.mark.asyncio
    async def test_bm25_search_success(self):
        """Test successful BM25 search."""
        mock_hybrid_search = MagicMock()
        mock_hybrid_search.keyword_search = AsyncMock(
            return_value=[
                {"id": "chunk1", "text": "Amsterdam", "score": 15.0, "metadata": {}},
            ]
        )

        result = await _bm25_search(
            hybrid_search=mock_hybrid_search,
            query="Amsterdam",
            top_k=10,
        )

        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "chunk1"
        assert result["latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_bm25_search_handles_error(self):
        """Test error handling in BM25 search."""
        mock_hybrid_search = MagicMock()
        mock_hybrid_search.keyword_search = AsyncMock(side_effect=Exception("BM25 failed"))

        result = await _bm25_search(
            hybrid_search=mock_hybrid_search,
            query="test",
            top_k=10,
        )

        assert result["results"] == []
        assert result["latency_ms"] == 0


class TestLightRAGLocalSearch:
    """Tests for _lightrag_local_search() helper function."""

    @pytest.mark.asyncio
    async def test_lightrag_local_search_success(self):
        """Test successful LightRAG local mode query."""
        mock_lightrag = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "# Entities\n- Amsterdam: Capital city"
        mock_lightrag.query_graph = AsyncMock(return_value=mock_result)

        result = await _lightrag_local_search(
            lightrag_client=mock_lightrag,
            query="Amsterdam",
        )

        assert result["context"] == "# Entities\n- Amsterdam: Capital city"
        assert result["latency_ms"] > 0

        # Verify query_graph called with local mode
        mock_lightrag.query_graph.assert_called_once()
        call_kwargs = mock_lightrag.query_graph.call_args.kwargs
        assert call_kwargs["mode"] == "local"

    @pytest.mark.asyncio
    async def test_lightrag_local_search_handles_error(self):
        """Test error handling in LightRAG local search."""
        mock_lightrag = MagicMock()
        mock_lightrag.query_graph = AsyncMock(side_effect=Exception("LightRAG failed"))

        result = await _lightrag_local_search(
            lightrag_client=mock_lightrag,
            query="test",
        )

        assert result["context"] == ""
        assert result["latency_ms"] == 0


class TestLightRAGGlobalSearch:
    """Tests for _lightrag_global_search() helper function."""

    @pytest.mark.asyncio
    async def test_lightrag_global_search_success(self):
        """Test successful LightRAG global mode query."""
        mock_lightrag = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "## Community 1\n- Theme: Geography"
        mock_lightrag.query_graph = AsyncMock(return_value=mock_result)

        result = await _lightrag_global_search(
            lightrag_client=mock_lightrag,
            query="Amsterdam",
        )

        assert result["context"] == "## Community 1\n- Theme: Geography"
        assert result["latency_ms"] > 0

        # Verify query_graph called with global mode
        call_kwargs = mock_lightrag.query_graph.call_args.kwargs
        assert call_kwargs["mode"] == "global"

    @pytest.mark.asyncio
    async def test_lightrag_global_search_handles_error(self):
        """Test error handling in LightRAG global search."""
        mock_lightrag = MagicMock()
        mock_lightrag.query_graph = AsyncMock(side_effect=Exception("LightRAG failed"))

        result = await _lightrag_global_search(
            lightrag_client=mock_lightrag,
            query="test",
        )

        assert result["context"] == ""
        assert result["latency_ms"] == 0
