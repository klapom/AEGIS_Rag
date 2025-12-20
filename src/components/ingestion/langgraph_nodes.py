"""LangGraph Ingestion Pipeline Nodes - Backward Compatibility Facade.

Sprint 54: This file is now a facade that re-exports from the new modularized nodes package.
All functionality has been moved to src/components/ingestion/nodes/ for better maintainability.

MIGRATION NOTICE:
    Old imports (still work):
        from src.components.ingestion.langgraph_nodes import memory_check_node

    New imports (preferred):
        from src.components.ingestion.nodes import memory_check_node

Node Pipeline:
1. memory_check_node       -> Check RAM/VRAM availability
2. docling_parse_node      -> Parse document with Docling
3. image_enrichment_node   -> VLM image descriptions
4. chunking_node           -> Adaptive section-aware chunking
5. embedding_node          -> Generate BGE-M3 vectors -> Qdrant
6. graph_extraction_node   -> Extract entities/relations -> Neo4j

See ADR-046 for details on the modularization strategy.
"""

# Re-export everything from the new nodes package for backward compatibility
# All existing imports from this file will continue to work

# Data models
from src.components.ingestion.nodes.adaptive_chunking import (
    adaptive_section_chunking,
    chunking_node,
    merge_small_chunks,
)
from src.components.ingestion.nodes.document_parsers import (
    docling_extraction_node,
    docling_parse_node,
    llamaindex_parse_node,
)
from src.components.ingestion.nodes.graph_extraction import graph_extraction_node
from src.components.ingestion.nodes.image_enrichment import image_enrichment_node

# Node functions
from src.components.ingestion.nodes.memory_management import memory_check_node
from src.components.ingestion.nodes.models import (
    AdaptiveChunk,
    SectionMetadata,
)
from src.components.ingestion.nodes.vector_embedding import embedding_node

# Export all symbols for backward compatibility
__all__ = [
    # Data models
    "SectionMetadata",
    "AdaptiveChunk",
    # Node functions
    "memory_check_node",
    "docling_extraction_node",
    "docling_parse_node",
    "llamaindex_parse_node",
    "image_enrichment_node",
    "adaptive_section_chunking",
    "merge_small_chunks",
    "chunking_node",
    "embedding_node",
    "graph_extraction_node",
]
