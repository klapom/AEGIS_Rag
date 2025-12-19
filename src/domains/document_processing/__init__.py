"""Document Processing Domain - Public API.

Sprint 56.3: Domain boundary for document ingestion and processing.

Subdomains:
- parsing: Docling integration for PDF/document parsing
- chunking: Adaptive section-aware chunking
- enrichment: Image/VLM enrichment
- pipeline: LangGraph ingestion pipeline

Usage:
    from src.domains.document_processing import (
        run_ingestion_pipeline,
        DoclingContainerClient,
        FormatRouter,
    )

For backward compatibility, these are also available from:
    from src.components.ingestion import ...
"""

# OPL-010: Re-export from components/ingestion until Sprint 58

# Protocols (Sprint 57)
from src.domains.document_processing.protocols import (
    DocumentParser,
    ChunkingService,
    ImageEnricher,
    IngestionPipeline,
    EmbeddingGenerator,
    FormatRouter as FormatRouterProtocol,
)

# Parsing
from src.domains.document_processing.parsing import (
    DoclingContainerClient,
    DoclingParsedDocument,
    FormatRouter,
    ParserType,
    RoutingDecision,
    DOCLING_FORMATS,
    LLAMAINDEX_EXCLUSIVE,
    SHARED_FORMATS,
    ALL_FORMATS,
    check_docling_availability,
    initialize_format_router,
)

# Pipeline
from src.domains.document_processing.pipeline import (
    IngestionState,
    create_initial_state,
    calculate_progress,
    add_error,
    should_retry,
    increment_retry,
    create_ingestion_graph,
    run_ingestion_pipeline,
    run_ingestion_pipeline_streaming,
    initialize_pipeline_router,
    run_batch_ingestion,
    StreamingPipelineOrchestrator,
)

# Chunking
from src.domains.document_processing.chunking import (
    chunking_node,
    adaptive_section_chunking,
    SectionMetadata,
    AdaptiveChunk,
    extract_section_hierarchy,
)

# Enrichment
from src.domains.document_processing.enrichment import (
    image_enrichment_node,
    ImageProcessor,
    process_image_with_vlm,
)

__all__ = [
    # Protocols (Sprint 57)
    "DocumentParser",
    "ChunkingService",
    "ImageEnricher",
    "IngestionPipeline",
    "EmbeddingGenerator",
    "FormatRouterProtocol",
    # Parsing
    "DoclingContainerClient",
    "DoclingParsedDocument",
    "FormatRouter",
    "ParserType",
    "RoutingDecision",
    "DOCLING_FORMATS",
    "LLAMAINDEX_EXCLUSIVE",
    "SHARED_FORMATS",
    "ALL_FORMATS",
    "check_docling_availability",
    "initialize_format_router",
    # Pipeline
    "IngestionState",
    "create_initial_state",
    "calculate_progress",
    "add_error",
    "should_retry",
    "increment_retry",
    "create_ingestion_graph",
    "run_ingestion_pipeline",
    "run_ingestion_pipeline_streaming",
    "initialize_pipeline_router",
    "run_batch_ingestion",
    "StreamingPipelineOrchestrator",
    # Chunking
    "chunking_node",
    "adaptive_section_chunking",
    "SectionMetadata",
    "AdaptiveChunk",
    "extract_section_hierarchy",
    # Enrichment
    "image_enrichment_node",
    "ImageProcessor",
    "process_image_with_vlm",
]
