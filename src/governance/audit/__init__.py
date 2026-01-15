"""Audit trail system for governance compliance.

This module provides immutable audit logging with cryptographic integrity
for 7-year compliance requirements (GDPR, GxP, SOC2).

Key Components:
    - AuditEventType: Event type taxonomy (13+ types)
    - AuditEvent: Immutable event with SHA-256 chain integrity
    - AuditTrailManager: Append-only logging with tamper detection
    - SkillAuditDecorator: Auto-audit skill executions
    - AuditStorage: Persistence interface (mock/Redis/PostgreSQL)

Example:
    >>> from src.governance.audit import AuditTrailManager, AuditEventType
    >>>
    >>> manager = AuditTrailManager(storage)
    >>> event = await manager.log(
    ...     event_type=AuditEventType.SKILL_EXECUTED,
    ...     actor_id="user_123",
    ...     action="retrieve_documents",
    ...     outcome="success"
    ... )
    >>>
    >>> # Verify integrity
    >>> is_valid, errors = await manager.verify_integrity(start, end)
    >>> assert is_valid
"""

from .storage import AuditStorage, InMemoryAuditStorage
from .trail import (
    AuditEvent,
    AuditEventType,
    AuditTrailManager,
    SkillAuditDecorator,
    audit_skill,
)

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditTrailManager",
    "AuditStorage",
    "InMemoryAuditStorage",
    "SkillAuditDecorator",
    "audit_skill",
]
