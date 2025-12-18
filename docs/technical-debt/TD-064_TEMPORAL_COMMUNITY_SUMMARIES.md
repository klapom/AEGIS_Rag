# TD-064: Temporal Community Summaries

## Status
**PLANNED** (2025-12-18)

## Context

TD-058 implements community summary generation for Maximum Hybrid Search. However, the bi-temporal
aspect (time-travel queries for community summaries) was deferred to reduce Sprint 52 scope.

With `valid_from`/`valid_to` on RELATES_TO relationships (Sprint 39), community structures
change over time. Summaries should reflect the graph state at specific timestamps.

## Problem

### 1. Community Structures are Time-Dependent
```
Vorher (2025-01-01): Community 5 (10 Entities) + Community 8 (8 Entities)
Nachher (2025-06-01): Community 5 (18 Entities) ← Merged durch neue RELATES_TO Edge
```

### 2. Current Summaries Only Reflect "Now"
Without temporal summaries, time-travel queries cannot use community-level context.

### 3. Storage vs Computation Trade-off
- **Option A:** Store snapshots at every change → High storage
- **Option B:** Regenerate on-demand → Slow (LLM call per query)
- **Option C:** Hybrid approach → Recommended

## Proposed Solution

### Bi-Temporal Summary Storage

```python
@dataclass
class TemporalCommunitySummary:
    community_id: int
    summary: str
    valid_from: datetime
    valid_to: datetime | None  # None = currently valid

async def get_community_summary_at(
    community_id: int,
    timestamp: datetime
) -> str | None:
    """Get community summary valid at timestamp."""
    query = """
    MATCH (cs:CommunitySummary {community_id: $community_id})
    WHERE cs.valid_from <= $timestamp
      AND (cs.valid_to IS NULL OR cs.valid_to > $timestamp)
    RETURN cs.summary
    """
    return await neo4j.execute_read(query, community_id=community_id, timestamp=timestamp)
```

### Hybrid Strategy (Recommended)

1. **Store snapshots at important points** (monthly, major ingestions)
2. **Regenerate on-demand** for intermediate timestamps
3. **Cache regenerated summaries** for frequently queried periods

### Neo4j Schema Extension

```cypher
-- Extend CommunitySummary for temporal storage
ALTER TABLE CommunitySummary ADD valid_from DATETIME;
ALTER TABLE CommunitySummary ADD valid_to DATETIME;

-- Index for time-travel queries
CREATE INDEX community_summary_temporal
FOR (cs:CommunitySummary)
ON (cs.community_id, cs.valid_from, cs.valid_to);

-- Unique constraint per community and time
CREATE CONSTRAINT community_summary_unique
FOR (cs:CommunitySummary)
REQUIRE (cs.community_id, cs.valid_from) IS UNIQUE;
```

## Implementation Plan

### Phase 1: Temporal Storage (5 SP)
- [ ] Add `valid_from`, `valid_to` fields to CommunitySummary
- [ ] Update `store_community_summary()` to close previous and create new
- [ ] Index for temporal queries

### Phase 2: Time-Travel Query Support (5 SP)
- [ ] `get_summary_at_timestamp()` with fallback regeneration
- [ ] Integration in Maximum Hybrid Search for historical queries
- [ ] Caching strategy for frequent periods

### Phase 3: Snapshot Automation (3 SP)
- [ ] Monthly automatic snapshot creation
- [ ] Snapshot on major ingestion events
- [ ] Cleanup of old snapshots (retention policy)

## Effort Estimate
**13 SP total** (deferred from Sprint 52)

## Dependencies

- TD-058: Community Summary Generation (prerequisite)
- Sprint 39: Bi-Temporal Knowledge Graph (existing)

## Priority
**LOW** - Nice-to-have for compliance/audit use cases

## Decision Makers
- Klaus Pommer (Project Lead)
- Claude Code (Implementation)

## Date
2025-12-18
