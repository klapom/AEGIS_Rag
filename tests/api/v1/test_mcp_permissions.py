"""
Tests for MCP Tool Permission Management API endpoints.

Sprint 116 Feature 116.5: MCP Tool Management UI
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.main import app
from src.components.mcp import MCPServer, TransportType
from src.api.v1.mcp import get_connection_manager


@pytest.fixture
async def mock_mcp_tool():
    """Set up a mock MCP tool for testing."""
    # Get connection manager
    manager = get_connection_manager()

    # Create a test server
    server = MCPServer(
        name="test-server",
        transport=TransportType.STDIO,
        endpoint="echo test",
        description="Test server",
        timeout=30,
    )

    # Connect (mock)
    # In real tests, this would connect to a real MCP server
    # For now, we'll just check if the endpoints work

    yield {
        "tool_name": "test_tool",
        "server_name": "test-server",
    }


@pytest.mark.asyncio
class TestToolPermissions:
    """Test tool permission management endpoints."""

    async def test_get_tool_permissions_not_found(self, client: AsyncClient):
        """Test getting permissions for non-existent tool."""
        response = await client.get("/api/v1/mcp/tools/nonexistent/permissions")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    async def test_update_tool_permissions_not_found(self, client: AsyncClient):
        """Test updating permissions for non-existent tool."""
        response = await client.put(
            "/api/v1/mcp/tools/nonexistent/permissions",
            json={"enabled": False},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_tool_config_not_found(self, client: AsyncClient):
        """Test getting config for non-existent tool."""
        response = await client.get("/api/v1/mcp/tools/nonexistent/config")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_tool_config_not_found(self, client: AsyncClient):
        """Test updating config for non-existent tool."""
        response = await client.put(
            "/api/v1/mcp/tools/nonexistent/config",
            json={"config": {"timeout": 60}},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
class TestToolPermissionsIntegration:
    """Integration tests for tool permissions with real MCP connection."""

    @pytest.mark.skip(reason="Requires real MCP server connection")
    async def test_full_permission_workflow(self, client: AsyncClient):
        """
        Test complete permission workflow.

        This test requires a real MCP server to be running.
        Steps:
        1. Get initial permissions (should be enabled by default)
        2. Disable tool
        3. Verify disabled state
        4. Re-enable tool
        5. Update configuration
        6. Verify configuration
        """
        tool_name = "bash"  # Builtin tool

        # 1. Get initial permissions
        response = await client.get(f"/api/v1/mcp/tools/{tool_name}/permissions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tool_name"] == tool_name
        assert data["enabled"] is True

        # 2. Disable tool
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/permissions",
            json={"enabled": False},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is False

        # 3. Verify disabled state
        response = await client.get(f"/api/v1/mcp/tools/{tool_name}/permissions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is False

        # 4. Re-enable tool
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/permissions",
            json={"enabled": True},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["enabled"] is True

        # 5. Update configuration
        config = {"timeout": 120, "max_retries": 5}
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/config",
            json={"config": config},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["config"] == config

        # 6. Verify configuration
        response = await client.get(f"/api/v1/mcp/tools/{tool_name}/config")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["config"] == config


@pytest.mark.asyncio
class TestPermissionValidation:
    """Test permission request validation."""

    @pytest.mark.skip(reason="Requires real MCP server connection")
    async def test_update_permissions_invalid_payload(self, client: AsyncClient):
        """Test that invalid permission update payloads are rejected."""
        tool_name = "bash"

        # Missing enabled field
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/permissions",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid type for enabled
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/permissions",
            json={"enabled": "invalid"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.skip(reason="Requires real MCP server connection")
    async def test_update_config_validation(self, client: AsyncClient):
        """Test config update payload validation."""
        tool_name = "bash"

        # Missing config field
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/config",
            json={},
        )
        # Should still work with default empty config
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

        # Config must be an object
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/config",
            json={"config": "invalid"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestPermissionPersistence:
    """Test that permissions persist across requests."""

    @pytest.mark.skip(reason="Requires real MCP server connection")
    async def test_permission_persistence(self, client: AsyncClient):
        """Test that permission changes persist."""
        tool_name = "bash"

        # Set permission to disabled
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/permissions",
            json={"enabled": False},
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify it persists
        response = await client.get(f"/api/v1/mcp/tools/{tool_name}/permissions")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["enabled"] is False

        # Clean up - re-enable
        await client.put(
            f"/api/v1/mcp/tools/{tool_name}/permissions",
            json={"enabled": True},
        )

    @pytest.mark.skip(reason="Requires real MCP server connection")
    async def test_config_persistence(self, client: AsyncClient):
        """Test that configuration changes persist."""
        tool_name = "bash"
        config = {"test_key": "test_value"}

        # Set config
        response = await client.put(
            f"/api/v1/mcp/tools/{tool_name}/config",
            json={"config": config},
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify it persists
        response = await client.get(f"/api/v1/mcp/tools/{tool_name}/config")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["config"] == config

        # Clean up - reset config
        await client.put(
            f"/api/v1/mcp/tools/{tool_name}/config",
            json={"config": {}},
        )
