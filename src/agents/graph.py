"""LangGraph Base Graph Implementation.

This module defines the base graph structure for the multi-agent RAG system.
The graph orchestrates query routing and agent coordination.

Sprint 4 Features 4.1-4.4: Base Graph Structure with State Persistence
Sprint 5 Feature 5.5: Graph Query Agent Integration
Sprint 42: True Hybrid Mode - Vector + Graph parallel execution
Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP) - LLM Generation
Implements the foundational graph with optional checkpointing for conversation history.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.graph_query_agent import graph_query_node
from src.agents.memory_agent import memory_node
from src.agents.phase_events_queue import stream_citation_map, stream_phase_event, stream_token
from src.agents.router import route_query as router_node_with_phase_events
from src.agents.state import AgentState, create_initial_state
from src.agents.vector_search_agent import vector_search_node
from src.core.logging import get_logger
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType

logger = get_logger(__name__)


# Sprint 48: Use instrumented router from router.py with phase events
router_node = router_node_with_phase_events


async def llm_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate LLM-based answer with inline source citations and token streaming.

    Sprint 11 Feature 11.1: Replaces simple_answer_node with proper LLM generation.
    Sprint 27 Feature 27.10: Inline Source Citations
    Sprint 48 Feature 48.3: Emits phase events for LLM generation.
    Sprint 51 Feature 51.1: Adds phase events to list for streaming.
    Sprint 52: Real-time phase event emission via LangGraph stream_writer.
    Sprint 52: Token-by-token streaming to chat window.
    Sprint 80 Feature 80.1: Strict faithfulness mode for RAGAS optimization.
    Uses AnswerGenerator to synthesize answers with citation markers [1], [2], etc.

    Args:
        state: Current agent state with retrieved_contexts

    Returns:
        State with generated answer in messages, citation_map, and phase_event
    """
    from src.agents.answer_generator import get_answer_generator
    from src.core.config import settings

    query = state.get("query", "")
    contexts = state.get("retrieved_contexts", [])
    # Sprint 69 Feature 69.3: Get intent for model selection
    intent = state.get("intent")
    # Sprint 80 Feature 80.1: Get strict_faithfulness from state or global config
    strict_faithfulness = state.get("strict_faithfulness", settings.strict_faithfulness_enabled)
    # Sprint 81 Feature 81.8: Get no_hedging from state or global config
    no_hedging = state.get("no_hedging", settings.no_hedging_enabled)

    logger.info(
        "llm_answer_node_start",
        query=query[:100],
        contexts_count=len(contexts),
        intent=intent,
        strict_faithfulness=strict_faithfulness,
        no_hedging=no_hedging,
    )

    # Initialize phase_events list if not present
    if "phase_events" not in state:
        state["phase_events"] = []

    # Sprint 52: Emit IN_PROGRESS event immediately via LangGraph stream
    stream_phase_event(
        phase_type=PhaseType.LLM_GENERATION,
        status=PhaseStatus.IN_PROGRESS,
    )

    # Create phase event for LLM generation
    event = PhaseEvent(
        phase_type=PhaseType.LLM_GENERATION,
        status=PhaseStatus.IN_PROGRESS,
        start_time=datetime.utcnow(),
    )

    try:
        # Generate answer with inline citations and streaming (Sprint 52)
        generator = get_answer_generator()

        # Sprint 52: Stream tokens in real-time to chat window
        # Sprint 69 Feature 69.3: Pass intent for model selection
        # Sprint 80 Feature 80.1: Pass strict_faithfulness for citation enforcement
        answer = ""
        citation_map = {}

        # Sprint 81 Feature 81.8: Pass no_hedging to eliminate meta-commentary
        async for token_event in generator.generate_with_citations_streaming(
            query, contexts, intent=intent, strict_faithfulness=strict_faithfulness, no_hedging=no_hedging
        ):
            event_type = token_event.get("event")

            if event_type == "citation_map":
                # Citation map is sent first - emit via stream
                citation_map = token_event.get("data", {})
                stream_citation_map(citation_map)

            elif event_type == "token":
                # Stream each token to the UI in real-time
                token_content = token_event.get("data", {}).get("content", "")
                if token_content:
                    stream_token(token_content)

            elif event_type == "complete":
                # Final answer with full text
                answer = token_event.get("data", {}).get("answer", "")
                citation_map = token_event.get("data", {}).get("citation_map", citation_map)

            elif event_type == "error":
                # Log error but continue (fallback will follow)
                error_msg = token_event.get("data", {}).get("error", "Unknown error")
                logger.warning("llm_streaming_error", error=error_msg)

        # Add to messages (LangGraph format)
        if "messages" not in state:
            state["messages"] = []

        state["messages"].append({"role": "assistant", "content": answer})

        # Also add as direct field for easier access
        state["answer"] = answer

        # Store citation map for API response (Sprint 27 Feature 27.10)
        state["citation_map"] = citation_map

        # Update phase event with success
        event.status = PhaseStatus.COMPLETED
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000
        event.metadata = {
            "answer_length": len(answer),
            "contexts_used": len(contexts),
            "citations_count": len(citation_map),
            "streaming": True,  # Sprint 52: Mark as streamed
        }

        # Sprint 52: Emit COMPLETED event via LangGraph stream
        stream_phase_event(
            phase_type=PhaseType.LLM_GENERATION,
            status=PhaseStatus.COMPLETED,
            duration_ms=event.duration_ms,
            metadata=event.metadata,
        )

        # Sprint 51 Feature 51.1: Add to phase_events list
        state["phase_events"].append(event)
        # Also add as phase_event for backward compatibility
        state["phase_event"] = event

        logger.info(
            "llm_answer_node_complete",
            answer_length=len(answer),
            contexts_used=len(contexts),
            citations_count=len(citation_map),
            duration_ms=event.duration_ms,
            streaming=True,
        )

        return state

    except Exception as e:
        # Mark phase event as failed
        event.status = PhaseStatus.FAILED
        event.error = str(e)
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        # Sprint 51 Feature 51.1: Add to phase_events list
        state["phase_events"].append(event)
        # Also add as phase_event for backward compatibility
        state["phase_event"] = event

        logger.error(
            "llm_answer_node_failed",
            error=str(e),
            duration_ms=event.duration_ms,
        )

        # Re-raise to let error handling take over
        raise


