"""Result Handlers for Tool Execution.

Sprint 59 Feature 59.2: Result processing and formatting for tool outputs.

This module provides utilities for processing tool execution results:
- Format standardization
- Error normalization
- Result truncation for large outputs
- Metadata extraction

Architecture:
    - ToolResult: Standardized result dataclass
    - Result formatters for different output types
    - Error handling and normalization

Usage:
    >>> from src.domains.llm_integration.tools.result_handlers import format_tool_result
    >>>
    >>> raw_result = {"result": {"data": [1, 2, 3], "count": 3}}
    >>> formatted = format_tool_result(raw_result, max_length=1000)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ToolResult:
    """Standardized tool execution result.

    Attributes:
        success: Whether execution succeeded
        data: Tool output data (None on error)
        error: Error message (None on success)
        metadata: Additional metadata (execution time, truncated, etc.)
        timestamp: Result timestamp
    """

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def format_tool_result(
    raw_result: dict[str, Any],
    max_length: int | None = None,
    include_metadata: bool = True,
) -> ToolResult:
    """Format raw tool result into standardized ToolResult.

    Args:
        raw_result: Raw result dict from tool execution
                   Expected format: {"result": ...} or {"error": ...}
        max_length: Maximum result length (truncate if exceeded)
        include_metadata: Include metadata in result

    Returns:
        ToolResult with standardized format

    Example:
        >>> raw = {"result": "Search found 42 documents"}
        >>> result = format_tool_result(raw, max_length=100)
        >>> assert result.success == True
        >>> assert result.data == "Search found 42 documents"
    """
    # Check if error
    if "error" in raw_result:
        return ToolResult(
            success=False,
            error=str(raw_result["error"]),
            metadata={"error_type": "tool_error"} if include_metadata else {},
        )

    # Extract result data
    data = raw_result.get("result")

    # Apply truncation if needed
    truncated = False
    if max_length and data is not None:
        data_str = str(data)
        if len(data_str) > max_length:
            data = data_str[:max_length] + "... [truncated]"
            truncated = True

    # Build metadata
    metadata = {}
    if include_metadata:
        metadata["truncated"] = truncated
        if truncated:
            metadata["original_length"] = len(str(raw_result.get("result", "")))

    return ToolResult(
        success=True,
        data=data,
        metadata=metadata,
    )


def normalize_error(error: Any) -> str:
    """Normalize error to string format.

    Args:
        error: Error (Exception, str, dict, etc.)

    Returns:
        Normalized error string

    Example:
        >>> err = normalize_error(ValueError("Invalid input"))
        >>> assert "Invalid input" in err
    """
    if isinstance(error, Exception):
        return f"{type(error).__name__}: {str(error)}"
    elif isinstance(error, dict):
        return error.get("message", str(error))
    else:
        return str(error)


def truncate_large_output(
    data: Any,
    max_length: int = 10000,
    placeholder: str = "... [output truncated]",
) -> tuple[Any, bool]:
    """Truncate large outputs to prevent memory issues.

    Args:
        data: Data to potentially truncate
        max_length: Maximum allowed length
        placeholder: Truncation placeholder text

    Returns:
        Tuple of (truncated_data, was_truncated)

    Example:
        >>> long_text = "a" * 20000
        >>> truncated, was_trunc = truncate_large_output(long_text, max_length=1000)
        >>> assert was_trunc == True
        >>> assert len(truncated) <= 1000 + len("... [output truncated]")
    """
    data_str = str(data)

    if len(data_str) <= max_length:
        return data, False

    # Truncate and add placeholder
    truncated = data_str[:max_length] + placeholder

    logger.info(
        "output_truncated",
        original_length=len(data_str),
        truncated_length=len(truncated),
        max_length=max_length,
    )

    return truncated, True


def extract_metadata_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from tool result.

    Looks for common metadata fields like:
    - execution_time
    - warnings
    - source
    - version

    Args:
        result: Tool result dict

    Returns:
        Extracted metadata dict

    Example:
        >>> result = {
        ...     "result": "data",
        ...     "execution_time_ms": 42,
        ...     "warnings": ["Deprecated API"]
        ... }
        >>> meta = extract_metadata_from_result(result)
        >>> assert meta["execution_time_ms"] == 42
    """
    metadata_keys = [
        "execution_time_ms",
        "execution_time",
        "warnings",
        "source",
        "version",
        "cached",
        "rate_limit",
    ]

    metadata = {}
    for key in metadata_keys:
        if key in result:
            metadata[key] = result[key]

    return metadata


def format_error_result(
    error: str | Exception,
    tool_name: str | None = None,
    context: dict[str, Any] | None = None,
) -> ToolResult:
    """Format error into standardized ToolResult.

    Args:
        error: Error message or exception
        tool_name: Name of tool that failed
        context: Additional error context

    Returns:
        ToolResult with error information

    Example:
        >>> result = format_error_result(
        ...     ValueError("Invalid input"),
        ...     tool_name="calculator",
        ...     context={"input": "abc"}
        ... )
        >>> assert result.success == False
        >>> assert "ValueError" in result.error
    """
    error_msg = normalize_error(error)

    metadata = {}
    if tool_name:
        metadata["tool_name"] = tool_name
    if context:
        metadata["context"] = context

    return ToolResult(
        success=False,
        error=error_msg,
        metadata=metadata,
    )


def combine_results(results: list[ToolResult]) -> dict[str, Any]:
    """Combine multiple tool results into summary.

    Args:
        results: List of ToolResult objects

    Returns:
        Summary dict with aggregate statistics

    Example:
        >>> results = [
        ...     ToolResult(success=True, data="result1"),
        ...     ToolResult(success=False, error="error1"),
        ...     ToolResult(success=True, data="result2")
        ... ]
        >>> summary = combine_results(results)
        >>> assert summary["total"] == 3
        >>> assert summary["successful"] == 2
        >>> assert summary["failed"] == 1
    """
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful

    errors = [r.error for r in results if r.error]
    data_outputs = [r.data for r in results if r.success and r.data is not None]

    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": successful / total if total > 0 else 0.0,
        "errors": errors,
        "results": data_outputs,
    }
