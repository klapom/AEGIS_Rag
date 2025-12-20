"""Progress Event System for Ingestion Pipeline - Sprint 51.

This module provides real-time progress updates during document ingestion,
especially for long-running operations like entity/relation extraction.

The system uses an async queue to pass progress events from the graph
extraction node to the streaming endpoint, enabling real-time UI updates.

Usage:
    # In graph_extraction_node:
    from src.components.ingestion.progress_events import emit_progress

    await emit_progress(
        document_id="doc123",
        phase="entity_extraction",
        current=1,
        total=5,
        message="Extracting entities from chunk 1/5"
    )

    # In run_ingestion_pipeline_streaming:
    from src.components.ingestion.progress_events import get_progress_queue

    queue = get_progress_queue(document_id)
    while not queue.empty():
        event = await queue.get()
        yield event
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Global registry of progress queues per document
_progress_queues: dict[str, asyncio.Queue] = {}
_progress_lock = asyncio.Lock()


@dataclass
class ProgressEvent:
    """Progress event for ingestion pipeline.

    Attributes:
        document_id: Document being processed
        phase: Current phase (entity_extraction, relation_extraction, etc.)
        current: Current item number (1-indexed)
        total: Total items to process
        message: Human-readable message
        timestamp: Local timestamp (HH:MM:SS)
        details: Optional additional details
    """

    document_id: str
    phase: str
    current: int
    total: int
    message: str
    # Sprint 51 Fix: Use local time instead of UTC for consistent display
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "phase": self.phase,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
        }


async def get_or_create_progress_queue(document_id: str) -> asyncio.Queue:
    """Get or create a progress queue for a document.

    Args:
        document_id: Document identifier

    Returns:
        AsyncIO queue for progress events
    """
    async with _progress_lock:
        if document_id not in _progress_queues:
            _progress_queues[document_id] = asyncio.Queue(maxsize=100)
            logger.debug("progress_queue_created", document_id=document_id)
        return _progress_queues[document_id]


async def get_progress_queue(document_id: str) -> asyncio.Queue | None:
    """Get progress queue for a document (if exists).

    Args:
        document_id: Document identifier

    Returns:
        AsyncIO queue or None if not exists
    """
    return _progress_queues.get(document_id)


async def cleanup_progress_queue(document_id: str) -> None:
    """Clean up progress queue after document processing.

    Args:
        document_id: Document identifier
    """
    async with _progress_lock:
        if document_id in _progress_queues:
            del _progress_queues[document_id]
            logger.debug("progress_queue_cleaned", document_id=document_id)


async def emit_progress(
    document_id: str,
    phase: str,
    current: int,
    total: int,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Emit a progress event to the document's queue.

    This function is called during long-running operations to report
    real-time progress to the UI.

    Args:
        document_id: Document being processed
        phase: Current phase (entity_extraction, relation_extraction, etc.)
        current: Current item number (1-indexed)
        total: Total items to process
        message: Human-readable message
        details: Optional additional details

    Example:
        await emit_progress(
            document_id="abc123",
            phase="relation_extraction",
            current=2,
            total=5,
            message="Extracting relations from chunk 2/5",
            details={"entities_found": 10}
        )
    """
    queue = await get_or_create_progress_queue(document_id)

    event = ProgressEvent(
        document_id=document_id,
        phase=phase,
        current=current,
        total=total,
        message=message,
        details=details or {},
    )

    try:
        # Non-blocking put - drop if queue is full
        queue.put_nowait(event)
        logger.debug(
            "progress_event_emitted",
            document_id=document_id,
            phase=phase,
            current=current,
            total=total,
        )
    except asyncio.QueueFull:
        logger.warning(
            "progress_queue_full",
            document_id=document_id,
            phase=phase,
            dropping_event=True,
        )


async def drain_progress_events(document_id: str) -> list[ProgressEvent]:
    """Drain all pending progress events from a document's queue.

    Non-blocking - returns immediately with all available events.

    Args:
        document_id: Document identifier

    Returns:
        List of progress events (may be empty)
    """
    events = []
    queue = await get_progress_queue(document_id)

    if queue is None:
        return events

    while not queue.empty():
        try:
            event = queue.get_nowait()
            events.append(event)
        except asyncio.QueueEmpty:
            break

    return events


def format_progress_message(phase: str, current: int, total: int, _base_message: str = "") -> str:
    """Format a progress message with timestamp and chunk info.

    Args:
        phase: Current phase
        current: Current chunk (1-indexed)
        total: Total chunks
        _base_message: Optional base message (reserved for future use)

    Returns:
        Formatted message like "[12:34:56] Extracting entities (chunk 1/5)"
    """
    # Sprint 51 Fix: Use local time for consistent display
    timestamp = datetime.now().strftime("%H:%M:%S")

    phase_names = {
        "entity_extraction": "Extracting entities",
        "relation_extraction": "Extracting relations",
        "community_detection": "Detecting communities",
        "lightrag_insert": "Processing with LightRAG",
    }

    phase_name = phase_names.get(phase, phase.replace("_", " ").title())

    if total > 0:
        return f"[{timestamp}] {phase_name} (chunk {current}/{total})"
    else:
        return f"[{timestamp}] {phase_name}"
