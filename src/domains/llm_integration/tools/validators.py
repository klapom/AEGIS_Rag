"""Parameter Validators for Tool Execution.

Sprint 59 Feature 59.2: Input validation for tool parameters.

This module provides JSON Schema-based validation for tool parameters
before execution. Ensures type safety and prevents invalid inputs.

Architecture:
    - ValidationResult: Result dataclass with success/error info
    - validate_parameters: Main validation function using JSON Schema
    - Type coercion for common cases (string -> int, etc.)

Usage:
    >>> from src.domains.llm_integration.tools.validators import validate_parameters
    >>>
    >>> schema = {
    ...     "type": "object",
    ...     "properties": {
    ...         "query": {"type": "string"},
    ...         "limit": {"type": "integer", "minimum": 1, "maximum": 100}
    ...     },
    ...     "required": ["query"]
    ... }
    >>>
    >>> result = validate_parameters({"query": "test", "limit": 10}, schema)
    >>> assert result.valid == True
    >>>
    >>> result = validate_parameters({"limit": 10}, schema)  # Missing required
    >>> assert result.valid == False
    >>> assert "query" in result.error
"""

from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of parameter validation.

    Attributes:
        valid: Whether validation passed
        error: Error message if validation failed (None if valid)
        coerced_params: Parameters after type coercion (same as input if no coercion)
    """

    valid: bool
    error: str | None = None
    coerced_params: dict[str, Any] | None = None


def validate_parameters(
    parameters: dict[str, Any],
    schema: dict[str, Any],
) -> ValidationResult:
    """Validate tool parameters against JSON Schema.

    Performs JSON Schema validation and type coercion where safe.

    Args:
        parameters: Input parameters to validate
        schema: JSON Schema definition

    Returns:
        ValidationResult with validation status and any errors

    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "name": {"type": "string"},
        ...         "age": {"type": "integer"}
        ...     },
        ...     "required": ["name"]
        ... }
        >>> result = validate_parameters({"name": "Alice", "age": 30}, schema)
        >>> assert result.valid == True
    """
    try:
        # Import jsonschema for validation
        try:
            from jsonschema import validate as jsonschema_validate
            from jsonschema.exceptions import ValidationError
        except ImportError:
            logger.warning("jsonschema_not_installed", fallback="basic_validation")
            # Fallback to basic validation
            return _basic_validation(parameters, schema)

        # Validate against schema
        try:
            jsonschema_validate(instance=parameters, schema=schema)
            return ValidationResult(valid=True, coerced_params=parameters)
        except ValidationError as e:
            error_msg = f"Validation error: {e.message}"
            logger.warning(
                "parameter_validation_failed",
                error=error_msg,
                path=list(e.path) if e.path else None,
            )
            return ValidationResult(valid=False, error=error_msg)

    except Exception as e:
        logger.error("validation_exception", error=str(e))
        return ValidationResult(valid=False, error=f"Validation failed: {str(e)}")


def _basic_validation(
    parameters: dict[str, Any],
    schema: dict[str, Any],
) -> ValidationResult:
    """Basic validation when jsonschema is not available.

    Checks:
    - Required fields present
    - Basic type checking
    - No advanced schema features

    Args:
        parameters: Input parameters
        schema: JSON Schema

    Returns:
        ValidationResult
    """
    try:
        # Check type
        if schema.get("type") != "object":
            return ValidationResult(
                valid=False,
                error=f"Schema type must be 'object', got '{schema.get('type')}'",
            )

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in parameters:
                return ValidationResult(valid=False, error=f"Missing required field: {field}")

        # Basic type checking for properties
        properties = schema.get("properties", {})
        for key, value in parameters.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type:
                    if not _check_type(value, expected_type):
                        return ValidationResult(
                            valid=False,
                            error=f"Field '{key}' has wrong type. Expected {expected_type}, got {type(value).__name__}",
                        )

        return ValidationResult(valid=True, coerced_params=parameters)

    except Exception as e:
        return ValidationResult(valid=False, error=f"Basic validation failed: {str(e)}")


def _check_type(value: Any, expected_type: str) -> bool:
    """Check if value matches expected JSON Schema type.

    Args:
        value: Value to check
        expected_type: JSON Schema type string

    Returns:
        True if type matches
    """
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    python_type = type_map.get(expected_type)
    if python_type is None:
        return True  # Unknown type, skip check

    return isinstance(value, python_type)


def validate_required_fields(
    parameters: dict[str, Any],
    required_fields: list[str],
) -> ValidationResult:
    """Simple validation for required fields only.

    Args:
        parameters: Input parameters
        required_fields: List of required field names

    Returns:
        ValidationResult

    Example:
        >>> result = validate_required_fields(
        ...     {"name": "Alice"},
        ...     ["name", "age"]
        ... )
        >>> assert result.valid == False
        >>> assert "age" in result.error
    """
    missing = [field for field in required_fields if field not in parameters]

    if missing:
        return ValidationResult(
            valid=False,
            error=f"Missing required fields: {', '.join(missing)}",
        )

    return ValidationResult(valid=True, coerced_params=parameters)


def coerce_types(
    parameters: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Attempt type coercion for common cases.

    Coerces:
    - String to int/float for numeric fields
    - String "true"/"false" to boolean
    - List to string (join)

    Args:
        parameters: Input parameters
        schema: JSON Schema with type hints

    Returns:
        Parameters with coerced types

    Example:
        >>> schema = {"properties": {"age": {"type": "integer"}}}
        >>> result = coerce_types({"age": "25"}, schema)
        >>> assert result["age"] == 25
    """
    coerced = parameters.copy()
    properties = schema.get("properties", {})

    for key, value in parameters.items():
        if key not in properties:
            continue

        expected_type = properties[key].get("type")
        if not expected_type:
            continue

        try:
            if expected_type == "integer" and isinstance(value, str):
                coerced[key] = int(value)
            elif expected_type == "number" and isinstance(value, str):
                coerced[key] = float(value)
            elif expected_type == "boolean" and isinstance(value, str):
                coerced[key] = value.lower() in ("true", "1", "yes")
            elif expected_type == "string" and isinstance(value, (int, float, bool)):
                coerced[key] = str(value)
        except (ValueError, TypeError):
            # Keep original value if coercion fails
            pass

    return coerced
