"""
Unit tests for Trace Storage.

Tests cover:
- In-memory storage save/get/delete operations
- Query filtering by time and skill
- Count operations
- Edge cases and error handling
"""

from datetime import datetime, timedelta

import pytest

from src.governance.explainability.engine import (
    DecisionTrace,
    SkillSelectionReason,
    SourceAttribution,
)
from src.governance.explainability.storage import (
    InMemoryTraceStorage,
    RedisTraceStorage,
)


@pytest.fixture
def storage():
    """Provide clean in-memory storage."""
    return InMemoryTraceStorage()


@pytest.fixture
def sample_trace():
    """Provide a sample decision trace."""
    return DecisionTrace(
        id="trace_001",
        timestamp=datetime.now(),
        query="What are the transparency requirements?",
        final_response="The transparency requirements include...",
        skills_considered=[
            SkillSelectionReason(
                skill_name="research_agent",
                confidence=0.85,
                trigger_matched="find information",
            )
        ],
        skills_activated=["research_agent"],
        retrieval_mode="hybrid",
        chunks_retrieved=10,
        chunks_used=5,
        attributions=[
            SourceAttribution(
                document_id="doc_123",
                document_name="Test Document",
                chunk_ids=["chunk_1"],
                relevance_score=0.9,
                text_excerpt="Sample text...",
            )
        ],
        tools_invoked=[],
        overall_confidence=0.85,
        hallucination_risk=0.1,
        total_duration_ms=200.0,
    )


# === Basic Operations Tests ===


@pytest.mark.asyncio
async def test_save_and_get_trace(storage, sample_trace):
    """Test saving and retrieving a trace."""
    await storage.save(sample_trace)

    retrieved = await storage.get(sample_trace.id)

    assert retrieved is not None
    assert retrieved.id == sample_trace.id
    assert retrieved.query == sample_trace.query
    assert retrieved.final_response == sample_trace.final_response


@pytest.mark.asyncio
async def test_get_nonexistent_trace(storage):
    """Test retrieving a nonexistent trace returns None."""
    retrieved = await storage.get("nonexistent_id")
    assert retrieved is None


@pytest.mark.asyncio
async def test_save_multiple_traces(storage):
    """Test saving multiple traces."""
    traces = [
        DecisionTrace(
            id=f"trace_{i}",
            timestamp=datetime.now(),
            query=f"Query {i}",
            final_response=f"Response {i}",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        )
        for i in range(5)
    ]

    for trace in traces:
        await storage.save(trace)

    # Verify all traces are retrievable
    for trace in traces:
        retrieved = await storage.get(trace.id)
        assert retrieved is not None
        assert retrieved.id == trace.id


