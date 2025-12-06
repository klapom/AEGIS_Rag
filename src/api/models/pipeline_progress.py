"""Pipeline Progress SSE Schema (Sprint 37 Feature 37.5).

Pydantic models for SSE event serialization in document ingestion pipeline.

This module defines the schema for real-time pipeline progress updates streamed
to the frontend during document ingestion. The schema matches the frontend's
PipelineProgressData interface for seamless integration.

Models:
    - StageProgressSchema: Progress for a single pipeline stage
    - WorkerInfoSchema: Status of a single extraction worker
    - WorkerPoolSchema: Worker pool status
    - MetricsSchema: Live extraction metrics
    - TimingSchema: Timing information
    - PipelineProgressEventData: Complete progress data payload
    - PipelineProgressEvent: SSE event wrapper

Example SSE Event:
    ```json
    {
        "type": "pipeline_progress",
        "data": {
            "document_id": "doc-123",
            "document_name": "report.pdf",
            "total_chunks": 32,
            "total_images": 5,
            "stages": {
                "parsing": {
                    "name": "parsing",
                    "status": "completed",
                    "processed": 1,
                    "total": 1,
                    "in_flight": 0,
                    "progress_percent": 100.0,
                    "duration_ms": 1200,
                    "is_complete": true
                },
                "extraction": {
                    "name": "extraction",
                    "status": "in_progress",
                    "processed": 15,
                    "total": 32,
                    "in_flight": 4,
                    "progress_percent": 46.9,
                    "duration_ms": 8500,
                    "is_complete": false
                }
            },
            "worker_pool": {
                "active": 4,
                "max": 4,
                "queue_depth": 13,
                "workers": [
                    {
                        "id": 0,
                        "status": "processing",
                        "current_chunk": "chunk-15",
                        "progress_percent": 75.0
                    }
                ]
            },
            "metrics": {
                "entities_total": 42,
                "relations_total": 28,
                "neo4j_writes": 70,
                "qdrant_writes": 15
            },
            "timing": {
                "started_at": 1701234567.89,
                "elapsed_ms": 12500,
                "estimated_remaining_ms": 14200
            },
            "overall_progress_percent": 46.9
        }
    }
    ```

See Also:
    - src/components/ingestion/progress_manager.py: PipelineProgressManager implementation
    - src/api/v1/admin.py: SSE endpoint using these models
    - frontend/src/types/admin.ts: Frontend interface (PipelineProgressData)
"""

from typing import Dict

from pydantic import BaseModel, Field


class StageProgressSchema(BaseModel):
    """Progress for a single pipeline stage.

    Tracks the processing state of one stage in the ingestion pipeline
    (parsing, vlm, chunking, embedding, extraction).

    Attributes:
        name: Stage name (parsing, vlm, chunking, embedding, extraction)
        status: Stage status (pending, in_progress, completed, error)
        processed: Number of items processed
        total: Total number of items to process
        in_flight: Number of items currently being processed
        progress_percent: Progress percentage (0-100)
        duration_ms: Duration in milliseconds (0 if not started)
        is_complete: Whether stage is completed

    Example:
        >>> stage = StageProgressSchema(
        ...     name="extraction",
        ...     status="in_progress",
        ...     processed=15,
        ...     total=32,
        ...     in_flight=4,
        ...     progress_percent=46.9,
        ...     duration_ms=8500,
        ...     is_complete=False
        ... )
        >>> stage.progress_percent
        46.9
    """

    name: str = Field(..., description="Stage name")
    status: str = Field(..., description="pending, in_progress, completed, error")
    processed: int = Field(..., description="Number of items processed")
    total: int = Field(..., description="Total number of items")
    in_flight: int = Field(..., description="Items currently being processed")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    is_complete: bool = Field(..., description="Whether stage is completed")


class WorkerInfoSchema(BaseModel):
    """Status of a single extraction worker.

    Tracks the state of one worker thread in the parallel extraction pool.

    Attributes:
        id: Worker ID (0-indexed)
        status: Worker status (idle, processing, error)
        current_chunk: Chunk ID currently being processed (null if idle)
        progress_percent: Progress on current chunk (0-100)

    Example:
        >>> worker = WorkerInfoSchema(
        ...     id=0,
        ...     status="processing",
        ...     current_chunk="chunk-15",
        ...     progress_percent=75.0
        ... )
        >>> worker.status
        'processing'
    """

    id: int = Field(..., description="Worker ID")
    status: str = Field(..., description="idle, processing, error")
    current_chunk: str | None = Field(None, description="Current chunk ID (null if idle)")
    progress_percent: float = Field(0.0, description="Progress on current chunk (0-100)")


