"""LangGraph Ingestion Pipeline Nodes.

Sprint 54: Modularized node functions for better maintainability.
Each node handles one specific stage of document ingestion.

Node Pipeline:
1. memory_check_node       -> Check RAM/VRAM availability
2. docling_parse_node      -> Parse document with Docling
3. image_enrichment_node   -> VLM image descriptions
4. chunking_node           -> Adaptive section-aware chunking
5. embedding_node          -> Generate BGE-M3 vectors -> Qdrant
6. graph_extraction_node   -> Extract entities/relations -> Neo4j

Usage:
    from src.components.ingestion.nodes import (
        memory_check_node,
        docling_parse_node,
        image_enrichment_node,
        chunking_node,
        embedding_node,
        graph_extraction_node,
    )

For backward compatibility, these are also re-exported from:
    from src.components.ingestion.langgraph_nodes import ...
"""

# Data models
# Sprint 54.5: adaptive_chunking
from src.components.ingestion.nodes.adaptive_chunking import (
    adaptive_section_chunking,
    chunking_node,
    merge_small_chunks,
)

# Sprint 54.3: document_parsers
from src.components.ingestion.nodes.document_parsers import (
    docling_extraction_node,
    docling_parse_node,
    llamaindex_parse_node,
)

# Sprint 54.7: graph_extraction
from src.components.ingestion.nodes.graph_extraction import graph_extraction_node

# Sprint 54.4: image_enrichment
from src.components.ingestion.nodes.image_enrichment import image_enrichment_node

# Sprint 54.2: memory_management
from src.components.ingestion.nodes.memory_management import memory_check_node
from src.components.ingestion.nodes.models import AdaptiveChunk, SectionMetadata

# Sprint 54.6: vector_embedding
from src.components.ingestion.nodes.vector_embedding import embedding_node

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
