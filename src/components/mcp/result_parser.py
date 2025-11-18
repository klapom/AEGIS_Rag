"""MCP Result Parser.

Parses and normalizes tool execution results from different formats.
Handles JSON, text, binary, and raw data formats.

Sprint 9 Feature 9.7: Tool Execution Handler
"""

import base64
import json
from typing import Any, Dict


class ResultParser:
    """Parse tool execution results into normalized format."""

    @staticmethod
    def parse(raw_result: Any, expected_format: str = "json") -> Dict[str, Any]:
        """Parse tool result based on expected format.

        Args:
            raw_result: Raw result from tool execution
            expected_format: Expected format ("json", "text", "binary", or "auto")

        Returns:
            Parsed result as dictionary

        Raises:
            ValueError: If result cannot be parsed in expected format
        """
        if expected_format == "auto":
            return ResultParser._auto_detect_and_parse(raw_result)

        parsers = {
            "json": ResultParser._parse_json,
            "text": ResultParser._parse_text,
            "binary": ResultParser._parse_binary,
            "raw": ResultParser._parse_raw,
        }

        parser = parsers.get(expected_format)
        if not parser:
            raise ValueError(f"Unknown format: {expected_format}")

        return parser(raw_result)

    @staticmethod
    def _parse_json(raw_result: Any) -> Dict[str, Any]:
        """Parse JSON result.

        Args:
            raw_result: Result to parse as JSON

        Returns:
            Parsed JSON as dictionary
        """
        if isinstance(raw_result, dict):
            return raw_result

        if isinstance(raw_result, str):
            try:
                parsed: Dict[str, Any] = json.loads(raw_result)
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {str(e)}") from e

        # Try to convert to dict
        if hasattr(raw_result, "__dict__"):
            return vars(raw_result)

        return {"value": raw_result}

    @staticmethod
    def _parse_text(raw_result: Any) -> Dict[str, Any]:
        """Parse text result.

        Args:
            raw_result: Result to parse as text

        Returns:
            Dictionary with text content
        """
        return {"content": str(raw_result), "format": "text"}

    @staticmethod
    def _parse_binary(raw_result: Any) -> Dict[str, Any]:
        """Parse binary result.

        Args:
            raw_result: Result to parse as binary

        Returns:
            Dictionary with base64-encoded binary data
        """
        if isinstance(raw_result, bytes):
            encoded = base64.b64encode(raw_result).decode("utf-8")
            return {"data": encoded, "encoding": "base64", "format": "binary"}

        # If it's a string, assume it's already base64-encoded
        if isinstance(raw_result, str):
            return {"data": raw_result, "encoding": "base64", "format": "binary"}

        # Try to convert to bytes
        try:
            binary_data = bytes(raw_result)
            encoded = base64.b64encode(binary_data).decode("utf-8")
            return {"data": encoded, "encoding": "base64", "format": "binary"}
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot convert to binary: {str(e)}") from e

    @staticmethod
    def _parse_raw(raw_result: Any) -> Dict[str, Any]:
        """Return raw result as-is.

        Args:
            raw_result: Result to return unchanged

        Returns:
            Dictionary with raw result
        """
        return {"raw": raw_result, "format": "raw"}

    @staticmethod
    def _auto_detect_and_parse(raw_result: Any) -> Dict[str, Any]:
        """Auto-detect format and parse accordingly.

        Args:
            raw_result: Result to parse

        Returns:
            Parsed result based on detected format
        """
        # Try JSON first
        if isinstance(raw_result, dict):
            return raw_result

        if isinstance(raw_result, str):
            # Try parsing as JSON
            try:
                parsed: Dict[str, Any] = json.loads(raw_result)
                return parsed
            except json.JSONDecodeError:
                # Not JSON, treat as text
                return ResultParser._parse_text(raw_result)

        # Check if binary
        if isinstance(raw_result, bytes):
            return ResultParser._parse_binary(raw_result)

        # Try to convert to dict
        if hasattr(raw_result, "__dict__"):
            return vars(raw_result)

        # Default to raw
        return ResultParser._parse_raw(raw_result)

    @staticmethod
    def validate_result(result: Dict[str, Any]) -> bool:
        """Validate that a parsed result is well-formed.

        Args:
            result: Parsed result to validate

        Returns:
            True if result is valid
        """
        if not isinstance(result, dict):
            return False

        # Must have at least one key
        if not result:
            return False

        # If it has a format field, it should be a known format
        if "format" in result:
            valid_formats = {"text", "binary", "raw"}
            if result["format"] not in valid_formats:
                return False

        return True

    @staticmethod
    def extract_content(result: Dict[str, Any]) -> Any:
        """Extract the main content from a parsed result.

        Args:
            result: Parsed result dictionary

        Returns:
            Main content value
        """
        # Try common content keys in order of preference
        content_keys = ["content", "value", "data", "result", "raw"]

        for key in content_keys:
            if key in result:
                return result[key]

        # If no standard key found, return the whole dict
        return result
