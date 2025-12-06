"""Unit tests for Graph Extraction Worker Pool (Sprint 37 Feature 37.2).

Tests parallel LLM calls for entity/relation extraction with:
- Worker pool parallelism (4 workers)
- Semaphore-based VRAM management
- Per-chunk timeout and retry logic
- Progress callbacks and status tracking

Author: Claude Code (Backend Agent)
Date: 2025-12-06
Sprint: 37 Feature 37.2 - Worker Pool for Graph Extraction (8 SP)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.ingestion.extraction_worker_pool import (
    ExtractionResult,
    GraphExtractionWorkerPool,
    WorkerPoolConfig,
    WorkerStatus,
    get_extraction_worker_pool,
)


@pytest.fixture
def mock_extractor():
    """Create a mock RelationExtractor."""
    extractor = MagicMock()
    extractor.model = "qwen3:32b"
    extractor.temperature = 0.1
    extractor.extract = AsyncMock(
        return_value=[
            {
                "source": "Alex",
                "target": "TechCorp",
                "description": "Alex works at TechCorp",
                "strength": 8,
            }
        ]
    )
    return extractor


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    return [
        {
            "chunk_id": "chunk_1",
            "text": "Alex and Jordan work at TechCorp together.",
            "document_id": "doc_1",
        },
        {
            "chunk_id": "chunk_2",
            "text": "Sarah leads the engineering team at DataCorp.",
            "document_id": "doc_1",
        },
        {
            "chunk_id": "chunk_3",
            "text": "Michael collaborates with Lisa on ML projects.",
            "document_id": "doc_1",
        },
        {
            "chunk_id": "chunk_4",
            "text": "The company hired 50 engineers last year.",
            "document_id": "doc_1",
        },
    ]


@pytest.fixture
def worker_pool_config():
    """Create a test worker pool configuration."""
    return WorkerPoolConfig(
        num_workers=2,  # Use 2 workers for faster tests
        chunk_timeout_seconds=30,
        max_retries=2,
        max_concurrent_llm_calls=4,
        vram_limit_mb=5500,
    )


@pytest.fixture
def worker_pool(worker_pool_config, mock_extractor):
    """Create a worker pool instance for testing."""
    return GraphExtractionWorkerPool(config=worker_pool_config, extractor=mock_extractor)


class TestWorkerPoolConfig:
    """Test WorkerPoolConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WorkerPoolConfig()

        assert config.num_workers == 4
        assert config.chunk_timeout_seconds == 120
        assert config.max_retries == 2
        assert config.max_concurrent_llm_calls == 8
        assert config.vram_limit_mb == 5500

    def test_custom_config(self):
        """Test custom configuration values."""
        config = WorkerPoolConfig(
            num_workers=8,
            chunk_timeout_seconds=60,
            max_retries=5,
            max_concurrent_llm_calls=16,
            vram_limit_mb=10000,
        )

        assert config.num_workers == 8
        assert config.chunk_timeout_seconds == 60
        assert config.max_retries == 5
        assert config.max_concurrent_llm_calls == 16
        assert config.vram_limit_mb == 10000


class TestWorkerStatus:
    """Test WorkerStatus dataclass."""

    def test_initial_worker_status(self):
        """Test initial worker status values."""
        status = WorkerStatus(worker_id=0, status="idle")

        assert status.worker_id == 0
        assert status.status == "idle"
        assert status.current_chunk_id is None
        assert status.progress_percent == 0.0
        assert status.chunks_processed == 0

    def test_worker_status_update(self):
        """Test updating worker status during processing."""
        status = WorkerStatus(worker_id=1, status="idle")

        # Simulate processing
        status.status = "processing"
        status.current_chunk_id = "chunk_1"
        status.progress_percent = 50.0

        assert status.status == "processing"
        assert status.current_chunk_id == "chunk_1"
        assert status.progress_percent == 50.0

        # Simulate completion
        status.status = "idle"
        status.current_chunk_id = None
        status.chunks_processed = 1

        assert status.status == "idle"
        assert status.current_chunk_id is None
        assert status.chunks_processed == 1


