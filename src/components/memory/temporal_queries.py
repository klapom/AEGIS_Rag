"""Bi-Temporal Memory Query Support.

This module provides bi-temporal querying capabilities for episodic memory:
- Valid time: When the fact was true in the real world
- Transaction time: When the fact was stored in the database
- Point-in-time queries
- Time range queries
- Entity history tracking
"""

from datetime import datetime, timezone
from typing import Any, Dict

import structlog

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.config import settings
from src.core.exceptions import MemoryError

logger = structlog.get_logger(__name__)


class TemporalMemoryQuery:
    """Bi-temporal query support for episodic memory.

    Implements bitemporal model with:
    - valid_from/valid_to: Real-world validity period
    - transaction_from/transaction_to: Database transaction period
    """

    def __init__(self) -> None:
        """Initialize temporal query handler."""
        self.neo4j_client = get_neo4j_client()

        logger.info("Initialized TemporalMemoryQuery")

    async def ensure_temporal_indexes(self) -> None:
        """Create temporal indexes if not exist.

        Creates indexes on temporal properties for efficient querying.
        """
        if not settings.graph_temporal_index_enabled:
            logger.info("Temporal indexes disabled in settings")
            return

        try:
            await self.neo4j_client.create_temporal_indexes()
            logger.info("Temporal indexes ensured")
        except Exception as e:
            logger.warning("Failed to create temporal indexes", error=str(e))

    async def query_point_in_time(
        self,
        entity_name: str,
        valid_time: datetime,
        transaction_time: datetime | None = None,
    ) -> Dict[str, Any] | None:
        """Query entity state at a specific point in time.

        Args:
            entity_name: Entity name to query
            valid_time: Point in valid time (real-world time)
            transaction_time: Point in transaction time (default: now)

        Returns:
            Entity state at the specified time, or None if not found

        Raises:
            MemoryError: If query fails
        """
        try:
            transaction_time = transaction_time or datetime.now(timezone.utc)

            # Cypher query for bi-temporal point-in-time retrieval
            query = """
            MATCH (e:Entity {name: $entity_name})
            WHERE e.valid_from <= $valid_time
              AND (e.valid_to IS NULL OR e.valid_to > $valid_time)
              AND e.transaction_from <= $transaction_time
              AND (e.transaction_to IS NULL OR e.transaction_to > $transaction_time)
            RETURN e {
                .id,
                .name,
                .type,
                .properties,
                .valid_from,
                .valid_to,
                .transaction_from,
                .transaction_to,
                .version_number
            } AS entity
            ORDER BY e.version_number DESC
            LIMIT 1
            """

            results = await self.neo4j_client.execute_read(
                query,
                parameters={
                    "entity_name": entity_name,
                    "valid_time": valid_time.isoformat(),
                    "transaction_time": transaction_time.isoformat(),
                },
            )

            if not results:
                logger.debug(
                    "No entity found at point in time",
                    entity_name=entity_name,
                    valid_time=valid_time.isoformat(),
                )
                return None

            entity = results[0]["entity"]
            logger.info(
                "Retrieved entity at point in time",
                entity_name=entity_name,
                version=entity.get("version_number"),
            )

            return entity

        except Exception as e:
            logger.error(
                "Point-in-time query failed",
                entity_name=entity_name,
                error=str(e),
            )
            raise MemoryError(operation="Point-in-time query failed", reason=str(e)) from e

    async def query_time_range(
        self,
        entity_name: str,
        valid_start: datetime,
        valid_end: datetime,
        transaction_time: datetime | None = None,
    ) -> list[Dict[str, Any]]:
        """Query entity states over a time range.

        Returns all versions of the entity that were valid during
        the specified time range.

        Args:
            entity_name: Entity name to query
            valid_start: Start of valid time range
            valid_end: End of valid time range
            transaction_time: Transaction time to query at (default: now)

        Returns:
            List of entity states during the time range

        Raises:
            MemoryError: If query fails
        """
        try:
            transaction_time = transaction_time or datetime.now(timezone.utc)

            # Query for entities valid during any part of the range
            query = """
            MATCH (e:Entity {name: $entity_name})
            WHERE e.valid_from <= $valid_end
              AND (e.valid_to IS NULL OR e.valid_to >= $valid_start)
              AND e.transaction_from <= $transaction_time
              AND (e.transaction_to IS NULL OR e.transaction_to > $transaction_time)
            RETURN e {
                .id,
                .name,
                .type,
                .properties,
                .valid_from,
                .valid_to,
                .transaction_from,
                .transaction_to,
                .version_number
            } AS entity
            ORDER BY e.valid_from ASC, e.version_number DESC
            """

            results = await self.neo4j_client.execute_read(
                query,
                parameters={
                    "entity_name": entity_name,
                    "valid_start": valid_start.isoformat(),
                    "valid_end": valid_end.isoformat(),
                    "transaction_time": transaction_time.isoformat(),
                },
            )

            entities = [r["entity"] for r in results]

            logger.info(
                "Retrieved entities in time range",
                entity_name=entity_name,
                count=len(entities),
                valid_start=valid_start.isoformat(),
                valid_end=valid_end.isoformat(),
            )

            return entities

        except Exception as e:
            logger.error(
                "Time range query failed",
                entity_name=entity_name,
                error=str(e),
            )
            raise MemoryError(operation="Time range query failed", reason=str(e)) from e

    async def get_entity_history(
        self,
        entity_name: str,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """Get complete history of entity changes.

        Returns all versions of an entity ordered by transaction time.

        Args:
            entity_name: Entity name to query
            limit: Maximum number of versions to return (default: 100)

        Returns:
            List of entity versions with change metadata

        Raises:
            MemoryError: If query fails
        """
        try:
            query = """
            MATCH (e:Entity {name: $entity_name})
            RETURN e {
                .id,
                .name,
                .type,
                .properties,
                .valid_from,
                .valid_to,
                .transaction_from,
                .transaction_to,
                .version_number,
                .version_id
            } AS entity
            ORDER BY e.transaction_from DESC, e.version_number DESC
            LIMIT $limit
            """

            results = await self.neo4j_client.execute_read(
                query,
                parameters={
                    "entity_name": entity_name,
                    "limit": limit,
                },
            )

            history = []
            for r in results:
                entity = r["entity"]
                history.append(
                    {
                        "version_id": entity.get("version_id"),
                        "version_number": entity.get("version_number"),
                        "properties": entity.get("properties"),
                        "valid_from": entity.get("valid_from"),
                        "valid_to": entity.get("valid_to"),
                        "transaction_from": entity.get("transaction_from"),
                        "transaction_to": entity.get("transaction_to"),
                        "type": entity.get("type"),
                    }
                )

            logger.info(
                "Retrieved entity history",
                entity_name=entity_name,
                versions_count=len(history),
            )

            return history

        except Exception as e:
            logger.error(
                "Entity history query failed",
                entity_name=entity_name,
                error=str(e),
            )
            raise MemoryError(operation="Entity history query failed", reason=str(e)) from e

    async def query_entities_by_relationship(
        self,
        entity_name: str,
        relationship_type: str,
        valid_time: datetime | None = None,
        direction: str = "outgoing",
    ) -> list[Dict[str, Any]]:
        """Query entities connected by relationship at a point in time.

        Args:
            entity_name: Source entity name
            relationship_type: Type of relationship to traverse
            valid_time: Point in time to query (default: now)
            direction: Relationship direction ("outgoing", "incoming", "both")

        Returns:
            List of connected entities with relationship details

        Raises:
            MemoryError: If query fails
        """
        try:
            valid_time = valid_time or datetime.now(timezone.utc)

            # Build direction pattern
            if direction == "outgoing":
                pattern = "(e:Entity {name: $entity_name})-[r:$rel_type]->(target:Entity)"
            elif direction == "incoming":
                pattern = "(e:Entity {name: $entity_name})<-[r:$rel_type]-(target:Entity)"
            else:  # both
                pattern = "(e:Entity {name: $entity_name})-[r:$rel_type]-(target:Entity)"

            query = f"""
            MATCH {pattern}
            WHERE e.valid_from <= $valid_time
              AND (e.valid_to IS NULL OR e.valid_to > $valid_time)
              AND r.valid_from <= $valid_time
              AND (r.valid_to IS NULL OR r.valid_to > $valid_time)
              AND target.valid_from <= $valid_time
              AND (target.valid_to IS NULL OR target.valid_to > $valid_time)
            RETURN target {{
                .id,
                .name,
                .type,
                .properties
            }} AS entity,
            r {{
                .type,
                .properties,
                .valid_from,
                .valid_to
            }} AS relationship
            """

            results = await self.neo4j_client.execute_read(
                query,
                parameters={
                    "entity_name": entity_name,
                    "rel_type": relationship_type,
                    "valid_time": valid_time.isoformat(),
                },
            )

            connected_entities = [
                {
                    "entity": r["entity"],
                    "relationship": r["relationship"],
                }
                for r in results
            ]

            logger.info(
                "Retrieved connected entities",
                entity_name=entity_name,
                relationship_type=relationship_type,
                count=len(connected_entities),
            )

            return connected_entities

        except Exception as e:
            logger.error(
                "Relationship query failed",
                entity_name=entity_name,
                error=str(e),
            )
            raise MemoryError(operation="Relationship query failed", reason=str(e)) from e


# Global instance (singleton pattern)
_temporal_query: TemporalMemoryQuery | None = None


def get_temporal_query() -> TemporalMemoryQuery:
    """Get global temporal query instance (singleton).

    Returns:
        TemporalMemoryQuery instance
    """
    global _temporal_query
    if _temporal_query is None:
        _temporal_query = TemporalMemoryQuery()
    return _temporal_query
