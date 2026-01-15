"""Entity Consolidation Service.

Sprint 92 Feature 92.14: Entity Consolidation Pipeline

Problem (discovered during Sprint 92 analysis):
- SpaCy extracts good entities but LLM enrichment adds noise
- LLM returns full sentences as "ENTITY" type entities (91-145 chars)
- No deduplication between SpaCy and LLM entities
- Quality filter applied too late (after relation extraction)

Solution:
- Consolidation step BEFORE relation extraction
- Apply quality filter to ALL entities (SpaCy + LLM)
- Embedding-based deduplication for similar entities
- Strict type validation (reject generic "ENTITY" type from LLM)

Pipeline Position:
    Stage 1: SpaCy NER
    Stage 2: LLM Entity Enrichment
    >>> NEW: Entity Consolidation <<<
    Stage 3: LLM Relation Extraction

Usage:
    from src.components.graph_rag.entity_consolidator import EntityConsolidator

    consolidator = EntityConsolidator()
    consolidated = await consolidator.consolidate(
        spacy_entities=spacy_entities,
        llm_entities=llm_entities,
    )
"""

import asyncio
from dataclasses import dataclass, field

import structlog

from src.core.models import GraphEntity

logger = structlog.get_logger(__name__)


# Valid entity types from SpaCy and LLM enrichment
VALID_ENTITY_TYPES = {
    # SpaCy types (mapped)
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "TEMPORAL",
    "QUANTITY",
    "EVENT",
    "DOCUMENT",
    # LLM enrichment types (domain-specific)
    "CONCEPT",
    "TECHNOLOGY",
    "PRODUCT",
    "MODEL",
    "ARCHITECTURE",
    "PROGRAMMING_LANGUAGE",
    # Additional valid types
    "WORK_OF_ART",
    "LAW",
    "LANGUAGE",
    "MONEY",
    "PERCENT",
    "DATE",
    "TIME",
    "GPE",  # Geo-Political Entity
    "FAC",  # Facility
    "NORP",  # Nationalities, religious, political groups
    "ORG",
}

# Types to reject (noise or too generic)
INVALID_ENTITY_TYPES = {
    "ENTITY",  # Generic fallback - usually indicates LLM extraction failure
    "MISC",  # Too generic
    "UNKNOWN",
}


@dataclass
class ConsolidationStats:
    """Statistics from entity consolidation."""

    spacy_input: int = 0
    llm_input: int = 0
    total_input: int = 0

    # Filtering stats
    filtered_by_type: int = 0
    filtered_by_length: int = 0
    filtered_by_duplicate: int = 0

    # Output
    total_output: int = 0

    @property
    def filter_rate(self) -> float:
        """Percentage of entities filtered."""
        if self.total_input == 0:
            return 0.0
        return (self.total_input - self.total_output) / self.total_input * 100


@dataclass
class ConsolidationConfig:
    """Configuration for entity consolidation."""

    # Length constraints
    min_length: int = 2
    max_length: int = 80  # Sprint 92: Filter sentence-like entities

    # Type validation
    reject_generic_types: bool = True  # Reject "ENTITY", "MISC" types
    valid_types: set[str] = field(default_factory=lambda: VALID_ENTITY_TYPES)

    # Deduplication
    enable_deduplication: bool = True
    similarity_threshold: float = 0.85  # Embedding similarity for dedup
    use_exact_match: bool = True  # Also check exact name match (case-insensitive)

    # Source preference (when deduplicating)
    prefer_spacy: bool = True  # SpaCy entities are more reliable


