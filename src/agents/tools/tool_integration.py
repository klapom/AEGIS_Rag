"""Tool Integration for LangGraph ReAct Pattern.

Sprint 70 Feature 70.5: Tool Use in Normal Chat
Sprint 70 Feature 70.6: Tool Use in Deep Research
Sprint 70 Feature 70.9: Tool Result Streaming
Sprint 70 Feature 70.10: Tool Analytics & Monitoring

This module provides tool nodes and decision functions for integrating
MCP tools into the chat and research graphs using the ReAct pattern.
Includes real-time streaming of tool execution progress as phase events
and Prometheus metrics for operational monitoring.
"""

import time
from datetime import datetime
from typing import Any

from langgraph.types import StreamWriter

from src.agents.action_agent import ActionAgent
from src.components.mcp.client import MCPClient
from src.components.mcp.tool_executor import ToolExecutor
from src.core.logging import get_logger
from src.core.metrics import (
    decrement_active_tools,
    increment_active_tools,
    track_tool_execution,
)
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

logger = get_logger(__name__)

# Singleton MCP client instance
_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """Get or create singleton MCP client instance.

    Returns:
        MCPClient instance

    Examples:
        >>> client = get_mcp_client()
        >>> client is get_mcp_client()
        True
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


def should_use_tools(state: dict[str, Any]) -> str:
    """Conditional edge: Decide if tools should be used.

    Args:
        state: Current agent state with answer

    Returns:
        "tools" if tools should be used, "end" otherwise

    Examples:
        >>> state = {"answer": "Let me search for that..."}
        >>> should_use_tools(state)
        'end'
    """
    answer = state.get("answer", "")

    # Check for tool call indicators
    # This is a simple heuristic - can be enhanced with LLM decision
    tool_indicators = [
        "[TOOL:",  # Explicit tool marker
        "[SEARCH:",  # Search request
        "[FETCH:",  # Data fetch request
        "I need to",  # Action indicator
        "Let me check",  # External check
        "I'll need to access",  # Access requirement
    ]

    for indicator in tool_indicators:
        if indicator in answer:
            logger.info("tool_use_detected", indicator=indicator, answer_preview=answer[:100])
            return "tools"

    # Default: no tools needed
    return "end"


async def tools_node(
    state: dict[str, Any],
    *,
    writer: StreamWriter | None = None,
) -> dict[str, Any]:
    """Execute MCP tools using ActionAgent with real-time streaming.

    **Sprint 70 Feature 70.9: Tool Result Streaming**

    Emits phase events during tool execution for real-time progress tracking:
    1. TOOL_EXECUTION IN_PROGRESS - Tool execution started
    2. TOOL_EXECUTION COMPLETED - Tool execution finished successfully
    3. TOOL_EXECUTION FAILED - Tool execution encountered error

    Args:
        state: Current agent state with answer containing tool request
        writer: Optional StreamWriter for emitting phase events

    Returns:
        Updated state with tool results added to contexts

    Examples:
        >>> state = {"answer": "[TOOL:search] query", "retrieved_contexts": []}
        >>> result = await tools_node(state)
        >>> len(result["retrieved_contexts"]) > 0
        True
    """
    logger.info("tools_node_start", answer_preview=state.get("answer", "")[:100])

    # Extract tool request from answer
    answer = state.get("answer", "")
    tool_request = _extract_tool_request(answer)

    if not tool_request:
        logger.warning("no_tool_request_found", answer=answer[:200])
        # Return state unchanged if no valid tool request
        return {}

    # Track timing
    start_time = time.perf_counter()
    start_datetime = datetime.now()

    # Sprint 70 Feature 70.10: Increment active tool executions
    increment_active_tools()

    # Sprint 70 Feature 70.9: Emit IN_PROGRESS event
    if writer:
        in_progress_event = PhaseEvent(
            phase_type=PhaseType.TOOL_EXECUTION,
            status=PhaseStatus.IN_PROGRESS,
            start_time=start_datetime,
            metadata={
                "tool_action": tool_request["action"],
                "parameters": tool_request.get("parameters", {}),
            },
        )
        writer(in_progress_event.model_dump())
        logger.debug("tool_execution_phase_event_emitted", status="in_progress")

    try:
        # Initialize ActionAgent
        mcp_client = get_mcp_client()
        tool_executor = ToolExecutor(mcp_client)
        action_agent = ActionAgent(mcp_client, tool_executor)

        # Execute tool via ActionAgent graph
        result = await action_agent.graph.ainvoke(
            {
                "action": tool_request["action"],
                "parameters": tool_request.get("parameters", {}),
                "messages": [],
            }
        )

        # Extract tool result
        tool_result_text = result.get("tool_result", {})
        if isinstance(tool_result_text, dict):
            tool_result_text = str(tool_result_text)

        # Calculate duration
        end_time = time.perf_counter()
        end_datetime = datetime.now()
        duration_ms = (end_time - start_time) * 1000

        # Create tool context for re-generation
        tool_context = {
            "text": tool_result_text,
            "source": "tool",
            "tool_name": result.get("selected_tool", "unknown"),
            "score": 1.0,  # Tools always relevant
            "source_channel": "tool_execution",
        }

        # Add tool result to contexts
        contexts = state.get("retrieved_contexts", [])
        contexts.append(tool_context)

        tool_name = result.get("selected_tool", "unknown")

        logger.info(
            "tool_execution_success",
            tool_name=tool_name,
            result_length=len(tool_result_text),
            duration_ms=duration_ms,
        )

        # Sprint 70 Feature 70.10: Track successful execution
        track_tool_execution(
            tool_name=tool_name,
            status="success",
            duration_seconds=duration_ms / 1000,
        )
        decrement_active_tools()

        # Sprint 70 Feature 70.9: Emit COMPLETED event
        if writer:
            completed_event = PhaseEvent(
                phase_type=PhaseType.TOOL_EXECUTION,
                status=PhaseStatus.COMPLETED,
                start_time=start_datetime,
                end_time=end_datetime,
                duration_ms=duration_ms,
                metadata={
                    "tool_action": tool_request["action"],
                    "tool_name": result.get("selected_tool", "unknown"),
                    "result_length": len(tool_result_text),
                    "result_preview": tool_result_text[:200] if tool_result_text else "",
                },
            )
            writer(completed_event.model_dump())
            logger.debug("tool_execution_phase_event_emitted", status="completed")

        return {
            "retrieved_contexts": contexts,
            "tool_execution_count": state.get("tool_execution_count", 0) + 1,
        }

    except Exception as e:
        # Calculate duration
        end_time = time.perf_counter()
        end_datetime = datetime.now()
        duration_ms = (end_time - start_time) * 1000

        tool_name = tool_request.get("action", "unknown")

        logger.error(
            "tool_execution_failed",
            tool_name=tool_name,
            error=str(e),
            exc_info=True,
            duration_ms=duration_ms,
        )

        # Sprint 70 Feature 70.10: Track failed execution
        track_tool_execution(
            tool_name=tool_name,
            status="failed",
            duration_seconds=duration_ms / 1000,
        )
        decrement_active_tools()

        # Sprint 70 Feature 70.9: Emit FAILED event
        if writer:
            failed_event = PhaseEvent(
                phase_type=PhaseType.TOOL_EXECUTION,
                status=PhaseStatus.FAILED,
                start_time=start_datetime,
                end_time=end_datetime,
                duration_ms=duration_ms,
                metadata={
                    "tool_action": tool_request["action"],
                    "tool_name": tool_request.get("action", "unknown"),
                },
                error=str(e),
            )
            writer(failed_event.model_dump())
            logger.debug("tool_execution_phase_event_emitted", status="failed")

        # Add error context
        error_context = {
            "text": f"Tool execution failed: {str(e)}",
            "source": "tool_error",
            "tool_name": tool_request.get("action", "unknown"),
            "score": 0.5,
            "source_channel": "tool_execution",
        }

        contexts = state.get("retrieved_contexts", [])
        contexts.append(error_context)

        return {
            "retrieved_contexts": contexts,
            "tool_execution_count": state.get("tool_execution_count", 0) + 1,
        }


def _extract_tool_request(answer: str) -> dict[str, Any] | None:
    """Extract tool request from answer text.

    Args:
        answer: LLM answer with potential tool markers

    Returns:
        Dict with action and parameters, or None if no tool request

    Examples:
        >>> _extract_tool_request("[TOOL:search] machine learning")
        {'action': 'search machine learning', 'parameters': {}}

        >>> _extract_tool_request("[FETCH:url] https://example.com")
        {'action': 'fetch url https://example.com', 'parameters': {}}

        >>> _extract_tool_request("Normal answer")
        None
    """
    # Simple extraction logic - can be enhanced with regex or LLM parsing
    if "[TOOL:" in answer:
        start = answer.index("[TOOL:") + 6
        end = answer.index("]", start) if "]" in answer[start:] else len(answer)
        action = answer[start:end].strip()
        return {"action": action, "parameters": {}}

    if "[SEARCH:" in answer:
        start = answer.index("[SEARCH:") + 8
        end = answer.index("]", start) if "]" in answer[start:] else len(answer)
        query = answer[start:end].strip()
        return {"action": f"search {query}", "parameters": {}}

    if "[FETCH:" in answer:
        start = answer.index("[FETCH:") + 7
        end = answer.index("]", start) if "]" in answer[start:] else len(answer)
        url = answer[start:end].strip()
        return {"action": f"fetch url {url}", "parameters": {}}

    return None
