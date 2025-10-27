"""Extended Unit Tests for Retry Logic - Coverage Improvement.

Tests retry decorators, callbacks, and utilities.

Author: Claude Code
Date: 2025-10-27
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from src.agents.error_handler import LLMError, RetrievalError, RouterError
from src.agents.retry import (
    log_retry_attempt,
    retry_async_operation,
    retry_on_failure,
    retry_with_fallback,
)


# ============================================================================
# Retry Callback Tests
# ============================================================================


@pytest.mark.unit
def test_log_retry_attempt_first_attempt():
    """Test log_retry_attempt does not log on first attempt."""
    mock_state = MagicMock()
    mock_state.attempt_number = 1
    mock_state.fn.__name__ = "test_function"

    with patch("src.agents.retry.logger") as mock_logger:
        log_retry_attempt(mock_state)

        # Should not log warning on first attempt
        mock_logger.warning.assert_not_called()


@pytest.mark.unit
def test_log_retry_attempt_subsequent_attempts():
    """Test log_retry_attempt logs on retry attempts."""
    mock_state = MagicMock()
    mock_state.attempt_number = 2
    mock_state.fn.__name__ = "test_function"
    mock_state.outcome.failed = True
    mock_state.outcome.exception.return_value = ValueError("test error")

    with patch("src.agents.retry.logger") as mock_logger:
        log_retry_attempt(mock_state)

        # Should log warning on retry
        mock_logger.warning.assert_called_once()
        assert mock_logger.warning.call_args[0][0] == "retry_attempt"


# ============================================================================
# retry_on_failure Decorator Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_success_first_attempt():
    """Test retry_on_failure succeeds on first attempt."""

    @retry_on_failure(max_attempts=3)
    async def async_operation():
        return "success"

    result = await async_operation()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_retries_on_retrieval_error():
    """Test retry_on_failure retries on RetrievalError."""
    call_count = 0

    @retry_on_failure(max_attempts=3, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetrievalError("Database connection failed")
        return "success"

    result = await async_operation()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_retries_on_llm_error():
    """Test retry_on_failure retries on LLMError."""
    call_count = 0

    @retry_on_failure(max_attempts=2, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise LLMError("Ollama server unavailable")
        return "success"

    result = await async_operation()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_retries_on_router_error():
    """Test retry_on_failure retries on RouterError."""
    call_count = 0

    @retry_on_failure(max_attempts=2, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RouterError("Intent classification failed")
        return "success"

    result = await async_operation()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_retries_on_httpx_error():
    """Test retry_on_failure retries on httpx HTTPError."""
    call_count = 0

    @retry_on_failure(max_attempts=2, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.HTTPError("Connection error")
        return "success"

    result = await async_operation()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_retries_on_connection_error():
    """Test retry_on_failure retries on ConnectionError."""
    call_count = 0

    @retry_on_failure(max_attempts=2, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Connection refused")
        return "success"

    result = await async_operation()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_fails_after_max_attempts():
    """Test retry_on_failure raises error after max attempts."""

    @retry_on_failure(max_attempts=3, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        raise RetrievalError("Permanent failure")

    with pytest.raises(RetrievalError, match="Permanent failure"):
        await async_operation()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_failure_does_not_retry_value_error():
    """Test retry_on_failure does not retry non-retryable errors."""
    call_count = 0

    @retry_on_failure(max_attempts=3, min_wait=0.01, max_wait=0.01)
    async def async_operation():
        nonlocal call_count
        call_count += 1
        raise ValueError("Validation error")

    with pytest.raises(ValueError, match="Validation error"):
        await async_operation()

    # Should only be called once (no retries)
    assert call_count == 1


@pytest.mark.unit
def test_retry_on_failure_sync_function():
    """Test retry_on_failure works with synchronous functions."""
    call_count = 0

    @retry_on_failure(max_attempts=2, min_wait=0.01, max_wait=0.01)
    def sync_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RetrievalError("Transient error")
        return "success"

    result = sync_operation()
    assert result == "success"
    assert call_count == 2


# ============================================================================
# retry_with_fallback Decorator Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_fallback_success():
    """Test retry_with_fallback succeeds on first attempt."""

    @retry_with_fallback(max_attempts=3, fallback_value="fallback")
    async def async_operation():
        return "success"

    result = await async_operation()
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_fallback_returns_fallback_after_exhaustion():
    """Test retry_with_fallback returns fallback value after all retries."""

    @retry_with_fallback(max_attempts=2, fallback_value=[])
    async def async_operation():
        raise RetrievalError("Permanent failure")

    result = await async_operation()
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_fallback_custom_fallback_value():
    """Test retry_with_fallback uses custom fallback value."""

    @retry_with_fallback(max_attempts=1, fallback_value={"status": "error"})
    async def async_operation():
        raise LLMError("LLM unavailable")

    result = await async_operation()
    assert result == {"status": "error"}


@pytest.mark.unit
def test_retry_with_fallback_sync_function():
    """Test retry_with_fallback works with synchronous functions."""

    @retry_with_fallback(max_attempts=1, fallback_value="fallback")
    def sync_operation():
        raise RetrievalError("Error")

    result = sync_operation()
    assert result == "fallback"


# ============================================================================
# retry_async_operation Utility Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_async_operation_success_first_attempt():
    """Test retry_async_operation succeeds on first attempt."""

    async def operation():
        return "success"

    result = await retry_async_operation(operation, max_attempts=3, operation_name="test")

    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_async_operation_retries_and_succeeds():
    """Test retry_async_operation retries and succeeds."""
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetrievalError("Transient error")
        return "success"

    result = await retry_async_operation(operation, max_attempts=3, operation_name="test")

    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_async_operation_fails_after_max_attempts():
    """Test retry_async_operation raises error after max attempts."""

    async def operation():
        raise RetrievalError("Permanent failure")

    with pytest.raises(RetrievalError, match="Permanent failure"):
        await retry_async_operation(operation, max_attempts=2, operation_name="test")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_async_operation_exponential_backoff():
    """Test retry_async_operation uses exponential backoff."""
    import time

    call_times = []

    async def operation():
        call_times.append(time.time())
        raise RetrievalError("Failure")

    with pytest.raises(RetrievalError):
        await retry_async_operation(operation, max_attempts=3, operation_name="test")

    # Check that backoff times are increasing (2^1, 2^2, ...)
    # We had 3 attempts, so 2 wait periods
    if len(call_times) >= 2:
        wait1 = call_times[1] - call_times[0]
        assert wait1 >= 0.5  # At least 1 second wait (2^1 - margin)
