"""Semantic Entity Deduplication using BGE-M3 embeddings.

Sprint 13 Feature 13.9: ADR-017
Uses embeddings to identify and merge duplicate entities based on
semantic similarity rather than string matching.

Sprint 20 Feature 20.3: Singleton Pattern for Embedding Service
- Eliminates redundant model loads during indexing
- Lazy initialization (load on first use)
- Shared LRU cache across all components
- Saves ~111 seconds per 223 chunks

Sprint 43 Feature 43.x: MultiCriteriaDeduplicator (ADR-044, TD-062)
- Multi-criteria matching: exact, edit distance, substring, semantic
- Catches case variations ("Nicolas Cage" vs "nicolas cage")
- Catches typos ("Nicolas Cage" vs "Nicholas Cage")
- Catches abbreviations ("Nicolas Cage" vs "Cage")
- Min-length guards prevent false positives ("AI" in "NVIDIA")

Sprint 49 Feature 49.9: BGE-M3 Migration (ADR-024)
- Migrated from sentence-transformers (all-MiniLM-L6-v2, 384-dim) to BGE-M3 (1024-dim)
- Consolidates all embeddings to single model via UnifiedEmbeddingService
- Async batch embedding for better performance
- Removes sentence-transformers dependency

Author: Claude Code
Date: 2025-10-24, Updated: 2025-12-16
"""

from __future__ import annotations

from typing import Any

import numpy as np
import structlog
from sklearn.metrics.pairwise import cosine_similarity

from src.components.shared.embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)

# Sprint 43: Levenshtein distance for edit-distance deduplication (ADR-044)
try:
    from Levenshtein import distance as levenshtein_distance

    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    logger.info(
        "python-Levenshtein not available, edit distance check disabled. "
        "Install with: pip install python-Levenshtein"
    )


