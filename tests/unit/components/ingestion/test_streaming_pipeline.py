"""Unit tests for StreamingPipelineOrchestrator (Sprint 37 Feature 37.1).

Tests the core streaming pipeline architecture with AsyncIO queues.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.ingestion.pipeline_queues import (
    ChunkQueueItem,
    EmbeddedChunkItem,
    TypedQueue,
)
from src.components.ingestion.streaming_pipeline import (
    PipelineConfig,
    StreamingPipelineOrchestrator,
)


class TestTypedQueue:
    """Test TypedQueue functionality."""

    @pytest.mark.asyncio
    async def test_put_get(self):
        """Test basic put/get operations."""
        queue: TypedQueue[ChunkQueueItem] = TypedQueue(maxsize=5)

        item = ChunkQueueItem(
            chunk_id="chunk_1",
            chunk_index=0,
            text="Test chunk",
            token_count=100,
            document_id="doc_1",
            metadata={},
        )

        await queue.put(item)
        retrieved = await queue.get()

        assert retrieved is not None
        assert retrieved.chunk_id == "chunk_1"
        assert retrieved.text == "Test chunk"

    @pytest.mark.asyncio
    async def test_mark_done(self):
        """Test queue completion signaling."""
        queue: TypedQueue[ChunkQueueItem] = TypedQueue()

        # Mark done
        await queue.mark_done()

        # Next get should return None
        item = await queue.get()
        assert item is None

    @pytest.mark.asyncio
    async def test_backpressure(self):
        """Test backpressure with maxsize."""
        queue: TypedQueue[ChunkQueueItem] = TypedQueue(maxsize=2)

        item1 = ChunkQueueItem(
            chunk_id="chunk_1",
            chunk_index=0,
            text="Test",
            token_count=10,
            document_id="doc_1",
            metadata={},
        )
        item2 = ChunkQueueItem(
            chunk_id="chunk_2",
            chunk_index=1,
            text="Test",
            token_count=10,
            document_id="doc_1",
            metadata={},
        )

        # Put two items (queue is now full)
        await queue.put(item1)
        await queue.put(item2)

        # Queue should be full
        assert queue.full()

        # Verify we can still get items
        retrieved = await queue.get()
        assert retrieved.chunk_id == "chunk_1"


class TestPipelineConfig:
    """Test PipelineConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()

        assert config.chunk_queue_max_size == 10
        assert config.embedding_queue_max_size == 10
        assert config.embedding_workers == 2
        assert config.extraction_workers == 4
        assert config.vlm_workers == 1

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PipelineConfig(
            chunk_queue_max_size=20,
            embedding_workers=4,
            vlm_workers=2,
        )

        assert config.chunk_queue_max_size == 20
        assert config.embedding_workers == 4
        assert config.vlm_workers == 2


