"""Retrieval API Endpoints - Sprint 2.

DEPRECATED: This entire router is not called from the frontend (identified 2025-12-07).
All retrieval functionality has been migrated to:
- CoordinatorAgent (for search/query)
- /api/v1/admin/indexing/* (for document ingestion)

Consider removal of this entire file in next major version.

FastAPI endpoints for document ingestion and hybrid search retrieval.

Sprint 22 Feature 22.2.2: Using standardized error responses with custom exceptions.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict, Field

from src.api.auth.jwt import get_current_user
from src.api.dependencies import get_request_id  # Sprint 22 Feature 22.2.1
from src.api.middleware import limiter
from src.components.ingestion.format_router import FormatRouter  # Sprint 22 Feature 22.3
from src.components.retrieval import MetadataFilters
from src.components.vector_search import (
    DocumentIngestionPipeline,
    HybridSearch,
)
from src.core.config import get_settings
from src.core.exceptions import (
    AegisRAGException,
    InvalidFileFormatError,
    ValidationError,
    VectorSearchError,
)

logger = structlog.get_logger(__name__)
settings = get_settings()  # Sprint 22 Feature 22.2.3: Config-driven rate limits

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])

# Initialize format router (Sprint 22 Feature 22.3)
# NOTE: Will be properly initialized with health check in main.py lifespan
# Default: docling_available=True (will be updated on startup)
_format_router = FormatRouter()  # Placeholder, updated in main.py lifespan with health check


# Request/Response Models
class SearchRequest(BaseModel):
    """Search request model with enhanced validation."""

    query: str = Field(
        ...,
        description="Search query text",
        min_length=1,
        max_length=1000,  # P1: Prevent excessive queries
        examples=["What is RAG?"],
    )
    top_k: int = Field(10, description="Number of results to return", ge=1, le=100)
    search_type: str = Field(
        "hybrid",
        description="Search type: 'vector', 'bm25', or 'hybrid'",
        pattern="^(vector|bm25|hybrid)$",  # P1: Strict validation
    )
    score_threshold: float | None = Field(
        None,
        description="Minimum similarity score for vector search",
        ge=0.0,
        le=1.0,
    )
    # Sprint 3: Reranking parameters
    use_reranking: bool = Field(
        True, description="Apply cross-encoder reranking for improved relevance (Sprint 3)"
    )
    rerank_top_k: int | None = Field(
        None,
        description="Number of candidates to rerank (default: 2*top_k)",
        ge=1,
        le=100,
    )
    # Sprint 3: Metadata filters
    filters: dict[str, Any] | None = Field(
        None,
        description="Metadata filters for targeted search (Sprint 3)",
        examples=[
            {
                "created_after": "2024-01-01T00:00:00",
                "doc_type_in": ["pdf", "md"],
                "tags_contains": ["tutorial"],
            }
        ],
    )
    # Sprint 81: TD-099 - Namespace filtering for multi-tenant isolation
    namespaces: list[str] | None = Field(
        None,
        description="Namespaces to filter by (Sprint 81 TD-099)",
        examples=[["default"], ["ragas_eval"], ["default", "general"]],
    )
    # Sprint 125 Feature 125.9b: Domain filtering
    domain_ids: list[str] | None = Field(
        None,
        description="Domain IDs to filter by (Sprint 125 Feature 125.9b)",
        examples=[["computer_science_it"], ["medicine_health", "chemistry"]],
    )

    model_config = ConfigDict(
        # P1: Validate assignment to prevent invalid data
        validate_assignment=True,
        # P1: Strict validation
        str_strip_whitespace=True,
    )


class SearchResult(BaseModel):
    """Single search result."""

    id: str
    text: str
    score: float
    source: str
    document_id: str
    rank: int
    rrf_score: float | None = None
    # Sprint 3: Reranking scores
    rerank_score: float | None = Field(None, description="Cross-encoder relevance score")
    normalized_rerank_score: float | None = Field(None, description="Normalized rerank score (0-1)")
    original_rrf_rank: int | None = Field(None, description="Rank before reranking")
    final_rank: int | None = Field(None, description="Rank after reranking")
    # Sprint 81: TD-099 fix - Include namespace_id in response for debugging
    namespace_id: str | None = Field(None, description="Namespace for multi-tenant isolation")


class SearchResponse(BaseModel):
    """Search response model."""

    query: str
    results: list[SearchResult]
    total_results: int
    search_type: str
    search_metadata: dict[str, Any] | None = None


class IngestionRequest(BaseModel):
    """Document ingestion request with enhanced validation."""

    input_dir: str = Field(
        ...,
        description="Directory containing documents (relative to documents_base_path)",
        min_length=1,
        max_length=500,  # P1: Prevent path injection
        examples=["./data/sample_documents"],
    )
    chunk_size: int = Field(512, description="Maximum tokens per chunk", ge=128, le=2048)
    chunk_overlap: int = Field(128, description="Overlap between chunks", ge=0, le=512)
    file_extensions: list[str] | None = Field(
        default=None,
        description="File extensions to process (default: .pdf, .txt, .md)",
        max_length=20,  # P1: Prevent DoS with excessive extensions
    )

    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True)


class IngestionResponse(BaseModel):
    """Document ingestion response."""

    status: str
    documents_loaded: int
    chunks_created: int
    embeddings_generated: int
    points_indexed: int
    duration_seconds: float
    collection_name: str
    # Sprint 11: Unified Ingestion Pipeline fields
    neo4j_entities: int = Field(default=0, description="Entities extracted to Neo4j")
    neo4j_relationships: int = Field(default=0, description="Relationships extracted to Neo4j")


# Global hybrid search instance
_hybrid_search: HybridSearch | None = None


def get_hybrid_search() -> HybridSearch:
    """Get or create hybrid search instance."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search


