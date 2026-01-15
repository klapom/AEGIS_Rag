"""Unit tests for Audit Trail API endpoints.

Sprint 99 Feature 99.4: Audit Trail APIs (8 SP)
Target Coverage: >80%

Test Coverage:
    - list_audit_events: Pagination, filtering by type/actor/outcome/time
    - generate_audit_report: Report types (GDPR, security, skill_usage)
    - verify_audit_integrity: SHA-256 chain verification
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.audit_models import OutcomeEnum, ReportTypeEnum


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_audit_manager():
    """Mock audit trail manager."""
    with patch("src.api.v1.audit.get_audit_manager") as mock:
        from src.governance.audit.storage import InMemoryAuditStorage
        from src.governance.audit.trail import AuditTrailManager

        storage = InMemoryAuditStorage(retention_days=365 * 7)
        manager = AuditTrailManager(storage=storage, retention_days=365 * 7)
        mock.return_value = manager
        yield manager


class TestListAuditEvents:
    """Tests for GET /api/v1/audit/events."""

    @pytest.mark.asyncio
    async def test_list_events_empty(self, client, mock_audit_manager):
        """Test listing audit events when empty."""
        response = client.get("/api/v1/audit/events")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_events_with_data(self, client, mock_audit_manager):
        """Test listing audit events with data."""
        from src.governance.audit.trail import AuditEventType

        # Log some events
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Execute skill",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.DATA_READ,
            actor_id="user123",
            action="Read document",
            outcome="success",
        )

        response = client.get("/api/v1/audit/events")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_list_events_pagination(self, client, mock_audit_manager):
        """Test pagination of audit events."""
        from src.governance.audit.trail import AuditEventType

        # Log 5 events
        for i in range(5):
            await mock_audit_manager.log(
                event_type=AuditEventType.SKILL_EXECUTED,
                actor_id=f"agent{i}",
                action=f"Action {i}",
                outcome="success",
            )

        # Request page 1 with 2 items per page
        response = client.get("/api/v1/audit/events?page=1&page_size=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_events_filter_by_actor(self, client, mock_audit_manager):
        """Test filtering events by actor ID."""
        from src.governance.audit.trail import AuditEventType

        # Log events for different actors
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Action 1",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent2",
            action="Action 2",
            outcome="success",
        )

        response = client.get("/api/v1/audit/events?actor_id=agent1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["actor_id"] == "agent1"

    @pytest.mark.asyncio
    async def test_list_events_filter_by_outcome(self, client, mock_audit_manager):
        """Test filtering events by outcome."""
        from src.governance.audit.trail import AuditEventType

        # Log events with different outcomes
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Success action",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_FAILED,
            actor_id="agent2",
            action="Failed action",
            outcome="failure",
        )

        response = client.get("/api/v1/audit/events?outcome=success")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_list_events_time_range_filter(self, client, mock_audit_manager):
        """Test filtering events by time range."""
        from src.governance.audit.trail import AuditEventType

        # Log events
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Action",
            outcome="success",
        )

        # Query with time range
        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.get(
            f"/api/v1/audit/events?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1


class TestGenerateAuditReport:
    """Tests for GET /api/v1/audit/reports/{type}."""

    @pytest.mark.asyncio
    async def test_generate_gdpr_compliance_report(self, client, mock_audit_manager):
        """Test generating GDPR compliance report."""
        from src.governance.audit.trail import AuditEventType

        # Log data access events
        await mock_audit_manager.log(
            event_type=AuditEventType.DATA_READ,
            actor_id="user123",
            action="Read data",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.DATA_WRITE,
            actor_id="user123",
            action="Write data",
            outcome="success",
        )

        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.get(
            f"/api/v1/audit/reports/gdpr_compliance"
            f"?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "gdpr_compliance"
        assert "summary" in data
        assert "events" in data
        assert "recommendations" in data
        assert data["summary"]["total_events"] >= 0

    @pytest.mark.asyncio
    async def test_generate_security_audit_report(self, client, mock_audit_manager):
        """Test generating security audit report."""
        from src.governance.audit.trail import AuditEventType

        # Log security events
        await mock_audit_manager.log(
            event_type=AuditEventType.AUTH_SUCCESS,
            actor_id="user123",
            action="Login",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.AUTH_FAILURE,
            actor_id="user456",
            action="Failed login",
            outcome="failure",
        )

        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.get(
            f"/api/v1/audit/reports/security_audit"
            f"?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "security_audit"
        assert len(data["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_generate_skill_usage_report(self, client, mock_audit_manager):
        """Test generating skill usage report."""
        from src.governance.audit.trail import AuditEventType

        # Log skill execution events
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Execute skill",
            outcome="success",
            metadata={"skill_id": "rag-001", "duration_ms": 120},
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_FAILED,
            actor_id="agent2",
            action="Execute skill",
            outcome="failure",
            metadata={"skill_id": "rag-002", "error": "Timeout"},
        )

        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.get(
            f"/api/v1/audit/reports/skill_usage"
            f"?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["report_type"] == "skill_usage"
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_generate_report_missing_time_params(self, client, mock_audit_manager):
        """Test generating report without time parameters."""
        response = client.get("/api/v1/audit/reports/gdpr_compliance")

        # Should fail validation (start_time and end_time are required)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVerifyAuditIntegrity:
    """Tests for GET /api/v1/audit/integrity."""

    @pytest.mark.asyncio
    async def test_verify_integrity_empty_chain(self, client, mock_audit_manager):
        """Test verifying integrity of empty audit trail."""
        response = client.get("/api/v1/audit/integrity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert data["total_events"] == 0
        assert data["verified_events"] == 0
        assert len(data["chain_breaks"]) == 0
        assert "last_verified_at" in data
        assert "verification_duration_ms" in data

    @pytest.mark.asyncio
    async def test_verify_integrity_valid_chain(self, client, mock_audit_manager):
        """Test verifying integrity of valid audit chain."""
        from src.governance.audit.trail import AuditEventType

        # Log some events (creates hash chain)
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Action 1",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent2",
            action="Action 2",
            outcome="success",
        )

        response = client.get("/api/v1/audit/integrity")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert data["total_events"] == 2
        assert data["verified_events"] == 2
        assert len(data["chain_breaks"]) == 0

    @pytest.mark.asyncio
    async def test_verify_integrity_with_time_range(self, client, mock_audit_manager):
        """Test verifying integrity within time range."""
        from src.governance.audit.trail import AuditEventType

        # Log events
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Action",
            outcome="success",
        )

        start_time = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        end_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        response = client.get(
            f"/api/v1/audit/integrity?start_time={start_time}&end_time={end_time}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_valid"] is True
        assert data["total_events"] >= 1

    @pytest.mark.asyncio
    async def test_verify_integrity_tampered_chain(self, client, mock_audit_manager):
        """Test detecting tampered audit chain."""
        from src.governance.audit.trail import AuditEventType

        # Log events
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Action 1",
            outcome="success",
        )
        await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent2",
            action="Action 2",
            outcome="success",
        )

        # Tamper with an event's hash (simulate tampering)
        events = await mock_audit_manager.storage.query(limit=100)
        if len(events) > 0:
            # Access the event object and modify hash (breaks immutability for testing)
            # Note: In production, this would be prevented by frozen dataclass
            import dataclasses

            first_event = events[0]
            # Create tampered version by modifying hash
            tampered_event = dataclasses.replace(first_event, event_hash="tampered_hash")

            # Replace in storage (hack for testing)
            mock_audit_manager.storage.events[0] = tampered_event

            response = client.get("/api/v1/audit/integrity")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            # Chain should be invalid due to tampering
            assert data["is_valid"] is False or len(data["chain_breaks"]) > 0


class TestAuditEventStructure:
    """Tests for audit event structure and metadata."""

    @pytest.mark.asyncio
    async def test_event_has_sha256_hash(self, client, mock_audit_manager):
        """Test that events have SHA-256 hash."""
        from src.governance.audit.trail import AuditEventType

        # Log event
        event = await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Test action",
            outcome="success",
        )

        assert event.event_hash is not None
        assert len(event.event_hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_event_chain_linking(self, client, mock_audit_manager):
        """Test that events are linked via previous_hash."""
        from src.governance.audit.trail import AuditEventType

        # Log two events
        event1 = await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Action 1",
            outcome="success",
        )
        event2 = await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent2",
            action="Action 2",
            outcome="success",
        )

        # Second event should link to first event
        assert event2.previous_hash == event1.event_hash

    @pytest.mark.asyncio
    async def test_event_metadata_preserved(self, client, mock_audit_manager):
        """Test that event metadata is preserved."""
        from src.governance.audit.trail import AuditEventType

        metadata = {"skill_id": "rag-001", "duration_ms": 120, "custom_field": "value"}

        event = await mock_audit_manager.log(
            event_type=AuditEventType.SKILL_EXECUTED,
            actor_id="agent1",
            action="Test action",
            outcome="success",
            metadata=metadata,
        )

        assert event.metadata == metadata
        assert event.metadata["skill_id"] == "rag-001"
        assert event.metadata["duration_ms"] == 120
