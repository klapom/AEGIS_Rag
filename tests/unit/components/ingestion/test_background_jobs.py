"""Unit tests for Background Job Queue (Sprint 83 Feature 83.4).

Tests:
1. BackgroundJobQueue initialization
2. Redis connection and status tracking
3. Job enqueue and execution
4. Retry logic with exponential backoff
5. Status updates (processing_fast -> processing_background -> ready/failed)
6. Job cleanup on success/failure
"""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError

from src.components.ingestion.background_jobs import (
    BackgroundJobQueue,
    get_background_job_queue,
)
from src.core.exceptions import IngestionError, MemoryError


@pytest.fixture
async def job_queue():
    """Create BackgroundJobQueue instance for testing."""
    queue = BackgroundJobQueue(redis_url="redis://localhost:6379")
    yield queue
    await queue.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_client.setex.return_value = True
    mock_client.get.return_value = None
    mock_client.delete.return_value = 1
    return mock_client


class TestBackgroundJobQueueInitialization:
    """Test BackgroundJobQueue initialization and connection."""

    async def test_initialize_success(self, job_queue, mock_redis):
        """Test successful Redis initialization."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            assert job_queue._client is not None
            mock_redis.ping.assert_awaited_once()

    async def test_initialize_connection_failure(self, job_queue):
        """Test Redis connection failure."""
        with patch(
            "redis.asyncio.Redis.from_url",
            side_effect=RedisError("Connection failed"),
        ):
            with pytest.raises(MemoryError, match="Failed to connect to Redis"):
                await job_queue.initialize()

    async def test_initialize_idempotent(self, job_queue, mock_redis):
        """Test initialize is idempotent (doesn't reconnect if already connected)."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()
            client_1 = job_queue._client

            await job_queue.initialize()
            client_2 = job_queue._client

            assert client_1 is client_2
            mock_redis.ping.assert_awaited_once()

    async def test_close_cancels_active_jobs(self, job_queue, mock_redis):
        """Test close cancels all active jobs."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            # Create mock tasks
            mock_task_1 = MagicMock()
            mock_task_1.done.return_value = False
            mock_task_2 = MagicMock()
            mock_task_2.done.return_value = False

            job_queue._active_jobs = {
                "doc1": mock_task_1,
                "doc2": mock_task_2,
            }

            await job_queue.close()

            mock_task_1.cancel.assert_called_once()
            mock_task_2.cancel.assert_called_once()
            mock_redis.close.assert_awaited_once()


class TestStatusTracking:
    """Test Redis-based status tracking."""

    async def test_set_status_new_document(self, job_queue, mock_redis):
        """Test setting status for new document."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            # Mock get_status to return None (new document)
            mock_redis.get.return_value = None

            await job_queue.set_status(
                document_id="doc_123",
                status="processing_fast",
                progress_pct=50.0,
                current_phase="chunking",
                namespace="research",
                domain="ai_papers",
            )

            # Verify setex was called with correct key and data
            mock_redis.setex.assert_awaited_once()
            call_args = mock_redis.setex.await_args
            key = call_args[0][0]
            ttl = call_args[0][1]
            data_json = call_args[0][2]

            assert key == "upload_status:doc_123"
            assert ttl == 86400  # 24 hours
            data = json.loads(data_json)
            assert data["document_id"] == "doc_123"
            assert data["status"] == "processing_fast"
            assert data["progress_pct"] == 50.0
            assert data["current_phase"] == "chunking"
            assert data["namespace"] == "research"
            assert data["domain"] == "ai_papers"

    async def test_set_status_preserves_created_at(self, job_queue, mock_redis):
        """Test set_status preserves created_at timestamp on updates."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            original_created_at = "2026-01-10T10:00:00Z"

            # Mock get_status to return existing status
            existing_status = {
                "document_id": "doc_123",
                "status": "processing_fast",
                "created_at": original_created_at,
                "updated_at": "2026-01-10T10:01:00Z",
            }
            mock_redis.get.return_value = json.dumps(existing_status)

            await job_queue.set_status(
                document_id="doc_123",
                status="processing_background",
                progress_pct=60.0,
                current_phase="extraction",
            )

            # Verify created_at is preserved
            call_args = mock_redis.setex.await_args
            data_json = call_args[0][2]
            data = json.loads(data_json)
            assert data["created_at"] == original_created_at

    async def test_get_status_success(self, job_queue, mock_redis):
        """Test getting status for existing document."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            status_data = {
                "document_id": "doc_123",
                "status": "ready",
                "progress_pct": 100.0,
                "current_phase": "completed",
            }
            mock_redis.get.return_value = json.dumps(status_data)

            result = await job_queue.get_status("doc_123")

            assert result == status_data
            mock_redis.get.assert_awaited_once_with("upload_status:doc_123")

    async def test_get_status_not_found(self, job_queue, mock_redis):
        """Test getting status for non-existent document."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            mock_redis.get.return_value = None

            result = await job_queue.get_status("doc_nonexistent")

            assert result is None

    async def test_delete_status(self, job_queue, mock_redis):
        """Test deleting status from Redis."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.delete_status("doc_123")

            mock_redis.delete.assert_awaited_once_with("upload_status:doc_123")


