"""Domain Override Models for Manual Domain Classification.

Sprint 117 Feature 117.11: Manual Domain Override.

This module provides Pydantic models for manual domain override functionality,
allowing users to override automatically detected domain classifications.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DomainOverrideRequest(BaseModel):
    """Request model for manually overriding document domain classification.

    Sprint 117 Feature 117.11: Manual domain override.
    """

    domain_id: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="New domain ID to assign to the document",
        examples=["medical", "legal", "tech_docs"],
    )
    reason: str | None = Field(
        None,
        max_length=500,
        description="Optional reason for overriding the domain classification",
        examples=["Document contains medical terminology not detected by classifier"],
    )
    reprocess_extraction: bool = Field(
        default=False,
        description="Whether to re-run entity extraction with new domain prompts",
    )


class DomainInfo(BaseModel):
    """Domain information for override response.

    Sprint 117 Feature 117.11: Domain information structure.
    """

    domain_id: str = Field(..., description="Domain ID")
    domain_name: str = Field(..., description="Human-readable domain name")
    confidence: float | None = Field(
        None,
        description="Classification confidence (0.0-1.0) if applicable",
        ge=0.0,
        le=1.0,
    )
    classification_path: str = Field(
        ...,
        description="Classification path (auto, manual_override, fallback)",
        examples=["auto", "manual_override", "fallback"],
    )
    overridden_by: str | None = Field(
        None,
        description="User who overrode the domain (future: user_id)",
        examples=["admin", "user_123"],
    )
    overridden_at: datetime | None = Field(
        None,
        description="Timestamp when domain was overridden",
    )


class ReprocessingInfo(BaseModel):
    """Reprocessing information for domain override response.

    Sprint 117 Feature 117.11: Reprocessing status tracking.
    """

    status: str = Field(
        ...,
        description="Reprocessing status (pending, processing, completed, failed)",
        examples=["pending", "processing", "completed", "failed"],
    )
    job_id: str | None = Field(
        None,
        description="Background job ID for tracking reprocessing",
        examples=["job_abc123"],
    )


class DomainOverrideResponse(BaseModel):
    """Response model for domain override operation.

    Sprint 117 Feature 117.11: Manual domain override response.
    """

    document_id: str = Field(..., description="Document ID that was updated")
    previous_domain: DomainInfo = Field(..., description="Previous domain classification")
    new_domain: DomainInfo = Field(..., description="New domain classification")
    reprocessing: ReprocessingInfo | None = Field(
        None,
        description="Reprocessing information if reprocess_extraction=True",
    )