async def hybrid_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """Execute Vector search with 4-way hybrid retrieval.

    Sprint 42: True Hybrid Mode - combines vector semantic search with
    graph entity/relationship search for comprehensive retrieval.
    Sprint 48 Feature 48.3: Emits phase events for hybrid search phases.
    Sprint 52: Real-time phase event emission via LangGraph stream_writer.

    Sprint 115 ADR-057: DISABLED graph_query_node (SmartEntityExpander)
    - graph_query_node adds ~26s latency via 2 LLM calls in SmartEntityExpander
    - vector_search_node already includes 4-way hybrid via FourWayHybridSearch:
      * Dense vectors (BGE-M3 semantic)
      * Sparse vectors (BGE-M3 lexical)
      * Graph Local (term-matching via Cypher, ~100ms)
      * Graph Global (community-based, ~100ms)
    - Removing redundant graph_query_node reduces query time from 27s to <2s

    Args:
        state: Current agent state

    Returns:
        State with retrieved_contexts from 4-way hybrid search and phase_event
    """
    logger.info("hybrid_search_node_start", query=state.get("query", "")[:100])

    # Sprint 52: Track start times for accurate duration measurement
    vector_start = time.perf_counter()

    # Sprint 52: Emit IN_PROGRESS event for vector search (includes 4-way hybrid)
    stream_phase_event(
        phase_type=PhaseType.BM25_SEARCH,
        status=PhaseStatus.IN_PROGRESS,
    )

    # Sprint 115 ADR-057: Only run vector_search_node (already includes 4-way hybrid)
    # graph_query_node DISABLED - was redundant and added ~26s latency
    vector_task = asyncio.create_task(vector_search_node(state.copy()))

    # Sprint 115 ADR-057: Simplified - only wait for vector_task
    # (graph_query_node disabled - was redundant, added ~26s latency)
    try:
        vector_result = await vector_task
        duration_ms = (time.perf_counter() - vector_start) * 1000
        count = len(vector_result.get("retrieved_contexts", [])) if isinstance(vector_result, dict) else 0

        stream_phase_event(
            phase_type=PhaseType.BM25_SEARCH,
            status=PhaseStatus.COMPLETED,
            duration_ms=duration_ms,
            metadata={"results_count": count},
        )
        logger.info("hybrid_vector_results", count=count, duration_ms=duration_ms)
    except Exception as e:
        duration_ms = (time.perf_counter() - vector_start) * 1000
        stream_phase_event(
            phase_type=PhaseType.BM25_SEARCH,
            status=PhaseStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e),
        )
        vector_result = e
        logger.warning("hybrid_vector_failed", error=str(e))

    # Sprint 115 ADR-057: No graph_result - graph search is handled by FourWayHybridSearch
    # inside vector_search_node (channels: graph_local, graph_global)
    merged_contexts = []

    # Add vector results (includes 4-way hybrid: dense, sparse, graph_local, graph_global)
    if isinstance(vector_result, dict):
        vector_contexts = vector_result.get("retrieved_contexts", [])
        for ctx in vector_contexts:
            # Keep original search_type from FourWayHybridSearch (vector/graph_local/graph_global)
            if "search_type" not in ctx:
                ctx["search_type"] = "hybrid"
            merged_contexts.append(ctx)
    else:
        logger.warning("hybrid_search_no_results", error=str(vector_result))

    # Sprint 52: Emit RRF fusion IN_PROGRESS via LangGraph stream
    stream_phase_event(
        phase_type=PhaseType.RRF_FUSION,
        status=PhaseStatus.IN_PROGRESS,
    )

    # Sprint 48 Feature 48.3: Create phase event for RRF fusion
    fusion_event = PhaseEvent(
        phase_type=PhaseType.RRF_FUSION,
        status=PhaseStatus.IN_PROGRESS,
        start_time=datetime.utcnow(),
    )

    try:
        # Deduplicate by text content (keep first occurrence)
        seen_texts = set()
        unique_contexts = []
        for ctx in merged_contexts:
            text = ctx.get("text", "")[:200]  # Use first 200 chars for dedup
            if text not in seen_texts:
                seen_texts.add(text)
                unique_contexts.append(ctx)

        state["retrieved_contexts"] = unique_contexts

        # Update metadata
        if "metadata" not in state:
            state["metadata"] = {}

        # Sprint 115 ADR-057: vector_count now includes all 4-way hybrid results
        # (dense, sparse, graph_local, graph_global) since FourWayHybridSearch does the fusion
        hybrid_count = (
            len(vector_result.get("retrieved_contexts", []))
            if isinstance(vector_result, dict)
            else 0
        )

        # Sprint 115: Extract channel counts from FourWayHybridSearch metadata if available
        search_metadata = (
            vector_result.get("metadata", {}).get("search", {})
            if isinstance(vector_result, dict)
            else {}
        )

        state["metadata"]["hybrid_search"] = {
            "hybrid_count": hybrid_count,  # Total from 4-way hybrid
            "merged_count": len(unique_contexts),
            # Channel counts from FourWayHybridSearch (if available)
            "dense_count": search_metadata.get("dense_results_count", 0),
            "sparse_count": search_metadata.get("sparse_results_count", 0),
            "graph_local_count": search_metadata.get("graph_local_results_count", 0),
            "graph_global_count": search_metadata.get("graph_global_results_count", 0),
            # Legacy field for backward compatibility
            "vector_count": hybrid_count,
            "graph_count": 0,  # Deprecated: graph now inside FourWayHybridSearch
        }

        # Complete fusion phase event
        fusion_event.status = PhaseStatus.COMPLETED
        fusion_event.end_time = datetime.utcnow()
        fusion_event.duration_ms = (
            fusion_event.end_time - fusion_event.start_time
        ).total_seconds() * 1000
        fusion_event.metadata = {
            "hybrid_count": hybrid_count,
            "merged_count": len(unique_contexts),
        }

        # Sprint 52: Emit COMPLETED event via LangGraph stream
        stream_phase_event(
            phase_type=PhaseType.RRF_FUSION,
            status=PhaseStatus.COMPLETED,
            duration_ms=fusion_event.duration_ms,
            metadata=fusion_event.metadata,
        )

        # Add phase event to state
        state["phase_event"] = fusion_event

        logger.info(
            "hybrid_search_node_complete",
            total_contexts=len(unique_contexts),
            duration_ms=fusion_event.duration_ms,
        )

        return state

    except Exception as e:
        # Mark phase event as failed
        fusion_event.status = PhaseStatus.FAILED
        fusion_event.error = str(e)
        fusion_event.end_time = datetime.utcnow()
        fusion_event.duration_ms = (
            fusion_event.end_time - fusion_event.start_time
        ).total_seconds() * 1000

        # Add failed phase event to state
        state["phase_event"] = fusion_event

        logger.error("hybrid_search_node_failed", error=str(e))
        raise


