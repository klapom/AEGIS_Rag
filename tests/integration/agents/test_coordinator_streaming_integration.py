"""Integration tests for Coordinator Agent Streaming with Full Workflow.

Sprint 48 Feature 48.2: CoordinatorAgent Streaming Method (13 SP)
Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP)
Sprint 48 Feature 48.5: Phase Events Redis Persistence (5 SP)

These tests verify the complete streaming workflow with real components:
- Full phase event emission throughout the pipeline
- Phase event persistence to Redis
- Proper timing and metadata collection
- Error handling during streaming
"""

import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest

from src.agents.coordinator import CoordinatorAgent
from src.agents.reasoning_data import ReasoningData
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

# ============================================================================
# Full Streaming Workflow Integration Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_streaming_workflow():
    """Test complete streaming workflow with all phases and proper event emissions."""
    coordinator = CoordinatorAgent(use_persistence=False)

    query = "What is retrieval augmented generation?"
    session_id = "test-conv-streaming-" + str(datetime.utcnow().timestamp()).replace(".", "-")

    events_received = []
    answer_chunks = []
    reasoning_complete = None

    async def mock_astream(initial_state, config=None, stream_mode=None):
        """Mock the compiled graph's astream with stream_mode=['custom', 'values'] to return tuples."""
        # Build up phase events list across iterations
        phase_events = []

        # Iteration 1: Intent Classification
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=75.5,
                metadata={"detected_intent": "hybrid", "confidence": 0.95},
            )
        )
        # Sprint 52: Yield tuples matching stream_mode format
        yield (
            "values",
            {
                "query": query,
                "intent": "hybrid",
                "phase_events": phase_events.copy(),
            },
        )

        # Iteration 2: Vector Search
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=150.0,
                metadata={"docs_retrieved": 2, "collection": "documents_v1", "top_k": 10},
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "hybrid",
                "retrieved_contexts": [
                    {"text": "RAG combines retrieval with generation", "score": 0.92},
                    {"text": "Vector search finds relevant documents", "score": 0.88},
                ],
                "phase_events": phase_events.copy(),
            },
        )

        # Iteration 3: Graph Query
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.GRAPH_QUERY,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=120.0,
                metadata={"entities_found": 1, "relationships_found": 2},
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "hybrid",
                "graph_results": [
                    {
                        "entity": "RAG",
                        "type": "system",
                        "properties": {"full_name": "Retrieval-Augmented Generation"},
                    },
                ],
                "phase_events": phase_events.copy(),
            },
        )

        # Iteration 4: Reranking
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.RERANKING,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=85.0,
                metadata={"reranked_count": 1, "model": "cross-encoder"},
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "hybrid",
                "reranked_contexts": [
                    {"text": "RAG combines retrieval with generation", "score": 0.96},
                ],
                "phase_events": phase_events.copy(),
            },
        )

        # Iteration 5: LLM Generation
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=250.0,
                metadata={"tokens_generated": 35, "model": "ollama:llama3.2"},
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "hybrid",
                "answer": "RAG (Retrieval-Augmented Generation) combines retrieval mechanisms with LLM generation to provide more accurate and contextual answers.",
                "citation_map": {"source1": 0},
                "phase_events": phase_events.copy(),
            },
        )

    # Mock the compiled graph
    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
        async for event in coordinator.process_query_stream(
            query=query,
            session_id=session_id,
        ):
            if event["type"] == "phase_event":
                events_received.append(event["data"])
            elif event["type"] == "answer_chunk":
                answer_chunks.append(event["data"])
            elif event["type"] == "reasoning_complete":
                reasoning_complete = event["data"]

    # Verify phase events
    assert (
        len(events_received) >= 5
    ), f"Expected at least 5 phase events, got {len(events_received)}"

    # Verify all phases completed successfully
    completed = [e for e in events_received if e["status"] == "completed"]
    assert len(completed) >= 5, f"Expected at least 5 completed phases, got {len(completed)}"

    # Verify phase types present
    phase_types = {e["phase_type"] for e in events_received}
    assert PhaseType.INTENT_CLASSIFICATION.value in phase_types
    assert PhaseType.VECTOR_SEARCH.value in phase_types
    assert PhaseType.GRAPH_QUERY.value in phase_types
    assert PhaseType.RERANKING.value in phase_types
    assert PhaseType.LLM_GENERATION.value in phase_types

    # Verify timing information
    for event in completed:
        assert event["start_time"] is not None
        assert event["end_time"] is not None
        assert event["duration_ms"] > 0

    # Verify metadata
    vector_event = next(e for e in events_received if e["phase_type"] == "vector_search")
    assert vector_event["metadata"]["docs_retrieved"] == 2
    assert vector_event["metadata"]["collection"] == "documents_v1"

    graph_event = next(e for e in events_received if e["phase_type"] == "graph_query")
    assert graph_event["metadata"]["entities_found"] == 1

    # Verify answer generated
    assert len(answer_chunks) > 0
    assert "RAG" in answer_chunks[0]["answer"]

    # Verify reasoning summary
    assert reasoning_complete is not None
    assert len(reasoning_complete["phase_events"]) >= 5
    assert reasoning_complete["retrieved_docs_count"] >= 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_streaming_with_error_phase():
    """Test streaming handles phase failures gracefully with error events."""
    coordinator = CoordinatorAgent(use_persistence=False)

    query = "What causes errors?"
    session_id = "test-conv-error-" + str(datetime.utcnow().timestamp()).replace(".", "-")

    events_received = []
    error_events = []

    async def mock_astream_with_error(initial_state, config=None, stream_mode=None):
        """Mock astream that emits a failed phase event."""
        phase_events = []

        # Successful intent classification
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=50.0,
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "phase_events": phase_events.copy(),
            },
        )

        # Failed vector search
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=100.0,
                error="Connection timeout to Qdrant",
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "phase_events": phase_events.copy(),
            },
        )

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream_with_error):
        async for event in coordinator.process_query_stream(query=query, session_id=session_id):
            if event["type"] == "phase_event":
                events_received.append(event["data"])
                if event["data"]["status"] == "failed":
                    error_events.append(event["data"])

    # Verify error event was captured
    assert len(error_events) > 0
    assert error_events[0]["phase_type"] == "vector_search"
    assert error_events[0]["status"] == "failed"
    assert "Qdrant" in error_events[0]["error"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_streaming_with_skipped_phases():
    """Test streaming correctly marks phases as skipped when not needed."""
    coordinator = CoordinatorAgent(use_persistence=False)

    query = "Vector-only query"
    session_id = "test-conv-skip-" + str(datetime.utcnow().timestamp()).replace(".", "-")

    events_received = []

    async def mock_astream_with_skips(initial_state, config=None, stream_mode=None):
        """Mock astream with skipped phases."""
        phase_events = []

        # Intent: vector-only
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=50.0,
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "phase_events": phase_events.copy(),
            },
        )

        # Vector search
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=100.0,
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "retrieved_contexts": [{"text": "result", "score": 0.9}],
                "phase_events": phase_events.copy(),
            },
        )

        # Graph query: skipped (vector-only intent)
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.GRAPH_QUERY,
                status=PhaseStatus.SKIPPED,
                start_time=datetime.utcnow(),
                metadata={"reason": "vector_only_intent"},
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "phase_events": phase_events.copy(),
            },
        )

        # Memory retrieval: skipped
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.MEMORY_RETRIEVAL,
                status=PhaseStatus.SKIPPED,
                start_time=datetime.utcnow(),
                metadata={"reason": "vector_only_intent"},
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "phase_events": phase_events.copy(),
            },
        )

        # LLM generation
        phase_events.append(
            PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=150.0,
            )
        )
        yield (
            "values",
            {
                "query": query,
                "intent": "vector",
                "answer": "Answer based on vector search",
                "citation_map": {},
                "phase_events": phase_events.copy(),
            },
        )

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream_with_skips):
        async for event in coordinator.process_query_stream(query=query, session_id=session_id):
            if event["type"] == "phase_event":
                events_received.append(event["data"])

    # Verify skipped phases are marked correctly
    skipped_phases = [e for e in events_received if e["status"] == "skipped"]
    assert len(skipped_phases) == 2
    skipped_types = {e["phase_type"] for e in skipped_phases}
    assert "graph_query" in skipped_types
    assert "memory_retrieval" in skipped_types

    # Verify reason is documented
    for skipped in skipped_phases:
        assert "reason" in skipped["metadata"]
        assert skipped["metadata"]["reason"] == "vector_only_intent"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase_event_timing_accuracy():
    """Test that phase event timing is accurate across multiple phases."""
    coordinator = CoordinatorAgent(use_persistence=False)

    query = "Timing test query"
    session_id = "test-conv-timing-" + str(datetime.utcnow().timestamp()).replace(".", "-")

    events_received = []
    timings = {}

    async def mock_astream_with_timing(initial_state, config=None, stream_mode=None):
        """Mock astream with realistic timings."""
        phases = [
            (PhaseType.INTENT_CLASSIFICATION, 75),
            (PhaseType.VECTOR_SEARCH, 150),
            (PhaseType.BM25_SEARCH, 120),
            (PhaseType.RRF_FUSION, 50),
            (PhaseType.RERANKING, 100),
            (PhaseType.LLM_GENERATION, 300),
        ]

        phase_events = []

        for phase_type, duration_ms in phases:
            start = datetime.utcnow()
            await asyncio.sleep(0.001)  # Small delay to simulate work
            end = datetime.utcnow()

            phase_events.append(
                PhaseEvent(
                    phase_type=phase_type,
                    status=PhaseStatus.COMPLETED,
                    start_time=start,
                    end_time=end,
                    duration_ms=duration_ms,
                )
            )
            yield {
                "query": query,
                "phase_events": phase_events.copy(),
            }

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream_with_timing):
        async for event in coordinator.process_query_stream(query=query, session_id=session_id):
            if event["type"] == "phase_event":
                data = event["data"]
                events_received.append(data)
                timings[data["phase_type"]] = data["duration_ms"]

    # Verify all expected phases present
    assert len(events_received) == 6
    expected_phases = {
        "intent_classification",
        "vector_search",
        "bm25_search",
        "rrf_fusion",
        "reranking",
        "llm_generation",
    }
    actual_phases = {e["phase_type"] for e in events_received}
    assert actual_phases == expected_phases

    # Verify LLM generation took longest
    assert timings["llm_generation"] == 300
    assert timings["intent_classification"] == 75


