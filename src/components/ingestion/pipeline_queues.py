"""Pipeline Queue Management (Sprint 37 Feature 37.1).

Provides typed queues and sentinel values for pipeline stage coordination.

Architecture:
  - Type-safe async queue wrappers
  - Sentinel value for signaling completion
  - Queue item dataclasses for type safety
  - Support for backpressure via maxsize

Usage:
    >>> chunk_queue = TypedQueue[ChunkQueueItem](maxsize=10)
    >>> await chunk_queue.put(ChunkQueueItem(...))
    >>> item = await chunk_queue.get()  # Returns ChunkQueueItem or None (if done)
    >>> await chunk_queue.mark_done()  # Signal no more items
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")

# Sentinel value to signal queue completion
QUEUE_DONE = object()


@dataclass
class ChunkQueueItem:
    """Item in the chunk queue between chunking and embedding stages.

    Attributes:
        chunk_id: Unique identifier for this chunk
        chunk_index: Index in document (0-based)
        text: Chunk text content
        token_count: Number of tokens in chunk
        document_id: Parent document identifier
        metadata: Additional metadata (section headings, pages, bboxes)
    """

    chunk_id: str
    chunk_index: int
    text: str
    token_count: int
    document_id: str
    metadata: dict[str, Any]


@dataclass
class EmbeddedChunkItem:
    """Item in the embedding queue between embedding and extraction stages.

    Attributes:
        chunk_id: Unique identifier for this chunk
        chunk_index: Index in document (0-based)
        text: Chunk text content
        embedding: Vector embedding (1024D for BGE-M3)
        token_count: Number of tokens in chunk
        document_id: Parent document identifier
        metadata: Additional metadata (section headings, pages, bboxes)
    """

    chunk_id: str
    chunk_index: int
    text: str
    embedding: list[float]
    token_count: int
    document_id: str
    metadata: dict[str, Any]


@dataclass
class ExtractionQueueItem:
    """Item in the extraction queue for graph extraction stage.

    Attributes:
        chunk_id: Unique identifier for this chunk
        chunk_index: Index in document (0-based)
        text: Chunk text content
        embedding: Vector embedding (1024D for BGE-M3)
        qdrant_point_id: UUID of uploaded Qdrant point
        document_id: Parent document identifier
        metadata: Additional metadata (section headings, pages, bboxes)
    """

    chunk_id: str
    chunk_index: int
    text: str
    embedding: list[float]
    qdrant_point_id: str
    document_id: str
    metadata: dict[str, Any]


class TypedQueue(Generic[T]):
    """Type-safe async queue wrapper with sentinel support.

    Provides type-safe access to asyncio.Queue with automatic completion signaling.
    Supports backpressure via maxsize parameter.

    Example:
        >>> queue: TypedQueue[ChunkQueueItem] = TypedQueue(maxsize=10)
        >>> await queue.put(ChunkQueueItem(...))
        >>> item = await queue.get()  # Returns ChunkQueueItem | None
        >>> if item is None:
        ...     print("Queue is done")
    """

    def __init__(self, maxsize: int = 0):
        """Initialize typed queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited, >0 enables backpressure)
        """
        self._queue: asyncio.Queue[T | object] = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: T) -> None:
        """Put an item on the queue.

        Blocks if queue is full (backpressure).

        Args:
            item: Item to put on queue
        """
        await self._queue.put(item)

    async def get(self) -> T | None:
        """Get an item from the queue.

        Returns:
            Item from queue, or None if queue is done (QUEUE_DONE sentinel received)
        """
        item = await self._queue.get()
        if item is QUEUE_DONE:
            return None
        return item  # type: ignore[return-value]

    async def mark_done(self) -> None:
        """Signal that no more items will be added.

        Producer should call this when finished to notify consumers.
        """
        await self._queue.put(QUEUE_DONE)

    def qsize(self) -> int:
        """Return approximate queue size.

        Returns:
            Number of items currently in queue
        """
        return self._queue.qsize()

    def empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if queue is empty, False otherwise
        """
        return self._queue.empty()

    def full(self) -> bool:
        """Check if queue is full.

        Returns:
            True if queue is full, False otherwise
        """
        return self._queue.full()


__all__ = [
    "QUEUE_DONE",
    "ChunkQueueItem",
    "EmbeddedChunkItem",
    "ExtractionQueueItem",
    "TypedQueue",
]