def route_query(
    state: dict[str, Any],
) -> Literal["hybrid_search", "vector_search", "graph", "memory", "end"]:
    """Determine the next node based on intent.

    This is a conditional edge function that determines routing.
    Sprint 42: Routes HYBRID to parallel vector+graph search.
    Routes GRAPH intent to graph_query node (Sprint 5 Feature 5.5).
    Routes MEMORY intent to memory node (Sprint 7 Feature 7.4).
    Routes VECTOR to vector_search only.

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    intent = state.get("intent", "hybrid")
    route_decision = state.get("route_decision", intent)

    logger.info("routing_decision", intent=intent, route=route_decision)

    # Sprint 42: Route HYBRID to parallel vector+graph search
    if route_decision.lower() == "hybrid":
        logger.info("routing_to_hybrid_search", intent=intent)
        return "hybrid_search"

    # Sprint 5: Route GRAPH intent to graph_query node
    if route_decision.lower() == "graph":
        logger.info("routing_to_graph_query", intent=intent)
        return "graph"

    # Sprint 7: Route MEMORY intent to memory node
    if route_decision.lower() == "memory":
        logger.info("routing_to_memory", intent=intent)
        return "memory"

    # Route vector to vector_search node only
    logger.info("routing_to_vector_search", intent=intent)
    return "vector_search"


def create_base_graph(enable_tools: bool = False) -> StateGraph:
    """Create the base LangGraph structure.

    This creates the foundational graph with:
    - START node
    - Router node for query classification
    - Hybrid search node (Sprint 42: parallel vector+graph)
    - Vector search node
    - Graph query node (Sprint 5 Feature 5.5)
    - Memory node (Sprint 7 Feature 7.4)
    - Conditional edges for routing
    - Tool use support (Sprint 70 Feature 70.5)
    - END node

    Args:
        enable_tools: Enable tool use with ReAct pattern (default: False)

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("creating_base_graph", enable_tools=enable_tools)

    # Initialize graph with AgentState schema
    graph = StateGraph(AgentState)

    # Add router node
    graph.add_node("router", router_node)

    # Sprint 42: Add hybrid search node (parallel vector+graph)
    graph.add_node("hybrid_search", hybrid_search_node)

    # Sprint 4: Add vector search node
    graph.add_node("vector_search", vector_search_node)

    # Sprint 5: Add graph query node
    graph.add_node("graph_query", graph_query_node)

    # Sprint 7: Add memory node
    graph.add_node("memory", memory_node)

    # Sprint 11: Add LLM-based answer generator node (replaces simple_answer_node)
    graph.add_node("answer", llm_answer_node)

    # Sprint 70 Feature 70.5: Add tool use support (ReAct pattern)
    if enable_tools:
        from src.agents.tools import should_use_tools, tools_node

        graph.add_node("tools", tools_node)

    # Add edge from START to router
    graph.add_edge(START, "router")

    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        route_query,
        {
            "hybrid_search": "hybrid_search",  # Sprint 42: Parallel vector+graph
            "vector_search": "vector_search",  # Vector only
            "graph": "graph_query",  # Sprint 5: Graph only
            "memory": "memory",  # Sprint 7: Memory agent
            "end": END,
        },
    )

    # Sprint 42: Connect hybrid_search to answer generator
    graph.add_edge("hybrid_search", "answer")

    # Sprint 10: Connect vector_search to answer generator
    graph.add_edge("vector_search", "answer")

    # Sprint 79 Fix: Connect graph_query to answer generator (was going to END)
    # graph_query retrieves contexts but does NOT generate answers
    graph.add_edge("graph_query", "answer")

    # Sprint 7: Connect memory to END
    graph.add_edge("memory", END)

    # Sprint 70 Feature 70.5: Add tool use edges (ReAct pattern)
    if enable_tools:
        from src.agents.tools import should_use_tools

        # Conditional edge: answer → [tools | END]
        graph.add_conditional_edges(
            "answer",
            should_use_tools,
            {
                "tools": "tools",  # Use tools
                "end": END,  # No tools needed
            },
        )
        # Cycle: tools → answer (for multi-turn tool conversations)
        graph.add_edge("tools", "answer")
    else:
        # Sprint 10: Connect answer to END (original behavior)
        graph.add_edge("answer", END)

    nodes = ["router", "hybrid_search", "vector_search", "graph_query", "memory", "answer"]
    if enable_tools:
        nodes.append("tools")

    logger.info("base_graph_created", nodes=nodes, enable_tools=enable_tools)

    return graph


