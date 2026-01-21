"""Domain Repository for DSPy-based Training Configuration.

Sprint 45 - Feature 45.1: Domain Registry in Neo4j
Sprint 83 - Feature 83.2: ERExtractionSettings (Cascade Configuration)

This module provides a repository for managing domain-specific extraction prompts
and training configurations in Neo4j. Domains are matched to documents using
semantic similarity of description embeddings.

Neo4j Schema:
    (:Domain {
        id: uuid,
        name: string (unique, lowercase, underscores),
        description: string,
        description_embedding: float[] (1024-dim BGE-M3),
        entity_prompt: string,
        relation_prompt: string,
        entity_examples: string (JSON array),
        relation_examples: string (JSON array),
        llm_model: string,
        extraction_model_cascade: string (JSON array, Sprint 83),  # Custom cascade configuration
        extraction_settings: string (JSON object, Sprint 83.4),  # ERExtractionSettings (fast vs refinement)
        training_samples: int,
        training_metrics: string (JSON object),
        status: string (pending/training/ready/failed),
        created_at: datetime,
        updated_at: datetime,
        trained_at: datetime
    })

    (:TrainingLog {
        id: uuid,
        started_at: datetime,
        completed_at: datetime,
        status: string (pending/running/completed/failed),
        current_step: string,
        progress_percent: float,
        log_messages: string (JSON array),
        metrics: string (JSON object),
        error_message: string
    })

    (d:Domain)-[:HAS_TRAINING_LOG]->(t:TrainingLog)

Example:
    >>> repo = get_domain_repository()
    >>> await repo.initialize()
    >>> domain = await repo.create_domain(
    ...     name="tech_docs",
    ...     description="Technical documentation...",
    ...     llm_model="qwen3:32b",
    ...     description_embedding=[0.1, 0.2, ...]
    ... )
    >>> matched = await repo.find_best_matching_domain(doc_embedding)
"""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

import structlog
from neo4j import AsyncTransaction
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)

# Constants
DEFAULT_DOMAIN_NAME = "general"
DEFAULT_DOMAIN_DESCRIPTION = (
    "General-purpose domain for documents that don't match specialized domains"
)
DEFAULT_SIMILARITY_THRESHOLD = 0.5
MAX_RETRY_ATTEMPTS = 3


# --- Pydantic Models ---


