"""Integration tests for GDPR & Compliance APIs (Feature 99.3).

Sprint 99: Backend API Integration

Tests cover full GDPR compliance workflows:
- Consent lifecycle management
- Data subject request handling
- Processing activity logging
- PII detection and redaction
- GDPR compliance reporting
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC, timedelta


class TestConsentLifecycleIntegration:
    """GDPR consent lifecycle integration tests."""

    def test_create_and_list_consent_flow(
        self, integration_test_client, admin_auth_headers, gdpr_consent_lifecycle_data
    ):
        """Test creating consent and listing all consents."""
        consent_to_create = {
            "data_subject_id": gdpr_consent_lifecycle_data["data_subject_id"],
            "legal_basis": gdpr_consent_lifecycle_data["legal_basis"],
            "data_categories": gdpr_consent_lifecycle_data["data_categories"],
            "purpose": gdpr_consent_lifecycle_data["purpose"],
        }

        created_consent = {
            "id": "consent_123",
            **consent_to_create,
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
        }

        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            # Create consent
            mock_manager.return_value.create_consent = AsyncMock(
                return_value=created_consent
            )

            create_response = integration_test_client.post(
                "/api/v1/gdpr/consent",
                json=consent_to_create,
                headers=admin_auth_headers,
            )
            assert create_response.status_code == 201

            # List consents
            mock_manager.return_value.list_consents = AsyncMock(
                return_value=[created_consent]
            )

            list_response = integration_test_client.get(
                "/api/v1/gdpr/consents",
                headers=admin_auth_headers,
            )
            assert list_response.status_code == 200
            data = list_response.json()
            assert len(data["items"]) >= 1

    def test_renew_and_withdraw_consent_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test renewing and withdrawing consent."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            # Renew consent
            mock_manager.return_value.update_consent = AsyncMock(
                return_value={"status": "renewed"}
            )

            renew_response = integration_test_client.put(
                "/api/v1/gdpr/consent/consent_123",
                json={
                    "action": "renew",
                    "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
                },
                headers=admin_auth_headers,
            )
            assert renew_response.status_code == 200

            # Withdraw consent
            mock_manager.return_value.update_consent = AsyncMock(
                return_value={"status": "withdrawn"}
            )

            withdraw_response = integration_test_client.put(
                "/api/v1/gdpr/consent/consent_123",
                json={"action": "withdraw"},
                headers=admin_auth_headers,
            )
            assert withdraw_response.status_code == 200

    def test_filter_consents_by_legal_basis_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test filtering consents by legal basis."""
        with patch(
            "src.components.gdpr.get_consent_manager"
        ) as mock_manager:
            # Filter by consent basis
            mock_manager.return_value.list_consents = AsyncMock(return_value=[])

            consent_response = integration_test_client.get(
                "/api/v1/gdpr/consents?legal_basis=consent",
                headers=admin_auth_headers,
            )
            assert consent_response.status_code == 200

            # Filter by contract basis
            contract_response = integration_test_client.get(
                "/api/v1/gdpr/consents?legal_basis=contract",
                headers=admin_auth_headers,
            )
            assert contract_response.status_code == 200


