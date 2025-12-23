"""Unit tests for AuditEvent model.

Sprint 63 Feature 63.2: Tests for audit event validation and serialization.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domains.knowledge_graph.audit.models import AuditEvent


class TestAuditEventModel:
    """Test AuditEvent Pydantic model."""

    def test_create_entity_created_event(self) -> None:
        """Test creating entity_created audit event."""
        event = AuditEvent(
            event_type="entity_created",
            entity_id="entity-123",
            entity_type="PERSON",
            new_properties={"name": "John Doe", "age": 30},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "entity_created"
        assert event.entity_id == "entity-123"
        assert event.entity_type == "PERSON"
        assert event.new_properties == {"name": "John Doe", "age": 30}
        assert event.old_properties is None
        assert event.namespace == "default"
        assert event.document_id == "doc-456"
        assert event.user_id == "system"
        assert isinstance(event.event_id, str)
        assert isinstance(event.timestamp, datetime)

    def test_create_entity_updated_event(self) -> None:
        """Test creating entity_updated audit event."""
        event = AuditEvent(
            event_type="entity_updated",
            entity_id="entity-123",
            entity_type="PERSON",
            old_properties={"name": "John"},
            new_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
            user_id="user-789",
        )

        assert event.event_type == "entity_updated"
        assert event.old_properties == {"name": "John"}
        assert event.new_properties == {"name": "John Doe"}
        assert event.user_id == "user-789"

    def test_create_entity_deleted_event(self) -> None:
        """Test creating entity_deleted audit event."""
        event = AuditEvent(
            event_type="entity_deleted",
            entity_id="entity-123",
            entity_type="PERSON",
            old_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "entity_deleted"
        assert event.old_properties == {"name": "John Doe"}
        assert event.new_properties is None

    def test_create_relationship_created_event(self) -> None:
        """Test creating relationship_created audit event."""
        event = AuditEvent(
            event_type="relationship_created",
            relationship_id="rel-789",
            relationship_type="WORKS_FOR",
            new_properties={"since": "2024-01-01"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "relationship_created"
        assert event.relationship_id == "rel-789"
        assert event.relationship_type == "WORKS_FOR"
        assert event.new_properties == {"since": "2024-01-01"}
        assert event.entity_id is None
        assert event.entity_type is None

    def test_create_relationship_deleted_event(self) -> None:
        """Test creating relationship_deleted audit event."""
        event = AuditEvent(
            event_type="relationship_deleted",
            relationship_id="rel-789",
            relationship_type="WORKS_FOR",
            old_properties={"since": "2024-01-01"},
            namespace="default",
            document_id="doc-456",
        )

        assert event.event_type == "relationship_deleted"
        assert event.old_properties == {"since": "2024-01-01"}

    def test_invalid_event_type(self) -> None:
        """Test that invalid event types raise validation error."""
        with pytest.raises(ValidationError):
            AuditEvent(
                event_type="invalid_type",  # type: ignore
                entity_id="entity-123",
                namespace="default",
                document_id="doc-456",
            )

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            AuditEvent(
                event_type="entity_created",
                entity_id="entity-123",
                # Missing namespace and document_id
            )  # type: ignore

    def test_to_neo4j_dict(self) -> None:
        """Test conversion to Neo4j node properties."""
        event = AuditEvent(
            event_type="entity_created",
            entity_id="entity-123",
            entity_type="PERSON",
            new_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
        )

        neo4j_dict = event.to_neo4j_dict()

        assert neo4j_dict["event_id"] == event.event_id
        assert neo4j_dict["event_type"] == "entity_created"
        assert neo4j_dict["entity_id"] == "entity-123"
        assert neo4j_dict["entity_type"] == "PERSON"
        assert neo4j_dict["namespace"] == "default"
        assert neo4j_dict["document_id"] == "doc-456"
        assert neo4j_dict["user_id"] == "system"
        assert isinstance(neo4j_dict["timestamp"], str)
        assert isinstance(neo4j_dict["new_properties"], str)

    def test_from_neo4j_record(self) -> None:
        """Test creating AuditEvent from Neo4j record."""
        record = {
            "event_id": "evt-123",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "entity_created",
            "entity_id": "entity-123",
            "entity_type": "PERSON",
            "relationship_id": None,
            "relationship_type": None,
            "old_properties": None,
            "new_properties": "{'name': 'John Doe'}",
            "namespace": "default",
            "document_id": "doc-456",
            "user_id": "system",
        }

        event = AuditEvent.from_neo4j_record(record)

        assert event.event_id == "evt-123"
        assert event.event_type == "entity_created"
        assert event.entity_id == "entity-123"
        assert event.entity_type == "PERSON"
        assert event.new_properties == {"name": "John Doe"}
        assert event.namespace == "default"
        assert event.document_id == "doc-456"
        assert isinstance(event.timestamp, datetime)

    def test_from_neo4j_record_with_complex_properties(self) -> None:
        """Test parsing complex property dictionaries from Neo4j."""
        record = {
            "event_id": "evt-123",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "entity_updated",
            "entity_id": "entity-123",
            "entity_type": "PERSON",
            "relationship_id": None,
            "relationship_type": None,
            "old_properties": "{'name': 'John', 'age': 29}",
            "new_properties": "{'name': 'John Doe', 'age': 30}",
            "namespace": "default",
            "document_id": "doc-456",
            "user_id": "user-789",
        }

        event = AuditEvent.from_neo4j_record(record)

        assert event.old_properties == {"name": "John", "age": 29}
        assert event.new_properties == {"name": "John Doe", "age": 30}
        assert event.user_id == "user-789"

    def test_from_neo4j_record_with_invalid_properties(self) -> None:
        """Test handling of invalid property strings from Neo4j."""
        record = {
            "event_id": "evt-123",
            "timestamp": "2024-01-01T12:00:00",
            "event_type": "entity_created",
            "entity_id": "entity-123",
            "entity_type": "PERSON",
            "relationship_id": None,
            "relationship_type": None,
            "old_properties": None,
            "new_properties": "invalid json",  # Invalid format
            "namespace": "default",
            "document_id": "doc-456",
            "user_id": "system",
        }

        event = AuditEvent.from_neo4j_record(record)

        # Should handle gracefully by setting to None
        assert event.new_properties is None

    def test_roundtrip_neo4j_conversion(self) -> None:
        """Test roundtrip conversion to/from Neo4j format."""
        original = AuditEvent(
            event_type="entity_updated",
            entity_id="entity-123",
            entity_type="PERSON",
            old_properties={"name": "John"},
            new_properties={"name": "John Doe"},
            namespace="default",
            document_id="doc-456",
        )

        # Convert to Neo4j dict
        neo4j_dict = original.to_neo4j_dict()

        # Convert back to AuditEvent
        restored = AuditEvent.from_neo4j_record(neo4j_dict)

        assert restored.event_id == original.event_id
        assert restored.event_type == original.event_type
        assert restored.entity_id == original.entity_id
        assert restored.entity_type == original.entity_type
        assert restored.old_properties == original.old_properties
        assert restored.new_properties == original.new_properties
        assert restored.namespace == original.namespace
        assert restored.document_id == original.document_id

    def test_property_types(self) -> None:
        """Test that various property types are supported."""
        event = AuditEvent(
            event_type="entity_created",
            entity_id="entity-123",
            entity_type="CONCEPT",
            new_properties={
                "name": "Test",
                "count": 42,
                "score": 0.95,
                "active": True,
                "optional": None,
            },
            namespace="default",
            document_id="doc-456",
        )

        assert event.new_properties["name"] == "Test"
        assert event.new_properties["count"] == 42
        assert event.new_properties["score"] == 0.95
        assert event.new_properties["active"] is True
        assert event.new_properties["optional"] is None
