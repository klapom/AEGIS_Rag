"""Unit tests for community detection batch job.

Sprint 126 Feature 126.1: Scheduled Community Detection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

from src.jobs.community_batch_job import (
    run_community_detection_batch,
    start_community_detection_scheduler,
    shutdown_community_detection_scheduler,
    get_scheduler_status,
)
from src.core.models import Community


@pytest.mark.asyncio
async def test_run_community_detection_batch_success():
    """Test successful batch job execution."""
    # Mock community detector
    mock_community = Community(
        id="community_1",
        label="Test Community",
        entity_ids=["entity_1", "entity_2"],
        size=2,
        density=0.8,
        created_at=datetime.now(UTC),
        metadata={"algorithm": "leiden"},
    )

    mock_detector = MagicMock()
    mock_detector.detect_communities = AsyncMock(return_value=[mock_community])
    mock_detector.algorithm = "leiden"

    with patch(
        "src.jobs.community_batch_job.get_community_detector",
        return_value=mock_detector,
    ):
        result = await run_community_detection_batch()

        # Assertions
        assert result["success"] is True
        assert result["communities_detected"] == 1
        assert result["summaries_generated"] == 1
        assert result["algorithm"] == "leiden"
        assert "job_id" in result
        assert "started_at" in result
        assert "completed_at" in result
        assert result["duration_seconds"] >= 0  # May be 0 for fast mock execution

        # Verify detector was called
        mock_detector.detect_communities.assert_called_once_with(track_delta=True)


@pytest.mark.asyncio
async def test_run_community_detection_batch_failure():
    """Test batch job failure handling."""
    # Mock community detector that raises exception
    mock_detector = MagicMock()
    mock_detector.detect_communities = AsyncMock(side_effect=Exception("Test error"))
    mock_detector.algorithm = "leiden"

    with patch(
        "src.jobs.community_batch_job.get_community_detector",
        return_value=mock_detector,
    ):
        result = await run_community_detection_batch()

        # Assertions
        assert result["success"] is False
        assert result["communities_detected"] == 0
        assert result["summaries_generated"] == 0
        assert "error" in result
        assert "Test error" in result["error"]
        assert result["duration_seconds"] >= 0  # May be 0 for fast mock execution


def test_start_community_detection_scheduler_scheduled_mode():
    """Test scheduler starts in scheduled mode."""
    with patch("src.jobs.community_batch_job.settings") as mock_settings:
        mock_settings.graph_community_detection_mode = "scheduled"

        # Mock APScheduler
        with patch("src.jobs.community_batch_job.AsyncIOScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler
            mock_scheduler.running = False

            # Mock job
            mock_job = MagicMock()
            mock_job.next_run_time = datetime.now(UTC)
            mock_scheduler.get_job.return_value = mock_job

            scheduler = start_community_detection_scheduler()

            # Assertions
            assert scheduler is not None
            mock_scheduler.start.assert_called_once()
            mock_scheduler.add_job.assert_called_once()


def test_start_community_detection_scheduler_sync_mode():
    """Test scheduler does not start in sync mode."""
    with patch("src.jobs.community_batch_job.settings") as mock_settings:
        mock_settings.graph_community_detection_mode = "sync"

        scheduler = start_community_detection_scheduler()

        # Should return None in sync mode
        assert scheduler is None


def test_start_community_detection_scheduler_disabled_mode():
    """Test scheduler does not start in disabled mode."""
    with patch("src.jobs.community_batch_job.settings") as mock_settings:
        mock_settings.graph_community_detection_mode = "disabled"

        scheduler = start_community_detection_scheduler()

        # Should return None in disabled mode
        assert scheduler is None


def test_shutdown_community_detection_scheduler():
    """Test scheduler shutdown."""
    with patch("src.jobs.community_batch_job._scheduler") as mock_scheduler:
        mock_scheduler.running = True

        shutdown_community_detection_scheduler()

        # Should call shutdown with wait=True
        mock_scheduler.shutdown.assert_called_once_with(wait=True)


def test_get_scheduler_status_running():
    """Test get_scheduler_status when scheduler is running."""
    with patch("src.jobs.community_batch_job._scheduler") as mock_scheduler:
        mock_scheduler.running = True

        # Mock job
        mock_job = MagicMock()
        mock_job.next_run_time = datetime.now(UTC)
        mock_scheduler.get_job.return_value = mock_job

        with patch("src.jobs.community_batch_job.settings") as mock_settings:
            mock_settings.graph_community_detection_mode = "scheduled"

            status = get_scheduler_status()

            assert status["running"] is True
            assert status["next_run"] is not None
            assert status["mode"] == "scheduled"


def test_get_scheduler_status_not_running():
    """Test get_scheduler_status when scheduler is not running."""
    with patch("src.jobs.community_batch_job._scheduler", None):
        with patch("src.jobs.community_batch_job.settings") as mock_settings:
            mock_settings.graph_community_detection_mode = "disabled"

            status = get_scheduler_status()

            assert status["running"] is False
            assert status["next_run"] is None
            assert status["mode"] == "disabled"
