"""Pydantic models for Audit Trail API.

Sprint 99 Feature 99.4: Audit Trail APIs (8 SP)
Implements EU AI Act Article 12 compliance with SHA-256 cryptographic chain.

Sprint 100 Fix #4: ISO 8601 datetime serialization with Z suffix.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer


class AuditEventTypeEnum(str, Enum):
    """Audit event type taxonomy."""

    # Authentication
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"

    # Data operations
    DATA_ACCESS = "data_access"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"

    # Skill operations
    SKILL_EXECUTE = "skill_execute"
    SKILL_DELEGATE = "skill_delegate"

    # Policy enforcement
    POLICY_VIOLATION = "policy_violation"
    POLICY_ENFORCEMENT = "policy_enforcement"

    # GDPR compliance
    GDPR_REQUEST = "gdpr_request"
    GDPR_CONSENT = "gdpr_consent"

    # System operations
    SYSTEM_CONFIG = "system_config"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    SYSTEM_ERROR = "system_error"
    SYSTEM_SECURITY = "system_security"


class OutcomeEnum(str, Enum):
    """Event outcome status."""

    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    ERROR = "error"


class ReportTypeEnum(str, Enum):
    """Compliance report types."""

    GDPR_COMPLIANCE = "gdpr_compliance"
    SECURITY_AUDIT = "security_audit"
    SKILL_USAGE = "skill_usage"


# Response Models


class AuditEvent(BaseModel):
    """Audit event response model."""

    id: str
    timestamp: datetime
    event_type: AuditEventTypeEnum
    actor_id: str
    actor_type: str = Field(..., description="Actor type: human, agent, system")
    action: str = Field(..., description="Human-readable action description")
    outcome: OutcomeEnum
    metadata: Dict[str, Any] = Field(default_factory=dict)
    context_hash: Optional[str] = None
    output_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    event_hash: str = Field(..., description="SHA-256 hash of event")

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime, _info) -> str:
        """Serialize datetime to ISO 8601 with Z suffix (Sprint 100 Fix #4)."""
        return value.isoformat() + "Z" if not value.isoformat().endswith("Z") else value.isoformat()


class AuditEventListResponse(BaseModel):
    """Paginated list of audit events."""

    items: List[AuditEvent]
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of events")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class AuditReportSummary(BaseModel):
    """Summary section of audit report."""

    report_type: ReportTypeEnum
    start_time: datetime
    end_time: datetime
    generated_at: datetime
    total_events: int
    integrity_verified: bool
    integrity_errors: List[str] = Field(default_factory=list)

    @field_serializer("start_time", "end_time", "generated_at")
    def serialize_datetime(self, value: datetime, _info) -> str:
        """Serialize datetime to ISO 8601 with Z suffix (Sprint 100 Fix #4)."""
        return value.isoformat() + "Z" if not value.isoformat().endswith("Z") else value.isoformat()


class GDPRComplianceReportData(BaseModel):
    """GDPR compliance report data."""

    processing_activities: Dict[str, Any]


class SecurityAuditReportData(BaseModel):
    """Security audit report data."""

    security_summary: Dict[str, Any]


class SkillUsageReportData(BaseModel):
    """Skill usage report data."""

    skill_usage: Dict[str, Any]


class AuditReportResponse(BaseModel):
    """Audit report response."""

    report_type: ReportTypeEnum
    generated_at: datetime
    summary: AuditReportSummary
    events: List[AuditEvent]
    recommendations: List[str] = Field(default_factory=list)
    # Type-specific data
    data: Dict[str, Any] = Field(default_factory=dict)

    @field_serializer("generated_at")
    def serialize_datetime(self, value: datetime, _info) -> str:
        """Serialize datetime to ISO 8601 with Z suffix (Sprint 100 Fix #4)."""
        return value.isoformat() + "Z" if not value.isoformat().endswith("Z") else value.isoformat()


class IntegrityCheckResponse(BaseModel):
    """Audit trail integrity verification response."""

    is_valid: bool
    total_events: int
    verified_events: int
    chain_breaks: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of chain integrity violations",
    )
    last_verified_at: datetime
    verification_duration_ms: float = Field(..., description="Time taken to verify chain")

    @field_serializer("last_verified_at")
    def serialize_datetime(self, value: datetime, _info) -> str:
        """Serialize datetime to ISO 8601 with Z suffix (Sprint 100 Fix #4)."""
        return value.isoformat() + "Z" if not value.isoformat().endswith("Z") else value.isoformat()
