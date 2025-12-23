"""Audit Event Models.

Sprint 63 Feature 63.2: Pydantic models for audit trail events.
"""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Audit event for tracking changes to entities and relationships.

    This model tracks all modifications to the knowledge graph, including:
    - Entity creation, updates, and deletion
    - Relationship creation and deletion
    - Property changes with old/new values

    The audit trail enables:
    - Debugging graph changes
    - Analyzing entity evolution
    - Provenance tracking
    - Rollback capabilities (future)

    Example:
        >>> event = AuditEvent(
        ...     event_type="entity_created",
        ...     entity_id="entity-123",
        ...     entity_type="PERSON",
        ...     new_properties={"name": "John Doe"},
        ...     namespace="default",
        ...     document_id="doc-456"
        ... )
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event ID",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp (UTC)",
    )
    event_type: Literal[
        "entity_created",
        "entity_updated",
        "entity_deleted",
        "relationship_created",
        "relationship_deleted",
    ] = Field(..., description="Type of audit event")

    # Entity-related fields (for entity events)
    entity_id: str | None = Field(
        None,
        description="Entity ID affected by this event",
    )
    entity_type: str | None = Field(
        None,
        description="Entity type (PERSON, ORG, CONCEPT, etc.)",
    )

    # Relationship-related fields (for relationship events)
    relationship_id: str | None = Field(
        None,
        description="Relationship ID affected by this event",
    )
    relationship_type: str | None = Field(
        None,
        description="Relationship type (RELATES_TO, WORKS_FOR, etc.)",
    )

    # Property changes
    old_properties: dict[str, str | int | float | bool | None] | None = Field(
        None,
        description="Properties before the change (for updates/deletes)",
    )
    new_properties: dict[str, str | int | float | bool | None] | None = Field(
        None,
        description="Properties after the change (for creates/updates)",
    )

    # Context
    namespace: str = Field(..., description="Namespace for multi-tenancy")
    document_id: str = Field(..., description="Source document ID")
    user_id: str = Field(
        default="system",
        description="User/system that triggered this event",
    )

    def to_neo4j_dict(self) -> dict[str, str | int | float | bool | None]:
        """Convert to Neo4j node properties.

        Returns:
            Dictionary suitable for creating AuditEvent nodes in Neo4j

        Example:
            >>> event = AuditEvent(...)
            >>> props = event.to_neo4j_dict()
            >>> # Use in Cypher: CREATE (e:AuditEvent $props)
        """
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "relationship_id": self.relationship_id,
            "relationship_type": self.relationship_type,
            # Store as JSON strings for complex types
            "old_properties": (
                str(self.old_properties) if self.old_properties is not None else None
            ),
            "new_properties": (
                str(self.new_properties) if self.new_properties is not None else None
            ),
            "namespace": self.namespace,
            "document_id": self.document_id,
            "user_id": self.user_id,
        }

    @classmethod
    def from_neo4j_record(cls, record: dict[str, str | int | float | bool | None]) -> "AuditEvent":
        """Create AuditEvent from Neo4j record.

        Args:
            record: Neo4j record dictionary

        Returns:
            AuditEvent instance

        Example:
            >>> records = await neo4j_client.execute_read(query)
            >>> events = [AuditEvent.from_neo4j_record(r) for r in records]
        """
        import ast

        # Parse JSON strings back to dicts
        old_props = None
        if record.get("old_properties"):
            try:
                old_props = ast.literal_eval(str(record["old_properties"]))
            except (ValueError, SyntaxError):
                old_props = None

        new_props = None
        if record.get("new_properties"):
            try:
                new_props = ast.literal_eval(str(record["new_properties"]))
            except (ValueError, SyntaxError):
                new_props = None

        # Parse timestamp
        timestamp = record.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            event_id=str(record["event_id"]),
            timestamp=timestamp,
            event_type=str(record["event_type"]),
            entity_id=record.get("entity_id"),
            entity_type=record.get("entity_type"),
            relationship_id=record.get("relationship_id"),
            relationship_type=record.get("relationship_type"),
            old_properties=old_props,
            new_properties=new_props,
            namespace=str(record["namespace"]),
            document_id=str(record["document_id"]),
            user_id=str(record.get("user_id", "system")),
        )


__all__ = ["AuditEvent"]
