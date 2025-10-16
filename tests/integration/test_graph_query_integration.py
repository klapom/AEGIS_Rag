"""Integration tests for Graph Query Agent E2E flow.

Tests the complete flow: User Query → Router → GRAPH Intent → Graph Query Agent → Results

Sprint 5: Feature 5.5 - Graph Query Agent Integration Tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.graph import compile_graph, invoke_graph
from src.agents.graph_query_agent import GraphQueryAgent, graph_query_node
from src.agents.state import create_initial_state
from src.components.graph_rag.dual_level_search import (
    GraphSearchResult,
    SearchMode,
)


# ============================================================================
# Test E2E Graph Query Flow
# ============================================================================


class TestGraphQueryE2EFlow:
    """Test end-to-end graph query flow through LangGraph."""

    @pytest.fixture
    def mock_dual_level_search(self):
        """Mock DualLevelSearch for testing."""
        mock = MagicMock()
        mock.search = AsyncMock(
            return_value=GraphSearchResult(
                query="How are RAG and LLMs related?",
                mode=SearchMode.HYBRID,
                answer="RAG (Retrieval-Augmented Generation) enhances LLMs by providing external knowledge.",
                entities=[
                    {
                        "id": "rag_entity",
                        "name": "RAG",
                        "description": "Retrieval-Augmented Generation technique",
                    },
                    {
                        "id": "llm_entity",
                        "name": "LLM",
                        "description": "Large Language Model",
                    },
                ],
                relationships=[
                    {
                        "id": "rel_1",
                        "source": "RAG",
                        "target": "LLM",
                        "type": "ENHANCES",
                        "description": "RAG enhances LLMs with external knowledge",
                    }
                ],
                context="RAG enhances LLMs...",
                topics=["Machine Learning", "NLP"],
                metadata={"search_mode": "hybrid"},
            )
        )
        return mock

    @pytest.mark.asyncio
    async def test_graph_query_node_standalone(self, mock_dual_level_search):
        """Test graph_query_node function standalone."""
        # Create initial state with GRAPH intent
        state = create_initial_state(
            query="How are RAG and LLMs related?", intent="graph"
        )

        # Patch GraphQueryAgent to use mock
        with patch(
            "src.agents.graph_query_agent.get_dual_level_search",
            return_value=mock_dual_level_search,
        ):
            updated_state = await graph_query_node(state)

        # Verify state was updated correctly
        assert "graph_query_result" in updated_state
        assert updated_state["graph_query_result"]["query"] == "How are RAG and LLMs related?"
        assert (
            "RAG (Retrieval-Augmented Generation)"
            in updated_state["graph_query_result"]["answer"]
        )
        assert len(updated_state["graph_query_result"]["entities"]) == 2

        # Verify metadata
        assert "metadata" in updated_state
        assert "graph_search" in updated_state["metadata"]
        assert updated_state["metadata"]["graph_search"]["mode"] == "hybrid"

        # Verify contexts were added
        assert "retrieved_contexts" in updated_state
        assert len(updated_state["retrieved_contexts"]) == 2

    @pytest.mark.asyncio
    async def test_full_graph_execution(self, mock_dual_level_search):
        """Test full graph execution with GRAPH intent routing."""
        query = "How are RAG and LLMs related?"

        # Create initial state with GRAPH intent
        initial_state = create_initial_state(query=query, intent="graph")

        # Patch graph_query_node to use mock
        with patch(
            "src.agents.graph_query_agent.get_dual_level_search",
            return_value=mock_dual_level_search,
        ):
            # Compile and invoke graph
            compiled_graph = compile_graph(checkpointer=None)
            final_state = await compiled_graph.ainvoke(initial_state)

        # Verify routing worked
        assert "metadata" in final_state
        assert "agent_path" in final_state["metadata"]
        agent_path = final_state["metadata"]["agent_path"]

        # Should have router and graph_query_agent in path
        assert any("router" in str(step) for step in agent_path)
        assert any("graph_query" in str(step) for step in agent_path)

        # Verify graph query results
        assert "graph_query_result" in final_state
        assert final_state["graph_query_result"]["mode"] == "hybrid"

    @pytest.mark.asyncio
    async def test_invoke_graph_with_graph_intent(self, mock_dual_level_search):
        """Test invoke_graph convenience function with GRAPH intent."""
        query = "How are RAG and LLMs related?"

        # Patch dual level search
        with patch(
            "src.agents.graph_query_agent.get_dual_level_search",
            return_value=mock_dual_level_search,
        ):
            final_state = await invoke_graph(query=query, intent="graph")

        # Verify execution
        assert final_state["query"] == query
        assert final_state["intent"] == "graph"

        # Verify graph results present
        assert "graph_query_result" in final_state

    @pytest.mark.asyncio
    async def test_graph_query_with_local_mode(self, mock_dual_level_search):
        """Test graph query that classifies as LOCAL mode."""
        query = "Who is John Smith?"  # Should classify as LOCAL

        # Update mock to return local mode results
        mock_dual_level_search.search.return_value = GraphSearchResult(
            query=query,
            mode=SearchMode.LOCAL,
            answer="John Smith is a software engineer at Google.",
            entities=[
                {
                    "id": "john_smith",
                    "name": "John Smith",
                    "description": "Software engineer",
                }
            ],
            relationships=[],
            context="John Smith entity...",
            topics=[],
            metadata={"search_mode": "local"},
        )

        state = create_initial_state(query=query, intent="graph")

        with patch(
            "src.agents.graph_query_agent.get_dual_level_search",
            return_value=mock_dual_level_search,
        ):
            updated_state = await graph_query_node(state)

        # Verify LOCAL mode was used
        assert updated_state["graph_query_result"]["mode"] == "local"
        assert len(updated_state["graph_query_result"]["entities"]) == 1

    @pytest.mark.asyncio
    async def test_graph_query_with_global_mode(self, mock_dual_level_search):
        """Test graph query that classifies as GLOBAL mode."""
        query = "Summarize the main themes in the documents"  # Should classify as GLOBAL

        # Update mock to return global mode results
        mock_dual_level_search.search.return_value = GraphSearchResult(
            query=query,
            mode=SearchMode.GLOBAL,
            answer="The main themes include machine learning, NLP, and AI ethics.",
            entities=[],
            relationships=[],
            context="Topics: ML, NLP...",
            topics=["Machine Learning", "NLP", "AI Ethics"],
            metadata={"search_mode": "global"},
        )

        state = create_initial_state(query=query, intent="graph")

        with patch(
            "src.agents.graph_query_agent.get_dual_level_search",
            return_value=mock_dual_level_search,
        ):
            updated_state = await graph_query_node(state)

        # Verify GLOBAL mode was used
        assert updated_state["graph_query_result"]["mode"] == "global"
        assert len(updated_state["graph_query_result"]["topics"]) == 3


# ============================================================================
# Test Graph Query Agent Error Handling
# ============================================================================


class TestGraphQueryAgentErrorHandling:
    """Test error handling in graph query agent."""

    @pytest.mark.asyncio
    async def test_graph_query_with_search_error(self):
        """Test error handling when graph search fails."""
        # Create mock that raises exception
        mock_search = MagicMock()
        mock_search.search = AsyncMock(side_effect=Exception("Neo4j connection failed"))

        agent = GraphQueryAgent(dual_level_search=mock_search)

        state = create_initial_state(query="test query", intent="graph")

        # Process should handle error gracefully
        updated_state = await agent.process(state)

        # Verify error was captured in state
        assert "metadata" in updated_state
        assert "error" in updated_state["metadata"]
        assert "Neo4j connection failed" in updated_state["metadata"]["error"]["message"]

    @pytest.mark.asyncio
    async def test_graph_query_with_empty_query(self):
        """Test handling of empty query."""
        mock_search = MagicMock()
        agent = GraphQueryAgent(dual_level_search=mock_search)

        state = create_initial_state(query="", intent="graph")

        updated_state = await agent.process(state)

        # Should return unchanged (search not called)
        mock_search.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_graph_query_retry_on_transient_error(self):
        """Test retry logic on transient errors."""
        # Create mock that fails twice then succeeds
        mock_search = MagicMock()
        mock_search.search = AsyncMock(
            side_effect=[
                Exception("Transient error 1"),
                Exception("Transient error 2"),
                GraphSearchResult(
                    query="test",
                    mode=SearchMode.HYBRID,
                    answer="Success after retries",
                    entities=[],
                    relationships=[],
                    context="",
                    topics=[],
                    metadata={},
                ),
            ]
        )

        agent = GraphQueryAgent(dual_level_search=mock_search)

        state = create_initial_state(query="test query", intent="graph")

        updated_state = await agent.process(state)

        # Verify it succeeded after retries
        assert "graph_query_result" in updated_state
        assert updated_state["graph_query_result"]["answer"] == "Success after retries"

        # Verify search was called 3 times (2 failures + 1 success)
        assert mock_search.search.call_count == 3


# ============================================================================
# Test Graph Query State Updates
# ============================================================================


class TestGraphQueryStateUpdates:
    """Test that graph query correctly updates state."""

    @pytest.fixture
    def mock_search_with_full_results(self):
        """Mock with comprehensive results."""
        mock = MagicMock()
        mock.search = AsyncMock(
            return_value=GraphSearchResult(
                query="test",
                mode=SearchMode.HYBRID,
                answer="Comprehensive answer",
                entities=[
                    {"id": "e1", "name": "Entity1", "description": "First entity"},
                    {"id": "e2", "name": "Entity2", "description": "Second entity"},
                ],
                relationships=[
                    {
                        "id": "r1",
                        "source": "Entity1",
                        "target": "Entity2",
                        "type": "RELATES_TO",
                    }
                ],
                context="Full context",
                topics=["Topic1", "Topic2"],
                metadata={"custom": "metadata"},
            )
        )
        return mock

    @pytest.mark.asyncio
    async def test_state_includes_all_graph_components(
        self, mock_search_with_full_results
    ):
        """Test that state includes entities, relationships, topics."""
        agent = GraphQueryAgent(dual_level_search=mock_search_with_full_results)

        state = create_initial_state(query="test query", intent="graph")

        updated_state = await agent.process(state)

        # Verify all components present
        result = updated_state["graph_query_result"]
        assert len(result["entities"]) == 2
        assert len(result["relationships"]) == 1
        assert len(result["topics"]) == 2
        assert result["context"] == "Full context"

    @pytest.mark.asyncio
    async def test_retrieved_contexts_format(self, mock_search_with_full_results):
        """Test retrieved_contexts have correct format."""
        agent = GraphQueryAgent(dual_level_search=mock_search_with_full_results)

        state = create_initial_state(query="test query", intent="graph")

        updated_state = await agent.process(state)

        # Verify retrieved_contexts format
        contexts = updated_state["retrieved_contexts"]
        assert len(contexts) == 2

        # Check first context structure
        ctx = contexts[0]
        assert "id" in ctx
        assert "text" in ctx
        assert "score" in ctx
        assert ctx["source"] == "graph"
        assert ctx["search_type"] == "graph"
        assert "metadata" in ctx

    @pytest.mark.asyncio
    async def test_metadata_includes_latency(self, mock_search_with_full_results):
        """Test that metadata includes latency information."""
        agent = GraphQueryAgent(dual_level_search=mock_search_with_full_results)

        state = create_initial_state(query="test query", intent="graph")

        updated_state = await agent.process(state)

        # Verify latency tracking
        metadata = updated_state["metadata"]["graph_search"]
        assert "latency_ms" in metadata
        assert metadata["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_agent_path_tracking(self, mock_search_with_full_results):
        """Test that agent path is tracked correctly."""
        agent = GraphQueryAgent(
            name="test_graph_agent", dual_level_search=mock_search_with_full_results
        )

        state = create_initial_state(query="test query", intent="graph")

        updated_state = await agent.process(state)

        # Verify agent path
        agent_path = updated_state["metadata"]["agent_path"]
        assert len(agent_path) > 0
        assert any("test_graph_agent" in str(step) for step in agent_path)


# ============================================================================
# Test Classification Logic
# ============================================================================


@pytest.mark.asyncio
async def test_classification_influences_search_mode():
    """Test that query classification determines search mode."""
    from src.agents.graph_query_agent import classify_search_mode

    mock_search = MagicMock()
    mock_search.search = AsyncMock(
        return_value=GraphSearchResult(
            query="test",
            mode=SearchMode.LOCAL,
            answer="answer",
            entities=[],
            relationships=[],
            context="",
            topics=[],
            metadata={},
        )
    )

    agent = GraphQueryAgent(dual_level_search=mock_search)

    # Test LOCAL classification
    local_query = "Who is John Smith?"
    assert classify_search_mode(local_query) == SearchMode.LOCAL

    state = create_initial_state(query=local_query, intent="graph")
    await agent.process(state)

    # Verify search was called with LOCAL mode
    call_args = mock_search.search.call_args
    assert call_args[1]["mode"] == SearchMode.LOCAL
