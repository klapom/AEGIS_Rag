"""Tool Registry for LLM Tool Use.

Sprint 59 Feature 59.2: Central registry for available tools.

This module provides a centralized registry for LLM-callable tools with:
- Decorator-based tool registration
- OpenAI-compatible function calling schemas
- Tool metadata and parameter definitions
- Support for sandboxed and non-sandboxed tools

Architecture:
    - ToolDefinition: Dataclass for tool metadata
    - ToolRegistry: Class-level registry with decorator pattern
    - Automatic schema generation for LLM providers

Usage:
    >>> from src.domains.llm_integration.tools.registry import ToolRegistry
    >>>
    >>> @ToolRegistry.register(
    ...     name="search",
    ...     description="Search the knowledge base",
    ...     parameters={
    ...         "type": "object",
    ...         "properties": {
    ...             "query": {"type": "string", "description": "Search query"}
    ...         },
    ...         "required": ["query"]
    ...     }
    ... )
    >>> async def search_tool(query: str) -> dict:
    ...     return {"results": [...]}
    >>>
    >>> # Get OpenAI-compatible schema
    >>> tools_schema = ToolRegistry.get_openai_tools_schema()
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolDefinition:
    """Definition of an available tool.

    Attributes:
        name: Tool name (used in function calls)
        description: Human-readable description
        parameters: JSON Schema for parameters
        handler: Async function to execute
        requires_sandbox: Whether tool needs sandboxing (default: False)
        metadata: Additional tool metadata
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable
    requires_sandbox: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Registry for LLM-callable tools.

    Class-level registry that manages tool registration and retrieval.
    Provides decorator-based registration and OpenAI-compatible schemas.
    """

    _tools: dict[str, ToolDefinition] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: dict[str, Any],
        requires_sandbox: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Callable:
        """Decorator to register a tool in the registry.

        Args:
            name: Tool name (must be unique)
            description: Human-readable description
            parameters: JSON Schema for parameters
            requires_sandbox: Whether tool execution needs sandboxing
            metadata: Additional metadata (tags, version, etc.)

        Returns:
            Decorator function

        Example:
            >>> @ToolRegistry.register(
            ...     name="calculator",
            ...     description="Perform arithmetic operations",
            ...     parameters={
            ...         "type": "object",
            ...         "properties": {
            ...             "operation": {"type": "string"},
            ...             "a": {"type": "number"},
            ...             "b": {"type": "number"}
            ...         },
            ...         "required": ["operation", "a", "b"]
            ...     }
            ... )
            >>> async def calculator(operation: str, a: float, b: float) -> float:
            ...     if operation == "add":
            ...         return a + b
            ...     # ...
        """

        def decorator(func: Callable) -> Callable:
            if name in cls._tools:
                logger.warning("tool_already_registered", name=name, action="overwriting")

            cls._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                requires_sandbox=requires_sandbox,
                metadata=metadata or {},
            )
            logger.info("tool_registered", name=name, requires_sandbox=requires_sandbox)
            return func

        return decorator

    @classmethod
    def get_tool(cls, name: str) -> ToolDefinition | None:
        """Get tool definition by name.

        Args:
            name: Tool name

        Returns:
            ToolDefinition or None if not found
        """
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> list[ToolDefinition]:
        """Get all registered tools.

        Returns:
            List of all ToolDefinition objects
        """
        return list(cls._tools.values())

    @classmethod
    def get_openai_tools_schema(cls) -> list[dict[str, Any]]:
        """Get tools in OpenAI function calling format.

        Returns OpenAI-compatible tool schemas for use with chat completions.

        Returns:
            List of tool schemas in OpenAI format

        Example output:
            [
                {
                    "type": "function",
                    "function": {
                        "name": "search",
                        "description": "Search the knowledge base",
                        "parameters": {
                            "type": "object",
                            "properties": {...},
                            "required": [...]
                        }
                    }
                }
            ]
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in cls._tools.values()
        ]

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a tool.

        Args:
            name: Tool name to remove

        Returns:
            True if tool was removed, False if not found
        """
        if name in cls._tools:
            del cls._tools[name]
            logger.info("tool_unregistered", name=name)
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools.

        Useful for testing or dynamic tool management.
        """
        count = len(cls._tools)
        cls._tools.clear()
        logger.info("tools_registry_cleared", tools_removed=count)

    @classmethod
    def list_tool_names(cls) -> list[str]:
        """Get list of all registered tool names.

        Returns:
            List of tool names
        """
        return list(cls._tools.keys())

    @classmethod
    def get_tool_count(cls) -> int:
        """Get number of registered tools.

        Returns:
            Count of registered tools
        """
        return len(cls._tools)
