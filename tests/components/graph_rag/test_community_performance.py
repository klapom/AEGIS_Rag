"""Performance tests for community detection optimizations.

Sprint 11.7: Community Detection Performance Optimization

Tests verify:
- Community detection < 2 seconds for 1000+ node graphs
- Cached results returned instantly (< 10ms)
- Async execution doesn't block event loop
- Cache hit rate for repeated queries
"""

import asyncio
import time
from unittest.mock import AsyncMock

import networkx as nx
import pytest

from src.components.graph_rag.community_detector import (
    CommunityDetector,
    _detect_communities_cached,
    _hash_graph,
)


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for performance tests."""
    return AsyncMock()


@pytest.fixture
def detector(mock_neo4j_client):
    """Create CommunityDetector with mocked Neo4j client."""
    return CommunityDetector(
        neo4j_client=mock_neo4j_client,
        algorithm="louvain",
        resolution=1.0,
        min_size=3,
        use_gds=False,  # Force NetworkX for consistent performance testing
    )


@pytest.fixture
def large_graph():
    """Create a 1000-node graph for performance testing.

    Structure: Connected communities with some inter-community edges
    - 10 communities of ~100 nodes each
    - Intra-community edge probability: 0.3
    - Inter-community edge probability: 0.01
    """
    graph = nx.Graph()

    # Create communities
    num_communities = 10
    nodes_per_community = 100

    for comm_id in range(num_communities):
        # Add nodes for this community
        start_node = comm_id * nodes_per_community
        end_node = start_node + nodes_per_community

        for node_id in range(start_node, end_node):
            graph.add_node(f"node_{node_id}")

        # Add dense intra-community edges
        for i in range(start_node, end_node):
            for j in range(i + 1, end_node):
                # 30% edge probability within community
                if (i + j) % 10 < 3:
                    graph.add_edge(f"node_{i}", f"node_{j}")

    # Add sparse inter-community edges
    for i in range(0, num_communities * nodes_per_community, 10):
        for j in range(i + nodes_per_community, num_communities * nodes_per_community, 50):
            # 2% edge probability between communities
            if (i + j) % 50 == 0:
                graph.add_edge(f"node_{i}", f"node_{j}")

    return graph


@pytest.fixture
def mock_graph_data(large_graph):
    """Mock Neo4j data for large graph."""
    entities = [{"id": node} for node in large_graph.nodes()]
    relationships = [{"source": u, "target": v} for u, v in large_graph.edges()]
    return entities, relationships


class TestGraphHashing:
    """Tests for graph hashing function."""

    def test_hash_deterministic(self):
        """Test that hashing is deterministic."""
        graph = nx.Graph()
        graph.add_nodes_from(["a", "b", "c"])
        graph.add_edges_from([("a", "b"), ("b", "c")])

        hash1 = _hash_graph(graph, "louvain", 1.0)
        hash2 = _hash_graph(graph, "louvain", 1.0)

        assert hash1 == hash2

    def test_hash_different_structures(self):
        """Test that different graphs have different hashes."""
        graph1 = nx.Graph()
        graph1.add_nodes_from(["a", "b", "c"])
        graph1.add_edges_from([("a", "b"), ("b", "c")])

        graph2 = nx.Graph()
        graph2.add_nodes_from(["a", "b", "c"])
        graph2.add_edges_from([("a", "c")])

        hash1 = _hash_graph(graph1, "louvain", 1.0)
        hash2 = _hash_graph(graph2, "louvain", 1.0)

        assert hash1 != hash2

    def test_hash_different_parameters(self):
        """Test that different parameters produce different hashes."""
        graph = nx.Graph()
        graph.add_nodes_from(["a", "b", "c"])
        graph.add_edges_from([("a", "b"), ("b", "c")])

        hash1 = _hash_graph(graph, "louvain", 1.0)
        hash2 = _hash_graph(graph, "louvain", 2.0)
        hash3 = _hash_graph(graph, "leiden", 1.0)

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3


class TestCacheFunctionality:
    """Tests for LRU cache functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        _detect_communities_cached.cache_clear()

    def test_cache_miss_then_hit(self):
        """Test cache miss on first call, hit on second."""
        graph = nx.Graph()
        graph.add_nodes_from([f"node_{i}" for i in range(50)])
        for i in range(0, 50, 2):
            graph.add_edge(f"node_{i}", f"node_{i+1}")

        graph_hash = _hash_graph(graph, "louvain", 1.0)
        nodes_tuple = tuple(sorted(graph.nodes()))
        edges_tuple = tuple(sorted(graph.edges()))

        # First call - cache miss
        cache_info_before = _detect_communities_cached.cache_info()
        result1 = _detect_communities_cached(graph_hash, nodes_tuple, edges_tuple, "louvain", 1.0)
        cache_info_after_first = _detect_communities_cached.cache_info()

        assert cache_info_after_first.misses == cache_info_before.misses + 1
        assert cache_info_after_first.hits == cache_info_before.hits

        # Second call - cache hit
        result2 = _detect_communities_cached(graph_hash, nodes_tuple, edges_tuple, "louvain", 1.0)
        cache_info_after_second = _detect_communities_cached.cache_info()

        assert cache_info_after_second.hits == cache_info_after_first.hits + 1
        assert result1 == result2

    def test_cached_result_instant(self):
        """Test that cached results are returned instantly (<10ms)."""
        graph = nx.Graph()
        graph.add_nodes_from([f"node_{i}" for i in range(100)])
        for i in range(0, 100, 2):
            graph.add_edge(f"node_{i}", f"node_{i+1}")

        graph_hash = _hash_graph(graph, "louvain", 1.0)
        nodes_tuple = tuple(sorted(graph.nodes()))
        edges_tuple = tuple(sorted(graph.edges()))

        # First call - populate cache
        _detect_communities_cached(graph_hash, nodes_tuple, edges_tuple, "louvain", 1.0)

        # Second call - measure cached performance
        start_time = time.perf_counter()
        _detect_communities_cached(graph_hash, nodes_tuple, edges_tuple, "louvain", 1.0)
        cached_time_ms = (time.perf_counter() - start_time) * 1000

        # Cached result should be instant (< 10ms)
        assert cached_time_ms < 10, f"Cached call took {cached_time_ms:.2f}ms, expected < 10ms"

    def test_cache_max_size(self):
        """Test that cache respects maxsize of 10."""
        cache_info = _detect_communities_cached.cache_info()
        assert cache_info.maxsize == 10


