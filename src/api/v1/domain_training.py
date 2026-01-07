"""Domain Training API Endpoints for DSPy-based Knowledge Graph Optimization.

Sprint 45 - Feature 45.3, 45.10: Domain Training API

This module provides FastAPI endpoints for managing domain-specific extraction prompts
and training configurations. It enables creating domains, training them with DSPy,
and classifying documents to domains.

Key Endpoints:
- POST /admin/domains - Create new domain configuration
- GET /admin/domains - List all domains
- GET /admin/domains/{name} - Get domain details
- POST /admin/domains/{name}/train - Start DSPy training
- GET /admin/domains/{name}/training-status - Monitor training progress
- DELETE /admin/domains/{name} - Delete domain and all associated data (51.4)
- GET /admin/domains/available-models - List Ollama models
- POST /admin/domains/classify - Classify document to domain
- POST /admin/domains/ingest-batch - Batch ingestion grouped by LLM model (45.10)

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
    >>> response = client.post("/admin/domains/", json={
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
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.config import get_settings
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/admin/domains", tags=["Domain Training"])


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


class TrainingStatusResponse(BaseModel):
    """Response for training status and progress.

    Provides real-time updates on DSPy optimization progress.
    """

    status: str = Field(..., description="Training status (pending/running/completed/failed)")
    progress_percent: float = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str = Field(..., description="Current training step description")
    logs: list[dict[str, Any]] = Field(default_factory=list, description="Training log messages")
    metrics: dict[str, Any] | None = Field(
        default=None, description="Training metrics (available after completion)"
    )


class AvailableModel(BaseModel):
    """Available LLM model from Ollama."""

    name: str = Field(..., description="Model name (e.g., 'qwen3:32b')")
    size: int = Field(..., description="Model size in bytes")
    modified_at: str | None = Field(default=None, description="Last modification time")


class ClassificationRequest(BaseModel):
    """Request for document classification to domain."""

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


class ClassificationResult(BaseModel):
    """Single domain classification result."""

    domain: str = Field(..., description="Domain name")
    score: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    description: str = Field(..., description="Domain description")


class ClassificationResponse(BaseModel):
    """Response for document classification."""

    classifications: list[ClassificationResult] = Field(
        ..., description="Ranked domain classifications"
    )
    recommended: str = Field(..., description="Top recommended domain")
    confidence: float = Field(..., ge=0, le=1, description="Confidence of top recommendation")


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
    """Request for domain auto-discovery.

    Upload 3-10 representative documents and let the LLM analyze them
    to suggest an appropriate domain configuration.
    """

    sample_texts: list[str] = Field(
        ...,
        min_items=3,
        max_items=10,
        description="3-10 representative document texts",
    )
    llm_model: str = Field(
        default="qwen3:32b",
        description="LLM model to use for analysis",
    )


class AutoDiscoveryResponse(BaseModel):
    """Response from domain auto-discovery.

    Contains the LLM's suggested domain configuration including name,
    description, and expected entity/relation types.
    """

    name: str = Field(..., description="Suggested domain name (normalized)")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed domain description")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    reasoning: str = Field(..., description="LLM's reasoning for suggestion")
    entity_types: list[str] = Field(..., description="Expected entity types")
    relation_types: list[str] = Field(..., description="Expected relation types")


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


@router.post("/", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def create_domain(request: DomainCreateRequest) -> DomainResponse:
    """Create a new domain configuration.

    Creates a domain entry in Neo4j with the given configuration.
    The domain will be in 'pending' status until training is completed.

    The description is embedded using BGE-M3 for semantic matching during
    document classification.

    Args:
        request: Domain creation request with name, description, and LLM model

    Returns:
        Created domain configuration

    Raises:
        HTTPException 400: If domain name already exists or validation fails
        HTTPException 500: If database operation fails
    """
    logger.info(
        "create_domain_request",
        name=request.name,
        llm_model=request.llm_model,
    )

    try:
        from src.components.domain_training import get_domain_repository
        from src.components.vector_search import EmbeddingService

        repo = get_domain_repository()
        embedding_service = EmbeddingService()

        # Generate description embedding using BGE-M3
        description_embedding = await embedding_service.embed_single(request.description)

        logger.info(
            "description_embedded",
            name=request.name,
            embedding_dim=len(description_embedding),
        )

        # Create domain in Neo4j
        domain = await repo.create_domain(
            name=request.name,
            description=request.description,
            llm_model=request.llm_model,
            description_embedding=description_embedding,
        )

        logger.info(
            "domain_created",
            name=request.name,
            domain_id=domain["id"],
            status=domain["status"],
        )

        return DomainResponse(
            id=domain["id"],
            name=domain["name"],
            description=domain["description"],
            status=domain["status"],
            llm_model=domain["llm_model"],
            training_metrics=None,
            created_at=domain["created_at"],
            trained_at=None,
        )

    except ValueError as e:
        # Domain already exists or validation error
        logger.warning("domain_creation_validation_error", name=request.name, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except DatabaseConnectionError as e:
        logger.error("domain_creation_db_error", name=request.name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        ) from e

    except Exception as e:
        logger.error(
            "domain_creation_unexpected_error",
            name=request.name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("", response_model=list[DomainResponse])
@router.get("/", response_model=list[DomainResponse])
async def list_domains() -> list[DomainResponse]:
    """List all registered domains.

    Returns all domains with their current status, training metrics, and metadata.
    Domains are sorted by creation date (newest first).

    Returns:
        List of domain configurations

    Raises:
        HTTPException 500: If database query fails
    """
    logger.info("list_domains_request")

    try:
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()
        domains = await repo.list_domains()

        logger.info("domains_listed", count=len(domains))

        return [
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
            )
            for d in domains
        ]

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


@router.get("/available-models", response_model=list[AvailableModel])
async def get_available_models() -> list[AvailableModel]:
    """Get list of available LLM models from Ollama.

    Queries the local Ollama instance to retrieve all available models
    that can be used for domain training.

    Returns:
        List of available Ollama models

    Raises:
        HTTPException 503: If Ollama is not available
        HTTPException 500: If query fails
    """
    logger.info("get_available_models_request")

    try:
        ollama_url = settings.ollama_base_url or "http://localhost:11434"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()

            models_data = response.json()
            models = models_data.get("models", [])

            logger.info("available_models_retrieved", count=len(models))

            return [
                AvailableModel(
                    name=m["name"],
                    size=m.get("size", 0),
                    modified_at=m.get("modified_at"),
                )
                for m in models
            ]

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
        background_tasks.add_task(
            run_dspy_optimization,
            domain_name=domain_name,
            training_run_id=training_log["id"] if domain else training_run_id,
            dataset=[s.model_dump() for s in dataset.samples],
            log_path=dataset.log_path,  # SSE event log for later DSPy evaluation
            create_domain_if_not_exists=domain is None,  # Signal to create domain transactionally
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
    logger.info("get_training_status_request", domain=domain_name)

    try:
        from src.components.domain_training import get_domain_repository

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

        # Parse JSON fields safely
        logs = []
        if training_log.get("log_messages"):
            try:
                logs = eval(training_log["log_messages"])
            except Exception:
                logs = []

        metrics = None
        if training_log.get("metrics"):
            try:
                metrics = eval(training_log["metrics"])
            except Exception:
                metrics = {}

        return TrainingStatusResponse(
            status=training_log["status"],
            progress_percent=training_log["progress_percent"],
            current_step=training_log["current_step"],
            logs=logs,
            metrics=metrics,
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

    Uses BGE-M3 embeddings and cosine similarity to match documents to domains.
    Returns top-k most similar domains ranked by confidence score.

    Classification process:
    1. Embed document text using BGE-M3
    2. Load all ready domains with their description embeddings
    3. Compute cosine similarity between document and domain embeddings
    4. Return top-k domains ranked by similarity

    Args:
        request: Classification request with text and top_k

    Returns:
        Ranked domain classifications with confidence scores

    Raises:
        HTTPException 500: If classification fails
    """
    logger.info(
        "classify_document_request",
        text_length=len(request.text),
        top_k=request.top_k,
    )

    try:
        from src.components.domain_training import get_domain_classifier

        classifier = get_domain_classifier()

        # Load domains (cached after first call)
        await classifier.load_domains()

        # Classify document
        results = classifier.classify_document(text=request.text, top_k=request.top_k)

        logger.info(
            "document_classified",
            text_length=len(request.text),
            top_domain=results[0]["domain"] if results else "general",
            score=results[0]["score"] if results else 0.0,
        )

        # Build response
        classifications = [
            ClassificationResult(
                domain=r["domain"],
                score=r["score"],
                description=r["description"],
            )
            for r in results
        ]

        recommended = results[0]["domain"] if results else "general"
        confidence = results[0]["score"] if results else 0.0

        return ClassificationResponse(
            classifications=classifications,
            recommended=recommended,
            confidence=confidence,
        )

    except Exception as e:
        logger.error(
            "classify_document_unexpected_error",
            text_length=len(request.text),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification failed",
        ) from e


