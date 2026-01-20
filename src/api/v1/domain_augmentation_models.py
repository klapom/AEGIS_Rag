"""Pydantic models for Domain Data Augmentation API (Sprint 117.4).

This module defines request/response models for the enhanced data augmentation endpoint.
"""

from pydantic import BaseModel, Field


class AugmentationRequestV2(BaseModel):
    """Request for enhanced data augmentation (Sprint 117.4).

    Provides seed samples and configuration for LLM-based generation of
    additional training data using multiple strategies.
    """

    domain_name: str = Field(..., description="Domain name for augmentation")
    seed_samples: list[dict] = Field(
        ...,
        min_items=5,
        description="5+ high-quality seed samples with text, entities, and relations",
    )
    target_count: int = Field(
        default=100,
        ge=5,
        le=1000,
        description="Number of samples to generate (5-1000)",
    )
    augmentation_strategy: str = Field(
        default="paraphrase_and_vary",
        description="Augmentation strategy",
        examples=[
            "paraphrase_and_vary",
            "entity_substitution",
            "back_translation",
            "synthetic_documents",
            "hybrid",
        ],
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=1.0, description="LLM temperature for diversity"
    )


class GenerationSummaryV2(BaseModel):
    """Summary of generation methods used."""

    paraphrases: int = Field(default=0, description="Paraphrase samples")
    entity_substitutions: int = Field(default=0, description="Entity substitution samples")
    back_translations: int = Field(default=0, description="Back translation samples")
    synthetic_documents: int = Field(default=0, description="Synthetic samples")


class QualityMetricsV2(BaseModel):
    """Quality metrics for augmented dataset."""

    diversity_score: float = Field(..., ge=0.0, le=1.0, description="Average pairwise distance")
    entity_coverage: float = Field(..., ge=0.0, le=1.0, description="Entity type coverage")
    relation_coverage: float = Field(..., ge=0.0, le=1.0, description="Relation type coverage")
    duplicate_rate: float = Field(..., ge=0.0, le=1.0, description="Near-duplicate rate")


class AugmentationResponseV2(BaseModel):
    """Response from enhanced data augmentation (Sprint 117.4).

    Contains generated samples, quality metrics, and job tracking information.
    """

    augmentation_job_id: str = Field(..., description="Unique job ID")
    domain_name: str = Field(..., description="Domain name")
    seed_count: int = Field(..., description="Number of seed samples")
    target_count: int = Field(..., description="Target sample count")
    generated_count: int = Field(..., description="Actual generated count")
    status: str = Field(..., description="Job status (completed/partial/failed)")
    generation_summary: GenerationSummaryV2 = Field(..., description="Generation breakdown")
    quality_metrics: QualityMetricsV2 = Field(..., description="Quality metrics")
    sample_outputs: list[dict] = Field(default_factory=list, description="Sample outputs (first 5)")
    created_at: str = Field(..., description="Job start time (ISO 8601)")
    completed_at: str | None = Field(None, description="Job completion time (ISO 8601)")
    processing_time_ms: int | None = Field(None, description="Processing time in ms")
