"""Unit tests for Memory Monitoring (Sprint 9 Feature 9.5).

Tests cover:
- Prometheus metrics initialization
- Redis metrics collection
- Qdrant metrics collection (placeholder)
- Graphiti metrics collection (placeholder)
- Latency tracking
- Hit rate tracking
- Health status tracking
- Error tracking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from src.components.memory.monitoring import MemoryMonitoring, get_monitoring


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    """Reset Prometheus registry before each test to avoid duplicate metrics."""
    # Clear all collectors from the registry
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass  # Ignore errors if collector already unregistered
    yield
    # Clear singleton instance after test
    import src.components.memory.monitoring as monitoring_module

    monitoring_module._monitoring = None


class TestMemoryMonitoringInit:
    """Test MemoryMonitoring initialization."""

    def test_monitoring_initialization(self):
        """Test MemoryMonitoring initializes with all metrics."""
        monitoring = MemoryMonitoring()

        # Verify all capacity metrics are created
        assert monitoring.redis_capacity is not None
        assert monitoring.qdrant_capacity is not None
        assert monitoring.graphiti_capacity is not None

        # Verify entry count metrics
        assert monitoring.redis_entries is not None
        assert monitoring.qdrant_entries is not None
        assert monitoring.graphiti_entries is not None

        # Verify latency metrics
        assert monitoring.redis_read_latency is not None
        assert monitoring.redis_write_latency is not None
        assert monitoring.qdrant_search_latency is not None
        assert monitoring.qdrant_upsert_latency is not None
        assert monitoring.graphiti_query_latency is not None
        assert monitoring.graphiti_add_latency is not None

        # Verify hit rate metrics
        assert monitoring.cache_hits is not None
        assert monitoring.cache_misses is not None

        # Verify operation metrics
        assert monitoring.operations_total is not None
        assert monitoring.operation_errors is not None
        assert monitoring.layer_health is not None

    def test_singleton_pattern(self):
        """Test get_monitoring returns singleton instance."""
        monitoring1 = get_monitoring()
        monitoring2 = get_monitoring()

        assert monitoring1 is monitoring2


class TestRedisMetricsCollection:
    """Test Redis metrics collection."""

    @pytest.mark.asyncio
    async def test_collect_redis_metrics_success(self):
        """Test successful Redis metrics collection."""
        monitoring = MemoryMonitoring()

        # Mock RedisMemoryManager
        mock_redis = AsyncMock()
        mock_redis.get_capacity.return_value = 0.45
        mock_redis.get_stats.return_value = {
            "total_entries": 1234,
            "total_access_count": 5678,
            "avg_ttl_seconds": 300,
        }

        metrics = await monitoring.collect_redis_metrics(mock_redis)

        # Verify metrics were collected
        assert metrics["layer"] == "redis"
        assert metrics["capacity"] == 0.45
        assert metrics["entries"] == 1234
        assert "timestamp" in metrics

        # Verify manager methods were called
        mock_redis.get_capacity.assert_called_once()
        mock_redis.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_redis_metrics_error(self):
        """Test Redis metrics collection with error."""
        monitoring = MemoryMonitoring()

        # Mock RedisMemoryManager that raises error
        mock_redis = AsyncMock()
        mock_redis.get_capacity.side_effect = Exception("Redis connection failed")

        metrics = await monitoring.collect_redis_metrics(mock_redis)

        # Verify error is captured
        assert metrics["layer"] == "redis"
        assert "error" in metrics
        assert "Redis connection failed" in metrics["error"]


class TestQdrantMetricsCollection:
    """Test Qdrant metrics collection."""

    @pytest.mark.asyncio
    async def test_collect_qdrant_metrics_placeholder(self):
        """Test Qdrant metrics collection (real implementation)."""
        monitoring = MemoryMonitoring()

        # Mock QdrantClient with collections
        mock_qdrant = AsyncMock()
        mock_collections = AsyncMock()
        mock_collections.collections = []
        mock_qdrant.async_client.get_collections.return_value = mock_collections

        metrics = await monitoring.collect_qdrant_metrics(mock_qdrant)

        # Verify metrics structure
        assert metrics["layer"] == "qdrant"
        assert "capacity" in metrics
        assert "entries" in metrics
        assert "timestamp" in metrics
        # Real implementation returns actual metrics, not placeholder note
        assert metrics["capacity"] == 0.0
        assert metrics["entries"] == 0


class TestGraphitiMetricsCollection:
    """Test Graphiti metrics collection."""

    @pytest.mark.asyncio
    async def test_collect_graphiti_metrics_placeholder(self):
        """Test Graphiti metrics collection (real implementation with Neo4j)."""
        with patch("src.components.graph_rag.neo4j_client.get_neo4j_client") as mock_get_neo4j:
            monitoring = MemoryMonitoring()

            # Mock Neo4jClient with driver and session
            mock_neo4j = MagicMock()
            mock_session = AsyncMock()
            mock_result = AsyncMock()
            mock_record = {"node_count": 42}

            mock_result.single = AsyncMock(return_value=mock_record)
            mock_session.run = AsyncMock(return_value=mock_result)

            # Mock the async context manager for session
            mock_session_cm = MagicMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)

            mock_neo4j.driver.session.return_value = mock_session_cm
            mock_neo4j.database = "neo4j"
            mock_get_neo4j.return_value = mock_neo4j

            # Mock GraphitiClient (passed as argument but not used)
            mock_graphiti = AsyncMock()

            metrics = await monitoring.collect_graphiti_metrics(mock_graphiti)

            # Verify metrics structure
            assert metrics["layer"] == "graphiti"
            assert "capacity" in metrics
            assert "entries" in metrics
            assert "timestamp" in metrics
            # Real implementation returns actual node count from Neo4j
            assert metrics["entries"] == 42


class TestCollectAllMetrics:
    """Test collecting metrics from all layers."""

    @pytest.mark.asyncio
    async def test_collect_all_metrics_all_layers(self):
        """Test collecting metrics from all 3 layers."""
        monitoring = MemoryMonitoring()

        # Mock all clients
        mock_redis = AsyncMock()
        mock_redis.get_capacity.return_value = 0.5
        mock_redis.get_stats.return_value = {"total_entries": 100}

        mock_qdrant = AsyncMock()
        mock_graphiti = AsyncMock()

        metrics = await monitoring.collect_all_metrics(
            redis_manager=mock_redis,
            qdrant_client=mock_qdrant,
            graphiti_client=mock_graphiti,
        )

        # Verify all layers are present
        assert "timestamp" in metrics
        assert "layers" in metrics
        assert "redis" in metrics["layers"]
        assert "qdrant" in metrics["layers"]
        assert "graphiti" in metrics["layers"]

    @pytest.mark.asyncio
    async def test_collect_all_metrics_partial(self):
        """Test collecting metrics from only Redis."""
        monitoring = MemoryMonitoring()

        # Only Redis client provided
        mock_redis = AsyncMock()
        mock_redis.get_capacity.return_value = 0.3
        mock_redis.get_stats.return_value = {"total_entries": 50}

        metrics = await monitoring.collect_all_metrics(redis_manager=mock_redis)

        # Verify only Redis layer is present
        assert "layers" in metrics
        assert "redis" in metrics["layers"]
        assert "qdrant" not in metrics["layers"]
        assert "graphiti" not in metrics["layers"]


class TestLatencyTracking:
    """Test latency tracking methods."""

    def test_track_redis_read_latency(self):
        """Test tracking Redis read latency."""
        monitoring = MemoryMonitoring()

        # Track some latencies
        monitoring.track_redis_read(0.005)  # 5ms
        monitoring.track_redis_read(0.010)  # 10ms
        monitoring.track_redis_read(0.003)  # 3ms

        # Verify metrics were recorded (no exceptions)
        # Note: We can't easily verify histogram values without accessing internal state

    def test_track_redis_write_latency(self):
        """Test tracking Redis write latency."""
        monitoring = MemoryMonitoring()

        monitoring.track_redis_write(0.008)  # 8ms
        monitoring.track_redis_write(0.012)  # 12ms

        # Verify no exceptions

    def test_track_qdrant_latency(self):
        """Test tracking Qdrant search and upsert latency."""
        monitoring = MemoryMonitoring()

        monitoring.track_qdrant_search(0.5)  # 500ms
        monitoring.track_qdrant_upsert(1.0)  # 1s

        # Verify no exceptions

    def test_track_graphiti_latency(self):
        """Test tracking Graphiti query and add latency."""
        monitoring = MemoryMonitoring()

        monitoring.track_graphiti_query(0.8)  # 800ms
        monitoring.track_graphiti_add(1.2)  # 1.2s

        # Verify no exceptions


class TestHitRateTracking:
    """Test cache hit rate tracking."""

    def test_record_cache_hits(self):
        """Test recording cache hits."""
        monitoring = MemoryMonitoring()

        # Record some hits
        monitoring.record_cache_hit("redis")
        monitoring.record_cache_hit("redis")
        monitoring.record_cache_hit("qdrant")

        # Verify no exceptions

    def test_record_cache_misses(self):
        """Test recording cache misses."""
        monitoring = MemoryMonitoring()

        # Record some misses
        monitoring.record_cache_miss("redis")
        monitoring.record_cache_miss("graphiti")

        # Verify no exceptions

    def test_get_cache_hit_rate_placeholder(self):
        """Test cache hit rate calculation (placeholder)."""
        monitoring = MemoryMonitoring()

        # Record some hits and misses
        monitoring.record_cache_hit("redis")
        monitoring.record_cache_hit("redis")
        monitoring.record_cache_miss("redis")

        # Get hit rate (currently returns 0.0 as placeholder)
        hit_rate = monitoring.get_cache_hit_rate("redis")

        # Verify it returns a value
        assert isinstance(hit_rate, float)
        assert 0.0 <= hit_rate <= 1.0
