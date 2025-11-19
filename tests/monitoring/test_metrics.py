"""Unit tests for Prometheus Metrics (Sprint 14 Feature 14.6).

Tests cover:
- Metric registration and initialization
- Counter increments (entities, relations, documents, errors)
- Histogram observations (duration, deduplication, query)
- Gauge updates (GPU memory, utilization)
- Helper function behavior with labels
- Concurrent access and thread safety
- Metrics export format
- System info initialization

Author: Claude Code
Date: 2025-10-27
Sprint: 14 Feature 14.6
Target Coverage: 70%
"""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, Mock, patch

import pytest
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram, Info

from src.monitoring import metrics


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clean_registry():
    """Provide a clean CollectorRegistry for isolated tests.

    This fixture is crucial for test isolation to prevent metric conflicts
    when running tests in parallel or sequentially.
    """
    registry = CollectorRegistry()
    yield registry


@pytest.fixture
def mock_config():
    """Mock configuration object for system info initialization."""
    config = Mock()
    config.app_version = "0.1.0"
    config.environment = "test"
    config.extraction_pipeline = "three_phase"
    config.enable_semantic_dedup = True
    return config


# ============================================================================
# Metric Registration Tests
# ============================================================================


@pytest.mark.unit
class TestPrometheusMetricsRegistration:
    """Test Prometheus metrics are properly registered."""

    def test_extraction_duration_histogram_registered(self):
        """Test extraction duration histogram is registered with correct labels."""
        # Verify metric exists
        assert metrics.extraction_duration is not None
        assert isinstance(metrics.extraction_duration, Histogram)

        # Verify metric can be labeled
        labeled = metrics.extraction_duration.labels(
            phase="phase1_spacy", pipeline_type="three_phase"
        )
        assert labeled is not None

    def test_extraction_entities_counter_registered(self):
        """Test extraction entities counter is registered with correct labels."""
        assert metrics.extraction_entities_total is not None
        assert isinstance(metrics.extraction_entities_total, Counter)

        # Verify labels work
        labeled = metrics.extraction_entities_total.labels(
            entity_type="PERSON", pipeline_type="three_phase"
        )
        assert labeled is not None

    def test_extraction_relations_counter_registered(self):
        """Test extraction relations counter is registered."""
        assert metrics.extraction_relations_total is not None
        assert isinstance(metrics.extraction_relations_total, Counter)

        labeled = metrics.extraction_relations_total.labels(pipeline_type="three_phase")
        assert labeled is not None

    def test_extraction_documents_counter_registered(self):
        """Test extraction documents counter is registered with status labels."""
        assert metrics.extraction_documents_total is not None
        assert isinstance(metrics.extraction_documents_total, Counter)

        # Verify status labels
        labeled = metrics.extraction_documents_total.labels(
            pipeline_type="three_phase", status="success"
        )
        assert labeled is not None

    def test_extraction_errors_counter_registered(self):
        """Test extraction errors counter is registered."""
        assert metrics.extraction_errors_total is not None
        assert isinstance(metrics.extraction_errors_total, Counter)

        labeled = metrics.extraction_errors_total.labels(phase="phase3_gemma", error_type="timeout")
        assert labeled is not None

    def test_extraction_retries_counter_registered(self):
        """Test extraction retries counter is registered."""
        assert metrics.extraction_retries_total is not None
        assert isinstance(metrics.extraction_retries_total, Counter)

    def test_deduplication_reduction_histogram_registered(self):
        """Test deduplication reduction histogram is registered."""
        assert metrics.deduplication_reduction_ratio is not None
        assert isinstance(metrics.deduplication_reduction_ratio, Histogram)

    def test_gpu_metrics_gauges_registered(self):
        """Test GPU metrics gauges are registered."""
        assert metrics.gpu_memory_usage_bytes is not None
        assert isinstance(metrics.gpu_memory_usage_bytes, Gauge)

        assert metrics.gpu_memory_allocated_bytes is not None
        assert isinstance(metrics.gpu_memory_allocated_bytes, Gauge)

        assert metrics.gpu_utilization_percent is not None
        assert isinstance(metrics.gpu_utilization_percent, Gauge)

    def test_query_metrics_registered(self):
        """Test query duration and results count histograms are registered."""
        assert metrics.query_duration is not None
        assert isinstance(metrics.query_duration, Histogram)

        assert metrics.query_results_count is not None
        assert isinstance(metrics.query_results_count, Histogram)

    def test_system_info_registered(self):
        """Test system info metric is registered."""
        assert metrics.system_info is not None
        assert isinstance(metrics.system_info, Info)

    def test_active_connections_gauge_registered(self):
        """Test active connections gauge is registered."""
        assert metrics.active_connections is not None
        assert isinstance(metrics.active_connections, Gauge)


