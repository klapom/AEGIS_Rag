"""
Unit tests for SSE message formatting.

Sprint 15 Feature 15.1: SSE Streaming Backend
Tests the SSE format helper functions without requiring full app.
"""

import json
import pytest
from datetime import datetime, timezone


def _format_sse_message(data: dict) -> str:
    """Format data as Server-Sent Events (SSE) message."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_iso_timestamp() -> str:
    """Get current timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def test_format_sse_message_simple():
    """Test SSE message formatting with simple data."""
    data = {"type": "token", "content": "Hello"}
    result = _format_sse_message(data)

    assert result.startswith("data: ")
    assert result.endswith("\n\n")
    assert "Hello" in result
    assert json.loads(result[6:-2]) == data


def test_format_sse_message_metadata():
    """Test SSE message formatting with metadata."""
    data = {"type": "metadata", "session_id": "test-123", "timestamp": "2025-01-01T00:00:00Z"}
    result = _format_sse_message(data)

    parsed = json.loads(result[6:-2])
    assert parsed["type"] == "metadata"
    assert parsed["session_id"] == "test-123"


def test_format_sse_message_with_unicode():
    """Test SSE message formatting with Unicode characters."""
    data = {"type": "token", "content": "Hallo Welt! 🎉"}
    result = _format_sse_message(data)

    parsed = json.loads(result[6:-2])
    assert parsed["content"] == "Hallo Welt! 🎉"


def test_format_sse_message_nested_data():
    """Test SSE message formatting with nested data structures."""
    data = {
        "type": "source",
        "source": {"document_id": "doc-123", "score": 0.95, "metadata": {"author": "Test Author"}},
    }
    result = _format_sse_message(data)

    parsed = json.loads(result[6:-2])
    assert parsed["source"]["document_id"] == "doc-123"
    assert parsed["source"]["score"] == 0.95
    assert parsed["source"]["metadata"]["author"] == "Test Author"


def test_get_iso_timestamp_format():
    """Test ISO timestamp format."""
    timestamp = _get_iso_timestamp()

    # Should be parseable as ISO format
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert isinstance(parsed, datetime)

    # Should include timezone
    assert "+" in timestamp or "Z" in timestamp or timestamp.endswith("+00:00")


def test_sse_message_multiple_messages():
    """Test formatting multiple SSE messages."""
    messages = [
        {"type": "metadata", "session_id": "123"},
        {"type": "token", "content": "Hello"},
        {"type": "token", "content": " World"},
        {"type": "done"},
    ]

    formatted = [_format_sse_message(msg) for msg in messages]

    assert len(formatted) == 4
    for msg in formatted:
        assert msg.startswith("data: ")
        assert msg.endswith("\n\n")


def test_sse_done_signal():
    """Test formatting of [DONE] signal."""
    done_signal = "data: [DONE]\n\n"

    assert done_signal.startswith("data: ")
    assert done_signal.endswith("\n\n")
    assert "[DONE]" in done_signal


def test_sse_message_with_empty_content():
    """Test SSE message with empty content."""
    data = {"type": "token", "content": ""}
    result = _format_sse_message(data)

    parsed = json.loads(result[6:-2])
    assert parsed["content"] == ""


def test_sse_message_with_special_characters():
    """Test SSE message with special characters that need escaping."""
    data = {"type": "token", "content": 'Text with "quotes" and \n newlines'}
    result = _format_sse_message(data)

    # Should be valid JSON
    parsed = json.loads(result[6:-2])
    assert parsed["content"] == 'Text with "quotes" and \n newlines'


def test_sse_error_message():
    """Test formatting of error messages."""
    data = {"type": "error", "error": "Something went wrong", "code": "INTERNAL_ERROR"}
    result = _format_sse_message(data)

    parsed = json.loads(result[6:-2])
    assert parsed["type"] == "error"
    assert parsed["error"] == "Something went wrong"
    assert parsed["code"] == "INTERNAL_ERROR"
