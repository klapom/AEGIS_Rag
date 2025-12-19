"""Knowledge Graph Analytics & Recommendations.

Sprint 56.2: Analytics engine and recommendation system.

Usage:
    from src.domains.knowledge_graph.analytics import (
        GraphAnalyticsEngine,
        RecommendationEngine,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.analytics_engine import (
    GraphAnalyticsEngine,
    get_analytics_engine,
)
from src.components.graph_rag.recommendation_engine import (
    RecommendationEngine,
    get_recommendation_engine,
)

__all__ = [
    "GraphAnalyticsEngine",
    "get_analytics_engine",
    "RecommendationEngine",
    "get_recommendation_engine",
]
