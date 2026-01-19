"""MCP Registry Client for server discovery and installation.

Sprint 107 Feature 107.2: Auto-Discovery of MCP servers from public registries.

This module provides integration with public MCP server registries for:
- Browsing available servers
- Searching servers by name/description
- Installing servers from registry
- Dependency resolution
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import yaml

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Registry URLs
# Sprint 112 Fix: Updated to new official MCP Registry API with multi-registry support
# Old URL (returns 404): https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/mcp-servers.json
OFFICIAL_REGISTRY = "https://registry.modelcontextprotocol.io/v0.1/servers"
COMMUNITY_REGISTRY = "https://raw.githubusercontent.com/mcpregistry/registry/main/servers.json"

# Sprint 112 Feature: Predefined registry list for MCP Marketplace
# Users can select from these registries in the MCP Marketplace UI
PREDEFINED_REGISTRIES: dict[str, dict[str, str]] = {
    "official": {
        "name": "Official MCP Registry",
        "url": "https://registry.modelcontextprotocol.io/v0.1/servers",
        "description": "Official Model Context Protocol server registry",
        "type": "json",
    },
    "official_v1": {
        "name": "Official MCP Registry (v1)",
        "url": "https://registry.modelcontextprotocol.io/v1/servers",
        "description": "Official MCP Registry v1 API",
        "type": "json",
    },
    "pulsemcp": {
        "name": "PulseMCP",
        "url": "https://www.pulsemcp.com/servers",
        "description": "Community-driven MCP server directory",
        "type": "html",
    },
    "glama": {
        "name": "Glama.ai MCP Servers",
        "url": "https://glama.ai/mcp/servers",
        "description": "Glama.ai's curated MCP server list",
        "type": "html",
    },
    "mcpservers": {
        "name": "MCPServers.org",
        "url": "https://mcpservers.org",
        "description": "Community MCP server directory",
        "type": "html",
    },
    "mastra": {
        "name": "Mastra MCP Registry",
        "url": "https://mastra.ai/mcp-registry-registry",
        "description": "Mastra's MCP registry aggregator",
        "type": "html",
    },
    "github_mcp": {
        "name": "GitHub MCP Servers",
        "url": "https://github.com/modelcontextprotocol/servers",
        "description": "Official GitHub repository for MCP servers",
        "type": "github",
    },
    "github_registry": {
        "name": "GitHub MCP Registry",
        "url": "https://github.com/modelcontextprotocol/registry",
        "description": "Official MCP Registry GitHub repository",
        "type": "github",
    },
    "microsoft_mcp": {
        "name": "Microsoft MCP",
        "url": "https://github.com/microsoft/mcp",
        "description": "Microsoft's MCP implementations",
        "type": "github",
    },
}


def resolve_registry_url(registry: str) -> str:
    """Resolve registry name or URL to full URL.

    Sprint 112 Feature: Support both named registries and direct URLs.

    Args:
        registry: Registry name (e.g., "official") or full URL

    Returns:
        Full registry URL

    Example:
        >>> resolve_registry_url("official")
        'https://registry.modelcontextprotocol.io/v0.1/servers'
        >>> resolve_registry_url("https://custom.registry/servers")
        'https://custom.registry/servers'
    """
    # If already a URL, return as-is
    if registry.startswith("http://") or registry.startswith("https://"):
        return registry

    # Look up in predefined registries
    registry_lower = registry.lower()
    if registry_lower in PREDEFINED_REGISTRIES:
        return PREDEFINED_REGISTRIES[registry_lower]["url"]

    # Default to official registry if unknown
    logger.warning(f"Unknown registry '{registry}', defaulting to official")
    return OFFICIAL_REGISTRY


def get_available_registries() -> list[dict[str, str]]:
    """Get list of all available predefined registries.

    Sprint 112 Feature: Registry selection for MCP Marketplace.

    Returns:
        List of registry info dictionaries with id, name, url, description, type

    Example:
        >>> registries = get_available_registries()
        >>> for reg in registries:
        ...     print(f"{reg['name']}: {reg['url']}")
    """
    return [
        {"id": key, **value}
        for key, value in PREDEFINED_REGISTRIES.items()
    ]


@dataclass
class MCPServerDefinition:
    """Definition of an MCP server from a registry.

    Attributes:
        id: Unique server identifier (e.g., "@modelcontextprotocol/server-filesystem")
        name: Human-readable name
        description: Server description
        transport: Transport type (stdio or http)
        command: Command to execute (for stdio)
        args: Command arguments (for stdio)
        url: URL template (for http)
        dependencies: Package dependencies (npm, pip, etc.)
        repository: GitHub repository URL
        homepage: Homepage URL
        version: Latest version
        stars: GitHub stars count
        downloads: Download count (if available)
        tags: Tags for categorization
        metadata: Additional metadata
    """

    id: str
    name: str
    description: str
    transport: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None
    dependencies: dict[str, Any] = field(default_factory=dict)
    repository: str | None = None
    homepage: str | None = None
    version: str = "1.0.0"
    stars: int = 0
    downloads: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPRegistryClient:
    """Client for fetching MCP server definitions from registries.

    Sprint 107 Feature 107.2: Registry integration for server discovery.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        cache_ttl_seconds: int = 3600,
    ):
        """Initialize registry client.

        Args:
            cache_dir: Directory for caching registry data (default: .cache/mcp_registry)
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        if cache_dir is None:
            self.cache_dir = Path.home() / ".cache" / "mcp_registry"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def discover_servers(
        self, registry: str = "official"
    ) -> list[MCPServerDefinition]:
        """Fetch available servers from registry.

        Sprint 112 Fix: Accepts both registry names ("official") and full URLs.

        Args:
            registry: Registry name (e.g., "official", "pulsemcp") or full URL

        Returns:
            List of server definitions

        Example:
            >>> client = MCPRegistryClient()
            >>> servers = await client.discover_servers("official")
            >>> print(f"Found {len(servers)} servers")
        """
        # Resolve registry name to URL
        registry_url = resolve_registry_url(registry)
        logger.info(f"Fetching servers from registry: {registry_url}")

        # Check cache first
        cache_key = self._get_cache_key(registry_url)
        cached = self._read_cache(cache_key)
        if cached:
            logger.info(f"Using cached registry data (key: {cache_key[:8]}...)")
            return [MCPServerDefinition(**server) for server in cached]

        # Fetch from registry
        try:
            response = await self._http_client.get(registry_url)
            response.raise_for_status()
            data = response.json()

            # Parse server definitions
            # Sprint 112 Fix: Handle new nested JSON structure
            # New format: {"servers": [{"server": {...}}, ...]}
            # Old format: {"servers": [{...}, ...]}
            servers = []
            for item in data.get("servers", []):
                # Check if new nested format or old flat format
                if "server" in item:
                    # New nested format from registry.modelcontextprotocol.io
                    server_data = item["server"]
                else:
                    # Old flat format or community registries
                    server_data = item
                servers.append(self._parse_server_definition(server_data))

            # Sprint 112 Fix: Deduplicate servers - keep only latest version
            servers = self._deduplicate_servers(servers)

            # Cache results
            self._write_cache(cache_key, [self._server_to_dict(s) for s in servers])

            logger.info(f"Discovered {len(servers)} servers from registry")
            return servers

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch registry: {e}")
            return []

    async def search_servers(
        self, query: str, registry: str = "official"
    ) -> list[MCPServerDefinition]:
        """Search registries for servers matching query.

        Sprint 112 Fix: Accepts both registry names and full URLs.

        Args:
            query: Search query (name, description, tags)
            registry: Registry name or URL to search

        Returns:
            List of matching server definitions

        Example:
            >>> client = MCPRegistryClient()
            >>> results = await client.search_servers("filesystem")
            >>> for server in results:
            ...     print(f"{server.name}: {server.description}")
        """
        all_servers = await self.discover_servers(registry)

        query_lower = query.lower()
        results = []

        for server in all_servers:
            # Search in name, description, tags, and id
            if (
                query_lower in server.name.lower()
                or query_lower in server.description.lower()
                or query_lower in server.id.lower()
                or any(query_lower in tag.lower() for tag in server.tags)
            ):
                results.append(server)

        logger.info(f"Search '{query}' found {len(results)} servers")
        return results

    async def get_server_details(
        self, server_id: str, registry: str = "official"
    ) -> MCPServerDefinition | None:
        """Get detailed information about a specific server.

        Sprint 112 Fix: Accepts both registry names and full URLs.

        Args:
            server_id: Unique server identifier
            registry: Registry name or URL

        Returns:
            Server definition or None if not found
        """
        servers = await self.discover_servers(registry)

        for server in servers:
            if server.id == server_id:
                return server

        logger.warning(f"Server not found in registry: {server_id}")
        return None

    async def install_server(
        self,
        server_id: str,
        registry: str = "official",
        config_path: Path | None = None,
        auto_connect: bool = False,
    ) -> dict[str, Any]:
        """Install server from registry.

        This method:
        1. Fetches server definition from registry
        2. Installs dependencies (npm, pip) if needed
        3. Adds server to config/mcp_servers.yaml
        4. Optionally connects to server

        Args:
            server_id: Unique server identifier
            registry: Registry URL
            config_path: Path to mcp_servers.yaml (default: config/mcp_servers.yaml)
            auto_connect: Whether to auto-connect after installation

        Returns:
            Installation result dictionary

        Example:
            >>> client = MCPRegistryClient()
            >>> result = await client.install_server(
            ...     "@modelcontextprotocol/server-filesystem",
            ...     auto_connect=True
            ... )
            >>> print(result["status"])  # "installed"
        """
        logger.info(f"Installing MCP server: {server_id}")

        # Get server definition
        server_def = await self.get_server_details(server_id, registry)
        if not server_def:
            return {
                "status": "error",
                "message": f"Server not found in registry: {server_id}",
            }

        # Check if already installed
        if config_path is None:
            config_path = Path(__file__).parents[3] / "config" / "mcp_servers.yaml"

        if self._is_server_installed(server_id, config_path):
            logger.warning(f"Server already installed: {server_id}")
            return {
                "status": "already_installed",
                "message": f"Server {server_id} is already installed",
                "server": self._server_to_dict(server_def),
            }

        # Install dependencies (if any)
        dependency_results = await self._install_dependencies(server_def)

        # Add to configuration
        success = self._add_to_config(server_def, config_path, auto_connect)

        if success:
            logger.info(f"Successfully installed server: {server_id}")
            return {
                "status": "installed",
                "message": f"Server {server_id} installed successfully",
                "server": self._server_to_dict(server_def),
                "dependencies": dependency_results,
                "auto_connect": auto_connect,
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to add server to configuration",
            }

    def _parse_server_definition(self, data: dict[str, Any]) -> MCPServerDefinition:
        """Parse server definition from registry data.

        Sprint 112 Fix: Handle new MCP Registry API structure.

        New format from registry.modelcontextprotocol.io:
        {
            "name": "org/project",
            "description": "...",
            "packages": [
                {"registryType": "npm", "identifier": "@org/package"}
            ],
            "homepage": "...",
            "repository": {"type": "github", "url": "..."}
        }

        Args:
            data: Raw server data from registry

        Returns:
            MCPServerDefinition instance
        """
        # Extract server name (used as ID)
        server_name = data.get("name", data.get("id", "unknown"))

        # Extract package info for command/args
        packages = data.get("packages", [])
        npm_package = None
        pip_package = None
        for pkg in packages:
            if pkg.get("registryType") == "npm":
                npm_package = pkg.get("identifier")
            elif pkg.get("registryType") == "pip" or pkg.get("registryType") == "pypi":
                pip_package = pkg.get("identifier")

        # Determine command and args based on package type
        command = data.get("command")
        args = data.get("args", [])
        if not command and npm_package:
            command = "npx"
            args = [npm_package]
        elif not command and pip_package:
            command = "python"
            args = ["-m", pip_package]

        # Extract repository URL (handles both old and new format)
        repository = data.get("repository")
        if isinstance(repository, dict):
            repository = repository.get("url", "")

        # Build dependencies from packages
        dependencies = data.get("dependencies", {})
        if npm_package and "npm" not in dependencies:
            dependencies["npm"] = [npm_package]
        if pip_package and "pip" not in dependencies:
            dependencies["pip"] = [pip_package]

        return MCPServerDefinition(
            id=server_name,
            name=data.get("displayName", server_name.split("/")[-1] if "/" in server_name else server_name),
            description=data.get("description", ""),
            transport=data.get("transport", "stdio"),
            command=command,
            args=args,
            url=data.get("url"),
            dependencies=dependencies,
            repository=repository,
            homepage=data.get("homepage"),
            version=data.get("version", "1.0.0"),
            stars=data.get("stars", 0),
            downloads=data.get("downloads", 0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def _deduplicate_servers(
        self, servers: list[MCPServerDefinition]
    ) -> list[MCPServerDefinition]:
        """Deduplicate servers - keep only the latest version of each server.

        Sprint 112 Fix: Registry returns all versions of each server.
        Users expect to see only the latest version.

        Args:
            servers: List of all server definitions (may contain duplicates)

        Returns:
            List of unique servers with only latest version of each
        """
        from packaging import version as pkg_version

        # Group by server ID
        servers_by_id: dict[str, list[MCPServerDefinition]] = {}
        for server in servers:
            if server.id not in servers_by_id:
                servers_by_id[server.id] = []
            servers_by_id[server.id].append(server)

        # Keep only the latest version of each server
        latest_servers = []
        for server_id, versions in servers_by_id.items():
            if len(versions) == 1:
                latest_servers.append(versions[0])
            else:
                # Sort by version (descending) and take the first one
                try:
                    sorted_versions = sorted(
                        versions,
                        key=lambda s: pkg_version.parse(s.version),
                        reverse=True,
                    )
                    latest_servers.append(sorted_versions[0])
                    logger.debug(
                        f"Deduplicated {server_id}: kept {sorted_versions[0].version} "
                        f"from {len(versions)} versions"
                    )
                except Exception as e:
                    # If version parsing fails, just take the last one
                    logger.warning(f"Version parsing failed for {server_id}: {e}")
                    latest_servers.append(versions[-1])

        logger.info(
            f"Deduplicated servers: {len(servers)} → {len(latest_servers)} unique"
        )
        return latest_servers

    def _server_to_dict(self, server: MCPServerDefinition) -> dict[str, Any]:
        """Convert server definition to dictionary.

        Args:
            server: Server definition

        Returns:
            Dictionary representation
        """
        return {
            "id": server.id,
            "name": server.name,
            "description": server.description,
            "transport": server.transport,
            "command": server.command,
            "args": server.args,
            "url": server.url,
            "dependencies": server.dependencies,
            "repository": server.repository,
            "homepage": server.homepage,
            "version": server.version,
            "stars": server.stars,
            "downloads": server.downloads,
            "tags": server.tags,
            "metadata": server.metadata,
        }

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL.

        Args:
            url: Registry URL

        Returns:
            Cache key (SHA256 hash)
        """
        return hashlib.sha256(url.encode()).hexdigest()

    def _read_cache(self, cache_key: str) -> list[dict[str, Any]] | None:
        """Read cached registry data.

        Args:
            cache_key: Cache key

        Returns:
            Cached data or None if expired/missing
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        # Check if cache is expired
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime, tz=UTC)
        if datetime.now(UTC) - mtime > self.cache_ttl:
            logger.debug(f"Cache expired: {cache_key[:8]}...")
            cache_file.unlink()
            return None

        # Read cache
        try:
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
            return None

    def _write_cache(self, cache_key: str, data: list[dict[str, Any]]) -> None:
        """Write data to cache.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Wrote cache: {cache_key[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def _is_server_installed(self, server_id: str, config_path: Path) -> bool:
        """Check if server is already installed in config.

        Args:
            server_id: Server identifier
            config_path: Path to config file

        Returns:
            True if already installed
        """
        if not config_path.exists():
            return False

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            servers = config.get("servers", [])
            for server in servers:
                # Check by name or command (for npm packages)
                if server.get("name") == server_id:
                    return True
                if server_id in str(server.get("command", "")):
                    return True
                if server_id in " ".join(server.get("args", [])):
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to check installed servers: {e}")
            return False

    def _add_to_config(
        self, server: MCPServerDefinition, config_path: Path, auto_connect: bool
    ) -> bool:
        """Add server to configuration file.

        Args:
            server: Server definition
            config_path: Path to config file
            auto_connect: Whether to enable auto-connect

        Returns:
            True if successful
        """
        try:
            # Load existing config
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}

            # Ensure servers list exists
            if "servers" not in config:
                config["servers"] = []

            # Build server config
            server_config = {
                "name": server.id.replace("@", "").replace("/", "-"),
                "transport": server.transport,
                "description": server.description,
                "auto_connect": auto_connect,
                "enabled": True,
            }

            if server.transport == "stdio":
                server_config["command"] = server.command or "npx"
                # If server.id is npm package, use it in args
                if server.command is None or "npx" in str(server.command):
                    server_config["args"] = [server.id]
                else:
                    server_config["args"] = server.args
            else:
                server_config["url"] = server.url

            # Add dependencies if any
            if server.dependencies:
                server_config["dependencies"] = server.dependencies

            # Append to servers
            config["servers"].append(server_config)

            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Added server to config: {server.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add server to config: {e}")
            return False

    async def _install_dependencies(
        self, server: MCPServerDefinition
    ) -> dict[str, Any]:
        """Install server dependencies (npm, pip, etc.).

        Sprint 107 Feature 107.4: Automatic dependency installation.

        Args:
            server: Server definition

        Returns:
            Dictionary with installation results
        """
        results = {"npm": [], "pip": [], "env": [], "errors": []}

        if not server.dependencies:
            return results

        # Check environment variables
        env_vars = server.dependencies.get("env", [])
        if env_vars:
            import os

            for var in env_vars:
                if os.getenv(var):
                    results["env"].append({"variable": var, "status": "found"})
                else:
                    results["env"].append({"variable": var, "status": "missing"})
                    results["errors"].append({
                        "type": "env",
                        "variable": var,
                        "error": f"Environment variable {var} is not set"
                    })

        # Install npm packages
        npm_packages = server.dependencies.get("npm", [])
        if npm_packages:
            for package in npm_packages:
                try:
                    logger.info(f"Installing npm package: {package}")

                    # Check if npm is available
                    npm_check = await asyncio.create_subprocess_exec(
                        "npm", "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await npm_check.communicate()

                    if npm_check.returncode != 0:
                        logger.warning("npm not available, skipping package installation")
                        results["npm"].append({"package": package, "status": "skipped_no_npm"})
                        continue

                    # Install package globally
                    process = await asyncio.create_subprocess_exec(
                        "npm", "install", "-g", package,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode == 0:
                        logger.info(f"Successfully installed npm package: {package}")
                        results["npm"].append({"package": package, "status": "installed"})
                    else:
                        error_msg = stderr.decode() if stderr else "Unknown error"
                        logger.error(f"Failed to install npm package {package}: {error_msg}")
                        results["npm"].append({"package": package, "status": "failed"})
                        results["errors"].append({
                            "type": "npm",
                            "package": package,
                            "error": error_msg
                        })

                except Exception as e:
                    logger.error(f"Failed to install npm package {package}: {e}")
                    results["npm"].append({"package": package, "status": "error"})
                    results["errors"].append({
                        "type": "npm",
                        "package": package,
                        "error": str(e)
                    })

        # Install pip packages
        pip_packages = server.dependencies.get("pip", [])
        if pip_packages:
            for package in pip_packages:
                try:
                    logger.info(f"Installing pip package: {package}")

                    # Install package
                    process = await asyncio.create_subprocess_exec(
                        "pip", "install", package,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode == 0:
                        logger.info(f"Successfully installed pip package: {package}")
                        results["pip"].append({"package": package, "status": "installed"})
                    else:
                        error_msg = stderr.decode() if stderr else "Unknown error"
                        logger.error(f"Failed to install pip package {package}: {error_msg}")
                        results["pip"].append({"package": package, "status": "failed"})
                        results["errors"].append({
                            "type": "pip",
                            "package": package,
                            "error": error_msg
                        })

                except Exception as e:
                    logger.error(f"Failed to install pip package {package}: {e}")
                    results["pip"].append({"package": package, "status": "error"})
                    results["errors"].append({
                        "type": "pip",
                        "package": package,
                        "error": str(e)
                    })

        return results

    async def close(self) -> None:
        """Close HTTP client."""
        await self._http_client.aclose()


# Singleton instance
_client: MCPRegistryClient | None = None


def get_registry_client() -> MCPRegistryClient:
    """Get singleton registry client instance.

    Returns:
        MCPRegistryClient instance
    """
    global _client
    if _client is None:
        _client = MCPRegistryClient()
    return _client
