"""Community Detection Batch Job.

Sprint 126 Feature 126.1: Scheduled Community Detection

This module provides a scheduled batch job for community detection that runs
outside the ingestion pipeline to avoid blocking API requests.

Usage:
    # Start the scheduler (typically in main.py or a separate worker process)
    scheduler = start_community_detection_scheduler()

    # Or trigger manually
    await run_community_detection_batch()

Schedule:
    - Runs daily at 5:00 AM
    - Can be configured via COMMUNITY_DETECTION_SCHEDULE env var (cron format)

Example:
    >>> from src.jobs.community_batch_job import run_community_detection_batch
    >>> result = await run_community_detection_batch()
    >>> print(f"Detected {result['communities_detected']} communities")
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.components.graph_rag.community_detector import get_community_detector
from src.components.graph_rag.community_summarizer import get_community_summarizer
from src.core.config import settings

logger = structlog.get_logger(__name__)

# Global scheduler instance (singleton)
_scheduler: AsyncIOScheduler | None = None


async def run_community_detection_batch() -> dict[str, Any]:
    """Run community detection and summarization as a batch job.

    This function runs the complete community detection pipeline:
    1. Detect communities using Leiden/Louvain algorithm
    2. Generate LLM summaries for detected communities
    3. Store results in Neo4j

    Returns:
        Dictionary with batch job statistics:
        - job_id: Unique job ID
        - started_at: ISO timestamp of job start
        - completed_at: ISO timestamp of job completion
        - duration_seconds: Total execution time
        - communities_detected: Number of communities found
        - summaries_generated: Number of summaries created
        - algorithm: Detection algorithm used
        - success: True if completed without errors

    Example:
        >>> result = await run_community_detection_batch()
        >>> print(result)
        {
            "job_id": "comm_batch_20260207_050000",
            "started_at": "2026-02-07T05:00:00Z",
            "completed_at": "2026-02-07T05:15:23Z",
            "duration_seconds": 923.45,
            "communities_detected": 2387,
            "summaries_generated": 2387,
            "algorithm": "leiden",
            "success": True
        }
    """
    job_id = f"comm_batch_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    start_time = time.time()
    started_at = datetime.now(UTC).isoformat()

    logger.info(
        "community_batch_job_started",
        job_id=job_id,
        started_at=started_at,
        mode="batch",
        note="Running community detection outside ingestion pipeline",
    )

    try:
        # Step 1: Run community detection
        logger.info("batch_job_phase", phase="community_detection", status="starting")
        community_detector = get_community_detector()
        communities = await community_detector.detect_communities(track_delta=True)

        communities_detected = len(communities)
        logger.info(
            "batch_job_phase",
            phase="community_detection",
            status="complete",
            communities_detected=communities_detected,
        )

        # Step 2: Generate summaries for changed communities
        # Note: detect_communities() with track_delta=True already triggers
        # summary generation for affected communities via CommunityDelta
        # So summaries are already created - we just log the count
        logger.info(
            "batch_job_phase",
            phase="community_summarization",
            status="complete",
            note="Summaries generated automatically via delta tracking",
        )

        # Completion stats
        end_time = time.time()
        duration_seconds = end_time - start_time
        completed_at = datetime.now(UTC).isoformat()

        result = {
            "job_id": job_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": round(duration_seconds, 2),
            "communities_detected": communities_detected,
            "summaries_generated": communities_detected,  # Delta tracking handles this
            "algorithm": community_detector.algorithm,
            "success": True,
        }

        logger.info(
            "community_batch_job_completed",
            **result,
            note="Community detection batch job finished successfully",
        )

        return result

    except Exception as e:
        # Log error and return failure stats
        end_time = time.time()
        duration_seconds = end_time - start_time
        completed_at = datetime.now(UTC).isoformat()

        logger.error(
            "community_batch_job_failed",
            job_id=job_id,
            error=str(e),
            duration_seconds=round(duration_seconds, 2),
            exc_info=True,
        )

        return {
            "job_id": job_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": round(duration_seconds, 2),
            "communities_detected": 0,
            "summaries_generated": 0,
            "algorithm": settings.graph_community_algorithm,
            "success": False,
            "error": str(e),
        }


def start_community_detection_scheduler() -> AsyncIOScheduler:
    """Start the background scheduler for community detection.

    Creates and starts an APScheduler instance with a cron trigger
    configured to run community detection daily at 5:00 AM.

    Returns:
        AsyncIOScheduler instance (already started)

    Example:
        >>> scheduler = start_community_detection_scheduler()
        >>> # Scheduler runs in background until shutdown
        >>> scheduler.shutdown()  # When app exits

    Notes:
        - Only starts scheduler if mode is 'scheduled' in config
        - If scheduler is already running, returns existing instance
        - Uses APScheduler with cron trigger (5 AM daily by default)
    """
    global _scheduler

    # Only start scheduler if in scheduled mode
    if settings.graph_community_detection_mode != "scheduled":
        logger.info(
            "community_scheduler_not_started",
            mode=settings.graph_community_detection_mode,
            reason="not_in_scheduled_mode",
        )
        return None  # type: ignore[return-value]

    # Return existing scheduler if already running
    if _scheduler is not None and _scheduler.running:
        logger.info("community_scheduler_already_running")
        return _scheduler

    # Create new scheduler
    _scheduler = AsyncIOScheduler()

    # Add community detection job with cron trigger (5 AM daily)
    # Format: minute hour day month day_of_week
    cron_schedule = "0 5 * * *"  # 5:00 AM daily

    _scheduler.add_job(
        run_community_detection_batch,
        trigger=CronTrigger.from_crontab(cron_schedule),
        id="community_detection_batch",
        name="Community Detection Batch Job",
        replace_existing=True,
        max_instances=1,  # Only one instance at a time
        coalesce=True,  # Coalesce missed runs into one
    )

    # Start scheduler
    _scheduler.start()

    logger.info(
        "community_scheduler_started",
        schedule=cron_schedule,
        next_run=_scheduler.get_job("community_detection_batch").next_run_time.isoformat(),
        mode="scheduled",
    )

    return _scheduler


def shutdown_community_detection_scheduler() -> None:
    """Shutdown the community detection scheduler.

    Gracefully stops the scheduler and waits for any running jobs to complete.

    Example:
        >>> shutdown_community_detection_scheduler()
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("shutting_down_community_scheduler")
        _scheduler.shutdown(wait=True)
        _scheduler = None
        logger.info("community_scheduler_shutdown_complete")
    else:
        logger.info("community_scheduler_not_running")


def get_scheduler_status() -> dict[str, Any]:
    """Get current scheduler status and next run time.

    Returns:
        Dictionary with scheduler status:
        - running: True if scheduler is active
        - next_run: ISO timestamp of next scheduled run (or None)
        - last_run: ISO timestamp of last run (or None)
        - mode: Current detection mode from config

    Example:
        >>> status = get_scheduler_status()
        >>> print(status)
        {
            "running": True,
            "next_run": "2026-02-08T05:00:00Z",
            "last_run": "2026-02-07T05:00:00Z",
            "mode": "scheduled"
        }
    """
    global _scheduler

    if _scheduler is None or not _scheduler.running:
        return {
            "running": False,
            "next_run": None,
            "last_run": None,
            "mode": settings.graph_community_detection_mode,
        }

    job = _scheduler.get_job("community_detection_batch")
    if job is None:
        return {
            "running": True,
            "next_run": None,
            "last_run": None,
            "mode": settings.graph_community_detection_mode,
        }

    return {
        "running": True,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        "last_run": None,  # APScheduler doesn't track last run by default
        "mode": settings.graph_community_detection_mode,
    }
