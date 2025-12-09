"""Pipeline Progress State Manager (Sprint 37 Feature 37.3).

Centralized state management for tracking ingestion progress across all stages.
Thread-safe updates with asyncio.Lock, emits SSE-compatible events.

Architecture:
  - Singleton pattern for global access
  - Stage-level progress tracking
  - Worker-level status for extraction pool
  - Timing metrics and ETA calculation
  - SSE event emission on state changes
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class StageStatus(Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StageProgress:
    """Progress tracking for a single pipeline stage."""

    name: str
    status: StageStatus = StageStatus.PENDING
    processed: int = 0
    total: int = 0
    in_flight: int = 0  # Currently being processed
    started_at: float | None = None
    completed_at: float | None = None
    duration_ms: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total == 0:
            return 0.0 if self.status == StageStatus.PENDING else 100.0
        return min(100.0, (self.processed / self.total) * 100)

    @property
    def is_complete(self) -> bool:
        """Check if stage is completed."""
        return self.status == StageStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """Convert to SSE-compatible dict."""
        return {
            "name": self.name,
            "status": self.status.value,
            "processed": self.processed,
            "total": self.total,
            "in_flight": self.in_flight,
            "progress_percent": round(self.progress_percent, 1),
            "duration_ms": self.duration_ms,
            "is_complete": self.is_complete,
        }


@dataclass
class WorkerInfo:
    """Information about a single worker."""

    worker_id: int
    status: str = "idle"  # "idle", "processing", "error"
    current_chunk_id: str | None = None
    progress_percent: float = 0.0
    chunks_processed: int = 0


@dataclass
class PipelineProgress:
    """Complete progress state for a document being processed."""

    document_id: str
    document_name: str
    total_chunks: int = 0
    total_images: int = 0

    # Stage progress
    parsing: StageProgress = field(default_factory=lambda: StageProgress(name="parsing"))
    vlm: StageProgress = field(default_factory=lambda: StageProgress(name="vlm"))
    chunking: StageProgress = field(default_factory=lambda: StageProgress(name="chunking"))
    embedding: StageProgress = field(default_factory=lambda: StageProgress(name="embedding"))
    extraction: StageProgress = field(
        default_factory=lambda: StageProgress(name="extraction")
    )

    # Worker pool info
    workers: list[WorkerInfo] = field(default_factory=list)
    max_workers: int = 4
    queue_depth: int = 0

    # Live metrics
    entities_extracted: int = 0
    relations_extracted: int = 0
    neo4j_writes: int = 0
    qdrant_writes: int = 0

    # Timing
    started_at: float = field(default_factory=time.time)
    last_update_at: float = field(default_factory=time.time)

    @property
    def elapsed_ms(self) -> int:
        """Milliseconds since processing started."""
        return int((time.time() - self.started_at) * 1000)

    @property
    def overall_progress_percent(self) -> float:
        """Calculate overall progress across all stages."""
        stages = [self.parsing, self.vlm, self.chunking, self.embedding, self.extraction]
        total_weight = sum(
            1 for s in stages if s.total > 0 or s.status != StageStatus.PENDING
        )
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(
            s.progress_percent
            for s in stages
            if s.total > 0 or s.status != StageStatus.PENDING
        )
        return weighted_sum / total_weight

    @property
    def estimated_remaining_ms(self) -> int:
        """Estimate remaining time based on current throughput."""
        elapsed = self.elapsed_ms
        progress = self.overall_progress_percent

        if progress < 5:  # Not enough data
            return 0

        # Simple linear extrapolation
        total_estimated = elapsed / (progress / 100)
        return max(0, int(total_estimated - elapsed))

    def to_sse_event(self) -> dict[str, Any]:
        """Convert to SSE event format."""
        return {
            "type": "pipeline_progress",
            "data": {
                "document_id": self.document_id,
                "document_name": self.document_name,
                "total_chunks": self.total_chunks,
                "total_images": self.total_images,
                "stages": {
                    "parsing": self.parsing.to_dict(),
                    "vlm": self.vlm.to_dict(),
                    "chunking": self.chunking.to_dict(),
                    "embedding": self.embedding.to_dict(),
                    "extraction": self.extraction.to_dict(),
                },
                "worker_pool": {
                    "active": sum(1 for w in self.workers if w.status == "processing"),
                    "max": self.max_workers,
                    "queue_depth": self.queue_depth,
                    "workers": [
                        {
                            "id": w.worker_id,
                            "status": w.status,
                            "current_chunk": w.current_chunk_id,
                            "progress_percent": w.progress_percent,
                        }
                        for w in self.workers
                    ],
                },
                "metrics": {
                    "entities_total": self.entities_extracted,
                    "relations_total": self.relations_extracted,
                    "neo4j_writes": self.neo4j_writes,
                    "qdrant_writes": self.qdrant_writes,
                },
                "timing": {
                    "started_at": self.started_at,
                    "elapsed_ms": self.elapsed_ms,
                    "estimated_remaining_ms": self.estimated_remaining_ms,
                },
                "overall_progress_percent": round(self.overall_progress_percent, 1),
            },
        }


class PipelineProgressManager:
    """Singleton manager for pipeline progress tracking.

    Thread-safe state management with SSE event emission.

    Example:
        manager = get_progress_manager()

        # Start tracking a document
        manager.start_document("doc-123", "report.pdf")

        # Update stage progress
        await manager.update_stage("doc-123", "chunking", processed=5, total=32)

        # Get SSE event
        event = manager.get_sse_event("doc-123")
    """

    _instance: Optional["PipelineProgressManager"] = None
    _lock: asyncio.Lock | None = None

    def __new__(cls) -> "PipelineProgressManager":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._documents: dict[str, PipelineProgress] = {}
            cls._instance._sse_callbacks: list[Callable[[dict], None]] = []
            cls._instance._throttle_ms = 500  # Min interval between SSE events
            cls._instance._last_emit: dict[str, float] = {}
        return cls._instance

    async def _get_lock(self) -> asyncio.Lock:
        """Get or create asyncio lock."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def start_document(
        self,
        document_id: str,
        document_name: str,
        total_chunks: int = 0,
        total_images: int = 0,
        max_workers: int = 4,
    ) -> PipelineProgress:
        """Start tracking a new document.

        Args:
            document_id: Unique document identifier
            document_name: Human-readable document name
            total_chunks: Total number of chunks to process (if known)
            total_images: Total number of images to process (if known)
            max_workers: Maximum number of worker threads

        Returns:
            PipelineProgress: Progress tracker for this document
        """
        progress = PipelineProgress(
            document_id=document_id,
            document_name=document_name,
            total_chunks=total_chunks,
            total_images=total_images,
            max_workers=max_workers,
            workers=[WorkerInfo(worker_id=i) for i in range(max_workers)],
        )
        self._documents[document_id] = progress

        logger.info(
            "progress_manager_document_started",
            document_id=document_id,
            document_name=document_name,
        )

        return progress

    def get_progress(self, document_id: str) -> PipelineProgress | None:
        """Get progress for a document.

        Args:
            document_id: Document identifier

        Returns:
            PipelineProgress | None: Progress tracker or None if not found
        """
        return self._documents.get(document_id)

    async def update_stage(
        self,
        document_id: str,
        stage_name: str,
        processed: int | None = None,
        total: int | None = None,
        in_flight: int | None = None,
        status: StageStatus | None = None,
        error: str | None = None,
    ) -> None:
        """Update progress for a specific stage.

        Args:
            document_id: Document identifier
            stage_name: Name of stage (parsing, vlm, chunking, embedding, extraction)
            processed: Number of items processed
            total: Total number of items
            in_flight: Number of items currently being processed
            status: Stage status
            error: Error message (if any)
        """
        lock = await self._get_lock()
        async with lock:
            progress = self._documents.get(document_id)
            if not progress:
                logger.warning("update_stage_no_document", document_id=document_id)
                return

            stage = getattr(progress, stage_name, None)
            if not isinstance(stage, StageProgress):
                logger.warning("update_stage_invalid_stage", stage_name=stage_name)
                return

            # Update fields
            if processed is not None:
                stage.processed = processed
            if total is not None:
                stage.total = total
            if in_flight is not None:
                stage.in_flight = in_flight
            if status is not None:
                if (
                    stage.status == StageStatus.PENDING
                    and status == StageStatus.IN_PROGRESS
                ):
                    stage.started_at = time.time()
                elif status == StageStatus.COMPLETED:
                    stage.completed_at = time.time()
                    if stage.started_at:
                        stage.duration_ms = int(
                            (stage.completed_at - stage.started_at) * 1000
                        )
                stage.status = status
            if error:
                stage.errors.append(error)

            progress.last_update_at = time.time()

            # Emit SSE event (throttled)
            await self._emit_sse_event(document_id)

    async def update_workers(
        self,
        document_id: str,
        workers: list[WorkerInfo],
        queue_depth: int | None = None,
    ) -> None:
        """Update worker pool status.

        Args:
            document_id: Document identifier
            workers: List of worker information
            queue_depth: Number of items in processing queue
        """
        lock = await self._get_lock()
        async with lock:
            progress = self._documents.get(document_id)
            if not progress:
                return

            progress.workers = workers
            if queue_depth is not None:
                progress.queue_depth = queue_depth

            progress.last_update_at = time.time()
            await self._emit_sse_event(document_id)

    async def update_metrics(
        self,
        document_id: str,
        entities: int | None = None,
        relations: int | None = None,
        neo4j_writes: int | None = None,
        qdrant_writes: int | None = None,
    ) -> None:
        """Update live metrics.

        Args:
            document_id: Document identifier
            entities: Total entities extracted
            relations: Total relations extracted
            neo4j_writes: Total Neo4j write operations
            qdrant_writes: Total Qdrant write operations
        """
        lock = await self._get_lock()
        async with lock:
            progress = self._documents.get(document_id)
            if not progress:
                return

            if entities is not None:
                progress.entities_extracted = entities
            if relations is not None:
                progress.relations_extracted = relations
            if neo4j_writes is not None:
                progress.neo4j_writes = neo4j_writes
            if qdrant_writes is not None:
                progress.qdrant_writes = qdrant_writes

            progress.last_update_at = time.time()
            await self._emit_sse_event(document_id)

    def register_sse_callback(self, callback: Callable[[dict], None]) -> None:
        """Register callback for SSE event emission.

        Args:
            callback: Function to call when SSE event is emitted
        """
        self._sse_callbacks.append(callback)

    def unregister_sse_callback(self, callback: Callable[[dict], None]) -> None:
        """Unregister SSE callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._sse_callbacks:
            self._sse_callbacks.remove(callback)

    async def _emit_sse_event(self, document_id: str) -> None:
        """Emit SSE event if throttle allows.

        Args:
            document_id: Document identifier
        """
        now = time.time() * 1000  # ms
        last = self._last_emit.get(document_id, 0)

        if now - last < self._throttle_ms:
            return  # Throttled

        self._last_emit[document_id] = now

        progress = self._documents.get(document_id)
        if not progress:
            return

        event = progress.to_sse_event()

        for callback in self._sse_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("sse_callback_error", error=str(e))

    def get_sse_event(self, document_id: str) -> dict[str, Any] | None:
        """Get current SSE event for a document.

        Args:
            document_id: Document identifier

        Returns:
            dict[str, Any] | None: SSE event dict or None if not found
        """
        progress = self._documents.get(document_id)
        if not progress:
            return None
        return progress.to_sse_event()

    def complete_document(self, document_id: str) -> None:
        """Mark document processing as complete.

        Args:
            document_id: Document identifier
        """
        progress = self._documents.get(document_id)
        if progress:
            logger.info(
                "progress_manager_document_complete",
                document_id=document_id,
                elapsed_ms=progress.elapsed_ms,
                entities=progress.entities_extracted,
                relations=progress.relations_extracted,
            )

    def remove_document(self, document_id: str) -> None:
        """Remove document from tracking.

        Args:
            document_id: Document identifier
        """
        if document_id in self._documents:
            del self._documents[document_id]
        if document_id in self._last_emit:
            del self._last_emit[document_id]


# Singleton accessor
_progress_manager: PipelineProgressManager | None = None


def get_progress_manager() -> PipelineProgressManager:
    """Get singleton PipelineProgressManager instance.

    Returns:
        PipelineProgressManager: Singleton instance
    """
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = PipelineProgressManager()
    return _progress_manager
