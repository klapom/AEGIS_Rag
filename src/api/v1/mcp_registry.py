"""MCP Registry API endpoints.

Sprint 107 Feature 107.2: MCP server discovery from public registries.

This module provides API endpoints for:
- Browsing available MCP servers from registries
- Searching servers by name/description/tags
- Installing servers from registry
- Getting server details
"""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user
from src.components.mcp.registry_client import (
    OFFICIAL_REGISTRY,
    MCPRegistryClient,
    get_available_registries,
    get_registry_client,
    get_registry_type,
    resolve_registry_url,
)
from src.core.auth import User

router = APIRouter(prefix="/api/v1/mcp/registry", tags=["MCP Registry"])
logger = structlog.get_logger(__name__)


# Pydantic models for API requests/responses


class ServerDefinitionResponse(BaseModel):
    """MCP server definition from registry.

    Attributes:
        id: Unique server identifier
        name: Human-readable name
        description: Server description
        transport: Transport type (stdio or http)
        command: Command to execute (for stdio)
        args: Command arguments
        url: URL (for http)
        dependencies: Package dependencies
        repository: GitHub repository URL
        version: Latest version
        stars: GitHub stars count
        tags: Tags for categorization
    """

    id: str
    name: str
    description: str
    transport: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    dependencies: dict[str, Any] = Field(default_factory=dict)
    repository: str | None = None
    homepage: str | None = None
    version: str = "1.0.0"
    stars: int = 0
    downloads: int = 0
    tags: list[str] = Field(default_factory=list)


class InstallServerRequest(BaseModel):
    """Request to install a server from registry.

    Attributes:
        server_id: Unique server identifier
        registry: Registry name or URL (default: official registry)
        auto_connect: Whether to auto-connect after installation
    """

    server_id: str = Field(..., description="Unique server identifier")
    registry: str = Field(default="official", description="Registry name or URL")
    auto_connect: bool = Field(default=False, description="Auto-connect after install")


class InstallServerResponse(BaseModel):
    """Response from server installation.

    Attributes:
        status: Installation status (installed, already_installed, error)
        message: Human-readable message
        server: Server definition (if successful)
        dependencies: Dependency installation results
        auto_connect: Whether auto-connect was enabled
    """

    status: str
    message: str
    server: ServerDefinitionResponse | None = None
    dependencies: dict[str, Any] = Field(default_factory=dict)
    auto_connect: bool = False


@router.get("/registries")
async def list_available_registries() -> dict[str, Any]:
    """List all available MCP registries.

    Sprint 112 Feature: Registry selection for MCP Marketplace.

    Returns:
        Dictionary with available registries

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/mcp/registry/registries"
        ```

    Response:
        ```json
        {
          "count": 9,
          "registries": [
            {
              "id": "official",
              "name": "Official MCP Registry",
              "url": "https://registry.modelcontextprotocol.io/v0.1/servers",
              "description": "Official Model Context Protocol server registry",
              "type": "json"
            }
          ]
        }
        ```
    """
    registries = get_available_registries()

    logger.info(
        "mcp_registries_listed",
        count=len(registries),
    )

    return {
        "count": len(registries),
        "registries": registries,
    }