class TestExtractionResult:
    """Test ExtractionResult dataclass."""

    def test_successful_result(self):
        """Test successful extraction result."""
        result = ExtractionResult(
            chunk_id="chunk_1",
            entities=[{"name": "Alex", "type": "PERSON"}],
            relations=[{"source": "Alex", "target": "TechCorp"}],
            success=True,
            processing_time_ms=5000,
        )

        assert result.chunk_id == "chunk_1"
        assert len(result.entities) == 1
        assert len(result.relations) == 1
        assert result.success is True
        assert result.error is None
        assert result.processing_time_ms == 5000

    def test_failed_result(self):
        """Test failed extraction result."""
        result = ExtractionResult(
            chunk_id="chunk_2",
            entities=[],
            relations=[],
            success=False,
            error="Timeout after 120s",
        )

        assert result.chunk_id == "chunk_2"
        assert len(result.entities) == 0
        assert len(result.relations) == 0
        assert result.success is False
        assert result.error == "Timeout after 120s"


@pytest.mark.asyncio
class TestGraphExtractionWorkerPool:
    """Test GraphExtractionWorkerPool main functionality."""

    async def test_worker_pool_initialization(self, worker_pool, worker_pool_config):
        """Test worker pool initialization."""
        assert worker_pool.config == worker_pool_config
        assert len(worker_pool.worker_statuses) == 2
        assert all(w.status == "idle" for w in worker_pool.worker_statuses)

    async def test_worker_statuses_property(self, worker_pool):
        """Test worker_statuses property returns copy."""
        statuses1 = worker_pool.worker_statuses
        statuses2 = worker_pool.worker_statuses

        # Should be different lists (copies)
        assert statuses1 is not statuses2
        # But with same content
        assert len(statuses1) == len(statuses2)

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_process_chunks_basic(self, mock_time, worker_pool, sample_chunks):
        """Test basic chunk processing with worker pool."""
        # Mock time for processing_time_ms
        mock_time.side_effect = [0, 5.0] * 10  # Each extraction takes 5s

        # Mock the extraction method
        async def mock_extract(chunk):
            await asyncio.sleep(0.01)  # Simulate work
            return (
                [{"name": "TestEntity", "type": "PERSON"}],
                [{"source": "A", "target": "B", "description": "test", "strength": 8}],
            )

        worker_pool._extract_entities_relations = mock_extract

        results = []
        async for result in worker_pool.process_chunks(sample_chunks):
            results.append(result)

        # Should process all chunks
        assert len(results) == len(sample_chunks)

        # All results should be successful
        assert all(r.success for r in results)

        # Check chunk IDs match
        result_chunk_ids = {r.chunk_id for r in results}
        expected_chunk_ids = {c["chunk_id"] for c in sample_chunks}
        assert result_chunk_ids == expected_chunk_ids

    async def test_process_chunks_empty(self, worker_pool):
        """Test processing empty chunk list."""
        results = []
        async for result in worker_pool.process_chunks([]):
            results.append(result)

        assert len(results) == 0

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_process_chunks_with_progress_callback(
        self, mock_time, worker_pool, sample_chunks
    ):
        """Test chunk processing with progress callback."""
        mock_time.side_effect = [0, 1.0] * 20

        # Track progress updates
        progress_updates = []

        def progress_callback(update):
            progress_updates.append(update)

        # Mock extraction
        async def mock_extract(chunk):
            await asyncio.sleep(0.01)
            return ([{"name": "E"}], [{"source": "A", "target": "B"}])

        worker_pool._extract_entities_relations = mock_extract

        results = []
        async for result in worker_pool.process_chunks(sample_chunks, progress_callback):
            results.append(result)

        # Should have progress updates
        assert len(progress_updates) > 0

        # Should have aggregate progress updates
        aggregate_updates = [
            u for u in progress_updates if u["type"] == "extraction_aggregate_progress"
        ]
        assert len(aggregate_updates) == len(sample_chunks)

        # Last aggregate update should be 100%
        assert aggregate_updates[-1]["progress_percent"] == 100.0

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_retry_on_failure(self, mock_time, worker_pool_config):
        """Test retry logic on transient failures."""
        mock_time.side_effect = [0, 1.0] * 100

        pool = GraphExtractionWorkerPool(config=worker_pool_config)

        # Mock extraction that fails first, then succeeds
        call_count = 0

        async def mock_extract_with_failure(chunk):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Temporary connection error")
            return ([{"name": "E"}], [])

        pool._extract_entities_relations = mock_extract_with_failure

        chunks = [{"chunk_id": "c1", "text": "test", "document_id": "d1"}]
        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        # Should succeed after retry
        assert len(results) == 1
        assert results[0].success is True
        assert call_count == 2  # Failed once, succeeded on retry

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_timeout_handling(self, mock_time, worker_pool_config):
        """Test timeout handling for slow extractions."""
        mock_time.side_effect = [0, 1.0] * 100

        # Set short timeout for testing
        worker_pool_config.chunk_timeout_seconds = 1

        pool = GraphExtractionWorkerPool(config=worker_pool_config)

        # Mock extraction that takes too long
        async def mock_slow_extract(chunk):
            await asyncio.sleep(10)  # Longer than timeout
            return ([], [])

        pool._extract_entities_relations = mock_slow_extract

        chunks = [{"chunk_id": "c1", "text": "test", "document_id": "d1"}]
        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        # Should fail with timeout
        assert len(results) == 1
        assert results[0].success is False
        assert "Timeout" in results[0].error

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_max_retries_exhausted(self, mock_time, worker_pool_config):
        """Test behavior when max retries are exhausted."""
        mock_time.side_effect = [0, 1.0] * 100

        worker_pool_config.max_retries = 2

        pool = GraphExtractionWorkerPool(config=worker_pool_config)

        # Mock extraction that always fails
        async def mock_always_fail(chunk):
            raise RuntimeError("Persistent error")

        pool._extract_entities_relations = mock_always_fail

        chunks = [{"chunk_id": "c1", "text": "test", "document_id": "d1"}]
        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        # Should fail after exhausting retries
        assert len(results) == 1
        assert results[0].success is False
        assert "Persistent error" in results[0].error

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_semaphore_limits_concurrent_calls(self, mock_time, worker_pool_config):
        """Test that semaphore limits concurrent LLM calls."""
        mock_time.side_effect = [0, 0.5] * 100

        worker_pool_config.max_concurrent_llm_calls = 2  # Only 2 concurrent
        worker_pool_config.num_workers = 4  # But 4 workers

        pool = GraphExtractionWorkerPool(config=worker_pool_config)

        # Track concurrent calls
        concurrent_calls = 0
        max_concurrent = 0

        async def mock_extract_track_concurrent(chunk):
            nonlocal concurrent_calls, max_concurrent
            concurrent_calls += 1
            max_concurrent = max(max_concurrent, concurrent_calls)
            await asyncio.sleep(0.1)
            concurrent_calls -= 1
            return ([{"name": "E"}], [])

        pool._extract_entities_relations = mock_extract_track_concurrent

        chunks = [{"chunk_id": f"c{i}", "text": "test", "document_id": "d1"} for i in range(8)]

        results = []
        async for result in pool.process_chunks(chunks):
            results.append(result)

        # Should have processed all chunks
        assert len(results) == 8

        # Concurrent calls should never exceed semaphore limit
        assert max_concurrent <= worker_pool_config.max_concurrent_llm_calls

    async def test_lazy_extractor_initialization(self, worker_pool_config):
        """Test lazy initialization of RelationExtractor."""
        pool = GraphExtractionWorkerPool(config=worker_pool_config, extractor=None)

        assert pool._extractor is None

        # Mock the lazy import at the source module
        with patch(
            "src.components.graph_rag.relation_extractor.create_relation_extractor_from_config"
        ) as mock_create:
            mock_extractor = MagicMock()
            mock_extractor.model = "qwen3:32b"
            mock_extractor.temperature = 0.1
            mock_extractor.extract = AsyncMock(return_value=[])
            mock_create.return_value = mock_extractor

            # Call extraction (should trigger lazy init)
            chunk = {"chunk_id": "c1", "text": "test", "document_id": "d1"}
            await pool._extract_entities_relations(chunk)

            # Should have initialized extractor
            assert pool._extractor is not None
            assert mock_create.called


