"""Unit tests for research planner.

Sprint 62 Feature 62.10: Research Endpoint Backend
"""

import pytest

from src.agents.research.planner import (
    evaluate_plan_quality,
    parse_plan,
    plan_research,
    refine_query,
)


class TestParsePlan:
    """Test plan parsing functionality."""

    def test_parse_numbered_list(self):
        """Test parsing numbered list format."""
        plan_text = """1. Search for machine learning basics
2. Find deep learning tutorials
3. Look for AI applications"""

        queries = parse_plan(plan_text)

        assert len(queries) == 3
        assert "machine learning basics" in queries[0]
        assert "deep learning tutorials" in queries[1]
        assert "AI applications" in queries[2]

    def test_parse_bullet_list(self):
        """Test parsing bullet list format."""
        plan_text = """- Search for ML
* Find DL
• Look for AI"""

        queries = parse_plan(plan_text)

        assert len(queries) == 3
        assert "ML" in queries[0]
        assert "DL" in queries[1]
        assert "AI" in queries[2]

    def test_parse_plain_lines(self):
        """Test parsing plain lines without markers."""
        plan_text = """Search for machine learning
Find deep learning
Look for AI applications"""

        queries = parse_plan(plan_text)

        assert len(queries) == 3
        assert "machine learning" in queries[0]

    def test_parse_empty_input(self):
        """Test parsing empty input."""
        queries = parse_plan("")

        assert queries == []

    def test_parse_mixed_format(self):
        """Test parsing mixed formats (numbered takes precedence)."""
        plan_text = """1. First query
2. Second query
- Third query (bullet)"""

        queries = parse_plan(plan_text)

        # Numbered format takes precedence
        assert len(queries) == 2
        assert "First query" in queries[0]
        assert "Second query" in queries[1]


@pytest.mark.asyncio
class TestPlanResearch:
    """Test research planning functionality."""

    async def test_plan_research_basic(self):
        """Test basic research planning."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value="""1. Search for AI fundamentals
2. Find machine learning concepts
3. Look for deep learning architectures"""
        )

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            queries = await plan_research("What is AI?", max_queries=5)

            assert len(queries) == 3
            assert "AI fundamentals" in queries[0]
            mock_llm.generate.assert_called_once()

    async def test_plan_research_respects_max_queries(self):
        """Test that max_queries limit is respected."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value="""1. Query 1
2. Query 2
3. Query 3
4. Query 4
5. Query 5
6. Query 6"""
        )

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            queries = await plan_research("Test query", max_queries=3)

            assert len(queries) == 3

    async def test_plan_research_fallback_on_error(self):
        """Test fallback to original query on error."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM failed")

        with patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        ):
            queries = await plan_research("Test query")

            # Fallback to original query
            assert queries == ["Test query"]


class TestRefineQuery:
    """Test query refinement functionality."""

    def test_refine_query_no_results(self):
        """Test refinement with no previous results."""
        refined = refine_query("What is AI?", [])

        assert refined == "What is AI?"

    def test_refine_query_with_short_results(self):
        """Test refinement with short previous results."""
        results = [{"text": "AI is artificial intelligence."}]

        refined = refine_query("What is AI?", results)

        assert "related concepts" in refined or "background" in refined

    def test_refine_query_with_long_results(self):
        """Test refinement with substantial previous results."""
        results = [{"text": "A" * 200} for _ in range(3)]

        refined = refine_query("What is AI?", results)

        assert "more specific details" in refined or "more details" in refined


@pytest.mark.asyncio
class TestEvaluatePlanQuality:
    """Test plan quality evaluation."""

    async def test_evaluate_plan_quality_good(self):
        """Test evaluation of good quality plan."""
        plan = ["Query 1", "Query 2", "Query 3"]

        metrics = await evaluate_plan_quality("Test query", plan)

        assert metrics["num_queries"] == 3
        assert metrics["coverage_score"] == 1.0  # 3 queries = full coverage
        assert metrics["diversity_score"] == 1.0  # All unique
        assert 0 <= metrics["quality_score"] <= 1.0

    async def test_evaluate_plan_quality_too_few(self):
        """Test evaluation of plan with too few queries."""
        plan = ["Query 1"]

        metrics = await evaluate_plan_quality("Test query", plan)

        assert metrics["num_queries"] == 1
        assert metrics["coverage_score"] < 1.0  # Less than ideal
        assert metrics["diversity_score"] == 1.0

    async def test_evaluate_plan_quality_duplicates(self):
        """Test evaluation of plan with duplicates."""
        plan = ["Query 1", "Query 1", "Query 2"]

        metrics = await evaluate_plan_quality("Test query", plan)

        assert metrics["num_queries"] == 3
        assert metrics["diversity_score"] < 1.0  # Has duplicates

    async def test_evaluate_plan_quality_empty(self):
        """Test evaluation of empty plan."""
        plan = []

        metrics = await evaluate_plan_quality("Test query", plan)

        assert metrics["num_queries"] == 0
        assert metrics["coverage_score"] == 0.0