@router.get("/servers")
async def list_registry_servers(
    registry: str = Query(
        default="official",
        description="Registry name (e.g., 'official', 'pulsemcp') or full URL",
    ),
    # Sprint 112: Made public for MCP Marketplace UI
) -> dict[str, Any]:
    """List all available MCP servers from registry.

    Sprint 107 Feature 107.2: Browse available servers.

    Args:
        registry: Registry URL (default: official MCP registry)

    Returns:
        Dictionary with servers list and metadata

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \
          "http://localhost:8000/api/v1/mcp/registry/servers"
        ```

    Response:
        ```json
        {
          "registry": "https://...",
          "count": 25,
          "servers": [
            {
              "id": "@modelcontextprotocol/server-filesystem",
              "name": "Filesystem Server",
              "description": "Read/write files and directories",
              "transport": "stdio",
              "command": "npx",
              "args": ["@modelcontextprotocol/server-filesystem"],
              "stars": 1250,
              "tags": ["filesystem", "files"]
            }
          ]
        }
        ```
    """
    client = get_registry_client()

    try:
        servers = await client.discover_servers(registry)

        # Convert to response format
        server_dicts = [
            ServerDefinitionResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                transport=s.transport,
                command=s.command,
                args=s.args,
                url=s.url,
                dependencies=s.dependencies,
                repository=s.repository,
                homepage=s.homepage,
                version=s.version,
                stars=s.stars,
                downloads=s.downloads,
                tags=s.tags,
            ).model_dump()
            for s in servers
        ]

        logger.info(
            "mcp_registry_servers_listed",
            registry=registry,
            count=len(servers),
        )

        return {
            "registry": registry,
            "count": len(servers),
            "servers": server_dicts,
        }

    except ValueError as e:
        # Sprint 112: Handle non-JSON registries gracefully
        registry_url, registry_type = resolve_registry_url(registry)
        logger.warning(
            "mcp_registry_not_fetchable",
            registry=registry,
            registry_type=registry_type,
            message=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "registry_not_fetchable",
                "message": str(e),
                "registry_type": registry_type,
                "browse_url": registry_url,
            },
        ) from e
    except Exception as e:
        logger.error(
            "mcp_registry_list_failed",
            registry=registry,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch registry servers: {e}",
        ) from e


@router.get("/search")
async def search_registry_servers(
    q: str = Query(..., description="Search query", min_length=1),
    registry: str = Query(
        default="official",
        description="Registry name (e.g., 'official') or full URL",
    ),
    # Sprint 112: Made public for MCP Marketplace UI
) -> dict[str, Any]:
    """Search for MCP servers in registry.

    Sprint 107 Feature 107.2: Search servers by name, description, or tags.

    Args:
        q: Search query
        registry: Registry URL

    Returns:
        Dictionary with search results

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \
          "http://localhost:8000/api/v1/mcp/registry/search?q=filesystem"
        ```
    """
    client = get_registry_client()

    try:
        results = await client.search_servers(q, registry)

        # Convert to response format
        server_dicts = [
            ServerDefinitionResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                transport=s.transport,
                command=s.command,
                args=s.args,
                url=s.url,
                dependencies=s.dependencies,
                repository=s.repository,
                homepage=s.homepage,
                version=s.version,
                stars=s.stars,
                downloads=s.downloads,
                tags=s.tags,
            ).model_dump()
            for s in results
        ]

        logger.info(
            "mcp_registry_search",
            query=q,
            registry=registry,
            results=len(results),
        )

        return {
            "query": q,
            "registry": registry,
            "count": len(results),
            "servers": server_dicts,
        }

    except Exception as e:
        logger.error(
            "mcp_registry_search_failed",
            query=q,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registry search failed: {e}",
        ) from e


@router.get("/servers/{server_id}")
async def get_server_details(
    server_id: str,
    registry: str = Query(
        default="official",
        description="Registry name or URL",
    ),
    # Sprint 112: Made public for MCP Marketplace UI
) -> ServerDefinitionResponse:
    """Get detailed information about a specific server.

    Sprint 107 Feature 107.2: Get server details before installation.

    Args:
        server_id: Unique server identifier
        registry: Registry URL

    Returns:
        Server definition

    Example:
        ```bash
        curl -H "Authorization: Bearer $TOKEN" \
          "http://localhost:8000/api/v1/mcp/registry/servers/@modelcontextprotocol/server-filesystem"
        ```
    """
    client = get_registry_client()

    try:
        server = await client.get_server_details(server_id, registry)

        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server not found: {server_id}",
            )

        logger.info(
            "mcp_registry_server_details",
            server_id=server_id,
        )

        return ServerDefinitionResponse(
            id=server.id,
            name=server.name,
            description=server.description,
            transport=server.transport,
            command=server.command,
            args=server.args,
            url=server.url,
            dependencies=server.dependencies,
            repository=server.repository,
            homepage=server.homepage,
            version=server.version,
            stars=server.stars,
            downloads=server.downloads,
            tags=server.tags,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "mcp_registry_details_failed",
            server_id=server_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get server details: {e}",
        ) from e


