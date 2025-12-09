"""Extended Unit Tests for MCP Models - Coverage Improvement.

Tests MCP data models for validation, serialization, and edge cases.

Author: Claude Code
Date: 2025-10-27
"""

import pytest

from src.components.mcp.models import (
    MCPClientStats,
    MCPServer,
    MCPServerConnection,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    ServerStatus,
    TransportType,
)

# ============================================================================
# MCPServer Tests
# ============================================================================


@pytest.mark.unit
def test_mcp_server_creation_valid():
    """Test MCPServer creation with valid data."""
    server = MCPServer(
        name="test-server",
        transport=TransportType.STDIO,
        endpoint="/usr/local/bin/mcp-server",
        description="Test server",
        timeout=60,
        retry_attempts=5,
    )

    assert server.name == "test-server"
    assert server.transport == TransportType.STDIO
    assert server.endpoint == "/usr/local/bin/mcp-server"
    assert server.timeout == 60
    assert server.retry_attempts == 5


@pytest.mark.unit
def test_mcp_server_defaults():
    """Test MCPServer uses correct defaults."""
    server = MCPServer(name="test", transport=TransportType.HTTP, endpoint="http://localhost:3000")

    assert server.description == ""
    assert server.timeout == 30
    assert server.retry_attempts == 3
    assert server.metadata == {}


@pytest.mark.unit
def test_mcp_server_validates_empty_name():
    """Test MCPServer raises ValueError for empty name."""
    with pytest.raises(ValueError, match="name cannot be empty"):
        MCPServer(name="", transport=TransportType.STDIO, endpoint="/bin/test")


@pytest.mark.unit
def test_mcp_server_validates_empty_endpoint():
    """Test MCPServer raises ValueError for empty endpoint."""
    with pytest.raises(ValueError, match="endpoint cannot be empty"):
        MCPServer(name="test", transport=TransportType.STDIO, endpoint="")


@pytest.mark.unit
def test_mcp_server_validates_negative_timeout():
    """Test MCPServer raises ValueError for negative timeout."""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        MCPServer(name="test", transport=TransportType.STDIO, endpoint="/bin/test", timeout=-1)


@pytest.mark.unit
def test_mcp_server_validates_negative_retry():
    """Test MCPServer raises ValueError for negative retry attempts."""
    with pytest.raises(ValueError, match="Retry attempts cannot be negative"):
        MCPServer(
            name="test", transport=TransportType.STDIO, endpoint="/bin/test", retry_attempts=-1
        )


@pytest.mark.unit
def test_mcp_server_with_metadata():
    """Test MCPServer stores custom metadata."""
    server = MCPServer(
        name="test",
        transport=TransportType.HTTP,
        endpoint="http://localhost",
        metadata={"version": "1.0", "author": "test"},
    )

    assert server.metadata["version"] == "1.0"
    assert server.metadata["author"] == "test"


# ============================================================================
# MCPTool Tests
# ============================================================================


@pytest.mark.unit
def test_mcp_tool_creation_valid():
    """Test MCPTool creation with valid data."""
    tool = MCPTool(
        name="read_file",
        description="Read file contents",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        server="filesystem-server",
        version="2.0.0",
    )

    assert tool.name == "read_file"
    assert tool.server == "filesystem-server"
    assert tool.version == "2.0.0"
    assert "path" in tool.parameters["properties"]


@pytest.mark.unit
def test_mcp_tool_defaults():
    """Test MCPTool uses correct defaults."""
    tool = MCPTool(name="test_tool", description="Test", parameters={}, server="test-server")

    assert tool.version == "1.0.0"
    assert tool.metadata == {}


@pytest.mark.unit
def test_mcp_tool_validates_empty_name():
    """Test MCPTool raises ValueError for empty name."""
    with pytest.raises(ValueError, match="Tool name cannot be empty"):
        MCPTool(name="", description="Test", parameters={}, server="test-server")


@pytest.mark.unit
def test_mcp_tool_validates_empty_server():
    """Test MCPTool raises ValueError for empty server."""
    with pytest.raises(ValueError, match="Tool server cannot be empty"):
        MCPTool(name="test_tool", description="Test", parameters={}, server="")


# ============================================================================
# MCPToolCall Tests
# ============================================================================


@pytest.mark.unit
def test_mcp_tool_call_creation_valid():
    """Test MCPToolCall creation with valid data."""
    call = MCPToolCall(tool_name="read_file", arguments={"path": "/etc/hosts"}, timeout=120)

    assert call.tool_name == "read_file"
    assert call.arguments["path"] == "/etc/hosts"
    assert call.timeout == 120


@pytest.mark.unit
def test_mcp_tool_call_defaults():
    """Test MCPToolCall uses correct defaults."""
    call = MCPToolCall(tool_name="test_tool", arguments={})

    assert call.timeout == 60
    assert call.metadata == {}


