"""Unit tests for MCP Tool Executor.

Tests cover:
- Tool execution with success and failure scenarios
- Retry logic with transient failures
- Timeout handling
- Error classification
- Result parsing

Sprint 9 Feature 9.7: Tool Execution Handler
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.mcp.client import MCPClient
from src.components.mcp.models import MCPTool, MCPToolCall, MCPToolResult
from src.components.mcp.tool_executor import ToolExecutor


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock(spec=MCPClient)
    client.list_tools = MagicMock(return_value=[])
    client.get_tool = MagicMock(return_value=None)
    client.execute_tool = AsyncMock()
    return client


@pytest.fixture
def sample_tool():
    """Create a sample MCP tool."""
    return MCPTool(
        name="test_tool",
        description="A test tool",
        parameters={
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
        },
        server="test_server",
    )


@pytest.fixture
def tool_executor(mock_mcp_client):
    """Create a tool executor instance."""
    return ToolExecutor(mock_mcp_client, timeout=30)


class TestToolExecutorInit:
    """Test ToolExecutor initialization."""

    def test_init_with_defaults(self, mock_mcp_client):
        """Test initialization with default timeout."""
        executor = ToolExecutor(mock_mcp_client)
        assert executor.client == mock_mcp_client
        assert executor.timeout == 30

    def test_init_with_custom_timeout(self, mock_mcp_client):
        """Test initialization with custom timeout."""
        executor = ToolExecutor(mock_mcp_client, timeout=60)
        assert executor.timeout == 60


class TestToolExecution:
    """Test tool execution scenarios."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, tool_executor, mock_mcp_client, sample_tool):
        """Test successful tool execution."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result={"output": "test result"},
            execution_time=0.5,
        )

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={"input": "test"},
        )

        # Verify
        assert result.success
        assert result.result == {"output": "test result"}
        assert result.tool_name == "test_tool"
        mock_mcp_client.execute_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, tool_executor, mock_mcp_client):
        """Test execution when tool is not found."""
        # Setup
        mock_mcp_client.get_tool.return_value = None

        # Execute
        result = await tool_executor.execute(
            tool_name="nonexistent_tool",
            parameters={},
        )

        # Verify
        assert not result.success
        assert "not found" in result.error.lower()
        assert result.tool_name == "nonexistent_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self, tool_executor, mock_mcp_client, sample_tool):
        """Test execution when tool returns error."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=False,
            error="Tool execution failed",
            execution_time=0.1,
        )

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={"input": "test"},
        )

        # Verify
        assert not result.success
        assert "Tool execution failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_server_name(self, tool_executor, mock_mcp_client, sample_tool):
        """Test execution with specific server name."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result={"data": "test"},
            execution_time=0.3,
        )

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={},
            server_name="test_server",
        )

        # Verify
        assert result.success
        mock_mcp_client.get_tool.assert_called_with("test_tool", "test_server")


class TestRetryLogic:
    """Test retry logic for transient failures."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, tool_executor, mock_mcp_client, sample_tool):
        """Test retry on timeout error."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool

        # First two calls fail with timeout, third succeeds
        mock_mcp_client.execute_tool.side_effect = [
            MCPToolResult(
                tool_name="test_tool",
                success=False,
                error="Timeout after 30s",
                execution_time=30.0,
            ),
            MCPToolResult(
                tool_name="test_tool",
                success=False,
                error="Timeout after 30s",
                execution_time=30.0,
            ),
            MCPToolResult(
                tool_name="test_tool",
                success=True,
                result={"data": "success"},
                execution_time=5.0,
            ),
        ]

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={"input": "test"},
        )

        # Verify - should succeed after retries
        assert result.success
        assert mock_mcp_client.execute_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(self, tool_executor, mock_mcp_client, sample_tool):
        """Test no retry on permanent errors."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=False,
            error="Invalid parameters",
            execution_time=0.1,
        )

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={"input": "test"},
        )

        # Verify - should not retry
        assert not result.success
        assert mock_mcp_client.execute_tool.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, tool_executor, mock_mcp_client, sample_tool):
        """Test that retries stop after max attempts."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=False,
            error="Connection timeout",
            execution_time=5.0,
        )

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={"input": "test"},
        )

        # Verify - should try 3 times then give up
        assert not result.success
        assert mock_mcp_client.execute_tool.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(
        self, tool_executor, mock_mcp_client, sample_tool
    ):
        """Test that retry uses exponential backoff."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.side_effect = [
            MCPToolResult(
                tool_name="test_tool",
                success=False,
                error="Network error",
                execution_time=1.0,
            ),
            MCPToolResult(
                tool_name="test_tool",
                success=True,
                result={"data": "success"},
                execution_time=1.0,
            ),
        ]

        # Execute and time it
        import time

        start = time.time()
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={"input": "test"},
        )
        duration = time.time() - start

        # Verify - should have waited at least 1 second (2^0) before retry
        assert result.success
        assert duration >= 1.0  # First backoff is 1 second


