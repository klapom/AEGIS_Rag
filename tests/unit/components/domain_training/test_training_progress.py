"""Unit Tests for Training Progress Tracker.

Sprint 45 - Feature 45.5: Training Progress & Logging

This module tests the TrainingProgressTracker class for DSPy optimization
progress tracking and logging.

Test Coverage:
- Phase transitions and progress tracking
- Progress event emission and callbacks
- Sub-progress calculation within phases
- Training completion and failure handling
- Structured logging integration
- Event history management
"""

from datetime import datetime
from unittest.mock import Mock

from src.components.domain_training.training_progress import (
    ProgressEvent,
    TrainingPhase,
    TrainingProgressTracker,
)


class TestTrainingPhase:
    """Test TrainingPhase enum."""

    def test_phase_values(self):
        """Test phase enum values are correct."""
        assert TrainingPhase.INITIALIZING.value == "initializing"
        assert TrainingPhase.LOADING_DATA.value == "loading_data"
        assert TrainingPhase.ENTITY_OPTIMIZATION.value == "entity_optimization"
        assert TrainingPhase.RELATION_OPTIMIZATION.value == "relation_optimization"
        assert TrainingPhase.PROMPT_EXTRACTION.value == "prompt_extraction"
        assert TrainingPhase.VALIDATION.value == "validation"
        assert TrainingPhase.SAVING.value == "saving"
        assert TrainingPhase.COMPLETED.value == "completed"
        assert TrainingPhase.FAILED.value == "failed"

    def test_all_phases_have_weights(self):
        """Test all phases (except FAILED) have progress weights."""
        for phase in TrainingPhase:
            if phase != TrainingPhase.FAILED:
                assert phase in TrainingProgressTracker.PHASE_WEIGHTS


class TestProgressEvent:
    """Test ProgressEvent dataclass."""

    def test_progress_event_creation(self):
        """Test creating a progress event."""
        event = ProgressEvent(
            phase=TrainingPhase.ENTITY_OPTIMIZATION,
            progress_percent=25.5,
            message="Training in progress",
            timestamp=datetime.utcnow(),
            metrics={"loss": 0.5, "f1": 0.8},
        )

        assert event.phase == TrainingPhase.ENTITY_OPTIMIZATION
        assert event.progress_percent == 25.5
        assert event.message == "Training in progress"
        assert isinstance(event.timestamp, datetime)
        assert event.metrics == {"loss": 0.5, "f1": 0.8}

    def test_progress_event_without_metrics(self):
        """Test creating event without metrics."""
        event = ProgressEvent(
            phase=TrainingPhase.INITIALIZING,
            progress_percent=0.0,
            message="Starting",
            timestamp=datetime.utcnow(),
        )

        assert event.metrics is None


