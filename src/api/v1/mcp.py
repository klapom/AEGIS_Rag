"""MCP (Model Context Protocol) API endpoints.

Sprint Context: Sprint 40 (2025-12-08) - Feature 40.2: Tool Discovery & Management

This module provides API endpoints for managing MCP server connections and
executing tools from external MCP servers.

Endpoints:
    GET /api/v1/mcp/servers - List configured MCP servers and their status
    POST /api/v1/mcp/servers/{server_name}/connect - Connect to an MCP server
    POST /api/v1/mcp/servers/{server_name}/disconnect - Disconnect from server
    GET /api/v1/mcp/tools - List all available tools across servers
    GET /api/v1/mcp/tools/{tool_name} - Get details for a specific tool
    POST /api/v1/mcp/tools/{tool_name}/execute - Execute an MCP tool

Security:
    - All endpoints require JWT authentication
    - Tool execution is logged for audit

Example Usage:
    # List servers
    >>> response = requests.get("/api/v1/mcp/servers", headers=auth_headers)
    >>> print(response.json())

    # Connect to filesystem server
    >>> response = requests.post(
    ...     "/api/v1/mcp/servers/filesystem/connect",
    ...     headers=auth_headers
    ... )

    # List available tools
    >>> response = requests.get("/api/v1/mcp/tools", headers=auth_headers)
    >>> tools = response.json()

    # Execute a tool
    >>> response = requests.post(
    ...     "/api/v1/mcp/tools/read_file/execute",
    ...     json={"arguments": {"path": "/data/report.txt"}},
    ...     headers=auth_headers
    ... )

See Also:
    - src/components/mcp/client.py: MCP client implementation
    - src/components/mcp/connection_manager.py: Connection management
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.components.mcp import (
    ConnectionManager,
    MCPServer,
    MCPToolCall,
    ServerStatus,
    TransportType,
)
from src.core.auth import User

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP"])
logger = structlog.get_logger(__name__)

# Global connection manager instance
# This is initialized on first request and persists for the application lifetime
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the global MCP connection manager.

    Sprint 107 Feature 107.1: Enabled auto_connect_on_init for config loading.

    Returns:
        ConnectionManager instance

    Note:
        This uses a module-level singleton pattern to ensure only one
        connection manager exists for the application lifetime.
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager(
            auto_reconnect=True,
            reconnect_interval=30,
            max_reconnect_attempts=5,
            auto_connect_on_init=True,  # Sprint 107 Feature 107.1
        )
        logger.info("mcp_manager_initialized", config_loaded=True)
    return _connection_manager


# Pydantic models for API requests/responses


class MCPToolSummary(BaseModel):
    """Lightweight tool info embedded in server responses.

    Attributes:
        name: Tool name
        description: Tool description
        parameters: JSON Schema for tool parameters
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class MCPServerInfo(BaseModel):
    """MCP server information for API responses.

    Attributes:
        name: Server name
        transport: Transport type (stdio/http)
        endpoint: Connection endpoint
        description: Server description
        status: Connection status
        tool_count: Number of available tools
        tools: List of tool summaries (Sprint 120)
        connection_time: When connected (ISO format)
        error: Last error message if any
    """

    name: str
    transport: str
    endpoint: str
    description: str
    status: str
    tool_count: int = 0
    tools: list[MCPToolSummary] = Field(default_factory=list)
    connection_time: str | None = None
    error: str | None = None


class MCPToolInfo(BaseModel):
    """MCP tool information for API responses.

    Attributes:
        name: Tool name
        description: Tool description
        server: Server providing this tool
        version: Tool version
        parameters: JSON schema for tool parameters
    """

    name: str
    description: str
    server: str
    version: str = "1.0.0"
    parameters: dict[str, Any] = Field(default_factory=dict)


class ServerConnectRequest(BaseModel):
    """Request to connect to an MCP server.

    Attributes:
        transport: Transport type (stdio or http)
        endpoint: Connection endpoint (command for stdio, URL for http)
        description: Optional server description
        timeout: Connection timeout in seconds
    """

    transport: str = Field(..., description="Transport type: stdio or http")
    endpoint: str = Field(..., description="Connection endpoint")
    description: str = Field(default="", description="Server description")
    timeout: int = Field(default=30, description="Timeout in seconds", ge=1, le=300)


class ServerConnectResponse(BaseModel):
    """Response after connecting to a server.

    Attributes:
        success: Whether connection succeeded
        server_name: Name of the server
        status: Connection status
        tool_count: Number of discovered tools
        error: Error message if failed
    """

    success: bool
    server_name: str
    status: str
    tool_count: int = 0
    error: str | None = None


