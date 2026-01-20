"""Enhanced Domain Data Augmentation API Endpoint (Sprint 117.4).

This module provides the enhanced /augment endpoint with multiple strategies,
quality metrics, and comprehensive augmentation capabilities.
"""

import httpx
import structlog
from fastapi import APIRouter, HTTPException, status

from src.api.v1.domain_augmentation_models import (
    AugmentationRequestV2,
    AugmentationResponseV2,
    GenerationSummaryV2,
    QualityMetricsV2,
)
from src.components.domain_training.augmentation_service import (
    AugmentationStrategy,
    get_augmentation_service,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/domains", tags=["domain-training"])


@router.post("/augment-v2", response_model=AugmentationResponseV2)
async def augment_training_data_v2(request: AugmentationRequestV2) -> AugmentationResponseV2:
    """Generate enhanced training data with multiple strategies (Sprint 117.4).

    This enhanced endpoint provides:
    - Multiple augmentation strategies (paraphrase, entity substitution, back translation, synthetic, hybrid)
    - Quality metrics (diversity score, entity coverage, relation coverage, duplicate rate)
    - Duplicate detection using embedding similarity
    - Comprehensive job tracking

    Augmentation Strategies:
    1. **paraphrase_and_vary**: Rephrase while preserving entities (default, 70% of samples)
    2. **entity_substitution**: Replace entities with synonyms (20% of samples)
    3. **back_translation**: EN→DE→EN for variation (5% of samples)
    4. **synthetic_documents**: Generate new from patterns (5% of samples)
    5. **hybrid**: Combination of above strategies (auto-balanced)

    Quality Metrics:
    - **Diversity Score**: Average pairwise cosine distance (target: >0.8)
    - **Entity Coverage**: Fraction of entity types present (target: >0.9)
    - **Relation Coverage**: Fraction of relation types present (target: >0.85)
    - **Duplicate Rate**: Fraction of near-duplicates (target: <0.05)

    Args:
        request: Augmentation request with domain, seed samples, strategy, and configuration

    Returns:
        AugmentationResponseV2 with generated samples, quality metrics, and job tracking

    Raises:
        HTTPException 400: If less than 5 seed samples or invalid parameters
        HTTPException 503: If Ollama service is not available
        HTTPException 500: If generation fails

    Example:
        >>> response = client.post("/admin/domains/augment-v2", json={
        ...     "domain_name": "medical",
        ...     "seed_samples": [
        ...         {
        ...             "text": "Patient with Type 2 diabetes and hypertension",
        ...             "entities": [
        ...                 {"text": "Type 2 diabetes", "type": "Disease"},
        ...                 {"text": "hypertension", "type": "Disease"}
        ...             ],
        ...             "relations": [
        ...                 {"source": "Type 2 diabetes", "target": "hypertension", "type": "CO_OCCURS_WITH"}
        ...             ]
        ...         },
        ...         # ... more seed samples ...
        ...     ],
        ...     "target_count": 100,
        ...     "augmentation_strategy": "hybrid",
        ...     "temperature": 0.7
        ... })
        >>> print(f"Job ID: {response.json()['augmentation_job_id']}")
        >>> print(f"Generated {response.json()['generated_count']} samples")
        >>> print(f"Diversity: {response.json()['quality_metrics']['diversity_score']}")
    """
    logger.info(
        "augment_training_data_v2_request",
        domain_name=request.domain_name,
        seed_count=len(request.seed_samples),
        target_count=request.target_count,
        strategy=request.augmentation_strategy,
        temperature=request.temperature,
    )

    try:
        # Get augmentation service
        service = get_augmentation_service()

        # Map strategy string to enum
        try:
            strategy = AugmentationStrategy(request.augmentation_strategy)
        except ValueError:
            raise ValueError(
                f"Invalid strategy: {request.augmentation_strategy}. "
                f"Valid options: paraphrase_and_vary, entity_substitution, "
                f"back_translation, synthetic_documents, hybrid"
            )

        # Run augmentation
        result = await service.augment(
            domain_name=request.domain_name,
            seed_samples=request.seed_samples,
            target_count=request.target_count,
            strategy=strategy,
            temperature=request.temperature,
        )

        logger.info(
            "augmentation_v2_completed",
            job_id=result.augmentation_job_id,
            domain_name=request.domain_name,
            generated_count=result.generated_count,
            status=result.status,
            diversity_score=result.quality_metrics.diversity_score,
            entity_coverage=result.quality_metrics.entity_coverage,
            duplicate_rate=result.quality_metrics.duplicate_rate,
            processing_time_ms=result.processing_time_ms,
        )

        # Convert to API response format
        return AugmentationResponseV2(
            augmentation_job_id=result.augmentation_job_id,
            domain_name=result.domain_name,
            seed_count=result.seed_count,
            target_count=result.target_count,
            generated_count=result.generated_count,
            status=result.status,
            generation_summary=GenerationSummaryV2(
                paraphrases=result.generation_summary.paraphrases,
                entity_substitutions=result.generation_summary.entity_substitutions,
                back_translations=result.generation_summary.back_translations,
                synthetic_documents=result.generation_summary.synthetic_documents,
            ),
            quality_metrics=QualityMetricsV2(
                diversity_score=result.quality_metrics.diversity_score,
                entity_coverage=result.quality_metrics.entity_coverage,
                relation_coverage=result.quality_metrics.relation_coverage,
                duplicate_rate=result.quality_metrics.duplicate_rate,
            ),
            sample_outputs=[s.dict() for s in result.sample_outputs],
            created_at=result.created_at.isoformat(),
            completed_at=result.completed_at.isoformat() if result.completed_at else None,
            processing_time_ms=result.processing_time_ms,
        )

    except ValueError as e:
        # Invalid parameters (less than 5 seed samples, invalid strategy, etc.)
        logger.warning(
            "augmentation_v2_validation_error",
            domain_name=request.domain_name,
            seed_count=len(request.seed_samples),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except httpx.ConnectError as e:
        logger.error(
            "augmentation_v2_ollama_connection_error",
            domain_name=request.domain_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is not available. Please check if Ollama is running.",
        ) from e

    except httpx.HTTPStatusError as e:
        logger.error(
            "augmentation_v2_ollama_http_error",
            domain_name=request.domain_name,
            status_code=e.response.status_code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama API error: {e.response.status_code}",
        ) from e

    except Exception as e:
        logger.error(
            "augmentation_v2_unexpected_error",
            domain_name=request.domain_name,
            seed_count=len(request.seed_samples),
            target_count=request.target_count,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data augmentation failed: {str(e)}",
        ) from e
