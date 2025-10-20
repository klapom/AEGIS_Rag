"""Memory Components for AEGIS RAG Sprint 9.

This module provides a 3-layer memory system:
- Layer 1 (Short-term): Redis working memory for recent context
- Layer 2 (Long-term): Qdrant vector store for semantic facts
- Layer 3 (Episodic): Graphiti temporal graph for episodic memory

Key Components:
- GraphitiWrapper: Ollama-powered episodic memory with Neo4j backend
- TemporalMemoryQuery: Bi-temporal query support (valid time + transaction time)
- RedisMemoryManager: Working memory with TTL-based expiration (Sprint 9.1)
- EnhancedMemoryRouter: Strategy-based routing with parallel querying (Sprint 9.2)
- RoutingStrategy: Pluggable routing strategies (Recency, QueryType, Hybrid)
- MemoryEntry: Core memory entry model with TTL and tags
- MemoryConsolidationPipeline: Automatic memory consolidation with relevance scoring
- RelevanceScorer: Importance calculation for consolidation decisions
- UnifiedMemoryAPI: Single facade for all memory operations
"""

from src.components.memory.consolidation import (
    AccessCountPolicy,
    ConsolidationPolicy,
    MemoryConsolidationPipeline,
    TimeBasedPolicy,
    get_consolidation_pipeline,
    start_background_consolidation,
)
from src.components.memory.enhanced_router import (
    EnhancedMemoryRouter,
    get_enhanced_router,
)
from src.components.memory.graphiti_wrapper import (
    GraphitiWrapper,
    OllamaLLMClient,
    get_graphiti_wrapper,
)
from src.components.memory.memory_router import (
    MemoryLayer,
    MemoryRouter,
    get_memory_router,
)
from src.components.memory.models import MemoryEntry, MemorySearchResult
from src.components.memory.redis_manager import RedisMemoryManager as RedisManager
from src.components.memory.redis_manager import get_redis_manager
from src.components.memory.redis_memory import (
    RedisMemoryManager,
    get_redis_memory,
)
from src.components.memory.relevance_scorer import (
    RelevanceScore,
    RelevanceScorer,
    get_relevance_scorer,
)
from src.components.memory.routing_strategy import (
    FallbackAllStrategy,
    HybridStrategy,
    QueryTypeStrategy,
    RecencyBasedStrategy,
    RoutingStrategy,
)
from src.components.memory.temporal_queries import (
    TemporalMemoryQuery,
    get_temporal_query,
)
from src.components.memory.unified_api import UnifiedMemoryAPI, get_unified_memory_api

__all__ = [
    # Graphiti (Layer 3: Episodic)
    "GraphitiWrapper",
    "OllamaLLMClient",
    "get_graphiti_wrapper",
    # Temporal Queries
    "TemporalMemoryQuery",
    "get_temporal_query",
    # Redis (Layer 1: Short-term)
    "RedisMemoryManager",
    "get_redis_memory",
    # Sprint 9.1: Enhanced Redis Manager
    "RedisManager",
    "get_redis_manager",
    # Sprint 9.2: Models
    "MemoryEntry",
    "MemorySearchResult",
    # Sprint 9.2: Routing Strategies
    "RoutingStrategy",
    "RecencyBasedStrategy",
    "QueryTypeStrategy",
    "HybridStrategy",
    "FallbackAllStrategy",
    # Sprint 9.2: Enhanced Memory Router
    "EnhancedMemoryRouter",
    "get_enhanced_router",
    # Memory Router (Legacy)
    "MemoryRouter",
    "MemoryLayer",
    "get_memory_router",
    # Consolidation
    "MemoryConsolidationPipeline",
    "ConsolidationPolicy",
    "AccessCountPolicy",
    "TimeBasedPolicy",
    "get_consolidation_pipeline",
    "start_background_consolidation",
    # Relevance Scoring
    "RelevanceScorer",
    "RelevanceScore",
    "get_relevance_scorer",
    # Unified API
    "UnifiedMemoryAPI",
    "get_unified_memory_api",
]
