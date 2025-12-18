"""Phase Event Emission Helper for Real-Time Thinking Display.

Sprint 51 Feature 51.1: Phase Display Backend Fix

This module provides helper functions for emitting phase events throughout
the RAG pipeline. It ensures consistent phase event tracking across all agents.

Usage:
    from src.agents.phase_emitter import emit_phase_start, emit_phase_end

    # Start phase
    start_time = emit_phase_start(PhaseType.VECTOR_SEARCH)

    # Do work...

    # End phase
    emit_phase_end(PhaseType.VECTOR_SEARCH, start_time, metadata={"results": 10})
"""

import time
from datetime import datetime
from typing import Any

import structlog

from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

logger = structlog.get_logger(__name__)


def create_phase_event(
    phase_type: PhaseType,
    status: PhaseStatus,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> PhaseEvent:
    """Create a phase event with proper timestamp handling.

    Args:
        phase_type: Type of phase (e.g., VECTOR_SEARCH)
        status: Phase status (PENDING, IN_PROGRESS, COMPLETED, FAILED)
        start_time: Phase start time (default: now)
        end_time: Phase end time (default: None)
        duration_ms: Phase duration in milliseconds (auto-calculated if not provided)
        metadata: Phase-specific metadata
        error: Error message if phase failed

    Returns:
        PhaseEvent instance
    """
    if start_time is None:
        start_time = datetime.utcnow()

    # Calculate duration if end_time is provided but duration_ms is not
    if end_time is not None and duration_ms is None:
        duration_ms = (end_time - start_time).total_seconds() * 1000

    return PhaseEvent(
        phase_type=phase_type,
        status=status,
        start_time=start_time,
        end_time=end_time,
        duration_ms=duration_ms,
        metadata=metadata or {},
        error=error,
    )


def emit_phase_start(phase_type: PhaseType) -> float:
    """Emit a phase start event.

    This should be called at the beginning of each processing phase.

    Args:
        phase_type: Type of phase being started

    Returns:
        Start time (perf_counter) for calculating duration later

    Example:
        >>> start_time = emit_phase_start(PhaseType.VECTOR_SEARCH)
        >>> # Do work...
        >>> emit_phase_end(PhaseType.VECTOR_SEARCH, start_time)
    """
    start_perf = time.perf_counter()
    logger.info(
        "phase_started",
        phase=phase_type.value,
        timestamp=datetime.utcnow().isoformat(),
    )
    return start_perf


def emit_phase_end(
    phase_type: PhaseType,
    start_perf: float,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> PhaseEvent:
    """Emit a phase end event.

    This should be called at the end of each processing phase.

    Args:
        phase_type: Type of phase being completed
        start_perf: Start time from emit_phase_start()
        metadata: Phase-specific metadata (e.g., results count)
        error: Error message if phase failed

    Returns:
        PhaseEvent instance

    Example:
        >>> start_time = emit_phase_start(PhaseType.VECTOR_SEARCH)
        >>> results = search_vector_db(query)
        >>> event = emit_phase_end(
        ...     PhaseType.VECTOR_SEARCH,
        ...     start_time,
        ...     metadata={"results_count": len(results)}
        ... )
    """
    end_perf = time.perf_counter()
    duration_ms = (end_perf - start_perf) * 1000
    status = PhaseStatus.FAILED if error else PhaseStatus.COMPLETED

    logger.info(
        "phase_completed",
        phase=phase_type.value,
        duration_ms=duration_ms,
        status=status.value,
        error=error,
        metadata=metadata,
    )

    return create_phase_event(
        phase_type=phase_type,
        status=status,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow(),
        duration_ms=duration_ms,
        metadata=metadata,
        error=error,
    )


def add_phase_to_state(state: dict[str, Any], event: PhaseEvent) -> None:
    """Add a phase event to the agent state.

    This allows the coordinator to capture and stream the phase event.

    Args:
        state: Current agent state
        event: PhaseEvent to add

    Example:
        >>> event = emit_phase_end(PhaseType.VECTOR_SEARCH, start_time)
        >>> add_phase_to_state(state, event)
    """
    state["phase_event"] = event
    logger.debug(
        "phase_added_to_state",
        phase=event.phase_type.value,
        status=event.status.value,
    )


__all__ = [
    "create_phase_event",
    "emit_phase_start",
    "emit_phase_end",
    "add_phase_to_state",
]
