"""Unit tests for domain validation API endpoint.

Sprint 117 - Feature 117.7: Domain Validation (5 SP)

Tests cover:
- Successful validation
- Domain not found
- Database connection errors
- Response model validation
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@pytest.fixture
def mock_validator():
    """Mock domain validator."""
    with patch("src.api.v1.domain_training.get_domain_validator") as mock:
        validator = AsyncMock()
        mock.return_value = validator
        yield validator


class TestValidateDomainEndpoint:
    """Test POST /admin/domains/{name}/validate endpoint."""

    def test_validate_domain_success(self, mock_validator):
        """Test successful domain validation."""
        # Mock validation result
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "warning",
            "health_score": 72,
            "checks": [
                {
                    "name": "training_samples_count",
                    "status": "pass",
                    "message": "50 training samples (minimum: 20)",
                    "details": {"count": 50, "minimum": 20},
                },
                {
                    "name": "entity_type_coverage",
                    "status": "warning",
                    "message": "3/5 entity types have samples",
                    "details": {"covered": 3, "total": 5, "missing": ["Medication", "Dosage"]},
                },
                {
                    "name": "relation_type_coverage",
                    "status": "pass",
                    "message": "All relation types have samples",
                    "details": {"covered": 4, "total": 4},
                },
                {
                    "name": "mentioned_in_relations",
                    "status": "pass",
                    "message": "MENTIONED_IN relations present",
                    "details": {"count": 2847},
                },
                {
                    "name": "model_trained",
                    "status": "fail",
                    "message": "DSPy model not trained",
                    "details": {"last_trained": None, "status": "pending"},
                },
                {
                    "name": "confidence_calibration",
                    "status": "pass",
                    "message": "Confidence threshold calibrated",
                    "details": {"threshold": 0.75, "avg_confidence": 0.78},
                },
                {
                    "name": "recent_activity",
                    "status": "pass",
                    "message": "Active domain (10 docs, 50 entities in last 30 days)",
                    "details": {"recent_entities": 50, "recent_documents": 10},
                },
            ],
            "issues": [
                {
                    "severity": "warning",
                    "category": "coverage",
                    "message": "Entity types 'Medication', 'Dosage' have no training samples",
                    "recommendation": "Add training samples for missing entity types: Medication, Dosage",
                },
                {
                    "severity": "error",
                    "category": "model",
                    "message": "Domain model not trained",
                    "recommendation": "Run POST /api/v1/admin/domains/medical/train to optimize prompts",
                },
            ],
            "recommendations": [
                "Run POST /api/v1/admin/domains/medical/train to optimize prompts",
                "Add training samples for missing entity types: Medication, Dosage",
            ],
        }

        # Make request
        response = client.post("/api/v1/admin/domains/medical/validate")

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["domain_name"] == "medical"
        assert data["validation_status"] == "warning"
        assert data["health_score"] == 72
        assert len(data["checks"]) == 7
        assert len(data["issues"]) == 2
        assert len(data["recommendations"]) == 2

        # Verify checks structure
        training_check = data["checks"][0]
        assert training_check["name"] == "training_samples_count"
        assert training_check["status"] == "pass"
        assert "50 training samples" in training_check["message"]
        assert training_check["details"]["count"] == 50

        # Verify MENTIONED_IN check is present
        mentioned_in_check = next(
            (c for c in data["checks"] if c["name"] == "mentioned_in_relations"), None
        )
        assert mentioned_in_check is not None
        assert mentioned_in_check["status"] == "pass"
        assert mentioned_in_check["details"]["count"] == 2847

        # Verify issues structure
        coverage_issue = data["issues"][0]
        assert coverage_issue["severity"] == "warning"
        assert coverage_issue["category"] == "coverage"
        assert "Medication" in coverage_issue["message"]

        model_issue = data["issues"][1]
        assert model_issue["severity"] == "error"
        assert model_issue["category"] == "model"
        assert "not trained" in model_issue["message"]

        # Verify recommendations
        assert any("train" in rec.lower() for rec in data["recommendations"])

    def test_validate_domain_all_pass(self, mock_validator):
        """Test validation with all checks passing."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "pass",
            "health_score": 100,
            "checks": [
                {
                    "name": "training_samples_count",
                    "status": "pass",
                    "message": "100 training samples (minimum: 20)",
                    "details": {"count": 100, "minimum": 20},
                },
                {
                    "name": "entity_type_coverage",
                    "status": "pass",
                    "message": "All entity types have samples",
                    "details": {"covered": 5, "total": 5, "missing": []},
                },
                {
                    "name": "relation_type_coverage",
                    "status": "pass",
                    "message": "All relation types have samples",
                    "details": {"covered": 4, "total": 4, "missing": []},
                },
                {
                    "name": "mentioned_in_relations",
                    "status": "pass",
                    "message": "MENTIONED_IN relations present",
                    "details": {"count": 5000},
                },
                {
                    "name": "model_trained",
                    "status": "pass",
                    "message": "DSPy model trained and ready",
                    "details": {"last_trained": "2024-01-15T12:00:00", "status": "ready"},
                },
                {
                    "name": "confidence_calibration",
                    "status": "pass",
                    "message": "Confidence threshold calibrated",
                    "details": {"threshold": 0.75, "avg_confidence": 0.76},
                },
                {
                    "name": "recent_activity",
                    "status": "pass",
                    "message": "Active domain (20 docs, 100 entities in last 30 days)",
                    "details": {"recent_entities": 100, "recent_documents": 20},
                },
            ],
            "issues": [],
            "recommendations": [],
        }

        response = client.post("/api/v1/admin/domains/medical/validate")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["validation_status"] == "pass"
        assert data["health_score"] == 100
        assert len(data["issues"]) == 0
        assert len(data["recommendations"]) == 0

    def test_validate_domain_all_fail(self, mock_validator):
        """Test validation with all checks failing."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "empty_domain",
            "validation_status": "fail",
            "health_score": 0,
            "checks": [
                {
                    "name": "training_samples_count",
                    "status": "fail",
                    "message": "No training samples available",
                    "details": {"count": 0, "minimum": 20},
                },
                {
                    "name": "entity_type_coverage",
                    "status": "fail",
                    "message": "Only 0/5 entity types have samples",
                    "details": {"covered": 0, "total": 5, "missing": ["Person", "Org", "Loc", "Med", "Dose"]},
                },
                {
                    "name": "relation_type_coverage",
                    "status": "fail",
                    "message": "Only 0/4 relation types have samples",
                    "details": {"covered": 0, "total": 4, "missing": ["TREATS", "DIAGNOSES", "PRESCRIBES", "RELATED_TO"]},
                },
                {
                    "name": "mentioned_in_relations",
                    "status": "fail",
                    "message": "No MENTIONED_IN relations (provenance missing)",
                    "details": {"count": 0},
                },
                {
                    "name": "model_trained",
                    "status": "fail",
                    "message": "DSPy model not trained",
                    "details": {"last_trained": None, "status": "pending"},
                },
                {
                    "name": "confidence_calibration",
                    "status": "fail",
                    "message": "Unable to determine confidence calibration",
                    "details": {"threshold": None, "avg_confidence": None},
                },
                {
                    "name": "recent_activity",
                    "status": "fail",
                    "message": "No activity in last 30 days",
                    "details": {"recent_entities": 0, "recent_documents": 0},
                },
            ],
            "issues": [
                {
                    "severity": "error",
                    "category": "coverage",
                    "message": "Domain has insufficient training samples (0 < 20)",
                    "recommendation": "Add at least 20 more training samples",
                },
                {
                    "severity": "error",
                    "category": "provenance",
                    "message": "No MENTIONED_IN relations found (provenance missing)",
                    "recommendation": "Ensure entity extraction creates MENTIONED_IN links to source chunks",
                },
                {
                    "severity": "error",
                    "category": "model",
                    "message": "Domain model not trained",
                    "recommendation": "Run POST /api/v1/admin/domains/empty_domain/train to optimize prompts",
                },
            ],
            "recommendations": [
                "Add at least 20 more training samples",
                "Ensure entity extraction creates MENTIONED_IN links to source chunks",
                "Run POST /api/v1/admin/domains/empty_domain/train to optimize prompts",
            ],
        }

        response = client.post("/api/v1/admin/domains/empty_domain/validate")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["validation_status"] == "fail"
        assert data["health_score"] == 0
        assert len(data["issues"]) == 3
        assert all(issue["severity"] == "error" for issue in data["issues"])

    def test_validate_domain_not_found(self, mock_validator):
        """Test validation with non-existent domain."""
        mock_validator.validate_domain.side_effect = ValueError("Domain 'nonexistent' not found")

        response = client.post("/api/v1/admin/domains/nonexistent/validate")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_validate_domain_database_error(self, mock_validator):
        """Test validation with database connection error."""
        from src.core.exceptions import DatabaseConnectionError

        mock_validator.validate_domain.side_effect = DatabaseConnectionError(
            "Neo4j", "Connection failed"
        )

        response = client.post("/api/v1/admin/domains/medical/validate")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "database connection failed" in response.json()["detail"].lower()

    def test_validate_domain_unexpected_error(self, mock_validator):
        """Test validation with unexpected error."""
        mock_validator.validate_domain.side_effect = Exception("Unexpected error")

        response = client.post("/api/v1/admin/domains/medical/validate")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "validation failed" in response.json()["detail"].lower()

    def test_validate_domain_special_characters(self, mock_validator):
        """Test validation with domain name containing special characters."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "tech_docs_v2",
            "validation_status": "pass",
            "health_score": 95,
            "checks": [
                {
                    "name": "training_samples_count",
                    "status": "pass",
                    "message": "50 samples",
                    "details": {"count": 50},
                }
            ] * 7,  # 7 checks
            "issues": [],
            "recommendations": [],
        }

        response = client.post("/api/v1/admin/domains/tech_docs_v2/validate")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["domain_name"] == "tech_docs_v2"


