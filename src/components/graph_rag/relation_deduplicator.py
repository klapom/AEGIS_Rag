"""Relation Deduplication for Knowledge Graph.

Sprint 44 Feature 44.1-44.4: TD-063
Deduplicates relationships extracted from documents using:

1. **Entity Name Normalization**: Remap relation endpoints to canonical entity names
   after entity deduplication (e.g., "nicolas cage" → "Nicolas Cage")

2. **Type Synonym Resolution**: Normalize relation types to canonical forms
   (e.g., STARRED_IN, PLAYED_IN, APPEARED_IN → ACTED_IN)

3. **Bidirectional Relation Handling**: For symmetric relations, ensure only one
   direction is stored (e.g., A-KNOWS-B and B-KNOWS-A → only A-KNOWS-B)

Author: Claude Code
Date: 2025-12-12
"""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# RELATION TYPE SYNONYMS
# ============================================================================
# Maps canonical relation types to their synonyms.
# When a synonym is encountered, it's normalized to the canonical type.

RELATION_TYPE_SYNONYMS: dict[str, list[str]] = {
    # Acting/Performing
    "ACTED_IN": ["STARRED_IN", "PLAYED_IN", "APPEARED_IN", "PERFORMED_IN", "FEATURED_IN"],
    "DIRECTED": ["DIRECTED_BY", "HELMED", "MADE_BY"],
    "PRODUCED": ["PRODUCED_BY", "EXECUTIVE_PRODUCED"],
    "WRITTEN_BY": ["WROTE", "AUTHORED", "PENNED", "SCRIPTED"],
    # Personal relationships
    "MARRIED_TO": ["SPOUSE_OF", "WED_TO", "HUSBAND_OF", "WIFE_OF", "PARTNER_OF"],
    "CHILD_OF": ["SON_OF", "DAUGHTER_OF", "OFFSPRING_OF"],
    "PARENT_OF": ["FATHER_OF", "MOTHER_OF"],
    "SIBLING_OF": ["BROTHER_OF", "SISTER_OF"],
    # Professional
    "WORKS_FOR": ["EMPLOYED_BY", "WORKS_AT", "EMPLOYEE_OF"],
    "MEMBER_OF": ["BELONGS_TO", "PART_OF", "AFFILIATED_WITH"],
    "FOUNDED": ["CREATED", "ESTABLISHED", "STARTED", "CO_FOUNDED"],
    "CEO_OF": ["LEADS", "HEADS", "RUNS", "MANAGES"],
    # Location
    "LOCATED_IN": ["BASED_IN", "SITUATED_IN", "FOUND_IN", "HEADQUARTERED_IN"],
    "BORN_IN": ["BIRTHPLACE", "NATIVE_OF", "FROM"],
    "DIED_IN": ["DEATH_PLACE", "PASSED_AWAY_IN"],
    # Education
    "STUDIED_AT": ["ATTENDED", "GRADUATED_FROM", "EDUCATED_AT", "ALUMNI_OF"],
    "TAUGHT_AT": ["PROFESSOR_AT", "TEACHES_AT", "LECTURER_AT"],
    # Generic
    "RELATES_TO": ["RELATED_TO", "ASSOCIATED_WITH", "CONNECTED_TO", "LINKED_TO"],
    "KNOWS": ["KNOWS_OF", "ACQUAINTED_WITH", "MET"],
}

# Build reverse mapping: synonym → canonical
_SYNONYM_TO_CANONICAL: dict[str, str] = {}
for canonical, synonyms in RELATION_TYPE_SYNONYMS.items():
    for syn in synonyms:
        _SYNONYM_TO_CANONICAL[syn.upper()] = canonical
    # Also map canonical to itself (for consistency)
    _SYNONYM_TO_CANONICAL[canonical.upper()] = canonical


# ============================================================================
# SYMMETRIC RELATIONS
# ============================================================================
# Relations where A-REL-B is equivalent to B-REL-A.
# For these, we normalize to alphabetical order of entities.

SYMMETRIC_RELATIONS: set[str] = {
    "KNOWS",
    "RELATED_TO",
    "RELATES_TO",
    "MARRIED_TO",
    "SIBLING_OF",
    "COLLABORATED_WITH",
    "WORKS_WITH",
    "FRIENDS_WITH",
    "PARTNERS_WITH",
    "CONNECTED_TO",
    "ASSOCIATED_WITH",
}


