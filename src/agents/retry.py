"""Retry Logic for Agent Operations.

Provides decorators and utilities for retrying failed agent operations
with exponential backoff and intelligent error handling.

Sprint 4 Feature 4.6: Error Handling & Retry Logic
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
import structlog
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.error_handler import LLMError, RetrievalError, RouterError

logger = structlog.get_logger(__name__)

# Type variable for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# Retry Callbacks
# ============================================================================


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry attempts for observability.

    Args:
        retry_state: Tenacity retry state
    """
    if retry_state.attempt_number > 1:
        logger.warning(
            "retry_attempt",
            attempt=retry_state.attempt_number,
            function=retry_state.fn.__name__ if retry_state.fn else "unknown",
            error=(
                str(retry_state.outcome.exception())
                if retry_state.outcome and retry_state.outcome.failed
                else None
            ),
        )


# ============================================================================
# Retry Decorators
# ============================================================================


def retry_on_failure(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable[[F], F]:
    """Decorator to retry failed agent operations.

    Retries operations that fail with retryable errors (RetrievalError, LLMError,
    httpx errors). Does not retry validation or state errors.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        backoff_factor: Exponential backoff multiplier (default: 2.0)
        min_wait: Minimum wait time in seconds (default: 1.0)
        max_wait: Maximum wait time in seconds (default: 10.0)

    Returns:
        Decorated function with retry logic

    Example:
        >>> @retry_on_failure(max_attempts=3)
        ... async def search_vectors(query: str):
        ...     # Operation that may fail transiently
        ...     return await vector_db.search(query)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=backoff_factor,
                min=min_wait,
                max=max_wait,
            ),
            retry=retry_if_exception_type(
                (
                    RetrievalError,
                    LLMError,
                    RouterError,
                    httpx.HTTPError,
                    httpx.TimeoutException,
                    ConnectionError,
                )
            ),
            before_sleep=log_retry_attempt,
            reraise=True,
        )
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=backoff_factor,
                min=min_wait,
                max=max_wait,
            ),
            retry=retry_if_exception_type(
                (
                    RetrievalError,
                    LLMError,
                    RouterError,
                    httpx.HTTPError,
                    httpx.TimeoutException,
                    ConnectionError,
                )
            ),
            before_sleep=log_retry_attempt,
            reraise=True,
        )
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def retry_with_fallback(
    max_attempts: int = 3,
    fallback_value: Any = None,
) -> Callable[[F], F]:
    """Decorator to retry with fallback value on final failure.

    Similar to retry_on_failure but returns a fallback value instead of
    raising an exception after all retries are exhausted.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        fallback_value: Value to return on final failure (default: None)

    Returns:
        Decorated function with retry logic and fallback

    Example:
        >>> @retry_with_fallback(max_attempts=3, fallback_value=[])
        ... async def get_results(query: str):
        ...     return await search(query)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await retry_on_failure(max_attempts=max_attempts)(func)(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "retry_exhausted_using_fallback",
                    function=func.__name__,
                    error=str(e),
                    fallback_value=fallback_value,
                )
                return fallback_value

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return retry_on_failure(max_attempts=max_attempts)(func)(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "retry_exhausted_using_fallback",
                    function=func.__name__,
                    error=str(e),
                    fallback_value=fallback_value,
                )
                return fallback_value

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator


# ============================================================================
# Utility Functions
# ============================================================================


async def retry_async_operation(
    operation: Callable[[], Any],
    max_attempts: int = 3,
    operation_name: str = "operation",
) -> Any:
    """Retry an async operation with logging.

    Utility function for one-off retry logic without decorators.

    Args:
        operation: Async function to retry
        max_attempts: Maximum number of attempts
        operation_name: Name for logging

    Returns:
        Result of the operation

    Raises:
        Exception: If all retries fail

    Example:
        >>> result = await retry_async_operation(
        ...     lambda: client.search(query),
        ...     max_attempts=3,
        ...     operation_name="vector_search"
        ... )
    """
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(
                "retry_operation_attempt",
                operation=operation_name,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            result = await operation()
            if attempt > 1:
                logger.info(
                    "retry_operation_succeeded",
                    operation=operation_name,
                    attempt=attempt,
                )
            return result

        except Exception as e:
            last_error = e
            logger.warning(
                "retry_operation_failed",
                operation=operation_name,
                attempt=attempt,
                max_attempts=max_attempts,
                error=str(e),
            )

            if attempt < max_attempts:
                # Exponential backoff
                import asyncio

                wait_time = min(2**attempt, 10)
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    "retry_operation_exhausted",
                    operation=operation_name,
                    total_attempts=max_attempts,
                    final_error=str(e),
                )

    # Raise last error after all retries
    if last_error:
        raise last_error

    # Should never reach here
    raise RuntimeError(f"Retry operation failed: {operation_name}")


# Export public API
__all__ = [
    "retry_on_failure",
    "retry_with_fallback",
    "retry_async_operation",
]