class TestValidationResponseSchema:
    """Test validation response schema compliance."""

    def test_response_has_all_required_fields(self, mock_validator):
        """Test that response includes all required fields."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "pass",
            "health_score": 85,
            "checks": [
                {"name": "test", "status": "pass", "message": "OK", "details": {}}
            ],
            "issues": [],
            "recommendations": [],
        }

        response = client.post("/api/v1/admin/domains/medical/validate")
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            "domain_name",
            "validation_status",
            "health_score",
            "checks",
            "issues",
            "recommendations",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_check_structure(self, mock_validator):
        """Test that check objects have correct structure."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "pass",
            "health_score": 100,
            "checks": [
                {
                    "name": "training_samples_count",
                    "status": "pass",
                    "message": "50 training samples",
                    "details": {"count": 50, "minimum": 20},
                }
            ],
            "issues": [],
            "recommendations": [],
        }

        response = client.post("/api/v1/admin/domains/medical/validate")
        check = response.json()["checks"][0]

        assert "name" in check
        assert "status" in check
        assert "message" in check
        assert "details" in check
        assert isinstance(check["details"], dict)

    def test_issue_structure(self, mock_validator):
        """Test that issue objects have correct structure."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "warning",
            "health_score": 70,
            "checks": [],
            "issues": [
                {
                    "severity": "warning",
                    "category": "coverage",
                    "message": "Some issue",
                    "recommendation": "Fix it",
                }
            ],
            "recommendations": ["Fix it"],
        }

        response = client.post("/api/v1/admin/domains/medical/validate")
        issue = response.json()["issues"][0]

        assert "severity" in issue
        assert "category" in issue
        assert "message" in issue
        assert "recommendation" in issue

    def test_health_score_range(self, mock_validator):
        """Test that health score is within valid range (0-100)."""
        for score in [0, 50, 100]:
            mock_validator.validate_domain.return_value = {
                "domain_name": "medical",
                "validation_status": "pass",
                "health_score": score,
                "checks": [],
                "issues": [],
                "recommendations": [],
            }

            response = client.post("/api/v1/admin/domains/medical/validate")
            data = response.json()

            assert 0 <= data["health_score"] <= 100

    def test_validation_status_values(self, mock_validator):
        """Test that validation status is one of valid values."""
        for status_value in ["pass", "warning", "fail"]:
            mock_validator.validate_domain.return_value = {
                "domain_name": "medical",
                "validation_status": status_value,
                "health_score": 50,
                "checks": [],
                "issues": [],
                "recommendations": [],
            }

            response = client.post("/api/v1/admin/domains/medical/validate")
            data = response.json()

            assert data["validation_status"] in ["pass", "warning", "fail"]


class TestMentionedInCheck:
    """Test that MENTIONED_IN check is always included."""

    def test_mentioned_in_check_present(self, mock_validator):
        """Test that MENTIONED_IN check is always in the response."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "pass",
            "health_score": 100,
            "checks": [
                {
                    "name": "training_samples_count",
                    "status": "pass",
                    "message": "50 samples",
                    "details": {},
                },
                {
                    "name": "mentioned_in_relations",
                    "status": "pass",
                    "message": "MENTIONED_IN relations present",
                    "details": {"count": 1000},
                },
            ],
            "issues": [],
            "recommendations": [],
        }

        response = client.post("/api/v1/admin/domains/medical/validate")
        checks = response.json()["checks"]

        # Verify MENTIONED_IN check is present
        mentioned_in_check = next(
            (c for c in checks if c["name"] == "mentioned_in_relations"), None
        )
        assert mentioned_in_check is not None
        assert "count" in mentioned_in_check["details"]

    def test_mentioned_in_check_fail_creates_issue(self, mock_validator):
        """Test that failed MENTIONED_IN check creates provenance issue."""
        mock_validator.validate_domain.return_value = {
            "domain_name": "medical",
            "validation_status": "fail",
            "health_score": 50,
            "checks": [
                {
                    "name": "mentioned_in_relations",
                    "status": "fail",
                    "message": "No MENTIONED_IN relations (provenance missing)",
                    "details": {"count": 0},
                },
            ],
            "issues": [
                {
                    "severity": "error",
                    "category": "provenance",
                    "message": "No MENTIONED_IN relations found (provenance missing)",
                    "recommendation": "Ensure entity extraction creates MENTIONED_IN links to source chunks",
                }
            ],
            "recommendations": [
                "Ensure entity extraction creates MENTIONED_IN links to source chunks"
            ],
        }

        response = client.post("/api/v1/admin/domains/medical/validate")
        data = response.json()

        # Verify provenance issue exists
        provenance_issue = next(
            (i for i in data["issues"] if i["category"] == "provenance"), None
        )
        assert provenance_issue is not None
        assert provenance_issue["severity"] == "error"
        assert "MENTIONED_IN" in provenance_issue["message"]
