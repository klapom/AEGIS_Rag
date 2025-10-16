"""Integration tests for Coordinator Agent end-to-end flow.

Sprint 4 Feature 4.4: Coordinator Agent Integration
Tests complete query flow, multi-turn conversations, error recovery, and performance.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.coordinator import CoordinatorAgent
from src.agents.error_handler import RetrievalError

# ============================================================================
# End-to-End Query Flow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_query_flow_basic():
    """Test end-to-end query flow without external dependencies."""
    coordinator = CoordinatorAgent(use_persistence=False)

    # Mock the entire graph execution
    mock_result = {
        "query": "What is RAG?",
        "intent": "hybrid",
        "retrieved_contexts": [
            {
                "id": "doc1",
                "text": "RAG stands for Retrieval-Augmented Generation",
                "score": 0.95,
                "source": "test",
                "document_id": "doc1",
                "rank": 1,
                "search_type": "hybrid",
                "metadata": {},
            }
        ],
        "messages": [],
        "metadata": {
            "agent_path": ["router: started", "vector_search: completed"],
        },
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        result = await coordinator.process_query(query="What is RAG?")

        # Verify complete flow
        assert result["query"] == "What is RAG?"
        assert result["intent"] == "hybrid"
        assert len(result["retrieved_contexts"]) == 1
        assert "coordinator" in result["metadata"]
        assert "total_latency_ms" in result["metadata"]["coordinator"]


@pytest.mark.asyncio
async def test_e2e_query_flow_with_session():
    """Test end-to-end flow with session persistence."""
    coordinator = CoordinatorAgent(use_persistence=True)

    mock_result = {
        "query": "Test query",
        "intent": "vector",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        # First query
        result1 = await coordinator.process_query(
            query="Test query 1",
            session_id="session123",
        )

        # Second query in same session
        result2 = await coordinator.process_query(
            query="Test query 2",
            session_id="session123",
        )

        # Both should have same session ID
        assert result1["metadata"]["coordinator"]["session_id"] == "session123"
        assert result2["metadata"]["coordinator"]["session_id"] == "session123"


@pytest.mark.asyncio
async def test_e2e_query_flow_different_intents():
    """Test query flow with different intent types."""
    coordinator = CoordinatorAgent(use_persistence=False)

    intents = ["vector", "hybrid", "graph"]

    for intent in intents:
        mock_result = {
            "query": f"Test {intent} query",
            "intent": intent,
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

        with patch.object(
            coordinator.compiled_graph,
            "ainvoke",
            new=AsyncMock(return_value=mock_result),
        ):
            result = await coordinator.process_query(
                query=f"Test {intent} query",
                intent=intent,
            )

            assert result["intent"] == intent


# ============================================================================
# Multi-Turn Conversation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_multi_turn_conversation_flow():
    """Test multi-turn conversation maintains context."""
    coordinator = CoordinatorAgent(use_persistence=True)

    queries = [
        "What is RAG?",
        "How does it work?",
        "What are the benefits?",
    ]

    call_count = 0

    async def mock_invoke(state, config=None):
        nonlocal call_count
        call_count += 1
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [{"id": f"doc{call_count}", "text": f"Answer {call_count}"}],
            "messages": [],
            "metadata": {"agent_path": [], "turn": call_count},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        results = await coordinator.process_multi_turn(
            queries=queries,
            session_id="conversation123",
        )

        assert len(results) == 3
        assert all("error" not in r for r in results)
        # Verify all used same session
        assert all(r["metadata"]["coordinator"]["session_id"] == "conversation123" for r in results)


@pytest.mark.asyncio
async def test_multi_turn_state_persistence():
    """Test state persists across turns in conversation."""
    coordinator = CoordinatorAgent(use_persistence=True)

    session_id = "persistent_session"
    queries = ["Query 1", "Query 2"]

    configs_seen = []

    async def mock_invoke(state, config=None):
        if config:
            configs_seen.append(config["configurable"]["thread_id"])
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        await coordinator.process_multi_turn(queries=queries, session_id=session_id)

        # All turns should use same thread_id for state persistence
        assert len(configs_seen) == 2
        assert all(tid == session_id for tid in configs_seen)


# ============================================================================
# Error Recovery Tests
# ============================================================================


@pytest.mark.asyncio
async def test_error_recovery_with_retry():
    """Test coordinator recovers from transient errors."""
    coordinator = CoordinatorAgent(use_persistence=False)

    attempt_count = 0

    async def mock_invoke(state, config=None):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise RetrievalError("Temporary database error", agent_name="VectorAgent")
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        result = await coordinator.process_query(query="test query")

        # Should succeed after retry
        assert result["query"] == "test query"
        assert attempt_count == 2


@pytest.mark.asyncio
async def test_error_recovery_multi_turn_continues():
    """Test multi-turn conversation continues after single query error."""
    coordinator = CoordinatorAgent(use_persistence=True)

    call_count = 0

    async def mock_invoke(state, config=None):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            # Fail second query with non-retryable error
            raise ValueError("Invalid query format")
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        results = await coordinator.process_multi_turn(
            queries=["query1", "query2", "query3"],
            session_id="session123",
        )

        # Should have 3 results, one with error
        assert len(results) == 3
        assert "error" not in results[0]
        assert "error" in results[1]  # Failed query
        assert "error" not in results[2]  # Continued after error


@pytest.mark.asyncio
async def test_error_recovery_graceful_degradation():
    """Test graceful degradation when errors occur."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_invoke(state, config=None):
        raise RuntimeError("Complete system failure")

    with (
        patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke),
        pytest.raises(RuntimeError),
    ):
        await coordinator.process_query(query="test query")

        # Even with error, system should not crash


