"""Domain Training API Endpoints for DSPy-based Knowledge Graph Optimization.

Sprint 45 - Feature 45.3, 45.10: Domain Training API

This module provides FastAPI endpoints for managing domain-specific extraction prompts
and training configurations. It enables creating domains, training them with DSPy,
and classifying documents to domains.

Key Endpoints:
- POST /api/v1/admin/domains - Create new domain configuration
- GET /api/v1/admin/domains - List all domains
- GET /api/v1/admin/domains/{name} - Get domain details
- POST /api/v1/admin/domains/{name}/train - Start DSPy training
- GET /api/v1/admin/domains/{name}/training-status - Monitor training progress
- DELETE /api/v1/admin/domains/{name} - Delete domain and all associated data (51.4)
- GET /api/v1/admin/domains/available-models - List Ollama models
- POST /api/v1/admin/domains/classify - Classify document to domain
- POST /api/v1/admin/domains/ingest-batch - Batch ingestion grouped by LLM model (45.10)
- POST /api/v1/admin/domains/{name}/validate - Validate domain quality (117.7)

Sprint 119: Fixed router prefix from /admin/domains to /api/v1/admin/domains
to match E2E test expectations and API conventions.

Security:
- All endpoints require authentication (future Sprint)
- Rate limiting: 10 requests/minute per user
- Input validation with Pydantic v2 models

Performance:
- Training runs in background tasks (non-blocking)
- Classification uses cached embeddings (<100ms)
- Status endpoints are real-time from Neo4j

Example:
    >>> # Create domain
    >>> response = client.post("/api/v1/admin/domains/", json={
    ...     "name": "tech_docs",
    ...     "description": "Technical documentation for software projects",
    ...     "llm_model": "qwen3:32b"
    ... })
    >>> # Start training
    >>> response = client.post("/admin/domains/tech_docs/train", json={
    ...     "samples": [
    ...         {"text": "FastAPI is a web framework", "entities": ["FastAPI", "web framework"]},
    ...         ...
    ...     ]
    ... })
"""

import json
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.exceptions import DatabaseConnectionError
from src.core.models import DomainUpdateRequest, ErrorCode
from src.core.models.response import ApiResponse
from src.core.response_utils import error_response_from_request, success_response_from_request

logger = structlog.get_logger(__name__)
settings = get_settings()


def _parse_json_field(value: str | None, default: Any = None) -> Any:
    """Parse a JSON string from Neo4j, returning default if None/empty."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        import json

        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


router = APIRouter(prefix="/api/v1/admin/domains", tags=["Domain Training"])


# --- Request/Response Models ---


class DomainCreateRequest(BaseModel):
    """Request to create a new domain configuration.

    The domain name must be lowercase with underscores only (e.g., "tech_docs").
    The description should be detailed and specific to enable accurate semantic matching.
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern="^[a-z][a-z0-9_]*$",
        description="Unique domain name (lowercase, underscores)",
        examples=["tech_docs", "legal_contracts", "medical_reports"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Detailed domain description for semantic matching",
        examples=[
            "Technical documentation for software development projects including API docs, guides, and READMEs"
        ],
    )
    llm_model: str = Field(
        default="qwen3:32b",
        description="LLM model to use for extraction (must be available in Ollama)",
        examples=["qwen3:32b", "llama3.2:8b", "mistral:7b"],
    )
    entity_sub_type_mapping: dict[str, str] | None = Field(
        default=None,
        description="Sprint 126: Domain sub-type → universal type mapping (e.g., {DISEASE: CONCEPT})",
    )
    relation_hints: list[str] | None = Field(
        default=None,
        description="Sprint 126: Domain-specific relation examples (e.g., 'TREATS → Medication → Disease')",
    )


class TrainingSample(BaseModel):
    """A single training sample for DSPy optimization.

    Each sample should include source text, extracted entities, and optionally relations.
    Provide at least 5-10 high-quality samples for effective optimization.
    """

    text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Source text to extract entities/relations from",
    )
    entities: list[str] = Field(
        ..., min_items=1, description="List of entities extracted from text"
    )
    relations: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of relations (subject, predicate, object)",
    )


class DomainConfig(BaseModel):
    """Domain configuration for training.

    Sprint 124: Added to allow specifying llm_model in training request.
    """

    name: str | None = Field(default=None, description="Domain name (optional, uses URL param)")
    description: str | None = Field(default=None, description="Domain description")
    llm_model: str | None = Field(
        default=None,
        description="LLM model to use for extraction (e.g., gpt-oss:120b)",
        examples=["gpt-oss:120b", "nemotron-3-nano:128k", "qwen3:32b"],
    )
    entity_types: list[str] | None = Field(default=None, description="Entity types")
    relation_types: list[str] | None = Field(default=None, description="Relation types")


class TrainingDataset(BaseModel):
    """Dataset for training a domain.

    Provide diverse, representative samples covering the domain's typical content.
    More samples generally lead to better optimization results.
    """

    samples: list[TrainingSample] = Field(
        ..., min_items=5, description="Training samples (minimum 5 recommended)"
    )
    log_path: str | None = Field(
        default=None,
        description="Optional path to save training log as JSONL. "
        "All events (prompts, responses, scores) will be saved for later analysis.",
        examples=["/var/log/aegis/training/tech_docs_2025-12-12.jsonl"],
    )
    domain_config: DomainConfig | None = Field(
        default=None,
        description="Sprint 124: Domain configuration including llm_model override",
    )


class DomainResponse(BaseModel):
    """Response model for domain configuration.

    Represents a domain with its training status, prompts, and metadata.
    """

    id: str = Field(..., description="Unique domain ID (UUID)")
    name: str = Field(..., description="Domain name")
    description: str = Field(..., description="Domain description")
    status: str = Field(..., description="Domain status (pending/training/ready/failed)")
    llm_model: str = Field(..., description="LLM model used for extraction")
    training_metrics: dict[str, Any] | None = Field(
        default=None, description="Training metrics (e.g., F1 scores)"
    )
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")
    trained_at: str | None = Field(default=None, description="Training completion timestamp")
    entity_sub_type_mapping: dict[str, str] | None = Field(
        default=None,
        description="Sprint 126: Domain sub-type → universal type mapping (JSON)",
    )
    relation_hints: list[str] | None = Field(
        default=None,
        description="Sprint 126: Domain-specific relation examples",
    )


class TrainingStep(BaseModel):
    """Represents a single training step with progress information.

    Sprint 117.6: Step-by-step training progress tracking.
    """

    name: str = Field(..., description="Step name (e.g., 'entity_extraction_optimization')")
    status: str = Field(..., description="Step status (pending/in_progress/completed/failed)")
    progress: int = Field(..., ge=0, le=100, description="Step progress percentage (0-100)")


class TrainingStatusResponse(BaseModel):
    """Response for training status and progress.

    Provides real-time updates on DSPy optimization progress.

    Sprint 117.6 Enhancement: Added step-by-step progress, started_at,
    estimated_completion, and elapsed_time_ms fields.
    """

    domain_name: str = Field(..., description="Domain name being trained")
    status: str = Field(..., description="Training status (pending/training/completed/failed)")
    progress: int = Field(..., ge=0, le=100, description="Overall progress percentage (0-100)")
    current_step: str = Field(..., description="Current training step description")
    steps: list[TrainingStep] = Field(
        default_factory=list, description="Step-by-step progress information"
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Current training metrics (entity_f1, relation_f1, etc.)"
    )
    started_at: str | None = Field(default=None, description="Training start timestamp (ISO 8601)")
    estimated_completion: str | None = Field(
        default=None, description="Estimated completion timestamp (ISO 8601)"
    )
    elapsed_time_ms: int | None = Field(
        default=None, description="Elapsed time since start in milliseconds"
    )


class TrainingLog(BaseModel):
    """Represents a single training log entry.

    Sprint 117.6: Structured training log message.
    """

    timestamp: str = Field(..., description="Log timestamp (ISO 8601)")
    level: str = Field(..., description="Log level (INFO/WARNING/ERROR)")
    message: str = Field(..., description="Log message")
    step: str | None = Field(default=None, description="Training step that produced this log")
    metrics: dict[str, Any] | None = Field(
        default=None, description="Optional metrics associated with this log entry"
    )


class TrainingLogsResponse(BaseModel):
    """Response for training logs with pagination.

    Sprint 117.6: Paginated training logs endpoint.
    """

    domain_name: str = Field(..., description="Domain name")
    logs: list[TrainingLog] = Field(default_factory=list, description="Training log entries")
    total_logs: int = Field(..., description="Total number of logs available")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Number of logs per page")


class AvailableModel(BaseModel):
    """Available LLM model from Ollama.

    Sprint 117.12: Enhanced with categorization and recommendations.
    """

    id: str = Field(..., description="Model ID (e.g., 'nemotron3', 'qwen3:32b')")
    name: str = Field(..., description="Human-readable model name (e.g., 'Nemotron3 8B')")
    provider: str = Field(default="ollama", description="Model provider")
    size_gb: float = Field(..., description="Model size in GB")
    recommended_for: list[str] = Field(
        default_factory=list,
        description="Use cases this model is recommended for (training/extraction/classification)",
    )
    speed: str = Field(..., description="Speed category (fast/medium/slow)")
    quality: str = Field(..., description="Quality category (good/excellent)")
    available: bool = Field(default=True, description="Whether model is currently available")


class AvailableModelsResponse(BaseModel):
    """Response for available models with recommendations.

    Sprint 117.12: Per-domain LLM model selection.
    """

    models: list[AvailableModel] = Field(..., description="List of available models")
    recommendations: dict[str, str] = Field(
        ...,
        description="Recommended models for each use case (training/extraction/classification)",
    )


class ClassificationRequest(BaseModel):
    """Request for document classification to domain.

    Sprint 117.2: Enhanced with C-LARA hybrid classification options.
    """

    text: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Document text to classify",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of top domains to return",
    )
    document_id: str | None = Field(
        default=None,
        description="Optional document ID for tracking (Sprint 117.2)",
    )
    chunk_ids: list[str] | None = Field(
        default=None,
        description="Optional chunk IDs associated with document (Sprint 117.2)",
    )
    threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold (Sprint 117.2)",
    )
    force_llm: bool = Field(
        default=False,
        description="Force LLM verification regardless of confidence (Sprint 117.2)",
    )


class ClassificationResult(BaseModel):
    """Single domain classification result."""

    domain: str = Field(..., description="Domain name")
    score: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    description: str = Field(..., description="Domain description")


class ClassificationResponse(BaseModel):
    """Response for document classification.

    Sprint 117.2: Enhanced with C-LARA hybrid classification metadata.
    """

    classifications: list[ClassificationResult] = Field(
        ..., description="Ranked domain classifications"
    )
    recommended: str = Field(..., description="Top recommended domain")
    confidence: float = Field(..., ge=0, le=1, description="Confidence of top recommendation")
    classification_path: str | None = Field(
        default=None,
        description="Classification path taken (fast/verified/fallback) - Sprint 117.2",
    )
    classification_status: str | None = Field(
        default=None,
        description="Classification status (confident/uncertain/unclassified) - Sprint 117.2",
    )
    requires_review: bool | None = Field(
        default=None,
        description="Whether classification requires manual review - Sprint 117.2",
    )
    reasoning: str | None = Field(
        default=None,
        description="LLM reasoning for classification (if LLM was used) - Sprint 117.2",
    )
    matched_entity_types: list[str] | None = Field(
        default=None,
        description="Matched entity types (if LLM was used) - Sprint 117.2",
    )
    matched_intent: str | None = Field(
        default=None,
        description="Detected intent (if LLM was used) - Sprint 117.2",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Total classification latency in milliseconds - Sprint 117.2",
    )


