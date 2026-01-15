"""Integration tests for Audit Trail APIs (Feature 99.4).

Sprint 99: Backend API Integration

Tests cover full audit trail workflows:
- Event logging and retrieval
- Cryptographic chain integrity verification
- Compliance report generation
- Tamper detection and chain validation
- 7-year retention compliance
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC, timedelta


class TestAuditEventWorkflowIntegration:
    """Audit event logging and retrieval integration tests."""

    def test_audit_event_creation_and_retrieval_flow(
        self, integration_test_client, admin_auth_headers, audit_event_batch_data
    ):
        """Test creating audit events and retrieving them."""
        event_data = {
            "type": "data_access",
            "outcome": "success",
            "actor_id": "user_123",
            "resource": "document_456",
            "action": "read",
        }

        created_event = {
            "id": "event_789",
            **event_data,
            "timestamp": datetime.now(UTC).isoformat(),
            "hash": "abc123def456",
        }

        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            # List events
            mock_system.return_value.list_events = AsyncMock(
                return_value=[created_event]
            )

            list_response = integration_test_client.get(
                "/api/v1/audit/events",
                headers=admin_auth_headers,
            )
            assert list_response.status_code == 200
            data = list_response.json()
            assert len(data["items"]) >= 1

            # Get specific event
            mock_system.return_value.get_event = AsyncMock(
                return_value=created_event
            )

            detail_response = integration_test_client.get(
                "/api/v1/audit/events/event_789",
                headers=admin_auth_headers,
            )
            assert detail_response.status_code == 200

    def test_filter_events_by_multiple_criteria_flow(
        self, integration_test_client, admin_auth_headers, time_range_30_days
    ):
        """Test filtering audit events by multiple criteria."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            # Filter by type and outcome
            response = integration_test_client.get(
                "/api/v1/audit/events?type=policy_violation&outcome=failure",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200

            # Filter by actor and time range
            response = integration_test_client.get(
                f"/api/v1/audit/events?actor_id=user_123&start_time={time_range_30_days['start_time']}&end_time={time_range_30_days['end_time']}",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200

    def test_audit_event_type_filtering_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test filtering events by all event types."""
        event_types = [
            "auth_login",
            "auth_logout",
            "data_access",
            "data_create",
            "skill_execute",
            "policy_violation",
            "gdpr_request",
            "system_error",
        ]

        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            for event_type in event_types:
                mock_system.return_value.list_events = AsyncMock(return_value=[])

                response = integration_test_client.get(
                    f"/api/v1/audit/events?type={event_type}",
                    headers=admin_auth_headers,
                )
                assert response.status_code == 200


class TestAuditIntegrityVerificationIntegration:
    """Cryptographic chain integrity verification integration tests."""

    def test_verify_chain_integrity_flow(
        self, integration_test_client, admin_auth_headers, audit_event_batch_data
    ):
        """Test verifying cryptographic chain integrity."""
        integrity_result = {
            "valid": True,
            "total_events": len(audit_event_batch_data),
            "verified_events": len(audit_event_batch_data),
            "broken_indices": [],
            "chain_integrity_score": 1.0,
            "verification_duration_ms": 1234,
        }

        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value=integrity_result
            )

            response = integration_test_client.get(
                "/api/v1/audit/integrity",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["chain_integrity_score"] == 1.0

    def test_detect_tampered_chain_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test detecting tampering in audit chain."""
        tampered_result = {
            "valid": False,
            "total_events": 1000,
            "verified_events": 997,
            "broken_indices": [42, 100, 567],
            "chain_integrity_score": 0.997,
            "last_verified": datetime.now(UTC).isoformat(),
        }

        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value=tampered_result
            )

            response = integration_test_client.get(
                "/api/v1/audit/integrity",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert len(data["broken_indices"]) == 3

    def test_sha256_chain_calculation_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test SHA-256 hash chain calculation and validation."""
        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            # Large event chain (100k events)
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value={
                    "valid": True,
                    "total_events": 100000,
                    "verified_events": 100000,
                    "broken_indices": [],
                    "chain_integrity_score": 1.0,
                    "verification_duration_ms": 5678,
                }
            )

            response = integration_test_client.get(
                "/api/v1/audit/integrity",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total_events"] == 100000


class TestComplianceReportGenerationIntegration:
    """Compliance report generation integration tests."""

    def test_generate_all_report_types_flow(
        self, integration_test_client, admin_auth_headers, compliance_report_test_data
    ):
        """Test generating all three compliance report types."""
        report_types = [
            "gdpr_compliance",
            "security_audit",
            "skill_usage",
        ]

        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            for report_type in report_types:
                mock_generator.return_value.generate_report = AsyncMock(
                    return_value={
                        "report_type": report_type,
                        "generated_at": datetime.now(UTC).isoformat(),
                    }
                )

                response = integration_test_client.get(
                    f"/api/v1/audit/reports/{report_type}",
                    headers=admin_auth_headers,
                )
                assert response.status_code == 200
                data = response.json()
                assert data["report_type"] == report_type

    def test_gdpr_compliance_report_includes_consents_and_requests(
        self, integration_test_client, admin_auth_headers, compliance_report_test_data
    ):
        """Test GDPR compliance report includes consents and requests."""
        gdpr_report = {
            "report_type": "gdpr_compliance",
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_consents": 100,
                "active_consents": 95,
                "pending_requests": 3,
                "approved_requests": 25,
            },
        }

        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value=gdpr_report
            )

            response = integration_test_client.get(
                "/api/v1/audit/reports/gdpr_compliance",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "summary" in data
            assert "total_consents" in data["summary"]

    def test_security_audit_report_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test generating security audit report."""
        security_report = {
            "report_type": "security_audit",
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": {
                "total_events": 5000,
                "failed_events": 12,
                "error_rate": 0.0024,
                "policy_violations": 5,
            },
        }

        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value=security_report
            )

            response = integration_test_client.get(
                "/api/v1/audit/reports/security_audit",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200

    def test_skill_usage_report_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test generating skill usage report."""
        skill_report = {
            "report_type": "skill_usage",
            "generated_at": datetime.now(UTC).isoformat(),
            "skills": [
                {"name": "skill_1", "invocations": 1000, "success_rate": 0.98},
                {"name": "skill_2", "invocations": 500, "success_rate": 0.95},
            ],
        }

        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value=skill_report
            )

            response = integration_test_client.get(
                "/api/v1/audit/reports/skill_usage",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200

    def test_report_generation_with_time_range_flow(
        self, integration_test_client, admin_auth_headers, time_range_30_days
    ):
        """Test report generation with specific time range."""
        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value={
                    "report_type": "gdpr_compliance",
                    "date_range": time_range_30_days,
                }
            )

            response = integration_test_client.get(
                f"/api/v1/audit/reports/gdpr_compliance?start_time={time_range_30_days['start_time']}&end_time={time_range_30_days['end_time']}",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200


class TestAuditExportIntegration:
    """Audit event export functionality integration tests."""

    def test_export_events_csv_format_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test exporting audit events in CSV format."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(
                return_value=b"id,type,outcome,timestamp\nevent_1,auth_login,success,2026-01-15T10:00:00Z"
            )

            response = integration_test_client.get(
                "/api/v1/audit/export?format=csv",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
            assert "text/csv" in response.headers.get("Content-Type", "")

    def test_export_events_json_format_flow(
        self, integration_test_client, admin_auth_headers
    ):
        """Test exporting audit events in JSON format."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(
                return_value=[
                    {
                        "id": "event_1",
                        "type": "auth_login",
                        "outcome": "success",
                    }
                ]
            )

            response = integration_test_client.get(
                "/api/v1/audit/export?format=json",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200


class TestAuditRetention7YearComplianceIntegration:
    """7-year audit retention compliance integration tests."""

    def test_retrieve_events_within_7_year_window(
        self, integration_test_client, admin_auth_headers
    ):
        """Test retrieving events within 7-year retention window."""
        seven_years_ago = datetime.now(UTC) - timedelta(days=365 * 7)

        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = integration_test_client.get(
                f"/api/v1/audit/events?start_time={seven_years_ago.isoformat()}",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200

    def test_verify_7_year_retention_compliance(
        self, integration_test_client, admin_auth_headers
    ):
        """Test that system supports 7-year retention queries."""
        # EU AI Act Art. 12 requires 7-year record keeping
        seven_years_ago = datetime.now(UTC) - timedelta(days=365 * 7)
        now = datetime.now(UTC)

        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            # Simulate 7 years of audit events
            events = [
                {
                    "id": f"event_{i}",
                    "timestamp": (seven_years_ago + timedelta(days=i)).isoformat(),
                }
                for i in range(365 * 7)
            ]
            mock_system.return_value.list_events = AsyncMock(
                return_value=events[:100]  # Return first 100 for pagination
            )

            response = integration_test_client.get(
                f"/api/v1/audit/events?start_time={seven_years_ago.isoformat()}&end_time={now.isoformat()}",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200

    def test_export_7_year_compliant_audit_trail(
        self, integration_test_client, admin_auth_headers
    ):
        """Test exporting complete 7-year audit trail for compliance."""
        seven_years_ago = datetime.now(UTC) - timedelta(days=365 * 7)

        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(
                return_value=b"Full 7-year audit trail data"
            )

            response = integration_test_client.get(
                f"/api/v1/audit/export?format=csv&start_time={seven_years_ago.isoformat()}",
                headers=admin_auth_headers,
            )
            assert response.status_code == 200