class EntityConsolidator:
    """Consolidates entities from SpaCy and LLM sources.

    This class implements the missing consolidation step in the extraction pipeline:
    1. Validates entity types (rejects generic "ENTITY" type)
    2. Filters by length (min/max)
    3. Deduplicates using exact match and embedding similarity
    4. Prefers SpaCy entities when duplicates found

    Attributes:
        config: ConsolidationConfig with filtering rules
        embedding_service: Optional embedding service for semantic dedup
    """

    def __init__(
        self,
        config: ConsolidationConfig | None = None,
        embedding_service: any = None,
    ):
        """Initialize the entity consolidator.

        Args:
            config: Consolidation configuration (uses defaults if None)
            embedding_service: Embedding service for semantic deduplication
        """
        self.config = config or ConsolidationConfig()
        self.embedding_service = embedding_service

        logger.info(
            "entity_consolidator_initialized",
            min_length=self.config.min_length,
            max_length=self.config.max_length,
            reject_generic_types=self.config.reject_generic_types,
            enable_deduplication=self.config.enable_deduplication,
            similarity_threshold=self.config.similarity_threshold,
        )

    async def consolidate(
        self,
        spacy_entities: list[GraphEntity],
        llm_entities: list[GraphEntity],
    ) -> tuple[list[GraphEntity], ConsolidationStats]:
        """Consolidate entities from SpaCy and LLM sources.

        Args:
            spacy_entities: Entities from SpaCy NER (Stage 1)
            llm_entities: Entities from LLM enrichment (Stage 2)

        Returns:
            Tuple of (consolidated_entities, stats)
        """
        stats = ConsolidationStats(
            spacy_input=len(spacy_entities),
            llm_input=len(llm_entities),
            total_input=len(spacy_entities) + len(llm_entities),
        )

        # Step 1: Filter SpaCy entities
        # Sprint 92.14 Fix: Also check types for SpaCy - MISC/unknown labels become "ENTITY"
        filtered_spacy = self._filter_entities(
            spacy_entities,
            source="spacy",
            stats=stats,
            check_types=self.config.reject_generic_types,  # Sprint 92: Filter "ENTITY" from SpaCy too
        )

        # Step 2: Filter LLM entities (stricter - check types too)
        filtered_llm = self._filter_entities(
            llm_entities,
            source="llm",
            stats=stats,
            check_types=self.config.reject_generic_types,
        )

        # Step 3: Deduplicate (prefer SpaCy entities)
        if self.config.enable_deduplication:
            consolidated = await self._deduplicate(
                filtered_spacy,
                filtered_llm,
                stats=stats,
            )
        else:
            consolidated = filtered_spacy + filtered_llm

        stats.total_output = len(consolidated)

        logger.info(
            "entity_consolidation_complete",
            spacy_input=stats.spacy_input,
            llm_input=stats.llm_input,
            filtered_by_type=stats.filtered_by_type,
            filtered_by_length=stats.filtered_by_length,
            filtered_by_duplicate=stats.filtered_by_duplicate,
            total_output=stats.total_output,
            filter_rate=f"{stats.filter_rate:.1f}%",
        )

        return consolidated, stats

    def _filter_entities(
        self,
        entities: list[GraphEntity],
        source: str,
        stats: ConsolidationStats,
        check_types: bool = False,
    ) -> list[GraphEntity]:
        """Filter entities by type and length.

        Args:
            entities: List of entities to filter
            source: Source name for logging ("spacy" or "llm")
            stats: Stats object to update
            check_types: Whether to validate entity types

        Returns:
            Filtered list of entities
        """
        filtered = []

        for entity in entities:
            name = entity.name.strip() if entity.name else ""
            etype = entity.type.upper() if entity.type else ""

            # Check type validity (only for LLM entities)
            if check_types and etype in INVALID_ENTITY_TYPES:
                logger.debug(
                    "entity_filtered_invalid_type",
                    name=name[:50],
                    type=etype,
                    source=source,
                )
                stats.filtered_by_type += 1
                continue

            # Check length constraints
            if len(name) < self.config.min_length:
                stats.filtered_by_length += 1
                continue

            if len(name) > self.config.max_length:
                logger.debug(
                    "entity_filtered_too_long",
                    name=name[:50] + "..." if len(name) > 50 else name,
                    length=len(name),
                    source=source,
                )
                stats.filtered_by_length += 1
                continue

            filtered.append(entity)

        return filtered

    async def _deduplicate(
        self,
        spacy_entities: list[GraphEntity],
        llm_entities: list[GraphEntity],
        stats: ConsolidationStats,
    ) -> list[GraphEntity]:
        """Deduplicate entities, preferring SpaCy over LLM.

        Args:
            spacy_entities: Filtered SpaCy entities (preferred)
            llm_entities: Filtered LLM entities
            stats: Stats object to update

        Returns:
            Deduplicated list of entities
        """
        # Start with all SpaCy entities (they're preferred)
        result = list(spacy_entities)

        # Build set of existing names (case-insensitive)
        existing_names = {e.name.lower().strip() for e in spacy_entities}

        # Add LLM entities that don't duplicate SpaCy
        for llm_entity in llm_entities:
            name_lower = llm_entity.name.lower().strip()

            # Exact match check
            if self.config.use_exact_match and name_lower in existing_names:
                logger.debug(
                    "entity_filtered_exact_duplicate",
                    name=llm_entity.name,
                    source="llm",
                )
                stats.filtered_by_duplicate += 1
                continue

            # Semantic similarity check (if embedding service available)
            if self.embedding_service and self.config.similarity_threshold < 1.0:
                is_duplicate = await self._is_semantic_duplicate(
                    llm_entity.name,
                    existing_names,
                )
                if is_duplicate:
                    logger.debug(
                        "entity_filtered_semantic_duplicate",
                        name=llm_entity.name,
                        source="llm",
                    )
                    stats.filtered_by_duplicate += 1
                    continue

            # Not a duplicate - add it
            result.append(llm_entity)
            existing_names.add(name_lower)

        return result

    async def _is_semantic_duplicate(
        self,
        name: str,
        existing_names: set[str],
    ) -> bool:
        """Check if entity name is semantically similar to existing names.

        Args:
            name: Name to check
            existing_names: Set of existing entity names

        Returns:
            True if name is semantically similar to any existing name
        """
        if not self.embedding_service or not existing_names:
            return False

        try:
            # Get embedding for the new name
            name_embedding = await self.embedding_service.embed_query(name)

            # Compare with each existing name
            for existing in existing_names:
                existing_embedding = await self.embedding_service.embed_query(existing)

                # Cosine similarity
                similarity = self._cosine_similarity(name_embedding, existing_embedding)

                if similarity >= self.config.similarity_threshold:
                    logger.debug(
                        "semantic_duplicate_found",
                        name=name,
                        existing=existing,
                        similarity=round(similarity, 3),
                    )
                    return True

            return False

        except Exception as e:
            logger.warning(
                "semantic_duplicate_check_failed",
                name=name,
                error=str(e),
            )
            return False

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# Singleton instance
_consolidator_instance: EntityConsolidator | None = None


def get_entity_consolidator() -> EntityConsolidator:
    """Get singleton EntityConsolidator instance.

    Returns:
        EntityConsolidator singleton
    """
    global _consolidator_instance
    if _consolidator_instance is None:
        _consolidator_instance = EntityConsolidator()
    return _consolidator_instance
