"""Unit tests for Coordinator Agent Streaming.

Sprint 48 Feature 48.2: CoordinatorAgent Streaming Method (13 SP)
Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP)
Tests process_query_stream and phase event emission.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.coordinator import CoordinatorAgent
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType


# ============================================================================
# Streaming Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_query_stream_basic():
    """Test basic streaming query processing."""
    coordinator = CoordinatorAgent(use_persistence=False)

    # Mock the astream method to yield events
    async def mock_astream(initial_state, config=None):
        # Yield router node completion
        yield {
            "router": {
                "query": "test query",
                "intent": "hybrid",
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.INTENT_CLASSIFICATION,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=50.0,
                    metadata={"intent": "hybrid"},
                ),
            }
        }

        # Yield vector search completion
        yield {
            "vector_search": {
                "query": "test query",
                "retrieved_contexts": [{"text": "context1", "score": 0.9}],
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.VECTOR_SEARCH,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=100.0,
                    metadata={"results_count": 1},
                ),
            }
        }

        # Yield answer generation completion
        yield {
            "answer": {
                "query": "test query",
                "answer": "Test answer",
                "citation_map": {},
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.LLM_GENERATION,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=200.0,
                    metadata={"answer_length": 11},
                ),
            }
        }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(query="test query"):
            events.append(event)

        # Verify we got events
        assert len(events) > 0

        # Check for phase_event types
        phase_events = [e for e in events if e["type"] == "phase_event"]
        assert len(phase_events) == 3  # Router, vector search, LLM generation

        # Check for answer_chunk
        answer_chunks = [e for e in events if e["type"] == "answer_chunk"]
        assert len(answer_chunks) == 1
        assert answer_chunks[0]["data"]["answer"] == "Test answer"

        # Check for reasoning_complete
        reasoning_complete = [e for e in events if e["type"] == "reasoning_complete"]
        assert len(reasoning_complete) == 1
        assert "phase_events" in reasoning_complete[0]["data"]


@pytest.mark.asyncio
async def test_process_query_stream_phase_events_order():
    """Test that phase events are emitted in correct order."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None):
        phases = [
            PhaseType.INTENT_CLASSIFICATION,
            PhaseType.VECTOR_SEARCH,
            PhaseType.LLM_GENERATION,
        ]

        for i, phase in enumerate(phases):
            yield {
                f"node_{i}": {
                    "phase_event": PhaseEvent(
                        phase_type=phase,
                        status=PhaseStatus.COMPLETED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration_ms=float(i * 50),
                        metadata={},
                    ),
                    "answer": "Final answer" if i == len(phases) - 1 else None,
                }
            }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(query="test query"):
            events.append(event)

        # Extract phase events
        phase_events = [e for e in events if e["type"] == "phase_event"]

        # Verify order
        assert len(phase_events) == 3
        assert phase_events[0]["data"]["phase_type"] == PhaseType.INTENT_CLASSIFICATION.value
        assert phase_events[1]["data"]["phase_type"] == PhaseType.VECTOR_SEARCH.value
        assert phase_events[2]["data"]["phase_type"] == PhaseType.LLM_GENERATION.value


@pytest.mark.asyncio
async def test_process_query_stream_with_failed_phase():
    """Test streaming with a failed phase event."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None):
        # Successful router
        yield {
            "router": {
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.INTENT_CLASSIFICATION,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=50.0,
                ),
            }
        }

        # Failed vector search
        raise Exception("Vector search failed")

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        with pytest.raises(Exception, match="Vector search failed"):
            events = []
            async for event in coordinator.process_query_stream(query="test query"):
                events.append(event)


@pytest.mark.asyncio
async def test_process_query_stream_with_session_id():
    """Test streaming with session ID for persistence."""
    coordinator = CoordinatorAgent(use_persistence=True)

    async def mock_astream(initial_state, config=None):
        # Verify config has session_id
        assert config is not None
        assert "configurable" in config
        assert "thread_id" in config["configurable"]

        yield {
            "answer": {
                "answer": "Test answer",
                "citation_map": {},
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.LLM_GENERATION,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=100.0,
                ),
            }
        }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(
            query="test query", session_id="session123"
        ):
            events.append(event)

        # Verify we got events
        assert len(events) > 0


@pytest.mark.asyncio
async def test_process_query_stream_metadata_accumulation():
    """Test that ReasoningData accumulates phase events correctly."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None):
        for i in range(3):
            yield {
                f"node_{i}": {
                    "phase_event": PhaseEvent(
                        phase_type=PhaseType.VECTOR_SEARCH,
                        status=PhaseStatus.COMPLETED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration_ms=float(i * 100),
                        metadata={"iteration": i},
                    ),
                    "answer": "Final" if i == 2 else None,
                }
            }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(query="test query"):
            events.append(event)

        # Find reasoning_complete event
        reasoning_complete = [e for e in events if e["type"] == "reasoning_complete"]
        assert len(reasoning_complete) == 1

        # Verify all phase events accumulated
        phase_events = reasoning_complete[0]["data"]["phase_events"]
        assert len(phase_events) == 3
        assert all(e["phase_type"] == PhaseType.VECTOR_SEARCH.value for e in phase_events)


@pytest.mark.asyncio
async def test_process_query_stream_with_namespaces():
    """Test streaming with namespace filtering."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None):
        # Verify namespaces in initial state
        assert "namespaces" in initial_state
        assert initial_state["namespaces"] == ["ns1", "ns2"]

        yield {
            "answer": {
                "answer": "Answer",
                "citation_map": {},
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.LLM_GENERATION,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=100.0,
                ),
            }
        }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(
            query="test query", namespaces=["ns1", "ns2"]
        ):
            events.append(event)

        assert len(events) > 0


# ============================================================================
# Phase Event Tests
# ============================================================================


@pytest.mark.asyncio
async def test_phase_event_contains_duration():
    """Test that completed phase events include duration."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None):
        yield {
            "router": {
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.INTENT_CLASSIFICATION,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=123.45,
                    metadata={"intent": "hybrid"},
                ),
            }
        }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(query="test"):
            events.append(event)

        phase_events = [e for e in events if e["type"] == "phase_event"]
        assert len(phase_events) >= 1
        assert phase_events[0]["data"]["duration_ms"] == 123.45
        assert phase_events[0]["data"]["status"] == PhaseStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_phase_event_contains_metadata():
    """Test that phase events include relevant metadata."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None):
        yield {
            "vector_search": {
                "phase_event": PhaseEvent(
                    phase_type=PhaseType.VECTOR_SEARCH,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=100.0,
                    metadata={
                        "results_count": 5,
                        "vector_count": 3,
                        "bm25_count": 2,
                        "reranking_applied": False,
                    },
                ),
            }
        }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        events = []
        async for event in coordinator.process_query_stream(query="test"):
            events.append(event)

        phase_events = [e for e in events if e["type"] == "phase_event"]
        assert len(phase_events) >= 1
        metadata = phase_events[0]["data"]["metadata"]
        assert metadata["results_count"] == 5
        assert metadata["vector_count"] == 3
        assert metadata["bm25_count"] == 2
        assert metadata["reranking_applied"] is False