@pytest.mark.asyncio
class TestGetExtractionWorkerPool:
    """Test factory function for worker pool."""

    @patch("src.core.config.settings")
    async def test_get_worker_pool_from_settings(self, mock_settings):
        """Test creating worker pool from settings."""
        mock_settings.extraction_max_workers = 6
        mock_settings.extraction_max_retries = 5

        pool = get_extraction_worker_pool()

        assert pool.config.num_workers == 6
        assert pool.config.max_retries == 5

    @patch("src.core.config.settings")
    async def test_get_worker_pool_with_override(self, mock_settings):
        """Test creating worker pool with override."""
        mock_settings.extraction_max_workers = 6

        pool = get_extraction_worker_pool(num_workers=8)

        # Should use override
        assert pool.config.num_workers == 8

    async def test_get_worker_pool_settings_fail(self):
        """Test fallback to defaults if settings fail."""
        # Mock the import to fail
        with patch.dict("sys.modules", {"src.core.config": None}):
            pool = get_extraction_worker_pool()

            # Should use defaults despite failed import
            assert pool.config.num_workers == 4

    async def test_get_worker_pool_with_custom_extractor(self, mock_extractor):
        """Test creating worker pool with custom extractor."""
        pool = get_extraction_worker_pool(extractor=mock_extractor)

        assert pool._extractor == mock_extractor


