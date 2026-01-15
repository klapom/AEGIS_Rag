"""API Models for AegisRAG.

Sprint 31 Feature 31.10a: Cost API Backend Implementation
Sprint 37 Feature 37.5: Pipeline Progress SSE Schema
Sprint 62 Feature 62.9: Section Analytics Endpoint
Sprint 99 Feature 99.3/99.4: GDPR & Audit API Models
"""

from src.api.models.analytics import (
    SectionAnalyticsRequest,
    SectionAnalyticsResponse,
    SectionStats,
)
from src.api.models.audit_models import (
    AuditEvent,
    AuditEventListResponse,
    AuditEventTypeEnum,
    AuditReportResponse,
    AuditReportSummary,
    GDPRComplianceReportData,
    IntegrityCheckResponse,
    OutcomeEnum,
    ReportTypeEnum,
    SecurityAuditReportData,
    SkillUsageReportData,
)
from src.api.models.cost_stats import (
    BudgetStatus,
    CostHistory,
    CostStats,
    ModelCost,
    ProviderCost,
)
from src.api.models.gdpr_models import (
    ConsentCreateRequest,
    ConsentListResponse,
    ConsentRecord,
    ConsentStatusEnum,
    ConsentUpdateRequest,
    DataCategoryEnum,
    DataSubjectRequestCreate,
    DataSubjectRequestResponse,
    LegalBasisEnum,
    PIISettingsResponse,
    PIISettingsUpdate,
    ProcessingActivity,
    ProcessingActivityResponse,
    RequestStatusEnum,
    RequestTypeEnum,
)
from src.api.models.pipeline_progress import (
    MetricsSchema,
    PipelineProgressEvent,
    PipelineProgressEventData,
    StageProgressSchema,
    TimingSchema,
    WorkerInfoSchema,
    WorkerPoolSchema,
)

__all__ = [
    # Analytics models
    "SectionAnalyticsRequest",
    "SectionAnalyticsResponse",
    "SectionStats",
    # Cost stats models
    "BudgetStatus",
    "CostHistory",
    "CostStats",
    "ModelCost",
    "ProviderCost",
    # Pipeline progress models
    "PipelineProgressEvent",
    "PipelineProgressEventData",
    "StageProgressSchema",
    "WorkerInfoSchema",
    "WorkerPoolSchema",
    "MetricsSchema",
    "TimingSchema",
    # GDPR models (Sprint 99 Feature 99.3)
    "ConsentCreateRequest",
    "ConsentListResponse",
    "ConsentRecord",
    "ConsentStatusEnum",
    "ConsentUpdateRequest",
    "DataCategoryEnum",
    "DataSubjectRequestCreate",
    "DataSubjectRequestResponse",
    "LegalBasisEnum",
    "PIISettingsResponse",
    "PIISettingsUpdate",
    "ProcessingActivity",
    "ProcessingActivityResponse",
    "RequestStatusEnum",
    "RequestTypeEnum",
    # Audit models (Sprint 99 Feature 99.4)
    "AuditEvent",
    "AuditEventListResponse",
    "AuditEventTypeEnum",
    "AuditReportResponse",
    "AuditReportSummary",
    "GDPRComplianceReportData",
    "IntegrityCheckResponse",
    "OutcomeEnum",
    "ReportTypeEnum",
    "SecurityAuditReportData",
    "SkillUsageReportData",
]
