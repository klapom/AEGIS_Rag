"""Unit tests for Training Runner.

Sprint 45 - Feature 45.3, 45.5, 45.13: Domain Training API with Progress Tracking & SSE

Tests:
- run_dspy_optimization function with full pipeline
- Progress tracking through phases
- SSE event emission
- Error handling (ValueError, DatabaseConnectionError, generic exceptions)
- Task cancellation handling
- Neo4j persistence
- Progress callback invocation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.components.domain_training.training_progress import (
    ProgressEvent,
    TrainingPhase,
)
from src.components.domain_training.training_runner import run_dspy_optimization
from src.components.domain_training.training_stream import EventType


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_domain_repository():
    """Mock DomainRepository."""
    repo = AsyncMock()
    repo.get_domain = AsyncMock(
        return_value={
            "name": "tech_docs",
            "llm_model": "qwen3:32b",
            "entity_prompt": "Extract entities...",
            "relation_prompt": "Extract relations...",
        }
    )
    repo.update_training_log = AsyncMock()
    repo.update_domain_prompts = AsyncMock()
    return repo


@pytest.fixture
def mock_training_stream():
    """Mock TrainingEventStream."""
    stream = MagicMock()
    stream.start_stream = MagicMock()
    stream.emit = MagicMock()
    stream.close_stream = MagicMock()
    return stream


@pytest.fixture
def mock_dspy_optimizer():
    """Mock DSPyOptimizer."""
    optimizer = AsyncMock()
    optimizer.set_event_stream = MagicMock()
    optimizer.optimize_entity_extraction = AsyncMock(
        return_value={
            "instructions": "Extract entities",
            "demos": [{"input": {"source_text": "Sample"}, "output": {"entities": ["Entity1"]}}],
            "metrics": {"f1": 0.85, "precision": 0.88, "recall": 0.82},
        }
    )
    optimizer.optimize_relation_extraction = AsyncMock(
        return_value={
            "instructions": "Extract relations",
            "demos": [
                {
                    "input": {"source_text": "Sample", "entities": ["Entity1"]},
                    "output": {
                        "relations": [
                            {
                                "subject": "Entity1",
                                "predicate": "is_a",
                                "object": "Thing",
                            }
                        ]
                    },
                }
            ],
            "metrics": {"f1": 0.82, "precision": 0.85, "recall": 0.79},
        }
    )
    return optimizer


@pytest.fixture
def sample_training_dataset():
    """Sample training dataset."""
    return [
        {
            "text": "Python is a programming language.",
            "entities": ["Python"],
            "relations": [{"subject": "Python", "predicate": "is_a", "object": "language"}],
        },
        {
            "text": "FastAPI is a web framework for Python.",
            "entities": ["FastAPI", "Python"],
            "relations": [
                {"subject": "FastAPI", "predicate": "built_with", "object": "Python"}
            ],
        },
    ]


# ============================================================================
# Test: Happy Path
# ============================================================================


@pytest.mark.asyncio
async def test_run_dspy_optimization_success(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test successful DSPy optimization run."""
    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": f"Prompt for {x.get('instructions', 'unknown')}",
            "instructions": x.get("instructions", ""),
        },
    ):
        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify stream operations
        mock_training_stream.start_stream.assert_called_once()
        assert mock_training_stream.emit.call_count > 0
        mock_training_stream.close_stream.assert_called_once()

        # Verify repository operations
        assert mock_domain_repository.get_domain.called
        assert mock_domain_repository.update_training_log.called
        assert mock_domain_repository.update_domain_prompts.called

        # Verify optimizer operations
        assert mock_dspy_optimizer.optimize_entity_extraction.called
        assert mock_dspy_optimizer.optimize_relation_extraction.called


@pytest.mark.asyncio
async def test_run_dspy_optimization_full_phase_sequence(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test complete training run with all phases."""
    emit_calls = []

    def capture_emit(**kwargs):
        emit_calls.append(kwargs)

    mock_training_stream.emit.side_effect = capture_emit

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": "Prompt template",
            "instructions": x.get("instructions", ""),
        },
    ):
        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

    # Verify key events were emitted
    event_types = [call["event_type"] for call in emit_calls]
    assert EventType.STARTED in event_types
    assert EventType.PHASE_CHANGED in event_types
    assert EventType.COMPLETED in event_types


# ============================================================================
# Test: Progress Callback
# ============================================================================


@pytest.mark.asyncio
async def test_run_dspy_optimization_invokes_progress_callback(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test progress callback is invoked with events."""
    progress_events = []

    async def capture_progress(event: ProgressEvent):
        progress_events.append(event)

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": "Prompt",
            "instructions": x.get("instructions", ""),
        },
    ), patch(
        "src.components.domain_training.training_runner.TrainingProgressTracker"
    ) as mock_tracker_class:
        mock_tracker = AsyncMock()
        mock_tracker.enter_phase = MagicMock()
        mock_tracker.update_progress = MagicMock()
        mock_tracker.complete = MagicMock()
        mock_tracker.current_progress = 50.0
        mock_tracker_class.return_value = mock_tracker

        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify tracker was used
        assert mock_tracker.enter_phase.called
        assert mock_tracker.update_progress.called
        assert mock_tracker.complete.called


