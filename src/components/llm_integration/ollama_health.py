"""Ollama Health Monitor for LLM Extraction Reliability.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy

This module provides health monitoring for Ollama LLM service:
- Periodic health checks (every 30s)
- Automatic restart on consecutive failures (3+ failures)
- Graceful degradation to next cascade rank on persistent failures
- Integration with extraction cascade fallback logic

The monitor runs as a background task and provides health status to ExtractionService.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


class OllamaHealthMonitor:
    """Health monitor for Ollama LLM service.

    Provides methods for:
    - Periodic health checks (GET /api/health every 30s)
    - Automatic restart on consecutive failures
    - Health status reporting
    - Integration with cascade fallback

    Attributes:
        ollama_base_url: Ollama API base URL
        health_check_interval_s: Interval between health checks (seconds)
        max_consecutive_failures: Max failures before triggering restart (default: 3)
        is_healthy: Current health status (True/False)
        consecutive_failures: Count of consecutive health check failures
    """

    def __init__(
        self,
        ollama_base_url: str | None = None,
        health_check_interval_s: int = 30,
        max_consecutive_failures: int = 3,
    ) -> None:
        """Initialize Ollama health monitor.

        Args:
            ollama_base_url: Ollama API base URL (default: from settings)
            health_check_interval_s: Interval between health checks (default: 30s)
            max_consecutive_failures: Max failures before restart (default: 3)
        """
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.health_check_interval_s = health_check_interval_s
        self.max_consecutive_failures = max_consecutive_failures

        # Health state
        self.is_healthy = True
        self.consecutive_failures = 0
        self.last_check_time: datetime | None = None
        self.last_success_time: datetime | None = None

        # Background task
        self._monitor_task: asyncio.Task[Any] | None = None
        self._is_running = False

        logger.info(
            "ollama_health_monitor_initialized",
            ollama_base_url=self.ollama_base_url,
            health_check_interval_s=self.health_check_interval_s,
            max_consecutive_failures=self.max_consecutive_failures,
        )

    async def check_health(self) -> bool:
        """Check Ollama health status with a single HTTP request.

        Returns:
            True if Ollama is healthy, False otherwise

        Example:
            >>> monitor = OllamaHealthMonitor()
            >>> is_healthy = await monitor.check_health()
            >>> if not is_healthy:
            ...     logger.warning("ollama_unhealthy")
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Ollama health endpoint: GET /api/health
                # Returns 200 OK if healthy
                response = await client.get(f"{self.ollama_base_url}/api/health")

                if response.status_code == 200:
                    self.consecutive_failures = 0
                    self.is_healthy = True
                    self.last_success_time = datetime.now()

                    logger.debug(
                        "ollama_health_check_success",
                        status_code=response.status_code,
                        consecutive_failures=self.consecutive_failures,
                    )

                    return True
                else:
                    self.consecutive_failures += 1
                    self.is_healthy = False

                    logger.warning(
                        "ollama_health_check_failed",
                        status_code=response.status_code,
                        consecutive_failures=self.consecutive_failures,
                    )

                    return False

        except (httpx.RequestError, httpx.TimeoutException) as e:
            self.consecutive_failures += 1
            self.is_healthy = False

            logger.warning(
                "ollama_health_check_error",
                error=str(e),
                consecutive_failures=self.consecutive_failures,
                max_allowed=self.max_consecutive_failures,
            )

            return False

        finally:
            self.last_check_time = datetime.now()

    async def trigger_restart(self) -> bool:
        """Trigger Ollama restart (if restart logic is available).

        Returns:
            True if restart triggered successfully, False otherwise

        Note:
            Current implementation logs the restart trigger but does not
            actually restart Ollama (requires Docker/systemd integration).
            Future: Integrate with Docker Compose restart or systemd service.
        """
        logger.error(
            "ollama_restart_triggered",
            consecutive_failures=self.consecutive_failures,
            max_allowed=self.max_consecutive_failures,
            note="restart_not_implemented_manual_intervention_required",
        )

        # TODO: Implement actual restart logic in Sprint 83+
        # Options:
        # 1. Docker Compose: subprocess.run(["docker", "compose", "restart", "ollama"])
        # 2. Systemd: subprocess.run(["systemctl", "restart", "ollama"])
        # 3. Kubernetes: kubectl rollout restart deployment ollama

        # For now, just reset failure count to prevent spam
        self.consecutive_failures = 0

        return False

    async def _monitor_loop(self) -> None:
        """Background monitoring loop (runs every health_check_interval_s).

        This method runs as an asyncio background task and:
        1. Checks Ollama health every N seconds
        2. Triggers restart on max_consecutive_failures
        3. Logs health status changes
        """
        logger.info(
            "ollama_health_monitor_started",
            interval_s=self.health_check_interval_s,
        )

        while self._is_running:
            try:
                is_healthy = await self.check_health()

                # Trigger restart if max consecutive failures reached
                if not is_healthy and self.consecutive_failures >= self.max_consecutive_failures:
                    logger.error(
                        "ollama_max_failures_reached_triggering_restart",
                        consecutive_failures=self.consecutive_failures,
                        max_allowed=self.max_consecutive_failures,
                    )
                    await self.trigger_restart()

                # Sleep until next check
                await asyncio.sleep(self.health_check_interval_s)

            except asyncio.CancelledError:
                logger.info("ollama_health_monitor_cancelled")
                break

            except Exception as e:
                logger.error(
                    "ollama_health_monitor_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Continue monitoring even on unexpected errors
                await asyncio.sleep(self.health_check_interval_s)

    async def start(self) -> None:
        """Start background health monitoring.

        Example:
            >>> monitor = OllamaHealthMonitor()
            >>> await monitor.start()
            >>> # Monitor runs in background, checking health every 30s
        """
        if self._is_running:
            logger.warning("ollama_health_monitor_already_running")
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("ollama_health_monitor_background_task_started")

    async def stop(self) -> None:
        """Stop background health monitoring.

        Example:
            >>> monitor = OllamaHealthMonitor()
            >>> await monitor.start()
            >>> # ... later ...
            >>> await monitor.stop()
        """
        if not self._is_running:
            logger.warning("ollama_health_monitor_not_running")
            return

        self._is_running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("ollama_health_monitor_stopped")

    def should_fallback_to_next_rank(self) -> bool:
        """Check if extraction should fallback to next cascade rank.

        Returns:
            True if Ollama is unhealthy and fallback is recommended, False otherwise

        Example:
            >>> monitor = get_ollama_health_monitor()
            >>> if monitor.should_fallback_to_next_rank():
            ...     logger.warning("ollama_unhealthy_falling_back_to_rank2")
            ...     # Use Rank 2 (gpt-oss:20b) instead of Rank 1 (nemotron3)
        """
        # Fallback if:
        # 1. Ollama is currently unhealthy
        # 2. We have at least 2 consecutive failures (not just a transient blip)
        should_fallback = not self.is_healthy and self.consecutive_failures >= 2

        if should_fallback:
            logger.warning(
                "ollama_unhealthy_recommending_fallback",
                consecutive_failures=self.consecutive_failures,
                is_healthy=self.is_healthy,
                last_check_time=self.last_check_time.isoformat() if self.last_check_time else None,
            )

        return should_fallback

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status as a dictionary.

        Returns:
            Dictionary with health status:
            {
                "is_healthy": bool,
                "consecutive_failures": int,
                "last_check_time": str (ISO format),
                "last_success_time": str (ISO format),
                "should_fallback": bool
            }
        """
        return {
            "is_healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "last_success_time": (
                self.last_success_time.isoformat() if self.last_success_time else None
            ),
            "should_fallback": self.should_fallback_to_next_rank(),
            "ollama_base_url": self.ollama_base_url,
        }


# Global singleton instance
_ollama_health_monitor: OllamaHealthMonitor | None = None


def get_ollama_health_monitor() -> OllamaHealthMonitor:
    """Get global Ollama health monitor instance (singleton).

    Returns:
        OllamaHealthMonitor instance

    Example:
        >>> monitor = get_ollama_health_monitor()
        >>> await monitor.start()
        >>> # Check health status
        >>> status = monitor.get_health_status()
        >>> logger.info("ollama_health", **status)
    """
    global _ollama_health_monitor

    if _ollama_health_monitor is None:
        _ollama_health_monitor = OllamaHealthMonitor()

    return _ollama_health_monitor
