"""Unit tests for Research Agent.

Sprint 59 Feature 59.6: Agentic search tests.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.research.graph import create_research_graph, run_research
from src.agents.research.planner import evaluate_plan_quality, parse_plan, plan_research
from src.agents.research.searcher import (
    deduplicate_results,
    evaluate_results,
    execute_searches,
    rank_results,
)
from src.agents.research.synthesizer import (
    extract_key_points,
    format_results_for_synthesis,
    synthesize_findings,
)

# =============================================================================
# Planner Tests
# =============================================================================


class TestResearchPlanner:
    """Tests for research planning."""

    def test_parse_plan_numbered_list(self):
        """Test parsing numbered list format."""
        plan_text = """
1. Search for machine learning basics
2. Look up neural networks
3. Find deep learning applications
"""
        queries = parse_plan(plan_text)

        assert len(queries) == 3
        assert "machine learning" in queries[0].lower()
        assert "neural networks" in queries[1].lower()
        assert "deep learning" in queries[2].lower()

    def test_parse_plan_bullet_list(self):
        """Test parsing bullet list format."""
        plan_text = """
- First query
- Second query
- Third query
"""
        queries = parse_plan(plan_text)

        assert len(queries) == 3

    def test_parse_plan_fallback(self):
        """Test fallback parsing for unstructured text."""
        plan_text = """
This is a longer line that should be captured
Another line here
Short
"""
        queries = parse_plan(plan_text)

        # Should capture long lines, ignore short ones
        assert len(queries) >= 2

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM proxy module - implement when integrating with LLM")
    async def test_plan_research_with_llm(self):
        """Test research planning with LLM."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = """
