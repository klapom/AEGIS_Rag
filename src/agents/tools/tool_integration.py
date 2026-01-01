"""Tool Integration for LangGraph ReAct Pattern.

Sprint 70 Feature 70.5: Tool Use in Normal Chat
Sprint 70 Feature 70.6: Tool Use in Deep Research

This module provides tool nodes and decision functions for integrating
MCP tools into the chat and research graphs using the ReAct pattern.
"""

from typing import Any

from src.agents.action_agent import ActionAgent
from src.components.mcp.client import MCPClient
from src.components.mcp.tool_executor import ToolExecutor
from src.core.logging import get_logger

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


async def tools_node(state: dict[str, Any]) -> dict[str, Any]:
    """Execute MCP tools using ActionAgent.

    Args:
        state: Current agent state with answer containing tool request

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

        logger.info(
            "tool_execution_success",
            tool_name=result.get("selected_tool"),
            result_length=len(tool_result_text),
        )

        return {
            "retrieved_contexts": contexts,
            "tool_execution_count": state.get("tool_execution_count", 0) + 1,
        }

    except Exception as e:
        logger.error("tool_execution_failed", error=str(e), exc_info=True)

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
