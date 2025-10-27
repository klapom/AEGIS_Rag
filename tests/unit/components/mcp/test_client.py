"""Unit tests for MCP Client (Feature 9.6).

Tests cover:
- Model validation
- Connection management (stdio and HTTP)
- Tool discovery
- Tool execution
- Error handling
- Statistics tracking
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from src.components.mcp import (
    MCPClient,
    MCPClientError,
    MCPConnectionError,
    MCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolError,
    ServerStatus,
    TransportType,
)


class TestMCPModels:
    """Test MCP data models validation."""

    def test_mcp_server_valid(self):
        """Test valid MCPServer creation."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            description="Test server",
        )
        assert server.name == "test-server"
        assert server.transport == TransportType.HTTP
        assert server.endpoint == "http://localhost:8000"
        assert server.timeout == 30  # default

    def test_mcp_server_invalid_name(self):
        """Test MCPServer with empty name raises ValueError."""
        with pytest.raises(ValueError, match="Server name cannot be empty"):
            MCPServer(name="", transport=TransportType.HTTP, endpoint="http://localhost")

    def test_mcp_server_invalid_timeout(self):
        """Test MCPServer with invalid timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            MCPServer(
                name="test",
                transport=TransportType.HTTP,
                endpoint="http://localhost",
                timeout=-1,
            )

    def test_mcp_tool_valid(self):
        """Test valid MCPTool creation."""
        tool = MCPTool(
            name="read_file",
            description="Read a file",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            server="fs-server",
        )
        assert tool.name == "read_file"
        assert tool.server == "fs-server"

    def test_mcp_tool_call_valid(self):
        """Test valid MCPToolCall creation."""
        call = MCPToolCall(tool_name="read_file", arguments={"path": "/tmp/test.txt"}, timeout=30)
        assert call.tool_name == "read_file"
        assert call.arguments == {"path": "/tmp/test.txt"}

    def test_mcp_tool_call_invalid_timeout(self):
        """Test MCPToolCall with invalid timeout."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            MCPToolCall(tool_name="test", arguments={}, timeout=0)


class TestMCPClientInit:
    """Test MCP client initialization."""

    def test_client_initialization(self):
        """Test MCPClient initializes with empty state."""
        client = MCPClient()
        assert len(client.servers) == 0
        assert len(client.connections) == 0
        assert len(client.tools) == 0
        stats = client.get_stats()
        assert stats.total_servers == 0
        assert stats.total_tools == 0


