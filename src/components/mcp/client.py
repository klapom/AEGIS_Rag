"""MCP (Model Context Protocol) Client implementation.

This module provides the main MCP client for connecting to external MCP servers,
discovering tools, and executing tool calls. Follows MCP Spec 2025-06-18.
"""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from .models import (
    MCPClientStats,
    MCPServer,
    MCPServerConnection,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    ServerStatus,
    TransportType,
)

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors."""

    pass


class MCPConnectionError(MCPClientError):
    """Exception raised when connection to MCP server fails."""

    pass


class MCPToolError(MCPClientError):
    """Exception raised when tool execution fails."""

    pass


class MCPClient:
    """MCP Client to connect to external MCP servers.

    The client supports multiple servers via stdio and HTTP transports,
    automatic tool discovery, and tool execution with timeout and retries.
    """

    def __init__(self) -> None:
        """Initialize the MCP client."""
        self.servers: dict[str, MCPServer] = {}
        self.connections: dict[str, MCPServerConnection] = {}
        self.tools: dict[str, list[MCPTool]] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._http_clients: dict[str, httpx.AsyncClient] = {}
        self._stats = MCPClientStats()
        self._tool_call_times: list[float] = []

    async def connect(self, server: MCPServer) -> bool:
        """Connect to an MCP server.

        Args:
            server: MCP server configuration

        Returns:
            True if connection successful, False otherwise

        Raises:
            MCPConnectionError: If connection fails after all retries
        """
        logger.info(f"Connecting to MCP server: {server.name} ({server.transport.value})")

        connection = MCPServerConnection(
            server=server,
            status=ServerStatus.CONNECTING,
        )
        self.connections[server.name] = connection

        for attempt in range(server.retry_attempts):
            try:
                if server.transport == TransportType.STDIO:
                    await self._connect_stdio(server)
                else:  # HTTP
                    await self._connect_http(server)

                self.servers[server.name] = server
                connection.status = ServerStatus.CONNECTED
                connection.connection_time = datetime.now(UTC).isoformat()
                self._stats.total_servers += 1
                self._stats.connected_servers += 1

                # Discover tools from this server
                await self.discover_tools(server.name)

                logger.info(f"Successfully connected to {server.name}")
                return True

            except Exception as e:
                logger.warning(
                    f"Connection attempt {attempt + 1}/{server.retry_attempts} "
                    f"failed for {server.name}: {e}"
                )
                if attempt == server.retry_attempts - 1:
                    connection.status = ServerStatus.ERROR
                    connection.error = str(e)
                    raise MCPConnectionError(
                        f"Failed to connect to {server.name} after "
                        f"{server.retry_attempts} attempts: {e}"
                    ) from e
                await asyncio.sleep(1)  # Wait before retry

        return False

    async def _connect_stdio(self, server: MCPServer) -> None:
        """Connect to stdio-based MCP server.

        Args:
            server: MCP server configuration

        Raises:
            MCPConnectionError: If subprocess creation fails
        """
        try:
            # Parse command and arguments
            cmd_parts = server.endpoint.split()

            # Start subprocess with server command
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._processes[server.name] = process

            # Send initialization request (MCP handshake)
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "clientInfo": {"name": "aegis-rag"}},
                "id": 1,
            }

            await self._send_stdio_request(server.name, init_request)

            # Sprint 120: Add timeout to prevent hanging on non-MCP processes
            try:
                response = await asyncio.wait_for(
                    self._read_stdio_response(server.name),
                    timeout=server.timeout,
                )
            except TimeoutError:
                # Kill the hung process
                process.kill()
                raise MCPConnectionError(
                    f"Timeout waiting for MCP init response from {server.name} "
                    f"after {server.timeout}s — is '{cmd_parts[0]}' a valid MCP server?"
                )

            if "error" in response:
                raise MCPConnectionError(f"Initialization failed: {response['error']}")

            logger.debug(f"STDIO connection established to {server.name}")

        except Exception as e:
            raise MCPConnectionError(f"Failed to create stdio process: {e}") from e

    async def _connect_http(self, server: MCPServer) -> None:
        """Connect to HTTP-based MCP server.

        Args:
            server: MCP server configuration

        Raises:
            MCPConnectionError: If HTTP connection fails
        """
        try:
            # Create HTTP client
            client = httpx.AsyncClient(base_url=server.endpoint, timeout=server.timeout)
            self._http_clients[server.name] = client

            # Test connection with health check
            response = await client.get("/health")
            if response.status_code != 200:
                raise MCPConnectionError(
                    f"HTTP server unhealthy: {response.status_code} {response.text}"
                )

            logger.debug(f"HTTP connection established to {server.name}")

        except httpx.HTTPError as e:
            raise MCPConnectionError(f"HTTP connection failed: {e}") from e

    async def discover_tools(self, server_name: str) -> list[MCPTool]:
        """Discover available tools from a server.

        Args:
            server_name: Name of the connected server

        Returns:
            list of discovered tools

        Raises:
            ValueError: If not connected to the server
            MCPToolError: If tool discovery fails
        """
        connection = self.connections.get(server_name)
        if not connection or connection.status != ServerStatus.CONNECTED:
            raise ValueError(f"Not connected to {server_name}")

        logger.info(f"Discovering tools from {server_name}")

        try:
            server = self.servers[server_name]
            if server.transport == TransportType.STDIO:
                tools = await self._discover_tools_stdio(server_name)
            else:  # HTTP
                tools = await self._discover_tools_http(server_name)

            # Store tools
            self.tools[server_name] = tools
            connection.tools = tools
            self._stats.total_tools += len(tools)
            self._stats.tools_by_server[server_name] = len(tools)

            logger.info(f"Discovered {len(tools)} tools from {server_name}")
            return tools

        except Exception as e:
            raise MCPToolError(f"Tool discovery failed for {server_name}: {e}") from e

    async def _discover_tools_stdio(self, server_name: str) -> list[MCPTool]:
        """Discover tools via stdio transport.

        Args:
            server_name: Name of the server

        Returns:
            list of discovered tools
        """
        # Send MCP tools/list request
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}

        await self._send_stdio_request(server_name, request)
        response = await self._read_stdio_response(server_name)

        if "error" in response:
            raise MCPToolError(f"Tool discovery error: {response['error']}")

        # Parse tools from response
        tools = []
        for tool_data in response.get("result", {}).get("tools", []):
            tools.append(
                MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("inputSchema", {}),
                    server=server_name,
                    version=tool_data.get("version", "1.0.0"),
                )
            )

        return tools

    async def _discover_tools_http(self, server_name: str) -> list[MCPTool]:
        """Discover tools via HTTP transport.

        Args:
            server_name: Name of the server

        Returns:
            list of discovered tools
        """
        client = self._http_clients[server_name]
        response = await client.get("/tools")
        response.raise_for_status()

        tools_data = response.json()

        # Parse tools from response
        tools = []
        for tool_data in tools_data.get("tools", []):
            tools.append(
                MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("inputSchema", {}),
                    server=server_name,
                    version=tool_data.get("version", "1.0.0"),
                )
            )

        return tools

    def list_tools(self, server_name: str | None = None) -> list[MCPTool]:
        """list all discovered tools (optionally filtered by server).

        Args:
            server_name: Optional server name to filter by

        Returns:
            list of tools
        """
        if server_name:
            return self.tools.get(server_name, [])  # type: ignore[no-any-return]
        else:
            # Return tools from all servers
            all_tools = []
            for tools in self.tools.values():
                all_tools.extend(tools)
            return all_tools

    def get_tool(self, tool_name: str, server_name: str | None = None) -> MCPTool | None:
        """Get a specific tool by name.

        Args:
            tool_name: Name of the tool
            server_name: Optional server name to search in

        Returns:
            MCPTool if found, None otherwise
        """
        if server_name:
            tools = self.tools.get(server_name, [])
            return next((t for t in tools if t.name == tool_name), None)
        else:
            # Search in all servers
            for tools in self.tools.values():
                tool = next((t for t in tools if t.name == tool_name), None)
                if tool:
                    return tool
            return None

    async def execute_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute an MCP tool.

        Args:
            tool_call: Tool call configuration

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
            MCPToolError: If tool execution fails
        """
        # Find the tool
        tool = self.get_tool(tool_call.tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_call.tool_name}")

        logger.info(f"Executing tool: {tool_call.tool_name} on server {tool.server}")

        start_time = time.time()
        self._stats.total_calls += 1

        try:
            server = self.servers[tool.server]
            if server.transport == TransportType.STDIO:
                result = await self._execute_tool_stdio(tool, tool_call)
            else:  # HTTP
                result = await self._execute_tool_http(tool, tool_call)

            execution_time = time.time() - start_time
            result.execution_time = execution_time
            self._tool_call_times.append(execution_time)

            if result.success:
                self._stats.successful_calls += 1
            else:
                self._stats.failed_calls += 1

            # Update average execution time
            if self._tool_call_times:
                self._stats.average_execution_time = sum(self._tool_call_times) / len(
                    self._tool_call_times
                )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._stats.failed_calls += 1
            logger.error(f"Tool execution failed: {e}")
            return MCPToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time,
            )

    async def _execute_tool_stdio(self, tool: MCPTool, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute tool via stdio transport.

        Args:
            tool: Tool definition
            tool_call: Tool call configuration

        Returns:
            Tool execution result
        """
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool.name, "arguments": tool_call.arguments},
            "id": 3,
        }

        await self._send_stdio_request(tool.server, request)

        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                self._read_stdio_response(tool.server), timeout=tool_call.timeout
            )
        except TimeoutError:
            return MCPToolResult(
                tool_name=tool.name, success=False, error=f"Timeout after {tool_call.timeout}s"
            )

        if "error" in response:
            return MCPToolResult(tool_name=tool.name, success=False, error=str(response["error"]))  # type: ignore[no-any-return]

        return MCPToolResult(tool_name=tool.name, success=True, result=response.get("result"))  # type: ignore[no-any-return]

    async def _execute_tool_http(self, tool: MCPTool, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute tool via HTTP transport.

        Args:
            tool: Tool definition
            tool_call: Tool call configuration

        Returns:
            Tool execution result
        """
        client = self._http_clients[tool.server]

        try:
            response = await client.post(
                f"/tools/{tool.name}",
                json=tool_call.arguments,
                timeout=tool_call.timeout,
            )
            response.raise_for_status()
            result_data = response.json()

            return MCPToolResult(
                tool_name=tool.name, success=True, result=result_data.get("result")
            )

        except httpx.TimeoutException:
            return MCPToolResult(
                tool_name=tool.name, success=False, error=f"Timeout after {tool_call.timeout}s"
            )
        except httpx.HTTPStatusError as e:
            return MCPToolResult(
                tool_name=tool.name, success=False, error=f"HTTP {e.response.status_code}: {e}"
            )

    async def disconnect(self, server_name: str) -> None:
        """Disconnect from a server.

        Args:
            server_name: Name of the server to disconnect
        """
        logger.info(f"Disconnecting from {server_name}")

        # Close connection based on transport type
        if server_name in self._processes:
            process = self._processes.pop(server_name)
            process.terminate()
            await process.wait()

        if server_name in self._http_clients:
            client = self._http_clients.pop(server_name)
            await client.aclose()

        # Update state
        if server_name in self.connections:
            self.connections[server_name].status = ServerStatus.DISCONNECTED
            self._stats.connected_servers -= 1

        self.servers.pop(server_name, None)
        tool_count = len(self.tools.pop(server_name, []))
        self._stats.total_tools -= tool_count
        self._stats.tools_by_server.pop(server_name, None)

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        server_names = list(self.servers.keys())
        for server_name in server_names:
            await self.disconnect(server_name)

    def get_stats(self) -> MCPClientStats:
        """Get client statistics.

        Returns:
            Current client statistics
        """
        return self._stats

    def get_connections(self) -> dict[str, MCPServerConnection]:
        """Get all server connections.

        Returns:
            Dictionary of server connections
        """
        return self.connections.copy()

    async def _send_stdio_request(self, server_name: str, request: dict[str, Any]) -> None:
        """Send JSON-RPC request via stdio.

        Args:
            server_name: Name of the server
            request: JSON-RPC request
        """
        process = self._processes[server_name]
        request_json = json.dumps(request) + "\n"
        process.stdin.write(request_json.encode())
        await process.stdin.drain()

    async def _read_stdio_response(self, server_name: str) -> dict[str, Any]:
        """Read JSON-RPC response via stdio.

        Args:
            server_name: Name of the server

        Returns:
            JSON-RPC response
        """
        process = self._processes[server_name]
        response_line = await process.stdout.readline()
        return json.loads(response_line.decode())  # type: ignore[no-any-return]