class TestJobExecution:
    """Test background job execution and retry logic."""

    async def test_enqueue_job_success(self, job_queue, mock_redis):
        """Test enqueueing a background job."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            async def dummy_func(doc_id, namespace, domain):
                """Dummy job function."""
                pass

            await job_queue.enqueue_job(
                document_id="doc_123",
                func=dummy_func,
                namespace="research",
                domain="ai_papers",
            )

            assert "doc_123" in job_queue._active_jobs
            assert isinstance(job_queue._active_jobs["doc_123"], asyncio.Task)

    async def test_enqueue_job_duplicate_raises_error(self, job_queue, mock_redis):
        """Test enqueueing duplicate job raises ValueError."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            async def dummy_func(doc_id, namespace, domain):
                pass

            await job_queue.enqueue_job(
                document_id="doc_123",
                func=dummy_func,
                namespace="research",
                domain="ai_papers",
            )

            with pytest.raises(ValueError, match="Job already exists"):
                await job_queue.enqueue_job(
                    document_id="doc_123",
                    func=dummy_func,
                    namespace="research",
                    domain="ai_papers",
                )

    async def test_execute_with_retry_success(self, job_queue, mock_redis):
        """Test job execution with retry succeeds on first attempt."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            call_count = 0

            async def job_func(doc_id, namespace, domain):
                nonlocal call_count
                call_count += 1

            await job_queue._execute_with_retry(
                func=job_func,
                document_id="doc_123",
                namespace="research",
                domain="ai_papers",
            )

            assert call_count == 1

    async def test_execute_with_retry_retries_on_failure(self, job_queue, mock_redis):
        """Test job execution retries on failure."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            call_count = 0

            async def failing_job(doc_id, namespace, domain):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise IngestionError(document_id=doc_id, reason="Test failure")

            await job_queue._execute_with_retry(
                func=failing_job,
                document_id="doc_123",
                namespace="research",
                domain="ai_papers",
            )

            assert call_count == 2  # Failed once, succeeded on retry

    async def test_run_job_marks_ready_on_success(self, job_queue, mock_redis):
        """Test _run_job marks status as ready on successful completion."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            async def successful_job(doc_id, namespace, domain):
                pass

            await job_queue._run_job(
                document_id="doc_123",
                func=successful_job,
                namespace="research",
                domain="ai_papers",
            )

            # Verify final set_status call marked as ready
            final_call = mock_redis.setex.await_args_list[-1]
            data_json = final_call[0][2]
            data = json.loads(data_json)
            assert data["status"] == "ready"
            assert data["progress_pct"] == 100.0

    async def test_run_job_marks_failed_on_error(self, job_queue, mock_redis):
        """Test _run_job marks status as failed on error."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            async def failing_job(doc_id, namespace, domain):
                raise IngestionError(document_id=doc_id, reason="Test failure")

            await job_queue._run_job(
                document_id="doc_123",
                func=failing_job,
                namespace="research",
                domain="ai_papers",
            )

            # Verify final set_status call marked as failed
            final_call = mock_redis.setex.await_args_list[-1]
            data_json = final_call[0][2]
            data = json.loads(data_json)
            assert data["status"] == "failed"
            assert "Test failure" in data["error_message"]

    async def test_get_active_jobs_count_cleans_completed(self, job_queue, mock_redis):
        """Test get_active_jobs_count removes completed tasks."""
        with patch("redis.asyncio.Redis.from_url", return_value=mock_redis):
            await job_queue.initialize()

            # Create mock tasks
            completed_task = MagicMock()
            completed_task.done.return_value = True
            active_task = MagicMock()
            active_task.done.return_value = False

            job_queue._active_jobs = {
                "doc_completed": completed_task,
                "doc_active": active_task,
            }

            count = await job_queue.get_active_jobs_count()

            assert count == 1
            assert "doc_completed" not in job_queue._active_jobs
            assert "doc_active" in job_queue._active_jobs


class TestSingleton:
    """Test singleton pattern for BackgroundJobQueue."""

    def test_get_background_job_queue_singleton(self):
        """Test get_background_job_queue returns same instance."""
        queue_1 = get_background_job_queue()
        queue_2 = get_background_job_queue()

        assert queue_1 is queue_2
