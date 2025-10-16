"""Unit tests for error handling module.

Sprint 4 Feature 4.6: Error Handling & Retry Logic
Tests exception hierarchy, error handlers, and retry decorators.
"""

import pytest

from src.agents.error_handler import (
    AgentExecutionError,
    LLMError,
    RetrievalError,
    RouterError,
    StateError,
    TimeoutError,
    clear_errors,
    get_error_summary,
    handle_agent_error,
)
from src.agents.retry import retry_async_operation, retry_on_failure, retry_with_fallback

# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


def test_agent_execution_error_creation():
    """Test base AgentExecutionError creation."""
    error = AgentExecutionError(
        message="Test error",
        agent_name="TestAgent",
        context={"key": "value"},
    )

    assert error.message == "Test error"
    assert error.agent_name == "TestAgent"
    assert error.context == {"key": "value"}
    assert "Test error" in str(error)
    assert "TestAgent" in str(error)


def test_agent_execution_error_with_original():
    """Test AgentExecutionError with original exception."""
    original = ValueError("Original error")
    error = AgentExecutionError(
        message="Wrapped error",
        agent_name="TestAgent",
        original_error=original,
    )

    assert error.original_error == original
    assert "ValueError" in str(error)


def test_retrieval_error_inheritance():
    """Test RetrievalError inherits from AgentExecutionError."""
    error = RetrievalError("Vector search failed", agent_name="VectorAgent")

    assert isinstance(error, AgentExecutionError)
    assert error.message == "Vector search failed"
    assert error.agent_name == "VectorAgent"


def test_llm_error_inheritance():
    """Test LLMError inherits from AgentExecutionError."""
    error = LLMError("LLM timeout", agent_name="RouterAgent")

    assert isinstance(error, AgentExecutionError)
    assert error.message == "LLM timeout"


def test_state_error_inheritance():
    """Test StateError inherits from AgentExecutionError."""
    error = StateError("Invalid state", agent_name="CoordinatorAgent")

    assert isinstance(error, AgentExecutionError)
    assert error.message == "Invalid state"


def test_router_error_inheritance():
    """Test RouterError inherits from AgentExecutionError."""
    error = RouterError("Routing failed", agent_name="RouterAgent")

    assert isinstance(error, AgentExecutionError)
    assert error.message == "Routing failed"


def test_timeout_error_inheritance():
    """Test TimeoutError inherits from AgentExecutionError."""
    error = TimeoutError("Operation timed out", agent_name="TestAgent")

    assert isinstance(error, AgentExecutionError)
    assert error.message == "Operation timed out"


# ============================================================================
# Error Handler Tests
# ============================================================================


def test_handle_agent_error_basic():
    """Test basic error handling."""
    state = {"query": "test"}
    error = ValueError("Test error")

    result = handle_agent_error(error, state, "TestAgent", "test context")

    assert "metadata" in result
    assert "error" in result["metadata"]
    assert result["metadata"]["error"]["agent"] == "TestAgent"
    assert result["metadata"]["error"]["error_type"] == "ValueError"
    assert result["metadata"]["error"]["message"] == "Test error"
    assert result["metadata"]["error"]["context"] == "test context"


def test_handle_agent_error_creates_metadata():
    """Test error handler creates metadata if missing."""
    state = {}
    error = ValueError("Test error")

    result = handle_agent_error(error, state, "TestAgent")

    assert "metadata" in result
    assert "error" in result["metadata"]
    assert "errors" in result["metadata"]
    assert "agent_path" in result["metadata"]


def test_handle_agent_error_appends_to_agent_path():
    """Test error handler appends to agent path."""
    state = {
        "metadata": {
            "agent_path": ["router: started"],
        }
    }
    error = ValueError("Test error")

    result = handle_agent_error(error, state, "TestAgent")

    assert "TestAgent: error - ValueError" in result["metadata"]["agent_path"]
    assert len(result["metadata"]["agent_path"]) == 2


def test_handle_agent_error_multiple_errors():
    """Test handling multiple errors."""
    state = {}
    error1 = ValueError("First error")
    error2 = RuntimeError("Second error")

    state = handle_agent_error(error1, state, "Agent1")
    state = handle_agent_error(error2, state, "Agent2")

    assert len(state["metadata"]["errors"]) == 2
    assert state["metadata"]["errors"][0]["error_type"] == "ValueError"
    assert state["metadata"]["errors"][1]["error_type"] == "RuntimeError"


