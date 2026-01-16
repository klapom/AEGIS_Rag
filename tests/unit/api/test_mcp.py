"""Unit tests for MCP API endpoints.

Sprint Context: Sprint 40 (2025-12-08) - Feature 40.2: Tool Discovery & Management

Tests all MCP API endpoints including:
- Server listing
- Server connection/disconnection
- Tool discovery
- Tool execution
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.dependencies import get_current_user
from src.api.main import app
from src.components.mcp import (
    MCPServer,
    MCPServerConnection,
    MCPTool,
    MCPToolResult,
    ServerStatus,
    TransportType,
)
from src.core.auth import User

# Mock user for bypassing authentication in tests
MOCK_USER = User(user_id="test-user-id", username="testuser", role="user")


def mock_get_current_user() -> User:
    """Mock get_current_user dependency."""
    return MOCK_USER


@pytest.fixture
def test_client():
    """Create test client with auth bypassed."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    if hasattr(app.state, "limiter"):
        delattr(app.state, "limiter")
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_connection_manager():
    """Mock MCP connection manager."""
    mock_manager = MagicMock()
    mock_manager.client = MagicMock()
    mock_manager.client.servers = {}
    mock_manager.get_connection_details = MagicMock(return_value=[])
    mock_manager.get_all_tools = MagicMock(return_value=[])
    mock_manager.get_tools_by_server = MagicMock(return_value=[])
    mock_manager.health_check = AsyncMock(
        return_value={
            "status": "healthy",
            "total_servers": 0,
            "connected_servers": 0,
            "total_tools": 0,
            "connections": {},
            "auto_reconnect": True,
        }
    )

    with patch("src.api.v1.mcp.get_connection_manager", return_value=mock_manager):
        yield mock_manager


class TestListServers:
    """Tests for GET /api/v1/mcp/servers endpoint."""

    def test_list_servers_empty(self, test_client, mock_connection_manager):
        """Test listing servers when none are configured."""
        mock_connection_manager.get_connection_details.return_value = []

        response = test_client.get("/api/v1/mcp/servers")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_servers_with_connections(self, test_client, mock_connection_manager):
        """Test listing servers with active connections."""
        # Mock server connection
        server = MCPServer(
            name="filesystem",
            transport=TransportType.STDIO,
            endpoint="npx @modelcontextprotocol/server-filesystem /data",
            description="Filesystem server",
        )
        connection = MCPServerConnection(
            server=server,
            status=ServerStatus.CONNECTED,
            connection_time="2025-12-08T10:00:00Z",
            tools=[
                MCPTool(
                    name="read_file",
                    description="Read file contents",
                    parameters={},
                    server="filesystem",
                )
            ],
        )

        mock_connection_manager.get_connection_details.return_value = [connection]

        response = test_client.get("/api/v1/mcp/servers")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "filesystem"
        assert data[0]["transport"] == "stdio"
        assert data[0]["status"] == "connected"
        assert data[0]["tool_count"] == 1


