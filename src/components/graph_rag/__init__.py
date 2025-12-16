"""Graph RAG components for Neo4j-backed LightRAG integration."""

from src.components.graph_rag.hybrid_relation_deduplicator import (
    HybridRelationDeduplicator,
    get_hybrid_relation_deduplicator,
)
from src.components.graph_rag.neo4j_client import (
    Neo4jClient,
    get_neo4j_client,
    get_neo4j_client_async,
)
from src.components.graph_rag.relation_deduplicator import (
    RelationDeduplicator,
    create_relation_deduplicator_from_config,
)
from src.components.graph_rag.semantic_deduplicator import (
    MultiCriteriaDeduplicator,
    SemanticDeduplicator,
    create_deduplicator_from_config,
)
from src.components.graph_rag.semantic_relation_deduplicator import (
    SYMMETRIC_RELATIONS,
    SemanticRelationDeduplicator,
    create_semantic_relation_deduplicator,
)

__all__ = [
    # Neo4j Client
    "Neo4jClient",
    "get_neo4j_client",
    "get_neo4j_client_async",
    # Entity Deduplication (Sprint 43)
    "SemanticDeduplicator",
    "MultiCriteriaDeduplicator",
    "create_deduplicator_from_config",
    # Relation Deduplication (Sprint 44)
    "RelationDeduplicator",
    "create_relation_deduplicator_from_config",
    # Semantic Relation Deduplication (Sprint 49.7)
    "SemanticRelationDeduplicator",
    "create_semantic_relation_deduplicator",
    "SYMMETRIC_RELATIONS",
    # Hybrid Relation Deduplication (Sprint 49.8)
    "HybridRelationDeduplicator",
    "get_hybrid_relation_deduplicator",
]
