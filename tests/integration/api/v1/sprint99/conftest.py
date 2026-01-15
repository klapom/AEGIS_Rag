"""Pytest fixtures for Sprint 99 integration tests.

Integration tests use real FastAPI app and mocked backend services
to test full endpoint-to-service interaction flows.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def admin_auth_headers() -> dict[str, str]:
    """Authorization headers for admin user."""
    return {"Authorization": "Bearer admin_token_sprint99"}


@pytest.fixture
def integration_test_client():
    """Create FastAPI test client for integration testing."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)


@pytest.fixture
def mock_all_services():
    """Mock all backend services for integration tests."""
    mocks = {
        "skill_registry": AsyncMock(),
        "skill_lifecycle": AsyncMock(),
        "tool_composer": AsyncMock(),
        "message_bus": AsyncMock(),
        "blackboard": AsyncMock(),
        "agent_hierarchy": AsyncMock(),
        "skill_orchestrator": AsyncMock(),
        "consent_manager": AsyncMock(),
        "rights_handler": AsyncMock(),
        "activity_logger": AsyncMock(),
        "pii_settings": AsyncMock(),
        "audit_system": AsyncMock(),
        "crypto_chain": AsyncMock(),
        "report_generator": AsyncMock(),
    }
    return mocks


@pytest.fixture
def skill_lifecycle_data() -> dict[str, Any]:
    """Complete skill lifecycle data for integration test."""
    return {
        "skill_name": "document_analyzer",
        "version": "1.0.0",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "status": "active",
        "config": {
            "model": "qwen3:32b",
            "timeout": 30,
        },
    }


@pytest.fixture
def tool_authorization_flow_data() -> dict[str, Any]:
    """Data for tool authorization flow integration test."""
    return {
        "skill_name": "document_analyzer",
        "tools": [
            {
                "tool_id": "tool_pdf_parser",
                "tool_name": "pdf_parser",
                "access_level": "standard",
            },
            {
                "tool_id": "tool_text_extractor",
                "tool_name": "text_extractor",
                "access_level": "elevated",
            },
        ],
    }


@pytest.fixture
def orchestration_flow_data() -> dict[str, Any]:
    """Data for orchestration flow integration test."""
    now = datetime.now(UTC)
    return {
        "orchestration_id": str(uuid4()),
        "skills": ["skill_1", "skill_2"],
        "agents": ["coordinator", "manager_1", "worker_1", "worker_2"],
        "messages": [
            {
                "type": "SKILL_REQUEST",
                "sender": "coordinator",
                "receiver": "worker_1",
                "timestamp": now.isoformat(),
            },
            {
                "type": "SKILL_RESPONSE",
                "sender": "worker_1",
                "receiver": "coordinator",
                "timestamp": (now + timedelta(seconds=2)).isoformat(),
            },
        ],
    }


@pytest.fixture
def gdpr_consent_lifecycle_data() -> dict[str, Any]:
    """Data for GDPR consent lifecycle integration test."""
    return {
        "data_subject_id": "user_integration_test",
        "legal_basis": "consent",
        "data_categories": ["identifier", "contact"],
        "purpose": "Integration test data processing",
        "expiration_days": 365,
    }


@pytest.fixture
def data_subject_request_flow_data() -> dict[str, Any]:
    """Data for data subject request workflow integration test."""
    return {
        "data_subject_id": "user_integration_test",
        "requests": [
            {
                "request_type": "access",
                "description": "Access request for integration test",
            },
            {
                "request_type": "erasure",
                "description": "Erasure request for integration test",
            },
        ],
    }


@pytest.fixture
def audit_event_batch_data() -> list[dict[str, Any]]:
    """Batch of audit events for integrity test."""
    events = []
    now = datetime.now(UTC)

    for i in range(100):
        events.append(
            {
                "id": str(uuid4()),
                "type": "data_access" if i % 2 == 0 else "skill_execute",
                "outcome": "success",
                "actor_id": f"actor_{i % 10}",
                "timestamp": (now + timedelta(seconds=i)).isoformat(),
                "resource": f"resource_{i}",
                "hash": f"hash_{i:05d}",
                "prev_hash": f"hash_{i-1:05d}" if i > 0 else None,
            }
        )

    return events


@pytest.fixture
def compliance_report_test_data() -> dict[str, Any]:
    """Data for compliance report generation integration test."""
    return {
        "consents": [
            {
                "id": str(uuid4()),
                "legal_basis": "consent",
                "status": "active",
            },
            {
                "id": str(uuid4()),
                "legal_basis": "contract",
                "status": "active",
            },
        ],
        "requests": [
            {
                "id": str(uuid4()),
                "request_type": "access",
                "status": "approved",
            },
            {
                "id": str(uuid4()),
                "request_type": "erasure",
                "status": "pending",
            },
        ],
    }


@pytest.fixture
def time_range_7_days() -> dict[str, str]:
    """7-day time range for filtering."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=7)
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }


@pytest.fixture
def time_range_30_days() -> dict[str, str]:
    """30-day time range for filtering."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=30)
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }


@pytest.fixture
def time_range_90_days() -> dict[str, str]:
    """90-day time range for filtering."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=90)
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