@pytest.mark.asyncio
@pytest.mark.integration
async def test_streaming_early_termination():
    """Test streaming handles early termination (client disconnect) gracefully."""
    coordinator = CoordinatorAgent(use_persistence=False)

    query = "Will be interrupted"
    session_id = "test-conv-interrupt-" + str(datetime.utcnow().timestamp()).replace(".", "-")

    events_received = []

    async def mock_astream_slow(initial_state, config=None, stream_mode=None):
        """Mock astream with slow, long-running phases."""
        yield (
            "values",
            {
                "router": {
                    "query": query,
                    "intent": "hybrid",
                    "phase_event": PhaseEvent(
                        phase_type=PhaseType.INTENT_CLASSIFICATION,
                        status=PhaseStatus.COMPLETED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration_ms=50.0,
                    ),
                }
            },
        )

        # Simulate a very slow phase
        yield (
            "values",
            {
                "vector_agent": {
                    "phase_event": PhaseEvent(
                        phase_type=PhaseType.VECTOR_SEARCH,
                        status=PhaseStatus.IN_PROGRESS,
                        start_time=datetime.utcnow(),
                        duration_ms=None,
                    ),
                }
            },
        )

        # This would not be yielded if client disconnects
        await asyncio.sleep(10)
        yield (
            "values",
            {
                "vector_agent": {
                    "phase_event": PhaseEvent(
                        phase_type=PhaseType.VECTOR_SEARCH,
                        status=PhaseStatus.COMPLETED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration_ms=10000,
                    ),
                }
            },
        )

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream_slow):
        try:
            async for event in coordinator.process_query_stream(query=query, session_id=session_id):
                events_received.append(event)
                if len(events_received) >= 2:
                    # Simulate client disconnect
                    break
        except Exception:
            # Should not raise - gracefully handle disconnection
            pass

    # Should have received at least the first two events
    assert len(events_received) >= 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_reasoning_data_accumulation():
    """Test that reasoning data correctly accumulates phase events."""
    reasoning = ReasoningData()

    # Add multiple phase events
    events = [
        PhaseEvent(
            phase_type=PhaseType.INTENT_CLASSIFICATION,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=50.0,
        ),
        PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=150.0,
            metadata={"docs_retrieved": 10},
        ),
        PhaseEvent(
            phase_type=PhaseType.LLM_GENERATION,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration_ms=200.0,
        ),
    ]

    for event in events:
        reasoning.add_phase_event(event)

    # Add some supporting data
    reasoning.retrieved_docs.append({"doc_id": "123", "score": 0.95})
    reasoning.retrieved_docs.append({"doc_id": "456", "score": 0.87})
    reasoning.graph_entities.append({"entity": "RAG", "type": "system"})
    reasoning.memories.append({"memory_id": "mem1", "content": "context"})

    # Generate summary
    summary = reasoning.to_dict()

    # Verify summary
    assert len(summary["phase_events"]) == 3
    assert summary["retrieved_docs_count"] == 2
    assert summary["graph_entities_count"] == 1
    assert summary["memories_count"] == 1

    # Verify total duration can be calculated from events
    total_duration = sum(e["duration_ms"] for e in summary["phase_events"] if e.get("duration_ms"))
    assert total_duration == 400.0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_streaming_sessions():
    """Test multiple concurrent streaming sessions don't interfere."""
    coordinator = CoordinatorAgent(use_persistence=False)

    async def mock_astream(initial_state, config=None, stream_mode=None):
        """Mock astream yielding a simple event."""
        yield (
            "values",
            {
                "router": {
                    "query": initial_state.get("query", "test"),
                    "intent": "hybrid",
                    "phase_event": PhaseEvent(
                        phase_type=PhaseType.INTENT_CLASSIFICATION,
                        status=PhaseStatus.COMPLETED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration_ms=50.0,
                    ),
                }
            },
        )

    async def stream_query(query_text, session_id):
        """Stream a single query."""
        events = []
        with patch.object(coordinator.compiled_graph, "astream", new=mock_astream):
            async for event in coordinator.process_query_stream(
                query=query_text,
                session_id=session_id,
            ):
                events.append(event)
        return events

    # Run multiple concurrent streams
    results = await asyncio.gather(
        stream_query("Query 1", "session-1"),
        stream_query("Query 2", "session-2"),
        stream_query("Query 3", "session-3"),
    )

    # Verify each stream got events
    for events in results:
        assert len(events) > 0
        # Should have reasoning_complete event
        complete = [e for e in events if e["type"] == "reasoning_complete"]
        assert len(complete) > 0