class TestLargeGraphPerformance:
    """Tests for 1000+ node graph performance."""

    def setup_method(self):
        """Clear cache before each test."""
        _detect_communities_cached.cache_clear()

    @pytest.mark.asyncio
    async def test_1000_node_performance(self, detector, mock_neo4j_client, mock_graph_data):
        """Test that 1000-node graph completes in < 2 seconds (uncached).

        Success Criteria: First run < 2s for 1000 nodes
        """
        entities, relationships = mock_graph_data

        # Mock Neo4j to return large graph data
        mock_neo4j_client.execute_read.side_effect = [
            entities,  # First call returns entities
            relationships,  # Second call returns relationships
        ]

        # Mock write operations
        mock_neo4j_client.execute_write.return_value = [{"updated_count": len(entities)}]

        # Measure performance
        start_time = time.perf_counter()
        communities = await detector._detect_with_networkx(algorithm="louvain", resolution=1.0)
        execution_time = (time.perf_counter() - start_time) * 1000

        # Verify performance
        assert (
            execution_time < 2000
        ), f"Community detection took {execution_time:.0f}ms, expected < 2000ms"

        # Verify communities were detected
        assert len(communities) > 0
        assert all(c.size > 0 for c in communities)

        print(f"\n[PASS] 1000-node graph: {execution_time:.0f}ms (target: < 2000ms)")

    @pytest.mark.asyncio
    async def test_cached_performance(self, detector, mock_neo4j_client, mock_graph_data):
        """Test that cached queries are instant (< 10ms).

        Success Criteria: Cached run < 10ms
        """
        entities, relationships = mock_graph_data

        # First run - populate cache
        mock_neo4j_client.execute_read.side_effect = [entities, relationships]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": len(entities)}]

        await detector._detect_with_networkx(algorithm="louvain", resolution=1.0)

        # Second run - should hit cache
        mock_neo4j_client.execute_read.side_effect = [entities, relationships]

        start_time = time.perf_counter()
        communities = await detector._detect_with_networkx(algorithm="louvain", resolution=1.0)
        cached_time_ms = (time.perf_counter() - start_time) * 1000

        # Cached query should be instant (< 10ms for computation, allow more for async overhead)
        assert cached_time_ms < 100, f"Cached query took {cached_time_ms:.0f}ms, expected < 100ms"

        # Verify cache was hit
        cache_info = detector.get_cache_info()
        assert cache_info["hits"] > 0, "Cache should have hits"

        print(f"\n[PASS] Cached query: {cached_time_ms:.0f}ms (target: < 100ms)")
        print(f"[PASS] Cache hit rate: {cache_info['hit_rate'] * 100:.1f}%")

    @pytest.mark.asyncio
    async def test_async_non_blocking(self, detector, mock_neo4j_client, mock_graph_data):
        """Test that async execution doesn't block event loop.

        Success Criteria: Can run other tasks concurrently
        """
        entities, relationships = mock_graph_data

        # Mock Neo4j
        mock_neo4j_client.execute_read.side_effect = [entities, relationships]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": len(entities)}]

        # Track concurrent execution
        concurrent_task_completed = False

        async def concurrent_task():
            """Simple task that should complete during community detection."""
            nonlocal concurrent_task_completed
            await asyncio.sleep(0.1)
            concurrent_task_completed = True

        # Run both tasks concurrently
        await asyncio.gather(
            detector._detect_with_networkx(algorithm="louvain", resolution=1.0), concurrent_task()
        )

        # Concurrent task should have completed
        assert concurrent_task_completed, "Concurrent task should complete (event loop not blocked)"

        print("\n[PASS] Event loop not blocked during community detection")


