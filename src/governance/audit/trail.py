"""Immutable audit trail with cryptographic integrity.

Core Components:
    - AuditEventType: Event taxonomy (13+ types)
    - AuditEvent: Immutable event with SHA-256 chain
    - AuditTrailManager: Append-only logging with tamper detection
    - SkillAuditDecorator: Auto-audit skill executions

Integrity:
    - SHA-256 hash chain (blockchain-inspired)
    - Each event links to previous event's hash
    - Tamper detection via chain verification
    - Supports compliance audits (GDPR Art. 30, SOC2)

Example:
    >>> manager = AuditTrailManager(storage)
    >>>
    >>> # Log skill execution
    >>> event = await manager.log(
    ...     event_type=AuditEventType.SKILL_EXECUTED,
    ...     actor_id="claude_agent",
    ...     action="retrieve_documents",
    ...     outcome="success",
    ...     metadata={"skill_id": "rag-001", "duration_ms": 120}
    ... )
    >>>
    >>> # Verify integrity
    >>> is_valid, errors = await manager.verify_integrity()
    >>> assert is_valid
"""

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Taxonomy of audit event types.

    Categories:
        - Skill lifecycle: loaded, executed, failed, updated, deleted
        - Data access: read, write, delete, exported
        - Decisions: routed, rejected, approved
        - Security: auth success/failure, policy violation
        - System: config changed
    """

    # Skill lifecycle
    SKILL_LOADED = "skill.loaded"
    SKILL_EXECUTED = "skill.executed"
    SKILL_FAILED = "skill.failed"
    SKILL_UPDATED = "skill.updated"
    SKILL_DELETED = "skill.deleted"

    # Data access
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    DATA_DELETE = "data.delete"
    DATA_EXPORTED = "data.exported"

    # Decisions
    DECISION_ROUTED = "decision.routed"
    DECISION_REJECTED = "decision.rejected"
    DECISION_APPROVED = "decision.approved"

    # Security
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    POLICY_VIOLATION = "policy.violation"

    # System
    CONFIG_CHANGED = "config.changed"


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event with cryptographic integrity.

    Attributes:
        id: Unique event ID (UUID)
        timestamp: Event timestamp (UTC)
        event_type: Event type from taxonomy
        actor_id: Actor identifier (user, agent, system)
        actor_type: Actor type (human, agent, system)
        action: Human-readable action description
        outcome: Outcome (success, failure, pending)
        metadata: Additional context (skill ID, duration, etc.)
        context_hash: SHA-256 hash of input context
        output_hash: SHA-256 hash of output data
        previous_hash: Hash of previous event (chain integrity)
        event_hash: SHA-256 hash of this event

    Integrity:
        - event_hash = SHA-256(id + timestamp + event_type + ... + previous_hash)
        - Chain integrity verified by recomputing hashes
    """

    id: str
    timestamp: datetime
    event_type: AuditEventType
    actor_id: str
    actor_type: str  # "human", "agent", "system"
    action: str
    outcome: str  # "success", "failure", "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    context_hash: Optional[str] = None
    output_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    event_hash: str = ""

    def __post_init__(self):
        """Compute event hash after initialization."""
        if not self.event_hash:
            # Use object.__setattr__ for frozen dataclass
            object.__setattr__(self, "event_hash", self.compute_hash())

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of event for chain integrity.

        Hash includes:
            - All fields except event_hash itself
            - Deterministic JSON serialization
            - UTF-8 encoding

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Prepare data for hashing (exclude event_hash)
        hash_data = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "action": self.action,
            "outcome": self.outcome,
            "metadata": self.metadata,
            "context_hash": self.context_hash,
            "output_hash": self.output_hash,
            "previous_hash": self.previous_hash,
        }

        # Deterministic JSON serialization
        json_str = json.dumps(hash_data, sort_keys=True, default=str)

        # SHA-256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def verify_hash(self) -> bool:
        """Verify event hash matches computed hash.

        Returns:
            True if hash is valid
        """
        return self.event_hash == self.compute_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """Create event from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AuditEvent instance
        """
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["event_type"] = AuditEventType(data["event_type"])
        return cls(**data)


