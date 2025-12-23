"""Unit tests for research searcher.

Sprint 62 Feature 62.10: Research Endpoint Backend
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.research.searcher import (
    deduplicate_results,
    evaluate_results,
    execute_searches,
    execute_single_query,
    rank_results,
)


@pytest.fixture
def sample_results():
    """Sample search results for testing."""
    return [
        {
            "text": "Machine learning is a subset of AI.",
            "score": 0.9,
            "source": "vector",
            "metadata": {"doc_id": "1"},
            "query": "What is ML?",
        },
        {
            "text": "Deep learning uses neural networks.",
            "score": 0.8,
            "source": "graph",
            "entities": ["Deep Learning", "Neural Networks"],
            "relationships": ["uses"],
            "metadata": {"doc_id": "2"},
            "query": "What is DL?",
        },
    ]


@pytest.mark.asyncio
class TestExecuteSearches:
    """Test multi-query search execution."""

    async def test_execute_searches_basic(self):
        """Test basic search execution."""
        with (
            patch(
                "src.agents.research.searcher._execute_vector_search",
                new_callable=AsyncMock,
            ) as mock_vector,
            patch(
                "src.agents.research.searcher._execute_graph_search",
                new_callable=AsyncMock,
            ) as mock_graph,
        ):
            # Mock responses
            mock_vector.return_value = [{"text": "Vector result", "score": 0.9, "source": "vector"}]
            mock_graph.return_value = [{"text": "Graph result", "score": 0.8, "source": "graph"}]

            results = await execute_searches(
                queries=["Query 1", "Query 2"],
                top_k=5,
                use_graph=True,
                use_vector=True,
                namespace="test_ns",
            )

            # Should call both searches for each query
            assert mock_vector.call_count == 2
            assert mock_graph.call_count == 2

            # Should have results from both searches
            assert len(results) > 0

    async def test_execute_searches_vector_only(self):
        """Test search with vector only."""
        with (
            patch(
                "src.agents.research.searcher._execute_vector_search",
                new_callable=AsyncMock,
            ) as mock_vector,
            patch(
                "src.agents.research.searcher._execute_graph_search",
                new_callable=AsyncMock,
            ) as mock_graph,
        ):
            mock_vector.return_value = [{"text": "Result", "score": 0.9, "source": "vector"}]

            await execute_searches(
                queries=["Query 1"],
                use_graph=False,
                use_vector=True,
                namespace="test_ns",
            )

            assert mock_vector.call_count == 1
            assert mock_graph.call_count == 0

    async def test_execute_searches_graph_only(self):
        """Test search with graph only."""
        with (
            patch(
                "src.agents.research.searcher._execute_vector_search",
                new_callable=AsyncMock,
            ) as mock_vector,
            patch(
                "src.agents.research.searcher._execute_graph_search",
                new_callable=AsyncMock,
            ) as mock_graph,
        ):
            mock_graph.return_value = [{"text": "Result", "score": 0.8, "source": "graph"}]

            await execute_searches(
                queries=["Query 1"],
                use_graph=True,
                use_vector=False,
                namespace="test_ns",
            )

            assert mock_vector.call_count == 0
            assert mock_graph.call_count == 1

    async def test_execute_searches_namespace_propagation(self):
        """Test that namespace is passed to search functions."""
        with patch(
            "src.agents.research.searcher._execute_vector_search",
            new_callable=AsyncMock,
        ) as mock_vector:
            mock_vector.return_value = []

            await execute_searches(
                queries=["Query 1"],
                use_vector=True,
                use_graph=False,
                namespace="custom_ns",
            )

            # Verify namespace was passed
            mock_vector.assert_called_once()
            args, kwargs = mock_vector.call_args
            assert args[2] == "custom_ns"  # Third argument is namespace


@pytest.mark.asyncio
class TestExecuteSingleQuery:
    """Test single query execution."""

    async def test_execute_single_query_success(self):
        """Test successful single query execution."""
        with (
            patch(
                "src.agents.research.searcher._execute_vector_search",
                new_callable=AsyncMock,
            ) as mock_vector,
            patch(
                "src.agents.research.searcher._execute_graph_search",
                new_callable=AsyncMock,
            ) as mock_graph,
        ):
            mock_vector.return_value = [{"text": "Vector", "score": 0.9}]
            mock_graph.return_value = [{"text": "Graph", "score": 0.8}]

            results = await execute_single_query(
                query="Test query",
                top_k=5,
                use_graph=True,
                use_vector=True,
                namespace="test_ns",
            )

            assert len(results) == 2

    async def test_execute_single_query_handles_errors(self):
        """Test error handling in single query execution."""
        with patch(
            "src.agents.research.searcher._execute_vector_search",
            new_callable=AsyncMock,
        ) as mock_vector:
            mock_vector.side_effect = Exception("Search failed")

            # Should not raise, returns empty list
            results = await execute_single_query(
                query="Test query",
                use_vector=True,
                use_graph=False,
                namespace="test_ns",
            )

            assert results == []


class TestDeduplicateResults:
    """Test result deduplication."""

    def test_deduplicate_results_removes_duplicates(self):
        """Test that duplicates are removed."""
        results = [
            {"text": "Same content here", "score": 0.9},
            {"text": "Same content here", "score": 0.8},
            {"text": "Different content", "score": 0.7},
        ]

        unique = deduplicate_results(results)

        assert len(unique) == 2

    def test_deduplicate_results_preserves_unique(self):
        """Test that unique results are preserved."""
        results = [
            {"text": "Content A", "score": 0.9},
            {"text": "Content B", "score": 0.8},
            {"text": "Content C", "score": 0.7},
        ]

        unique = deduplicate_results(results)

        assert len(unique) == 3

    def test_deduplicate_results_empty_input(self):
        """Test deduplication with empty input."""
        unique = deduplicate_results([])

        assert unique == []

    def test_deduplicate_results_similar_start(self):
        """Test deduplication with similar text starts."""
        results = [
            {"text": "A" * 300 + " different end 1", "score": 0.9},
            {"text": "A" * 300 + " different end 2", "score": 0.8},
        ]

        # Should treat as duplicates (first 200 chars are same)
        unique = deduplicate_results(results)

        assert len(unique) == 1


class TestRankResults:
    """Test result ranking."""

    def test_rank_results_by_score(self, sample_results):
        """Test ranking by score."""
        ranked = rank_results(sample_results, "test query")

        # Graph gets priority (2x multiplier), so even with 0.8 score,
        # graph result comes first with effective score of 1.6 vs vector's 0.9
        assert ranked[0]["source"] == "graph"
        assert ranked[1]["source"] == "vector"

    def test_rank_results_graph_priority(self):
        """Test that graph results get priority."""
        results = [
            {"text": "Vector", "score": 0.9, "source": "vector"},
            {"text": "Graph", "score": 0.9, "source": "graph"},
        ]

        ranked = rank_results(results, "test query")

        # Graph should be first (2x multiplier)
        assert ranked[0]["source"] == "graph"

    def test_rank_results_empty(self):
        """Test ranking empty results."""
        ranked = rank_results([], "test query")

        assert ranked == []


@pytest.mark.asyncio
class TestEvaluateResults:
    """Test result evaluation."""

    async def test_evaluate_results_sufficient(self, sample_results):
        """Test evaluation of sufficient results."""
        # Add more results to reach threshold
        results = sample_results * 3  # 6 results

        metrics = await evaluate_results(results, "test query")

        assert metrics["num_results"] == 6
        assert metrics["sufficient"] is True
        assert metrics["avg_score"] > 0

    async def test_evaluate_results_insufficient(self):
        """Test evaluation of insufficient results."""
        results = [
            {"text": "Only one result", "score": 0.3, "source": "vector"},
        ]

        metrics = await evaluate_results(results, "test query")

        assert metrics["sufficient"] is False

    async def test_evaluate_results_empty(self):
        """Test evaluation of empty results."""
        metrics = await evaluate_results([], "test query")

        assert metrics["coverage"] == 0.0
        assert metrics["diversity"] == 0.0
        assert metrics["quality"] == 0.0
        assert metrics["sufficient"] is False

    async def test_evaluate_results_multiple_sources(self, sample_results):
        """Test diversity calculation with multiple sources."""
        # sample_results has both vector and graph sources
        metrics = await evaluate_results(sample_results * 3, "test query")

        # Should detect 2 sources
        assert metrics["num_sources"] == 2
        assert metrics["diversity"] == 1.0  # 2/2 = 1.0
