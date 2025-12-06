"""Integration tests for Sprint 37 Streaming Pipeline.

Tests the interaction between:
- StreamingPipelineOrchestrator
- GraphExtractionWorkerPool
- PipelineProgressManager
- TypedQueue (backpressure handling)

Test Markers:
- @pytest.mark.integration: Full component integration
- @pytest.mark.asyncio: Async test functions
- @pytest.mark.slow: Tests taking >5 seconds

Architecture Under Test:
    Docling Parse → VLM → Chunking → Embedding → Graph Extraction
                                        ↓            ↓              ↓
                                    chunk_queue  embed_queue  extraction_queue
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.ingestion.extraction_worker_pool import (
    ExtractionResult,
    GraphExtractionWorkerPool,
    WorkerPoolConfig,
    WorkerStatus,
)
from src.components.ingestion.progress_manager import (
    PipelineProgressManager,
    StageProgress,
    StageStatus,
    get_progress_manager,
)
from src.components.ingestion.pipeline_queues import (
    ChunkQueueItem,
    EmbeddedChunkItem,
    TypedQueue,
)
from src.components.ingestion.streaming_pipeline import (
    PipelineConfig,
    StreamingPipelineOrchestrator,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def progress_manager():
    """Get fresh progress manager for each test."""
    manager = get_progress_manager()
    # Clear any existing state
    manager._documents.clear()
    manager._last_emit.clear()
    yield manager
    # Cleanup after test
    manager._documents.clear()
    manager._last_emit.clear()


@pytest.fixture
def pipeline_config():
    """Standard pipeline configuration for testing."""
    return PipelineConfig(
        chunk_queue_max_size=5,
        embedding_queue_max_size=5,
        embedding_workers=2,
        extraction_workers=2,
        vlm_workers=1,
        embedding_timeout=30,
        extraction_timeout=60,
        vlm_timeout=90,
    )


@pytest.fixture
def worker_pool_config():
    """Standard worker pool configuration for testing."""
    return WorkerPoolConfig(
        num_workers=2,
        chunk_timeout_seconds=30,
        max_retries=1,
        max_concurrent_llm_calls=4,
    )


@pytest.fixture
def sample_chunks():
    """Generate sample chunk data for testing."""
    return [
        {
            "chunk_id": "c0",
            "chunk_index": 0,
            "text": "Entity1 works at Organization1. They collaborate with Entity2.",
            "token_count": 15,
            "document_id": "doc1",
            "metadata": {"section": "intro", "page": 1},
        },
        {
            "chunk_id": "c1",
            "chunk_index": 1,
            "text": "Entity3 is located in City1. This relates to Entity1's project.",
            "token_count": 14,
            "document_id": "doc1",
            "metadata": {"section": "location", "page": 2},
        },
        {
            "chunk_id": "c2",
            "chunk_index": 2,
            "text": "The meeting involved Entity4 and Entity5 discussing technology.",
            "token_count": 12,
            "document_id": "doc1",
            "metadata": {"section": "meeting", "page": 3},
        },
    ]


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    service = AsyncMock()

    async def mock_embed(text: str) -> list[float]:
        """Return consistent embedding based on text length."""
        # Simulate real embedding: 1024-dim BGE-M3
        base_val = len(text) / 1000.0
        return [base_val + (i % 10) / 100.0 for i in range(1024)]

    service.embed = mock_embed
    return service


@pytest.fixture
def mock_extractor():
    """Mock relation extractor for testing."""
    extractor = AsyncMock()

    async def mock_extract(chunk_text: str, entities: list) -> tuple[list, list]:
        """Return mock extracted entities and relations."""
        # Parse simple entities from text
        entities = [
            {"name": "Entity1", "type": "PERSON"},
            {"name": "Organization1", "type": "ORG"},
        ]
        relations = [
            {
                "source": "Entity1",
                "target": "Organization1",
                "type": "WORKS_AT",
                "strength": 0.9,
            }
        ]
        return entities, relations

    extractor.extract = mock_extract
    extractor.model = "test-model"
    extractor.temperature = 0.7
    return extractor


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.integration
class TestPipelineProgressManagerIntegration:
    """Integration tests for PipelineProgressManager."""

    def test_start_document_creates_tracker(self, progress_manager):
        """Test starting a document creates progress tracker."""
        doc_id = "test-doc-1"
        progress = progress_manager.start_document(doc_id, "test.pdf")

        assert progress.document_id == doc_id
        assert progress.document_name == "test.pdf"
        assert progress.total_chunks == 0
        assert progress.max_workers == 4

    def test_start_document_with_metadata(self, progress_manager):
        """Test starting document with chunk and image counts."""
        doc_id = "test-doc-2"
        progress = progress_manager.start_document(
            doc_id, "report.pdf", total_chunks=32, total_images=10, max_workers=6
        )

        assert progress.total_chunks == 32
        assert progress.total_images == 10
        assert progress.max_workers == 6
        assert len(progress.workers) == 6

    @pytest.mark.asyncio
    async def test_update_stage_progress(self, progress_manager):
        """Test updating stage progress."""
        doc_id = "test-doc-3"
        progress_manager.start_document(doc_id, "doc.pdf", total_chunks=20)

        await progress_manager.update_stage(
            doc_id,
            "chunking",
            status=StageStatus.IN_PROGRESS,
            total=20,
            processed=0,
        )

        progress = progress_manager.get_progress(doc_id)
        assert progress.chunking.status == StageStatus.IN_PROGRESS
        assert progress.chunking.total == 20

    @pytest.mark.asyncio
    async def test_stage_completion_tracking(self, progress_manager):
        """Test stage completion tracking and timing."""
        doc_id = "test-doc-4"
        progress_manager.start_document(doc_id, "doc.pdf")

        # Start stage
        await progress_manager.update_stage(
            doc_id,
            "parsing",
            status=StageStatus.IN_PROGRESS,
        )

        await asyncio.sleep(0.1)  # Simulate work

        # Complete stage
        await progress_manager.update_stage(
            doc_id, "parsing", status=StageStatus.COMPLETED, processed=1, total=1
        )

        progress = progress_manager.get_progress(doc_id)
        assert progress.parsing.is_complete
        assert progress.parsing.progress_percent == 100.0
        assert progress.parsing.duration_ms > 50  # At least 50ms of work

    @pytest.mark.asyncio
    async def test_sse_event_format(self, progress_manager):
        """Test SSE event format matches frontend expectations."""
        doc_id = "test-doc-5"
        progress_manager.start_document(
            doc_id,
            "report.pdf",
            total_chunks=32,
            total_images=5,
            max_workers=4,
        )

        await progress_manager.update_stage(
            doc_id,
            "chunking",
            status=StageStatus.IN_PROGRESS,
            total=32,
            processed=16,
        )

        event = progress_manager.get_sse_event(doc_id)

        # Verify SSE structure
        assert event["type"] == "pipeline_progress"
        assert "data" in event

        data = event["data"]
        assert data["document_id"] == doc_id
        assert data["document_name"] == "report.pdf"
        assert data["total_chunks"] == 32
        assert data["total_images"] == 5
        assert "stages" in data
        assert "worker_pool" in data
        assert "metrics" in data
        assert "timing" in data

        # Verify stage format
        chunking = data["stages"]["chunking"]
        assert chunking["processed"] == 16
        assert chunking["total"] == 32
        assert chunking["progress_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_overall_progress_calculation(self, progress_manager):
        """Test overall progress across multiple stages."""
        doc_id = "test-doc-6"
        progress_manager.start_document(doc_id, "doc.pdf")

        # Update multiple stages
        await progress_manager.update_stage(
            doc_id,
            "parsing",
            status=StageStatus.COMPLETED,
            processed=1,
            total=1,
        )

        await progress_manager.update_stage(
            doc_id,
            "chunking",
            status=StageStatus.IN_PROGRESS,
            processed=10,
            total=20,
        )

        progress = progress_manager.get_progress(doc_id)
        # parsing = 100%, chunking = 50%, others = 0%
        # Average: (100 + 50) / 2 = 75%
        assert progress.overall_progress_percent == 75.0

    @pytest.mark.asyncio
    async def test_eta_calculation(self, progress_manager):
        """Test estimated remaining time calculation."""
        doc_id = "test-doc-7"
        progress_manager.start_document(doc_id, "doc.pdf")

        # Manually set the started_at to simulate elapsed time
        progress = progress_manager.start_document(doc_id, "doc.pdf")
        progress.started_at = time.time() - 2.0  # 2 seconds ago

        await progress_manager.update_stage(
            doc_id,
            "embedding",
            status=StageStatus.IN_PROGRESS,
            processed=40,
            total=100,
        )

        # Get updated progress
        progress = progress_manager.get_progress(doc_id)
        # With 40% done in ~2 seconds, ETA should be ~3 more seconds
        eta_ms = progress.estimated_remaining_ms
        assert eta_ms > 0  # Should have positive ETA

    @pytest.mark.asyncio
    async def test_worker_status_updates(self, progress_manager):
        """Test updating worker pool status."""
        doc_id = "test-doc-8"
        progress_manager.start_document(doc_id, "doc.pdf", max_workers=4)

        workers = [
            WorkerStatus(worker_id=0, status="processing", current_chunk_id="c0"),
            WorkerStatus(worker_id=1, status="idle"),
            WorkerStatus(worker_id=2, status="processing", current_chunk_id="c1"),
            WorkerStatus(worker_id=3, status="idle"),
        ]

        await progress_manager.update_workers(doc_id, workers, queue_depth=5)

        progress = progress_manager.get_progress(doc_id)
        assert len(progress.workers) == 4
        assert progress.queue_depth == 5

        # Verify worker details in SSE event
        event = progress_manager.get_sse_event(doc_id)
        worker_pool = event["data"]["worker_pool"]
        assert worker_pool["active"] == 2  # 2 processing
        assert worker_pool["queue_depth"] == 5

    @pytest.mark.asyncio
    async def test_metrics_updates(self, progress_manager):
        """Test updating extraction metrics."""
        doc_id = "test-doc-9"
        progress_manager.start_document(doc_id, "doc.pdf")

        await progress_manager.update_metrics(
            doc_id,
            entities=42,
            relations=15,
            neo4j_writes=100,
            qdrant_writes=50,
        )

        progress = progress_manager.get_progress(doc_id)
        assert progress.entities_extracted == 42
        assert progress.relations_extracted == 15
        assert progress.neo4j_writes == 100
        assert progress.qdrant_writes == 50

        # Verify in SSE event
        event = progress_manager.get_sse_event(doc_id)
        metrics = event["data"]["metrics"]
        assert metrics["entities_total"] == 42
        assert metrics["relations_total"] == 15

    @pytest.mark.asyncio
    async def test_remove_document(self, progress_manager):
        """Test removing document from tracking."""
        doc_id = "test-doc-10"
        progress_manager.start_document(doc_id, "doc.pdf")

        assert progress_manager.get_progress(doc_id) is not None

        progress_manager.remove_document(doc_id)

        assert progress_manager.get_progress(doc_id) is None


@pytest.mark.integration
class TestWorkerPoolIntegration:
    """Integration tests for GraphExtractionWorkerPool."""

    @pytest.mark.asyncio
    async def test_worker_pool_parallel_execution(
        self, worker_pool_config, sample_chunks, mock_extractor
    ):
        """Test worker pool processes chunks in parallel."""
        pool = GraphExtractionWorkerPool(config=worker_pool_config, extractor=mock_extractor)

        # Track execution times
        call_times = []

        async def mock_extract_with_timing(chunk_text, entities):
            call_times.append(time.time())
            await asyncio.sleep(0.05)  # Simulate LLM work
            return [{"name": "Entity1"}], [{"source": "E1", "target": "E2"}]

        mock_extractor.extract = mock_extract_with_timing

        # Process chunks
        results = []
        async for result in pool.process_chunks(sample_chunks):
            results.append(result)

        assert len(results) == 3
        assert all(r.success for r in results)

        # Verify parallel execution (first 2 should start nearly simultaneously)
        if len(call_times) >= 2:
            time_spread = max(call_times[:2]) - min(call_times[:2])
            assert time_spread < 0.1  # Should start within 100ms (parallel)

    @pytest.mark.asyncio
    async def test_worker_status_tracking(self, worker_pool_config, mock_extractor):
        """Test worker status updates during processing."""
        pool = GraphExtractionWorkerPool(config=worker_pool_config, extractor=mock_extractor)

        chunks = [
            {"chunk_id": f"c{i}", "text": f"text {i}", "document_id": "d1"}
            for i in range(4)
        ]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

            # Check worker statuses
            statuses = pool.worker_statuses
            assert all(w.status in ["idle", "processing"] for w in statuses)

        # All workers should be idle after completion
        statuses = pool.worker_statuses
        assert all(w.status == "idle" for w in statuses)
        assert sum(w.chunks_processed for w in statuses) == 4

    @pytest.mark.asyncio
    async def test_error_isolation_between_chunks(
        self, worker_pool_config, mock_extractor
    ):
        """Test errors in one chunk don't stop other chunks."""
        pool = GraphExtractionWorkerPool(config=worker_pool_config, extractor=mock_extractor)

        call_count = 0

        async def mock_extract_with_error(chunk_text, entities):
            nonlocal call_count
            call_count += 1
            if "error" in chunk_text:
                raise ValueError("Simulated extraction error")
            return [{"name": "Entity1"}], [{"source": "E1", "target": "E2"}]

        mock_extractor.extract = mock_extract_with_error

        chunks = [
            {"chunk_id": "c0", "text": "normal text", "document_id": "d1"},
            {"chunk_id": "c1", "text": "error text here", "document_id": "d1"},
            {"chunk_id": "c2", "text": "more normal text", "document_id": "d1"},
        ]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        # All chunks should be attempted (possibly with retries)
        assert len(results) == 3
        assert call_count >= 3  # At least 3 calls (may have retries on error)

        # One should fail, two should succeed
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 2
        assert len(failures) == 1
        assert failures[0].error is not None

    @pytest.mark.asyncio
    async def test_timeout_handling(self, worker_pool_config, mock_extractor):
        """Test timeout handling in worker pool."""
        config = WorkerPoolConfig(
            num_workers=1,
            chunk_timeout_seconds=1,
            max_retries=0,
        )
        pool = GraphExtractionWorkerPool(config=config, extractor=mock_extractor)

        async def slow_extract(chunk_text, entities):
            await asyncio.sleep(2)  # Longer than timeout
            return [], []

        mock_extractor.extract = slow_extract

        chunks = [
            {"chunk_id": "c0", "text": "slow text", "document_id": "d1"},
        ]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        assert len(results) == 1
        assert not results[0].success
        assert "timeout" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_retry_logic(self, mock_extractor):
        """Test retry logic on transient failures."""
        config = WorkerPoolConfig(
            num_workers=1,
            chunk_timeout_seconds=30,
            max_retries=2,
        )
        pool = GraphExtractionWorkerPool(config=config, extractor=mock_extractor)

        attempt_count = 0

        async def flaky_extract(chunk_text, entities):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise RuntimeError("Transient error")
            return [{"name": "Entity1"}], [{"source": "E1", "target": "E2"}]

        mock_extractor.extract = flaky_extract

        chunks = [
            {"chunk_id": "c0", "text": "text", "document_id": "d1"},
        ]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        assert len(results) == 1
        assert results[0].success  # Should succeed after retries
        assert attempt_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_processing_time_tracking(self, worker_pool_config, mock_extractor):
        """Test processing time is tracked for each chunk."""
        pool = GraphExtractionWorkerPool(config=worker_pool_config, extractor=mock_extractor)

        async def timed_extract(chunk_text, entities):
            await asyncio.sleep(0.05)  # 50ms of work
            return [{"name": "Entity1"}], []

        mock_extractor.extract = timed_extract

        chunks = [
            {"chunk_id": "c0", "text": "text", "document_id": "d1"},
        ]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        assert results[0].processing_time_ms >= 50
        assert results[0].processing_time_ms < 500  # Should not be much more

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_calls(self, mock_extractor):
        """Test semaphore limits concurrent LLM calls."""
        config = WorkerPoolConfig(
            num_workers=4,  # 4 workers
            max_concurrent_llm_calls=2,  # But only 2 concurrent LLM calls
        )
        pool = GraphExtractionWorkerPool(config=config, extractor=mock_extractor)

        concurrent_calls = 0
        max_concurrent = 0

        async def monitored_extract(chunk_text, entities):
            nonlocal concurrent_calls, max_concurrent
            concurrent_calls += 1
            max_concurrent = max(max_concurrent, concurrent_calls)
            await asyncio.sleep(0.1)
            concurrent_calls -= 1
            return [], []

        mock_extractor.extract = monitored_extract

        chunks = [
            {"chunk_id": f"c{i}", "text": f"text {i}", "document_id": "d1"}
            for i in range(6)
        ]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        # Max concurrent should be limited by semaphore
        assert max_concurrent <= 2


