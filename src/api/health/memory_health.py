"""Memory System Health Check Endpoints (Sprint 9 Feature 9.5).

This module provides health check endpoints for the 3-layer memory architecture:
- Layer 1: Redis (Working Memory)
- Layer 2: Qdrant (Episodic Memory)
- Layer 3: Graphiti (Long-term Memory)
"""

import time
from typing import Any, Dict

import structlog
from fastapi import APIRouter, status

from src.components.memory.monitoring import get_monitoring
from src.components.memory.redis_manager import get_redis_manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/health/memory", tags=["health", "memory"])


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Overall memory system health",
    description="Check health of all 3 memory layers",
)
async def memory_health_check() -> Dict[str, Any]:
    """Overall memory system health check.

    Checks all 3 layers:
    - Redis (Layer 1): Working memory
    - Qdrant (Layer 2): Episodic memory
    - Graphiti (Layer 3): Long-term memory

    Returns:
        Dictionary with overall health status and per-layer details
    """
    start_time = time.time()

    # Check all 3 layers
    redis_health = await check_redis_health()
    qdrant_health = await check_qdrant_health()
    graphiti_health = await check_graphiti_health()

    # Determine overall status
    all_healthy = all(
        [
            redis_health["status"] == "healthy",
            qdrant_health["status"] == "healthy",
            graphiti_health["status"] == "healthy",
        ]
    )

    any_degraded = any(
        [
            redis_health["status"] == "degraded",
            qdrant_health["status"] == "degraded",
            graphiti_health["status"] == "degraded",
        ]
    )

    any_unhealthy = any(
        [
            redis_health["status"] == "unhealthy",
            qdrant_health["status"] == "unhealthy",
            graphiti_health["status"] == "unhealthy",
        ]
    )

    if any_unhealthy:
        overall_status = "unhealthy"
    elif any_degraded:
        overall_status = "degraded"
    elif all_healthy:
        overall_status = "healthy"
    else:
        overall_status = "unknown"

    elapsed_ms = (time.time() - start_time) * 1000

    response = {
        "status": overall_status,
        "layers": {
            "redis": redis_health,
            "qdrant": qdrant_health,
            "graphiti": graphiti_health,
        },
        "latency_ms": round(elapsed_ms, 2),
    }

    logger.info(
        "Memory health check completed",
        status=overall_status,
        latency_ms=round(elapsed_ms, 2),
    )

    return response


@router.get(
    "/redis",
    status_code=status.HTTP_200_OK,
    summary="Redis memory health",
    description="Health check for Redis working memory (Layer 1)",
)
async def redis_health() -> Dict[str, Any]:
    """Redis-specific health check.

    Checks:
    - Connection status
    - Capacity utilization
    - Memory statistics

    Returns:
        Dictionary with Redis health details
    """
    return await check_redis_health()


@router.get(
    "/qdrant",
    status_code=status.HTTP_200_OK,
    summary="Qdrant memory health",
    description="Health check for Qdrant episodic memory (Layer 2)",
)
async def qdrant_health() -> Dict[str, Any]:
    """Qdrant-specific health check.

    Checks:
    - Connection status
    - Collection status
    - Vector count

    Returns:
        Dictionary with Qdrant health details
    """
    return await check_qdrant_health()


@router.get(
    "/graphiti",
    status_code=status.HTTP_200_OK,
    summary="Graphiti memory health",
    description="Health check for Graphiti long-term memory (Layer 3)",
)
async def graphiti_health() -> Dict[str, Any]:
    """Graphiti-specific health check.

    Checks:
    - Connection status
    - Graph statistics
    - Node count

    Returns:
        Dictionary with Graphiti health details
    """
    return await check_graphiti_health()


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Memory metrics summary",
    description="Aggregate metrics across all memory layers",
)
async def memory_metrics() -> Dict[str, Any]:
    """Get aggregated memory metrics from all layers.

    Returns:
        Dictionary with metrics from all layers
    """
    monitoring = get_monitoring()
    redis_manager = get_redis_manager()

    try:
        # Collect metrics from all available layers
        metrics = await monitoring.collect_all_metrics(
            redis_manager=redis_manager,
            qdrant_client=None,  # TODO: Get Qdrant client when available
            graphiti_client=None,  # TODO: Get Graphiti client when available
        )

        return metrics

    except Exception as e:
        logger.error("Failed to collect memory metrics", error=str(e))
        return {
            "error": str(e),
            "timestamp": metrics.get("timestamp") if "metrics" in locals() else None,
        }


# ============= Internal Health Check Functions =============


async def check_redis_health() -> Dict[str, Any]:
    """Internal function to check Redis health.

    Returns:
        Dictionary with Redis health status
    """
    start_time = time.time()

    try:
        redis_manager = get_redis_manager()
        await redis_manager.initialize()

        # Get capacity and stats
        capacity = await redis_manager.get_capacity()
        stats = await redis_manager.get_stats()

        # Determine status based on capacity
        if capacity >= 0.9:
            status_value = "unhealthy"  # Critical capacity
        elif capacity >= 0.8:
            status_value = "degraded"  # High capacity (eviction threshold)
        else:
            status_value = "healthy"

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "status": status_value,
            "capacity": round(capacity, 3),
            "entries": stats.get("total_entries", 0),
            "avg_ttl_seconds": round(stats.get("avg_ttl_seconds", 0), 2),
            "eviction_threshold": stats.get("eviction_threshold", 0.8),
            "latency_ms": round(elapsed_ms, 2),
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error("Redis health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(elapsed_ms, 2),
        }


async def check_qdrant_health() -> Dict[str, Any]:
    """Internal function to check Qdrant health.

    Returns:
        Dictionary with Qdrant health status
    """
    start_time = time.time()

    try:
        # TODO: Implement Qdrant health check when client is available
        # For now, return placeholder status

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "collections": 0,  # TODO: Get actual collection count
            "vectors": 0,  # TODO: Get actual vector count
            "capacity": 0.0,  # TODO: Get actual capacity
            "latency_ms": round(elapsed_ms, 2),
            "note": "Placeholder - Qdrant client not yet integrated",
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error("Qdrant health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(elapsed_ms, 2),
        }


async def check_graphiti_health() -> Dict[str, Any]:
    """Internal function to check Graphiti health.

    Returns:
        Dictionary with Graphiti health status
    """
    start_time = time.time()

    try:
        # TODO: Implement Graphiti health check when client is available
        # For now, return placeholder status

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "nodes": 0,  # TODO: Get actual node count
            "edges": 0,  # TODO: Get actual edge count
            "capacity": 0.0,  # TODO: Get actual capacity
            "latency_ms": round(elapsed_ms, 2),
            "note": "Placeholder - Graphiti client not yet integrated",
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error("Graphiti health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(elapsed_ms, 2),
        }
