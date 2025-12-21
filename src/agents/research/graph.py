"""Deep Research Agent with LangGraph.

Sprint 59 Feature 59.6: Multi-step research workflow.

This module implements a LangGraph-based research agent that:
1. Plans research strategy (decompose query)
2. Executes searches across multiple sources
3. Evaluates results and decides whether to continue
4. Synthesizes findings into comprehensive answer
"""

from typing import TypedDict, Annotated, Literal
import operator
import structlog

from langgraph.graph import StateGraph, END

from src.agents.research.planner import plan_research, evaluate_plan_quality
from src.agents.research.searcher import execute_searches, evaluate_results
from src.agents.research.synthesizer import synthesize_findings

logger = structlog.get_logger(__name__)


class ResearchState(TypedDict):
    """State for research workflow.

    This state is threaded through all nodes in the graph.
    """

    query: str
    """Original research question"""

    research_plan: list[str]
    """List of search queries to execute"""

    search_results: Annotated[list[dict], operator.add]
    """Accumulated search results (add-only)"""

    synthesis: str
    """Final synthesized answer"""

    iteration: int
    """Current iteration number"""

    max_iterations: int
    """Maximum iterations allowed"""

    quality_metrics: dict
    """Quality metrics for evaluation"""

    should_continue: bool
    """Whether to continue searching"""


# =============================================================================
# Graph Nodes
# =============================================================================


async def plan_node(state: ResearchState) -> ResearchState:
    """Plan research strategy by decomposing query.

    Args:
        state: Current research state

    Returns:
        Updated state with research plan
    """
    logger.info("research_planning", query=state["query"])

    # Generate research plan
    plan = await plan_research(
        query=state["query"],
        max_queries=5,
    )

    # Evaluate plan quality
    quality = await evaluate_plan_quality(
        query=state["query"],
        plan=plan,
    )

    state["research_plan"] = plan
    state["quality_metrics"] = quality

    logger.info("research_planned", num_queries=len(plan), quality=quality)

    return state


async def search_node(state: ResearchState) -> ResearchState:
    """Execute searches based on research plan.

    Args:
        state: Current research state

    Returns:
        Updated state with search results
    """
    logger.info(
        "executing_searches",
        iteration=state["iteration"],
        num_queries=len(state["research_plan"]),
    )

    # Execute searches
    results = await execute_searches(
        queries=state["research_plan"],
        top_k=5,
        use_graph=True,
        use_vector=True,
    )

    # Results are automatically accumulated due to Annotated[list, operator.add]
    state["search_results"] = results

    logger.info("searches_executed", num_results=len(results))

    return state


async def evaluate_node(state: ResearchState) -> ResearchState:
    """Evaluate search results and decide whether to continue.

    Args:
        state: Current research state

    Returns:
        Updated state with evaluation metrics
    """
    logger.info("evaluating_results", iteration=state["iteration"])

    # Increment iteration counter
    state["iteration"] = state.get("iteration", 0) + 1

    # Evaluate results
    metrics = await evaluate_results(
        results=state["search_results"],
        query=state["query"],
    )

    state["quality_metrics"].update(metrics)

    # Decide whether to continue
    sufficient = metrics.get("sufficient", False)
    max_reached = state["iteration"] >= state["max_iterations"]

    state["should_continue"] = not sufficient and not max_reached

    logger.info(
        "evaluation_completed",
        sufficient=sufficient,
        max_reached=max_reached,
        should_continue=state["should_continue"],
        metrics=metrics,
    )

    return state


async def synthesize_node(state: ResearchState) -> ResearchState:
    """Synthesize all findings into final answer.

    Args:
        state: Current research state

    Returns:
        Updated state with synthesis
    """
    logger.info(
        "synthesizing_findings",
        num_results=len(state["search_results"]),
    )

    # Synthesize findings
    synthesis = await synthesize_findings(
        query=state["query"],
        results=state["search_results"],
    )

    state["synthesis"] = synthesis

    logger.info("synthesis_completed", length=len(synthesis))

    return state


# =============================================================================
# Conditional Edge Logic
# =============================================================================


def should_continue_searching(state: ResearchState) -> Literal["search", "synthesize"]:
    """Determine whether to continue searching or synthesize results.

    Args:
        state: Current research state

    Returns:
        Next node name
    """
    if state.get("should_continue", False):
        logger.info("continuing_search", iteration=state["iteration"])
        return "search"
    else:
        logger.info("moving_to_synthesis", iteration=state["iteration"])
        return "synthesize"


# =============================================================================
# Graph Construction
# =============================================================================


def create_research_graph() -> StateGraph:
    """Create the research agent graph.

    Returns:
        Compiled StateGraph

    The graph structure:
        START → plan → search → evaluate → [continue?]
                                    ↓           ↓
                                    ↓        search (loop)
                                    ↓
                               synthesize → END

    Examples:
        >>> graph = create_research_graph()
        >>> result = await graph.ainvoke({
        ...     "query": "What is machine learning?",
        ...     "max_iterations": 2
        ... })
        >>> "synthesis" in result
        True
    """
    # Create workflow
    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("plan", plan_node)
    workflow.add_node("search", search_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("synthesize", synthesize_node)

    # Add edges
    workflow.add_edge("plan", "search")
    workflow.add_edge("search", "evaluate")

    # Conditional edge: continue searching or synthesize?
    workflow.add_conditional_edges(
        "evaluate",
        should_continue_searching,
        {
            "search": "search",
            "synthesize": "synthesize",
        },
    )

    # End after synthesis
    workflow.add_edge("synthesize", END)

    # Set entry point
    workflow.set_entry_point("plan")

    # Compile graph
    logger.info("research_graph_compiled")

    return workflow.compile()


# =============================================================================
# Helper Functions
# =============================================================================


async def run_research(
    query: str,
    max_iterations: int = 3,
) -> dict:
    """Run complete research workflow.

    Args:
        query: Research question
        max_iterations: Maximum search iterations

    Returns:
        Final research state with synthesis

    Examples:
        >>> result = await run_research("What is deep learning?")
        >>> result["synthesis"]
        "Deep learning is..."
    """
    logger.info("starting_research", query=query, max_iterations=max_iterations)

    # Create initial state
    initial_state: ResearchState = {
        "query": query,
        "research_plan": [],
        "search_results": [],
        "synthesis": "",
        "iteration": 0,
        "max_iterations": max_iterations,
        "quality_metrics": {},
        "should_continue": True,
    }

    # Create and run graph
    graph = create_research_graph()
    final_state = await graph.ainvoke(initial_state)

    logger.info(
        "research_completed",
        query=query,
        iterations=final_state["iteration"],
        num_results=len(final_state["search_results"]),
    )

    return final_state
