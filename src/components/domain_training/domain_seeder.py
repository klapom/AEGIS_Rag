"""Domain Seeding on System Initialization.

Sprint 117 - Feature 117.9: Default Domain Seeding

This module provides automatic seeding of default domains on application startup.
Ensures that a "general" domain always exists for non-specialized content.

Architecture:
    - Idempotent seeding function (safe to run multiple times)
    - Uses DomainRepository for domain management
    - Called from FastAPI lifespan event on startup
    - Default domain has MENTIONED_IN relation for provenance tracking

Example:
    >>> from src.components.domain_training.domain_seeder import seed_default_domains
    >>> await seed_default_domains()
    >>> # "general" domain now exists in Neo4j

Notes:
    - Seeding is idempotent (checks if domain exists first)
    - Default domain cannot be deleted or updated (protected)
    - MENTIONED_IN relation type is CRITICAL for provenance
    - Uses zero embedding (won't match specific domains)
"""

from typing import Any

import structlog

from src.components.domain_training.domain_repository import get_domain_repository
from src.core.config import settings

logger = structlog.get_logger(__name__)

# Default domain configuration
DEFAULT_DOMAIN_CONFIG: dict[str, Any] = {
    "name": "general",
    "description": "General purpose domain for non-specialized content",
    "entity_types": ["Entity", "Person", "Organization", "Location", "Concept"],
    "relation_types": ["RELATES_TO", "MENTIONED_IN", "AUTHORED_BY", "LOCATED_IN"],
    "intent_classes": ["general_inquiry", "information_request", "clarification"],
    "model_family": "general",
    "confidence_threshold": 0.5,
    "status": "active",
}


async def seed_default_domains() -> None:
    """Seed default domains on system initialization.

    Creates the "general" domain with default configuration if it doesn't exist.
    This function is idempotent - safe to call multiple times without side effects.

    Domain Properties:
        - name: "general" (immutable, protected from deletion)
        - description: General purpose domain for non-specialized content
        - entity_types: 5 basic types (Entity, Person, Organization, Location, Concept)
        - relation_types: 4 basic types (RELATES_TO, MENTIONED_IN, AUTHORED_BY, LOCATED_IN)
        - intent_classes: 3 basic intents (general_inquiry, information_request, clarification)
        - model_family: "general"
        - confidence_threshold: 0.5
        - status: "active"
        - embedding: Zero vector (1024-dim, won't match specific domains)

    CRITICAL: MENTIONED_IN relation type is required for document provenance tracking.

    Raises:
        DatabaseConnectionError: If Neo4j connection fails
        ValueError: If domain creation fails due to validation errors

    Example:
        >>> # Called automatically on application startup
        >>> await seed_default_domains()
        >>> # Domain already exists (idempotent)
        >>> await seed_default_domains()

    Notes:
        - Called from FastAPI lifespan event (main.py)
        - Uses DomainRepository.create_domain() for atomic creation
        - Zero embedding ensures no semantic matching (fallback only)
        - Default domain is protected from update/delete operations
        - Logs INFO level for seeding activity

    See Also:
        - DomainRepository: Domain CRUD operations
        - main.py: Application startup hooks
        - ADR-XXX: Default domain architecture
    """
    logger.info(
        "seeding_default_domains",
        phase="startup",
        domain_name=DEFAULT_DOMAIN_CONFIG["name"],
    )

    repo = get_domain_repository()

    try:
        # Check if "general" domain already exists (idempotency check)
        existing_domain = await repo.get_domain(DEFAULT_DOMAIN_CONFIG["name"])

        if existing_domain:
            logger.info(
                "default_domain_exists",
                domain_name=DEFAULT_DOMAIN_CONFIG["name"],
                status=existing_domain.get("status", "unknown"),
                skip_reason="domain_already_seeded",
            )
            return

        # Create default domain with zero embedding (1024-dim for BGE-M3)
        # Zero embedding ensures it doesn't semantically match any specific domain
        zero_embedding = [0.0] * 1024

        # Create domain in Neo4j
        await repo.create_domain(
            name=DEFAULT_DOMAIN_CONFIG["name"],
            description=DEFAULT_DOMAIN_CONFIG["description"],
            llm_model=settings.lightrag_llm_model,  # Use system default LLM
            description_embedding=zero_embedding,
            status=DEFAULT_DOMAIN_CONFIG["status"],
        )

        logger.info(
            "default_domain_created",
            domain_name=DEFAULT_DOMAIN_CONFIG["name"],
            entity_types_count=len(DEFAULT_DOMAIN_CONFIG["entity_types"]),
            relation_types_count=len(DEFAULT_DOMAIN_CONFIG["relation_types"]),
            intent_classes_count=len(DEFAULT_DOMAIN_CONFIG["intent_classes"]),
            confidence_threshold=DEFAULT_DOMAIN_CONFIG["confidence_threshold"],
            has_mentioned_in=("MENTIONED_IN" in DEFAULT_DOMAIN_CONFIG["relation_types"]),
        )

    except ValueError as e:
        # Domain creation failed due to validation error
        # This could happen if domain name format is invalid
        logger.error(
            "default_domain_seeding_failed",
            domain_name=DEFAULT_DOMAIN_CONFIG["name"],
            error=str(e),
            error_type="validation_error",
        )
        raise

    except Exception as e:
        # Unexpected error during seeding (e.g., Neo4j connection failure)
        logger.error(
            "default_domain_seeding_failed",
            domain_name=DEFAULT_DOMAIN_CONFIG["name"],
            error=str(e),
            error_type="database_error",
        )
        raise