@pytest.mark.asyncio
async def test_delete_trace(storage, sample_trace):
    """Test deleting a trace."""
    await storage.save(sample_trace)

    # Verify trace exists
    assert await storage.get(sample_trace.id) is not None

    # Delete trace
    result = await storage.delete(sample_trace.id)
    assert result is True

    # Verify trace is gone
    assert await storage.get(sample_trace.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_trace(storage):
    """Test deleting a nonexistent trace returns False."""
    result = await storage.delete("nonexistent_id")
    assert result is False


# === Query Tests ===


@pytest.mark.asyncio
async def test_query_all_traces(storage):
    """Test querying all traces."""
    traces = [
        DecisionTrace(
            id=f"trace_{i}",
            timestamp=datetime.now(),
            query=f"Query {i}",
            final_response=f"Response {i}",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        )
        for i in range(5)
    ]

    for trace in traces:
        await storage.save(trace)

    results = await storage.query()

    assert len(results) == 5


@pytest.mark.asyncio
async def test_query_by_time_range(storage):
    """Test querying traces by time range."""
    now = datetime.now()

    # Create traces at different times
    traces = [
        DecisionTrace(
            id="trace_1",
            timestamp=now - timedelta(hours=2),
            query="Old query",
            final_response="Old response",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_2",
            timestamp=now - timedelta(hours=1),
            query="Recent query",
            final_response="Recent response",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_3",
            timestamp=now,
            query="Current query",
            final_response="Current response",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
    ]

    for trace in traces:
        await storage.save(trace)

    # Query for traces in the last 90 minutes
    results = await storage.query(start_time=now - timedelta(minutes=90))

    assert len(results) == 2
    assert results[0].id == "trace_3"  # Sorted newest first
    assert results[1].id == "trace_2"


@pytest.mark.asyncio
async def test_query_by_skill_name(storage):
    """Test querying traces by skill name."""
    traces = [
        DecisionTrace(
            id="trace_1",
            timestamp=datetime.now(),
            query="Query 1",
            final_response="Response 1",
            skills_considered=[],
            skills_activated=["research_agent"],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_2",
            timestamp=datetime.now(),
            query="Query 2",
            final_response="Response 2",
            skills_considered=[],
            skills_activated=["synthesis_agent"],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_3",
            timestamp=datetime.now(),
            query="Query 3",
            final_response="Response 3",
            skills_considered=[],
            skills_activated=["research_agent", "synthesis_agent"],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
    ]

    for trace in traces:
        await storage.save(trace)

    # Query for traces using research_agent
    results = await storage.query(skill_name="research_agent")

    assert len(results) == 2
    assert "trace_1" in [r.id for r in results]
    assert "trace_3" in [r.id for r in results]


@pytest.mark.asyncio
async def test_query_with_limit(storage):
    """Test query respects limit parameter."""
    traces = [
        DecisionTrace(
            id=f"trace_{i}",
            timestamp=datetime.now(),
            query=f"Query {i}",
            final_response=f"Response {i}",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        )
        for i in range(10)
    ]

    for trace in traces:
        await storage.save(trace)

    results = await storage.query(limit=5)

    assert len(results) == 5


@pytest.mark.asyncio
async def test_query_sorted_by_timestamp(storage):
    """Test query results are sorted by timestamp (newest first)."""
    now = datetime.now()

    traces = [
        DecisionTrace(
            id="trace_1",
            timestamp=now - timedelta(hours=2),
            query="Query 1",
            final_response="Response 1",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_2",
            timestamp=now,
            query="Query 2",
            final_response="Response 2",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_3",
            timestamp=now - timedelta(hours=1),
            query="Query 3",
            final_response="Response 3",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
    ]

    for trace in traces:
        await storage.save(trace)

    results = await storage.query()

    # Should be sorted newest first
    assert results[0].id == "trace_2"
    assert results[1].id == "trace_3"
    assert results[2].id == "trace_1"


# === Count Tests ===


@pytest.mark.asyncio
async def test_count_all_traces(storage):
    """Test counting all traces."""
    traces = [
        DecisionTrace(
            id=f"trace_{i}",
            timestamp=datetime.now(),
            query=f"Query {i}",
            final_response=f"Response {i}",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        )
        for i in range(7)
    ]

    for trace in traces:
        await storage.save(trace)

    count = await storage.count()
    assert count == 7


@pytest.mark.asyncio
async def test_count_by_time_range(storage):
    """Test counting traces by time range."""
    now = datetime.now()

    traces = [
        DecisionTrace(
            id="trace_1",
            timestamp=now - timedelta(hours=2),
            query="Query 1",
            final_response="Response 1",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_2",
            timestamp=now - timedelta(hours=1),
            query="Query 2",
            final_response="Response 2",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_3",
            timestamp=now,
            query="Query 3",
            final_response="Response 3",
            skills_considered=[],
            skills_activated=[],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
    ]

    for trace in traces:
        await storage.save(trace)

    # Count traces in the last 90 minutes
    count = await storage.count(start_time=now - timedelta(minutes=90))
    assert count == 2


@pytest.mark.asyncio
async def test_count_empty_storage(storage):
    """Test counting traces in empty storage."""
    count = await storage.count()
    assert count == 0


# === Clear Tests ===


@pytest.mark.asyncio
async def test_clear_storage(storage, sample_trace):
    """Test clearing all traces from storage."""
    await storage.save(sample_trace)
    assert await storage.get(sample_trace.id) is not None

    storage.clear()

    assert await storage.get(sample_trace.id) is None
    assert await storage.count() == 0


# === Redis Storage Tests ===


@pytest.mark.asyncio
async def test_redis_storage_not_implemented():
    """Test Redis storage raises NotImplementedError."""
    redis_storage = RedisTraceStorage(redis_client=None)

    with pytest.raises(NotImplementedError):
        await redis_storage.save(None)

    with pytest.raises(NotImplementedError):
        await redis_storage.get("trace_id")

    with pytest.raises(NotImplementedError):
        await redis_storage.query()

    with pytest.raises(NotImplementedError):
        await redis_storage.delete("trace_id")

    with pytest.raises(NotImplementedError):
        await redis_storage.count()


# === Edge Cases ===


@pytest.mark.asyncio
async def test_save_overwrites_existing_trace(storage, sample_trace):
    """Test saving a trace with same ID overwrites existing one."""
    await storage.save(sample_trace)

    # Modify and save again
    sample_trace.query = "Modified query"
    await storage.save(sample_trace)

    retrieved = await storage.get(sample_trace.id)
    assert retrieved.query == "Modified query"


@pytest.mark.asyncio
async def test_query_empty_storage(storage):
    """Test querying empty storage returns empty list."""
    results = await storage.query()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_query_combined_filters(storage):
    """Test query with combined time and skill filters."""
    now = datetime.now()

    traces = [
        DecisionTrace(
            id="trace_1",
            timestamp=now - timedelta(hours=2),
            query="Query 1",
            final_response="Response 1",
            skills_considered=[],
            skills_activated=["research_agent"],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_2",
            timestamp=now - timedelta(hours=1),
            query="Query 2",
            final_response="Response 2",
            skills_considered=[],
            skills_activated=["research_agent"],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
        DecisionTrace(
            id="trace_3",
            timestamp=now,
            query="Query 3",
            final_response="Response 3",
            skills_considered=[],
            skills_activated=["synthesis_agent"],
            retrieval_mode="vector",
            chunks_retrieved=0,
            chunks_used=0,
            attributions=[],
            tools_invoked=[],
            overall_confidence=0.5,
            hallucination_risk=0.0,
            total_duration_ms=100.0,
        ),
    ]

    for trace in traces:
        await storage.save(trace)

    # Query for research_agent traces in last 90 minutes
    results = await storage.query(
        start_time=now - timedelta(minutes=90), skill_name="research_agent"
    )

    assert len(results) == 1
    assert results[0].id == "trace_2"