@router.post("/search", response_model=SearchResponse)
@limiter.limit(f"{settings.rate_limit_search}/minute")  # Config-driven rate limit
async def search(
    request: Request,
    search_params: SearchRequest,
    current_user: str | None = Depends(get_current_user),
    request_id: str = Depends(get_request_id),  # Sprint 22 Feature 22.2.1
) -> SearchResponse:
    """Search documents using vector, BM25, or hybrid search.

    Requires authentication (if enabled). Rate limited to 10 requests/minute.

    Args:
        request: FastAPI request (for rate limiting)
        search_params: Search request parameters
        current_user: Authenticated user (from JWT token)
        request_id: Unique request ID (auto-injected by RequestIDMiddleware)

    Returns:
        SearchResponse with ranked results (includes request_id in metadata)

    Example:
        ```bash
        # With authentication
        curl -X POST "http://localhost:8000/api/v1/retrieval/search" \\
             -H "Content-Type: application/json" \\
             -H "Authorization: Bearer <your-token>" \\
             -d '{"query": "What is RAG?", "search_type": "hybrid", "top_k": 10}'

        # Response includes X-Request-ID header for debugging:
        # X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
        ```

    Note:
        Sprint 22 Feature 22.2.1: All logs for this request automatically include
        the request_id field for correlation and debugging.
    """
    try:
        # Request ID is automatically in all logs via structlog contextvars
        logger.info(
            "search_request_received",
            query_length=len(search_params.query),
            search_type=search_params.search_type,
            top_k=search_params.top_k,
            user=current_user or "anonymous",
        )

        hybrid_search = get_hybrid_search()

        # Parse metadata filters if provided
        metadata_filters = None
        if search_params.filters:
            try:
                # Convert datetime strings to datetime objects
                filter_dict = search_params.filters.copy()
                if "created_after" in filter_dict and filter_dict["created_after"]:
                    filter_dict["created_after"] = datetime.fromisoformat(
                        filter_dict["created_after"].replace("Z", "+00:00")
                    )
                if "created_before" in filter_dict and filter_dict["created_before"]:
                    filter_dict["created_before"] = datetime.fromisoformat(
                        filter_dict["created_before"].replace("Z", "+00:00")
                    )
                metadata_filters = MetadataFilters(**filter_dict)
                logger.info(
                    "metadata_filters_parsed",
                    active_filters=metadata_filters.get_active_filters(),
                )
            except Exception as e:
                logger.warning("Failed to parse metadata filters", error=str(e))
                # Sprint 22 Feature 22.2.2: Use custom exception
                raise ValidationError(field="filters", issue=str(e)) from None

        # Sprint 81: TD-099 - Add namespace filtering to MetadataFilters
        if search_params.namespaces:
            if metadata_filters is None:
                metadata_filters = MetadataFilters(namespace=search_params.namespaces)
            else:
                metadata_filters.namespace = search_params.namespaces
            logger.info(
                "namespace_filter_applied",
                namespaces=search_params.namespaces,
            )

        # Sprint 125 Feature 125.9b: Add domain filtering to MetadataFilters
        if search_params.domain_ids:
            if metadata_filters is None:
                metadata_filters = MetadataFilters()
            # Add domain_id filter (assuming MetadataFilters supports custom filters)
            # This will be handled by Qdrant filtering on domain_id payload field
            if not hasattr(metadata_filters, "domain_ids"):
                # Store in filters dict if MetadataFilters doesn't have domain_ids attribute
                if not hasattr(metadata_filters, "_custom_filters"):
                    metadata_filters._custom_filters = {}
                metadata_filters._custom_filters["domain_ids"] = search_params.domain_ids
            else:
                metadata_filters.domain_ids = search_params.domain_ids
            logger.info(
                "domain_filter_applied",
                domain_ids=search_params.domain_ids,
            )

        if search_params.search_type == "hybrid":
            # Hybrid search (Vector + BM25 + RRF + optional Reranking + optional Filters)
            result = await hybrid_search.hybrid_search(
                query=search_params.query,
                top_k=search_params.top_k,
                score_threshold=search_params.score_threshold,
                use_reranking=search_params.use_reranking,  # Sprint 3
                rerank_top_k=search_params.rerank_top_k,  # Sprint 3
                filters=metadata_filters,  # Sprint 3
            )

            logger.info(
                "search_completed",
                search_type="hybrid",
                results_count=result["total_results"],
            )

            return SearchResponse(
                query=result["query"],
                results=[SearchResult(**r) for r in result["results"]],
                total_results=result["total_results"],
                search_type="hybrid",
                search_metadata=result["search_metadata"],
            )

        elif search_params.search_type == "vector":
            # Vector-only search (with optional filters)
            results = await hybrid_search.vector_search(
                query=search_params.query,
                top_k=search_params.top_k,
                score_threshold=search_params.score_threshold,
                filters=metadata_filters,  # Sprint 3
            )

            return SearchResponse(
                query=search_params.query,
                results=[SearchResult(**r) for r in results],
                total_results=len(results),
                search_type="vector",
            )

        elif search_params.search_type == "bm25":
            # BM25-only search (no filter support for BM25)
            results = await hybrid_search.keyword_search(
                query=search_params.query,
                top_k=search_params.top_k,
            )

            return SearchResponse(
                query=search_params.query,
                results=[SearchResult(**r) for r in results],
                total_results=len(results),
                search_type="bm25",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_type: {search_params.search_type}. Use 'vector', 'bm25', or 'hybrid'.",
            )

    except ValidationError:
        # Re-raise custom exceptions (will be handled by global handler)
        raise
    except Exception as e:
        # Sprint 22 Feature 22.2.1: request_id automatically in logs
        logger.error("search_failed", error=str(e), query=search_params.query, exc_info=True)
        # Sprint 22 Feature 22.2.2: Use custom exception with request_id
        raise VectorSearchError(query=search_params.query, reason=str(e)) from None


