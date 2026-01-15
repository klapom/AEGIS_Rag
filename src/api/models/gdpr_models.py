"""Pydantic models for GDPR API.

Sprint 99 Feature 99.3: GDPR & Compliance APIs (12 SP)
Implements GDPR Article 6,7,13-22,30 compliance for EU legal requirements.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class LegalBasisEnum(str, Enum):
    """GDPR Article 6 legal bases for processing personal data."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataCategoryEnum(str, Enum):
    """GDPR personal data categories."""

    # Standard personal data (Article 4(1))
    IDENTIFIER = "identifier"
    CONTACT = "contact"
    FINANCIAL = "financial"
    HEALTH = "health"
    BEHAVIORAL = "behavioral"
    BIOMETRIC = "biometric"
    LOCATION = "location"
    DEMOGRAPHIC = "demographic"
    PROFESSIONAL = "professional"
    OTHER = "other"


class RequestTypeEnum(str, Enum):
    """GDPR Article 15-22 data subject rights."""

    ACCESS = "access"  # Article 15: Right of access
    ERASURE = "erasure"  # Article 17: Right to erasure
    RECTIFICATION = "rectification"  # Article 16: Right to rectification
    PORTABILITY = "portability"  # Article 20: Right to data portability
    RESTRICTION = "restriction"  # Article 18: Right to restriction
    OBJECTION = "objection"  # Article 21: Right to object


class ConsentStatusEnum(str, Enum):
    """Consent record status."""

    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class RequestStatusEnum(str, Enum):
    """Data subject request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


# Request Models


class ConsentCreateRequest(BaseModel):
    """Request model for creating a consent record."""

    user_id: str = Field(..., description="Data subject user ID")
    purpose: str = Field(..., description="Specific purpose for processing")
    legal_basis: LegalBasisEnum = Field(..., description="GDPR Article 6 legal basis")
    data_categories: List[DataCategoryEnum] = Field(
        ..., min_length=1, description="Categories of personal data"
    )
    retention_period: Optional[int] = Field(
        None, ge=1, description="Retention period in days"
    )
    explicit_consent: bool = Field(
        True, description="Whether explicit consent was obtained"
    )

    @field_validator("retention_period")
    @classmethod
    def validate_retention_period(cls, v: Optional[int]) -> Optional[int]:
        """Validate retention period is reasonable."""
        if v is not None and v > 3650:  # 10 years
            raise ValueError("Retention period cannot exceed 10 years (3650 days)")
        return v


class ConsentUpdateRequest(BaseModel):
    """Request model for updating a consent record."""

    withdrawn: bool = Field(False, description="Withdraw consent")
    withdrawal_reason: Optional[str] = Field(None, description="Reason for withdrawal")


class DataSubjectRequestCreate(BaseModel):
    """Request model for creating a data subject request."""

    request_type: RequestTypeEnum = Field(..., description="Type of request")
    user_id: str = Field(..., description="Data subject user ID")
    details: Optional[str] = Field(None, description="Additional request details")


class PIISettingsUpdate(BaseModel):
    """Request model for updating PII detection settings."""

    entity_types: Optional[List[str]] = Field(
        None, description="PII entity types to detect"
    )
    confidence_threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Detection confidence threshold"
    )
    anonymization_rules: Optional[Dict[str, str]] = Field(
        None, description="Anonymization rules for PII categories"
    )


# Response Models


class ConsentRecord(BaseModel):
    """Consent record response model."""

    consent_id: str
    user_id: str
    purpose: str
    legal_basis: LegalBasisEnum
    data_categories: List[DataCategoryEnum]
    granted_at: datetime
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    status: ConsentStatusEnum
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsentListResponse(BaseModel):
    """Paginated list of consent records."""

    items: List[ConsentRecord]
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of consents")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class DataSubjectRequestResponse(BaseModel):
    """Data subject request response model."""

    request_id: str
    request_type: RequestTypeEnum
    user_id: str
    status: RequestStatusEnum
    details: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    response_data: Optional[Dict[str, Any]] = None


class ProcessingActivity(BaseModel):
    """Processing activity record (Article 30)."""

    record_id: str
    controller_name: str
    processing_purpose: str
    legal_basis: LegalBasisEnum
    data_categories: List[DataCategoryEnum]
    data_subjects: List[str]
    recipients: List[str]
    retention_period: Optional[str] = None
    security_measures: List[str]
    processed_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessingActivityResponse(BaseModel):
    """List of processing activities."""

    activities: List[ProcessingActivity]
    total: int = Field(..., ge=0, description="Total number of activities")


class PIISettingsResponse(BaseModel):
    """PII detection settings response."""

    entity_types: List[str] = Field(
        default_factory=lambda: [
            "PERSON",
            "EMAIL",
            "PHONE",
            "SSN",
            "CREDIT_CARD",
            "IBAN",
            "IP_ADDRESS",
        ]
    )
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    anonymization_rules: Dict[str, str] = Field(
        default_factory=lambda: {
            "identifier": "[REDACTED_ID]",
            "contact": "[REDACTED_CONTACT]",
            "financial": "[REDACTED_FINANCIAL]",
            "health": "[REDACTED_HEALTH]",
        }
    )