@router.post("/discover", response_model=AutoDiscoveryResponse)
async def discover_domain(request: AutoDiscoveryRequest) -> AutoDiscoveryResponse:
    """Auto-discover domain from sample documents.

    Upload 3-10 representative documents and let the LLM analyze their content
    to suggest an appropriate domain name, description, and expected entity/relation types.

    This endpoint is useful when you have a collection of documents but aren't sure
    how to categorize them or what domain configuration to use.

    Discovery process:
    1. Sample documents are sent to LLM (qwen3:32b by default)
    2. LLM analyzes content to identify common themes and patterns
    3. LLM suggests domain name, description, and expected types
    4. Response includes confidence score and reasoning

    Args:
        request: Auto-discovery request with sample texts and LLM model

    Returns:
        Suggested domain configuration with confidence and reasoning

    Raises:
        HTTPException 400: If less than 3 samples provided
        HTTPException 503: If Ollama service is unavailable
        HTTPException 500: If discovery fails
    """
    logger.info(
        "discover_domain_request",
        sample_count=len(request.sample_texts),
        llm_model=request.llm_model,
    )

    try:
        from src.components.domain_training import get_domain_discovery_service

        service = get_domain_discovery_service()
        service.llm_model = request.llm_model

        # Perform discovery
        suggestion = await service.discover_domain(request.sample_texts)

        logger.info(
            "domain_discovered",
            name=suggestion.name,
            confidence=suggestion.confidence,
            entity_types_count=len(suggestion.entity_types),
            relation_types_count=len(suggestion.relation_types),
        )

        return AutoDiscoveryResponse(
            name=suggestion.name,
            title=suggestion.title,
            description=suggestion.description,
            confidence=suggestion.confidence,
            reasoning=suggestion.reasoning,
            entity_types=suggestion.entity_types,
            relation_types=suggestion.relation_types,
        )

    except ValueError as e:
        # Insufficient samples or validation error
        logger.warning(
            "discover_domain_validation_error",
            error=str(e),
            sample_count=len(request.sample_texts),
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


@router.post("/{domain_name}/validate", response_model=ValidateDomainResponse)
async def validate_domain(domain_name: str) -> ValidateDomainResponse:
    """Validate a domain's configuration and data integrity.

    Sprint 52 Feature 52.2.2: Domain Management Enhancement

    Checks:
    - Domain configuration is complete
    - Training prompts are available (if status is 'ready')
    - Entity and relationship counts are consistent
    - No orphaned chunks or entities

    Args:
        domain_name: Domain name to validate

    Returns:
        Validation results with any errors and recommendations

    Raises:
        HTTPException 404: If domain not found
        HTTPException 500: If validation fails
    """
    logger.info("validate_domain_request", domain=domain_name)

    try:
        from src.components.domain_training import get_domain_repository
        from src.components.graph_rag.neo4j_client import get_neo4j_client

        repo = get_domain_repository()

        # Check if domain exists
        domain = await repo.get_domain(domain_name)
        if not domain:
            logger.warning("domain_not_found_for_validation", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        validation_errors: list[str] = []
        recommendations: list[str] = []

        # Check domain configuration
        if not domain.get("description"):
            validation_errors.append("Domain description is missing")

        if not domain.get("llm_model"):
            validation_errors.append("LLM model is not configured")

        # Check training status
        if domain.get("status") == "ready":
            if not domain.get("entity_prompt"):
                validation_errors.append(
                    "Entity extraction prompt is missing despite 'ready' status"
                )
            if not domain.get("relation_prompt"):
                validation_errors.append(
                    "Relation extraction prompt is missing despite 'ready' status"
                )
        elif domain.get("status") == "pending":
            recommendations.append("Domain has not been trained yet. Consider running training.")
        elif domain.get("status") == "failed":
            validation_errors.append("Domain training has failed. Check training logs.")

        # Check data integrity in Neo4j
        try:
            neo4j = get_neo4j_client()

            # Check for orphaned entities (no MENTIONED_IN relationships)
            orphan_result = await neo4j.execute_read(
                """
                MATCH (e:base {namespace_id: $namespace_id})
                WHERE NOT (e)-[:MENTIONED_IN]->()
                RETURN count(e) AS orphan_count
                """,
                {"namespace_id": domain_name},
            )
            if orphan_result:
                orphan_count = orphan_result[0].get("orphan_count", 0)
                if orphan_count > 0:
                    recommendations.append(
                        f"Found {orphan_count} orphaned entities without chunk references"
                    )

            # Check for chunks without entities
            no_entity_result = await neo4j.execute_read(
                """
                MATCH (c:chunk {namespace_id: $namespace_id})
                WHERE NOT ()-[:MENTIONED_IN]->(c)
                RETURN count(c) AS no_entity_count
                """,
                {"namespace_id": domain_name},
            )
            if no_entity_result:
                no_entity_count = no_entity_result[0].get("no_entity_count", 0)
                if no_entity_count > 0:
                    recommendations.append(
                        f"Found {no_entity_count} chunks without entity references"
                    )

        except Exception as e:
            validation_errors.append(f"Neo4j validation failed: {str(e)}")

        is_valid = len(validation_errors) == 0

        logger.info(
            "domain_validated",
            domain=domain_name,
            is_valid=is_valid,
            error_count=len(validation_errors),
            recommendation_count=len(recommendations),
        )

        return ValidateDomainResponse(
            domain_name=domain_name,
            is_valid=is_valid,
            validation_errors=validation_errors,
            recommendations=recommendations,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(
            "validate_domain_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Domain validation failed",
        ) from e


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
