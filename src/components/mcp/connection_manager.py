"""MCP Connection Manager for handling multiple server connections.

This module provides a high-level manager for handling multiple MCP server
connections, automatic reconnection, and connection pooling.
"""

import asyncio
import logging

from .client import MCPClient, MCPConnectionError
from .models import MCPServer, MCPServerConnection, MCPTool, ServerStatus

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages multiple MCP server connections with automatic reconnection.

    The connection manager handles:
    - Parallel connection to multiple servers
    - Automatic reconnection on failure
    - Connection health monitoring
    - Graceful shutdown
    """

    def __init__(
        self,
        auto_reconnect: bool = True,
        reconnect_interval: int = 30,
        max_reconnect_attempts: int = 5,
    ):
        """Initialize the connection manager.

        Args:
            auto_reconnect: Whether to automatically reconnect on failure
            reconnect_interval: Interval between reconnection attempts (seconds)
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        self.client = MCPClient()
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_tasks: dict[str, asyncio.Task] = {}
        self._shutdown = False

    async def connect_all(self, servers: list[MCPServer]) -> dict[str, bool]:
        """Connect to multiple servers in parallel.

        Args:
            servers: List of server configurations

        Returns:
            Dictionary mapping server name to connection success status
        """
        logger.info(f"Connecting to {len(servers)} MCP servers in parallel")

        # Create connection tasks
        tasks = []
        server_names = []
        for server in servers:
            tasks.append(self._connect_with_retry(server))
            server_names.append(server.name)

        # Wait for all connections
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dictionary
        connection_results = {}
        for server_name, result in zip(server_names, results, strict=False):
            if isinstance(result, Exception):
                logger.error(f"Failed to connect to {server_name}: {result}")
                connection_results[server_name] = False
            else:
                connection_results[server_name] = result

        successful = sum(1 for success in connection_results.values() if success)
        logger.info(f"Connected to {successful}/{len(servers)} servers")

        return connection_results

    async def _connect_with_retry(self, server: MCPServer) -> bool:
        """Connect to a server with retries and auto-reconnect.

        Args:
            server: Server configuration

        Returns:
            True if connection successful
        """
        try:
            success = await self.client.connect(server)

            # Start auto-reconnect monitoring if enabled
            if self.auto_reconnect and success:
                self._start_reconnect_monitor(server)

            return success

        except MCPConnectionError as e:
            logger.error(f"Connection failed for {server.name}: {e}")
            return False

    def _start_reconnect_monitor(self, server: MCPServer) -> None:
        """Start a background task to monitor and reconnect if needed.

        Args:
            server: Server configuration
        """
        if server.name in self._reconnect_tasks:
            # Already monitoring
            return

        task = asyncio.create_task(self._reconnect_monitor(server))
        self._reconnect_tasks[server.name] = task

    async def _reconnect_monitor(self, server: MCPServer) -> None:
        """Monitor connection and reconnect if it fails.

        Args:
            server: Server configuration
        """
        attempt = 0
        while not self._shutdown and attempt < self.max_reconnect_attempts:
            await asyncio.sleep(self.reconnect_interval)

            # Check connection status
            connection = self.client.connections.get(server.name)
            if not connection or connection.status != ServerStatus.CONNECTED:
                logger.warning(f"Connection lost to {server.name}, attempting to reconnect")

                try:
                    # Attempt reconnection
                    await self.client.disconnect(server.name)
                    success = await self.client.connect(server)

                    if success:
                        logger.info(f"Successfully reconnected to {server.name}")
                        attempt = 0  # Reset attempt counter
                    else:
                        attempt += 1
                        logger.warning(
                            f"Reconnection attempt {attempt}/{self.max_reconnect_attempts} "
                            f"failed for {server.name}"
                        )

                except Exception as e:
                    attempt += 1
                    logger.error(f"Reconnection error for {server.name}: {e}")

        if attempt >= self.max_reconnect_attempts:
            logger.error(
                f"Max reconnection attempts reached for {server.name}, giving up"
            )

    async def disconnect_all(self) -> None:
        """Disconnect from all servers gracefully."""
        logger.info("Disconnecting from all MCP servers")

        # Stop reconnection tasks
        self._shutdown = True
        for task in self._reconnect_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._reconnect_tasks.values(), return_exceptions=True)
        self._reconnect_tasks.clear()

        # Disconnect all servers
        await self.client.disconnect_all()

    def get_connection_status(self) -> dict[str, ServerStatus]:
        """Get connection status for all servers.

        Returns:
            Dictionary mapping server name to connection status
        """
        return {
            name: conn.status for name, conn in self.client.connections.items()
        }

    def get_healthy_servers(self) -> list[str]:
        """Get list of currently healthy (connected) servers.

        Returns:
            List of server names
        """
        return [
            name
            for name, conn in self.client.connections.items()
            if conn.status == ServerStatus.CONNECTED
        ]

    def get_all_tools(self) -> list[MCPTool]:
        """Get all tools from all connected servers.

        Returns:
            List of all available tools
        """
        return self.client.list_tools()

    def get_tools_by_server(self, server_name: str) -> list[MCPTool]:
        """Get tools from a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of tools from the server
        """
        return self.client.list_tools(server_name=server_name)

    async def refresh_tools(self, server_name: str | None = None) -> int:
        """Refresh tool discovery for one or all servers.

        Args:
            server_name: Optional specific server to refresh (all if None)

        Returns:
            Total number of tools discovered
        """
        servers = [server_name] if server_name else self.get_healthy_servers()

        total_tools = 0
        for srv in servers:
            try:
                tools = await self.client.discover_tools(srv)
                total_tools += len(tools)
                logger.info(f"Refreshed {len(tools)} tools from {srv}")
            except Exception as e:
                logger.error(f"Failed to refresh tools from {srv}: {e}")

        return total_tools

    def get_connection_details(self) -> list[MCPServerConnection]:
        """Get detailed connection information for all servers.

        Returns:
            List of server connections with details
        """
        return list(self.client.connections.values())

    async def health_check(self) -> dict[str, any]:
        """Perform health check on all connections.

        Returns:
            Health status dictionary
        """
        stats = self.client.get_stats()
        connections = self.get_connection_status()

        healthy_count = sum(
            1 for status in connections.values() if status == ServerStatus.CONNECTED
        )

        return {
            "status": "healthy" if healthy_count > 0 else "unhealthy",
            "total_servers": stats.total_servers,
            "connected_servers": stats.connected_servers,
            "total_tools": stats.total_tools,
            "connections": {
                name: status.value for name, status in connections.items()
            },
            "auto_reconnect": self.auto_reconnect,
        }
