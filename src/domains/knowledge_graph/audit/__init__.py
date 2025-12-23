"""Knowledge Graph Audit Trail Module.

Sprint 63 Feature 63.2: Basic Temporal Audit Trail
This module provides auditing capabilities for tracking changes to entities
and relationships in Neo4j over time.

Capabilities:
- Track entity creation, update, deletion events
- Track relationship creation and deletion events
- Query entity change history
- Query changes within time ranges
- Automatic event logging with minimal overhead (<10ms)

Usage:
    from src.domains.knowledge_graph.audit import AuditService, AuditEvent

    service = AuditService()
    await service.log_entity_change(
        event_type="entity_created",
        entity_id="entity-123",
        entity_type="PERSON",
        new_properties={"name": "John Doe"},
        namespace="default",
        document_id="doc-456"
    )
"""

from src.domains.knowledge_graph.audit.audit_service import AuditService, get_audit_service
from src.domains.knowledge_graph.audit.models import AuditEvent

__all__ = [
    "AuditService",
    "AuditEvent",
    "get_audit_service",
]
