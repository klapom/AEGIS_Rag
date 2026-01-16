"""Unit tests for MCP Registry Service.

Sprint 102 Feature: MCP Server Registry backend.

Tests:
- Default server initialization
- Server listing
- Server connection/disconnection
- Health checking
- Tool listing
- Registry health status
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.mcp import MCPServer, MCPServerConnection, MCPTool, ServerStatus, TransportType
from src.domains.mcp_integration.registry import MCPRegistryService


@pytest.fixture
def mock_connection_manager():
    """Create a mock ConnectionManager."""
    manager = MagicMock()
    manager.connect_all = AsyncMock(return_value={"bash-tools": True, "python-tools": True})
    manager.get_connection_details = MagicMock(return_value=[])
    manager.get_tools_by_server = MagicMock(return_value=[])
    manager.get_all_tools = MagicMock(return_value=[])
    manager.health_check = AsyncMock(
        return_value={
            "status": "healthy",
            "total_servers": 2,
            "connected_servers": 2,
        }
    )
    manager.disconnect_all = AsyncMock()
    manager.client = MagicMock()
    manager.client.servers = {}
    manager.client.connections = {}
    manager.client.disconnect = AsyncMock()
    return manager


@pytest.fixture
def registry_service(mock_connection_manager):
    """Create a MCPRegistryService with mocked manager."""
    with patch("src.domains.mcp_integration.registry.ConnectionManager") as mock_cm:
        mock_cm.return_value = mock_connection_manager
        service = MCPRegistryService()
        return service


@pytest.mark.asyncio
class TestMCPRegistryService:
    """Test suite for MCPRegistryService."""

    async def test_initialize_creates_default_servers(self, registry_service, mock_connection_manager):
        """Test that initialize creates bash and python tool servers."""
        await registry_service.initialize()

        # Verify connect_all was called with default servers
        mock_connection_manager.connect_all.assert_called_once()
        servers = mock_connection_manager.connect_all.call_args[0][0]

        assert len(servers) == 2
        assert any(s.name == "bash-tools" for s in servers)
        assert any(s.name == "python-tools" for s in servers)

    async def test_initialize_only_runs_once(self, registry_service, mock_connection_manager):
        """Test that initialize can be called multiple times safely."""
        await registry_service.initialize()
        await registry_service.initialize()

        # Should only connect once
        assert mock_connection_manager.connect_all.call_count == 1

    async def test_list_servers_returns_all_servers(self, registry_service):
        """Test listing all registered servers."""
        # Setup mock connections
        bash_server = MCPServer(
            name="bash-tools",
            transport=TransportType.STDIO,
            endpoint="local",
            description="Bash tools",
        )
        python_server = MCPServer(
            name="python-tools",
            transport=TransportType.STDIO,
            endpoint="local",
            description="Python tools",
        )

        bash_connection = MCPServerConnection(
            server=bash_server,
            status=ServerStatus.CONNECTED,
            tools=[
                MCPTool(
                    name="bash",
                    description="Execute bash",
                    parameters={},
                    server="bash-tools",
                )
            ],
        )
        python_connection = MCPServerConnection(
            server=python_server,
            status=ServerStatus.CONNECTED,
            tools=[
                MCPTool(
                    name="python",
                    description="Execute python",
                    parameters={},
                    server="python-tools",
                )
            ],
        )

        registry_service._manager.get_connection_details.return_value = [
            bash_connection,
            python_connection,
        ]

        servers = registry_service.list_servers()

        assert len(servers) == 2
        assert servers[0]["name"] == "bash-tools"
        assert servers[0]["status"] == "connected"
        assert servers[0]["tools"] == ["bash"]
        assert servers[1]["name"] == "python-tools"

    async def test_connect_server_success(self, registry_service):
        """Test successful server connection."""
        # Setup mock server
        server = MCPServer(
            name="test-server",
            transport=TransportType.STDIO,
            endpoint="test",
            description="Test server",
        )

        registry_service._manager.client.servers = {"test-server": server}
        registry_service._manager.connect_all = AsyncMock(return_value={"test-server": True})
        registry_service._manager.get_tools_by_server.return_value = [
            MCPTool(
                name="test-tool",
                description="Test tool",
                parameters={"type": "object"},
                server="test-server",
            )
        ]

        # Mock _get_server_by_name
        registry_service._get_server_by_name = MagicMock(return_value=server)

        result = await registry_service.connect_server("test-server")

        assert result["status"] == "connected"
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "test-tool"

    async def test_connect_server_failure(self, registry_service):
        """Test failed server connection."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.STDIO,
            endpoint="test",
            description="Test server",
        )

        registry_service._manager.connect_all = AsyncMock(return_value={"test-server": False})
        registry_service._get_server_by_name = MagicMock(return_value=server)

        result = await registry_service.connect_server("test-server")

        assert result["status"] == "error"
        assert result["tools"] == []
        assert "error" in result

    async def test_connect_server_not_found(self, registry_service):
        """Test connecting to non-existent server raises error."""
        registry_service._get_server_by_name = MagicMock(return_value=None)

        with pytest.raises(ValueError, match="Server not found"):
            await registry_service.connect_server("non-existent")

    async def test_disconnect_server_success(self, registry_service):
        """Test successful server disconnection."""
        registry_service._manager.client.servers = {"test-server": MagicMock()}

        result = await registry_service.disconnect_server("test-server")

        assert result["status"] == "disconnected"
        registry_service._manager.client.disconnect.assert_called_once_with("test-server")

    async def test_disconnect_server_not_found(self, registry_service):
        """Test disconnecting from non-existent server raises error."""
        registry_service._manager.client.servers = {}

        with pytest.raises(ValueError, match="Server not found"):
            await registry_service.disconnect_server("non-existent")

    async def test_check_server_health_healthy(self, registry_service):
        """Test health check for healthy server."""
        # Setup connected server
        connection = MagicMock()
        connection.status = ServerStatus.CONNECTED
        registry_service._manager.client.connections = {"test-server": connection}
        registry_service._manager.get_tools_by_server.return_value = [
            MagicMock(name="tool1"),
            MagicMock(name="tool2"),
        ]

        health = await registry_service.check_server_health("test-server")

        assert health["status"] == "healthy"
        assert "latency_ms" in health
        assert health["latency_ms"] is not None
        assert isinstance(health["latency_ms"], int)

    async def test_check_server_health_not_connected(self, registry_service):
        """Test health check for disconnected server."""
        registry_service._manager.client.connections = {}

        health = await registry_service.check_server_health("test-server")

        assert health["status"] == "unhealthy"
        assert health["latency_ms"] is None
        assert "error" in health

    async def test_check_server_health_disconnected_status(self, registry_service):
        """Test health check for server with disconnected status."""
        connection = MagicMock()
        connection.status = ServerStatus.DISCONNECTED
        registry_service._manager.client.connections = {"test-server": connection}

        health = await registry_service.check_server_health("test-server")

        assert health["status"] == "unhealthy"
        assert "disconnected" in health["error"].lower()

    async def test_check_server_health_caching(self, registry_service):
        """Test that health checks are cached."""
        connection = MagicMock()
        connection.status = ServerStatus.CONNECTED
        registry_service._manager.client.connections = {"test-server": connection}
        registry_service._manager.get_tools_by_server.return_value = []

        # First call
        health1 = await registry_service.check_server_health("test-server")

        # Second call (should use cache)
        health2 = await registry_service.check_server_health("test-server")

        # get_tools_by_server should only be called once
        assert registry_service._manager.get_tools_by_server.call_count == 1
        assert health1["status"] == health2["status"]

    async def test_list_tools_all_servers(self, registry_service):
        """Test listing tools from all servers."""
        tools = [
            MCPTool(
                name="bash",
                description="Execute bash",
                parameters={"type": "object"},
                server="bash-tools",
            ),
            MCPTool(
                name="python",
                description="Execute python",
                parameters={"type": "object"},
                server="python-tools",
            ),
        ]
        registry_service._manager.get_all_tools.return_value = tools

        result = registry_service.list_tools()

        assert len(result) == 2
        assert result[0]["name"] == "bash"
        assert result[0]["server"] == "bash-tools"
        assert result[1]["name"] == "python"

    async def test_list_tools_specific_server(self, registry_service):
        """Test listing tools from specific server."""
        tools = [
            MCPTool(
                name="bash",
                description="Execute bash",
                parameters={"type": "object"},
                server="bash-tools",
            )
        ]
        registry_service._manager.get_tools_by_server.return_value = tools

        result = registry_service.list_tools(server_name="bash-tools")

        assert len(result) == 1
        assert result[0]["name"] == "bash"
        registry_service._manager.get_tools_by_server.assert_called_once_with("bash-tools")

    async def test_get_registry_health(self, registry_service):
        """Test getting overall registry health."""
        health = await registry_service.get_registry_health()

        assert health["status"] == "healthy"
        assert health["total_servers"] == 2
        assert health["connected_servers"] == 2

    async def test_shutdown_cleans_up(self, registry_service):
        """Test that shutdown disconnects all servers."""
        await registry_service.initialize()

        await registry_service.shutdown()

        registry_service._manager.disconnect_all.assert_called_once()
        assert not registry_service._initialized
        assert len(registry_service._health_cache) == 0

    def test_get_default_servers_configuration(self, registry_service):
        """Test default server configurations are correct."""
        servers = registry_service._get_default_servers()

        assert len(servers) == 2

        # Check bash-tools
        bash = next(s for s in servers if s.name == "bash-tools")
        assert bash.transport == TransportType.STDIO
        assert bash.endpoint == "local"
        assert bash.timeout == 30
        assert bash.metadata["local"] is True

        # Check python-tools
        python = next(s for s in servers if s.name == "python-tools")
        assert python.transport == TransportType.STDIO
        assert python.endpoint == "local"
        assert python.timeout == 30
        assert python.metadata["local"] is True

    async def test_health_check_error_handling(self, registry_service):
        """Test health check handles errors gracefully."""
        connection = MagicMock()
        connection.status = ServerStatus.CONNECTED
        registry_service._manager.client.connections = {"test-server": connection}
        registry_service._manager.get_tools_by_server.side_effect = Exception("Connection error")

        health = await registry_service.check_server_health("test-server")

        assert health["status"] == "unhealthy"
        assert "error" in health
        assert "Connection error" in health["error"]

    def test_get_cached_latency(self, registry_service):
        """Test getting cached latency values."""
        # No cache
        assert registry_service._get_cached_latency("test-server") is None

        # Add to cache
        import time

        registry_service._health_cache["test-server"] = {
            "status": "healthy",
            "latency_ms": 42,
            "timestamp": time.time(),
        }

        # Get cached value
        assert registry_service._get_cached_latency("test-server") == 42

        # Expired cache
        registry_service._health_cache["test-server"]["timestamp"] = time.time() - 20
        assert registry_service._get_cached_latency("test-server") is None