class TestStreamingPipelineOrchestrator:
    """Test StreamingPipelineOrchestrator functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test orchestrator initialization."""
        orchestrator = StreamingPipelineOrchestrator()

        assert orchestrator.config is not None
        assert orchestrator.config.chunk_queue_max_size == 10
        assert orchestrator._chunk_queue is None
        assert orchestrator._embedding_queue is None

    @pytest.mark.asyncio
    async def test_process_document_file_not_found(self):
        """Test process_document raises FileNotFoundError for missing file."""
        orchestrator = StreamingPipelineOrchestrator()

        with pytest.raises(FileNotFoundError):
            await orchestrator.process_document(
                document_path=Path("/nonexistent/file.pdf"),
                document_id="doc_1",
            )

    @pytest.mark.asyncio
    async def test_chunking_stage_with_mock_data(self):
        """Test chunking stage with mock parsed document."""
        orchestrator = StreamingPipelineOrchestrator()
        orchestrator._chunk_queue = TypedQueue[ChunkQueueItem](maxsize=10)

        # Mock parsed document with sections
        mock_doc = MagicMock()
        mock_doc.pictures = []

        results = {"chunks": [], "errors": []}

        # Mock section extraction and chunking
        with (
            patch(
                "src.components.ingestion.streaming_pipeline.extract_section_hierarchy"
            ) as mock_extract,
            patch(
                "src.components.ingestion.streaming_pipeline.adaptive_section_chunking"
            ) as mock_chunk,
        ):

            # Setup mock returns
            from src.components.ingestion.langgraph_nodes import AdaptiveChunk

            mock_extract.return_value = []  # Empty sections
            mock_chunk.return_value = [
                AdaptiveChunk(
                    text="Test chunk 1",
                    token_count=100,
                    section_headings=["Section 1"],
                    section_pages=[1],
                    section_bboxes=[{"l": 0, "t": 0, "r": 100, "b": 100}],
                    primary_section="Section 1",
                    metadata={"source": "test.pdf"},
                ),
                AdaptiveChunk(
                    text="Test chunk 2",
                    token_count=150,
                    section_headings=["Section 2"],
                    section_pages=[2],
                    section_bboxes=[{"l": 0, "t": 0, "r": 100, "b": 100}],
                    primary_section="Section 2",
                    metadata={"source": "test.pdf"},
                ),
            ]

            # Run chunking stage
            await orchestrator._chunking_stage(
                parsed_doc=mock_doc,
                document_id="doc_1",
                results=results,
                progress_callback=None,
            )

            # Verify chunks were created
            assert len(results["chunks"]) == 2
            assert results["chunks"][0].text == "Test chunk 1"
            assert results["chunks"][1].text == "Test chunk 2"

            # Verify queue was marked done
            item = await orchestrator._chunk_queue.get()
            assert item is None  # Queue should be done

    @pytest.mark.asyncio
    async def test_embedding_stage_with_workers(self):
        """Test embedding stage with parallel workers."""
        config = PipelineConfig(embedding_workers=2)
        orchestrator = StreamingPipelineOrchestrator(config)

        # Setup queues
        orchestrator._chunk_queue = TypedQueue[ChunkQueueItem](maxsize=10)
        orchestrator._embedding_queue = TypedQueue[EmbeddedChunkItem](maxsize=10)

        # Put test chunks on queue
        chunks = [
            ChunkQueueItem(
                chunk_id=f"chunk_{i}",
                chunk_index=i,
                text=f"Test chunk {i}",
                token_count=100,
                document_id="doc_1",
                metadata={},
            )
            for i in range(5)
        ]

        for chunk in chunks:
            await orchestrator._chunk_queue.put(chunk)
        await orchestrator._chunk_queue.mark_done()

        results = {"embeddings": [], "errors": []}

        # Mock embedding service
        mock_embedding = [0.1] * 1024  # 1024D embedding
        with patch(
            "src.components.ingestion.streaming_pipeline.get_embedding_service"
        ) as mock_service:
            mock_instance = AsyncMock()
            mock_instance.embed = AsyncMock(return_value=mock_embedding)
            mock_service.return_value = mock_instance

            # Run embedding stage
            await orchestrator._embedding_stage(
                document_id="doc_1",
                results=results,
                progress_callback=None,
            )

            # Verify embeddings were created
            assert len(results["embeddings"]) == 5
            assert all(len(emb) == 1024 for emb in results["embeddings"])

            # Verify embedding queue was marked done
            item = await orchestrator._embedding_queue.get()
            assert item is None

    @pytest.mark.asyncio
    async def test_progress_callbacks(self):
        """Test progress callbacks are called."""
        orchestrator = StreamingPipelineOrchestrator()
        orchestrator._chunk_queue = TypedQueue[ChunkQueueItem](maxsize=10)

        progress_updates = []

        def progress_callback(update: dict):
            progress_updates.append(update)

        # Mock parsed document
        mock_doc = MagicMock()
        results = {"chunks": [], "errors": []}

        with (
            patch(
                "src.components.ingestion.streaming_pipeline.extract_section_hierarchy"
            ) as mock_extract,
            patch(
                "src.components.ingestion.streaming_pipeline.adaptive_section_chunking"
            ) as mock_chunk,
        ):

            mock_extract.return_value = []
            mock_chunk.return_value = []

            await orchestrator._chunking_stage(
                parsed_doc=mock_doc,
                document_id="doc_1",
                results=results,
                progress_callback=progress_callback,
            )

            # Verify progress callbacks were called
            assert len(progress_updates) >= 2  # Start and end
            assert progress_updates[0]["stage"] == "chunking"
            assert progress_updates[-1]["progress"] == 1.0

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """Test errors in one chunk don't stop pipeline."""
        config = PipelineConfig(embedding_workers=1)
        orchestrator = StreamingPipelineOrchestrator(config)

        # Setup queues
        orchestrator._chunk_queue = TypedQueue[ChunkQueueItem](maxsize=10)
        orchestrator._embedding_queue = TypedQueue[EmbeddedChunkItem](maxsize=10)

        # Put test chunks on queue
        chunks = [
            ChunkQueueItem(
                chunk_id=f"chunk_{i}",
                chunk_index=i,
                text=f"Test chunk {i}",
                token_count=100,
                document_id="doc_1",
                metadata={},
            )
            for i in range(3)
        ]

        for chunk in chunks:
            await orchestrator._chunk_queue.put(chunk)
        await orchestrator._chunk_queue.mark_done()

        results = {"embeddings": [], "errors": []}

        # Mock embedding service that fails on second chunk
        call_count = 0

        async def mock_embed(text):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated embedding failure")
            return [0.1] * 1024

        with patch(
            "src.components.ingestion.streaming_pipeline.get_embedding_service"
        ) as mock_service:
            mock_instance = AsyncMock()
            mock_instance.embed = mock_embed
            mock_service.return_value = mock_instance

            # Run embedding stage
            await orchestrator._embedding_stage(
                document_id="doc_1",
                results=results,
                progress_callback=None,
            )

            # Verify some embeddings were created despite error
            assert len(results["embeddings"]) == 2  # 2 succeeded, 1 failed
            assert len(results["errors"]) == 1  # 1 error recorded
            assert "chunk_1" in results["errors"][0]["chunk_id"]


@pytest.mark.asyncio
async def test_queue_consumer_producer_pattern():
    """Test typical consumer-producer pattern with queues."""
    queue: TypedQueue[int] = TypedQueue(maxsize=5)

    # Producer task
    async def producer():
        for i in range(10):
            await queue.put(i)
            await asyncio.sleep(0.01)  # Simulate work
        await queue.mark_done()

    # Consumer task
    consumed = []

    async def consumer():
        while True:
            item = await queue.get()
            if item is None:
                break
            consumed.append(item)
            await asyncio.sleep(0.02)  # Simulate slower consumer

    # Run producer and consumer concurrently
    await asyncio.gather(producer(), consumer())

    # Verify all items were consumed
    assert consumed == list(range(10))
