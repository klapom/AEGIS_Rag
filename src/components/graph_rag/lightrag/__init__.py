"""LightRAG Integration Package.

Sprint 55: Modularized LightRAG wrapper for better maintainability.
Provides graph-based knowledge retrieval with Neo4j backend.

Node Pipeline:
1. types.py           -> Data models and type definitions
2. initialization.py  -> LightRAG instance creation and setup
3. converters.py      -> Format conversion utilities
4. ingestion.py       -> Document ingestion operations
5. neo4j_storage.py   -> Neo4j storage operations
6. client.py          -> Main facade class

Usage:
    from src.components.graph_rag.lightrag import (
        LightRAGClient,
        get_lightrag_client,
        get_lightrag_client_async,
    )

    # Singleton access
    client = get_lightrag_client()

    # Or async initialization
    client = await get_lightrag_client_async()
    result = await client.query_graph("What is machine learning?")

For backward compatibility, these are also re-exported from:
    from src.components.graph_rag.lightrag_wrapper import ...
"""

# Client (main facade)
from src.components.graph_rag.lightrag.client import (
    LightRAGClient,
    LightRAGWrapper,
    get_lightrag_client,
    get_lightrag_client_async,
    get_lightrag_wrapper,
    get_lightrag_wrapper_async,
)

# Converters
from src.components.graph_rag.lightrag.converters import (
    chunk_text_with_metadata,
    convert_chunks_to_lightrag_format,
    convert_entities_to_lightrag_format,
    convert_relations_to_lightrag_format,
)

# Ingestion
from src.components.graph_rag.lightrag.ingestion import (
    extract_per_chunk,
    insert_documents,
    insert_documents_optimized,
    insert_prechunked_documents,
)

# Initialization
from src.components.graph_rag.lightrag.initialization import (
    UnifiedEmbeddingFunc,
    create_lightrag_instance,
    get_default_config,
    setup_neo4j_environment,
)

# Neo4j Storage
from src.components.graph_rag.lightrag.neo4j_storage import (
    check_neo4j_health,
    clear_neo4j_database,
    get_neo4j_stats,
    store_chunks_and_provenance,
    store_relates_to_relationships,
)

# Types
from src.components.graph_rag.lightrag.types import (
    ChunkMetadata,
    EntityData,
    ExtractionStats,
    IngestionResult,
    LightRAGConfig,
    QueryMode,
    RelationData,
)

__all__ = [
    # Client
    "LightRAGClient",
    "LightRAGWrapper",
    "get_lightrag_client",
    "get_lightrag_client_async",
    "get_lightrag_wrapper",
    "get_lightrag_wrapper_async",
    # Types
    "QueryMode",
    "LightRAGConfig",
    "IngestionResult",
    "ExtractionStats",
    "ChunkMetadata",
    "EntityData",
    "RelationData",
    # Initialization
    "get_default_config",
    "setup_neo4j_environment",
    "create_lightrag_instance",
    "UnifiedEmbeddingFunc",
    # Converters
    "chunk_text_with_metadata",
    "convert_chunks_to_lightrag_format",
    "convert_entities_to_lightrag_format",
    "convert_relations_to_lightrag_format",
    # Ingestion
    "extract_per_chunk",
    "insert_documents",
    "insert_documents_optimized",
    "insert_prechunked_documents",
    # Neo4j Storage
    "store_chunks_and_provenance",
    "store_relates_to_relationships",
    "clear_neo4j_database",
    "get_neo4j_stats",
    "check_neo4j_health",
]