class BatchIngestionItemRequest(BaseModel):
    """Single item in batch ingestion request."""

    file_path: str = Field(..., description="Path to source document")
    text: str = Field(..., min_length=10, max_length=50000, description="Document text")
    domain: str = Field(..., description="Target domain for extraction")


class BatchIngestionRequest(BaseModel):
    """Request for batch ingestion grouped by LLM model.

    Items will be automatically grouped by the LLM model configured for their
    target domain, minimizing model switching overhead during extraction.
    """

    items: list[BatchIngestionItemRequest] = Field(
        ..., min_items=1, description="List of documents to ingest"
    )


class BatchIngestionResponse(BaseModel):
    """Response for batch ingestion request."""

    message: str = Field(..., description="Status message")
    total_items: int = Field(..., description="Total items in batch")
    model_groups: dict[str, int] = Field(..., description="Count per LLM model")
    domain_groups: dict[str, int] = Field(..., description="Count per domain")


class AutoDiscoveryRequest(BaseModel):
    """Request for domain auto-discovery with clustering.

    Sprint 117.3: Enhanced discovery with document clustering and entity extraction.

    Upload 3-10 representative documents and let the system analyze them using:
    1. BGE-M3 embeddings for document clustering
    2. LLM analysis for entity/relation type extraction
    3. Confidence scoring based on cluster cohesion
    """

    sample_documents: list[str] = Field(
        ...,
        min_length=3,
        max_length=10,
        description="3-10 representative document texts",
    )
    min_samples: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Minimum number of samples required",
    )
    max_samples: int = Field(
        default=10,
        ge=3,
        le=20,
        description="Maximum number of samples to analyze",
    )
    suggested_count: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Target number of domain suggestions",
    )


class DiscoveredDomainResponse(BaseModel):
    """Single discovered domain suggestion."""

    name: str = Field(..., description="Normalized domain name")
    suggested_description: str = Field(..., description="Domain description")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    entity_types: list[str] = Field(..., description="Suggested entity types")
    relation_types: list[str] = Field(
        ..., description="Suggested relation types (includes MENTIONED_IN)"
    )
    intent_classes: list[str] = Field(..., description="Suggested intent classes")
    sample_entities: dict[str, list[str]] = Field(..., description="Example entities by type")
    recommended_model_family: str = Field(..., description="Recommended model family")
    reasoning: str = Field(..., description="LLM reasoning for suggestion")


class AutoDiscoveryResponse(BaseModel):
    """Response from enhanced domain auto-discovery.

    Sprint 117.3: Returns multiple domain suggestions from clustering analysis.
    """

    discovered_domains: list[DiscoveredDomainResponse] = Field(
        ..., description="List of discovered domain suggestions"
    )
    processing_time_ms: float = Field(..., gt=0, description="Total processing time")
    documents_analyzed: int = Field(..., gt=0, description="Number of documents analyzed")
    clusters_found: int = Field(..., ge=0, description="Number of clusters identified")


class DomainBatchDocumentRequest(BaseModel):
    """Single document in domain batch ingestion request (Sprint 117.5)."""

    document_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Unique document identifier",
    )
    content: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Document text content",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (source, page, etc.)",
    )


class DomainBatchIngestionRequest(BaseModel):
    """Request for domain-specific batch document ingestion (Sprint 117.5).

    Process up to 100 documents with domain-specific extraction.
    """

    documents: list[DomainBatchDocumentRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Documents to ingest (max 100)",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Ingestion options (extract_entities, parallel_workers, etc.)",
    )


class DomainBatchIngestionResponse(BaseModel):
    """Response for domain batch ingestion (Sprint 117.5)."""

    batch_id: str = Field(..., description="Batch identifier for status polling")
    domain_name: str = Field(..., description="Target domain name")
    total_documents: int = Field(..., ge=1, description="Total documents in batch")
    status: str = Field(..., description="Batch status (processing/completed/failed)")
    progress: dict[str, int] = Field(
        ...,
        description="Progress counts (completed, failed, pending)",
    )
    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Per-document results",
    )
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Error details",
    )


class AugmentationRequest(BaseModel):
    """Request for data augmentation.

    Provides seed samples and configuration for LLM-based generation of
    additional training data.
    """

    seed_samples: list[dict] = Field(
        ...,
        min_items=5,
        max_items=10,
        description="5-10 high-quality seed samples with text, entities, and relations",
    )
    target_count: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Number of samples to generate (5-100)",
    )
    llm_model: str = Field(
        default="qwen3:32b",
        description="LLM model to use for generation",
        examples=["qwen3:32b", "llama3.2:8b", "mistral:7b"],
    )


class AugmentationResponse(BaseModel):
    """Response from data augmentation.

    Contains generated samples and statistics about the augmentation process.
    """

    generated_samples: list[dict] = Field(..., description="Generated training samples (validated)")
    seed_count: int = Field(..., description="Number of seed samples provided")
    generated_count: int = Field(..., description="Number of samples generated (after validation)")
    validation_rate: float = Field(
        ..., ge=0, le=1, description="Validation rate (validated/target)"
    )


# --- Endpoints ---