@router.post("/ingest", response_model=IngestionResponse)
@limiter.limit("5/hour")  # Rate limit: 5 requests per hour (heavy operation)
async def ingest(
    request: Request,
    ingest_params: IngestionRequest,
    background_tasks: BackgroundTasks,
    current_user: str | None = Depends(get_current_user),
) -> IngestionResponse:
    """Ingest documents from directory into vector database.

    Requires authentication (if enabled). Rate limited to 5 requests/hour.

    Args:
        request: FastAPI request (for rate limiting)
        ingest_params: Ingestion request parameters
        background_tasks: FastAPI background tasks
        current_user: Authenticated user (from JWT token)

    Returns:
        IngestionResponse with statistics

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/ingest" \\
             -H "Content-Type: application/json" \\
             -H "Authorization: Bearer <your-token>" \\
             -d '{"input_dir": "./data/documents", "chunk_size": 512}'
        ```
    """
    try:
        # Validate input directory
        input_path = Path(ingest_params.input_dir)
        if not input_path.exists():
            # Sprint 22 Feature 22.2.2: Use custom exception
            raise ValidationError(
                field="input_dir",
                issue=f"Directory does not exist: {ingest_params.input_dir}",
            )

        if not input_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Input path is not a directory: {ingest_params.input_dir}",
            )

        # Run ingestion
        pipeline = DocumentIngestionPipeline(
            chunk_size=ingest_params.chunk_size,
            chunk_overlap=ingest_params.chunk_overlap,
        )

        stats = await pipeline.index_documents(
            input_dir=input_path,
            required_exts=ingest_params.file_extensions,
        )

        # Sprint 120: BM25 background task REMOVED.
        # Lexical search now uses BGE-M3 sparse vectors (Sprint 87).

        return IngestionResponse(
            status="success",
            documents_loaded=stats["documents_loaded"],
            chunks_created=stats["chunks_created"],
            embeddings_generated=stats["embeddings_generated"],
            points_indexed=stats["points_indexed"],
            duration_seconds=stats["duration_seconds"],
            collection_name=stats["collection_name"],
        )

    except ValueError as e:
        # P1: Path validation errors should be clear but not expose internals
        logger.warning("Invalid ingestion path", error=str(e), input_dir=ingest_params.input_dir)
        raise HTTPException(status_code=400, detail="Invalid directory path") from None
    except HTTPException:
        raise
    except AegisRAGException:
        # Sprint 22 Feature 22.2.2: Let custom exceptions bubble up to global handler
        raise
    except Exception as e:
        logger.error(
            "Ingestion failed", error=str(e), input_dir=ingest_params.input_dir, exc_info=True
        )
        # P1: Don't expose internal error details
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed. Please check your input and try again.",
        ) from None


