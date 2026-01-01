"""Unit tests for research searcher.

Sprint 70 Feature 70.2: Test searcher with CoordinatorAgent reuse.
"""

import pytest

from src.agents.research.searcher import (
    deduplicate_contexts,
    evaluate_search_quality,
    execute_research_queries,
)


class TestDeduplicateContexts:
    """Test context deduplication."""

    def test_deduplicate_identical(self):
        """Test deduplication of identical contexts."""
        contexts = [
            {"text": "Same text here", "score": 0.9},
            {"text": "Same text here", "score": 0.8},
            {"text": "Different text", "score": 0.7},
        ]

        unique = deduplicate_contexts(contexts)

        assert len(unique) == 2
        assert unique[0]["text"] == "Same text here"
        assert unique[1]["text"] == "Different text"

    def test_deduplicate_empty(self):
        """Test deduplication of empty list."""
        unique = deduplicate_contexts([])
        assert len(unique) == 0

    def test_deduplicate_all_unique(self):
        """Test deduplication with all unique contexts."""
        contexts = [
            {"text": "Text 1", "score": 0.9},
            {"text": "Text 2", "score": 0.8},
            {"text": "Text 3", "score": 0.7},
        ]

        unique = deduplicate_contexts(contexts)

        assert len(unique) == 3

    def test_deduplicate_case_insensitive(self):
        """Test that deduplication is case-insensitive."""
        contexts = [
            {"text": "SAME TEXT", "score": 0.9},
            {"text": "same text", "score": 0.8},
        ]

        unique = deduplicate_contexts(contexts)

        # Should deduplicate (case-insensitive)
        assert len(unique) == 1


class TestEvaluateSearchQuality:
    """Test search quality evaluation."""

    def test_evaluate_excellent_quality(self):
        """Test evaluation of excellent results."""
        contexts = [
            {"text": "Context 1", "score": 0.9},
            {"text": "Context 2", "score": 0.8},
            {"text": "Context 3", "score": 0.85},
            {"text": "Context 4", "score": 0.75},
            {"text": "Context 5", "score": 0.7},
            {"text": "Context 6", "score": 0.8},
            {"text": "Context 7", "score": 0.9},
            {"text": "Context 8", "score": 0.85},
            {"text": "Context 9", "score": 0.75},
            {"text": "Context 10", "score": 0.8},
        ]

        metrics = evaluate_search_quality(contexts)

        assert metrics["num_results"] == 10
        assert metrics["avg_score"] > 0.7
        assert metrics["quality"] == "excellent"
        assert metrics["sufficient"] is True

    def test_evaluate_good_quality(self):
        """Test evaluation of good results."""
        contexts = [
            {"text": "Context 1", "score": 0.6},
            {"text": "Context 2", "score": 0.5},
            {"text": "Context 3", "score": 0.7},
            {"text": "Context 4", "score": 0.6},
            {"text": "Context 5", "score": 0.5},
        ]

        metrics = evaluate_search_quality(contexts)

        assert metrics["num_results"] == 5
        assert metrics["quality"] == "good"
        assert metrics["sufficient"] is True

    def test_evaluate_fair_quality(self):
        """Test evaluation of fair results."""
        contexts = [
            {"text": "Context 1", "score": 0.4},
            {"text": "Context 2", "score": 0.3},
            {"text": "Context 3", "score": 0.5},
        ]

        metrics = evaluate_search_quality(contexts)

        assert metrics["num_results"] == 3
        assert metrics["quality"] == "fair"
        assert metrics["sufficient"] is False

    def test_evaluate_poor_quality(self):
        """Test evaluation of poor results."""
        contexts = [
            {"text": "Context 1", "score": 0.2},
        ]

        metrics = evaluate_search_quality(contexts)

        assert metrics["num_results"] == 1
        assert metrics["quality"] == "poor"
        assert metrics["sufficient"] is False

    def test_evaluate_no_results(self):
        """Test evaluation with no results."""
        metrics = evaluate_search_quality([])

        assert metrics["num_results"] == 0
        assert metrics["avg_score"] == 0.0
        assert metrics["quality"] == "poor"
        assert metrics["sufficient"] is False


