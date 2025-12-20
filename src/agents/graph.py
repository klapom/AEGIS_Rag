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
    Uses AnswerGenerator to synthesize answers with citation markers [1], [2], etc.

    Args:
        state: Current agent state with retrieved_contexts

    Returns:
        State with generated answer in messages, citation_map, and phase_event
    """
    from src.agents.answer_generator import get_answer_generator

    query = state.get("query", "")
    contexts = state.get("retrieved_contexts", [])

    logger.info("llm_answer_node_start", query=query[:100], contexts_count=len(contexts))

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
        answer = ""
        citation_map = {}

        async for token_event in generator.generate_with_citations_streaming(query, contexts):
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
    """Execute Vector + Graph search in parallel and merge results.

    Sprint 42: True Hybrid Mode - combines vector semantic search with
    graph entity/relationship search for comprehensive retrieval.
    Sprint 48 Feature 48.3: Emits phase events for hybrid search phases.
    Sprint 52: Real-time phase event emission via LangGraph stream_writer.
              Uses asyncio.wait(FIRST_COMPLETED) to emit events as each task finishes.

    Args:
        state: Current agent state

    Returns:
        State with merged retrieved_contexts from both searches and phase_event
    """
    logger.info("hybrid_search_node_start", query=state.get("query", "")[:100])

    # Sprint 52: Track start times for accurate duration measurement
    bm25_start = time.perf_counter()
    graph_start = time.perf_counter()

    # Sprint 52: Emit IN_PROGRESS events for parallel searches via LangGraph stream
    stream_phase_event(
        phase_type=PhaseType.BM25_SEARCH,
        status=PhaseStatus.IN_PROGRESS,
    )
    stream_phase_event(
        phase_type=PhaseType.GRAPH_QUERY,
        status=PhaseStatus.IN_PROGRESS,
    )

    # Run both searches in parallel
    vector_task = asyncio.create_task(vector_search_node(state.copy()))
    graph_task = asyncio.create_task(graph_query_node(state.copy()))

    # Sprint 52: Use asyncio.wait with FIRST_COMPLETED to emit events as each task finishes
    # This gives real-time feedback instead of waiting for both
    task_info = {
        vector_task: (PhaseType.BM25_SEARCH, bm25_start),
        graph_task: (PhaseType.GRAPH_QUERY, graph_start),
    }
    results = {}
    pending = {vector_task, graph_task}

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            phase_type, start_time = task_info[task]
            duration_ms = (time.perf_counter() - start_time) * 1000

            try:
                result = task.result()
                count = len(result.get("retrieved_contexts", [])) if isinstance(result, dict) else 0
                stream_phase_event(
                    phase_type=phase_type,
                    status=PhaseStatus.COMPLETED,
                    duration_ms=duration_ms,
                    metadata={"results_count": count},
                )
                results[task] = result
            except Exception as e:
                stream_phase_event(
                    phase_type=phase_type,
                    status=PhaseStatus.FAILED,
                    duration_ms=duration_ms,
                    error=str(e),
                )
                results[task] = e

    # Extract results
    vector_result = results.get(vector_task)
    graph_result = results.get(graph_task)

    # Merge retrieved contexts
    merged_contexts = []

    # Add vector results
    if isinstance(vector_result, dict):
        vector_contexts = vector_result.get("retrieved_contexts", [])
        for ctx in vector_contexts:
            ctx["search_type"] = "vector"
            merged_contexts.append(ctx)
        logger.info("hybrid_vector_results", count=len(vector_contexts))
    else:
        logger.warning("hybrid_vector_failed", error=str(vector_result))

    # Add graph results
    if isinstance(graph_result, dict):
        graph_contexts = graph_result.get("retrieved_contexts", [])
        for ctx in graph_contexts:
            ctx["search_type"] = "graph"
            merged_contexts.append(ctx)
        logger.info("hybrid_graph_results", count=len(graph_contexts))
    else:
        logger.warning("hybrid_graph_failed", error=str(graph_result))

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

        vector_count = (
            len(vector_result.get("retrieved_contexts", []))
            if isinstance(vector_result, dict)
            else 0
        )
        graph_count = (
            len(graph_result.get("retrieved_contexts", [])) if isinstance(graph_result, dict) else 0
        )

        state["metadata"]["hybrid_search"] = {
            "vector_count": vector_count,
            "graph_count": graph_count,
            "merged_count": len(unique_contexts),
        }

        # Complete fusion phase event
        fusion_event.status = PhaseStatus.COMPLETED
        fusion_event.end_time = datetime.utcnow()
        fusion_event.duration_ms = (
            fusion_event.end_time - fusion_event.start_time
        ).total_seconds() * 1000
        fusion_event.metadata = {
            "vector_count": vector_count,
            "graph_count": graph_count,
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


def create_base_graph() -> StateGraph:
    """Create the base LangGraph structure.

    This creates the foundational graph with:
    - START node
    - Router node for query classification
    - Hybrid search node (Sprint 42: parallel vector+graph)
    - Vector search node
    - Graph query node (Sprint 5 Feature 5.5)
    - Memory node (Sprint 7 Feature 7.4)
    - Conditional edges for routing
    - END node

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("creating_base_graph")

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

    # Sprint 5: Connect graph_query to END (has its own answer generation)
    graph.add_edge("graph_query", END)

    # Sprint 7: Connect memory to END
    graph.add_edge("memory", END)

    # Sprint 10: Connect answer to END
    graph.add_edge("answer", END)

    logger.info(
        "base_graph_created",
        nodes=["router", "hybrid_search", "vector_search", "graph_query", "memory", "answer"],
    )

    return graph


def compile_graph(checkpointer: MemorySaver | None = None) -> Any:
    """Compile the base graph for execution.

    Args:
        checkpointer: Optional checkpointer for state persistence.
                     If provided, enables conversation history across invocations.
                     Use create_checkpointer() from checkpointer module.

    Returns:
        Compiled graph ready for invocation

    Example:
        >>> from src.agents.checkpointer import create_checkpointer
        >>> checkpointer = create_checkpointer()
        >>> compiled = compile_graph(checkpointer=checkpointer)
        >>> # State persists across invocations with same thread_id
    """
    logger.info(
        "compiling_graph",
        with_checkpointer=checkpointer is not None,
    )

    graph = create_base_graph()

    # Compile with optional checkpointer
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
        logger.info("graph_compiled_with_persistence")
    else:
        compiled = graph.compile()
        logger.info("graph_compiled_stateless")

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