class WorkerPoolSchema(BaseModel):
    """Worker pool status.

    Tracks the overall state of the parallel extraction worker pool.

    Attributes:
        active: Number of active workers (currently processing)
        max: Maximum number of workers
        queue_depth: Number of chunks waiting in queue
        workers: List of worker statuses

    Example:
        >>> pool = WorkerPoolSchema(
        ...     active=4,
        ...     max=4,
        ...     queue_depth=13,
        ...     workers=[WorkerInfoSchema(id=0, status="processing", current_chunk="chunk-1")]
        ... )
        >>> pool.queue_depth
        13
    """

    active: int = Field(..., description="Number of active workers")
    max: int = Field(..., description="Maximum number of workers")
    queue_depth: int = Field(..., description="Chunks waiting in queue")
    workers: list[WorkerInfoSchema] = Field(..., description="Worker statuses")


class MetricsSchema(BaseModel):
    """Live extraction metrics.

    Tracks cumulative metrics during graph extraction.

    Attributes:
        entities_total: Total entities extracted
        relations_total: Total relations extracted
        neo4j_writes: Total Neo4j write operations
        qdrant_writes: Total Qdrant write operations

    Example:
        >>> metrics = MetricsSchema(
        ...     entities_total=42,
        ...     relations_total=28,
        ...     neo4j_writes=70,
        ...     qdrant_writes=15
        ... )
        >>> metrics.entities_total
        42
    """

    entities_total: int = Field(..., description="Total entities extracted")
    relations_total: int = Field(..., description="Total relations extracted")
    neo4j_writes: int = Field(..., description="Total Neo4j writes")
    qdrant_writes: int = Field(..., description="Total Qdrant writes")


class TimingSchema(BaseModel):
    """Timing information.

    Tracks elapsed time and estimated remaining time.

    Attributes:
        started_at: Unix timestamp when processing started
        elapsed_ms: Milliseconds elapsed since start
        estimated_remaining_ms: Estimated milliseconds remaining (0 if unknown)

    Example:
        >>> timing = TimingSchema(
        ...     started_at=1701234567.89,
        ...     elapsed_ms=12500,
        ...     estimated_remaining_ms=14200
        ... )
        >>> timing.elapsed_ms
        12500
    """

    started_at: float = Field(..., description="Unix timestamp when processing started")
    elapsed_ms: int = Field(..., description="Milliseconds elapsed since start")
    estimated_remaining_ms: int = Field(
        ..., description="Estimated milliseconds remaining (0 if unknown)"
    )


class PipelineProgressEventData(BaseModel):
    """Data payload for pipeline progress SSE event.

    Complete progress state for a document being processed. This matches
    the frontend PipelineProgressData interface exactly.

    Attributes:
        document_id: Unique document identifier (job ID)
        document_name: Human-readable document name
        total_chunks: Total number of chunks to process
        total_images: Total number of images to process
        stages: Stage progress (dict: stage_name -> StageProgressSchema)
        worker_pool: Worker pool status
        metrics: Live extraction metrics
        timing: Timing information
        overall_progress_percent: Overall progress across all stages (0-100)

    Example:
        >>> data = PipelineProgressEventData(
        ...     document_id="doc-123",
        ...     document_name="report.pdf",
        ...     total_chunks=32,
        ...     total_images=5,
        ...     stages={
        ...         "parsing": StageProgressSchema(
        ...             name="parsing", status="completed", processed=1, total=1,
        ...             in_flight=0, progress_percent=100.0, duration_ms=1200, is_complete=True
        ...         )
        ...     },
        ...     worker_pool=WorkerPoolSchema(active=0, max=4, queue_depth=0, workers=[]),
        ...     metrics=MetricsSchema(entities_total=0, relations_total=0, neo4j_writes=0, qdrant_writes=0),
        ...     timing=TimingSchema(started_at=1701234567.89, elapsed_ms=1200, estimated_remaining_ms=0),
        ...     overall_progress_percent=20.0
        ... )
        >>> data.document_name
        'report.pdf'
    """

    document_id: str = Field(..., description="Unique document identifier")
    document_name: str = Field(..., description="Document name")
    total_chunks: int = Field(..., description="Total number of chunks")
    total_images: int = Field(..., description="Total number of images")
    stages: Dict[str, StageProgressSchema] = Field(..., description="Stage progress")
    worker_pool: WorkerPoolSchema = Field(..., description="Worker pool status")
    metrics: MetricsSchema = Field(..., description="Live metrics")
    timing: TimingSchema = Field(..., description="Timing information")
    overall_progress_percent: float = Field(
        ..., description="Overall progress across all stages (0-100)"
    )


class PipelineProgressEvent(BaseModel):
    """Complete SSE event for pipeline progress.

    Wrapper for SSE event containing pipeline progress data.

    Attributes:
        type: Event type (always "pipeline_progress")
        data: Progress data payload

    Example:
        >>> event = PipelineProgressEvent(
        ...     type="pipeline_progress",
        ...     data=PipelineProgressEventData(...)
        ... )
        >>> event.type
        'pipeline_progress'
    """

    type: str = Field(
        default="pipeline_progress", description='Event type (always "pipeline_progress")'
    )
    data: PipelineProgressEventData = Field(..., description="Progress data payload")
