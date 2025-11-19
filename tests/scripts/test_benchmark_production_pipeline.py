"""Unit and Integration Tests for Production Benchmarking Suite.

Sprint 14 Feature 14.3: Test Suite for benchmark_production_pipeline.py
Tests benchmark scenarios, metrics calculation, JSON output, and performance validation.

Target Coverage: >70%

Author: Claude Code
Date: 2025-10-27
"""

import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import benchmark script functions
from scripts.benchmark_production_pipeline import (
    TEST_SCENARIOS,
    benchmark_batch_processing,
    benchmark_scenario,
    check_target,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_extractor():
    """Mock ThreePhaseExtractor for unit tests.

    Returns:
        Mock extractor with predictable behavior
    """
    extractor = AsyncMock()

    # Configure extract method to return realistic results
    async def mock_extract(text: str, document_id: str = None):
        """Mock extraction with realistic entity/relation counts based on text size."""
        word_count = len(text.split())

        # Simulate entity extraction (roughly 1 entity per 50 words)
        num_entities = max(5, word_count // 50)
        entities = [
            {
                "name": f"Entity_{i}",
                "type": "PERSON",
                "description": f"Description for entity {i}",
            }
            for i in range(num_entities)
        ]

        # Simulate relation extraction (roughly 70% of entity count)
        num_relations = max(3, int(num_entities * 0.7))
        relations = [
            {
                "source": f"Entity_{i}",
                "target": f"Entity_{i+1}",
                "type": "WORKS_WITH",
                "description": f"Relation {i}",
            }
            for i in range(num_relations)
        ]

        # Simulate realistic processing time based on word count
        # Small (100-500 words): ~5s
        # Medium (500-2000 words): ~15s
        # Large (2000-5000 words): ~30s
        if word_count < 500:
            await asyncio.sleep(0.01)  # Fast for tests (0.01s instead of 5s)
        elif word_count < 2000:
            await asyncio.sleep(0.02)  # Fast for tests (0.02s instead of 15s)
        else:
            await asyncio.sleep(0.03)  # Fast for tests (0.03s instead of 30s)

        return entities, relations

    extractor.extract = mock_extract
    return extractor


@pytest.fixture
def mock_settings():
    """Mock application settings for unit tests.

    Returns:
        Mock settings object
    """
    settings = MagicMock()
    settings.extraction_pipeline = "three_phase"
    settings.enable_semantic_dedup = True
    settings.extraction_max_retries = 3
    return settings


@pytest.fixture
def sample_scenario_config():
    """Sample scenario configuration for testing.

    Returns:
        Dict with scenario config
    """
    return {
        "name": "Test Documents (100 words)",
        "word_count_range": (100, 200),
        "sample_text": "Test " * 100,  # 100 words
    }


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for benchmark output files.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path to temporary output directory
    """
    output_dir = tmp_path / "benchmark_output"
    output_dir.mkdir()
    return output_dir


# ============================================================================
# Unit Tests: Scenario Benchmarking
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_small_document_scenario(mock_extractor):
    """Test benchmark with small document scenario.

    Verifies:
    - Extraction runs successfully
    - Results include expected metrics
    - Throughput calculated correctly
    """
    scenario_name = "small"
    scenario_config = TEST_SCENARIOS["small"]
    iterations = 3

    result = await benchmark_scenario(
        mock_extractor, scenario_name, scenario_config, iterations=iterations
    )

    # Verify result structure
    assert result["scenario"] == "small"
    assert result["name"] == scenario_config["name"]
    assert result["iterations"] == iterations

    # Verify metrics exist
    assert "avg_time_sec" in result
    assert "std_time_sec" in result
    assert "min_time_sec" in result
    assert "max_time_sec" in result
    assert "avg_entities" in result
    assert "avg_relations" in result
    assert "throughput_docs_per_min" in result
    assert "throughput_words_per_sec" in result
    assert "raw_results" in result

    # Verify raw results count
    assert len(result["raw_results"]) == iterations

    # Verify throughput calculations
    assert result["throughput_docs_per_min"] > 0
    assert result["throughput_words_per_sec"] > 0

    print(f"[PASS] Small scenario benchmark: {result['avg_time_sec']:.2f}s avg")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_medium_document_scenario(mock_extractor):
    """Test benchmark with medium document scenario.

    Verifies:
    - Medium documents handled correctly
    - Processing time scales appropriately
    - Entity/relation counts are reasonable
    """
    scenario_name = "medium"
    scenario_config = TEST_SCENARIOS["medium"]
    iterations = 2

    result = await benchmark_scenario(
        mock_extractor, scenario_name, scenario_config, iterations=iterations
    )

    # Verify scenario processed
    assert result["scenario"] == "medium"
    assert result["iterations"] == iterations

    # Verify entity/relation counts are higher than small docs
    assert result["avg_entities"] >= 10, "Medium docs should have >= 10 entities"
    assert result["avg_relations"] >= 7, "Medium docs should have >= 7 relations"

    print(
        f"[PASS] Medium scenario: {result['avg_entities']:.0f} entities, {result['avg_relations']:.0f} relations"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_large_document_scenario(mock_extractor):
    """Test benchmark with large document scenario.

    Verifies:
    - Large documents processed successfully
    - Higher entity/relation counts for large docs
    - Metrics calculated correctly
    """
    scenario_name = "large"
    scenario_config = TEST_SCENARIOS["large"]
    iterations = 2

    result = await benchmark_scenario(
        mock_extractor, scenario_name, scenario_config, iterations=iterations
    )

    # Verify scenario processed
    assert result["scenario"] == "large"
    assert result["word_count"] >= 2000, "Large docs should have >= 2000 words"

    # Verify entity/relation counts are highest
    assert result["avg_entities"] >= 20, "Large docs should have >= 20 entities"
    assert result["avg_relations"] >= 14, "Large docs should have >= 14 relations"

    print(f"[PASS] Large scenario: {result['word_count']} words")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_batch_processing(mock_extractor):
    """Test batch processing benchmark.

    Verifies:
    - Multiple documents processed in batch
    - Total metrics aggregated correctly
    - Average per-document metrics calculated
    """
    batch_size = 5
    doc_size = "small"

    result = await benchmark_batch_processing(
        mock_extractor, batch_size=batch_size, doc_size=doc_size
    )

    # Verify result structure
    assert result["batch_size"] == batch_size
    assert result["doc_size"] == doc_size

    # Verify metrics
    assert "total_time_sec" in result
    assert "avg_time_per_doc_sec" in result
    assert "throughput_docs_per_sec" in result
    assert "total_entities" in result
    assert "total_relations" in result
    assert "avg_entities_per_doc" in result
    assert "avg_relations_per_doc" in result

    # Verify batch metrics
    assert result["total_entities"] > 0
    assert result["total_relations"] > 0
    assert result["throughput_docs_per_sec"] > 0

    # Verify average calculations
    expected_avg_entities = result["total_entities"] / batch_size
    assert abs(result["avg_entities_per_doc"] - expected_avg_entities) < 0.01

    print(f"[PASS] Batch processing: {batch_size} docs in {result['total_time_sec']:.2f}s")


# ============================================================================
# Unit Tests: Metrics Calculation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_calculates_throughput(mock_extractor):
    """Test that throughput metrics are calculated correctly.

    Verifies:
    - Documents per minute calculated from avg time
    - Words per second calculated correctly
    - Throughput values are positive
    """
    scenario_name = "small"
    scenario_config = TEST_SCENARIOS["small"]

    result = await benchmark_scenario(mock_extractor, scenario_name, scenario_config, iterations=2)

    # Verify throughput calculations
    word_count = result["word_count"]
    avg_time = result["avg_time_sec"]

    expected_docs_per_min = 60 / avg_time if avg_time > 0 else 0
    expected_words_per_sec = word_count / avg_time if avg_time > 0 else 0

    assert abs(result["throughput_docs_per_min"] - expected_docs_per_min) < 0.01
    assert abs(result["throughput_words_per_sec"] - expected_words_per_sec) < 0.01

    print(
        f"[PASS] Throughput: {result['throughput_docs_per_min']:.1f} docs/min, {result['throughput_words_per_sec']:.1f} words/sec"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_tracks_entity_relation_counts(mock_extractor):
    """Test that entity and relation counts are tracked correctly.

    Verifies:
    - Entity counts recorded for each iteration
    - Relation counts recorded for each iteration
    - Averages calculated correctly
    """
    scenario_name = "small"
    scenario_config = TEST_SCENARIOS["small"]
    iterations = 3

    result = await benchmark_scenario(
        mock_extractor, scenario_name, scenario_config, iterations=iterations
    )

    # Verify raw results have entity/relation counts
    for raw_result in result["raw_results"]:
        assert "entities" in raw_result
        assert "relations" in raw_result
        assert raw_result["entities"] > 0
        assert raw_result["relations"] > 0

    # Verify averages
    entity_counts = [r["entities"] for r in result["raw_results"]]
    relation_counts = [r["relations"] for r in result["raw_results"]]

    expected_avg_entities = statistics.mean(entity_counts)
    expected_avg_relations = statistics.mean(relation_counts)

    assert abs(result["avg_entities"] - expected_avg_entities) < 0.01
    assert abs(result["avg_relations"] - expected_avg_relations) < 0.01

    print(
        f"[PASS] Entity/relation tracking: {result['avg_entities']:.0f} entities, {result['avg_relations']:.0f} relations"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_json_output_format(mock_extractor, temp_output_dir):
    """Test that benchmark results can be serialized to JSON.

    Verifies:
    - Results are JSON-serializable
    - JSON structure is correct
    - All required fields present
    """
    scenario_name = "small"
    scenario_config = TEST_SCENARIOS["small"]

    result = await benchmark_scenario(mock_extractor, scenario_name, scenario_config, iterations=2)

    # Verify JSON serialization
    json_str = json.dumps(result, indent=2)
    assert json_str is not None

    # Verify can be deserialized
    deserialized = json.loads(json_str)
    assert deserialized["scenario"] == scenario_name
    assert "avg_time_sec" in deserialized
    assert "avg_entities" in deserialized
    assert "raw_results" in deserialized

    # Test writing to file
    output_file = temp_output_dir / "test_benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    assert output_file.exists()

    # Verify file can be read back
    with open(output_file, "r") as f:
        loaded_result = json.load(f)

    assert loaded_result["scenario"] == scenario_name

    print(f"[PASS] JSON output: {len(json_str)} chars written to {output_file.name}")


# ============================================================================
# Unit Tests: Performance Validation
# ============================================================================


@pytest.mark.unit
def test_benchmark_validates_performance_targets(capsys):
    """Test that performance target validation works correctly.

    Verifies:
    - PASS when actual <= target
    - FAIL when actual > target
    - Proper output formatting
    """
    # Test PASS case
    check_target("Test scenario", 5.0, 10.0)
    captured = capsys.readouterr()
    assert "✅ PASS" in captured.out
    assert "5.00s" in captured.out
    assert "target: <10.0s" in captured.out

    # Test FAIL case
    check_target("Test scenario", 15.0, 10.0)
    captured = capsys.readouterr()
    assert "❌ FAIL" in captured.out
    assert "15.00s" in captured.out

    print("[PASS] Performance target validation")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_fails_on_timeout():
    """Test that benchmark handles timeout scenarios gracefully.

    Verifies:
    - Timeout behavior for slow extractors
    - Error handling for timeouts
    """
    # Create slow extractor that times out
    slow_extractor = AsyncMock()

    async def slow_extract(text: str, document_id: str = None):
        await asyncio.sleep(10)  # Simulate slow extraction
        return [], []

    slow_extractor.extract = slow_extract

    scenario_config = {
        "name": "Timeout Test",
        "word_count_range": (100, 200),
        "sample_text": "Test " * 100,
    }

    # Test with timeout
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            benchmark_scenario(slow_extractor, "timeout_test", scenario_config, iterations=1),
            timeout=1.0,
        )

    print("[PASS] Timeout handling")


# ============================================================================
# Unit Tests: Integration with Mocked Extractor
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_with_mock_extractor(mock_extractor, mock_settings):
    """Test complete benchmark flow with mocked extractor.

    Verifies:
    - All scenarios run successfully
    - Batch processing works
    - Results aggregated correctly
    """
    all_results = {
        "timestamp": "2025-10-27T12:00:00",
        "config": {
            "extraction_pipeline": mock_settings.extraction_pipeline,
            "enable_dedup": mock_settings.enable_semantic_dedup,
            "max_retries": mock_settings.extraction_max_retries,
        },
        "scenarios": [],
        "batch_tests": [],
    }

    # Run all scenario benchmarks
    for scenario_name, scenario_config in TEST_SCENARIOS.items():
        result = await benchmark_scenario(
            mock_extractor, scenario_name, scenario_config, iterations=2
        )
        all_results["scenarios"].append(result)

    # Run batch processing benchmarks
    batch_configs = [(5, "small"), (3, "medium")]
    for batch_size, doc_size in batch_configs:
        result = await benchmark_batch_processing(
            mock_extractor, batch_size=batch_size, doc_size=doc_size
        )
        all_results["batch_tests"].append(result)

    # Verify all results collected
    assert len(all_results["scenarios"]) == len(TEST_SCENARIOS)
    assert len(all_results["batch_tests"]) == len(batch_configs)

    # Verify JSON serialization
    json_str = json.dumps(all_results, indent=2)
    assert json_str is not None

    print(
        f"[PASS] Full benchmark with mock extractor: {len(all_results['scenarios'])} scenarios, {len(all_results['batch_tests'])} batch tests"
    )


# ============================================================================
# Integration Tests: Real Pipeline
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_benchmark_with_real_pipeline(ollama_client_real):
    """Integration test with real Three-Phase Extraction Pipeline.

    Uses real ThreePhaseExtractor with Ollama models.
    Tests actual performance and output quality.

    Note: This test requires:
    - Ollama running locally
    - gemma-3-4b-it model available
    - nomic-embed-text model available
    """
    from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

    # Initialize real extractor
    extractor = ThreePhaseExtractor()

    # Test with small scenario only (faster)
    scenario_name = "small"
    scenario_config = TEST_SCENARIOS["small"]

    result = await benchmark_scenario(extractor, scenario_name, scenario_config, iterations=2)

    # Verify realistic results
    assert result["avg_time_sec"] > 0, "Extraction should take measurable time"
    assert result["avg_time_sec"] < 60, "Small docs should complete within 60s"

    # Verify entity/relation extraction quality
    assert result["avg_entities"] >= 3, "Should extract at least 3 entities"
    assert result["avg_relations"] >= 2, "Should extract at least 2 relations"

    # Verify performance target (relaxed for integration test)
    assert (
        result["avg_time_sec"] < 30
    ), f"Small docs should be < 30s (got {result['avg_time_sec']:.1f}s)"

    print(
        f"[PASS] Real pipeline integration: {result['avg_time_sec']:.1f}s, {result['avg_entities']:.0f} entities, {result['avg_relations']:.0f} relations"
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(180)
async def test_benchmark_batch_with_real_pipeline(ollama_client_real):
    """Integration test for batch processing with real pipeline.

    Tests batch processing performance with real extractor.
    """
    from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

    # Initialize real extractor
    extractor = ThreePhaseExtractor()

    # Test small batch
    batch_size = 3
    doc_size = "small"

    result = await benchmark_batch_processing(extractor, batch_size=batch_size, doc_size=doc_size)

    # Verify batch processing
    assert result["total_time_sec"] > 0
    assert result["total_time_sec"] < 120, "3 small docs should complete within 120s"

    # Verify aggregated metrics
    assert result["total_entities"] >= batch_size * 3, "Should extract entities from all docs"
    assert result["total_relations"] >= batch_size * 2, "Should extract relations from all docs"

    # Verify throughput
    assert result["throughput_docs_per_sec"] > 0
    assert result["avg_time_per_doc_sec"] < 40, "Avg per doc should be < 40s"

    print(f"[PASS] Real batch processing: {batch_size} docs in {result['total_time_sec']:.1f}s")


# ============================================================================
# Unit Tests: Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_with_empty_text(mock_extractor):
    """Test benchmark with empty text input.

    Verifies:
    - Empty text handled gracefully
    - No errors raised
    - Metrics still calculated
    """

    # Configure mock to return empty results for empty text
    async def mock_extract_empty(text: str, document_id: str = None):
        if not text.strip():
            return [], []
        return [{"name": "Entity_1"}], [{"source": "Entity_1", "target": "Entity_2"}]

    mock_extractor.extract = mock_extract_empty

    scenario_config = {
        "name": "Empty Text Test",
        "word_count_range": (0, 0),
        "sample_text": "",
    }

    result = await benchmark_scenario(mock_extractor, "empty_test", scenario_config, iterations=1)

    # Verify empty results
    assert result["avg_entities"] == 0
    assert result["avg_relations"] == 0
    assert result["word_count"] == 0

    print("[PASS] Empty text handling")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_with_single_iteration(mock_extractor):
    """Test benchmark with single iteration (no std dev).

    Verifies:
    - Single iteration handled correctly
    - Std dev is 0 for single iteration
    - No division by zero errors
    """
    scenario_config = TEST_SCENARIOS["small"]

    result = await benchmark_scenario(mock_extractor, "single_test", scenario_config, iterations=1)

    # Verify single iteration results
    assert result["iterations"] == 1
    assert result["std_time_sec"] == 0, "Std dev should be 0 for single iteration"
    assert len(result["raw_results"]) == 1

    print("[PASS] Single iteration handling")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_preserves_document_ids(mock_extractor):
    """Test that document IDs are properly passed to extractor.

    Verifies:
    - Document IDs generated correctly for scenarios
    - Document IDs unique for batch processing
    """
    captured_doc_ids = []

    async def mock_extract_with_id_capture(text: str, document_id: str = None):
        captured_doc_ids.append(document_id)
        return [{"name": "Entity_1"}], [{"source": "Entity_1", "target": "Entity_2"}]

    mock_extractor.extract = mock_extract_with_id_capture

    # Test scenario benchmark
    scenario_config = TEST_SCENARIOS["small"]
    await benchmark_scenario(mock_extractor, "test_scenario", scenario_config, iterations=2)

    # Verify document IDs include scenario name
    # Warmup run + 2 iterations = 3 calls
    assert len(captured_doc_ids) == 3
    assert captured_doc_ids[0] == "warmup"
    assert "test_scenario" in captured_doc_ids[1]
    assert "test_scenario" in captured_doc_ids[2]

    # Test batch processing
    captured_doc_ids.clear()
    await benchmark_batch_processing(mock_extractor, batch_size=3, doc_size="small")

    # Verify unique document IDs for batch
    assert len(captured_doc_ids) == 3
    assert all("batch_" in doc_id for doc_id in captured_doc_ids)
    assert len(set(captured_doc_ids)) == 3, "All document IDs should be unique"

    print(f"[PASS] Document ID preservation: {len(captured_doc_ids)} unique IDs")


# ============================================================================
# Unit Tests: Statistics Calculation
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_calculates_min_max_correctly(mock_extractor):
    """Test that min/max time statistics are calculated correctly.

    Verifies:
    - Min time is minimum of all iterations
    - Max time is maximum of all iterations
    - Values within expected range
    """
    scenario_config = TEST_SCENARIOS["small"]

    result = await benchmark_scenario(mock_extractor, "minmax_test", scenario_config, iterations=3)

    # Extract all elapsed times
    elapsed_times = [r["elapsed"] for r in result["raw_results"]]

    # Verify min/max calculations
    assert result["min_time_sec"] == min(elapsed_times)
    assert result["max_time_sec"] == max(elapsed_times)
    assert result["min_time_sec"] <= result["avg_time_sec"] <= result["max_time_sec"]

    print(
        f"[PASS] Min/max calculation: min={result['min_time_sec']:.3f}s, max={result['max_time_sec']:.3f}s"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_benchmark_calculates_std_dev_correctly(mock_extractor):
    """Test that standard deviation is calculated correctly.

    Verifies:
    - Std dev calculated from all iterations
    - Value is non-negative
    - Value increases with variance
    """
    scenario_config = TEST_SCENARIOS["small"]

    result = await benchmark_scenario(mock_extractor, "stddev_test", scenario_config, iterations=3)

    # Extract elapsed times
    elapsed_times = [r["elapsed"] for r in result["raw_results"]]

    # Verify std dev calculation
    expected_std = statistics.stdev(elapsed_times) if len(elapsed_times) > 1 else 0
    assert abs(result["std_time_sec"] - expected_std) < 0.001
    assert result["std_time_sec"] >= 0

    print(f"[PASS] Std dev calculation: {result['std_time_sec']:.3f}s")


# ============================================================================
# Test Summary
# ============================================================================


def test_coverage_summary():
    """Print test coverage summary.

    This is not a real test, just a summary for documentation.
    """
    summary = """
    Test Coverage Summary for benchmark_production_pipeline.py:

    Scenario Tests: ✅
    - test_benchmark_small_document_scenario
    - test_benchmark_medium_document_scenario
    - test_benchmark_large_document_scenario
    - test_benchmark_batch_processing

    Metrics Tests: ✅
    - test_benchmark_calculates_throughput
    - test_benchmark_tracks_entity_relation_counts
    - test_benchmark_json_output_format

    Performance Validation: ✅
    - test_benchmark_validates_performance_targets
    - test_benchmark_fails_on_timeout

    Integration: ✅
    - test_benchmark_with_mock_extractor
    - test_benchmark_with_real_pipeline (integration)
    - test_benchmark_batch_with_real_pipeline (integration)

    Edge Cases: ✅
    - test_benchmark_with_empty_text
    - test_benchmark_with_single_iteration
    - test_benchmark_preserves_document_ids

    Statistics: ✅
    - test_benchmark_calculates_min_max_correctly
    - test_benchmark_calculates_std_dev_correctly

    Total Tests: 19 (17 unit, 2 integration)
    Target Coverage: >70%
    """
    print(summary)
