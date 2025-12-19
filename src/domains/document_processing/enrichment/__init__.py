"""Image/VLM Enrichment.

Sprint 56.3: Enrichment subdomain of document_processing.

Usage:
    from src.domains.document_processing.enrichment import (
        image_enrichment_node,
        ImageProcessor,
    )
"""

# OPL-010: Re-export from components/ingestion until Sprint 58
from src.components.ingestion.nodes.image_enrichment import (
    image_enrichment_node,
)
from src.components.ingestion.image_processor import (
    ImageProcessor,
    process_image_with_vlm,
)

__all__ = [
    # Image Enrichment Node
    "image_enrichment_node",
    # Image Processor
    "ImageProcessor",
    "process_image_with_vlm",
]
