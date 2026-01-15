"""Unit tests for GDPR & Compliance APIs (Feature 99.3).

Sprint 99: Backend API Integration

Tests cover:
- GDPR consent management (creation, withdrawal)
- Data subject rights (6 types: access, erasure, rectification, portability, restriction, objection)
- Processing activity logging (Article 30)
- PII detection settings
- Consent expiration and validation
- Legal basis enum validation
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC, timedelta


class TestConsentListingEndpoint:
    """Tests for GET /api/v1/gdpr/consents endpoint."""

    def test_list_consents_success(
        self, admin_test_client, sample_consent_list_response, auth_headers
    ):
        """Test listing all GDPR consents."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.list_consents = AsyncMock(
                return_value=sample_consent_list_response["items"]
            )

            response = admin_test_client.get(
                "/api/v1/gdpr/consents",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["page"] == 1

    def test_list_consents_pagination(self, admin_test_client, auth_headers):
        """Test consent list pagination."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.list_consents = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/gdpr/consents?page=2&page_size=50",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 50

    def test_list_consents_filter_by_status(self, admin_test_client, auth_headers):
        """Test filtering consents by status."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.list_consents = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/gdpr/consents?status=active",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_consents_filter_by_legal_basis(self, admin_test_client, auth_headers):
        """Test filtering consents by legal basis."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.list_consents = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/gdpr/consents?legal_basis=consent",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_consents_filter_by_data_category(self, admin_test_client, auth_headers):
        """Test filtering consents by data category."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.list_consents = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/gdpr/consents?data_category=identifier",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_consents_empty(self, admin_test_client, auth_headers):
        """Test listing when no consents exist."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.list_consents = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/gdpr/consents",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []

    def test_list_consents_unauthorized(self, admin_test_client):
        """Test list without authorization."""
        response = admin_test_client.get("/api/v1/gdpr/consents")

        assert response.status_code == 401


class TestCreateConsentEndpoint:
    """Tests for POST /api/v1/gdpr/consent endpoint."""

    def test_create_consent_with_legal_basis_consent(
        self, admin_test_client, sample_consent, auth_headers
    ):
        """Test creating consent with legal basis: consent."""
        consent_data = {
            "data_subject_id": "user_123",
            "legal_basis": "consent",
            "data_categories": ["identifier", "contact"],
            "purpose": "Customer support",
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value=consent_data
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_with_legal_basis_contract(
        self, admin_test_client, auth_headers
    ):
        """Test creating consent with legal basis: contract."""
        consent_data = {
            "data_subject_id": "user_456",
            "legal_basis": "contract",
            "data_categories": ["contact"],
            "purpose": "Contract execution",
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value={"id": "consent_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_with_legal_basis_legal_obligation(
        self, admin_test_client, auth_headers
    ):
        """Test creating consent with legal basis: legal_obligation."""
        consent_data = {
            "data_subject_id": "user_789",
            "legal_basis": "legal_obligation",
            "data_categories": ["identifier"],
            "purpose": "Regulatory compliance",
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value={"id": "consent_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_with_legal_basis_vital_interests(
        self, admin_test_client, auth_headers
    ):
        """Test creating consent with legal basis: vital_interests."""
        consent_data = {
            "data_subject_id": "user_abc",
            "legal_basis": "vital_interests",
            "data_categories": ["health"],
            "purpose": "Emergency medical assistance",
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value={"id": "consent_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_with_legal_basis_public_task(
        self, admin_test_client, auth_headers
    ):
        """Test creating consent with legal basis: public_task."""
        consent_data = {
            "data_subject_id": "user_def",
            "legal_basis": "public_task",
            "data_categories": ["identifier"],
            "purpose": "Public sector processing",
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value={"id": "consent_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_with_legal_basis_legitimate_interests(
        self, admin_test_client, auth_headers
    ):
        """Test creating consent with legal basis: legitimate_interests."""
        consent_data = {
            "data_subject_id": "user_ghi",
            "legal_basis": "legitimate_interests",
            "data_categories": ["contact"],
            "purpose": "Marketing communications",
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value={"id": "consent_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_invalid_legal_basis(self, admin_test_client, auth_headers):
        """Test creating consent with invalid legal basis."""
        consent_data = {
            "data_subject_id": "user_123",
            "legal_basis": "invalid_basis",
            "data_categories": ["identifier"],
        }

        response = admin_test_client.post(
            "/api/v1/gdpr/consent",
            json=consent_data,
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_consent_missing_fields(self, admin_test_client, auth_headers):
        """Test creating consent with missing required fields."""
        consent_data = {"data_subject_id": "user_123"}

        response = admin_test_client.post(
            "/api/v1/gdpr/consent",
            json=consent_data,
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_create_consent_future_expiration(self, admin_test_client, auth_headers):
        """Test creating consent with future expiration date."""
        future_date = (datetime.now(UTC) + timedelta(days=365)).isoformat()

        consent_data = {
            "data_subject_id": "user_123",
            "legal_basis": "consent",
            "data_categories": ["identifier"],
            "expires_at": future_date,
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.create_consent = AsyncMock(
                return_value={"id": "consent_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_consent_past_expiration_rejected(self, admin_test_client, auth_headers):
        """Test creating consent with past expiration date is rejected."""
        past_date = (datetime.now(UTC) - timedelta(days=1)).isoformat()

        consent_data = {
            "data_subject_id": "user_123",
            "legal_basis": "consent",
            "data_categories": ["identifier"],
            "expires_at": past_date,
        }

        response = admin_test_client.post(
            "/api/v1/gdpr/consent",
            json=consent_data,
            headers=auth_headers,
        )

        assert response.status_code == 400


class TestUpdateConsentEndpoint:
    """Tests for PUT /api/v1/gdpr/consent/:id endpoint."""

    def test_update_consent_renew(self, admin_test_client, auth_headers):
        """Test renewing consent (extending expiration)."""
        update_data = {
            "action": "renew",
            "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.update_consent = AsyncMock(
                return_value={"status": "renewed"}
            )

            response = admin_test_client.put(
                "/api/v1/gdpr/consent/consent_123",
                json=update_data,
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_consent_withdraw(self, admin_test_client, auth_headers):
        """Test withdrawing consent."""
        update_data = {"action": "withdraw"}

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.update_consent = AsyncMock(
                return_value={"status": "withdrawn"}
            )

            response = admin_test_client.put(
                "/api/v1/gdpr/consent/consent_123",
                json=update_data,
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_consent_not_found(self, admin_test_client, auth_headers):
        """Test updating non-existent consent."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            mock_manager.return_value.update_consent = AsyncMock(return_value=None)

            response = admin_test_client.put(
                "/api/v1/gdpr/consent/nonexistent",
                json={"action": "renew"},
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestDataSubjectRequestEndpoints:
    """Tests for data subject rights endpoints."""

    def test_create_request_type_access(self, admin_test_client, auth_headers):
        """Test creating data subject access request (GDPR Art. 15)."""
        request_data = {
            "data_subject_id": "user_123",
            "request_type": "access",
            "description": "Provide all personal data",
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value={"id": "request_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_request_type_erasure(self, admin_test_client, auth_headers):
        """Test creating data subject erasure request (GDPR Art. 17)."""
        request_data = {
            "data_subject_id": "user_456",
            "request_type": "erasure",
            "description": "Delete all my data",
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value={"id": "request_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_request_type_rectification(self, admin_test_client, auth_headers):
        """Test creating data subject rectification request (GDPR Art. 16)."""
        request_data = {
            "data_subject_id": "user_789",
            "request_type": "rectification",
            "description": "Correct my email address",
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value={"id": "request_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_request_type_portability(self, admin_test_client, auth_headers):
        """Test creating data subject portability request (GDPR Art. 20)."""
        request_data = {
            "data_subject_id": "user_abc",
            "request_type": "portability",
            "description": "Export my data in portable format",
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value={"id": "request_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_request_type_restriction(self, admin_test_client, auth_headers):
        """Test creating data subject restriction request (GDPR Art. 18)."""
        request_data = {
            "data_subject_id": "user_def",
            "request_type": "restriction",
            "description": "Restrict processing of my data",
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value={"id": "request_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_request_type_objection(self, admin_test_client, auth_headers):
        """Test creating data subject objection request (GDPR Art. 21)."""
        request_data = {
            "data_subject_id": "user_ghi",
            "request_type": "objection",
            "description": "Object to marketing communications",
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value={"id": "request_123"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201

    def test_create_request_invalid_type(self, admin_test_client, auth_headers):
        """Test creating request with invalid type."""
        request_data = {
            "data_subject_id": "user_123",
            "request_type": "invalid_type",
        }

        response = admin_test_client.post(
            "/api/v1/gdpr/request",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_approve_request_success(self, admin_test_client, auth_headers):
        """Test approving data subject request."""
        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.approve_request = AsyncMock(
                return_value={"status": "approved"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request/request_123/approve",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_reject_request_success(self, admin_test_client, auth_headers):
        """Test rejecting data subject request."""
        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.reject_request = AsyncMock(
                return_value={"status": "rejected"}
            )

            response = admin_test_client.post(
                "/api/v1/gdpr/request/request_123/reject",
                json={"reason": "Duplicate request"},
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestProcessingActivityEndpoint:
    """Tests for GET /api/v1/gdpr/processing-activities endpoint."""

    def test_list_processing_activities_success(
        self, admin_test_client, sample_processing_activity, auth_headers
    ):
        """Test listing processing activities (GDPR Art. 30)."""
        with patch(
            "src.components.gdpr.get_activity_logger"
        ) as mock_logger:
            mock_logger.return_value.list_activities = AsyncMock(
                return_value=[sample_processing_activity]
            )

            response = admin_test_client.get(
                "/api/v1/gdpr/processing-activities",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data

    def test_list_processing_activities_empty(self, admin_test_client, auth_headers):
        """Test listing when no activities exist."""
        with patch(
            "src.components.gdpr.get_activity_logger"
        ) as mock_logger:
            mock_logger.return_value.list_activities = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/gdpr/processing-activities",
                headers=auth_headers,
            )

            assert response.status_code == 200


class TestPIISettingsEndpoints:
    """Tests for PII detection settings endpoints."""

    def test_get_pii_settings_success(
        self, admin_test_client, sample_pii_settings, auth_headers
    ):
        """Test retrieving PII detection settings."""
        with patch(
            "src.components.gdpr.get_pii_settings"
        ) as mock_settings:
            mock_settings.return_value.get_settings = AsyncMock(
                return_value=sample_pii_settings
            )

            response = admin_test_client.get(
                "/api/v1/gdpr/pii-settings",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "detection_enabled" in data
            assert "auto_redaction_enabled" in data

    def test_update_pii_settings_success(
        self, admin_test_client, sample_pii_settings, auth_headers
    ):
        """Test updating PII detection settings."""
        update_data = {
            "detection_enabled": False,
            "auto_redaction_enabled": True,
            "detection_threshold": 0.9,
        }

        with patch(
            "src.components.gdpr.get_pii_settings"
        ) as mock_settings:
            mock_settings.return_value.update_settings = AsyncMock(
                return_value=update_data
            )

            response = admin_test_client.put(
                "/api/v1/gdpr/pii-settings",
                json=update_data,
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_update_pii_settings_invalid_threshold(self, admin_test_client, auth_headers):
        """Test updating with invalid detection threshold."""
        update_data = {
            "detection_threshold": 1.5,  # Invalid: should be 0-1
        }

        response = admin_test_client.put(
            "/api/v1/gdpr/pii-settings",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 400
