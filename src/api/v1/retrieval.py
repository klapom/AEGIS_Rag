"""Retrieval API Endpoints - Sprint 2.

FastAPI endpoints for document ingestion and hybrid search retrieval.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel, Field

from src.api.auth.jwt import get_current_user
from src.api.middleware import limiter
from src.components.retrieval import MetadataFilters
from src.components.vector_search import (
    DocumentIngestionPipeline,
    HybridSearch,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


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

    class Config:
        # P1: Validate assignment to prevent invalid data
        validate_assignment = True
        # P1: Strict validation
        str_strip_whitespace = True


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

    class Config:
        validate_assignment = True
        str_strip_whitespace = True


class IngestionResponse(BaseModel):
    """Document ingestion response."""

    status: str
    documents_loaded: int
    chunks_created: int
    embeddings_generated: int
    points_indexed: int
    duration_seconds: float
    collection_name: str


# Global hybrid search instance
_hybrid_search: HybridSearch | None = None


def get_hybrid_search() -> HybridSearch:
    """Get or create hybrid search instance."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search


@router.post("/search", response_model=SearchResponse)
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute
async def search(
    request: Request,
    search_params: SearchRequest,
    current_user: str | None = Depends(get_current_user),
) -> SearchResponse:
    """Search documents using vector, BM25, or hybrid search.

    Requires authentication (if enabled). Rate limited to 10 requests/minute.

    Args:
        request: FastAPI request (for rate limiting)
        search_params: Search request parameters
        current_user: Authenticated user (from JWT token)

    Returns:
        SearchResponse with ranked results

    Example:
        ```bash
        # With authentication
        curl -X POST "http://localhost:8000/api/v1/retrieval/search" \\
             -H "Content-Type: application/json" \\
             -H "Authorization: Bearer <your-token>" \\
             -d '{"query": "What is RAG?", "search_type": "hybrid", "top_k": 10}'
        ```
    """
    try:
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
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metadata filters: {str(e)}",
                ) from None

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Search failed", error=str(e), query=search_params.query, exc_info=True)
        # P1: Don't expose internal error details to client
        raise HTTPException(
            status_code=500, detail="Search operation failed. Please try again or contact support."
        ) from None


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
            raise HTTPException(
                status_code=400,
                detail=f"Input directory does not exist: {ingest_params.input_dir}",
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

        # Prepare BM25 index in background
        hybrid_search = get_hybrid_search()
        background_tasks.add_task(hybrid_search.prepare_bm25_index)

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
    except Exception as e:
        logger.error(
            "Ingestion failed", error=str(e), input_dir=ingest_params.input_dir, exc_info=True
        )
        # P1: Don't expose internal error details
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed. Please check your input and try again.",
        ) from None


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
async def get_stats():
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
):
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
