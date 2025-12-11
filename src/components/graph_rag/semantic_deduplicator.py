"""Semantic Entity Deduplication using sentence-transformers.

Sprint 13 Feature 13.9: ADR-017
Uses sentence-transformers to identify and merge duplicate entities based on
semantic similarity rather than string matching.

Sprint 20 Feature 20.3: Singleton Pattern for SentenceTransformer
- Eliminates 200+ redundant model loads during indexing
- Lazy initialization (load on first use)
- Thread-safe singleton pattern
- Saves ~111 seconds per 223 chunks

Sprint 20 Feature 20.5: CPU Embeddings Migration
- Runs on CPU instead of GPU (frees 1-2GB VRAM for LLMs)
- Device forced to 'cpu' in singleton initialization
- No performance impact (embeddings are fast on CPU)

Sprint 43 Feature 43.x: MultiCriteriaDeduplicator (ADR-044, TD-062)
- Multi-criteria matching: exact, edit distance, substring, semantic
- Catches case variations ("Nicolas Cage" vs "nicolas cage")
- Catches typos ("Nicolas Cage" vs "Nicholas Cage")
- Catches abbreviations ("Nicolas Cage" vs "Cage")
- Min-length guards prevent false positives ("AI" in "NVIDIA")

Author: Claude Code
Date: 2025-10-24, Updated: 2025-12-10
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

# Sprint 24 Feature 24.15: Lazy import for optional reranking dependency
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = structlog.get_logger(__name__)

# Runtime conditional imports
try:
    from sentence_transformers import SentenceTransformer  # noqa: F811
    from sklearn.metrics.pairwise import cosine_similarity

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logger.warning(
        "sentence-transformers not available. Install with: "
        "pip install sentence-transformers scikit-learn"
    )

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

# ============================================================================
# Sprint 20 Feature 20.3: SINGLETON PATTERN
# ============================================================================

_sentence_transformer_instance: SentenceTransformer | None = None
_singleton_lock = None  # Will be threading.Lock() if needed


def get_sentence_transformer_singleton(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    device: str = "cpu",  # Sprint 20.5: Force CPU to free VRAM
) -> SentenceTransformer:
    """Get or create singleton SentenceTransformer instance.

    Sprint 20 Feature 20.3: Singleton pattern to prevent redundant model loading.

    Performance Impact:
    - BEFORE: 200+ model loads per indexing run = ~111 seconds wasted
    - AFTER: 1 model load per indexing run = ~0.5 seconds
    - SAVINGS: ~110 seconds per 223 chunks (98% reduction)

    Sprint 20 Feature 20.5: CPU device to free 1-2GB VRAM for LLMs.

    Args:
        model_name: Model identifier (default: all-MiniLM-L6-v2)
        device: Device to use (default: 'cpu' for VRAM savings)

    Returns:
        Singleton SentenceTransformer instance

    Thread Safety:
        Uses lazy initialization with double-checked locking pattern.
        Safe for concurrent access from multiple threads/chunks.
    """
    global _sentence_transformer_instance, _singleton_lock

    # Fast path: already initialized
    if _sentence_transformer_instance is not None:
        return _sentence_transformer_instance

    # Lazy lock creation (avoid import if not needed)
    if _singleton_lock is None:
        import threading

        _singleton_lock = threading.Lock()

    # Double-checked locking pattern
    with _singleton_lock:
        if _sentence_transformer_instance is None:
            logger.info(
                "sentence_transformer_singleton_initializing",
                model=model_name,
                device=device,
                note="First initialization - subsequent calls will reuse this instance",
            )

            _sentence_transformer_instance = SentenceTransformer(model_name, device=device)

            logger.info(
                "sentence_transformer_singleton_ready",
                model=model_name,
                device=device,
            )

        return _sentence_transformer_instance


class SemanticDeduplicator:
    """Deduplicate entities using semantic similarity.

    Uses sentence-transformers to compute embeddings of entity names and
    identifies duplicates using cosine similarity. Entities with similarity
    above threshold are merged, keeping the first mention and aggregating
    descriptions.

    Architecture Decision: ADR-017 (Semantic Entity Deduplication)
    Model Selection: ADR-018 (all-MiniLM-L6-v2)

    Example:
        >>> dedup = SemanticDeduplicator(threshold=0.93)
        >>> entities = [
        ...     {"name": "Alex", "type": "PERSON", "description": "..."},
        ...     {"name": "Alex", "type": "PERSON", "description": "..."},  # Duplicate
        ...     {"name": "Jordan", "type": "PERSON", "description": "..."}
        ... ]
        >>> clean = dedup.deduplicate(entities)
        >>> len(clean)  # 2 (Alex merged)
        2
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.93,
        device: str = "cpu",  # Sprint 20.5: Default to CPU
    ) -> None:
        """Initialize semantic deduplicator.

        Sprint 20 Changes:
        - Feature 20.3: Uses singleton SentenceTransformer (prevents 200+ reloads)
        - Feature 20.5: Defaults to CPU device (frees 1-2GB VRAM for LLMs)

        Args:
            model_name: Sentence transformer model name
                       Default: all-MiniLM-L6-v2 (90MB, 384-dim, fast)
            threshold: Cosine similarity threshold for duplicate detection
                      Recommended range: 0.90-0.95
                      - Lower (0.90): More aggressive merging
                      - Higher (0.95): More conservative
            device: Device to use (default: 'cpu' to free VRAM)
                   Sprint 20.5: Changed from 'auto' to 'cpu'

        Raises:
            ImportError: If sentence-transformers not installed
        """
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError(
                "sentence-transformers required. Install with: "
                "pip install sentence-transformers scikit-learn"
            )

        # Sprint 20.3: Use singleton instead of creating new model
        self.model = get_sentence_transformer_singleton(model_name=model_name, device=device)
        self.threshold = threshold
        self.device = device
        self.model_name = model_name

        logger.info(
            "semantic_deduplicator_initialized",
            model=model_name,
            threshold=threshold,
            device=device,
            singleton_mode=True,
            note="Using singleton SentenceTransformer (Sprint 20.3)",
        )

    def deduplicate(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate entities using semantic similarity.

        Strategy:
        1. Group entities by type (only compare same types)
        2. Compute embeddings for all entity names within each type
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

            # Deduplicate this group
            deduped_group = self._deduplicate_group(group, etype)
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

    def _deduplicate_group(
        self, entities: list[dict[str, Any]], entity_type: str
    ) -> list[dict[str, Any]]:
        """Deduplicate entities of the same type.

        Args:
            entities: Entities of same type
            entity_type: Type label (for logging)

        Returns:
            Deduplicated entities
        """
        # Extract names - handle both "name" (extraction) and "entity_name" (LightRAG format)
        names = [e.get("name", e.get("entity_name", "UNKNOWN")) for e in entities]

        # Compute embeddings (batched for efficiency)
        embeddings = self.model.encode(
            names, batch_size=64, convert_to_tensor=True, show_progress_bar=False
        )

        # Convert to numpy for sklearn
        embeddings_np = embeddings.cpu().numpy()

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
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.93,
        device: str = "cpu",
        edit_distance_threshold: int = 3,
        min_length_for_edit: int = 5,
        min_length_for_substring: int = 6,
    ) -> None:
        """Initialize multi-criteria deduplicator.

        Args:
            model_name: Sentence transformer model name (for semantic matching)
            threshold: Cosine similarity threshold for semantic matching
            device: Device for embeddings (default: 'cpu')
            edit_distance_threshold: Max edit distance to consider as duplicate
                                    Default: 3 (catches 1-2 char typos)
            min_length_for_edit: Min entity name length for edit distance check
                                Default: 5 (prevents "AI" ~ "UI")
            min_length_for_substring: Min entity name length for substring check
                                     Default: 6 (prevents "AI" in "NVIDIA")
        """
        super().__init__(model_name=model_name, threshold=threshold, device=device)

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
            model=model_name,
            threshold=threshold,
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

    def _deduplicate_group(
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

            # Compute embeddings for cluster representatives only
            embeddings = self.model.encode(
                rep_names, batch_size=64, convert_to_tensor=True, show_progress_bar=False
            )
            embeddings_np = embeddings.cpu().numpy()
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


def create_deduplicator_from_config(config) -> SemanticDeduplicator | MultiCriteriaDeduplicator | None:
    """Factory function to create deduplicator from app config.

    Sprint 20 Feature 20.5: Defaults to 'cpu' device to free VRAM.
    Sprint 43 Feature 43.1: MultiCriteriaDeduplicator support (ADR-044).

    Args:
        config: Application config object with attributes:
               - enable_semantic_dedup (bool)
               - enable_multi_criteria_dedup (bool) - Sprint 43: use multi-criteria
               - semantic_dedup_model (str)
               - semantic_dedup_threshold (float)
               - semantic_dedup_device (str) - Sprint 20.5: defaults to 'cpu'
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

    # Sprint 20.5: Default to 'cpu' instead of 'auto' to free VRAM
    device = getattr(config, "semantic_dedup_device", "cpu")
    # Convert 'auto' to 'cpu' (Sprint 20.5: no auto-detection, always use CPU)
    if device == "auto":
        device = "cpu"

    model_name = getattr(
        config, "semantic_dedup_model", "sentence-transformers/all-MiniLM-L6-v2"
    )
    threshold = getattr(config, "semantic_dedup_threshold", 0.93)

    # Sprint 43: Use MultiCriteriaDeduplicator by default (ADR-044)
    use_multi_criteria = getattr(config, "enable_multi_criteria_dedup", True)

    if use_multi_criteria:
        return MultiCriteriaDeduplicator(
            model_name=model_name,
            threshold=threshold,
            device=device,
            edit_distance_threshold=getattr(config, "dedup_edit_distance_threshold", 3),
            min_length_for_edit=getattr(config, "dedup_min_length_for_edit", 5),
            min_length_for_substring=getattr(config, "dedup_min_length_for_substring", 6),
        )
    else:
        return SemanticDeduplicator(
            model_name=model_name,
            threshold=threshold,
            device=device,
        )