class TestMCPClientHTTPConnection:
    """Test HTTP transport connection."""

    @pytest.mark.asyncio
    async def test_connect_http_success(self):
        """Test successful HTTP connection."""
        client = MCPClient()
        server = MCPServer(
            name="test-http",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
        )

        # Mock HTTP client
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Mock tool discovery
            with patch.object(client, "discover_tools", return_value=[]):
                success = await client.connect(server)

        assert success is True
        assert server.name in client.servers
        assert client.connections[server.name].status == ServerStatus.CONNECTED

    @pytest.mark.asyncio
    async def test_connect_http_unhealthy(self):
        """Test HTTP connection to unhealthy server."""
        client = MCPClient()
        server = MCPServer(
            name="test-http",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            retry_attempts=1,
        )

        # Mock unhealthy response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(MCPConnectionError, match="HTTP server unhealthy"):
                await client.connect(server)

        assert client.connections[server.name].status == ServerStatus.ERROR

    @pytest.mark.asyncio
    async def test_connect_http_network_error(self):
        """Test HTTP connection with network error."""
        client = MCPClient()
        server = MCPServer(
            name="test-http",
            transport=TransportType.HTTP,
            endpoint="http://localhost:8000",
            retry_attempts=1,
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client_class.return_value = mock_client

            with pytest.raises(MCPConnectionError, match="HTTP connection failed"):
                await client.connect(server)


class TestMCPClientStdioConnection:
    """Test stdio transport connection."""

    @pytest.mark.asyncio
    async def test_connect_stdio_success(self):
        """Test successful stdio connection."""
        client = MCPClient()
        server = MCPServer(
            name="test-stdio", transport=TransportType.STDIO, endpoint="node server.js"
        )

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()

        # Mock initialization response
        init_response = {"jsonrpc": "2.0", "result": {"protocolVersion": "2025-06-18"}, "id": 1}
        mock_process.stdout.readline.return_value = (json.dumps(init_response) + "\n").encode()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Mock tool discovery
            with patch.object(client, "discover_tools", return_value=[]):
                success = await client.connect(server)

        assert success is True
        assert server.name in client.servers

    @pytest.mark.asyncio
    async def test_connect_stdio_init_error(self):
        """Test stdio connection with initialization error."""
        client = MCPClient()
        server = MCPServer(
            name="test-stdio",
            transport=TransportType.STDIO,
            endpoint="node server.js",
            retry_attempts=1,
        )

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()

        # Mock error response
        error_response = {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Init failed"}}
        mock_process.stdout.readline.return_value = (json.dumps(error_response) + "\n").encode()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(MCPConnectionError, match="Initialization failed"):
                await client.connect(server)


class TestMCPClientToolDiscovery:
    """Test tool discovery functionality."""

    @pytest.mark.asyncio
    async def test_discover_tools_http(self):
        """Test tool discovery via HTTP."""
        client = MCPClient()
        server = MCPServer(
            name="test-http", transport=TransportType.HTTP, endpoint="http://localhost:8000"
        )

        # Setup mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "tools": [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "inputSchema": {"type": "object"},
                },
                {
                    "name": "write_file",
                    "description": "Write a file",
                    "inputSchema": {"type": "object"},
                },
            ]
        }
        mock_client.get.return_value = mock_response

        client._http_clients[server.name] = mock_client
        client.servers[server.name] = server
        client.connections[server.name] = MagicMock(status=ServerStatus.CONNECTED)

        tools = await client.discover_tools(server.name)

        assert len(tools) == 2
        assert tools[0].name == "read_file"
        assert tools[1].name == "write_file"
        assert all(t.server == server.name for t in tools)

    @pytest.mark.asyncio
    async def test_discover_tools_stdio(self):
        """Test tool discovery via stdio."""
        client = MCPClient()
        server = MCPServer(
            name="test-stdio", transport=TransportType.STDIO, endpoint="node server.js"
        )

        # Setup mock process
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()

        # Mock tools/list response
        tools_response = {
            "jsonrpc": "2.0",
            "result": {
                "tools": [{"name": "query_db", "description": "Query database", "inputSchema": {}}]
            },
        }
        mock_process.stdout.readline.return_value = (json.dumps(tools_response) + "\n").encode()

        client._processes[server.name] = mock_process
        client.servers[server.name] = server
        client.connections[server.name] = MagicMock(status=ServerStatus.CONNECTED)

        tools = await client.discover_tools(server.name)

        assert len(tools) == 1
        assert tools[0].name == "query_db"

    @pytest.mark.asyncio
    async def test_discover_tools_not_connected(self):
        """Test tool discovery when not connected raises error."""
        client = MCPClient()

        with pytest.raises(ValueError, match="Not connected to nonexistent"):
            await client.discover_tools("nonexistent")

    @pytest.mark.asyncio
    async def test_list_tools_all(self):
        """Test listing all tools from all servers."""
        client = MCPClient()
        client.tools = {
            "server1": [
                MCPTool("tool1", "desc1", {}, "server1"),
                MCPTool("tool2", "desc2", {}, "server1"),
            ],
            "server2": [MCPTool("tool3", "desc3", {}, "server2")],
        }

        all_tools = client.list_tools()
        assert len(all_tools) == 3

    @pytest.mark.asyncio
    async def test_list_tools_by_server(self):
        """Test listing tools from specific server."""
        client = MCPClient()
        client.tools = {
            "server1": [MCPTool("tool1", "desc1", {}, "server1")],
            "server2": [MCPTool("tool2", "desc2", {}, "server2")],
        }

        tools = client.list_tools(server_name="server1")
        assert len(tools) == 1
        assert tools[0].name == "tool1"

    def test_get_tool_by_name(self):
        """Test getting specific tool by name."""
        client = MCPClient()
        client.tools = {
            "server1": [MCPTool("read_file", "Read file", {}, "server1")],
        }

        tool = client.get_tool("read_file")
        assert tool is not None
        assert tool.name == "read_file"

        # Non-existent tool
        tool = client.get_tool("nonexistent")
        assert tool is None


