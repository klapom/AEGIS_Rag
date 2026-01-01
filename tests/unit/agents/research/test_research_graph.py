"""Unit tests for research graph.

Sprint 70 Feature 70.4: Test research supervisor graph.
"""

import pytest

from src.agents.research.research_graph import (
    create_initial_research_state,
    create_research_graph,
    get_research_graph,
    should_continue_research,
)


class TestCreateInitialResearchState:
    """Test initial state creation."""

    def test_create_state_defaults(self):
        """Test state creation with defaults."""
        state = create_initial_research_state(query="What is AI?")

        assert state["original_query"] == "What is AI?"
        assert state["sub_queries"] == []
        assert state["iteration"] == 0
        assert state["max_iterations"] == 3
        assert state["all_contexts"] == []
        assert state["synthesis"] == ""
        assert state["should_continue"] is True
        assert state["metadata"]["namespace"] == "default"
        assert state["error"] is None

    def test_create_state_custom(self):
        """Test state creation with custom values."""
        state = create_initial_research_state(
            query="What is ML?",
            max_iterations=5,
            namespace="ml_docs",
        )

        assert state["original_query"] == "What is ML?"
        assert state["max_iterations"] == 5
        assert state["metadata"]["namespace"] == "ml_docs"


class TestShouldContinueResearch:
    """Test supervisor decision function."""

    def test_should_continue_true(self):
        """Test that research continues when flag is True."""
        state = {"should_continue": True}

        decision = should_continue_research(state)

        assert decision == "continue"

    def test_should_continue_false(self):
        """Test that research synthesizes when flag is False."""
        state = {"should_continue": False}

        decision = should_continue_research(state)

        assert decision == "synthesize"

    def test_should_continue_default(self):
        """Test default behavior when flag is missing."""
        state = {}

        decision = should_continue_research(state)

        assert decision == "synthesize"  # False by default


class TestCreateResearchGraph:
    """Test research graph creation."""

    def test_create_graph(self):
        """Test that graph is created successfully."""
        graph = create_research_graph()

        assert graph is not None
        # Verify graph is compiled (has invoke method)
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "astream")

    def test_get_research_graph_singleton(self):
        """Test that get_research_graph returns singleton."""
        graph1 = get_research_graph()
        graph2 = get_research_graph()

        # Should be same instance
        assert graph1 is graph2


class TestGraphNodes:
    """Test individual graph nodes."""

    @pytest.mark.asyncio
    async def test_planner_node(self, mocker):
        """Test planner node execution."""
        from src.agents.research.research_graph import planner_node

        # Mock plan_research at source module
        mock_plan_research = mocker.patch(
            "src.agents.research.planner.plan_research",
            return_value=["Query 1", "Query 2", "Query 3"],
        )

        state = {
            "original_query": "What is AI?",
            "max_iterations": 3,
        }

        result = await planner_node(state)

        assert "sub_queries" in result
        assert result["iteration"] == 0
        assert len(result["sub_queries"]) == 3

        # Verify plan_research was called
        mock_plan_research.assert_called_once()

    @pytest.mark.asyncio
    async def test_searcher_node(self, mocker):
        """Test searcher node execution."""
        from src.agents.research.research_graph import searcher_node

        # Mock execute_research_queries at source module
        mock_execute = mocker.patch(
            "src.agents.research.searcher.execute_research_queries",
            return_value=[
                {"text": "Context 1", "score": 0.9},
                {"text": "Context 2", "score": 0.8},
            ],
        )

        state = {
            "sub_queries": ["Query 1", "Query 2"],
            "iteration": 0,
            "all_contexts": [],
            "metadata": {"namespace": "default"},
        }

        result = await searcher_node(state)

        assert "all_contexts" in result
        assert "iteration" in result
        assert result["iteration"] == 1

        # Verify execute_research_queries was called
        mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_supervisor_node_continue(self, mocker):
        """Test supervisor decides to continue."""
        from src.agents.research.research_graph import supervisor_node

        # Mock evaluate_search_quality at source module
        mock_evaluate = mocker.patch(
            "src.agents.research.searcher.evaluate_search_quality",
            return_value={
                "num_results": 3,
                "quality": "fair",
                "sufficient": False,
            },
        )

        state = {
            "iteration": 1,
            "max_iterations": 3,
            "all_contexts": [
                {"text": "Context 1", "score": 0.5},
                {"text": "Context 2", "score": 0.4},
                {"text": "Context 3", "score": 0.3},
            ],
        }

        result = await supervisor_node(state)

        assert result["should_continue"] is True

        # Verify evaluate_search_quality was called
        mock_evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_supervisor_node_synthesize(self, mocker):
        """Test supervisor decides to synthesize."""
        from src.agents.research.research_graph import supervisor_node

        # Mock evaluate_search_quality at source module
        mock_evaluate = mocker.patch(
            "src.agents.research.searcher.evaluate_search_quality",
            return_value={
                "num_results": 10,
                "quality": "excellent",
                "sufficient": True,
            },
        )

        state = {
            "iteration": 1,
            "max_iterations": 3,
            "all_contexts": [{"text": f"Context {i}", "score": 0.8} for i in range(10)],
        }

        result = await supervisor_node(state)

        assert result["should_continue"] is False

        # Verify evaluate_search_quality was called
        mock_evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_supervisor_node_max_iterations(self, mocker):
        """Test supervisor stops at max iterations."""
        from src.agents.research.research_graph import supervisor_node

        state = {
            "iteration": 3,
            "max_iterations": 3,
            "all_contexts": [],
        }

        result = await supervisor_node(state)

        # Should stop due to max iterations
        assert result["should_continue"] is False

    @pytest.mark.asyncio
    async def test_synthesizer_node(self, mocker):
        """Test synthesizer node execution."""
        from src.agents.research.research_graph import synthesizer_node

        # Mock synthesize_research_findings at source module
        mock_synthesize = mocker.patch(
            "src.agents.research.synthesizer.synthesize_research_findings",
            return_value={
                "answer": "Synthesized answer",
                "sources": [{"index": 1}],
                "metadata": {"num_contexts": 5},
            },
        )

        state = {
            "original_query": "What is AI?",
            "all_contexts": [{"text": "Context", "score": 0.9}],
            "metadata": {"namespace": "default"},
        }

        result = await synthesizer_node(state)

        assert "synthesis" in result
        assert "metadata" in result

        # Verify synthesize_research_findings was called
        mock_synthesize.assert_called_once()