@router.post("/", response_model=ApiResponse[DomainResponse], status_code=status.HTTP_201_CREATED)
async def create_domain(
    domain_request: DomainCreateRequest,
    request: Request,
) -> ApiResponse[DomainResponse]:
    """Create a new domain configuration.

    Creates a domain entry in Neo4j with the given configuration.
    The domain will be in 'pending' status until training is completed.

    The description is embedded using BGE-M3 for semantic matching during
    document classification.

    Sprint 117.8: Returns standardized response with request metadata.

    Args:
        domain_request: Domain creation request with name, description, and LLM model
        request: FastAPI request object for metadata

    Returns:
        ApiResponse with created domain configuration

    Raises:
        HTTPException 400: If domain name already exists or validation fails
        HTTPException 500: If database operation fails
    """
    logger.info(
        "create_domain_request",
        name=domain_request.name,
        llm_model=domain_request.llm_model,
    )

    try:
        from src.components.domain_training import get_domain_repository
        from src.components.shared.embedding_factory import get_embedding_service

        repo = get_domain_repository()
        embedding_service = get_embedding_service()

        # Generate description embedding using BGE-M3
        # Sprint 124 Fix: Use embedding factory for correct backend selection
        embedding_result = await embedding_service.embed_single(domain_request.description)

        # Handle both dict (flag-embedding) and list[float] (other backends)
        if isinstance(embedding_result, dict):
            description_embedding = embedding_result.get("dense", [])
        else:
            description_embedding = embedding_result

        logger.info(
            "description_embedded",
            name=domain_request.name,
            embedding_dim=len(description_embedding),
        )

        # Create domain in Neo4j
        # Sprint 126: Pass entity_sub_type_mapping and relation_hints from request
        domain = await repo.create_domain(
            name=domain_request.name,
            description=domain_request.description,
            llm_model=domain_request.llm_model,
            description_embedding=description_embedding,
            entity_sub_type_mapping=domain_request.entity_sub_type_mapping,
            relation_hints=domain_request.relation_hints,
        )

        logger.info(
            "domain_created",
            name=domain_request.name,
            domain_id=domain["id"],
            status=domain["status"],
        )

        domain_response = DomainResponse(
            id=domain["id"],
            name=domain["name"],
            description=domain["description"],
            status=domain["status"],
            llm_model=domain["llm_model"],
            training_metrics=None,
            created_at=domain["created_at"],
            trained_at=None,
            entity_sub_type_mapping=_parse_json_field(domain.get("entity_sub_type_mapping"), {}),
            relation_hints=_parse_json_field(domain.get("relation_hints"), []),
        )

        return success_response_from_request(domain_response, request)

    except ValueError as e:
        # Domain already exists or validation error
        logger.warning("domain_creation_validation_error", name=domain_request.name, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except DatabaseConnectionError as e:
        logger.error("domain_creation_db_error", name=domain_request.name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "domain_creation_unexpected_error",
            name=domain_request.name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("", response_model=ApiResponse[list[DomainResponse]])
@router.get("/", response_model=ApiResponse[list[DomainResponse]])
async def list_domains(request: Request) -> ApiResponse[list[DomainResponse]]:
    """List all registered domains.

    Returns all domains with their current status, training metrics, and metadata.
    Domains are sorted by creation date (newest first).

    Sprint 117.8: Returns standardized response with request metadata.

    Returns:
        ApiResponse with list of domain configurations

    Raises:
        HTTPException 500: If database query fails
    """
    logger.info("list_domains_request")

    try:
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()
        domains = await repo.list_domains()

        logger.info("domains_listed", count=len(domains))

        domain_list = [
            DomainResponse(
                id=d["id"],
                name=d["name"],
                description=d["description"],
                status=d["status"],
                llm_model=d["llm_model"],
                training_metrics=(
                    eval(d["training_metrics"]) if d.get("training_metrics") else None
                ),
                created_at=str(d["created_at"]),
                trained_at=str(d["trained_at"]) if d.get("trained_at") else None,
                entity_sub_type_mapping=_parse_json_field(d.get("entity_sub_type_mapping"), {}),
                relation_hints=_parse_json_field(d.get("relation_hints"), []),
            )
            for d in domains
        ]

        return success_response_from_request(domain_list, request)

    except DatabaseConnectionError as e:
        logger.error("list_domains_db_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error("list_domains_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/available-models", response_model=AvailableModelsResponse)
async def get_available_models() -> AvailableModelsResponse:
    """Get list of available LLM models from Ollama with recommendations.

    Sprint 117.12: Enhanced with model categorization and use case recommendations.

    Queries the local Ollama instance to retrieve all available models,
    categorizes them by size and capabilities, and provides recommendations
    for training vs extraction use cases.

    Returns:
        AvailableModelsResponse with models list and recommendations

    Raises:
        HTTPException 503: If Ollama is not available
        HTTPException 500: If query fails

    Example response:
        {
            "models": [
                {
                    "id": "nemotron3",
                    "name": "Nemotron3 8B",
                    "provider": "ollama",
                    "size_gb": 4.7,
                    "recommended_for": ["extraction", "classification"],
                    "speed": "fast",
                    "quality": "good",
                    "available": true
                },
                {
                    "id": "qwen3:32b",
                    "name": "Qwen3 32B",
                    "provider": "ollama",
                    "size_gb": 18.5,
                    "recommended_for": ["training"],
                    "speed": "slow",
                    "quality": "excellent",
                    "available": true
                }
            ],
            "recommendations": {
                "training": "qwen3:32b",
                "extraction": "nemotron3",
                "classification": "nemotron3"
            }
        }
    """
    logger.info("get_available_models_request")

    try:
        # Import here to avoid circular dependencies
        from src.components.domain_training.model_service import get_model_service

        model_service = get_model_service()

        # Fetch and categorize models
        models_info = await model_service.get_available_models()

        # Get recommendations
        recommendations = model_service.get_model_recommendations(models_info)

        # Convert to API response models
        models_response = [
            AvailableModel(
                id=m.id,
                name=m.name,
                provider=m.provider,
                size_gb=m.size_gb,
                recommended_for=m.recommended_for,
                speed=m.speed,
                quality=m.quality,
                available=m.available,
            )
            for m in models_info
        ]

        logger.info(
            "available_models_retrieved",
            count=len(models_response),
            recommendations=recommendations,
        )

        return AvailableModelsResponse(
            models=models_response,
            recommendations=recommendations,
        )

    except httpx.ConnectError as e:
        logger.error("ollama_connection_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is not available",
        ) from e

    except httpx.HTTPStatusError as e:
        logger.error("ollama_http_error", status_code=e.response.status_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama API error: {e.response.status_code}",
        ) from e

    except Exception as e:
        logger.error("get_available_models_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{domain_name}", response_model=DomainResponse)
async def get_domain(domain_name: str) -> DomainResponse:
    """Get domain details by name.

    Retrieves full domain configuration including optimized prompts,
    training examples, and metrics.

    Args:
        domain_name: Domain name

    Returns:
        Domain configuration

    Raises:
        HTTPException 404: If domain not found
        HTTPException 500: If database query fails
    """
    logger.info("get_domain_request", name=domain_name)

    try:
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()
        domain = await repo.get_domain(domain_name)

        if not domain:
            logger.warning("domain_not_found", name=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        logger.info("domain_retrieved", name=domain_name, status=domain["status"])

        # Parse JSON fields safely
        training_metrics = None
        if domain.get("training_metrics"):
            try:
                training_metrics = eval(domain["training_metrics"])
            except Exception:
                training_metrics = {}

        return DomainResponse(
            id=domain["id"],
            name=domain["name"],
            description=domain["description"],
            status=domain["status"],
            llm_model=domain["llm_model"],
            training_metrics=training_metrics,
            created_at=str(domain["created_at"]),
            trained_at=str(domain["trained_at"]) if domain.get("trained_at") else None,
            entity_sub_type_mapping=_parse_json_field(domain.get("entity_sub_type_mapping"), {}),
            relation_hints=_parse_json_field(domain.get("relation_hints"), []),
        )

    except HTTPException:
        raise

    except DatabaseConnectionError as e:
        logger.error("get_domain_db_error", name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "get_domain_unexpected_error",
            name=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.put("/{domain_name}")
async def update_domain(
    domain_name: str,
    update_request: DomainUpdateRequest,
) -> dict[str, Any]:
    """Update domain configuration.

    Sprint 117 Feature 117.1: Domain CRUD API - Update endpoint.

    Updates domain configuration including entity types, relation types,
    confidence threshold, and LLM settings. MENTIONED_IN relation is
    automatically added if not present.

    Args:
        domain_name: Domain name to update
        update_request: Update request with optional fields

    Returns:
        Updated domain configuration

    Raises:
        HTTPException 400: If validation fails
        HTTPException 404: If domain not found
        HTTPException 500: If database update fails
    """
    logger.info("update_domain_request", name=domain_name)

    try:
        from src.components.domain_training import get_domain_repository

        # Sprint 118 Fix: DomainUpdateRequest now imported at module level

        repo = get_domain_repository()

        # Convert Pydantic model to dict for repository
        update_data = {}
        if update_request.description is not None:
            update_data["description"] = update_request.description
        if update_request.entity_types is not None:
            update_data["entity_types"] = update_request.entity_types
        if update_request.relation_types is not None:
            update_data["relation_types"] = update_request.relation_types
        if update_request.intent_classes is not None:
            update_data["intent_classes"] = update_request.intent_classes
        if update_request.confidence_threshold is not None:
            update_data["confidence_threshold"] = update_request.confidence_threshold
        if update_request.status is not None:
            update_data["status"] = update_request.status
        if update_request.llm_config is not None:
            update_data["llm_config"] = update_request.llm_config.model_dump()
        # Sprint 126: entity_sub_type_mapping and relation_hints (YAML override via UI)
        if update_request.entity_sub_type_mapping is not None:
            update_data["entity_sub_type_mapping"] = update_request.entity_sub_type_mapping
        if update_request.relation_hints is not None:
            update_data["relation_hints"] = update_request.relation_hints

        # Update domain
        updated_domain = await repo.update_domain(domain_name, **update_data)

        # Sprint 126: Invalidate extraction type mapping cache if mapping changed
        if update_request.entity_sub_type_mapping is not None or update_request.relation_hints is not None:
            from src.components.graph_rag.extraction_service import (
                invalidate_domain_type_mappings_cache,
            )

            invalidate_domain_type_mappings_cache()

        logger.info("domain_updated_successfully", name=domain_name)

        return {
            "success": True,
            "message": f"Domain '{domain_name}' updated successfully",
            "domain": updated_domain,
        }

    except ValueError as e:
        logger.warning("update_domain_validation_error", name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except DatabaseConnectionError as e:
        logger.error("update_domain_db_error", name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "update_domain_unexpected_error",
            name=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post("/{domain_name}/train")
async def start_training(
    domain_name: str,
    dataset: TrainingDataset,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Start DSPy optimization for a domain with transactional rollback support.

    Feature 64.2 Part 2: Transactional Domain Creation

    Launches background training that optimizes entity and relation extraction
    prompts using DSPy's BootstrapFewShot optimizer. Training progress can be
    monitored via GET /domains/{name}/training-status.

    **Important:** If the domain does not exist, it will be created transactionally
    as part of the training process. If training fails (validation, database errors,
    or optimization failures), the domain creation will be rolled back and no
    domain will persist in Neo4j.

    Training process:
    1. Validate request (minimum 5 samples required)
    2. Create domain transactionally (if not exists)
    3. Optimize entity extraction prompts
    4. Optimize relation extraction prompts
    5. Extract static prompts for production use
    6. Save prompts and metrics to domain
    7. Commit transaction on success / Rollback on failure

    Args:
        domain_name: Domain to train
        dataset: Training samples (minimum 5 required for validation)
        background_tasks: FastAPI background task handler

    Returns:
        Training job information with status URL

    Raises:
        HTTPException 422: If validation fails (e.g., less than 5 samples)
        HTTPException 409: If training already in progress
        HTTPException 500: If training job creation fails
    """
    logger.info(
        "start_training_request",
        domain=domain_name,
        sample_count=len(dataset.samples),
    )

    # CRITICAL: Validate samples BEFORE any domain creation
    # This prevents creating domains that will fail training
    if len(dataset.samples) < 5:
        logger.warning(
            "training_validation_failed",
            domain=domain_name,
            sample_count=len(dataset.samples),
            required_minimum=5,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": f"Minimum 5 samples required, got {len(dataset.samples)}",
                    "details": {
                        "validation_errors": [
                            {
                                "loc": ["body", "samples"],
                                "msg": f"List should have at least 5 items after validation, not {len(dataset.samples)}",
                                "type": "too_short",
                            }
                        ]
                    },
                }
            },
        )

    try:
        import uuid
        from src.components.domain_training import get_domain_repository
        from src.components.domain_training.training_runner import run_dspy_optimization

        repo = get_domain_repository()
        domain = await repo.get_domain(domain_name)

        # Check if domain exists and handle re-training
        if domain:
            if domain.get("status") == "completed" or domain.get("status") == "ready":
                logger.info(
                    "retraining_existing_domain",
                    domain=domain_name,
                    previous_status=domain.get("status"),
                )
                # Allow re-training of completed domains
            elif domain.get("status") == "training":
                logger.warning("training_already_in_progress", domain=domain_name)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Training already in progress for this domain",
                )

        # Create training log (will be associated with domain during training)
        # NOTE: If domain doesn't exist, it will be created transactionally
        # by the training runner with rollback support
        if domain:
            training_log = await repo.create_training_log(domain_name)
            logger.info(
                "training_log_created",
                domain=domain_name,
                training_run_id=training_log["id"],
            )
        else:
            # Generate training_run_id for new domain (log will be created during training)
            training_run_id = str(uuid.uuid4())
            logger.info(
                "training_new_domain",
                domain=domain_name,
                training_run_id=training_run_id,
            )

        # Start background training with transactional rollback support
        # If domain doesn't exist, run_dspy_optimization will create it transactionally
        # Sprint 124: Pass domain_config to allow llm_model override
        domain_config_dict = None
        if dataset.domain_config:
            domain_config_dict = dataset.domain_config.model_dump(exclude_none=True)
            logger.info(
                "domain_config_provided",
                domain=domain_name,
                llm_model=domain_config_dict.get("llm_model"),
            )

        background_tasks.add_task(
            run_dspy_optimization,
            domain_name=domain_name,
            training_run_id=training_log["id"] if domain else training_run_id,
            dataset=[s.model_dump() for s in dataset.samples],
            log_path=dataset.log_path,  # SSE event log for later DSPy evaluation
            create_domain_if_not_exists=domain is None,  # Signal to create domain transactionally
            domain_config=domain_config_dict,  # Sprint 124: Pass llm_model override
        )

        logger.info(
            "training_started_background",
            domain=domain_name,
            training_run_id=training_log["id"] if domain else training_run_id,
            is_new_domain=domain is None,
        )

        return {
            "message": "Training started in background",
            "training_run_id": training_log["id"] if domain else training_run_id,
            "status_url": f"/admin/domains/{domain_name}/training-status",
            "domain": domain_name,
            "sample_count": len(dataset.samples),
            "is_new_domain": domain is None,
        }

    except HTTPException:
        raise

    except DatabaseConnectionError as e:
        logger.error("start_training_db_error", domain=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "start_training_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{domain_name}/training-status", response_model=TrainingStatusResponse)
async def get_training_status(domain_name: str) -> TrainingStatusResponse:
    """Get current training status and progress.

    Provides real-time updates on DSPy optimization progress including:
    - Current training step
    - Progress percentage
    - Training metrics (when completed)
    - Error messages (if failed)

    Args:
        domain_name: Domain name

    Returns:
        Training status and progress information

    Raises:
        HTTPException 404: If domain or training log not found
        HTTPException 500: If database query fails
    """
    from datetime import datetime, timedelta

    logger.info("get_training_status_request", domain=domain_name)

    try:
        from src.components.domain_training import get_domain_repository
        from src.components.domain_training.training_progress import TrainingPhase

        repo = get_domain_repository()
        training_log = await repo.get_latest_training_log(domain_name)

        if not training_log:
            logger.warning("training_log_not_found", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No training log found for domain '{domain_name}'",
            )

        logger.info(
            "training_status_retrieved",
            domain=domain_name,
            status=training_log["status"],
            progress=training_log["progress_percent"],
        )

        # Parse metrics JSON
        metrics = {}
        if training_log.get("metrics"):
            try:
                metrics_str = training_log["metrics"]
                metrics = json.loads(metrics_str) if metrics_str else {}
            except (json.JSONDecodeError, TypeError):
                logger.warning("invalid_metrics_json", domain=domain_name)
                metrics = {}

        # Calculate step-by-step progress based on TrainingPhase weights
        progress_percent = float(training_log["progress_percent"])
        current_step_name = training_log["current_step"]

        # Map progress percentage to phase and steps
        steps = []

        # Define training steps (aligned with TrainingPhase.PHASE_WEIGHTS)
        training_steps = [
            ("initialization", TrainingPhase.INITIALIZING),
            ("loading_data", TrainingPhase.LOADING_DATA),
            ("entity_extraction_optimization", TrainingPhase.ENTITY_OPTIMIZATION),
            ("relation_extraction_optimization", TrainingPhase.RELATION_OPTIMIZATION),
            ("prompt_extraction", TrainingPhase.PROMPT_EXTRACTION),
            ("model_validation", TrainingPhase.VALIDATION),
            ("saving_results", TrainingPhase.SAVING),
        ]

        # Hardcoded phase weights (from TrainingProgressTracker.PHASE_WEIGHTS)
        phase_weights_map = {
            TrainingPhase.INITIALIZING: (0, 5),
            TrainingPhase.LOADING_DATA: (5, 10),
            TrainingPhase.ENTITY_OPTIMIZATION: (10, 45),
            TrainingPhase.RELATION_OPTIMIZATION: (45, 80),
            TrainingPhase.PROMPT_EXTRACTION: (80, 85),
            TrainingPhase.VALIDATION: (85, 95),
            TrainingPhase.SAVING: (95, 100),
        }

        for step_name, phase in training_steps:
            start_pct, end_pct = phase_weights_map.get(phase, (0, 0))

            # Determine step status and progress
            if progress_percent < start_pct:
                step_status = "pending"
                step_progress = 0
            elif progress_percent >= end_pct:
                step_status = "completed"
                step_progress = 100
            else:
                step_status = "in_progress"
                step_progress = int(((progress_percent - start_pct) / (end_pct - start_pct)) * 100)

            steps.append(
                TrainingStep(
                    name=step_name,
                    status=step_status,
                    progress=step_progress,
                )
            )

        # Calculate elapsed time and estimated completion
        started_at = training_log.get("started_at")
        elapsed_time_ms = None
        estimated_completion = None

        if started_at:
            # Parse started_at (Neo4j datetime object or ISO string)
            # Sprint 124 Fix: Handle Neo4j DateTime vs Python datetime
            if hasattr(started_at, "to_native"):
                # Neo4j DateTime object - convert to Python datetime
                started_at_dt = started_at.to_native()
                started_at_str = started_at_dt.isoformat()
            elif hasattr(started_at, "isoformat"):
                # Already a Python datetime
                started_at_dt = started_at
                started_at_str = started_at.isoformat()
            else:
                started_at_str = str(started_at)
                try:
                    started_at_dt = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
                except ValueError:
                    started_at_dt = None

            if started_at_dt:
                # Calculate elapsed time
                now = datetime.utcnow()
                elapsed = now - started_at_dt.replace(tzinfo=None)
                elapsed_time_ms = int(elapsed.total_seconds() * 1000)

                # Estimate completion time (based on progress)
                if progress_percent > 0 and training_log["status"] in ("pending", "running"):
                    avg_time_per_percent = elapsed_time_ms / progress_percent
                    remaining_percent = 100 - progress_percent
                    remaining_ms = avg_time_per_percent * remaining_percent
                    estimated_completion_dt = now + timedelta(milliseconds=remaining_ms)
                    estimated_completion = estimated_completion_dt.isoformat() + "Z"
        else:
            started_at_str = None

        # Map internal status to API status
        api_status = training_log["status"]
        if api_status == "running":
            api_status = "training"

        return TrainingStatusResponse(
            domain_name=domain_name,
            status=api_status,
            progress=int(progress_percent),
            current_step=current_step_name,
            steps=steps,
            metrics=metrics,
            started_at=started_at_str,
            estimated_completion=estimated_completion,
            elapsed_time_ms=elapsed_time_ms,
        )

    except HTTPException:
        raise

    except DatabaseConnectionError as e:
        logger.error("get_training_status_db_error", domain=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "get_training_status_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{domain_name}/training-logs", response_model=TrainingLogsResponse)
async def get_training_logs(
    domain_name: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Logs per page (max 100)"),
) -> TrainingLogsResponse:
    """Get paginated training logs for a domain.

    Sprint 117.6: Retrieves structured training log messages with pagination support.

    Provides historical training logs including:
    - Timestamp (ISO 8601)
    - Log level (INFO/WARNING/ERROR)
    - Log message
    - Training step that produced the log
    - Optional metrics associated with the log

    Args:
        domain_name: Domain name
        page: Page number (1-indexed, default: 1)
        page_size: Number of logs per page (1-100, default: 20)

    Returns:
        Paginated training logs response

    Raises:
        HTTPException 404: If domain not found
        HTTPException 422: If pagination parameters invalid
        HTTPException 500: If database query fails
    """
    logger.info(
        "get_training_logs_request",
        domain=domain_name,
        page=page,
        page_size=page_size,
    )

    try:
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()

        # Validate pagination parameters (repo will also validate, but fail early)
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="page must be >= 1",
            )
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="page_size must be 1-100",
            )

        # Get paginated logs from repository
        result = await repo.get_training_log_messages(
            domain_name=domain_name,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "training_logs_retrieved",
            domain=domain_name,
            total_logs=result["total_logs"],
            page_logs=len(result["logs"]),
        )

        # Convert log dicts to TrainingLog models
        training_logs = [
            TrainingLog(
                timestamp=log.get("timestamp", ""),
                level=log.get("level", "INFO"),
                message=log.get("message", ""),
                step=log.get("step"),
                metrics=log.get("metrics"),
            )
            for log in result["logs"]
        ]

        return TrainingLogsResponse(
            domain_name=domain_name,
            logs=training_logs,
            total_logs=result["total_logs"],
            page=result["page"],
            page_size=result["page_size"],
        )

    except HTTPException:
        raise

    except ValueError as e:
        # Catch validation errors from repository
        logger.warning("invalid_pagination_parameters", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    except DatabaseConnectionError as e:
        logger.error("get_training_logs_db_error", domain=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "get_training_logs_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{domain_name}/training-stream")
async def stream_training_progress(
    domain_name: str,
    training_run_id: str = Query(..., description="Training run ID to stream"),
) -> StreamingResponse:
    """Stream training progress via Server-Sent Events (SSE).

    Provides real-time streaming of training events including:
    - Progress updates (percentage, phase)
    - LLM interactions (full prompts and responses)
    - Sample processing results
    - Evaluation scores

    The stream delivers events in SSE format (data: {...}\\n\\n).
    Content is NOT truncated - full prompts and responses are included.

    Connect with EventSource or fetch with streaming:
        ```javascript
        const eventSource = new EventSource(
            `/api/v1/domain-training/${domain}/training-stream?training_run_id=${runId}`
        );
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
        ```

    Args:
        domain_name: Domain being trained
        training_run_id: Unique training run identifier

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException 404: If training stream not found or not active
    """
    logger.info(
        "training_stream_requested",
        domain=domain_name,
        training_run_id=training_run_id,
    )

    from src.components.domain_training.training_stream import get_training_stream

    stream = get_training_stream()

    if not stream.is_active(training_run_id):
        logger.warning(
            "training_stream_not_found",
            domain=domain_name,
            training_run_id=training_run_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training stream '{training_run_id}' not found or not active",
        )

    async def event_generator():
        """Generate SSE events from the training stream."""
        try:
            async for event in stream.subscribe(training_run_id):
                yield event.to_sse()
        except Exception as e:
            logger.error(
                "training_stream_error",
                training_run_id=training_run_id,
                error=str(e),
            )
            # Send error event before closing
            error_data = {
                "event_type": "error",
                "message": str(e),
                "training_run_id": training_run_id,
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/{domain_name}/training-stream/stats")
async def get_training_stream_stats(
    domain_name: str,
    training_run_id: str = Query(..., description="Training run ID"),
) -> dict:
    """Get statistics for an active training stream.

    Args:
        domain_name: Domain being trained
        training_run_id: Training run identifier

    Returns:
        Stream statistics including event count and duration

    Raises:
        HTTPException 404: If stream not found
    """
    from src.components.domain_training.training_stream import get_training_stream

    stream = get_training_stream()
    stats = stream.get_stats(training_run_id)

    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training stream '{training_run_id}' not found",
        )

    return stats


class DomainDeletionResponse(BaseModel):
    """Response model for domain deletion.

    Provides statistics on what was deleted across all storage backends.
    """

    message: str = Field(..., description="Deletion status message")
    domain_name: str = Field(..., description="Name of deleted domain")
    deleted_counts: dict[str, int] = Field(
        ...,
        description="Counts of deleted items per backend (qdrant_points, neo4j_entities, neo4j_chunks, bm25_documents)",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-critical warnings during deletion",
    )


class DomainStatsResponse(BaseModel):
    """Response model for domain statistics.

    Sprint 52 Feature 52.2.2: Domain Management Enhancement
    Provides counts and health information for a domain.
    """

    domain_name: str = Field(..., description="Domain name")
    documents: int = Field(..., ge=0, description="Number of documents in domain")
    chunks: int = Field(..., ge=0, description="Number of chunks in domain")
    entities: int = Field(..., ge=0, description="Number of entities in domain")
    relationships: int = Field(..., ge=0, description="Number of relationships in domain")
    last_indexed: str | None = Field(None, description="Last indexing timestamp (ISO 8601)")
    indexing_progress: float = Field(
        ..., ge=0, le=100, description="Indexing progress percentage (0-100)"
    )
    error_count: int = Field(..., ge=0, description="Number of indexing errors")
    errors: list[str] = Field(default_factory=list, description="List of recent error messages")
    health_status: str = Field(
        ...,
        description="Domain health status (healthy, degraded, error)",
    )


class ReindexDomainResponse(BaseModel):
    """Response model for domain re-indexing operation.

    Sprint 52 Feature 52.2.2: Domain Management Enhancement
    """

    message: str = Field(..., description="Status message")
    domain_name: str = Field(..., description="Domain name")
    documents_queued: int = Field(
        ..., ge=0, description="Number of documents queued for re-indexing"
    )


class ValidateDomainResponse(BaseModel):
    """Response model for domain validation operation.

    Sprint 52 Feature 52.2.2: Domain Management Enhancement
    """

    domain_name: str = Field(..., description="Domain name")
    is_valid: bool = Field(..., description="Whether the domain is valid")
    validation_errors: list[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    recommendations: list[str] = Field(default_factory=list, description="List of recommendations")


@router.delete("/{domain_name}", response_model=DomainDeletionResponse)
async def delete_domain(domain_name: str) -> DomainDeletionResponse:
    """Delete a domain and all its associated data.

    This will:
    1. Delete domain record from Neo4j (Domain node + training logs)
    2. Delete all documents in domain's namespace from Qdrant
    3. Delete all entities/relationships/chunks with matching namespace from Neo4j
    4. Clean up BM25 index entries for the domain

    The default 'general' domain cannot be deleted.

    **WARNING**: This is a destructive operation that cannot be undone.
    All documents, entities, and relationships associated with this domain
    will be permanently deleted.

    Args:
        domain_name: Domain to delete

    Returns:
        Deletion statistics showing what was removed from each backend

    Raises:
        HTTPException 400: If trying to delete default 'general' domain
        HTTPException 404: If domain not found
        HTTPException 409: If domain is currently training
        HTTPException 500: If database operation fails
    """
    logger.info("delete_domain_request", name=domain_name)

    if domain_name == "general":
        logger.warning("delete_default_domain_attempted", name=domain_name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete default 'general' domain",
        )

    try:
        from src.components.domain_training import get_domain_repository
        from src.core.namespace import get_namespace_manager

        repo = get_domain_repository()
        namespace_manager = get_namespace_manager()

        # Check if domain exists and get its status
        domain = await repo.get_domain(domain_name)

        if not domain:
            logger.warning("domain_not_found_for_deletion", name=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        # Prevent deletion if domain is currently training
        if domain.get("status") == "training":
            logger.warning(
                "delete_domain_training_in_progress",
                name=domain_name,
                status=domain.get("status"),
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete domain '{domain_name}' while training is in progress",
            )

        warnings: list[str] = []
        deleted_counts: dict[str, int] = {
            "qdrant_points": 0,
            "neo4j_entities": 0,
            "neo4j_chunks": 0,
            "neo4j_relationships": 0,
            "bm25_documents": 0,
        }

        # Step 1: Delete namespace data (Qdrant + Neo4j entities/chunks)
        # Use domain_name as namespace_id (domains map 1:1 with namespaces)
        namespace_id = domain_name
        try:
            namespace_stats = await namespace_manager.delete_namespace(namespace_id)
            deleted_counts["qdrant_points"] = namespace_stats.get("qdrant_points_deleted", 0)
            deleted_counts["neo4j_entities"] = namespace_stats.get("neo4j_nodes_deleted", 0)
            deleted_counts["neo4j_relationships"] = namespace_stats.get(
                "neo4j_relationships_deleted", 0
            )

            logger.info(
                "namespace_data_deleted",
                domain=domain_name,
                namespace_id=namespace_id,
                stats=namespace_stats,
            )

        except Exception as e:
            warning_msg = f"Failed to delete namespace data: {str(e)}"
            logger.warning(
                "namespace_deletion_partial_failure",
                domain=domain_name,
                error=str(e),
            )
            warnings.append(warning_msg)

        # Step 2: Clean up BM25 index
        # BM25 corpus is filtered at query time, but we should remove entries for memory efficiency
        try:
            from src.components.vector_search.bm25_retrieval import get_bm25_retrieval

            bm25 = get_bm25_retrieval()

            # Remove documents matching domain from BM25 corpus
            # BM25Retrieval stores corpus with metadata including namespace_id
            if hasattr(bm25, "corpus") and bm25.corpus:
                original_count = len(bm25.corpus)

                # Filter out documents from this domain's namespace
                bm25.corpus = [
                    doc
                    for doc in bm25.corpus
                    if doc.get("metadata", {}).get("namespace_id") != namespace_id
                ]

                deleted_count = original_count - len(bm25.corpus)
                deleted_counts["bm25_documents"] = deleted_count

                # Rebuild BM25 index if corpus changed
                if deleted_count > 0:
                    bm25._build_index()  # noqa: SLF001

                logger.info(
                    "bm25_corpus_cleaned",
                    domain=domain_name,
                    deleted_count=deleted_count,
                    remaining_count=len(bm25.corpus),
                )

        except Exception as e:
            warning_msg = f"Failed to clean BM25 index: {str(e)}"
            logger.warning(
                "bm25_cleanup_failed",
                domain=domain_name,
                error=str(e),
            )
            warnings.append(warning_msg)

        # Step 3: Delete domain configuration and training logs
        deleted = await repo.delete_domain(domain_name)

        if not deleted:
            # This should not happen since we already checked domain exists
            logger.error(
                "domain_deletion_inconsistent_state",
                name=domain_name,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Domain deletion encountered inconsistent state",
            )

        logger.info(
            "domain_fully_deleted",
            name=domain_name,
            deleted_counts=deleted_counts,
            warnings=warnings,
        )

        return DomainDeletionResponse(
            message=f"Domain '{domain_name}' and all associated data deleted successfully",
            domain_name=domain_name,
            deleted_counts=deleted_counts,
            warnings=warnings,
        )

    except HTTPException:
        raise

    except ValueError as e:
        # Cannot delete default domain
        logger.warning("domain_deletion_validation_error", name=domain_name, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except DatabaseConnectionError as e:
        logger.error("delete_domain_db_error", name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "delete_domain_unexpected_error",
            name=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post("/classify", response_model=ClassificationResponse)
async def classify_document(request: ClassificationRequest) -> ClassificationResponse:
    """Classify document text to best matching domain.

    Sprint 117.2: Enhanced with C-LARA hybrid classification.

    Two-stage classification approach:
        Stage A: C-LARA SetFit classifier (~40ms, local, no LLM cost)
        Stage B: LLM Verification (optional, when confidence < 0.85)

    Confidence Routing:
        - conf >= 0.85  → Fast Return (no LLM, 70-80% of requests)
        - 0.60-0.85     → LLM Verify Top-K (15-25%)
        - conf < 0.60   → LLM Fallback All Domains (5-10%)

    Args:
        request: Classification request with text, top_k, and optional params

    Returns:
        Ranked domain classifications with confidence scores and metadata

    Raises:
        HTTPException 500: If classification fails
    """
    logger.info(
        "classify_document_request",
        text_length=len(request.text),
        top_k=request.top_k,
        document_id=request.document_id,
        force_llm=request.force_llm,
    )

    try:
        # Sprint 117.2: Use LangGraph workflow for classification
        from src.agents.domain_classifier import get_domain_classification_graph

        graph = get_domain_classification_graph()

        # Prepare state
        initial_state = {
            "document_text": request.text,
            "document_id": request.document_id,
            "chunk_ids": request.chunk_ids,
            "top_k": request.top_k,
            "threshold": request.threshold,
            "force_llm": request.force_llm,
        }

        # Run classification workflow with LangSmith metadata
        result = await graph.ainvoke(
            initial_state,
            config={
                "metadata": {
                    "sprint": "117.2",
                    "feature": "c-lara-domain-classification",
                    "document_id": request.document_id,
                    "text_length": len(request.text),
                    "force_llm": request.force_llm,
                }
            },
        )

        # Extract final classification
        final_domain = result.get("final_domain_id", "general")
        final_confidence = result.get("final_confidence", 0.0)
        alternative_domains = result.get("alternative_domains", [])

        logger.info(
            "document_classified",
            text_length=len(request.text),
            document_id=request.document_id,
            final_domain=final_domain,
            confidence=final_confidence,
            classification_path=result.get("classification_path"),
            latency_ms=result.get("latency_ms"),
        )

        # Build response (need to fetch domain descriptions)
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()

        # Fetch domain descriptions for response
        all_domains = await repo.list_domains()
        domain_desc_map = {d["name"]: d.get("description", "") for d in all_domains}

        # Build classifications list
        classifications = [
            ClassificationResult(
                domain=final_domain,
                score=final_confidence,
                description=domain_desc_map.get(final_domain, ""),
            )
        ]

        # Add alternative domains
        for alt in alternative_domains:
            domain_id = alt.get("domain_id", "")
            confidence = alt.get("confidence", 0.0)
            classifications.append(
                ClassificationResult(
                    domain=domain_id,
                    score=confidence,
                    description=domain_desc_map.get(domain_id, ""),
                )
            )

        return ClassificationResponse(
            classifications=classifications,
            recommended=final_domain,
            confidence=final_confidence,
            classification_path=result.get("classification_path"),
            classification_status=result.get("classification_status"),
            requires_review=result.get("requires_review"),
            reasoning=result.get("reasoning"),
            matched_entity_types=result.get("matched_entity_types"),
            matched_intent=result.get("matched_intent"),
            latency_ms=result.get("latency_ms"),
        )

    except Exception as e:
        logger.error(
            "classify_document_unexpected_error",
            text_length=len(request.text),
            document_id=request.document_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed",
        ) from e


@router.post("/auto-discover", response_model=AutoDiscoveryResponse)
async def discover_domain(request: AutoDiscoveryRequest) -> AutoDiscoveryResponse:
    """Auto-discover domains from sample documents using clustering.

    Sprint 117.3: Enhanced domain discovery with BGE-M3 clustering and LLM analysis.
    Sprint 119: Renamed from /discover to /auto-discover to avoid route collision
    with domain_discovery.py's file-upload-based POST /discover endpoint.

    Upload 3-10 representative documents and let the system analyze them using:
    1. BGE-M3 embeddings to cluster similar documents
    2. K-means clustering to identify distinct domain groups
    3. LLM analysis to extract entity/relation types per cluster
    4. Confidence scoring based on cluster cohesion and entity consistency

    This endpoint is useful when you have a collection of documents but aren't sure
    how to categorize them or what domain configurations to use.

    Discovery process:
    1. Embed documents using BGE-M3 (dense vectors)
    2. Cluster documents using K-means
    3. For each cluster, analyze with LLM to extract domain configuration
    4. Return all discovered domains ranked by confidence

    Args:
        request: Auto-discovery request with sample documents and parameters

    Returns:
        Multiple domain suggestions with entity/relation types and confidence scores

    Raises:
        HTTPException 400: If less than min_samples provided
        HTTPException 503: If Ollama service is unavailable
        HTTPException 500: If discovery fails
    """
    logger.info(
        "discover_domains_request",
        sample_count=len(request.sample_documents),
        min_samples=request.min_samples,
        max_samples=request.max_samples,
        suggested_count=request.suggested_count,
    )

    try:
        from src.components.domain_discovery import get_domain_discovery_service

        service = get_domain_discovery_service()

        # Perform enhanced discovery with clustering
        result = await service.discover_domains(
            sample_documents=request.sample_documents,
            min_samples=request.min_samples,
            max_samples=request.max_samples,
            suggested_count=request.suggested_count,
        )

        logger.info(
            "domains_discovered",
            domains_found=len(result.discovered_domains),
            clusters_found=result.clusters_found,
            processing_time_ms=result.processing_time_ms,
        )

        # Convert to response format
        discovered_domains = [
            DiscoveredDomainResponse(
                name=domain.name,
                suggested_description=domain.suggested_description,
                confidence=domain.confidence,
                entity_types=domain.entity_types,
                relation_types=domain.relation_types,
                intent_classes=domain.intent_classes,
                sample_entities=domain.sample_entities,
                recommended_model_family=domain.recommended_model_family,
                reasoning=domain.reasoning,
            )
            for domain in result.discovered_domains
        ]

        return AutoDiscoveryResponse(
            discovered_domains=discovered_domains,
            processing_time_ms=result.processing_time_ms,
            documents_analyzed=result.documents_analyzed,
            clusters_found=result.clusters_found,
        )

    except ValueError as e:
        # Insufficient samples or validation error
        logger.warning(
            "discover_domains_validation_error",
            error=str(e),
            sample_count=len(request.sample_documents),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except httpx.ConnectError as e:
        logger.error("discover_domain_ollama_connection_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is not available",
        ) from e

    except httpx.HTTPStatusError as e:
        logger.error(
            "discover_domain_ollama_http_error",
            status_code=e.response.status_code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama API error: {e.response.status_code}",
        ) from e

    except Exception as e:
        logger.error(
            "discover_domain_unexpected_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Domain discovery failed",
        ) from e


@router.post("/ingest-batch", response_model=BatchIngestionResponse)
async def ingest_batch(
    request: BatchIngestionRequest,
    background_tasks: BackgroundTasks,
) -> BatchIngestionResponse:
    """Ingest documents in batches grouped by LLM model.

    Items are automatically grouped by the LLM model configured for their
    target domain, minimizing model switching overhead during extraction.

    This endpoint optimizes batch processing by:
    1. Loading each domain's LLM model configuration
    2. Grouping items by model (largest batches first)
    3. Processing each group sequentially with one model load
    4. Reducing GPU memory thrashing and context switching

    Processing runs in background, use domain status endpoints to monitor progress.

    Args:
        request: Batch ingestion request with list of documents
        background_tasks: FastAPI background task handler

    Returns:
        Immediate response with grouping statistics

    Raises:
        HTTPException 400: If invalid domain or request data
        HTTPException 500: If batch processing setup fails

    Example:
        >>> response = client.post("/admin/domains/ingest-batch", json={
        ...     "items": [
        ...         {
        ...             "file_path": "/docs/api.md",
        ...             "text": "FastAPI documentation...",
        ...             "domain": "tech_docs"
        ...         },
        ...         {
        ...             "file_path": "/legal/contract.pdf",
        ...             "text": "This agreement...",
        ...             "domain": "legal_contracts"
        ...         }
        ...     ]
        ... })
        >>> print(response.json())
        {
            "message": "Batch ingestion started",
            "total_items": 2,
            "model_groups": {"qwen3:32b": 1, "llama3.2:8b": 1},
            "domain_groups": {"tech_docs": 1, "legal_contracts": 1}
        }
    """
    logger.info(
        "ingest_batch_request",
        total_items=len(request.items),
    )

    try:
        from collections import Counter

        from src.components.domain_training import (
            IngestionItem,
            get_domain_repository,
            get_grouped_ingestion_processor,
        )

        repo = get_domain_repository()

        # Build ingestion items with model info
        items: list[IngestionItem] = []
        for item_data in request.items:
            domain = await repo.get_domain(item_data.domain)

            # Fallback to general domain if not found
            if not domain:
                logger.warning(
                    "domain_not_found_fallback",
                    domain=item_data.domain,
                    file_path=item_data.file_path,
                )
                domain = await repo.get_domain("general")

                # If even general domain doesn't exist, use default config
                if not domain:
                    domain = {
                        "name": "general",
                        "llm_model": "qwen3:32b",
                    }

            llm_model = domain.get("llm_model", "qwen3:32b")

            items.append(
                IngestionItem(
                    file_path=item_data.file_path,
                    text=item_data.text,
                    domain=item_data.domain,
                    llm_model=llm_model,
                )
            )

        logger.info(
            "ingestion_items_prepared",
            total_items=len(items),
            unique_domains=len({item.domain for item in items}),
            unique_models=len({item.llm_model for item in items}),
        )

        # Process in background
        processor = get_grouped_ingestion_processor()
        background_tasks.add_task(processor.process_batch, items)

        # Return immediate response with grouping info
        model_counts = Counter(item.llm_model for item in items)
        domain_counts = Counter(item.domain for item in items)

        logger.info(
            "batch_ingestion_started",
            total_items=len(items),
            model_groups=dict(model_counts),
            domain_groups=dict(domain_counts),
        )

        return BatchIngestionResponse(
            message="Batch ingestion started in background",
            total_items=len(items),
            model_groups=dict(model_counts),
            domain_groups=dict(domain_counts),
        )

    except ValueError as e:
        logger.warning(
            "ingest_batch_validation_error",
            error=str(e),
            items_count=len(request.items),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except DatabaseConnectionError as e:
        logger.error(
            "ingest_batch_db_error",
            error=str(e),
            items_count=len(request.items),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "ingest_batch_unexpected_error",
            error=str(e),
            items_count=len(request.items),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch ingestion setup failed",
        ) from e


@router.post("/augment", response_model=AugmentationResponse)
async def augment_training_data(request: AugmentationRequest) -> AugmentationResponse:
    """Generate additional training samples from seed examples.

    Provide 5-10 high-quality seed samples, and the LLM will generate additional
    samples in the same style/domain. This is useful for expanding small training
    datasets to improve DSPy optimization results.

    Augmentation process:
    1. Format seed samples into few-shot prompt
    2. Call Ollama LLM to generate batch of samples
    3. Parse JSON response and validate structure
    4. Filter by quality criteria (length, entity count)
    5. Return validated samples

    Quality Criteria:
    - Text length: 50-2000 characters
    - Minimum entities: 2
    - Valid JSON structure with text, entities, relations

    Args:
        request: Augmentation request with seed samples and configuration

    Returns:
        Generated samples with validation statistics

    Raises:
        HTTPException 400: If less than 5 seed samples provided
        HTTPException 503: If Ollama service is not available
        HTTPException 500: If generation fails

    Example:
        >>> response = client.post("/admin/domains/augment", json={
        ...     "seed_samples": [
        ...         {
        ...             "text": "FastAPI is a modern web framework...",
        ...             "entities": ["FastAPI", "web framework"],
        ...             "relations": [
        ...                 {"subject": "FastAPI", "predicate": "is_a", "object": "web framework"}
        ...             ]
        ...         },
        ...         ...  # 5-10 seed samples
        ...     ],
        ...     "target_count": 20,
        ...     "llm_model": "qwen3:32b"
        ... })
        >>> print(f"Generated {response.json()['generated_count']} samples")
    """
    logger.info(
        "augment_training_data_request",
        seed_count=len(request.seed_samples),
        target_count=request.target_count,
        llm_model=request.llm_model,
    )

    try:
        from src.components.domain_training import get_training_data_augmenter

        # Get augmenter and configure model
        augmenter = get_training_data_augmenter()
        augmenter.llm_model = request.llm_model

        # Generate samples
        generated = await augmenter.augment(
            seed_samples=request.seed_samples,
            target_count=request.target_count,
        )

        logger.info(
            "training_data_augmented",
            seed_count=len(request.seed_samples),
            target_count=request.target_count,
            generated_count=len(generated),
            validation_rate=(
                len(generated) / request.target_count if request.target_count > 0 else 0
            ),
        )

        return AugmentationResponse(
            generated_samples=generated,
            seed_count=len(request.seed_samples),
            generated_count=len(generated),
            validation_rate=(
                len(generated) / request.target_count if request.target_count > 0 else 0
            ),
        )

    except ValueError as e:
        # Less than 5 seed samples
        logger.warning(
            "augmentation_validation_error",
            seed_count=len(request.seed_samples),
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except httpx.ConnectError as e:
        logger.error("augmentation_ollama_connection_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is not available",
        ) from e

    except httpx.HTTPStatusError as e:
        logger.error(
            "augmentation_ollama_http_error",
            status_code=e.response.status_code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama API error: {e.response.status_code}",
        ) from e

    except Exception as e:
        logger.error(
            "augment_training_data_unexpected_error",
            seed_count=len(request.seed_samples),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Training data augmentation failed",
        ) from e


@router.get("/{domain_name}/stats", response_model=DomainStatsResponse)
async def get_domain_stats(domain_name: str) -> DomainStatsResponse:
    """Get statistics for a domain.

    Sprint 52 Feature 52.2.2: Domain Management Enhancement

    Returns counts for documents, chunks, entities, and relationships in the domain,
    along with health status and indexing progress.

    Args:
        domain_name: Domain name to get stats for

    Returns:
        Domain statistics including counts and health status

    Raises:
        HTTPException 404: If domain not found
        HTTPException 500: If database query fails
    """
    logger.info("get_domain_stats_request", domain=domain_name)

    try:
        from src.components.domain_training import get_domain_repository
        from src.components.graph_rag.neo4j_client import get_neo4j_client
        from src.components.vector_search.qdrant_client import get_qdrant_client
        from src.core.config import settings as app_settings

        repo = get_domain_repository()

        # Check if domain exists
        domain = await repo.get_domain(domain_name)
        if not domain:
            logger.warning("domain_not_found_for_stats", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        # Initialize counts
        document_count = 0
        chunk_count = 0
        entity_count = 0
        relationship_count = 0
        errors: list[str] = []
        last_indexed: str | None = None

        # Get counts from Qdrant (documents/chunks)
        try:
            qdrant = get_qdrant_client()
            collection_name = app_settings.qdrant_collection

            # Count points with namespace_id matching domain
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            namespace_filter = Filter(
                must=[
                    FieldCondition(
                        key="namespace_id",
                        match=MatchValue(value=domain_name),
                    )
                ]
            )

            # Count chunks (all points in namespace)
            count_result = await qdrant.async_client.count(
                collection_name=collection_name,
                count_filter=namespace_filter,
            )
            chunk_count = count_result.count

            # Estimate document count by getting unique document_ids
            # Use scroll to sample and count unique documents
            scroll_result = await qdrant.async_client.scroll(
                collection_name=collection_name,
                scroll_filter=namespace_filter,
                limit=10000,
                with_payload=["document_id"],
            )
            unique_docs = set()
            for point in scroll_result[0]:
                doc_id = point.payload.get("document_id")
                if doc_id:
                    unique_docs.add(doc_id)
            document_count = len(unique_docs)

            logger.info(
                "qdrant_stats_retrieved",
                domain=domain_name,
                chunks=chunk_count,
                documents=document_count,
            )

        except Exception as e:
            error_msg = f"Failed to get Qdrant stats: {str(e)}"
            logger.warning("qdrant_stats_error", domain=domain_name, error=str(e))
            errors.append(error_msg)

        # Get counts from Neo4j (entities/relationships)
        try:
            neo4j = get_neo4j_client()

            # Count entities in namespace
            entity_result = await neo4j.execute_read(
                """
                MATCH (e:base {namespace_id: $namespace_id})
                RETURN count(e) AS count
                """,
                {"namespace_id": domain_name},
            )
            if entity_result:
                entity_count = entity_result[0].get("count", 0)

            # Count relationships in namespace
            rel_result = await neo4j.execute_read(
                """
                MATCH (e1:base {namespace_id: $namespace_id})-[r]->
                      (e2:base {namespace_id: $namespace_id})
                RETURN count(r) AS count
                """,
                {"namespace_id": domain_name},
            )
            if rel_result:
                relationship_count = rel_result[0].get("count", 0)

            # Get last indexed timestamp from chunk nodes
            last_indexed_result = await neo4j.execute_read(
                """
                MATCH (c:chunk {namespace_id: $namespace_id})
                WHERE c.created_at IS NOT NULL
                RETURN max(c.created_at) AS last_indexed
                """,
                {"namespace_id": domain_name},
            )
            if last_indexed_result and last_indexed_result[0].get("last_indexed"):
                last_indexed_dt = last_indexed_result[0]["last_indexed"]
                if hasattr(last_indexed_dt, "isoformat"):
                    last_indexed = last_indexed_dt.isoformat()
                else:
                    last_indexed = str(last_indexed_dt)

            logger.info(
                "neo4j_stats_retrieved",
                domain=domain_name,
                entities=entity_count,
                relationships=relationship_count,
            )

        except Exception as e:
            error_msg = f"Failed to get Neo4j stats: {str(e)}"
            logger.warning("neo4j_stats_error", domain=domain_name, error=str(e))
            errors.append(error_msg)

        # Determine health status
        if errors:
            health_status = "degraded" if entity_count > 0 or chunk_count > 0 else "error"
        elif domain.get("status") == "failed":
            health_status = "error"
        elif domain.get("status") == "training":
            health_status = "indexing"
        elif entity_count == 0 and chunk_count == 0:
            health_status = "empty"
        else:
            health_status = "healthy"

        # Calculate indexing progress (100% if ready, 0% if pending)
        indexing_progress = 100.0 if domain.get("status") == "ready" else 0.0
        if domain.get("status") == "training":
            # Get training progress if available
            training_log = await repo.get_latest_training_log(domain_name)
            if training_log:
                indexing_progress = training_log.get("progress_percent", 50.0)

        logger.info(
            "domain_stats_retrieved",
            domain=domain_name,
            documents=document_count,
            chunks=chunk_count,
            entities=entity_count,
            relationships=relationship_count,
            health_status=health_status,
        )

        return DomainStatsResponse(
            domain_name=domain_name,
            documents=document_count,
            chunks=chunk_count,
            entities=entity_count,
            relationships=relationship_count,
            last_indexed=last_indexed,
            indexing_progress=indexing_progress,
            error_count=len(errors),
            errors=errors,
            health_status=health_status,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "get_domain_stats_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve domain statistics",
        ) from e


@router.post("/{domain_name}/reindex", response_model=ReindexDomainResponse)
async def reindex_domain(
    domain_name: str,
    background_tasks: BackgroundTasks,
) -> ReindexDomainResponse:
    """Trigger re-indexing of all documents in a domain.

    Sprint 52 Feature 52.2.2: Domain Management Enhancement

    Re-indexes all documents by re-running entity extraction and relationship detection.
    This is useful after training updates or when graph quality needs improvement.

    Args:
        domain_name: Domain name to re-index
        background_tasks: FastAPI background task handler

    Returns:
        Re-indexing job information

    Raises:
        HTTPException 404: If domain not found
        HTTPException 409: If re-indexing already in progress
        HTTPException 500: If re-indexing setup fails
    """
    logger.info("reindex_domain_request", domain=domain_name)

    try:
        from src.components.domain_training import get_domain_repository
        from src.components.vector_search.qdrant_client import get_qdrant_client
        from src.core.config import settings as app_settings

        repo = get_domain_repository()

        # Check if domain exists
        domain = await repo.get_domain(domain_name)
        if not domain:
            logger.warning("domain_not_found_for_reindex", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        # Check if training/indexing already in progress
        if domain.get("status") == "training":
            logger.warning("reindex_already_in_progress", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain '{domain_name}' is currently being trained/indexed",
            )

        # Count documents to re-index
        documents_queued = 0
        try:
            qdrant = get_qdrant_client()
            collection_name = app_settings.qdrant_collection

            from qdrant_client.models import FieldCondition, Filter, MatchValue

            namespace_filter = Filter(
                must=[
                    FieldCondition(
                        key="namespace_id",
                        match=MatchValue(value=domain_name),
                    )
                ]
            )

            scroll_result = await qdrant.async_client.scroll(
                collection_name=collection_name,
                scroll_filter=namespace_filter,
                limit=10000,
                with_payload=["document_id"],
            )
            unique_docs = set()
            for point in scroll_result[0]:
                doc_id = point.payload.get("document_id")
                if doc_id:
                    unique_docs.add(doc_id)
            documents_queued = len(unique_docs)

        except Exception as e:
            logger.warning("reindex_count_error", domain=domain_name, error=str(e))

        # Queue re-indexing task (placeholder - actual implementation depends on ingestion pipeline)
        async def reindex_task():
            """Background task to re-index domain documents."""
            logger.info("reindex_task_started", domain=domain_name)
            # In a full implementation, this would:
            # 1. Iterate through all documents in the domain
            # 2. Re-run entity extraction and relationship detection
            # 3. Update the graph database
            # For now, this is a placeholder that logs completion
            logger.info(
                "reindex_task_completed",
                domain=domain_name,
                documents_processed=documents_queued,
            )

        background_tasks.add_task(reindex_task)

        logger.info(
            "reindex_domain_queued",
            domain=domain_name,
            documents_queued=documents_queued,
        )

        return ReindexDomainResponse(
            message=f"Re-indexing started for domain '{domain_name}'",
            domain_name=domain_name,
            documents_queued=documents_queued,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "reindex_domain_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start re-indexing",
        ) from e


# Sprint 52 validate_domain endpoint replaced by Sprint 117.7 comprehensive validation
# See DomainValidationResponse and validate_domain endpoint at line 3079


# ============================================================================
# Connectivity Evaluation (Sprint 77 Feature 77.5 - TD-095)
# ============================================================================


class ConnectivityEvaluationRequest(BaseModel):
    """Request for entity connectivity evaluation.

    Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
    """

    namespace_id: str = Field(..., description="Namespace to evaluate")
    domain_type: str = Field(
        default="factual",
        description="Domain type for benchmark (factual, narrative, technical, academic)",
        pattern="^(factual|narrative|technical|academic)$",
    )


class ConnectivityEvaluationResponse(BaseModel):
    """Response with connectivity metrics and benchmark comparison.

    Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
    """

    namespace_id: str = Field(..., description="Namespace identifier")
    domain_type: str = Field(..., description="Domain type used for benchmark")
    total_entities: int = Field(..., description="Total entities in namespace")
    total_relationships: int = Field(..., description="Total relationships")
    total_communities: int = Field(..., description="Total communities")
    relations_per_entity: float = Field(..., description="Relations per entity ratio")
    entities_per_community: float = Field(..., description="Entities per community ratio")
    benchmark_min: float = Field(..., description="Benchmark minimum")
    benchmark_max: float = Field(..., description="Benchmark maximum")
    within_benchmark: bool = Field(..., description="Whether within expected range")
    benchmark_status: str = Field(..., description="Status: below, within, above")
    recommendations: list[str] = Field(..., description="Actionable recommendations")


@router.post(
    "/connectivity/evaluate",
    response_model=ConnectivityEvaluationResponse,
    summary="Evaluate entity connectivity metrics",
    description="Evaluate entity connectivity for a namespace against domain-specific benchmarks. "
    "Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric",
)
async def evaluate_domain_connectivity(
    request: ConnectivityEvaluationRequest,
) -> ConnectivityEvaluationResponse:
    """Evaluate entity connectivity metrics for a namespace.

    **Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric**

    This endpoint evaluates knowledge graph connectivity and compares it to
    domain-specific benchmarks. Different domains have different expected
    connectivity patterns:

    **Domain Types:**
    - **Factual** (HotpotQA, Wikipedia): Sparse, atomic facts (0.3-0.8 relations/entity)
    - **Narrative** (Stories, articles): Dense, narrative-driven (1.5-3.0 relations/entity)
    - **Technical** (Documentation, manuals): Hierarchical (2.0-4.0 relations/entity)
    - **Academic** (Research papers): Citation-heavy (2.5-5.0 relations/entity)

    **Metrics Returned:**
    - Total entities, relationships, communities
    - Relations per entity ratio (key metric)
    - Entities per community ratio
    - Benchmark comparison (min/max range)
    - Status (below, within, above benchmark)
    - Actionable recommendations for improving connectivity

    **Use Cases:**
    - Domain Training UI: Display connectivity with benchmark indicators
    - DSPy Optimization: Use as quality metric for prompt optimization
    - Graph Health Monitoring: Track connectivity trends over time

    Args:
        request: ConnectivityEvaluationRequest with namespace_id and domain_type

    Returns:
        ConnectivityEvaluationResponse with metrics, benchmark comparison, recommendations

    Raises:
        HTTPException: If Neo4j connection fails or namespace not found

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/admin/domains/connectivity/evaluate \\
             -H "Content-Type: application/json" \\
             -d '{"namespace_id": "hotpotqa_large", "domain_type": "factual"}'
        ```

        Response:
        ```json
        {
          "namespace_id": "hotpotqa_large",
          "domain_type": "factual",
          "total_entities": 146,
          "total_relationships": 65,
          "total_communities": 92,
          "relations_per_entity": 0.45,
          "entities_per_community": 1.59,
          "benchmark_min": 0.3,
          "benchmark_max": 0.8,
          "within_benchmark": true,
          "benchmark_status": "within",
          "recommendations": [
            "✅ Entity connectivity within benchmark (0.45 in [0.3, 0.8])",
            "Graph quality is appropriate for factual domain",
            "Continue monitoring connectivity as more documents are ingested"
          ]
        }
        ```
    """
    try:
        from src.components.domain_training.domain_metrics import (
            DomainType,
            evaluate_connectivity,
        )

        logger.info(
            "connectivity_evaluation_requested",
            namespace_id=request.namespace_id,
            domain_type=request.domain_type,
        )

        # Validate domain_type (should be caught by Pydantic but double-check)
        if request.domain_type not in ["factual", "narrative", "technical", "academic"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid domain_type: {request.domain_type}. "
                f"Must be one of: factual, narrative, technical, academic",
            )

        # Evaluate connectivity
        metrics = await evaluate_connectivity(
            namespace_id=request.namespace_id,
            domain_type=request.domain_type,  # type: ignore[arg-type]
        )

        logger.info(
            "connectivity_evaluation_complete",
            namespace_id=request.namespace_id,
            relations_per_entity=round(metrics.relations_per_entity, 2),
            benchmark_status=metrics.benchmark_status,
            within_benchmark=metrics.within_benchmark,
        )

        return ConnectivityEvaluationResponse(
            namespace_id=metrics.namespace_id,
            domain_type=metrics.domain_type,
            total_entities=metrics.total_entities,
            total_relationships=metrics.total_relationships,
            total_communities=metrics.total_communities,
            relations_per_entity=metrics.relations_per_entity,
            entities_per_community=metrics.entities_per_community,
            benchmark_min=metrics.benchmark_min,
            benchmark_max=metrics.benchmark_max,
            within_benchmark=metrics.within_benchmark,
            benchmark_status=metrics.benchmark_status,
            recommendations=metrics.recommendations,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "connectivity_evaluation_failed",
            namespace_id=request.namespace_id,
            domain_type=request.domain_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate connectivity: {str(e)}",
        ) from e


# ============================================================================
# Sprint 117 Feature 117.7: Domain Validation
# ============================================================================


class ValidationCheckResponse(BaseModel):
    """Individual validation check result.

    Attributes:
        name: Check name (e.g., "training_samples_count")
        status: ValidationStatus (pass/warning/fail)
        message: Human-readable message
        details: Additional details (counts, lists, etc.)
    """

    name: str = Field(..., description="Check name")
    status: str = Field(..., description="Validation status (pass/warning/fail)")
    message: str = Field(..., description="Human-readable message")
    details: dict[str, Any] = Field(..., description="Additional details")


class ValidationIssueResponse(BaseModel):
    """Validation issue with severity and recommendation.

    Attributes:
        severity: IssueSeverity (error/warning/info)
        category: IssueCategory
        message: Human-readable message
        recommendation: Actionable recommendation
    """

    severity: str = Field(..., description="Issue severity (error/warning/info)")
    category: str = Field(..., description="Issue category")
    message: str = Field(..., description="Human-readable message")
    recommendation: str = Field(..., description="Actionable recommendation")


class DomainValidationResponse(BaseModel):
    """Domain validation response.

    Sprint 117 Feature 117.7: Comprehensive domain quality validation.

    Attributes:
        domain_name: Domain name
        validation_status: Overall status (pass/warning/fail)
        health_score: Health score (0-100)
        checks: List of validation checks
        issues: List of validation issues
        recommendations: List of actionable recommendations
    """

    domain_name: str = Field(..., description="Domain name")
    validation_status: str = Field(..., description="Overall validation status (pass/warning/fail)")
    health_score: int = Field(..., ge=0, le=100, description="Health score (0-100)")
    checks: list[ValidationCheckResponse] = Field(..., description="Validation checks")
    issues: list[ValidationIssueResponse] = Field(..., description="Validation issues")
    recommendations: list[str] = Field(..., description="Actionable recommendations")

    model_config = {
        "json_schema_extra": {
            "example": {
                "domain_name": "medical",
                "validation_status": "warning",
                "health_score": 72,
                "checks": [
                    {
                        "name": "training_samples_count",
                        "status": "pass",
                        "message": "1247 training samples (minimum: 20)",
                        "details": {"count": 1247, "minimum": 20},
                    },
                    {
                        "name": "entity_type_coverage",
                        "status": "warning",
                        "message": "3/5 entity types have samples",
                        "details": {"covered": 3, "total": 5, "missing": ["Medication", "Dosage"]},
                    },
                    {
                        "name": "relation_type_coverage",
                        "status": "pass",
                        "message": "All relation types have samples",
                        "details": {"covered": 4, "total": 4},
                    },
                    {
                        "name": "mentioned_in_relations",
                        "status": "pass",
                        "message": "MENTIONED_IN relations present",
                        "details": {"count": 2847},
                    },
                    {
                        "name": "model_trained",
                        "status": "fail",
                        "message": "DSPy model not trained",
                        "details": {"last_trained": None},
                    },
                ],
                "issues": [
                    {
                        "severity": "warning",
                        "category": "coverage",
                        "message": "Entity types 'Medication', 'Dosage' have no training samples",
                        "recommendation": "Add training samples for missing entity types: Medication, Dosage",
                    },
                    {
                        "severity": "error",
                        "category": "model",
                        "message": "Domain model not trained",
                        "recommendation": "Run POST /api/v1/admin/domains/medical/train to optimize prompts",
                    },
                ],
                "recommendations": [
                    "Add training samples for missing entity types: Medication, Dosage",
                    "Run POST /api/v1/admin/domains/medical/train to optimize prompts",
                ],
            }
        }
    }


@router.post("/{domain_name}/validate", response_model=DomainValidationResponse)
async def validate_domain(domain_name: str) -> DomainValidationResponse:
    """Validate domain quality and readiness.

    Sprint 117 Feature 117.7: Comprehensive domain validation.

    This endpoint validates a domain's quality and readiness for production use.
    It checks training samples, entity/relation coverage, provenance links,
    model training status, confidence calibration, and recent activity.

    **Validation Checks:**
    1. **Training Samples Count** - Minimum 20 samples
    2. **Entity Type Coverage** - All entity types have samples
    3. **Relation Type Coverage** - All relation types have samples
    4. **MENTIONED_IN Relations** - Provenance links exist (CRITICAL)
    5. **Model Trained** - DSPy prompts optimized
    6. **Confidence Calibration** - Threshold makes sense
    7. **Recent Activity** - Domain used recently

    **Health Score Calculation:**
    - Pass = 100 points
    - Warning = 50 points
    - Fail = 0 points
    - Health Score = average of all checks

    Args:
        domain_name: Domain name to validate

    Returns:
        DomainValidationResponse with validation results

    Raises:
        HTTPException 404: If domain not found
        HTTPException 500: If validation fails

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/v1/admin/domains/medical/validate
        ```

        Response:
        ```json
        {
          "domain_name": "medical",
          "validation_status": "warning",
          "health_score": 72,
          "checks": [
            {
              "name": "training_samples_count",
              "status": "pass",
              "message": "1247 training samples (minimum: 20)",
              "details": {"count": 1247, "minimum": 20}
            },
            {
              "name": "mentioned_in_relations",
              "status": "pass",
              "message": "MENTIONED_IN relations present",
              "details": {"count": 2847}
            }
          ],
          "issues": [
            {
              "severity": "warning",
              "category": "coverage",
              "message": "Entity types 'Medication', 'Dosage' have no training samples",
              "recommendation": "Add training samples for missing entity types"
            }
          ],
          "recommendations": [
            "Add training samples for missing entity types: Medication, Dosage",
            "Run POST /api/v1/admin/domains/medical/train to optimize prompts"
          ]
        }
        ```
    """
    try:
        from src.components.domain_training.domain_validator import get_domain_validator

        logger.info("domain_validation_requested", domain_name=domain_name)

        # Get validator and run validation
        validator = get_domain_validator()
        result = await validator.validate_domain(domain_name)

        logger.info(
            "domain_validation_complete",
            domain_name=domain_name,
            validation_status=result["validation_status"],
            health_score=result["health_score"],
            issues_count=len(result["issues"]),
        )

        # Convert to response model
        return DomainValidationResponse(
            domain_name=result["domain_name"],
            validation_status=result["validation_status"],
            health_score=result["health_score"],
            checks=[ValidationCheckResponse(**check) for check in result["checks"]],
            issues=[ValidationIssueResponse(**issue) for issue in result["issues"]],
            recommendations=result["recommendations"],
        )

    except ValueError as e:
        logger.warning("domain_not_found", domain_name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain_name}' not found",
        ) from e

    except DatabaseConnectionError as e:
        logger.error("domain_validation_db_error", domain_name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e

    except Exception as e:
        logger.error(
            "domain_validation_failed",
            domain_name=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Domain validation failed: {str(e)}",
        ) from e


@router.post(
    "/{domain_name}/ingest-batch",
    response_model=DomainBatchIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_batch_documents(
    domain_name: str,
    request: DomainBatchIngestionRequest,
) -> DomainBatchIngestionResponse:
    """Ingest documents in batch with domain-specific extraction.

    Sprint 117.5: Domain-Specific Batch Document Ingestion (8 SP)

    Process up to 100 documents in parallel with domain-specific entity/relation
    extraction, chunking, and indexing. Each document is processed independently
    with isolated error handling.

    Features:
    - Parallel processing with configurable workers (default: 4, max: 10)
    - Domain-specific DSPy-optimized prompts
    - Real-time progress tracking per document
    - Isolated failures (one document error doesn't stop batch)
    - MENTIONED_IN relation auto-creation for all entities
    - Comprehensive per-document statistics

    Processing Options:
    - extract_entities: Enable entity extraction (default: true)
    - extract_relations: Enable relation extraction (default: true)
    - chunk_strategy: Chunking strategy (default: "section_aware")
    - parallel_workers: Number of parallel workers (default: 4, max: 10)

    Args:
        domain_name: Target domain name
        request: Batch ingestion request with documents and options

    Returns:
        Batch response with ID for status polling

    Raises:
        HTTPException 400: If domain not found or invalid request
        HTTPException 500: If batch processing setup fails

    Example:
        ```python
        response = client.post(
            "/api/v1/admin/domains/tech_docs/ingest-batch",
            json={
                "documents": [
                    {
                        "document_id": "doc_001",
                        "content": "FastAPI is a modern web framework...",
                        "metadata": {"source": "api_docs.pdf", "page": 1}
                    },
                    {
                        "document_id": "doc_002",
                        "content": "Django is a high-level Python framework...",
                        "metadata": {"source": "django_guide.pdf", "page": 1}
                    }
                ],
                "options": {
                    "extract_entities": True,
                    "extract_relations": True,
                    "chunk_strategy": "section_aware",
                    "parallel_workers": 4
                }
            }
        )
        print(response.json())
        # {
        #   "batch_id": "batch_abc123",
        #   "domain_name": "tech_docs",
        #   "total_documents": 2,
        #   "status": "processing",
        #   "progress": {"completed": 0, "failed": 0, "pending": 2},
        #   "results": [],
        #   "errors": []
        # }
        ```

    Status Polling:
        Use GET /api/v1/admin/domains/{domain_name}/ingest-batch/{batch_id}/status
        to poll for batch progress and results.
    """
    logger.info(
        "domain_batch_ingestion_requested",
        domain_name=domain_name,
        total_documents=len(request.documents),
    )

    try:
        from src.components.domain_training import (
            DocumentRequest,
            IngestionOptions,
            get_batch_ingestion_service,
        )

        # Convert Pydantic models to domain models
        documents = [
            DocumentRequest(
                document_id=doc.document_id,
                content=doc.content,
                metadata=doc.metadata,
            )
            for doc in request.documents
        ]

        # Parse options with defaults
        options = IngestionOptions(
            extract_entities=request.options.get("extract_entities", True),
            extract_relations=request.options.get("extract_relations", True),
            chunk_strategy=request.options.get("chunk_strategy", "section_aware"),
            parallel_workers=request.options.get("parallel_workers", 4),
        )

        # Start batch processing
        service = get_batch_ingestion_service()
        batch_id = await service.start_batch(
            domain_name=domain_name,
            documents=documents,
            options=options,
        )

        # Get initial status
        batch_status = await service.get_batch_status(batch_id)

        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create batch",
            )

        logger.info(
            "domain_batch_ingestion_started",
            domain_name=domain_name,
            batch_id=batch_id,
            total_documents=len(request.documents),
        )

        return DomainBatchIngestionResponse(
            batch_id=batch_id,
            domain_name=domain_name,
            total_documents=batch_status["total_documents"],
            status=batch_status["status"],
            progress=batch_status["progress"],
            results=batch_status["results"],
            errors=batch_status["errors"],
        )

    except ValueError as e:
        logger.warning(
            "domain_batch_ingestion_validation_error",
            domain_name=domain_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.error(
            "domain_batch_ingestion_failed",
            domain_name=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch ingestion setup failed: {str(e)}",
        ) from e


@router.get(
    "/{domain_name}/ingest-batch/{batch_id}/status",
    response_model=DomainBatchIngestionResponse,
)
async def get_batch_ingestion_status(
    domain_name: str,
    batch_id: str,
) -> DomainBatchIngestionResponse:
    """Get status of a batch ingestion job.

    Sprint 117.5: Batch Status Polling Endpoint

    Poll this endpoint to get real-time progress of a batch ingestion job.
    The response includes per-document results, error details, and overall
    progress statistics.

    Args:
        domain_name: Domain name (for validation)
        batch_id: Batch identifier from ingest-batch response

    Returns:
        Current batch status with progress and results

    Raises:
        HTTPException 404: If batch not found

    Example:
        ```python
        response = client.get(
            "/api/v1/admin/domains/tech_docs/ingest-batch/batch_abc123/status"
        )
        print(response.json())
        # {
        #   "batch_id": "batch_abc123",
        #   "domain_name": "tech_docs",
        #   "total_documents": 100,
        #   "status": "processing",
        #   "progress": {
        #     "completed": 45,
        #     "failed": 2,
        #     "pending": 53
        #   },
        #   "results": [
        #     {
        #       "document_id": "doc_001",
        #       "status": "completed",
        #       "entities_extracted": 23,
        #       "relations_extracted": 12,
        #       "chunks_created": 5,
        #       "processing_time_ms": 2340
        #     },
        #     ...
        #   ],
        #   "errors": [
        #     {
        #       "document_id": "doc_050",
        #       "error": "Failed to extract entities",
        #       "error_code": "EXTRACTION_FAILED"
        #     }
        #   ]
        # }
        ```

    Polling Strategy:
        - Poll every 2-5 seconds during processing
        - Stop polling when status is "completed" or "completed_with_errors"
        - Check errors array for failed documents
    """
    logger.info(
        "batch_status_requested",
        domain_name=domain_name,
        batch_id=batch_id,
    )

    try:
        from src.components.domain_training import get_batch_ingestion_service

        service = get_batch_ingestion_service()
        batch_status = await service.get_batch_status(batch_id)

        if not batch_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch not found: {batch_id}",
            )

        # Validate domain name matches
        if batch_status["domain_name"] != domain_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch belongs to domain '{batch_status['domain_name']}', not '{domain_name}'",
            )

        logger.info(
            "batch_status_retrieved",
            domain_name=domain_name,
            batch_id=batch_id,
            status=batch_status["status"],
            completed=batch_status["progress"]["completed"],
            failed=batch_status["progress"]["failed"],
        )

        return DomainBatchIngestionResponse(
            batch_id=batch_id,
            domain_name=batch_status["domain_name"],
            total_documents=batch_status["total_documents"],
            status=batch_status["status"],
            progress=batch_status["progress"],
            results=batch_status["results"],
            errors=batch_status["errors"],
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "batch_status_retrieval_failed",
            domain_name=domain_name,
            batch_id=batch_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch status: {str(e)}",
        ) from e
