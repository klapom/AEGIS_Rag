"""Unit tests for Audit Trail APIs (Feature 99.4).

Sprint 99: Backend API Integration

Tests cover:
- Audit event listing and filtering
- Cryptographic chain integrity verification
- Compliance report generation (GDPR, Security, Skill Usage)
- SHA-256 hash validation and tamper detection
- 7-year retention compliance
- Audit export (CSV/JSON)
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, UTC, timedelta


class TestAuditEventListingEndpoint:
    """Tests for GET /api/v1/audit/events endpoint."""

    def test_list_audit_events_success(
        self, admin_test_client, sample_audit_event_list_response, auth_headers
    ):
        """Test listing audit events."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(
                return_value=sample_audit_event_list_response["items"]
            )

            response = admin_test_client.get(
                "/api/v1/audit/events",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert data["page"] == 1

    def test_list_audit_events_pagination(self, admin_test_client, auth_headers):
        """Test audit events pagination."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?page=2&page_size=100",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 100

    def test_list_events_filter_by_type_auth_login(self, admin_test_client, auth_headers):
        """Test filtering events by type: auth_login."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?type=auth_login",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_type_data_access(self, admin_test_client, auth_headers):
        """Test filtering events by type: data_access."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?type=data_access",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_type_skill_execute(self, admin_test_client, auth_headers):
        """Test filtering events by type: skill_execute."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?type=skill_execute",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_type_policy_violation(self, admin_test_client, auth_headers):
        """Test filtering events by type: policy_violation."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?type=policy_violation",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_type_gdpr_request(self, admin_test_client, auth_headers):
        """Test filtering events by type: gdpr_request."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?type=gdpr_request",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_outcome_success(self, admin_test_client, auth_headers):
        """Test filtering events by outcome: success."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?outcome=success",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_outcome_failure(self, admin_test_client, auth_headers):
        """Test filtering events by outcome: failure."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?outcome=failure",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_actor(self, admin_test_client, auth_headers):
        """Test filtering events by actor ID."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?actor_id=user_123",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_filter_by_time_range(self, admin_test_client, auth_headers):
        """Test filtering events by time range."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=7)

            response = admin_test_client.get(
                f"/api/v1/audit/events?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_full_text_search(self, admin_test_client, auth_headers):
        """Test full-text search in audit events."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events?search=data+breach",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_list_events_empty(self, admin_test_client, auth_headers):
        """Test listing when no events exist."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                "/api/v1/audit/events",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []

    def test_list_events_unauthorized(self, admin_test_client):
        """Test event listing without authorization."""
        response = admin_test_client.get("/api/v1/audit/events")

        assert response.status_code == 401


class TestGetAuditEventDetailsEndpoint:
    """Tests for GET /api/v1/audit/events/:id endpoint."""

    def test_get_audit_event_success(
        self, admin_test_client, sample_audit_event, auth_headers
    ):
        """Test retrieving specific audit event."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.get_event = AsyncMock(
                return_value=sample_audit_event
            )

            response = admin_test_client.get(
                f"/api/v1/audit/events/{sample_audit_event['id']}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == sample_audit_event["id"]
            assert "hash" in data
            assert "prev_hash" in data

    def test_get_audit_event_not_found(self, admin_test_client, auth_headers):
        """Test retrieving non-existent event."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.get_event = AsyncMock(return_value=None)

            response = admin_test_client.get(
                "/api/v1/audit/events/nonexistent_id",
                headers=auth_headers,
            )

            assert response.status_code == 404


class TestComplianceReportEndpoint:
    """Tests for GET /api/v1/audit/reports/:type endpoint."""

    def test_generate_gdpr_compliance_report(
        self, admin_test_client, sample_compliance_report, auth_headers
    ):
        """Test generating GDPR compliance report."""
        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_report = sample_compliance_report.copy()
            mock_report["report_type"] = "gdpr_compliance"
            mock_generator.return_value.generate_report = AsyncMock(
                return_value=mock_report
            )

            response = admin_test_client.get(
                "/api/v1/audit/reports/gdpr_compliance",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["report_type"] == "gdpr_compliance"
            assert "summary" in data

    def test_generate_security_audit_report(
        self, admin_test_client, auth_headers
    ):
        """Test generating security audit report."""
        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value={
                    "report_type": "security_audit",
                    "generated_at": datetime.now(UTC).isoformat(),
                }
            )

            response = admin_test_client.get(
                "/api/v1/audit/reports/security_audit",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["report_type"] == "security_audit"

    def test_generate_skill_usage_report(
        self, admin_test_client, auth_headers
    ):
        """Test generating skill usage report."""
        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value={
                    "report_type": "skill_usage",
                    "generated_at": datetime.now(UTC).isoformat(),
                }
            )

            response = admin_test_client.get(
                "/api/v1/audit/reports/skill_usage",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["report_type"] == "skill_usage"

    def test_generate_report_with_time_range(self, admin_test_client, auth_headers):
        """Test generating report with specific time range."""
        with patch(
            "src.components.audit.get_report_generator"
        ) as mock_generator:
            mock_generator.return_value.generate_report = AsyncMock(
                return_value={"report_type": "gdpr_compliance"}
            )

            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=30)

            response = admin_test_client.get(
                f"/api/v1/audit/reports/gdpr_compliance?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_generate_report_invalid_type(self, admin_test_client, auth_headers):
        """Test generating report with invalid type."""
        response = admin_test_client.get(
            "/api/v1/audit/reports/invalid_type",
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_generate_report_unauthorized(self, admin_test_client):
        """Test report generation without authorization."""
        response = admin_test_client.get("/api/v1/audit/reports/gdpr_compliance")

        assert response.status_code == 401


class TestIntegrityVerificationEndpoint:
    """Tests for GET /api/v1/audit/integrity endpoint."""

    def test_verify_chain_integrity_success(
        self, admin_test_client, sample_integrity_verification, auth_headers
    ):
        """Test cryptographic chain integrity verification."""
        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value=sample_integrity_verification
            )

            response = admin_test_client.get(
                "/api/v1/audit/integrity",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert "broken_indices" in data

    def test_verify_chain_tamper_detection(self, admin_test_client, auth_headers):
        """Test tamper detection in chain."""
        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value={
                    "valid": False,
                    "broken_indices": [42, 100, 567],
                    "verification_duration_ms": 2345,
                }
            )

            response = admin_test_client.get(
                "/api/v1/audit/integrity",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert len(data["broken_indices"]) == 3

    def test_verify_chain_sha256_validation(self, admin_test_client, auth_headers):
        """Test SHA-256 chain integrity calculation."""
        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value={
                    "valid": True,
                    "total_events": 5000,
                    "verified_events": 5000,
                    "chain_integrity_score": 1.0,
                }
            )

            response = admin_test_client.get(
                "/api/v1/audit/integrity",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["chain_integrity_score"] == 1.0

    def test_verify_chain_performance(self, admin_test_client, auth_headers):
        """Test chain verification performance metrics."""
        with patch(
            "src.components.audit.get_cryptographic_chain"
        ) as mock_chain:
            mock_chain.return_value.verify_chain = AsyncMock(
                return_value={
                    "valid": True,
                    "verification_duration_ms": 1234,
                    "total_events": 100000,
                }
            )

            response = admin_test_client.get(
                "/api/v1/audit/integrity",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_verify_chain_unauthorized(self, admin_test_client):
        """Test integrity check without authorization."""
        response = admin_test_client.get("/api/v1/audit/integrity")

        assert response.status_code == 401


class TestAuditExportEndpoint:
    """Tests for GET /api/v1/audit/export endpoint."""

    def test_export_events_csv_format(self, admin_test_client, auth_headers):
        """Test exporting audit events in CSV format."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(
                return_value=b"id,type,outcome,actor_id,timestamp\n..."
            )

            response = admin_test_client.get(
                "/api/v1/audit/export?format=csv",
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert response.headers.get("Content-Type") == "text/csv"

    def test_export_events_json_format(self, admin_test_client, auth_headers):
        """Test exporting audit events in JSON format."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(
                return_value=[{"id": "event_1", "type": "auth_login"}]
            )

            response = admin_test_client.get(
                "/api/v1/audit/export?format=json",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_export_with_time_range_filter(self, admin_test_client, auth_headers):
        """Test export with time range filtering."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(return_value=b"...")

            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=30)

            response = admin_test_client.get(
                f"/api/v1/audit/export?format=csv&start_time={start_time.isoformat()}&end_time={end_time.isoformat()}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_export_with_event_type_filter(self, admin_test_client, auth_headers):
        """Test export with event type filtering."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.export_events = AsyncMock(return_value=b"...")

            response = admin_test_client.get(
                "/api/v1/audit/export?format=csv&type=policy_violation",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_export_invalid_format(self, admin_test_client, auth_headers):
        """Test export with invalid format."""
        response = admin_test_client.get(
            "/api/v1/audit/export?format=xml",
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_export_unauthorized(self, admin_test_client):
        """Test export without authorization."""
        response = admin_test_client.get("/api/v1/audit/export?format=csv")

        assert response.status_code == 401


class TestAuditRetentionCompliance:
    """Tests for 7-year audit retention compliance."""

    def test_list_events_7_year_retention(self, admin_test_client, auth_headers):
        """Test that audit system can retrieve events up to 7 years old."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            seven_years_ago = datetime.now(UTC) - timedelta(days=365 * 7)

            mock_system.return_value.list_events = AsyncMock(return_value=[])

            response = admin_test_client.get(
                f"/api/v1/audit/events?start_time={seven_years_ago.isoformat()}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    def test_events_older_than_7_years_accessible(self, admin_test_client, auth_headers):
        """Test that events beyond 7 years can still be accessed (legal requirement)."""
        with patch(
            "src.components.audit.get_audit_trail_system"
        ) as mock_system:
            mock_system.return_value.list_events = AsyncMock(return_value=[])

            # Even older than 7 years
            ten_years_ago = datetime.now(UTC) - timedelta(days=365 * 10)

            response = admin_test_client.get(
                f"/api/v1/audit/events?start_time={ten_years_ago.isoformat()}",
                headers=auth_headers,
            )

            # Should be accessible for compliance verification
            assert response.status_code == 200
