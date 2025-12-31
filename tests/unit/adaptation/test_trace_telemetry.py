"""Unit tests for UnifiedTracer and TraceEvent.

Sprint 67 Feature 67.5: Unified Trace & Telemetry (8 SP)

Test Coverage:
    - TraceEvent serialization/deserialization
    - UnifiedTracer event logging (JSONL format)
    - Metrics aggregation (avg, p95, cache hit rate)
    - Time-range filtering
    - Stage-specific filtering
    - Event retrieval with limits
    - Error handling (malformed JSON, I/O errors)
    - Performance benchmarks (<5ms logging overhead)
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.adaptation.trace_telemetry import PipelineStage, TraceEvent, UnifiedTracer


class TestPipelineStage:
    """Test PipelineStage enum."""

    def test_stage_values(self):
        """Test all stage enum values."""
        assert PipelineStage.INTENT_CLASSIFICATION.value == "intent_classification"
        assert PipelineStage.QUERY_REWRITING.value == "query_rewriting"
        assert PipelineStage.RETRIEVAL.value == "retrieval"
        assert PipelineStage.RERANKING.value == "reranking"
        assert PipelineStage.GENERATION.value == "generation"
        assert PipelineStage.MEMORY_RETRIEVAL.value == "memory_retrieval"
        assert PipelineStage.GRAPH_TRAVERSAL.value == "graph_traversal"
        assert PipelineStage.CACHE_LOOKUP.value == "cache_lookup"

    def test_stage_from_string(self):
        """Test creating stage from string value."""
        stage = PipelineStage("retrieval")
        assert stage == PipelineStage.RETRIEVAL


class TestTraceEvent:
    """Test TraceEvent dataclass."""

    def test_trace_event_creation(self):
        """Test creating TraceEvent with required fields."""
        now = datetime.now()
        event = TraceEvent(
            timestamp=now,
            stage=PipelineStage.RETRIEVAL,
            latency_ms=180.5,
        )

        assert event.timestamp == now
        assert event.stage == PipelineStage.RETRIEVAL
        assert event.latency_ms == 180.5
        assert event.tokens_used is None
        assert event.cache_hit is None
        assert event.metadata == {}
        assert event.request_id is None
        assert event.user_id is None

    def test_trace_event_with_all_fields(self):
        """Test creating TraceEvent with all optional fields."""
        now = datetime.now()
        metadata = {"query": "test", "top_k": 10}
        event = TraceEvent(
            timestamp=now,
            stage=PipelineStage.GENERATION,
            latency_ms=450.0,
            tokens_used=250,
            cache_hit=True,
            metadata=metadata,
            request_id="req_123",
            user_id="user_456",
        )

        assert event.timestamp == now
        assert event.stage == PipelineStage.GENERATION
        assert event.latency_ms == 450.0
        assert event.tokens_used == 250
        assert event.cache_hit is True
        assert event.metadata == metadata
        assert event.request_id == "req_123"
        assert event.user_id == "user_456"


class TestUnifiedTracer:
    """Test UnifiedTracer class."""

    @pytest.fixture
    def temp_trace_file(self):
        """Create temporary trace file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            trace_path = Path(f.name)
        yield trace_path
        # Cleanup
        if trace_path.exists():
            trace_path.unlink()

    @pytest.fixture
    def tracer(self, temp_trace_file):
        """Create UnifiedTracer instance."""
        return UnifiedTracer(log_path=str(temp_trace_file))

    def test_tracer_initialization(self, tracer, temp_trace_file):
        """Test tracer initialization."""
        assert tracer.log_path == temp_trace_file
        assert temp_trace_file.parent.exists()

    def test_tracer_creates_directories(self):
        """Test tracer creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "subdir1" / "subdir2" / "traces.jsonl"
            tracer = UnifiedTracer(log_path=str(log_path))
            assert log_path.parent.exists()

    @pytest.mark.asyncio
    async def test_log_event(self, tracer, temp_trace_file):
        """Test logging a single event."""
        now = datetime.now()
        event = TraceEvent(
            timestamp=now,
            stage=PipelineStage.RETRIEVAL,
            latency_ms=180.5,
            metadata={"top_k": 10},
        )

        await tracer.log_event(event)

        # Verify event was written
        assert temp_trace_file.exists()
        content = temp_trace_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 1

        # Parse and verify
        logged_event = json.loads(lines[0])
        assert logged_event["stage"] == "retrieval"
        assert logged_event["latency_ms"] == 180.5
        assert logged_event["metadata"]["top_k"] == 10
        # Timestamp should be ISO format
        assert datetime.fromisoformat(logged_event["timestamp"])

    @pytest.mark.asyncio
    async def test_log_multiple_events(self, tracer, temp_trace_file):
        """Test logging multiple events (JSONL format)."""
        events = [
            TraceEvent(
                timestamp=datetime.now(),
                stage=PipelineStage.INTENT_CLASSIFICATION,
                latency_ms=45.2,
            ),
            TraceEvent(
                timestamp=datetime.now(),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=180.5,
            ),
            TraceEvent(
                timestamp=datetime.now(),
                stage=PipelineStage.GENERATION,
                latency_ms=320.0,
                tokens_used=250,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        # Verify all events written
        content = temp_trace_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3

        # Verify each line is valid JSON
        for line in lines:
            event_dict = json.loads(line)
            assert "stage" in event_dict
            assert "latency_ms" in event_dict
            assert "timestamp" in event_dict

    @pytest.mark.asyncio
    async def test_get_metrics_empty_file(self, tracer):
        """Test get_metrics with no events."""
        now = datetime.now()
        metrics = await tracer.get_metrics((now - timedelta(hours=1), now))

        assert metrics["total_events"] == 0
        assert metrics["avg_latency_ms"] == 0.0
        assert metrics["p95_latency_ms"] == 0.0
        assert metrics["total_tokens"] == 0
        assert metrics["cache_hit_rate"] == 0.0
        assert metrics["stage_breakdown"] == {}

    @pytest.mark.asyncio
    async def test_get_metrics_single_event(self, tracer):
        """Test get_metrics with single event."""
        now = datetime.now()
        event = TraceEvent(
            timestamp=now,
            stage=PipelineStage.RETRIEVAL,
            latency_ms=180.5,
            cache_hit=True,
        )
        await tracer.log_event(event)

        metrics = await tracer.get_metrics((now - timedelta(hours=1), now + timedelta(hours=1)))

        assert metrics["total_events"] == 1
        assert metrics["avg_latency_ms"] == 180.5
        assert metrics["p95_latency_ms"] == 180.5
        assert metrics["cache_hit_rate"] == 1.0
        assert "retrieval" in metrics["stage_breakdown"]
        assert metrics["stage_breakdown"]["retrieval"]["count"] == 1

    @pytest.mark.asyncio
    async def test_get_metrics_multiple_events(self, tracer):
        """Test get_metrics with multiple events."""
        now = datetime.now()
        events = [
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0,
                cache_hit=True,
            ),
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=200.0,
                cache_hit=False,
            ),
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.GENERATION,
                latency_ms=300.0,
                tokens_used=250,
            ),
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.GENERATION,
                latency_ms=400.0,
                tokens_used=300,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        metrics = await tracer.get_metrics((now - timedelta(hours=1), now + timedelta(hours=1)))

        assert metrics["total_events"] == 4
        # Average: (100 + 200 + 300 + 400) / 4 = 250
        assert metrics["avg_latency_ms"] == 250.0
        # P95: 400 (95th percentile of sorted [100, 200, 300, 400])
        assert metrics["p95_latency_ms"] == 400.0
        # Total tokens: 250 + 300 = 550
        assert metrics["total_tokens"] == 550
        # Cache hit rate: 1/2 = 0.5 (only retrieval events have cache_hit)
        assert metrics["cache_hit_rate"] == 0.5

        # Stage breakdown
        assert "retrieval" in metrics["stage_breakdown"]
        assert metrics["stage_breakdown"]["retrieval"]["count"] == 2
        assert metrics["stage_breakdown"]["retrieval"]["avg_latency_ms"] == 150.0

        assert "generation" in metrics["stage_breakdown"]
        assert metrics["stage_breakdown"]["generation"]["count"] == 2
        assert metrics["stage_breakdown"]["generation"]["avg_latency_ms"] == 350.0
        assert metrics["stage_breakdown"]["generation"]["avg_tokens"] == 275.0

    @pytest.mark.asyncio
    async def test_get_metrics_time_range_filter(self, tracer):
        """Test get_metrics with time range filtering."""
        base_time = datetime.now()
        events = [
            TraceEvent(
                timestamp=base_time - timedelta(hours=2),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0,
            ),
            TraceEvent(
                timestamp=base_time - timedelta(minutes=30),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=200.0,
            ),
            TraceEvent(
                timestamp=base_time,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=300.0,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        # Query last hour (should get 2 events)
        metrics = await tracer.get_metrics(
            (base_time - timedelta(hours=1), base_time + timedelta(minutes=1))
        )

        assert metrics["total_events"] == 2
        assert metrics["avg_latency_ms"] == 250.0  # (200 + 300) / 2

    @pytest.mark.asyncio
    async def test_get_events_no_filters(self, tracer):
        """Test get_events without filters."""
        now = datetime.now()
        events = [
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0,
            ),
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.GENERATION,
                latency_ms=200.0,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        retrieved = await tracer.get_events()

        assert len(retrieved) == 2
        assert retrieved[0].stage == PipelineStage.RETRIEVAL
        assert retrieved[1].stage == PipelineStage.GENERATION

    @pytest.mark.asyncio
    async def test_get_events_stage_filter(self, tracer):
        """Test get_events with stage filter."""
        now = datetime.now()
        events = [
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0,
            ),
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.GENERATION,
                latency_ms=200.0,
            ),
            TraceEvent(
                timestamp=now,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=150.0,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        # Filter by RETRIEVAL stage
        retrieved = await tracer.get_events(stage=PipelineStage.RETRIEVAL)

        assert len(retrieved) == 2
        assert all(e.stage == PipelineStage.RETRIEVAL for e in retrieved)

    @pytest.mark.asyncio
    async def test_get_events_time_range_filter(self, tracer):
        """Test get_events with time range filter."""
        base_time = datetime.now()
        events = [
            TraceEvent(
                timestamp=base_time - timedelta(hours=2),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0,
            ),
            TraceEvent(
                timestamp=base_time - timedelta(minutes=30),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=200.0,
            ),
            TraceEvent(
                timestamp=base_time,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=300.0,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        # Query last hour
        retrieved = await tracer.get_events(
            time_range=(base_time - timedelta(hours=1), base_time + timedelta(minutes=1))
        )

        assert len(retrieved) == 2
        assert retrieved[0].latency_ms == 200.0
        assert retrieved[1].latency_ms == 300.0

    @pytest.mark.asyncio
    async def test_get_events_limit(self, tracer):
        """Test get_events with limit."""
        now = datetime.now()
        events = [
            TraceEvent(timestamp=now, stage=PipelineStage.RETRIEVAL, latency_ms=100.0 + i)
            for i in range(10)
        ]

        for event in events:
            await tracer.log_event(event)

        # Limit to 5 events
        retrieved = await tracer.get_events(limit=5)

        assert len(retrieved) == 5

    @pytest.mark.asyncio
    async def test_get_events_combined_filters(self, tracer):
        """Test get_events with multiple filters."""
        base_time = datetime.now()
        events = [
            TraceEvent(
                timestamp=base_time - timedelta(minutes=30),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0,
            ),
            TraceEvent(
                timestamp=base_time - timedelta(minutes=20),
                stage=PipelineStage.GENERATION,
                latency_ms=200.0,
            ),
            TraceEvent(
                timestamp=base_time - timedelta(minutes=10),
                stage=PipelineStage.RETRIEVAL,
                latency_ms=150.0,
            ),
            TraceEvent(
                timestamp=base_time,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=175.0,
            ),
        ]

        for event in events:
            await tracer.log_event(event)

        # Filter by stage, time range, and limit
        retrieved = await tracer.get_events(
            time_range=(base_time - timedelta(hours=1), base_time + timedelta(minutes=1)),
            stage=PipelineStage.RETRIEVAL,
            limit=2,
        )

        assert len(retrieved) == 2
        assert all(e.stage == PipelineStage.RETRIEVAL for e in retrieved)

    @pytest.mark.asyncio
    async def test_log_event_error_handling(self, tracer, temp_trace_file):
        """Test error handling when logging fails."""
        # Make file read-only to trigger write error
        temp_trace_file.chmod(0o444)

        event = TraceEvent(
            timestamp=datetime.now(),
            stage=PipelineStage.RETRIEVAL,
            latency_ms=100.0,
        )

        # Should not raise exception (logs error instead)
        await tracer.log_event(event)

        # Restore permissions for cleanup
        temp_trace_file.chmod(0o644)

    @pytest.mark.asyncio
    async def test_get_metrics_malformed_json(self, tracer, temp_trace_file):
        """Test get_metrics handles malformed JSON gracefully."""
        # Write malformed JSON
        temp_trace_file.write_text("not valid json\n")

        now = datetime.now()
        metrics = await tracer.get_metrics((now - timedelta(hours=1), now))

        # Should return empty metrics
        assert metrics["total_events"] == 0

    @pytest.mark.asyncio
    async def test_get_metrics_missing_fields(self, tracer, temp_trace_file):
        """Test get_metrics handles events with missing fields."""
        # Write event with missing latency_ms
        malformed_event = {
            "timestamp": datetime.now().isoformat(),
            "stage": "retrieval",
            # Missing latency_ms
        }
        temp_trace_file.write_text(json.dumps(malformed_event) + "\n")

        now = datetime.now()
        metrics = await tracer.get_metrics((now - timedelta(hours=1), now + timedelta(hours=1)))

        # Should skip malformed event
        assert metrics["total_events"] == 0

    @pytest.mark.asyncio
    async def test_event_logging_preserves_metadata(self, tracer):
        """Test that metadata is preserved during logging."""
        now = datetime.now()
        metadata = {
            "query": "test query",
            "top_k": 10,
            "vector_score": 0.89,
            "bm25_score": 0.72,
            "rrf_weights": {"vector": 0.2, "bm25": 0.1},
        }

        event = TraceEvent(
            timestamp=now,
            stage=PipelineStage.RETRIEVAL,
            latency_ms=180.5,
            metadata=metadata,
        )

        await tracer.log_event(event)

        # Retrieve and verify metadata
        events = await tracer.get_events()
        assert len(events) == 1
        assert events[0].metadata == metadata

    @pytest.mark.asyncio
    async def test_concurrent_event_logging(self, tracer):
        """Test thread-safe concurrent event logging."""
        import asyncio

        now = datetime.now()

        # Create 10 concurrent logging tasks
        async def log_task(i: int):
            event = TraceEvent(
                timestamp=now,
                stage=PipelineStage.RETRIEVAL,
                latency_ms=100.0 + i,
                request_id=f"req_{i}",
            )
            await tracer.log_event(event)

        # Run concurrently
        await asyncio.gather(*[log_task(i) for i in range(10)])

        # Verify all events logged
        events = await tracer.get_events()
        assert len(events) == 10
        # Verify unique request IDs
        request_ids = {e.request_id for e in events}
        assert len(request_ids) == 10


class TestPerformance:
    """Performance tests for UnifiedTracer."""

    @pytest.mark.asyncio
    async def test_logging_latency_overhead(self):
        """Test logging latency is <5ms per event (P95)."""
        import time

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            trace_path = Path(f.name)

        try:
            tracer = UnifiedTracer(log_path=str(trace_path))

            latencies = []
            for i in range(100):
                event = TraceEvent(
                    timestamp=datetime.now(),
                    stage=PipelineStage.RETRIEVAL,
                    latency_ms=100.0 + i,
                )

                start = time.perf_counter()
                await tracer.log_event(event)
                latency_ms = (time.perf_counter() - start) * 1000
                latencies.append(latency_ms)

            # Compute P95
            latencies_sorted = sorted(latencies)
            p95_index = int(len(latencies_sorted) * 0.95)
            p95_latency = latencies_sorted[p95_index]

            # Assert P95 <5ms (relaxed to 10ms for CI environments)
            assert p95_latency < 10.0, f"P95 logging latency {p95_latency:.2f}ms > 10ms"

        finally:
            if trace_path.exists():
                trace_path.unlink()

    @pytest.mark.asyncio
    async def test_metrics_aggregation_performance(self):
        """Test metrics aggregation is <500ms for 1k events."""
        import time

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            trace_path = Path(f.name)

        try:
            tracer = UnifiedTracer(log_path=str(trace_path))

            # Log 1000 events
            now = datetime.now()
            for i in range(1000):
                event = TraceEvent(
                    timestamp=now,
                    stage=PipelineStage.RETRIEVAL,
                    latency_ms=100.0 + (i % 100),
                )
                await tracer.log_event(event)

            # Measure aggregation time
            start = time.perf_counter()
            metrics = await tracer.get_metrics((now - timedelta(hours=1), now + timedelta(hours=1)))
            aggregation_ms = (time.perf_counter() - start) * 1000

            assert metrics["total_events"] == 1000
            # Assert aggregation <500ms (relaxed to 1000ms for CI)
            assert aggregation_ms < 1000.0, f"Aggregation time {aggregation_ms:.2f}ms > 1000ms"

        finally:
            if trace_path.exists():
                trace_path.unlink()
