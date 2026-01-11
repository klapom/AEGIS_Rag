"""Unit tests for ingestion logging utilities.

Sprint 83 Feature 83.1: Comprehensive ingestion logging tests
Tests all logging functions: phase summary, LLM cost, quality metrics, provenance, memory.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import structlog

from src.components.ingestion.logging_utils import (
    PhaseLatencyTracker,
    calculate_percentiles,
    get_gpu_memory_info,
    log_chunk_entity_mapping,
    log_extraction_quality_metrics,
    log_llm_cost_summary,
    log_memory_snapshot,
    log_phase_summary,
)


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock structlog logger to capture log events."""
    mock = MagicMock()
    monkeypatch.setattr("src.components.ingestion.logging_utils.logger", mock)
    return mock


class TestCalculatePercentiles:
    """Test percentile calculation for latency analysis."""

    def test_calculate_percentiles_normal_distribution(self):
        """Test percentile calculation with normal distribution."""
        # 100 samples from 100ms to 1000ms
        values = list(range(100, 1001, 10))
        percentiles = calculate_percentiles(values)

        assert "p50_ms" in percentiles
        assert "p95_ms" in percentiles
        assert "p99_ms" in percentiles

        # P50 should be around 550ms (median)
        assert 500 <= percentiles["p50_ms"] <= 600

        # P95 should be around 950ms
        assert 900 <= percentiles["p95_ms"] <= 1000

        # P99 should be around 990ms (allow slight tolerance for rounding)
        assert 950 <= percentiles["p99_ms"] <= 1005

    def test_calculate_percentiles_empty_list(self):
        """Test percentile calculation with empty list."""
        percentiles = calculate_percentiles([])

        assert percentiles["p50_ms"] == 0.0
        assert percentiles["p95_ms"] == 0.0
        assert percentiles["p99_ms"] == 0.0

    def test_calculate_percentiles_single_value(self):
        """Test percentile calculation with single value."""
        percentiles = calculate_percentiles([100.0])

        # All percentiles should be the single value
        assert percentiles["p50_ms"] == 100.0
        assert percentiles["p95_ms"] == 100.0
        assert percentiles["p99_ms"] == 100.0

    def test_calculate_percentiles_outliers(self):
        """Test percentile calculation with outliers."""
        # 95 fast samples (100-200ms) + 5 slow outliers (1000-2000ms)
        values = list(range(100, 201)) + [1000, 1200, 1500, 1800, 2000]
        percentiles = calculate_percentiles(values)

        # P50 should still be around 150ms (not affected by outliers)
        assert 140 <= percentiles["p50_ms"] <= 160

        # P95 should capture the outliers
        assert percentiles["p95_ms"] > 500

        # P99 should be close to max outlier
        assert percentiles["p99_ms"] > 1500


