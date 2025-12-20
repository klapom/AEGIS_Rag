"""Training Progress Tracking for DSPy Optimization.

Sprint 45 - Feature 45.5: Training Progress & Logging

This module provides structured progress tracking for DSPy-based domain training.
It defines training phases, progress events, and a callback-based tracker for
real-time monitoring and logging.

Key Features:
- Phase-based progress tracking with weighted percentages
- Real-time progress events with callbacks
- Structured logging integration
- Automatic metric collection and reporting
- Training summary generation

Architecture:
    TrainingProgressTracker
    ├── Phase transitions (INITIALIZING → COMPLETED)
    ├── Progress updates (0-100% with sub-progress)
    ├── Event emission with callbacks
    └── Summary logging with metrics

Training Phases:
    1. INITIALIZING (0-5%): Domain config loading
    2. LOADING_DATA (5-10%): Dataset validation
    3. ENTITY_OPTIMIZATION (10-45%): Entity extraction tuning
    4. RELATION_OPTIMIZATION (45-80%): Relation extraction tuning
    5. PROMPT_EXTRACTION (80-85%): Static prompt generation
    6. VALIDATION (85-95%): Metric validation
    7. SAVING (95-100%): Neo4j persistence
    8. COMPLETED (100%): Training finished successfully
    9. FAILED: Training error occurred

Usage:
    >>> from src.components.domain_training import TrainingProgressTracker, TrainingPhase
    >>> tracker = TrainingProgressTracker(
    ...     training_run_id="uuid-1234",
    ...     domain_name="tech_docs",
    ...     on_progress=lambda event: print(event.message)
    ... )
    >>> tracker.enter_phase(TrainingPhase.INITIALIZING, "Loading config...")
    >>> tracker.update_progress(0.5, "Validating domain", {"domain": "tech_docs"})
    >>> tracker.complete({"f1": 0.85, "samples": 100})
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Union

import structlog

logger = structlog.get_logger(__name__)


class TrainingPhase(Enum):
    """Training phase enumeration with semantic meaning.

    Each phase represents a distinct stage in the DSPy optimization pipeline.
    Phases are ordered and have associated progress percentage ranges.
    """

    INITIALIZING = "initializing"
    LOADING_DATA = "loading_data"
    ENTITY_OPTIMIZATION = "entity_optimization"
    RELATION_OPTIMIZATION = "relation_optimization"
    PROMPT_EXTRACTION = "prompt_extraction"
    VALIDATION = "validation"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """Represents a single progress event during training.

    Attributes:
        phase: Current training phase
        progress_percent: Overall progress percentage (0-100)
        message: Human-readable progress message
        timestamp: Event timestamp (UTC)
        metrics: Optional metrics dictionary (e.g., F1, recall)
    """

    phase: TrainingPhase
    progress_percent: float  # 0-100
    message: str
    timestamp: datetime
    metrics: dict | None = None


class TrainingProgressTracker:
    """Tracks and logs training progress with callbacks.

    This tracker manages phase transitions, progress updates, and event emission
    for DSPy optimization. It provides structured logging and callback support
    for real-time progress monitoring.

    Attributes:
        PHASE_WEIGHTS: Mapping of phases to progress percentage ranges (start, end)
        training_run_id: Unique identifier for training run
        domain_name: Domain being trained
        on_progress: Optional callback for progress events

    Example:
        >>> async def persist_callback(event: ProgressEvent):
        ...     await repo.update_training_log(
        ...         training_run_id,
        ...         progress=event.progress_percent,
        ...         message=event.message,
        ...         metrics=event.metrics
        ...     )
        >>> tracker = TrainingProgressTracker(
        ...     training_run_id="uuid-1234",
        ...     domain_name="tech_docs",
        ...     on_progress=persist_callback
        ... )
        >>> tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Starting entity tuning")
        >>> tracker.update_progress(0.3, "Epoch 3/10", {"loss": 0.5})
        >>> tracker.complete({"f1": 0.85})
    """

    # Phase progress percentage ranges (start%, end%)
    PHASE_WEIGHTS = {
        TrainingPhase.INITIALIZING: (0, 5),
        TrainingPhase.LOADING_DATA: (5, 10),
        TrainingPhase.ENTITY_OPTIMIZATION: (10, 45),
        TrainingPhase.RELATION_OPTIMIZATION: (45, 80),
        TrainingPhase.PROMPT_EXTRACTION: (80, 85),
        TrainingPhase.VALIDATION: (85, 95),
        TrainingPhase.SAVING: (95, 100),
        TrainingPhase.COMPLETED: (100, 100),
    }

    # Type alias for progress callback - supports both sync and async
    ProgressCallback = (
        Callable[["ProgressEvent"], None] | Callable[["ProgressEvent"], Awaitable[None]]
    )

    def __init__(
        self,
        training_run_id: str,
        domain_name: str,
        on_progress: "TrainingProgressTracker.ProgressCallback | None" = None,
    ):
        """Initialize training progress tracker.

        Args:
            training_run_id: Unique identifier for training run (UUID)
            domain_name: Domain being trained (e.g., "tech_docs")
            on_progress: Optional callback for progress events. Called for each event.
                        Can be sync or async function.
        """
        self.training_run_id = training_run_id
        self.domain_name = domain_name
        self.on_progress = on_progress
        self._events: list[ProgressEvent] = []
        self._current_phase = TrainingPhase.INITIALIZING
        self._start_time = datetime.utcnow()

    def enter_phase(self, phase: TrainingPhase, message: str = "") -> None:
        """Enter a new training phase.

        This method transitions to a new phase and emits a progress event
        at the start percentage of that phase.

        Args:
            phase: Training phase to enter
            message: Optional custom message. Defaults to "Entering {phase.value}"

        Example:
            >>> tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Starting entity tuning")
        """
        self._current_phase = phase
        start, _ = self.PHASE_WEIGHTS[phase]

        event = ProgressEvent(
            phase=phase,
            progress_percent=start,
            message=message or f"Entering {phase.value}",
            timestamp=datetime.utcnow(),
        )
        self._emit(event)

    def update_progress(
        self, sub_progress: float, message: str, metrics: dict | None = None
    ) -> None:
        """Update progress within current phase.

        This method calculates overall progress by mapping sub-progress (0-1)
        to the current phase's percentage range.

        Args:
            sub_progress: Progress within current phase (0.0 to 1.0)
            message: Human-readable progress message
            metrics: Optional metrics dictionary (e.g., {"loss": 0.5, "f1": 0.85})

        Example:
            >>> tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Starting")
            >>> tracker.update_progress(0.3, "Epoch 3/10", {"loss": 0.5})
            >>> # Overall progress: 10% + 0.3 * (45% - 10%) = 20.5%
        """
        start, end = self.PHASE_WEIGHTS[self._current_phase]
        overall = start + sub_progress * (end - start)

        event = ProgressEvent(
            phase=self._current_phase,
            progress_percent=overall,
            message=message,
            timestamp=datetime.utcnow(),
            metrics=metrics,
        )
        self._emit(event)

    def complete(self, metrics: dict) -> None:
        """Mark training as completed successfully.

        This method emits a completion event with final metrics and logs
        a training summary.

        Args:
            metrics: Final training metrics (e.g., {"entity_f1": 0.85, "relation_f1": 0.82})

        Example:
            >>> tracker.complete({
            ...     "entity_f1": 0.85,
            ...     "relation_f1": 0.82,
            ...     "training_samples": 100
            ... })
        """
        event = ProgressEvent(
            phase=TrainingPhase.COMPLETED,
            progress_percent=100,
            message="Training completed successfully",
            timestamp=datetime.utcnow(),
            metrics=metrics,
        )
        self._emit(event)
        self._log_summary(metrics)

    def fail(self, error: str) -> None:
        """Mark training as failed.

        This method emits a failure event with error message and retains
        the last known progress percentage.

        Args:
            error: Error message describing the failure

        Example:
            >>> try:
            ...     await optimizer.optimize_entity_extraction(data)
            ... except Exception as e:
            ...     tracker.fail(str(e))
        """
        event = ProgressEvent(
            phase=TrainingPhase.FAILED,
            progress_percent=self._events[-1].progress_percent if self._events else 0,
            message=f"Training failed: {error}",
            timestamp=datetime.utcnow(),
        )
        self._emit(event)

    def _emit(self, event: ProgressEvent) -> None:
        """Emit progress event to logger and callback.

        Supports both sync and async callbacks. Async callbacks are
        scheduled as background tasks to avoid blocking the training loop.

        Args:
            event: Progress event to emit
        """
        self._events.append(event)

        logger.info(
            "training_progress",
            training_run_id=self.training_run_id,
            domain=self.domain_name,
            phase=event.phase.value,
            progress=event.progress_percent,
            message=event.message,
            metrics=event.metrics,
        )

        if self.on_progress:
            # Check if callback is async (coroutine function)
            if inspect.iscoroutinefunction(self.on_progress):
                # Schedule async callback as background task (fire-and-forget)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.on_progress(event))
                except RuntimeError:
                    # No running loop - skip async callback
                    logger.warning(
                        "async_callback_skipped",
                        reason="no_running_event_loop",
                    )
            else:
                # Sync callback - call directly
                self.on_progress(event)

    def _log_summary(self, metrics: dict) -> None:
        """Log training summary with duration and metrics.

        Args:
            metrics: Final training metrics
        """
        duration = (datetime.utcnow() - self._start_time).total_seconds()
        logger.info(
            "training_completed",
            training_run_id=self.training_run_id,
            domain=self.domain_name,
            duration_seconds=duration,
            metrics=metrics,
            event_count=len(self._events),
        )

    @property
    def events(self) -> list[ProgressEvent]:
        """Get copy of all progress events.

        Returns:
            List of progress events (copy, not reference)
        """
        return self._events.copy()
