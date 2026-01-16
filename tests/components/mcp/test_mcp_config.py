"""Unit tests for MCP configuration system.

Sprint 107 Feature 107.1: Test YAML-based MCP server configuration.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.components.mcp.config import (
    MCPConfigLoader,
    MCPConfiguration,
    MCPServerConfig,
    get_config_loader,
    load_mcp_config,
)
from src.components.mcp.models import TransportType


class TestMCPServerConfig:
    """Test MCPServerConfig Pydantic model."""

    def test_stdio_server_valid(self):
        """Test valid stdio server configuration."""
        config = MCPServerConfig(
            name="bash-tools",
            transport="stdio",
            command="/usr/bin/bash",
            args=[],
            description="Bash tools",
            auto_connect=True,
            enabled=True,
        )

        assert config.name == "bash-tools"
        assert config.transport == "stdio"
        assert config.command == "/usr/bin/bash"
        assert config.auto_connect is True
        assert config.enabled is True

    def test_http_server_valid(self):
        """Test valid http server configuration."""
        config = MCPServerConfig(
            name="browser-tools",
            transport="http",
            url="http://localhost:9222",
            description="Browser tools",
        )

        assert config.name == "browser-tools"
        assert config.transport == "http"
        assert config.url == "http://localhost:9222"

    def test_invalid_transport(self):
        """Test invalid transport type raises error."""
        with pytest.raises(ValueError, match="Invalid transport type"):
            MCPServerConfig(
                name="test",
                transport="invalid",
                command="/bin/bash",
            )

    def test_stdio_without_command(self):
        """Test stdio transport without command raises error."""
        with pytest.raises(ValueError, match="stdio transport requires 'command'"):
            MCPServerConfig(
                name="test",
                transport="stdio",
            )

    def test_http_without_url(self):
        """Test http transport without url raises error."""
        with pytest.raises(ValueError, match="http transport requires 'url'"):
            MCPServerConfig(
                name="test",
                transport="http",
            )

    def test_to_mcp_server_stdio(self):
        """Test conversion to MCPServer for stdio transport."""
        config = MCPServerConfig(
            name="python-tools",
            transport="stdio",
            command="/usr/bin/python3",
            args=["-m", "mcp_server"],
            description="Python tools",
            timeout=60,
            retry_attempts=5,
        )

        server = config.to_mcp_server()

        assert server.name == "python-tools"
        assert server.transport == TransportType.STDIO
        assert server.endpoint == "/usr/bin/python3 -m mcp_server"
        assert server.description == "Python tools"
        assert server.timeout == 60
        assert server.retry_attempts == 5

    def test_to_mcp_server_http(self):
        """Test conversion to MCPServer for http transport."""
        config = MCPServerConfig(
            name="web-tools",
            transport="http",
            url="http://localhost:8080/mcp",
            description="Web tools",
        )

        server = config.to_mcp_server()

        assert server.name == "web-tools"
        assert server.transport == TransportType.HTTP
        assert server.endpoint == "http://localhost:8080/mcp"
        assert server.description == "Web tools"


class TestMCPConfiguration:
    """Test MCPConfiguration model."""

    def test_empty_configuration(self):
        """Test empty configuration."""
        config = MCPConfiguration(servers=[])

        assert len(config.servers) == 0
        assert len(config.get_auto_connect_servers()) == 0
        assert len(config.get_all_enabled_servers()) == 0

    def test_get_auto_connect_servers(self):
        """Test filtering auto-connect servers."""
        config = MCPConfiguration(
            servers=[
                MCPServerConfig(
                    name="server1",
                    transport="stdio",
                    command="/bin/bash",
                    auto_connect=True,
                    enabled=True,
                ),
                MCPServerConfig(
                    name="server2",
                    transport="stdio",
                    command="/bin/bash",
                    auto_connect=False,
                    enabled=True,
                ),
                MCPServerConfig(
                    name="server3",
                    transport="stdio",
                    command="/bin/bash",
                    auto_connect=True,
                    enabled=False,
                ),
            ]
        )

        auto_connect = config.get_auto_connect_servers()

        assert len(auto_connect) == 1
        assert auto_connect[0].name == "server1"

    def test_get_all_enabled_servers(self):
        """Test filtering enabled servers."""
        config = MCPConfiguration(
            servers=[
                MCPServerConfig(
                    name="server1",
                    transport="stdio",
                    command="/bin/bash",
                    enabled=True,
                ),
                MCPServerConfig(
                    name="server2",
                    transport="stdio",
                    command="/bin/bash",
                    enabled=False,
                ),
            ]
        )

        enabled = config.get_all_enabled_servers()

        assert len(enabled) == 1
        assert enabled[0].name == "server1"


class TestMCPConfigLoader:
    """Test MCPConfigLoader."""

    def test_load_from_file(self):
        """Test loading configuration from YAML file."""
        # Create temporary YAML config
        config_data = {
            "servers": [
                {
                    "name": "bash-tools",
                    "transport": "stdio",
                    "command": "/usr/bin/bash",
                    "args": [],
                    "description": "Bash tools",
                    "auto_connect": True,
                    "enabled": True,
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = MCPConfigLoader(temp_path)
            config = loader.load()

            assert len(config.servers) == 1
            assert config.servers[0].name == "bash-tools"
            assert config.servers[0].auto_connect is True

        finally:
            Path(temp_path).unlink()

    def test_load_empty_file(self):
        """Test loading empty YAML file returns empty config."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("")
            temp_path = f.name

        try:
            loader = MCPConfigLoader(temp_path)
            config = loader.load()

            assert len(config.servers) == 0

        finally:
            Path(temp_path).unlink()

    def test_load_missing_file(self):
        """Test loading missing file returns empty config."""
        loader = MCPConfigLoader("/nonexistent/config.yaml")
        config = loader.load()

        assert len(config.servers) == 0

    def test_load_invalid_yaml(self):
        """Test loading invalid YAML raises ValueError."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content:\n  - broken")
            temp_path = f.name

        try:
            loader = MCPConfigLoader(temp_path)

            with pytest.raises(ValueError, match="Invalid YAML"):
                loader.load()

        finally:
            Path(temp_path).unlink()

    def test_load_invalid_config(self):
        """Test loading invalid config raises ValueError."""
        config_data = {
            "servers": [
                {
                    "name": "test",
                    "transport": "invalid",  # Invalid transport
                    "command": "/bin/bash",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = MCPConfigLoader(temp_path)

            with pytest.raises(ValueError):
                loader.load()

        finally:
            Path(temp_path).unlink()

    def test_reload(self):
        """Test reloading configuration."""
        config_data = {"servers": []}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = MCPConfigLoader(temp_path)
            config1 = loader.load()
            assert len(config1.servers) == 0

            # Update file
            config_data["servers"].append(
                {
                    "name": "new-server",
                    "transport": "stdio",
                    "command": "/bin/bash",
                }
            )

            with open(temp_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            # Reload
            config2 = loader.reload()
            assert len(config2.servers) == 1
            assert config2.servers[0].name == "new-server"

        finally:
            Path(temp_path).unlink()

    def test_config_property(self):
        """Test config property lazy loading."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump({"servers": []}, f)
            temp_path = f.name

        try:
            loader = MCPConfigLoader(temp_path)

            # Access config property (should load)
            config1 = loader.config
            assert len(config1.servers) == 0

            # Access again (should return cached)
            config2 = loader.config
            assert config1 is config2

        finally:
            Path(temp_path).unlink()