class AuditTrailManager:
    """Audit trail manager with cryptographic integrity.

    Features:
        - Append-only logging
        - SHA-256 hash chain
        - Tamper detection
        - Compliance reporting (GDPR Art. 30, SOC2)
        - 7-year retention

    Attributes:
        storage: Audit storage backend
        retention_days: Retention period (default: 2555 = 7 years)
    """

    def __init__(
        self,
        storage: "AuditStorage",  # type: ignore
        retention_days: int = 365 * 7,
    ):
        """Initialize audit trail manager.

        Args:
            storage: Audit storage backend
            retention_days: Retention period (default: 7 years)
        """
        self.storage = storage
        self.retention_days = retention_days
        self._last_hash: Optional[str] = None

    async def log(
        self,
        event_type: AuditEventType,
        actor_id: str,
        action: str,
        outcome: str,
        actor_type: str = "agent",
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Any] = None,
        output: Optional[Any] = None,
    ) -> AuditEvent:
        """Log audit event with cryptographic integrity.

        Args:
            event_type: Event type from taxonomy
            actor_id: Actor identifier
            action: Human-readable action description
            outcome: Outcome (success, failure, pending)
            actor_type: Actor type (human, agent, system)
            metadata: Additional context
            context: Input context (hashed)
            output: Output data (hashed)

        Returns:
            Created audit event

        Example:
            >>> event = await manager.log(
            ...     event_type=AuditEventType.SKILL_EXECUTED,
            ...     actor_id="claude",
            ...     action="retrieve_documents",
            ...     outcome="success",
            ...     metadata={"skill_id": "rag-001", "duration_ms": 120}
            ... )
        """
        # Get previous hash for chain
        if self._last_hash is None:
            last_event = await self.storage.get_last_event()
            self._last_hash = last_event.event_hash if last_event else None

        # Hash context and output
        context_hash = self._hash_data(context) if context else None
        output_hash = self._hash_data(output) if output else None

        # Create event
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            outcome=outcome,
            metadata=metadata or {},
            context_hash=context_hash,
            output_hash=output_hash,
            previous_hash=self._last_hash,
        )

        # Append to storage
        await self.storage.append(event)

        # Update last hash
        self._last_hash = event.event_hash

        logger.info(
            f"Audit event logged: {event_type.value} | "
            f"actor={actor_id} | outcome={outcome} | id={event.id}"
        )

        return event

    async def verify_integrity(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[bool, List[str]]:
        """Verify cryptographic integrity of audit trail.

        Checks:
            - Each event's hash matches computed hash
            - Each event's previous_hash matches prior event's hash
            - No gaps in chain

        Args:
            start_time: Verification start time (optional)
            end_time: Verification end time (optional)

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            >>> is_valid, errors = await manager.verify_integrity()
            >>> if not is_valid:
            ...     logger.error(f"Integrity violations: {errors}")
        """
        errors: List[str] = []

        # Query events
        events = await self.storage.query(
            start_time=start_time,
            end_time=end_time,
            limit=100000,  # Large limit for integrity check
        )

        if not events:
            return True, []

        # Verify each event's hash
        for event in events:
            if not event.verify_hash():
                errors.append(
                    f"Event {event.id} has invalid hash: "
                    f"expected={event.compute_hash()}, actual={event.event_hash}"
                )

        # Verify chain integrity
        for i in range(1, len(events)):
            prev_event = events[i - 1]
            curr_event = events[i]

            if curr_event.previous_hash != prev_event.event_hash:
                errors.append(
                    f"Chain break at event {curr_event.id}: "
                    f"previous_hash={curr_event.previous_hash} != "
                    f"prior_event_hash={prev_event.event_hash}"
                )

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(
                f"Audit trail integrity verified: {len(events)} events, "
                f"time_range={start_time} to {end_time}"
            )
        else:
            logger.error(
                f"Audit trail integrity VIOLATED: {len(errors)} errors, "
                f"{len(events)} events checked"
            )

        return is_valid, errors

    async def generate_compliance_report(
        self,
        report_type: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """Generate compliance report for auditors.

        Report Types:
            - "gdpr_art30": GDPR Article 30 processing activities log
            - "security": Security events (auth, violations)
            - "skill_usage": Skill execution audit trail
            - "data_access": Data read/write/delete events

        Args:
            report_type: Report type identifier
            start_time: Report start time
            end_time: Report end time

        Returns:
            Compliance report dictionary

        Example:
            >>> report = await manager.generate_compliance_report(
            ...     report_type="gdpr_art30",
            ...     start_time=datetime(2025, 1, 1),
            ...     end_time=datetime(2025, 12, 31)
            ... )
        """
        # Query all events in time range
        all_events = await self.storage.query(
            start_time=start_time,
            end_time=end_time,
            limit=100000,
        )

        # Verify integrity first
        is_valid, errors = await self.verify_integrity(start_time, end_time)

        report: Dict[str, Any] = {
            "report_type": report_type,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "total_events": len(all_events),
            "integrity_verified": is_valid,
            "integrity_errors": errors,
        }

        if report_type == "gdpr_art30":
            # GDPR Article 30: Processing activities
            data_events = [
                e for e in all_events
                if e.event_type in [
                    AuditEventType.DATA_READ,
                    AuditEventType.DATA_WRITE,
                    AuditEventType.DATA_DELETE,
                    AuditEventType.DATA_EXPORTED,
                ]
            ]

            report["processing_activities"] = {
                "total": len(data_events),
                "by_type": self._count_by_event_type(data_events),
                "by_actor": self._count_by_actor(data_events),
                "events": [e.to_dict() for e in data_events],
            }

        elif report_type == "security":
            # Security events
            security_events = [
                e for e in all_events
                if e.event_type in [
                    AuditEventType.AUTH_SUCCESS,
                    AuditEventType.AUTH_FAILURE,
                    AuditEventType.POLICY_VIOLATION,
                ]
            ]

            report["security_summary"] = {
                "total": len(security_events),
                "by_type": self._count_by_event_type(security_events),
                "failed_auth": len([
                    e for e in security_events
                    if e.event_type == AuditEventType.AUTH_FAILURE
                ]),
                "violations": len([
                    e for e in security_events
                    if e.event_type == AuditEventType.POLICY_VIOLATION
                ]),
                "events": [e.to_dict() for e in security_events],
            }

        elif report_type == "skill_usage":
            # Skill execution audit
            skill_events = [
                e for e in all_events
                if e.event_type in [
                    AuditEventType.SKILL_LOADED,
                    AuditEventType.SKILL_EXECUTED,
                    AuditEventType.SKILL_FAILED,
                ]
            ]

            report["skill_usage"] = {
                "total_executions": len([
                    e for e in skill_events
                    if e.event_type == AuditEventType.SKILL_EXECUTED
                ]),
                "failures": len([
                    e for e in skill_events
                    if e.event_type == AuditEventType.SKILL_FAILED
                ]),
                "by_skill": self._count_by_metadata_key(skill_events, "skill_id"),
                "by_actor": self._count_by_actor(skill_events),
                "events": [e.to_dict() for e in skill_events],
            }

        elif report_type == "data_access":
            # Data access audit
            data_events = [
                e for e in all_events
                if e.event_type in [
                    AuditEventType.DATA_READ,
                    AuditEventType.DATA_WRITE,
                    AuditEventType.DATA_DELETE,
                ]
            ]

            report["data_access"] = {
                "total": len(data_events),
                "reads": len([e for e in data_events if e.event_type == AuditEventType.DATA_READ]),
                "writes": len([e for e in data_events if e.event_type == AuditEventType.DATA_WRITE]),
                "deletes": len([e for e in data_events if e.event_type == AuditEventType.DATA_DELETE]),
                "by_actor": self._count_by_actor(data_events),
                "events": [e.to_dict() for e in data_events],
            }

        else:
            report["error"] = f"Unknown report type: {report_type}"

        logger.info(
            f"Compliance report generated: {report_type} | "
            f"events={len(all_events)} | time_range={start_time} to {end_time}"
        )

        return report

    async def purge_old_events(self) -> int:
        """Purge events older than retention period.

        Returns:
            Number of events purged
        """
        count = await self.storage.purge_old_events(self.retention_days)

        logger.info(
            f"Purged {count} audit events older than {self.retention_days} days"
        )

        return count

    def _hash_data(self, data: Any) -> str:
        """Hash arbitrary data with SHA-256.

        Args:
            data: Data to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _count_by_event_type(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Count events by type.

        Args:
            events: List of events

        Returns:
            Dictionary of event_type -> count
        """
        counts: Dict[str, int] = {}
        for event in events:
            key = event.event_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_actor(self, events: List[AuditEvent]) -> Dict[str, int]:
        """Count events by actor.

        Args:
            events: List of events

        Returns:
            Dictionary of actor_id -> count
        """
        counts: Dict[str, int] = {}
        for event in events:
            key = event.actor_id
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _count_by_metadata_key(
        self,
        events: List[AuditEvent],
        key: str,
    ) -> Dict[str, int]:
        """Count events by metadata key.

        Args:
            events: List of events
            key: Metadata key to count

        Returns:
            Dictionary of key_value -> count
        """
        counts: Dict[str, int] = {}
        for event in events:
            value = event.metadata.get(key)
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts


class SkillAuditDecorator:
    """Decorator for auto-auditing skill executions.

    Automatically logs:
        - Skill loaded (first call)
        - Skill executed (each call)
        - Skill failed (on exception)

    Example:
        >>> @audit_skill(manager, skill_id="rag-001")
        ... async def retrieve_documents(query: str) -> List[str]:
        ...     return await qdrant.search(query)
    """

    def __init__(
        self,
        manager: AuditTrailManager,
        skill_id: str,
        actor_id: str = "system",
    ):
        """Initialize skill audit decorator.

        Args:
            manager: Audit trail manager
            skill_id: Skill identifier
            actor_id: Actor identifier (default: system)
        """
        self.manager = manager
        self.skill_id = skill_id
        self.actor_id = actor_id
        self._loaded = False

    def __call__(self, func: Callable) -> Callable:
        """Wrap function with audit logging.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Log skill loaded (once)
            if not self._loaded:
                await self.manager.log(
                    event_type=AuditEventType.SKILL_LOADED,
                    actor_id=self.actor_id,
                    action=f"Load skill: {self.skill_id}",
                    outcome="success",
                    metadata={"skill_id": self.skill_id, "function": func.__name__},
                )
                self._loaded = True

            # Log skill execution
            start_time = datetime.utcnow()

            try:
                result = await func(*args, **kwargs)

                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                await self.manager.log(
                    event_type=AuditEventType.SKILL_EXECUTED,
                    actor_id=self.actor_id,
                    action=f"Execute skill: {self.skill_id}",
                    outcome="success",
                    metadata={
                        "skill_id": self.skill_id,
                        "function": func.__name__,
                        "duration_ms": duration_ms,
                    },
                    context={"args": args, "kwargs": kwargs},
                    output=result,
                )

                return result

            except Exception as e:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                await self.manager.log(
                    event_type=AuditEventType.SKILL_FAILED,
                    actor_id=self.actor_id,
                    action=f"Execute skill: {self.skill_id}",
                    outcome="failure",
                    metadata={
                        "skill_id": self.skill_id,
                        "function": func.__name__,
                        "duration_ms": duration_ms,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    context={"args": args, "kwargs": kwargs},
                )

                raise

        return wrapper


def audit_skill(
    manager: AuditTrailManager,
    skill_id: str,
    actor_id: str = "system",
) -> SkillAuditDecorator:
    """Convenience function for skill audit decorator.

    Args:
        manager: Audit trail manager
        skill_id: Skill identifier
        actor_id: Actor identifier

    Returns:
        Decorator instance

    Example:
        >>> @audit_skill(manager, skill_id="rag-001")
        ... async def retrieve_documents(query: str):
        ...     pass
    """
    return SkillAuditDecorator(manager, skill_id, actor_id)
