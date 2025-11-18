"""LangGraph Base Graph Implementation.

This module defines the base graph structure for the multi-agent RAG system.
The graph orchestrates query routing and agent coordination.

Sprint 4 Features 4.1-4.4: Base Graph Structure with State Persistence
Sprint 5 Feature 5.5: Graph Query Agent Integration
Implements the foundational graph with optional checkpointing for conversation history.
"""

from typing import Any, Literal, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.graph_query_agent import graph_query_node
from src.agents.memory_agent import memory_node
from src.agents.state import AgentState, create_initial_state
from src.agents.vector_search_agent import vector_search_node
from src.core.logging import get_logger

logger = get_logger(__name__)


async def router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Route queries based on intent.

    This is a placeholder router that will be enhanced in Feature 4.2.
    Currently returns the state unchanged with routing metadata.

    Args:
        state: Current agent state

    Returns:
        State with routing decision added
    """
    logger.info(
        "router_processing",
        query=state.get("query", ""),
        intent=state.get("intent", "hybrid"),
    )

    # Add router to agent path
    if "metadata" not in state:
        state["metadata"] = {}
    if "agent_path" not in state["metadata"]:
        state["metadata"]["agent_path"] = []

    state["metadata"]["agent_path"].append("router")

    # Default routing decision (will be enhanced in Feature 4.2)
    state["route_decision"] = state.get("intent", "hybrid")

    return state


async def llm_answer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate LLM-based answer from retrieved contexts.

    Sprint 11 Feature 11.1: Replaces simple_answer_node with proper LLM generation.
    Uses AnswerGenerator to synthesize answers from retrieved contexts.

    Args:
        state: Current agent state with retrieved_contexts

    Returns:
        State with generated answer in messages
    """
    from src.agents.answer_generator import get_answer_generator

    query = state.get("query", "")
    contexts = state.get("retrieved_contexts", [])

    logger.info("llm_answer_node_start", query=query[:100], contexts_count=len(contexts))

    # Generate answer using LLM
    generator = get_answer_generator()
    answer = await generator.generate_answer(query, contexts, mode="simple")

    # Add to messages (LangGraph format)
    if "messages" not in state:
        state["messages"] = []

    state["messages"].append({"role": "assistant", "content": answer})

    # Also add as direct field for easier access
    state["answer"] = answer

    logger.info("llm_answer_node_complete", answer_length=len(answer), contexts_used=len(contexts))

    return state


def route_query(state: Dict[str, Any]) -> Literal["vector_search", "graph", "memory", "end"]:
    """Determine the next node based on intent.

    This is a conditional edge function that determines routing.
    Routes GRAPH intent to graph_query node (Sprint 5 Feature 5.5).
    Routes MEMORY intent to memory node (Sprint 7 Feature 7.4).
    Routes HYBRID/VECTOR intents to vector_search node (Sprint 10 Fix).

    Args:
        state: Current agent state

    Returns:
        Next node name
    """
    intent = state.get("intent", "hybrid")
    route_decision = state.get("route_decision", intent)

    logger.info("routing_decision", intent=intent, route=route_decision)

    # Sprint 5: Route GRAPH intent to graph_query node
    if route_decision.lower() == "graph":
        logger.info("routing_to_graph_query", intent=intent)
        return "graph"

    # Sprint 7: Route MEMORY intent to memory node
    if route_decision.lower() == "memory":
        logger.info("routing_to_memory", intent=intent)
        return "memory"

    # Sprint 10 Fix: Route hybrid/vector to vector_search node
    logger.info("routing_to_vector_search", intent=intent)
    return "vector_search"


def create_base_graph() -> StateGraph:
    """Create the base LangGraph structure.

    This creates the foundational graph with:
    - START node
    - Router node for query classification
    - Graph query node (Sprint 5 Feature 5.5)
    - Memory node (Sprint 7 Feature 7.4)
    - Conditional edges for routing
    - END node

    Additional agent nodes will be added in future sprints.

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("creating_base_graph")

    # Initialize graph with AgentState schema
    graph = StateGraph(AgentState)

    # Add router node
    graph.add_node("router", router_node)

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
            "vector_search": "vector_search",  # Sprint 10: Route hybrid/vector to vector search
            "graph": "graph_query",  # Sprint 5: Route to graph query agent
            "memory": "memory",  # Sprint 7: Route to memory agent
            "end": END,
        },
    )

    # Sprint 10: Connect vector_search to answer generator
    graph.add_edge("vector_search", "answer")

    # Sprint 5: Connect graph_query to END
    graph.add_edge("graph_query", END)

    # Sprint 7: Connect memory to END
    graph.add_edge("memory", END)

    # Sprint 10: Connect answer to END
    graph.add_edge("answer", END)

    logger.info(
        "base_graph_created", nodes=["router", "vector_search", "graph_query", "memory", "answer"]
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
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
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
