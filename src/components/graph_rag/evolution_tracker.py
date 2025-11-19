"""Evolution Tracker for Graph Entity Change Monitoring.

This module tracks entity changes, detects drift, and provides change analytics.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict

import structlog
from pydantic import BaseModel

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client

logger = structlog.get_logger(__name__)


class ChangeEvent(BaseModel):
    """Change event record."""

    entity_id: str
    version_from: int
    version_to: int
    timestamp: datetime
    changed_fields: list[str]
    change_type: str  # "create", "update", "delete"
    changed_by: str
    reason: str = ""


class EvolutionTracker:
    """Tracks and analyzes entity evolution and changes."""

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """Initialize evolution tracker.

        Args:
            neo4j_client: Neo4j client instance (default: from singleton)
        """
        self.client = neo4j_client or get_neo4j_client()
        logger.info("Initialized EvolutionTracker")

    async def track_changes(
        self,
        entity_id: str,
        old_version: Dict[str, Any] | None,
        new_version: Dict[str, Any],
    ) -> ChangeEvent:
        """Record change event for an entity.

        Args:
            entity_id: Entity ID
            old_version: Previous version data (None for create)
            new_version: New version data

        Returns:
            ChangeEvent with change details
        """
        # Determine change type
        if old_version is None:
            change_type = "create"
            changed_fields = list(new_version.keys())
            version_from = 0
        else:
            change_type = "update"
            changed_fields = []
            ignore_keys = {
                "version_id",
                "version_number",
                "valid_from",
                "valid_to",
                "transaction_from",
                "transaction_to",
                "changed_by",
                "change_reason",
            }

            for key in new_version:
                if key in ignore_keys:
                    continue
                if old_version.get(key) != new_version.get(key):
                    changed_fields.append(key)

            version_from = old_version.get("version_number", 0)

        # Create change event
        event = ChangeEvent(
            entity_id=entity_id,
            version_from=version_from,
            version_to=new_version.get("version_number", 1),
            timestamp=datetime.now(UTC),
            changed_fields=changed_fields,
            change_type=change_type,
            changed_by=new_version.get("changed_by", "system"),
            reason=new_version.get("change_reason", ""),
        )

        # Store change event in Neo4j
        query = """
        CREATE (c:ChangeEvent {
            entity_id: $entity_id,
            version_from: $version_from,
            version_to: $version_to,
            timestamp: datetime($timestamp),
            changed_fields: $changed_fields,
            change_type: $change_type,
            changed_by: $changed_by,
            reason: $reason
        })
        RETURN c
        """

        await self.client.execute_write(
            query,
            {
                "entity_id": entity_id,
                "version_from": event.version_from,
                "version_to": event.version_to,
                "timestamp": event.timestamp.isoformat(),
                "changed_fields": event.changed_fields,
                "change_type": event.change_type,
                "changed_by": event.changed_by,
                "reason": event.reason,
            },
        )

        logger.info(
            "Tracked change",
            entity_id=entity_id,
            change_type=change_type,
            fields_changed=len(changed_fields),
        )

        return event

    async def get_change_log(
        self,
        entity_id: str,
        limit: int = 50,
    ) -> list[Dict[str, Any]]:
        """Get change history for an entity.

        Args:
            entity_id: Entity ID
            limit: Maximum number of changes to return

        Returns:
            List of change events ordered by timestamp descending
        """
        query = """
        MATCH (c:ChangeEvent {entity_id: $entity_id})
        RETURN c
        ORDER BY c.timestamp DESC
        LIMIT $limit
        """

        results = await self.client.execute_read(query, {"entity_id": entity_id, "limit": limit})

        changes = []
        for record in results:
            change_data = dict(record["c"])
            # Convert datetime to ISO string
            if "timestamp" in change_data and hasattr(change_data["timestamp"], "isoformat"):
                change_data["timestamp"] = change_data["timestamp"].isoformat()
            changes.append(change_data)

        logger.debug("Retrieved change log", entity_id=entity_id, count=len(changes))
        return changes

    async def get_change_statistics(self, entity_id: str) -> Dict[str, Any]:
        """Get change statistics for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Statistics including change count, frequency, and field changes
        """
        query = """
        MATCH (c:ChangeEvent {entity_id: $entity_id})
        WITH c
        ORDER BY c.timestamp
        WITH collect(c) as changes
        WITH changes,
             size(changes) as total_changes,
             changes[0].timestamp as first_change,
             changes[-1].timestamp as last_change
        RETURN total_changes, first_change, last_change, changes
        """

        results = await self.client.execute_read(query, {"entity_id": entity_id})

        if not results or not results[0].get("total_changes"):
            return {
                "entity_id": entity_id,
                "total_changes": 0,
                "change_frequency": 0.0,
                "first_change": None,
                "last_change": None,
                "most_changed_fields": [],
            }

        record = results[0]
        total_changes = record["total_changes"]
        first_change = record["first_change"]
        last_change = record["last_change"]

        # Calculate change frequency (changes per day)
        if first_change and last_change:
            if hasattr(first_change, "isoformat"):
                first_change = datetime.fromisoformat(first_change.isoformat())
            if hasattr(last_change, "isoformat"):
                last_change = datetime.fromisoformat(last_change.isoformat())

            time_span = (last_change - first_change).total_seconds() / 86400  # days
            change_frequency = total_changes / max(time_span, 1.0)
        else:
            change_frequency = 0.0

        # Count field changes
        field_counts: dict[str, int] = {}
        for change in record["changes"]:
            for field in change.get("changed_fields", []):
                field_counts[field] = field_counts.get(field, 0) + 1

        # Sort fields by change count
        most_changed_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        result = {
            "entity_id": entity_id,
            "total_changes": total_changes,
            "change_frequency": round(change_frequency, 2),
            "first_change": (
                first_change.isoformat() if isinstance(first_change, datetime) else first_change
            ),
            "last_change": (
                last_change.isoformat() if isinstance(last_change, datetime) else last_change
            ),
            "most_changed_fields": [
                {"field": field, "change_count": count} for field, count in most_changed_fields
            ],
        }

        logger.debug("Retrieved change statistics", entity_id=entity_id, total=total_changes)
        return result

    async def detect_drift(self, entity_id: str, days: int = 30) -> Dict[str, Any]:
        """Detect rapid changes (drift) in an entity.

        Args:
            entity_id: Entity ID
            days: Time window in days to analyze

        Returns:
            Drift analysis with change rate and alert status
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        query = """
        MATCH (c:ChangeEvent {entity_id: $entity_id})
        WHERE c.timestamp >= datetime($cutoff_date)
        RETURN count(c) as recent_changes,
               collect(c.changed_fields) as all_changed_fields
        """

        results = await self.client.execute_read(
            query, {"entity_id": entity_id, "cutoff_date": cutoff_date.isoformat()}
        )

        if not results:
            return {
                "entity_id": entity_id,
                "days_analyzed": days,
                "recent_changes": 0,
                "change_rate": 0.0,
                "drift_detected": False,
                "alert_level": "normal",
            }

        record = results[0]
        recent_changes = record.get("recent_changes", 0)
        change_rate = recent_changes / days

        # Determine alert level based on change rate
        # Thresholds: >1 change/day = high, >0.5 = medium, else normal
        if change_rate > 1.0:
            alert_level = "high"
            drift_detected = True
        elif change_rate > 0.5:
            alert_level = "medium"
            drift_detected = True
        else:
            alert_level = "normal"
            drift_detected = False

        # Count unique fields changed
        unique_fields = set()
        for fields_list in record.get("all_changed_fields", []):
            unique_fields.update(fields_list)

        result = {
            "entity_id": entity_id,
            "days_analyzed": days,
            "recent_changes": recent_changes,
            "change_rate": round(change_rate, 2),
            "drift_detected": drift_detected,
            "alert_level": alert_level,
            "unique_fields_changed": list(unique_fields),
            "unique_field_count": len(unique_fields),
        }

        if drift_detected:
            logger.warning(
                "Drift detected",
                entity_id=entity_id,
                alert_level=alert_level,
                change_rate=change_rate,
            )
        else:
            logger.debug("No drift detected", entity_id=entity_id, change_rate=change_rate)

        return result

    async def get_stable_entities(
        self,
        min_age_days: int = 30,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """Find entities with no recent changes (stable entities).

        Args:
            min_age_days: Minimum age in days with no changes
            limit: Maximum number of entities to return

        Returns:
            List of stable entity IDs with metadata
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=min_age_days)

        query = """
        MATCH (e:Entity)
        WHERE e.transaction_to IS NULL
          AND NOT exists((e)<-[:CHANGED]-(:ChangeEvent))
          AND e.valid_from <= datetime($cutoff_date)
        OPTIONAL MATCH (c:ChangeEvent {entity_id: e.id})
        WHERE c.timestamp >= datetime($cutoff_date)
        WITH e, count(c) as recent_changes
        WHERE recent_changes = 0
        RETURN e.id as entity_id,
               e.name as name,
               e.type as type,
               e.valid_from as created_at,
               e.version_number as version
        ORDER BY e.valid_from
        LIMIT $limit
        """

        results = await self.client.execute_read(
            query, {"cutoff_date": cutoff_date.isoformat(), "limit": limit}
        )

        stable_entities = []
        for record in results:
            entity_data = {
                "entity_id": record.get("entity_id"),
                "name": record.get("name"),
                "type": record.get("type"),
                "version": record.get("version", 1),
            }

            created_at = record.get("created_at")
            if created_at:
                if hasattr(created_at, "isoformat"):
                    entity_data["created_at"] = created_at.isoformat()
                else:
                    entity_data["created_at"] = created_at

            stable_entities.append(entity_data)

        logger.info(
            "Retrieved stable entities",
            count=len(stable_entities),
            min_age_days=min_age_days,
        )

        return stable_entities

    async def get_active_entities(
        self,
        days: int = 7,
        min_changes: int = 3,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """Find entities with frequent recent changes (active entities).

        Args:
            days: Time window in days
            min_changes: Minimum number of changes required
            limit: Maximum number of entities to return

        Returns:
            List of active entity IDs with change counts
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        query = """
        MATCH (c:ChangeEvent)
        WHERE c.timestamp >= datetime($cutoff_date)
        WITH c.entity_id as entity_id, count(c) as change_count
        WHERE change_count >= $min_changes
        MATCH (e:Entity {id: entity_id})
        WHERE e.transaction_to IS NULL
        RETURN e.id as entity_id,
               e.name as name,
               e.type as type,
               change_count
        ORDER BY change_count DESC
        LIMIT $limit
        """

        results = await self.client.execute_read(
            query,
            {
                "cutoff_date": cutoff_date.isoformat(),
                "min_changes": min_changes,
                "limit": limit,
            },
        )

        active_entities = []
        for record in results:
            active_entities.append(
                {
                    "entity_id": record.get("entity_id"),
                    "name": record.get("name"),
                    "type": record.get("type"),
                    "change_count": record.get("change_count", 0),
                    "days_analyzed": days,
                }
            )

        logger.info(
            "Retrieved active entities",
            count=len(active_entities),
            days=days,
            min_changes=min_changes,
        )

        return active_entities


# Singleton instance
_evolution_tracker: EvolutionTracker | None = None


def get_evolution_tracker() -> EvolutionTracker:
    """Get global evolution tracker instance (singleton).

    Returns:
        EvolutionTracker instance
    """
    global _evolution_tracker
    if _evolution_tracker is None:
        _evolution_tracker = EvolutionTracker()
    return _evolution_tracker