@router.post("/detect-domain")
@limiter.limit(f"{settings.rate_limit_upload}/minute")  # Config-driven rate limit
async def detect_domain(
    request: Request,
    file: UploadFile = File(None),
    text_sample: str = Form(None),
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Detect document domain from file or text sample.

    Sprint 125 Feature 125.9a: Domain Detection API

    Analyzes document content and returns top-3 domain predictions using BGE-M3
    embedding similarity against domain keyword embeddings from seed catalog.

    Args:
        request: FastAPI request (for rate limiting)
        file: Optional uploaded file (PDF or text)
        text_sample: Optional text sample for classification
        current_user: Authenticated user (optional)

    Returns:
        Dictionary with:
        - domains: List of top-3 domain predictions with scores
        - text_sample_length: Length of analyzed text
        - classification_method: "bge_m3_similarity"

    Example:
        ```bash
        # From file
        curl -X POST "http://localhost:8000/api/v1/retrieval/detect-domain" \\
             -F "file=@research_paper.pdf"

        # From text
        curl -X POST "http://localhost:8000/api/v1/retrieval/detect-domain" \\
             -F "text_sample=This paper discusses neural networks..."
        ```
    """
    import io

    try:
        # Require either file or text_sample
        if not file and not text_sample:
            raise HTTPException(
                status_code=400,
                detail="Either 'file' or 'text_sample' must be provided",
            )

        # Extract text sample
        extracted_text = ""
        sample_length = 0

        if text_sample:
            extracted_text = text_sample
            sample_length = len(text_sample)
            logger.info("domain_detection_from_text", sample_length=sample_length)

        elif file:
            # Read file and extract first ~2000 characters
            file_content = await file.read()
            file_path = Path(file.filename)

            if file_path.suffix.lower() == ".pdf":
                # Extract text from PDF using pdfminer.six
                try:
                    from pdfminer.high_level import extract_text_to_fp
                    from pdfminer.layout import LAParams

                    output = io.StringIO()
                    extract_text_to_fp(
                        io.BytesIO(file_content),
                        output,
                        laparams=LAParams(),
                        maxpages=3,  # Only first 3 pages
                    )
                    extracted_text = output.getvalue()[:2000]
                    sample_length = len(extracted_text)

                except ImportError:
                    logger.error("pdfminer_not_installed")
                    raise HTTPException(
                        status_code=500,
                        detail="PDF support not available. Install pdfminer.six",
                    ) from None

            elif file_path.suffix.lower() in [".txt", ".md"]:
                # Plain text file
                extracted_text = file_content.decode("utf-8", errors="ignore")[:2000]
                sample_length = len(extracted_text)

            else:
                # Try as plain text
                try:
                    extracted_text = file_content.decode("utf-8", errors="ignore")[:2000]
                    sample_length = len(extracted_text)
                except Exception as e:
                    logger.warning("file_decode_failed", filename=file.filename, error=str(e))
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not extract text from file: {file.filename}",
                    ) from None

            logger.info(
                "domain_detection_from_file",
                filename=file.filename,
                sample_length=sample_length,
            )

        # Validate extracted text
        if not extracted_text or not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from input",
            )

        # Load domain classifier
        from src.components.domain_training import get_domain_classifier
        from src.components.domain_training.domain_seeder import get_active_domains

        classifier = get_domain_classifier()

        # Ensure domains are loaded
        if not classifier.is_loaded():
            await classifier.load_domains()

        # Classify document
        results = classifier.classify_document(
            text=extracted_text,
            top_k=3,
            sample_size=2000,
        )

        # Filter by active deployment profile domains
        active_domain_ids = await get_active_domains()
        filtered_results = [r for r in results if r["domain"] in active_domain_ids]

        # If no active domains match, return all results (backward compatibility)
        final_results = filtered_results if filtered_results else results

        # Load domain metadata from catalog
        from src.components.domain_training.domain_seeder import _load_seed_domains

        catalog = _load_seed_domains()
        domain_lookup = {d["domain_id"]: d for d in catalog.get("domains", [])}

        # Enrich results with domain names
        enriched_results = []
        for result in final_results:
            domain_id = result["domain"]
            domain_config = domain_lookup.get(domain_id, {})
            enriched_results.append(
                {
                    "domain_id": domain_id,
                    "name": domain_config.get("name", domain_id),
                    "score": result["score"],
                }
            )

        logger.info(
            "domain_detection_complete",
            num_results=len(enriched_results),
            top_match=enriched_results[0] if enriched_results else None,
        )

        return {
            "domains": enriched_results,
            "text_sample_length": sample_length,
            "classification_method": "bge_m3_similarity",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("domain_detection_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Domain detection failed: {str(e)}",
        ) from None


@router.post("/upload")
@limiter.limit(f"{settings.rate_limit_upload}/minute")  # Config-driven rate limit
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    namespace_id: str = Form("default"),
    domain_id: str = Form(None),
    current_user: str | None = Depends(get_current_user),
) -> IngestionResponse:
    """Upload and index a single document file.

    Sprint 21 Feature 21.2: LangGraph Ingestion Pipeline
    - Sequential pipeline: Docling → Chunking → Embedding (Qdrant) → Graph (Neo4j)
    - Container-based parsing with GPU acceleration
    - Progress tracking and error handling

    Sprint 125 Feature 125.9b: Domain-aware ingestion
    - Optional domain_id parameter for manual domain assignment
    - If not provided, domain will be auto-detected by ingestion pipeline

    Args:
        request: FastAPI request (for rate limiting)
        file: Uploaded file (30 formats supported, see /formats endpoint)
        namespace_id: Namespace for data isolation (default: "default")
        domain_id: Optional domain identifier (e.g., "cs_it", "medicine_health")
        current_user: Authenticated user (optional)

    Returns:
        IngestionResponse with indexing statistics for all systems

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/upload" \\
             -F "file=@document.pdf" \\
             -F "namespace_id=my_namespace" \\
             -F "domain_id=computer_science_it"
        ```
    """
    import hashlib
    import shutil
    import tempfile

    from src.components.ingestion.format_router import ALL_FORMATS

    # Validate file format using FormatRouter (Sprint 22 Feature 22.3/22.4)
    file_path = Path(file.filename)

    # Check if format is supported
    if not _format_router.is_supported(file_path):
        supported_formats = sorted(ALL_FORMATS)
        logger.warning(
            "unsupported_format_upload",
            filename=file.filename,
            format=file_path.suffix,
            supported_count=len(supported_formats),
        )
        raise InvalidFileFormatError(
            filename=file.filename,
            expected_formats=supported_formats,
        )

    # Get routing decision (Docling or LlamaIndex)
    routing_decision = _format_router.route(file_path)

    logger.info(
        "upload_format_routing",
        filename=file.filename,
        format=routing_decision.format,
        parser=routing_decision.parser,
        reason=routing_decision.reason,
        confidence=routing_decision.confidence,
    )

    try:
        # Save uploaded file to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / file.filename

            # Save file
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            logger.info(
                "file_uploaded_to_temp", filename=file.filename, size=temp_path.stat().st_size
            )

            # Generate document ID (SHA-256 hash of file path)
            document_id = hashlib.sha256(str(temp_path).encode()).hexdigest()[:16]
            batch_id = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Use new LangGraph ingestion pipeline (Sprint 21)
            from src.components.ingestion import run_ingestion_pipeline

            start_time = datetime.now()
            final_state = await run_ingestion_pipeline(
                document_path=str(temp_path),
                document_id=document_id,
                batch_id=batch_id,
                batch_index=0,
                total_documents=1,
                namespace_id=namespace_id,
                domain_id=domain_id,  # Sprint 125.9b: Pass domain_id to pipeline
                max_retries=3,
            )
            duration_seconds = (datetime.now() - start_time).total_seconds()

            # Extract statistics from final state
            chunks_created = len(final_state.get("chunks", []))
            points_indexed = len(final_state.get("embedded_chunk_ids", []))
            # Sprint 82 Fix: Use count fields instead of empty arrays
            neo4j_entities = final_state.get("entities_count", 0)
            neo4j_relationships = final_state.get("relations_count", 0)

            logger.info(
                "file_ingestion_complete",
                filename=file.filename,
                documents=1,
                chunks_created=chunks_created,
                points_indexed=points_indexed,
                neo4j_entities=neo4j_entities,
                neo4j_relationships=neo4j_relationships,
                duration=duration_seconds,
                errors=len(final_state.get("errors", [])),
            )

            return IngestionResponse(
                status="success" if final_state.get("graph_status") == "completed" else "partial",
                documents_loaded=1,
                chunks_created=chunks_created,
                embeddings_generated=points_indexed,
                points_indexed=points_indexed,
                duration_seconds=duration_seconds,
                collection_name="aegis_rag_docs",  # Default collection name
                neo4j_entities=neo4j_entities,
                neo4j_relationships=neo4j_relationships,
            )

    except Exception as e:
        logger.error("file_upload_failed", filename=file.filename, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}",
        ) from None


@router.get("/formats")
async def get_supported_formats() -> None:
    """Get list of all supported document formats.

    Returns format information including:
    - Total supported formats (30)
    - Formats by parser (Docling, LlamaIndex, Shared)
    - Parser capabilities (GPU acceleration, OCR accuracy, etc.)

    Sprint 22 Features 22.3/22.4: Hybrid Docling/LlamaIndex ingestion

    Returns:
        Dictionary with format support information

    Example:
        ```bash
        curl http://localhost:8000/api/v1/retrieval/formats
        ```
    """
    from src.components.ingestion.format_router import (
        ALL_FORMATS,
        DOCLING_FORMATS,
        LLAMAINDEX_EXCLUSIVE,
        SHARED_FORMATS,
    )

    return {
        "total_formats": len(ALL_FORMATS),
        "formats": {
            "docling_exclusive": sorted(DOCLING_FORMATS - SHARED_FORMATS),
            "llamaindex_exclusive": sorted(LLAMAINDEX_EXCLUSIVE),
            "shared": sorted(SHARED_FORMATS),
        },
        "parser_info": {
            "docling": {
                "formats": len(DOCLING_FORMATS | SHARED_FORMATS),
                "features": [
                    "GPU-accelerated OCR (95% accuracy)",
                    "Table extraction (92% accuracy)",
                    "Image extraction with BBox coordinates",
                    "Layout preservation",
                ],
            },
            "llamaindex": {
                "formats": len(LLAMAINDEX_EXCLUSIVE | SHARED_FORMATS),
                "features": [
                    "Text-only extraction",
                    "300+ connector ecosystem",
                    "E-book support (EPUB)",
                    "LaTeX and Markdown parsing",
                ],
            },
        },
        "all_formats": sorted(ALL_FORMATS),
    }


@router.post("/prepare-bm25")
@limiter.limit("2/hour")  # Rate limit: 2 requests per hour
async def prepare_bm25(
    request: Request,
    current_user: str | None = Depends(get_current_user),
):
    """Prepare BM25 index from Qdrant collection.

    This endpoint loads all documents from Qdrant and builds the BM25 index.
    Should be called once after document ingestion.

    Requires authentication (if enabled). Rate limited to 2 requests/hour.

    Args:
        request: FastAPI request (for rate limiting)
        current_user: Authenticated user (from JWT token)

    Returns:
        Statistics about BM25 indexing

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/prepare-bm25" \\
             -H "Authorization: Bearer <your-token>"
        ```
    """
    try:
        hybrid_search = get_hybrid_search()
        stats = await hybrid_search.prepare_bm25_index()

        return {
            "status": "success",
            **stats,
        }

    except Exception as e:
        logger.error("BM25 preparation failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"BM25 preparation failed: {str(e)}",
        ) from None


@router.get("/stats")
async def get_stats() -> None:
    """Get retrieval system statistics.

    Returns:
        Statistics about indexed documents and search performance

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/retrieval/stats"
        ```
    """
    try:
        pipeline = DocumentIngestionPipeline()
        collection_stats = await pipeline.get_collection_stats()

        hybrid_search = get_hybrid_search()
        bm25_corpus_size = (
            hybrid_search.bm25_search.get_corpus_size()
            if hybrid_search.bm25_search.is_fitted()
            else 0
        )

        return {
            "status": "success",
            "qdrant_stats": collection_stats or {},
            "bm25_corpus_size": bm25_corpus_size,
            "bm25_fitted": hybrid_search.bm25_search.is_fitted(),
        }

    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}") from None


# Authentication Endpoint
class TokenRequest(BaseModel):
    """Token request model."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


@router.post("/auth/token", response_model=TokenResponse)
@limiter.limit("10/minute")  # Rate limit: 10 login attempts per minute
async def login(
    request: Request,
    credentials: TokenRequest,
) -> None:
    """Authenticate and get JWT access token.

    Args:
        request: FastAPI request (for rate limiting)
        credentials: Token request with credentials

    Returns:
        TokenResponse with JWT access token

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/auth/token" \\
             -H "Content-Type: application/json" \\
             -d '{"username": "admin", "password": "admin123"}'
        ```
    """
    from src.api.auth.jwt import create_access_token
    from src.core.config import settings

    # Simple hardcoded authentication (replace with database lookup in production)
    if (
        credentials.username == "admin"
        and credentials.password == settings.api_admin_password.get_secret_value()
    ):
        token = create_access_token(data={"sub": credentials.username})
        logger.info("User authenticated", username=credentials.username)
        return TokenResponse(access_token=token)

    logger.warning("Authentication failed", username=credentials.username)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Sprint 125 Feature 125.9c: Deployment Profile Management
@router.get("/admin/deployment-profile")
async def get_deployment_profile(
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current deployment profile and active domains.

    Sprint 125 Feature 125.9c: Deployment Profile API

    Returns the currently active deployment profile and list of enabled domains.

    Returns:
        Dictionary with:
        - profile_name: Current profile (e.g., "pharma_company", "university")
        - active_domains: List of domain IDs enabled for this profile
        - domain_count: Number of active domains

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/retrieval/admin/deployment-profile"
        ```
    """
    try:
        from src.components.domain_training.domain_seeder import (
            _load_seed_domains,
            get_active_domains,
        )
        from src.core.config import settings

        import redis.asyncio as aioredis

        # Get active profile from Redis
        redis_client = aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            encoding="utf-8",
            decode_responses=True,
        )

        profile_name = await redis_client.get("aegis:deployment_profile")
        await redis_client.close()

        # Get active domains
        active_domains = await get_active_domains()

        # Load catalog for profile metadata
        catalog = _load_seed_domains()
        profiles = catalog.get("deployment_profiles", {})
        profile_config = profiles.get(profile_name, {}) if profile_name else {}

        logger.info(
            "deployment_profile_retrieved",
            profile=profile_name or "none",
            active_domains_count=len(active_domains),
        )

        return {
            "profile_name": profile_name or None,
            "profile_display_name": profile_config.get("name", profile_name),
            "active_domains": active_domains,
            "domain_count": len(active_domains),
        }

    except Exception as e:
        logger.error("get_deployment_profile_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve deployment profile: {str(e)}",
        ) from None


