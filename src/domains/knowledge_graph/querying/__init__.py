"""Graph Querying via DualLevelSearch.

Sprint 56.2: Querying subdomain of knowledge_graph.
Sprint 62.1: Section-aware graph queries.
Sprint 128: LightRAG removed — DualLevelSearch is the sole query path.

Usage:
    from src.domains.knowledge_graph.querying import (
        DualLevelSearch,
        get_dual_level_search,
        SectionGraphService,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.dual_level_search import (
    DualLevelSearch,
    get_dual_level_search,
)

# Sprint 62.1: Section-aware queries
from src.domains.knowledge_graph.querying.section_graph_service import (
    EntityWithSection,
    RelationshipWithSection,
    SectionGraphQueryResult,
    SectionGraphService,
    SectionMetadataResult,
    get_section_graph_service,
    reset_section_graph_service,
)

__all__ = [
    # Dual Level Search
    "DualLevelSearch",
    "get_dual_level_search",
    # Section-Aware Queries (Sprint 62.1)
    "SectionGraphService",
    "SectionGraphQueryResult",
    "EntityWithSection",
    "RelationshipWithSection",
    "SectionMetadataResult",
    "get_section_graph_service",
    "reset_section_graph_service",
]
