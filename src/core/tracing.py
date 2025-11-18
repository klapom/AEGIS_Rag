"""LangSmith Tracing Integration.

Provides LangSmith observability and tracing for LangGraph agents.
Automatically traces all agent executions when enabled.

Sprint 4 Feature 4.5: LangSmith Integration
"""

import os

import structlog

from src.core.config import settings
from typing import Set

logger = structlog.get_logger(__name__)


def setup_langsmith_tracing() -> bool:
    """Setup LangSmith tracing for LangGraph agents.

    Sets environment variables required by LangChain for tracing.
    Should be called at application startup (in FastAPI lifespan).

    Environment variables set:
        - LANGCHAIN_TRACING_V2: Enable tracing ("true")
        - LANGCHAIN_PROJECT: Project name for organizing traces
        - LANGCHAIN_API_KEY: API key for authentication
        - LANGCHAIN_ENDPOINT: LangSmith API endpoint (optional)

    Returns:
        True if tracing was enabled, False if disabled or failed

    Example:
        >>> # In FastAPI lifespan
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     setup_langsmith_tracing()
        ...     yield
    """
    # Check if tracing is enabled
    if not settings.langsmith_tracing:
        logger.info(
            "langsmith_tracing_disabled",
            note="Set LANGSMITH_TRACING=true to enable",
        )
        return False

    # Check if API key is provided
    if not settings.langsmith_api_key:
        logger.warning(
            "langsmith_tracing_disabled_no_api_key",
            note="Set LANGSMITH_API_KEY to enable tracing",
        )
        return False

    try:
        # Set LangChain tracing environment variables
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key.get_secret_value()

        # Optional: Set custom endpoint if needed
        # os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

        logger.info(
            "langsmith_tracing_enabled",
            project=settings.langsmith_project,
            note="All LangGraph agents will be traced",
        )

        return True

    except Exception as e:
        logger.error(
            "langsmith_tracing_setup_failed",
            error=str(e),
        )
        return False


def disable_langsmith_tracing() -> None:
    """Disable LangSmith tracing.

    Removes tracing environment variables.
    Useful for testing or when you want to temporarily disable tracing.

    Example:
        >>> disable_langsmith_tracing()
        >>> # Run operations without tracing
        >>> setup_langsmith_tracing()  # Re-enable
    """
    try:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        os.environ.pop("LANGCHAIN_PROJECT", None)
        os.environ.pop("LANGCHAIN_API_KEY", None)
        os.environ.pop("LANGCHAIN_ENDPOINT", None)

        logger.info("langsmith_tracing_disabled")

    except Exception as e:
        logger.error(
            "langsmith_tracing_disable_failed",
            error=str(e),
        )


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is currently enabled.

    Returns:
        True if tracing is enabled, False otherwise

    Example:
        >>> if is_tracing_enabled():
        ...     print("Traces will be sent to LangSmith")
    """
    return os.environ.get("LANGCHAIN_TRACING_V2") == "true"  # type: ignore[no-any-return]


def get_trace_url(run_id: str) -> str:
    """Get LangSmith trace URL for a specific run.

    Args:
        run_id: LangChain run ID

    Returns:
        URL to view the trace in LangSmith UI

    Example:
        >>> url = get_trace_url("abc123")
        >>> print(f"View trace: {url}")
    """
    project = settings.langsmith_project
    return f"https://smith.langchain.com/o/default/projects/p/{project}/r/{run_id}"


# Export public API
__all__ = [
    "setup_langsmith_tracing",
    "disable_langsmith_tracing",
    "is_tracing_enabled",
    "get_trace_url",
]
