"""Integration tests for Sprint 69 Feature 69.7: Production Monitoring & Observability.

Tests verify:
1. Prometheus metrics are properly instrumented
2. Metrics are exported correctly
3. Helper functions work as expected
4. Metrics integration with query processing
"""

import pytest
from prometheus_client import REGISTRY

from src.core.metrics import (
    cache_hits_total,
    cache_misses_total,
    error_total,
    memory_facts_count,
    query_latency_seconds,
    query_total,
    track_cache_hit,
    track_cache_miss,
    track_error,
    track_query,
    update_memory_facts,
)


class TestSpring69Metrics:
    """Test Sprint 69 metrics instrumentation."""

    def test_query_total_metric_exists(self):
        """Test that query_total metric is registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        # Prometheus client removes _total suffix from Counter metric names
        assert "aegis_queries" in metric_names

    def test_query_latency_metric_exists(self):
        """Test that query_latency_seconds metric is registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        assert "aegis_query_latency_seconds" in metric_names

    def test_cache_metrics_exist(self):
        """Test that cache hit/miss metrics are registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        # Prometheus client removes _total suffix from Counter metric names
        assert "aegis_cache_hits" in metric_names
        assert "aegis_cache_misses" in metric_names

    def test_memory_facts_metric_exists(self):
        """Test that memory_facts_count metric is registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        assert "aegis_memory_facts_count" in metric_names

    def test_error_metric_exists(self):
        """Test that error_total metric is registered."""
        metric_names = [m.name for m in REGISTRY.collect()]
        # Prometheus client removes _total suffix from Counter metric names
        assert "aegis_errors" in metric_names

    def test_track_query_increments_counter(self):
        """Test that track_query() increments the query counter."""
        # Get initial value
        initial_value = query_total.labels(
            intent="hybrid", model="nemotron-no-think:latest"
        )._value.get()

        # Track a query
        track_query(
            intent="hybrid",
            model="nemotron-no-think:latest",
            stage_latencies={
                "intent_classification": 0.05,
                "retrieval": 0.3,
                "generation": 0.8,
                "total": 1.15,
            },
        )

        # Verify counter incremented
        final_value = query_total.labels(
            intent="hybrid", model="nemotron-no-think:latest"
        )._value.get()
        assert final_value == initial_value + 1

    def test_track_query_records_latencies(self):
        """Test that track_query() records latencies for all stages."""
        # Track a query with multiple stages
        track_query(
            intent="vector_search",
            model="gpt-oss:20b",
            stage_latencies={
                "intent_classification": 0.05,
                "retrieval": 0.3,
                "generation": 0.8,
                "total": 1.15,
            },
        )

        # Verify histogram observations (check sum > 0)
        for stage in ["intent_classification", "retrieval", "generation", "total"]:
            histogram = query_latency_seconds.labels(stage=stage)
            # The _sum attribute tracks cumulative observed values
            assert histogram._sum.get() > 0

    def test_track_cache_hit(self):
        """Test that track_cache_hit() increments cache hit counter."""
        initial_value = cache_hits_total.labels(cache_type="redis")._value.get()

        track_cache_hit("redis")

        final_value = cache_hits_total.labels(cache_type="redis")._value.get()
        assert final_value == initial_value + 1

    def test_track_cache_miss(self):
        """Test that track_cache_miss() increments cache miss counter."""
        initial_value = cache_misses_total.labels(cache_type="embedding")._value.get()

        track_cache_miss("embedding")

        final_value = cache_misses_total.labels(cache_type="embedding")._value.get()
        assert final_value == initial_value + 1

    def test_update_memory_facts(self):
        """Test that update_memory_facts() sets gauge value."""
        update_memory_facts("episodic", 1234)

        value = memory_facts_count.labels(fact_type="episodic")._value.get()
        assert value == 1234

    def test_track_error(self):
        """Test that track_error() increments error counter."""
        initial_value = error_total.labels(error_type="timeout")._value.get()

        track_error("timeout")

        final_value = error_total.labels(error_type="timeout")._value.get()
        assert final_value == initial_value + 1

    def test_multiple_intents_tracked_separately(self):
        """Test that different intents are tracked separately."""
        # Track queries with different intents
        track_query(
            intent="vector_search",
            model="nemotron-no-think:latest",
            stage_latencies={"total": 0.5},
        )
        track_query(
            intent="graph_reasoning",
            model="nemotron-no-think:latest",
            stage_latencies={"total": 0.8},
        )

        # Verify separate counters
        vector_count = query_total.labels(
            intent="vector_search", model="nemotron-no-think:latest"
        )._value.get()
        graph_count = query_total.labels(
            intent="graph_reasoning", model="nemotron-no-think:latest"
        )._value.get()

        assert vector_count >= 1
        assert graph_count >= 1

    def test_cache_hit_rate_calculation(self):
        """Test that cache hit rate can be calculated from metrics."""
        # Record some cache operations
        for _ in range(7):
            track_cache_hit("llm_config")
        for _ in range(3):
            track_cache_miss("llm_config")

        hits = cache_hits_total.labels(cache_type="llm_config")._value.get()
        misses = cache_misses_total.labels(cache_type="llm_config")._value.get()

        # Calculate hit rate
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0

        # Should be 70% hit rate
        assert hit_rate >= 0.65  # Allow some tolerance for test setup

    def test_stage_latency_breakdown(self):
        """Test that stage latencies can be broken down for analysis."""
        # Track query with detailed stage latencies
        stage_latencies = {
            "intent_classification": 0.05,
            "retrieval": 0.3,
            "generation": 0.8,
            "total": 1.15,
        }

        track_query(
            intent="hybrid", model="nemotron-no-think:latest", stage_latencies=stage_latencies
        )

        # Verify each stage was recorded
        for stage, expected_latency in stage_latencies.items():
            histogram = query_latency_seconds.labels(stage=stage)
            # Sum should include our observation
            assert histogram._sum.get() >= expected_latency

    @pytest.mark.parametrize(
        "error_type",
        ["llm_error", "database_error", "timeout", "validation_error"],
    )
    def test_error_types_tracked_separately(self, error_type):
        """Test that different error types are tracked separately."""
        initial_value = error_total.labels(error_type=error_type)._value.get()

        track_error(error_type)

        final_value = error_total.labels(error_type=error_type)._value.get()
        assert final_value == initial_value + 1

    def test_memory_fact_types_tracked_separately(self):
        """Test that different memory fact types are tracked separately."""
        update_memory_facts("episodic", 100)
        update_memory_facts("semantic", 200)
        update_memory_facts("entity", 300)

        episodic = memory_facts_count.labels(fact_type="episodic")._value.get()
        semantic = memory_facts_count.labels(fact_type="semantic")._value.get()
        entity = memory_facts_count.labels(fact_type="entity")._value.get()

        assert episodic == 100
        assert semantic == 200
        assert entity == 300


