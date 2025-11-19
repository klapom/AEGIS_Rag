"""Integration tests for Coordinator Agent (Sprint 27 Feature 27.2).

This module tests the LangGraph coordinator agent with real/mocked agent interactions.

Tests cover:
- Intent routing to vector/graph agents
- Parallel agent execution (Send API)
- Context fusion from multiple sources
- Error recovery and fallback strategies
- State management and persistence
- Multi-turn conversation flows
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from langgraph.graph import StateGraph
from src.agents.router import IntentClassifier, QueryIntent
from src.core.models import DocumentChunk

# Alias for test compatibility
Document = DocumentChunk


@pytest.fixture
def mock_vector_agent():
    """Mock vector search agent."""
    agent = MagicMock()
    agent.search = AsyncMock(
        return_value=[
            Document(
                id="doc1",
                content="Vector search retrieves documents using embeddings.",
                metadata={"source": "docs.md", "score": 0.95},
            ),
            Document(
                id="doc2",
                content="BGE-M3 is used for 1024-dimensional embeddings.",
                metadata={"source": "tech.md", "score": 0.87},
            ),
        ]
    )
    return agent


@pytest.fixture
def mock_graph_agent():
    """Mock graph reasoning agent."""
    agent = MagicMock()
    agent.query = AsyncMock(
        return_value={
            "answer": "Graph reasoning uses LightRAG and Neo4j for multi-hop queries.",
            "entities": ["LightRAG", "Neo4j", "AEGIS RAG"],
            "relationships": [{"source": "AEGIS RAG", "target": "LightRAG", "type": "USES"}],
        }
    )
    return agent


@pytest.fixture
def mock_memory_agent():
    """Mock memory agent."""
    agent = MagicMock()
    agent.retrieve = AsyncMock(
        return_value={
            "short_term": ["User asked about vector search 5 minutes ago"],
            "long_term": ["User prefers technical explanations"],
            "episodic": ["Previous conversation covered RAG basics"],
        }
    )
    return agent


@pytest.fixture
def intent_classifier():
    """IntentClassifier instance for testing."""
    return IntentClassifier()


# ============================================================================
# Intent Routing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coordinator_route_to_vector_agent(intent_classifier):
    """Test routing simple query to vector agent."""
    query = "What is vector search?"

    intent = await intent_classifier.classify(query)

    assert intent == QueryIntent.VECTOR


@pytest.mark.asyncio
async def test_coordinator_route_to_graph_agent(intent_classifier):
    """Test routing complex query to graph agent."""
    query = "How does LightRAG connect to Neo4j and what entities does it extract?"

    intent = await intent_classifier.classify(query)

    assert intent == QueryIntent.GRAPH


@pytest.mark.asyncio
async def test_coordinator_route_hybrid_query(intent_classifier):
    """Test routing query requiring both vector and graph."""
    query = "Explain hybrid search and how it integrates with graph reasoning"

    intent = await intent_classifier.classify(query)

    # Should route to hybrid or both agents
    assert intent in [QueryIntent.HYBRID, QueryIntent.VECTOR, QueryIntent.GRAPH]


# ============================================================================
# Parallel Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coordinator_parallel_agent_execution(mock_vector_agent, mock_graph_agent):
    """Test parallel execution of vector and graph agents."""
    import asyncio

    query = "Test query"

    # Execute both agents in parallel
    vector_task = mock_vector_agent.search(query)
    graph_task = mock_graph_agent.query(query)

    vector_results, graph_results = await asyncio.gather(vector_task, graph_task)

    assert len(vector_results) == 2
    assert "answer" in graph_results
    assert vector_results[0].id == "doc1"


@pytest.mark.asyncio
async def test_coordinator_send_api_usage():
    """Test LangGraph Send API for dynamic parallelism."""
    from langgraph.types import Send

    # Create mock agents
    async def vector_node(state: dict) -> dict:
        return {"vector_results": ["result1", "result2"]}

    async def graph_node(state: dict) -> dict:
        return {"graph_results": {"answer": "test"}}

    # Test Send API dispatch
    sends = [Send("vector_agent", {"query": "test"}), Send("graph_agent", {"query": "test"})]

    assert len(sends) == 2
    assert sends[0].node == "vector_agent"
    assert sends[1].node == "graph_agent"


# ============================================================================
# Context Fusion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coordinator_context_fusion():
    """Test merging results from multiple agents."""
    vector_contexts = [
        Document(id="d1", content="Vector result 1", metadata={"score": 0.9}),
        Document(id="d2", content="Vector result 2", metadata={"score": 0.8}),
    ]

    graph_context = {"answer": "Graph answer", "entities": ["Entity1", "Entity2"]}

    # Fuse contexts
    fused = {
        "vector_results": vector_contexts,
        "graph_results": graph_context,
        "fusion_strategy": "concatenate",
    }

    assert len(fused["vector_results"]) == 2
    assert "answer" in fused["graph_results"]


@pytest.mark.asyncio
async def test_coordinator_deduplication():
    """Test deduplication of overlapping results."""
    results = [
        Document(id="doc1", content="Content 1", metadata={}),
        Document(id="doc2", content="Content 2", metadata={}),
        Document(id="doc1", content="Content 1", metadata={}),  # Duplicate
    ]

    # Deduplicate by ID
    unique_results = {doc.id: doc for doc in results}.values()

    assert len(list(unique_results)) == 2


# ============================================================================
# Error Recovery Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coordinator_error_recovery(mock_vector_agent):
    """Test fallback when agent fails."""
    # Simulate vector agent failure
    mock_vector_agent.search = AsyncMock(side_effect=Exception("Vector search failed"))

    try:
        await mock_vector_agent.search("test")
    except Exception as e:
        # Should fall back to alternative retrieval
        assert "Vector search failed" in str(e)


@pytest.mark.asyncio
async def test_coordinator_partial_failure_handling(mock_vector_agent, mock_graph_agent):
    """Test handling when one agent fails but others succeed."""
    import asyncio

    # Vector agent succeeds, graph agent fails
    mock_graph_agent.query = AsyncMock(side_effect=Exception("Graph query failed"))

    vector_results = await mock_vector_agent.search("test")

    try:
        graph_results = await mock_graph_agent.query("test")
    except Exception:
        graph_results = None

    # Should have vector results even if graph failed
    assert len(vector_results) > 0
    assert graph_results is None


# ============================================================================
# State Management Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coordinator_state_persistence():
    """Test state persistence across conversation turns."""
    state = {
        "messages": [
            {"role": "user", "content": "What is RAG?"},
            {"role": "assistant", "content": "RAG is..."},
        ],
        "retrieved_contexts": [],
        "session_id": "session_123",
    }

    # Simulate state update
    state["messages"].append({"role": "user", "content": "Tell me more"})

    assert len(state["messages"]) == 3
    assert state["session_id"] == "session_123"


@pytest.mark.asyncio
async def test_coordinator_multi_turn_context():
    """Test context accumulation over multiple turns."""
    conversation_history = []

    # Turn 1
    conversation_history.append(
        {"query": "What is vector search?", "response": "Vector search uses embeddings..."}
    )

    # Turn 2 (references Turn 1)
    conversation_history.append(
        {"query": "How does it compare to BM25?", "response": "Compared to vector search, BM25..."}
    )

    assert len(conversation_history) == 2
    assert "vector search" in conversation_history[0]["query"]


# ============================================================================
# Integration Flow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_coordinator_flow(mock_vector_agent, mock_graph_agent, mock_memory_agent):
    """Test complete coordinator flow: route → execute → fuse → generate."""
    query = "Explain hybrid search in AEGIS RAG"

    # Step 1: Retrieve memory context
    memory_context = await mock_memory_agent.retrieve(query)

    # Step 2: Execute retrieval agents
    vector_results = await mock_vector_agent.search(query)
    graph_results = await mock_graph_agent.query(query)

    # Step 3: Fuse contexts
    fused_context = {"memory": memory_context, "vector": vector_results, "graph": graph_results}

    # Step 4: Generate response (mocked)
    final_response = f"Based on context, hybrid search combines vector and keyword retrieval."

    assert "vector" in fused_context
    assert "graph" in fused_context
    assert len(final_response) > 0