class TestResultParsing:
    """Test result parsing for different formats."""

    @pytest.mark.asyncio
    async def test_parse_json_result(self, tool_executor, mock_mcp_client, sample_tool):
        """Test parsing JSON result."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result={"key": "value", "number": 42},
            execution_time=0.5,
        )

        # Execute with JSON format
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={},
            expected_format="json",
        )

        # Verify
        assert result.success
        assert isinstance(result.result, dict)
        assert result.result["key"] == "value"

    @pytest.mark.asyncio
    async def test_parse_text_result(self, tool_executor, mock_mcp_client, sample_tool):
        """Test parsing text result."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result="This is a text result",
            execution_time=0.5,
        )

        # Execute with text format
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={},
            expected_format="text",
        )

        # Verify
        assert result.success
        assert "content" in result.result
        assert result.result["content"] == "This is a text result"

    @pytest.mark.asyncio
    async def test_parse_auto_format(self, tool_executor, mock_mcp_client, sample_tool):
        """Test auto-detection of result format."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result={"auto": "detected"},
            execution_time=0.5,
        )

        # Execute with auto format
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={},
            expected_format="auto",
        )

        # Verify
        assert result.success
        assert result.result == {"auto": "detected"}


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handle_exception_during_execution(
        self, tool_executor, mock_mcp_client, sample_tool
    ):
        """Test handling of unexpected exceptions."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.side_effect = Exception("Unexpected error")

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={},
        )

        # Verify
        assert not result.success
        assert "error" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handle_empty_result(self, tool_executor, mock_mcp_client, sample_tool):
        """Test handling of empty/None result."""
        # Setup
        mock_mcp_client.get_tool.return_value = sample_tool
        mock_mcp_client.execute_tool.return_value = MCPToolResult(
            tool_name="test_tool",
            success=True,
            result=None,
            execution_time=0.5,
        )

        # Execute
        result = await tool_executor.execute(
            tool_name="test_tool",
            parameters={},
        )

        # Verify
        assert result.success
        # Result should remain None if parsing is skipped


class TestRetryClassification:
    """Test retry classification logic."""

    def test_should_retry_timeout(self, tool_executor):
        """Test that timeout errors are retryable."""
        result = MCPToolResult(
            tool_name="test",
            success=False,
            error="Timeout after 30s",
        )
        assert tool_executor._should_retry_result(result)

    def test_should_retry_connection_error(self, tool_executor):
        """Test that connection errors are retryable."""
        result = MCPToolResult(
            tool_name="test",
            success=False,
            error="Connection refused",
        )
        assert tool_executor._should_retry_result(result)

    def test_should_not_retry_invalid_params(self, tool_executor):
        """Test that invalid parameter errors are not retryable."""
        result = MCPToolResult(
            tool_name="test",
            success=False,
            error="Invalid parameters",
        )
        assert not tool_executor._should_retry_result(result)

    def test_should_not_retry_success(self, tool_executor):
        """Test that successful results are not retried."""
        result = MCPToolResult(
            tool_name="test",
            success=True,
            result={"data": "ok"},
        )
        assert not tool_executor._should_retry_result(result)