class TestMetricsIntegration:
    """Test metrics integration scenarios."""

    def test_query_lifecycle_metrics(self):
        """Test full query lifecycle metrics tracking."""
        # Simulate a complete query processing lifecycle

        # 1. Track query with all stages
        track_query(
            intent="hybrid",
            model="nemotron-no-think:latest",
            stage_latencies={
                "intent_classification": 0.05,
                "retrieval": 0.35,
                "generation": 0.9,
                "total": 1.3,
            },
        )

        # 2. Track cache operations during retrieval
        track_cache_hit("redis")  # Query cache hit
        track_cache_miss("embedding")  # Embedding not cached

        # 3. Update memory facts after query
        update_memory_facts("episodic", 1235)

        # Verify all metrics updated
        query_count = query_total.labels(
            intent="hybrid", model="nemotron-no-think:latest"
        )._value.get()
        assert query_count >= 1

        cache_hits = cache_hits_total.labels(cache_type="redis")._value.get()
        assert cache_hits >= 1

        memory_facts = memory_facts_count.labels(fact_type="episodic")._value.get()
        assert memory_facts == 1235

    def test_error_scenario_metrics(self):
        """Test metrics tracking during error scenarios."""
        # Simulate an error during query processing
        try:
            # Attempt to track query
            track_query(
                intent="vector_search",
                model="gpt-oss:20b",
                stage_latencies={"intent_classification": 0.05, "retrieval": 0.2},
            )

            # Simulate error during generation
            raise TimeoutError("LLM generation timeout")

        except TimeoutError:
            # Track the error
            track_error("timeout")

        # Verify error was tracked
        errors = error_total.labels(error_type="timeout")._value.get()
        assert errors >= 1

    def test_high_load_metrics(self):
        """Test metrics under high load simulation."""
        # Simulate 100 queries
        for i in range(100):
            intent = "hybrid" if i % 2 == 0 else "vector_search"
            track_query(
                intent=intent,
                model="nemotron-no-think:latest",
                stage_latencies={"total": 0.5 + (i % 10) * 0.1},
            )

            # Simulate cache behavior
            if i % 3 == 0:
                track_cache_hit("redis")
            else:
                track_cache_miss("redis")

        # Verify metrics accumulated correctly
        total_queries = (
            query_total.labels(intent="hybrid", model="nemotron-no-think:latest")._value.get()
            + query_total.labels(
                intent="vector_search", model="nemotron-no-think:latest"
            )._value.get()
        )
        assert total_queries >= 100

        # Verify cache metrics
        cache_hits = cache_hits_total.labels(cache_type="redis")._value.get()
        cache_misses = cache_misses_total.labels(cache_type="redis")._value.get()
        assert cache_hits > 0
        assert cache_misses > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
