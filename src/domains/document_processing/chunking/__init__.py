"""Adaptive Chunking.

Sprint 56.3: Chunking subdomain of document_processing.

Usage:
    from src.domains.document_processing.chunking import (
        chunking_node,
        SectionMetadata,
        AdaptiveChunk,
    )
"""

# Re-export from components/ingestion
from src.components.ingestion.nodes.adaptive_chunking import (
    chunking_node,
    adaptive_section_chunking,
)
from src.components.ingestion.nodes.models import (
    SectionMetadata,
    AdaptiveChunk,
)
from src.components.ingestion.section_extraction import (
    extract_section_hierarchy,
)

__all__ = [
    # Chunking Node
    "chunking_node",
    "adaptive_section_chunking",
    # Models
    "SectionMetadata",
    "AdaptiveChunk",
    # Section Extraction
    "extract_section_hierarchy",
]
