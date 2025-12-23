"""Graph Querying via LightRAG.

Sprint 56.2: Querying subdomain of knowledge_graph.
Sprint 62.1: Section-aware graph queries.

Usage:
    from src.domains.knowledge_graph.querying import (
        LightRAGClient,
        get_lightrag_client,
        DualLevelSearch,
        SectionGraphService,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.dual_level_search import (
    DualLevelSearch,
    get_dual_level_search,
)
from src.components.graph_rag.lightrag import (
    LightRAGClient,
    LightRAGWrapper,
    get_lightrag_client,
    get_lightrag_client_async,
    get_lightrag_wrapper,
    get_lightrag_wrapper_async,
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
    # LightRAG Client
    "LightRAGClient",
    "LightRAGWrapper",
    "get_lightrag_client",
    "get_lightrag_client_async",
    "get_lightrag_wrapper",
    "get_lightrag_wrapper_async",
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