class ToolExecuteRequest(BaseModel):
    """Request to execute an MCP tool.

    Attributes:
        arguments: Tool arguments as key-value pairs
        timeout: Execution timeout in seconds
    """

    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    timeout: int = Field(default=60, description="Timeout in seconds", ge=1, le=300)


class ToolExecuteResponse(BaseModel):
    """Response from tool execution.

    Attributes:
        success: Whether execution succeeded
        tool_name: Name of the executed tool
        result: Tool result data
        error: Error message if failed
        execution_time: Execution duration in seconds
    """

    success: bool
    tool_name: str
    result: Any | None = None
    error: str | None = None
    execution_time: float = 0.0


# API Endpoints


@router.get("/servers", response_model=list[MCPServerInfo])
async def list_mcp_servers() -> list[MCPServerInfo]:
    """List all configured MCP servers and their connection status.

    Sprint 112 Feature 112.8.4: Made public for admin UI access.

    Returns:
        list of MCP server information

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/mcp/servers"
        ```
    """
    manager = get_connection_manager()
    connections = manager.get_connection_details()

    logger.info("mcp_servers_listed", count=len(connections))

    return [
        MCPServerInfo(
            name=conn.server.name,
            transport=conn.server.transport.value,
            endpoint=conn.server.endpoint,
            description=conn.server.description,
            status=conn.status.value,
            tool_count=len(conn.tools),
            tools=[
                MCPToolSummary(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.parameters,
                )
                for tool in conn.tools
            ],
            connection_time=conn.connection_time,
            error=conn.error,
        )
        for conn in connections
    ]


@router.post("/servers/{server_name}/connect", response_model=ServerConnectResponse)
async def connect_server(
    server_name: str,
    request: ServerConnectRequest | None = None,
    current_user: User = Depends(get_current_user),
) -> ServerConnectResponse:
    """Connect to an MCP server.

    Sprint 120: Request body is optional for reconnecting already-registered servers.
    If the server is already in ConnectionManager, just reconnect it.
    If not, a request body with transport and endpoint is required.

    Args:
        server_name: Unique name for the server
        request: Connection configuration (optional for reconnect)

    Returns:
        Connection result with tool count

    Raises:
        HTTPException: 400 if invalid transport type
        HTTPException: 404 if server not found and no request body
        HTTPException: 500 if connection fails

    Example:
        ```bash
        # Reconnect an already-registered server (no body needed)
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/servers/filesystem-server/connect"

        # Connect a new server (body required)
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"transport": "stdio", "endpoint": "npx @modelcontextprotocol/server-filesystem /data"}' \\
             "http://localhost:8000/api/v1/mcp/servers/filesystem/connect"
        ```
    """
    manager = get_connection_manager()

    # Sprint 120: Check if server is already registered (reconnect case)
    existing_conn = manager.client.connections.get(server_name)

    if existing_conn:
        # Reconnect existing server using stored configuration
        server = existing_conn.server
        logger.info(
            "mcp_server_reconnect_requested",
            user_id=current_user.user_id,
            server_name=server_name,
            transport=server.transport.value,
        )
    elif request:
        # New server — create from request body
        logger.info(
            "mcp_server_connect_requested",
            user_id=current_user.user_id,
            server_name=server_name,
            transport=request.transport,
        )

        # Validate transport type
        try:
            transport = TransportType(request.transport.lower())
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transport type: {request.transport}. Must be 'stdio' or 'http'",
            ) from e

        server = MCPServer(
            name=server_name,
            transport=transport,
            endpoint=request.endpoint,
            description=request.description,
            timeout=request.timeout,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server '{server_name}' not found. Provide transport and endpoint to create it.",
        )

    # Connect to server
    try:
        results = await manager.connect_all([server])
        success = results.get(server_name, False)

        if success:
            # Get tool count
            tools = manager.get_tools_by_server(server_name)
            logger.info(
                "mcp_server_connected",
                user_id=current_user.user_id,
                server_name=server_name,
                tool_count=len(tools),
            )

            return ServerConnectResponse(
                success=True,
                server_name=server_name,
                status=ServerStatus.CONNECTED.value,
                tool_count=len(tools),
            )
        else:
            logger.warning(
                "mcp_server_connection_failed",
                user_id=current_user.user_id,
                server_name=server_name,
            )
            return ServerConnectResponse(
                success=False,
                server_name=server_name,
                status=ServerStatus.ERROR.value,
                error="Connection failed",
            )

    except Exception as e:
        logger.error(
            "mcp_server_connection_error",
            user_id=current_user.user_id,
            server_name=server_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to server: {str(e)}",
        ) from e


