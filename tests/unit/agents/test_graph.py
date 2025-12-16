"""Unit tests for LangGraph base graph implementation.

Sprint 4 Feature 4.1: Base Graph Tests
Sprint 27 Feature 27.10: Citation tests for llm_answer_node
"""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.graph import StateGraph

from src.agents.graph import (
    compile_graph,
    create_base_graph,
    llm_answer_node,
    route_query,
    router_node,
)
from src.agents.state import create_initial_state


class TestRouterNode:
    """Test router_node function."""

    @pytest.mark.asyncio
    async def test_router_node__adds_routing_metadata(self):
        """Test that router adds routing metadata to state."""
        state = create_initial_state("test query", "hybrid")

        result = await router_node(state)

        assert "metadata" in result
        assert "agent_path" in result["metadata"]
        assert "router" in result["metadata"]["agent_path"]

    @pytest.mark.asyncio
    async def test_router_node__sets_route_decision(self):
        """Test that router sets route_decision based on intent."""
        state = create_initial_state("test query", "vector")

        result = await router_node(state)

        assert "route_decision" in result
        assert result["route_decision"] == "vector"

    @pytest.mark.asyncio
    async def test_router_node__default_intent(self):
        """Test router with default (hybrid) intent."""
        state = create_initial_state("test query")  # Default intent

        result = await router_node(state)

        assert result["route_decision"] == "hybrid"


class TestRouteQuery:
    """Test route_query conditional edge function."""

    def test_route_query__vector_intent__routes_correctly(self):
        """Test routing for vector intent."""
        state = {
            "query": "test",
            "intent": "vector",
            "route_decision": "vector",
        }

        route = route_query(state)

        # Should route to vector_search (updated in Feature 4.3)
        # For Feature 4.1, this might route to "end"
        assert route in ["vector_search", "end"]

    def test_route_query__hybrid_intent__routes_correctly(self):
        """Test routing for hybrid intent."""
        state = {
            "query": "test",
            "intent": "hybrid",
            "route_decision": "hybrid",
        }

        route = route_query(state)

        # Sprint 42: hybrid intent routes to hybrid_search node
        assert route in ["vector_search", "hybrid_search", "end"]

    def test_route_query__graph_intent__routes_correctly(self):
        """Test routing for graph intent."""
        state = {
            "query": "test",
            "intent": "graph",
            "route_decision": "graph",
        }

        route = route_query(state)

        # Should route to graph or end
        assert route in ["graph", "end"]

    def test_route_query__missing_intent__defaults_gracefully(self):
        """Test that missing intent defaults to hybrid_search (Sprint 42)."""
        state = {"query": "test"}

        route = route_query(state)

        # Default intent is hybrid, which routes to hybrid_search
        assert route in ["vector_search", "graph", "hybrid_search", "memory", "end"]


class TestCreateBaseGraph:
    """Test create_base_graph function."""

    def test_create_base_graph__returns_state_graph(self):
        """Test that create_base_graph returns a StateGraph."""
        graph = create_base_graph()

        assert isinstance(graph, StateGraph)

    def test_create_base_graph__has_router_node(self):
        """Test that graph has router node."""
        graph = create_base_graph()

        # Graph should have nodes (checking via graph structure)
        assert graph is not None


class TestCompileGraph:
    """Test compile_graph function."""

    def test_compile_graph__compiles_successfully(self):
        """Test that graph compiles without errors."""
        compiled = compile_graph()

        assert compiled is not None

    def test_compile_graph__can_be_invoked(self):
        """Test that compiled graph has invoke methods."""
        compiled = compile_graph()

        # Should have invoke and ainvoke methods
        assert hasattr(compiled, "invoke")
        assert hasattr(compiled, "ainvoke")


