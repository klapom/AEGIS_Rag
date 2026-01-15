# Audit Trail System

**Sprint 96 Feature 96.2: Immutable Audit Trail with Cryptographic Integrity**

## Overview

The audit trail system provides immutable, tamper-proof logging for compliance with 7-year retention requirements (GDPR, GxP, SOC2). Uses SHA-256 blockchain-inspired hash chaining for integrity verification.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ AuditTrailManager                                       │
│  - Append-only logging                                  │
│  - SHA-256 hash chain                                   │
│  - Compliance reporting                                 │
│  - Tamper detection                                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ AuditStorage (Abstract Interface)                       │
│  - append(event)                                        │
│  - query(filters)                                       │
│  - get_last_event()                                     │
│  - purge_old_events(retention_days)                     │
└────────────────┬────────────────────────────────────────┘
                 │
     ┌───────────┴───────────┐
     ▼                       ▼
┌──────────────┐    ┌──────────────────┐
│ InMemory     │    │ Redis/PostgreSQL │
│ (Mock)       │    │ (Production)     │
└──────────────┘    └──────────────────┘
```

## Key Components

### 1. AuditEventType (16 Types)

**Skill Lifecycle (5):**
- `SKILL_LOADED` - Skill loaded into system
- `SKILL_EXECUTED` - Skill execution completed
- `SKILL_FAILED` - Skill execution failed
- `SKILL_UPDATED` - Skill updated
- `SKILL_DELETED` - Skill removed

**Data Access (4):**
- `DATA_READ` - Data accessed
- `DATA_WRITE` - Data written
- `DATA_DELETE` - Data deleted
- `DATA_EXPORTED` - Data exported

**Decisions (3):**
- `DECISION_ROUTED` - Decision routed
- `DECISION_REJECTED` - Decision rejected
- `DECISION_APPROVED` - Decision approved

**Security (3):**
- `AUTH_SUCCESS` - Authentication succeeded
- `AUTH_FAILURE` - Authentication failed
- `POLICY_VIOLATION` - Policy violated

**System (1):**
- `CONFIG_CHANGED` - Configuration changed

### 2. AuditEvent (Immutable Dataclass)

```python
@dataclass(frozen=True)
class AuditEvent:
    id: str                          # UUID
    timestamp: datetime              # UTC timestamp
    event_type: AuditEventType       # Event type
    actor_id: str                    # Actor (user/agent/system)
    actor_type: str                  # "human", "agent", "system"
    action: str                      # Human-readable action
    outcome: str                     # "success", "failure", "pending"
    metadata: Dict[str, Any]         # Additional context
    context_hash: Optional[str]      # SHA-256 of input context
    output_hash: Optional[str]       # SHA-256 of output
    previous_hash: Optional[str]     # Previous event hash (chain)
    event_hash: str                  # SHA-256 of this event
```

**Hash Computation:**
```python
event_hash = SHA-256(
    id + timestamp + event_type + actor_id +
    actor_type + action + outcome + metadata +
    context_hash + output_hash + previous_hash
)
```

### 3. AuditTrailManager

**Core Operations:**
- `log()` - Append event to trail
- `verify_integrity()` - Verify hash chain
- `generate_compliance_report()` - Generate compliance reports
- `purge_old_events()` - Remove events older than retention period

**Compliance Reports:**
- `gdpr_art30` - GDPR Article 30 processing activities
- `security` - Security events (auth, violations)
- `skill_usage` - Skill execution audit
- `data_access` - Data access audit

### 4. SkillAuditDecorator

Auto-audit skill executions:

```python
@audit_skill(manager, skill_id="rag-001")
async def retrieve_documents(query: str) -> List[str]:
    return await qdrant.search(query)
```

Automatically logs:
- `SKILL_LOADED` (first call)
- `SKILL_EXECUTED` (each call, with duration)
- `SKILL_FAILED` (on exception)

## Usage Examples

### Basic Logging

```python
from src.governance.audit import (
    AuditTrailManager,
    AuditEventType,
    InMemoryAuditStorage,
)

# Initialize
storage = InMemoryAuditStorage()
manager = AuditTrailManager(storage, retention_days=365 * 7)

# Log skill execution
event = await manager.log(
    event_type=AuditEventType.SKILL_EXECUTED,
    actor_id="claude_agent",
    action="retrieve_documents",
    outcome="success",
    metadata={
        "skill_id": "rag-001",
        "duration_ms": 120,
        "query_length": 50
    }
)
```

### Integrity Verification

```python
# Verify entire trail
is_valid, errors = await manager.verify_integrity()

if not is_valid:
    for error in errors:
        logger.error(f"Integrity violation: {error}")