@router.post("/install")
async def install_server(
    request: InstallServerRequest,
    current_user: User = Depends(get_current_user),
) -> InstallServerResponse:
    """Install an MCP server from registry.

    Sprint 107 Feature 107.2: One-click server installation.

    This endpoint:
    1. Fetches server definition from registry
    2. Installs dependencies (npm, pip) if needed
    3. Adds server to config/mcp_servers.yaml
    4. Optionally connects to server and discovers tools

    Args:
        request: Installation request

    Returns:
        Installation result

    Example:
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" \
          -d '{
            "server_id": "@modelcontextprotocol/server-filesystem",
            "auto_connect": true
          }' \
          "http://localhost:8000/api/v1/mcp/registry/install"
        ```

    Response:
        ```json
        {
          "status": "installed",
          "message": "Server installed successfully",
          "server": {...},
          "auto_connect": true
        }
        ```

    Note:
        After installation with auto_connect=true, the server will be
        available in GET /api/v1/mcp/servers and its tools will be
        discoverable via GET /api/v1/mcp/tools.
    """
    client = get_registry_client()

    try:
        result = await client.install_server(
            server_id=request.server_id,
            registry=request.registry,
            auto_connect=request.auto_connect,
        )

        logger.info(
            "mcp_server_installed",
            user_id=current_user.user_id,
            server_id=request.server_id,
            status=result["status"],
            auto_connect=request.auto_connect,
        )

        # Convert to response format
        response = InstallServerResponse(
            status=result["status"],
            message=result["message"],
            dependencies=result.get("dependencies", {}),
            auto_connect=result.get("auto_connect", False),
        )

        # Add server details if available
        if "server" in result:
            server_data = result["server"]
            response.server = ServerDefinitionResponse(
                id=server_data["id"],
                name=server_data["name"],
                description=server_data["description"],
                transport=server_data["transport"],
                command=server_data.get("command"),
                args=server_data.get("args", []),
                url=server_data.get("url"),
                dependencies=server_data.get("dependencies", {}),
                repository=server_data.get("repository"),
                homepage=server_data.get("homepage"),
                version=server_data.get("version", "1.0.0"),
                stars=server_data.get("stars", 0),
                downloads=server_data.get("downloads", 0),
                tags=server_data.get("tags", []),
            )

        # If installed with auto_connect, inform about tool discovery
        if result["status"] == "installed" and request.auto_connect:
            response.message += (
                " Server will auto-connect on next startup. "
                "Use POST /api/v1/mcp/reload-config to connect immediately."
            )

        return response

    except Exception as e:
        logger.error(
            "mcp_server_install_failed",
            user_id=current_user.user_id,
            server_id=request.server_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server installation failed: {e}",
        ) from e


class CustomServerRequest(BaseModel):
    """Request to add a custom MCP server.

    Sprint 112 Feature: Direct MCP server input for tool discovery.

    Attributes:
        name: Server name (for identification)
        transport: Transport type (stdio or http)
        command: Command to execute (for stdio)
        args: Command arguments (for stdio)
        url: Server URL (for http)
        description: Optional description
        auto_connect: Whether to connect and discover tools
    """

    name: str = Field(..., description="Server name for identification")
    transport: str = Field(default="stdio", description="Transport type: stdio or http")
    command: str | None = Field(default=None, description="Command to execute (for stdio)")
    args: list[str] = Field(default_factory=list, description="Command arguments (for stdio)")
    url: str | None = Field(default=None, description="Server URL (for http)")
    description: str = Field(default="", description="Optional server description")
    auto_connect: bool = Field(default=True, description="Connect and discover tools")


class CustomServerResponse(BaseModel):
    """Response from adding a custom server.

    Attributes:
        status: Operation status
        message: Human-readable message
        server: Server configuration
        tools: Discovered tools (if auto_connect=true)
    """

    status: str
    message: str
    server: dict[str, Any] = Field(default_factory=dict)
    tools: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/custom")