@pytest.mark.asyncio
class TestWorkerPoolPerformance:
    """Test worker pool performance characteristics."""

    @patch("src.components.ingestion.extraction_worker_pool.time.time")
    async def test_parallel_speedup(self, mock_time):
        """Test that parallelism provides speedup."""
        # Sequential processing time
        mock_time.side_effect = [i * 0.5 for i in range(100)]

        # Create pools with different worker counts
        config_1_worker = WorkerPoolConfig(num_workers=1, max_concurrent_llm_calls=1)
        config_4_workers = WorkerPoolConfig(num_workers=4, max_concurrent_llm_calls=4)

        pool_1 = GraphExtractionWorkerPool(config=config_1_worker)
        pool_4 = GraphExtractionWorkerPool(config=config_4_workers)

        # Mock extraction with fixed delay
        async def mock_extract(chunk):
            await asyncio.sleep(0.1)  # 100ms per extraction
            return ([{"name": "E"}], [])

        pool_1._extract_entities_relations = mock_extract
        pool_4._extract_entities_relations = mock_extract

        # Create test chunks
        chunks = [{"chunk_id": f"c{i}", "text": "test", "document_id": "d1"} for i in range(8)]

        # Process with 1 worker
        start_1 = asyncio.get_event_loop().time()
        results_1 = []
        async for result in pool_1.process_chunks(chunks):
            results_1.append(result)
        time_1 = asyncio.get_event_loop().time() - start_1

        # Process with 4 workers
        start_4 = asyncio.get_event_loop().time()
        results_4 = []
        async for result in pool_4.process_chunks(chunks):
            results_4.append(result)
        time_4 = asyncio.get_event_loop().time() - start_4

        # Should process all chunks
        assert len(results_1) == 8
        assert len(results_4) == 8

        # Parallel should be faster (with some tolerance for overhead)
        # Expected: 4 workers should be ~3-4x faster
        assert time_4 < time_1 * 0.5  # At least 2x faster
