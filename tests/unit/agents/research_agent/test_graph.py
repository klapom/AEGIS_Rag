"""Unit tests for research agent graph.

Sprint 62 Feature 62.10: Research Endpoint Backend
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.research.graph import (
    create_research_graph,
    evaluate_node,
    plan_node,
    run_research,
    search_node,
    should_continue_searching,
    synthesize_node,
)


@pytest.fixture
def base_state():
    """Base research state for testing."""
    return {
        "query": "What is machine learning?",
        "namespace": "test_ns",
        "research_plan": [],
        "search_results": [],
        "synthesis": "",
        "iteration": 0,
        "max_iterations": 3,
        "quality_metrics": {},
        "should_continue": True,
    }


@pytest.mark.asyncio
class TestPlanNode:
    """Test planning node."""

    async def test_plan_node_creates_plan(self, base_state):
        """Test that plan node creates research plan."""
        with (
            patch("src.agents.research.graph.plan_research") as mock_plan,
            patch("src.agents.research.graph.evaluate_plan_quality") as mock_eval,
        ):
            mock_plan.return_value = ["Query 1", "Query 2", "Query 3"]
            mock_eval.return_value = {"quality_score": 0.8}

            updated_state = await plan_node(base_state)

            assert len(updated_state["research_plan"]) == 3
            assert "quality_metrics" in updated_state
            mock_plan.assert_called_once()
            mock_eval.assert_called_once()

    async def test_plan_node_preserves_other_fields(self, base_state):
        """Test that plan node preserves other state fields."""
        with (
            patch("src.agents.research.graph.plan_research") as mock_plan,
            patch("src.agents.research.graph.evaluate_plan_quality") as mock_eval,
        ):
            mock_plan.return_value = ["Query 1"]
            mock_eval.return_value = {}

            updated_state = await plan_node(base_state)

            assert updated_state["query"] == base_state["query"]
            assert updated_state["namespace"] == base_state["namespace"]
            assert updated_state["max_iterations"] == base_state["max_iterations"]


@pytest.mark.asyncio
class TestSearchNode:
    """Test search node."""

    async def test_search_node_executes_searches(self, base_state):
        """Test that search node executes searches."""
        base_state["research_plan"] = ["Query 1", "Query 2"]

        with patch("src.agents.research.graph.execute_searches") as mock_search:
            mock_search.return_value = [
                {"text": "Result 1", "score": 0.9},
                {"text": "Result 2", "score": 0.8},
            ]

            updated_state = await search_node(base_state)

            assert len(updated_state["search_results"]) == 2
            mock_search.assert_called_once()

            # Verify namespace was passed
            call_args = mock_search.call_args
            assert call_args.kwargs.get("namespace") == "test_ns"

    async def test_search_node_uses_correct_parameters(self, base_state):
        """Test that search node uses correct parameters."""
        base_state["research_plan"] = ["Query 1"]

        with patch("src.agents.research.graph.execute_searches") as mock_search:
            mock_search.return_value = []

            await search_node(base_state)

            # Verify parameters
            call_args = mock_search.call_args
            assert call_args.kwargs.get("top_k") == 5
            assert call_args.kwargs.get("use_graph") is True
            assert call_args.kwargs.get("use_vector") is True


@pytest.mark.asyncio
class TestEvaluateNode:
    """Test evaluation node."""

    async def test_evaluate_node_increments_iteration(self, base_state):
        """Test that evaluate node increments iteration."""
        base_state["search_results"] = [{"text": "Result", "score": 0.9}]

        with patch("src.agents.research.graph.evaluate_results") as mock_eval:
            mock_eval.return_value = {"sufficient": False}

            updated_state = await evaluate_node(base_state)

            assert updated_state["iteration"] == 1

    async def test_evaluate_node_stops_when_sufficient(self, base_state):
        """Test that evaluation stops when results are sufficient."""
        base_state["search_results"] = [{"text": "Result", "score": 0.9}]

        with patch("src.agents.research.graph.evaluate_results") as mock_eval:
            mock_eval.return_value = {"sufficient": True}

            updated_state = await evaluate_node(base_state)

            assert updated_state["should_continue"] is False

    async def test_evaluate_node_stops_at_max_iterations(self, base_state):
        """Test that evaluation stops at max iterations."""
        base_state["iteration"] = 2  # Will be incremented to 3
        base_state["max_iterations"] = 3
        base_state["search_results"] = [{"text": "Result", "score": 0.5}]

        with patch("src.agents.research.graph.evaluate_results") as mock_eval:
            mock_eval.return_value = {"sufficient": False}

            updated_state = await evaluate_node(base_state)

            assert updated_state["iteration"] == 3
            assert updated_state["should_continue"] is False

    async def test_evaluate_node_continues_when_insufficient(self, base_state):
        """Test that evaluation continues when results are insufficient."""
        base_state["iteration"] = 0
        base_state["search_results"] = [{"text": "Result", "score": 0.3}]

        with patch("src.agents.research.graph.evaluate_results") as mock_eval:
            mock_eval.return_value = {"sufficient": False}

            updated_state = await evaluate_node(base_state)

            assert updated_state["should_continue"] is True


@pytest.mark.asyncio
class TestSynthesizeNode:
    """Test synthesis node."""

    async def test_synthesize_node_creates_synthesis(self, base_state):
        """Test that synthesize node creates synthesis."""
        base_state["search_results"] = [
            {"text": "ML is AI", "score": 0.9},
            {"text": "ML learns from data", "score": 0.8},
        ]

        with patch("src.agents.research.graph.synthesize_findings") as mock_synth:
            mock_synth.return_value = "Machine learning is a subset of AI that learns from data."

            updated_state = await synthesize_node(base_state)

            assert len(updated_state["synthesis"]) > 0
            assert "Machine learning" in updated_state["synthesis"]
            mock_synth.assert_called_once()


class TestShouldContinueSearching:
    """Test conditional edge logic."""

    def test_should_continue_when_flag_true(self, base_state):
        """Test continuation when flag is True."""
        base_state["should_continue"] = True

        result = should_continue_searching(base_state)

        assert result == "search"

    def test_should_stop_when_flag_false(self, base_state):
        """Test stopping when flag is False."""
        base_state["should_continue"] = False

        result = should_continue_searching(base_state)

        assert result == "synthesize"


class TestCreateResearchGraph:
    """Test graph creation."""

    def test_create_research_graph(self):
        """Test that graph is created successfully."""
        graph = create_research_graph()

        assert graph is not None

        # Verify graph structure by checking compiled graph
        # The graph should have nodes and edges
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")


@pytest.mark.asyncio
class TestRunResearch:
    """Test end-to-end research workflow."""

    async def test_run_research_basic(self):
        """Test basic research workflow."""
        with patch("src.agents.research.graph.create_research_graph") as mock_create:
            # Mock graph execution
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {
                "query": "What is AI?",
                "namespace": "default",
                "research_plan": ["Query 1", "Query 2"],
                "search_results": [{"text": "Result", "score": 0.9}],
                "synthesis": "AI is artificial intelligence.",
                "iteration": 2,
                "max_iterations": 3,
                "quality_metrics": {"sufficient": True},
                "should_continue": False,
            }
            mock_create.return_value = mock_graph

            result = await run_research("What is AI?", max_iterations=3, namespace="test_ns")

            assert result["synthesis"] == "AI is artificial intelligence."
            assert result["iteration"] == 2
            mock_graph.ainvoke.assert_called_once()

    async def test_run_research_with_custom_namespace(self):
        """Test research with custom namespace."""
        with patch("src.agents.research.graph.create_research_graph") as mock_create:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {
                "query": "Test",
                "namespace": "custom_ns",
                "research_plan": [],
                "search_results": [],
                "synthesis": "Result",
                "iteration": 1,
                "max_iterations": 3,
                "quality_metrics": {},
                "should_continue": False,
            }
            mock_create.return_value = mock_graph

            await run_research("Test", namespace="custom_ns")

            # Verify initial state had correct namespace
            call_args = mock_graph.ainvoke.call_args
            initial_state = call_args[0][0]
            assert initial_state["namespace"] == "custom_ns"

    async def test_run_research_respects_max_iterations(self):
        """Test that max_iterations is respected."""
        with patch("src.agents.research.graph.create_research_graph") as mock_create:
            mock_graph = AsyncMock()
            mock_graph.ainvoke.return_value = {
                "query": "Test",
                "namespace": "default",
                "research_plan": [],
                "search_results": [],
                "synthesis": "Result",
                "iteration": 1,
                "max_iterations": 2,
                "quality_metrics": {},
                "should_continue": False,
            }
            mock_create.return_value = mock_graph

            await run_research("Test", max_iterations=2)

            # Verify initial state had correct max_iterations
            call_args = mock_graph.ainvoke.call_args
            initial_state = call_args[0][0]
            assert initial_state["max_iterations"] == 2
