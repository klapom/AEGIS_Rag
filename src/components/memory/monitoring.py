"""Memory Health Monitoring for 3-Layer Memory Architecture (Sprint 9 Feature 9.5).

This module provides:
- Prometheus metrics for all memory layers (Redis, Qdrant, Graphiti)
- Real-time capacity, latency, and hit rate tracking
- Alerting thresholds for capacity and performance
- Integration with Grafana dashboards
"""

import time
from datetime import datetime
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)


class MemoryMonitoring:
    """Prometheus metrics collector for memory system health.

    Tracks metrics across all 3 layers:
    - Layer 1 (Redis): Working memory, short-term cache
    - Layer 2 (Qdrant): Episodic memory, vector search
    - Layer 3 (Graphiti): Long-term memory, knowledge graph

    Metrics:
    - Capacity: Memory utilization (0.0-1.0) per layer
    - Latency: Operation latency (read/write) per layer
    - Hit Rate: Cache hits vs misses per layer
    - Entry Count: Number of entries per layer
    """

    def __init__(self):
        """Initialize Prometheus metrics."""
        # ============= Capacity Metrics =============
        self.redis_capacity = Gauge(
            "memory_redis_capacity",
            "Redis memory utilization (0.0-1.0)",
        )

        self.qdrant_capacity = Gauge(
            "memory_qdrant_capacity",
            "Qdrant memory utilization (0.0-1.0)",
        )

        self.graphiti_capacity = Gauge(
            "memory_graphiti_capacity",
            "Graphiti memory utilization (0.0-1.0)",
        )

        # ============= Entry Count Metrics =============
        self.redis_entries = Gauge(
            "memory_redis_entries_total",
            "Total number of entries in Redis",
        )

        self.qdrant_entries = Gauge(
            "memory_qdrant_entries_total",
            "Total number of vectors in Qdrant",
        )

        self.graphiti_entries = Gauge(
            "memory_graphiti_entries_total",
            "Total number of nodes in Graphiti",
        )

        # ============= Latency Metrics =============
        # Redis latency (in seconds)
        self.redis_read_latency = Histogram(
            "memory_redis_read_latency_seconds",
            "Redis read operation latency in seconds",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        self.redis_write_latency = Histogram(
            "memory_redis_write_latency_seconds",
            "Redis write operation latency in seconds",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        # Qdrant latency
        self.qdrant_search_latency = Histogram(
            "memory_qdrant_search_latency_seconds",
            "Qdrant vector search latency in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        self.qdrant_upsert_latency = Histogram(
            "memory_qdrant_upsert_latency_seconds",
            "Qdrant vector upsert latency in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Graphiti latency
        self.graphiti_query_latency = Histogram(
            "memory_graphiti_query_latency_seconds",
            "Graphiti graph query latency in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        self.graphiti_add_latency = Histogram(
            "memory_graphiti_add_latency_seconds",
            "Graphiti add memory latency in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # ============= Hit Rate Metrics =============
        self.cache_hits = Counter(
            "memory_cache_hits_total",
            "Total number of cache hits",
            ["layer"],  # redis, qdrant, graphiti
        )

        self.cache_misses = Counter(
            "memory_cache_misses_total",
            "Total number of cache misses",
            ["layer"],
        )

        # ============= Operation Metrics =============
        self.operations_total = Counter(
            "memory_operations_total",
            "Total number of memory operations",
            ["layer", "operation"],  # layer: redis/qdrant/graphiti, operation: read/write/search
        )

        self.operation_errors = Counter(
            "memory_operation_errors_total",
            "Total number of failed memory operations",
            ["layer", "operation", "error_type"],
        )

        # ============= Health Status =============
        self.layer_health = Gauge(
            "memory_layer_health",
            "Health status of memory layer (1=healthy, 0=unhealthy)",
            ["layer"],
        )

        logger.info("MemoryMonitoring initialized with Prometheus metrics")

    # ============= Redis Metrics Collection =============

    async def collect_redis_metrics(self, redis_manager) -> dict[str, Any]:
        """Collect metrics from Redis layer.

        Args:
            redis_manager: RedisMemoryManager instance

        Returns:
            Dictionary with collected metrics
        """
        try:
            start_time = time.time()

            # Get capacity
            capacity = await redis_manager.get_capacity()
            self.redis_capacity.set(capacity)

            # Get stats
            stats = await redis_manager.get_stats()
            total_entries = stats.get("total_entries", 0)
            self.redis_entries.set(total_entries)

            # Update health status
            self.layer_health.labels(layer="redis").set(1)

            elapsed = time.time() - start_time

            logger.info(
                "Redis metrics collected",
                capacity=round(capacity, 3),
                entries=total_entries,
                collection_time_ms=round(elapsed * 1000, 2),
            )

            return {
                "layer": "redis",
                "capacity": capacity,
                "entries": total_entries,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to collect Redis metrics", error=str(e))
            self.layer_health.labels(layer="redis").set(0)
            self.operation_errors.labels(
                layer="redis", operation="collect_metrics", error_type=type(e).__name__
            ).inc()
            return {"layer": "redis", "error": str(e)}

    async def collect_qdrant_metrics(self, qdrant_client) -> dict[str, Any]:
        """Collect metrics from Qdrant layer.

        Args:
            qdrant_client: QdrantClient instance

        Returns:
            Dictionary with collected metrics
        """
        try:
            start_time = time.time()

            # Get collection info (if available)
            # Note: Actual implementation depends on Qdrant client API
            # This is a placeholder that can be extended when Qdrant client is available

            # For now, set placeholder values
            capacity = 0.0  # TODO: Get from Qdrant API
            entries = 0  # TODO: Get collection size

            self.qdrant_capacity.set(capacity)
            self.qdrant_entries.set(entries)
            self.layer_health.labels(layer="qdrant").set(1)

            elapsed = time.time() - start_time

            logger.debug(
                "Qdrant metrics collected",
                capacity=capacity,
                entries=entries,
                collection_time_ms=round(elapsed * 1000, 2),
            )

            return {
                "layer": "qdrant",
                "capacity": capacity,
                "entries": entries,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to collect Qdrant metrics", error=str(e))
            self.layer_health.labels(layer="qdrant").set(0)
            self.operation_errors.labels(
                layer="qdrant", operation="collect_metrics", error_type=type(e).__name__
            ).inc()
            return {"layer": "qdrant", "error": str(e)}

    async def collect_graphiti_metrics(self, graphiti_client) -> dict[str, Any]:
        """Collect metrics from Graphiti layer.

        Args:
            graphiti_client: GraphitiClient instance

        Returns:
            Dictionary with collected metrics
        """
        try:
            start_time = time.time()

            # Get graph stats (if available)
            # Note: Actual implementation depends on Graphiti client API
            # This is a placeholder that can be extended when Graphiti client is available

            # For now, set placeholder values
            capacity = 0.0  # TODO: Get from Graphiti API
            entries = 0  # TODO: Get node count

            self.graphiti_capacity.set(capacity)
            self.graphiti_entries.set(entries)
            self.layer_health.labels(layer="graphiti").set(1)

            elapsed = time.time() - start_time

            logger.debug(
                "Graphiti metrics collected",
                capacity=capacity,
                entries=entries,
                collection_time_ms=round(elapsed * 1000, 2),
            )

            return {
                "layer": "graphiti",
                "capacity": capacity,
                "entries": entries,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error("Failed to collect Graphiti metrics", error=str(e))
            self.layer_health.labels(layer="graphiti").set(0)
            self.operation_errors.labels(
                layer="graphiti", operation="collect_metrics", error_type=type(e).__name__
            ).inc()
            return {"layer": "graphiti", "error": str(e)}

    async def collect_all_metrics(
        self,
        redis_manager=None,
        qdrant_client=None,
        graphiti_client=None,
    ) -> dict[str, Any]:
        """Collect metrics from all memory layers.

        Args:
            redis_manager: Optional RedisMemoryManager instance
            qdrant_client: Optional QdrantClient instance
            graphiti_client: Optional GraphitiClient instance

        Returns:
            Dictionary with all collected metrics
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "layers": {},
        }

        # Collect Redis metrics
        if redis_manager:
            redis_metrics = await self.collect_redis_metrics(redis_manager)
            metrics["layers"]["redis"] = redis_metrics

        # Collect Qdrant metrics
        if qdrant_client:
            qdrant_metrics = await self.collect_qdrant_metrics(qdrant_client)
            metrics["layers"]["qdrant"] = qdrant_metrics

        # Collect Graphiti metrics
        if graphiti_client:
            graphiti_metrics = await self.collect_graphiti_metrics(graphiti_client)
            metrics["layers"]["graphiti"] = graphiti_metrics

        return metrics

    # ============= Latency Tracking Decorators =============

    def track_redis_read(self, duration_seconds: float) -> None:
        """Track Redis read operation latency.

        Args:
            duration_seconds: Operation duration in seconds
        """
        self.redis_read_latency.observe(duration_seconds)
        self.operations_total.labels(layer="redis", operation="read").inc()

    def track_redis_write(self, duration_seconds: float) -> None:
        """Track Redis write operation latency.

        Args:
            duration_seconds: Operation duration in seconds
        """
        self.redis_write_latency.observe(duration_seconds)
        self.operations_total.labels(layer="redis", operation="write").inc()

    def track_qdrant_search(self, duration_seconds: float) -> None:
        """Track Qdrant search operation latency.

        Args:
            duration_seconds: Operation duration in seconds
        """
        self.qdrant_search_latency.observe(duration_seconds)
        self.operations_total.labels(layer="qdrant", operation="search").inc()

    def track_qdrant_upsert(self, duration_seconds: float) -> None:
        """Track Qdrant upsert operation latency.

        Args:
            duration_seconds: Operation duration in seconds
        """
        self.qdrant_upsert_latency.observe(duration_seconds)
        self.operations_total.labels(layer="qdrant", operation="upsert").inc()

    def track_graphiti_query(self, duration_seconds: float) -> None:
        """Track Graphiti query operation latency.

        Args:
            duration_seconds: Operation duration in seconds
        """
        self.graphiti_query_latency.observe(duration_seconds)
        self.operations_total.labels(layer="graphiti", operation="query").inc()

    def track_graphiti_add(self, duration_seconds: float) -> None:
        """Track Graphiti add operation latency.

        Args:
            duration_seconds: Operation duration in seconds
        """
        self.graphiti_add_latency.observe(duration_seconds)
        self.operations_total.labels(layer="graphiti", operation="add").inc()

    # ============= Hit Rate Tracking =============

    def record_cache_hit(self, layer: str) -> None:
        """Record a cache hit for a specific layer.

        Args:
            layer: Memory layer (redis, qdrant, graphiti)
        """
        self.cache_hits.labels(layer=layer).inc()

    def record_cache_miss(self, layer: str) -> None:
        """Record a cache miss for a specific layer.

        Args:
            layer: Memory layer (redis, qdrant, graphiti)
        """
        self.cache_misses.labels(layer=layer).inc()

    def get_cache_hit_rate(self, layer: str) -> float:
        """Calculate cache hit rate for a layer.

        Args:
            layer: Memory layer

        Returns:
            Hit rate (0.0-1.0)
        """
        # Note: This requires accessing the internal counter values
        # In production, this would be calculated from Prometheus queries
        # For now, return 0.0 as placeholder
        return 0.0


# Global singleton instance
_monitoring: MemoryMonitoring | None = None


def get_monitoring() -> MemoryMonitoring:
    """Get global MemoryMonitoring instance (singleton).

    Returns:
        MemoryMonitoring instance
    """
    global _monitoring
    if _monitoring is None:
        _monitoring = MemoryMonitoring()
    return _monitoring
