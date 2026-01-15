"""Pytest fixtures for Sprint 99 unit tests.

Sprint 99: Backend API Integration for Sprint 97-98 UI Features

Provides fixtures for:
- JWT authentication tokens
- Test data (skills, agents, consents, audit events)
- Mock backend services
- Request/response models
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def admin_jwt_token() -> str:
    """JWT token for admin user."""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbjEyMyIsInJvbGUiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.test"


@pytest.fixture
def user_jwt_token() -> str:
    """JWT token for regular user."""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwicm9sZSI6InVzZXIiLCJleHAiOjk5OTk5OTk5OTl9.test"


@pytest.fixture
def expired_jwt_token() -> str:
    """Expired JWT token."""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIiwicm9sZSI6InVzZXIiLCJleHAiOjB9.test"


# ============================================================================
# Feature 99.1: Skill Management Fixtures
# ============================================================================


@pytest.fixture
def sample_skill_data() -> dict[str, Any]:
    """Complete sample skill object."""
    return {
        "name": "document_analyzer",
        "version": "1.0.0",
        "status": "active",
        "health": "healthy",
        "description": "Analyzes and extracts insights from documents",
        "config": {
            "model": "qwen3:32b",
            "timeout": 30,
            "max_tokens": 1000,
            "temperature": 0.7,
        },
        "tools": [
            {
                "id": "tool_1",
                "name": "pdf_parser",
                "access_level": "standard",
            },
            {
                "id": "tool_2",
                "name": "text_extractor",
                "access_level": "standard",
            },
        ],
        "metrics": {
            "invocations": 1024,
            "success_rate": 0.98,
            "avg_latency_ms": 245,
            "error_count": 20,
        },
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_skill_list_response() -> dict[str, Any]:
    """Sample paginated skill list response."""
    return {
        "items": [
            {
                "name": "document_analyzer",
                "version": "1.0.0",
                "status": "active",
                "health": "healthy",
            },
            {
                "name": "entity_extractor",
                "version": "2.1.0",
                "status": "active",
                "health": "healthy",
            },
            {
                "name": "graph_builder",
                "version": "1.5.0",
                "status": "inactive",
                "health": "offline",
            },
        ],
        "total": 3,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


@pytest.fixture
def sample_skill_config() -> dict[str, Any]:
    """Sample skill YAML configuration."""
    return {
        "name": "document_analyzer",
        "version": "1.0.0",
        "model": "qwen3:32b",
        "timeout": 30,
        "max_tokens": 1000,
        "temperature": 0.7,
        "tools": ["pdf_parser", "text_extractor"],
        "rate_limits": {
            "requests_per_minute": 60,
            "tokens_per_hour": 100000,
        },
    }


@pytest.fixture
def sample_tool_authorization() -> dict[str, Any]:
    """Sample tool authorization record."""
    return {
        "tool_id": "tool_1",
        "tool_name": "pdf_parser",
        "skill_name": "document_analyzer",
        "access_level": "standard",
        "authorized_at": datetime.now(UTC).isoformat(),
        "authorized_by": "admin123",
    }


@pytest.fixture
def sample_skill_metrics() -> dict[str, Any]:
    """Sample skill metrics."""
    return {
        "name": "document_analyzer",
        "invocations": 1024,
        "success_count": 1003,
        "error_count": 21,
        "success_rate": 0.9795,
        "avg_latency_ms": 245.3,
        "min_latency_ms": 45,
        "max_latency_ms": 1230,
        "p95_latency_ms": 589,
        "p99_latency_ms": 891,
        "last_invocation": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_activation_history() -> dict[str, Any]:
    """Sample skill activation history."""
    now = datetime.now(UTC)
    return {
        "name": "document_analyzer",
        "events": [
            {
                "timestamp": (now - timedelta(days=5)).isoformat(),
                "event_type": "activated",
                "triggered_by": "user123",
            },
            {
                "timestamp": (now - timedelta(days=3)).isoformat(),
                "event_type": "deactivated",
                "triggered_by": "system",
            },
            {
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "event_type": "activated",
                "triggered_by": "user456",
            },
        ],
    }


@pytest.fixture
def mock_skill_registry() -> AsyncMock:
    """Mock SkillRegistry service."""
    registry = AsyncMock()
    registry.list_skills = AsyncMock(return_value=["skill_1", "skill_2", "skill_3"])
    registry.get_skill = AsyncMock(
        return_value={
            "name": "document_analyzer",
            "version": "1.0.0",
            "status": "active",
        }
    )
    registry.create_skill = AsyncMock(return_value={"name": "new_skill", "status": "pending"})
    registry.update_skill = AsyncMock(return_value={"name": "updated_skill"})
    registry.delete_skill = AsyncMock(return_value=True)
    return registry


@pytest.fixture
def mock_skill_lifecycle_api() -> AsyncMock:
    """Mock SkillLifecycleAPI service."""
    api = AsyncMock()
    api.activate_skill = AsyncMock(return_value={"status": "active"})
    api.deactivate_skill = AsyncMock(return_value={"status": "inactive"})
    api.get_skill_metrics = AsyncMock(return_value={"invocations": 1024})
    api.get_activation_history = AsyncMock(return_value={"events": []})
    return api


@pytest.fixture
def mock_tool_composer() -> AsyncMock:
    """Mock ToolComposer service."""
    composer = AsyncMock()
    composer.authorize_tool = AsyncMock(return_value={"authorized": True})
    composer.revoke_tool = AsyncMock(return_value={"revoked": True})
    composer.list_authorized_tools = AsyncMock(return_value=[])
    return composer


# ============================================================================
# Feature 99.2: Agent Monitoring Fixtures
# ============================================================================


@pytest.fixture
def sample_agent_message() -> dict[str, Any]:
    """Sample agent message from MessageBus."""
    return {
        "id": str(uuid4()),
        "type": "SKILL_REQUEST",
        "sender_id": "coordinator_1",
        "receiver_id": "worker_3",
        "payload": {
            "skill_name": "document_analyzer",
            "parameters": {"document_id": "doc_123"},
        },
        "timestamp": datetime.now(UTC).isoformat(),
        "priority": "high",
        "status": "delivered",
    }


@pytest.fixture
def sample_blackboard_state() -> dict[str, Any]:
    """Sample blackboard state snapshot."""
    return {
        "namespace": "skill_execution_state",
        "data": {
            "active_skills": ["skill_1", "skill_2"],
            "pending_requests": 5,
            "last_update": datetime.now(UTC).isoformat(),
            "agent_id": "executor_1",
        },
    }


@pytest.fixture
def sample_orchestration() -> dict[str, Any]:
    """Sample orchestration record."""
    return {
        "id": str(uuid4()),
        "name": "document_processing_flow",
        "phase": "skill_execution",
        "status": "running",
        "agents_involved": ["coordinator", "manager_1", "worker_1", "worker_2"],
        "skills_invoked": ["document_analyzer", "entity_extractor"],
        "started_at": datetime.now(UTC).isoformat(),
        "estimated_completion": (datetime.now(UTC) + timedelta(seconds=30)).isoformat(),
    }


@pytest.fixture
def sample_orchestration_trace() -> dict[str, Any]:
    """Sample orchestration execution trace."""
    now = datetime.now(UTC)
    return {
        "orchestration_id": str(uuid4()),
        "timeline": [
            {
                "timestamp": now.isoformat(),
                "event": "orchestration_started",
                "agent_id": "coordinator",
                "details": {"phase": "initialization"},
            },
            {
                "timestamp": (now + timedelta(seconds=2)).isoformat(),
                "event": "skill_delegated",
                "agent_id": "manager_1",
                "details": {"skill": "document_analyzer", "worker": "worker_1"},
            },
            {
                "timestamp": (now + timedelta(seconds=5)).isoformat(),
                "event": "skill_completed",
                "agent_id": "worker_1",
                "details": {"skill": "document_analyzer", "status": "success"},
            },
        ],
    }


@pytest.fixture
def sample_communication_metrics() -> dict[str, Any]:
    """Sample communication metrics."""
    return {
        "total_messages": 1543,
        "total_latency_ms": 378234,
        "p50_latency_ms": 198,
        "p95_latency_ms": 450,
        "p99_latency_ms": 820,
        "throughput_mps": 25.7,
        "error_rate": 0.002,
        "time_window": "5m",
    }


@pytest.fixture
def sample_hierarchy_tree() -> dict[str, Any]:
    """Sample agent hierarchy tree (D3.js format)."""
    return {
        "name": "coordinator",
        "agent_id": "coordinator_1",
        "level": "executive",
        "skills": ["task_routing", "delegation"],
        "children": [
            {
                "name": "manager",
                "agent_id": "manager_1",
                "level": "manager",
                "skills": ["task_coordination", "resource_allocation"],
                "children": [
                    {
                        "name": "worker",
                        "agent_id": "worker_1",
                        "level": "worker",
                        "skills": ["document_analyzer"],
                        "children": [],
                    },
                    {
                        "name": "worker",
                        "agent_id": "worker_2",
                        "level": "worker",
                        "skills": ["entity_extractor"],
                        "children": [],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_agent_details() -> dict[str, Any]:
    """Sample agent details."""
    return {
        "agent_id": "worker_1",
        "name": "Document Analysis Worker",
        "level": "worker",
        "status": "online",
        "current_tasks": 2,
        "completed_tasks": 456,
        "failed_tasks": 3,
        "avg_task_duration_ms": 234,
        "success_rate": 0.9934,
        "assigned_skills": ["document_analyzer"],
        "last_heartbeat": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_task_delegation_chain() -> dict[str, Any]:
    """Sample task delegation chain."""
    now = datetime.now(UTC)
    return {
        "task_id": str(uuid4()),
        "delegation_chain": [
            {
                "hop": 1,
                "agent_id": "coordinator",
                "timestamp": now.isoformat(),
                "action": "received",
                "duration_ms": 0,
            },
            {
                "hop": 2,
                "agent_id": "manager_1",
                "timestamp": (now + timedelta(milliseconds=100)).isoformat(),
                "action": "delegated",
                "duration_ms": 100,
            },
            {
                "hop": 3,
                "agent_id": "worker_1",
                "timestamp": (now + timedelta(milliseconds=200)).isoformat(),
                "action": "executed",
                "duration_ms": 200,
            },
        ],
    }


@pytest.fixture
def mock_message_bus() -> AsyncMock:
    """Mock MessageBus service."""
    bus = AsyncMock()
    bus.list_messages = AsyncMock(return_value=[])
    bus.get_message = AsyncMock(return_value={"id": "msg_123"})
    bus.send_message = AsyncMock(return_value={"id": "msg_456"})
    return bus


@pytest.fixture
def mock_blackboard() -> AsyncMock:
    """Mock Blackboard service."""
    board = AsyncMock()
    board.get_all_namespaces = AsyncMock(return_value=["namespace_1", "namespace_2"])
    board.get_namespace = AsyncMock(return_value={"data": {}})
    board.write_state = AsyncMock(return_value=True)
    return board


@pytest.fixture
def mock_agent_hierarchy() -> AsyncMock:
    """Mock AgentHierarchy service."""
    hierarchy = AsyncMock()
    hierarchy.get_tree = AsyncMock(return_value={"name": "coordinator"})
    hierarchy.get_agent_details = AsyncMock(return_value={"agent_id": "agent_1"})
    hierarchy.get_current_tasks = AsyncMock(return_value=[])
    return hierarchy


@pytest.fixture
def mock_skill_orchestrator() -> AsyncMock:
    """Mock SkillOrchestrator service."""
    orchestrator = AsyncMock()
    orchestrator.list_active_orchestrations = AsyncMock(return_value=[])
    orchestrator.get_orchestration_trace = AsyncMock(return_value={"timeline": []})
    orchestrator.get_metrics = AsyncMock(return_value={})
    return orchestrator


# ============================================================================
# Feature 99.3: GDPR & Compliance Fixtures
# ============================================================================


@pytest.fixture
def sample_consent() -> dict[str, Any]:
    """Sample GDPR consent record."""
    return {
        "id": str(uuid4()),
        "data_subject_id": "user_123",
        "legal_basis": "consent",
        "data_categories": ["identifier", "contact"],
        "purpose": "Processing customer support requests",
        "processing_description": "Customer data used for support ticket creation and resolution",
        "third_parties": ["support_team"],
        "retention_period_days": 90,
        "given_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
        "status": "active",
        "version": 1,
    }


@pytest.fixture
def sample_consent_list_response() -> dict[str, Any]:
    """Sample paginated consent list response."""
    return {
        "items": [
            {
                "id": str(uuid4()),
                "data_subject_id": "user_123",
                "legal_basis": "consent",
                "status": "active",
                "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
            },
            {
                "id": str(uuid4()),
                "data_subject_id": "user_456",
                "legal_basis": "contract",
                "status": "active",
                "expires_at": None,
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


@pytest.fixture
def sample_data_subject_request() -> dict[str, Any]:
    """Sample data subject request (GDPR Art. 15-22)."""
    return {
        "id": str(uuid4()),
        "data_subject_id": "user_123",
        "request_type": "access",
        "description": "Please provide all personal data you hold about me",
        "status": "pending",
        "submitted_at": datetime.now(UTC).isoformat(),
        "deadline": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        "data_formats": ["json", "csv"],
        "reasoning": "Data subject rights request",
    }


@pytest.fixture
def sample_processing_activity() -> dict[str, Any]:
    """Sample processing activity (GDPR Art. 30)."""
    return {
        "id": str(uuid4()),
        "skill_name": "document_analyzer",
        "purpose": "Analyzing customer documents for insights",
        "legal_basis": "legitimate_interests",
        "data_categories": ["identifier", "document_content"],
        "recipients": ["analysis_team", "ml_model"],
        "retention_period_days": 180,
        "controller": "Data Controller Name",
        "processor": "Data Processor Name",
        "established_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


@pytest.fixture
def sample_pii_settings() -> dict[str, Any]:
    """Sample PII detection settings."""
    return {
        "detection_enabled": True,
        "auto_redaction_enabled": True,
        "detection_threshold": 0.8,
        "pii_categories": [
            "email_address",
            "phone_number",
            "credit_card",
            "ssn",
            "name",
            "date_of_birth",
        ],
        "redaction_method": "mask",
        "mask_character": "*",
        "log_detections": True,
        "notify_on_high_confidence": True,
    }


@pytest.fixture
def mock_gdpr_consent_manager() -> AsyncMock:
    """Mock GDPRConsentManager service."""
    manager = AsyncMock()
    manager.list_consents = AsyncMock(return_value=[])
    manager.create_consent = AsyncMock(return_value={"id": "consent_123"})
    manager.update_consent = AsyncMock(return_value={"id": "consent_123"})
    manager.withdraw_consent = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_data_subject_rights_handler() -> AsyncMock:
    """Mock DataSubjectRightsHandler service."""
    handler = AsyncMock()
    handler.create_request = AsyncMock(return_value={"id": "request_123"})
    handler.approve_request = AsyncMock(return_value={"status": "approved"})
    handler.reject_request = AsyncMock(return_value={"status": "rejected"})
    handler.get_request_details = AsyncMock(return_value={"id": "request_123"})
    return handler


@pytest.fixture
def mock_processing_activity_logger() -> AsyncMock:
    """Mock ProcessingActivityLogger service."""
    logger = AsyncMock()
    logger.list_activities = AsyncMock(return_value=[])
    logger.log_activity = AsyncMock(return_value={"id": "activity_123"})
    return logger


@pytest.fixture
def mock_pii_detection_settings() -> AsyncMock:
    """Mock PIIDetectionSettings service."""
    settings = AsyncMock()
    settings.get_settings = AsyncMock(return_value={"detection_enabled": True})
    settings.update_settings = AsyncMock(return_value={"detection_enabled": True})
    return settings


# ============================================================================
# Feature 99.4: Audit Trail Fixtures
# ============================================================================


@pytest.fixture
def sample_audit_event() -> dict[str, Any]:
    """Sample audit event."""
    return {
        "id": str(uuid4()),
        "type": "data_access",
        "outcome": "success",
        "actor_id": "user_123",
        "actor_type": "user",
        "timestamp": datetime.now(UTC).isoformat(),
        "resource": "document_123",
        "action": "read",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0...",
        "payload": {
            "document_id": "document_123",
            "page_count": 15,
        },
        "hash": "abc123def456",
        "prev_hash": "xyz789uvw012",
    }


@pytest.fixture
def sample_audit_event_list_response() -> dict[str, Any]:
    """Sample paginated audit event list response."""
    return {
        "items": [
            {
                "id": str(uuid4()),
                "type": "auth_login",
                "outcome": "success",
                "actor_id": "user_123",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            {
                "id": str(uuid4()),
                "type": "data_access",
                "outcome": "success",
                "actor_id": "user_123",
                "timestamp": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


@pytest.fixture
def sample_compliance_report() -> dict[str, Any]:
    """Sample compliance report."""
    return {
        "report_type": "gdpr_compliance",
        "generated_at": datetime.now(UTC).isoformat(),
        "date_range": {
            "start": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
            "end": datetime.now(UTC).isoformat(),
        },
        "summary": {
            "total_consents": 1542,
            "active_consents": 1480,
            "expired_consents": 62,
            "pending_requests": 3,
            "approved_requests": 28,
            "rejected_requests": 5,
        },
        "details": {
            "consent_breakdown": {
                "consent": 800,
                "contract": 450,
                "legal_obligation": 200,
                "legitimate_interests": 92,
            },
            "request_types": {
                "access": 15,
                "erasure": 8,
                "rectification": 3,
                "portability": 2,
                "restriction": 3,
                "objection": 1,
            },
        },
    }


@pytest.fixture
def sample_integrity_verification() -> dict[str, Any]:
    """Sample integrity verification result."""
    return {
        "valid": True,
        "total_events": 5000,
        "verified_events": 5000,
        "broken_indices": [],
        "last_verified": datetime.now(UTC).isoformat(),
        "verification_duration_ms": 1234,
        "chain_integrity_score": 1.0,
    }


@pytest.fixture
def mock_audit_trail_system() -> AsyncMock:
    """Mock AuditTrailSystem service."""
    system = AsyncMock()
    system.list_events = AsyncMock(return_value=[])
    system.get_event = AsyncMock(return_value={"id": "event_123"})
    system.log_event = AsyncMock(return_value={"id": "event_456"})
    return system


@pytest.fixture
def mock_cryptographic_chain() -> AsyncMock:
    """Mock CryptographicChain service."""
    chain = AsyncMock()
    chain.verify_chain = AsyncMock(return_value={"valid": True})
    chain.get_chain_hash = AsyncMock(return_value="abc123def456")
    return chain


@pytest.fixture
def mock_compliance_report_generator() -> AsyncMock:
    """Mock ComplianceReportGenerator service."""
    generator = AsyncMock()
    generator.generate_report = AsyncMock(
        return_value={
            "report_type": "gdpr_compliance",
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )
    return generator


# ============================================================================
# Common Fixtures
# ============================================================================


@pytest.fixture
def auth_headers(admin_jwt_token) -> dict[str, str]:
    """Authorization headers with admin token."""
    return {"Authorization": admin_jwt_token}


@pytest.fixture
def user_auth_headers(user_jwt_token) -> dict[str, str]:
    """Authorization headers with user token."""
    return {"Authorization": user_jwt_token}


@pytest.fixture
def pagination_params() -> dict[str, int]:
    """Standard pagination parameters."""
    return {"page": 1, "page_size": 20}


@pytest.fixture
def time_range_params() -> dict[str, str]:
    """Standard time range parameters."""
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=30)
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
