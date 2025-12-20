"""Hybrid Relation Deduplication with Redis-backed Manual Overrides.

Sprint 49 Feature 49.8: Manual synonym overrides for relation deduplication.
Combines automatic deduplication with manual Redis-backed overrides.

Manual overrides stored in Redis hash map:
- Key: "graph:relation-synonyms"
- Type: Hash
- Fields: {"USES": "USED_BY", "ACTED_IN": "STARRED_IN", ...}
- TTL: None (persistent)

Priority:
1. Manual overrides (highest priority) - from Redis
2. Automatic deduplication - from RelationDeduplicator
3. Original type (lowest priority)

Author: Claude Code
Date: 2025-12-16
"""

from __future__ import annotations

from typing import Any

import structlog

from src.components.graph_rag.relation_deduplicator import RelationDeduplicator

logger = structlog.get_logger(__name__)

# Redis key for manual synonym overrides
REDIS_KEY_RELATION_SYNONYMS = "graph:relation-synonyms"


class HybridRelationDeduplicator:
    """Hybrid deduplicator: automatic + manual overrides.

    Sprint 49 Feature 49.8: Combines RelationDeduplicator with Redis manual overrides.

    Manual overrides take precedence over automatic type normalization.
    This allows domain experts to fix edge cases without code changes.

    Example:
        >>> dedup = HybridRelationDeduplicator()
        >>> # Add manual override
        >>> await dedup.add_manual_override("USES", "USED_BY")
        >>> # Deduplicate relations
        >>> relations = [{"source": "A", "target": "B", "relationship_type": "USES"}]
        >>> result = await dedup.deduplicate_types(["USES", "ACTED_IN"])
        >>> result["USES"]
        'USED_BY'  # Manual override applied
    """

    def __init__(
        self,
        base_deduplicator: RelationDeduplicator | None = None,
        preserve_original_type: bool = False,
    ) -> None:
        """Initialize hybrid deduplicator.

        Args:
            base_deduplicator: Base deduplicator for automatic normalization.
                             If None, creates default RelationDeduplicator.
            preserve_original_type: If True, store original type in metadata.
        """
        self.base_deduplicator = base_deduplicator or RelationDeduplicator(
            preserve_original_type=preserve_original_type
        )
        self.preserve_original_type = preserve_original_type

        logger.info(
            "hybrid_relation_deduplicator_initialized",
            preserve_original_type=preserve_original_type,
        )

    async def deduplicate_types(
        self,
        relation_types: list[str],
        use_manual_overrides: bool = True,
    ) -> dict[str, str]:
        """Deduplicate relation types with manual overrides.

        Process:
        1. Get manual overrides from Redis (if enabled)
        2. Apply manual overrides first
        3. Apply automatic normalization to remaining types
        4. Return combined type_synonym_map

        Args:
            relation_types: List of relation types to deduplicate
            use_manual_overrides: If True, apply manual overrides from Redis

        Returns:
            Mapping from original type to canonical type
            e.g., {"USES": "USED_BY", "ACTED_IN": "ACTED_IN", ...}
        """
        if not relation_types:
            return {}

        type_mapping: dict[str, str] = {}

        # Step 1: Get manual overrides from Redis
        manual_overrides: dict[str, str] = {}
        if use_manual_overrides:
            try:
                manual_overrides = await self._get_manual_overrides()
                logger.debug(
                    "manual_overrides_loaded",
                    count=len(manual_overrides),
                    overrides=list(manual_overrides.keys())[:5],  # Show first 5
                )
            except Exception as e:
                logger.warning("failed_to_load_manual_overrides", error=str(e))

        # Step 2: Apply manual overrides first (highest priority)
        for rel_type in relation_types:
            # Normalize to uppercase for lookup
            normalized = rel_type.upper().strip().replace(" ", "_").replace("-", "_")

            if normalized in manual_overrides:
                type_mapping[normalized] = manual_overrides[normalized]
                logger.debug(
                    "manual_override_applied",
                    original_type=normalized,
                    canonical_type=manual_overrides[normalized],
                )

        # Step 3: Apply automatic normalization to remaining types
        for rel_type in relation_types:
            normalized = rel_type.upper().strip().replace(" ", "_").replace("-", "_")

            # Skip if already mapped by manual override
            if normalized in type_mapping:
                continue

            # Apply automatic normalization
            canonical = self.base_deduplicator.normalize_relation_type(rel_type)
            type_mapping[normalized] = canonical

        stats = {
            "total_types": len(relation_types),
            "manual_overrides_applied": sum(
                1 for t in relation_types if t.upper() in manual_overrides
            ),
            "automatic_normalizations": len(type_mapping) - sum(
                1 for t in relation_types if t.upper() in manual_overrides
            ),
            "unique_canonical_types": len(set(type_mapping.values())),
        }

        logger.info(
            "type_deduplication_complete",
            **stats,
        )

        return type_mapping

    async def deduplicate(
        self,
        relations: list[dict[str, Any]],
        entity_mapping: dict[str, str] | None = None,
        use_manual_overrides: bool = True,
    ) -> list[dict[str, Any]]:
        """Deduplicate relations with manual overrides.

        Args:
            relations: List of relation dicts with source, target, relationship_type
            entity_mapping: Optional entity name mapping from entity deduplication
            use_manual_overrides: If True, apply manual overrides from Redis

        Returns:
            Deduplicated relations with normalized types
        """
        if not relations:
            return []

        # Step 1: Get type mapping (manual overrides + automatic)
        relation_types = [r.get("relationship_type", "RELATES_TO") for r in relations]
        type_mapping = await self.deduplicate_types(
            relation_types, use_manual_overrides=use_manual_overrides
        )

        # Step 2: Apply type mapping to relations
        relations_with_normalized_types = []
        for rel in relations:
            orig_type = rel.get("relationship_type", "RELATES_TO")
            normalized_type = orig_type.upper().strip().replace(" ", "_").replace("-", "_")
            canonical_type = type_mapping.get(normalized_type, normalized_type)

            new_rel = rel.copy()
            new_rel["relationship_type"] = canonical_type

            # Preserve original type if requested
            if self.preserve_original_type and orig_type.upper() != canonical_type:
                new_rel["original_type"] = orig_type

            relations_with_normalized_types.append(new_rel)

        # Step 3: Use base deduplicator for final deduplication
        # (handles entity remapping, bidirectional relations, etc.)
        return self.base_deduplicator.deduplicate(
            relations_with_normalized_types,
            entity_mapping=entity_mapping,
        )

    async def _get_manual_overrides(self) -> dict[str, str]:
        """Get manual synonym overrides from Redis.

        Returns:
            Mapping of relation_type -> canonical_type
            e.g., {"USES": "USED_BY", "ACTED_IN": "STARRED_IN"}
        """
        try:
            # Lazy import to avoid circular dependency
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            # Get all fields from hash map
            overrides_data = await redis_client.hgetall(REDIS_KEY_RELATION_SYNONYMS)  # type: ignore[misc]

            if not overrides_data:
                return {}

            # Convert bytes to strings if needed
            overrides = {}
            for key, value in overrides_data.items():
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                value_str = value.decode("utf-8") if isinstance(value, bytes) else value
                overrides[key_str.upper()] = value_str.upper()

            return overrides

        except Exception as e:
            logger.error("failed_to_get_manual_overrides", error=str(e))
            return {}

    async def add_manual_override(
        self, from_type: str, to_type: str
    ) -> None:
        """Add manual synonym override.

        Args:
            from_type: Relation type to map (e.g., "USES")
            to_type: Target canonical type (e.g., "USED_BY")

        Example:
            >>> await dedup.add_manual_override("USES", "USED_BY")
        """
        try:
            # Lazy import to avoid circular dependency
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            # Normalize both types
            from_type_normalized = from_type.upper().strip().replace(" ", "_").replace("-", "_")
            to_type_normalized = to_type.upper().strip().replace(" ", "_").replace("-", "_")

            # Store in Redis hash map (persistent, no TTL)
            await redis_client.hset(  # type: ignore[misc]
                REDIS_KEY_RELATION_SYNONYMS,
                from_type_normalized,
                to_type_normalized,
            )

            logger.info(
                "manual_override_added",
                from_type=from_type_normalized,
                to_type=to_type_normalized,
            )

        except Exception as e:
            logger.error(
                "failed_to_add_manual_override",
                from_type=from_type,
                to_type=to_type,
                error=str(e),
            )
            raise

    async def remove_manual_override(self, from_type: str) -> bool:
        """Remove manual synonym override.

        Args:
            from_type: Relation type to remove mapping for

        Returns:
            True if override was removed, False if it didn't exist
        """
        try:
            # Lazy import to avoid circular dependency
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            # Normalize type
            from_type_normalized = from_type.upper().strip().replace(" ", "_").replace("-", "_")

            # Remove from Redis hash map
            result = await redis_client.hdel(REDIS_KEY_RELATION_SYNONYMS, from_type_normalized)  # type: ignore[misc]

            success = bool(result > 0)
            if success:
                logger.info("manual_override_removed", from_type=from_type_normalized)
            else:
                logger.debug("manual_override_not_found", from_type=from_type_normalized)

            return success

        except Exception as e:
            logger.error(
                "failed_to_remove_manual_override",
                from_type=from_type,
                error=str(e),
            )
            raise

    async def get_all_manual_overrides(self) -> dict[str, str]:
        """Get all manual synonym overrides.

        Returns:
            All current overrides as dict
        """
        return await self._get_manual_overrides()

    async def clear_all_manual_overrides(self) -> int:
        """Clear all manual synonym overrides.

        Returns:
            Number of overrides that were cleared
        """
        try:
            # Lazy import to avoid circular dependency
            from src.components.memory import get_redis_memory

            redis_memory = get_redis_memory()
            redis_client = await redis_memory.client

            # Get count before deletion
            overrides = await self._get_manual_overrides()
            count = len(overrides)

            # Delete the entire hash map
            if count > 0:
                await redis_client.delete(REDIS_KEY_RELATION_SYNONYMS)

            logger.info("manual_overrides_cleared", count=count)
            return count

        except Exception as e:
            logger.error("failed_to_clear_manual_overrides", error=str(e))
            raise


def get_hybrid_relation_deduplicator(
    preserve_original_type: bool = False,
) -> HybridRelationDeduplicator:
    """Factory function to get hybrid relation deduplicator.

    Args:
        preserve_original_type: If True, store original type in metadata

    Returns:
        HybridRelationDeduplicator instance
    """
    return HybridRelationDeduplicator(preserve_original_type=preserve_original_type)
