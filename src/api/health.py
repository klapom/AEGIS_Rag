"""Health check endpoints."""

import time
from typing import Any

import httpx
from fastapi import APIRouter, status
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from redis import Redis

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.models import HealthResponse, HealthStatus, ServiceHealth

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


async def check_qdrant() -> ServiceHealth:
    """Check Qdrant vector database health."""
    settings = get_settings()
    start_time = time.time()

    try:
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
            timeout=5,
        )
        # Simple health check
        _ = client.get_collections()
        latency_ms = (time.time() - start_time) * 1000

        return ServiceHealth(status=HealthStatus.HEALTHY, latency_ms=latency_ms, error=None)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("qdrant_health_check_failed", error=str(e))
        return ServiceHealth(status=HealthStatus.UNHEALTHY, latency_ms=latency_ms, error=str(e))


async def check_neo4j() -> ServiceHealth:
    """Check Neo4j graph database health."""
    settings = get_settings()
    start_time = time.time()

    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run("RETURN 1 AS health")
            _ = result.single()

        driver.close()
        latency_ms = (time.time() - start_time) * 1000

        return ServiceHealth(status=HealthStatus.HEALTHY, latency_ms=latency_ms, error=None)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("neo4j_health_check_failed", error=str(e))
        return ServiceHealth(status=HealthStatus.UNHEALTHY, latency_ms=latency_ms, error=str(e))


async def check_redis() -> ServiceHealth:
    """Check Redis cache health."""
    settings = get_settings()
    start_time = time.time()

    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=5.0)
        client.ping()
        client.close()
        latency_ms = (time.time() - start_time) * 1000

        return ServiceHealth(status=HealthStatus.HEALTHY, latency_ms=latency_ms, error=None)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("redis_health_check_failed", error=str(e))
        return ServiceHealth(status=HealthStatus.UNHEALTHY, latency_ms=latency_ms, error=str(e))


async def check_ollama() -> ServiceHealth:
    """Check Ollama LLM server health."""
    settings = get_settings()
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()

        latency_ms = (time.time() - start_time) * 1000

        return ServiceHealth(status=HealthStatus.HEALTHY, latency_ms=latency_ms, error=None)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("ollama_health_check_failed", error=str(e))
        return ServiceHealth(status=HealthStatus.UNHEALTHY, latency_ms=latency_ms, error=str(e))


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
    description="Check health of all system components",
)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check for all services.

    Returns:
        Health status of all system components
    """
    settings = get_settings()

    # Check all services
    qdrant_health = await check_qdrant()
    neo4j_health = await check_neo4j()
    redis_health = await check_redis()
    ollama_health = await check_ollama()

    services = {
        "qdrant": qdrant_health,
        "neo4j": neo4j_health,
        "redis": redis_health,
        "ollama": ollama_health,
    }

    # Determine overall status
    unhealthy_count = sum(1 for s in services.values() if s.status == HealthStatus.UNHEALTHY)
    degraded_count = sum(1 for s in services.values() if s.status == HealthStatus.DEGRADED)

    if unhealthy_count > 0:
        overall_status = HealthStatus.UNHEALTHY
    elif degraded_count > 0:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    logger.info(
        "health_check_completed",
        status=overall_status.value,
        unhealthy=unhealthy_count,
        degraded=degraded_count,
    )

    return HealthResponse(status=overall_status, version=settings.app_version, services=services)


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes",
)
async def liveness() -> dict[str, str]:
    """
    Liveness probe for Kubernetes.

    Returns:
        Simple status response
    """
    return {"status": "alive"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Readiness check for Kubernetes",
)
async def readiness() -> dict[str, Any]:
    """
    Readiness probe for Kubernetes.

    Checks if the service is ready to accept traffic.

    Returns:
        Readiness status
    """
    # Quick check of critical services
    try:
        qdrant_health = await check_qdrant()
        ollama_health = await check_ollama()

        if (
            qdrant_health.status == HealthStatus.HEALTHY
            and ollama_health.status == HealthStatus.HEALTHY
        ):
            return {"status": "ready", "services": ["qdrant", "ollama"]}
        else:
            return {"status": "not_ready", "reason": "Critical services unavailable"}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return {"status": "not_ready", "reason": str(e)}
