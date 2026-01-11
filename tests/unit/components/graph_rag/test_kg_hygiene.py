"""Unit tests for KG Hygiene Service.

Sprint 85 Feature 85.5: KG Hygiene & Deduplication
"""

import pytest

from src.components.graph_rag.kg_hygiene import (
    HygieneReport,
    HygieneViolation,
    KGHygieneService,
    VALID_RELATION_TYPES,
)
from src.core.models import GraphRelationship


class TestHygieneReport:
    """Test HygieneReport dataclass."""

    def test_default_values(self) -> None:
        """Test default report values."""
        report = HygieneReport()

        assert report.total_entities == 0
        assert report.total_relations == 0
        assert report.self_loops == 0
        assert report.is_healthy

    def test_is_healthy_with_issues(self) -> None:
        """Test is_healthy with various issues."""
        # Self-loops make it unhealthy
        report = HygieneReport(self_loops=1)
        assert not report.is_healthy

        # Orphan relations make it unhealthy
        report = HygieneReport(orphan_relations=1)
        assert not report.is_healthy

        # Invalid types make it unhealthy
        report = HygieneReport(invalid_types=1)
        assert not report.is_healthy

        # Missing evidence is OK (not in is_healthy check)
        report = HygieneReport(missing_evidence=10)
        assert report.is_healthy

    def test_health_score(self) -> None:
        """Test health score calculation."""
        # Perfect health
        report = HygieneReport(total_relations=100)
        assert report.health_score == 100.0

        # 10% issues
        report = HygieneReport(
            total_relations=100,
            self_loops=5,
            orphan_relations=3,
            invalid_types=2,
        )
        assert report.health_score == 90.0

        # Empty graph
        report = HygieneReport(total_relations=0)
        assert report.health_score == 100.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        report = HygieneReport(
            total_entities=100,
            total_relations=50,
            self_loops=2,
        )

        result = report.to_dict()

        assert result["total_entities"] == 100
        assert result["total_relations"] == 50
        assert result["self_loops"] == 2
        assert "is_healthy" in result
        assert "health_score" in result


class TestHygieneViolation:
    """Test HygieneViolation dataclass."""

    def test_create_violation(self) -> None:
        """Test creating a violation."""
        violation = HygieneViolation(
            rule="no_self_loops",
            entity_or_relation_id="entity_123",
            description="Self-loop detected",
            severity="error",
            auto_fixable=True,
        )

        assert violation.rule == "no_self_loops"
        assert violation.severity == "error"
        assert violation.auto_fixable


class TestKGHygieneService:
    """Test KGHygieneService class."""

    @pytest.fixture
    def service(self) -> KGHygieneService:
        """Create hygiene service instance."""
        return KGHygieneService()

    def test_validate_relation_valid(self, service: KGHygieneService) -> None:
        """Test validating a valid relation."""
        relation = {
            "source": "Entity1",
            "target": "Entity2",
            "type": "USES",
            "evidence_span": "Entity1 uses Entity2",
        }

        is_valid, reason = service.validate_relation(relation)

        assert is_valid
        assert reason == "valid"

    def test_validate_relation_self_loop(self, service: KGHygieneService) -> None:
        """Test detecting self-loop."""
        relation = {
            "source": "Entity1",
            "target": "Entity1",  # Same entity
            "type": "RELATES_TO",
        }

        is_valid, reason = service.validate_relation(relation)

        assert not is_valid
        assert "Self-loop" in reason

    def test_validate_relation_self_loop_case_insensitive(
        self, service: KGHygieneService
    ) -> None:
        """Test self-loop detection is case-insensitive."""
        relation = {
            "source": "Machine Learning",
            "target": "machine learning",  # Same when lowercased
            "type": "RELATES_TO",
        }

        is_valid, reason = service.validate_relation(relation)

        assert not is_valid
        assert "Self-loop" in reason

    def test_validate_relation_missing_evidence(
        self, service: KGHygieneService
    ) -> None:
        """Test detecting missing evidence when required."""
        relation = {
            "source": "Entity1",
            "target": "Entity2",
            "type": "USES",
            # No evidence_span
        }

        # When evidence is required
        is_valid, reason = service.validate_relation(relation, require_evidence=True)
        assert not is_valid
        assert "evidence" in reason.lower()

        # When evidence is not required
        is_valid, reason = service.validate_relation(relation, require_evidence=False)
        assert is_valid

    def test_validate_relation_with_graph_relationship(
        self, service: KGHygieneService
    ) -> None:
        """Test validating GraphRelationship object."""
        relation = GraphRelationship(
            id="rel_001",
            source="Entity1",
            target="Entity2",
            type="USES",
        )

        is_valid, reason = service.validate_relation(relation, require_evidence=False)

        assert is_valid


class TestValidRelationTypes:
    """Test valid relation types constant."""

    def test_standard_types_present(self) -> None:
        """Test that standard types are present."""
        assert "RELATES_TO" in VALID_RELATION_TYPES
        assert "USES" in VALID_RELATION_TYPES
        assert "CONTAINS" in VALID_RELATION_TYPES

    def test_causal_types_present(self) -> None:
        """Test that causal types are present."""
        assert "CAUSES" in VALID_RELATION_TYPES
        assert "LEADS_TO" in VALID_RELATION_TYPES
        assert "ENABLES" in VALID_RELATION_TYPES

    def test_organizational_types_present(self) -> None:
        """Test that organizational types are present."""
        assert "OWNS" in VALID_RELATION_TYPES
        assert "MANAGES" in VALID_RELATION_TYPES
        assert "LOCATED_IN" in VALID_RELATION_TYPES