class DomainLLMConfig(BaseModel):
    """LLM configuration per domain.

    Sprint 117.12: Per-domain LLM model selection.

    Attributes:
        training_model: LLM model for DSPy prompt optimization (larger, slower, better quality)
        training_temperature: Temperature for training model (default: 0.7)
        training_max_tokens: Max tokens for training model (default: 4096)
        extraction_model: LLM model for production entity/relation extraction (faster)
        extraction_temperature: Temperature for extraction model (default: 0.3)
        extraction_max_tokens: Max tokens for extraction model (default: 2048)
        classification_model: LLM model for C-LARA fallback LLM verification
        provider: Model provider (ollama/alibaba/openai)

    Example:
        >>> config = DomainLLMConfig(
        ...     training_model="qwen3:32b",
        ...     extraction_model="nemotron3",
        ...     classification_model="nemotron3"
        ... )
        >>> config.to_dict()
    """

    # DSPy Training Model (for prompt optimization)
    training_model: str = Field(
        default="qwen3:32b",
        description="LLM model for DSPy training (larger, better quality)",
    )
    training_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for training model",
    )
    training_max_tokens: int = Field(
        default=4096,
        ge=128,
        le=32768,
        description="Max tokens for training model",
    )

    # Production Extraction Model (for entity/relation extraction)
    extraction_model: str = Field(
        default="nemotron3",
        description="LLM model for production extraction (faster)",
    )
    extraction_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for extraction model",
    )
    extraction_max_tokens: int = Field(
        default=2048,
        ge=128,
        le=32768,
        description="Max tokens for extraction model",
    )

    # Classification Model (for C-LARA fallback LLM verification)
    classification_model: str = Field(
        default="nemotron3",
        description="LLM model for intent classification",
    )

    # Model Provider
    provider: Literal["ollama", "alibaba", "openai"] = Field(
        default="ollama",
        description="Model provider",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Neo4j storage."""
        return {
            "training_model": self.training_model,
            "training_temperature": self.training_temperature,
            "training_max_tokens": self.training_max_tokens,
            "extraction_model": self.extraction_model,
            "extraction_temperature": self.extraction_temperature,
            "extraction_max_tokens": self.extraction_max_tokens,
            "classification_model": self.classification_model,
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DomainLLMConfig":
        """Create from dictionary loaded from Neo4j."""
        return cls(**data)


class DomainRepository:
    """Repository for managing domain training configurations in Neo4j.

    Provides methods for:
    - Creating and managing domain configurations
    - Semantic domain matching using embeddings
    - Training log tracking with progress and metrics
    - Default "general" domain fallback
    """

    def __init__(self) -> None:
        """Initialize domain repository with Neo4j client."""
        self.neo4j_client = get_neo4j_client()
        logger.info(
            "domain_repository_initialized",
            neo4j_uri=settings.neo4j_uri,
            neo4j_database=settings.neo4j_database,
        )

    @asynccontextmanager
    async def transaction(self):
        """Create a Neo4j transaction context for atomic operations.

        Use this context manager to ensure multiple domain operations are
        executed atomically. If any operation fails, all changes are rolled back.

        Yields:
            AsyncTransaction: Neo4j transaction object

        Example:
            >>> async with repo.transaction() as tx:
            ...     await repo.create_domain(..., tx=tx)
            ...     await repo.save_training_results(..., tx=tx)
            ...     # Commits automatically on success
            ...     # Rolls back on exception
        """
        async with self.neo4j_client.driver.session() as session:
            async with session.begin_transaction() as tx:
                try:
                    yield tx
                    # Commit handled by context manager
                except Exception:
                    await tx.rollback()
                    raise

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(DatabaseConnectionError),
    )
    async def initialize(self) -> None:
        """Initialize domain repository with constraints and default domain.

        Creates:
        - Unique constraint on Domain.name
        - Vector index on Domain.description_embedding
        - Default "general" domain if not exists

        Raises:
            DatabaseConnectionError: If initialization fails after retries
        """
        logger.info("initializing_domain_repository")

        try:
            # Create unique constraint on domain name
            await self.neo4j_client.execute_write(
                """
                CREATE CONSTRAINT domain_name_unique IF NOT EXISTS
                FOR (d:Domain) REQUIRE d.name IS UNIQUE
                """
            )
            logger.info("domain_constraint_created")

            # Create index on domain status for efficient filtering
            await self.neo4j_client.execute_write(
                """
                CREATE INDEX domain_status_idx IF NOT EXISTS
                FOR (d:Domain) ON (d.status)
                """
            )
            logger.info("domain_status_index_created")

            # Check if default domain exists
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $name})
                RETURN d
                """,
                {"name": DEFAULT_DOMAIN_NAME},
            )

            if not result:
                # Create default "general" domain with zero embedding
                # Zero embedding ensures it doesn't match any specific domain
                zero_embedding = [0.0] * 1024  # BGE-M3 dimension
                await self.create_domain(
                    name=DEFAULT_DOMAIN_NAME,
                    description=DEFAULT_DOMAIN_DESCRIPTION,
                    llm_model=settings.lightrag_llm_model,
                    description_embedding=zero_embedding,
                )
                logger.info("default_domain_created", name=DEFAULT_DOMAIN_NAME)
            else:
                logger.info("default_domain_exists", name=DEFAULT_DOMAIN_NAME)

        except Exception as e:
            logger.error("domain_repository_initialization_failed", error=str(e))
            raise DatabaseConnectionError(
                "Neo4j", f"Domain repository initialization failed: {e}"
            ) from e

    async def create_domain(
        self,
        name: str,
        description: str,
        llm_model: str,
        description_embedding: list[float],
        status: str = "pending",
        llm_config: DomainLLMConfig | None = None,
        tx: AsyncTransaction | None = None,
    ) -> dict[str, Any]:
        """Create a new domain configuration.

        Sprint 117.12: Added llm_config parameter for per-domain LLM model selection.

        Args:
            name: Unique domain name (lowercase, underscores)
            description: Human-readable domain description
            llm_model: LLM model to use for extraction (e.g., "qwen3:32b") - DEPRECATED, use llm_config
            description_embedding: BGE-M3 embedding of description (1024-dim)
            status: Initial domain status (default: "pending")
            llm_config: LLM configuration (training/extraction/classification models) - Sprint 117.12
            tx: Optional transaction for rollback support

        Returns:
            Dictionary with created domain properties

        Raises:
            DatabaseConnectionError: If domain creation fails
            ValueError: If domain name already exists
        """
        # Default llm_config if not provided
        if llm_config is None:
            llm_config = DomainLLMConfig(
                training_model=llm_model,
                extraction_model=llm_model,
                classification_model=llm_model,
            )

        logger.info(
            "creating_domain",
            name=name,
            llm_model=llm_model,
            llm_config=llm_config.to_dict(),
            embedding_dim=len(description_embedding),
            status=status,
            transactional=tx is not None,
        )

        # Validate name format (lowercase, underscores only)
        if not name.replace("_", "").islower():
            raise ValueError(f"Domain name must be lowercase with underscores: {name}")

        # Validate embedding dimension
        if len(description_embedding) != 1024:
            raise ValueError(f"Embedding must be 1024-dim, got {len(description_embedding)}")

        domain_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Serialize llm_config to JSON
        llm_config_json = json.dumps(llm_config.to_dict())

        query = """
        CREATE (d:Domain {
            id: $id,
            name: $name,
            description: $description,
            description_embedding: $embedding,
            entity_prompt: null,
            relation_prompt: null,
            entity_examples: '[]',
            relation_examples: '[]',
            llm_model: $llm_model,
            llm_config: $llm_config,
            extraction_settings: '{}',
            training_samples: 0,
            training_metrics: '{}',
            status: $status,
            created_at: datetime($created_at),
            updated_at: datetime($updated_at),
            trained_at: null
        })
        RETURN d.id as id, d.name as name, d.status as status
        """

        params = {
            "id": domain_id,
            "name": name,
            "description": description,
            "embedding": description_embedding,
            "llm_model": llm_model,
            "llm_config": llm_config_json,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }

        try:
            if tx:
                # Use provided transaction
                result = await tx.run(query, params)
                record = await result.single()
            else:
                # Create own session
                await self.neo4j_client.execute_write(query, params)
                record = None

            logger.info(
                "domain_created",
                domain_id=domain_id,
                name=name,
                status=status,
                transactional=tx is not None,
            )

            return {
                "id": domain_id,
                "name": name,
                "description": description,
                "llm_model": llm_model,
                "status": status,
                "created_at": now,
            }

        except Exception as e:
            if "ConstraintValidationFailed" in str(e):
                raise ValueError(f"Domain with name '{name}' already exists") from e

            logger.error("domain_creation_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Domain creation failed: {e}") from e

    async def get_domain(self, name: str) -> dict[str, Any] | None:
        """Get domain configuration by name.

        Args:
            name: Domain name

        Returns:
            Domain configuration dict or None if not found

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info("getting_domain", name=name)

        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $name})
                RETURN d.id as id, d.name as name, d.description as description,
                       d.entity_prompt as entity_prompt, d.relation_prompt as relation_prompt,
                       d.entity_examples as entity_examples,
                       d.relation_examples as relation_examples,
                       d.llm_model as llm_model, d.training_samples as training_samples,
                       d.training_metrics as training_metrics, d.status as status,
                       d.created_at as created_at, d.updated_at as updated_at,
                       d.trained_at as trained_at
                """,
                {"name": name},
            )

            if not result:
                logger.info("domain_not_found", name=name)
                return None

            domain = result[0]
            logger.info("domain_retrieved", name=name, status=domain["status"])
            return domain

        except Exception as e:
            logger.error("get_domain_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Get domain failed: {e}") from e

    async def list_domains(self) -> list[dict[str, Any]]:
        """List all domains.

        Returns:
            List of domain configuration dictionaries

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info("listing_domains")

        try:
            results = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain)
                RETURN d.id as id, d.name as name, d.description as description,
                       d.llm_model as llm_model, d.training_samples as training_samples,
                       d.status as status, d.created_at as created_at,
                       d.trained_at as trained_at
                ORDER BY d.created_at DESC
                """
            )

            logger.info("domains_listed", count=len(results))
            return results

        except Exception as e:
            logger.error("list_domains_failed", error=str(e))
            raise DatabaseConnectionError("Neo4j", f"List domains failed: {e}") from e

    async def update_domain_status(
        self,
        domain_name: str,
        status: str,
        tx: AsyncTransaction | None = None,
    ) -> None:
        """Update domain status.

        Args:
            domain_name: Domain name
            status: New status (pending/training/ready/failed)
            tx: Optional transaction for rollback support

        Raises:
            DatabaseConnectionError: If update fails
        """
        logger.info("updating_domain_status", domain=domain_name, status=status)

        query = """
        MATCH (d:Domain {name: $name})
        SET d.status = $status, d.updated_at = datetime($updated_at)
        RETURN d.name as name
        """

        params = {
            "name": domain_name,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            if tx:
                await tx.run(query, params)
            else:
                await self.neo4j_client.execute_write(query, params)

            logger.info("domain_status_updated", domain=domain_name, status=status)

        except Exception as e:
            logger.error("update_domain_status_failed", domain=domain_name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Update domain status failed: {e}") from e

    async def save_training_results(
        self,
        domain_name: str,
        entity_prompt: str,
        relation_prompt: str,
        entity_examples: list[dict[str, Any]],
        relation_examples: list[dict[str, Any]],
        metrics: dict[str, Any],
        status: str = "ready",
        tx: AsyncTransaction | None = None,
    ) -> None:
        """Save training results to domain with transaction support.

        Args:
            domain_name: Domain name
            entity_prompt: Optimized entity extraction prompt
            relation_prompt: Optimized relation extraction prompt
            entity_examples: Entity extraction examples
            relation_examples: Relation extraction examples
            metrics: Training metrics
            status: Domain status after training (default: "ready")
            tx: Optional transaction for rollback support

        Raises:
            DatabaseConnectionError: If save fails
        """
        logger.info(
            "saving_training_results",
            domain=domain_name,
            entity_examples_count=len(entity_examples),
            relation_examples_count=len(relation_examples),
            status=status,
        )

        now = datetime.utcnow().isoformat()
        entity_examples_json = json.dumps(entity_examples)
        relation_examples_json = json.dumps(relation_examples)
        metrics_json = json.dumps(metrics)

        query = """
        MATCH (d:Domain {name: $name})
        SET d.entity_prompt = $entity_prompt,
            d.relation_prompt = $relation_prompt,
            d.entity_examples = $entity_examples,
            d.relation_examples = $relation_examples,
            d.training_samples = $training_samples,
            d.training_metrics = $metrics,
            d.status = $status,
            d.updated_at = datetime($updated_at),
            d.trained_at = datetime($trained_at)
        RETURN d.name as name
        """

        params = {
            "name": domain_name,
            "entity_prompt": entity_prompt,
            "relation_prompt": relation_prompt,
            "entity_examples": entity_examples_json,
            "relation_examples": relation_examples_json,
            "training_samples": len(entity_examples) + len(relation_examples),
            "metrics": metrics_json,
            "status": status,
            "updated_at": now,
            "trained_at": now,
        }

        try:
            if tx:
                await tx.run(query, params)
            else:
                await self.neo4j_client.execute_write(query, params)

            logger.info("training_results_saved", domain=domain_name, status=status)

        except Exception as e:
            logger.error("save_training_results_failed", domain=domain_name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Save training results failed: {e}") from e

    async def update_domain_prompts(
        self,
        name: str,
        entity_prompt: str,
        relation_prompt: str,
        entity_examples: list[dict[str, Any]],
        relation_examples: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> bool:
        """Update domain prompts and training results after DSPy optimization.

        Args:
            name: Domain name
            entity_prompt: Optimized entity extraction prompt
            relation_prompt: Optimized relation extraction prompt
            entity_examples: Entity extraction examples (list of dicts)
            relation_examples: Relation extraction examples (list of dicts)
            metrics: Training metrics (e.g., {"entity_f1": 0.85})

        Returns:
            True if update successful

        Raises:
            DatabaseConnectionError: If update fails
        """
        logger.info(
            "updating_domain_prompts",
            name=name,
            entity_examples_count=len(entity_examples),
            relation_examples_count=len(relation_examples),
        )

        now = datetime.utcnow().isoformat()
        entity_examples_json = json.dumps(entity_examples)
        relation_examples_json = json.dumps(relation_examples)
        metrics_json = json.dumps(metrics)

        try:
            await self.neo4j_client.execute_write(
                """
                MATCH (d:Domain {name: $name})
                SET d.entity_prompt = $entity_prompt,
                    d.relation_prompt = $relation_prompt,
                    d.entity_examples = $entity_examples,
                    d.relation_examples = $relation_examples,
                    d.training_samples = $training_samples,
                    d.training_metrics = $metrics,
                    d.status = 'ready',
                    d.updated_at = datetime($updated_at),
                    d.trained_at = datetime($trained_at)
                RETURN d.name as name
                """,
                {
                    "name": name,
                    "entity_prompt": entity_prompt,
                    "relation_prompt": relation_prompt,
                    "entity_examples": entity_examples_json,
                    "relation_examples": relation_examples_json,
                    "training_samples": len(entity_examples) + len(relation_examples),
                    "metrics": metrics_json,
                    "updated_at": now,
                    "trained_at": now,
                },
            )

            logger.info("domain_prompts_updated", name=name, status="ready")
            return True

        except Exception as e:
            logger.error("update_domain_prompts_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Update domain prompts failed: {e}") from e

    async def update_extraction_settings(
        self,
        name: str,
        extraction_settings: dict[str, Any],
    ) -> bool:
        """Update domain extraction settings for fast vs refinement strategies.

        Sprint 83 Feature 83.4: ERExtractionSettings for two-phase upload.

        Args:
            name: Domain name
            extraction_settings: Extraction settings dict (e.g., {"fast_strategy": "spacy_ner", "refinement_strategy": "llm_gleaning"})

        Returns:
            True if update successful

        Raises:
            DatabaseConnectionError: If update fails
        """
        logger.info(
            "updating_extraction_settings",
            name=name,
            settings=extraction_settings,
        )

        now = datetime.utcnow().isoformat()
        settings_json = json.dumps(extraction_settings)

        try:
            await self.neo4j_client.execute_write(
                """
                MATCH (d:Domain {name: $name})
                SET d.extraction_settings = $settings,
                    d.updated_at = datetime($updated_at)
                RETURN d.name as name
                """,
                {
                    "name": name,
                    "settings": settings_json,
                    "updated_at": now,
                },
            )

            logger.info("extraction_settings_updated", name=name)
            return True

        except Exception as e:
            logger.error("update_extraction_settings_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Update extraction settings failed: {e}") from e

    async def get_extraction_settings(self, name: str) -> dict[str, Any]:
        """Get domain extraction settings.

        Sprint 83 Feature 83.4: Retrieve ERExtractionSettings for document processing.

        Args:
            name: Domain name

        Returns:
            Extraction settings dict (empty dict if not set)

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info("getting_extraction_settings", name=name)

        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $name})
                RETURN d.extraction_settings as extraction_settings
                """,
                {"name": name},
            )

            if not result or not result[0].get("extraction_settings"):
                logger.info("extraction_settings_not_found", name=name)
                return {}

            settings_json = result[0]["extraction_settings"]
            settings = json.loads(settings_json) if settings_json else {}

            logger.info("extraction_settings_retrieved", name=name, settings=settings)
            return settings

        except Exception as e:
            logger.error("get_extraction_settings_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Get extraction settings failed: {e}") from e

    async def find_best_matching_domain(
        self,
        document_embedding: list[float],
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> dict[str, Any] | None:
        """Find best matching domain for a document using cosine similarity.

        Args:
            document_embedding: BGE-M3 embedding of document (1024-dim)
            threshold: Minimum cosine similarity threshold (default: 0.5)

        Returns:
            Dict with {"domain": domain_dict, "score": float} or None if no match

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info(
            "finding_best_matching_domain",
            embedding_dim=len(document_embedding),
            threshold=threshold,
        )

        # Validate embedding dimension
        if len(document_embedding) != 1024:
            raise ValueError(f"Embedding must be 1024-dim, got {len(document_embedding)}")

        try:
            # Calculate cosine similarity using Neo4j vector functions
            # Note: Neo4j uses gds.similarity.cosine for vector similarity
            # Formula: similarity = dot(a, b) / (norm(a) * norm(b))
            results = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain)
                WHERE d.status = 'ready' AND d.name <> $default_domain
                WITH d,
                     reduce(dot = 0.0, i IN range(0, size(d.description_embedding)-1) |
                            dot + d.description_embedding[i] * $doc_embedding[i]) AS dot_product,
                     sqrt(reduce(sum = 0.0, x IN d.description_embedding | sum + x * x)) AS norm_domain,
                     sqrt(reduce(sum = 0.0, x IN $doc_embedding | sum + x * x)) AS norm_doc
                WITH d, dot_product / (norm_domain * norm_doc) AS similarity
                WHERE similarity >= $threshold
                RETURN d.id as id, d.name as name, d.description as description,
                       d.entity_prompt as entity_prompt, d.relation_prompt as relation_prompt,
                       d.llm_model as llm_model, similarity
                ORDER BY similarity DESC
                LIMIT 1
                """,
                {
                    "doc_embedding": document_embedding,
                    "threshold": threshold,
                    "default_domain": DEFAULT_DOMAIN_NAME,
                },
            )

            if not results:
                logger.info(
                    "no_matching_domain_found",
                    threshold=threshold,
                    fallback=DEFAULT_DOMAIN_NAME,
                )
                return None

            match = results[0]
            score = match.pop("similarity")

            logger.info(
                "domain_matched",
                domain_name=match["name"],
                similarity_score=round(score, 3),
            )

            return {"domain": match, "score": score}

        except Exception as e:
            logger.error("find_best_matching_domain_failed", error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Find matching domain failed: {e}") from e

    async def update_domain(
        self,
        name: str,
        description: str | None = None,
        entity_types: list[str] | None = None,
        relation_types: list[str] | None = None,
        intent_classes: list[str] | None = None,
        confidence_threshold: float | None = None,
        status: str | None = None,
        llm_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update domain configuration.

        Sprint 117 Feature 117.1: Domain CRUD API - Update endpoint.

        Args:
            name: Domain name
            description: Updated description (optional)
            entity_types: Updated entity types (optional)
            relation_types: Updated relation types (optional, MENTIONED_IN auto-added)
            intent_classes: Updated intent classes (optional)
            confidence_threshold: Updated confidence threshold (optional)
            status: Updated status (optional)
            llm_config: Updated LLM configuration (optional)

        Returns:
            Updated domain configuration dict

        Raises:
            DatabaseConnectionError: If update fails
            ValueError: If domain not found or trying to update default domain
        """
        if name == DEFAULT_DOMAIN_NAME:
            raise ValueError(f"Cannot update default domain: {name}")

        logger.info("updating_domain", name=name)

        # Build dynamic SET clause
        set_clauses = ["d.updated_at = datetime($updated_at)"]
        params: dict[str, Any] = {
            "name": name,
            "updated_at": datetime.utcnow().isoformat(),
        }

        if description is not None:
            set_clauses.append("d.description = $description")
            params["description"] = description

        if entity_types is not None:
            # Validate entity types
            for entity_type in entity_types:
                if not (5 <= len(entity_type) <= 50):
                    raise ValueError(
                        f"Entity type '{entity_type}' must be 5-50 characters, got {len(entity_type)}"
                    )
            set_clauses.append("d.entity_types = $entity_types")
            params["entity_types"] = json.dumps(entity_types)

        if relation_types is not None:
            # Validate relation types
            for relation_type in relation_types:
                if not (5 <= len(relation_type) <= 50):
                    raise ValueError(
                        f"Relation type '{relation_type}' must be 5-50 characters, got {len(relation_type)}"
                    )
            # CRITICAL: Ensure MENTIONED_IN is always present
            if "MENTIONED_IN" not in relation_types:
                relation_types.append("MENTIONED_IN")
                logger.info(
                    "mentioned_in_auto_added",
                    name=name,
                    relation_types=relation_types,
                )
            set_clauses.append("d.relation_types = $relation_types")
            params["relation_types"] = json.dumps(relation_types)

        if intent_classes is not None:
            set_clauses.append("d.intent_classes = $intent_classes")
            params["intent_classes"] = json.dumps(intent_classes)

        if confidence_threshold is not None:
            if not (0.0 <= confidence_threshold <= 1.0):
                raise ValueError(
                    f"Confidence threshold must be 0.0-1.0, got {confidence_threshold}"
                )
            set_clauses.append("d.confidence_threshold = $confidence_threshold")
            params["confidence_threshold"] = confidence_threshold

        if status is not None:
            if status not in ("active", "training", "inactive"):
                raise ValueError(f"Invalid status: {status}")
            set_clauses.append("d.status = $status")
            params["status"] = status

        if llm_config is not None:
            set_clauses.append("d.llm_config = $llm_config")
            params["llm_config"] = json.dumps(llm_config)

        set_clause = ", ".join(set_clauses)

        try:
            # Check if domain exists
            check_result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $name})
                RETURN d.id AS id
                """,
                {"name": name},
            )

            if not check_result:
                raise ValueError(f"Domain '{name}' not found")

            # Update domain
            await self.neo4j_client.execute_write(
                f"""
                MATCH (d:Domain {{name: $name}})
                SET {set_clause}
                RETURN d
                """,
                params,
            )

            # Retrieve updated domain
            updated_domain = await self.get_domain(name)
            if not updated_domain:
                raise DatabaseConnectionError("Neo4j", f"Failed to retrieve updated domain: {name}")

            logger.info("domain_updated", name=name)
            return updated_domain

        except ValueError:
            raise
        except Exception as e:
            logger.error("update_domain_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Update domain failed: {e}") from e

    async def delete_domain(self, name: str) -> bool:
        """Delete a domain and its training logs.

        Args:
            name: Domain name

        Returns:
            True if deletion successful, False if domain not found

        Raises:
            DatabaseConnectionError: If deletion fails
            ValueError: If trying to delete default domain
        """
        if name == DEFAULT_DOMAIN_NAME:
            raise ValueError(f"Cannot delete default domain: {name}")

        logger.info("deleting_domain", name=name)

        try:
            # First check if domain exists
            check_result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $name})
                RETURN d.id AS id
                """,
                {"name": name},
            )

            if not check_result:
                logger.warning("domain_not_found_for_deletion", name=name)
                return False

            # Delete domain and associated training logs
            await self.neo4j_client.execute_write(
                """
                MATCH (d:Domain {name: $name})
                OPTIONAL MATCH (d)-[:HAS_TRAINING_LOG]->(t:TrainingLog)
                DETACH DELETE d, t
                """,
                {"name": name},
            )

            logger.info("domain_deleted", name=name)
            return True

        except Exception as e:
            logger.error("delete_domain_failed", name=name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Delete domain failed: {e}") from e

    async def create_training_log(self, domain_name: str) -> dict[str, Any]:
        """Create a new training log for a domain.

        Args:
            domain_name: Domain name

        Returns:
            Created training log dictionary

        Raises:
            DatabaseConnectionError: If creation fails
        """
        logger.info("creating_training_log", domain_name=domain_name)

        log_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        try:
            # Use execute_query instead of execute_write to get RETURN values
            result = await self.neo4j_client.execute_query(
                """
                MATCH (d:Domain {name: $domain_name})
                CREATE (t:TrainingLog {
                    id: $id,
                    started_at: datetime($started_at),
                    completed_at: null,
                    status: 'pending',
                    current_step: 'Initializing...',
                    progress_percent: 0.0,
                    log_messages: '[]',
                    metrics: '{}',
                    error_message: null
                })
                CREATE (d)-[:HAS_TRAINING_LOG]->(t)
                SET d.status = 'training'
                RETURN t.id as id, t.status as status, t.started_at as started_at
                """,
                {
                    "id": log_id,
                    "domain_name": domain_name,
                    "started_at": now,
                },
            )

            if not result:
                raise ValueError(f"Domain '{domain_name}' not found")

            logger.info("training_log_created", log_id=log_id, domain=domain_name)

            return {
                "id": log_id,
                "domain_name": domain_name,
                "status": "pending",
                "started_at": now,
                "progress_percent": 0.0,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error("create_training_log_failed", domain=domain_name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Create training log failed: {e}") from e

    async def update_training_log(
        self,
        log_id: str,
        progress: float,
        message: str,
        status: str | None = None,
        metrics: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Update training log progress and status.

        Args:
            log_id: Training log ID
            progress: Progress percentage (0-100)
            message: Progress message
            status: Training status (pending/running/completed/failed)
            metrics: Training metrics dictionary
            error_message: Error message if failed

        Returns:
            True if update successful

        Raises:
            DatabaseConnectionError: If update fails
        """
        logger.info(
            "updating_training_log",
            log_id=log_id,
            progress=progress,
            status=status,
        )

        now = datetime.utcnow().isoformat()

        # Build SET clause dynamically based on provided parameters
        set_clauses = [
            "t.progress_percent = $progress",
            "t.current_step = $message",
        ]
        params: dict[str, Any] = {
            "log_id": log_id,
            "progress": progress,
            "message": message,
            "now": now,
        }

        if status:
            set_clauses.append("t.status = $status")
            params["status"] = status

        if metrics:
            set_clauses.append("t.metrics = $metrics")
            params["metrics"] = json.dumps(metrics)

        if error_message:
            set_clauses.append("t.error_message = $error_message")
            params["error_message"] = error_message

        if status == "completed":
            set_clauses.append("t.completed_at = datetime($now)")

        set_clause = ", ".join(set_clauses)

        try:
            await self.neo4j_client.execute_write(
                f"""
                MATCH (t:TrainingLog {{id: $log_id}})
                SET {set_clause}
                RETURN t.id as id
                """,
                params,
            )

            logger.info("training_log_updated", log_id=log_id, progress=progress)
            return True

        except Exception as e:
            logger.error("update_training_log_failed", log_id=log_id, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Update training log failed: {e}") from e

    async def get_latest_training_log(self, domain_name: str) -> dict[str, Any] | None:
        """Get latest training log for a domain.

        Args:
            domain_name: Domain name

        Returns:
            Latest training log dict or None if not found

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info("getting_latest_training_log", domain=domain_name)

        try:
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})-[:HAS_TRAINING_LOG]->(t:TrainingLog)
                RETURN t.id as id, t.started_at as started_at,
                       t.completed_at as completed_at, t.status as status,
                       t.current_step as current_step, t.progress_percent as progress_percent,
                       t.log_messages as log_messages, t.metrics as metrics,
                       t.error_message as error_message
                ORDER BY t.started_at DESC
                LIMIT 1
                """,
                {"domain_name": domain_name},
            )

            if not result:
                logger.info("no_training_log_found", domain=domain_name)
                return None

            log = result[0]
            logger.info("training_log_retrieved", domain=domain_name, status=log["status"])
            return log

        except Exception as e:
            logger.error("get_latest_training_log_failed", domain=domain_name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Get training log failed: {e}") from e

    async def append_training_log_message(
        self,
        log_id: str,
        timestamp: str,
        level: str,
        message: str,
        step: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> bool:
        """Append a log message to a training log.

        Sprint 117.6: Structured log message appending for training-logs endpoint.

        Args:
            log_id: Training log ID
            timestamp: Log timestamp (ISO 8601)
            level: Log level (INFO/WARNING/ERROR)
            message: Log message
            step: Optional training step name
            metrics: Optional metrics dictionary

        Returns:
            True if append successful

        Raises:
            DatabaseConnectionError: If append fails
        """
        logger.info(
            "appending_training_log_message",
            log_id=log_id,
            level=level,
            step=step,
        )

        # Create log entry dict
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
        }
        if step:
            log_entry["step"] = step
        if metrics:
            log_entry["metrics"] = metrics

        log_entry_json = json.dumps(log_entry)

        try:
            # Append to log_messages array
            await self.neo4j_client.execute_write(
                """
                MATCH (t:TrainingLog {id: $log_id})
                WITH t, CASE WHEN t.log_messages IS NULL OR t.log_messages = '[]'
                         THEN []
                         ELSE apoc.convert.fromJsonList(t.log_messages)
                         END AS current_logs
                SET t.log_messages = apoc.convert.toJson(current_logs + [$log_entry])
                RETURN t.id as id
                """,
                {
                    "log_id": log_id,
                    "log_entry": log_entry,
                },
            )

            logger.info("training_log_message_appended", log_id=log_id, level=level)
            return True

        except Exception as e:
            logger.error("append_training_log_message_failed", log_id=log_id, error=str(e))
            raise DatabaseConnectionError(
                "Neo4j", f"Append training log message failed: {e}"
            ) from e

    async def get_training_log_messages(
        self,
        domain_name: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated training log messages for a domain.

        Sprint 117.6: Paginated training logs retrieval.

        Args:
            domain_name: Domain name
            page: Page number (1-indexed)
            page_size: Number of logs per page (max 100)

        Returns:
            Dictionary with logs, total_logs, page, page_size

        Raises:
            DatabaseConnectionError: If query fails
        """
        logger.info(
            "getting_training_log_messages",
            domain=domain_name,
            page=page,
            page_size=page_size,
        )

        # Validate pagination parameters
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be 1-100")

        try:
            # Get latest training log with messages
            result = await self.neo4j_client.execute_read(
                """
                MATCH (d:Domain {name: $domain_name})-[:HAS_TRAINING_LOG]->(t:TrainingLog)
                WITH t
                ORDER BY t.started_at DESC
                LIMIT 1
                RETURN t.log_messages as log_messages
                """,
                {"domain_name": domain_name},
            )

            if not result or not result[0].get("log_messages"):
                logger.info("no_training_log_messages_found", domain=domain_name)
                return {
                    "logs": [],
                    "total_logs": 0,
                    "page": page,
                    "page_size": page_size,
                }

            # Parse log messages JSON array
            log_messages_json = result[0]["log_messages"]
            try:
                all_logs = json.loads(log_messages_json) if log_messages_json else []
            except json.JSONDecodeError:
                logger.warning(
                    "invalid_log_messages_json",
                    domain=domain_name,
                    json_value=log_messages_json,
                )
                all_logs = []

            # Calculate pagination
            total_logs = len(all_logs)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            # Reverse logs (newest first) and paginate
            logs_page = list(reversed(all_logs))[start_idx:end_idx]

            logger.info(
                "training_log_messages_retrieved",
                domain=domain_name,
                total_logs=total_logs,
                page_logs=len(logs_page),
            )

            return {
                "logs": logs_page,
                "total_logs": total_logs,
                "page": page,
                "page_size": page_size,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error("get_training_log_messages_failed", domain=domain_name, error=str(e))
            raise DatabaseConnectionError("Neo4j", f"Get training log messages failed: {e}") from e


# Global instance (singleton pattern)
_domain_repository: DomainRepository | None = None


def get_domain_repository() -> DomainRepository:
    """Get global domain repository instance (singleton).

    Returns:
        DomainRepository instance
    """
    global _domain_repository
    if _domain_repository is None:
        _domain_repository = DomainRepository()
    return _domain_repository