def test_handle_agent_error_retryable():
    """Test retryable error detection."""
    state = {}

    # Retryable errors
    retrieval_error = RetrievalError("Search failed", agent_name="VectorAgent")
    result = handle_agent_error(retrieval_error, state, "VectorAgent")
    assert result["metadata"]["error"]["retryable"] is True

    # Non-retryable errors
    state_error = StateError("Invalid state", agent_name="CoordinatorAgent")
    result = handle_agent_error(state_error, state, "CoordinatorAgent")
    assert result["metadata"]["error"]["retryable"] is False


def test_get_error_summary():
    """Test getting error summary from state."""
    state = {}
    error = ValueError("Test error")
    state = handle_agent_error(error, state, "TestAgent", "test context")

    summary = get_error_summary(state)

    assert summary is not None
    assert summary["has_error"] is True
    assert summary["agent"] == "TestAgent"
    assert summary["error_type"] == "ValueError"
    assert summary["message"] == "Test error"
    assert summary["total_errors"] == 1


def test_get_error_summary_no_error():
    """Test getting error summary when no errors."""
    state = {}

    summary = get_error_summary(state)

    assert summary is None


def test_clear_errors():
    """Test clearing errors from state."""
    state = {}
    error = ValueError("Test error")
    state = handle_agent_error(error, state, "TestAgent")

    assert "error" in state["metadata"]
    assert "errors" in state["metadata"]

    state = clear_errors(state)

    assert "error" not in state["metadata"]
    assert "errors" not in state["metadata"]


# ============================================================================
# Retry Decorator Tests
# ============================================================================


@pytest.mark.asyncio
async def test_retry_on_failure_success_first_attempt():
    """Test retry decorator succeeds on first attempt."""
    call_count = 0

    @retry_on_failure(max_attempts=3)
    async def test_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await test_func()

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_on_failure_success_after_retry():
    """Test retry decorator succeeds after retries."""
    call_count = 0

    @retry_on_failure(max_attempts=3, min_wait=0.1, max_wait=0.2)
    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RetrievalError("Temporary failure", agent_name="TestAgent")
        return "success"

    result = await test_func()

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_failure_exhausted():
    """Test retry decorator exhausts retries."""
    call_count = 0

    @retry_on_failure(max_attempts=3, min_wait=0.1, max_wait=0.2)
    async def test_func():
        nonlocal call_count
        call_count += 1
        raise LLMError("Persistent failure", agent_name="TestAgent")

    with pytest.raises(LLMError):
        await test_func()

    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_failure_non_retryable():
    """Test retry decorator doesn't retry non-retryable errors."""
    call_count = 0

    @retry_on_failure(max_attempts=3)
    async def test_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("Non-retryable error")

    with pytest.raises(ValueError):
        await test_func()

    # Should only be called once (no retries for ValueError)
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_with_fallback_success():
    """Test retry with fallback succeeds."""

    @retry_with_fallback(max_attempts=2, fallback_value={"default": True})
    async def test_func():
        return {"result": "success"}

    result = await test_func()

    assert result == {"result": "success"}


@pytest.mark.asyncio
async def test_retry_with_fallback_uses_fallback():
    """Test retry with fallback returns fallback value."""

    @retry_with_fallback(max_attempts=2, fallback_value=[])
    async def test_func():
        raise RetrievalError("Failure", agent_name="TestAgent")

    result = await test_func()

    assert result == []


@pytest.mark.asyncio
async def test_retry_async_operation_success():
    """Test retry_async_operation succeeds."""
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_async_operation(operation, max_attempts=3)

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_operation_retries():
    """Test retry_async_operation retries on failure."""
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Temporary failure")
        return "success"

    result = await retry_async_operation(operation, max_attempts=3)

    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_async_operation_exhausted():
    """Test retry_async_operation exhausts retries."""
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("Persistent failure")

    with pytest.raises(RuntimeError):
        await retry_async_operation(operation, max_attempts=3)

    assert call_count == 3


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_error_handling_with_retry_integration():
    """Test error handling integrated with retry logic."""
    state = {}
    call_count = 0

    @retry_on_failure(max_attempts=3, min_wait=0.1, max_wait=0.2)
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RetrievalError("Temporary failure", agent_name="TestAgent")
        return {"result": "success"}

    try:
        result = await failing_operation()
        assert result == {"result": "success"}
        assert call_count == 2
    except Exception as e:
        state = handle_agent_error(e, state, "TestAgent", "operation")
        assert "error" in state["metadata"]
