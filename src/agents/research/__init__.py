"""Deep Research Agent.

Sprint 59 Feature 59.6: Multi-step research workflow with LangGraph.

This agent provides iterative research capabilities:
1. Query analysis and research planning
2. Multi-source search execution
3. Result evaluation and refinement
4. Comprehensive synthesis

Usage:
    from src.agents.research import create_research_graph

    graph = create_research_graph()
    result = await graph.ainvoke({
        "query": "What is the latest in machine learning?",
        "max_iterations": 3
    })
"""

from src.agents.research.graph import create_research_graph, ResearchState

__all__ = [
    "create_research_graph",
    "ResearchState",
]
