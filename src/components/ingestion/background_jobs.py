"""Background Job Queue for Two-Phase Document Upload (Sprint 83 Feature 83.4).

This module provides:
- Asyncio-based background job queue
- Redis-based status tracking
- Retry logic with exponential backoff
- Job cleanup on success/failure

Job Status Lifecycle:
    processing_fast -> processing_background -> ready/failed

Redis Schema:
    upload_status:{document_id} = {
        document_id: str,
        status: str (processing_fast, processing_background, ready, failed),
        progress_pct: float (0-100),
        current_phase: str (parsing, chunking, embedding, extraction, indexing),
        error_message: str | None,
        created_at: str (ISO8601),
        updated_at: str (ISO8601),
        namespace: str,
        domain: str
    }

TTL: 24 hours (auto-cleanup)
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any, Callable

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.exceptions import IngestionError, MemoryError

logger = structlog.get_logger(__name__)

# Constants
MAX_RETRY_ATTEMPTS = 3
STATUS_TTL_SECONDS = 86400  # 24 hours
RETRY_WAIT_MIN_SECONDS = 2
RETRY_WAIT_MAX_SECONDS = 30


class BackgroundJobQueue:
    """Asyncio-based background job queue with Redis status tracking.

    Features:
    - Submit jobs for background processing
    - Track job status in Redis
    - Retry failed jobs with exponential backoff
    - Auto-cleanup after 24 hours

    Example:
        >>> queue = get_background_job_queue()
        >>> await queue.initialize()
        >>> await queue.enqueue_job(document_id, refinement_func, namespace, domain)
        >>> status = await queue.get_status(document_id)
        >>> # status = {"status": "processing_background", "progress_pct": 60, ...}
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize background job queue.

        Args:
            redis_url: Redis connection URL (default: from settings)
        """
        self.redis_url = redis_url or settings.redis_url
        self._client: Redis | None = None
        self._active_jobs: dict[str, asyncio.Task] = {}

        logger.info(
            "background_job_queue_initialized",
            redis_url=self.redis_url,
            max_retry_attempts=MAX_RETRY_ATTEMPTS,
        )

    async def initialize(self) -> None:
        """Initialize Redis client connection.

        Raises:
            MemoryError: If connection fails
        """
        if self._client is not None:
            return

        try:
            self._client = await Redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("background_job_queue_redis_connected")

        except Exception as e:
            logger.error("background_job_queue_redis_connection_failed", error=str(e))
            raise MemoryError(
                f"Failed to connect to Redis for background jobs: {e}",
                reason="connection_failed",
            ) from e

    async def close(self) -> None:
        """Close Redis connection and cancel active jobs."""
        # Cancel all active jobs
        for document_id, task in self._active_jobs.items():
            if not task.done():
                task.cancel()
                logger.info("background_job_cancelled", document_id=document_id)

        if self._client:
            await self._client.close()
            self._client = None
            logger.info("background_job_queue_redis_closed")

    def _get_status_key(self, document_id: str) -> str:
        """Get Redis key for job status.

        Args:
            document_id: Document ID

        Returns:
            Redis key (e.g., "upload_status:doc_abc123")
        """
        return f"upload_status:{document_id}"

    async def set_status(
        self,
        document_id: str,
        status: str,
        progress_pct: float = 0.0,
        current_phase: str = "",
        error_message: str | None = None,
        namespace: str = "default",
        domain: str = "general",
    ) -> None:
        """Set job status in Redis.

        Args:
            document_id: Document ID
            status: Job status (processing_fast, processing_background, ready, failed)
            progress_pct: Progress percentage (0-100)
            current_phase: Current processing phase
            error_message: Error message if failed
            namespace: Document namespace
            domain: Document domain

        Raises:
            MemoryError: If Redis operation fails
        """
        await self.initialize()

        now = datetime.now(UTC).isoformat()

        # Get existing status to preserve created_at
        existing = await self.get_status(document_id)
        created_at = existing.get("created_at", now) if existing else now

        status_data = {
            "document_id": document_id,
            "status": status,
            "progress_pct": progress_pct,
            "current_phase": current_phase,
            "error_message": error_message,
            "created_at": created_at,
            "updated_at": now,
            "namespace": namespace,
            "domain": domain,
        }

        try:
            key = self._get_status_key(document_id)
            await self._client.setex(
                key,
                STATUS_TTL_SECONDS,
                json.dumps(status_data),
            )

            logger.info(
                "background_job_status_updated",
                document_id=document_id,
                status=status,
                progress_pct=progress_pct,
                current_phase=current_phase,
            )

        except RedisError as e:
            logger.error(
                "background_job_status_update_failed",
                document_id=document_id,
                error=str(e),
            )
            raise MemoryError(
                f"Failed to update job status in Redis: {e}",
                reason="redis_operation_failed",
            ) from e

    async def get_status(self, document_id: str) -> dict[str, Any] | None:
        """Get job status from Redis.

        Args:
            document_id: Document ID

        Returns:
            Status dict or None if not found

        Raises:
            MemoryError: If Redis operation fails
        """
        await self.initialize()

        try:
            key = self._get_status_key(document_id)
            status_json = await self._client.get(key)

            if not status_json:
                logger.info("background_job_status_not_found", document_id=document_id)
                return None

            status = json.loads(status_json)
            return status

        except (RedisError, json.JSONDecodeError) as e:
            logger.error(
                "background_job_status_get_failed",
                document_id=document_id,
                error=str(e),
            )
            raise MemoryError(
                f"Failed to get job status from Redis: {e}",
                reason="redis_operation_failed",
            ) from e

    async def delete_status(self, document_id: str) -> None:
        """Delete job status from Redis.

        Args:
            document_id: Document ID
        """
        await self.initialize()

        try:
            key = self._get_status_key(document_id)
            await self._client.delete(key)
            logger.info("background_job_status_deleted", document_id=document_id)

        except RedisError as e:
            logger.error(
                "background_job_status_delete_failed",
                document_id=document_id,
                error=str(e),
            )
            # Don't raise exception on delete failure

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=1,
            min=RETRY_WAIT_MIN_SECONDS,
            max=RETRY_WAIT_MAX_SECONDS,
        ),
        retry=retry_if_exception_type((IngestionError, Exception)),
        reraise=True,
    )
    async def _execute_with_retry(
        self,
        func: Callable,
        document_id: str,
        namespace: str,
        domain: str,
    ) -> None:
        """Execute job function with retry logic.

        Args:
            func: Async function to execute
            document_id: Document ID
            namespace: Document namespace
            domain: Document domain

        Raises:
            Exception: If all retry attempts fail
        """
        try:
            logger.info(
                "background_job_executing",
                document_id=document_id,
                namespace=namespace,
                domain=domain,
            )
            await func(document_id, namespace, domain)
            logger.info("background_job_execution_success", document_id=document_id)

        except Exception as e:
            logger.error(
                "background_job_execution_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    async def _run_job(
        self,
        document_id: str,
        func: Callable,
        namespace: str,
        domain: str,
    ) -> None:
        """Run background job with status tracking and error handling.

        Args:
            document_id: Document ID
            func: Async function to execute (must accept document_id, namespace, domain)
            namespace: Document namespace
            domain: Document domain
        """
        start_time = time.time()

        try:
            # Execute with retry
            await self._execute_with_retry(func, document_id, namespace, domain)

            # Mark as ready
            await self.set_status(
                document_id=document_id,
                status="ready",
                progress_pct=100.0,
                current_phase="completed",
                namespace=namespace,
                domain=domain,
            )

            duration = time.time() - start_time
            logger.info(
                "background_job_completed",
                document_id=document_id,
                duration_seconds=round(duration, 2),
            )

        except Exception as e:
            # Mark as failed
            await self.set_status(
                document_id=document_id,
                status="failed",
                progress_pct=0.0,
                current_phase="failed",
                error_message=str(e),
                namespace=namespace,
                domain=domain,
            )

            duration = time.time() - start_time
            logger.error(
                "background_job_failed_after_retries",
                document_id=document_id,
                error=str(e),
                duration_seconds=round(duration, 2),
                max_retries=MAX_RETRY_ATTEMPTS,
            )

        finally:
            # Remove from active jobs
            if document_id in self._active_jobs:
                del self._active_jobs[document_id]

    async def enqueue_job(
        self,
        document_id: str,
        func: Callable,
        namespace: str = "default",
        domain: str = "general",
    ) -> None:
        """Enqueue background job for execution.

        Args:
            document_id: Document ID
            func: Async function to execute (must accept document_id, namespace, domain)
            namespace: Document namespace
            domain: Document domain

        Raises:
            ValueError: If job already exists for document_id
        """
        if document_id in self._active_jobs:
            raise ValueError(f"Job already exists for document_id: {document_id}")

        # Create background task
        task = asyncio.create_task(self._run_job(document_id, func, namespace, domain))
        self._active_jobs[document_id] = task

        logger.info(
            "background_job_enqueued",
            document_id=document_id,
            namespace=namespace,
            domain=domain,
            active_jobs_count=len(self._active_jobs),
        )

    async def get_active_jobs_count(self) -> int:
        """Get count of active background jobs.

        Returns:
            Number of active jobs
        """
        # Clean up completed tasks
        completed_ids = [doc_id for doc_id, task in self._active_jobs.items() if task.done()]
        for doc_id in completed_ids:
            del self._active_jobs[doc_id]

        return len(self._active_jobs)

    async def list_all_statuses(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """List all job statuses (optionally filtered by namespace).

        Args:
            namespace: Optional namespace filter

        Returns:
            List of status dicts
        """
        await self.initialize()

        try:
            # Scan for all upload_status keys
            keys = []
            async for key in self._client.scan_iter(match="upload_status:*", count=100):
                keys.append(key)

            # Get all statuses
            statuses = []
            for key in keys:
                status_json = await self._client.get(key)
                if status_json:
                    status = json.loads(status_json)
                    if namespace is None or status.get("namespace") == namespace:
                        statuses.append(status)

            logger.info("background_job_list_statuses", count=len(statuses), namespace=namespace)
            return statuses

        except (RedisError, json.JSONDecodeError) as e:
            logger.error("background_job_list_statuses_failed", error=str(e))
            return []


# Global instance (singleton pattern)
_background_job_queue: BackgroundJobQueue | None = None


def get_background_job_queue() -> BackgroundJobQueue:
    """Get global background job queue instance (singleton).

    Returns:
        BackgroundJobQueue instance
    """
    global _background_job_queue
    if _background_job_queue is None:
        _background_job_queue = BackgroundJobQueue()
    return _background_job_queue
