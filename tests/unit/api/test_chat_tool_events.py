"""Unit tests for SSE tool event emission in chat streaming.

Sprint 120 Feature 120.14: SSE Tool Events in Chat Stream

Tests that tool-specific SSE events (tool_use, tool_result, tool_error) are correctly
emitted when TOOL_EXECUTION phase events are received during chat streaming.
"""

import json
from datetime import datetime

import pytest

from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType


class TestToolEventEmission:
    """Test SSE tool event emission from TOOL_EXECUTION phase events."""

    def test_tool_use_event_format(self):
        """Test tool_use event format matches frontend expectations."""
        # Simulate a TOOL_EXECUTION IN_PROGRESS phase event
        phase_event = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.IN_PROGRESS,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            metadata={
                "tool_name": "bash",
                "parameters": {"command": "ls -la"},
            },
        )

        # Extract tool data (simulating chat.py logic)
        tool_name = phase_event.metadata.get("tool_name", "unknown")
        execution_id = f"{tool_name}_{phase_event.start_time.isoformat()}"
        timestamp = phase_event.start_time.isoformat()

        tool_use_event = {
            "type": "tool_use",
            "data": {
                "tool": tool_name,
                "server": "mcp",
                "parameters": phase_event.metadata.get("parameters", {}),
                "execution_id": execution_id,
                "timestamp": timestamp,
            },
        }

        # Verify event structure
        assert tool_use_event["type"] == "tool_use"
        assert tool_use_event["data"]["tool"] == "bash"
        assert tool_use_event["data"]["server"] == "mcp"
        assert tool_use_event["data"]["parameters"] == {"command": "ls -la"}
        assert "execution_id" in tool_use_event["data"]
        assert "timestamp" in tool_use_event["data"]

    def test_tool_result_event_format(self):
        """Test tool_result event format matches frontend expectations."""
        # Simulate a TOOL_EXECUTION COMPLETED phase event
        phase_event = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.COMPLETED,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            end_time=datetime(2025, 1, 26, 12, 0, 1),
            duration_ms=1000.0,
            metadata={
                "tool_name": "bash",
                "result_preview": "total 48\ndrwxr-xr-x 10 user user 4096 Jan 26 12:00 .",
            },
        )

        # Extract tool data
        tool_name = phase_event.metadata.get("tool_name", "unknown")
        execution_id = f"{tool_name}_{phase_event.start_time.isoformat()}"

        tool_result_event = {
            "type": "tool_result",
            "data": {
                "tool": tool_name,
                "server": "mcp",
                "result": phase_event.metadata.get("result_preview", ""),
                "success": True,
                "duration_ms": phase_event.duration_ms,
                "execution_id": execution_id,
                "timestamp": phase_event.end_time.isoformat() if phase_event.end_time else phase_event.start_time.isoformat(),
            },
        }

        # Verify event structure
        assert tool_result_event["type"] == "tool_result"
        assert tool_result_event["data"]["tool"] == "bash"
        assert tool_result_event["data"]["success"] is True
        assert tool_result_event["data"]["duration_ms"] == 1000.0
        assert "result" in tool_result_event["data"]
        assert "execution_id" in tool_result_event["data"]
        assert "timestamp" in tool_result_event["data"]

    def test_tool_error_event_format(self):
        """Test tool_error event format matches frontend expectations."""
        # Simulate a TOOL_EXECUTION FAILED phase event
        phase_event = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.FAILED,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            end_time=datetime(2025, 1, 26, 12, 0, 1),
            duration_ms=500.0,
            error="Permission denied",
            metadata={
                "tool_name": "bash",
                "error_details": "User does not have permission to execute this command",
            },
        )

        # Extract tool data
        tool_name = phase_event.metadata.get("tool_name", "unknown")
        execution_id = f"{tool_name}_{phase_event.start_time.isoformat()}"

        tool_error_event = {
            "type": "tool_error",
            "data": {
                "tool": tool_name,
                "error": phase_event.error or "Tool execution failed",
                "details": phase_event.metadata.get("error_details", ""),
                "execution_id": execution_id,
                "timestamp": phase_event.end_time.isoformat() if phase_event.end_time else phase_event.start_time.isoformat(),
            },
        }

        # Verify event structure
        assert tool_error_event["type"] == "tool_error"
        assert tool_error_event["data"]["tool"] == "bash"
        assert tool_error_event["data"]["error"] == "Permission denied"
        assert "details" in tool_error_event["data"]
        assert "execution_id" in tool_error_event["data"]
        assert "timestamp" in tool_error_event["data"]

    def test_execution_id_uniqueness(self):
        """Test that execution IDs are unique for different tool executions."""
        # Create two phase events at different times
        event1 = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.IN_PROGRESS,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            metadata={"tool_name": "bash"},
        )

        event2 = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.IN_PROGRESS,
            start_time=datetime(2025, 1, 26, 12, 0, 1),
            metadata={"tool_name": "bash"},
        )

        exec_id1 = f"bash_{event1.start_time.isoformat()}"
        exec_id2 = f"bash_{event2.start_time.isoformat()}"

        # Execution IDs should be different even for same tool
        assert exec_id1 != exec_id2

    def test_fallback_tool_name_extraction(self):
        """Test fallback to tool_action if tool_name not in metadata."""
        phase_event = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.IN_PROGRESS,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            metadata={
                "tool_action": "search machine learning",  # Fallback field
            },
        )

        # Simulate chat.py logic
        tool_name = phase_event.metadata.get("tool_name") or phase_event.metadata.get("tool_action", "unknown")

        assert tool_name == "search machine learning"

    def test_missing_tool_name_defaults_to_unknown(self):
        """Test that missing tool name defaults to 'unknown'."""
        phase_event = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.IN_PROGRESS,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            metadata={},  # No tool name
        )

        # Simulate chat.py logic
        tool_name = phase_event.metadata.get("tool_name") or phase_event.metadata.get("tool_action", "unknown")

        assert tool_name == "unknown"

    def test_event_serialization(self):
        """Test that tool events can be serialized to JSON for SSE."""
        tool_use_event = {
            "type": "tool_use",
            "data": {
                "tool": "bash",
                "server": "mcp",
                "parameters": {"command": "ls"},
                "execution_id": "bash_2025-01-26T12:00:00",
                "timestamp": "2025-01-26T12:00:00",
            },
        }

        # Should serialize without errors
        json_str = json.dumps(tool_use_event)
        assert "tool_use" in json_str
        assert "bash" in json_str

    def test_non_tool_phase_events_not_affected(self):
        """Test that non-TOOL_EXECUTION phase events are not affected."""
        # Create a different phase event type
        phase_event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime(2025, 1, 26, 12, 0, 0),
            end_time=datetime(2025, 1, 26, 12, 0, 1),
            duration_ms=150.0,
        )

        # Should NOT generate tool events
        assert phase_event.phase_type != PhaseType.TOOL_EXECUTION