class RelationDeduplicator:
    """Deduplicates relations extracted from documents.

    Sprint 44 Feature 44.1-44.4 (TD-063)

    Three-stage deduplication:
    1. Entity name normalization (remap to canonical names)
    2. Type synonym resolution (STARRED_IN → ACTED_IN)
    3. Bidirectional handling (symmetric relations only once)

    Example:
        >>> dedup = RelationDeduplicator()
        >>> relations = [
        ...     {"source": "nicolas cage", "target": "Leaving Las Vegas", "relationship_type": "STARRED_IN"},
        ...     {"source": "Nicolas Cage", "target": "Leaving Las Vegas", "relationship_type": "ACTED_IN"},
        ... ]
        >>> entity_mapping = {"nicolas cage": "Nicolas Cage"}
        >>> result = dedup.deduplicate(relations, entity_mapping=entity_mapping)
        >>> len(result)  # Merged into 1
        1
    """

    def __init__(
        self,
        type_synonyms: dict[str, list[str]] | None = None,
        symmetric_relations: set[str] | None = None,
        preserve_original_type: bool = False,
    ) -> None:
        """Initialize relation deduplicator.

        Args:
            type_synonyms: Custom type synonym mapping. If None, uses default.
            symmetric_relations: Custom set of symmetric relation types. If None, uses default.
            preserve_original_type: If True, store original type in metadata.
        """
        self.type_synonyms = type_synonyms or RELATION_TYPE_SYNONYMS
        self.symmetric_relations = symmetric_relations or SYMMETRIC_RELATIONS
        self.preserve_original_type = preserve_original_type

        # Build reverse mapping for custom synonyms
        self._synonym_to_canonical: dict[str, str] = {}
        for canonical, synonyms in self.type_synonyms.items():
            for syn in synonyms:
                self._synonym_to_canonical[syn.upper()] = canonical
            self._synonym_to_canonical[canonical.upper()] = canonical

        logger.info(
            "relation_deduplicator_initialized",
            type_synonyms_count=len(self.type_synonyms),
            symmetric_relations_count=len(self.symmetric_relations),
            preserve_original_type=preserve_original_type,
        )

    def normalize_relation_type(self, rel_type: str) -> str:
        """Normalize relation type to canonical form.

        Args:
            rel_type: Original relation type (e.g., "STARRED_IN", "starred_in")

        Returns:
            Canonical relation type (e.g., "ACTED_IN")
        """
        # Normalize: uppercase, replace spaces with underscores
        normalized = rel_type.upper().strip().replace(" ", "_").replace("-", "_")

        # Look up canonical form
        return self._synonym_to_canonical.get(normalized, normalized)

    def normalize_entity_references(
        self,
        relations: list[dict[str, Any]],
        entity_mapping: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Remap relation endpoints to canonical entity names.

        After entity deduplication, some entity names may have been merged.
        This method updates relation source/target to use the canonical names.

        Args:
            relations: List of relation dicts with source, target, relationship_type
            entity_mapping: Mapping from original name (lowercase) to canonical name

        Returns:
            Relations with updated source/target names
        """
        if not entity_mapping:
            return relations

        normalized = []
        remapped_count = 0

        for rel in relations:
            new_rel = rel.copy()

            # Normalize source
            source = rel.get("source", "")
            source_lower = source.lower().strip()
            if source_lower in entity_mapping:
                new_rel["source"] = entity_mapping[source_lower]
                if new_rel["source"] != source:
                    remapped_count += 1

            # Normalize target
            target = rel.get("target", "")
            target_lower = target.lower().strip()
            if target_lower in entity_mapping:
                new_rel["target"] = entity_mapping[target_lower]
                if new_rel["target"] != target:
                    remapped_count += 1

            normalized.append(new_rel)

        if remapped_count > 0:
            logger.debug(
                "entity_references_normalized",
                total_relations=len(relations),
                remapped_endpoints=remapped_count,
            )

        return normalized

    def deduplicate(
        self,
        relations: list[dict[str, Any]],
        entity_mapping: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Deduplicate relations using all three stages.

        Args:
            relations: List of relation dicts with:
                      - source (str): Source entity name
                      - target (str): Target entity name
                      - relationship_type (str): Relation type
                      - description (str, optional): Relation description
                      - weight (float, optional): Relation weight
            entity_mapping: Optional mapping from old entity names to canonical names
                           (from entity deduplication step)

        Returns:
            Deduplicated relations with normalized types
        """
        if not relations:
            return []

        stats = {
            "input_count": len(relations),
            "entity_remaps": 0,
            "type_normalizations": 0,
            "bidirectional_merges": 0,
            "output_count": 0,
        }

        # Stage 1: Entity name normalization
        if entity_mapping:
            relations = self.normalize_entity_references(relations, entity_mapping)
            # Count remaps (approximate)
            stats["entity_remaps"] = sum(
                1
                for r in relations
                if r.get("source", "").lower() in entity_mapping
                or r.get("target", "").lower() in entity_mapping
            )

        # Stage 2 & 3: Type normalization + deduplication
        seen: dict[str, dict[str, Any]] = {}

        for rel in relations:
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            orig_type = rel.get("relationship_type", "RELATES_TO")

            # Skip invalid relations
            if not source or not target:
                continue

            # Normalize type
            norm_type = self.normalize_relation_type(orig_type)
            if norm_type != orig_type.upper():
                stats["type_normalizations"] += 1

            # Build deduplication key
            # For symmetric relations, sort endpoints alphabetically
            if norm_type in self.symmetric_relations:
                sorted_endpoints = tuple(sorted([source.lower(), target.lower()]))
                key = f"{sorted_endpoints[0]}|{sorted_endpoints[1]}|{norm_type}"

                # Check if we're merging a bidirectional relation
                reverse_key = f"{target.lower()}|{source.lower()}|{norm_type}"
                if reverse_key in seen:
                    stats["bidirectional_merges"] += 1
            else:
                key = f"{source.lower()}|{target.lower()}|{norm_type}"

            # Deduplicate: keep first occurrence, optionally merge metadata
            if key not in seen:
                new_rel = rel.copy()
                new_rel["source"] = source
                new_rel["target"] = target
                new_rel["relationship_type"] = norm_type

                # Preserve original type if requested
                if self.preserve_original_type and orig_type.upper() != norm_type:
                    new_rel["original_type"] = orig_type

                seen[key] = new_rel
            else:
                # Merge: combine descriptions if both exist
                existing = seen[key]
                new_desc = rel.get("description", "")
                existing_desc = existing.get("description", "")

                if new_desc and new_desc != existing_desc:
                    if existing_desc:
                        existing["description"] = f"{existing_desc}; {new_desc}"
                    else:
                        existing["description"] = new_desc

                # Merge weights (sum or max)
                new_weight = rel.get("weight", 0)
                existing_weight = existing.get("weight", 0)
                if new_weight or existing_weight:
                    existing["weight"] = max(existing_weight, new_weight)

        result = list(seen.values())
        stats["output_count"] = len(result)

        # Calculate reduction
        reduction_pct = (
            100 * (stats["input_count"] - stats["output_count"]) / stats["input_count"]
            if stats["input_count"] > 0
            else 0
        )

        logger.info(
            "relation_deduplication_complete",
            input_count=stats["input_count"],
            output_count=stats["output_count"],
            reduction_pct=f"{reduction_pct:.1f}%",
            type_normalizations=stats["type_normalizations"],
            bidirectional_merges=stats["bidirectional_merges"],
        )

        return result

    def get_stats(self, relations: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze relations without modifying them.

        Useful for reporting on potential deduplication impact.

        Args:
            relations: List of relations to analyze

        Returns:
            Statistics about potential deduplication
        """
        type_counts: dict[str, int] = {}
        canonical_type_counts: dict[str, int] = {}
        potential_symmetric_dupes = 0

        for rel in relations:
            rel_type = rel.get("relationship_type", "UNKNOWN")
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

            canonical = self.normalize_relation_type(rel_type)
            canonical_type_counts[canonical] = canonical_type_counts.get(canonical, 0) + 1

        # Count potential symmetric duplicates
        seen_symmetric: set[str] = set()
        for rel in relations:
            source = rel.get("source", "").lower()
            target = rel.get("target", "").lower()
            rel_type = self.normalize_relation_type(rel.get("relationship_type", ""))

            if rel_type in self.symmetric_relations:
                key = f"{min(source, target)}|{max(source, target)}|{rel_type}"
                if key in seen_symmetric:
                    potential_symmetric_dupes += 1
                else:
                    seen_symmetric.add(key)

        return {
            "total_relations": len(relations),
            "unique_types": len(type_counts),
            "type_distribution": type_counts,
            "canonical_type_distribution": canonical_type_counts,
            "potential_type_merges": len(type_counts) - len(canonical_type_counts),
            "potential_symmetric_duplicates": potential_symmetric_dupes,
        }


def create_relation_deduplicator_from_config(config) -> RelationDeduplicator | None:
    """Factory function to create relation deduplicator from app config.

    Args:
        config: Application config object with attributes:
               - enable_relation_dedup (bool): Enable relation deduplication
               - relation_preserve_original_type (bool): Keep original type in metadata

    Returns:
        RelationDeduplicator or None if disabled
    """
    if not getattr(config, "enable_relation_dedup", True):
        logger.info("relation_deduplication_disabled")
        return None

    preserve_original = getattr(config, "relation_preserve_original_type", False)

    return RelationDeduplicator(preserve_original_type=preserve_original)