@router.put("/admin/deployment-profile")
async def set_deployment_profile_endpoint(
    profile_name: str = Form(...),
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    """Set deployment profile (activates relevant domains).

    Sprint 125 Feature 125.9c: Deployment Profile API

    Sets the active deployment profile, which determines which domains are
    enabled for document classification and search filtering.

    Args:
        profile_name: Profile to activate (e.g., "pharma_company", "law_firm", "university")

    Returns:
        Dictionary with updated profile information

    Example:
        ```bash
        curl -X PUT "http://localhost:8000/api/v1/retrieval/admin/deployment-profile" \\
             -F "profile_name=pharma_company"
        ```
    """
    try:
        from src.components.domain_training.domain_seeder import (
            get_active_domains,
            set_deployment_profile,
        )

        # Set profile (validates against seed catalog)
        success = await set_deployment_profile(profile_name)

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid profile name: {profile_name}",
            )

        # Get updated active domains
        active_domains = await get_active_domains()

        logger.info(
            "deployment_profile_updated",
            profile=profile_name,
            active_domains_count=len(active_domains),
        )

        return {
            "status": "success",
            "profile_name": profile_name,
            "active_domains": active_domains,
            "domain_count": len(active_domains),
        }

    except ValueError as e:
        logger.warning("invalid_deployment_profile", profile=profile_name, error=str(e))
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.error("set_deployment_profile_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set deployment profile: {str(e)}",
        ) from None


@router.get("/admin/domains")
async def list_domains(
    current_user: str | None = Depends(get_current_user),
) -> dict[str, Any]:
    """List all available domains from seed catalog.

    Sprint 125 Feature 125.9c: Domain Catalog API

    Returns the complete list of 35 domains from seed_domains.yaml with
    metadata including DDC codes, FORD codes, keywords, and entity sub-types.

    Returns:
        Dictionary with:
        - domains: List of all domain configurations
        - total_domains: Number of domains in catalog
        - deployment_profiles: Available deployment profiles

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/retrieval/admin/domains"
        ```
    """
    try:
        from src.components.domain_training.domain_seeder import _load_seed_domains

        # Load full catalog
        catalog = _load_seed_domains()

        domains = catalog.get("domains", [])
        profiles = catalog.get("deployment_profiles", {})

        logger.info("domains_catalog_retrieved", total_domains=len(domains))

        return {
            "domains": domains,
            "total_domains": len(domains),
            "deployment_profiles": profiles,
        }

    except Exception as e:
        logger.error("list_domains_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve domains: {str(e)}",
        ) from None