class TestLogPhaseSummary:
    """Test phase summary logging with percentiles."""

    def test_log_phase_summary_basic(self, mock_logger):
        """Test basic phase summary logging."""
        log_phase_summary(
            phase="test_phase",
            total_time_ms=1000.0,
            items_processed=10,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "TIMING_phase_summary"
        assert call_args[1]["phase"] == "test_phase"
        assert call_args[1]["total_time_ms"] == 1000.0
        assert call_args[1]["items_processed"] == 10
        assert call_args[1]["per_item_avg_ms"] == 100.0

    def test_log_phase_summary_with_percentiles(self, mock_logger):
        """Test phase summary with per-item latencies."""
        latencies = [100, 150, 200, 250, 300]
        log_phase_summary(
            phase="test_phase",
            total_time_ms=1000.0,
            items_processed=5,
            per_item_latencies_ms=latencies,
        )

        call_args = mock_logger.info.call_args
        assert "p50_ms" in call_args[1]
        assert "p95_ms" in call_args[1]
        assert "p99_ms" in call_args[1]

    def test_log_phase_summary_with_extra_metrics(self, mock_logger):
        """Test phase summary with extra metrics."""
        log_phase_summary(
            phase="graph_extraction",
            total_time_ms=5000.0,
            items_processed=50,
            entities_extracted=150,
            relations_created=80,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["entities_extracted"] == 150
        assert call_args[1]["relations_created"] == 80

    def test_log_phase_summary_zero_items(self, mock_logger):
        """Test phase summary with zero items (should not divide by zero)."""
        log_phase_summary(
            phase="test_phase",
            total_time_ms=1000.0,
            items_processed=0,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["per_item_avg_ms"] == 0.0


class TestLogLLMCostSummary:
    """Test LLM cost summary logging."""

    def test_log_llm_cost_summary_basic(self, mock_logger):
        """Test basic LLM cost summary."""
        log_llm_cost_summary(
            document_id="doc_123",
            phase="entity_extraction",
            total_tokens=125000,
            prompt_tokens=100000,
            completion_tokens=25000,
            model="qwen3:32b",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "llm_cost_summary"
        assert call_args[1]["document_id"] == "doc_123"
        assert call_args[1]["phase"] == "entity_extraction"
        assert call_args[1]["total_tokens"] == 125000
        assert call_args[1]["prompt_tokens"] == 100000
        assert call_args[1]["completion_tokens"] == 25000
        assert call_args[1]["model"] == "qwen3:32b"

    def test_log_llm_cost_summary_with_cost(self, mock_logger):
        """Test LLM cost summary with cost estimate."""
        log_llm_cost_summary(
            document_id="doc_123",
            phase="entity_extraction",
            total_tokens=125000,
            prompt_tokens=100000,
            completion_tokens=25000,
            model="qwen3:32b",
            estimated_cost_usd=0.025,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["estimated_cost_usd"] == 0.025

    def test_log_llm_cost_summary_no_cost(self, mock_logger):
        """Test LLM cost summary without cost (local model)."""
        log_llm_cost_summary(
            document_id="doc_123",
            phase="entity_extraction",
            total_tokens=125000,
            prompt_tokens=100000,
            completion_tokens=25000,
            model="nemotron3",
        )

        call_args = mock_logger.info.call_args
        assert "estimated_cost_usd" not in call_args[1]


class TestLogExtractionQualityMetrics:
    """Test extraction quality metrics logging."""

    def test_log_extraction_quality_metrics_basic(self, mock_logger):
        """Test basic extraction quality metrics."""
        log_extraction_quality_metrics(
            chunk_id="chunk_456",
            raw_entities_extracted=45,
            deduplicated_entities=32,
            entity_types=["Product", "Feature", "Error Code"],
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "extraction_quality_metrics"
        assert call_args[1]["chunk_id"] == "chunk_456"
        assert call_args[1]["raw_entities_extracted"] == 45
        assert call_args[1]["deduplicated_entities"] == 32
        assert call_args[1]["deduplication_rate"] == 0.29  # (45-32)/45 = 0.29
        assert call_args[1]["entity_types"] == ["Product", "Feature", "Error Code"]

    def test_log_extraction_quality_metrics_with_confidence(self, mock_logger):
        """Test extraction quality metrics with relation confidence."""
        log_extraction_quality_metrics(
            chunk_id="chunk_456",
            raw_entities_extracted=45,
            deduplicated_entities=32,
            entity_types=["Product"],
            relation_confidence_avg=0.78,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["relation_confidence_avg"] == 0.78

    def test_log_extraction_quality_metrics_zero_entities(self, mock_logger):
        """Test extraction quality metrics with zero entities."""
        log_extraction_quality_metrics(
            chunk_id="chunk_456",
            raw_entities_extracted=0,
            deduplicated_entities=0,
            entity_types=[],
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["deduplication_rate"] == 0.0


class TestLogChunkEntityMapping:
    """Test chunk-entity provenance logging."""

    def test_log_chunk_entity_mapping_basic(self, mock_logger):
        """Test basic chunk-entity mapping."""
        log_chunk_entity_mapping(
            chunk_id="chunk_456",
            entities_created=["Entity_789", "Entity_790"],
            relations_created=["Rel_123", "Rel_124"],
            section_hierarchy=["1.2.3 Troubleshooting", "1.2.3.1 Common Issues"],
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "chunk_entity_mapping"
        assert call_args[1]["chunk_id"] == "chunk_456"
        assert call_args[1]["entities_created"] == ["Entity_789", "Entity_790"]
        assert call_args[1]["relations_created"] == ["Rel_123", "Rel_124"]
        assert call_args[1]["section_hierarchy"] == [
            "1.2.3 Troubleshooting",
            "1.2.3.1 Common Issues",
        ]

    def test_log_chunk_entity_mapping_with_extra_provenance(self, mock_logger):
        """Test chunk-entity mapping with extra provenance data."""
        log_chunk_entity_mapping(
            chunk_id="chunk_456",
            entities_created=["Entity_789"],
            relations_created=["Rel_123"],
            section_hierarchy=["Introduction"],
            page_no=5,
            document_id="doc_123",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["page_no"] == 5
        assert call_args[1]["document_id"] == "doc_123"


class TestLogMemorySnapshot:
    """Test memory snapshot logging."""

    def test_log_memory_snapshot_ram_only(self, mock_logger):
        """Test memory snapshot with RAM only (no GPU)."""
        with patch("src.components.ingestion.logging_utils.get_gpu_memory_info", return_value=None):
            log_memory_snapshot(
                phase="entity_extraction",
                ram_used_mb=2048,
                ram_available_mb=6144,
            )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "memory_snapshot"
        assert call_args[1]["phase"] == "entity_extraction"
        assert call_args[1]["ram_used_mb"] == 2048
        assert call_args[1]["ram_available_mb"] == 6144
        assert "vram_used_mb" not in call_args[1]

    def test_log_memory_snapshot_with_gpu(self, mock_logger):
        """Test memory snapshot with GPU VRAM."""
        with patch(
            "src.components.ingestion.logging_utils.get_gpu_memory_info",
            return_value={"vram_used_mb": 4096, "vram_available_mb": 4096},
        ):
            log_memory_snapshot(
                phase="entity_extraction",
                ram_used_mb=2048,
                ram_available_mb=6144,
            )

        call_args = mock_logger.info.call_args
        assert call_args[1]["vram_used_mb"] == 4096
        assert call_args[1]["vram_available_mb"] == 4096


class TestGetGPUMemoryInfo:
    """Test GPU memory info retrieval."""

    def test_get_gpu_memory_info_no_pynvml(self):
        """Test GPU memory info when pynvml not available."""
        with patch("src.components.ingestion.logging_utils.PYNVML_AVAILABLE", False):
            result = get_gpu_memory_info()
            assert result is None

    # Note: Advanced pynvml mocking tests removed as pynvml is imported conditionally
    # The function itself handles missing pynvml gracefully by returning None
    # GPU functionality is tested during integration tests on actual hardware


class TestPhaseLatencyTracker:
    """Test latency tracker context manager."""

    def test_phase_latency_tracker_basic(self, mock_logger):
        """Test basic latency tracking."""
        tracker = PhaseLatencyTracker()

        # Track 3 operations
        for _ in range(3):
            with tracker.track():
                time.sleep(0.01)  # 10ms

        tracker.log_summary(phase="test_phase", items_processed=3)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["phase"] == "test_phase"
        assert call_args[1]["items_processed"] == 3
        assert len(tracker.latencies_ms) == 3
        # Each latency should be around 10ms (with some tolerance)
        for latency in tracker.latencies_ms:
            assert 5 <= latency <= 50  # Allow for system variance

    def test_phase_latency_tracker_empty(self, mock_logger):
        """Test latency tracker with no tracked operations."""
        tracker = PhaseLatencyTracker()
        tracker.log_summary(phase="test_phase", items_processed=0)

        call_args = mock_logger.info.call_args
        assert call_args[1]["total_time_ms"] == 0.0
        assert call_args[1]["items_processed"] == 0

    def test_phase_latency_tracker_with_extra_metrics(self, mock_logger):
        """Test latency tracker with extra metrics."""
        tracker = PhaseLatencyTracker()

        with tracker.track():
            time.sleep(0.01)

        tracker.log_summary(
            phase="test_phase",
            items_processed=1,
            entities_extracted=50,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["entities_extracted"] == 50
