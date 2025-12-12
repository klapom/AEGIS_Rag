"""Domain Training API Endpoints for DSPy-based Knowledge Graph Optimization.

Sprint 45 - Feature 45.3: Domain Training API

This module provides FastAPI endpoints for managing domain-specific extraction prompts
and training configurations. It enables creating domains, training them with DSPy,
and classifying documents to domains.

Key Endpoints:
- POST /admin/domains - Create new domain configuration
- GET /admin/domains - List all domains
- GET /admin/domains/{name} - Get domain details
- POST /admin/domains/{name}/train - Start DSPy training
- GET /admin/domains/{name}/training-status - Monitor training progress
- DELETE /admin/domains/{name} - Delete domain
- GET /admin/domains/available-models - List Ollama models
- POST /admin/domains/classify - Classify document to domain

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

from datetime import datetime
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
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

    status: str = Field(
        ..., description="Training status (pending/running/completed/failed)"
    )
    progress_percent: float = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str = Field(..., description="Current training step description")
    logs: list[dict[str, Any]] = Field(
        default_factory=list, description="Training log messages"
    )
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
        description_embedding = await embedding_service.embed_text(request.description)

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except DatabaseConnectionError as e:
        logger.error("domain_creation_db_error", name=request.name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        )

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
        )


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
        )

    except Exception as e:
        logger.error("list_domains_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


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
        )

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
        )


@router.post("/{domain_name}/train")
async def start_training(
    domain_name: str,
    dataset: TrainingDataset,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Start DSPy optimization for a domain.

    Launches background training that optimizes entity and relation extraction
    prompts using DSPy's BootstrapFewShot optimizer. Training progress can be
    monitored via GET /domains/{name}/training-status.

    Training process:
    1. Optimize entity extraction prompts
    2. Optimize relation extraction prompts
    3. Extract static prompts for production use
    4. Save prompts and metrics to domain

    Args:
        domain_name: Domain to train
        dataset: Training samples (minimum 5 recommended)
        background_tasks: FastAPI background task handler

    Returns:
        Training job information with status URL

    Raises:
        HTTPException 404: If domain not found
        HTTPException 409: If training already in progress
        HTTPException 500: If training job creation fails
    """
    logger.info(
        "start_training_request",
        domain=domain_name,
        sample_count=len(dataset.samples),
    )

    try:
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()
        domain = await repo.get_domain(domain_name)

        if not domain:
            logger.warning("training_domain_not_found", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        if domain.get("status") == "training":
            logger.warning("training_already_in_progress", domain=domain_name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Training already in progress for this domain",
            )

        # Create training log
        training_log = await repo.create_training_log(domain_name)

        logger.info(
            "training_job_created",
            domain=domain_name,
            training_run_id=training_log["id"],
        )

        # Import here to avoid circular dependency
        from src.components.domain_training.training_runner import run_dspy_optimization

        # Start background training
        background_tasks.add_task(
            run_dspy_optimization,
            domain_name=domain_name,
            training_run_id=training_log["id"],
            dataset=[s.model_dump() for s in dataset.samples],
        )

        logger.info(
            "training_started_background",
            domain=domain_name,
            training_run_id=training_log["id"],
        )

        return {
            "message": "Training started in background",
            "training_run_id": training_log["id"],
            "status_url": f"/admin/domains/{domain_name}/training-status",
            "domain": domain_name,
            "sample_count": len(dataset.samples),
        }

    except HTTPException:
        raise

    except DatabaseConnectionError as e:
        logger.error("start_training_db_error", domain=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        )

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
        )


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
        )

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
        )


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
        )

    except httpx.HTTPStatusError as e:
        logger.error("ollama_http_error", status_code=e.response.status_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ollama API error: {e.response.status_code}",
        )

    except Exception as e:
        logger.error("get_available_models_unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.delete("/{domain_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(domain_name: str) -> None:
    """Delete a domain configuration.

    Permanently deletes a domain and all associated training logs.
    The default 'general' domain cannot be deleted.

    Args:
        domain_name: Domain to delete

    Raises:
        HTTPException 400: If trying to delete default 'general' domain
        HTTPException 404: If domain not found
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

        repo = get_domain_repository()
        deleted = await repo.delete_domain(domain_name)

        if not deleted:
            logger.warning("domain_not_found_for_deletion", name=domain_name)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain '{domain_name}' not found",
            )

        logger.info("domain_deleted", name=domain_name)

    except HTTPException:
        raise

    except ValueError as e:
        # Cannot delete default domain
        logger.warning("domain_deletion_validation_error", name=domain_name, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except DatabaseConnectionError as e:
        logger.error("delete_domain_db_error", name=domain_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed",
        )

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
        )


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
        )