@pytest.mark.unit
def test_mcp_tool_call_validates_empty_name():
    """Test MCPToolCall raises ValueError for empty tool name."""
    with pytest.raises(ValueError, match="Tool name cannot be empty"):
        MCPToolCall(tool_name="", arguments={})


@pytest.mark.unit
def test_mcp_tool_call_validates_negative_timeout():
    """Test MCPToolCall raises ValueError for negative timeout."""
    with pytest.raises(ValueError, match="Timeout must be positive"):
        MCPToolCall(tool_name="test", arguments={}, timeout=-10)


# ============================================================================
# MCPToolResult Tests
# ============================================================================


@pytest.mark.unit
def test_mcp_tool_result_success():
    """Test MCPToolResult for successful execution."""
    result = MCPToolResult(
        tool_name="read_file",
        success=True,
        result={"content": "file contents"},
        execution_time=0.5,
    )

    assert result.success is True
    assert result.result["content"] == "file contents"
    assert result.error is None
    assert result.execution_time == 0.5


@pytest.mark.unit
def test_mcp_tool_result_failure():
    """Test MCPToolResult for failed execution."""
    result = MCPToolResult(
        tool_name="read_file", success=False, error="File not found", execution_time=0.1
    )

    assert result.success is False
    assert result.error == "File not found"
    assert result.result is None


@pytest.mark.unit
def test_mcp_tool_result_validates_empty_tool_name():
    """Test MCPToolResult raises ValueError for empty tool name."""
    with pytest.raises(ValueError, match="Tool name cannot be empty"):
        MCPToolResult(tool_name="", success=True, result={})


@pytest.mark.unit
def test_mcp_tool_result_validates_failure_without_error():
    """Test MCPToolResult raises ValueError for failure without error message."""
    with pytest.raises(ValueError, match="Failed execution must have an error message"):
        MCPToolResult(tool_name="test", success=False, result=None, error=None)


# ============================================================================
# MCPServerConnection Tests
# ============================================================================


@pytest.mark.unit
def test_mcp_server_connection_creation():
    """Test MCPServerConnection creation."""
    server = MCPServer(name="test", transport=TransportType.STDIO, endpoint="/bin/test")
    connection = MCPServerConnection(
        server=server, status=ServerStatus.CONNECTED, connection_time="2025-10-27T10:00:00"
    )

    assert connection.server.name == "test"
    assert connection.status == ServerStatus.CONNECTED
    assert connection.connection_time == "2025-10-27T10:00:00"
    assert connection.tools == []


@pytest.mark.unit
def test_mcp_server_connection_with_tools():
    """Test MCPServerConnection stores discovered tools."""
    server = MCPServer(name="test", transport=TransportType.STDIO, endpoint="/bin/test")
    tool1 = MCPTool(name="tool1", description="Test", parameters={}, server="test")
    tool2 = MCPTool(name="tool2", description="Test", parameters={}, server="test")

    connection = MCPServerConnection(
        server=server, status=ServerStatus.CONNECTED, tools=[tool1, tool2]
    )

    assert len(connection.tools) == 2
    assert connection.tools[0].name == "tool1"
    assert connection.tools[1].name == "tool2"


# ============================================================================
# MCPClientStats Tests
# ============================================================================


@pytest.mark.unit
def test_mcp_client_stats_defaults():
    """Test MCPClientStats default values."""
    stats = MCPClientStats()

    assert stats.total_servers == 0
    assert stats.connected_servers == 0
    assert stats.total_tools == 0
    assert stats.total_calls == 0
    assert stats.successful_calls == 0
    assert stats.failed_calls == 0
    assert stats.average_execution_time == 0.0
    assert stats.tools_by_server == {}


@pytest.mark.unit
def test_mcp_client_stats_with_data():
    """Test MCPClientStats with actual data."""
    stats = MCPClientStats(
        total_servers=5,
        connected_servers=3,
        total_tools=15,
        tools_by_server={"server1": 5, "server2": 10},
        total_calls=100,
        successful_calls=95,
        failed_calls=5,
        average_execution_time=0.25,
    )

    assert stats.total_servers == 5
    assert stats.connected_servers == 3
    assert stats.total_tools == 15
    assert stats.tools_by_server["server1"] == 5
    assert stats.successful_calls == 95
    assert stats.failed_calls == 5


# ============================================================================
# Enum Tests
# ============================================================================


@pytest.mark.unit
def test_transport_type_enum():
    """Test TransportType enum values."""
    assert TransportType.STDIO.value == "stdio"
    assert TransportType.HTTP.value == "http"


@pytest.mark.unit
def test_server_status_enum():
    """Test ServerStatus enum values."""
    assert ServerStatus.DISCONNECTED.value == "disconnected"
    assert ServerStatus.CONNECTING.value == "connecting"
    assert ServerStatus.CONNECTED.value == "connected"
    assert ServerStatus.ERROR.value == "error"
