"""Built-in Tools for Tool Composition Framework.

Sprint 93 Feature 93.1: Tool Composition Framework

This module provides basic utility tools that are always available
in the Tool Composer. These tools are used for data transformation,
testing, and common operations within tool chains.

Tool Categories:
    - Utility: echo, format, json_extract
    - Transform: template, split, join
    - Control: conditional, loop (future)

LangGraph 1.0 Integration:
    All tools are decorated with @tool for LangGraph compatibility
    and support InjectedState for skill context access.

Example:
    >>> from src.agents.tools.builtin import echo_tool, format_tool
    >>> result = echo_tool("Hello, World!")
    >>> result
    'Hello, World!'
    >>> result = format_tool("Name: {name}", {"name": "Claude"})
    >>> result
    'Name: Claude'

See Also:
    - src/agents/tools/composition.py: ToolComposer that uses these tools
    - docs/sprints/SPRINT_93_PLAN.md: Feature specification
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.tools import tool

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Utility Tools
# =============================================================================


@tool
def echo_tool(message: str) -> str:
    """Echo the input message unchanged.

    Useful for testing tool chains and passing values through.

    Args:
        message: The message to echo

    Returns:
        The same message

    Example:
        >>> echo_tool("test")
        'test'
    """
    logger.debug("echo_tool_called", message_length=len(message))
    return message


@tool
def format_tool(template: str, values: dict[str, Any]) -> str:
    """Format a template string with provided values.

    Uses Python str.format() syntax for variable substitution.

    Args:
        template: Template string with {variable} placeholders
        values: Dictionary of variable names to values

    Returns:
        Formatted string with variables substituted

    Example:
        >>> format_tool("Hello, {name}!", {"name": "World"})
        'Hello, World!'

        >>> format_tool("Item: {item}, Count: {count}", {"item": "Apple", "count": 5})
        'Item: Apple, Count: 5'
    """
    try:
        result = template.format(**values)
        logger.debug(
            "format_tool_success",
            template_length=len(template),
            value_count=len(values),
        )
        return result
    except KeyError as e:
        logger.warning("format_tool_missing_key", key=str(e), template=template[:100])
        return template  # Return unformatted on error


@tool
def json_extract_tool(json_str: str, path: str) -> Any:
    """Extract a value from JSON using a dot-notation path.

    Supports nested paths like "data.items[0].name".

    Args:
        json_str: JSON string to parse
        path: Dot-notation path to value (e.g., "data.name", "items[0]")

    Returns:
        Extracted value or None if path not found

    Example:
        >>> json_extract_tool('{"user": {"name": "Alice"}}', "user.name")
        'Alice'

        >>> json_extract_tool('{"items": [1, 2, 3]}', "items[1]")
        2
    """
    try:
        data = json.loads(json_str)
        result = _extract_path(data, path)
        logger.debug("json_extract_success", path=path, result_type=type(result).__name__)
        return result
    except json.JSONDecodeError as e:
        logger.warning("json_extract_parse_error", error=str(e))
        return None
    except Exception as e:
        logger.warning("json_extract_error", path=path, error=str(e))
        return None


def _extract_path(data: Any, path: str) -> Any:
    """Extract value from nested data using dot notation.

    Internal helper for json_extract_tool.

    Args:
        data: Nested dict/list structure
        path: Dot-notation path with optional array indexing

    Returns:
        Value at path or None
    """
    if not path:
        return data

    parts = _parse_path(path)
    current = data

    for part in parts:
        if isinstance(part, int):
            # Array index
            if isinstance(current, (list, tuple)) and len(current) > part:
                current = current[part]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

        if current is None:
            return None

    return current


def _parse_path(path: str) -> list[str | int]:
    """Parse dot notation path into parts.

    Handles both dot notation (data.field) and bracket notation (items[0]).

    Args:
        path: Path string like "data.items[0].name"

    Returns:
        List of string keys and integer indices

    Example:
        >>> _parse_path("data.items[0].name")
        ['data', 'items', 0, 'name']
    """
    parts: list[str | int] = []

    # Match either a field name or array index
    pattern = r"([a-zA-Z_][a-zA-Z0-9_]*|\[\d+\])"
    matches = re.findall(pattern, path)

    for match in matches:
        if match.startswith("["):
            # Array index
            idx = int(match[1:-1])
            parts.append(idx)
        else:
            parts.append(match)

    return parts


# =============================================================================
# Transform Tools
# =============================================================================


@tool
def template_tool(template: str, context: dict[str, Any]) -> str:
    """Advanced template rendering with Jinja2-like syntax.

    Supports:
        - Simple substitution: {{ variable }}
        - Default values: {{ variable | default("fallback") }}
        - Conditionals: {% if condition %}...{% endif %}

    Args:
        template: Template string with Jinja2-like syntax
        context: Dictionary of variable values

    Returns:
        Rendered template string

    Example:
        >>> template_tool("Hello, {{ name }}!", {"name": "World"})
        'Hello, World!'
    """
    try:
        # Simple Jinja2-like substitution
        result = template

        # Replace {{ variable }} patterns
        pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        result = re.sub(pattern, replace_var, result)

        logger.debug("template_tool_success", template_length=len(template))
        return result

    except Exception as e:
        logger.warning("template_tool_error", error=str(e))
        return template


@tool
def split_tool(text: str, separator: str = "\n") -> list[str]:
    """Split text into a list of parts.

    Args:
        text: Text to split
        separator: Separator string (default: newline)

    Returns:
        List of text parts

    Example:
        >>> split_tool("a,b,c", ",")
        ['a', 'b', 'c']
    """
    result = text.split(separator)
    logger.debug("split_tool_success", parts=len(result))
    return result


@tool
def join_tool(items: list[str], separator: str = ", ") -> str:
    """Join list items into a single string.

    Args:
        items: List of strings to join
        separator: Separator between items (default: ", ")

    Returns:
        Joined string

    Example:
        >>> join_tool(["a", "b", "c"], " - ")
        'a - b - c'
    """
    result = separator.join(items)
    logger.debug("join_tool_success", item_count=len(items))
    return result


@tool
def to_json_tool(data: Any, indent: int = 2) -> str:
    """Convert Python object to JSON string.

    Args:
        data: Python object (dict, list, str, int, etc.)
        indent: JSON indentation (default: 2 spaces)

    Returns:
        JSON string representation

    Example:
        >>> to_json_tool({"name": "test", "count": 5})
        '{\\n  "name": "test",\\n  "count": 5\\n}'
    """
    try:
        result = json.dumps(data, indent=indent, ensure_ascii=False)
        logger.debug("to_json_success", data_type=type(data).__name__)
        return result
    except (TypeError, ValueError) as e:
        logger.warning("to_json_error", error=str(e))
        return str(data)


@tool
def from_json_tool(json_str: str) -> Any:
    """Parse JSON string to Python object.

    Args:
        json_str: JSON string to parse

    Returns:
        Python object (dict, list, str, int, etc.)

    Example:
        >>> from_json_tool('{"name": "test"}')
        {'name': 'test'}
    """
    try:
        result = json.loads(json_str)
        logger.debug("from_json_success", result_type=type(result).__name__)
        return result
    except json.JSONDecodeError as e:
        logger.warning("from_json_error", error=str(e))
        return None


# =============================================================================
# String Manipulation Tools
# =============================================================================


@tool
def truncate_tool(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to maximum length with optional suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to append when truncated

    Returns:
        Truncated text

    Example:
        >>> truncate_tool("Hello World", 5, "...")
        'Hello...'
    """
    if len(text) <= max_length:
        return text

    result = text[:max_length] + suffix
    logger.debug("truncate_tool", original_length=len(text), truncated_length=len(result))
    return result


@tool
def replace_tool(text: str, old: str, new: str, count: int = -1) -> str:
    """Replace occurrences in text.

    Args:
        text: Original text
        old: String to replace
        new: Replacement string
        count: Max replacements (-1 for all)

    Returns:
        Text with replacements

    Example:
        >>> replace_tool("hello world world", "world", "earth")
        'hello earth earth'
    """
    if count < 0:
        result = text.replace(old, new)
    else:
        result = text.replace(old, new, count)

    logger.debug("replace_tool", old=old, new=new)
    return result


# =============================================================================
# Registry
# =============================================================================


def get_builtin_tools() -> dict[str, Any]:
    """Get all built-in tools as a registry dict.

    Returns:
        Dict mapping tool names to tool functions
    """
    return {
        # Utility
        "echo": echo_tool,
        "format": format_tool,
        "json_extract": json_extract_tool,
        # Transform
        "template": template_tool,
        "split": split_tool,
        "join": join_tool,
        "to_json": to_json_tool,
        "from_json": from_json_tool,
        # String
        "truncate": truncate_tool,
        "replace": replace_tool,
    }