class TestMCPClientToolExecution:
    """Test tool execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_http_success(self):
        """Test successful tool execution via HTTP."""
        client = MCPClient()
        server = MCPServer(
            name="test-server", transport=TransportType.HTTP, endpoint="http://localhost:8000"
        )

        # Setup tool
        tool = MCPTool(
            name="read_file", description="Read file", parameters={}, server="test-server"
        )
        client.servers[server.name] = server
        client.tools[server.name] = [tool]

        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"result": {"content": "file content"}}
        mock_client.post.return_value = mock_response
        client._http_clients[server.name] = mock_client

        # Execute tool
        tool_call = MCPToolCall(tool_name="read_file", arguments={"path": "/tmp/test.txt"})
        result = await client.execute_tool(tool_call)

        assert result.success is True
        assert result.result == {"content": "file content"}
        assert result.tool_name == "read_file"

    @pytest.mark.asyncio
    async def test_execute_tool_http_timeout(self):
        """Test tool execution timeout via HTTP."""
        client = MCPClient()
        server = MCPServer(
            name="test-server", transport=TransportType.HTTP, endpoint="http://localhost:8000"
        )

        tool = MCPTool(
            name="slow_tool", description="Slow tool", parameters={}, server="test-server"
        )
        client.servers[server.name] = server
        client.tools[server.name] = [tool]

        # Mock timeout
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        client._http_clients[server.name] = mock_client

        tool_call = MCPToolCall(tool_name="slow_tool", arguments={}, timeout=5)
        result = await client.execute_tool(tool_call)

        assert result.success is False
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_execute_tool_stdio_success(self):
        """Test successful tool execution via stdio."""
        client = MCPClient()
        server = MCPServer(
            name="test-stdio", transport=TransportType.STDIO, endpoint="node server.js"
        )

        tool = MCPTool(name="query_db", description="Query DB", parameters={}, server="test-stdio")
        client.servers[server.name] = server
        client.tools[server.name] = [tool]

        # Mock process
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()

        # Mock successful response
        response = {"jsonrpc": "2.0", "result": {"rows": [1, 2, 3]}}
        mock_process.stdout.readline.return_value = (json.dumps(response) + "\n").encode()
        client._processes[server.name] = mock_process

        tool_call = MCPToolCall(tool_name="query_db", arguments={"query": "SELECT * FROM users"})
        result = await client.execute_tool(tool_call)

        assert result.success is True
        assert result.result == {"rows": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test executing non-existent tool raises error."""
        client = MCPClient()

        tool_call = MCPToolCall(tool_name="nonexistent", arguments={})

        with pytest.raises(ValueError, match="Tool not found"):
            await client.execute_tool(tool_call)


class TestMCPClientDisconnection:
    """Test disconnection functionality."""

    @pytest.mark.asyncio
    async def test_disconnect_http(self):
        """Test disconnecting from HTTP server."""
        client = MCPClient()
        server_name = "test-http"

        # Setup mock HTTP client
        mock_client = AsyncMock()
        client._http_clients[server_name] = mock_client
        client.servers[server_name] = MCPServer(
            name=server_name, transport=TransportType.HTTP, endpoint="http://localhost"
        )
        client.connections[server_name] = MagicMock(status=ServerStatus.CONNECTED)
        client.tools[server_name] = [MCPTool("tool1", "desc", {}, server_name)]
        client._stats.connected_servers = 1
        client._stats.total_tools = 1

        await client.disconnect(server_name)

        assert server_name not in client.servers
        assert server_name not in client._http_clients
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_stdio(self):
        """Test disconnecting from stdio server."""
        client = MCPClient()
        server_name = "test-stdio"

        # Setup mock process
        mock_process = AsyncMock()
        client._processes[server_name] = mock_process
        client.servers[server_name] = MCPServer(
            name=server_name, transport=TransportType.STDIO, endpoint="node server.js"
        )
        client.connections[server_name] = MagicMock(status=ServerStatus.CONNECTED)
        client._stats.connected_servers = 1

        await client.disconnect(server_name)

        assert server_name not in client.servers
        assert server_name not in client._processes
        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Test disconnecting from all servers."""
        client = MCPClient()

        # Setup multiple servers
        mock_http = AsyncMock()
        mock_process = AsyncMock()

        client._http_clients["http-server"] = mock_http
        client._processes["stdio-server"] = mock_process
        client.servers["http-server"] = MCPServer(
            name="http-server", transport=TransportType.HTTP, endpoint="http://localhost"
        )
        client.servers["stdio-server"] = MCPServer(
            name="stdio-server", transport=TransportType.STDIO, endpoint="node server.js"
        )

        await client.disconnect_all()

        assert len(client.servers) == 0
        assert len(client._http_clients) == 0
        assert len(client._processes) == 0


class TestMCPClientStats:
    """Test client statistics tracking."""

    def test_stats_initialization(self):
        """Test stats are initialized to zero."""
        client = MCPClient()
        stats = client.get_stats()

        assert stats.total_servers == 0
        assert stats.connected_servers == 0
        assert stats.total_tools == 0
        assert stats.total_calls == 0

    @pytest.mark.asyncio
    async def test_stats_after_connection(self):
        """Test stats updated after connection."""
        client = MCPClient()
        server = MCPServer(name="test", transport=TransportType.HTTP, endpoint="http://localhost")

        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with patch.object(client, "discover_tools", return_value=[]):
                await client.connect(server)

        stats = client.get_stats()
        assert stats.total_servers == 1
        assert stats.connected_servers == 1