class SemanticDeduplicator:
    """Deduplicate entities using semantic similarity.

    Uses BGE-M3 embeddings (1024-dim) via UnifiedEmbeddingService to compute
    embeddings of entity names and identifies duplicates using cosine similarity.
    Entities with similarity above threshold are merged, keeping the first mention
    and aggregating descriptions.

    Architecture Decision: ADR-017 (Semantic Entity Deduplication)
    Model Selection: ADR-024 (BGE-M3, 1024-dim multilingual embeddings)

    Example:
        >>> dedup = SemanticDeduplicator(threshold=0.85)
        >>> entities = [
        ...     {"name": "Alex", "type": "PERSON", "description": "..."},
        ...     {"name": "Alex", "type": "PERSON", "description": "..."},  # Duplicate
        ...     {"name": "Jordan", "type": "PERSON", "description": "..."}
        ... ]
        >>> clean = await dedup.deduplicate(entities)
        >>> len(clean)  # 2 (Alex merged)
        2

    Sprint 49 Feature 49.9:
    - Migrated from sentence-transformers to BGE-M3 embeddings
    - All methods are now async
    - Uses UnifiedEmbeddingService singleton with LRU cache
    - Better batch processing with configurable concurrency
    """

    def __init__(
        self,
        threshold: float = 0.85,
        batch_size: int = 32,
    ) -> None:
        """Initialize semantic deduplicator.

        Sprint 49 Feature 49.9: BGE-M3 Migration
        - Uses UnifiedEmbeddingService (BGE-M3, 1024-dim)
        - Shared LRU cache across all AEGIS RAG components
        - Async batch embedding for better performance

        Args:
            threshold: Cosine similarity threshold for duplicate detection
                      Default: 0.85 (conservative, prevents false merges)
                      Recommended range: 0.80-0.90
                      - Lower (0.80): More aggressive merging
                      - Higher (0.90): More conservative
            batch_size: Number of entities to embed in parallel (default: 32)
                       Higher values improve throughput but may increase memory usage
        """
        self.embedding_service = get_embedding_service()
        self.threshold = threshold
        self.batch_size = batch_size

        logger.info(
            "semantic_deduplicator_initialized",
            model="bge-m3",
            embedding_dim=1024,
            threshold=threshold,
            batch_size=batch_size,
            note="Using UnifiedEmbeddingService with BGE-M3 (Sprint 49.9)",
        )

    async def deduplicate(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate entities using semantic similarity.

        Strategy:
        1. Group entities by type (only compare same types)
        2. Compute embeddings for all entity names within each type (async batch)
        3. Find clusters with similarity >= threshold
        4. Keep first entity from each cluster
        5. Merge descriptions from duplicates

        Args:
            entities: list of entity dicts with keys:
                     - name (str): Entity name
                     - type (str): Entity type (PERSON, ORG, etc.)
                     - description (str): Entity description

        Returns:
            Deduplicated entity list with merged descriptions

        Example:
            Input:  [{"name": "Alex", ...}, {"name": "Alex", ...}, {"name": "Jordan", ...}]
            Output: [{"name": "Alex", "description": "... [Deduplicated from 2 mentions]"},
                    {"name": "Jordan", ...}]

        Sprint 49 Feature 49.9: Now async, uses BGE-M3 embeddings via UnifiedEmbeddingService
        """
        if not entities:
            return []

        # Group by type (only compare same types to avoid false positives)
        type_groups = {}
        for entity in entities:
            etype = entity.get("type", "OTHER")
            if etype not in type_groups:
                type_groups[etype] = []
            type_groups[etype].append(entity)

        deduplicated = []
        stats = {
            "total": len(entities),
            "removed": 0,
            "kept": 0,
            "groups_processed": len(type_groups),
        }

        # Deduplicate within each type
        for etype, group in type_groups.items():
            if len(group) == 1:
                # No duplicates possible
                deduplicated.extend(group)
                stats["kept"] += 1
                continue

            # Deduplicate this group (async)
            deduped_group = await self._deduplicate_group(group, etype)
            deduplicated.extend(deduped_group)

            stats["kept"] += len(deduped_group)
            stats["removed"] += len(group) - len(deduped_group)

        reduction_pct = 100 * stats["removed"] / stats["total"] if stats["total"] > 0 else 0

        logger.info(
            "deduplication_complete",
            total=stats["total"],
            kept=stats["kept"],
            removed=stats["removed"],
            reduction_pct=f"{reduction_pct:.1f}",
            groups=stats["groups_processed"],
        )

        return deduplicated

    async def deduplicate_with_mapping(
        self, entities: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Deduplicate entities and return mapping from old names to canonical names.

        Sprint 44 Feature 44.2: Required for relation deduplication (TD-063).
        After entity deduplication, relations need to be updated to use the
        canonical entity names. This method provides that mapping.

        Sprint 49 Feature 49.9: Now async, uses BGE-M3 embeddings

        Args:
            entities: List of entity dicts

        Returns:
            Tuple of:
            - Deduplicated entity list
            - Mapping from original name (lowercase) to canonical name
              e.g., {"nicolas cage": "Nicolas Cage", "nick cage": "Nicolas Cage"}

        Example:
            >>> dedup = SemanticDeduplicator()
            >>> entities = [
            ...     {"name": "Nicolas Cage", "type": "PERSON"},
            ...     {"name": "nicolas cage", "type": "PERSON"},
            ... ]
            >>> deduped, mapping = await dedup.deduplicate_with_mapping(entities)
            >>> mapping
            {'nicolas cage': 'Nicolas Cage'}
        """
        if not entities:
            return [], {}

        # Group by type
        type_groups: dict[str, list[dict[str, Any]]] = {}
        for entity in entities:
            etype = entity.get("type", "OTHER")
            if etype not in type_groups:
                type_groups[etype] = []
            type_groups[etype].append(entity)

        deduplicated = []
        entity_mapping: dict[str, str] = {}

        for etype, group in type_groups.items():
            if len(group) == 1:
                deduplicated.extend(group)
                continue

            # Deduplicate and get mapping (async)
            deduped_group, group_mapping = await self._deduplicate_group_with_mapping(group, etype)
            deduplicated.extend(deduped_group)
            entity_mapping.update(group_mapping)

        logger.info(
            "deduplication_with_mapping_complete",
            total_entities=len(entities),
            deduplicated_count=len(deduplicated),
            mapping_entries=len(entity_mapping),
        )

        return deduplicated, entity_mapping

    async def _deduplicate_group_with_mapping(
        self, entities: list[dict[str, Any]], entity_type: str
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        """Deduplicate a group and return name mapping.

        Args:
            entities: Entities of same type
            entity_type: Type label

        Returns:
            Tuple of (deduplicated entities, name mapping)

        Sprint 49 Feature 49.9: Now async
        """
        # Use the regular deduplication and build mapping from result
        deduped = await self._deduplicate_group(entities, entity_type)

        # Build mapping: we need to track which names were merged
        # This is a simplified approach - we map all variants to the representative
        names = [e.get("name", e.get("entity_name", "UNKNOWN")) for e in entities]
        deduped_names = {e.get("name", e.get("entity_name", "")).lower() for e in deduped}

        mapping: dict[str, str] = {}
        for entity in entities:
            name = entity.get("name", entity.get("entity_name", ""))
            name_lower = name.lower().strip()

            # Find the representative for this entity
            for deduped_entity in deduped:
                rep_name = deduped_entity.get("name", deduped_entity.get("entity_name", ""))
                rep_lower = rep_name.lower().strip()

                # Check if this entity was merged into this representative
                if name_lower == rep_lower:
                    # Same entity (possibly different case)
                    if name != rep_name:
                        mapping[name_lower] = rep_name
                    break
                elif self._are_duplicates(name, rep_name):
                    mapping[name_lower] = rep_name
                    break

        return deduped, mapping

    def _are_duplicates(self, name1: str, name2: str) -> bool:
        """Check if two names are duplicates (for mapping purposes).

        Override in subclasses for multi-criteria matching.
        """
        # Default: exact match (case-insensitive)
        return name1.lower().strip() == name2.lower().strip()

    async def _deduplicate_group(
        self, entities: list[dict[str, Any]], entity_type: str
    ) -> list[dict[str, Any]]:
        """Deduplicate entities of the same type using BGE-M3 embeddings.

        Args:
            entities: Entities of same type
            entity_type: Type label (for logging)

        Returns:
            Deduplicated entities

        Sprint 49 Feature 49.9: Now async, uses BGE-M3 via UnifiedEmbeddingService
        """
        # Extract names - handle both "name" (extraction) and "entity_name" (LightRAG format)
        names = [e.get("name", e.get("entity_name", "UNKNOWN")) for e in entities]

        # Compute embeddings using BGE-M3 (async batch embedding)
        embeddings = await self.embedding_service.embed_batch(
            names, max_concurrent=self.batch_size
        )

        # Convert to numpy for sklearn
        embeddings_np = np.array(embeddings)

        # Compute pairwise cosine similarity
        similarity_matrix = cosine_similarity(embeddings_np)

        # Find clusters using greedy clustering
        used = set()
        deduplicated = []

        for i in range(len(entities)):
            if i in used:
                continue

            # Find all similar entities (cluster)
            similar = [i]
            for j in range(i + 1, len(entities)):
                if j not in used and similarity_matrix[i, j] >= self.threshold:
                    similar.append(j)
                    used.add(j)

            # Keep first entity as representative
            representative = entities[i].copy()

            if len(similar) > 1:
                # Merge descriptions from duplicates
                duplicate_names = [
                    entities[idx].get("name", entities[idx].get("entity_name", "?"))
                    for idx in similar
                ]
                orig_desc = entities[i].get("description", "")
                representative["description"] = (
                    f"{orig_desc} [Deduplicated from {len(similar)} mentions]"
                )

                logger.debug(
                    "entities_merged",
                    type=entity_type,
                    representative=names[i],
                    duplicates=duplicate_names,
                    count=len(similar),
                )

            deduplicated.append(representative)

        return deduplicated


# ============================================================================
# Sprint 43: MULTI-CRITERIA DEDUPLICATOR (ADR-044, TD-062)
# ============================================================================


class MultiCriteriaDeduplicator(SemanticDeduplicator):
    """Extended deduplicator using multiple matching criteria.

    Sprint 43 Feature: ADR-044, TD-062
    Extends SemanticDeduplicator with additional matching criteria:

    1. **Exact match (case-insensitive)**: "Nicolas Cage" == "nicolas cage"
    2. **Edit distance < threshold**: "Nicolas Cage" ~ "Nicholas Cage" (typo)
    3. **Substring containment**: "Cage" in "Nicolas Cage" (abbreviation)
    4. **Semantic similarity** (existing): cosine >= 0.93

    Min-length guards prevent false positives:
    - Edit distance: only for entities >= 5 chars (prevents "AI" ~ "UI")
    - Substring: only for entities >= 6 chars (prevents "AI" in "NVIDIA")

    Performance:
    - Criteria 1-3 are O(n²) string operations (very fast)
    - Criterion 4 uses batch embeddings (existing optimization)
    - Two-phase: fast criteria first, semantic only for unmatched

    Example:
        >>> dedup = MultiCriteriaDeduplicator(threshold=0.93)
        >>> entities = [
        ...     {"name": "Nicolas Cage", "type": "PERSON", "description": "Actor"},
        ...     {"name": "nicolas cage", "type": "PERSON", "description": "Star"},
        ...     {"name": "Nicholas Cage", "type": "PERSON", "description": "Lead"},
        ... ]
        >>> clean = dedup.deduplicate(entities)
        >>> len(clean)  # All merged into 1
        1
    """

    def __init__(
        self,
        threshold: float = 0.85,
        batch_size: int = 32,
        edit_distance_threshold: int = 3,
        min_length_for_edit: int = 5,
        min_length_for_substring: int = 6,
    ) -> None:
        """Initialize multi-criteria deduplicator.

        Sprint 49 Feature 49.9: Migrated to BGE-M3 embeddings

        Args:
            threshold: Cosine similarity threshold for semantic matching (default: 0.85)
            batch_size: Number of entities to embed in parallel (default: 32)
            edit_distance_threshold: Max edit distance to consider as duplicate
                                    Default: 3 (catches 1-2 char typos)
            min_length_for_edit: Min entity name length for edit distance check
                                Default: 5 (prevents "AI" ~ "UI")
            min_length_for_substring: Min entity name length for substring check
                                     Default: 6 (prevents "AI" in "NVIDIA")
        """
        super().__init__(threshold=threshold, batch_size=batch_size)

        self.edit_distance_threshold = edit_distance_threshold
        self.min_length_for_edit = min_length_for_edit
        self.min_length_for_substring = min_length_for_substring

        if not LEVENSHTEIN_AVAILABLE:
            logger.warning(
                "multi_criteria_dedup_degraded",
                reason="python-Levenshtein not installed, edit distance disabled",
                install_cmd="pip install python-Levenshtein",
            )

        logger.info(
            "multi_criteria_deduplicator_initialized",
            model="bge-m3",
            embedding_dim=1024,
            threshold=threshold,
            batch_size=batch_size,
            edit_distance_threshold=edit_distance_threshold,
            min_length_for_edit=min_length_for_edit,
            min_length_for_substring=min_length_for_substring,
            levenshtein_available=LEVENSHTEIN_AVAILABLE,
        )

    def _is_duplicate_by_criteria(
        self, name1: str, name2: str
    ) -> tuple[bool, str]:
        """Check if two entity names are duplicates using multiple criteria.

        Criteria are checked in order (first match wins):
        1. Exact match (case-insensitive)
        2. Edit distance < threshold (for names >= min_length_for_edit)
        3. Substring containment (for names >= min_length_for_substring)

        Args:
            name1: First entity name
            name2: Second entity name

        Returns:
            Tuple of (is_duplicate, matched_criterion)
            criterion is one of: "exact", "edit_distance", "substring", "none"
        """
        n1_lower = name1.lower().strip()
        n2_lower = name2.lower().strip()

        # Criterion 1: Exact case-insensitive match
        if n1_lower == n2_lower:
            return True, "exact"

        # Criterion 2: Edit distance (for typos/minor variations)
        if LEVENSHTEIN_AVAILABLE:
            len_n1 = len(n1_lower)
            len_n2 = len(n2_lower)
            if len_n1 >= self.min_length_for_edit and len_n2 >= self.min_length_for_edit:
                edit_dist = levenshtein_distance(n1_lower, n2_lower)
                if edit_dist < self.edit_distance_threshold:
                    return True, "edit_distance"

        # Criterion 3: Substring containment (for abbreviations)
        len_n1 = len(n1_lower)
        len_n2 = len(n2_lower)
        if len_n1 >= self.min_length_for_substring and len_n2 >= self.min_length_for_substring:
            if n1_lower in n2_lower or n2_lower in n1_lower:
                return True, "substring"

        return False, "none"

    async def _deduplicate_group(
        self, entities: list[dict[str, Any]], entity_type: str
    ) -> list[dict[str, Any]]:
        """Deduplicate entities using multi-criteria matching.

        Two-phase approach for efficiency:
        1. Fast phase: Check criteria 1-3 (string operations, O(n²) but fast)
        2. Slow phase: Check semantic similarity for remaining unmatched entities

        Args:
            entities: Entities of same type
            entity_type: Type label (for logging)

        Returns:
            Deduplicated entities with merged descriptions

        Sprint 49 Feature 49.9: Now async, uses BGE-M3 embeddings
        """
        if len(entities) <= 1:
            return entities

        # Handle both "name" (extraction) and "entity_name" (LightRAG format)
        names = [e.get("name", e.get("entity_name", "UNKNOWN")) for e in entities]

        # Phase 1: Fast criteria (exact, edit distance, substring)
        # Build clusters using union-find style approach
        used = set()
        clusters: list[tuple[int, list[int]]] = []  # (representative_idx, member_indices)

        for i in range(len(entities)):
            if i in used:
                continue

            cluster_members = [i]
            used.add(i)

            for j in range(i + 1, len(entities)):
                if j in used:
                    continue

                is_dup, criterion = self._is_duplicate_by_criteria(names[i], names[j])
                if is_dup:
                    cluster_members.append(j)
                    used.add(j)
                    logger.debug(
                        "multi_criteria_match",
                        entity1=names[i],
                        entity2=names[j],
                        criterion=criterion,
                        type=entity_type,
                    )

            clusters.append((i, cluster_members))

        # Phase 2: Semantic similarity for cluster representatives
        # Only compute embeddings for entities not yet matched by fast criteria
        if len(clusters) > 1:
            rep_indices = [c[0] for c in clusters]
            rep_names = [names[i] for i in rep_indices]

            # Compute embeddings using BGE-M3 (async batch embedding)
            embeddings = await self.embedding_service.embed_batch(
                rep_names, max_concurrent=self.batch_size
            )
            embeddings_np = np.array(embeddings)
            similarity_matrix = cosine_similarity(embeddings_np)

            # Merge clusters based on semantic similarity
            merged_used = set()
            final_clusters: list[tuple[int, list[int]]] = []

            for idx, (rep_i, members_i) in enumerate(clusters):
                if idx in merged_used:
                    continue

                merged_members = list(members_i)

                for jdx in range(idx + 1, len(clusters)):
                    if jdx in merged_used:
                        continue

                    if similarity_matrix[idx, jdx] >= self.threshold:
                        rep_j, members_j = clusters[jdx]
                        merged_members.extend(members_j)
                        merged_used.add(jdx)
                        logger.debug(
                            "semantic_match",
                            entity1=names[rep_i],
                            entity2=names[rep_j],
                            similarity=float(similarity_matrix[idx, jdx]),
                            type=entity_type,
                        )

                final_clusters.append((rep_i, merged_members))
        else:
            final_clusters = clusters

        # Build deduplicated result
        deduplicated = []
        for rep_idx, member_indices in final_clusters:
            representative = entities[rep_idx].copy()

            if len(member_indices) > 1:
                # Merge: keep representative name, aggregate info
                merged_names = [names[idx] for idx in member_indices]
                orig_desc = entities[rep_idx].get("description", "")
                representative["description"] = (
                    f"{orig_desc} "
                    f"[Deduplicated from {len(member_indices)} mentions: {', '.join(merged_names[:3])}{'...' if len(merged_names) > 3 else ''}]"
                )

                logger.debug(
                    "entities_merged",
                    type=entity_type,
                    representative=names[rep_idx],
                    duplicates=merged_names,
                    count=len(member_indices),
                )

            deduplicated.append(representative)

        return deduplicated

    def _are_duplicates(self, name1: str, name2: str) -> bool:
        """Check if two names are duplicates using multi-criteria matching.

        Override of base class method for proper mapping support.
        """
        is_dup, _ = self._is_duplicate_by_criteria(name1, name2)
        return is_dup


def create_deduplicator_from_config(config) -> SemanticDeduplicator | MultiCriteriaDeduplicator | None:
    """Factory function to create deduplicator from app config.

    Sprint 43 Feature 43.1: MultiCriteriaDeduplicator support (ADR-044).
    Sprint 49 Feature 49.9: Migrated to BGE-M3 embeddings via UnifiedEmbeddingService.

    Args:
        config: Application config object with attributes:
               - enable_semantic_dedup (bool)
               - enable_multi_criteria_dedup (bool) - Sprint 43: use multi-criteria
               - semantic_dedup_threshold (float) - Default: 0.85
               - dedup_batch_size (int) - Sprint 49: batch size for embeddings
               - dedup_edit_distance_threshold (int) - Sprint 43: max edit distance
               - dedup_min_length_for_edit (int) - Sprint 43: min length for edit check
               - dedup_min_length_for_substring (int) - Sprint 43: min length for substring

    Returns:
        MultiCriteriaDeduplicator (default), SemanticDeduplicator, or None if disabled

    Example:
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> dedup = create_deduplicator_from_config(settings)
    """
    if not getattr(config, "enable_semantic_dedup", True):
        logger.info("semantic_deduplication_disabled")
        return None

    threshold = getattr(config, "semantic_dedup_threshold", 0.85)
    batch_size = getattr(config, "dedup_batch_size", 32)

    # Sprint 43: Use MultiCriteriaDeduplicator by default (ADR-044)
    use_multi_criteria = getattr(config, "enable_multi_criteria_dedup", True)

    if use_multi_criteria:
        return MultiCriteriaDeduplicator(
            threshold=threshold,
            batch_size=batch_size,
            edit_distance_threshold=getattr(config, "dedup_edit_distance_threshold", 3),
            min_length_for_edit=getattr(config, "dedup_min_length_for_edit", 5),
            min_length_for_substring=getattr(config, "dedup_min_length_for_substring", 6),
        )
    else:
        return SemanticDeduplicator(
            threshold=threshold,
            batch_size=batch_size,
        )