# Verify time range
is_valid, errors = await manager.verify_integrity(
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 12, 31)
)
```

### Compliance Reports

```python
# GDPR Article 30 report
report = await manager.generate_compliance_report(
    report_type="gdpr_art30",
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 12, 31)
)

print(f"Processing activities: {report['processing_activities']['total']}")
print(f"By type: {report['processing_activities']['by_type']}")
print(f"By actor: {report['processing_activities']['by_actor']}")

# Security report
report = await manager.generate_compliance_report(
    report_type="security",
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 12, 31)
)

print(f"Failed auth attempts: {report['security_summary']['failed_auth']}")
print(f"Policy violations: {report['security_summary']['violations']}")
```

### Skill Decorator

```python
from src.governance.audit import audit_skill

@audit_skill(manager, skill_id="rag-retrieval", actor_id="claude")
async def retrieve_documents(query: str, top_k: int = 5) -> List[Dict]:
    """Retrieve documents from Qdrant."""
    results = await qdrant.search(query, top_k=top_k)
    return results
```

## Integration Points

### 1. Policy Engine (Sprint 93)

```python
# Log policy violations
if not policy_engine.evaluate(action, context):
    await audit_manager.log(
        event_type=AuditEventType.POLICY_VIOLATION,
        actor_id=user_id,
        action=action,
        outcome="blocked",
        metadata={"policy": policy.id, "reason": reason}
    )
```

### 2. GDPR Processing Log (Feature 96.1)

```python
# Log data processing
await audit_manager.log(
    event_type=AuditEventType.DATA_READ,
    actor_id=user_id,
    action="retrieve_personal_data",
    outcome="success",
    metadata={
        "data_category": "personal_info",
        "legal_basis": "consent",
        "purpose": "query_response"
    }
)
```

### 3. Skill Orchestration

```python
# Auto-audit all skills
skill_registry = SkillRegistry(audit_manager=audit_manager)

@skill_registry.register("vector_search")
async def vector_search(query: str):
    # Automatically audited via decorator
    pass
```

## Storage Backends

### In-Memory (Testing)

```python
from src.governance.audit import InMemoryAuditStorage

storage = InMemoryAuditStorage(retention_days=365 * 7)
```

### Redis Streams (Production - Future)

```python
# TODO: Implement RedisAuditStorage
# - Uses Redis Streams for append-only log
# - XADD for appends, XRANGE for queries
# - TTL for automatic retention
```

### PostgreSQL (Production - Future)

```python
# TODO: Implement PostgreSQLAuditStorage
# - Uses append-only table with CHECK constraint (no updates)
# - Partition by time for efficient queries
# - Automatic archival after retention period
```

## Performance

**Target Metrics:**
- Log operation: <10ms p95
- Integrity verification: <100ms for 10k events
- Report generation: <500ms for 10k events
- Storage overhead: ~500 bytes per event

**Scalability:**
- 1M events = ~500 MB storage
- 7 years @ 100 events/hour = 6.1M events = ~3 GB
- Query performance: Time-range indexed

## Security

**Cryptographic Integrity:**
- SHA-256 hash chain (blockchain-inspired)
- Tamper detection via hash verification
- Immutable dataclass (frozen)

**Access Control:**
- Append-only storage (no updates/deletes)
- Admin-only purge operations
- Integrity reports for auditors

**Compliance:**
- 7-year retention (EU GxP, GDPR)
- GDPR Article 30 processing log
- SOC2 audit trail
- Tamper-proof evidence

## Testing

**Coverage: 97% (51 tests)**

Test categories:
- Event types (6 tests)
- Event hashing (12 tests)
- Storage operations (10 tests)
- Trail management (13 tests)
- Skill decorator (7 tests)
- Integration (3 tests)

Run tests:
```bash
poetry run pytest tests/unit/governance/audit/ -v --cov=src/governance/audit
```

## Future Enhancements

1. **Production Storage:**
   - Redis Streams implementation
   - PostgreSQL with partitioning
   - S3 archival for old events

2. **Query Optimization:**
   - Full-text search in metadata
   - Aggregation queries (GROUP BY)
   - Real-time event streaming

3. **Advanced Features:**
   - Digital signatures (PKI)
   - Merkle tree for batch verification
   - Distributed consensus (multi-node)

4. **Monitoring:**
   - Prometheus metrics (events/sec, integrity checks)
   - Grafana dashboards
   - Alerting on integrity violations

## References

- **ADR-096:** Governance framework with audit trail
- **GDPR Article 30:** Record of processing activities
- **SOC2 CC6.3:** Audit logging requirements
- **GxP:** 21 CFR Part 11 electronic records
- **Sprint 96:** Governance foundation implementation

## License

Internal use only - AegisRAG project.
