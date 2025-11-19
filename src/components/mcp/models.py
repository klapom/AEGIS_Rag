"""MCP (Model Context Protocol) data models.

This module defines the data structures for MCP server connections and tools.
Follows MCP Spec 2025-06-18.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TransportType(Enum):
    """Transport type for MCP server communication."""

    STDIO = "stdio"
    HTTP = "http"

class ServerStatus(Enum):
    """Status of an MCP server connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class MCPServer:
    """Configuration for an MCP server.

    Attributes:
        name: Unique name identifier for the server
        transport: Transport protocol (stdio or HTTP)
        endpoint: Connection endpoint (command for stdio, URL for HTTP)
        description: Human-readable description of the server
        timeout: Connection timeout in seconds
        retry_attempts: Number of retry attempts on connection failure
        metadata: Additional server metadata
    """

    name: str
    transport: TransportType
    endpoint: str
    description: str = ""
    timeout: int = 30
    retry_attempts: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate server configuration."""
        if not self.name:
            raise ValueError("Server name cannot be empty")
        if not self.endpoint:
            raise ValueError("Server endpoint cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.retry_attempts < 0:
            raise ValueError("Retry attempts cannot be negative")

@dataclass
class MCPTool:
    """MCP tool definition.

    Attributes:
        name: Tool name (unique within server)
        description: Human-readable description
        parameters: JSON Schema for tool parameters (inputSchema in MCP spec)
        server: Name of the server providing this tool
        version: Tool version (optional)
        metadata: Additional tool metadata
    """

    name: str
    description: str
    parameters: dict[str, Any]
    server: str
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate tool definition."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.server:
            raise ValueError("Tool server cannot be empty")

@dataclass
class MCPToolCall:
    """Request to execute an MCP tool.

    Attributes:
        tool_name: Name of the tool to execute
        arguments: Tool arguments matching the tool's parameter schema
        timeout: Execution timeout in seconds
        metadata: Additional metadata for the call
    """

    tool_name: str
    arguments: dict[str, Any]
    timeout: int = 60
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate tool call."""
        if not self.tool_name:
            raise ValueError("Tool name cannot be empty")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

@dataclass
class MCPToolResult:
    """Result of an MCP tool execution.

    Attributes:
        tool_name: Name of the executed tool
        success: Whether the execution succeeded
        result: Tool result data (if successful)
        error: Error message (if failed)
        execution_time: Execution time in seconds
        metadata: Additional metadata about the execution
    """

    tool_name: str
    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate tool result."""
        if not self.tool_name:
            raise ValueError("Tool name cannot be empty")
        if self.success and self.result is None:
            # Warning: successful execution without result
            pass
        if not self.success and not self.error:
            raise ValueError("Failed execution must have an error message")

@dataclass
class MCPServerConnection:
    """Active connection to an MCP server.

    Attributes:
        server: Server configuration
        status: Current connection status
        connection_time: When the connection was established
        tools: list of discovered tools from this server
        error: Last error message (if any)
        metadata: Additional connection metadata
    """

    server: MCPServer
    status: ServerStatus
    connection_time: str | None = None
    tools: list[MCPTool] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class MCPClientStats:
    """Statistics for the MCP client.

    Attributes:
        total_servers: Total number of configured servers
        connected_servers: Number of currently connected servers
        total_tools: Total number of discovered tools
        tools_by_server: Tool count per server
        total_calls: Total number of tool calls executed
        successful_calls: Number of successful tool calls
        failed_calls: Number of failed tool calls
        average_execution_time: Average tool execution time in seconds
    """

    total_servers: int = 0
    connected_servers: int = 0
    total_tools: int = 0
    tools_by_server: dict[str, int] = field(default_factory=dict)
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    average_execution_time: float = 0.0
