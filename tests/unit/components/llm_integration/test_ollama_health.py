"""Unit tests for Ollama Health Monitor.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy

Tests:
- Health check success/failure
- Consecutive failure tracking
- Restart trigger on max failures
- Fallback recommendation logic
- Background monitoring loop
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.components.llm_integration.ollama_health import OllamaHealthMonitor, get_ollama_health_monitor


class TestOllamaHealthMonitor:
    """Test suite for OllamaHealthMonitor."""

    @pytest.fixture
    def monitor(self) -> OllamaHealthMonitor:
        """Create OllamaHealthMonitor instance for testing."""
        return OllamaHealthMonitor(
            ollama_base_url="http://localhost:11434",
            health_check_interval_s=1,  # Short interval for testing
            max_consecutive_failures=3,
        )

    @pytest.mark.asyncio
    async def test_check_health_success(self, monitor: OllamaHealthMonitor) -> None:
        """Test health check succeeds with 200 OK response."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            # Check health
            is_healthy = await monitor.check_health()

            # Assertions
            assert is_healthy is True
            assert monitor.is_healthy is True
            assert monitor.consecutive_failures == 0
            assert monitor.last_success_time is not None

            # Verify HTTP call
            mock_client.get.assert_called_once_with("http://localhost:11434/api/health")

    @pytest.mark.asyncio
    async def test_check_health_failure_status_code(self, monitor: OllamaHealthMonitor) -> None:
        """Test health check fails with non-200 status code."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 503

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            # Check health
            is_healthy = await monitor.check_health()

            # Assertions
            assert is_healthy is False
            assert monitor.is_healthy is False
            assert monitor.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_check_health_failure_timeout(self, monitor: OllamaHealthMonitor) -> None:
        """Test health check fails with timeout exception."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            # Check health
            is_healthy = await monitor.check_health()

            # Assertions
            assert is_healthy is False
            assert monitor.is_healthy is False
            assert monitor.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_check_health_failure_request_error(self, monitor: OllamaHealthMonitor) -> None:
        """Test health check fails with request error."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            # Check health
            is_healthy = await monitor.check_health()

            # Assertions
            assert is_healthy is False
            assert monitor.is_healthy is False
            assert monitor.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_consecutive_failures_tracking(self, monitor: OllamaHealthMonitor) -> None:
        """Test consecutive failure tracking increments correctly."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 503

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            # Check health 3 times (should increment consecutive_failures)
            await monitor.check_health()
            assert monitor.consecutive_failures == 1

            await monitor.check_health()
            assert monitor.consecutive_failures == 2

            await monitor.check_health()
            assert monitor.consecutive_failures == 3

    @pytest.mark.asyncio
    async def test_consecutive_failures_reset_on_success(
        self, monitor: OllamaHealthMonitor
    ) -> None:
        """Test consecutive failures reset to 0 on successful health check."""
        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_cls:
            # First 2 failures
            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 503

            # Then success
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=[mock_response_fail, mock_response_fail, mock_response_success]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            # Check health 3 times
            await monitor.check_health()
            assert monitor.consecutive_failures == 1

            await monitor.check_health()
            assert monitor.consecutive_failures == 2

            await monitor.check_health()
            assert monitor.consecutive_failures == 0  # Reset on success
            assert monitor.is_healthy is True

    @pytest.mark.asyncio
    async def test_trigger_restart(self, monitor: OllamaHealthMonitor) -> None:
        """Test restart trigger logs error and resets failure count."""
        monitor.consecutive_failures = 3

        # Trigger restart
        result = await monitor.trigger_restart()

        # Assertions (restart not implemented yet, returns False)
        assert result is False
        assert monitor.consecutive_failures == 0  # Reset after trigger

    @pytest.mark.asyncio
    async def test_should_fallback_to_next_rank(self, monitor: OllamaHealthMonitor) -> None:
        """Test fallback recommendation logic."""
        # Healthy - no fallback
        monitor.is_healthy = True
        monitor.consecutive_failures = 0
        assert monitor.should_fallback_to_next_rank() is False

        # 1 failure - not yet (transient)
        monitor.is_healthy = False
        monitor.consecutive_failures = 1
        assert monitor.should_fallback_to_next_rank() is False

        # 2 failures - fallback recommended
        monitor.consecutive_failures = 2
        assert monitor.should_fallback_to_next_rank() is True

        # 3 failures - fallback recommended
        monitor.consecutive_failures = 3
        assert monitor.should_fallback_to_next_rank() is True

    @pytest.mark.asyncio
    async def test_get_health_status(self, monitor: OllamaHealthMonitor) -> None:
        """Test health status reporting."""
        monitor.is_healthy = False
        monitor.consecutive_failures = 2

        status = monitor.get_health_status()

        # Assertions
        assert status["is_healthy"] is False
        assert status["consecutive_failures"] == 2
        assert status["should_fallback"] is True
        assert status["ollama_base_url"] == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_start_and_stop(self, monitor: OllamaHealthMonitor) -> None:
        """Test background monitoring start and stop."""
        # Mock check_health to avoid actual HTTP calls
        monitor.check_health = AsyncMock(return_value=True)

        # Start monitor
        await monitor.start()
        assert monitor._is_running is True
        assert monitor._monitor_task is not None

        # Wait a bit for background task to run
        await asyncio.sleep(0.1)

        # Stop monitor
        await monitor.stop()
        assert monitor._is_running is False

        # Verify check_health was called
        assert monitor.check_health.call_count >= 1

    @pytest.mark.asyncio
    async def test_monitor_loop_triggers_restart(self, monitor: OllamaHealthMonitor) -> None:
        """Test monitor loop triggers restart on max failures."""
        # Mock check_health to fail max_consecutive_failures times
        monitor.check_health = AsyncMock(return_value=False)
        monitor.trigger_restart = AsyncMock(return_value=True)

        # Set consecutive failures to max - 1 (next failure triggers restart)
        monitor.consecutive_failures = monitor.max_consecutive_failures - 1

        # Start monitor
        await monitor.start()

        # Wait for background task to run and trigger restart
        await asyncio.sleep(1.5)  # > health_check_interval_s

        # Stop monitor
        await monitor.stop()

        # Verify restart was triggered
        assert monitor.trigger_restart.call_count >= 1


def test_get_ollama_health_monitor_singleton() -> None:
    """Test get_ollama_health_monitor returns singleton instance."""
    monitor1 = get_ollama_health_monitor()
    monitor2 = get_ollama_health_monitor()

    assert monitor1 is monitor2
