"""Knowledge Graph Domain - Public API.

Sprint 56.2: Domain boundary for graph-based knowledge management.

Subdomains:
- extraction: Entity and relation extraction from text
- deduplication: Semantic entity and relation deduplication
- communities: Community detection and summarization
- querying: Graph queries via LightRAG
- persistence: Neo4j storage operations
- analytics: Graph analytics and recommendations
- utilities: Protocols, templates, and utilities

Usage:
    from src.domains.knowledge_graph import (
        LightRAGClient,
        get_lightrag_client,
        Neo4jClient,
        get_neo4j_client,
        CommunitySummarizer,
    )

For backward compatibility, these are also available from:
    from src.components.graph_rag import ...
"""

# Re-export from components/graph_rag

# Protocols (Sprint 57)
# Analytics
from src.domains.knowledge_graph.analytics import (
    GraphAnalyticsEngine,
    RecommendationEngine,
    get_analytics_engine,
    get_recommendation_engine,
)
from src.domains.knowledge_graph.communities import (
    CommunityDelta,
    CommunitySearch,
    CommunitySummarizer,
    get_community_detector,
    get_community_search,
    get_community_summarizer,
    get_entity_communities_snapshot,
    track_community_changes,
)

# Communities
from src.domains.knowledge_graph.communities import (
    CommunityDetector as CommunityDetectorClass,
)

# Deduplication
from src.domains.knowledge_graph.deduplication import (
    SYMMETRIC_RELATIONS,
    HybridRelationDeduplicator,
    MultiCriteriaDeduplicator,
    RelationDeduplicator,
    SemanticDeduplicator,
    SemanticRelationDeduplicator,
    create_deduplicator_from_config,
    create_relation_deduplicator_from_config,
    create_semantic_relation_deduplicator,
    get_hybrid_relation_deduplicator,
)

# Extraction
from src.domains.knowledge_graph.extraction import (
    ExtractionBenchmark,
    ExtractionPipelineFactory,
    ExtractionService,
    ParallelExtractor,
    RelationExtractor,
    create_extraction_pipeline_from_config,
    create_relation_extractor_from_config,
    extract_parallel,
    get_extraction_service,
    get_parallel_extractor,
    run_benchmark,
)

# Persistence
from src.domains.knowledge_graph.persistence import (
    CypherQueryBuilder,
    GraphQueryTemplates,
    Neo4jClient,
    TemporalQueryBuilder,
    get_neo4j_client,
    get_neo4j_client_async,
    get_temporal_query_builder,
)
from src.domains.knowledge_graph.protocols import (
    CommunityService,
    DeduplicationService,
    EntityExtractor,
    GraphAnalytics,
    GraphQueryService,
    GraphStorage,
    LLMConfigProvider,
    RelationExtractor,
)

# Querying
from src.domains.knowledge_graph.querying import (
    DualLevelSearch,
    LightRAGClient,
    LightRAGWrapper,
    get_dual_level_search,
    get_lightrag_client,
    get_lightrag_client_async,
    get_lightrag_wrapper,
    get_lightrag_wrapper_async,
)

# Utilities
from src.domains.knowledge_graph.utilities import (
    REDIS_KEY_SUMMARY_MODEL_CONFIG,
    CommunityDetectorProtocol,
    GraphStorage,
    GraphVisualizationExporter,
    LLMConfigProvider,
    get_configured_summary_model,
    get_visualization_exporter,
)

__all__ = [
    # Protocols (Sprint 57)
    "EntityExtractor",
    "RelationExtractor",
    "GraphStorage",
    "GraphQueryService",
    "CommunityService",
    "LLMConfigProvider",
    "DeduplicationService",
    "GraphAnalytics",
    # Persistence
    "Neo4jClient",
    "get_neo4j_client",
    "get_neo4j_client_async",
    "GraphQueryTemplates",
    "CypherQueryBuilder",
    "TemporalQueryBuilder",
    "get_temporal_query_builder",
    # Querying
    "LightRAGClient",
    "LightRAGWrapper",
    "get_lightrag_client",
    "get_lightrag_client_async",
    "get_lightrag_wrapper",
    "get_lightrag_wrapper_async",
    "DualLevelSearch",
    "get_dual_level_search",
    # Extraction
    "RelationExtractor",
    "create_relation_extractor_from_config",
    "ParallelExtractor",
    "get_parallel_extractor",
    "extract_parallel",
    "ExtractionPipelineFactory",
    "create_extraction_pipeline_from_config",
    "ExtractionService",
    "get_extraction_service",
    "ExtractionBenchmark",
    "run_benchmark",
    # Deduplication
    "SemanticDeduplicator",
    "MultiCriteriaDeduplicator",
    "create_deduplicator_from_config",
    "RelationDeduplicator",
    "create_relation_deduplicator_from_config",
    "SemanticRelationDeduplicator",
    "create_semantic_relation_deduplicator",
    "SYMMETRIC_RELATIONS",
    "HybridRelationDeduplicator",
    "get_hybrid_relation_deduplicator",
    # Communities
    "CommunityDetectorClass",
    "get_community_detector",
    "CommunitySummarizer",
    "get_community_summarizer",
    "CommunityDelta",
    "track_community_changes",
    "get_entity_communities_snapshot",
    "CommunitySearch",
    "get_community_search",
    # Analytics
    "GraphAnalyticsEngine",
    "get_analytics_engine",
    "RecommendationEngine",
    "get_recommendation_engine",
    # Utilities/Protocols
    "GraphStorage",
    "CommunityDetectorProtocol",
    "LLMConfigProvider",
    "GraphVisualizationExporter",
    "get_visualization_exporter",
    "get_configured_summary_model",
    "REDIS_KEY_SUMMARY_MODEL_CONFIG",
]