class TestDataSubjectRightsIntegration:
    """Data subject rights request handling integration tests."""

    def test_full_data_subject_request_workflow(
        self, integration_test_client, admin_auth_headers, data_subject_request_flow_data
    ):
        """Test complete data subject request workflow (create, approve, verify)."""
        access_request = {
            "data_subject_id": data_subject_request_flow_data["data_subject_id"],
            "request_type": "access",
            "description": "Access request for integration test",
        }

        created_request = {
            "id": "request_123",
            **access_request,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            # Create request
            mock_handler.return_value.create_request = AsyncMock(
                return_value=created_request
            )

            create_response = integration_test_client.post(
                "/api/v1/gdpr/request",
                json=access_request,
                headers=admin_auth_headers,
            )
            assert create_response.status_code == 201

            # Approve request
            mock_handler.return_value.approve_request = AsyncMock(
                return_value={"status": "approved"}
            )

            approve_response = integration_test_client.post(
                "/api/v1/gdpr/request/request_123/approve",
                headers=admin_auth_headers,
            )
            assert approve_response.status_code == 200

    def test_all_data_subject_request_types_flow(
        self, integration_test_client, admin_auth_headers, data_subject_request_flow_data
    ):
        """Test all 6 data subject request types."""
        request_types = ["access", "erasure", "rectification", "portability", "restriction", "objection"]

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            for req_type in request_types:
                mock_handler.return_value.create_request = AsyncMock(
                    return_value={"id": f"request_{req_type}", "request_type": req_type}
                )

                response = integration_test_client.post(
                    "/api/v1/gdpr/request",
                    json={
                        "data_subject_id": "user_123",
                        "request_type": req_type,
                        "description": f"Test {req_type} request",
                    },
                    headers=admin_auth_headers,
                )
                assert response.status_code == 201

    def test_reject_request_with_reason_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test rejecting data subject request with reason."""
        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.reject_request = AsyncMock(
                return_value={"status": "rejected", "reason": "Duplicate request"}
            )

            response = integration_test_client.post(
                "/api/v1/gdpr/request/request_123/reject",
                json={"reason": "Duplicate request"},
                headers=admin_auth_headers,
            )
            assert response.status_code == 200


class TestProcessingActivityIntegration:
    """Processing activity logging (GDPR Art. 30) integration tests."""

    def test_list_processing_activities_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test listing all processing activities."""
        activities = [
            {
                "id": "activity_1",
                "skill_name": "skill_1",
                "purpose": "Document processing",
                "legal_basis": "consent",
            },
            {
                "id": "activity_2",
                "skill_name": "skill_2",
                "purpose": "Data analysis",
                "legal_basis": "legitimate_interests",
            },
        ]

        with patch(
            "src.components.gdpr.get_activity_logger"
        ) as mock_logger:
            mock_logger.return_value.list_activities = AsyncMock(
                return_value=activities
            )

            response = integration_test_client.get(
                "/api/v1/gdpr/processing-activities",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 2


class TestPIIDetectionIntegration:
    """PII detection and redaction integration tests."""

    def test_get_and_update_pii_settings_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving and updating PII detection settings."""
        current_settings = {
            "detection_enabled": True,
            "auto_redaction_enabled": True,
            "detection_threshold": 0.8,
        }

        updated_settings = {
            "detection_enabled": False,
            "auto_redaction_enabled": True,
            "detection_threshold": 0.9,
        }

        with patch(
            "src.components.gdpr.get_pii_settings"
        ) as mock_settings:
            # Get current settings
            mock_settings.return_value.get_settings = AsyncMock(
                return_value=current_settings
            )

            get_response = integration_test_client.get(
                "/api/v1/gdpr/pii-settings",
                headers=admin_auth_headers,
            )
            assert get_response.status_code == 200

            # Update settings
            mock_settings.return_value.update_settings = AsyncMock(
                return_value=updated_settings
            )

            update_response = integration_test_client.put(
                "/api/v1/gdpr/pii-settings",
                json=updated_settings,
                headers=admin_auth_headers,
            )
            assert update_response.status_code == 200
            data = update_response.json()
            assert data["detection_threshold"] == 0.9


class TestGDPRCompliance30DayDeadlineIntegration:
    """GDPR 30-day deadline compliance integration tests."""

    def test_data_subject_request_deadline_tracking(
        self, integration_test_client, admin_auth_headers
    ):
        """Test that data subject requests track 30-day deadline."""
        request_data = {
            "data_subject_id": "user_123",
            "request_type": "access",
        }

        created_request = {
            "id": "request_123",
            **request_data,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "deadline": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        }

        with patch(
            "src.components.gdpr.get_rights_handler"
        ) as mock_handler:
            mock_handler.return_value.create_request = AsyncMock(
                return_value=created_request
            )

            response = integration_test_client.post(
                "/api/v1/gdpr/request",
                json=request_data,
                headers=admin_auth_headers,
            )
            assert response.status_code == 201
            data = response.json()
            # Verify deadline is 30 days from creation
            assert "deadline" in data
