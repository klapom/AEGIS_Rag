"""LightRAG wrapper for graph-based knowledge retrieval - Backward Compatibility Facade.

Sprint 55: This file is now a facade that re-exports from the new modularized lightrag package.
All functionality has been moved to src/components/graph_rag/lightrag/ for better maintainability.

MIGRATION NOTICE:
    Old imports (still work):
        from src.components.graph_rag.lightrag_wrapper import LightRAGClient

    New imports (preferred):
        from src.components.graph_rag.lightrag import LightRAGClient

Module Structure (Sprint 55):
1. lightrag/types.py           -> Data models and type definitions
2. lightrag/initialization.py  -> LightRAG instance creation and setup
3. lightrag/converters.py      -> Format conversion utilities
4. lightrag/ingestion.py       -> Document ingestion operations
5. lightrag/neo4j_storage.py   -> Neo4j storage operations
6. lightrag/client.py          -> Main facade class

See ADR-046 for details on the modularization strategy.
"""

# Re-export everything from the new lightrag package for backward compatibility
# All existing imports from this file will continue to work

# Main client class and singletons
from src.components.graph_rag.lightrag.client import (
    LightRAGClient,
    LightRAGWrapper,
    get_lightrag_client,
    get_lightrag_client_async,
    get_lightrag_wrapper,
    get_lightrag_wrapper_async,
)

# Export all symbols for backward compatibility
__all__ = [
    # Main client
    "LightRAGClient",
    "LightRAGWrapper",  # Deprecated alias
    # Singleton getters
    "get_lightrag_client",
    "get_lightrag_client_async",
    "get_lightrag_wrapper",  # Deprecated alias
    "get_lightrag_wrapper_async",  # Deprecated alias
]