class TestGlobalFunctions:
    """Test global helper functions."""

    def test_get_config_loader_singleton(self):
        """Test get_config_loader returns singleton."""
        loader1 = get_config_loader()
        loader2 = get_config_loader()

        assert loader1 is loader2

    def test_load_mcp_config(self):
        """Test load_mcp_config function."""
        # Note: This uses default config path which may not exist
        config = load_mcp_config()

        # Should return empty config if file doesn't exist
        assert isinstance(config, MCPConfiguration)


class TestConfigValidation:
    """Test configuration validation edge cases."""

    def test_timeout_validation(self):
        """Test timeout must be positive."""
        with pytest.raises(ValueError):
            MCPServerConfig(
                name="test",
                transport="stdio",
                command="/bin/bash",
                timeout=0,
            )

    def test_retry_attempts_validation(self):
        """Test retry attempts cannot be negative."""
        with pytest.raises(ValueError):
            MCPServerConfig(
                name="test",
                transport="stdio",
                command="/bin/bash",
                retry_attempts=-1,
            )

    def test_dependencies(self):
        """Test server with dependencies."""
        config = MCPServerConfig(
            name="github-tools",
            transport="stdio",
            command="npx",
            args=["@modelcontextprotocol/server-github"],
            dependencies={
                "npm": ["@modelcontextprotocol/server-github@^1.0.0"],
                "env": ["GITHUB_TOKEN"],
            },
        )

        assert "npm" in config.dependencies
        assert "env" in config.dependencies

        server = config.to_mcp_server()
        assert "dependencies" in server.metadata
        assert server.metadata["auto_connect"] is True  # Default value