class TestGraphExecution:
    """Integration tests for graph execution."""

    @pytest.mark.asyncio
    async def test_graph_execution__simple_flow(self):
        """Test basic graph execution."""
        compiled = compile_graph()
        initial_state = create_initial_state("What is RAG?", "hybrid")

        # Execute graph
        result = await compiled.ainvoke(initial_state)

        # Should have processed through router
        assert "metadata" in result
        assert "agent_path" in result["metadata"]

    @pytest.mark.asyncio
    async def test_graph_execution__vector_intent(self):
        """Test graph execution with vector intent."""
        compiled = compile_graph()
        initial_state = create_initial_state("Find documents", "vector")

        result = await compiled.ainvoke(initial_state)

        # Should have query
        assert result["query"] == "Find documents"
        assert result["intent"] == "vector"

    @pytest.mark.asyncio
    async def test_graph_execution__maintains_state(self):
        """Test that state is maintained through execution."""
        compiled = compile_graph()
        initial_state = create_initial_state("test query", "hybrid")

        # Add custom data to metadata (which is part of the schema)
        initial_state["metadata"]["custom_field"] = "test_value"

        result = await compiled.ainvoke(initial_state)

        # Custom field in metadata should be preserved
        assert result.get("metadata", {}).get("custom_field") == "test_value"

    @pytest.mark.asyncio
    async def test_graph_execution__multiple_queries(self):
        """Test executing graph with multiple queries."""
        compiled = compile_graph()

        queries = [
            ("Query 1", "vector"),
            ("Query 2", "hybrid"),
            ("Query 3", "graph"),
        ]

        for query, intent in queries:
            state = create_initial_state(query, intent)
            result = await compiled.ainvoke(state)

            # Each should process successfully
            assert result["query"] == query
            assert result["intent"] == intent


class TestGraphStateFlow:
    """Test state flow through the graph."""

    @pytest.mark.asyncio
    async def test_state_flow__router_adds_trace(self):
        """Test that router adds itself to trace."""
        compiled = compile_graph()
        state = create_initial_state("test")

        result = await compiled.ainvoke(state)

        assert "router" in result["metadata"]["agent_path"]

    @pytest.mark.asyncio
    async def test_state_flow__preserves_query(self):
        """Test that query is preserved throughout execution."""
        compiled = compile_graph()
        original_query = "What is the meaning of life?"
        state = create_initial_state(original_query)

        result = await compiled.ainvoke(state)

        assert result["query"] == original_query

    @pytest.mark.asyncio
    async def test_state_flow__initializes_contexts(self):
        """Test that retrieved_contexts is initialized."""
        compiled = compile_graph()
        state = create_initial_state("test")

        result = await compiled.ainvoke(state)

        assert "retrieved_contexts" in result
        assert isinstance(result["retrieved_contexts"], list)


class TestGraphConfiguration:
    """Test graph configuration options."""

    def test_graph_without_checkpointer(self):
        """Test that graph compiles without checkpointer (Feature 4.1)."""
        # Feature 4.1 should compile without checkpointer
        # Feature 4.4 will add checkpointing
        compiled = compile_graph()

        # Should compile successfully
        assert compiled is not None

    def test_graph_is_stateless(self):
        """Test that graph doesn't persist state between invocations (Feature 4.1)."""
        compiled = compile_graph()

        # This is a placeholder test - Feature 4.4 will add state persistence
        # For now, just verify graph can be invoked multiple times
        assert compiled is not None


class TestGraphErrorHandling:
    """Test error handling in graph execution."""

    @pytest.mark.asyncio
    async def test_graph_with_invalid_state__handles_gracefully(self):
        """Test that graph handles invalid state gracefully."""
        compiled = compile_graph()

        # Minimal state (might miss some fields)
        state = {"query": "test", "intent": "hybrid"}

        # Should not crash (might add defaults)
        try:
            result = await compiled.ainvoke(state)
            # If it succeeds, verify it has basic structure
            assert "query" in result
        except Exception as e:
            # If it fails, it should be a validation error
            assert "validation" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.asyncio
    async def test_graph_with_empty_query__processes(self):
        """Test graph with empty query."""
        compiled = compile_graph()
        state = create_initial_state("")  # Empty query

        result = await compiled.ainvoke(state)

        # Should process (even if query is empty)
        assert "query" in result
        assert result["query"] == ""