@router.post("/servers/{server_name}/disconnect")
async def disconnect_server(
    server_name: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Disconnect from an MCP server.

    Args:
        server_name: Name of the server to disconnect

    Returns:
        Status message

    Raises:
        HTTPException: 404 if server not found

    Example:
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/servers/filesystem/disconnect"
        ```
    """
    manager = get_connection_manager()

    # Sprint 120: Check connections (not servers — servers only has connected ones)
    if server_name not in manager.client.connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    try:
        await manager.client.disconnect(server_name)
        logger.info(
            "mcp_server_disconnected",
            user_id=current_user.user_id,
            server_name=server_name,
        )
        return {"status": "success", "message": f"Disconnected from {server_name}"}

    except Exception as e:
        logger.error(
            "mcp_server_disconnect_error",
            user_id=current_user.user_id,
            server_name=server_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}",
        ) from e


@router.get("/tools", response_model=list[MCPToolInfo])
async def list_all_tools(
    server_name: str | None = None,
) -> list[MCPToolInfo]:
    """List all available tools across connected servers.

    Sprint 112 Feature 112.8.4: Made public for admin UI access.

    Args:
        server_name: Optional filter by server name

    Returns:
        list of available tools

    Example:
        ```bash
        # All tools
        curl "http://localhost:8000/api/v1/mcp/tools"

        # Tools from specific server
        curl "http://localhost:8000/api/v1/mcp/tools?server_name=filesystem"
        ```
    """
    manager = get_connection_manager()

    if server_name:
        # Check if server exists
        if server_name not in manager.client.servers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server not found: {server_name}",
            )
        tools = manager.get_tools_by_server(server_name)
    else:
        tools = manager.get_all_tools()

    logger.info(
        "mcp_tools_listed",
        server_name=server_name,
        count=len(tools),
    )

    return [
        MCPToolInfo(
            name=tool.name,
            description=tool.description,
            server=tool.server,
            version=tool.version,
            parameters=tool.parameters,
        )
        for tool in tools
    ]


@router.get("/tools/{tool_name}", response_model=MCPToolInfo)
async def get_tool_details(
    tool_name: str,
    current_user: User = Depends(get_current_user),
) -> MCPToolInfo:
    """Get details for a specific tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Tool information

    Raises:
        HTTPException: 404 if tool not found

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/mcp/tools/read_file"
        ```
    """
    manager = get_connection_manager()
    tool = manager.client.get_tool(tool_name)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    logger.info(
        "mcp_tool_details_retrieved",
        user_id=current_user.user_id,
        tool_name=tool_name,
        server=tool.server,
    )

    return MCPToolInfo(
        name=tool.name,
        description=tool.description,
        server=tool.server,
        version=tool.version,
        parameters=tool.parameters,
    )


@router.post("/tools/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
) -> ToolExecuteResponse:
    """Execute an MCP tool.

    Args:
        tool_name: Name of the tool to execute
        request: Tool execution parameters

    Returns:
        Tool execution result

    Raises:
        HTTPException: 404 if tool not found
        HTTPException: 500 if execution fails

    Example:
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"arguments": {"path": "/data/report.txt"}, "timeout": 30}' \\
             "http://localhost:8000/api/v1/mcp/tools/read_file/execute"
        ```
    """
    manager = get_connection_manager()

    # Check if tool exists
    tool = manager.client.get_tool(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    logger.info(
        "mcp_tool_execution_started",
        user_id=current_user.user_id,
        tool_name=tool_name,
        server=tool.server,
        arguments=request.arguments,
    )

    # Create tool call
    tool_call = MCPToolCall(
        tool_name=tool_name,
        arguments=request.arguments,
        timeout=request.timeout,
    )

    # Execute tool
    try:
        result = await manager.client.execute_tool(tool_call)

        logger.info(
            "mcp_tool_execution_completed",
            user_id=current_user.user_id,
            tool_name=tool_name,
            success=result.success,
            execution_time=result.execution_time,
        )

        return ToolExecuteResponse(
            success=result.success,
            tool_name=result.tool_name,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
        )

    except Exception as e:
        logger.error(
            "mcp_tool_execution_error",
            user_id=current_user.user_id,
            tool_name=tool_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        ) from e


@router.get("/servers/{server_name}/health")
async def check_server_health(
    server_name: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Health check for a specific MCP server.

    Args:
        server_name: Name of the server to check

    Returns:
        Health status with latency measurement

    Raises:
        HTTPException: 404 if server not found

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/servers/bash-tools/health"
        ```
    """
    manager = get_connection_manager()

    # Check if server exists
    if server_name not in manager.client.servers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Server not found: {server_name}",
        )

    # Get connection status
    connection = manager.client.connections.get(server_name)
    if not connection:
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "error": "Not connected",
        }

    # Check if connected
    if connection.status != ServerStatus.CONNECTED:
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "error": f"Status: {connection.status.value}",
        }

    # Measure latency by listing tools
    import time

    start = time.time()
    try:
        tools = manager.get_tools_by_server(server_name)
        latency_ms = int((time.time() - start) * 1000)

        logger.info(
            "mcp_server_health_checked",
            user_id=current_user.user_id,
            server_name=server_name,
            latency_ms=latency_ms,
        )

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
        }

    except Exception as e:
        logger.error(
            "mcp_server_health_check_failed",
            user_id=current_user.user_id,
            server_name=server_name,
            error=str(e),
        )
        return {
            "status": "unhealthy",
            "latency_ms": None,
            "error": str(e),
        }


@router.get("/health")
async def mcp_health_check() -> dict[str, Any]:
    """Health check for MCP subsystem.

    Sprint 112 Feature 112.8.4: Made public for admin UI access.
    Health endpoints should be accessible without authentication.

    Returns:
        Health status with server and tool counts

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/mcp/health"
        ```
    """
    manager = get_connection_manager()
    health = await manager.health_check()

    logger.info("mcp_health_checked", status=health["status"])

    return health


@router.post("/reload-config")
async def reload_mcp_config(
    reconnect: bool = True,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Reload MCP server configuration from config file.

    Sprint 107 Feature 107.1: Configuration reload without restart.

    This endpoint reloads the MCP server configuration from config/mcp_servers.yaml
    and optionally reconnects to servers with auto_connect enabled.

    Args:
        reconnect: Whether to reconnect servers after reloading (default: True)

    Returns:
        Reload results with server counts and connection status

    Example:
        ```bash
        # Reload and reconnect
        curl -X POST -H "Authorization: Bearer $TOKEN" \
          "http://localhost:8000/api/v1/mcp/reload-config?reconnect=true"

        # Reload without reconnecting
        curl -X POST -H "Authorization: Bearer $TOKEN" \
          "http://localhost:8000/api/v1/mcp/reload-config?reconnect=false"
        ```
    """
    manager = get_connection_manager()

    try:
        result = await manager.reload_config(reconnect=reconnect)

        logger.info(
            "mcp_config_reloaded",
            user_id=current_user.user_id,
            servers_before=result["servers_before"],
            servers_after=result["servers_after"],
            reconnected=reconnect,
            connected=result.get("connected", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "mcp_config_reload_failed",
            user_id=current_user.user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload MCP configuration: {e}",
        ) from e


# ============================================================================
# Sprint 116 Feature 116.5: MCP Tool Permission Management
# ============================================================================


class ToolPermissionUpdate(BaseModel):
    """Request to update tool permission.

    Attributes:
        enabled: Whether the tool is enabled
    """

    enabled: bool


class ToolConfigUpdate(BaseModel):
    """Request to update tool configuration.

    Attributes:
        config: Tool-specific configuration as key-value pairs
    """

    config: dict[str, Any] = Field(default_factory=dict)


class ToolPermissionResponse(BaseModel):
    """Response with tool permission status.

    Attributes:
        tool_name: Name of the tool
        server_name: Server providing the tool
        enabled: Whether the tool is enabled
        allowed_users: List of user IDs allowed to use this tool (empty = all users)
        config: Tool-specific configuration
    """

    tool_name: str
    server_name: str
    enabled: bool
    allowed_users: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


# Global tool permissions storage (in-memory for MVP, should move to Redis/DB)
_tool_permissions: dict[str, ToolPermissionResponse] = {}


@router.get("/tools/{tool_name}/permissions", response_model=ToolPermissionResponse)
async def get_tool_permissions(
    tool_name: str,
    current_user: User = Depends(get_current_user),
) -> ToolPermissionResponse:
    """Get permission configuration for a specific tool.

    Sprint 116 Feature 116.5: Tool permission management.

    Args:
        tool_name: Name of the tool
        current_user: Authenticated user

    Returns:
        Tool permission configuration

    Raises:
        HTTPException: 404 if tool not found

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/tools/read_file/permissions"
        ```
    """
    manager = get_connection_manager()
    tool = manager.client.get_tool(tool_name)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    logger.info(
        "mcp_tool_permissions_retrieved",
        user_id=current_user.user_id,
        tool_name=tool_name,
    )

    # Return existing permissions or default (enabled by default)
    if tool_name in _tool_permissions:
        return _tool_permissions[tool_name]

    return ToolPermissionResponse(
        tool_name=tool_name,
        server_name=tool.server,
        enabled=True,
        allowed_users=[],
        config={},
    )


@router.put("/tools/{tool_name}/permissions", response_model=ToolPermissionResponse)
async def update_tool_permissions(
    tool_name: str,
    update: ToolPermissionUpdate,
    current_user: User = Depends(get_current_user),
) -> ToolPermissionResponse:
    """Enable or disable a specific tool.

    Sprint 116 Feature 116.5: Tool permission management.

    Args:
        tool_name: Name of the tool
        update: Permission update request
        current_user: Authenticated user

    Returns:
        Updated tool permission configuration

    Raises:
        HTTPException: 404 if tool not found

    Example:
        ```bash
        # Disable a tool
        curl -X PUT -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"enabled": false}' \\
             "http://localhost:8000/api/v1/mcp/tools/read_file/permissions"

        # Enable a tool
        curl -X PUT -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"enabled": true}' \\
             "http://localhost:8000/api/v1/mcp/tools/read_file/permissions"
        ```
    """
    manager = get_connection_manager()
    tool = manager.client.get_tool(tool_name)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    # Get existing permissions or create new
    if tool_name in _tool_permissions:
        permissions = _tool_permissions[tool_name]
        permissions.enabled = update.enabled
    else:
        permissions = ToolPermissionResponse(
            tool_name=tool_name,
            server_name=tool.server,
            enabled=update.enabled,
            allowed_users=[],
            config={},
        )
        _tool_permissions[tool_name] = permissions

    logger.info(
        "mcp_tool_permissions_updated",
        user_id=current_user.user_id,
        tool_name=tool_name,
        enabled=update.enabled,
    )

    return permissions


@router.get("/tools/{tool_name}/config")
async def get_tool_config(
    tool_name: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get configuration for a specific tool.

    Sprint 116 Feature 116.5: Tool configuration management.

    Args:
        tool_name: Name of the tool
        current_user: Authenticated user

    Returns:
        Tool configuration as key-value pairs

    Raises:
        HTTPException: 404 if tool not found

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \\
             "http://localhost:8000/api/v1/mcp/tools/read_file/config"
        ```
    """
    manager = get_connection_manager()
    tool = manager.client.get_tool(tool_name)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    logger.info(
        "mcp_tool_config_retrieved",
        user_id=current_user.user_id,
        tool_name=tool_name,
    )

    # Return config from permissions or empty dict
    if tool_name in _tool_permissions:
        return {"config": _tool_permissions[tool_name].config}

    return {"config": {}}


