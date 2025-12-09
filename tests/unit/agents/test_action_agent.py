"""Unit tests for Action Agent.

Tests cover:
- Action execution workflow
- Tool selection logic
- LangGraph state management
- Error handling and recovery
- Integration with ToolExecutor

Sprint 9 Feature 9.8: Action Agent (LangGraph Integration)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.action_agent import ActionAgent
from src.components.mcp.client import MCPClient
from src.components.mcp.models import MCPTool, MCPToolResult
from src.components.mcp.tool_executor import ToolExecutor


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock(spec=MCPClient)
    client.list_tools = MagicMock(return_value=[])
    client.get_tool = MagicMock(return_value=None)
    return client


@pytest.fixture
def mock_tool_executor():
    """Create a mock tool executor."""
    executor = MagicMock(spec=ToolExecutor)
    executor.execute = AsyncMock()
    return executor


@pytest.fixture
def sample_tools():
    """Create sample MCP tools."""
    return [
        MCPTool(
            name="read_file",
            description="Read a file from disk",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            server="filesystem",
        ),
        MCPTool(
            name="write_file",
            description="Write a file to disk",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            server="filesystem",
        ),
        MCPTool(
            name="create_issue",
            description="Create a GitHub issue",
            parameters={
                "type": "object",
                "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            },
            server="github",
        ),
    ]


@pytest.fixture
def action_agent(mock_mcp_client, mock_tool_executor):
    """Create an action agent instance."""
    return ActionAgent(mock_mcp_client, mock_tool_executor)


class TestActionAgentInit:
    """Test ActionAgent initialization."""

    def test_init(self, mock_mcp_client, mock_tool_executor):
        """Test action agent initialization."""
        agent = ActionAgent(mock_mcp_client, mock_tool_executor)
        assert agent.client == mock_mcp_client
        assert agent.executor == mock_tool_executor
        assert agent.tool_selector is not None
        assert agent.graph is not None


class TestActionExecution:
    """Test action execution workflows."""

    @pytest.mark.asyncio
    async def test_execute_action_success(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test successful action execution."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[0]  # read_file
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="read_file",
            success=True,
            result={"content": "file content"},
            execution_time=0.5,
        )

        # Execute
        result = await action_agent.execute(
            action="read the README file",
            parameters={"path": "README.md"},
        )

        # Verify
        assert result["success"]
        assert result["result"] == {"content": "file content"}
        assert result["tool"] == "read_file"
        assert len(result["trace"]) > 0
        assert result["error"] is None or result["error"] == ""

    @pytest.mark.asyncio
    async def test_execute_action_tool_not_found(
        self, action_agent, mock_mcp_client, mock_tool_executor
    ):
        """Test action when no suitable tool is found."""
        # Setup - no tools available
        mock_mcp_client.list_tools.return_value = []

        # Execute
        result = await action_agent.execute(
            action="do something impossible",
            parameters={},
        )

        # Verify
        assert not result["success"]
        assert "no tool" in result["error"].lower() or "not found" in result["error"].lower()
        mock_tool_executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_action_tool_failure(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test action when tool execution fails."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[0]
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="read_file",
            success=False,
            error="File not found",
            execution_time=0.1,
        )

        # Execute
        result = await action_agent.execute(
            action="read missing file",
            parameters={"path": "missing.txt"},
        )

        # Verify
        assert not result["success"]
        assert "file not found" in result["error"].lower()
        assert result["tool"] == "read_file"

    @pytest.mark.asyncio
    async def test_execute_with_no_parameters(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test execution without parameters."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[0]
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="read_file",
            success=True,
            result={"data": "ok"},
            execution_time=0.3,
        )

        # Execute without parameters
        result = await action_agent.execute(action="read file")

        # Verify
        assert result["success"]
        # Parameters should default to empty dict
        call_args = mock_tool_executor.execute.call_args
        assert call_args[1]["parameters"] == {}


class TestToolSelection:
    """Test tool selection logic."""

    @pytest.mark.asyncio
    async def test_select_file_read_tool(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test selection of file read tool."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[0]  # read_file
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="read_file",
            success=True,
            result={},
            execution_time=0.1,
        )

        # Execute with file read action
        result = await action_agent.execute(
            action="read the configuration file",
            parameters={},
        )

        # Verify correct tool was selected
        assert result["tool"] == "read_file"

    @pytest.mark.asyncio
    async def test_select_file_write_tool(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test selection of file write tool."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[1]  # write_file
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="write_file",
            success=True,
            result={},
            execution_time=0.2,
        )

        # Execute with file write action
        result = await action_agent.execute(
            action="write content to output file",
            parameters={},
        )

        # Verify
        assert result["success"]

    @pytest.mark.asyncio
    async def test_select_github_tool(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test selection of GitHub tool."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[2]  # create_issue
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="create_issue",
            success=True,
            result={"issue_number": 42},
            execution_time=1.0,
        )

        # Execute with GitHub action
        result = await action_agent.execute(
            action="create a GitHub issue for the bug",
            parameters={},
        )

        # Verify
        assert result["success"]


class TestStateManagement:
    """Test LangGraph state management."""

    @pytest.mark.asyncio
    async def test_state_trace_messages(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test that state trace messages are collected."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[0]
        mock_tool_executor.execute.return_value = MCPToolResult(
            tool_name="read_file",
            success=True,
            result={},
            execution_time=0.5,
        )

        # Execute
        result = await action_agent.execute(
            action="read file",
            parameters={},
        )

        # Verify trace messages exist
        assert len(result["trace"]) > 0
        assert any("selected tool" in msg.lower() for msg in result["trace"])
        assert any("success" in msg.lower() for msg in result["trace"])

    @pytest.mark.asyncio
    async def test_state_error_propagation(self, action_agent, mock_mcp_client, mock_tool_executor):
        """Test that errors propagate through state correctly."""
        # Setup - no tools available
        mock_mcp_client.list_tools.return_value = []

        # Execute
        result = await action_agent.execute(
            action="impossible action",
            parameters={},
        )

        # Verify error is in result
        assert not result["success"]
        assert result["error"]
        assert any("error" in msg.lower() for msg in result["trace"])


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handle_executor_exception(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test handling of executor exceptions."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools
        mock_mcp_client.get_tool.return_value = sample_tools[0]
        mock_tool_executor.execute.side_effect = Exception("Unexpected executor error")

        # Execute
        result = await action_agent.execute(
            action="read file",
            parameters={},
        )

        # Verify
        assert not result["success"]
        assert "error" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_graph_exception(
        self, action_agent, mock_mcp_client, mock_tool_executor, sample_tools
    ):
        """Test handling of graph execution exceptions."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools

        # Mock graph to raise exception
        with patch.object(action_agent.graph, "ainvoke", side_effect=Exception("Graph error")):
            # Execute
            result = await action_agent.execute(
                action="test action",
                parameters={},
            )

            # Verify
            assert not result["success"]
            assert "error" in result["error"].lower()


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_available_tools(self, action_agent, mock_mcp_client, sample_tools):
        """Test getting available tools list."""
        # Setup
        mock_mcp_client.list_tools.return_value = sample_tools

        # Execute
        tools = action_agent.get_available_tools()

        # Verify
        assert len(tools) == 3
        assert "read_file" in tools
        assert "write_file" in tools
        assert "create_issue" in tools

    def test_get_tool_info_exists(self, action_agent, mock_mcp_client, sample_tools):
        """Test getting tool info for existing tool."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tools[0]

        # Execute
        info = action_agent.get_tool_info("read_file")

        # Verify
        assert info is not None
        assert info["name"] == "read_file"
        assert info["server"] == "filesystem"
        assert "parameters" in info

    def test_get_tool_info_not_found(self, action_agent, mock_mcp_client):
        """Test getting tool info for non-existent tool."""
        # Setup
        mock_mcp_client.get_tool.return_value = None

        # Execute
        info = action_agent.get_tool_info("nonexistent_tool")

        # Verify
        assert info is None

    def test_get_available_tools_empty(self, action_agent, mock_mcp_client):
        """Test getting available tools when none exist."""
        # Setup
        mock_mcp_client.list_tools.return_value = []

        # Execute
        tools = action_agent.get_available_tools()

        # Verify
        assert tools == []