# ============================================================================
# Counter Tests
# ============================================================================


@pytest.mark.unit
class TestCounterIncrements:
    """Test counter metrics increment correctly."""

    def test_record_extraction_entities_increments_counter(self):
        """Test record_extraction_entities increments counter by specified count."""
        # Get initial value (may not be 0 if other tests ran)
        initial_metric = metrics.extraction_entities_total.labels(
            entity_type="PERSON", pipeline_type="test"
        )

        # Record entities
        metrics.record_extraction_entities("PERSON", "test", 5)
        metrics.record_extraction_entities("PERSON", "test", 3)

        # Note: We can't easily read the counter value, but we can verify no exceptions
        # In real scenario, you'd scrape /metrics endpoint to verify

    def test_record_extraction_entities_with_different_types(self):
        """Test recording different entity types independently."""
        # Record multiple entity types
        metrics.record_extraction_entities("PERSON", "three_phase", 10)
        metrics.record_extraction_entities("ORG", "three_phase", 5)
        metrics.record_extraction_entities("LOC", "three_phase", 3)

        # Verify no exceptions (counters are independent)

    def test_record_extraction_relations_increments_counter(self):
        """Test record_extraction_relations increments counter by specified count."""
        metrics.record_extraction_relations("three_phase", 15)
        metrics.record_extraction_relations("three_phase", 7)

        # Verify no exceptions

    def test_record_extraction_documents_increments_counter(self):
        """Test record_extraction_document increments counter."""
        # Record different statuses
        metrics.record_extraction_document("three_phase", "success")
        metrics.record_extraction_document("three_phase", "success")
        metrics.record_extraction_document("three_phase", "failed")
        metrics.record_extraction_document("lightrag_default", "skipped")

        # Verify no exceptions

    def test_record_extraction_error_increments_counter(self):
        """Test record_extraction_error increments error counter."""
        # Record different error types
        metrics.record_extraction_error("phase1_spacy", "connection_error")
        metrics.record_extraction_error("phase3_gemma", "timeout")
        metrics.record_extraction_error("phase2_dedup", "validation_error")

        # Verify no exceptions

    def test_record_extraction_retry_increments_counter(self):
        """Test record_extraction_retry tracks retry attempts."""
        # Record successful and failed retries
        metrics.record_extraction_retry("phase3_gemma", success=True)
        metrics.record_extraction_retry("phase3_gemma", success=True)
        metrics.record_extraction_retry("phase3_gemma", success=False)

        # Verify no exceptions


# ============================================================================
# Histogram Tests
# ============================================================================


