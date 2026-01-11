"""Unit tests for DSPy Training Data Collector.

Sprint 85 Feature 85.7: DSPy Training Data Collection
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.components.domain_training.training_data_collector import (
    DSPyTrainingSample,
    TrainingDataCollector,
    get_training_data_collector,
)


class TestDSPyTrainingSample:
    """Test DSPyTrainingSample dataclass."""

    def test_to_dspy_entity_format(self) -> None:
        """Test conversion to DSPy entity format."""
        sample = DSPyTrainingSample(
            text="Machine learning uses neural networks.",
            entities=["Machine Learning", "Neural Networks"],
            relations=[{"subject": "Machine Learning", "predicate": "USES", "object": "Neural Networks"}],
        )

        result = sample.to_dspy_entity_format()

        assert result == {
            "text": "Machine learning uses neural networks.",
            "entities": ["Machine Learning", "Neural Networks"],
        }

    def test_to_dspy_relation_format(self) -> None:
        """Test conversion to DSPy relation format."""
        sample = DSPyTrainingSample(
            text="Machine learning uses neural networks.",
            entities=["Machine Learning", "Neural Networks"],
            relations=[{"subject": "Machine Learning", "predicate": "USES", "object": "Neural Networks"}],
        )

        result = sample.to_dspy_relation_format()

        assert result["text"] == "Machine learning uses neural networks."
        assert result["entities"] == ["Machine Learning", "Neural Networks"]
        assert len(result["relations"]) == 1
        assert result["relations"][0]["predicate"] == "USES"

    def test_to_full_dict(self) -> None:
        """Test conversion to full dictionary."""
        sample = DSPyTrainingSample(
            text="Test text",
            entities=["Entity1"],
            relations=[],
            doc_type="pdf_text",
            language="en",
            document_id="doc_001",
        )

        result = sample.to_full_dict()

        assert result["text"] == "Test text"
        assert result["doc_type"] == "pdf_text"
        assert result["language"] == "en"
        assert result["document_id"] == "doc_001"
        assert "timestamp" in result  # ISO format


class TestTrainingDataCollector:
    """Test TrainingDataCollector class."""

    @pytest.fixture
    def collector(self) -> TrainingDataCollector:
        """Create collector with low thresholds for testing."""
        return TrainingDataCollector(
            min_entity_confidence=0.5,
            min_relation_confidence=0.5,
            min_evidence_coverage=0.0,  # Don't require evidence
            min_entities=1,
            min_relations=1,
        )

    def test_collect_success(self, collector: TrainingDataCollector) -> None:
        """Test successful sample collection."""
        entities = [
            {"name": "Entity1", "type": "CONCEPT", "confidence": 0.8},
            {"name": "Entity2", "type": "TECHNOLOGY", "confidence": 0.9},
        ]
        relations = [
            {"source": "Entity1", "target": "Entity2", "type": "USES", "confidence": 0.7},
        ]
        metadata = {
            "document_id": "doc_001",
            "chunk_id": "chunk_001",
            "doc_type": "pdf_text",
            "language": "en",
        }

        sample = collector.collect(
            text="Entity1 uses Entity2",
            entities=entities,
            relations=relations,
            metadata=metadata,
        )

        assert sample is not None
        assert len(sample.entities) == 2
        assert len(sample.relations) == 1
        assert sample.document_id == "doc_001"

    def test_collect_rejected_too_few_entities(
        self, collector: TrainingDataCollector
    ) -> None:
        """Test rejection when too few entities."""
        collector.min_entities = 5  # Require 5 entities

        sample = collector.collect(
            text="Test",
            entities=[{"name": "Entity1", "confidence": 0.9}],
            relations=[{"source": "A", "target": "B", "confidence": 0.9}],
            metadata={},
        )

        assert sample is None
        assert collector.rejected_too_few_items > 0

    def test_collect_rejected_low_confidence(
        self, collector: TrainingDataCollector
    ) -> None:
        """Test rejection when confidence too low."""
        collector.min_entity_confidence = 0.9  # Require high confidence

        sample = collector.collect(
            text="Test",
            entities=[{"name": "E1", "confidence": 0.5}, {"name": "E2", "confidence": 0.5}],
            relations=[{"source": "E1", "target": "E2", "confidence": 0.5}],
            metadata={},
        )

        assert sample is None
        assert collector.rejected_low_confidence > 0

    def test_get_statistics(self, collector: TrainingDataCollector) -> None:
        """Test statistics tracking."""
        # Collect some samples
        for i in range(3):
            collector.collect(
                text=f"Text {i}",
                entities=[{"name": f"E{i}", "confidence": 0.9}, {"name": f"E{i}2", "confidence": 0.9}],
                relations=[{"source": f"E{i}", "target": f"E{i}2", "confidence": 0.9}],
                metadata={},
            )

        stats = collector.get_statistics()

        assert stats["total_samples"] == 3
        assert stats["total_candidates"] == 3
        assert stats["acceptance_rate"] == 1.0

    def test_get_stratification(self, collector: TrainingDataCollector) -> None:
        """Test stratification breakdown."""
        # Collect samples with different doc_types
        collector.collect(
            text="Text 1",
            entities=[{"name": "E1", "confidence": 0.9}, {"name": "E2", "confidence": 0.9}],
            relations=[{"source": "E1", "target": "E2", "confidence": 0.9}],
            metadata={"doc_type": "pdf_text", "language": "en"},
        )
        collector.collect(
            text="Text 2",
            entities=[{"name": "E3", "confidence": 0.9}, {"name": "E4", "confidence": 0.9}],
            relations=[{"source": "E3", "target": "E4", "confidence": 0.9}],
            metadata={"doc_type": "docx", "language": "de"},
        )

        strat = collector.get_stratification()

        assert strat["by_doc_type"]["pdf_text"] == 1
        assert strat["by_doc_type"]["docx"] == 1
        assert strat["by_language"]["en"] == 1
        assert strat["by_language"]["de"] == 1

    def test_export_to_jsonl(self, collector: TrainingDataCollector) -> None:
        """Test JSONL export."""
        # Collect a sample
        collector.collect(
            text="Test text",
            entities=[{"name": "E1", "confidence": 0.9}, {"name": "E2", "confidence": 0.9}],
            relations=[{"source": "E1", "target": "E2", "confidence": 0.9}],
            metadata={"doc_type": "test"},
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        try:
            result = collector.export_to_jsonl(path, format="entity")

            assert result["entity_samples"] == 1
            assert path.exists()

            # Read and verify content
            with open(path) as f:
                line = f.readline()
                data = json.loads(line)
                assert "text" in data
                assert "entities" in data

        finally:
            path.unlink()

    def test_export_full_samples(self, collector: TrainingDataCollector) -> None:
        """Test full samples export."""
        collector.collect(
            text="Test text",
            entities=[{"name": "E1", "confidence": 0.9}, {"name": "E2", "confidence": 0.9}],
            relations=[{"source": "E1", "target": "E2", "confidence": 0.9}],
            metadata={"doc_type": "test", "document_id": "doc_001"},
        )

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)

        try:
            count = collector.export_full_samples(path)

            assert count == 1
            assert path.exists()

            # Read and verify metadata is included
            with open(path) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["document_id"] == "doc_001"
                assert "timestamp" in data

        finally:
            path.unlink()

    def test_clear(self, collector: TrainingDataCollector) -> None:
        """Test clearing collector."""
        collector.collect(
            text="Test",
            entities=[{"name": "E1", "confidence": 0.9}, {"name": "E2", "confidence": 0.9}],
            relations=[{"source": "E1", "target": "E2", "confidence": 0.9}],
            metadata={},
        )

        assert len(collector.samples) == 1

        collector.clear()

        assert len(collector.samples) == 0
        assert collector.total_candidates == 0


class TestGetTrainingDataCollector:
    """Test singleton getter."""

    def test_singleton_behavior(self) -> None:
        """Test that singleton returns same instance."""
        # Reset singleton for test
        import src.components.domain_training.training_data_collector as module
        module._training_data_collector = None

        c1 = get_training_data_collector()
        c2 = get_training_data_collector()

        assert c1 is c2
