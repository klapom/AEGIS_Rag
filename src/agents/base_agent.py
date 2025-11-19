"""Base Agent class for LangGraph agents.

Provides common functionality and interface for all agents in the system.

Sprint 4 Feature 4.1: Base Agent Implementation
All agents inherit from this class and implement async processing.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents.

    All agents should inherit from this class and implement the process() method.
    Provides common functionality for logging, error handling, and state updates.

    All agents are async by design to support concurrent operations.
    """

    def __init__(self, name: str) -> None:
        """Initialize base agent.

        Args:
            name: Name of the agent (used in logging and tracing)
        """
        self.name = name
        self.logger = logger.bind(agent=name)

    @abstractmethod
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process the state and return updated state.

        This is the main method that each agent must implement.
        The method must be async to support concurrent operations.

        Args:
            state: Current agent state dictionary

        Returns:
            Updated agent state dictionary

        Raises:
            Exception: If processing fails
        """
        pass

    def get_name(self) -> str:
        """Get the agent name.

        Returns:
            Agent name string
        """
        return self.name

    async def handle_error(
        self, state: dict[str, Any], error: Exception, context: str
    ) -> dict[str, Any]:
        """Handle error during agent processing.

        Args:
            state: Current state
            error: Exception that occurred
            context: Context description

        Returns:
            State with error information added
        """
        self._log_error("agent_processing", error, context=context)
        self._set_error(state, error, context)
        return state

    def _add_trace(self, state: dict[str, Any], action: str) -> None:
        """Add trace entry to state.

        Args:
            state: Current state
            action: Action description
        """
        if "metadata" not in state:
            state["metadata"] = {}
        if "agent_path" not in state["metadata"]:
            state["metadata"]["agent_path"] = []

        trace_entry = f"{self.name}: {action}"
        if (
            not state["metadata"]["agent_path"]
            or state["metadata"]["agent_path"][-1] != trace_entry
        ):
            state["metadata"]["agent_path"].append(trace_entry)

    def _measure_latency(self) -> dict[str, Any]:
        """Start measuring execution latency.

        Returns:
            Dict with start_time for latency calculation
        """
        return {"start_time": time.perf_counter()}

    def _calculate_latency_ms(self, timing: dict[str, Any]) -> float:
        """Calculate latency in milliseconds.

        Args:
            timing: Dict with start_time from _measure_latency()

        Returns:
            Latency in milliseconds
        """
        return (time.perf_counter() - timing["start_time"]) * 1000  # type: ignore[no-any-return]

    def _log_success(self, operation: str, **kwargs: Any) -> None:
        """Log successful operation.

        Args:
            operation: Operation description
            **kwargs: Additional log fields
        """
        self.logger.info(f"{operation}_success", **kwargs)

    def _log_error(self, operation: str, error: Exception, **kwargs: Any) -> None:
        """Log error.

        Args:
            operation: Operation description
            error: Exception that occurred
            **kwargs: Additional log fields
        """
        self.logger.error(
            f"{operation}_failed", error=str(error), error_type=type(error).__name__, **kwargs
        )

    def _set_error(self, state: dict[str, Any], error: Exception, context: str) -> None:
        """Set error in state.

        Args:
            state: Current state
            error: Exception that occurred
            context: Context description
        """
        if "metadata" not in state:
            state["metadata"] = {}

        state["metadata"]["error"] = {
            "agent": self.name,
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
        }
