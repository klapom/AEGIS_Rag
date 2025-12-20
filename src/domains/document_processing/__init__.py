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

# Re-export from components/ingestion

# Protocols (Sprint 57)
# Chunking
from src.domains.document_processing.chunking import (
    AdaptiveChunk,
    SectionMetadata,
    adaptive_section_chunking,
    chunking_node,
    extract_section_hierarchy,
)

# Enrichment
from src.domains.document_processing.enrichment import (
    ImageProcessor,
    image_enrichment_node,
    process_image_with_vlm,
)

# Parsing
from src.domains.document_processing.parsing import (
    ALL_FORMATS,
    DOCLING_FORMATS,
    LLAMAINDEX_EXCLUSIVE,
    SHARED_FORMATS,
    DoclingContainerClient,
    DoclingParsedDocument,
    FormatRouter,
    ParserType,
    RoutingDecision,
    check_docling_availability,
    initialize_format_router,
)

# Pipeline
from src.domains.document_processing.pipeline import (
    IngestionState,
    StreamingPipelineOrchestrator,
    add_error,
    calculate_progress,
    create_ingestion_graph,
    create_initial_state,
    increment_retry,
    initialize_pipeline_router,
    run_batch_ingestion,
    run_ingestion_pipeline,
    run_ingestion_pipeline_streaming,
    should_retry,
)
from src.domains.document_processing.protocols import (
    ChunkingService,
    DocumentParser,
    EmbeddingGenerator,
    ImageEnricher,
    IngestionPipeline,
)
from src.domains.document_processing.protocols import (
    FormatRouter as FormatRouterProtocol,
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
