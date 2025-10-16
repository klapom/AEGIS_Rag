"""Unit tests for Coordinator Agent.

Sprint 4 Feature 4.4: Coordinator Agent with State Persistence
Tests process_query, session management, and state persistence.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.coordinator import CoordinatorAgent, get_coordinator
from src.agents.error_handler import RetrievalError

# ============================================================================
# Coordinator Initialization Tests
# ============================================================================


def test_coordinator_initialization_with_persistence():
    """Test coordinator initializes with persistence enabled."""
    coordinator = CoordinatorAgent(use_persistence=True)

    assert coordinator.name == "CoordinatorAgent"
    assert coordinator.use_persistence is True
    assert coordinator.checkpointer is not None
    assert coordinator.compiled_graph is not None


def test_coordinator_initialization_without_persistence():
    """Test coordinator initializes without persistence."""
    coordinator = CoordinatorAgent(use_persistence=False)

    assert coordinator.name == "CoordinatorAgent"
    assert coordinator.use_persistence is False
    assert coordinator.checkpointer is None
    assert coordinator.compiled_graph is not None


def test_coordinator_initialization_custom_recursion_limit():
    """Test coordinator with custom recursion limit."""
    coordinator = CoordinatorAgent(recursion_limit=50)

    assert coordinator.recursion_limit == 50


def test_coordinator_initialization_default_recursion_limit():
    """Test coordinator uses default recursion limit from settings."""
    with patch("src.agents.coordinator.settings") as mock_settings:
        mock_settings.langgraph_recursion_limit = 30

        coordinator = CoordinatorAgent()

        assert coordinator.recursion_limit == 30


# ============================================================================
# Process Query Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_query_basic():
    """Test basic query processing."""
    coordinator = CoordinatorAgent(use_persistence=False)

    # Mock the compiled graph
    mock_result = {
        "query": "test query",
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        result = await coordinator.process_query(query="test query")

        assert result["query"] == "test query"
        assert "metadata" in result
        assert "coordinator" in result["metadata"]
        assert result["metadata"]["coordinator"]["use_persistence"] is False


@pytest.mark.asyncio
async def test_process_query_with_session_id():
    """Test query processing with session ID."""
    coordinator = CoordinatorAgent(use_persistence=True)

    mock_result = {
        "query": "test query",
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        result = await coordinator.process_query(
            query="test query",
            session_id="session123",
        )

        assert result["metadata"]["coordinator"]["session_id"] == "session123"
        assert result["metadata"]["coordinator"]["use_persistence"] is True


@pytest.mark.asyncio
async def test_process_query_with_intent_override():
    """Test query processing with intent override."""
    coordinator = CoordinatorAgent(use_persistence=False)

    mock_result = {
        "query": "test query",
        "intent": "vector",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ) as mock_invoke:
        await coordinator.process_query(
            query="test query",
            intent="vector",
        )

        # Verify intent was passed to initial state
        call_args = mock_invoke.call_args
        assert call_args[0][0]["intent"] == "vector"


@pytest.mark.asyncio
async def test_process_query_updates_agent_path():
    """Test process_query adds coordinator to agent path."""
    coordinator = CoordinatorAgent(use_persistence=False)

    mock_result = {
        "query": "test query",
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": ["router: started"]},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        result = await coordinator.process_query(query="test query")

        agent_path = result["metadata"]["agent_path"]
        assert agent_path[0] == "coordinator: started"
        assert agent_path[-1].startswith("coordinator: completed")


@pytest.mark.asyncio
async def test_process_query_tracks_latency():
    """Test process_query tracks execution latency."""
    coordinator = CoordinatorAgent(use_persistence=False)

    mock_result = {
        "query": "test query",
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        result = await coordinator.process_query(query="test query")

        assert "total_latency_ms" in result["metadata"]["coordinator"]
        assert result["metadata"]["coordinator"]["total_latency_ms"] > 0


@pytest.mark.asyncio
async def test_process_query_with_results():
    """Test process_query with retrieved contexts."""
    coordinator = CoordinatorAgent(use_persistence=False)

    mock_result = {
        "query": "test query",
        "intent": "hybrid",
        "retrieved_contexts": [
            {"id": "doc1", "text": "context 1", "score": 0.9},
            {"id": "doc2", "text": "context 2", "score": 0.8},
        ],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        result = await coordinator.process_query(query="test query")

        assert len(result["retrieved_contexts"]) == 2
        assert result["retrieved_contexts"][0]["id"] == "doc1"


@pytest.mark.asyncio
async def test_process_query_error_handling():
    """Test process_query handles errors gracefully."""
    coordinator = CoordinatorAgent(use_persistence=False)

    # Mock graph to raise exception
    with (
        patch.object(
            coordinator.compiled_graph,
            "ainvoke",
            new=AsyncMock(side_effect=RuntimeError("Test error")),
        ),
        pytest.raises(RuntimeError),
    ):
        await coordinator.process_query(query="test query")


@pytest.mark.asyncio
async def test_process_query_retry_on_failure():
    """Test process_query retries on retryable errors."""
    coordinator = CoordinatorAgent(use_persistence=False)

    call_count = 0

    async def mock_invoke(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RetrievalError("Temporary failure", agent_name="TestAgent")
        return {
            "query": "test query",
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        result = await coordinator.process_query(query="test query")

        # Should succeed after retry
        assert result["query"] == "test query"
        assert call_count == 2


# ============================================================================
# Multi-Turn Conversation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_multi_turn_basic():
    """Test multi-turn conversation processing."""
    coordinator = CoordinatorAgent(use_persistence=True)

    mock_result_template = {
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    async def mock_invoke(state, config=None):
        result = mock_result_template.copy()
        result["query"] = state["query"]
        return result

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        results = await coordinator.process_multi_turn(
            queries=["query 1", "query 2", "query 3"],
            session_id="session123",
        )

        assert len(results) == 3
        assert results[0]["query"] == "query 1"
        assert results[1]["query"] == "query 2"
        assert results[2]["query"] == "query 3"


@pytest.mark.asyncio
async def test_process_multi_turn_maintains_session():
    """Test multi-turn maintains same session ID."""
    coordinator = CoordinatorAgent(use_persistence=True)

    session_ids_seen = []

    async def mock_invoke(state, config=None):
        if config:
            session_ids_seen.append(config["configurable"]["thread_id"])
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        await coordinator.process_multi_turn(
            queries=["query 1", "query 2"],
            session_id="session123",
        )

        # All queries should use same session ID
        assert all(sid == "session123" for sid in session_ids_seen)


@pytest.mark.asyncio
async def test_process_multi_turn_error_continues():
    """Test multi-turn continues after error in one query."""
    coordinator = CoordinatorAgent(use_persistence=True)

    call_count = 0

    async def mock_invoke(state, config=None):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Error in query 2")
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        results = await coordinator.process_multi_turn(
            queries=["query 1", "query 2", "query 3"],
            session_id="session123",
        )

        assert len(results) == 3
        assert "error" not in results[0]
        assert "error" in results[1]  # Failed query
        assert "error" not in results[2]


# ============================================================================
# Session History Tests
# ============================================================================


def test_get_session_history_with_persistence():
    """Test getting session history with persistence enabled."""
    coordinator = CoordinatorAgent(use_persistence=True)

    with patch("src.agents.checkpointer.get_conversation_history") as mock_get_history:
        mock_get_history.return_value = [{"checkpoint": 1}, {"checkpoint": 2}]

        history = coordinator.get_session_history("session123")

        assert len(history) == 2
        mock_get_history.assert_called_once_with(coordinator.checkpointer, "session123")


def test_get_session_history_without_persistence():
    """Test getting session history with persistence disabled."""
    coordinator = CoordinatorAgent(use_persistence=False)

    history = coordinator.get_session_history("session123")

    assert history == []


def test_get_session_history_error_handling():
    """Test session history handles errors gracefully."""
    coordinator = CoordinatorAgent(use_persistence=True)

    with patch(
        "src.agents.checkpointer.get_conversation_history",
        side_effect=RuntimeError("Test error"),
    ):
        history = coordinator.get_session_history("session123")

        # Should return empty list on error
        assert history == []


# ============================================================================
# Singleton Tests
# ============================================================================


def test_get_coordinator_singleton():
    """Test get_coordinator returns singleton instance."""
    coordinator1 = get_coordinator(use_persistence=False, force_new=True)
    coordinator2 = get_coordinator()

    # Should be same instance
    assert coordinator1 is coordinator2


def test_get_coordinator_force_new():
    """Test get_coordinator with force_new creates new instance."""
    coordinator1 = get_coordinator(use_persistence=False, force_new=True)
    coordinator2 = get_coordinator(use_persistence=True, force_new=True)

    # Should be different instances
    assert coordinator1 is not coordinator2


def test_get_coordinator_default_persistence():
    """Test get_coordinator uses default persistence setting."""
    coordinator = get_coordinator(force_new=True)

    assert coordinator.use_persistence is True


# ============================================================================
# Integration with State Persistence Tests
# ============================================================================


@pytest.mark.asyncio
async def test_coordinator_passes_config_to_graph():
    """Test coordinator passes config to graph for state persistence."""
    coordinator = CoordinatorAgent(use_persistence=True)

    config_received = None

    async def mock_invoke(state, config=None):
        nonlocal config_received
        config_received = config
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        await coordinator.process_query(query="test", session_id="session123")

        assert config_received is not None
        assert "configurable" in config_received
        assert config_received["configurable"]["thread_id"] == "session123"
        assert "recursion_limit" in config_received


@pytest.mark.asyncio
async def test_coordinator_no_config_without_session():
    """Test coordinator doesn't pass config without session ID."""
    coordinator = CoordinatorAgent(use_persistence=True)

    config_received = "not_set"

    async def mock_invoke(state, config=None):
        nonlocal config_received
        config_received = config
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        await coordinator.process_query(query="test")

        # Should be None when no session_id provided
        assert config_received is None
