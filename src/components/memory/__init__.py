"""Memory Components for AEGIS RAG Sprint 7.

This module provides a 3-layer memory system:
- Layer 1 (Short-term): Redis working memory for recent context
- Layer 2 (Long-term): Qdrant vector store for semantic facts
- Layer 3 (Episodic): Graphiti temporal graph for episodic memory

Key Components:
- GraphitiWrapper: Ollama-powered episodic memory with Neo4j backend
- TemporalMemoryQuery: Bi-temporal query support (valid time + transaction time)
- RedisMemoryManager: Working memory with TTL-based expiration
- MemoryRouter: Intelligent routing across memory layers
- MemoryConsolidationPipeline: Automatic memory consolidation
"""

from src.components.memory.consolidation import (
    AccessCountPolicy,
    ConsolidationPolicy,
    MemoryConsolidationPipeline,
    TimeBasedPolicy,
    get_consolidation_pipeline,
    start_background_consolidation,
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
from src.components.memory.redis_memory import RedisMemoryManager, get_redis_memory
from src.components.memory.temporal_queries import (
    TemporalMemoryQuery,
    get_temporal_query,
)

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
    # Memory Router
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
]