class TestExecuteResearchQueries:
    """Test research query execution."""

    @pytest.mark.asyncio
    async def test_execute_queries_success(self, mocker):
        """Test successful query execution."""
        # Mock CoordinatorAgent with different contexts for each query
        mock_coordinator = mocker.MagicMock()

        # Side effect returns different contexts based on query
        async def process_query_side_effect(*args, **kwargs):
            query = kwargs.get("query", "")
            if "AI" in query:
                return {
                    "retrieved_contexts": [
                        {"text": "AI Context 1", "score": 0.9, "source_channel": "vector"},
                        {"text": "AI Context 2", "score": 0.8, "source_channel": "graph_global"},
                    ]
                }
            else:  # ML query
                return {
                    "retrieved_contexts": [
                        {"text": "ML Context 1", "score": 0.9, "source_channel": "vector"},
                        {"text": "ML Context 2", "score": 0.8, "source_channel": "bm25"},
                    ]
                }

        mock_coordinator.process_query = mocker.AsyncMock(
            side_effect=process_query_side_effect
        )

        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mock_coordinator,
        )

        # Execute
        queries = ["What is AI?", "What is ML?"]
        contexts = await execute_research_queries(
            queries=queries,
            namespace="test",
            top_k_per_query=5,
        )

        # Verify
        assert len(contexts) == 4  # 2 contexts per query, 2 queries
        assert contexts[0]["research_query"] == "What is AI?"
        assert contexts[2]["research_query"] == "What is ML?"
        assert contexts[0]["query_index"] == 1
        assert contexts[2]["query_index"] == 2

        # Verify CoordinatorAgent was called correctly
        assert mock_coordinator.process_query.call_count == 2
        first_call = mock_coordinator.process_query.call_args_list[0]
        assert first_call[1]["query"] == "What is AI?"
        assert first_call[1]["intent"] == "hybrid"
        assert first_call[1]["namespace"] == "test"

    @pytest.mark.asyncio
    async def test_execute_queries_with_error(self, mocker):
        """Test query execution with partial errors."""
        # Mock CoordinatorAgent with error on second query
        mock_coordinator = mocker.MagicMock()

        async def process_query_side_effect(*args, **kwargs):
            if kwargs["query"] == "What is AI?":
                return {
                    "retrieved_contexts": [
                        {"text": "AI context", "score": 0.9, "source_channel": "vector"}
                    ]
                }
            else:
                raise Exception("Query failed")

        mock_coordinator.process_query = mocker.AsyncMock(
            side_effect=process_query_side_effect
        )

        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mock_coordinator,
        )

        # Execute
        queries = ["What is AI?", "What is ML?"]
        contexts = await execute_research_queries(queries=queries)

        # Should still return contexts from successful query
        assert len(contexts) == 1
        assert contexts[0]["text"] == "AI context"

    @pytest.mark.asyncio
    async def test_execute_queries_deduplication(self, mocker):
        """Test that duplicate contexts are removed."""
        # Mock CoordinatorAgent returning duplicate contexts
        mock_coordinator = mocker.MagicMock()
        mock_coordinator.process_query = mocker.AsyncMock(
            return_value={
                "retrieved_contexts": [
                    {"text": "Same context", "score": 0.9, "source_channel": "vector"},
                    {"text": "Same context", "score": 0.8, "source_channel": "bm25"},
                ]
            }
        )

        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mock_coordinator,
        )

        # Execute
        queries = ["What is AI?"]
        contexts = await execute_research_queries(queries=queries)

        # Should deduplicate
        assert len(contexts) == 1
        assert contexts[0]["text"] == "Same context"

    @pytest.mark.asyncio
    async def test_execute_queries_empty_list(self, mocker):
        """Test execution with empty query list."""
        mock_coordinator = mocker.MagicMock()

        mocker.patch(
            "src.agents.coordinator.CoordinatorAgent",
            return_value=mock_coordinator,
        )

        # Execute
        contexts = await execute_research_queries(queries=[])

        # Should return empty list
        assert len(contexts) == 0
        mock_coordinator.process_query.assert_not_called()
