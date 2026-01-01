"""Unit tests for research planner.

Sprint 70 Feature 70.1: Test planner with LLMTask API fix.
"""

import pytest

from src.agents.research.planner import evaluate_plan_quality, parse_plan, plan_research


class TestParsePlan:
    """Test plan parsing from LLM output."""

    def test_parse_numbered_list(self):
        """Test parsing numbered list format."""
        plan_text = """1. First query about X
2. Second query about Y
3. Third query about Z"""

        queries = parse_plan(plan_text)

        assert len(queries) == 3
        assert queries[0] == "First query about X"
        assert queries[1] == "Second query about Y"
        assert queries[2] == "Third query about Z"

    def test_parse_bullet_list(self):
        """Test parsing bullet list format."""
        plan_text = """- First query
- Second query
- Third query"""

        queries = parse_plan(plan_text)

        assert len(queries) == 3
        assert queries[0] == "First query"

    def test_parse_empty_text(self):
        """Test parsing empty text."""
        queries = parse_plan("")
        assert len(queries) == 0

    def test_parse_mixed_format(self):
        """Test that numbered format takes precedence."""
        plan_text = """1. Numbered query
- Bullet query"""

        queries = parse_plan(plan_text)

        # Should only get numbered query
        assert len(queries) == 1
        assert queries[0] == "Numbered query"


class TestEvaluatePlanQuality:
    """Test plan quality evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_quality_good_plan(self):
        """Test evaluation of a good plan."""
        query = "What is AI?"
        plan = [
            "AI definition and history",
            "AI applications",
            "AI future trends",
        ]

        metrics = await evaluate_plan_quality(query, plan)

        assert metrics["num_queries"] == 3
        assert metrics["coverage_score"] == 1.0  # 3 queries = ideal
        assert metrics["diversity_score"] == 1.0  # All unique
        assert metrics["quality_score"] > 0.5

    @pytest.mark.asyncio
    async def test_evaluate_quality_too_few(self):
        """Test evaluation with too few queries."""
        query = "What is ML?"
        plan = ["ML definition"]

        metrics = await evaluate_plan_quality(query, plan)

        assert metrics["num_queries"] == 1
        assert metrics["coverage_score"] < 1.0  # Less than ideal
        assert metrics["quality_score"] < 1.0

    @pytest.mark.asyncio
    async def test_evaluate_quality_empty(self):
        """Test evaluation with empty plan."""
        query = "What is DL?"
        plan = []

        metrics = await evaluate_plan_quality(query, plan)

        assert metrics["num_queries"] == 0
        assert metrics["coverage_score"] == 0.0
        assert metrics["quality_score"] == 0.0


class TestPlanResearch:
    """Test research planning with LLM."""

    @pytest.mark.asyncio
    async def test_plan_research_success(self, mocker):
        """Test successful research planning."""
        # Mock LLM response
        mock_response = mocker.MagicMock()
        mock_response.content = """1. Query about architecture
2. Query about features
3. Query about integration"""

        mock_llm = mocker.MagicMock()
        mock_llm.generate = mocker.AsyncMock(return_value=mock_response)

        # Patch at the actual import location
        mock_get_llm = mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        )

        # Execute
        queries = await plan_research("What is OMNITRACKER?", max_queries=5)

        # Verify
        assert len(queries) == 3
        assert "architecture" in queries[0].lower()
        assert "features" in queries[1].lower()
        assert "integration" in queries[2].lower()

        # Verify LLM was called with LLMTask
        mock_llm.generate.assert_called_once()
        call_args = mock_llm.generate.call_args
        task = call_args[0][0]

        # Verify task structure
        assert hasattr(task, "task_type")
        assert hasattr(task, "prompt")
        assert hasattr(task, "temperature")
        assert task.temperature == 0.7

    @pytest.mark.asyncio
    async def test_plan_research_llm_error(self, mocker):
        """Test fallback when LLM fails."""
        # Mock LLM to raise error
        mock_llm = mocker.MagicMock()
        mock_llm.generate = mocker.AsyncMock(
            side_effect=Exception("LLM error")
        )

        mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        )

        # Execute
        query = "What is AI?"
        queries = await plan_research(query)

        # Should fallback to original query
        assert len(queries) == 1
        assert queries[0] == query

    @pytest.mark.asyncio
    async def test_plan_research_max_queries_limit(self, mocker):
        """Test that max_queries is respected."""
        # Mock LLM with many queries
        mock_response = mocker.MagicMock()
        mock_response.content = """1. Query 1
2. Query 2
3. Query 3
4. Query 4
5. Query 5
6. Query 6
7. Query 7"""

        mock_llm = mocker.MagicMock()
        mock_llm.generate = mocker.AsyncMock(return_value=mock_response)

        mocker.patch(
            "src.domains.llm_integration.proxy.aegis_llm_proxy.get_aegis_llm_proxy",
            return_value=mock_llm,
        )

        # Execute with max_queries=3
        queries = await plan_research("Test query", max_queries=3)

        # Should be limited to 3
        assert len(queries) == 3
        assert queries[0] == "Query 1"
        assert queries[2] == "Query 3"
