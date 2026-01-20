"""Upload-related Pydantic models.

Sprint 117 Feature 117.10: Domain Classification Display in Upload Dialog.
"""

from pydantic import BaseModel, Field


class DomainClassificationResult(BaseModel):
    """Domain classification result for uploaded document.

    Sprint 117 Feature 117.10: Display domain classification after upload.
    """

    domain_id: str = Field(..., description="Classified domain ID")
    domain_name: str = Field(..., description="Human-readable domain name")
    confidence: float = Field(..., description="Classification confidence (0.0-1.0)", ge=0.0, le=1.0)
    classification_path: str = Field(
        ...,
        description="Classification path used (fast, verified, fallback)",
    )
    latency_ms: int = Field(..., description="Classification latency in milliseconds", ge=0)
    model_used: str = Field(..., description="Model used for classification")
    matched_entity_types: list[str] = Field(
        default_factory=list,
        description="Entity types matched in document",
    )
    matched_intent: str | None = Field(
        None,
        description="Matched intent classification",
    )
    requires_review: bool = Field(
        False,
        description="Whether classification requires manual review (low confidence)",
    )
    alternatives: list[dict[str, str | float]] = Field(
        default_factory=list,
        description="Alternative domain classifications with scores",
    )


class ExtractionSummary(BaseModel):
    """Extraction summary for uploaded document.

    Sprint 117 Feature 117.10: Display extraction statistics after upload.
    """

    entities_count: int = Field(..., description="Number of entities extracted", ge=0)
    relations_count: int = Field(..., description="Number of relations extracted", ge=0)
    chunks_count: int = Field(..., description="Number of chunks created", ge=0)
    mentioned_in_count: int = Field(
        ...,
        description="Number of MENTIONED_IN relations created",
        ge=0,
    )
