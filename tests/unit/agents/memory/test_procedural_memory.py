"""Unit Tests for Procedural Memory System.

Sprint 95 Feature 95.4: Procedural Memory System (4 SP)

Tests:
    - SkillExecutionTrace: Data model serialization
    - ProceduralMemoryStore: Trace recording and retrieval
    - PatternLearner: Pattern analysis and suggestions
    - Integration: Orchestrator integration

Coverage Target: >80%
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.memory.procedural_memory import (
    ExecutionPattern,
    PatternLearner,
    ProceduralMemoryStore,
    SkillExecutionTrace,
    create_procedural_memory,
    create_trace_from_orchestrator,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_trace() -> SkillExecutionTrace:
    """Create sample execution trace."""
    return SkillExecutionTrace(
        trace_id="trace_123",
        skill_name="web_search",
        inputs={"query": "quantum computing", "max_results": 10},
        outputs={"results": 8, "sources": ["arxiv", "nature"]},
        duration_ms=235.7,
        success=True,
        error=None,
        context_size=1500,
        timestamp="2026-01-15T10:30:00Z",
        metadata={"workflow_id": "wf_abc"},
    )


@pytest.fixture
def failed_trace() -> SkillExecutionTrace:
    """Create sample failed trace."""
    return SkillExecutionTrace(
        trace_id="trace_456",
        skill_name="web_search",
        inputs={"query": "invalid query"},
        outputs={},
        duration_ms=50.0,
        success=False,
        error="Timeout error",
        context_size=1000,
        timestamp="2026-01-15T11:00:00Z",
    )


@pytest.fixture
def mock_redis():
    """Mock Redis manager."""
    mock = AsyncMock()
    # Create a mock client object (not awaitable)
    mock_client = AsyncMock()
    mock_client.sadd = AsyncMock()
    mock_client.expire = AsyncMock()
    mock_client.smembers = AsyncMock(return_value=set())
    mock_client.delete = AsyncMock()
    mock.client = mock_client  # Not awaitable, just a property
    mock.store = AsyncMock(return_value=True)
    mock.retrieve = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=True)
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
def procedural_store(mock_redis):
    """Create ProceduralMemoryStore with mocked Redis."""
    return ProceduralMemoryStore(
        redis_manager=mock_redis,
        default_ttl_seconds=3600,
        namespace="test_procedural",
    )


# =============================================================================
# SkillExecutionTrace Tests
# =============================================================================


class TestSkillExecutionTrace:
    """Test SkillExecutionTrace data model."""

    def test_trace_creation(self, sample_trace):
        """Test trace creation with all fields."""
        assert sample_trace.trace_id == "trace_123"
        assert sample_trace.skill_name == "web_search"
        assert sample_trace.success is True
        assert sample_trace.duration_ms == 235.7
        assert sample_trace.context_size == 1500
        assert sample_trace.error is None

    def test_trace_to_dict(self, sample_trace):
        """Test trace serialization to dict."""
        data = sample_trace.to_dict()

        assert data["trace_id"] == "trace_123"
        assert data["skill_name"] == "web_search"
        assert data["success"] is True
        assert data["duration_ms"] == 235.7
        assert data["inputs"] == {"query": "quantum computing", "max_results": 10}
        assert data["outputs"] == {"results": 8, "sources": ["arxiv", "nature"]}
        assert data["metadata"] == {"workflow_id": "wf_abc"}

    def test_trace_from_dict(self, sample_trace):
        """Test trace deserialization from dict."""
        data = sample_trace.to_dict()
        reconstructed = SkillExecutionTrace.from_dict(data)

        assert reconstructed.trace_id == sample_trace.trace_id
        assert reconstructed.skill_name == sample_trace.skill_name
        assert reconstructed.success == sample_trace.success
        assert reconstructed.duration_ms == sample_trace.duration_ms
        assert reconstructed.inputs == sample_trace.inputs
        assert reconstructed.outputs == sample_trace.outputs

    def test_trace_default_timestamp(self):
        """Test trace auto-generates timestamp."""
        trace = SkillExecutionTrace(
            trace_id="test",
            skill_name="test_skill",
            inputs={},
            outputs={},
            duration_ms=100.0,
            success=True,
        )

        # Should have auto-generated timestamp
        assert trace.timestamp is not None
        assert isinstance(trace.timestamp, str)
        # Should be valid ISO format
        datetime.fromisoformat(trace.timestamp.replace("Z", "+00:00"))

    def test_failed_trace(self, failed_trace):
        """Test failed trace with error."""
        assert failed_trace.success is False
        assert failed_trace.error == "Timeout error"
        assert failed_trace.outputs == {}


# =============================================================================
# ProceduralMemoryStore Tests
# =============================================================================


class TestProceduralMemoryStore:
    """Test ProceduralMemoryStore functionality."""

    def test_store_initialization(self, procedural_store, mock_redis):
        """Test store initialization."""
        assert procedural_store._redis == mock_redis
        assert procedural_store._default_ttl == 3600
        assert procedural_store._namespace == "test_procedural"

    def test_build_trace_key(self, procedural_store):
        """Test trace key construction."""
        key = procedural_store._build_trace_key("trace_123", "web_search")
        assert key == "test_procedural:web_search:trace_123"

    def test_build_index_key_success(self, procedural_store):
        """Test success index key construction."""
        key = procedural_store._build_index_key("web_search", success=True)
        assert key == "test_procedural:success:web_search"

    def test_build_index_key_failure(self, procedural_store):
        """Test failure index key construction."""
        key = procedural_store._build_index_key("web_search", success=False)
        assert key == "test_procedural:failure:web_search"

    @pytest.mark.asyncio
    async def test_record_execution_success(self, procedural_store, sample_trace, mock_redis):
        """Test recording successful execution."""
        result = await procedural_store.record_execution(sample_trace)

        assert result is True
        mock_redis.store.assert_called_once()
        mock_redis.client.sadd.assert_called_once()
        mock_redis.client.expire.assert_called_once()

        # Verify stored data
        call_args = mock_redis.store.call_args
        assert call_args[1]["key"] == "test_procedural:web_search:trace_123"
        assert call_args[1]["ttl_seconds"] == 3600
        assert call_args[1]["namespace"] == ""

    @pytest.mark.asyncio
    async def test_record_execution_failure(self, procedural_store, failed_trace, mock_redis):
        """Test recording failed execution."""
        result = await procedural_store.record_execution(failed_trace)

        assert result is True

        # Verify added to failure index
        call_args = mock_redis.client.sadd.call_args
        assert "failure" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_record_execution_custom_ttl(self, procedural_store, sample_trace, mock_redis):
        """Test recording with custom TTL."""
        await procedural_store.record_execution(sample_trace, ttl_seconds=7200)

        # Verify custom TTL used
        call_args = mock_redis.store.call_args
        assert call_args[1]["ttl_seconds"] == 7200

    @pytest.mark.asyncio
    async def test_get_successful_patterns_empty(self, procedural_store, mock_redis):
        """Test getting patterns when none exist."""
        mock_redis.client.smembers = AsyncMock(return_value=set())

        patterns = await procedural_store.get_successful_patterns("web_search")

        assert patterns == []

    @pytest.mark.asyncio
    async def test_get_successful_patterns(self, procedural_store, sample_trace, mock_redis):
        """Test getting successful patterns."""
        # Mock index returning trace IDs
        mock_redis.client.smembers.return_value = {"trace_123", "trace_456"}

        # Mock retrieval returning serialized trace
        trace_data = sample_trace.to_dict()
        mock_redis.retrieve.return_value = trace_data

        patterns = await procedural_store.get_successful_patterns("web_search", limit=10)

        assert len(patterns) == 2
        assert all(isinstance(p, SkillExecutionTrace) for p in patterns)
        assert all(p.skill_name == "web_search" for p in patterns)

    @pytest.mark.asyncio
    async def test_get_successful_patterns_with_limit(self, procedural_store, mock_redis):
        """Test patterns respect limit."""
        # Return 5 trace IDs
        trace_ids = {f"trace_{i}" for i in range(5)}
        mock_redis.client.smembers = AsyncMock(return_value=trace_ids)
        mock_redis.retrieve = AsyncMock(return_value=None)

        patterns = await procedural_store.get_successful_patterns("web_search", limit=3)

        # Should retrieve only 3
        assert mock_redis.retrieve.call_count <= 3

    @pytest.mark.asyncio
    async def test_get_failure_patterns(self, procedural_store, failed_trace, mock_redis):
        """Test getting failure patterns."""
        mock_redis.client.smembers.return_value = {"trace_456"}
        mock_redis.retrieve.return_value = failed_trace.to_dict()

        patterns = await procedural_store.get_failure_patterns("web_search")

        assert len(patterns) == 1
        assert patterns[0].success is False
        assert patterns[0].error == "Timeout error"

    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, procedural_store, mock_redis):
        """Test metrics when no executions."""
        mock_redis.client.smembers = AsyncMock(return_value=set())

        metrics = await procedural_store.get_metrics("web_search")

        assert metrics["total_executions"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["avg_duration_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_get_metrics(self, procedural_store, sample_trace, failed_trace, mock_redis):
        """Test metrics calculation."""
        # Mock both success and failure traces
        success_trace = sample_trace.to_dict()
        fail_trace = failed_trace.to_dict()

        # Success index returns 2 traces
        # Failure index returns 1 trace
        async def mock_smembers(key):
            if "success" in key:
                return {"trace_1", "trace_2"}
            else:
                return {"trace_3"}

        mock_redis.client.smembers = AsyncMock(side_effect=mock_smembers)

        # Mock retrieve to return appropriate traces
        async def mock_retrieve(key, namespace, track_access):
            if "trace_1" in key or "trace_2" in key:
                return json.dumps(success_trace)
            else:
                return json.dumps(fail_trace)

        mock_redis.retrieve = AsyncMock(side_effect=mock_retrieve)

        metrics = await procedural_store.get_metrics("web_search")

        assert metrics["total_executions"] == 3
        assert metrics["successful_executions"] == 2
        assert metrics["failed_executions"] == 1
        assert metrics["success_rate"] == pytest.approx(2 / 3, rel=0.01)
        assert metrics["avg_duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_clear_history(self, procedural_store, mock_redis):
        """Test clearing execution history."""
        mock_redis.client.smembers = AsyncMock(
            side_effect=[{"trace_1", "trace_2"}, {"trace_3"}]
        )
        mock_redis.client.delete = AsyncMock()

        deleted = await procedural_store.clear_history("web_search")

        assert deleted == 3
        # Should delete all traces + 2 indexes
        assert mock_redis.delete.call_count == 3
        assert mock_redis.client.delete.call_count == 1

    @pytest.mark.asyncio
    async def test_aclose(self, procedural_store, mock_redis):
        """Test closing store."""
        await procedural_store.aclose()
        mock_redis.aclose.assert_called_once()


# =============================================================================
# PatternLearner Tests
# =============================================================================


class TestPatternLearner:
    """Test PatternLearner analysis."""

    def test_analyze_empty_traces(self):
        """Test analysis with no traces."""
        learner = PatternLearner()
        analysis = learner.analyze_traces([])

        assert analysis["total_traces"] == 0
        assert analysis["success_rate"] == 0.0
        assert analysis["avg_duration_ms"] == 0.0

    def test_analyze_successful_traces(self, sample_trace):
        """Test analysis of successful traces."""
        learner = PatternLearner()
        traces = [sample_trace] * 5

        analysis = learner.analyze_traces(traces)

        assert analysis["total_traces"] == 5
        assert analysis["success_rate"] == 1.0
        assert analysis["avg_duration_ms"] == 235.7
        assert analysis["common_errors"] == []

    def test_analyze_mixed_traces(self, sample_trace, failed_trace):
        """Test analysis with success and failures."""
        learner = PatternLearner()
        traces = [sample_trace, sample_trace, failed_trace]

        analysis = learner.analyze_traces(traces)

        assert analysis["total_traces"] == 3
        assert analysis["success_rate"] == pytest.approx(2 / 3, rel=0.01)
        assert len(analysis["common_errors"]) > 0

    def test_categorize_error_timeout(self):
        """Test timeout error categorization."""
        learner = PatternLearner()
        category = learner._categorize_error("Request timeout after 30s")
        assert category == "Timeout"

    def test_categorize_error_not_found(self):
        """Test not found error categorization."""
        learner = PatternLearner()
        category = learner._categorize_error("Resource not found (404)")
        assert category == "Not Found"

    def test_categorize_error_rate_limit(self):
        """Test rate limit error categorization."""
        learner = PatternLearner()
        category = learner._categorize_error("Rate limit exceeded (429)")
        assert category == "Rate Limit"

    def test_categorize_error_permission(self):
        """Test permission error categorization."""
        learner = PatternLearner()
        category = learner._categorize_error("Permission denied (403)")
        assert category == "Permission Denied"

    def test_categorize_error_other(self):
        """Test unknown error categorization."""
        learner = PatternLearner()
        category = learner._categorize_error("Some random error")
        assert category == "Other Error"

    def test_suggest_optimizations_empty(self):
        """Test suggestions with no traces."""
        learner = PatternLearner()
        suggestions = learner.suggest_optimizations("web_search", [])

        assert len(suggestions) == 1
        assert "No execution history" in suggestions[0]

    def test_suggest_optimizations_low_success_rate(self, failed_trace):
        """Test suggestions for low success rate."""
        learner = PatternLearner()
        traces = [failed_trace] * 5  # 0% success rate

        suggestions = learner.suggest_optimizations("web_search", traces)

        # Should suggest reviewing errors
        assert any("success rate" in s.lower() for s in suggestions)

    def test_suggest_optimizations_high_latency(self):
        """Test suggestions for high latency."""
        learner = PatternLearner()

        # Create traces with high duration
        high_latency_trace = SkillExecutionTrace(
            trace_id="trace_high",
            skill_name="web_search",
            inputs={},
            outputs={},
            duration_ms=1500.0,  # >1s
            success=True,
        )

        traces = [high_latency_trace] * 5

        suggestions = learner.suggest_optimizations("web_search", traces)

        # Should suggest caching or optimization
        assert any("latency" in s.lower() or "caching" in s.lower() for s in suggestions)

    def test_suggest_optimizations_timeout_errors(self):
        """Test suggestions for timeout errors."""
        learner = PatternLearner()

        timeout_trace = SkillExecutionTrace(
            trace_id="trace_timeout",
            skill_name="web_search",
            inputs={},
            outputs={},
            duration_ms=50.0,
            success=False,
            error="Timeout error",
        )

        traces = [timeout_trace] * 3  # 100% timeout rate

        suggestions = learner.suggest_optimizations("web_search", traces)

        # Should suggest increasing timeout
        assert any("timeout" in s.lower() for s in suggestions)


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Test integration with orchestrator."""

    def test_create_trace_from_orchestrator(self):
        """Test creating trace from orchestrator execution."""
        # Mock invocation
        invocation = MagicMock()
        invocation.action = "search"
        invocation.context_budget = 2000
        invocation.timeout = 30.0
        invocation.optional = False
        invocation.inputs = {"query": "test query"}

        result = {"results": 10}
        duration_ms = 250.0

        trace = create_trace_from_orchestrator(
            skill_name="web_search",
            invocation=invocation,
            result=result,
            duration_ms=duration_ms,
            success=True,
            error=None,
        )

        assert trace.skill_name == "web_search"
        assert trace.success is True
        assert trace.duration_ms == 250.0
        assert trace.inputs == {"query": "test query"}
        assert trace.outputs == {"results": 10}
        assert trace.metadata["action"] == "search"
        assert trace.metadata["context_budget"] == 2000

    def test_create_trace_from_orchestrator_failure(self):
        """Test creating trace for failed execution."""
        invocation = MagicMock()
        invocation.action = "search"
        invocation.context_budget = 1500
        invocation.timeout = 20.0
        invocation.optional = False
        invocation.inputs = {}

        trace = create_trace_from_orchestrator(
            skill_name="web_search",
            invocation=invocation,
            result={},
            duration_ms=100.0,
            success=False,
            error="Connection error",
        )

        assert trace.success is False
        assert trace.error == "Connection error"
        assert trace.outputs == {}


