"""Retrieval API Endpoints - Sprint 2.

FastAPI endpoints for document ingestion and hybrid search retrieval.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from src.components.vector_search import (
    HybridSearch,
    DocumentIngestionPipeline,
    ingest_documents,
)
from src.core.models import QueryRequest, QueryResponse, HealthResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


# Request/Response Models
class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query text", min_length=1)
    top_k: int = Field(10, description="Number of results to return", ge=1, le=100)
    search_type: str = Field(
        "hybrid",
        description="Search type: 'vector', 'bm25', or 'hybrid'",
    )
    score_threshold: Optional[float] = Field(
        None,
        description="Minimum similarity score for vector search",
        ge=0,
        le=1,
    )


class SearchResult(BaseModel):
    """Single search result."""

    id: str
    text: str
    score: float
    source: str
    document_id: str
    rank: int
    rrf_score: Optional[float] = None


class SearchResponse(BaseModel):
    """Search response model."""

    query: str
    results: List[SearchResult]
    total_results: int
    search_type: str
    search_metadata: Optional[Dict[str, Any]] = None


class IngestionRequest(BaseModel):
    """Document ingestion request."""

    input_dir: str = Field(..., description="Directory containing documents")
    chunk_size: int = Field(512, description="Maximum tokens per chunk", ge=128, le=2048)
    chunk_overlap: int = Field(128, description="Overlap between chunks", ge=0, le=512)
    file_extensions: Optional[List[str]] = Field(
        None,
        description="File extensions to process (default: .pdf, .txt, .md)",
    )


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
_hybrid_search: Optional[HybridSearch] = None


def get_hybrid_search() -> HybridSearch:
    """Get or create hybrid search instance."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch()
    return _hybrid_search


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
) -> SearchResponse:
    """Search documents using vector, BM25, or hybrid search.

    Args:
        request: Search request parameters

    Returns:
        SearchResponse with ranked results

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/search" \\
             -H "Content-Type: application/json" \\
             -d '{"query": "What is RAG?", "search_type": "hybrid", "top_k": 10}'
        ```
    """
    try:
        hybrid_search = get_hybrid_search()

        if request.search_type == "hybrid":
            # Hybrid search (Vector + BM25 + RRF)
            result = await hybrid_search.hybrid_search(
                query=request.query,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
            )

            return SearchResponse(
                query=result["query"],
                results=[SearchResult(**r) for r in result["results"]],
                total_results=result["total_results"],
                search_type="hybrid",
                search_metadata=result["search_metadata"],
            )

        elif request.search_type == "vector":
            # Vector-only search
            results = await hybrid_search.vector_search(
                query=request.query,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
            )

            return SearchResponse(
                query=request.query,
                results=[SearchResult(**r) for r in results],
                total_results=len(results),
                search_type="vector",
            )

        elif request.search_type == "bm25":
            # BM25-only search
            results = await hybrid_search.keyword_search(
                query=request.query,
                top_k=request.top_k,
            )

            return SearchResponse(
                query=request.query,
                results=[SearchResult(**r) for r in results],
                total_results=len(results),
                search_type="bm25",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_type: {request.search_type}. Use 'vector', 'bm25', or 'hybrid'.",
            )

    except Exception as e:
        logger.error("Search failed", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/ingest", response_model=IngestionResponse)
async def ingest(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
) -> IngestionResponse:
    """Ingest documents from directory into vector database.

    Args:
        request: Ingestion request parameters
        background_tasks: FastAPI background tasks

    Returns:
        IngestionResponse with statistics

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/ingest" \\
             -H "Content-Type: application/json" \\
             -d '{"input_dir": "./data/documents", "chunk_size": 512}'
        ```
    """
    try:
        # Validate input directory
        input_path = Path(request.input_dir)
        if not input_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Input directory does not exist: {request.input_dir}",
            )

        if not input_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Input path is not a directory: {request.input_dir}",
            )

        # Run ingestion
        pipeline = DocumentIngestionPipeline(
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        stats = await pipeline.index_documents(
            input_dir=input_path,
            required_exts=request.file_extensions,
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ingestion failed", error=str(e), input_dir=request.input_dir)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/prepare-bm25")
async def prepare_bm25():
    """Prepare BM25 index from Qdrant collection.

    This endpoint loads all documents from Qdrant and builds the BM25 index.
    Should be called once after document ingestion.

    Returns:
        Statistics about BM25 indexing

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/v1/retrieval/prepare-bm25"
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
        )


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
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