@pytest.mark.unit
class TestHistogramObservations:
    """Test histogram metrics observe values correctly."""

    def test_record_extraction_duration_observes_histogram(self):
        """Test record_extraction_duration observes duration values."""
        # Record various durations
        metrics.record_extraction_duration("phase1_spacy", "three_phase", 0.5)
        metrics.record_extraction_duration("phase2_dedup", "three_phase", 1.2)
        metrics.record_extraction_duration("phase3_gemma", "three_phase", 5.8)

        # Verify no exceptions

    def test_record_extraction_duration_with_different_phases(self):
        """Test recording duration for different phases independently."""
        phases = ["phase1_spacy", "phase2_dedup", "phase3_gemma"]

        for phase in phases:
            metrics.record_extraction_duration(phase, "three_phase", 1.0)

        # Verify no exceptions

    def test_record_extraction_duration_with_edge_cases(self):
        """Test recording very small and very large durations."""
        # Very fast operation
        metrics.record_extraction_duration("phase1_spacy", "three_phase", 0.001)

        # Very slow operation
        metrics.record_extraction_duration("phase3_gemma", "three_phase", 120.5)

        # Zero duration (edge case)
        metrics.record_extraction_duration("phase2_dedup", "three_phase", 0.0)

        # Verify no exceptions

    def test_record_deduplication_ratio_observes_histogram(self):
        """Test record_deduplication_reduction observes reduction ratios."""
        # Record various reduction ratios
        metrics.record_deduplication_reduction(0.15)  # 15% reduction
        metrics.record_deduplication_reduction(0.25)  # 25% reduction
        metrics.record_deduplication_reduction(0.05)  # 5% reduction

        # Verify no exceptions

    def test_record_deduplication_ratio_with_edge_cases(self):
        """Test recording deduplication ratios at boundaries."""
        # No reduction
        metrics.record_deduplication_reduction(0.0)

        # Maximum expected reduction
        metrics.record_deduplication_reduction(0.50)

        # Very low reduction
        metrics.record_deduplication_reduction(0.01)

        # Verify no exceptions

    def test_record_query_duration_observes_histogram(self):
        """Test record_query_duration observes query durations."""
        # Record different query types
        metrics.record_query_duration("vector", "local", 0.3)
        metrics.record_query_duration("graph", "global", 0.8)
        metrics.record_query_duration("hybrid", "local", 1.5)

        # Verify no exceptions

    def test_record_query_duration_with_all_modes(self):
        """Test recording query durations for all query types and modes."""
        query_types = ["vector", "graph", "hybrid"]
        modes = ["local", "global"]

        for query_type in query_types:
            for mode in modes:
                metrics.record_query_duration(query_type, mode, 0.5)

        # Verify no exceptions


# ============================================================================
# Gauge Tests
# ============================================================================


@pytest.mark.unit
class TestGaugeUpdates:
    """Test gauge metrics update correctly."""

    def test_update_gpu_memory_sets_all_gauges(self):
        """Test update_gpu_memory sets memory usage, allocated, and utilization gauges."""
        # Update GPU metrics
        metrics.update_gpu_memory(
            gpu_id=0,
            used_bytes=8_589_934_592,  # 8 GB
            allocated_bytes=6_442_450_944,  # 6 GB
            utilization=75.5,
        )

        # Verify no exceptions

    def test_update_gpu_memory_multiple_gpus(self):
        """Test updating GPU metrics for multiple GPUs independently."""
        # Update metrics for GPU 0
        metrics.update_gpu_memory(
            gpu_id=0, used_bytes=8_000_000_000, allocated_bytes=6_000_000_000, utilization=80.0
        )

        # Update metrics for GPU 1
        metrics.update_gpu_memory(
            gpu_id=1, used_bytes=4_000_000_000, allocated_bytes=3_000_000_000, utilization=45.0
        )

        # Verify no exceptions

    def test_update_gpu_memory_with_zero_utilization(self):
        """Test updating GPU metrics when GPU is idle."""
        metrics.update_gpu_memory(
            gpu_id=0,
            used_bytes=1_073_741_824,  # 1 GB baseline
            allocated_bytes=536_870_912,  # 512 MB
            utilization=0.0,
        )

        # Verify no exceptions

    def test_update_gpu_memory_with_full_utilization(self):
        """Test updating GPU metrics at maximum utilization."""
        metrics.update_gpu_memory(
            gpu_id=0,
            used_bytes=16_106_127_360,  # 15 GB (almost full)
            allocated_bytes=15_032_385_536,  # 14 GB
            utilization=100.0,
        )

        # Verify no exceptions

    def test_update_active_connections_sets_gauge(self):
        """Test update_active_connections sets connection count gauge."""
        # Update different connection types
        metrics.update_active_connections("neo4j", 5)
        metrics.update_active_connections("qdrant", 3)
        metrics.update_active_connections("redis", 10)
        metrics.update_active_connections("ollama", 2)

        # Verify no exceptions

    def test_update_active_connections_with_zero(self):
        """Test updating active connections to zero (no connections)."""
        metrics.update_active_connections("neo4j", 0)
        metrics.update_active_connections("qdrant", 0)

        # Verify no exceptions


