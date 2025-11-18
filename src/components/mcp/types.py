"""MCP Types and Data Models.

Type definitions for MCP (Model Context Protocol) integration.
These types are used by the tool executor and action agent.

Sprint 9 Feature 9.7: Tool Execution Handler
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class MCPTool:
    """Represents an MCP tool available for execution.

    Attributes:
        name: Unique name of the tool
        description: Human-readable description
        server: Name of the MCP server providing this tool
        parameters: JSON schema for tool parameters
        metadata: Additional tool metadata
    """

    name: str
    description: str
    server: str
    parameters: dict[str, Any]
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}

    def get_required_parameters(self) -> list[str]:
        """Get list of required parameter names.

        Returns:
            List of required parameter names
        """
        return self.parameters.get("required", [])

    def validate_parameters(self, params: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate parameters against tool schema.

        Args:
            params: Parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        required = self.get_required_parameters()

        for param in required:
            if param not in params:
                return False, f"Missing required parameter: {param}"

        return True, None


@dataclass
class MCPServer:
    """Represents an MCP server configuration.

    Attributes:
        name: Server name
        transport: Transport type ("stdio" or "http")
        command: Command to start server (for stdio)
        url: Server URL (for http)
        env: Environment variables for server
        tools: List of tools provided by this server
    """

    name: str
    transport: str
    command: str | None = None
    url: str | None = None
    env: dict[str, str] | None = None
    tools: list[MCPTool] | None = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.env is None:
            self.env = {}
        if self.tools is None:
            self.tools = []


@dataclass
class ToolExecutionResult:
    """Result of a tool execution.

    Attributes:
        success: Whether execution succeeded
        result: Parsed result data
        tool_name: Name of executed tool
        execution_time_ms: Execution time in milliseconds
        error: Error message if failed
        metadata: Additional metadata
    """

    success: bool
    result: dict[str, Any]
    tool_name: str
    execution_time_ms: float
    error: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