class TestTrainingProgressTracker:
    """Test TrainingProgressTracker class."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        assert tracker.training_run_id == "test-run-123"
        assert tracker.domain_name == "tech_docs"
        assert tracker.on_progress is None
        assert tracker._current_phase == TrainingPhase.INITIALIZING
        assert isinstance(tracker._start_time, datetime)
        assert len(tracker._events) == 0

    def test_initialization_with_callback(self):
        """Test tracker initialization with callback."""
        callback = Mock()
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        assert tracker.on_progress == callback

    def test_enter_phase(self):
        """Test entering a new phase."""
        callback = Mock()
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Starting entity training")

        # Check phase updated
        assert tracker._current_phase == TrainingPhase.ENTITY_OPTIMIZATION

        # Check event emitted
        assert len(tracker._events) == 1
        event = tracker._events[0]
        assert event.phase == TrainingPhase.ENTITY_OPTIMIZATION
        assert event.progress_percent == 10  # Start of ENTITY_OPTIMIZATION phase
        assert event.message == "Starting entity training"

        # Check callback invoked
        callback.assert_called_once()
        assert callback.call_args[0][0].phase == TrainingPhase.ENTITY_OPTIMIZATION

    def test_enter_phase_default_message(self):
        """Test entering phase with default message."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        tracker.enter_phase(TrainingPhase.LOADING_DATA)

        event = tracker._events[0]
        assert event.message == "Entering loading_data"

    def test_update_progress_within_phase(self):
        """Test updating progress within current phase."""
        callback = Mock()
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        # Enter entity optimization phase (10-45%)
        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION)
        callback.reset_mock()

        # Update to 50% within phase
        tracker.update_progress(0.5, "Epoch 5/10", {"loss": 0.3})

        # Check progress calculation: 10 + 0.5 * (45 - 10) = 27.5
        event = tracker._events[-1]
        assert event.phase == TrainingPhase.ENTITY_OPTIMIZATION
        assert event.progress_percent == 27.5
        assert event.message == "Epoch 5/10"
        assert event.metrics == {"loss": 0.3}

        callback.assert_called_once()

    def test_update_progress_boundary_values(self):
        """Test progress updates at boundaries (0, 1)."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION)

        # 0% within phase should be at start
        tracker.update_progress(0.0, "Start")
        assert tracker._events[-1].progress_percent == 10

        # 100% within phase should be at end
        tracker.update_progress(1.0, "End")
        assert tracker._events[-1].progress_percent == 45

    def test_complete(self):
        """Test marking training as completed."""
        callback = Mock()
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        metrics = {
            "entity_f1": 0.85,
            "relation_f1": 0.82,
            "training_samples": 100,
        }

        tracker.complete(metrics)

        # Check completion event
        event = tracker._events[-1]
        assert event.phase == TrainingPhase.COMPLETED
        assert event.progress_percent == 100
        assert event.message == "Training completed successfully"
        assert event.metrics == metrics

        callback.assert_called_once()

    def test_fail(self):
        """Test marking training as failed."""
        callback = Mock()
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        # Make some progress first
        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION)
        tracker.update_progress(0.3, "Training...")
        callback.reset_mock()

        last_progress = tracker._events[-1].progress_percent

        # Mark as failed
        tracker.fail("Out of memory error")

        # Check failure event
        event = tracker._events[-1]
        assert event.phase == TrainingPhase.FAILED
        assert event.progress_percent == last_progress  # Should retain last progress
        assert event.message == "Training failed: Out of memory error"

        callback.assert_called_once()

    def test_fail_without_prior_events(self):
        """Test marking as failed when no prior events exist."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        tracker.fail("Initialization error")

        event = tracker._events[-1]
        assert event.phase == TrainingPhase.FAILED
        assert event.progress_percent == 0  # Default when no prior events

    def test_events_property(self):
        """Test getting events property returns a copy."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        tracker.enter_phase(TrainingPhase.INITIALIZING)
        tracker.enter_phase(TrainingPhase.LOADING_DATA)

        events = tracker.events

        # Check it's a copy
        assert events is not tracker._events
        assert len(events) == 2

        # Modify copy shouldn't affect original
        events.clear()
        assert len(tracker._events) == 2

    def test_phase_weight_ranges(self):
        """Test phase weight ranges are sequential and cover 0-100."""
        weights = TrainingProgressTracker.PHASE_WEIGHTS
        phases = [
            TrainingPhase.INITIALIZING,
            TrainingPhase.LOADING_DATA,
            TrainingPhase.ENTITY_OPTIMIZATION,
            TrainingPhase.RELATION_OPTIMIZATION,
            TrainingPhase.PROMPT_EXTRACTION,
            TrainingPhase.VALIDATION,
            TrainingPhase.SAVING,
            TrainingPhase.COMPLETED,
        ]

        # Check first phase starts at 0
        assert weights[phases[0]][0] == 0

        # Check last phase ends at 100
        assert weights[phases[-1]][1] == 100

        # Check sequential coverage
        for i in range(len(phases) - 1):
            current_end = weights[phases[i]][1]
            next_start = weights[phases[i + 1]][0]
            assert current_end == next_start, f"Gap between {phases[i]} and {phases[i+1]}"

    def test_multiple_phase_transitions(self):
        """Test complete workflow with multiple phase transitions."""
        callback = Mock()
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        # Phase 1: INITIALIZING
        tracker.enter_phase(TrainingPhase.INITIALIZING, "Loading config")
        tracker.update_progress(0.8, "Config loaded")

        # Phase 2: LOADING_DATA
        tracker.enter_phase(TrainingPhase.LOADING_DATA, "Validating dataset")
        tracker.update_progress(0.5, "50% validated")

        # Phase 3: ENTITY_OPTIMIZATION
        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Training entities")
        tracker.update_progress(0.2, "Epoch 2/10")
        tracker.update_progress(0.8, "Epoch 8/10")

        # Phase 4: COMPLETED
        tracker.complete({"f1": 0.85})

        # Check event count
        assert len(tracker._events) == 8

        # Check callback was invoked for each event
        assert callback.call_count == 8

        # Check final event is completed
        assert tracker._events[-1].phase == TrainingPhase.COMPLETED
        assert tracker._events[-1].progress_percent == 100

    def test_callback_receives_correct_events(self):
        """Test callback receives correct event objects."""
        received_events = []

        def callback(event: ProgressEvent):
            received_events.append(event)

        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=callback,
        )

        tracker.enter_phase(TrainingPhase.INITIALIZING, "Starting")
        tracker.update_progress(0.5, "Progress", {"metric": 1})
        tracker.complete({"final": 2})

        assert len(received_events) == 3
        assert received_events[0].message == "Starting"
        assert received_events[1].message == "Progress"
        assert received_events[1].metrics == {"metric": 1}
        assert received_events[2].phase == TrainingPhase.COMPLETED
        assert received_events[2].metrics == {"final": 2}

    def test_progress_monotonicity(self):
        """Test progress percentages are monotonically increasing."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        phases = [
            TrainingPhase.INITIALIZING,
            TrainingPhase.LOADING_DATA,
            TrainingPhase.ENTITY_OPTIMIZATION,
            TrainingPhase.RELATION_OPTIMIZATION,
            TrainingPhase.PROMPT_EXTRACTION,
            TrainingPhase.VALIDATION,
            TrainingPhase.SAVING,
            TrainingPhase.COMPLETED,
        ]

        for phase in phases:
            tracker.enter_phase(phase)
            if phase != TrainingPhase.COMPLETED:
                tracker.update_progress(0.5, "Mid-phase")

        # Check progress is monotonically increasing
        for i in range(len(tracker._events) - 1):
            current_progress = tracker._events[i].progress_percent
            next_progress = tracker._events[i + 1].progress_percent
            assert (
                next_progress >= current_progress
            ), f"Progress decreased from {current_progress} to {next_progress}"

    def test_timestamp_progression(self):
        """Test event timestamps are in chronological order."""
        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
        )

        tracker.enter_phase(TrainingPhase.INITIALIZING)
        tracker.enter_phase(TrainingPhase.LOADING_DATA)
        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION)

        # Check timestamps are chronological
        for i in range(len(tracker._events) - 1):
            current_time = tracker._events[i].timestamp
            next_time = tracker._events[i + 1].timestamp
            assert next_time >= current_time, "Event timestamps are not chronological"


