"""Unit tests for MCP Registry Client.

Sprint 107 Feature 107.2: Test registry auto-discovery and installation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml

from src.components.mcp.registry_client import (
    MCPRegistryClient,
    MCPServerDefinition,
)


class TestMCPServerDefinition:
    """Test MCPServerDefinition dataclass."""

    def test_stdio_server_definition(self):
        """Test stdio server definition."""
        server = MCPServerDefinition(
            id="@test/server-filesystem",
            name="Filesystem Server",
            description="Test filesystem server",
            transport="stdio",
            command="npx",
            args=["@test/server-filesystem"],
            version="1.0.0",
        )

        assert server.id == "@test/server-filesystem"
        assert server.name == "Filesystem Server"
        assert server.transport == "stdio"
        assert server.command == "npx"
        assert server.args == ["@test/server-filesystem"]

    def test_http_server_definition(self):
        """Test HTTP server definition."""
        server = MCPServerDefinition(
            id="test-web-server",
            name="Web Server",
            description="Test web server",
            transport="http",
            url="http://localhost:8080/mcp",
            version="1.0.0",
        )

        assert server.id == "test-web-server"
        assert server.transport == "http"
        assert server.url == "http://localhost:8080/mcp"


class TestMCPRegistryClient:
    """Test MCPRegistryClient."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_registry_data(self):
        """Mock registry JSON data."""
        return {
            "servers": [
                {
                    "id": "@modelcontextprotocol/server-filesystem",
                    "name": "Filesystem Server",
                    "description": "Read and write files",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-filesystem"],
                    "version": "1.0.2",
                    "stars": 1250,
                    "downloads": 15000,
                    "tags": ["filesystem", "files"],
                },
                {
                    "id": "@modelcontextprotocol/server-github",
                    "name": "GitHub Server",
                    "description": "Interact with GitHub",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-github"],
                    "dependencies": {"npm": ["@modelcontextprotocol/server-github@^1.0.0"], "env": ["GITHUB_TOKEN"]},
                    "version": "1.0.1",
                    "stars": 980,
                    "downloads": 8500,
                    "tags": ["github", "git"],
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_discover_servers(self, temp_cache_dir, mock_registry_data):
        """Test discovering servers from registry."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_registry_data
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._http_client, "get", return_value=mock_response):
            servers = await client.discover_servers("https://test-registry.com/servers.json")

        assert len(servers) == 2
        assert servers[0].id == "@modelcontextprotocol/server-filesystem"
        assert servers[0].name == "Filesystem Server"
        assert servers[0].stars == 1250
        assert servers[1].id == "@modelcontextprotocol/server-github"
        assert "GITHUB_TOKEN" in servers[1].dependencies.get("env", [])

        await client.close()

    @pytest.mark.asyncio
    async def test_discover_servers_with_cache(self, temp_cache_dir, mock_registry_data):
        """Test discovering servers uses cache."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        # First call - should hit HTTP
        mock_response = MagicMock()
        mock_response.json.return_value = mock_registry_data
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._http_client, "get", return_value=mock_response) as mock_get:
            servers1 = await client.discover_servers("https://test-registry.com/servers.json")
            assert len(servers1) == 2
            assert mock_get.call_count == 1

            # Second call - should use cache
            servers2 = await client.discover_servers("https://test-registry.com/servers.json")
            assert len(servers2) == 2
            assert mock_get.call_count == 1  # Still 1 - no additional HTTP call

        await client.close()

    @pytest.mark.asyncio
    async def test_search_servers(self, temp_cache_dir, mock_registry_data):
        """Test searching servers."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_registry_data
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._http_client, "get", return_value=mock_response):
            # Search by name
            results = await client.search_servers("filesystem", "https://test-registry.com/servers.json")
            assert len(results) == 1
            assert results[0].name == "Filesystem Server"

            # Search by tag
            results = await client.search_servers("github", "https://test-registry.com/servers.json")
            assert len(results) == 1
            assert results[0].name == "GitHub Server"

            # Search with no results
            results = await client.search_servers("nonexistent", "https://test-registry.com/servers.json")
            assert len(results) == 0

        await client.close()

    @pytest.mark.asyncio
    async def test_get_server_details(self, temp_cache_dir, mock_registry_data):
        """Test getting server details."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_registry_data
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._http_client, "get", return_value=mock_response):
            # Get existing server
            server = await client.get_server_details(
                "@modelcontextprotocol/server-filesystem",
                "https://test-registry.com/servers.json"
            )
            assert server is not None
            assert server.name == "Filesystem Server"

            # Get non-existent server
            server = await client.get_server_details(
                "nonexistent-server",
                "https://test-registry.com/servers.json"
            )
            assert server is None

        await client.close()

    @pytest.mark.asyncio
    async def test_install_server(self, temp_cache_dir, mock_registry_data):
        """Test installing a server."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        # Create temp config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"servers": []}, f)
            config_path = Path(f.name)

        try:
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = mock_registry_data
            mock_response.raise_for_status = MagicMock()

            with patch.object(client._http_client, "get", return_value=mock_response):
                result = await client.install_server(
                    "@modelcontextprotocol/server-filesystem",
                    "https://test-registry.com/servers.json",
                    config_path=config_path,
                    auto_connect=True,
                )

            assert result["status"] == "installed"
            assert result["auto_connect"] is True

            # Check config was updated
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            assert len(config["servers"]) == 1
            assert config["servers"][0]["name"] == "modelcontextprotocol-server-filesystem"
            assert config["servers"][0]["auto_connect"] is True

        finally:
            config_path.unlink()
            await client.close()

    @pytest.mark.asyncio
    async def test_install_server_already_installed(self, temp_cache_dir, mock_registry_data):
        """Test installing a server that's already installed."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        # Create config with server already installed
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "servers": [{
                    "name": "modelcontextprotocol-server-filesystem",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-filesystem"],
                }]
            }, f)
            config_path = Path(f.name)

        try:
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = mock_registry_data
            mock_response.raise_for_status = MagicMock()

            with patch.object(client._http_client, "get", return_value=mock_response):
                result = await client.install_server(
                    "@modelcontextprotocol/server-filesystem",
                    "https://test-registry.com/servers.json",
                    config_path=config_path,
                )

            assert result["status"] == "already_installed"

        finally:
            config_path.unlink()
            await client.close()

    @pytest.mark.asyncio
    async def test_install_dependencies_env_check(self, temp_cache_dir, mock_registry_data):
        """Test environment variable checking."""
        client = MCPRegistryClient(cache_dir=temp_cache_dir, cache_ttl_seconds=3600)

        server = MCPServerDefinition(
            id="test-server",
            name="Test Server",
            description="Test",
            transport="stdio",
            command="npx",
            dependencies={"env": ["TEST_TOKEN"]},
            version="1.0.0",
        )

        # Without environment variable
        results = await client._install_dependencies(server)
        assert len(results["env"]) == 1
        assert results["env"][0]["status"] == "missing"
        assert len(results["errors"]) == 1

        # With environment variable
        with patch.dict("os.environ", {"TEST_TOKEN": "test_value"}):
            results = await client._install_dependencies(server)
            assert len(results["env"]) == 1
            assert results["env"][0]["status"] == "found"
            assert len(results["errors"]) == 0

        await client.close()


class TestCaching:
    """Test cache functionality."""

    def test_cache_key_generation(self, tmp_path):
        """Test cache key generation from URL."""
        client = MCPRegistryClient(cache_dir=tmp_path)

        key1 = client._get_cache_key("https://registry.com/servers.json")
        key2 = client._get_cache_key("https://registry.com/servers.json")
        key3 = client._get_cache_key("https://other-registry.com/servers.json")

        # Same URL should generate same key
        assert key1 == key2
        # Different URL should generate different key
        assert key1 != key3

    def test_cache_read_write(self, tmp_path):
        """Test reading and writing cache."""
        client = MCPRegistryClient(cache_dir=tmp_path)

        cache_key = "test_key"
        data = [{"id": "test", "name": "Test Server"}]

        # Write cache
        client._write_cache(cache_key, data)

        # Read cache
        cached = client._read_cache(cache_key)
        assert cached == data

        # Read non-existent cache
        cached = client._read_cache("nonexistent")
        assert cached is None
