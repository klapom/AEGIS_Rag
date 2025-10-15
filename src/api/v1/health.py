"""Health Check Endpoints - P2 Issue Fix.

Provides comprehensive health checks for all system dependencies.
"""

from typing import Any

import structlog
from fastapi import APIRouter
from fastapi import status as http_status
from pydantic import BaseModel

from src.components.vector_search import EmbeddingService, QdrantClientWrapper
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health check status."""

    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    environment: str


class DependencyHealth(BaseModel):
    """Individual dependency health."""

    name: str
    status: str  # "up", "down", "degraded"
    latency_ms: float
    details: dict[str, Any]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""

    status: str
    version: str
    environment: str
    dependencies: dict[str, DependencyHealth]


@router.get("/", response_model=HealthStatus, status_code=http_status.HTTP_200_OK)
async def health_check():
    """Basic health check - lightweight endpoint for load balancers.

    Returns:
        HealthStatus indicating service is running

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/health/"
        ```
    """
    return HealthStatus(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with dependency status.

    Checks connectivity to:
    - Qdrant vector database
    - Ollama embedding service
    - (Future: Neo4j, Redis)

    Returns:
        DetailedHealthResponse with all dependency statuses

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/health/detailed"
        ```
    """
    dependencies = {}
    overall_status = "healthy"

    # Check Qdrant
    try:
        import time

        start = time.time()

        qdrant = QdrantClientWrapper()
        collections = await qdrant.async_client.get_collections()

        latency_ms = (time.time() - start) * 1000

        dependencies["qdrant"] = DependencyHealth(
            name="Qdrant Vector Database",
            status="up",
            latency_ms=round(latency_ms, 2),
            details={
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
                "collections_count": len(collections.collections) if collections else 0,
            },
        )

    except Exception as e:
        logger.error("Qdrant health check failed", error=str(e))
        dependencies["qdrant"] = DependencyHealth(
            name="Qdrant Vector Database",
            status="down",
            latency_ms=0.0,
            details={"error": "Connection failed"},
        )
        overall_status = "unhealthy"

    # Check Ollama Embedding Service
    try:
        import time

        start = time.time()

        embedding_service = EmbeddingService()
        test_embedding = await embedding_service.embed_text("health check")

        latency_ms = (time.time() - start) * 1000

        dependencies["ollama_embeddings"] = DependencyHealth(
            name="Ollama Embedding Service",
            status="up",
            latency_ms=round(latency_ms, 2),
            details={
                "model": settings.ollama_model_embedding,
                "base_url": settings.ollama_base_url,
                "embedding_dimension": len(test_embedding),
            },
        )

    except Exception as e:
        logger.error("Ollama embedding health check failed", error=str(e))
        dependencies["ollama_embeddings"] = DependencyHealth(
            name="Ollama Embedding Service",
            status="down",
            latency_ms=0.0,
            details={"error": "Service unavailable"},
        )
        overall_status = "degraded" if overall_status == "healthy" else "unhealthy"

    return DetailedHealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        dependencies=dependencies,
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check - indicates if service can handle requests.

    Returns 200 if all critical dependencies are available, 503 otherwise.

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/health/ready"
        ```
    """
    try:
        # Check critical dependencies
        qdrant = QdrantClientWrapper()
        await qdrant.async_client.get_collections()

        return {"status": "ready", "message": "Service is ready to accept requests"}

    except Exception as e:
        logger.warning("Readiness check failed", error=str(e))
        from fastapi import HTTPException

        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service not ready"
        ) from e


@router.get("/live")
async def liveness_check():
    """Liveness check - indicates if service is alive.

    Always returns 200 unless application is completely broken.

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/health/live"
        ```
    """
    return {"status": "alive", "message": "Service is running"}