class TestTrainingProgressTrackerIntegration:
    """Integration tests for typical training workflows."""

    def test_successful_training_workflow(self):
        """Test complete successful training workflow."""
        events = []

        def track_progress(event: ProgressEvent):
            events.append(
                {
                    "phase": event.phase.value,
                    "progress": event.progress_percent,
                    "message": event.message,
                }
            )

        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=track_progress,
        )

        # Simulate training workflow
        tracker.enter_phase(TrainingPhase.INITIALIZING, "Loading domain config")
        tracker.update_progress(0.8, "Config loaded")

        tracker.enter_phase(TrainingPhase.LOADING_DATA, "Processing dataset")
        tracker.update_progress(0.8, "Dataset validated")

        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Optimizing entity extraction")
        tracker.update_progress(0.3, "Epoch 3/10")
        tracker.update_progress(0.7, "Epoch 7/10")

        tracker.enter_phase(TrainingPhase.RELATION_OPTIMIZATION, "Optimizing relation extraction")
        tracker.update_progress(0.5, "Epoch 5/10")

        tracker.enter_phase(TrainingPhase.PROMPT_EXTRACTION, "Extracting prompts")
        tracker.update_progress(0.8, "Prompts extracted")

        tracker.enter_phase(TrainingPhase.VALIDATION, "Validating metrics")
        tracker.update_progress(0.8, "Metrics validated")

        tracker.enter_phase(TrainingPhase.SAVING, "Saving to Neo4j")
        tracker.update_progress(0.8, "Saved successfully")

        tracker.complete({"entity_f1": 0.85, "relation_f1": 0.82})

        # Verify event sequence
        # 8 phase entries + 7 progress updates + 1 completion (complete creates its own entry)
        assert len(events) == 16
        assert events[0]["phase"] == "initializing"
        assert events[-1]["phase"] == "completed"
        assert events[-1]["progress"] == 100

    def test_failed_training_workflow(self):
        """Test training workflow that fails mid-way."""
        events = []

        def track_progress(event: ProgressEvent):
            events.append({"phase": event.phase.value, "message": event.message})

        tracker = TrainingProgressTracker(
            training_run_id="test-run-123",
            domain_name="tech_docs",
            on_progress=track_progress,
        )

        tracker.enter_phase(TrainingPhase.INITIALIZING, "Starting")
        tracker.enter_phase(TrainingPhase.LOADING_DATA, "Loading")
        tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Training")
        tracker.update_progress(0.2, "Epoch 2/10")

        # Simulate failure
        tracker.fail("CUDA out of memory")

        # Verify failure event
        assert events[-1]["phase"] == "failed"
        assert "CUDA out of memory" in events[-1]["message"]