async def compile_graph_with_tools_config(checkpointer: MemorySaver | None = None) -> Any:
    """Compile the graph with tool configuration from Redis.

    **Sprint 70 Feature 70.7: Dynamic Tool Configuration**

    Loads tool configuration from Redis and compiles graph accordingly.
    This allows hot-reloading of tool settings without service restart.

    Args:
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled graph with tool configuration applied

    Example:
        >>> checkpointer = create_checkpointer()
        >>> compiled = await compile_graph_with_tools_config(checkpointer=checkpointer)
        >>> # Tools enabled/disabled based on admin config
    """
    from src.components.tools_config import get_tools_config_service

    # Load tool configuration
    config_service = get_tools_config_service()
    tools_config = await config_service.get_config()

    enable_tools = tools_config.enable_chat_tools

    logger.info(
        "compiling_graph_with_config",
        enable_tools=enable_tools,
        with_checkpointer=checkpointer is not None,
    )

    graph = create_base_graph(enable_tools=enable_tools)

    # Compile with optional checkpointer
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("graph_compiled_with_persistence", enable_tools=enable_tools)
    else:
        compiled = graph.compile()
        logger.info("graph_compiled_stateless", enable_tools=enable_tools)

    return compiled


def compile_graph(
    checkpointer: MemorySaver | None = None,
    enable_tools: bool = False,
) -> Any:
    """Compile the base graph for execution.

    **Sprint 70 Feature 70.7: Optional Tool Support**

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     If provided, enables conversation history across invocations.
                     Use create_checkpointer() from checkpointer module.
        enable_tools: Enable MCP tool use (default: False)
                     For admin-configured tools, use compile_graph_with_tools_config()

    Returns:
        Compiled graph ready for invocation

    Example:
        >>> from src.agents.checkpointer import create_checkpointer
        >>> checkpointer = create_checkpointer()
        >>> compiled = compile_graph(checkpointer=checkpointer)
        >>> # State persists across invocations with same thread_id

        >>> # With tools enabled
        >>> compiled = compile_graph(checkpointer=checkpointer, enable_tools=True)
    """
    logger.info(
        "compiling_graph",
        with_checkpointer=checkpointer is not None,
        enable_tools=enable_tools,
    )

    graph = create_base_graph(enable_tools=enable_tools)

    # Compile with optional checkpointer
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("graph_compiled_with_persistence", enable_tools=enable_tools)
    else:
        compiled = graph.compile()
        logger.info("graph_compiled_stateless", enable_tools=enable_tools)

    return compiled


