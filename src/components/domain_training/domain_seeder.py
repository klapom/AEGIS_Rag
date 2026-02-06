"""Domain Seeding from YAML Catalog.

Sprint 117 - Feature 117.9: Default Domain Seeding
Sprint 125 - Feature 125.8: Domain Seeder Extension + Sub-Type Pipeline

This module provides automatic seeding of domains from data/seed_domains.yaml catalog.
Ensures that domains can be loaded from a standards-based taxonomy and supports
deployment profiles for customer-specific domain activation.

Architecture:
    - Loads domains from data/seed_domains.yaml (ADR-060 two-tier type system)
    - Uses DomainRepository for domain management
    - Idempotent seeding (MERGE semantics, preserves trained prompts)
    - Deployment profile support (pharma, law_firm, software_company, etc.)
    - Sub-type property support for entities (domain-specific types)

Example:
    >>> from src.components.domain_training.domain_seeder import seed_all_domains
    >>> await seed_all_domains()
    >>> # All 35 domains from seed_domains.yaml are now in Neo4j

    >>> from src.components.domain_training.domain_seeder import seed_domain
    >>> await seed_domain("medicine_health")
    >>> # Single domain seeded

    >>> from src.components.domain_training.domain_seeder import set_deployment_profile
    >>> await set_deployment_profile("pharma_company")
    >>> # Activates medicine_health, chemistry, biology_life_sciences domains

Notes:
    - Seeding is idempotent (checks if domain exists first)
    - Default domain cannot be deleted or updated (protected)
    - MENTIONED_IN relation type is CRITICAL for provenance
    - Uses zero embedding for default domain (won't match specific domains)
    - Sub-type property is optional on entities (only set when domain provides it)
"""

import os
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
import structlog
import yaml

from src.components.domain_training.domain_repository import (
    DomainLLMConfig,
    get_domain_repository,
)
from src.core.config import settings

logger = structlog.get_logger(__name__)

# Default domain configuration (backward compatibility)
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

# Redis key for active deployment profile
DEPLOYMENT_PROFILE_KEY = "aegis:deployment_profile"

# Path to seed_domains.yaml
SEED_DOMAINS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "seed_domains.yaml"


async def _get_redis_client() -> aioredis.Redis:
    """Get Redis client for deployment profile storage.

    Returns:
        Redis client instance

    Raises:
        ConnectionError: If Redis connection fails
    """
    redis_client = aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        encoding="utf-8",
        decode_responses=True,
    )
    return redis_client


def _load_seed_domains() -> dict[str, Any]:
    """Load domain catalog from data/seed_domains.yaml.

    Returns:
        Dictionary with keys:
            - universal_entity_types: List of 15 Tier 1 types
            - universal_relation_types: List of universal relations
            - deployment_profiles: Dict of profile_name -> config
            - domains: List of 35 domain configurations

    Raises:
        FileNotFoundError: If seed_domains.yaml not found
        ValueError: If YAML parsing fails
    """
    if not SEED_DOMAINS_PATH.exists():
        logger.error(
            "seed_domains_file_not_found",
            path=str(SEED_DOMAINS_PATH),
        )
        raise FileNotFoundError(f"seed_domains.yaml not found at {SEED_DOMAINS_PATH}")

    try:
        with open(SEED_DOMAINS_PATH, "r", encoding="utf-8") as f:
            catalog = yaml.safe_load(f)

        logger.info(
            "seed_domains_loaded",
            path=str(SEED_DOMAINS_PATH),
            domains_count=len(catalog.get("domains", [])),
            profiles_count=len(catalog.get("deployment_profiles", {})),
        )

        return catalog

    except Exception as e:
        logger.error(
            "seed_domains_load_failed",
            path=str(SEED_DOMAINS_PATH),
            error=str(e),
        )
        raise ValueError(f"Failed to load seed_domains.yaml: {e}") from e