@pytest.mark.integration
class TestQueueBackpressure:
    """Tests for queue backpressure handling."""

    @pytest.mark.asyncio
    async def test_queue_backpressure_blocks_producer(self):
        """Test queue backpressure prevents memory overflow."""
        queue = TypedQueue[ChunkQueueItem](maxsize=2)

        # Fill queue
        for i in range(2):
            await queue.put(
                ChunkQueueItem(
                    chunk_id=f"c{i}",
                    chunk_index=i,
                    text=f"text {i}",
                    token_count=100,
                    document_id="d1",
                    metadata={},
                )
            )

        assert queue.qsize() == 2
        assert queue.full()

        # Next put should block
        put_completed = False

        async def try_put():
            nonlocal put_completed
            await queue.put(
                ChunkQueueItem(
                    chunk_id="c2",
                    chunk_index=2,
                    text="text 2",
                    token_count=100,
                    document_id="d1",
                    metadata={},
                )
            )
            put_completed = True

        task = asyncio.create_task(try_put())
        await asyncio.sleep(0.1)

        assert not put_completed  # Should still be blocked

        # Consume one item
        item = await queue.get()
        assert item.chunk_id == "c0"
        await asyncio.sleep(0.1)

        assert put_completed  # Now should complete

    @pytest.mark.asyncio
    async def test_queue_completion_signal(self):
        """Test queue completion signal stops consumers."""
        queue = TypedQueue[ChunkQueueItem](maxsize=5)

        # Put some items
        for i in range(3):
            await queue.put(
                ChunkQueueItem(
                    chunk_id=f"c{i}",
                    chunk_index=i,
                    text=f"text {i}",
                    token_count=100,
                    document_id="d1",
                    metadata={},
                )
            )

        # Signal completion
        await queue.mark_done()

        # Consumer should get items then None
        items_received = []
        while True:
            item = await queue.get()
            if item is None:
                break
            items_received.append(item)

        assert len(items_received) == 3
        assert all(isinstance(item, ChunkQueueItem) for item in items_received)


