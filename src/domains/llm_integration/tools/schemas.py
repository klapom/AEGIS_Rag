"""OpenAI-Compatible Tool Schemas.

Sprint 59 Feature 59.2: JSON Schema definitions for tool parameters.

This module provides JSON Schema utilities and helpers for creating
OpenAI-compatible tool schemas for function calling.

Architecture:
    - Schema builders for common parameter types
    - Validation schema generators
    - OpenAI function calling format converters

Usage:
    >>> from src.domains.llm_integration.tools.schemas import (
    ...     create_parameter_schema,
    ...     create_function_schema
    ... )
    >>>
    >>> params = create_parameter_schema(
    ...     properties={
    ...         "query": {
    ...             "type": "string",
    ...             "description": "Search query"
    ...         },
    ...         "limit": {
    ...             "type": "integer",
    ...             "description": "Max results",
    ...             "minimum": 1,
    ...             "maximum": 100,
    ...             "default": 10
    ...         }
    ...     },
    ...     required=["query"]
    ... )
"""

from typing import Any


def create_parameter_schema(
    properties: dict[str, dict[str, Any]],
    required: list[str] | None = None,
    additional_properties: bool = False,
) -> dict[str, Any]:
    """Create JSON Schema for tool parameters.

    Args:
        properties: Property definitions (name -> schema)
        required: List of required property names
        additional_properties: Allow extra properties (default: False)

    Returns:
        JSON Schema dict

    Example:
        >>> schema = create_parameter_schema(
        ...     properties={
        ...         "name": {
        ...             "type": "string",
        ...             "description": "User name"
        ...         },
        ...         "age": {
        ...             "type": "integer",
        ...             "minimum": 0
        ...         }
        ...     },
        ...     required=["name"]
        ... )
    """
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": additional_properties,
    }


def create_function_schema(
    name: str,
    description: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Create OpenAI function calling schema.

    Args:
        name: Function name
        description: Human-readable description
        parameters: JSON Schema for parameters

    Returns:
        OpenAI function schema

    Example:
        >>> schema = create_function_schema(
        ...     name="search",
        ...     description="Search the knowledge base",
        ...     parameters={
        ...         "type": "object",
        ...         "properties": {
        ...             "query": {"type": "string"}
        ...         },
        ...         "required": ["query"]
        ...     }
        ... )
    """
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def create_string_property(
    description: str,
    enum: list[str] | None = None,
    pattern: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    default: str | None = None,
) -> dict[str, Any]:
    """Create string property schema.

    Args:
        description: Property description
        enum: List of allowed values
        pattern: Regex pattern for validation
        min_length: Minimum string length
        max_length: Maximum string length
        default: Default value

    Returns:
        Property schema dict

    Example:
        >>> prop = create_string_property(
        ...     description="Log level",
        ...     enum=["debug", "info", "warning", "error"],
        ...     default="info"
        ... )
    """
    schema = {
        "type": "string",
        "description": description,
    }

    if enum is not None:
        schema["enum"] = enum
    if pattern is not None:
        schema["pattern"] = pattern
    if min_length is not None:
        schema["minLength"] = min_length
    if max_length is not None:
        schema["maxLength"] = max_length
    if default is not None:
        schema["default"] = default

    return schema


def create_integer_property(
    description: str,
    minimum: int | None = None,
    maximum: int | None = None,
    default: int | None = None,
) -> dict[str, Any]:
    """Create integer property schema.

    Args:
        description: Property description
        minimum: Minimum value (inclusive)
        maximum: Maximum value (inclusive)
        default: Default value

    Returns:
        Property schema dict

    Example:
        >>> prop = create_integer_property(
        ...     description="Number of results",
        ...     minimum=1,
        ...     maximum=100,
        ...     default=10
        ... )
    """
    schema = {
        "type": "integer",
        "description": description,
    }

    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    if default is not None:
        schema["default"] = default

    return schema


def create_number_property(
    description: str,
    minimum: float | None = None,
    maximum: float | None = None,
    default: float | None = None,
) -> dict[str, Any]:
    """Create number (float) property schema.

    Args:
        description: Property description
        minimum: Minimum value (inclusive)
        maximum: Maximum value (inclusive)
        default: Default value

    Returns:
        Property schema dict

    Example:
        >>> prop = create_number_property(
        ...     description="Confidence threshold",
        ...     minimum=0.0,
        ...     maximum=1.0,
        ...     default=0.8
        ... )
    """
    schema = {
        "type": "number",
        "description": description,
    }

    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    if default is not None:
        schema["default"] = default

    return schema


def create_boolean_property(
    description: str,
    default: bool | None = None,
) -> dict[str, Any]:
    """Create boolean property schema.

    Args:
        description: Property description
        default: Default value

    Returns:
        Property schema dict

    Example:
        >>> prop = create_boolean_property(
        ...     description="Enable caching",
        ...     default=True
        ... )
    """
    schema = {
        "type": "boolean",
        "description": description,
    }

    if default is not None:
        schema["default"] = default

    return schema


def create_array_property(
    description: str,
    items: dict[str, Any],
    min_items: int | None = None,
    max_items: int | None = None,
    unique_items: bool = False,
) -> dict[str, Any]:
    """Create array property schema.

    Args:
        description: Property description
        items: Schema for array items
        min_items: Minimum array length
        max_items: Maximum array length
        unique_items: Whether items must be unique

    Returns:
        Property schema dict

    Example:
        >>> prop = create_array_property(
        ...     description="Search filters",
        ...     items={"type": "string"},
        ...     min_items=1,
        ...     max_items=5
        ... )
    """
    schema = {
        "type": "array",
        "description": description,
        "items": items,
    }

    if min_items is not None:
        schema["minItems"] = min_items
    if max_items is not None:
        schema["maxItems"] = max_items
    if unique_items:
        schema["uniqueItems"] = True

    return schema


def create_object_property(
    description: str,
    properties: dict[str, dict[str, Any]],
    required: list[str] | None = None,
    additional_properties: bool = False,
) -> dict[str, Any]:
    """Create nested object property schema.

    Args:
        description: Property description
        properties: Object property schemas
        required: Required property names
        additional_properties: Allow extra properties

    Returns:
        Property schema dict

    Example:
        >>> prop = create_object_property(
        ...     description="Query filters",
        ...     properties={
        ...         "min_score": {"type": "number"},
        ...         "categories": {"type": "array", "items": {"type": "string"}}
        ...     },
        ...     required=["min_score"]
        ... )
    """
    return {
        "type": "object",
        "description": description,
        "properties": properties,
        "required": required or [],
        "additionalProperties": additional_properties,
    }
