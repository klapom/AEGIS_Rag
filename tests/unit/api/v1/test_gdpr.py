"""Unit tests for GDPR API endpoints.

Sprint 99 Feature 99.3: GDPR & Compliance APIs (12 SP)
Target Coverage: >80%

Test Coverage:
    - list_consents: Pagination, filtering by user/purpose/legal_basis/status
    - create_consent: Validation, expiration calculation
    - create_data_subject_request: Request types, processing log
    - get_processing_activities: Time range filtering
    - get/update_pii_settings: Settings management
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.gdpr_models import (
    ConsentStatusEnum,
    DataCategoryEnum,
    LegalBasisEnum,
    RequestStatusEnum,
    RequestTypeEnum,
)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_consent_store():
    """Mock consent store."""
    with patch("src.api.v1.gdpr.get_consent_store") as mock:
        from src.governance.gdpr.storage import ConsentStore

        store = ConsentStore()
        mock.return_value = store
        yield store


@pytest.fixture
def mock_processing_log():
    """Mock processing log."""
    with patch("src.api.v1.gdpr.get_processing_log") as mock:
        from src.governance.gdpr.storage import ProcessingLog

        log = ProcessingLog()
        mock.return_value = log
        yield log


class TestListConsents:
    """Tests for GET /api/v1/gdpr/consents."""

    @pytest.mark.asyncio
    async def test_list_consents_empty(self, client, mock_consent_store):
        """Test listing consents when store is empty."""
        response = client.get("/api/v1/gdpr/consents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_consents_with_data(self, client, mock_consent_store):
        """Test listing consents with data."""
        # Add test consent
        from src.governance.gdpr.compliance import (
            ConsentRecord,
            DataCategory,
            LegalBasis,
        )

        consent = ConsentRecord(
            data_subject_id="user123",
            purpose="Marketing",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.CONTACT, DataCategory.BEHAVIORAL],
        )
        await mock_consent_store.add(consent)

        response = client.get("/api/v1/gdpr/consents")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == "user123"
        assert data["items"][0]["purpose"] == "Marketing"

    @pytest.mark.asyncio
    async def test_list_consents_filter_by_user(self, client, mock_consent_store):
        """Test filtering consents by user ID."""
        from src.governance.gdpr.compliance import (
            ConsentRecord,
            DataCategory,
            LegalBasis,
        )

        # Add consents for different users
        consent1 = ConsentRecord(
            data_subject_id="user123",
            purpose="Marketing",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.CONTACT],
        )
        consent2 = ConsentRecord(
            data_subject_id="user456",
            purpose="Analytics",
            legal_basis=LegalBasis.LEGITIMATE_INTERESTS,
            data_categories=[DataCategory.BEHAVIORAL],
        )
        await mock_consent_store.add(consent1)
        await mock_consent_store.add(consent2)

        response = client.get("/api/v1/gdpr/consents?user_id=user123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_list_consents_pagination(self, client, mock_consent_store):
        """Test pagination of consents."""
        from src.governance.gdpr.compliance import (
            ConsentRecord,
            DataCategory,
            LegalBasis,
        )

        # Add 5 consents
        for i in range(5):
            consent = ConsentRecord(
                data_subject_id=f"user{i}",
                purpose="Test",
                legal_basis=LegalBasis.CONSENT,
                data_categories=[DataCategory.IDENTIFIER],
            )
            await mock_consent_store.add(consent)

        # Request page 1 with 2 items per page
        response = client.get("/api/v1/gdpr/consents?page=1&page_size=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_consents_filter_by_status(self, client, mock_consent_store):
        """Test filtering consents by status."""
        from src.governance.gdpr.compliance import (
            ConsentRecord,
            DataCategory,
            LegalBasis,
        )

        # Add granted consent
        consent_granted = ConsentRecord(
            data_subject_id="user1",
            purpose="Test",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.IDENTIFIER],
        )
        await mock_consent_store.add(consent_granted)

        # Add withdrawn consent
        consent_withdrawn = ConsentRecord(
            data_subject_id="user2",
            purpose="Test",
            legal_basis=LegalBasis.CONSENT,
            data_categories=[DataCategory.IDENTIFIER],
        )
        consent_withdrawn.withdraw("User request")
        await mock_consent_store.add(consent_withdrawn)

        # Filter by granted status
        response = client.get("/api/v1/gdpr/consents?status=granted")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "granted"


class TestCreateConsent:
    """Tests for POST /api/v1/gdpr/consent."""

    @pytest.mark.asyncio
    async def test_create_consent_success(self, client, mock_consent_store):
        """Test creating a consent successfully."""
        request_data = {
            "user_id": "user123",
            "purpose": "Marketing emails",
            "legal_basis": "consent",
            "data_categories": ["contact", "behavioral"],
            "retention_period": 365,
            "explicit_consent": True,
        }

        response = client.post("/api/v1/gdpr/consent", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == "user123"
        assert data["purpose"] == "Marketing emails"
        assert data["status"] == "granted"
        assert "consent_id" in data

    @pytest.mark.asyncio
    async def test_create_consent_with_expiration(self, client, mock_consent_store):
        """Test creating consent with expiration."""
        request_data = {
            "user_id": "user123",
            "purpose": "Test",
            "legal_basis": "consent",
            "data_categories": ["identifier"],
            "retention_period": 30,
            "explicit_consent": True,
        }

        response = client.post("/api/v1/gdpr/consent", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_create_consent_validation_error(self, client, mock_consent_store):
        """Test consent creation with validation error."""
        request_data = {
            "user_id": "user123",
            "purpose": "Test",
            "legal_basis": "invalid_basis",  # Invalid legal basis
            "data_categories": ["identifier"],
        }

        response = client.post("/api/v1/gdpr/consent", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_consent_empty_categories(self, client, mock_consent_store):
        """Test consent creation with empty data categories."""
        request_data = {
            "user_id": "user123",
            "purpose": "Test",
            "legal_basis": "consent",
            "data_categories": [],  # Empty list
        }

        response = client.post("/api/v1/gdpr/consent", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateDataSubjectRequest:
    """Tests for POST /api/v1/gdpr/request."""

    @pytest.mark.asyncio
    async def test_create_request_access(self, client, mock_processing_log):
        """Test creating data access request (Article 15)."""
        request_data = {
            "request_type": "access",
            "user_id": "user123",
            "details": "Request all personal data",
        }

        response = client.post("/api/v1/gdpr/request", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["request_type"] == "access"
        assert data["user_id"] == "user123"
        assert data["status"] == "pending"
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_create_request_erasure(self, client, mock_processing_log):
        """Test creating erasure request (Article 17)."""
        request_data = {
            "request_type": "erasure",
            "user_id": "user123",
            "details": "Delete all my data",
        }

        response = client.post("/api/v1/gdpr/request", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["request_type"] == "erasure"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_request_portability(self, client, mock_processing_log):
        """Test creating portability request (Article 20)."""
        request_data = {
            "request_type": "portability",
            "user_id": "user123",
        }

        response = client.post("/api/v1/gdpr/request", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["request_type"] == "portability"

    @pytest.mark.asyncio
    async def test_create_request_logs_processing_activity(
        self, client, mock_processing_log
    ):
        """Test that request creation logs processing activity."""
        request_data = {
            "request_type": "access",
            "user_id": "user123",
        }

        response = client.post("/api/v1/gdpr/request", json=request_data)

        assert response.status_code == status.HTTP_201_CREATED

        # Verify processing log has entry
        records = await mock_processing_log.get_by_subject("user123")
        assert len(records) > 0


class TestGetProcessingActivities:
    """Tests for GET /api/v1/gdpr/processing-activities."""

    @pytest.mark.asyncio
    async def test_get_activities_empty(self, client, mock_processing_log):
        """Test getting processing activities when empty."""
        response = client.get("/api/v1/gdpr/processing-activities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["activities"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_activities_with_data(self, client, mock_processing_log):
        """Test getting processing activities with data."""
        from src.governance.gdpr.compliance import (
            DataCategory,
            DataProcessingRecord,
            LegalBasis,
        )

        # Add processing record
        record = DataProcessingRecord(
            controller_name="AegisRAG",
            processing_purpose="User query",
            legal_basis=LegalBasis.LEGITIMATE_INTERESTS,
            data_categories=[DataCategory.BEHAVIORAL],
            data_subjects=["user123"],
        )
        await mock_processing_log.add(record)

        response = client.get("/api/v1/gdpr/processing-activities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["activities"]) == 1
        assert data["total"] == 1
        assert data["activities"][0]["processing_purpose"] == "User query"

    @pytest.mark.asyncio
    async def test_get_activities_filter_by_purpose(self, client, mock_processing_log):
        """Test filtering processing activities by purpose."""
        from src.governance.gdpr.compliance import (
            DataCategory,
            DataProcessingRecord,
            LegalBasis,
        )

        # Add two records with different purposes
        record1 = DataProcessingRecord(
            controller_name="AegisRAG",
            processing_purpose="User query",
            legal_basis=LegalBasis.LEGITIMATE_INTERESTS,
            data_categories=[DataCategory.BEHAVIORAL],
            data_subjects=["user1"],
        )
        record2 = DataProcessingRecord(
            controller_name="AegisRAG",
            processing_purpose="GDPR Request: access",
            legal_basis=LegalBasis.LEGAL_OBLIGATION,
            data_categories=[DataCategory.IDENTIFIER],
            data_subjects=["user2"],
        )
        await mock_processing_log.add(record1)
        await mock_processing_log.add(record2)

        response = client.get("/api/v1/gdpr/processing-activities?purpose=GDPR")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["activities"]) == 1
        assert "GDPR" in data["activities"][0]["processing_purpose"]


class TestPIISettings:
    """Tests for GET/PUT /api/v1/gdpr/pii-settings."""

    def test_get_pii_settings_default(self, client):
        """Test getting default PII settings."""
        response = client.get("/api/v1/gdpr/pii-settings")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "entity_types" in data
        assert "confidence_threshold" in data
        assert "anonymization_rules" in data
        assert data["confidence_threshold"] == 0.7

    def test_update_pii_settings_confidence(self, client):
        """Test updating PII confidence threshold."""
        update_data = {"confidence_threshold": 0.85}

        response = client.put("/api/v1/gdpr/pii-settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["confidence_threshold"] == 0.85

    def test_update_pii_settings_entity_types(self, client):
        """Test updating PII entity types."""
        update_data = {
            "entity_types": ["PERSON", "EMAIL", "PHONE"],
        }

        response = client.put("/api/v1/gdpr/pii-settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["entity_types"]) == 3
        assert "PERSON" in data["entity_types"]

    def test_update_pii_settings_anonymization_rules(self, client):
        """Test updating anonymization rules."""
        update_data = {
            "anonymization_rules": {
                "identifier": "[CUSTOM_REDACTED_ID]",
                "contact": "[CUSTOM_REDACTED_CONTACT]",
            }
        }

        response = client.put("/api/v1/gdpr/pii-settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["anonymization_rules"]["identifier"] == "[CUSTOM_REDACTED_ID]"

    def test_update_pii_settings_invalid_threshold(self, client):
        """Test updating with invalid confidence threshold."""
        update_data = {"confidence_threshold": 1.5}  # Out of range 0-1

        response = client.put("/api/v1/gdpr/pii-settings", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
