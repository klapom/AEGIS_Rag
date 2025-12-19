"""Document Parsing (Docling Integration).

Sprint 56.3: Parsing subdomain of document_processing.

Usage:
    from src.domains.document_processing.parsing import (
        DoclingContainerClient,
        FormatRouter,
    )
"""

# OPL-010: Re-export from components/ingestion until Sprint 58
from src.components.ingestion.docling_client import (
    DoclingContainerClient,
    DoclingParsedDocument,
)
from src.components.ingestion.format_router import (
    ALL_FORMATS,
    DOCLING_FORMATS,
    LLAMAINDEX_EXCLUSIVE,
    SHARED_FORMATS,
    FormatRouter,
    ParserType,
    RoutingDecision,
    check_docling_availability,
    initialize_format_router,
)

__all__ = [
    # Docling Client
    "DoclingContainerClient",
    "DoclingParsedDocument",
    # Format Router
    "FormatRouter",
    "ParserType",
    "RoutingDecision",
    "DOCLING_FORMATS",
    "LLAMAINDEX_EXCLUSIVE",
    "SHARED_FORMATS",
    "ALL_FORMATS",
    "check_docling_availability",
    "initialize_format_router",
]
