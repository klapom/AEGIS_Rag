"""Audit Service for Knowledge Graph Changes.

Sprint 63 Feature 63.2: Service for logging and querying audit events.
"""

import time
from datetime import datetime
from typing import Literal

import structlog

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.core.exceptions import GraphQueryError
from src.domains.knowledge_graph.audit.models import AuditEvent

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for tracking changes to entities and relationships in Neo4j.

    This service provides:
    - Automatic audit logging for entity/relationship changes
    - Query capabilities for change history
    - Time-range filtering for debugging
    - Performance: <10ms overhead for audit logging

    Example:
        >>> service = AuditService()
        >>> await service.log_entity_change(
        ...     event_type="entity_created",
        ...     entity_id="entity-123",
        ...     entity_type="PERSON",
        ...     new_properties={"name": "John Doe"},
        ...     namespace="default",
        ...     document_id="doc-456"
        ... )
        >>> history = await service.get_entity_history("entity-123", "default")
    """

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        """Initialize audit service.

        Args:
            neo4j_client: Neo4j client instance (uses singleton if None)
        """
        self.neo4j_client = neo4j_client or get_neo4j_client()
        logger.info("audit_service_initialized")

    async def log_entity_change(
        self,
        event_type: Literal["entity_created", "entity_updated", "entity_deleted"],
        entity_id: str,
        entity_type: str,
        namespace: str,
        document_id: str,
        old_properties: dict[str, str | int | float | bool | None] | None = None,
        new_properties: dict[str, str | int | float | bool | None] | None = None,
        user_id: str = "system",
    ) -> AuditEvent:
        """Log an entity change event.

        Args:
            event_type: Type of change (created/updated/deleted)
            entity_id: Entity ID affected
            entity_type: Entity type (PERSON, ORG, CONCEPT, etc.)
            namespace: Namespace for multi-tenancy
            document_id: Source document ID
            old_properties: Properties before change (for updates/deletes)
            new_properties: Properties after change (for creates/updates)
            user_id: User/system that triggered the event

        Returns:
            Created AuditEvent instance

        Raises:
            GraphQueryError: If audit logging fails

        Example:
            >>> event = await service.log_entity_change(
            ...     event_type="entity_updated",
            ...     entity_id="entity-123",
            ...     entity_type="PERSON",
            ...     old_properties={"name": "John"},
            ...     new_properties={"name": "John Doe"},
            ...     namespace="default",
            ...     document_id="doc-456"
            ... )
        """
        start_time = time.perf_counter()

        # Create audit event
        event = AuditEvent(
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type,
            old_properties=old_properties,
            new_properties=new_properties,
            namespace=namespace,
            document_id=document_id,
            user_id=user_id,
        )

        # Store in Neo4j
        try:
            cypher = """
            CREATE (e:AuditEvent {
                event_id: $event_id,
                timestamp: datetime($timestamp),
                event_type: $event_type,
                entity_id: $entity_id,
                entity_type: $entity_type,
                old_properties: $old_properties,
                new_properties: $new_properties,
                namespace: $namespace,
                document_id: $document_id,
                user_id: $user_id
            })
            // Link to entity if it exists
            WITH e
            OPTIONAL MATCH (entity:base {id: $entity_id})
            FOREACH (_ IN CASE WHEN entity IS NOT NULL THEN [1] ELSE [] END |
                MERGE (e)-[:AUDITS_ENTITY]->(entity)
            )
            RETURN e.event_id as event_id
            """

            params = event.to_neo4j_dict()
            await self.neo4j_client.execute_write(cypher, params)

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "entity_change_logged",
                event_type=event_type,
                entity_id=entity_id,
                entity_type=entity_type,
                namespace=namespace,
                event_id=event.event_id,
                duration_ms=round(duration_ms, 2),
            )

            return event

        except Exception as e:
            logger.error(
                "entity_change_logging_failed",
                event_type=event_type,
                entity_id=entity_id,
                error=str(e),
            )
            raise GraphQueryError(
                query=f"log_entity_change({entity_id})",
                reason=str(e),
            ) from e

    async def log_relationship_change(
        self,
        event_type: Literal["relationship_created", "relationship_deleted"],
        relationship_id: str,
        relationship_type: str,
        namespace: str,
        document_id: str,
        source_entity_id: str | None = None,
        target_entity_id: str | None = None,
        old_properties: dict[str, str | int | float | bool | None] | None = None,
        new_properties: dict[str, str | int | float | bool | None] | None = None,
        user_id: str = "system",
    ) -> AuditEvent:
        """Log a relationship change event.

        Args:
            event_type: Type of change (created/deleted)
            relationship_id: Relationship ID affected
            relationship_type: Relationship type (RELATES_TO, WORKS_FOR, etc.)
            namespace: Namespace for multi-tenancy
            document_id: Source document ID
            source_entity_id: Source entity ID (optional, for linking)
            target_entity_id: Target entity ID (optional, for linking)
            old_properties: Properties before change (for deletes)
            new_properties: Properties after change (for creates)
            user_id: User/system that triggered the event

        Returns:
            Created AuditEvent instance

        Raises:
            GraphQueryError: If audit logging fails

        Example:
            >>> event = await service.log_relationship_change(
            ...     event_type="relationship_created",
            ...     relationship_id="rel-789",
            ...     relationship_type="WORKS_FOR",
            ...     source_entity_id="entity-123",
            ...     target_entity_id="entity-456",
            ...     new_properties={"since": "2024-01-01"},
            ...     namespace="default",
            ...     document_id="doc-456"
            ... )
        """
        start_time = time.perf_counter()

        # Store source/target in properties for reference
        props = new_properties or {}
        if source_entity_id:
            props["_source_entity_id"] = source_entity_id
        if target_entity_id:
            props["_target_entity_id"] = target_entity_id

        # Create audit event
        event = AuditEvent(
            event_type=event_type,
            relationship_id=relationship_id,
            relationship_type=relationship_type,
            old_properties=old_properties,
            new_properties=props,
            namespace=namespace,
            document_id=document_id,
            user_id=user_id,
        )

        # Store in Neo4j
        try:
            cypher = """
            CREATE (e:AuditEvent {
                event_id: $event_id,
                timestamp: datetime($timestamp),
                event_type: $event_type,
                relationship_id: $relationship_id,
                relationship_type: $relationship_type,
                old_properties: $old_properties,
                new_properties: $new_properties,
                namespace: $namespace,
                document_id: $document_id,
                user_id: $user_id
            })
            RETURN e.event_id as event_id
            """

            params = event.to_neo4j_dict()
            await self.neo4j_client.execute_write(cypher, params)

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "relationship_change_logged",
                event_type=event_type,
                relationship_id=relationship_id,
                relationship_type=relationship_type,
                namespace=namespace,
                event_id=event.event_id,
                duration_ms=round(duration_ms, 2),
            )

            return event

        except Exception as e:
            logger.error(
                "relationship_change_logging_failed",
                event_type=event_type,
                relationship_id=relationship_id,
                error=str(e),
            )
            raise GraphQueryError(
                query=f"log_relationship_change({relationship_id})",
                reason=str(e),
            ) from e

    async def get_entity_history(
        self,
        entity_id: str,
        namespace: str,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get change history for a specific entity.

        Args:
            entity_id: Entity ID to query
            namespace: Namespace filter
            limit: Maximum number of events to return (default: 100)

        Returns:
            List of AuditEvent instances, ordered by timestamp (newest first)

        Raises:
            GraphQueryError: If query fails

        Example:
            >>> history = await service.get_entity_history("entity-123", "default")
            >>> for event in history:
            ...     print(f"{event.timestamp}: {event.event_type}")
        """
        start_time = time.perf_counter()

        try:
            cypher = """
            MATCH (e:AuditEvent)
            WHERE e.entity_id = $entity_id
              AND e.namespace = $namespace
            RETURN e.event_id as event_id,
                   e.timestamp as timestamp,
                   e.event_type as event_type,
                   e.entity_id as entity_id,
                   e.entity_type as entity_type,
                   e.old_properties as old_properties,
                   e.new_properties as new_properties,
                   e.namespace as namespace,
                   e.document_id as document_id,
                   e.user_id as user_id
            ORDER BY e.timestamp DESC
            LIMIT $limit
            """

            records = await self.neo4j_client.execute_read(
                cypher,
                {
                    "entity_id": entity_id,
                    "namespace": namespace,
                    "limit": limit,
                },
            )

            events = [AuditEvent.from_neo4j_record(record) for record in records]

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "entity_history_retrieved",
                entity_id=entity_id,
                namespace=namespace,
                events_found=len(events),
                duration_ms=round(duration_ms, 2),
            )

            return events

        except Exception as e:
            logger.error(
                "entity_history_query_failed",
                entity_id=entity_id,
                error=str(e),
            )
            raise GraphQueryError(
                query=f"get_entity_history({entity_id})",
                reason=str(e),
            ) from e

    async def get_recent_changes(
        self,
        namespace: str,
        limit: int = 100,
        event_type: str | None = None,
    ) -> list[AuditEvent]:
        """Get recent changes across all entities/relationships.

        Args:
            namespace: Namespace filter
            limit: Maximum number of events to return (default: 100)
            event_type: Optional filter by event type

        Returns:
            List of AuditEvent instances, ordered by timestamp (newest first)

        Raises:
            GraphQueryError: If query fails

        Example:
            >>> recent = await service.get_recent_changes("default", limit=50)
            >>> entity_creates = await service.get_recent_changes(
            ...     "default",
            ...     event_type="entity_created"
            ... )
        """
        start_time = time.perf_counter()

        try:
            cypher = """
            MATCH (e:AuditEvent)
            WHERE e.namespace = $namespace
            """

            params: dict[str, str | int] = {"namespace": namespace, "limit": limit}

            if event_type:
                cypher += " AND e.event_type = $event_type"
                params["event_type"] = event_type

            cypher += """
            RETURN e.event_id as event_id,
                   e.timestamp as timestamp,
                   e.event_type as event_type,
                   e.entity_id as entity_id,
                   e.entity_type as entity_type,
                   e.relationship_id as relationship_id,
                   e.relationship_type as relationship_type,
                   e.old_properties as old_properties,
                   e.new_properties as new_properties,
                   e.namespace as namespace,
                   e.document_id as document_id,
                   e.user_id as user_id
            ORDER BY e.timestamp DESC
            LIMIT $limit
            """

            records = await self.neo4j_client.execute_read(cypher, params)

            events = [AuditEvent.from_neo4j_record(record) for record in records]

            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "recent_changes_retrieved",
                namespace=namespace,
                event_type=event_type,
                events_found=len(events),
                duration_ms=round(duration_ms, 2),
            )

            return events

        except Exception as e:
            logger.error(
                "recent_changes_query_failed",
                namespace=namespace,
                error=str(e),
            )
            raise GraphQueryError(
                query=f"get_recent_changes({namespace})",
                reason=str(e),
            ) from e

    async def get_changes_by_timerange(
        self,
        namespace: str,
        start_time: datetime,
        end_time: datetime,
        event_type: str | None = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """Get changes within a specific time range.

        Args:
            namespace: Namespace filter
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            event_type: Optional filter by event type
            limit: Maximum number of events to return (default: 1000)

        Returns:
            List of AuditEvent instances, ordered by timestamp (newest first)

        Raises:
            GraphQueryError: If query fails

        Example:
            >>> from datetime import datetime, timedelta
            >>> now = datetime.utcnow()
            >>> yesterday = now - timedelta(days=1)
            >>> changes = await service.get_changes_by_timerange(
            ...     "default",
            ...     start_time=yesterday,
            ...     end_time=now
            ... )
        """
        start_query = time.perf_counter()

        try:
            cypher = """
            MATCH (e:AuditEvent)
            WHERE e.namespace = $namespace
              AND datetime(e.timestamp) >= datetime($start_time)
              AND datetime(e.timestamp) <= datetime($end_time)
            """

            params: dict[str, str | int] = {
                "namespace": namespace,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": limit,
            }

            if event_type:
                cypher += " AND e.event_type = $event_type"
                params["event_type"] = event_type

            cypher += """
            RETURN e.event_id as event_id,
                   e.timestamp as timestamp,
                   e.event_type as event_type,
                   e.entity_id as entity_id,
                   e.entity_type as entity_type,
                   e.relationship_id as relationship_id,
                   e.relationship_type as relationship_type,
                   e.old_properties as old_properties,
                   e.new_properties as new_properties,
                   e.namespace as namespace,
                   e.document_id as document_id,
                   e.user_id as user_id
            ORDER BY e.timestamp DESC
            LIMIT $limit
            """

            records = await self.neo4j_client.execute_read(cypher, params)

            events = [AuditEvent.from_neo4j_record(record) for record in records]

            duration_ms = (time.perf_counter() - start_query) * 1000

            logger.info(
                "timerange_changes_retrieved",
                namespace=namespace,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                event_type=event_type,
                events_found=len(events),
                duration_ms=round(duration_ms, 2),
            )

            return events

        except Exception as e:
            logger.error(
                "timerange_changes_query_failed",
                namespace=namespace,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                error=str(e),
            )
            raise GraphQueryError(
                query=f"get_changes_by_timerange({namespace}, {start_time}, {end_time})",
                reason=str(e),
            ) from e

    async def create_indexes(self) -> dict[str, bool]:
        """Create Neo4j indexes for audit queries.

        Creates indexes on:
        - event_id (unique constraint)
        - timestamp (range queries)
        - entity_id (entity history)
        - namespace (multi-tenancy)
        - event_type (filtering)

        Returns:
            Dictionary with index creation status

        Raises:
            GraphQueryError: If index creation fails

        Example:
            >>> service = AuditService()
            >>> results = await service.create_indexes()
            >>> results["audit_event_timestamp"]
            True
        """
        indexes = {
            "audit_event_id": "CREATE CONSTRAINT audit_event_id IF NOT EXISTS FOR (e:AuditEvent) REQUIRE e.event_id IS UNIQUE",
            "audit_event_timestamp": "CREATE INDEX audit_event_timestamp IF NOT EXISTS FOR (e:AuditEvent) ON (e.timestamp)",
            "audit_event_entity_id": "CREATE INDEX audit_event_entity_id IF NOT EXISTS FOR (e:AuditEvent) ON (e.entity_id)",
            "audit_event_namespace": "CREATE INDEX audit_event_namespace IF NOT EXISTS FOR (e:AuditEvent) ON (e.namespace)",
            "audit_event_type": "CREATE INDEX audit_event_type IF NOT EXISTS FOR (e:AuditEvent) ON (e.event_type)",
        }

        results = {}
        for index_name, query in indexes.items():
            try:
                await self.neo4j_client.execute_write(query)
                results[index_name] = True
                logger.info("created_audit_index", index_name=index_name)
            except Exception as e:
                logger.warning(
                    "failed_to_create_audit_index",
                    index_name=index_name,
                    error=str(e),
                )
                results[index_name] = False

        return results


# Singleton instance
_audit_service: AuditService | None = None


def get_audit_service(neo4j_client: Neo4jClient | None = None) -> AuditService:
    """Get audit service instance (singleton).

    Args:
        neo4j_client: Optional Neo4j client (uses singleton if None)

    Returns:
        AuditService instance
    """
    global _audit_service

    if _audit_service is None:
        _audit_service = AuditService(neo4j_client)

    return _audit_service


def reset_audit_service() -> None:
    """Reset singleton (for testing)."""
    global _audit_service
    _audit_service = None


__all__ = ["AuditService", "get_audit_service", "reset_audit_service"]