# ============================================================================
# Test: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_run_dspy_optimization_domain_not_found(
    mock_domain_repository,
    mock_training_stream,
    sample_training_dataset,
):
    """Test handling when domain not found."""
    mock_domain_repository.get_domain = AsyncMock(return_value=None)

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.TrainingProgressTracker"
    ) as mock_tracker_class:
        mock_tracker = AsyncMock()
        mock_tracker.fail = MagicMock()
        mock_tracker.current_progress = 5.0
        mock_tracker_class.return_value = mock_tracker

        await run_dspy_optimization(
            domain_name="nonexistent",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify failure was handled
        mock_tracker.fail.assert_called()
        # Check that a FAILED event was emitted at some point
        failed_events = [
            call
            for call in mock_training_stream.emit.call_args_list
            if len(call[1]) > 0 and call[1].get("event_type") == EventType.FAILED
        ]
        assert len(failed_events) > 0


@pytest.mark.asyncio
async def test_run_dspy_optimization_database_error(
    sample_training_dataset,
):
    """Test handling database errors during training."""
    mock_domain_repository = AsyncMock()
    mock_domain_repository.get_domain = AsyncMock(
        return_value={
            "name": "tech_docs",
            "llm_model": "qwen3:32b",
        }
    )
    # Simulate database error by raising during update_training_log
    mock_domain_repository.update_training_log = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    mock_training_stream = MagicMock()
    mock_training_stream.start_stream = MagicMock()
    mock_training_stream.emit = MagicMock()
    mock_training_stream.close_stream = MagicMock()

    mock_dspy_optimizer = AsyncMock()
    mock_dspy_optimizer.set_event_stream = MagicMock()
    mock_dspy_optimizer.optimize_entity_extraction = AsyncMock(
        return_value={"metrics": {"f1": 0.85}}
    )

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": "Prompt",
            "instructions": x.get("instructions", ""),
        },
    ), patch(
        "src.components.domain_training.training_runner.TrainingProgressTracker"
    ) as mock_tracker_class:
        mock_tracker = AsyncMock()
        mock_tracker.enter_phase = MagicMock()
        mock_tracker.update_progress = MagicMock(side_effect=Exception("Database error"))
        mock_tracker.fail = MagicMock()
        mock_tracker.current_progress = 5.0
        mock_tracker_class.return_value = mock_tracker

        # The error during persist_progress should be caught and logged
        # Training should continue
        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify error was logged
        assert mock_training_stream.emit.called


