"""Unit tests for LangGraph 1.0 Handoff Tools.

Sprint 94 Feature 94.1: Agent Messaging Bus (8 SP)

Tests cover:
- HandoffResult dataclass
- create_handoff_tool factory
- create_handoff_tools batch factory
- Tool-based handoff execution
- Async handoff helpers
- Error handling and timeouts
- LangGraph integration patterns
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.messaging.handoff import (
    HandoffResult,
    async_handoff,
    create_handoff_tool,
    create_handoff_tools,
)
from src.agents.messaging.message_bus import MessageBus


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_message_bus():
    """Mock MessageBus instance."""
    bus = MagicMock(spec=MessageBus)
    bus.request_and_wait = AsyncMock()
    return bus


# =============================================================================
# Test HandoffResult
# =============================================================================


def test_handoff_result_success():
    """Test HandoffResult for successful handoff."""
    result = HandoffResult(
        success=True,
        agent="vector_agent",
        result={"documents": ["doc1", "doc2"]},
        message_id="msg-123",
        duration_seconds=1.5,
    )

    assert result.success is True
    assert result.agent == "vector_agent"
    assert result.result == {"documents": ["doc1", "doc2"]}
    assert result.message_id == "msg-123"
    assert result.duration_seconds == 1.5
    assert result.error is None


def test_handoff_result_failure():
    """Test HandoffResult for failed handoff."""
    result = HandoffResult(
        success=False,
        agent="vector_agent",
        error="Timeout after 30s",
        duration_seconds=30.1,
    )

    assert result.success is False
    assert result.agent == "vector_agent"
    assert result.error == "Timeout after 30s"
    assert result.result is None


def test_handoff_result_str_success():
    """Test string representation for successful handoff."""
    result = HandoffResult(
        success=True,
        agent="vector_agent",
        duration_seconds=2.5,
    )

    str_repr = str(result)

    assert "vector_agent" in str_repr
    assert "succeeded" in str_repr
    assert "2.5" in str_repr or "2.50" in str_repr


def test_handoff_result_str_failure():
    """Test string representation for failed handoff."""
    result = HandoffResult(
        success=False,
        agent="vector_agent",
        error="Connection timeout",
    )

    str_repr = str(result)

    assert "vector_agent" in str_repr
    assert "failed" in str_repr
    assert "Connection timeout" in str_repr


# =============================================================================
# Test create_handoff_tool
# =============================================================================


def test_create_handoff_tool_basic(mock_message_bus):
    """Test creating basic handoff tool."""
    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    assert tool is not None
    assert hasattr(tool, "name")
    assert tool.name == "handoff_to_vector_agent"
    assert hasattr(tool, "invoke") or hasattr(tool, "run")


def test_create_handoff_tool_custom_name(mock_message_bus):
    """Test creating handoff tool with custom name."""
    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        tool_name="delegate_to_vector",
    )

    assert tool.name == "delegate_to_vector"


def test_create_handoff_tool_custom_description(mock_message_bus):
    """Test creating handoff tool with custom description."""
    custom_desc = "Delegate vector search tasks to the vector agent"

    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        tool_description=custom_desc,
    )

    assert tool.description == custom_desc


def test_handoff_tool_success(mock_message_bus):
    """Test successful handoff tool execution."""
    mock_message_bus.request_and_wait.return_value = {"results": ["doc1", "doc2"]}

    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    # Execute tool using invoke()
    result = tool.invoke({"input": {"query": "test query", "top_k": 5}})

    assert isinstance(result, HandoffResult)
    assert result.success is True
    assert result.agent == "vector_agent"
    assert result.result == {"results": ["doc1", "doc2"]}

    # Verify message_bus was called
    mock_message_bus.request_and_wait.assert_called_once()
    call_args = mock_message_bus.request_and_wait.call_args
    assert call_args[1]["sender"] == "coordinator"
    assert call_args[1]["recipient"] == "vector_agent"
    assert call_args[1]["payload"] == {"query": "test query", "top_k": 5}


def test_handoff_tool_timeout(mock_message_bus):
    """Test handoff tool with timeout."""
    mock_message_bus.request_and_wait.return_value = None  # Timeout returns None

    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        timeout_seconds=10.0,
    )

    result = tool.invoke({"input": {"query": "test query"}})

    assert isinstance(result, HandoffResult)
    assert result.success is False
    assert "Timeout" in result.error
    assert "10.0s" in result.error


def test_handoff_tool_exception(mock_message_bus):
    """Test handoff tool handling exception."""
    mock_message_bus.request_and_wait.side_effect = Exception("Connection error")

    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    result = tool.invoke({"input": {"query": "test query"}})

    assert isinstance(result, HandoffResult)
    assert result.success is False
    assert "Connection error" in result.error


# =============================================================================
# Test create_handoff_tools
# =============================================================================


def test_create_handoff_tools_single_agent(mock_message_bus):
    """Test creating handoff tools for single agent."""
    agent_targets = {
        "coordinator": ["vector_agent", "graph_agent"],
    }

    tools_by_agent = create_handoff_tools(agent_targets, mock_message_bus)

    assert "coordinator" in tools_by_agent
    assert len(tools_by_agent["coordinator"]) == 2

    # Check tool names
    tool_names = [t.name for t in tools_by_agent["coordinator"]]
    assert "handoff_to_vector_agent" in tool_names
    assert "handoff_to_graph_agent" in tool_names


def test_create_handoff_tools_multiple_agents(mock_message_bus):
    """Test creating handoff tools for multiple agents."""
    agent_targets = {
        "coordinator": ["vector_agent", "graph_agent"],
        "vector_agent": ["coordinator"],
        "graph_agent": ["coordinator"],
    }

    tools_by_agent = create_handoff_tools(agent_targets, mock_message_bus)

    assert len(tools_by_agent) == 3
    assert len(tools_by_agent["coordinator"]) == 2
    assert len(tools_by_agent["vector_agent"]) == 1
    assert len(tools_by_agent["graph_agent"]) == 1


def test_create_handoff_tools_custom_timeout(mock_message_bus):
    """Test creating handoff tools with custom timeout."""
    agent_targets = {
        "coordinator": ["vector_agent"],
    }

    tools_by_agent = create_handoff_tools(
        agent_targets,
        mock_message_bus,
        timeout_seconds=60.0,
    )

    assert "coordinator" in tools_by_agent
    # Timeout is stored internally, verify via execution
    mock_message_bus.request_and_wait.return_value = {"status": "ok"}

    tool = tools_by_agent["coordinator"][0]
    tool.invoke({"input": {"test": "data"}})

    # Check timeout was passed to request_and_wait
    call_args = mock_message_bus.request_and_wait.call_args
    assert call_args[1]["timeout_seconds"] == 60.0


# =============================================================================
# Test async_handoff
# =============================================================================


@pytest.mark.asyncio
async def test_async_handoff_success(mock_message_bus):
    """Test successful async handoff."""
    mock_message_bus.request_and_wait.return_value = {"results": ["doc1", "doc2"]}

    result = await async_handoff(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        payload={"query": "test"},
    )

    assert isinstance(result, HandoffResult)
    assert result.success is True
    assert result.agent == "vector_agent"
    assert result.result == {"results": ["doc1", "doc2"]}

    mock_message_bus.request_and_wait.assert_called_once()


@pytest.mark.asyncio
async def test_async_handoff_timeout(mock_message_bus):
    """Test async handoff with timeout."""
    mock_message_bus.request_and_wait.return_value = None

    result = await async_handoff(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        payload={"query": "test"},
        timeout_seconds=5.0,
    )

    assert isinstance(result, HandoffResult)
    assert result.success is False
    assert "Timeout" in result.error
    assert "5.0s" in result.error


@pytest.mark.asyncio
async def test_async_handoff_exception(mock_message_bus):
    """Test async handoff handling exception."""
    mock_message_bus.request_and_wait.side_effect = Exception("Network error")

    result = await async_handoff(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        payload={"query": "test"},
    )

    assert isinstance(result, HandoffResult)
    assert result.success is False
    assert "Network error" in result.error


# =============================================================================
# Test LangGraph Integration
# =============================================================================


def test_handoff_tool_is_langchain_tool(mock_message_bus):
    """Test that handoff tool is a proper LangChain tool."""
    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    # Check LangChain tool attributes
    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
    assert hasattr(tool, "invoke") or hasattr(tool, "run")


def test_handoff_tool_can_be_used_in_tool_list(mock_message_bus):
    """Test that handoff tools can be collected in a list (for LangGraph)."""
    tool1 = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    tool2 = create_handoff_tool(
        target_agent="graph_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    tools = [tool1, tool2]

    assert len(tools) == 2
    assert all(hasattr(t, "invoke") or hasattr(t, "run") for t in tools)
    assert all(hasattr(t, "name") for t in tools)


# =============================================================================
# Test Error Recovery
# =============================================================================


def test_handoff_tool_graceful_failure(mock_message_bus):
    """Test that handoff tool fails gracefully without raising exceptions."""
    mock_message_bus.request_and_wait.side_effect = RuntimeError("Critical error")

    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    # Should not raise, should return HandoffResult with error
    result = tool.invoke({"input": {"query": "test"}})

    assert isinstance(result, HandoffResult)
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_async_handoff_graceful_failure(mock_message_bus):
    """Test that async handoff fails gracefully."""
    mock_message_bus.request_and_wait.side_effect = RuntimeError("Critical error")

    # Should not raise, should return HandoffResult with error
    result = await async_handoff(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        payload={"query": "test"},
    )

    assert isinstance(result, HandoffResult)
    assert result.success is False
    assert result.error is not None


# =============================================================================
# Test Performance Metrics
# =============================================================================


def test_handoff_result_tracks_duration(mock_message_bus):
    """Test that HandoffResult tracks execution duration."""
    mock_message_bus.request_and_wait.return_value = {"results": []}

    tool = create_handoff_tool(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
    )

    result = tool.invoke({"input": {"query": "test"}})

    assert result.duration_seconds > 0
    assert result.duration_seconds < 1.0  # Should be very fast for mock


@pytest.mark.asyncio
async def test_async_handoff_tracks_duration(mock_message_bus):
    """Test that async handoff tracks duration."""
    mock_message_bus.request_and_wait.return_value = {"results": []}

    result = await async_handoff(
        target_agent="vector_agent",
        message_bus=mock_message_bus,
        sender_agent="coordinator",
        payload={"query": "test"},
    )

    assert result.duration_seconds > 0
    assert result.duration_seconds < 1.0
