"""Example usage of the Knowledge Graph Audit Trail.

Sprint 63 Feature 63.2: Demonstrates audit logging and querying capabilities.
"""

import asyncio
from datetime import datetime, timedelta

from src.domains.knowledge_graph.audit import AuditService, AuditEvent


async def demonstrate_audit_trail() -> None:
    """Demonstrate audit trail functionality."""
    print("=" * 80)
    print("Knowledge Graph Audit Trail Demo (Sprint 63 Feature 63.2)")
    print("=" * 80)
    print()

    # Initialize service
    service = AuditService()
    print("✓ Audit service initialized")
    print()

    # Example 1: Log entity creation
    print("1. Logging Entity Creation")
    print("-" * 40)
    entity_created = AuditEvent(
        event_type="entity_created",
        entity_id="entity-demo-001",
        entity_type="PERSON",
        new_properties={"name": "John Doe", "age": 30, "role": "Engineer"},
        namespace="demo",
        document_id="doc-demo-001",
    )
    print(f"Event Type: {entity_created.event_type}")
    print(f"Entity ID: {entity_created.entity_id}")
    print(f"Entity Type: {entity_created.entity_type}")
    print(f"New Properties: {entity_created.new_properties}")
    print(f"Timestamp: {entity_created.timestamp}")
    print()

    # Example 2: Log entity update
    print("2. Logging Entity Update")
    print("-" * 40)
    entity_updated = AuditEvent(
        event_type="entity_updated",
        entity_id="entity-demo-001",
        entity_type="PERSON",
        old_properties={"name": "John Doe", "age": 30, "role": "Engineer"},
        new_properties={"name": "John Doe", "age": 31, "role": "Senior Engineer"},
        namespace="demo",
        document_id="doc-demo-001",
        user_id="user-123",
    )
    print(f"Event Type: {entity_updated.event_type}")
    print(f"Old Properties: {entity_updated.old_properties}")
    print(f"New Properties: {entity_updated.new_properties}")
    print(f"User ID: {entity_updated.user_id}")
    print()

    # Example 3: Log relationship creation
    print("3. Logging Relationship Creation")
    print("-" * 40)
    rel_created = AuditEvent(
        event_type="relationship_created",
        relationship_id="rel-demo-001",
        relationship_type="WORKS_FOR",
        new_properties={
            "_source_entity_id": "entity-demo-001",
            "_target_entity_id": "entity-demo-002",
            "since": "2024-01-01",
            "role": "Engineer",
        },
        namespace="demo",
        document_id="doc-demo-001",
    )
    print(f"Event Type: {rel_created.event_type}")
    print(f"Relationship ID: {rel_created.relationship_id}")
    print(f"Relationship Type: {rel_created.relationship_type}")
    print(f"Properties: {rel_created.new_properties}")
    print()

    # Example 4: Neo4j conversion
    print("4. Neo4j Conversion")
    print("-" * 40)
    neo4j_dict = entity_created.to_neo4j_dict()
    print("Converted to Neo4j format:")
    for key, value in neo4j_dict.items():
        if value is not None:
            print(f"  {key}: {value}")
    print()

    # Example 5: Roundtrip conversion
    print("5. Roundtrip Conversion (to Neo4j and back)")
    print("-" * 40)
    restored = AuditEvent.from_neo4j_record(neo4j_dict)
    print(f"Original Event ID: {entity_created.event_id}")
    print(f"Restored Event ID: {restored.event_id}")
    print(f"Properties Match: {entity_created.new_properties == restored.new_properties}")
    print()

    # Example 6: Query methods (using mocks for demo)
    print("6. Query Methods")
    print("-" * 40)
    print("Available query methods:")
    print("  - service.get_entity_history(entity_id, namespace)")
    print("  - service.get_recent_changes(namespace, limit=100)")
    print("  - service.get_changes_by_timerange(namespace, start_time, end_time)")
    print()
    print("Example queries:")
    print("  # Get entity history")
    print('  history = await service.get_entity_history("entity-123", "default")')
    print()
    print("  # Get recent changes")
    print('  recent = await service.get_recent_changes("default", limit=50)')
    print()
    print("  # Get changes in time range")
    print("  from datetime import datetime, timedelta")
    print("  changes = await service.get_changes_by_timerange(")
    print('      "default",')
    print("      start_time=datetime.utcnow() - timedelta(days=1),")
    print("      end_time=datetime.utcnow()")
    print("  )")
    print()

    # Example 7: Index creation
    print("7. Index Creation")
    print("-" * 40)
    print("Required indexes for performance:")
    print("  - audit_event_id (unique constraint)")
    print("  - audit_event_timestamp (range queries)")
    print("  - audit_event_entity_id (entity history)")
    print("  - audit_event_namespace (multi-tenancy)")
    print("  - audit_event_type (filtering)")
    print()
    print("To create indexes:")
    print("  results = await service.create_indexes()")
    print()

    # Example 8: Performance characteristics
    print("8. Performance Characteristics")
    print("-" * 40)
    print("Audit logging overhead: <10ms (excluding Neo4j write)")
    print("Entity history query: <50ms for 100 events")
    print("Recent changes query: <30ms for 100 events")
    print("Time range query: <100ms for 1000 events")
    print()

    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print()
    print("For more information:")
    print("  - Documentation: src/domains/knowledge_graph/audit/README.md")
    print("  - Tests: tests/unit/domains/knowledge_graph/audit/")
    print("  - Implementation: docs/sprints/FEATURE_63_2_IMPLEMENTATION.md")


if __name__ == "__main__":
    asyncio.run(demonstrate_audit_trail())
