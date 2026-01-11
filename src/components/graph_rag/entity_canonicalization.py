"""Entity Canonicalization for Knowledge Graph Consistency.

Sprint 85 Feature 85.4: Entity Canonicalization (Best Practice)

This module implements entity canonicalization following LightRAG best practices:
- Normalize entity names to canonical form (lowercase, underscores)
- Merge duplicate entities using embedding similarity
- Track surface forms for display while using canonical IDs internally

Best Practice Reference:
"In LightRAG, all occurrences of the same entities are combined and grouped
across chunks. Relationships are consolidated across chunks to give a
consistent, canonical key."
— Neo4j Blog: Under the Covers With LightRAG

Implementation:
1. Exact normalization (lowercase, whitespace → underscore, remove special chars)
2. Embedding similarity matching (BGE-M3, threshold >= 0.85)
3. Word distance fallback (Levenshtein for short names)
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.core.models import GraphEntity

logger = structlog.get_logger(__name__)


@dataclass
class CanonicalEntity:
    """Canonical entity form for stable graph construction.

    Attributes:
        canonical_id: Normalized identifier (e.g., "nvidia_rtx_3060")
        surface_forms: Original text forms ({"RTX 3060", "RTX3060", "GeForce RTX 3060"})
        entity_type: Entity type (e.g., "HARDWARE")
        merged_descriptions: Descriptions from all chunks where entity appears
        source_chunks: Chunk IDs where entity was found
        confidence: Average confidence across all occurrences
    """

    canonical_id: str
    surface_forms: set[str] = field(default_factory=set)
    entity_type: str = "ENTITY"
    merged_descriptions: list[str] = field(default_factory=list)
    source_chunks: list[str] = field(default_factory=list)
    confidence: float = 1.0

    @property
    def primary_name(self) -> str:
        """Most common/longest surface form as display name."""
        if not self.surface_forms:
            return self.canonical_id
        # Return longest surface form (usually most descriptive)
        # Sort by length descending, then alphabetically for consistent results
        return sorted(self.surface_forms, key=lambda x: (-len(x), x))[0]

    def to_graph_entity(self, original_id: str | None = None) -> GraphEntity:
        """Convert to GraphEntity for Neo4j storage."""
        return GraphEntity(
            id=original_id or self.canonical_id,
            name=self.primary_name,
            type=self.entity_type,
            description=self.merged_descriptions[0] if self.merged_descriptions else "",
            properties={
                "canonical_id": self.canonical_id,
                "surface_forms": list(self.surface_forms),
                "source_chunks": self.source_chunks,
            },
            source_document=None,
            confidence=self.confidence,
        )


class EntityCanonicalizer:
    """Canonicalize entities for stable graph construction.

    Uses a multi-strategy approach:
    1. Exact normalized match (fast, no API calls)
    2. Embedding similarity (BGE-M3, for semantic matching)
    3. Word distance (Levenshtein, for typos and variations)

    Attributes:
        similarity_threshold: Minimum cosine similarity for embedding match
        word_distance_threshold: Maximum Levenshtein distance for short names
        use_embeddings: Whether to use embedding similarity (requires BGE-M3)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        word_distance_threshold: int = 2,
        use_embeddings: bool = True,
    ) -> None:
        """Initialize entity canonicalizer.

        Args:
            similarity_threshold: Minimum cosine similarity for embedding match
            word_distance_threshold: Maximum Levenshtein distance for word match
            use_embeddings: Whether to use BGE-M3 embedding similarity
        """
        self.similarity_threshold = similarity_threshold
        self.word_distance_threshold = word_distance_threshold
        self.use_embeddings = use_embeddings

        # Lazy-loaded embedding service
        self._embedding_service = None

        # Cache for entity embeddings
        self._embedding_cache: dict[str, list[float]] = {}

        logger.info(
            "entity_canonicalizer_initialized",
            similarity_threshold=similarity_threshold,
            word_distance_threshold=word_distance_threshold,
            use_embeddings=use_embeddings,
        )

    def _get_embedding_service(self) -> Any:
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from src.components.embedding import get_embedding_service

            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def normalize(self, entity_name: str) -> str:
        """Normalize entity name to canonical form.

        Normalization rules:
        1. Convert to lowercase
        2. Replace whitespace with underscores
        3. Remove special characters (keep alphanumeric and underscore)
        4. Collapse multiple underscores

        Args:
            entity_name: Original entity name

        Returns:
            Normalized canonical ID

        Example:
            >>> canonicalizer.normalize("NVIDIA RTX 3060")
            'nvidia_rtx_3060'
            >>> canonicalizer.normalize("Machine Learning (ML)")
            'machine_learning_ml'
        """
        # Lowercase
        normalized = entity_name.lower().strip()

        # Replace whitespace with underscores
        normalized = re.sub(r"\s+", "_", normalized)

        # Remove special characters (keep alphanumeric and underscore)
        normalized = re.sub(r"[^\w]", "", normalized)

        # Collapse multiple underscores
        normalized = re.sub(r"_+", "_", normalized)

        # Strip leading/trailing underscores
        normalized = normalized.strip("_")

        return normalized

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein (edit) distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Number of single-character edits needed to transform s1 to s2
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost is 0 if characters match, 1 otherwise
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity in range [-1, 1]
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text, with caching.

        Args:
            text: Text to embed

        Returns:
            BGE-M3 embedding (1024-dim)
        """
        # Check cache
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        # Get embedding from service
        embedding_service = self._get_embedding_service()
        embedding = await embedding_service.embed_text(text)

        # Cache and return
        self._embedding_cache[text] = embedding
        return embedding

    async def find_canonical_match(
        self,
        entity: GraphEntity,
        existing_entities: list[CanonicalEntity],
    ) -> CanonicalEntity | None:
        """Find matching canonical entity for a new entity.

        Uses multi-strategy matching:
        1. Exact normalized match (fast)
        2. Embedding similarity (accurate, if enabled)
        3. Word distance (fallback for short names)

        Args:
            entity: New entity to match
            existing_entities: List of existing canonical entities

        Returns:
            Matching CanonicalEntity or None if no match found
        """
        if not existing_entities:
            return None

        normalized = self.normalize(entity.name)

        # Strategy 1: Exact normalized match
        for canonical in existing_entities:
            if normalized == canonical.canonical_id:
                logger.debug(
                    "canonical_match_exact",
                    entity=entity.name,
                    canonical=canonical.canonical_id,
                )
                return canonical

        # Strategy 2: Word distance for short names (< 20 chars)
        if len(entity.name) < 20:
            for canonical in existing_entities:
                for surface_form in canonical.surface_forms:
                    distance = self._levenshtein_distance(
                        entity.name.lower(), surface_form.lower()
                    )
                    if distance <= self.word_distance_threshold:
                        logger.debug(
                            "canonical_match_levenshtein",
                            entity=entity.name,
                            canonical=canonical.canonical_id,
                            distance=distance,
                        )
                        return canonical

        # Strategy 3: Embedding similarity (if enabled)
        if self.use_embeddings:
            try:
                entity_embedding = await self._get_embedding(entity.name)

                best_match: CanonicalEntity | None = None
                best_similarity = 0.0

                for canonical in existing_entities:
                    # Check similarity with primary name
                    canonical_embedding = await self._get_embedding(canonical.primary_name)
                    similarity = self._cosine_similarity(entity_embedding, canonical_embedding)

                    if similarity >= self.similarity_threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = canonical

                if best_match:
                    logger.debug(
                        "canonical_match_embedding",
                        entity=entity.name,
                        canonical=best_match.canonical_id,
                        similarity=round(best_similarity, 3),
                    )
                    return best_match

            except Exception as e:
                logger.warning(
                    "canonical_embedding_match_failed",
                    entity=entity.name,
                    error=str(e),
                )

        return None

    def merge_entity(
        self,
        entity: GraphEntity,
        canonical: CanonicalEntity,
        chunk_id: str | None = None,
    ) -> CanonicalEntity:
        """Merge entity into existing canonical entity.

        Updates:
        - Add surface form
        - Append description (if different)
        - Add chunk ID to source_chunks
        - Update confidence (average)

        Args:
            entity: Entity to merge
            canonical: Existing canonical entity
            chunk_id: Source chunk ID

        Returns:
            Updated canonical entity
        """
        # Add surface form
        canonical.surface_forms.add(entity.name)

        # Add description if unique
        if entity.description and entity.description not in canonical.merged_descriptions:
            canonical.merged_descriptions.append(entity.description)

        # Add chunk ID
        if chunk_id and chunk_id not in canonical.source_chunks:
            canonical.source_chunks.append(chunk_id)

        # Update confidence (running average)
        # Count all surface forms as the number of contributions
        contribution_count = len(canonical.surface_forms)
        if contribution_count > 1:
            # Running average: (old_avg * (n-1) + new) / n
            canonical.confidence = (
                (canonical.confidence * (contribution_count - 1)) + entity.confidence
            ) / contribution_count
        else:
            # First contribution, just use the new confidence
            canonical.confidence = entity.confidence

        logger.debug(
            "entity_merged",
            entity=entity.name,
            canonical=canonical.canonical_id,
            surface_forms_count=len(canonical.surface_forms),
        )

        return canonical

    def create_canonical(
        self,
        entity: GraphEntity,
        chunk_id: str | None = None,
    ) -> CanonicalEntity:
        """Create new canonical entity from GraphEntity.

        Args:
            entity: Source entity
            chunk_id: Source chunk ID

        Returns:
            New CanonicalEntity
        """
        canonical_id = self.normalize(entity.name)

        canonical = CanonicalEntity(
            canonical_id=canonical_id,
            surface_forms={entity.name},
            entity_type=entity.type,
            merged_descriptions=[entity.description] if entity.description else [],
            source_chunks=[chunk_id] if chunk_id else [],
            confidence=entity.confidence,
        )

        logger.debug(
            "canonical_created",
            entity=entity.name,
            canonical=canonical_id,
        )

        return canonical

    async def canonicalize_entities(
        self,
        entities: list[GraphEntity],
        chunk_id: str | None = None,
        existing_canonicals: list[CanonicalEntity] | None = None,
    ) -> tuple[list[CanonicalEntity], int]:
        """Canonicalize a list of entities, merging duplicates.

        Main entry point for entity canonicalization.

        Args:
            entities: List of entities to canonicalize
            chunk_id: Source chunk ID
            existing_canonicals: Optional list of existing canonical entities to merge with

        Returns:
            Tuple of (canonical entities list, number of duplicates merged)

        Example:
            >>> canonicalizer = EntityCanonicalizer()
            >>> canonicals, dupes = await canonicalizer.canonicalize_entities(entities)
            >>> print(f"Deduplicated {dupes} entities")
        """
        canonicals = list(existing_canonicals) if existing_canonicals else []
        duplicates_merged = 0

        for entity in entities:
            # Find existing match
            match = await self.find_canonical_match(entity, canonicals)

            if match:
                # Merge with existing
                self.merge_entity(entity, match, chunk_id)
                duplicates_merged += 1
            else:
                # Create new canonical
                new_canonical = self.create_canonical(entity, chunk_id)
                canonicals.append(new_canonical)

        logger.info(
            "canonicalization_complete",
            input_entities=len(entities),
            output_canonicals=len(canonicals),
            duplicates_merged=duplicates_merged,
            chunk_id=chunk_id,
        )

        return canonicals, duplicates_merged


# Global instance (singleton pattern)
_entity_canonicalizer: EntityCanonicalizer | None = None


def get_entity_canonicalizer(
    similarity_threshold: float = 0.85,
    use_embeddings: bool = True,
) -> EntityCanonicalizer:
    """Get global entity canonicalizer instance (singleton).

    Args:
        similarity_threshold: Minimum cosine similarity for embedding match
        use_embeddings: Whether to use embedding similarity

    Returns:
        EntityCanonicalizer instance
    """
    global _entity_canonicalizer
    if _entity_canonicalizer is None:
        _entity_canonicalizer = EntityCanonicalizer(
            similarity_threshold=similarity_threshold,
            use_embeddings=use_embeddings,
        )
    return _entity_canonicalizer
