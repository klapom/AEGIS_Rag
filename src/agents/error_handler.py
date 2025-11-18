"""Centralized Error Handling for LangGraph Agents.

This module provides a unified error handling system for all agents in the
multi-agent RAG system. It defines exception hierarchies and error handling
utilities for graceful degradation.

Sprint 4 Feature 4.6: Error Handling & Retry Logic
"""

from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Exception Hierarchy
# ============================================================================


class AgentExecutionError(Exception):
    """Base exception for agent execution errors.

    All agent-specific exceptions inherit from this class.
    Provides structured error information for debugging and recovery.
    """

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        context: Dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize agent execution error.

        Args:
            message: Error message
            agent_name: Name of the agent that raised the error
            context: Additional context information
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.agent_name = agent_name
        self.context = context or {}
        self.original_error = original_error

    def __str__(self) -> str:
        """Return string representation."""
        parts = [self.message]
        if self.agent_name:
            parts.append(f"[agent={self.agent_name}]")
        if self.original_error:
            parts.append(f"[caused by: {type(self.original_error).__name__}]")
        return " ".join(parts)


class RetrievalError(AgentExecutionError):
    """Raised when vector or graph retrieval fails.

    This error is retryable - the system can attempt the retrieval again.
    Typically caused by:
    - Database connection issues
    - Query parsing errors
    - Timeout errors
    """

    pass


class LLMError(AgentExecutionError):
    """Raised when LLM operations fail.

    This error is retryable - the system can attempt the LLM call again.
    Typically caused by:
    - Ollama server unavailable
    - Model not loaded
    - Timeout errors
    - Rate limiting
    """

    pass


class StateError(AgentExecutionError):
    """Raised when state validation or manipulation fails.

    This error is NOT retryable - the state is invalid and needs fixing.
    Typically caused by:
    - Missing required fields
    - Invalid data types
    - Schema validation errors
    """

    pass


class RouterError(AgentExecutionError):
    """Raised when query routing fails.

    This error is retryable - can fall back to default routing.
    Typically caused by:
    - Intent classification failure
    - Invalid routing decision
    """

    pass


class TimeoutError(AgentExecutionError):
    """Raised when agent execution times out.

    This error is retryable with increased timeout.
    Typically caused by:
    - Long-running operations
    - Slow database queries
    - Unresponsive external services
    """

    pass


# ============================================================================
# Error Handler
# ============================================================================


def handle_agent_error(
    error: Exception,
    state: Dict[str, Any],
    agent_name: str,
    context: str | None = None,
) -> Dict[str, Any]:
    """Handle agent execution error and update state.

    This function provides centralized error handling for all agents.
    It logs the error, updates state metadata, and returns the modified state
    without raising an exception (graceful degradation).

    Args:
        error: Exception that occurred
        state: Current agent state
        agent_name: Name of the agent that encountered the error
        context: Additional context description

    Returns:
        Updated state with error information added

    Example:
        >>> try:
        ...     result = await risky_operation()
        ... except Exception as e:
        ...     state = handle_agent_error(e, state, "VectorSearchAgent", "search")
        ...     return state
    """
    # Determine error type and severity
    error_type = type(error).__name__
    error_message = str(error)
    is_retryable = _is_retryable_error(error)

    # Log error with structured logging
    logger.error(
        "agent_error_handled",
        agent=agent_name,
        error_type=error_type,
        error_message=error_message,
        context=context,
        retryable=is_retryable,
    )

    # Initialize metadata if needed
    if "metadata" not in state:
        state["metadata"] = {}

    # Add error to metadata
    error_info = {
        "agent": agent_name,
        "error_type": error_type,
        "message": error_message,
        "context": context,
        "retryable": is_retryable,
    }

    # Store error (keep list of all errors if multiple occur)
    if "errors" not in state["metadata"]:
        state["metadata"]["errors"] = []
    state["metadata"]["errors"].append(error_info)

    # Also set current error for quick access
    state["metadata"]["error"] = error_info

    # Add to agent path
    if "agent_path" not in state["metadata"]:
        state["metadata"]["agent_path"] = []
    state["metadata"]["agent_path"].append(f"{agent_name}: error - {error_type}")

    return state


def _is_retryable_error(error: Exception) -> bool:
    """Determine if an error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if the error is retryable, False otherwise
    """
    # Retryable error types
    retryable_types = (
        RetrievalError,
        LLMError,
        RouterError,
        TimeoutError,
    )

    # Non-retryable error types
    non_retryable_types = (
        StateError,
        ValueError,
        TypeError,
        KeyError,
    )

    # Check explicit types
    if isinstance(error, retryable_types):
        return True
    if isinstance(error, non_retryable_types):
        return False

    # Check by error message patterns (heuristic)
    error_message = str(error).lower()
    retryable_patterns = [
        "connection",
        "timeout",
        "unavailable",
        "refused",
        "rate limit",
        "temporary",
    ]

    return any(pattern in error_message for pattern in retryable_patterns)


def get_error_summary(state: Dict[str, Any]) -> Dict[str, Any] | None:
    """Get summary of errors from state.

    Args:
        state: Agent state

    Returns:
        Error summary dict or None if no errors
    """
    if "metadata" not in state or "error" not in state["metadata"]:
        return None

    error = state["metadata"]["error"]
    return {
        "has_error": True,
        "agent": error.get("agent"),
        "error_type": error.get("error_type"),
        "message": error.get("message"),
        "retryable": error.get("retryable", False),
        "total_errors": len(state["metadata"].get("errors", [])),
    }


def clear_errors(state: Dict[str, Any]) -> Dict[str, Any]:
    """Clear error information from state.

    Useful when retrying operations or starting new queries.

    Args:
        state: Agent state

    Returns:
        State with errors cleared
    """
    if "metadata" in state:
        state["metadata"].pop("error", None)
        state["metadata"].pop("errors", None)

    return state


# Export public API
__all__ = [
    "AgentExecutionError",
    "RetrievalError",
    "LLMError",
    "StateError",
    "RouterError",
    "TimeoutError",
    "handle_agent_error",
    "get_error_summary",
    "clear_errors",
]
