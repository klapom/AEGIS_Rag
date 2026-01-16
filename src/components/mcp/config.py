"""MCP Server Configuration Management.

Sprint 107 Feature 107.1: YAML-based server configuration with auto-connect.

This module provides YAML-based configuration for MCP servers with:
- Pydantic validation
- Auto-connect on startup
- Configuration reloading
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from .models import MCPServer, TransportType

logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server.

    Attributes:
        name: Unique server identifier
        transport: Transport protocol (stdio or http)
        command: Command to execute (for stdio transport)
        args: Command arguments (for stdio transport)
        url: HTTP endpoint (for http transport)
        description: Human-readable description
        auto_connect: Whether to connect automatically on startup
        enabled: Whether this server is enabled
        timeout: Connection timeout in seconds
        retry_attempts: Number of connection retries
        dependencies: Optional dependencies (npm, pip, env vars)
    """

    name: str = Field(..., description="Unique server identifier")
    transport: str = Field(..., description="Transport protocol (stdio or http)")
    command: str | None = Field(None, description="Command for stdio transport")
    args: list[str] = Field(default_factory=list, description="Command arguments")
    url: str | None = Field(None, description="URL for http transport")
    description: str = Field(default="", description="Server description")
    auto_connect: bool = Field(True, description="Auto-connect on startup")
    enabled: bool = Field(True, description="Server is enabled")
    timeout: int = Field(30, ge=1, description="Connection timeout (seconds)")
    retry_attempts: int = Field(3, ge=0, description="Connection retry attempts")
    dependencies: dict[str, Any] = Field(
        default_factory=dict, description="Server dependencies"
    )

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate transport type."""
        if v not in ["stdio", "http"]:
            raise ValueError(f"Invalid transport type: {v}. Must be 'stdio' or 'http'")
        return v

    @field_validator("command", "url")
    @classmethod
    def validate_endpoint(cls, v: str | None, info: Any) -> str | None:
        """Validate endpoint based on transport."""
        values = info.data
        transport = values.get("transport")

        if transport == "stdio" and not values.get("command"):
            raise ValueError("stdio transport requires 'command'")
        if transport == "http" and not values.get("url"):
            raise ValueError("http transport requires 'url'")

        return v

    def to_mcp_server(self) -> MCPServer:
        """Convert to MCPServer model.

        Returns:
            MCPServer instance
        """
        # Determine endpoint based on transport
        if self.transport == "stdio":
            endpoint = f"{self.command} {' '.join(self.args)}".strip()
        else:
            endpoint = self.url or ""

        return MCPServer(
            name=self.name,
            transport=TransportType.STDIO if self.transport == "stdio" else TransportType.HTTP,
            endpoint=endpoint,
            description=self.description,
            timeout=self.timeout,
            retry_attempts=self.retry_attempts,
            metadata={"dependencies": self.dependencies, "auto_connect": self.auto_connect},
        )


class MCPConfiguration(BaseModel):
    """Root configuration for MCP servers.

    Attributes:
        servers: List of server configurations
    """

    servers: list[MCPServerConfig] = Field(default_factory=list, description="MCP servers")

    def get_auto_connect_servers(self) -> list[MCPServer]:
        """Get list of servers configured for auto-connect.

        Returns:
            List of MCPServer instances
        """
        return [
            server.to_mcp_server()
            for server in self.servers
            if server.enabled and server.auto_connect
        ]

    def get_all_enabled_servers(self) -> list[MCPServer]:
        """Get all enabled servers.

        Returns:
            List of MCPServer instances
        """
        return [server.to_mcp_server() for server in self.servers if server.enabled]


class MCPConfigLoader:
    """Loader for MCP server configuration from YAML files.

    Sprint 107 Feature 107.1: Configuration loader with validation.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize config loader.

        Args:
            config_path: Path to YAML config file (default: config/mcp_servers.yaml)
        """
        if config_path is None:
            # Default to config/mcp_servers.yaml relative to project root
            self.config_path = Path(__file__).parents[3] / "config" / "mcp_servers.yaml"
        else:
            self.config_path = Path(config_path)

        self._config: MCPConfiguration | None = None

    def load(self, validate: bool = True) -> MCPConfiguration:
        """Load configuration from YAML file.

        Args:
            validate: Whether to validate using Pydantic

        Returns:
            MCPConfiguration instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using empty config")
            return MCPConfiguration(servers=[])

        try:
            with open(self.config_path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            if not raw_config:
                logger.warning("Empty config file, using empty config")
                return MCPConfiguration(servers=[])

            if validate:
                config = MCPConfiguration(**raw_config)
            else:
                config = MCPConfiguration.model_construct(**raw_config)

            self._config = config
            logger.info(
                f"Loaded {len(config.servers)} MCP servers from {self.config_path}",
                extra={
                    "enabled": sum(1 for s in config.servers if s.enabled),
                    "auto_connect": sum(
                        1 for s in config.servers if s.enabled and s.auto_connect
                    ),
                },
            )

            return config

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}") from e

    def reload(self) -> MCPConfiguration:
        """Reload configuration from file.

        Returns:
            Updated MCPConfiguration instance
        """
        logger.info("Reloading MCP configuration")
        return self.load()

    @property
    def config(self) -> MCPConfiguration:
        """Get current configuration (loads if not loaded).

        Returns:
            MCPConfiguration instance
        """
        if self._config is None:
            self._config = self.load()
        return self._config


# Singleton instance
_loader: MCPConfigLoader | None = None


def get_config_loader() -> MCPConfigLoader:
    """Get singleton config loader instance.

    Returns:
        MCPConfigLoader instance
    """
    global _loader
    if _loader is None:
        _loader = MCPConfigLoader()
    return _loader


def load_mcp_config() -> MCPConfiguration:
    """Load MCP configuration from default location.

    Returns:
        MCPConfiguration instance
    """
    loader = get_config_loader()
    return loader.load()
