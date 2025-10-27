"""Semantic Entity Deduplication using sentence-transformers.

Sprint 13 Feature 13.9: ADR-017
Uses sentence-transformers to identify and merge duplicate entities based on
semantic similarity rather than string matching.

Author: Claude Code
Date: 2025-10-24
"""

from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Conditional imports
try:
    import torch
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity

    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logger.warning(
        "sentence-transformers not available. Install with: "
        "pip install sentence-transformers scikit-learn"
    )


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
        device: str = None,
    ):
        """Initialize semantic deduplicator.

        Args:
            model_name: Sentence transformer model name
                       Default: all-MiniLM-L6-v2 (90MB, 384-dim, fast)
            threshold: Cosine similarity threshold for duplicate detection
                      Recommended range: 0.90-0.95
                      - Lower (0.90): More aggressive merging
                      - Higher (0.95): More conservative
            device: Device to use ('cuda', 'cpu', or None for auto-detect)

        Raises:
            ImportError: If sentence-transformers not installed
        """
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError(
                "sentence-transformers required. Install with: "
                "pip install sentence-transformers scikit-learn"
            )

        # Auto-detect device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = SentenceTransformer(model_name, device=device)
        self.threshold = threshold
        self.device = device

        logger.info(
            "semantic_deduplicator_initialized",
            model=model_name,
            threshold=threshold,
            device=device,
        )

        if device == "cuda":
            gpu_name = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info("gpu_detected", gpu=gpu_name, vram_gb=f"{vram_gb:.1f}")

    def deduplicate(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Deduplicate entities using semantic similarity.

        Strategy:
        1. Group entities by type (only compare same types)
        2. Compute embeddings for all entity names within each type
        3. Find clusters with similarity >= threshold
        4. Keep first entity from each cluster
        5. Merge descriptions from duplicates

        Args:
            entities: List of entity dicts with keys:
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
        # Extract names
        names = [e["name"] for e in entities]

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
                duplicate_names = [entities[idx]["name"] for idx in similar]
                representative["description"] = (
                    f"{entities[i]['description']} " f"[Deduplicated from {len(similar)} mentions]"
                )

                logger.debug(
                    "entities_merged",
                    type=entity_type,
                    representative=entities[i]["name"],
                    duplicates=duplicate_names,
                    count=len(similar),
                )

            deduplicated.append(representative)

        return deduplicated


def create_deduplicator_from_config(config) -> SemanticDeduplicator:
    """Factory function to create deduplicator from app config.

    Args:
        config: Application config object with attributes:
               - enable_semantic_dedup (bool)
               - semantic_dedup_model (str)
               - semantic_dedup_threshold (float)
               - semantic_dedup_device (str)

    Returns:
        SemanticDeduplicator instance or None if disabled

    Example:
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> dedup = create_deduplicator_from_config(settings)
    """
    if not getattr(config, "enable_semantic_dedup", True):
        logger.info("semantic_deduplication_disabled")
        return None

    # Get device setting (convert "auto" to None for auto-detection)
    device = getattr(config, "semantic_dedup_device", "auto")
    if device == "auto":
        device = None  # SentenceTransformer will auto-detect cuda/cpu

    return SemanticDeduplicator(
        model_name=getattr(
            config, "semantic_dedup_model", "sentence-transformers/all-MiniLM-L6-v2"
        ),
        threshold=getattr(config, "semantic_dedup_threshold", 0.93),
        device=device,
    )