class TestConnectServer:
    """Tests for POST /api/v1/mcp/servers/{server_name}/connect endpoint."""

    def test_connect_server_success(self, test_client, mock_connection_manager):
        """Test successful server connection."""
        # Mock successful connection
        mock_connection_manager.connect_all = AsyncMock(return_value={"filesystem": True})
        mock_connection_manager.get_tools_by_server.return_value = [
            MCPTool(
                name="read_file",
                description="Read file contents",
                parameters={},
                server="filesystem",
            )
        ]

        response = test_client.post(
            "/api/v1/mcp/servers/filesystem/connect",
            json={
                "transport": "stdio",
                "endpoint": "npx @modelcontextprotocol/server-filesystem /data",
                "description": "Filesystem server",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["server_name"] == "filesystem"
        assert data["status"] == "connected"
        assert data["tool_count"] == 1

    def test_connect_server_failure(self, test_client, mock_connection_manager):
        """Test failed server connection."""
        # Mock failed connection
        mock_connection_manager.connect_all = AsyncMock(return_value={"filesystem": False})

        response = test_client.post(
            "/api/v1/mcp/servers/filesystem/connect",
            json={
                "transport": "stdio",
                "endpoint": "npx @modelcontextprotocol/server-filesystem /data",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"

    def test_connect_server_invalid_transport(self, test_client, mock_connection_manager):
        """Test connection with invalid transport type."""
        response = test_client.post(
            "/api/v1/mcp/servers/filesystem/connect",
            json={
                "transport": "invalid",
                "endpoint": "some-endpoint",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        # HTTPException detail can be in different formats depending on exception handler
        assert "Invalid transport type" in str(response_data)

    def test_connect_server_exception(self, test_client, mock_connection_manager):
        """Test connection with exception."""
        # Mock exception during connection
        mock_connection_manager.connect_all = AsyncMock(side_effect=Exception("Connection failed"))

        response = test_client.post(
            "/api/v1/mcp/servers/filesystem/connect",
            json={
                "transport": "stdio",
                "endpoint": "npx @modelcontextprotocol/server-filesystem /data",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to connect to server" in str(response.json())


class TestDisconnectServer:
    """Tests for POST /api/v1/mcp/servers/{server_name}/disconnect endpoint."""

    def test_disconnect_server_success(self, test_client, mock_connection_manager):
        """Test successful server disconnection."""
        # Mock server exists
        mock_connection_manager.client.servers = {"filesystem": MagicMock()}
        mock_connection_manager.client.disconnect = AsyncMock()

        response = test_client.post("/api/v1/mcp/servers/filesystem/disconnect")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "Disconnected from filesystem" in data["message"]

    def test_disconnect_server_not_found(self, test_client, mock_connection_manager):
        """Test disconnecting from non-existent server."""
        # Mock server doesn't exist
        mock_connection_manager.client.servers = {}

        response = test_client.post("/api/v1/mcp/servers/filesystem/disconnect")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Server not found" in str(response.json())

    def test_disconnect_server_exception(self, test_client, mock_connection_manager):
        """Test disconnection with exception."""
        # Mock server exists
        mock_connection_manager.client.servers = {"filesystem": MagicMock()}
        mock_connection_manager.client.disconnect = AsyncMock(
            side_effect=Exception("Disconnect failed")
        )

        response = test_client.post("/api/v1/mcp/servers/filesystem/disconnect")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to disconnect" in str(response.json())


class TestListTools:
    """Tests for GET /api/v1/mcp/tools endpoint."""

    def test_list_all_tools(self, test_client, mock_connection_manager):
        """Test listing all tools across servers."""
        tools = [
            MCPTool(
                name="read_file",
                description="Read file contents",
                parameters={"type": "object"},
                server="filesystem",
            ),
            MCPTool(
                name="fetch_url",
                description="Fetch URL content",
                parameters={"type": "object"},
                server="web",
            ),
        ]
        mock_connection_manager.get_all_tools.return_value = tools

        response = test_client.get("/api/v1/mcp/tools")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "read_file"
        assert data[0]["server"] == "filesystem"
        assert data[1]["name"] == "fetch_url"
        assert data[1]["server"] == "web"

    def test_list_tools_by_server(self, test_client, mock_connection_manager):
        """Test listing tools from specific server."""
        tools = [
            MCPTool(
                name="read_file",
                description="Read file contents",
                parameters={"type": "object"},
                server="filesystem",
            )
        ]
        mock_connection_manager.client.servers = {"filesystem": MagicMock()}
        mock_connection_manager.get_tools_by_server.return_value = tools

        response = test_client.get("/api/v1/mcp/tools?server_name=filesystem")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "read_file"

    def test_list_tools_server_not_found(self, test_client, mock_connection_manager):
        """Test listing tools from non-existent server."""
        mock_connection_manager.client.servers = {}

        response = test_client.get("/api/v1/mcp/tools?server_name=nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Server not found" in str(response.json())


class TestGetToolDetails:
    """Tests for GET /api/v1/mcp/tools/{tool_name} endpoint."""

    def test_get_tool_details_success(self, test_client, mock_connection_manager):
        """Test getting tool details."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
            server="filesystem",
            version="1.0.0",
        )
        mock_connection_manager.client.get_tool = MagicMock(return_value=tool)

        response = test_client.get("/api/v1/mcp/tools/read_file")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "read_file"
        assert data["server"] == "filesystem"
        assert data["version"] == "1.0.0"
        assert "path" in data["parameters"]["properties"]

    def test_get_tool_details_not_found(self, test_client, mock_connection_manager):
        """Test getting details for non-existent tool."""
        mock_connection_manager.client.get_tool = MagicMock(return_value=None)

        response = test_client.get("/api/v1/mcp/tools/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tool not found" in str(response.json())


class TestExecuteTool:
    """Tests for POST /api/v1/mcp/tools/{tool_name}/execute endpoint."""

    def test_execute_tool_success(self, test_client, mock_connection_manager):
        """Test successful tool execution."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            parameters={},
            server="filesystem",
        )
        mock_connection_manager.client.get_tool = MagicMock(return_value=tool)

        # Mock successful execution
        result = MCPToolResult(
            tool_name="read_file",
            success=True,
            result={"content": "file contents"},
            execution_time=0.5,
        )
        mock_connection_manager.client.execute_tool = AsyncMock(return_value=result)

        response = test_client.post(
            "/api/v1/mcp/tools/read_file/execute",
            json={"arguments": {"path": "/data/report.txt"}, "timeout": 30},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["tool_name"] == "read_file"
        assert data["result"]["content"] == "file contents"
        assert data["execution_time"] == 0.5

    def test_execute_tool_failure(self, test_client, mock_connection_manager):
        """Test failed tool execution."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            parameters={},
            server="filesystem",
        )
        mock_connection_manager.client.get_tool = MagicMock(return_value=tool)

        # Mock failed execution
        result = MCPToolResult(
            tool_name="read_file",
            success=False,
            error="File not found",
            execution_time=0.1,
        )
        mock_connection_manager.client.execute_tool = AsyncMock(return_value=result)

        response = test_client.post(
            "/api/v1/mcp/tools/read_file/execute",
            json={"arguments": {"path": "/nonexistent.txt"}},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "File not found"

    def test_execute_tool_not_found(self, test_client, mock_connection_manager):
        """Test executing non-existent tool."""
        mock_connection_manager.client.get_tool = MagicMock(return_value=None)

        response = test_client.post(
            "/api/v1/mcp/tools/nonexistent/execute",
            json={"arguments": {}},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Tool not found" in str(response.json())

    def test_execute_tool_exception(self, test_client, mock_connection_manager):
        """Test tool execution with exception."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            parameters={},
            server="filesystem",
        )
        mock_connection_manager.client.get_tool = MagicMock(return_value=tool)
        mock_connection_manager.client.execute_tool = AsyncMock(
            side_effect=Exception("Execution failed")
        )

        response = test_client.post(
            "/api/v1/mcp/tools/read_file/execute",
            json={"arguments": {"path": "/data/report.txt"}},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Tool execution failed" in str(response.json())


class TestMCPHealthCheck:
    """Tests for GET /api/v1/mcp/health endpoint."""

    def test_health_check_success(self, test_client, mock_connection_manager):
        """Test MCP health check."""
        health_data = {
            "status": "healthy",
            "total_servers": 2,
            "connected_servers": 2,
            "total_tools": 5,
            "connections": {"filesystem": "connected", "web": "connected"},
            "auto_reconnect": True,
        }
        mock_connection_manager.health_check = AsyncMock(return_value=health_data)

        response = test_client.get("/api/v1/mcp/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["total_servers"] == 2
        assert data["connected_servers"] == 2
        assert data["total_tools"] == 5


class TestServerHealth:
    """Tests for GET /api/v1/mcp/servers/{server_name}/health endpoint."""

    def test_server_health_healthy(self, test_client, mock_connection_manager):
        """Test health check for healthy server."""
        # Mock connected server
        server = MCPServer(
            name="bash-tools",
            transport=TransportType.STDIO,
            endpoint="local",
            description="Bash tools",
        )
        connection = MagicMock()
        connection.status = ServerStatus.CONNECTED

        mock_connection_manager.client.servers = {"bash-tools": server}
        mock_connection_manager.client.connections = {"bash-tools": connection}
        mock_connection_manager.get_tools_by_server.return_value = [
            MCPTool(
                name="bash",
                description="Execute bash",
                parameters={},
                server="bash-tools",
            )
        ]

        response = test_client.get("/api/v1/mcp/servers/bash-tools/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], int)

    def test_server_health_not_found(self, test_client, mock_connection_manager):
        """Test health check for non-existent server."""
        # Ensure servers dict is empty
        mock_connection_manager.client.servers = {}

        with patch("src.api.v1.mcp.get_connection_manager", return_value=mock_connection_manager):
            response = test_client.get("/api/v1/mcp/servers/non-existent/health")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        # API uses structured error format with error.message
        assert "error" in data
        assert "not found" in data["error"]["message"].lower()

    def test_server_health_not_connected(self, test_client, mock_connection_manager):
        """Test health check for server without connection."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.STDIO,
            endpoint="test",
            description="Test",
        )
        mock_connection_manager.client.servers = {"test-server": server}
        mock_connection_manager.client.connections = {}

        response = test_client.get("/api/v1/mcp/servers/test-server/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["latency_ms"] is None
        assert "error" in data

    def test_server_health_disconnected(self, test_client, mock_connection_manager):
        """Test health check for disconnected server."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.STDIO,
            endpoint="test",
            description="Test",
        )
        connection = MagicMock()
        connection.status = ServerStatus.DISCONNECTED

        mock_connection_manager.client.servers = {"test-server": server}
        mock_connection_manager.client.connections = {"test-server": connection}

        response = test_client.get("/api/v1/mcp/servers/test-server/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "disconnected" in data["error"].lower()

    def test_server_health_error(self, test_client, mock_connection_manager):
        """Test health check when tools retrieval fails."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.STDIO,
            endpoint="test",
            description="Test",
        )
        connection = MagicMock()
        connection.status = ServerStatus.CONNECTED

        mock_connection_manager.client.servers = {"test-server": server}
        mock_connection_manager.client.connections = {"test-server": connection}
        mock_connection_manager.get_tools_by_server.side_effect = Exception("Connection lost")

        response = test_client.get("/api/v1/mcp/servers/test-server/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "Connection lost" in data["error"]


class TestValidation:
    """Tests for request validation."""

    def test_connect_server_missing_transport(self, test_client, mock_connection_manager):
        """Test connection without transport."""
        response = test_client.post(
            "/api/v1/mcp/servers/filesystem/connect",
            json={"endpoint": "some-endpoint"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_connect_server_missing_endpoint(self, test_client, mock_connection_manager):
        """Test connection without endpoint."""
        response = test_client.post(
            "/api/v1/mcp/servers/filesystem/connect",
            json={"transport": "stdio"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_execute_tool_invalid_timeout(self, test_client, mock_connection_manager):
        """Test tool execution with invalid timeout."""
        tool = MCPTool(
            name="read_file",
            description="Read file contents",
            parameters={},
            server="filesystem",
        )
        mock_connection_manager.client.get_tool = MagicMock(return_value=tool)

        response = test_client.post(
            "/api/v1/mcp/tools/read_file/execute",
            json={"arguments": {}, "timeout": 0},  # Invalid timeout
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
