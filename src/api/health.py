"""Health check endpoints."""

import time
from typing import Any

import httpx
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from redis import Redis

# Import memory health router (Sprint 9 Feature 9.5)
from src.api.health.memory_health import router as memory_health_router
from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.models import HealthResponse, HealthStatus, ServiceHealth

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


# Sprint 51: Container health models
class ContainerHealth(BaseModel):
    """Container health information."""

    name: str = Field(..., description="Container name")
    status: str = Field(..., description="Container status (running, stopped, etc)")
    health: str = Field(default="unknown", description="Health status if available")
    image: str = Field(default="", description="Container image")
    created: str = Field(default="", description="Creation timestamp")
    logs: list[str] = Field(default_factory=list, description="Recent log lines")


class ContainersResponse(BaseModel):
    """Response for container health check."""

    containers: list[ContainerHealth] = Field(default_factory=list)
    docker_available: bool = Field(default=False, description="Whether Docker is accessible")
    error: str | None = Field(default=None, description="Error message if any")


class PrometheusMetric(BaseModel):
    """Single Prometheus metric."""

    name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)


class PrometheusMetricsResponse(BaseModel):
    """Response for Prometheus metrics."""

    metrics: list[PrometheusMetric] = Field(default_factory=list)
    prometheus_available: bool = Field(default=False)
    error: str | None = Field(default=None)


# Include memory health endpoints
router.include_router(memory_health_router)


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
    start_time = time.time()

    try:
        client = get_neo4j_client()
        await client.health_check()
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


async def check_docling() -> ServiceHealth:
    """Check Docling document processing service health."""
    settings = get_settings()
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.docling_base_url}/health")
            response.raise_for_status()

        latency_ms = (time.time() - start_time) * 1000

        return ServiceHealth(status=HealthStatus.HEALTHY, latency_ms=latency_ms, error=None)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error("docling_health_check_failed", error=str(e))
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
    docling_health = await check_docling()

    services = {
        "qdrant": qdrant_health,
        "neo4j": neo4j_health,
        "redis": redis_health,
        "ollama": ollama_health,
        "docling": docling_health,
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
            return {"status": "ready", "services": ["qdrant", "ollama"]}  # type: ignore[no-any-return]
        else:
            return {"status": "not_ready", "reason": "Critical services unavailable"}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        return {"status": "not_ready", "reason": str(e)}


# Sprint 51: Container health endpoints
@router.get(
    "/health/containers",
    response_model=ContainersResponse,
    summary="Container health check",
    description="Get health status and logs of Docker containers",
)
async def container_health(tail: int = 50) -> ContainersResponse:
    """
    Get Docker container health status and recent logs.

    Args:
        tail: Number of log lines to return per container (default: 50)

    Returns:
        Container health information including logs
    """
    try:
        import docker

        client = docker.from_env()
        containers_info = []

        # Filter for aegis-related containers
        container_prefixes = ["aegis", "qdrant", "neo4j", "redis", "ollama", "docling"]

        for container in client.containers.list(all=True):
            container_name = container.name.lower()

            # Check if container name matches any prefix
            if any(prefix in container_name for prefix in container_prefixes):
                # Get container logs
                try:
                    logs = container.logs(tail=tail, timestamps=True).decode("utf-8")
                    log_lines = logs.strip().split("\n") if logs.strip() else []
                except Exception as log_err:
                    logger.warning(
                        "container_logs_failed", container=container.name, error=str(log_err)
                    )
                    log_lines = [f"Error fetching logs: {log_err}"]

                # Get health status if available
                health_status = "unknown"
                if container.attrs.get("State", {}).get("Health"):
                    health_status = container.attrs["State"]["Health"].get("Status", "unknown")

                containers_info.append(
                    ContainerHealth(
                        name=container.name,
                        status=container.status,
                        health=health_status,
                        image=(
                            container.image.tags[0]
                            if container.image.tags
                            else str(container.image.id)[:12]
                        ),
                        created=container.attrs.get("Created", ""),
                        logs=log_lines[-tail:] if log_lines else [],
                    )
                )

        # Sort by name
        containers_info.sort(key=lambda c: c.name)

        return ContainersResponse(containers=containers_info, docker_available=True, error=None)

    except ImportError:
        logger.warning("docker_sdk_not_installed")
        return ContainersResponse(
            containers=[],
            docker_available=False,
            error="Docker SDK not installed. Install with: pip install docker",
        )
    except Exception as e:
        logger.error("container_health_check_failed", error=str(e))
        return ContainersResponse(containers=[], docker_available=False, error=str(e))


@router.get(
    "/health/metrics",
    response_model=PrometheusMetricsResponse,
    summary="Prometheus metrics",
    description="Get key performance metrics from Prometheus",
)
async def prometheus_metrics() -> PrometheusMetricsResponse:
    """
    Get key performance metrics from Prometheus.

    Returns:
        Selected Prometheus metrics for dashboard display
    """
    settings = get_settings()
    prometheus_url = getattr(settings, "prometheus_url", "http://localhost:9090")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Query key metrics
            metrics = []

            # Define queries for important metrics
            # Metric names align with actual Prometheus exports from aegis-api and qdrant
            queries = [
                (
                    "rag_requests_total",
                    'sum(aegis_rag_requests_total{job="aegis-api"}) or vector(0)',
                ),
                (
                    "rag_latency_p99_ms",
                    'histogram_quantile(0.99, sum(rate(aegis_rag_request_latency_seconds_bucket{job="aegis-api"}[5m])) by (le)) * 1000 or vector(0)',
                ),
                ("cpu_seconds", 'process_cpu_seconds_total{job="aegis-api"}'),
                ("memory_mb", 'process_resident_memory_bytes{job="aegis-api"} / 1024 / 1024'),
                ("qdrant_requests", "sum(qdrant_grpc_requests_total) or vector(0)"),
                (
                    "chunking_operations",
                    'sum(aegis_chunking_chunk_size_tokens_count{job="aegis-api"}) or vector(0)',
                ),
            ]

            for metric_name, query in queries:
                try:
                    response = await client.get(
                        f"{prometheus_url}/api/v1/query",
                        params={"query": query},
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "success" and data.get("data", {}).get("result"):
                            result = data["data"]["result"][0]
                            value = float(result.get("value", [0, 0])[1])
                            labels = result.get("metric", {})

                            metrics.append(
                                PrometheusMetric(name=metric_name, value=value, labels=labels)
                            )
                except Exception as query_err:
                    logger.debug(
                        "prometheus_query_failed", metric=metric_name, error=str(query_err)
                    )

            return PrometheusMetricsResponse(
                metrics=metrics,
                prometheus_available=len(metrics) > 0,
                error=None if metrics else "No metrics available",
            )

    except httpx.ConnectError:
        return PrometheusMetricsResponse(
            metrics=[],
            prometheus_available=False,
            error=f"Cannot connect to Prometheus at {prometheus_url}",
        )
    except Exception as e:
        logger.error("prometheus_metrics_failed", error=str(e))
        return PrometheusMetricsResponse(metrics=[], prometheus_available=False, error=str(e))