async def invoke_graph(
    query: str,
    intent: str = "hybrid",
    checkpointer: MemorySaver | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the graph with a query.

    This is a convenience function for invoking the graph.

    Args:
        query: User query string
        intent: Query intent (default: "hybrid")
        checkpointer: Optional checkpointer for state persistence
        config: Optional configuration (e.g., thread_id for session tracking)

    Returns:
        Final state after graph execution

    Example:
        >>> from src.agents.checkpointer import create_checkpointer, create_thread_config
        >>> checkpointer = create_checkpointer()
        >>> config = create_thread_config("session123")
        >>> result = await invoke_graph(query, checkpointer=checkpointer, config=config)
    """
    logger.info(
        "invoking_graph",
        query=query,
        intent=intent,
        with_persistence=checkpointer is not None,
        session_id=config.get("configurable", {}).get("thread_id") if config else None,
    )

    # Create initial state
    initial_state = create_initial_state(query, intent)

    # Compile and invoke graph
    compiled_graph = compile_graph(checkpointer=checkpointer)
    final_state = await compiled_graph.ainvoke(initial_state, config=config)

    logger.info(
        "graph_execution_complete",
        query=query,
        agent_path=final_state.get("metadata", {}).get("agent_path", []),
    )

    return final_state


# Export for convenience
__all__ = [
    "create_base_graph",
    "compile_graph",
    "invoke_graph",
    "router_node",
    "route_query",
]
