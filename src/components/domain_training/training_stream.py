"""Training Event Stream for SSE-based real-time progress updates.

Sprint 45 - Feature 45.13: Real-time Training Progress with SSE

This module provides infrastructure for streaming detailed training progress
events via Server-Sent Events (SSE). It captures LLM interactions, evaluation
results, and progress updates in real-time.

Key Features:
- Event queue per training run for SSE streaming
- Detailed LLM interaction logging (prompts, responses, scores)
- JSONL file logging for later evaluation
- Full content without truncation

Architecture:
    TrainingEventStream (singleton)
    ├── Active streams per training_run_id
    ├── Event queues for SSE consumers
    └── JSONL file writers

Usage:
    >>> stream = get_training_stream()
    >>> stream.start_stream("run-123", log_path="/logs/run-123.jsonl")
    >>> stream.emit_event("run-123", TrainingEvent(...))
    >>> async for event in stream.subscribe("run-123"):
    ...     yield f"data: {event.json()}\\n\\n"
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class EventType(str, Enum):
    """Types of training events."""

    # Progress events
    STARTED = "started"
    PHASE_CHANGED = "phase_changed"
    PROGRESS_UPDATE = "progress_update"
    COMPLETED = "completed"
    FAILED = "failed"

    # LLM interaction events
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"

    # Sample processing events
    SAMPLE_PROCESSING = "sample_processing"
    SAMPLE_RESULT = "sample_result"

    # Evaluation events
    EVALUATION_START = "evaluation_start"
    EVALUATION_RESULT = "evaluation_result"

    # Optimization events
    BOOTSTRAP_ITERATION = "bootstrap_iteration"
    DEMO_SELECTED = "demo_selected"


@dataclass
class TrainingEvent:
    """A single training event with full details."""

    event_type: EventType
    timestamp: str
    training_run_id: str
    domain: str
    progress_percent: float
    phase: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "training_run_id": self.training_run_id,
            "domain": self.domain,
            "progress_percent": self.progress_percent,
            "phase": self.phase,
            "message": self.message,
            "data": self.data,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        return f"data: {self.to_json()}\n\n"


@dataclass
class StreamState:
    """State for an active training stream."""

    training_run_id: str
    domain: str
    log_path: Path | None
    queue: asyncio.Queue[TrainingEvent | None]
    log_file: Any | None = None  # File handle
    started_at: datetime = field(default_factory=datetime.utcnow)
    event_count: int = 0


class TrainingEventStream:
    """Manages training event streams for SSE delivery.

    This singleton class handles:
    - Creating and managing event queues per training run
    - Writing events to JSONL files
    - Providing async iterators for SSE consumers
    """

    _instance: "TrainingEventStream | None" = None

    def __new__(cls) -> "TrainingEventStream":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._streams: dict[str, StreamState] = {}
        self._initialized = True
        logger.info("training_event_stream_initialized")

    def start_stream(
        self,
        training_run_id: str,
        domain: str,
        log_path: str | None = None,
    ) -> None:
        """Start a new training event stream.

        Args:
            training_run_id: Unique training run identifier
            domain: Domain being trained
            log_path: Optional path for JSONL log file
        """
        if training_run_id in self._streams:
            logger.warning("stream_already_exists", training_run_id=training_run_id)
            return

        # Create log file if path provided
        file_handle = None
        path = None
        if log_path:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handle = open(path, "w", encoding="utf-8")  # noqa: SIM115 - Closed in close_stream()
            logger.info("jsonl_log_file_created", path=str(path))

        state = StreamState(
            training_run_id=training_run_id,
            domain=domain,
            log_path=path,
            queue=asyncio.Queue(),
            log_file=file_handle,
        )

        self._streams[training_run_id] = state
        logger.info(
            "training_stream_started",
            training_run_id=training_run_id,
            domain=domain,
            log_path=str(path) if path else None,
        )

    def emit_event(self, training_run_id: str, event: TrainingEvent) -> None:
        """Emit an event to the stream.

        Args:
            training_run_id: Training run to emit to
            event: Event to emit
        """
        state = self._streams.get(training_run_id)
        if not state:
            logger.warning("stream_not_found", training_run_id=training_run_id)
            return

        # Update event count
        state.event_count += 1

        # Write to JSONL log file if configured
        if state.log_file:
            state.log_file.write(event.to_json() + "\n")
            state.log_file.flush()

        # Put in queue for SSE consumers (non-blocking)
        try:
            state.queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("event_queue_full", training_run_id=training_run_id)

    def emit(
        self,
        training_run_id: str,
        event_type: EventType,
        domain: str,
        progress_percent: float,
        phase: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Convenience method to emit an event.

        Args:
            training_run_id: Training run to emit to
            event_type: Type of event
            domain: Domain name
            progress_percent: Current progress (0-100)
            phase: Current training phase
            message: Human-readable message
            data: Additional event data
        """
        event = TrainingEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            training_run_id=training_run_id,
            domain=domain,
            progress_percent=progress_percent,
            phase=phase,
            message=message,
            data=data or {},
        )
        self.emit_event(training_run_id, event)

    async def subscribe(self, training_run_id: str) -> AsyncIterator[TrainingEvent]:
        """Subscribe to events for a training run.

        Yields events until the stream is closed (None sentinel).

        Args:
            training_run_id: Training run to subscribe to

        Yields:
            Training events as they occur
        """
        state = self._streams.get(training_run_id)
        if not state:
            logger.warning("subscribe_stream_not_found", training_run_id=training_run_id)
            return

        logger.info("sse_client_subscribed", training_run_id=training_run_id)

        try:
            while True:
                event = await state.queue.get()
                if event is None:
                    # Stream closed
                    break
                yield event
        finally:
            logger.info("sse_client_disconnected", training_run_id=training_run_id)

    def close_stream(self, training_run_id: str) -> None:
        """Close a training stream.

        Args:
            training_run_id: Training run to close
        """
        state = self._streams.get(training_run_id)
        if not state:
            return

        # Close log file
        if state.log_file:
            state.log_file.close()
            logger.info(
                "jsonl_log_file_closed",
                path=str(state.log_path),
                event_count=state.event_count,
            )

        # Send sentinel to close subscribers
        with contextlib.suppress(asyncio.QueueFull):
            state.queue.put_nowait(None)

        # Remove from active streams
        del self._streams[training_run_id]
        logger.info(
            "training_stream_closed",
            training_run_id=training_run_id,
            event_count=state.event_count,
        )

    def is_active(self, training_run_id: str) -> bool:
        """Check if a stream is active.

        Args:
            training_run_id: Training run to check

        Returns:
            True if stream is active
        """
        return training_run_id in self._streams

    def get_stats(self, training_run_id: str) -> dict[str, Any] | None:
        """Get statistics for a training stream.

        Args:
            training_run_id: Training run to get stats for

        Returns:
            Stream statistics or None if not found
        """
        state = self._streams.get(training_run_id)
        if not state:
            return None

        return {
            "training_run_id": state.training_run_id,
            "domain": state.domain,
            "log_path": str(state.log_path) if state.log_path else None,
            "started_at": state.started_at.isoformat(),
            "event_count": state.event_count,
        }


# Singleton instance
_stream_instance: TrainingEventStream | None = None


def get_training_stream() -> TrainingEventStream:
    """Get the singleton training event stream instance.

    Returns:
        TrainingEventStream singleton
    """
    global _stream_instance
    if _stream_instance is None:
        _stream_instance = TrainingEventStream()
    return _stream_instance


def reset_training_stream() -> None:
    """Reset the training stream singleton (for testing)."""
    global _stream_instance
    if _stream_instance:
        # Close all active streams
        for run_id in list(_stream_instance._streams.keys()):
            _stream_instance.close_stream(run_id)
    _stream_instance = None
