"""Multi-Document Progress Aggregation (Sprint 37 Feature 37.8).

Aggregates progress from multiple parallel document processing tasks.

Architecture:
  - DocumentProgress: Per-document status tracking
  - BatchProgress: Aggregated batch statistics
  - MultiDocProgressManager: Singleton manager for batch tracking
  - SSE event generation: Real-time frontend updates

Progress States:
  - pending: Document queued but not started
  - processing: Document currently being processed
  - completed: Document successfully processed
  - error: Document processing failed

Use Cases:
  - Admin UI: Real-time progress for multi-document batch indexing
  - API: Stream batch progress via SSE
  - Error tracking: Isolated failures don't stop batch

Example:
    >>> manager = get_multi_doc_progress_manager()
    >>> documents = [
    ...     {"id": "doc1", "name": "report.pdf", "path": "/data/report.pdf"},
    ...     {"id": "doc2", "name": "slides.pptx", "path": "/data/slides.pptx"},
    ... ]
    >>> batch = manager.start_batch("batch-123", documents, parallel_limit=3)
    >>> manager.update_document("batch-123", "doc1", status="completed", progress_percent=100.0)
    >>> event = batch.to_sse_event()

Notes:
  - Singleton pattern: Global state for batch tracking
  - Thread-safe: Uses dict operations (GIL protection)
  - Memory cleanup: Call remove_batch() after completion
  - Designed for ParallelIngestionOrchestrator integration
"""

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DocumentProgress:
    """Progress for a single document.

    Attributes:
        document_id: Unique document identifier
        document_name: Display name (filename)
        file_path: Full path to document
        status: Current processing status (pending/processing/completed/error)
        progress_percent: Overall progress (0-100)
        chunks_created: Number of chunks created
        entities_extracted: Number of entities extracted
        relations_extracted: Number of relations extracted
        error: Error message if status is "error"

    Example:
        >>> doc = DocumentProgress(
        ...     document_id="doc1",
        ...     document_name="report.pdf",
        ...     file_path="/data/report.pdf",
        ...     status="completed",
        ...     progress_percent=100.0,
        ...     chunks_created=42,
        ... )
    """

    document_id: str
    document_name: str
    file_path: str
    status: str = "pending"  # pending, processing, completed, error
    progress_percent: float = 0.0
    chunks_created: int = 0
    entities_extracted: int = 0
    relations_extracted: int = 0
    error: str | None = None


@dataclass
class BatchProgress:
    """Aggregated progress for a batch of documents.

    Attributes:
        batch_id: Unique batch identifier
        total_documents: Total number of documents in batch
        parallel_limit: Maximum concurrent documents (default 3)
        documents: Dict of document_id -> DocumentProgress

    Properties:
        completed_count: Number of completed documents
        in_progress_count: Number of documents currently processing
        failed_count: Number of failed documents
        overall_progress_percent: Average progress across all documents

    Example:
        >>> batch = BatchProgress(batch_id="batch-123", total_documents=5, parallel_limit=3)
        >>> batch.documents["doc1"] = DocumentProgress(...)
        >>> batch.completed_count
        0
        >>> batch.overall_progress_percent
        0.0
    """

    batch_id: str
    total_documents: int
    parallel_limit: int
    documents: dict[str, DocumentProgress] = field(default_factory=dict)

    @property
    def completed_count(self) -> int:
        """Count documents with status "completed"."""
        return sum(1 for d in self.documents.values() if d.status == "completed")

    @property
    def in_progress_count(self) -> int:
        """Count documents with status "processing"."""
        return sum(1 for d in self.documents.values() if d.status == "processing")

    @property
    def failed_count(self) -> int:
        """Count documents with status "error"."""
        return sum(1 for d in self.documents.values() if d.status == "error")

    @property
    def overall_progress_percent(self) -> float:
        """Calculate average progress across all documents.

        Returns:
            Float between 0.0 and 100.0

        Example:
            >>> batch = BatchProgress(batch_id="b1", total_documents=2, parallel_limit=3)
            >>> batch.documents["d1"] = DocumentProgress(..., progress_percent=50.0)
            >>> batch.documents["d2"] = DocumentProgress(..., progress_percent=100.0)
            >>> batch.overall_progress_percent
            75.0
        """
        if not self.documents:
            return 0.0
        total = sum(d.progress_percent for d in self.documents.values())
        return total / len(self.documents)

    def to_sse_event(self) -> dict[str, Any]:
        """Convert batch progress to SSE event format.

        Returns:
            Dict with "type" and "data" keys for SSE streaming

        Example:
            >>> batch = BatchProgress(...)
            >>> event = batch.to_sse_event()
            >>> event["type"]
            'batch_progress'
            >>> event["data"]["batch_id"]
            'batch-123'
        """
        return {
            "type": "batch_progress",
            "data": {
                "batch_id": self.batch_id,
                "total_documents": self.total_documents,
                "parallel_limit": self.parallel_limit,
                "completed": self.completed_count,
                "in_progress": self.in_progress_count,
                "failed": self.failed_count,
                "overall_progress_percent": round(self.overall_progress_percent, 1),
                "documents": [
                    {
                        "document_id": d.document_id,
                        "document_name": d.document_name,
                        "status": d.status,
                        "progress_percent": round(d.progress_percent, 1),
                        "chunks_created": d.chunks_created,
                        "entities_extracted": d.entities_extracted,
                        "error": d.error,
                    }
                    for d in self.documents.values()
                ],
            },
        }


