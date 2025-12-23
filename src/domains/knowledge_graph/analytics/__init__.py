"""Knowledge Graph Analytics & Recommendations.

Sprint 56.2: Analytics engine and recommendation system.
Sprint 62.9: Section analytics service.

Usage:
    from src.domains.knowledge_graph.analytics import (
        GraphAnalyticsEngine,
        RecommendationEngine,
        SectionAnalyticsService,
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

# Sprint 62.9: Section analytics
from src.domains.knowledge_graph.analytics.section_analytics import (
    SectionAnalyticsService,
    get_section_analytics_service,
)

__all__ = [
    "GraphAnalyticsEngine",
    "get_analytics_engine",
    "RecommendationEngine",
    "get_recommendation_engine",
    "SectionAnalyticsService",
    "get_section_analytics_service",
]
