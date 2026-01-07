"""Unit tests for domain_metrics module.

Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.components.domain_training.domain_metrics import (
    DOMAIN_CONNECTIVITY_BENCHMARKS,
    ConnectivityBenchmark,
    ConnectivityMetrics,
    DomainType,
    evaluate_connectivity,
    get_connectivity_score,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def factual_benchmark() -> ConnectivityBenchmark:
    """Factual domain benchmark."""
    return DOMAIN_CONNECTIVITY_BENCHMARKS["factual"]


@pytest.fixture
def narrative_benchmark() -> ConnectivityBenchmark:
    """Narrative domain benchmark."""
    return DOMAIN_CONNECTIVITY_BENCHMARKS["narrative"]


# ============================================================================
# Test: Domain Connectivity Benchmarks
# ============================================================================


def test_domain_benchmarks_exist():
    """All 4 domain types have benchmarks defined."""
    assert "factual" in DOMAIN_CONNECTIVITY_BENCHMARKS
    assert "narrative" in DOMAIN_CONNECTIVITY_BENCHMARKS
    assert "technical" in DOMAIN_CONNECTIVITY_BENCHMARKS
    assert "academic" in DOMAIN_CONNECTIVITY_BENCHMARKS


def test_factual_benchmark(factual_benchmark):
    """Factual benchmark has expected values (HotpotQA, Wikipedia)."""
    assert factual_benchmark.domain_type == "factual"
    assert factual_benchmark.relations_per_entity_min == 0.3
    assert factual_benchmark.relations_per_entity_max == 0.8
    assert factual_benchmark.entities_per_community_min == 1.5
    assert factual_benchmark.entities_per_community_max == 3.0
    assert "sparse" in factual_benchmark.description.lower()


def test_narrative_benchmark(narrative_benchmark):
    """Narrative benchmark has higher connectivity than factual."""
    assert narrative_benchmark.domain_type == "narrative"
    assert narrative_benchmark.relations_per_entity_min == 1.5
    assert narrative_benchmark.relations_per_entity_max == 3.0
    assert narrative_benchmark.relations_per_entity_min > DOMAIN_CONNECTIVITY_BENCHMARKS["factual"].relations_per_entity_max


def test_benchmark_ranges_valid():
    """All benchmark ranges are valid (min < max)."""
    for domain_type, benchmark in DOMAIN_CONNECTIVITY_BENCHMARKS.items():
        assert benchmark.relations_per_entity_min < benchmark.relations_per_entity_max
        assert benchmark.entities_per_community_min < benchmark.entities_per_community_max


# ============================================================================
# Test: evaluate_connectivity()
# ============================================================================


@pytest.mark.asyncio
async def test_evaluate_connectivity_hotpotqa():
    """Evaluate connectivity for HotpotQA (factual domain) - within benchmark."""
    # Mock Neo4j response (Sprint 76 HotpotQA data)
    mock_result = [
        {
            "total_entities": 146,
            "total_relationships": 65,
            "total_communities": 92,
        }
    ]

    with patch("src.components.domain_training.domain_metrics.get_neo4j_client") as mock_get_neo4j:
        # Setup mock
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
        mock_get_neo4j.return_value = mock_neo4j

        # Execute
        metrics = await evaluate_connectivity("hotpotqa_large", "factual")

        # Assert
        assert metrics.namespace_id == "hotpotqa_large"
        assert metrics.domain_type == "factual"
        assert metrics.total_entities == 146
        assert metrics.total_relationships == 65
        assert metrics.total_communities == 92
        assert metrics.relations_per_entity == pytest.approx(0.445, rel=0.01)  # 65/146 = 0.445
        assert metrics.entities_per_community == pytest.approx(1.587, rel=0.01)  # 146/92 = 1.587
        assert metrics.benchmark_min == 0.3
        assert metrics.benchmark_max == 0.8
        assert metrics.within_benchmark is True
        assert metrics.benchmark_status == "within"
        assert len(metrics.recommendations) > 0
        assert any("✅" in rec for rec in metrics.recommendations)


@pytest.mark.asyncio
async def test_evaluate_connectivity_empty_namespace():
    """Evaluate connectivity for empty namespace (no entities)."""
    # Mock Neo4j response (empty namespace)
    mock_result = []

    with patch("src.components.domain_training.domain_metrics.get_neo4j_client") as mock_get_neo4j:
        # Setup mock
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
        mock_get_neo4j.return_value = mock_neo4j

        # Execute
        metrics = await evaluate_connectivity("empty_namespace", "factual")

        # Assert
        assert metrics.namespace_id == "empty_namespace"
        assert metrics.total_entities == 0
        assert metrics.total_relationships == 0
        assert metrics.relations_per_entity == 0.0
        assert metrics.within_benchmark is False
        assert metrics.benchmark_status == "below"
        assert any("No entities found" in rec for rec in metrics.recommendations)


@pytest.mark.asyncio
async def test_evaluate_connectivity_below_benchmark():
    """Evaluate connectivity below benchmark (sparse graph)."""
    # Mock Neo4j response (below benchmark)
    mock_result = [
        {
            "total_entities": 100,
            "total_relationships": 10,  # 0.1 relations/entity (below 0.3)
            "total_communities": 50,
        }
    ]

    with patch("src.components.domain_training.domain_metrics.get_neo4j_client") as mock_get_neo4j:
        # Setup mock
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
        mock_get_neo4j.return_value = mock_neo4j

        # Execute
        metrics = await evaluate_connectivity("sparse_namespace", "factual")

        # Assert
        assert metrics.relations_per_entity == 0.1
        assert metrics.within_benchmark is False
        assert metrics.benchmark_status == "below"
        assert any("below benchmark" in rec.lower() for rec in metrics.recommendations)
        assert any("improve" in rec.lower() or "consider" in rec.lower() for rec in metrics.recommendations)


@pytest.mark.asyncio
async def test_evaluate_connectivity_above_benchmark():
    """Evaluate connectivity above benchmark (over-extraction)."""
    # Mock Neo4j response (above benchmark)
    mock_result = [
        {
            "total_entities": 100,
            "total_relationships": 350,  # 3.5 relations/entity (above 0.8)
            "total_communities": 20,
        }
    ]

    with patch("src.components.domain_training.domain_metrics.get_neo4j_client") as mock_get_neo4j:
        # Setup mock
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
        mock_get_neo4j.return_value = mock_neo4j

        # Execute
        metrics = await evaluate_connectivity("dense_namespace", "factual")

        # Assert
        assert metrics.relations_per_entity == 3.5
        assert metrics.within_benchmark is False
        assert metrics.benchmark_status == "above"
        assert any("above benchmark" in rec.lower() for rec in metrics.recommendations)
        assert any("over-extraction" in rec.lower() or "tightening" in rec.lower() for rec in metrics.recommendations)


# ============================================================================
# Test: get_connectivity_score()
# ============================================================================


def test_connectivity_score_within_range(factual_benchmark):
    """Score = 1.0 when within benchmark range."""
    score = get_connectivity_score(0.5, factual_benchmark)  # Within [0.3, 0.8]
    assert score == 1.0


def test_connectivity_score_at_min(factual_benchmark):
    """Score = 1.0 at benchmark minimum."""
    score = get_connectivity_score(0.3, factual_benchmark)
    assert score == 1.0


def test_connectivity_score_at_max(factual_benchmark):
    """Score = 1.0 at benchmark maximum."""
    score = get_connectivity_score(0.8, factual_benchmark)
    assert score == 1.0


def test_connectivity_score_below_range(factual_benchmark):
    """Score penalized linearly when below range."""
    score = get_connectivity_score(0.15, factual_benchmark)  # 0.15 / 0.3 = 0.5
    assert score == pytest.approx(0.5, rel=0.01)


def test_connectivity_score_above_range(factual_benchmark):
    """Score penalized inversely when above range."""
    score = get_connectivity_score(1.6, factual_benchmark)  # 0.8 / 1.6 = 0.5
    assert score == pytest.approx(0.5, rel=0.01)


def test_connectivity_score_zero():
    """Score = 0 when relations_per_entity = 0."""
    factual_benchmark = DOMAIN_CONNECTIVITY_BENCHMARKS["factual"]
    score = get_connectivity_score(0.0, factual_benchmark)
    assert score == 0.0


# ============================================================================
# Test: Recommendations Engine
# ============================================================================


@pytest.mark.asyncio
async def test_recommendations_within_benchmark():
    """Recommendations for connectivity within benchmark."""
    # Mock Neo4j response (within benchmark)
    mock_result = [
        {
            "total_entities": 146,
            "total_relationships": 65,  # 0.45 within [0.3, 0.8]
            "total_communities": 92,
        }
    ]

    with patch("src.components.domain_training.domain_metrics.get_neo4j_client") as mock_get_neo4j:
        # Setup mock
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
        mock_get_neo4j.return_value = mock_neo4j

        # Execute
        metrics = await evaluate_connectivity("hotpotqa_large", "factual")

        # Assert
        assert metrics.within_benchmark is True
        assert any("✅" in rec for rec in metrics.recommendations)
        assert any("within benchmark" in rec.lower() for rec in metrics.recommendations)
        assert any("appropriate" in rec.lower() for rec in metrics.recommendations)


@pytest.mark.asyncio
async def test_recommendations_below_benchmark():
    """Recommendations for connectivity below benchmark."""
    # Mock Neo4j response (below benchmark)
    mock_result = [
        {
            "total_entities": 100,
            "total_relationships": 20,  # 0.2 below [0.3, 0.8]
            "total_communities": 50,
        }
    ]

    with patch("src.components.domain_training.domain_metrics.get_neo4j_client") as mock_get_neo4j:
        # Setup mock
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_read = AsyncMock(return_value=mock_result)
        mock_get_neo4j.return_value = mock_neo4j

        # Execute
        metrics = await evaluate_connectivity("sparse_namespace", "factual")

        # Assert
        assert metrics.within_benchmark is False
        assert any("⚠️" in rec for rec in metrics.recommendations)
        assert any("below benchmark" in rec.lower() for rec in metrics.recommendations)
        assert any("consider improving" in rec.lower() or "dspy" in rec.lower() for rec in metrics.recommendations)


# ============================================================================
# Test: Edge Cases
# ============================================================================


def test_benchmark_all_domains_have_examples():
    """All domain benchmarks have example use cases."""
    for domain_type, benchmark in DOMAIN_CONNECTIVITY_BENCHMARKS.items():
        assert len(benchmark.examples) > 0
        assert all(isinstance(example, str) for example in benchmark.examples)


def test_benchmark_ordering():
    """Benchmark ranges are ordered correctly across domains."""
    factual = DOMAIN_CONNECTIVITY_BENCHMARKS["factual"]
    narrative = DOMAIN_CONNECTIVITY_BENCHMARKS["narrative"]
    technical = DOMAIN_CONNECTIVITY_BENCHMARKS["technical"]
    academic = DOMAIN_CONNECTIVITY_BENCHMARKS["academic"]

    # Factual < Narrative in terms of connectivity
    assert factual.relations_per_entity_max < narrative.relations_per_entity_min

    # Academic has highest connectivity
    assert academic.relations_per_entity_max >= technical.relations_per_entity_max
    assert academic.relations_per_entity_max >= narrative.relations_per_entity_max
