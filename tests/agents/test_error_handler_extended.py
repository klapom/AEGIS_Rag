"""Extended Unit Tests for Error Handler - Coverage Improvement.

Tests exception hierarchy and error handling utilities.

Author: Claude Code
Date: 2025-10-27
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

# ============================================================================
# Exception Hierarchy Tests
# ============================================================================


@pytest.mark.unit
def test_agent_execution_error_creation():
    """Test AgentExecutionError creation with all parameters."""
    original = ValueError("original error")
    error = AgentExecutionError(
        message="Test error",
        agent_name="TestAgent",
        context={"key": "value"},
        original_error=original,
    )

    assert error.message == "Test error"
    assert error.agent_name == "TestAgent"
    assert error.context == {"key": "value"}
    assert error.original_error == original


@pytest.mark.unit
def test_agent_execution_error_defaults():
    """Test AgentExecutionError uses defaults for optional parameters."""
    error = AgentExecutionError(message="Test error")

    assert error.message == "Test error"
    assert error.agent_name is None
    assert error.context == {}
    assert error.original_error is None


@pytest.mark.unit
def test_agent_execution_error_str_representation():
    """Test AgentExecutionError string representation."""
    original = ValueError("original")
    error = AgentExecutionError(
        message="Test error",
        agent_name="TestAgent",
        context={"key": "value"},
        original_error=original,
    )

    error_str = str(error)
    assert "Test error" in error_str
    assert "[agent=TestAgent]" in error_str
    assert "[caused by: ValueError]" in error_str


@pytest.mark.unit
def test_retrieval_error_inheritance():
    """Test RetrievalError inherits from AgentExecutionError."""
    error = RetrievalError(message="Database connection failed", agent_name="VectorAgent")

    assert isinstance(error, AgentExecutionError)
    assert isinstance(error, RetrievalError)
    assert error.message == "Database connection failed"


@pytest.mark.unit
def test_llm_error_inheritance():
    """Test LLMError inherits from AgentExecutionError."""
    error = LLMError(message="Ollama unavailable", agent_name="GenerateAgent")

    assert isinstance(error, AgentExecutionError)
    assert isinstance(error, LLMError)
    assert error.message == "Ollama unavailable"


@pytest.mark.unit
def test_state_error_inheritance():
    """Test StateError inherits from AgentExecutionError."""
    error = StateError(message="Missing required field", agent_name="CoordinatorAgent")

    assert isinstance(error, AgentExecutionError)
    assert isinstance(error, StateError)
    assert error.message == "Missing required field"


@pytest.mark.unit
def test_router_error_inheritance():
    """Test RouterError inherits from AgentExecutionError."""
    error = RouterError(message="Intent classification failed", agent_name="RouterAgent")

    assert isinstance(error, AgentExecutionError)
    assert isinstance(error, RouterError)
    assert error.message == "Intent classification failed"


@pytest.mark.unit
def test_timeout_error_inheritance():
    """Test TimeoutError inherits from AgentExecutionError."""
    error = TimeoutError(message="Operation timed out", agent_name="SearchAgent")

    assert isinstance(error, AgentExecutionError)
    assert isinstance(error, TimeoutError)
    assert error.message == "Operation timed out"


# ============================================================================
# handle_agent_error Function Tests
# ============================================================================


@pytest.mark.unit
def test_handle_agent_error_adds_metadata():
    """Test handle_agent_error adds error metadata to state."""
    state = {"query": "test query"}
    error = RetrievalError(message="Database error", agent_name="VectorAgent")

    updated_state = handle_agent_error(error, state, "VectorAgent", "search_operation")

    assert "metadata" in updated_state
    assert "error" in updated_state["metadata"]
    assert "errors" in updated_state["metadata"]
    assert updated_state["metadata"]["error"]["agent"] == "VectorAgent"
    assert updated_state["metadata"]["error"]["error_type"] == "RetrievalError"
    # Check that error message contains the original message (may include agent name in str representation)
    assert "Database error" in updated_state["metadata"]["error"]["message"]
    assert updated_state["metadata"]["error"]["context"] == "search_operation"


@pytest.mark.unit
def test_handle_agent_error_existing_metadata():
    """Test handle_agent_error preserves existing metadata."""
    state = {"query": "test", "metadata": {"existing": "data"}}
    error = LLMError(message="LLM error")

    updated_state = handle_agent_error(error, state, "GenerateAgent")

    assert updated_state["metadata"]["existing"] == "data"
    assert "error" in updated_state["metadata"]


@pytest.mark.unit
def test_handle_agent_error_multiple_errors():
    """Test handle_agent_error accumulates multiple errors."""
    state = {"query": "test"}

    # First error
    error1 = RetrievalError(message="Error 1")
    state = handle_agent_error(error1, state, "Agent1")

    # Second error
    error2 = LLMError(message="Error 2")
    state = handle_agent_error(error2, state, "Agent2")

    assert len(state["metadata"]["errors"]) == 2
    assert state["metadata"]["errors"][0]["error_type"] == "RetrievalError"
    assert state["metadata"]["errors"][1]["error_type"] == "LLMError"


@pytest.mark.unit
def test_handle_agent_error_retryable_classification():
    """Test handle_agent_error correctly classifies retryable errors."""
    state = {"query": "test"}

    # Retryable error
    error1 = RetrievalError(message="Connection error")
    state1 = handle_agent_error(error1, state.copy(), "Agent1")
    assert state1["metadata"]["error"]["retryable"] is True

    # Non-retryable error
    error2 = ValueError("Invalid input")
    state2 = handle_agent_error(error2, state.copy(), "Agent2")
    assert state2["metadata"]["error"]["retryable"] is False


@pytest.mark.unit
def test_handle_agent_error_updates_agent_path():
    """Test handle_agent_error adds to agent_path."""
    state = {"query": "test"}
    error = RetrievalError(message="Error")

    updated_state = handle_agent_error(error, state, "VectorAgent")

    assert "agent_path" in updated_state["metadata"]
    assert len(updated_state["metadata"]["agent_path"]) == 1
    assert "VectorAgent: error - RetrievalError" in updated_state["metadata"]["agent_path"]


# ============================================================================
# get_error_summary Function Tests
# ============================================================================


@pytest.mark.unit
def test_get_error_summary_with_error():
    """Test get_error_summary returns summary when error exists."""
    state = {
        "metadata": {
            "error": {
                "agent": "TestAgent",
                "error_type": "RetrievalError",
                "message": "Test error",
                "retryable": True,
            },
            "errors": [
                {"agent": "TestAgent", "error_type": "RetrievalError"},
            ],
        }
    }

    summary = get_error_summary(state)

    assert summary is not None
    assert summary["has_error"] is True
    assert summary["agent"] == "TestAgent"
    assert summary["error_type"] == "RetrievalError"
    assert summary["message"] == "Test error"
    assert summary["retryable"] is True
    assert summary["total_errors"] == 1


@pytest.mark.unit
def test_get_error_summary_no_error():
    """Test get_error_summary returns None when no error."""
    state = {"query": "test"}

    summary = get_error_summary(state)

    assert summary is None


@pytest.mark.unit
def test_get_error_summary_no_metadata():
    """Test get_error_summary returns None when no metadata."""
    state = {}

    summary = get_error_summary(state)

    assert summary is None


# ============================================================================
# clear_errors Function Tests
# ============================================================================


@pytest.mark.unit
def test_clear_errors_removes_error_data():
    """Test clear_errors removes error and errors from state."""
    state = {
        "query": "test",
        "metadata": {
            "error": {"agent": "TestAgent"},
            "errors": [{"agent": "TestAgent"}],
            "other": "data",
        },
    }

    cleared_state = clear_errors(state)

    assert "error" not in cleared_state["metadata"]
    assert "errors" not in cleared_state["metadata"]
    assert cleared_state["metadata"]["other"] == "data"


@pytest.mark.unit
def test_clear_errors_no_metadata():
    """Test clear_errors handles state without metadata."""
    state = {"query": "test"}

    cleared_state = clear_errors(state)

    assert cleared_state == state


@pytest.mark.unit
def test_clear_errors_no_error_fields():
    """Test clear_errors handles metadata without error fields."""
    state = {"query": "test", "metadata": {"other": "data"}}

    cleared_state = clear_errors(state)

    assert cleared_state["metadata"]["other"] == "data"


# ============================================================================
# _is_retryable_error Function Tests (via handle_agent_error)
# ============================================================================


@pytest.mark.unit
def test_retryable_error_types():
    """Test retryable error types are correctly identified."""
    state = {"query": "test"}

    retryable_errors = [
        RetrievalError("Retrieval failed"),
        LLMError("LLM unavailable"),
        RouterError("Routing failed"),
        TimeoutError("Operation timed out"),
    ]

    for error in retryable_errors:
        test_state = handle_agent_error(error, state.copy(), "TestAgent")
        assert (
            test_state["metadata"]["error"]["retryable"] is True
        ), f"{type(error).__name__} should be retryable"


@pytest.mark.unit
def test_non_retryable_error_types():
    """Test non-retryable error types are correctly identified."""
    state = {"query": "test"}

    non_retryable_errors = [
        StateError("State validation failed"),
        ValueError("Invalid value"),
        TypeError("Type mismatch"),
        KeyError("Missing key"),
    ]

    for error in non_retryable_errors:
        test_state = handle_agent_error(error, state.copy(), "TestAgent")
        assert (
            test_state["metadata"]["error"]["retryable"] is False
        ), f"{type(error).__name__} should not be retryable"


@pytest.mark.unit
def test_retryable_error_by_message_pattern():
    """Test errors are identified as retryable by message patterns."""
    state = {"query": "test"}

    retryable_messages = [
        "connection refused",
        "timeout occurred",
        "service unavailable",
        "temporarily refused",
        "rate limit exceeded",
    ]

    for message in retryable_messages:
        error = Exception(message)
        test_state = handle_agent_error(error, state.copy(), "TestAgent")
        assert (
            test_state["metadata"]["error"]["retryable"] is True
        ), f"Error with message '{message}' should be retryable"
