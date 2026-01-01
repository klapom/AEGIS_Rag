"""Research Supervisor Graph - Multi-Turn Iterative Research.

Sprint 70 Feature 70.4: Deep Research Supervisor Graph

This module implements the Supervisor Pattern for multi-turn research using LangGraph.
Instead of duplicating code, it reuses existing components:
- Planner: LLMTask API for query decomposition
- Searcher: CoordinatorAgent for retrieval
- Synthesizer: AnswerGenerator for final report

Architecture:
```
START → planner → searcher → supervisor → [continue | synthesize]
                      ↑           ↓
                      └───────────┘
                   (multi-turn loop)
```

Key Design:
- Supervisor coordinates research workflow
- Max 3 iterations (configurable)
- Quality-based stop condition
- Zero code duplication
"""

import structlog
from langgraph.graph import StateGraph, END, START

from src.agents.research.state import ResearchSupervisorState

logger = structlog.get_logger(__name__)


async def planner_node(state: ResearchSupervisorState) -> dict:
    """Plan research strategy using LLM.

    Decomposes the original query into 3-5 specific search queries.

    Args:
        state: Current research state

    Returns:
        Updated state with sub_queries
    """
    from src.agents.research.planner import plan_research

    logger.info("planner_node_executing", query=state["original_query"])

    try:
        # Generate research plan
        sub_queries = await plan_research(
            query=state["original_query"],
            max_queries=5,
        )

        logger.info(
            "planner_node_completed",
            num_queries=len(sub_queries),
            queries=sub_queries,
        )

        return {
            "sub_queries": sub_queries,
            "iteration": 0,  # Initialize iteration counter
        }

    except Exception as e:
        logger.error("planner_node_failed", error=str(e), exc_info=True)
        # Fallback: use original query
        return {
            "sub_queries": [state["original_query"]],
            "iteration": 0,
            "error": f"Planning failed: {str(e)}",
        }


async def searcher_node(state: ResearchSupervisorState) -> dict:
    """Execute searches using CoordinatorAgent.

    Reuses existing search infrastructure instead of duplicating code.

    Args:
        state: Current research state

    Returns:
        Updated state with all_contexts and incremented iteration
    """
    from src.agents.research.searcher import execute_research_queries

    logger.info(
        "searcher_node_executing",
        iteration=state["iteration"],
        num_queries=len(state["sub_queries"]),
    )

    try:
        # Execute all queries via CoordinatorAgent
        new_contexts = await execute_research_queries(
            queries=state["sub_queries"],
            namespace=state.get("metadata", {}).get("namespace", "default"),
            top_k_per_query=5,
        )

        # Append to existing contexts (accumulate across iterations)
        all_contexts = state.get("all_contexts", [])
        all_contexts.extend(new_contexts)

        logger.info(
            "searcher_node_completed",
            new_contexts=len(new_contexts),
            total_contexts=len(all_contexts),
        )

        return {
            "all_contexts": all_contexts,
            "iteration": state["iteration"] + 1,
        }

    except Exception as e:
        logger.error("searcher_node_failed", error=str(e), exc_info=True)
        return {
            "iteration": state["iteration"] + 1,
            "error": f"Search failed: {str(e)}",
        }


async def supervisor_node(state: ResearchSupervisorState) -> dict:
    """Supervisor decides whether to continue or synthesize.

    Evaluates:
    1. Max iterations reached?
    2. Sufficient context quality?
    3. Errors occurred?

    Args:
        state: Current research state

    Returns:
        Updated state with should_continue flag
    """
    from src.agents.research.searcher import evaluate_search_quality

    logger.info(
        "supervisor_node_executing",
        iteration=state["iteration"],
        max_iterations=state["max_iterations"],
        num_contexts=len(state.get("all_contexts", [])),
    )

    # Check for errors
    if state.get("error"):
        logger.warning("supervisor_stopping_due_to_error", error=state["error"])
        return {"should_continue": False}

    # Check max iterations
    if state["iteration"] >= state["max_iterations"]:
        logger.info("supervisor_stopping_max_iterations")
        return {"should_continue": False}

    # Evaluate search quality
    contexts = state.get("all_contexts", [])
    quality = evaluate_search_quality(contexts)

    logger.info(
        "supervisor_quality_check",
        quality=quality["quality"],
        num_results=quality["num_results"],
        sufficient=quality["sufficient"],
    )

    # Decide based on quality
    should_continue = not quality["sufficient"]

    if should_continue:
        logger.info("supervisor_continuing_research", reason="insufficient_quality")
    else:
        logger.info("supervisor_synthesizing", reason="sufficient_quality")

    return {"should_continue": should_continue}


async def synthesizer_node(state: ResearchSupervisorState) -> dict:
    """Synthesize final research report using AnswerGenerator.

    Reuses existing answer generation infrastructure.

    Args:
        state: Current research state

    Returns:
        Updated state with synthesis
    """
    from src.agents.research.synthesizer import synthesize_research_findings

    logger.info(
        "synthesizer_node_executing",
        num_contexts=len(state.get("all_contexts", [])),
    )

    try:
        # Synthesize using AnswerGenerator
        result = await synthesize_research_findings(
            query=state["original_query"],
            contexts=state.get("all_contexts", []),
            namespace=state.get("metadata", {}).get("namespace", "default"),
        )

        logger.info(
            "synthesizer_node_completed",
            answer_length=len(result["answer"]),
            num_sources_cited=len(result["sources"]),
        )

        # Store full result in metadata
        metadata = state.get("metadata", {})
        metadata.update(result["metadata"])

        return {
            "synthesis": result["answer"],
            "metadata": metadata,
        }

    except Exception as e:
        logger.error("synthesizer_node_failed", error=str(e), exc_info=True)
        return {
            "synthesis": "Synthesis failed. Please see contexts above.",
            "error": f"Synthesis failed: {str(e)}",
        }


