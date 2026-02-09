"""Integration tests for HyDE with Maximum Hybrid Search.

Sprint 128 Feature 128.4: HyDE Integration Tests

This module tests the integration of HyDE into the Maximum Hybrid Search pipeline:
1. HyDE runs in parallel with other signals (Qdrant, BM25, Graph)
2. HyDE results are fused via RRF
3. HyDE can be enabled/disabled via settings
4. HyDE metadata is included in results

Test Strategy:
    - Use real settings but mock external services
    - Test parallel execution with asyncio.gather
    - Verify RRF fusion includes HyDE results
    - Test enable/disable toggle
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.retrieval.maximum_hybrid_search import maximum_hybrid_search


@pytest.fixture
def mock_hybrid_search():
    """Mock HybridSearch for vector/BM25 operations."""
    search = MagicMock()
    search.vector_search = AsyncMock(
        return_value=[{"id": "chunk_1", "score": 0.9, "content": "Amsterdam is the capital."}]
    )
    search.keyword_search = AsyncMock(
        return_value=[{"id": "chunk_2", "score": 0.8, "content": "Netherlands is in Europe."}]
    )
    return search


@pytest.fixture
def mock_dual_level_search():
    """Mock DualLevelSearch for graph operations."""
    from src.core.models import GraphEntity, Topic

    search = MagicMock()

    # Mock local search
    entity = GraphEntity(
        id="entity_1",
        name="Amsterdam",
        entity_type="City",
        properties={"matched_entities": ["Amsterdam", "Netherlands"]},
    )
    search.local_search = AsyncMock(return_value=([entity], {}))

    # Mock global search
    topic = Topic(
        name="European Cities",
        summary="Overview of major European cities",
        entities=["Amsterdam", "Berlin", "Paris"],
        keywords=["city", "europe", "capital"],
    )
    search.global_search = AsyncMock(return_value=[topic])

    return search


@pytest.fixture
def mock_hyde_generator():
    """Mock HyDEGenerator for hypothetical document generation."""
    generator = MagicMock()
    generator.hyde_search = AsyncMock(
        return_value=[
            {
                "id": "chunk_3",
                "score": 0.85,
                "content": "Amsterdam is known for canals.",
                "source": "hyde",
                "metadata": {},
            }
        ]
    )
    generator.generate_hypothetical_document = AsyncMock(
        return_value="Amsterdam is the capital and most populous city of the Netherlands."
    )
    return generator


@pytest.mark.asyncio
async def test_maximum_hybrid_search_with_hyde_enabled(
    mock_hybrid_search, mock_dual_level_search, mock_hyde_generator
):
    """Test Maximum Hybrid Search with HyDE enabled."""
    with (
        patch(
            "src.components.retrieval.maximum_hybrid_search.HybridSearch",
            return_value=mock_hybrid_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_dual_level_search",
            return_value=mock_dual_level_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_hyde_generator",
            return_value=mock_hyde_generator,
        ),
        patch("src.components.retrieval.maximum_hybrid_search.cross_modal_fusion") as mock_fusion,
        patch("src.components.retrieval.maximum_hybrid_search.settings") as mock_settings,
    ):
        # Enable HyDE
        mock_settings.hyde_enabled = True
        mock_settings.hyde_weight = 0.5
        mock_settings.hyde_max_tokens = 512
        mock_settings.qdrant_host = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection = "documents_v1"

        # Mock fusion to return input unchanged
        mock_fusion.side_effect = lambda chunk_ranking, **kwargs: chunk_ranking

        # Execute search
        result = await maximum_hybrid_search(
            query="What is Amsterdam?",
            top_k=10,
            use_cross_modal_fusion=False,  # Disable for simpler test
        )

        # Verify HyDE was called
        assert mock_hyde_generator.hyde_search.called

        # Verify result metadata
        assert result.hyde_enabled is True
        assert result.hyde_results_count == 1
        assert result.hypothetical_document is not None
        assert "Amsterdam" in result.hypothetical_document


@pytest.mark.asyncio
async def test_maximum_hybrid_search_with_hyde_disabled(
    mock_hybrid_search, mock_dual_level_search, mock_hyde_generator
):
    """Test Maximum Hybrid Search with HyDE disabled."""
    with (
        patch(
            "src.components.retrieval.maximum_hybrid_search.HybridSearch",
            return_value=mock_hybrid_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_dual_level_search",
            return_value=mock_dual_level_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_hyde_generator",
            return_value=mock_hyde_generator,
        ),
        patch("src.components.retrieval.maximum_hybrid_search.cross_modal_fusion") as mock_fusion,
        patch("src.components.retrieval.maximum_hybrid_search.settings") as mock_settings,
    ):
        # Disable HyDE
        mock_settings.hyde_enabled = False
        mock_settings.hyde_weight = 0.5
        mock_settings.hyde_max_tokens = 512
        mock_settings.qdrant_host = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection = "documents_v1"

        # Mock fusion to return input unchanged
        mock_fusion.side_effect = lambda chunk_ranking, **kwargs: chunk_ranking

        # Execute search
        result = await maximum_hybrid_search(
            query="What is Amsterdam?",
            top_k=10,
            use_cross_modal_fusion=False,
        )

        # Verify HyDE was NOT called
        assert not mock_hyde_generator.hyde_search.called

        # Verify result metadata
        assert result.hyde_enabled is False
        assert result.hyde_results_count == 0
        assert result.hypothetical_document is None


@pytest.mark.asyncio
async def test_maximum_hybrid_search_hyde_parallel_execution(
    mock_hybrid_search, mock_dual_level_search, mock_hyde_generator
):
    """Test that HyDE executes in parallel with other signals."""
    execution_times = []

    async def track_time(name):
        """Track execution time for each signal."""
        import time

        start = time.perf_counter()
        # Simulate some work
        import asyncio

        await asyncio.sleep(0.01)
        end = time.perf_counter()
        execution_times.append((name, start, end))

    # Wrap each search method to track execution time
    mock_hybrid_search.vector_search = AsyncMock(
        side_effect=lambda **kwargs: track_time("vector") or [{"id": "c1", "score": 0.9}]
    )
    mock_hyde_generator.hyde_search = AsyncMock(
        side_effect=lambda **kwargs: track_time("hyde")
        or [{"id": "c2", "score": 0.85, "source": "hyde", "metadata": {}}]
    )

    with (
        patch(
            "src.components.retrieval.maximum_hybrid_search.HybridSearch",
            return_value=mock_hybrid_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_dual_level_search",
            return_value=mock_dual_level_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_hyde_generator",
            return_value=mock_hyde_generator,
        ),
        patch("src.components.retrieval.maximum_hybrid_search.cross_modal_fusion") as mock_fusion,
        patch("src.components.retrieval.maximum_hybrid_search.settings") as mock_settings,
    ):
        mock_settings.hyde_enabled = True
        mock_settings.hyde_weight = 0.5
        mock_settings.hyde_max_tokens = 512
        mock_settings.qdrant_host = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection = "documents_v1"

        mock_fusion.side_effect = lambda chunk_ranking, **kwargs: chunk_ranking

        # Execute search
        await maximum_hybrid_search(
            query="What is Amsterdam?",
            top_k=10,
            use_cross_modal_fusion=False,
        )

        # Verify both were executed
        assert len(execution_times) >= 2

        # In parallel execution, start times should be close
        # (within ~10ms, allowing for asyncio overhead)
        if len(execution_times) >= 2:
            start_times = [t[1] for t in execution_times]
            time_diff = max(start_times) - min(start_times)
            assert time_diff < 0.1, "Signals should execute in parallel"


@pytest.mark.asyncio
async def test_maximum_hybrid_search_hyde_fusion(
    mock_hybrid_search, mock_dual_level_search, mock_hyde_generator
):
    """Test that HyDE results are included in RRF fusion."""
    with (
        patch(
            "src.components.retrieval.maximum_hybrid_search.HybridSearch",
            return_value=mock_hybrid_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_dual_level_search",
            return_value=mock_dual_level_search,
        ),
        patch(
            "src.components.retrieval.maximum_hybrid_search.get_hyde_generator",
            return_value=mock_hyde_generator,
        ),
        patch("src.components.retrieval.maximum_hybrid_search.reciprocal_rank_fusion") as mock_rrf,
        patch("src.components.retrieval.maximum_hybrid_search.cross_modal_fusion") as mock_fusion,
        patch("src.components.retrieval.maximum_hybrid_search.settings") as mock_settings,
    ):
        mock_settings.hyde_enabled = True
        mock_settings.hyde_weight = 0.5
        mock_settings.hyde_max_tokens = 512
        mock_settings.qdrant_host = "localhost"
        mock_settings.qdrant_port = 6333
        mock_settings.qdrant_collection = "documents_v1"

        # Mock RRF to return fused results
        mock_rrf.return_value = [
            {"id": "chunk_1", "score": 0.95},
            {"id": "chunk_3", "score": 0.88},
            {"id": "chunk_2", "score": 0.85},
        ]
        mock_fusion.side_effect = lambda chunk_ranking, **kwargs: chunk_ranking

        # Execute search
        result = await maximum_hybrid_search(
            query="What is Amsterdam?",
            top_k=10,
            use_cross_modal_fusion=False,
        )

        # Verify RRF was called with 3 rankings (Qdrant, HyDE, BM25)
        assert mock_rrf.called
        rrf_args = mock_rrf.call_args
        rankings = rrf_args.kwargs["rankings"]
        assert len(rankings) == 3  # Qdrant + HyDE + BM25

        # Verify results contain fused chunks
        assert len(result.results) > 0