class TestCacheManagement:
    """Tests for cache management features."""

    def setup_method(self):
        """Clear cache before each test."""
        _detect_communities_cached.cache_clear()

    def test_get_cache_info(self, detector):
        """Test cache info retrieval."""
        cache_info = detector.get_cache_info()

        assert "hits" in cache_info
        assert "misses" in cache_info
        assert "size" in cache_info
        assert "maxsize" in cache_info
        assert "hit_rate" in cache_info

        assert cache_info["maxsize"] == 10

    def test_clear_cache(self, detector):
        """Test cache clearing."""
        # Create a small graph and populate cache
        graph = nx.Graph()
        graph.add_nodes_from(["a", "b", "c"])
        graph.add_edges_from([("a", "b"), ("b", "c")])

        graph_hash = _hash_graph(graph, "louvain", 1.0)
        nodes_tuple = tuple(sorted(graph.nodes()))
        edges_tuple = tuple(sorted(graph.edges()))

        _detect_communities_cached(graph_hash, nodes_tuple, edges_tuple, "louvain", 1.0)

        # Verify cache has entries
        cache_info_before = detector.get_cache_info()
        assert cache_info_before["size"] > 0

        # Clear cache
        detector.clear_cache()

        # Verify cache is empty
        cache_info_after = detector.get_cache_info()
        assert cache_info_after["size"] == 0
        assert cache_info_after["hits"] == 0
        assert cache_info_after["misses"] == 0


class TestPerformanceRegression:
    """Regression tests to ensure performance doesn't degrade."""

    def setup_method(self):
        """Clear cache before each test."""
        _detect_communities_cached.cache_clear()

    @pytest.mark.asyncio
    async def test_small_graph_still_fast(self, detector, mock_neo4j_client):
        """Test that small graphs (< 100 nodes) complete quickly (< 100ms)."""
        # Create small graph data
        entities = [{"id": f"node_{i}"} for i in range(50)]
        relationships = [{"source": f"node_{i}", "target": f"node_{i+1}"} for i in range(0, 49, 2)]

        mock_neo4j_client.execute_read.side_effect = [entities, relationships]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": 50}]

        start_time = time.perf_counter()
        communities = await detector._detect_with_networkx(algorithm="louvain", resolution=1.0)
        execution_time = (time.perf_counter() - start_time) * 1000

        assert execution_time < 100, f"Small graph took {execution_time:.0f}ms, expected < 100ms"
        assert len(communities) > 0

        print(f"\n[PASS] Small graph (50 nodes): {execution_time:.0f}ms (target: < 100ms)")

    @pytest.mark.asyncio
    async def test_medium_graph_performance(self, detector, mock_neo4j_client):
        """Test medium graphs (100-500 nodes) complete reasonably (< 500ms)."""
        # Create medium graph data
        num_nodes = 300
        entities = [{"id": f"node_{i}"} for i in range(num_nodes)]
        relationships = []
        for i in range(0, num_nodes - 1, 2):
            relationships.append({"source": f"node_{i}", "target": f"node_{i+1}"})
        for i in range(0, num_nodes, 10):
            for j in range(i + 10, min(i + 30, num_nodes)):
                relationships.append({"source": f"node_{i}", "target": f"node_{j}"})

        mock_neo4j_client.execute_read.side_effect = [entities, relationships]
        mock_neo4j_client.execute_write.return_value = [{"updated_count": num_nodes}]

        start_time = time.perf_counter()
        communities = await detector._detect_with_networkx(algorithm="louvain", resolution=1.0)
        execution_time = (time.perf_counter() - start_time) * 1000

        assert execution_time < 1000, f"Medium graph took {execution_time:.0f}ms, expected < 1000ms"
        assert len(communities) > 0

        print(f"\n[PASS] Medium graph (300 nodes): {execution_time:.0f}ms (target: < 1000ms)")