class MultiDocProgressManager:
    """Manages progress for multi-document batch processing.

    Singleton pattern to maintain global batch state across API requests.

    Attributes:
        _batches: Dict of batch_id -> BatchProgress

    Methods:
        start_batch: Initialize batch tracking
        update_document: Update single document progress
        get_batch: Retrieve batch by ID
        remove_batch: Clean up completed batch

    Example:
        >>> manager = MultiDocProgressManager()
        >>> batch = manager.start_batch("batch-1", documents=[...], parallel_limit=3)
        >>> manager.update_document("batch-1", "doc1", status="completed", progress_percent=100.0)
        >>> batch = manager.get_batch("batch-1")
        >>> manager.remove_batch("batch-1")
    """

    _instance: "MultiDocProgressManager | None" = None
    _batches: dict[str, BatchProgress]

    def __new__(cls) -> "MultiDocProgressManager":
        """Singleton constructor."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._batches = {}
            cls._instance = instance
        return cls._instance

    def start_batch(
        self,
        batch_id: str,
        documents: list[dict[str, str]],  # [{"id": ..., "name": ..., "path": ...}]
        parallel_limit: int = 3,
    ) -> BatchProgress:
        """Start tracking a new batch.

        Args:
            batch_id: Unique identifier for batch
            documents: List of dicts with "id", "name", "path" keys
            parallel_limit: Maximum concurrent documents (default 3)

        Returns:
            BatchProgress instance

        Example:
            >>> manager = MultiDocProgressManager()
            >>> documents = [
            ...     {"id": "d1", "name": "report.pdf", "path": "/data/report.pdf"},
            ...     {"id": "d2", "name": "slides.pptx", "path": "/data/slides.pptx"},
            ... ]
            >>> batch = manager.start_batch("batch-1", documents, parallel_limit=3)
            >>> batch.total_documents
            2
        """
        batch = BatchProgress(
            batch_id=batch_id,
            total_documents=len(documents),
            parallel_limit=parallel_limit,
        )

        for doc in documents:
            batch.documents[doc["id"]] = DocumentProgress(
                document_id=doc["id"],
                document_name=doc["name"],
                file_path=doc["path"],
            )

        self._batches[batch_id] = batch

        logger.info(
            "batch_started",
            batch_id=batch_id,
            total_documents=len(documents),
            parallel_limit=parallel_limit,
        )

        return batch

    def update_document(
        self,
        batch_id: str,
        document_id: str,
        status: str | None = None,
        progress_percent: float | None = None,
        chunks_created: int | None = None,
        entities_extracted: int | None = None,
        relations_extracted: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update progress for a single document in a batch.

        Args:
            batch_id: Batch identifier
            document_id: Document identifier
            status: New status (pending/processing/completed/error)
            progress_percent: Progress percentage (0-100)
            chunks_created: Number of chunks created
            entities_extracted: Number of entities extracted
            relations_extracted: Number of relations extracted
            error: Error message (for status="error")

        Example:
            >>> manager = MultiDocProgressManager()
            >>> manager.update_document(
            ...     "batch-1",
            ...     "doc1",
            ...     status="completed",
            ...     progress_percent=100.0,
            ...     chunks_created=42,
            ... )
        """
        batch = self._batches.get(batch_id)
        if not batch:
            logger.warning("batch_not_found", batch_id=batch_id)
            return

        doc = batch.documents.get(document_id)
        if not doc:
            logger.warning("document_not_found", batch_id=batch_id, document_id=document_id)
            return

        if status is not None:
            doc.status = status
        if progress_percent is not None:
            doc.progress_percent = progress_percent
        if chunks_created is not None:
            doc.chunks_created = chunks_created
        if entities_extracted is not None:
            doc.entities_extracted = entities_extracted
        if relations_extracted is not None:
            doc.relations_extracted = relations_extracted
        if error is not None:
            doc.error = error

    def get_batch(self, batch_id: str) -> BatchProgress | None:
        """Retrieve batch by ID.

        Args:
            batch_id: Batch identifier

        Returns:
            BatchProgress if found, None otherwise

        Example:
            >>> manager = MultiDocProgressManager()
            >>> batch = manager.get_batch("batch-1")
        """
        return self._batches.get(batch_id)

    def remove_batch(self, batch_id: str) -> None:
        """Clean up completed batch.

        Args:
            batch_id: Batch identifier

        Example:
            >>> manager = MultiDocProgressManager()
            >>> manager.remove_batch("batch-1")
        """
        if batch_id in self._batches:
            del self._batches[batch_id]
            logger.info("batch_removed", batch_id=batch_id)


def get_multi_doc_progress_manager() -> MultiDocProgressManager:
    """Get singleton MultiDocProgressManager instance.

    Returns:
        Global MultiDocProgressManager instance

    Example:
        >>> manager = get_multi_doc_progress_manager()
        >>> batch = manager.start_batch("batch-1", documents=[...])
    """
    return MultiDocProgressManager()