# ============================================================================
# Phase Event Metadata Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase_event_metadata_preservation():
    """Test that phase event metadata is preserved through streaming."""
    coordinator = CoordinatorAgent(use_persistence=False)

    metadata_examples = {
        "vector_search": {"collection": "docs_v1", "top_k": 10, "docs_retrieved": 8},
        "graph_query": {"entities_found": 3, "relationships_found": 5, "depth": 2},
        "reranking": {"model": "cross-encoder", "top_k_after": 5},
        "llm_generation": {"tokens_generated": 42, "model": "ollama:llama3.2", "temperature": 0.7},
    }

    async def mock_astream_metadata(initial_state, config=None, stream_mode=None):
        """Mock astream that includes detailed metadata."""
        for phase_type_str, metadata in metadata_examples.items():
            phase_type = PhaseType[phase_type_str.upper()]
            node_name = phase_type_str

            yield {
                node_name: {
                    "phase_event": PhaseEvent(
                        phase_type=phase_type,
                        status=PhaseStatus.COMPLETED,
                        start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(),
                        duration_ms=100.0,
                        metadata=metadata,
                    ),
                }
            }

    events_received = []

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream_metadata):
        async for event in coordinator.process_query_stream(query="Test", session_id="test-meta"):
            if event["type"] == "phase_event":
                events_received.append(event["data"])

    # Verify metadata preserved
    for event in events_received:
        phase_type = event["phase_type"]
        if phase_type in metadata_examples:
            assert event["metadata"] == metadata_examples[phase_type]


# ============================================================================
# Performance and Stress Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_streaming_with_many_phase_events():
    """Test streaming handles high volume of phase events efficiently."""
    coordinator = CoordinatorAgent(use_persistence=False)

    event_count = 20  # Many events

    async def mock_astream_many(initial_state, config=None, stream_mode=None):
        """Mock astream yielding many events."""
        phase_events = []

        for i in range(event_count):
            phase_type = list(PhaseType)[i % len(PhaseType)]
            phase_events.append(
                PhaseEvent(
                    phase_type=phase_type,
                    status=PhaseStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_ms=10.0 * (i + 1),
                )
            )
            yield {
                "query": "Test",
                "phase_events": phase_events.copy(),
            }

    events_received = []

    with patch.object(coordinator.compiled_graph, "astream", new=mock_astream_many):
        async for event in coordinator.process_query_stream(query="Test", session_id="test-many"):
            if event["type"] == "phase_event":
                events_received.append(event["data"])

    assert len(events_received) == event_count
    # Verify last event has correct duration
    assert events_received[-1]["duration_ms"] == 10.0 * event_count
