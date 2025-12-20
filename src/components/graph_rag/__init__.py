"""Graph RAG components for Neo4j-backed LightRAG integration."""

from src.components.graph_rag.community_delta_tracker import (
    CommunityDelta,
    get_entity_communities_snapshot,
    track_community_changes,
)
from src.components.graph_rag.community_summarizer import (
    CommunitySummarizer,
    get_community_summarizer,
)
from src.components.graph_rag.hybrid_relation_deduplicator import (
    HybridRelationDeduplicator,
    get_hybrid_relation_deduplicator,
)

# Sprint 53 Feature 53.1: LLM Config Provider and Protocols
from src.components.graph_rag.llm_config_provider import (
    REDIS_KEY_SUMMARY_MODEL_CONFIG,
    get_configured_summary_model,
)
from src.components.graph_rag.neo4j_client import (
    Neo4jClient,
    get_neo4j_client,
    get_neo4j_client_async,
)
from src.components.graph_rag.protocols import (
    CommunityDetector,
    GraphStorage,
    LLMConfigProvider,
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
    # Community Summary Generation (Sprint 52.1)
    "CommunityDelta",
    "track_community_changes",
    "get_entity_communities_snapshot",
    "CommunitySummarizer",
    "get_community_summarizer",
    # LLM Config Provider (Sprint 53.1)
    "get_configured_summary_model",
    "REDIS_KEY_SUMMARY_MODEL_CONFIG",
    # Protocols (Sprint 53.1)
    "LLMConfigProvider",
    "GraphStorage",
    "CommunityDetector",
]