@pytest.mark.integration
class TestPipelineIntegrationScenarios:
    """Integration tests for complete pipeline scenarios."""

    @pytest.mark.asyncio
    async def test_streaming_pipeline_with_progress_updates(
        self, progress_manager, pipeline_config, sample_chunks
    ):
        """Test pipeline updates progress manager throughout execution."""
        doc_id = "test-doc-integration"
        document_name = "integration_test.pdf"

        # Start tracking
        progress_manager.start_document(
            doc_id,
            document_name,
            total_chunks=len(sample_chunks),
            max_workers=pipeline_config.extraction_workers,
        )

        # Simulate pipeline stages
        stages_processed = []

        for stage_name in ["parsing", "chunking", "embedding", "extraction"]:
            stages_processed.append(stage_name)

            await progress_manager.update_stage(
                doc_id,
                stage_name,
                status=StageStatus.IN_PROGRESS,
                total=len(sample_chunks),
                processed=0,
            )

            # Simulate processing
            for i in range(len(sample_chunks)):
                await progress_manager.update_stage(
                    doc_id,
                    stage_name,
                    processed=i + 1,
                    in_flight=min(2, len(sample_chunks) - i - 1),
                )
                await asyncio.sleep(0.01)

            await progress_manager.update_stage(
                doc_id,
                stage_name,
                status=StageStatus.COMPLETED,
            )

        # Verify all stages were processed
        progress = progress_manager.get_progress(doc_id)
        assert progress is not None
        assert progress.parsing.is_complete
        assert progress.chunking.is_complete
        assert progress.embedding.is_complete
        assert progress.extraction.is_complete

        # Verify overall progress
        assert progress.overall_progress_percent == 100.0

    @pytest.mark.asyncio
    async def test_multiple_documents_parallel_processing(self, progress_manager):
        """Test tracking multiple documents in parallel."""
        doc_ids = ["doc1", "doc2", "doc3"]

        # Start all documents
        for doc_id in doc_ids:
            progress_manager.start_document(doc_id, f"{doc_id}.pdf", total_chunks=10)

        # Update stages for all documents concurrently
        async def process_doc(doc_id: str):
            for stage in ["parsing", "chunking", "embedding"]:
                await progress_manager.update_stage(
                    doc_id,
                    stage,
                    status=StageStatus.IN_PROGRESS,
                    total=10,
                    processed=0,
                )
                await asyncio.sleep(0.02)
                await progress_manager.update_stage(
                    doc_id, stage, processed=10, status=StageStatus.COMPLETED
                )

        await asyncio.gather(*[process_doc(doc_id) for doc_id in doc_ids])

        # Verify all documents tracked independently
        for doc_id in doc_ids:
            progress = progress_manager.get_progress(doc_id)
            assert progress is not None
            assert progress.overall_progress_percent == 100.0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_stress_test_rapid_updates(self, progress_manager):
        """Stress test with rapid progress updates."""
        doc_id = "stress-test-doc"
        progress_manager.start_document(doc_id, "stress.pdf", total_chunks=1000)

        # Rapid updates
        start_time = time.time()
        update_count = 0

        async def rapid_updates():
            nonlocal update_count
            for i in range(100):
                await progress_manager.update_stage(
                    doc_id,
                    "extraction",
                    status=StageStatus.IN_PROGRESS,
                    processed=i,
                    total=1000,
                )
                update_count += 1

        await rapid_updates()
        elapsed = time.time() - start_time

        assert update_count == 100
        # Should handle 100 updates in <1 second
        assert elapsed < 1.0

        progress = progress_manager.get_progress(doc_id)
        assert progress.extraction.processed == 99


# =============================================================================
# Test Cleanup
# =============================================================================


def test_progress_manager_singleton():
    """Test progress manager singleton pattern."""
    manager1 = get_progress_manager()
    manager2 = get_progress_manager()

    assert manager1 is manager2
