"""MCP Client Stub for Testing.

Stub implementation of MCP client for use in tests and when the full
MCP client from Subagent 3 is not yet available.

Sprint 9 Feature 9.7: Tool Execution Handler
"""

from typing import Any

from src.components.mcp.types import MCPServer, MCPTool

class MCPClientStub:
    """Stub MCP client for testing.

    This stub provides a minimal interface compatible with the real MCP client
    that will be implemented by Subagent 3. It allows Feature 9.7 and 9.8 to
    be developed and tested independently.
    """

    def __init__(self) -> None:
        """Initialize stub client."""
        self.servers: dict[str, MCPServer] = {}
        self.connections: dict[str, Any] = {}
        self._tools: list[MCPTool] = []

    async def connect(self, server: MCPServer) -> bool:
        """Connect to an MCP server (stub).

        Args:
            server: Server configuration

        Returns:
            True if connection successful
        """
        self.servers[server.name] = server
        self.connections[server.name] = MockConnection(server)

        # Add server's tools to available tools
        if server.tools:
            self._tools.extend(server.tools)

        return True

    async def disconnect(self, server_name: str) -> bool:
        """Disconnect from server (stub).

        Args:
            server_name: Name of server to disconnect

        Returns:
            True if disconnected
        """
        if server_name in self.connections:
            del self.connections[server_name]

        return True

    def list_tools(self, server_name: str | None = None) -> list[MCPTool]:
        """list available tools (stub).

        Args:
            server_name: Optional server name to filter by

        Returns:
            list of available tools
        """
        if server_name:
            return [t for t in self._tools if t.server == server_name]
        return self._tools

    def get_tool(self, tool_name: str, server_name: str | None = None) -> MCPTool | None:
        """Get a specific tool by name (stub).

        Args:
            tool_name: Name of the tool
            server_name: Optional server name to filter by

        Returns:
            MCPTool if found, None otherwise
        """
        tools = self.list_tools(server_name)
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None

    async def execute_tool(self, tool_call: Any) -> Any:
        """Execute a tool call (stub).

        Args:
            tool_call: Tool call to execute

        Returns:
            Mock tool result
        """
        from src.components.mcp.models import MCPToolResult

        # Find the tool to get server info
        tool = self.get_tool(tool_call.tool_name)
        if not tool:
            return MCPToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error="Tool not found",
                execution_time=0.0,
            )

        # Return success by default
        return MCPToolResult(
            tool_name=tool_call.tool_name,
            success=True,
            result={"status": "success", "stub": True},
            execution_time=0.1,
        )

    def add_tool(self, tool: MCPTool) -> None:
        """Add a tool to the stub client (for testing).

        Args:
            tool: Tool to add
        """
        self._tools.append(tool)

    def clear_tools(self) -> None:
        """Clear all tools (for testing)."""
        self._tools = []

class MockConnection:
    """Mock connection object for stub testing."""

    def __init__(self, server: MCPServer) -> None:
        """Initialize mock connection.

        Args:
            server: Server configuration
        """
        self.server = server
        self.transport = server.transport

    async def call_tool(self, tool_name: str, parameters: dict[str, Any]) -> Any:
        """Mock tool call.

        Args:
            tool_name: Name of tool to call
            parameters: Tool parameters

        Returns:
            Mock result
        """
        # Return a simple mock result
        return {"status": "success", "tool": tool_name, "params": parameters}