1. Search for AI history
2. Look up current AI applications
3. Find future AI trends
"""

        with patch(
            "src.domains.llm_integration.proxy.aegis_proxy.get_aegis_llm_proxy"
        ) as mock_get_llm:
            mock_get_llm.return_value = mock_llm

            plan = await plan_research("What is artificial intelligence?")

            assert len(plan) >= 1
            mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM proxy module")
    async def test_plan_research_fallback_on_error(self):
        """Test fallback when LLM fails."""
        with patch(
            "src.domains.llm_integration.proxy.aegis_proxy.get_aegis_llm_proxy"
        ) as mock_get_llm:
            mock_get_llm.side_effect = Exception("LLM error")

            plan = await plan_research("test query")

            # Should fall back to original query
            assert plan == ["test query"]

    @pytest.mark.asyncio
    async def test_evaluate_plan_quality(self):
        """Test plan quality evaluation."""
        query = "What is AI?"
        plan = ["AI definition", "AI history", "AI applications"]

        quality = await evaluate_plan_quality(query, plan)

        assert "num_queries" in quality
        assert quality["num_queries"] == 3
        assert "quality_score" in quality
        assert 0 <= quality["quality_score"] <= 1


# =============================================================================
# Searcher Tests
# =============================================================================


class TestResearchSearcher:
    """Tests for multi-source search."""

    def test_deduplicate_results(self):
        """Test result deduplication."""
        results = [
            {"text": "same content here", "score": 0.9},
            {"text": "same content here", "score": 0.8},  # Duplicate
            {"text": "different content", "score": 0.7},
        ]

        unique = deduplicate_results(results)

        assert len(unique) == 2
        # Should keep first occurrence
        assert unique[0]["score"] == 0.9

    def test_rank_results(self):
        """Test result ranking."""
        results = [
            {"text": "result 1", "score": 0.5, "source": "vector"},
            {"text": "result 2", "score": 0.8, "source": "graph"},
            {"text": "result 3", "score": 0.6, "source": "vector"},
        ]

        ranked = rank_results(results, "test query")

        # Graph results with high score should rank first
        assert ranked[0]["source"] == "graph"

    @pytest.mark.asyncio
    async def test_evaluate_results_sufficient(self):
        """Test result evaluation for sufficient results."""
        results = [{"text": f"result {i}", "score": 0.8, "source": "vector"} for i in range(10)]

        metrics = await evaluate_results(results, "test query")

        assert metrics["num_results"] == 10
        assert metrics["sufficient"] is True

    @pytest.mark.asyncio
    async def test_evaluate_results_insufficient(self):
        """Test result evaluation for insufficient results."""
        results = [
            {"text": "result 1", "score": 0.3, "source": "vector"},
        ]

        metrics = await evaluate_results(results, "test query")

        assert metrics["sufficient"] is False

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires vector/graph search modules")
    async def test_execute_searches_with_mocks(self):
        """Test search execution with mocked components."""
        with (
            patch("src.components.vector_search.hybrid.search_hybrid") as mock_vector,
            patch("src.components.graph_rag.query.query_graph") as mock_graph,
        ):

            mock_vector.return_value = [{"text": "vector result", "score": 0.9}]
            mock_graph.return_value = [{"text": "graph result", "score": 0.8}]

            results = await execute_searches(["test query"], top_k=5)

            # Should have results from both sources
            assert len(results) >= 1


# =============================================================================
# Synthesizer Tests
# =============================================================================


class TestResearchSynthesizer:
    """Tests for result synthesis."""

    def test_format_results_for_synthesis(self):
        """Test formatting results for context."""
        results = [
            {"text": "First result content", "score": 0.9, "source": "vector"},
            {"text": "Second result content", "score": 0.8, "source": "graph"},
        ]

        formatted = format_results_for_synthesis(results, max_length=1000)

        assert "First result" in formatted
        assert "Second result" in formatted
        assert "vector" in formatted.lower()
        assert "graph" in formatted.lower()

    def test_format_results_truncation(self):
        """Test that long results are truncated."""
        long_text = "x" * 5000
        results = [{"text": long_text, "score": 0.9, "source": "vector"}]

        formatted = format_results_for_synthesis(results, max_length=1000)

        assert len(formatted) <= 1000

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM proxy module")
    async def test_synthesize_findings_with_llm(self):
        """Test synthesis with LLM."""
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "This is a synthesized answer based on research."

        with patch(
            "src.domains.llm_integration.proxy.aegis_proxy.get_aegis_llm_proxy"
        ) as mock_get_llm:
            mock_get_llm.return_value = mock_llm

            results = [
                {"text": "Result 1", "score": 0.9, "source": "vector"},
                {"text": "Result 2", "score": 0.8, "source": "graph"},
            ]

            synthesis = await synthesize_findings("What is AI?", results)

            assert len(synthesis) > 0
            mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM proxy module")
    async def test_synthesize_findings_fallback(self):
        """Test synthesis fallback when LLM fails."""
        with patch(
            "src.domains.llm_integration.proxy.aegis_proxy.get_aegis_llm_proxy"
        ) as mock_get_llm:
            mock_get_llm.side_effect = Exception("LLM error")

            results = [
                {"text": "Result 1", "score": 0.9, "source": "vector"},
            ]

            synthesis = await synthesize_findings("What is AI?", results)

            # Should use fallback synthesis
            assert "Result 1" in synthesis

    def test_extract_key_points(self):
        """Test key point extraction."""
        text = """
First, machine learning is a subset of AI.
Second, it involves training models on data.
Third, applications include image recognition.
"""
        points = extract_key_points(text, max_points=3)

        assert len(points) <= 3
        assert any("first" in p.lower() for p in points)


# =============================================================================
# Graph Tests
# =============================================================================


class TestResearchGraph:
    """Tests for LangGraph research workflow."""

    def test_create_research_graph(self):
        """Test graph creation."""
        graph = create_research_graph()

        assert graph is not None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM proxy and search modules")
    async def test_run_research_workflow(self):
        """Test full research workflow (mocked)."""
        # Mock all external dependencies
        with (
            patch("src.domains.llm_integration.proxy.aegis_proxy.get_aegis_llm_proxy") as mock_llm,
            patch("src.components.vector_search.hybrid.search_hybrid") as mock_vector,
            patch("src.components.graph_rag.query.query_graph") as mock_graph,
        ):

            # Setup mocks
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate.return_value = "1. Test query"
            mock_llm.return_value = mock_llm_instance

            mock_vector.return_value = [{"text": "Result", "score": 0.9}]
            mock_graph.return_value = []

            # Run research
            result = await run_research("What is AI?", max_iterations=1)

            # Should have completed workflow
            assert "synthesis" in result
            assert "search_results" in result
