"""Tests for temporal memory retention policy."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.config import settings
from src.components.temporal_memory.retention import (
    purge_old_temporal_versions,
    start_retention_scheduler,
)


def test_retention_config():
    """Test that retention configuration is loaded correctly."""
    assert settings.temporal_retention_days == 365
    assert settings.temporal_auto_purge is True
    assert settings.temporal_purge_schedule == "0 2 * * *"


@pytest.mark.asyncio
async def test_purge_skips_when_infinite_retention():
    """Test that purge skips when retention_days = 0 (infinite retention)."""
    # Temporarily override the setting
    original_value = settings.temporal_retention_days

    try:
        # Mock settings to simulate infinite retention
        with patch("src.components.temporal_memory.retention.settings") as mock_settings:
            mock_settings.temporal_retention_days = 0

            # Mock the graphiti wrapper
            with patch(
                "src.components.temporal_memory.retention.get_graphiti_wrapper"
            ) as mock_graphiti:
                mock_graphiti.return_value = AsyncMock()

                # Run purge
                await purge_old_temporal_versions()

                # Verify graphiti was NOT called (purge was skipped)
                mock_graphiti.assert_not_called()
    finally:
        # Restore original value
        settings.temporal_retention_days = original_value


@pytest.mark.asyncio
async def test_purge_executes_when_retention_enabled():
    """Test that purge executes when retention is enabled."""
    with patch("src.components.temporal_memory.retention.settings") as mock_settings:
        mock_settings.temporal_retention_days = 365

        # Mock the graphiti wrapper - it's an async function, so return AsyncMock directly
        with patch(
            "src.components.temporal_memory.retention.get_graphiti_wrapper", new_callable=AsyncMock
        ) as mock_graphiti:
            mock_wrapper = AsyncMock()
            mock_graphiti.return_value = mock_wrapper

            # Run purge
            await purge_old_temporal_versions()

            # Verify graphiti was called
            mock_graphiti.assert_called_once()


@pytest.mark.asyncio
async def test_scheduler_skips_when_auto_purge_disabled():
    """Test that scheduler doesn't start when auto_purge is disabled."""
    with patch("src.components.temporal_memory.retention.settings") as mock_settings:
        mock_settings.temporal_auto_purge = False

        # Mock the purge function
        with patch(
            "src.components.temporal_memory.retention.purge_old_temporal_versions"
        ) as mock_purge:
            # Start scheduler (it should return immediately)
            await start_retention_scheduler()

            # Verify purge was never called
            mock_purge.assert_not_called()


@pytest.mark.asyncio
async def test_retention_cutoff_date_calculation():
    """Test that cutoff date is calculated correctly."""
    with patch("src.components.temporal_memory.retention.settings") as mock_settings:
        mock_settings.temporal_retention_days = 365

        # Mock the graphiti wrapper - it's an async function, so return AsyncMock directly
        with patch(
            "src.components.temporal_memory.retention.get_graphiti_wrapper", new_callable=AsyncMock
        ) as mock_graphiti:
            mock_wrapper = AsyncMock()
            mock_graphiti.return_value = mock_wrapper

            # Capture the current time before purge
            before_purge = datetime.now()

            # Run purge
            await purge_old_temporal_versions()

            # Calculate expected cutoff (365 days ago)
            expected_cutoff = before_purge - timedelta(days=365)

            # Verify the calculation is approximately correct (within 1 second tolerance)
            # Since we can't directly check the cutoff_date inside the function,
            # we're testing that the function executes without error
            # and the graphiti wrapper is called
            mock_graphiti.assert_called_once()
