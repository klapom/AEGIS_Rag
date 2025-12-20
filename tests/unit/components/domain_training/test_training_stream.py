"""Unit tests for Training Event Stream.

Sprint 45 - Feature 45.13: Real-time Training Progress with SSE

Tests:
- TrainingEventStream initialization and singleton pattern
- Event creation and serialization (to_dict, to_json, to_sse)
- Stream lifecycle (start, emit, subscribe, close)
- JSONL file logging
- Error handling and edge cases
- Event queue management
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.domain_training.training_stream import (
    EventType,
    StreamState,
    TrainingEvent,
    TrainingEventStream,
    get_training_stream,
    reset_training_stream,
)


# ============================================================================
# TrainingEvent Tests
# ============================================================================


class TestTrainingEvent:
    """Test TrainingEvent dataclass and serialization."""

    def test_training_event_creation(self):
        """Test creating a TrainingEvent."""
        event = TrainingEvent(
            event_type=EventType.STARTED,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=0.0,
            phase="initializing",
            message="Training started",
        )

        assert event.event_type == EventType.STARTED
        assert event.training_run_id == "run-123"
        assert event.domain == "tech_docs"
        assert event.progress_percent == 0.0
        assert event.message == "Training started"

    def test_training_event_with_data(self):
        """Test TrainingEvent with additional data."""
        data = {"llm_model": "qwen3:32b", "sample_count": 100}
        event = TrainingEvent(
            event_type=EventType.PROGRESS_UPDATE,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=25.0,
            phase="loading_data",
            message="Dataset loaded",
            data=data,
        )

        assert event.data == data
        assert event.data["llm_model"] == "qwen3:32b"

    def test_training_event_to_dict(self):
        """Test converting TrainingEvent to dictionary."""
        event = TrainingEvent(
            event_type=EventType.STARTED,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=0.0,
            phase="initializing",
            message="Training started",
            data={"key": "value"},
        )

        result = event.to_dict()

        assert isinstance(result, dict)
        assert result["event_type"] == "started"
        assert result["training_run_id"] == "run-123"
        assert result["domain"] == "tech_docs"
        assert result["progress_percent"] == 0.0
        assert result["data"] == {"key": "value"}

    def test_training_event_to_json(self):
        """Test converting TrainingEvent to JSON."""
        event = TrainingEvent(
            event_type=EventType.PROGRESS_UPDATE,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=50.0,
            phase="entity_optimization",
            message="Entity optimization in progress",
        )

        json_str = event.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "progress_update"
        assert parsed["training_run_id"] == "run-123"
        assert parsed["progress_percent"] == 50.0

    def test_training_event_to_sse(self):
        """Test converting TrainingEvent to SSE format."""
        event = TrainingEvent(
            event_type=EventType.COMPLETED,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=100.0,
            phase="completed",
            message="Training completed",
        )

        sse_str = event.to_sse()

        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")
        # Extract JSON from SSE format
        json_part = sse_str[6:-2]  # Remove "data: " and "\n\n"
        parsed = json.loads(json_part)
        assert parsed["event_type"] == "completed"

    def test_training_event_with_unicode(self):
        """Test TrainingEvent handles Unicode characters."""
        event = TrainingEvent(
            event_type=EventType.PROGRESS_UPDATE,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=50.0,
            phase="entity_optimization",
            message="Processing document: Rechtesystem (German docs)",
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert "Rechtesystem" in parsed["message"]


# ============================================================================
# TrainingEventStream Singleton Tests
# ============================================================================


class TestTrainingEventStream:
    """Test TrainingEventStream singleton class."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_training_stream()

    def teardown_method(self):
        """Cleanup after each test."""
        reset_training_stream()

    def test_singleton_pattern(self):
        """Test TrainingEventStream is a singleton."""
        stream1 = get_training_stream()
        stream2 = get_training_stream()

        assert stream1 is stream2

    def test_event_stream_initialization(self):
        """Test TrainingEventStream initializes correctly."""
        stream = TrainingEventStream()

        assert hasattr(stream, "_streams")
        assert isinstance(stream._streams, dict)
        assert stream._initialized

    def test_start_stream(self):
        """Test starting a new training stream."""
        stream = get_training_stream()
        stream.start_stream(
            training_run_id="run-123",
            domain="tech_docs",
        )

        assert stream.is_active("run-123")
        assert "run-123" in stream._streams

    def test_start_stream_with_log_file(self):
        """Test starting stream with JSONL logging."""
        stream = get_training_stream()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "training.jsonl")
            stream.start_stream(
                training_run_id="run-123",
                domain="tech_docs",
                log_path=log_path,
            )

            state = stream._streams["run-123"]
            assert state.log_file is not None
            assert state.log_path == Path(log_path)

    def test_start_stream_creates_parent_directory(self):
        """Test starting stream creates parent directories."""
        stream = get_training_stream()

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = str(Path(tmpdir) / "logs" / "subdir" / "training.jsonl")
            stream.start_stream(
                training_run_id="run-123",
                domain="tech_docs",
                log_path=nested_path,
            )

            assert Path(nested_path).parent.exists()

    def test_start_stream_duplicate_warning(self):
        """Test starting stream twice logs warning."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        # Starting same stream again should be idempotent
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        # Stream should still exist
        assert stream.is_active("run-123")

    def test_emit_event_to_queue(self):
        """Test emitting event to stream."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        event = TrainingEvent(
            event_type=EventType.STARTED,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-123",
            domain="tech_docs",
            progress_percent=0.0,
            phase="initializing",
            message="Training started",
        )

        stream.emit_event("run-123", event)

        state = stream._streams["run-123"]
        assert state.event_count == 1

    def test_emit_event_to_nonexistent_stream(self):
        """Test emitting to non-existent stream logs warning."""
        stream = get_training_stream()

        event = TrainingEvent(
            event_type=EventType.STARTED,
            timestamp="2025-12-19T10:00:00",
            training_run_id="run-456",
            domain="tech_docs",
            progress_percent=0.0,
            phase="initializing",
            message="Training started",
        )

        # Should not raise, just log warning
        stream.emit_event("run-456", event)

    def test_emit_convenience_method(self):
        """Test emit convenience method."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        stream.emit(
            training_run_id="run-123",
            event_type=EventType.PROGRESS_UPDATE,
            domain="tech_docs",
            progress_percent=25.0,
            phase="loading_data",
            message="Processing samples",
            data={"count": 100},
        )

        state = stream._streams["run-123"]
        assert state.event_count == 1

    def test_event_count_increments(self):
        """Test event count increments correctly."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        # Emit multiple events
        for i in range(5):
            stream.emit(
                training_run_id="run-123",
                event_type=EventType.PROGRESS_UPDATE,
                domain="tech_docs",
                progress_percent=float(i * 20),
                phase="entity_optimization",
                message=f"Update {i}",
            )

        state = stream._streams["run-123"]
        assert state.event_count == 5

    def test_write_event_to_jsonl_file(self):
        """Test events are written to JSONL file."""
        stream = get_training_stream()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "training.jsonl")
            stream.start_stream(
                training_run_id="run-123",
                domain="tech_docs",
                log_path=log_path,
            )

            event = TrainingEvent(
                event_type=EventType.PROGRESS_UPDATE,
                timestamp="2025-12-19T10:00:00",
                training_run_id="run-123",
                domain="tech_docs",
                progress_percent=50.0,
                phase="entity_optimization",
                message="Optimization in progress",
            )

            stream.emit_event("run-123", event)
            stream.close_stream("run-123")

            # Verify JSONL file was written
            with open(log_path) as f:
                line = f.readline()
                parsed = json.loads(line)
                assert parsed["event_type"] == "progress_update"
                assert parsed["progress_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_subscribe_to_stream(self):
        """Test subscribing to stream events."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        # Create subscription task
        events_received = []

        async def collect_events():
            async for event in stream.subscribe("run-123"):
                events_received.append(event)

        # Start subscriber in background
        subscribe_task = asyncio.create_task(collect_events())

        # Emit some events
        await asyncio.sleep(0.1)  # Let subscriber start
        stream.emit(
            training_run_id="run-123",
            event_type=EventType.STARTED,
            domain="tech_docs",
            progress_percent=0.0,
            phase="initializing",
            message="Training started",
        )

        # Close stream to signal end
        await asyncio.sleep(0.1)
        stream.close_stream("run-123")

        # Wait for subscriber to finish
        await asyncio.wait_for(subscribe_task, timeout=1.0)

        # Verify events were received
        assert len(events_received) >= 1
        assert events_received[0].event_type == EventType.STARTED

    @pytest.mark.asyncio
    async def test_subscribe_to_nonexistent_stream(self):
        """Test subscribing to non-existent stream."""
        stream = get_training_stream()

        events = []
        async for event in stream.subscribe("run-456"):
            events.append(event)

        # Should yield nothing
        assert len(events) == 0

    def test_is_active(self):
        """Test checking if stream is active."""
        stream = get_training_stream()

        assert not stream.is_active("run-123")
        stream.start_stream(training_run_id="run-123", domain="tech_docs")
        assert stream.is_active("run-123")
        stream.close_stream("run-123")
        assert not stream.is_active("run-123")

    def test_close_stream(self):
        """Test closing a stream."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        assert stream.is_active("run-123")
        stream.close_stream("run-123")
        assert not stream.is_active("run-123")

    def test_close_stream_closes_log_file(self):
        """Test closing stream closes log file."""
        stream = get_training_stream()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = str(Path(tmpdir) / "training.jsonl")
            stream.start_stream(
                training_run_id="run-123",
                domain="tech_docs",
                log_path=log_path,
            )

            # Emit an event
            stream.emit(
                training_run_id="run-123",
                event_type=EventType.STARTED,
                domain="tech_docs",
                progress_percent=0.0,
                phase="initializing",
                message="Training started",
            )

            # Close stream
            stream.close_stream("run-123")

            # File should exist and be readable
            with open(log_path) as f:
                content = f.read()
                assert len(content) > 0

    def test_close_nonexistent_stream(self):
        """Test closing non-existent stream is safe."""
        stream = get_training_stream()
        # Should not raise
        stream.close_stream("run-456")

    def test_get_stats(self):
        """Test getting stream statistics."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        # Emit some events
        for i in range(3):
            stream.emit(
                training_run_id="run-123",
                event_type=EventType.PROGRESS_UPDATE,
                domain="tech_docs",
                progress_percent=float(i * 33),
                phase="entity_optimization",
                message=f"Update {i}",
            )

        stats = stream.get_stats("run-123")

        assert stats is not None
        assert stats["training_run_id"] == "run-123"
        assert stats["domain"] == "tech_docs"
        assert stats["event_count"] == 3

    def test_get_stats_nonexistent_stream(self):
        """Test getting stats for non-existent stream."""
        stream = get_training_stream()
        stats = stream.get_stats("run-456")

        assert stats is None

    def test_stream_state_initialization(self):
        """Test StreamState initialization."""
        queue = asyncio.Queue()
        state = StreamState(
            training_run_id="run-123",
            domain="tech_docs",
            log_path=None,
            queue=queue,
        )

        assert state.training_run_id == "run-123"
        assert state.domain == "tech_docs"
        assert state.event_count == 0
        assert state.log_file is None


# ============================================================================
# EventType Enum Tests
# ============================================================================


class TestEventType:
    """Test EventType enumeration."""

    def test_event_type_values(self):
        """Test EventType enum values."""
        assert EventType.STARTED.value == "started"
        assert EventType.PHASE_CHANGED.value == "phase_changed"
        assert EventType.PROGRESS_UPDATE.value == "progress_update"
        assert EventType.COMPLETED.value == "completed"
        assert EventType.FAILED.value == "failed"

    def test_event_type_llm_events(self):
        """Test LLM-related event types."""
        assert EventType.LLM_REQUEST.value == "llm_request"
        assert EventType.LLM_RESPONSE.value == "llm_response"

    def test_event_type_sample_events(self):
        """Test sample processing event types."""
        assert EventType.SAMPLE_PROCESSING.value == "sample_processing"
        assert EventType.SAMPLE_RESULT.value == "sample_result"

    def test_event_type_evaluation_events(self):
        """Test evaluation event types."""
        assert EventType.EVALUATION_START.value == "evaluation_start"
        assert EventType.EVALUATION_RESULT.value == "evaluation_result"


# ============================================================================
# Integration Tests
# ============================================================================


class TestTrainingEventStreamIntegration:
    """Integration tests for complete event streaming workflow."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_training_stream()

    def teardown_method(self):
        """Cleanup after each test."""
        reset_training_stream()

    def test_complete_training_event_flow(self):
        """Test complete training event flow."""
        stream = get_training_stream()
        stream.start_stream(training_run_id="run-123", domain="tech_docs")

        # Emit events simulating a training run
        events = [
            (EventType.STARTED, 0.0, "initializing", "Training started"),
            (EventType.PHASE_CHANGED, 5.0, "loading_data", "Loading dataset"),
            (EventType.PROGRESS_UPDATE, 25.0, "entity_optimization", "Entity optimization started"),
            (EventType.EVALUATION_RESULT, 45.0, "entity_optimization", "Entity F1: 0.85"),
            (EventType.PROGRESS_UPDATE, 50.0, "relation_optimization", "Relation optimization started"),
            (EventType.EVALUATION_RESULT, 80.0, "relation_optimization", "Relation F1: 0.82"),
            (EventType.PROGRESS_UPDATE, 90.0, "validation", "Validating metrics"),
            (EventType.COMPLETED, 100.0, "completed", "Training completed"),
        ]

        for event_type, progress, phase, message in events:
            stream.emit(
                training_run_id="run-123",
                event_type=event_type,
                domain="tech_docs",
                progress_percent=progress,
                phase=phase,
                message=message,
            )

        stats = stream.get_stats("run-123")
        assert stats["event_count"] == len(events)

    def test_multiple_concurrent_streams(self):
        """Test managing multiple concurrent training streams."""
        stream = get_training_stream()

        # Start multiple streams
        stream.start_stream(training_run_id="run-1", domain="tech_docs")
        stream.start_stream(training_run_id="run-2", domain="medical_docs")
        stream.start_stream(training_run_id="run-3", domain="legal_docs")

        assert stream.is_active("run-1")
        assert stream.is_active("run-2")
        assert stream.is_active("run-3")

        # Emit events to each stream
        stream.emit("run-1", EventType.STARTED, "tech_docs", 0.0, "init", "Start")
        stream.emit("run-2", EventType.STARTED, "medical_docs", 0.0, "init", "Start")
        stream.emit("run-3", EventType.STARTED, "legal_docs", 0.0, "init", "Start")

        # Verify independent streams
        assert stream.get_stats("run-1")["event_count"] == 1
        assert stream.get_stats("run-2")["event_count"] == 1
        assert stream.get_stats("run-3")["event_count"] == 1

        # Close one stream
        stream.close_stream("run-2")
        assert not stream.is_active("run-2")
        assert stream.is_active("run-1")
        assert stream.is_active("run-3")
