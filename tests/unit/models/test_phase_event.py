"""Unit tests for Phase Event Models.

Sprint 48 Feature 48.1: Phase Event Models & Types (5 SP)

These tests verify:
- PhaseType enum values and serialization
- PhaseStatus enum values and state transitions
- PhaseEvent model validation and serialization
- Datetime handling and duration calculations
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType


class TestPhaseType:
    """Tests for PhaseType enum."""

    def test_phase_type_values(self) -> None:
        """Test all PhaseType enum values are defined."""
        assert PhaseType.INTENT_CLASSIFICATION == "intent_classification"
        assert PhaseType.VECTOR_SEARCH == "vector_search"
        assert PhaseType.BM25_SEARCH == "bm25_search"
        assert PhaseType.RRF_FUSION == "rrf_fusion"
        assert PhaseType.RERANKING == "reranking"
        assert PhaseType.GRAPH_QUERY == "graph_query"
        assert PhaseType.MEMORY_RETRIEVAL == "memory_retrieval"
        assert PhaseType.LLM_GENERATION == "llm_generation"
        assert PhaseType.FOLLOW_UP_QUESTIONS == "follow_up_questions"

    def test_phase_type_string_conversion(self) -> None:
        """Test PhaseType can be converted to string."""
        assert str(PhaseType.VECTOR_SEARCH.value) == "vector_search"
        assert PhaseType.VECTOR_SEARCH.value == "vector_search"

    def test_phase_type_from_string(self) -> None:
        """Test PhaseType can be created from string."""
        phase = PhaseType("vector_search")
        assert phase == PhaseType.VECTOR_SEARCH

    def test_phase_type_invalid_value(self) -> None:
        """Test invalid PhaseType raises ValueError."""
        with pytest.raises(ValueError):
            PhaseType("invalid_phase")


class TestPhaseStatus:
    """Tests for PhaseStatus enum."""

    def test_phase_status_values(self) -> None:
        """Test all PhaseStatus enum values are defined."""
        assert PhaseStatus.PENDING == "pending"
        assert PhaseStatus.IN_PROGRESS == "in_progress"
        assert PhaseStatus.COMPLETED == "completed"
        assert PhaseStatus.FAILED == "failed"
        assert PhaseStatus.SKIPPED == "skipped"

    def test_phase_status_lifecycle(self) -> None:
        """Test typical phase status lifecycle transitions."""
        # Simulate lifecycle: PENDING → IN_PROGRESS → COMPLETED
        statuses = [
            PhaseStatus.PENDING,
            PhaseStatus.IN_PROGRESS,
            PhaseStatus.COMPLETED,
        ]
        assert len(statuses) == 3
        assert statuses[0] == PhaseStatus.PENDING
        assert statuses[-1] == PhaseStatus.COMPLETED

    def test_phase_status_from_string(self) -> None:
        """Test PhaseStatus can be created from string."""
        status = PhaseStatus("in_progress")
        assert status == PhaseStatus.IN_PROGRESS


class TestPhaseEvent:
    """Tests for PhaseEvent model."""

    def test_phase_event_minimal_creation(self) -> None:
        """Test creating PhaseEvent with minimal required fields."""
        start_time = datetime.now()
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.IN_PROGRESS,
            start_time=start_time,
        )

        assert event.phase_type == PhaseType.VECTOR_SEARCH
        assert event.status == PhaseStatus.IN_PROGRESS
        assert event.start_time == start_time
        assert event.end_time is None
        assert event.duration_ms is None
        assert event.metadata == {}
        assert event.error is None

    def test_phase_event_full_creation(self) -> None:
        """Test creating PhaseEvent with all fields."""
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        end_time = datetime(2025, 1, 1, 12, 0, 0, 150000)
        metadata = {"docs_retrieved": 10, "collection": "documents_v1"}

        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            duration_ms=150.0,
            metadata=metadata,
            error=None,
        )

        assert event.phase_type == PhaseType.VECTOR_SEARCH
        assert event.status == PhaseStatus.COMPLETED
        assert event.start_time == start_time
        assert event.end_time == end_time
        assert event.duration_ms == 150.0
        assert event.metadata == metadata
        assert event.error is None

    def test_phase_event_with_error(self) -> None:
        """Test creating PhaseEvent with error."""
        event = PhaseEvent(
            phase_type=PhaseType.GRAPH_QUERY,
            status=PhaseStatus.FAILED,
            start_time=datetime.now(),
            error="Neo4j connection timeout",
        )

        assert event.status == PhaseStatus.FAILED
        assert event.error == "Neo4j connection timeout"

    def test_phase_event_serialization(self) -> None:
        """Test PhaseEvent serialization to dictionary."""
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        end_time = datetime(2025, 1, 1, 12, 0, 0, 150000)

        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            duration_ms=150.0,
            metadata={"docs_retrieved": 10},
        )

        # Serialize using Pydantic v2 model_dump
        data = event.model_dump()

        assert data["phase_type"] == "vector_search"
        assert data["status"] == "completed"
        assert isinstance(data["start_time"], datetime)
        assert isinstance(data["end_time"], datetime)
        assert data["duration_ms"] == 150.0
        assert data["metadata"]["docs_retrieved"] == 10
        assert data["error"] is None

    def test_phase_event_deserialization(self) -> None:
        """Test PhaseEvent deserialization from dictionary."""
        data = {
            "phase_type": "vector_search",
            "status": "completed",
            "start_time": datetime(2025, 1, 1, 12, 0, 0),
            "end_time": datetime(2025, 1, 1, 12, 0, 0, 150000),
            "duration_ms": 150.0,
            "metadata": {"docs_retrieved": 10},
        }

        # Deserialize using Pydantic v2 model_validate
        event = PhaseEvent.model_validate(data)

        assert event.phase_type == PhaseType.VECTOR_SEARCH
        assert event.status == PhaseStatus.COMPLETED
        assert event.duration_ms == 150.0

    def test_phase_event_missing_required_fields(self) -> None:
        """Test PhaseEvent validation fails without required fields."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseEvent()  # type: ignore  # Intentionally invalid

        errors = exc_info.value.errors()
        # Should have errors for: phase_type, status, start_time
        assert len(errors) >= 3

    def test_phase_event_duration_calculation(self) -> None:
        """Test manual duration calculation matches expected value."""
        start_time = datetime(2025, 1, 1, 12, 0, 0)
        end_time = start_time + timedelta(milliseconds=150)

        event = PhaseEvent(
            phase_type=PhaseType.RERANKING,
            status=PhaseStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
        )

        # Calculate duration manually
        calculated_duration = (end_time - start_time).total_seconds() * 1000
        assert calculated_duration == pytest.approx(150.0, abs=1.0)

        # Set duration on event
        event.duration_ms = calculated_duration
        assert event.duration_ms == pytest.approx(150.0, abs=1.0)

    def test_phase_event_metadata_flexibility(self) -> None:
        """Test PhaseEvent metadata accepts arbitrary dict data."""
        metadata_cases = [
            {"docs_retrieved": 10},
            {"top_k": 5, "score_threshold": 0.7},
            {"llm_model": "nemotron-no-think", "tokens": 1024, "temperature": 0.7},
            {"entities": ["NVIDIA", "AMD"], "relations": ["COMPETES_WITH"]},
        ]

        for metadata in metadata_cases:
            event = PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
                metadata=metadata,
            )
            assert event.metadata == metadata

    def test_phase_event_skipped_phase(self) -> None:
        """Test PhaseEvent for skipped phase (e.g., graph query not needed)."""
        event = PhaseEvent(
            phase_type=PhaseType.GRAPH_QUERY,
            status=PhaseStatus.SKIPPED,
            start_time=datetime.now(),
            metadata={"reason": "vector_only_intent"},
        )

        assert event.status == PhaseStatus.SKIPPED
        assert event.metadata["reason"] == "vector_only_intent"
        assert event.end_time is None  # Skipped phases may not have end_time

    def test_phase_event_multiple_phases(self) -> None:
        """Test creating multiple PhaseEvents for a pipeline."""
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        events = []

        # Intent classification
        events.append(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=base_time,
                end_time=base_time + timedelta(milliseconds=50),
                duration_ms=50.0,
            )
        )

        # Vector search
        events.append(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=base_time + timedelta(milliseconds=50),
                end_time=base_time + timedelta(milliseconds=200),
                duration_ms=150.0,
            )
        )

        # LLM generation
        events.append(
            PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=base_time + timedelta(milliseconds=200),
                end_time=base_time + timedelta(milliseconds=700),
                duration_ms=500.0,
            )
        )

        assert len(events) == 3
        assert all(e.status == PhaseStatus.COMPLETED for e in events)
        total_duration = sum(e.duration_ms for e in events if e.duration_ms)
        assert total_duration == pytest.approx(700.0, abs=1.0)
