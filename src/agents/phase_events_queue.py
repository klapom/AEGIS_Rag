"""Phase Event System for Real-Time Chat Progress - Sprint 52.

This module provides real-time phase event updates during query processing.

Two methods are available:
1. stream_phase_event() - Uses LangGraph's get_stream_writer() for REAL-TIME
   events that are emitted DURING node execution (preferred method).
2. emit_phase_event() (legacy) - Uses async queues, but these are only
   drained when the event loop yields.

Usage:
    # PREFERRED: In LangGraph nodes using stream_mode=["custom", "values"]:
    from src.agents.phase_events_queue import stream_phase_event

    stream_phase_event(
        phase_type=PhaseType.INTENT_CLASSIFICATION,
        status=PhaseStatus.IN_PROGRESS,
    )

    # LEGACY: Async queue approach (kept for backward compatibility)
    from src.agents.phase_events_queue import emit_phase_event, drain_phase_events
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from langgraph.config import get_stream_writer

from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

logger = structlog.get_logger(__name__)

# Global registry of phase event queues per session
_phase_queues: dict[str, asyncio.Queue] = {}
_phase_lock = asyncio.Lock()


async def get_or_create_phase_queue(session_id: str) -> asyncio.Queue:
    """Get or create a phase event queue for a session.

    Args:
        session_id: Session identifier

    Returns:
        AsyncIO queue for phase events
    """
    async with _phase_lock:
        if session_id not in _phase_queues:
            _phase_queues[session_id] = asyncio.Queue(maxsize=50)
            logger.debug("phase_queue_created", session_id=session_id)
        return _phase_queues[session_id]


async def get_phase_queue(session_id: str) -> asyncio.Queue | None:
    """Get phase queue for a session (if exists).

    Args:
        session_id: Session identifier

    Returns:
        AsyncIO queue or None if not exists
    """
    return _phase_queues.get(session_id)


async def cleanup_phase_queue(session_id: str) -> None:
    """Clean up phase queue after query processing.

    Args:
        session_id: Session identifier
    """
    async with _phase_lock:
        if session_id in _phase_queues:
            del _phase_queues[session_id]
            logger.debug("phase_queue_cleaned", session_id=session_id)


async def emit_phase_event(
    session_id: str,
    phase_type: PhaseType,
    status: PhaseStatus,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> PhaseEvent:
    """Emit a phase event to the session's queue.

    This function is called during query processing to report
    real-time phase progress to the UI.

    Args:
        session_id: Session being processed
        phase_type: Type of phase (INTENT_CLASSIFICATION, VECTOR_SEARCH, etc.)
        status: Phase status (IN_PROGRESS, COMPLETED, FAILED)
        duration_ms: Duration in milliseconds (for completed phases)
        metadata: Optional additional details
        error: Error message if failed

    Returns:
        The created PhaseEvent

    Example:
        await emit_phase_event(
            session_id="abc123",
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.IN_PROGRESS,
        )
    """
    queue = await get_or_create_phase_queue(session_id)

    now = datetime.utcnow()
    event = PhaseEvent(
        phase_type=phase_type,
        status=status,
        start_time=now,
        end_time=now if status in (PhaseStatus.COMPLETED, PhaseStatus.FAILED) else None,
        duration_ms=duration_ms,
        metadata=metadata or {},
        error=error,
    )

    try:
        # Non-blocking put - drop if queue is full
        queue.put_nowait(event)
        logger.debug(
            "phase_event_emitted",
            session_id=session_id,
            phase_type=phase_type.value,
            status=status.value,
        )
    except asyncio.QueueFull:
        logger.warning(
            "phase_queue_full",
            session_id=session_id,
            phase_type=phase_type.value,
            dropping_event=True,
        )

    return event


async def drain_phase_events(session_id: str) -> list[PhaseEvent]:
    """Drain all pending phase events from a session's queue.

    Non-blocking - returns immediately with all available events.

    Args:
        session_id: Session identifier

    Returns:
        List of phase events (may be empty)
    """
    events = []
    queue = await get_phase_queue(session_id)

    if queue is None:
        return events

    while not queue.empty():
        try:
            event = queue.get_nowait()
            events.append(event)
        except asyncio.QueueEmpty:
            break

    return events


def stream_phase_event(
    phase_type: PhaseType,
    status: PhaseStatus,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Emit a phase event via LangGraph's stream writer for real-time updates.

    Sprint 52: This function uses get_stream_writer() to emit phase events
    DURING node execution (not after), enabling real-time UI updates.

    IMPORTANT: This only works when the graph is called with:
        stream_mode=["custom", "values"]

    Args:
        phase_type: Type of phase (INTENT_CLASSIFICATION, BM25_SEARCH, etc.)
        status: Phase status (IN_PROGRESS, COMPLETED, FAILED)
        duration_ms: Duration in milliseconds (for completed phases)
        metadata: Optional additional details
        error: Error message if failed
    """
    try:
        writer = get_stream_writer()
        now = datetime.utcnow()

        event_data = {
            "phase_type": phase_type.value,
            "status": status.value,
            "start_time": now.isoformat(),
            "end_time": now.isoformat() if status in (PhaseStatus.COMPLETED, PhaseStatus.FAILED) else None,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
            "error": error,
        }

        # Write to LangGraph stream - this goes IMMEDIATELY to the client
        writer({"type": "phase_event", "data": event_data})

        logger.debug(
            "phase_event_streamed",
            phase_type=phase_type.value,
            status=status.value,
        )
    except Exception as e:
        # Don't fail the node if streaming fails
        logger.warning("phase_event_stream_failed", error=str(e))


def stream_token(content: str) -> None:
    """Emit a token via LangGraph's stream writer for real-time answer streaming.

    Sprint 52: This function uses get_stream_writer() to emit tokens
    DURING LLM generation, enabling real-time answer display in the UI.

    IMPORTANT: This only works when the graph is called with:
        stream_mode=["custom", "values"]

    Args:
        content: Token content to stream
    """
    try:
        writer = get_stream_writer()

        # Write token to LangGraph stream
        writer({"type": "token", "data": {"content": content}})

        logger.debug("token_streamed", content_length=len(content))
    except Exception as e:
        # Don't fail the node if streaming fails
        logger.warning("token_stream_failed", error=str(e))


def stream_citation_map(citation_map: dict[int, dict[str, Any]]) -> None:
    """Emit citation map via LangGraph's stream writer.

    Sprint 52: Sends citation metadata before token streaming begins.

    Args:
        citation_map: Dict mapping citation numbers to source metadata
    """
    try:
        writer = get_stream_writer()

        # Write citation map to LangGraph stream
        writer({"type": "citation_map", "data": citation_map})

        logger.debug("citation_map_streamed", citations_count=len(citation_map))
    except Exception as e:
        logger.warning("citation_map_stream_failed", error=str(e))


__all__ = [
    "stream_phase_event",
    "stream_token",
    "stream_citation_map",
    "emit_phase_event",
    "drain_phase_events",
    "get_or_create_phase_queue",
    "cleanup_phase_queue",
]