# ============================================================================
# Performance Benchmarks
# ============================================================================


@pytest.mark.asyncio
async def test_performance_single_query_latency():
    """Test single query completes within performance target."""
    coordinator = CoordinatorAgent(use_persistence=False)

    mock_result = {
        "query": "test",
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        start_time = time.perf_counter()
        result = await coordinator.process_query(query="test query")
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete quickly with mocked dependencies
        assert elapsed_ms < 1000  # Less than 1 second
        # Verify latency was tracked
        assert result["metadata"]["coordinator"]["total_latency_ms"] > 0


@pytest.mark.asyncio
async def test_performance_multi_turn_latency():
    """Test multi-turn conversation performance."""
    coordinator = CoordinatorAgent(use_persistence=True)

    async def mock_invoke(state, config=None):
        # Simulate some processing time
        import asyncio

        await asyncio.sleep(0.01)  # 10ms per query
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    queries = ["query1", "query2", "query3"]

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        start_time = time.perf_counter()
        results = await coordinator.process_multi_turn(
            queries=queries,
            session_id="perf_test",
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Should complete in reasonable time
        assert elapsed_ms < 1000  # Less than 1 second for 3 queries
        assert len(results) == 3


@pytest.mark.asyncio
async def test_performance_p95_latency():
    """Test p95 latency is within target."""
    coordinator = CoordinatorAgent(use_persistence=False)

    mock_result = {
        "query": "test",
        "intent": "hybrid",
        "retrieved_contexts": [],
        "messages": [],
        "metadata": {"agent_path": []},
    }

    latencies = []

    with patch.object(
        coordinator.compiled_graph, "ainvoke", new=AsyncMock(return_value=mock_result)
    ):
        # Run 20 queries to calculate p95
        for i in range(20):
            start = time.perf_counter()
            await coordinator.process_query(query=f"test query {i}")
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

    # Calculate p95 (19th out of 20 values when sorted)
    latencies.sort()
    p95_latency = latencies[18]  # 95th percentile

    # p95 should be under 1000ms
    assert p95_latency < 1000


# ============================================================================
# State Persistence Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_state_persistence_across_calls():
    """Test state persists across multiple calls with same session."""
    coordinator = CoordinatorAgent(use_persistence=True)

    session_id = "persistent_test"
    configs_seen = []

    async def mock_invoke(state, config=None):
        if config:
            configs_seen.append(config)
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        # First call
        await coordinator.process_query(query="query1", session_id=session_id)

        # Second call with same session
        await coordinator.process_query(query="query2", session_id=session_id)

        # Both should use same thread_id
        assert len(configs_seen) == 2
        assert configs_seen[0]["configurable"]["thread_id"] == session_id
        assert configs_seen[1]["configurable"]["thread_id"] == session_id


@pytest.mark.asyncio
async def test_different_sessions_isolated():
    """Test different sessions maintain isolated state."""
    coordinator = CoordinatorAgent(use_persistence=True)

    session_ids = []

    async def mock_invoke(state, config=None):
        if config:
            session_ids.append(config["configurable"]["thread_id"])
        return {
            "query": state["query"],
            "intent": "hybrid",
            "retrieved_contexts": [],
            "messages": [],
            "metadata": {"agent_path": []},
        }

    with patch.object(coordinator.compiled_graph, "ainvoke", new=mock_invoke):
        await coordinator.process_query(query="query1", session_id="session1")
        await coordinator.process_query(query="query2", session_id="session2")
        await coordinator.process_query(query="query3", session_id="session1")

        # Verify correct session IDs were used
        assert session_ids[0] == "session1"
        assert session_ids[1] == "session2"
        assert session_ids[2] == "session1"