def should_continue_research(state: ResearchSupervisorState) -> str:
    """Conditional edge function for supervisor routing.

    Args:
        state: Current research state

    Returns:
        Edge name: "continue" or "synthesize"
    """
    if state.get("should_continue", False):
        return "continue"
    return "synthesize"


def create_research_graph(enable_tools: bool = False) -> StateGraph:
    """Create the research supervisor graph.

    Args:
        enable_tools: Enable tool use with ReAct pattern (default: False)

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("creating_research_graph", enable_tools=enable_tools)

    # Initialize graph with ResearchSupervisorState schema
    graph = StateGraph(ResearchSupervisorState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("synthesizer", synthesizer_node)

    # Sprint 70 Feature 70.6: Add tool use support (ReAct pattern)
    if enable_tools:
        from src.agents.tools import tools_node

        graph.add_node("research_tools", tools_node)

    # Build workflow
    # START → planner → searcher → supervisor
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "supervisor")

    # Supervisor decision: continue (loop back to searcher) or synthesize
    graph.add_conditional_edges(
        "supervisor",
        should_continue_research,
        {
            "continue": "searcher",  # Multi-turn loop
            "synthesize": "synthesizer",
        },
    )

    # Sprint 70 Feature 70.6: Add tool use edges (ReAct pattern)
    if enable_tools:
        from src.agents.tools import should_use_tools

        # Conditional edge: synthesizer → [tools | END]
        graph.add_conditional_edges(
            "synthesizer",
            lambda state: should_use_tools({"answer": state.get("synthesis", "")}),
            {
                "tools": "research_tools",  # Use tools
                "end": END,  # No tools needed
            },
        )
        # Cycle: tools → synthesizer (for multi-turn tool conversations)
        graph.add_edge("research_tools", "synthesizer")
    else:
        # Synthesizer → END (original behavior)
        graph.add_edge("synthesizer", END)

    nodes = ["planner", "searcher", "supervisor", "synthesizer"]
    if enable_tools:
        nodes.append("research_tools")

    logger.info("research_graph_created", nodes=nodes, enable_tools=enable_tools)

    return graph.compile()


def create_initial_research_state(
    query: str,
    max_iterations: int = 3,
    namespace: str = "default",
) -> dict:
    """Create initial state for research graph.

    Args:
        query: User's research question
        max_iterations: Maximum research iterations (default: 3)
        namespace: Namespace to search in

    Returns:
        Initial ResearchSupervisorState dict
    """
    return {
        "original_query": query,
        "sub_queries": [],
        "iteration": 0,
        "max_iterations": max_iterations,
        "all_contexts": [],
        "synthesis": "",
        "should_continue": True,
        "metadata": {"namespace": namespace},
        "error": None,
    }


# Singleton pattern for graph instances (one per enable_tools value)
_research_graphs: dict[bool, StateGraph] = {}
# Sprint 70 Feature 70.7: Cache for tools config
_research_graph_config_cache: bool | None = None
_research_graph_cache_expires_at: float | None = None
_RESEARCH_GRAPH_CACHE_TTL_SECONDS = 60


def get_research_graph(enable_tools: bool = False) -> StateGraph:
    """Get compiled research graph (singleton).

    Args:
        enable_tools: Enable tool use with ReAct pattern (default: False)

    Returns:
        Compiled StateGraph instance
    """
    global _research_graphs
    if enable_tools not in _research_graphs:
        _research_graphs[enable_tools] = create_research_graph(enable_tools=enable_tools)
    return _research_graphs[enable_tools]


async def get_research_graph_with_config() -> StateGraph:
    """Get compiled research graph with tools config from Redis.

    **Sprint 70 Feature 70.7: Dynamic Tool Configuration for Research**

    Loads tool configuration from Redis and returns the appropriate
    compiled research graph. Caches config for 60 seconds.

    Returns:
        Compiled research StateGraph instance with tools config applied

    Example:
        >>> graph = await get_research_graph_with_config()
        >>> # Graph has tools enabled/disabled based on admin config
    """
    import time

    global _research_graph_config_cache, _research_graph_cache_expires_at

    # Check if cache is still valid
    now = time.time()
    if (
        _research_graph_config_cache is not None
        and _research_graph_cache_expires_at is not None
        and now < _research_graph_cache_expires_at
    ):
        logger.debug("using_cached_research_graph_config", enable_tools=_research_graph_config_cache)
        return get_research_graph(enable_tools=_research_graph_config_cache)

    # Load fresh config from Redis
    from src.components.tools_config import get_tools_config_service

    config_service = get_tools_config_service()
    tools_config = await config_service.get_config()

    enable_tools = tools_config.enable_research_tools

    logger.info(
        "loaded_research_graph_config",
        enable_tools=enable_tools,
        cache_ttl_seconds=_RESEARCH_GRAPH_CACHE_TTL_SECONDS,
    )

    # Update cache
    _research_graph_config_cache = enable_tools
    _research_graph_cache_expires_at = now + _RESEARCH_GRAPH_CACHE_TTL_SECONDS

    return get_research_graph(enable_tools=enable_tools)


# Public API
__all__ = [
    "create_research_graph",
    "get_research_graph",
    "get_research_graph_with_config",  # Sprint 70 Feature 70.7
    "create_initial_research_state",
    "ResearchSupervisorState",
]
