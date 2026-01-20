"""Unit tests for domain validation service.

Sprint 117 - Feature 117.7: Domain Validation (5 SP)

Tests cover:
- All 7 validation checks
- Health score calculation
- Issue generation
- Recommendation generation
- Error handling
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.domain_training.domain_validator import (
    DomainValidator,
    IssueCategory,
    IssueSeverity,
    ValidationCheck,
    ValidationIssue,
    ValidationStatus,
    get_domain_validator,
)
from src.core.exceptions import DatabaseConnectionError


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    with patch("src.components.domain_training.domain_validator.get_neo4j_client") as mock:
        client = MagicMock()
        client.execute_read = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_domain_repo():
    """Mock domain repository."""
    with patch("src.components.domain_training.domain_validator.get_domain_repository") as mock:
        repo = MagicMock()
        repo.get_domain = AsyncMock()
        mock.return_value = repo
        yield repo


@pytest.fixture
def validator(mock_neo4j_client, mock_domain_repo):
    """Create domain validator instance."""
    return DomainValidator()


@pytest.fixture
def sample_domain():
    """Sample domain configuration."""
    return {
        "id": "test-domain-id",
        "name": "medical",
        "description": "Medical domain for healthcare documents",
        "llm_model": "qwen3:32b",
        "training_samples": 50,
        "status": "ready",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "trained_at": datetime.utcnow().isoformat(),
    }


class TestValidationCheck:
    """Test ValidationCheck class."""

    def test_validation_check_creation(self):
        """Test creating a validation check."""
        check = ValidationCheck(
            name="test_check",
            status=ValidationStatus.PASS,
            message="Test passed",
            details={"count": 10},
        )

        assert check.name == "test_check"
        assert check.status == ValidationStatus.PASS
        assert check.message == "Test passed"
        assert check.details == {"count": 10}

    def test_validation_check_to_dict(self):
        """Test converting validation check to dict."""
        check = ValidationCheck(
            name="test_check",
            status=ValidationStatus.WARNING,
            message="Warning message",
            details={"value": 5},
        )

        result = check.to_dict()

        assert result == {
            "name": "test_check",
            "status": "warning",
            "message": "Warning message",
            "details": {"value": 5},
        }

    def test_validation_check_score_pass(self):
        """Test score calculation for pass status."""
        check = ValidationCheck(
            name="test", status=ValidationStatus.PASS, message="", details={}
        )
        assert check.score() == 100

    def test_validation_check_score_warning(self):
        """Test score calculation for warning status."""
        check = ValidationCheck(
            name="test", status=ValidationStatus.WARNING, message="", details={}
        )
        assert check.score() == 50

    def test_validation_check_score_fail(self):
        """Test score calculation for fail status."""
        check = ValidationCheck(
            name="test", status=ValidationStatus.FAIL, message="", details={}
        )
        assert check.score() == 0


class TestValidationIssue:
    """Test ValidationIssue class."""

    def test_validation_issue_creation(self):
        """Test creating a validation issue."""
        issue = ValidationIssue(
            severity=IssueSeverity.ERROR,
            category=IssueCategory.COVERAGE,
            message="Coverage issue",
            recommendation="Add more samples",
        )

        assert issue.severity == IssueSeverity.ERROR
        assert issue.category == IssueCategory.COVERAGE
        assert issue.message == "Coverage issue"
        assert issue.recommendation == "Add more samples"

    def test_validation_issue_to_dict(self):
        """Test converting validation issue to dict."""
        issue = ValidationIssue(
            severity=IssueSeverity.WARNING,
            category=IssueCategory.MODEL,
            message="Model warning",
            recommendation="Train model",
        )

        result = issue.to_dict()

        assert result == {
            "severity": "warning",
            "category": "model",
            "message": "Model warning",
            "recommendation": "Train model",
        }


class TestTrainingSamplesCountCheck:
    """Test training samples count validation check."""

    @pytest.mark.asyncio
    async def test_training_samples_count_pass(self, validator, sample_domain):
        """Test training samples count check with sufficient samples."""
        sample_domain["training_samples"] = 50

        check = await validator._check_training_samples_count("medical", sample_domain)

        assert check.name == "training_samples_count"
        assert check.status == ValidationStatus.PASS
        assert "50 training samples" in check.message
        assert check.details["count"] == 50
        assert check.details["minimum"] == 20

    @pytest.mark.asyncio
    async def test_training_samples_count_warning(self, validator, sample_domain):
        """Test training samples count check with insufficient samples."""
        sample_domain["training_samples"] = 10

        check = await validator._check_training_samples_count("medical", sample_domain)

        assert check.name == "training_samples_count"
        assert check.status == ValidationStatus.WARNING
        assert "Only 10 training samples" in check.message
        assert check.details["count"] == 10

    @pytest.mark.asyncio
    async def test_training_samples_count_fail(self, validator, sample_domain):
        """Test training samples count check with no samples."""
        sample_domain["training_samples"] = 0

        check = await validator._check_training_samples_count("medical", sample_domain)

        assert check.name == "training_samples_count"
        assert check.status == ValidationStatus.FAIL
        assert "No training samples" in check.message
        assert check.details["count"] == 0


class TestEntityTypeCoverageCheck:
    """Test entity type coverage validation check."""

    @pytest.mark.asyncio
    async def test_entity_type_coverage_pass(self, validator, mock_neo4j_client):
        """Test entity type coverage check with full coverage."""
        entity_types = ["Person", "Organization", "Location"]
        mock_neo4j_client.execute_read.return_value = [
            {
                "all_entity_types": json.dumps(entity_types),
                "covered_entity_types": entity_types,
            }
        ]

        check = await validator._check_entity_type_coverage("medical", {})

        assert check.name == "entity_type_coverage"
        assert check.status == ValidationStatus.PASS
        assert "All entity types have samples" in check.message
        assert check.details["covered"] == 3
        assert check.details["total"] == 3
        assert check.details["missing"] == []

    @pytest.mark.asyncio
    async def test_entity_type_coverage_warning(self, validator, mock_neo4j_client):
        """Test entity type coverage check with partial coverage."""
        entity_types = ["Person", "Organization", "Location", "Medication", "Dosage"]
        covered_types = ["Person", "Organization", "Location", "Medication"]
        mock_neo4j_client.execute_read.return_value = [
            {
                "all_entity_types": json.dumps(entity_types),
                "covered_entity_types": covered_types,
            }
        ]

        check = await validator._check_entity_type_coverage("medical", {})

        assert check.name == "entity_type_coverage"
        assert check.status == ValidationStatus.WARNING
        assert "4/5 entity types have samples" in check.message
        assert check.details["covered"] == 4
        assert check.details["total"] == 5
        assert check.details["missing"] == ["Dosage"]

    @pytest.mark.asyncio
    async def test_entity_type_coverage_fail(self, validator, mock_neo4j_client):
        """Test entity type coverage check with low coverage."""
        entity_types = ["Person", "Organization", "Location", "Medication", "Dosage"]
        covered_types = ["Person"]
        mock_neo4j_client.execute_read.return_value = [
            {
                "all_entity_types": json.dumps(entity_types),
                "covered_entity_types": covered_types,
            }
        ]

        check = await validator._check_entity_type_coverage("medical", {})

        assert check.name == "entity_type_coverage"
        assert check.status == ValidationStatus.FAIL
        assert "Only 1/5 entity types have samples" in check.message
        assert len(check.details["missing"]) == 4


class TestRelationTypeCoverageCheck:
    """Test relation type coverage validation check."""

    @pytest.mark.asyncio
    async def test_relation_type_coverage_pass(self, validator, mock_neo4j_client):
        """Test relation type coverage check with full coverage."""
        relation_types = ["TREATS", "DIAGNOSED_WITH", "PRESCRIBES"]
        mock_neo4j_client.execute_read.return_value = [
            {
                "all_relation_types": json.dumps(relation_types),
                "covered_relation_types": relation_types,
            }
        ]

        check = await validator._check_relation_type_coverage("medical", {})

        assert check.name == "relation_type_coverage"
        assert check.status == ValidationStatus.PASS
        assert "All relation types have samples" in check.message
        assert check.details["covered"] == 3
        assert check.details["total"] == 3


class TestMentionedInRelationsCheck:
    """Test MENTIONED_IN relations validation check."""

    @pytest.mark.asyncio
    async def test_mentioned_in_relations_pass(self, validator, mock_neo4j_client):
        """Test MENTIONED_IN check with relations present."""
        mock_neo4j_client.execute_read.return_value = [{"mentioned_in_count": 2847}]

        check = await validator._check_mentioned_in_relations("medical")

        assert check.name == "mentioned_in_relations"
        assert check.status == ValidationStatus.PASS
        assert "MENTIONED_IN relations present" in check.message
        assert check.details["count"] == 2847

    @pytest.mark.asyncio
    async def test_mentioned_in_relations_fail(self, validator, mock_neo4j_client):
        """Test MENTIONED_IN check with no relations."""
        mock_neo4j_client.execute_read.return_value = [{"mentioned_in_count": 0}]

        check = await validator._check_mentioned_in_relations("medical")

        assert check.name == "mentioned_in_relations"
        assert check.status == ValidationStatus.FAIL
        assert "No MENTIONED_IN relations" in check.message
        assert "provenance missing" in check.message
        assert check.details["count"] == 0


class TestModelTrainedCheck:
    """Test model training status validation check."""

    @pytest.mark.asyncio
    async def test_model_trained_pass(self, validator, sample_domain):
        """Test model trained check with trained model."""
        sample_domain["status"] = "ready"
        sample_domain["trained_at"] = datetime.utcnow().isoformat()

        check = await validator._check_model_trained("medical", sample_domain)

        assert check.name == "model_trained"
        assert check.status == ValidationStatus.PASS
        assert "DSPy model trained and ready" in check.message
        assert check.details["status"] == "ready"

    @pytest.mark.asyncio
    async def test_model_trained_warning(self, validator, sample_domain):
        """Test model trained check with training in progress."""
        sample_domain["status"] = "training"
        sample_domain["trained_at"] = None

        check = await validator._check_model_trained("medical", sample_domain)

        assert check.name == "model_trained"
        assert check.status == ValidationStatus.WARNING
        assert "training in progress" in check.message

    @pytest.mark.asyncio
    async def test_model_trained_fail(self, validator, sample_domain):
        """Test model trained check with untrained model."""
        sample_domain["status"] = "pending"
        sample_domain["trained_at"] = None

        check = await validator._check_model_trained("medical", sample_domain)

        assert check.name == "model_trained"
        assert check.status == ValidationStatus.FAIL
        assert "not trained" in check.message


class TestConfidenceCalibrationCheck:
    """Test confidence calibration validation check."""

    @pytest.mark.asyncio
    async def test_confidence_calibration_pass(self, validator, mock_neo4j_client):
        """Test confidence calibration check with calibrated threshold."""
        mock_neo4j_client.execute_read.return_value = [
            {"threshold": 0.75, "avg_confidence": 0.78, "entity_count": 100}
        ]

        check = await validator._check_confidence_calibration("medical", {})

        assert check.name == "confidence_calibration"
        assert check.status == ValidationStatus.PASS
        assert "Confidence threshold calibrated" in check.message
        assert check.details["threshold"] == 0.75

    @pytest.mark.asyncio
    async def test_confidence_calibration_warning(self, validator, mock_neo4j_client):
        """Test confidence calibration check with misaligned threshold."""
        mock_neo4j_client.execute_read.return_value = [
            {"threshold": 0.5, "avg_confidence": 0.85, "entity_count": 100}
        ]

        check = await validator._check_confidence_calibration("medical", {})

        assert check.name == "confidence_calibration"
        assert check.status == ValidationStatus.WARNING
        assert "may need calibration" in check.message


class TestRecentActivityCheck:
    """Test recent activity validation check."""

    @pytest.mark.asyncio
    async def test_recent_activity_pass(self, validator, mock_neo4j_client):
        """Test recent activity check with recent activity."""
        mock_neo4j_client.execute_read.return_value = [
            {
                "recent_entities": 50,
                "recent_documents": 10,
                "last_updated": datetime.utcnow().isoformat(),
            }
        ]

        check = await validator._check_recent_activity("medical")

        assert check.name == "recent_activity"
        assert check.status == ValidationStatus.PASS
        assert "Active domain" in check.message
        assert check.details["recent_entities"] == 50
        assert check.details["recent_documents"] == 10

    @pytest.mark.asyncio
    async def test_recent_activity_warning(self, validator, mock_neo4j_client):
        """Test recent activity check with no recent activity."""
        old_date = (datetime.utcnow() - timedelta(days=60)).isoformat()
        mock_neo4j_client.execute_read.return_value = [
            {"recent_entities": 0, "recent_documents": 0, "last_updated": old_date}
        ]

        check = await validator._check_recent_activity("medical")

        assert check.name == "recent_activity"
        assert check.status == ValidationStatus.WARNING
        assert "No activity" in check.message


class TestHealthScoreCalculation:
    """Test health score calculation."""

    def test_health_score_all_pass(self, validator):
        """Test health score with all checks passing."""
        checks = [
            ValidationCheck("check1", ValidationStatus.PASS, "", {}),
            ValidationCheck("check2", ValidationStatus.PASS, "", {}),
            ValidationCheck("check3", ValidationStatus.PASS, "", {}),
        ]

        score = validator._calculate_health_score(checks)

        assert score == 100

    def test_health_score_mixed(self, validator):
        """Test health score with mixed check results."""
        checks = [
            ValidationCheck("check1", ValidationStatus.PASS, "", {}),  # 100
            ValidationCheck("check2", ValidationStatus.WARNING, "", {}),  # 50
            ValidationCheck("check3", ValidationStatus.FAIL, "", {}),  # 0
        ]

        score = validator._calculate_health_score(checks)

        assert score == 50  # (100 + 50 + 0) // 3

    def test_health_score_all_fail(self, validator):
        """Test health score with all checks failing."""
        checks = [
            ValidationCheck("check1", ValidationStatus.FAIL, "", {}),
            ValidationCheck("check2", ValidationStatus.FAIL, "", {}),
        ]

        score = validator._calculate_health_score(checks)

        assert score == 0

    def test_health_score_empty(self, validator):
        """Test health score with no checks."""
        score = validator._calculate_health_score([])
        assert score == 0


class TestIssueGeneration:
    """Test issue generation from validation checks."""

    def test_generate_issues_training_samples(self, validator):
        """Test issue generation for insufficient training samples."""
        checks = [
            ValidationCheck(
                "training_samples_count",
                ValidationStatus.FAIL,
                "Insufficient samples",
                {"count": 5},
            )
        ]

        issues = validator._generate_issues(checks, {"name": "medical"})

        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.ERROR
        assert issues[0].category == IssueCategory.COVERAGE
        assert "insufficient training samples" in issues[0].message.lower()

    def test_generate_issues_entity_coverage(self, validator):
        """Test issue generation for entity type coverage."""
        checks = [
            ValidationCheck(
                "entity_type_coverage",
                ValidationStatus.WARNING,
                "Missing entity types",
                {"covered": 3, "total": 5, "missing": ["Medication", "Dosage"]},
            )
        ]

        issues = validator._generate_issues(checks, {"name": "medical"})

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.COVERAGE
        assert "Medication" in issues[0].message
        assert "Dosage" in issues[0].message

    def test_generate_issues_mentioned_in(self, validator):
        """Test issue generation for missing MENTIONED_IN relations."""
        checks = [
            ValidationCheck(
                "mentioned_in_relations",
                ValidationStatus.FAIL,
                "No MENTIONED_IN",
                {"count": 0},
            )
        ]

        issues = validator._generate_issues(checks, {"name": "medical"})

        assert len(issues) == 1
        assert issues[0].category == IssueCategory.PROVENANCE
        assert "MENTIONED_IN" in issues[0].message

    def test_generate_issues_no_issues_on_pass(self, validator):
        """Test that no issues are generated for passing checks."""
        checks = [
            ValidationCheck("check1", ValidationStatus.PASS, "All good", {}),
            ValidationCheck("check2", ValidationStatus.PASS, "All good", {}),
        ]

        issues = validator._generate_issues(checks, {"name": "medical"})

        assert len(issues) == 0


class TestRecommendationGeneration:
    """Test recommendation generation."""

    def test_generate_recommendations_sorted_by_severity(self, validator):
        """Test that recommendations are sorted by severity."""
        issues = [
            ValidationIssue(
                IssueSeverity.WARNING, IssueCategory.ACTIVITY, "Warning", "Fix warning"
            ),
            ValidationIssue(IssueSeverity.ERROR, IssueCategory.MODEL, "Error", "Fix error"),
            ValidationIssue(IssueSeverity.INFO, IssueCategory.COVERAGE, "Info", "Fix info"),
        ]

        recommendations = validator._generate_recommendations(issues)

        # Error should come first
        assert recommendations[0] == "Fix error"
        assert recommendations[1] == "Fix warning"
        assert recommendations[2] == "Fix info"


class TestValidateDomain:
    """Test full domain validation."""

    @pytest.mark.asyncio
    async def test_validate_domain_success(
        self, validator, mock_domain_repo, mock_neo4j_client, sample_domain
    ):
        """Test successful domain validation."""
        # Mock domain repository
        mock_domain_repo.get_domain.return_value = sample_domain

        # Mock all Neo4j queries
        mock_neo4j_client.execute_read.side_effect = [
            # Entity type coverage
            [{"all_entity_types": json.dumps(["Person"]), "covered_entity_types": ["Person"]}],
            # Relation type coverage
            [{"all_relation_types": json.dumps(["TREATS"]), "covered_relation_types": ["TREATS"]}],
            # MENTIONED_IN relations
            [{"mentioned_in_count": 100}],
            # Confidence calibration
            [{"threshold": 0.75, "avg_confidence": 0.78, "entity_count": 50}],
            # Recent activity
            [{"recent_entities": 10, "recent_documents": 5, "last_updated": datetime.utcnow().isoformat()}],
        ]

        result = await validator.validate_domain("medical")

        assert result["domain_name"] == "medical"
        assert result["validation_status"] in ["pass", "warning", "fail"]
        assert 0 <= result["health_score"] <= 100
        assert len(result["checks"]) == 7
        assert isinstance(result["issues"], list)
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_validate_domain_not_found(self, validator, mock_domain_repo):
        """Test validation with non-existent domain."""
        mock_domain_repo.get_domain.return_value = None

        with pytest.raises(ValueError, match="Domain 'nonexistent' not found"):
            await validator.validate_domain("nonexistent")

    @pytest.mark.asyncio
    async def test_validate_domain_database_error(
        self, validator, mock_domain_repo, mock_neo4j_client
    ):
        """Test validation with database connection error.

        Note: validate_domain has @retry decorator, so after MAX_RETRY_ATTEMPTS
        it raises tenacity.RetryError wrapping the original DatabaseConnectionError.
        """
        from tenacity import RetryError

        mock_domain_repo.get_domain.side_effect = DatabaseConnectionError("Neo4j", "Connection failed")

        # Expect RetryError after retry exhaustion (3 attempts)
        with pytest.raises(RetryError):
            await validator.validate_domain("medical")


class TestDetermineOverallStatus:
    """Test overall validation status determination."""

    def test_determine_overall_status_pass(self, validator):
        """Test overall status with all checks passing."""
        checks = [
            ValidationCheck("check1", ValidationStatus.PASS, "", {}),
            ValidationCheck("check2", ValidationStatus.PASS, "", {}),
        ]

        status = validator._determine_overall_status(checks)

        assert status == ValidationStatus.PASS

    def test_determine_overall_status_warning(self, validator):
        """Test overall status with warnings."""
        checks = [
            ValidationCheck("check1", ValidationStatus.PASS, "", {}),
            ValidationCheck("check2", ValidationStatus.WARNING, "", {}),
        ]

        status = validator._determine_overall_status(checks)

        assert status == ValidationStatus.WARNING

    def test_determine_overall_status_fail(self, validator):
        """Test overall status with failures."""
        checks = [
            ValidationCheck("check1", ValidationStatus.PASS, "", {}),
            ValidationCheck("check2", ValidationStatus.WARNING, "", {}),
            ValidationCheck("check3", ValidationStatus.FAIL, "", {}),
        ]

        status = validator._determine_overall_status(checks)

        assert status == ValidationStatus.FAIL


class TestGetDomainValidator:
    """Test singleton pattern for domain validator."""

    def test_get_domain_validator_singleton(self):
        """Test that get_domain_validator returns singleton instance."""
        validator1 = get_domain_validator()
        validator2 = get_domain_validator()

        assert validator1 is validator2