@router.put("/tools/{tool_name}/config")
async def update_tool_config(
    tool_name: str,
    update: ToolConfigUpdate,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update configuration for a specific tool.

    Sprint 116 Feature 116.5: Tool configuration management.

    Args:
        tool_name: Name of the tool
        update: Configuration update request
        current_user: Authenticated user

    Returns:
        Updated configuration

    Raises:
        HTTPException: 404 if tool not found

    Example:
        ```bash
        curl -X PUT -H "Authorization: Bearer $TOKEN" \\
             -H "Content-Type: application/json" \\
             -d '{"config": {"timeout": 60, "max_size": 1024}}' \\
             "http://localhost:8000/api/v1/mcp/tools/read_file/config"
        ```
    """
    manager = get_connection_manager()
    tool = manager.client.get_tool(tool_name)

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    # Get existing permissions or create new
    if tool_name in _tool_permissions:
        permissions = _tool_permissions[tool_name]
        permissions.config = update.config
    else:
        permissions = ToolPermissionResponse(
            tool_name=tool_name,
            server_name=tool.server,
            enabled=True,
            allowed_users=[],
            config=update.config,
        )
        _tool_permissions[tool_name] = permissions

    logger.info(
        "mcp_tool_config_updated",
        user_id=current_user.user_id,
        tool_name=tool_name,
        config_keys=list(update.config.keys()),
    )

    return {"config": permissions.config}