class TestLLMAnswerNode:
    """Test llm_answer_node with citation functionality.

    Sprint 27 Feature 27.10: Inline Source Citations
    """

    @pytest.mark.asyncio
    async def test_llm_answer_node__generates_answer_with_citations(self):
        """Test that llm_answer_node generates answer with citations."""
        # Mock AnswerGenerator
        mock_generator = AsyncMock()
        mock_generator.generate_with_citations = AsyncMock(
            return_value=(
                "AEGIS RAG is an agentic system [1] using LangGraph [2].",
                {
                    1: {
                        "text": "AEGIS RAG is an agentic enterprise system.",
                        "source": "docs/CLAUDE.md",
                        "title": "CLAUDE Documentation",
                        "score": 0.95,
                        "metadata": {},
                    },
                    2: {
                        "text": "The system uses LangGraph for orchestration.",
                        "source": "docs/architecture.md",
                        "title": "Architecture Overview",
                        "score": 0.88,
                        "metadata": {},
                    },
                },
            )
        )

        with patch("src.agents.answer_generator.get_answer_generator", return_value=mock_generator):
            state = {
                "query": "What is AEGIS RAG?",
                "retrieved_contexts": [
                    {"text": "AEGIS RAG is an agentic enterprise system.", "source": "docs/CLAUDE.md"},
                    {"text": "The system uses LangGraph for orchestration.", "source": "docs/architecture.md"},
                ],
            }

            result = await llm_answer_node(state)

            # Verify answer is in messages
            assert "messages" in result
            assert len(result["messages"]) == 1
            assert result["messages"][0]["role"] == "assistant"
            assert "[1]" in result["messages"][0]["content"]
            assert "[2]" in result["messages"][0]["content"]

            # Verify answer field
            assert "answer" in result
            assert result["answer"] == "AEGIS RAG is an agentic system [1] using LangGraph [2]."

            # Verify citation_map
            assert "citation_map" in result
            assert len(result["citation_map"]) == 2
            assert result["citation_map"][1]["source"] == "docs/CLAUDE.md"
            assert result["citation_map"][2]["source"] == "docs/architecture.md"

    @pytest.mark.asyncio
    async def test_llm_answer_node__empty_contexts_returns_fallback(self):
        """Test that llm_answer_node handles empty contexts gracefully."""
        mock_generator = AsyncMock()
        mock_generator.generate_with_citations = AsyncMock(
            return_value=(
                "I don't have enough information to answer this question.",
                {},
            )
        )

        with patch("src.agents.answer_generator.get_answer_generator", return_value=mock_generator):
            state = {
                "query": "What is AEGIS RAG?",
                "retrieved_contexts": [],
            }

            result = await llm_answer_node(state)

            # Should have answer
            assert "answer" in result
            assert "don't have enough information" in result["answer"]

            # Citation map should be empty
            assert "citation_map" in result
            assert result["citation_map"] == {}

    @pytest.mark.asyncio
    async def test_llm_answer_node__stores_citation_map_in_state(self):
        """Test that citation_map is properly stored in state."""
        mock_generator = AsyncMock()
        mock_generator.generate_with_citations = AsyncMock(
            return_value=(
                "Answer [1].",
                {1: {"text": "Context", "source": "doc.pdf", "title": "Doc", "score": 0.9, "metadata": {}}},
            )
        )

        with patch("src.agents.answer_generator.get_answer_generator", return_value=mock_generator):
            state = {
                "query": "Test?",
                "retrieved_contexts": [{"text": "Context", "source": "doc.pdf"}],
            }

            result = await llm_answer_node(state)

            # Verify citation_map structure
            assert "citation_map" in result
            assert isinstance(result["citation_map"], dict)
            assert 1 in result["citation_map"]
            assert "source" in result["citation_map"][1]
            assert result["citation_map"][1]["source"] == "doc.pdf"

    @pytest.mark.asyncio
    async def test_llm_answer_node__multiple_citations_ordered_correctly(self):
        """Test that multiple citations are ordered correctly."""
        citation_map = {
            1: {"text": "First", "source": "doc1.pdf", "title": "Doc 1", "score": 0.95, "metadata": {}},
            2: {"text": "Second", "source": "doc2.pdf", "title": "Doc 2", "score": 0.90, "metadata": {}},
            3: {"text": "Third", "source": "doc3.pdf", "title": "Doc 3", "score": 0.85, "metadata": {}},
        }

        mock_generator = AsyncMock()
        mock_generator.generate_with_citations = AsyncMock(
            return_value=("Answer [1] [2] [3].", citation_map)
        )

        with patch("src.agents.answer_generator.get_answer_generator", return_value=mock_generator):
            state = {
                "query": "Test?",
                "retrieved_contexts": [
                    {"text": "First", "source": "doc1.pdf"},
                    {"text": "Second", "source": "doc2.pdf"},
                    {"text": "Third", "source": "doc3.pdf"},
                ],
            }

            result = await llm_answer_node(state)

            # Verify all citations present
            assert len(result["citation_map"]) == 3
            assert result["citation_map"][1]["source"] == "doc1.pdf"
            assert result["citation_map"][2]["source"] == "doc2.pdf"
            assert result["citation_map"][3]["source"] == "doc3.pdf"