async def seed_default_domains() -> None:
    """Seed default domains on system initialization (backward compatibility).

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
        - ADR-060: Two-tier domain type system
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


async def seed_domain(domain_id: str, catalog: dict[str, Any] | None = None) -> bool:
    """Seed a single domain from the catalog.

    Sprint 125 Feature 125.8: Domain Seeder Extension

    Args:
        domain_id: Domain identifier (e.g., "medicine_health", "computer_science_it")
        catalog: Optional pre-loaded catalog (avoids re-reading YAML)

    Returns:
        True if domain was created or already exists, False if domain not found in catalog

    Raises:
        DatabaseConnectionError: If Neo4j connection fails
        ValueError: If domain configuration is invalid

    Example:
        >>> await seed_domain("medicine_health")
        True
        >>> await seed_domain("nonexistent_domain")
        False
    """
    # Load catalog if not provided
    if catalog is None:
        catalog = _load_seed_domains()

    # Find domain in catalog
    domain_config = None
    for domain in catalog.get("domains", []):
        if domain.get("domain_id") == domain_id:
            domain_config = domain
            break

    if not domain_config:
        logger.warning(
            "domain_not_found_in_catalog",
            domain_id=domain_id,
        )
        return False

    repo = get_domain_repository()

    # Check if domain already exists (idempotency)
    existing_domain = await repo.get_domain(domain_id)

    if existing_domain:
        logger.info(
            "domain_already_exists",
            domain_id=domain_id,
            status=existing_domain.get("status", "unknown"),
            skip_reason="domain_already_seeded",
        )
        return True

    # Generate zero embedding (domains will use semantic matching later)
    # For now, use zero embedding to avoid circular dependency on embedding service
    zero_embedding = [0.0] * 1024

    # Build LLM config (use system defaults)
    llm_config = DomainLLMConfig(
        training_model=settings.lightrag_llm_model,
        extraction_model=settings.lightrag_llm_model,
        classification_model=settings.lightrag_llm_model,
    )

    # Create domain in Neo4j with MERGE semantics
    try:
        await repo.create_domain(
            name=domain_id,
            description=domain_config.get("description", ""),
            llm_model=settings.lightrag_llm_model,
            description_embedding=zero_embedding,
            status="pending",  # Will be set to "active" after training
            llm_config=llm_config,
        )

        logger.info(
            "domain_seeded",
            domain_id=domain_id,
            name=domain_config.get("name", domain_id),
            ddc_code=domain_config.get("ddc_code", ""),
            ford_code=domain_config.get("ford_code", ""),
            entity_sub_types_count=len(domain_config.get("entity_sub_types", [])),
            relation_hints_count=len(domain_config.get("relation_hints", [])),
        )

        return True

    except ValueError as e:
        logger.error(
            "domain_seeding_failed",
            domain_id=domain_id,
            error=str(e),
            error_type="validation_error",
        )
        raise

    except Exception as e:
        logger.error(
            "domain_seeding_failed",
            domain_id=domain_id,
            error=str(e),
            error_type="database_error",
        )
        raise


async def seed_all_domains() -> dict[str, Any]:
    """Seed all 35 domains from data/seed_domains.yaml.

    Sprint 125 Feature 125.8: Domain Seeder Extension

    This function:
    1. Loads the seed_domains.yaml catalog
    2. Seeds all domains in the catalog
    3. Preserves existing domains (idempotent MERGE semantics)
    4. Does NOT overwrite trained prompts (entity_prompt, relation_prompt)

    Returns:
        Dictionary with seeding statistics:
            - total_domains: Number of domains in catalog
            - domains_created: Number of new domains created
            - domains_skipped: Number of existing domains skipped
            - failed_domains: List of domain_ids that failed to seed

    Raises:
        FileNotFoundError: If seed_domains.yaml not found
        ValueError: If YAML parsing fails

    Example:
        >>> stats = await seed_all_domains()
        >>> print(f"Created {stats['domains_created']} domains")
        Created 35 domains
    """
    logger.info("seeding_all_domains", phase="startup")

    # Load catalog
    try:
        catalog = _load_seed_domains()
    except (FileNotFoundError, ValueError) as e:
        logger.error("seed_all_domains_aborted", error=str(e))
        raise

    domains = catalog.get("domains", [])

    stats = {
        "total_domains": len(domains),
        "domains_created": 0,
        "domains_skipped": 0,
        "failed_domains": [],
    }

    # Seed each domain
    for domain in domains:
        domain_id = domain.get("domain_id")
        if not domain_id:
            logger.warning("domain_missing_id_skipped", domain=domain)
            continue

        try:
            # Check if domain exists
            repo = get_domain_repository()
            existing_domain = await repo.get_domain(domain_id)

            if existing_domain:
                stats["domains_skipped"] += 1
                logger.debug(
                    "domain_already_exists_skip",
                    domain_id=domain_id,
                )
            else:
                # Seed domain
                success = await seed_domain(domain_id, catalog)
                if success:
                    stats["domains_created"] += 1
                else:
                    stats["failed_domains"].append(domain_id)

        except Exception as e:
            logger.error(
                "domain_seeding_error",
                domain_id=domain_id,
                error=str(e),
            )
            stats["failed_domains"].append(domain_id)

    logger.info(
        "all_domains_seeded",
        total=stats["total_domains"],
        created=stats["domains_created"],
        skipped=stats["domains_skipped"],
        failed=len(stats["failed_domains"]),
    )

    return stats


async def get_active_domains() -> list[str]:
    """Get list of active domain IDs based on deployment profile.

    Sprint 125 Feature 125.8: Deployment Profile Support

    Returns:
        List of domain IDs that are active for the current deployment profile.
        If no profile is set, returns all domains.
        If profile is "university", returns all domains.
        If profile is "custom", returns domains from Redis list.

    Example:
        >>> await set_deployment_profile("pharma_company")
        >>> domains = await get_active_domains()
        >>> domains
        ['medicine_health', 'chemistry', 'biology_life_sciences']

    Raises:
        FileNotFoundError: If seed_domains.yaml not found
        ConnectionError: If Redis connection fails
    """
    # Load catalog
    catalog = _load_seed_domains()
    profiles = catalog.get("deployment_profiles", {})

    # Get active profile from Redis
    try:
        redis_client = await _get_redis_client()
        profile_name = await redis_client.get(DEPLOYMENT_PROFILE_KEY)
        await redis_client.close()

        if not profile_name:
            logger.info("no_deployment_profile_set", default="all_domains")
            # Return all domain IDs
            return [d.get("domain_id") for d in catalog.get("domains", []) if d.get("domain_id")]

        logger.info("active_deployment_profile", profile=profile_name)

        # Get profile config
        profile_config = profiles.get(profile_name)
        if not profile_config:
            logger.warning(
                "unknown_deployment_profile",
                profile=profile_name,
                fallback="all_domains",
            )
            return [d.get("domain_id") for d in catalog.get("domains", []) if d.get("domain_id")]

        # Check if profile activates all domains
        profile_domains = profile_config.get("domains")
        if profile_domains == "ALL":
            logger.info("deployment_profile_all_domains", profile=profile_name)
            return [d.get("domain_id") for d in catalog.get("domains", []) if d.get("domain_id")]

        # Return profile-specific domains
        return profile_domains if isinstance(profile_domains, list) else []

    except Exception as e:
        logger.error(
            "get_active_domains_failed",
            error=str(e),
            fallback="all_domains",
        )
        # Fallback to all domains
        return [d.get("domain_id") for d in catalog.get("domains", []) if d.get("domain_id")]


async def set_deployment_profile(profile_name: str) -> bool:
    """Set the active deployment profile.

    Sprint 125 Feature 125.8: Deployment Profile Support

    Args:
        profile_name: Profile name (e.g., "pharma_company", "law_firm", "university")

    Returns:
        True if profile was set successfully, False otherwise

    Raises:
        ValueError: If profile_name is not in seed_domains.yaml
        ConnectionError: If Redis connection fails

    Example:
        >>> await set_deployment_profile("pharma_company")
        True
        >>> domains = await get_active_domains()
        >>> domains
        ['medicine_health', 'chemistry', 'biology_life_sciences']
    """
    # Load catalog
    catalog = _load_seed_domains()
    profiles = catalog.get("deployment_profiles", {})

    # Validate profile exists
    if profile_name not in profiles:
        logger.error(
            "invalid_deployment_profile",
            profile=profile_name,
            valid_profiles=list(profiles.keys()),
        )
        raise ValueError(
            f"Invalid deployment profile: {profile_name}. Valid: {list(profiles.keys())}"
        )

    # Store profile in Redis
    try:
        redis_client = await _get_redis_client()
        await redis_client.set(DEPLOYMENT_PROFILE_KEY, profile_name)
        await redis_client.close()

        logger.info(
            "deployment_profile_set",
            profile=profile_name,
            domains=profiles[profile_name].get("domains"),
        )

        return True

    except Exception as e:
        logger.error(
            "set_deployment_profile_failed",
            profile=profile_name,
            error=str(e),
        )
        raise ConnectionError(f"Failed to set deployment profile: {e}") from e


async def get_domain_config(domain_id: str) -> dict[str, Any] | None:
    """Get domain configuration from seed_domains.yaml catalog.

    Sprint 125 Feature 125.8: Domain Configuration Access

    Args:
        domain_id: Domain identifier (e.g., "medicine_health")

    Returns:
        Domain configuration dict or None if not found

    Example:
        >>> config = await get_domain_config("medicine_health")
        >>> config["ddc_code"]
        '610-619'
        >>> config["entity_sub_types"]
        ['DISEASE', 'SYMPTOM', 'MEDICATION', ...]
    """
    catalog = _load_seed_domains()

    for domain in catalog.get("domains", []):
        if domain.get("domain_id") == domain_id:
            return domain

    logger.warning("domain_config_not_found", domain_id=domain_id)
    return None