# =============================================================================
# Factory Function Tests
# =============================================================================


def test_create_procedural_memory():
    """Test factory function."""
    with patch("src.agents.memory.procedural_memory.RedisMemoryManager"):
        store = create_procedural_memory(
            default_ttl_seconds=7200,
            namespace="custom_namespace",
        )

        assert isinstance(store, ProceduralMemoryStore)
        assert store._default_ttl == 7200
        assert store._namespace == "custom_namespace"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in procedural memory."""

    @pytest.mark.asyncio
    async def test_record_execution_redis_error(self, procedural_store, sample_trace, mock_redis):
        """Test recording fails gracefully on Redis error."""
        from src.core.exceptions import MemoryError

        mock_redis.store = AsyncMock(side_effect=Exception("Redis connection lost"))

        with pytest.raises(MemoryError):
            await procedural_store.record_execution(sample_trace)

    @pytest.mark.asyncio
    async def test_get_patterns_redis_error(self, procedural_store, mock_redis):
        """Test pattern retrieval fails gracefully."""
        mock_redis.client.smembers = AsyncMock(side_effect=Exception("Redis error"))

        # Should return empty list on error
        patterns = await procedural_store.get_successful_patterns("web_search")
        assert patterns == []

    @pytest.mark.asyncio
    async def test_get_optimization_suggestions_error(self, procedural_store, mock_redis):
        """Test suggestions fail gracefully."""
        mock_redis.client.smembers.side_effect = Exception("Redis error")

        # Should return empty list on error (from get_successful_patterns failing)
        suggestions = await procedural_store.get_optimization_suggestions("web_search")
        # Returns "No execution history" message when no traces found
        assert len(suggestions) == 1
        assert "No execution history" in suggestions[0]


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_batch_record_execution(self, procedural_store, mock_redis):
        """Test recording multiple traces."""
        mock_redis.client.sadd = AsyncMock()
        mock_redis.client.expire = AsyncMock()

        traces = [
            SkillExecutionTrace(
                trace_id=f"trace_{i}",
                skill_name="web_search",
                inputs={},
                outputs={},
                duration_ms=100.0,
                success=True,
            )
            for i in range(10)
        ]

        for trace in traces:
            result = await procedural_store.record_execution(trace)
            assert result is True

        # Should have called store 10 times
        assert mock_redis.store.call_count == 10

    @pytest.mark.asyncio
    async def test_get_patterns_large_dataset(self, procedural_store, sample_trace, mock_redis):
        """Test retrieving patterns with large dataset."""
        # Mock 100 trace IDs
        trace_ids = {f"trace_{i}" for i in range(100)}
        mock_redis.client.smembers = AsyncMock(return_value=trace_ids)
        mock_redis.retrieve = AsyncMock(return_value=json.dumps(sample_trace.to_dict()))

        # Request with limit
        patterns = await procedural_store.get_successful_patterns("web_search", limit=20)

        # Should respect limit
        assert len(patterns) <= 20
