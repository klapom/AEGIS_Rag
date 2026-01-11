"""Unit tests for ExtractionMetrics.

Sprint 85 Feature 85.6: Extraction Metrics (Log + LangGraph State)
"""

import pytest

from src.components.graph_rag.extraction_metrics import (
    ExtractionMetrics,
    create_metrics_from_extraction,
    merge_extraction_metrics,
)


class TestExtractionMetrics:
    """Test ExtractionMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default metric values."""
        metrics = ExtractionMetrics()

        assert metrics.entities_total == 0
        assert metrics.relations_total == 0
        assert metrics.relation_ratio == 0.0
        assert metrics.extraction_method == "unknown"

    def test_calculate_derived_metrics(self) -> None:
        """Test derived metrics calculation."""
        metrics = ExtractionMetrics(
            entities_total=10,
            relations_total=15,
            relation_types={"RELATES_TO": 5, "USES": 10},
        )

        metrics.calculate_derived_metrics()

        assert metrics.relation_ratio == 1.5  # 15 / 10
        assert metrics.typed_coverage == 2 / 3  # 10 typed / 15 total

    def test_calculate_derived_metrics_zero_entities(self) -> None:
        """Test derived metrics with zero entities."""
        metrics = ExtractionMetrics(
            entities_total=0,
            relations_total=5,
        )

        metrics.calculate_derived_metrics()

        assert metrics.relation_ratio == 0.0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        metrics = ExtractionMetrics(
            entities_total=10,
            relations_total=15,
            extraction_method="llm_cascade",
        )

        result = metrics.to_dict()

        assert isinstance(result, dict)
        assert result["entities_total"] == 10
        assert result["relations_total"] == 15
        assert result["extraction_method"] == "llm_cascade"

    def test_to_log_dict(self) -> None:
        """Test conversion to logging dictionary."""
        metrics = ExtractionMetrics(
            entities_total=10,
            relations_total=15,
            entity_types={"PERSON": 5, "ORGANIZATION": 5},
            relation_types={"USES": 10, "RELATES_TO": 5},
        )
        metrics.calculate_derived_metrics()

        result = metrics.to_log_dict()

        assert "top_entity_types" in result
        assert "top_relation_types" in result
        assert "relation_ratio" in result


class TestCreateMetricsFromExtraction:
    """Test create_metrics_from_extraction helper."""

    def test_create_from_entity_list(self) -> None:
        """Test creating metrics from entity list."""
        entities = [
            {"name": "Entity1", "type": "PERSON", "confidence": 0.9},
            {"name": "Entity2", "type": "ORGANIZATION", "confidence": 0.8},
        ]
        relations = [
            {"source": "Entity1", "target": "Entity2", "type": "WORKS_FOR"},
        ]

        metrics = create_metrics_from_extraction(
            entities=entities,
            relations=relations,
            llm_count=2,
            extraction_method="llm_cascade",
        )

        assert metrics.entities_total == 2
        assert metrics.relations_total == 1
        assert metrics.relation_ratio == 0.5
        assert metrics.extraction_method == "llm_cascade"
        assert "PERSON" in metrics.entity_types
        assert "ORGANIZATION" in metrics.entity_types

    def test_create_with_duplicates(self) -> None:
        """Test duplication rate calculation."""
        entities = [{"name": "Entity1", "type": "PERSON"}]

        metrics = create_metrics_from_extraction(
            entities=entities,
            relations=[],
            duplicates_removed=3,  # 3 duplicates removed
        )

        # 1 final + 3 removed = 4 total
        # duplication rate = 3/4 = 0.75
        assert metrics.duplication_rate == 0.75


class TestMergeExtractionMetrics:
    """Test merge_extraction_metrics function."""

    def test_merge_with_none(self) -> None:
        """Test merging with None existing metrics."""
        new_metrics = ExtractionMetrics(
            entities_total=10,
            relations_total=5,
        )

        result = merge_extraction_metrics(None, new_metrics)

        assert result.entities_total == 10
        assert result.relations_total == 5

    def test_merge_two_metrics(self) -> None:
        """Test merging two metrics objects."""
        existing = ExtractionMetrics(
            entities_total=10,
            relations_total=5,
            entity_types={"PERSON": 5, "ORGANIZATION": 5},
        )
        new = ExtractionMetrics(
            entities_total=8,
            relations_total=12,
            entity_types={"PERSON": 3, "LOCATION": 5},
        )

        result = merge_extraction_metrics(existing, new)

        assert result.entities_total == 18  # 10 + 8
        assert result.relations_total == 17  # 5 + 12
        assert result.entity_types["PERSON"] == 8  # 5 + 3
        assert result.entity_types["ORGANIZATION"] == 5
        assert result.entity_types["LOCATION"] == 5

    def test_merge_languages(self) -> None:
        """Test language list merging (unique values)."""
        existing = ExtractionMetrics(languages_detected=["en", "de"])
        new = ExtractionMetrics(languages_detected=["de", "fr"])

        result = merge_extraction_metrics(existing, new)

        assert set(result.languages_detected) == {"en", "de", "fr"}
