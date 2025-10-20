"""MCP (Model Context Protocol) integration for AEGIS RAG.

This package provides client-side MCP support for connecting to external
MCP servers and accessing their tools.
"""

from .client import MCPClient, MCPClientError, MCPConnectionError, MCPToolError
from .connection_manager import ConnectionManager
from .models import (
    MCPClientStats,
    MCPServer,
    MCPServerConnection,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    ServerStatus,
    TransportType,
)

__all__ = [
    # Client
    "MCPClient",
    "MCPClientError",
    "MCPConnectionError",
    "MCPToolError",
    # Connection Manager
    "ConnectionManager",
    # Models
    "MCPServer",
    "MCPServerConnection",
    "MCPTool",
    "MCPToolCall",
    "MCPToolResult",
    "MCPClientStats",
    "TransportType",
    "ServerStatus",
]
