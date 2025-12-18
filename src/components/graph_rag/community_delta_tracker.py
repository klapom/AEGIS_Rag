"""Community Delta Tracking for Incremental Summary Updates.

This module tracks changes to graph communities after ingestion,
enabling efficient incremental summary generation. Only communities
that have changed need their summaries regenerated.

Sprint 52 - Feature 52.1: Community Summary Generation (TD-058)

Supports:
- Tracking new communities after detection
- Tracking updated communities (changed membership)
- Tracking merged communities (multiple → single)
- Tracking split communities (single → multiple)
- Timestamp tracking for audit trail
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CommunityDelta:
    """Tracks community changes after ingestion.

    This dataclass captures all types of community changes that can occur
    during graph updates: new communities, membership updates, merges, and splits.

    Attributes:
        new_communities: Set of community IDs that were newly created
        updated_communities: Set of community IDs whose membership changed
        merged_communities: Map of old community IDs to the new merged ID
        split_communities: Map of old community IDs to set of new split IDs
        timestamp: When these changes occurred
    """

    new_communities: set[int] = field(default_factory=set)
    updated_communities: set[int] = field(default_factory=set)
    merged_communities: dict[int, int] = field(default_factory=dict)
    split_communities: dict[int, set[int]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def get_affected_communities(self) -> set[int]:
        """Get all community IDs that need summary regeneration.

        Returns:
            Set of community IDs that were affected by changes
        """
        affected = set(self.new_communities)
        affected.update(self.updated_communities)

        # Add target communities from merges
        affected.update(self.merged_communities.values())

        # Add all new communities from splits
        for split_ids in self.split_communities.values():
            affected.update(split_ids)

        return affected

    def has_changes(self) -> bool:
        """Check if there are any changes tracked.

        Returns:
            True if any changes are present
        """
        return bool(
            self.new_communities
            or self.updated_communities
            or self.merged_communities
            or self.split_communities
        )

    def __str__(self) -> str:
        """String representation of delta.

        Returns:
            Human-readable summary of changes
        """
        return (
            f"CommunityDelta("
            f"new={len(self.new_communities)}, "
            f"updated={len(self.updated_communities)}, "
            f"merged={len(self.merged_communities)}, "
            f"split={len(self.split_communities)}, "
            f"timestamp={self.timestamp.isoformat()})"
        )


async def track_community_changes(
    entities_before: dict[str, int | None],
    entities_after: dict[str, int],
) -> CommunityDelta:
    """Track changes between two community snapshots.

    Analyzes entity-to-community mappings before and after an operation
    (e.g., ingestion, re-clustering) to identify what changed.

    Args:
        entities_before: Map of entity_id → community_id (or None) before operation
        entities_after: Map of entity_id → community_id after operation

    Returns:
        CommunityDelta tracking all changes

    Example:
        >>> before = {"e1": 0, "e2": 0, "e3": None}
        >>> after = {"e1": 0, "e2": 1, "e3": 2, "e4": 2}
        >>> delta = await track_community_changes(before, after)
        >>> delta.new_communities  # {2} - e3 and e4 in new community
        >>> delta.updated_communities  # {0, 1} - e2 moved from 0 to 1
    """
    logger.info(
        "tracking_community_changes",
        entities_before_count=len(entities_before),
        entities_after_count=len(entities_after),
    )

    delta = CommunityDelta()

    # Get all community IDs before and after
    communities_before = {cid for cid in entities_before.values() if cid is not None}
    communities_after = set(entities_after.values())

    # Track new communities (appear in after but not before)
    delta.new_communities = communities_after - communities_before

    # Build reverse mapping: community_id → set of entity_ids
    comm_to_entities_before: dict[int, set[str]] = {}
    for entity_id, comm_id in entities_before.items():
        if comm_id is not None:
            if comm_id not in comm_to_entities_before:
                comm_to_entities_before[comm_id] = set()
            comm_to_entities_before[comm_id].add(entity_id)

    comm_to_entities_after: dict[int, set[str]] = {}
    for entity_id, comm_id in entities_after.items():
        if comm_id not in comm_to_entities_after:
            comm_to_entities_after[comm_id] = set()
        comm_to_entities_after[comm_id].add(entity_id)

    # Track updated communities (membership changed)
    for comm_id in communities_before:
        if comm_id not in communities_after:
            # Community disappeared - could be merged or split
            continue

        # Compare membership
        entities_before_set = comm_to_entities_before.get(comm_id, set())
        entities_after_set = comm_to_entities_after.get(comm_id, set())

        if entities_before_set != entities_after_set:
            delta.updated_communities.add(comm_id)

    # Detect merges: Multiple old communities → single new community
    # If entities from multiple old communities all ended up in one new community
    for new_comm_id in communities_after:
        if new_comm_id in delta.new_communities:
            continue  # Skip newly created communities

        new_entities = comm_to_entities_after[new_comm_id]

        # Find which old communities contributed entities
        contributing_old_comms = set()
        for entity_id in new_entities:
            old_comm_id = entities_before.get(entity_id)
            if old_comm_id is not None and old_comm_id != new_comm_id:
                contributing_old_comms.add(old_comm_id)

        # If any old communities contributed (even just 1) → those merged into new_comm_id
        if len(contributing_old_comms) >= 1:
            for old_comm_id in contributing_old_comms:
                delta.merged_communities[old_comm_id] = new_comm_id

    # Detect splits: Single old community → multiple new communities
    # If entities from one old community spread across multiple new communities
    for old_comm_id in communities_before:
        if old_comm_id not in communities_after:
            old_entities = comm_to_entities_before.get(old_comm_id, set())

            # Find which new communities received these entities
            receiving_new_comms = set()
            for entity_id in old_entities:
                if entity_id in entities_after:
                    new_comm_id = entities_after[entity_id]
                    if new_comm_id != old_comm_id:
                        receiving_new_comms.add(new_comm_id)

            # If 2+ new communities received entities → split
            if len(receiving_new_comms) >= 2:
                delta.split_communities[old_comm_id] = receiving_new_comms

    logger.info(
        "community_changes_tracked",
        new_communities=len(delta.new_communities),
        updated_communities=len(delta.updated_communities),
        merged_communities=len(delta.merged_communities),
        split_communities=len(delta.split_communities),
        total_affected=len(delta.get_affected_communities()),
    )

    return delta


async def get_entity_communities_snapshot(
    neo4j_client,
) -> dict[str, int | None]:
    """Get current entity-to-community mapping from Neo4j.

    Args:
        neo4j_client: Neo4j client instance

    Returns:
        Map of entity_id → community_id (or None if not assigned)

    Example:
        >>> from src.components.graph_rag.neo4j_client import get_neo4j_client
        >>> client = get_neo4j_client()
        >>> snapshot = await get_entity_communities_snapshot(client)
        >>> snapshot["entity_123"]
        5
    """
    cypher = """
    MATCH (e:base)
    RETURN e.entity_id AS entity_id, e.community_id AS community_id
    """

    results = await neo4j_client.execute_read(cypher)

    snapshot = {}
    for record in results:
        entity_id = record.get("entity_id")
        community_id = record.get("community_id")

        # Parse community_id from string (e.g., "community_5" → 5)
        if community_id is not None and isinstance(community_id, str):
            try:
                # Extract numeric part from "community_N"
                community_id = int(community_id.split("_")[-1])
            except (ValueError, IndexError):
                logger.warning(
                    "invalid_community_id_format",
                    entity_id=entity_id,
                    community_id=community_id,
                )
                community_id = None

        snapshot[entity_id] = community_id

    logger.info(
        "entity_communities_snapshot_retrieved",
        total_entities=len(snapshot),
        assigned_communities=sum(1 for cid in snapshot.values() if cid is not None),
    )

    return snapshot
