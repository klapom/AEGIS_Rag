"""Unit tests for Graph Query Agent.

Tests the GraphQueryAgent class, classify_search_mode function,
and graph_query_node LangGraph node function.

Sprint 5: Feature 5.5 - Graph Query Agent
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.graph_query_agent import (
    GraphQueryAgent,
    classify_search_mode,
    graph_query_node,
)
from src.components.graph_rag.dual_level_search import (
    GraphSearchResult,
    SearchMode,
)

# ============================================================================
# Test classify_search_mode function
# ============================================================================


class TestClassifySearchMode:
    """Test query classification for search mode selection."""

    def test_classify_local_who_is(self):
        """Test classification of 'who is' query."""
        query = "Who is John Smith?"
        mode = classify_search_mode(query)
        assert mode == SearchMode.LOCAL

    def test_classify_local_what_is(self):
        """Test classification of 'what is' query."""
        query = "What is Retrieval-Augmented Generation?"
        mode = classify_search_mode(query)
        assert mode == SearchMode.LOCAL

    def test_classify_local_which(self):
        """Test classification of 'which' query."""
        query = "Which companies use RAG?"
        mode = classify_search_mode(query)
        assert mode == SearchMode.LOCAL

    def test_classify_global_summarize(self):
        """Test classification of 'summarize' query."""
        query = "Summarize the main themes in the documents"
        mode = classify_search_mode(query)
        assert mode == SearchMode.GLOBAL

    def test_classify_global_overview(self):
        """Test classification of 'overview' query."""
        query = "Give me an overview of machine learning topics"
        mode = classify_search_mode(query)
        assert mode == SearchMode.GLOBAL

    def test_classify_global_main_themes(self):
        """Test classification of 'main themes' query."""
        query = "Summarize main themes in AI research?"
        mode = classify_search_mode(query)
        assert mode == SearchMode.GLOBAL

    def test_classify_hybrid_default(self):
        """Test default classification to hybrid."""
        query = "How are RAG and LLMs related?"
        mode = classify_search_mode(query)
        assert mode == SearchMode.HYBRID

    def test_classify_hybrid_complex(self):
        """Test complex query defaults to hybrid."""
        query = "Compare the advantages of vector search versus graph retrieval"
        mode = classify_search_mode(query)
        assert mode == SearchMode.HYBRID

    def test_classify_empty_query(self):
        """Test empty query defaults to hybrid."""
        query = ""
        mode = classify_search_mode(query)
        assert mode == SearchMode.HYBRID

    def test_classify_case_insensitive(self):
        """Test classification is case-insensitive."""
        query = "WHO IS John Smith?"
        mode = classify_search_mode(query)
        assert mode == SearchMode.LOCAL


# ============================================================================
# Test GraphQueryAgent class
# ============================================================================


class TestGraphQueryAgent:
    """Test GraphQueryAgent initialization and processing."""

    @pytest.fixture
    def mock_dual_level_search(self):
        """Mock DualLevelSearch instance."""
        from src.core.models import GraphEntity, Topic

        mock = MagicMock()

        # Configure local_search as AsyncMock - returns list[GraphEntity]
        mock.local_search = AsyncMock(
            return_value=[
                GraphEntity(
                    id="entity_1",
                    name="Test Entity",
                    type="PERSON",
                    description="A test entity",
                    properties={},
                    source_document="test_doc",
                    confidence=0.9,
                )
            ]
        )

        # Configure global_search as AsyncMock - returns list[Topic]
        mock.global_search = AsyncMock(
            return_value=[
                Topic(
                    id="topic_1",
                    name="Test Topic",
                    summary="A test topic summary",
                    entities=["entity_1"],
                    keywords=["keyword1", "keyword2"],
                    score=0.95,
                )
            ]
        )

        # Configure hybrid_search as AsyncMock - returns GraphSearchResult
        mock.hybrid_search = AsyncMock(
            return_value=GraphSearchResult(
                query="test query",
                mode=SearchMode.HYBRID,
                answer="Hybrid answer",
                entities=[
                    {
                        "id": "entity_2",
                        "name": "Hybrid Entity",
                        "type": "CONCEPT",
                        "description": "Entity from hybrid search",
                        "properties": {},
                        "source_document": "hybrid_doc",
                        "confidence": 0.85,
                    }
                ],
                relationships=[],
                context="Test context from hybrid search",
                topics=[],
                metadata={},
            )
        )

        return mock

    @pytest.fixture
    def agent(self, mock_dual_level_search):
        """GraphQueryAgent instance with mocked dependencies."""
        return GraphQueryAgent(name="test_graph_agent", dual_level_search=mock_dual_level_search)

    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent is not None
        assert agent.name == "test_graph_agent"
        assert agent.dual_level_search is not None

    def test_agent_get_name(self, agent):
        """Test get_name method."""
        assert agent.get_name() == "test_graph_agent"

    @pytest.mark.asyncio
    async def test_process_with_valid_query(self, agent, mock_dual_level_search):
        """Test processing with valid query."""
        state = {
            "query": "Who is John Smith?",
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Verify search was called
        mock_dual_level_search.local_search.assert_called_once()

        # Verify state was updated with graph results
        assert "graph_query_result" in updated_state
        assert updated_state["graph_query_result"]["query"] == "Who is John Smith?"
        assert updated_state["graph_query_result"]["mode"] == "local"
        # Agent constructs answer from entities count
        assert "Found 1 entities" in updated_state["graph_query_result"]["answer"]
        assert len(updated_state["graph_query_result"]["entities"]) == 1

        # Verify metadata was updated
        assert "graph_search" in updated_state["metadata"]
        assert "mode" in updated_state["metadata"]["graph_search"]
        assert "latency_ms" in updated_state["metadata"]["graph_search"]

    @pytest.mark.asyncio
    async def test_process_with_global_query(self, agent, mock_dual_level_search):
        """Test processing with query classified as global."""
        state = {
            "query": "Summarize the main themes",
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Verify global_search was called
        mock_dual_level_search.global_search.assert_called_once()

        # Verify global mode was used
        assert updated_state["graph_query_result"]["mode"] == "global"
        # Agent constructs answer from topics count
        assert "Found 1 topics" in updated_state["graph_query_result"]["answer"]
        assert len(updated_state["graph_query_result"]["topics"]) == 1

    @pytest.mark.asyncio
    async def test_process_with_empty_query(self, agent):
        """Test processing with empty query."""
        state = {
            "query": "",
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Should return state unchanged (with warning logged)
        assert updated_state == state

    @pytest.mark.asyncio
    async def test_process_adds_to_agent_path(self, agent):
        """Test that process adds agent to trace path."""
        state = {
            "query": "test query",
            "intent": "graph",
            "metadata": {"agent_path": []},
        }

        updated_state = await agent.process(state)

        # Verify agent was added to path
        assert "agent_path" in updated_state["metadata"]
        assert "test_graph_agent" in str(updated_state["metadata"]["agent_path"])

    @pytest.mark.asyncio
    async def test_process_converts_entities_to_contexts(self, agent, mock_dual_level_search):
        """Test that entities are converted to retrieved_contexts format."""
        state = {
            "query": "test query",
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Verify retrieved_contexts was populated
        assert "retrieved_contexts" in updated_state
        assert len(updated_state["retrieved_contexts"]) > 0

        # Verify context format
        context = updated_state["retrieved_contexts"][0]
        assert "id" in context
        assert "text" in context
        assert "score" in context
        assert context["source"] == "graph"
        assert context["search_type"] == "graph"

    @pytest.mark.asyncio
    async def test_process_handles_search_error(self, agent, mock_dual_level_search):
        """Test error handling when search fails."""
        # Make hybrid_search raise an exception (default for generic queries)
        mock_dual_level_search.hybrid_search.side_effect = Exception("Search failed")

        state = {
            "query": "test query",
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Verify error was handled
        assert "metadata" in updated_state
        assert "error" in updated_state["metadata"]
        assert "Search failed" in updated_state["metadata"]["error"]["message"]

    @pytest.mark.asyncio
    async def test_process_with_existing_contexts(self, agent, mock_dual_level_search):
        """Test that new contexts are appended to existing ones."""
        state = {
            "query": "test query",
            "intent": "graph",
            "metadata": {},
            "retrieved_contexts": [
                {
                    "id": "existing_1",
                    "text": "Existing context",
                    "score": 0.9,
                    "source": "vector",
                }
            ],
        }

        updated_state = await agent.process(state)

        # Verify new contexts were appended
        assert len(updated_state["retrieved_contexts"]) > 1
        assert updated_state["retrieved_contexts"][0]["id"] == "existing_1"
        assert updated_state["retrieved_contexts"][0]["source"] == "vector"


# ============================================================================
# Test graph_query_node function
# ============================================================================


class TestGraphQueryNode:
    """Test graph_query_node LangGraph node function."""

    @pytest.fixture
    def mock_agent(self):
        """Mock GraphQueryAgent."""
        mock = MagicMock()
        mock.process = AsyncMock(
            return_value={
                "query": "test",
                "intent": "graph",
                "graph_query_result": {
                    "answer": "Test answer",
                    "entities": [],
                },
                "metadata": {
                    "graph_search": {
                        "entities_found": 0,
                    }
                },
            }
        )
        return mock

    @pytest.mark.asyncio
    async def test_node_function_invokes_agent(self, mock_agent):
        """Test that node function creates and invokes agent."""
        state = {
            "query": "test query",
            "intent": "graph",
            "metadata": {},
        }

        with patch("src.agents.graph_query_agent.GraphQueryAgent", return_value=mock_agent):
            updated_state = await graph_query_node(state)

        # Verify agent was created and process was called
        mock_agent.process.assert_called_once_with(state)

        # Verify state was updated
        assert "graph_query_result" in updated_state
        assert updated_state["graph_query_result"]["answer"] == "Test answer"

    @pytest.mark.asyncio
    async def test_node_function_with_empty_state(self, mock_agent):
        """Test node function with minimal state."""
        state = {}

        with patch("src.agents.graph_query_agent.GraphQueryAgent", return_value=mock_agent):
            await graph_query_node(state)

        # Should still process without error
        mock_agent.process.assert_called_once()


# ============================================================================
# Integration-style tests (with real components, no external dependencies)
# ============================================================================


class TestGraphQueryAgentIntegration:
    """Integration tests for GraphQueryAgent with real components."""

    @pytest.mark.asyncio
    async def test_full_flow_with_real_classifier(self):
        """Test full flow with real classify_search_mode function."""
        from src.core.models import GraphEntity

        # Create agent with mock search
        mock_search = MagicMock()
        # local_search returns list[GraphEntity], not GraphSearchResult
        mock_search.local_search = AsyncMock(
            return_value=[
                GraphEntity(
                    id="john_smith",
                    name="John Smith",
                    type="PERSON",
                    description="A software engineer",
                    properties={},
                    source_document="doc1",
                    confidence=0.95,
                )
            ]
        )

        agent = GraphQueryAgent(dual_level_search=mock_search)

        state = {
            "query": "Who is John Smith?",  # Should classify as LOCAL
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Verify local_search was called
        mock_search.local_search.assert_called_once()
        # Verify result contains entity
        assert len(updated_state["graph_query_result"]["entities"]) == 1
        assert updated_state["graph_query_result"]["entities"][0]["name"] == "John Smith"

    @pytest.mark.asyncio
    async def test_full_flow_global_classification(self):
        """Test full flow with query that classifies as global."""
        from src.core.models import Topic

        mock_search = MagicMock()
        # global_search returns list[Topic], not GraphSearchResult
        mock_search.global_search = AsyncMock(
            return_value=[
                Topic(
                    id="topic1",
                    name="Machine Learning",
                    summary="Documents about ML",
                    entities=["entity1", "entity2"],
                    keywords=["ml", "ai"],
                    score=0.9,
                )
            ]
        )

        agent = GraphQueryAgent(dual_level_search=mock_search)

        state = {
            "query": "Summarize the main themes",  # Should classify as GLOBAL
            "intent": "graph",
            "metadata": {},
        }

        updated_state = await agent.process(state)

        # Verify global_search was called
        mock_search.global_search.assert_called_once()
        # Verify result contains topic
        assert len(updated_state["graph_query_result"]["topics"]) == 1
        assert updated_state["graph_query_result"]["topics"][0]["name"] == "Machine Learning"


# ============================================================================
# Parametrized tests for comprehensive coverage
# ============================================================================


@pytest.mark.parametrize(
    "query,expected_mode",
    [
        ("Who is the CEO?", SearchMode.LOCAL),
        ("What is machine learning?", SearchMode.LOCAL),
        ("Summarize the dataset", SearchMode.GLOBAL),
        ("Give me an overview", SearchMode.GLOBAL),
        ("How are X and Y related?", SearchMode.HYBRID),
        ("", SearchMode.HYBRID),
    ],
)
def test_classify_search_mode_parametrized(query: str, expected_mode: SearchMode):
    """Parametrized test for classify_search_mode."""
    mode = classify_search_mode(query)
    assert mode == expected_mode
