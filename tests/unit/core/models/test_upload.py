"""Unit tests for upload models.

Sprint 117 Feature 117.10: Domain Classification Display in Upload Dialog.
"""

import pytest
from pydantic import ValidationError

from src.core.models.upload import DomainClassificationResult, ExtractionSummary


class TestDomainClassificationResult:
    """Test suite for DomainClassificationResult model."""

    def test_valid_classification_result(self):
        """Test creating valid classification result."""
        result = DomainClassificationResult(
            domain_id="medical",
            domain_name="Medical Documents",
            confidence=0.94,
            classification_path="fast",
            latency_ms=42,
            model_used="C-LARA-SetFit-v2",
            matched_entity_types=["Disease", "Treatment", "Medication"],
            matched_intent="diagnosis_report",
            requires_review=False,
            alternatives=[],
        )

        assert result.domain_id == "medical"
        assert result.domain_name == "Medical Documents"
        assert result.confidence == 0.94
        assert result.classification_path == "fast"
        assert result.latency_ms == 42
        assert result.model_used == "C-LARA-SetFit-v2"
        assert len(result.matched_entity_types) == 3
        assert result.matched_intent == "diagnosis_report"
        assert result.requires_review is False
        assert len(result.alternatives) == 0

    def test_classification_with_alternatives(self):
        """Test classification result with alternative domains."""
        result = DomainClassificationResult(
            domain_id="legal",
            domain_name="Legal Documents",
            confidence=0.55,
            classification_path="fallback",
            latency_ms=150,
            model_used="Full-Pipeline",
            matched_entity_types=["Contract", "Party"],
            matched_intent=None,
            requires_review=True,
            alternatives=[
                {"domain": "financial", "confidence": 0.48},
                {"domain": "business", "confidence": 0.42},
            ],
        )

        assert result.confidence == 0.55
        assert result.requires_review is True
        assert len(result.alternatives) == 2
        assert result.alternatives[0]["domain"] == "financial"
        assert result.alternatives[0]["confidence"] == 0.48

    def test_confidence_validation_out_of_range(self):
        """Test confidence validation rejects values outside [0.0, 1.0]."""
        with pytest.raises(ValidationError) as exc_info:
            DomainClassificationResult(
                domain_id="test",
                domain_name="Test",
                confidence=1.5,  # Invalid: > 1.0
                classification_path="fast",
                latency_ms=50,
                model_used="Test-Model",
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("confidence",)
        assert "less than or equal to 1" in str(errors[0]["msg"]).lower()

    def test_negative_confidence_rejected(self):
        """Test negative confidence is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DomainClassificationResult(
                domain_id="test",
                domain_name="Test",
                confidence=-0.1,  # Invalid: < 0.0
                classification_path="fast",
                latency_ms=50,
                model_used="Test-Model",
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("confidence",)
        assert "greater than or equal to 0" in str(errors[0]["msg"]).lower()

    def test_negative_latency_rejected(self):
        """Test negative latency is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DomainClassificationResult(
                domain_id="test",
                domain_name="Test",
                confidence=0.8,
                classification_path="fast",
                latency_ms=-10,  # Invalid: < 0
                model_used="Test-Model",
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("latency_ms",)
        assert "greater than or equal to 0" in str(errors[0]["msg"]).lower()

    def test_default_fields(self):
        """Test default field values are applied correctly."""
        result = DomainClassificationResult(
            domain_id="general",
            domain_name="General Documents",
            confidence=0.75,
            classification_path="verified",
            latency_ms=80,
            model_used="Hybrid-Model",
        )

        # Default values should be applied
        assert result.matched_entity_types == []
        assert result.matched_intent is None
        assert result.requires_review is False
        assert result.alternatives == []


class TestExtractionSummary:
    """Test suite for ExtractionSummary model."""

    def test_valid_extraction_summary(self):
        """Test creating valid extraction summary."""
        summary = ExtractionSummary(
            entities_count=47,
            relations_count=23,
            chunks_count=12,
            mentioned_in_count=47,
        )

        assert summary.entities_count == 47
        assert summary.relations_count == 23
        assert summary.chunks_count == 12
        assert summary.mentioned_in_count == 47

    def test_zero_counts_valid(self):
        """Test extraction summary with all zero counts is valid."""
        summary = ExtractionSummary(
            entities_count=0,
            relations_count=0,
            chunks_count=0,
            mentioned_in_count=0,
        )

        assert summary.entities_count == 0
        assert summary.relations_count == 0
        assert summary.chunks_count == 0
        assert summary.mentioned_in_count == 0

    def test_negative_entities_count_rejected(self):
        """Test negative entities_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionSummary(
                entities_count=-5,  # Invalid: < 0
                relations_count=10,
                chunks_count=5,
                mentioned_in_count=15,
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("entities_count",)
        assert "greater than or equal to 0" in str(errors[0]["msg"]).lower()

    def test_negative_relations_count_rejected(self):
        """Test negative relations_count is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionSummary(
                entities_count=10,
                relations_count=-3,  # Invalid: < 0
                chunks_count=5,
                mentioned_in_count=15,
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert errors[0]["loc"] == ("relations_count",)

    def test_large_counts_valid(self):
        """Test extraction summary with large counts is valid."""
        summary = ExtractionSummary(
            entities_count=10000,
            relations_count=50000,
            chunks_count=1000,
            mentioned_in_count=20000,
        )

        assert summary.entities_count == 10000
        assert summary.relations_count == 50000
        assert summary.chunks_count == 1000
        assert summary.mentioned_in_count == 20000

    def test_mentioned_in_matches_entities(self):
        """Test mentioned_in_count typically matches entities_count."""
        # This is a business logic test - MENTIONED_IN relations link entities to chunks
        summary = ExtractionSummary(
            entities_count=100,
            relations_count=50,
            chunks_count=20,
            mentioned_in_count=100,  # Should match entities_count
        )

        # In typical extraction, each entity has one MENTIONED_IN relation
        assert summary.mentioned_in_count == summary.entities_count