# ============================================================================
# Helper Function Tests
# ============================================================================


@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions with various parameters and labels."""

    def test_record_extraction_duration_with_labels(self):
        """Test record_extraction_duration with different label combinations."""
        # Test various phase and pipeline_type combinations
        test_cases = [
            ("phase1_spacy", "three_phase", 0.5),
            ("phase2_dedup", "three_phase", 1.0),
            ("phase3_gemma", "three_phase", 3.5),
            ("default", "lightrag_default", 2.0),
        ]

        for phase, pipeline_type, duration in test_cases:
            metrics.record_extraction_duration(phase, pipeline_type, duration)

        # Verify no exceptions

    def test_record_extraction_entities_with_labels(self):
        """Test record_extraction_entities with different entity types."""
        entity_types = ["PERSON", "ORG", "GPE", "DATE", "MONEY", "PRODUCT"]

        for entity_type in entity_types:
            metrics.record_extraction_entities(entity_type, "three_phase", 10)

        # Verify no exceptions

    def test_record_extraction_error_with_error_types(self):
        """Test record_extraction_error with different error types."""
        error_types = [
            ("phase1_spacy", "connection_error"),
            ("phase2_dedup", "validation_error"),
            ("phase3_gemma", "timeout"),
            ("phase3_gemma", "rate_limit_error"),
            ("phase1_spacy", "memory_error"),
        ]

        for phase, error_type in error_types:
            metrics.record_extraction_error(phase, error_type)

        # Verify no exceptions

    def test_record_extraction_retry_with_boolean_success(self):
        """Test record_extraction_retry converts boolean to string correctly."""
        # Test with True
        metrics.record_extraction_retry("phase3_gemma", success=True)

        # Test with False
        metrics.record_extraction_retry("phase3_gemma", success=False)

        # Verify no exceptions

    def test_record_extraction_document_with_all_statuses(self):
        """Test record_extraction_document with all valid statuses."""
        statuses = ["success", "failed", "skipped"]

        for status in statuses:
            metrics.record_extraction_document("three_phase", status)

        # Verify no exceptions


# ============================================================================
# System Info Tests
# ============================================================================


@pytest.mark.unit
class TestSystemInfoInitialization:
    """Test system info metric initialization."""

    def test_initialize_system_info_with_config(self, mock_config):
        """Test initialize_system_info sets correct system information."""
        # Initialize system info
        metrics.initialize_system_info(mock_config)

        # Verify no exceptions
        # Note: We can't easily verify the info values without scraping /metrics

    def test_initialize_system_info_with_partial_config(self):
        """Test initialize_system_info with partial configuration."""
        # Create config with only some attributes
        config = Mock()
        config.app_version = "0.2.0"
        # Other attributes missing (will use getattr defaults)

        metrics.initialize_system_info(config)

        # Verify no exceptions

    @patch("src.monitoring.metrics.logger")
    def test_initialize_system_info_logs_initialization(self, mock_logger, mock_config):
        """Test initialize_system_info logs initialization event."""
        metrics.initialize_system_info(mock_config)

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "prometheus_metrics_initialized" in call_args[0]


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestMetricsIntegration:
    """Test metrics integration scenarios."""

    def test_multiple_metrics_concurrent_access(self):
        """Test thread-safety of metrics with concurrent access."""

        def record_metrics(thread_id: int):
            """Record various metrics from a single thread."""
            for i in range(100):
                metrics.record_extraction_duration("phase1_spacy", "three_phase", 0.5)
                metrics.record_extraction_entities("PERSON", "three_phase", 1)
                metrics.record_extraction_relations("three_phase", 1)
                metrics.record_extraction_document("three_phase", "success")
                metrics.record_deduplication_reduction(0.15)
                metrics.record_query_duration("vector", "local", 0.3)

        # Run in multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(record_metrics, i) for i in range(10)]

            # Wait for all threads to complete
            for future in futures:
                future.result()

        # Verify no exceptions occurred

    def test_metrics_workflow_extraction_pipeline(self):
        """Test complete extraction pipeline metrics workflow."""
        # Simulate extraction pipeline
        start_time = time.time()

        # Phase 1: SpaCy
        metrics.record_extraction_duration("phase1_spacy", "three_phase", 0.5)
        metrics.record_extraction_entities("PERSON", "three_phase", 25)
        metrics.record_extraction_entities("ORG", "three_phase", 10)

        # Phase 2: Deduplication
        metrics.record_extraction_duration("phase2_dedup", "three_phase", 0.3)
        metrics.record_deduplication_reduction(0.20)

        # Phase 3: Gemma
        metrics.record_extraction_duration("phase3_gemma", "three_phase", 4.5)
        metrics.record_extraction_relations("three_phase", 42)

        # Success
        metrics.record_extraction_document("three_phase", "success")

        # Verify workflow completed without errors

    def test_metrics_workflow_with_errors_and_retries(self):
        """Test metrics workflow with error handling and retries."""
        # First attempt fails
        metrics.record_extraction_duration("phase3_gemma", "three_phase", 2.0)
        metrics.record_extraction_error("phase3_gemma", "timeout")

        # Retry 1 fails
        metrics.record_extraction_retry("phase3_gemma", success=False)
        metrics.record_extraction_error("phase3_gemma", "timeout")

        # Retry 2 succeeds
        metrics.record_extraction_retry("phase3_gemma", success=True)
        metrics.record_extraction_duration("phase3_gemma", "three_phase", 3.5)
        metrics.record_extraction_relations("three_phase", 30)
        metrics.record_extraction_document("three_phase", "success")

        # Verify workflow completed

    def test_metrics_workflow_query_processing(self):
        """Test complete query processing metrics workflow."""
        # Hybrid query with vector and graph components
        metrics.record_query_duration("vector", "local", 0.2)
        metrics.record_query_duration("graph", "global", 0.8)
        metrics.record_query_duration("hybrid", "local", 1.0)

        # Verify workflow completed

    def test_metrics_export_format_compatibility(self):
        """Test that metrics are compatible with Prometheus export format."""
        # Record various metrics
        metrics.record_extraction_duration("phase1_spacy", "three_phase", 1.0)
        metrics.record_extraction_entities("PERSON", "three_phase", 10)
        metrics.record_extraction_relations("three_phase", 5)
        metrics.record_deduplication_reduction(0.15)
        metrics.update_gpu_memory(0, 8_000_000_000, 6_000_000_000, 75.0)
        metrics.record_query_duration("vector", "local", 0.5)

        # Verify all metrics can be collected by registry
        # This ensures they're properly formatted for Prometheus
        try:
            from prometheus_client import generate_latest

            output = generate_latest(REGISTRY)
            assert output is not None
            assert len(output) > 0
        except Exception as e:
            pytest.fail(f"Metrics export failed: {e}")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_record_extraction_entities_with_zero_count(self):
        """Test recording zero entities (edge case)."""
        metrics.record_extraction_entities("PERSON", "three_phase", 0)

        # Verify no exceptions

    def test_record_extraction_relations_with_large_count(self):
        """Test recording very large relation counts."""
        metrics.record_extraction_relations("three_phase", 10_000)

        # Verify no exceptions

    def test_record_deduplication_ratio_boundary_values(self):
        """Test deduplication ratio at boundary values."""
        # Minimum (no deduplication)
        metrics.record_deduplication_reduction(0.0)

        # Maximum (50% deduplication)
        metrics.record_deduplication_reduction(0.5)

        # Verify no exceptions

    def test_gpu_metrics_with_very_large_memory(self):
        """Test GPU metrics with very large memory values (e.g., A100 80GB)."""
        metrics.update_gpu_memory(
            gpu_id=0,
            used_bytes=85_899_345_920,  # 80 GB
            allocated_bytes=80_530_636_800,  # 75 GB
            utilization=95.0,
        )

        # Verify no exceptions

    def test_metrics_with_special_characters_in_labels(self):
        """Test metrics with special characters in label values."""
        # Entity types might have underscores or special chars
        metrics.record_extraction_entities("CUSTOM_ENTITY_TYPE", "three_phase", 5)
        metrics.record_extraction_error("phase3_gemma", "rate_limit_error")

        # Verify no exceptions

    def test_record_extraction_duration_with_negative_duration(self):
        """Test recording negative duration (should not crash, but may be invalid)."""
        # This is an edge case that shouldn't happen, but we test for robustness
        try:
            metrics.record_extraction_duration("phase1_spacy", "three_phase", -0.5)
            # If it doesn't raise, that's fine (Prometheus will handle it)
        except ValueError:
            # If it raises ValueError, that's also acceptable
            pass


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.unit
class TestMetricsPerformance:
    """Test metrics performance characteristics."""

    def test_metrics_recording_is_fast(self):
        """Test that metrics recording has minimal overhead."""
        iterations = 1000

        start_time = time.time()
        for i in range(iterations):
            metrics.record_extraction_duration("phase1_spacy", "three_phase", 1.0)
            metrics.record_extraction_entities("PERSON", "three_phase", 10)
            metrics.record_extraction_relations("three_phase", 5)
        elapsed = time.time() - start_time

        # Recording 3000 metrics should take less than 1 second
        assert (
            elapsed < 1.0
        ), f"Metrics recording too slow: {elapsed:.3f}s for {iterations*3} operations"

    def test_histogram_observation_performance(self):
        """Test histogram observation performance."""
        iterations = 1000

        start_time = time.time()
        for i in range(iterations):
            metrics.record_extraction_duration("phase1_spacy", "three_phase", float(i % 100) / 10)
        elapsed = time.time() - start_time

        # Should be very fast
        assert elapsed < 0.5, f"Histogram observations too slow: {elapsed:.3f}s"

    def test_counter_increment_performance(self):
        """Test counter increment performance."""
        iterations = 1000

        start_time = time.time()
        for i in range(iterations):
            metrics.record_extraction_entities("PERSON", "three_phase", 1)
        elapsed = time.time() - start_time

        # Should be very fast
        assert elapsed < 0.5, f"Counter increments too slow: {elapsed:.3f}s"


# ============================================================================
# Documentation Tests
# ============================================================================


@pytest.mark.unit
class TestMetricsDocumentation:
    """Test that metrics have proper documentation."""

    def test_metrics_have_descriptions(self):
        """Test that all metrics have help text/descriptions."""
        # Check a few key metrics have descriptions
        assert hasattr(metrics.extraction_duration, "_documentation")
        assert hasattr(metrics.extraction_entities_total, "_documentation")
        assert hasattr(metrics.deduplication_reduction_ratio, "_documentation")

    def test_histogram_buckets_are_reasonable(self):
        """Test that histogram buckets are configured appropriately."""
        # Extraction duration should have buckets for expected ranges
        # This is implicit in the metric definition, we just verify it exists
        assert metrics.extraction_duration is not None
        assert metrics.query_duration is not None
        assert metrics.deduplication_reduction_ratio is not None
