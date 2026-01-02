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


async def should_use_tools(state: dict[str, Any]) -> str:
    """Adaptive tool detection based on configuration.

    Sprint 70 Feature 70.11: LLM-based Tool Detection

    Routes to appropriate detection strategy based on admin configuration:
    - "markers": Fast marker-based detection (~0ms, legacy)
    - "llm": LLM-based intelligent detection (+50-200ms, smart)
    - "hybrid": Markers first, LLM fallback (balanced)

    Args:
        state: Current agent state with answer

    Returns:
        "tools" if tools should be used, "end" otherwise

    Examples:
        >>> state = {"answer": "[TOOL:search] machine learning"}
        >>> await should_use_tools(state)
        'tools'
    """
    from src.components.tools_config import get_tools_config_service

    # Load detection strategy from config
    try:
        config_service = get_tools_config_service()
        config = await config_service.get_config()
        strategy = config.tool_detection_strategy
    except Exception as e:
        logger.warning("failed_to_load_tool_detection_config", error=str(e))
        # Fallback to markers on error (safe default)
        strategy = "markers"

    # Route to appropriate strategy
    if strategy == "markers":
        return _should_use_tools_markers(state, config)
    elif strategy == "llm":
        return await _should_use_tools_llm(state, config)
    elif strategy == "hybrid":
        return await _should_use_tools_hybrid(state, config)
    else:
        logger.warning(
            "unknown_tool_detection_strategy",
            strategy=strategy,
            falling_back_to="markers"
        )
        return _should_use_tools_markers(state, config)


def _should_use_tools_markers(state: dict[str, Any], config: Any) -> str:
    """Marker-based tool detection (fast, ~0ms).

    Sprint 70 Feature 70.11: Marker-based Strategy

    Checks answer for explicit tool markers (e.g., "[TOOL:", "[SEARCH:").
    Fast but fragile - requires LLM to emit exact markers.

    Args:
        state: Current agent state with answer
        config: ToolsConfig with explicit_tool_markers list

    Returns:
        "tools" if marker found, "end" otherwise
    """
    answer = state.get("answer", "")

    # Use configured explicit markers
    explicit_markers = config.explicit_tool_markers

    for marker in explicit_markers:
        if marker in answer:
            logger.info("tool_use_detected_marker", marker=marker, answer_preview=answer[:100])
            return "tools"

    # No markers found
    logger.debug("tool_use_not_needed_markers")
    return "end"


async def _should_use_tools_llm(state: dict[str, Any], config: Any) -> str:
    """LLM-based tool detection (intelligent, +50-200ms).

    Sprint 70 Feature 70.11: LLM-based Strategy

    Uses LLM with structured output to intelligently decide if tools are needed.
    Understands context, nuances, and works multilingually.

    Args:
        state: Current agent state with answer and question
        config: ToolsConfig (unused in this strategy)

    Returns:
        "tools" if LLM decides tools needed, "end" otherwise
    """
    from pydantic import BaseModel, Field
    from langchain_core.prompts import ChatPromptTemplate
    from src.domains.llm_integration.streaming_client import get_llm_client

    # Define structured output schema
    class ToolDecision(BaseModel):
        """LLM decision on whether to use tools."""
        use_tools: bool = Field(description="True if external tools needed, False otherwise")
        reasoning: str = Field(description="Brief explanation why tools are/aren't needed")
        tool_type: str | None = Field(None, description="Type of tool: search, fetch, compute, etc.")
        query: str | None = Field(None, description="Specific query for tool if use_tools=True")

    answer = state.get("answer", "")
    question = state.get("question", "")

    # Create decision prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a tool usage classifier. Analyze the assistant's response and determine if external tools are needed.

Tools should be used when:
- Real-time data is needed (weather, stock prices, current events)
- Web search would provide better information
- External APIs need to be called
- File operations are required
- The answer indicates uncertainty that external data could resolve

Tools should NOT be used when:
- The answer can be given from existing context
- The question is conversational or opinion-based
- The information is general knowledge
- The assistant is providing a complete answer

Be conservative - only use tools when truly necessary."""),
        ("user", """Question: {question}

Assistant's Response: {answer}

Does this response require external tool use? Provide your decision.""")
    ])

    try:
        # Get LLM with structured output
        llm_client = get_llm_client()
        llm = llm_client.get_chat_model()
        structured_llm = llm.with_structured_output(ToolDecision)

        # Run decision
        chain = prompt | structured_llm
        decision: ToolDecision = await chain.ainvoke({
            "question": question,
            "answer": answer,
        })

        logger.info(
            "llm_tool_decision",
            use_tools=decision.use_tools,
            reasoning=decision.reasoning,
            tool_type=decision.tool_type,
        )

        if decision.use_tools:
            # Store tool query in state for tools_node
            state["tool_query"] = decision.query or answer
            state["tool_type"] = decision.tool_type
            return "tools"

        return "end"

    except Exception as e:
        logger.error("llm_tool_decision_failed", error=str(e), exc_info=True)
        # Fallback to "end" on error (safer than false positive)
        return "end"


async def _should_use_tools_hybrid(state: dict[str, Any], config: Any) -> str:
    """Hybrid tool detection (balanced, 0-200ms).

    Sprint 70 Feature 70.11: Hybrid Strategy

    Fast path: Check explicit markers first (~0ms)
    Slow path: Check action hints → LLM decision if hints present (~50-200ms)

    Balances speed (markers) with intelligence (LLM).

    Args:
        state: Current agent state with answer
        config: ToolsConfig with explicit_tool_markers and action_hint_phrases

    Returns:
        "tools" if marker found or LLM decides, "end" otherwise
    """
    answer = state.get("answer", "")

    # Fast path: Check explicit markers first
    explicit_markers = config.explicit_tool_markers
    for marker in explicit_markers:
        if marker in answer:
            logger.info("tool_use_detected_marker_fast_path", marker=marker)
            return "tools"

    # Slow path: Check for action hints
    action_hints = config.action_hint_phrases
    has_action_hint = any(hint.lower() in answer.lower() for hint in action_hints)

    if has_action_hint:
        # Invoke LLM for intelligent decision
        logger.info("tool_use_checking_with_llm_slow_path", hints_found=True)
        return await _should_use_tools_llm(state, config)

    # No markers, no hints → tools not needed
    logger.debug("tool_use_not_needed_hybrid")
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