@pytest.mark.asyncio
async def test_run_dspy_optimization_unexpected_error(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test handling unexpected errors."""
    mock_dspy_optimizer.optimize_entity_extraction = AsyncMock(
        side_effect=RuntimeError("Unexpected error")
    )

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.TrainingProgressTracker"
    ) as mock_tracker_class, patch(
        "src.components.graph_rag.neo4j_client.get_neo4j_client"
    ) as mock_neo4j:
        mock_tracker = AsyncMock()
        mock_tracker.enter_phase = MagicMock()
        mock_tracker.update_progress = MagicMock()
        mock_tracker.fail = MagicMock()
        mock_tracker.current_progress = 10.0
        mock_tracker_class.return_value = mock_tracker

        mock_neo4j_client = AsyncMock()
        mock_neo4j.return_value = mock_neo4j_client

        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify error was handled
        mock_tracker.fail.assert_called()
        # Check that a FAILED event was emitted
        failed_events = [
            call
            for call in mock_training_stream.emit.call_args_list
            if len(call[1]) > 0 and call[1].get("event_type") == EventType.FAILED
        ]
        assert len(failed_events) > 0


@pytest.mark.asyncio
async def test_run_dspy_optimization_task_cancellation(
    mock_domain_repository,
    mock_training_stream,
    sample_training_dataset,
):
    """Test handling task cancellation."""
    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer"
    ) as mock_optimizer_class, patch(
        "src.components.domain_training.training_runner.TrainingProgressTracker"
    ) as mock_tracker_class:
        mock_optimizer = AsyncMock()
        mock_optimizer.set_event_stream = MagicMock()
        # Simulate cancellation during entity optimization
        mock_optimizer.optimize_entity_extraction = AsyncMock(
            side_effect=asyncio.CancelledError()
        )
        mock_optimizer_class.return_value = mock_optimizer

        mock_tracker = AsyncMock()
        mock_tracker.enter_phase = MagicMock()
        mock_tracker.update_progress = MagicMock()
        mock_tracker.fail = MagicMock()
        mock_tracker.current_progress = 20.0
        mock_tracker_class.return_value = mock_tracker

        with pytest.raises(asyncio.CancelledError):
            await run_dspy_optimization(
                domain_name="tech_docs",
                training_run_id="run-123",
                dataset=sample_training_dataset,
            )

        # Verify cancellation was handled
        mock_tracker.fail.assert_called_with("Training cancelled by user")


# ============================================================================
# Test: Stream Integration
# ============================================================================


@pytest.mark.asyncio
async def test_run_dspy_optimization_emits_sse_events(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test SSE events are emitted during training."""
    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": "Prompt",
            "instructions": x.get("instructions", ""),
        },
    ):
        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify stream operations
        mock_training_stream.start_stream.assert_called_once_with(
            "run-123", "tech_docs", None
        )
        mock_training_stream.close_stream.assert_called_once_with("run-123")

        # Verify emit was called with proper structure
        calls = mock_training_stream.emit.call_args_list
        assert len(calls) > 0

        # Check first call
        first_call_kwargs = calls[0][1]
        assert first_call_kwargs["training_run_id"] == "run-123"
        assert first_call_kwargs["domain"] == "tech_docs"
        assert "event_type" in first_call_kwargs
        assert "progress_percent" in first_call_kwargs


@pytest.mark.asyncio
async def test_run_dspy_optimization_with_log_path(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test training with JSONL log path."""
    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": "Prompt",
            "instructions": x.get("instructions", ""),
        },
    ):
        log_path = "/logs/training.jsonl"

        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
            log_path=log_path,
        )

        # Verify log_path was passed to stream
        mock_training_stream.start_stream.assert_called_once_with("run-123", "tech_docs", log_path)


# ============================================================================
# Test: Metrics Tracking
# ============================================================================


@pytest.mark.asyncio
async def test_run_dspy_optimization_collects_metrics(
    mock_domain_repository,
    mock_training_stream,
    mock_dspy_optimizer,
    sample_training_dataset,
):
    """Test metrics are properly collected and logged."""
    captured_metrics = {}

    async def capture_update(log_id, progress, message, status, metrics):
        if metrics:
            captured_metrics["final"] = metrics

    mock_domain_repository.update_training_log = AsyncMock(side_effect=capture_update)

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.DSPyOptimizer",
        return_value=mock_dspy_optimizer,
    ), patch(
        "src.components.domain_training.training_runner.extract_prompt_from_dspy_result",
        side_effect=lambda x: {
            "prompt_template": "Prompt",
            "instructions": x.get("instructions", ""),
        },
    ):
        await run_dspy_optimization(
            domain_name="tech_docs",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify metrics were collected
        assert "final" in captured_metrics
        metrics = captured_metrics["final"]
        assert "entity_f1" in metrics
        assert "relation_f1" in metrics
        assert "training_samples" in metrics


@pytest.mark.asyncio
async def test_run_dspy_optimization_validation_error(
    mock_domain_repository,
    mock_training_stream,
    sample_training_dataset,
):
    """Test validation errors are properly handled."""
    mock_domain_repository.get_domain = AsyncMock(return_value=None)

    with patch(
        "src.components.domain_training.training_runner.get_domain_repository",
        return_value=mock_domain_repository,
    ), patch(
        "src.components.domain_training.training_runner.get_training_stream",
        return_value=mock_training_stream,
    ), patch(
        "src.components.domain_training.training_runner.TrainingProgressTracker"
    ) as mock_tracker_class:
        mock_tracker = AsyncMock()
        mock_tracker.enter_phase = MagicMock()
        mock_tracker.fail = MagicMock()
        mock_tracker.current_progress = 5.0
        mock_tracker_class.return_value = mock_tracker

        await run_dspy_optimization(
            domain_name="invalid_domain",
            training_run_id="run-123",
            dataset=sample_training_dataset,
        )

        # Verify validation error was caught and failed
        mock_tracker.fail.assert_called()
        call_args = mock_tracker.fail.call_args
        assert "not found" in str(call_args).lower() or "error" in str(call_args).lower()
