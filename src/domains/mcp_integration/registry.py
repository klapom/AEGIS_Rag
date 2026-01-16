"""MCP Registry Service.

Sprint 102 Feature: MCP Server Registry backend for managing MCP servers and tools.

This service provides:
- In-memory registry for MCP servers with health monitoring
- Default local tool servers (bash, python, browser)
- Integration with existing tool framework (Sprint 59)
- Server lifecycle management (connect/disconnect)

Architecture:
    - MCPRegistryService: Main service for registry operations
    - Default servers: bash-tools, python-tools, browser-tools (local)
    - ConnectionManager: Handles actual MCP connections (from components.mcp)

Usage:
    >>> registry = MCPRegistryService()
    >>> await registry.initialize()
    >>> servers = registry.list_servers()
    >>> health = await registry.check_server_health("bash-tools")
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import structlog

from src.components.mcp import ConnectionManager, MCPServer, ServerStatus, TransportType
from src.domains.llm_integration.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


class MCPRegistryService:
    """MCP Server Registry Service.

    Manages MCP server configurations, connections, and health monitoring.
    Provides default local tool servers for bash and python execution.
    """

    def __init__(self) -> None:
        """Initialize the MCP registry service."""
        self._manager = ConnectionManager(
            auto_reconnect=True,
            reconnect_interval=30,
            max_reconnect_attempts=5,
        )
        self._initialized = False
        self._health_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 10  # seconds

    async def initialize(self) -> None:
        """Initialize the registry with default servers.

        This connects to default local tool servers:
        - bash-tools: Local bash execution (Sprint 59)
        - python-tools: Local python execution (Sprint 59)
        - browser-tools: Playwright browser automation (MCP)
        """
        if self._initialized:
            logger.debug("registry_already_initialized")
            return

        logger.info("initializing_mcp_registry")

        # Define default servers
        default_servers = self._get_default_servers()

        # Connect to all default servers in parallel
        results = await self._manager.connect_all(default_servers)

        # Log connection results
        successful = sum(1 for success in results.values() if success)
        logger.info(
            "mcp_registry_initialized",
            total_servers=len(default_servers),
            connected_servers=successful,
            results=results,
        )

        self._initialized = True

    def _get_default_servers(self) -> list[MCPServer]:
        """Get default MCP server configurations.

        Returns:
            List of default MCPServer configurations

        Note:
            bash-tools and python-tools are virtual servers that use
            the existing ToolRegistry framework (Sprint 59).
        """
        return [
            MCPServer(
                name="bash-tools",
                transport=TransportType.STDIO,
                endpoint="local",  # Virtual endpoint - uses ToolRegistry
                description="Local bash command execution tool (Sprint 59)",
                timeout=30,
                metadata={
                    "category": "execution",
                    "local": True,
                    "tool_count": 1,
                },
            ),
            MCPServer(
                name="python-tools",
                transport=TransportType.STDIO,
                endpoint="local",  # Virtual endpoint - uses ToolRegistry
                description="Local Python code execution tool (Sprint 59)",
                timeout=30,
                metadata={
                    "category": "execution",
                    "local": True,
                    "tool_count": 1,
                },
            ),
            # Browser tools would be added here when Playwright MCP is integrated
            # MCPServer(
            #     name="browser-tools",
            #     transport=TransportType.STDIO,
            #     endpoint="npx @modelcontextprotocol/server-playwright",
            #     description="Playwright browser automation tools",
            #     timeout=60,
            #     metadata={"category": "browser"},
            # ),
        ]

    def list_servers(self) -> list[dict[str, Any]]:
        """List all registered MCP servers with their status.

        Returns:
            List of server information dictionaries

        Example:
            >>> servers = registry.list_servers()
            >>> [s["name"] for s in servers]
            ['bash-tools', 'python-tools']
        """
        connections = self._manager.get_connection_details()

        return [
            {
                "name": conn.server.name,
                "url": conn.server.endpoint,
                "status": conn.status.value,
                "tools": [tool.name for tool in conn.tools],
                "latency_ms": self._get_cached_latency(conn.server.name),
            }
            for conn in connections
        ]

    async def connect_server(self, server_name: str) -> dict[str, Any]:
        """Connect to an MCP server.

        Args:
            server_name: Name of the server to connect

        Returns:
            Connection result with status and tools

        Raises:
            ValueError: If server not found in registry

        Example:
            >>> result = await registry.connect_server("bash-tools")
            >>> result["status"]
            'connected'
        """
        # Check if server exists in our registry
        server = self._get_server_by_name(server_name)
        if not server:
            raise ValueError(f"Server not found: {server_name}")

        # Connect using connection manager
        results = await self._manager.connect_all([server])
        success = results.get(server_name, False)

        if success:
            tools = self._manager.get_tools_by_server(server_name)
            logger.info(
                "mcp_server_connected",
                server_name=server_name,
                tool_count=len(tools),
            )
            return {
                "status": "connected",
                "tools": [
                    {
                        "name": tool.name,
                        "server": tool.server,
                        "description": tool.description,
                        "input_schema": tool.parameters,
                    }
                    for tool in tools
                ],
            }
        else:
            logger.warning("mcp_server_connection_failed", server_name=server_name)
            return {
                "status": "error",
                "tools": [],
                "error": "Connection failed",
            }

    async def disconnect_server(self, server_name: str) -> dict[str, str]:
        """Disconnect from an MCP server.

        Args:
            server_name: Name of the server to disconnect

        Returns:
            Status message

        Raises:
            ValueError: If server not found

        Example:
            >>> result = await registry.disconnect_server("bash-tools")
            >>> result["status"]
            'disconnected'
        """
        if server_name not in self._manager.client.servers:
            raise ValueError(f"Server not found: {server_name}")

        await self._manager.client.disconnect(server_name)

        # Clear health cache
        self._health_cache.pop(server_name, None)

        logger.info("mcp_server_disconnected", server_name=server_name)
        return {"status": "disconnected"}

    async def check_server_health(
        self,
        server_name: str,
    ) -> dict[str, Any]:
        """Check health of a specific MCP server.

        Args:
            server_name: Name of the server to check

        Returns:
            Health status with latency measurement

        Example:
            >>> health = await registry.check_server_health("bash-tools")
            >>> health["status"]
            'healthy'
            >>> health["latency_ms"] < 100
            True
        """
        # Check cache first
        if server_name in self._health_cache:
            cached = self._health_cache[server_name]
            if time.time() - cached["timestamp"] < self._cache_ttl:
                return {
                    "status": cached["status"],
                    "latency_ms": cached["latency_ms"],
                }

        # Perform health check
        start = time.time()

        connection = self._manager.client.connections.get(server_name)
        if not connection:
            return {"status": "unhealthy", "latency_ms": None, "error": "Not connected"}

        # Check connection status
        if connection.status != ServerStatus.CONNECTED:
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "error": f"Status: {connection.status.value}",
            }

        # Measure latency by checking tool list
        try:
            tools = self._manager.get_tools_by_server(server_name)
            latency_ms = int((time.time() - start) * 1000)

            # Cache result
            self._health_cache[server_name] = {
                "status": "healthy",
                "latency_ms": latency_ms,
                "timestamp": time.time(),
            }

            logger.debug(
                "server_health_checked",
                server_name=server_name,
                latency_ms=latency_ms,
                tool_count=len(tools),
            )

            return {"status": "healthy", "latency_ms": latency_ms}

        except Exception as e:
            logger.error("server_health_check_failed", server_name=server_name, error=str(e))
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "error": str(e),
            }

    def list_tools(self, server_name: str | None = None) -> list[dict[str, Any]]:
        """List all available tools across servers or from specific server.

        Args:
            server_name: Optional server filter

        Returns:
            List of tool information dictionaries

        Example:
            >>> tools = registry.list_tools()
            >>> len(tools) >= 2  # bash + python at minimum
            True
            >>> tools = registry.list_tools("bash-tools")
            >>> len(tools)
            1
        """
        if server_name:
            tools = self._manager.get_tools_by_server(server_name)
        else:
            tools = self._manager.get_all_tools()

        return [
            {
                "name": tool.name,
                "server": tool.server,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]

    async def get_registry_health(self) -> dict[str, Any]:
        """Get overall registry health status.

        Returns:
            Health status with server and tool counts

        Example:
            >>> health = await registry.get_registry_health()
            >>> health["status"]
            'healthy'
            >>> health["connected_servers"] >= 2
            True
        """
        health = await self._manager.health_check()
        return health

    def _get_server_by_name(self, server_name: str) -> MCPServer | None:
        """Get server configuration by name.

        Args:
            server_name: Server name to lookup

        Returns:
            MCPServer or None if not found
        """
        return self._manager.client.servers.get(server_name)

    def _get_cached_latency(self, server_name: str) -> int | None:
        """Get cached latency for a server.

        Args:
            server_name: Server name

        Returns:
            Latency in ms or None if not cached
        """
        cached = self._health_cache.get(server_name)
        if cached and time.time() - cached["timestamp"] < self._cache_ttl:
            return cached["latency_ms"]
        return None

    async def shutdown(self) -> None:
        """Shutdown the registry and disconnect all servers.

        This should be called during application shutdown.
        """
        logger.info("shutting_down_mcp_registry")
        await self._manager.disconnect_all()
        self._health_cache.clear()
        self._initialized = False
        logger.info("mcp_registry_shutdown_complete")
