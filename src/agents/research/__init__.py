"""Deep Research Agent.

Sprint 59 Feature 59.6: Multi-step research workflow with LangGraph.
Sprint 70 Feature 70.4: Updated to Supervisor Pattern with component reuse.

This agent provides iterative research capabilities:
1. Query analysis and research planning
2. Multi-source search execution
3. Result evaluation and refinement
4. Comprehensive synthesis

Usage:
    from src.agents.research import get_research_graph, create_initial_research_state

    graph = get_research_graph()
    initial_state = create_initial_research_state(
        query="What is the latest in machine learning?",
        max_iterations=3
    )
    result = await graph.ainvoke(initial_state)
"""

# Sprint 70: Import from new research_graph.py
from src.agents.research.research_graph import (
    ResearchSupervisorState,
    create_initial_research_state,
    create_research_graph,
    get_research_graph,
)

__all__ = [
    "create_research_graph",
    "get_research_graph",
    "create_initial_research_state",
    "ResearchSupervisorState",
]
