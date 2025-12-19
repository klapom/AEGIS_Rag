"""Semantic Deduplication.

Sprint 56.2: Deduplication subdomain of knowledge_graph.

Usage:
    from src.domains.knowledge_graph.deduplication import (
        SemanticDeduplicator,
        RelationDeduplicator,
        HybridRelationDeduplicator,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.semantic_deduplicator import (
    SemanticDeduplicator,
    MultiCriteriaDeduplicator,
    create_deduplicator_from_config,
)
from src.components.graph_rag.relation_deduplicator import (
    RelationDeduplicator,
    create_relation_deduplicator_from_config,
)
from src.components.graph_rag.semantic_relation_deduplicator import (
    SemanticRelationDeduplicator,
    create_semantic_relation_deduplicator,
    SYMMETRIC_RELATIONS,
)
from src.components.graph_rag.hybrid_relation_deduplicator import (
    HybridRelationDeduplicator,
    get_hybrid_relation_deduplicator,
)

__all__ = [
    # Entity Deduplication
    "SemanticDeduplicator",
    "MultiCriteriaDeduplicator",
    "create_deduplicator_from_config",
    # Relation Deduplication
    "RelationDeduplicator",
    "create_relation_deduplicator_from_config",
    # Semantic Relation Deduplication
    "SemanticRelationDeduplicator",
    "create_semantic_relation_deduplicator",
    "SYMMETRIC_RELATIONS",
    # Hybrid Deduplication
    "HybridRelationDeduplicator",
    "get_hybrid_relation_deduplicator",
]