async def add_custom_server(
    request: CustomServerRequest,
    current_user: User = Depends(get_current_user),
) -> CustomServerResponse:
    """Add a custom MCP server directly (not from registry).

    Sprint 112 Feature: Direct MCP server input for tool discovery.

    This endpoint allows adding an MCP server by providing its configuration
    directly, without fetching from a registry. Useful for:
    - Testing custom/local MCP servers
    - Adding servers not in any registry
    - Quick tool discovery from known servers

    Args:
        request: Custom server configuration

    Returns:
        Server configuration and discovered tools

    Example (stdio):
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{
            "name": "my-filesystem",
            "transport": "stdio",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem", "/path/to/dir"],
            "auto_connect": true
          }' \\
          "http://localhost:8000/api/v1/mcp/registry/custom"
        ```

    Example (http):
        ```bash
        curl -X POST -H "Authorization: Bearer $TOKEN" \\
          -H "Content-Type: application/json" \\
          -d '{
            "name": "remote-server",
            "transport": "http",
            "url": "http://localhost:3000/mcp",
            "auto_connect": true
          }' \\
          "http://localhost:8000/api/v1/mcp/registry/custom"
        ```
    """
    import yaml
    from pathlib import Path

    # Validate request
    if request.transport == "stdio" and not request.command:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command is required for stdio transport",
        )
    if request.transport == "http" and not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required for http transport",
        )

    try:
        # Build server configuration
        server_config = {
            "name": request.name,
            "transport": request.transport,
            "description": request.description or f"Custom server: {request.name}",
            "auto_connect": request.auto_connect,
            "enabled": True,
        }

        if request.transport == "stdio":
            server_config["command"] = request.command
            server_config["args"] = request.args
        else:
            server_config["url"] = request.url

        # Sprint 112 Fix: Write to data directory (writable in Docker)
        # /app/config is read-only, but /app/data is read-write
        config_path = Path(__file__).parents[3] / "data" / "mcp_servers_installed.yaml"

        # Sprint 120: Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            except PermissionError:
                # Bind-mount may have wrong ownership; try atomic recreate
                config = {}
        else:
            config = {}

        if "servers" not in config:
            config["servers"] = []

        # Check if server already exists
        for existing in config["servers"]:
            if existing.get("name") == request.name:
                logger.warning(f"Server already exists: {request.name}")
                return CustomServerResponse(
                    status="already_exists",
                    message=f"Server '{request.name}' already exists in configuration",
                    server=existing,
                    tools=[],
                )

        config["servers"].append(server_config)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(
            "custom_mcp_server_added",
            user_id=current_user.user_id,
            server_name=request.name,
            transport=request.transport,
        )

        # Sprint 120: Register server in ConnectionManager so it appears
        # on /admin/tools immediately (no restart needed)
        discovered_tools: list[dict[str, Any]] = []
        try:
            from src.api.v1.mcp import get_connection_manager
            from src.components.mcp.models import MCPServer, MCPServerConnection, ServerStatus, TransportType

            manager = get_connection_manager()

            # Build MCPServer model from the config
            transport_enum = TransportType(request.transport)
            mcp_server = MCPServer(
                name=request.name,
                transport=transport_enum,
                endpoint=(
                    f"{request.command} {' '.join(request.args or [])}"
                    if request.transport == "stdio"
                    else (request.url or "")
                ),
                description=request.description,
                timeout=30,
            )

            # Register as DISCONNECTED so it shows up immediately
            manager.client.connections[request.name] = MCPServerConnection(
                server=mcp_server,
                status=ServerStatus.DISCONNECTED,
            )

            # Auto-connect if requested
            if request.auto_connect:
                try:
                    results = await manager.connect_all([mcp_server])
                    if results.get(request.name):
                        conn = manager.client.connections.get(request.name)
                        if conn and conn.tools:
                            discovered_tools = [
                                {
                                    "name": t.name,
                                    "description": t.description or "",
                                    "input_schema": getattr(t, "input_schema", {}),
                                }
                                for t in conn.tools
                            ]
                        logger.info(
                            "custom_server_connected",
                            server_name=request.name,
                            tool_count=len(discovered_tools),
                        )
                except Exception as conn_err:
                    logger.warning(
                        "custom_server_auto_connect_failed",
                        server_name=request.name,
                        error=str(conn_err),
                    )
        except Exception as e:
            logger.warning(
                "custom_server_registration_failed",
                server_name=request.name,
                error=str(e),
            )

        return CustomServerResponse(
            status="added",
            message=f"Custom server '{request.name}' added successfully",
            server=server_config,
            tools=discovered_tools,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "custom_server_add_failed",
            user_id=current_user.user_id,
            server_name=request.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add custom server: {e}",
        ) from e
