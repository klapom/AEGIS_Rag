# TD-120: Graphiti Time-Travel & Entity Versioning

**Status:** OPEN
**Priority:** LOW
**Story Points:** 31 SP (Full) / 10 SP (Minimal)
**Target Sprint:** DEFERRED (Sprint 98+)
**Created:** 2026-01-20
**Discovered During:** Sprint 114 (Planning)

---

## Summary

Graphiti's 3-layer temporal memory architecture (immediate → contextual → archival) and Redis-backed versioning provide infrastructure for advanced entity history features. These features are "nice-to-have" capabilities that would enhance the UI but are not critical for core RAG functionality. This TD documents the decision to defer indefinitely unless specific customer requirements emerge.

---

## Problem Statement

The system currently has the infrastructure to support time-travel and entity versioning:
- **Graphiti 3-layer memory:** Stores temporal snapshots
- **Neo4j timestamps:** Entity creation/modification dates recorded
- **Redis versioning:** Change tracking and rollback capability

However, the UI lacks three features to surface this historical data:

### Feature Set Overview

| Feature | Story Points | Complexity | Customer Value |
|---------|----------|-----------|-----------------|
| **Time Travel Tab** | 8 SP | High | Medium |
| **Version Comparison** | 13 SP | Very High | Low |
| **Entity Changelog Panel** | 10 SP | Medium | Low |
| **Total** | **31 SP** | - | - |

---

## Feature Details

### Feature 1: Time Travel Tab (8 SP)

**Description:** Interactive temporal point-in-time query interface

**Component Locations:**
```
frontend/src/components/MemoryVisualization.tsx (Time Travel Tab)
src/api/v1/memory.py (GET /temporal/snapshot endpoint)
src/components/memory/temporal_query.py (TemporalQueryBuilder)
```

**Implementation Requirements:**
- Date/time slider (from first ingestion to now)
- Point-in-time graph state reconstruction
- Entity relationship state at selected timestamp
- Performance consideration: ~100ms per temporal query

**Story Point Breakdown:**
- Slider UI component: 2 SP
- Temporal query builder: 3 SP
- Graph reconstruction API: 2 SP
- Testing: 1 SP

**TODO Markers for Future Implementation:**
```python
# src/api/v1/memory.py
@router.get("/temporal/snapshot")
async def get_temporal_snapshot(timestamp: datetime):
    """TODO-TD120-1: Implement time-travel snapshot retrieval

    Returns the state of the knowledge graph at a specific point in time.
    Requires:
    1. Query Neo4j for entities/relations with valid_from <= timestamp <= valid_to
    2. Reconstruct Qdrant vectors at that timestamp (if versioned)
    3. Return historical relationship state

    Performance Target: <100ms for graphs with <10k entities
    Cache Strategy: Redis TTL 1 hour for frequently accessed timestamps
    """
    pass
```

```typescript
// frontend/src/components/MemoryVisualization.tsx
interface TimelineProps {
  // TODO-TD120-2: Add timestamp-aware visualization
  // Requires: ReactVis timeline + date slider component
  // State: { selectedTimestamp, showingHistorical, historicalEntities }
}
```

---

### Feature 2: Version Comparison View (13 SP)

**Description:** Side-by-side diff view showing entity property evolution

**Component Locations:**
```
frontend/src/components/EntityVersionComparison.tsx (Main UI)
src/api/v1/entity.py (GET /entities/{id}/versions endpoint)
src/components/knowledge_graph/entity_versioning.py (VersionComparisonEngine)
```

**Implementation Requirements:**
- Entity version history retrieval
- Side-by-side property diff highlighting
- Relationship count changes over time
- Attribute value changes (with semantic diff for text)

**Story Point Breakdown:**
- Version history API endpoint: 3 SP
- Diff algorithm (text, relations, properties): 5 SP
- UI component (split-pane, highlighting): 4 SP
- Testing: 1 SP

**Complexity Considerations:**
- **Challenge 1:** Semantic diff for long text fields (descriptions)
  - Simple substring diff is insufficient
  - Could use edit distance algorithms (Levenshtein)
  - Or LLM-based semantic comparison (~200ms per entity pair)

- **Challenge 2:** Relationship cardinality changes
  - "Entity X had 3 relations in v1 → 5 relations in v2"
  - Showing which relations were added/removed
  - Complex visualization at scale

- **Challenge 3:** Timestamp alignment
  - Multiple versions created in rapid succession
  - Which versions to show? All? Sampled? Only "significant" changes?

**TODO Markers for Future Implementation:**
```python
# src/api/v1/entity.py
@router.get("/entities/{entity_id}/versions")
async def get_entity_versions(entity_id: str, limit: int = 10):
    """TODO-TD120-3: Implement entity version history retrieval

    Returns timestamped versions of an entity with:
    1. Property snapshots (name, description, entity_type, metadata)
    2. Relationship count at each version
    3. Modification timestamps and source (user/system/LLM)

    Decision Required: How many versions to keep?
    - Keep all: Storage cost ~10KB per entity (10k entities = 100MB)
    - Sample: Keep 1 every hour, archive daily snapshots (90% reduction)
    - Truncate: Keep last 30 versions (most common pattern)

    Current: No version limit defined
    """
    pass

class VersionComparisonEngine:
    """TODO-TD120-4: Implement semantic diff for entity properties

    Challenge: Simple text diff doesn't capture semantic changes
    Example:
      v1: "Machine learning model for NLP tasks"
      v2: "Deep learning transformer for text classification"

    Options:
    1. Edit distance (Levenshtein): Fast, shows character changes
    2. Word-level diff: Shows word-by-word changes, cleaner UI
    3. Semantic diff: Run through SBERT, show concept changes (slow)

    Current: None implemented
    Recommendation: Start with word-level diff (fast, clear)
    """
    pass
```

```typescript
// frontend/src/components/EntityVersionComparison.tsx
export function EntityVersionComparison({
  entityId,
  version1Timestamp,
  version2Timestamp,
}: Props) {
  // TODO-TD120-5: Implement side-by-side version comparison UI
  // Requires:
  // 1. Fetch both versions from API
  // 2. Compute diff for each property
  // 3. Render side-by-side with highlighting
  //    - Green: Added/changed properties
  //    - Red: Removed properties
  //    - Gray: Unchanged
  //
  // Performance: React Diff View or similar library
  // Library suggestion: react-diff-view or custom diff renderer
  return null;
}
```

---

### Feature 3: Entity Changelog Panel (10 SP)

**Description:** Timeline/changelog view showing all changes to an entity

**Component Locations:**
```
frontend/src/components/EntityChangeLog.tsx (Timeline UI)
src/api/v1/entity.py (GET /entities/{id}/changelog endpoint)
src/components/knowledge_graph/audit_trail.py (ChangeLogBuilder)
```

**Implementation Requirements:**
- Event timeline (chronological list)
- Change type indicators (created, modified, related-to, deleted)
- Change magnitude (trivial vs significant)
- Change source (LLM extraction, user edit, gleaning, etc.)

**Story Point Breakdown:**
- Changelog API endpoint: 2 SP
- Changelog aggregation logic: 3 SP
- Timeline UI component: 3 SP
- Testing: 2 SP

**TODO Markers for Future Implementation:**
```python
# src/api/v1/entity.py
@router.get("/entities/{entity_id}/changelog")
async def get_entity_changelog(
    entity_id: str,
    limit: int = 50,
    filter_type: str | None = None,
):
    """TODO-TD120-6: Implement entity changelog retrieval

    Returns chronological list of changes to an entity:
    1. Created: Initial extraction
    2. Modified: Property changes (description, type, metadata)
    3. Related: New relationships added/removed
    4. Merged: Entity merged with another
    5. Deleted: Entity deleted (soft delete, recoverable)

    Data Source: Neo4j temporal properties
      - created_at: Timestamp
      - modified_at: Timestamp
      - modification_count: Integer
      - related_at: Relationship timestamp

    Current Implementation: None (audit trail exists but not surfaced in UI)
    """
    pass

class ChangeLogBuilder:
    """TODO-TD120-7: Aggregate Neo4j temporal data into changelog events

    Requires:
    1. Query all Neo4j node versions for entity_id
    2. Query all relationship creation/deletion events
    3. Merge and sort chronologically
    4. Calculate change magnitude (diff size, property count changed)
    5. Infer change type and source

    Data Model:
    {
        "timestamp": "2026-01-20T10:30:00Z",
        "event_type": "modified",
        "properties_changed": ["description", "confidence"],
        "change_magnitude": "major",  # trivial | minor | major
        "source": "llm_extraction",  # user_edit | gleaning | llm | system
        "summary": "Description updated based on new document"
    }
    """
    pass
```

```typescript
// frontend/src/components/EntityChangeLog.tsx
export function EntityChangeLog({ entityId }: Props) {
  // TODO-TD120-8: Render entity changelog as vertical timeline
  //
  // UI Pattern:
  // Timeline (vertical line)
  // ├─ 2026-01-20 10:30 [Modified] Description updated (major)
  // ├─ 2026-01-19 15:45 [Related] Connected to "NLP" entity (minor)
  // ├─ 2026-01-18 08:00 [Created] Extracted from research_paper_001.pdf
  //
  // Interactive Features:
  // - Click event to show diff
  // - Filter by change type
  // - Filter by date range
  // - Show/hide minor changes
  //
  // Performance: Virtualize list if >100 events
  return null;
}
```

---

## Risk Assessment

### Why This is Deferred (Option 3)

| Risk Factor | Impact | Justification |
|------------|--------|---------------|
| **Low Priority** | MEDIUM | Users rarely ask for time-travel. Feature request frequency: ~1/month |
| **High Complexity** | HIGH | 31 SP for features touching Neo4j temporality, Redis versioning, UI state |
| **Uncertain Value** | HIGH | No AB test data. Similar features in competitors (Confluence history) have <5% usage |
| **Maintenance Cost** | MEDIUM | Temporal data requires versioning strategy, storage limits, cleanup |
| **Alternative** | - | Users can export graph at any time via API for manual comparison |

### Maintenance Burden if Implemented

- **Storage:** Each entity version = ~5KB. 10k entities × 30 versions = 1.5GB per namespace
- **Retention Policy:** Need to decide: keep all? Sample? Truncate after N?
- **Database Queries:** Temporal queries slower than current state queries (~2-5x latency)
- **Cache Invalidation:** Temporal snapshots require careful Redis TTL strategy

---

## Options Analysis

### Option 1: Full Implementation (31 SP)

**Timeline:** 1.5 sprints
**When:** Sprint 98-99

**Pros:**
- Complete time-travel and versioning capabilities
- Professional-grade audit trail
- Supports potential compliance requirements
- Enables rollback workflows

**Cons:**
- Takes 1.5 sprints away from RAGAS optimization or other features
- Increases storage and query latency
- Complex testing and maintenance
- Uncertain ROI

**Cost-Benefit Ratio:** LOW (31 SP for medium-value features)

---

### Option 2: Minimal Implementation (10 SP)

**Timeline:** 0.5 sprint
**When:** Sprint 98 (if capacity)

**Scope:**
- Only Entity Changelog Panel (Feature 3)
- Basic timeline UI
- Skip semantic diff and version comparison
- Time-travel deferred

**Pros:**
- Quick to implement
- Covers most common use case (audit trail)
- Lower maintenance burden
- Rollout smaller risk

**Cons:**
- Time-travel still missing (most sophisticated feature)
- Version comparison unavailable
- Incomplete feature set

**Cost-Benefit Ratio:** MEDIUM (10 SP for medium-value)

---

### Option 3: Defer Indefinitely (RECOMMENDED)

**Timeline:** Sprint 99+
**Trigger:** Customer request with SLA requirement

**Process if triggered:**
1. Estimate full 31 SP vs customer value
2. Implement whichever features customer prioritizes
3. Add customer-driven retention policy (not our guess)
4. Include in contract SLA for temporal query latency

**Pros:**
- No maintenance burden currently
- Preserved capacity for core RAG optimization
- Decision moves to customer-driven priorities
- Can be added quickly if needed (clear implementation plan exists)

**Cons:**
- Users don't have audit trail (but compliance requirements unlikely)
- No rollback capability (data is mutable, not append-only)

**Cost-Benefit Ratio:** HIGHEST (0 SP current cost, future-proofed)

---

## RECOMMENDATION: Option 3 (Defer Indefinitely)

**Rationale:**
1. **Low Usage Likelihood:** Time-travel is aspirational feature, rarely demanded by users
2. **Capacity Better Used:** RAGAS Phase 3, LightRAG CRUD (TD-104), Relation Quality (TD-102) have higher ROI
3. **Implementation Ready:** This TD document provides clear roadmap if customer request emerges
4. **Compliance Unlikely:** AegisRAG is not in regulated domain requiring audit trails
5. **Technical Debt Instead:** Feature should live in TD_INDEX until customer-driven trigger

**Decision Rule:**
- Implement Features 1-3 in full IF: Customer contract includes "temporal query SLA" or "entity rollback" requirements
- Otherwise: Keep in TD_INDEX, revisit Sprint 100+

---

## Code Markers & Locations

### Backend Markers

```python
# src/api/v1/memory.py
@router.get("/temporal/snapshot")
async def get_temporal_snapshot(timestamp: datetime):
    """TODO-TD120-1: Temporal snapshot implementation pending"""
    pass

# src/api/v1/entity.py
@router.get("/entities/{entity_id}/versions")
async def get_entity_versions(entity_id: str):
    """TODO-TD120-3: Version history API pending"""
    pass

@router.get("/entities/{entity_id}/changelog")
async def get_entity_changelog(entity_id: str):
    """TODO-TD120-6: Changelog API pending"""
    pass

# src/components/knowledge_graph/entity_versioning.py
class VersionComparisonEngine:
    """TODO-TD120-4: Semantic diff implementation pending"""
    pass

class ChangeLogBuilder:
    """TODO-TD120-7: Changelog aggregation pending"""
    pass
```

### Frontend Markers

```typescript
// frontend/src/components/MemoryVisualization.tsx
interface TimelineProps {
  // TODO-TD120-2: Time Travel Tab implementation pending
}

// frontend/src/components/EntityVersionComparison.tsx
export function EntityVersionComparison() {
  // TODO-TD120-5: Version comparison UI implementation pending
  return null;
}

// frontend/src/components/EntityChangeLog.tsx
export function EntityChangeLog() {
  // TODO-TD120-8: Changelog timeline UI implementation pending
  return null;
}
```

---

## Related Documents

- [TD-104: LightRAG CRUD Feature Gap](TD-104_LIGHTRAG_CRUD_FEATURE_GAP.md) - Higher priority
- [TD-102: Relation Extraction Improvement](TD-102_RELATION_EXTRACTION_IMPROVEMENT.md) - Higher priority
- [ADR-054: Entity Versioning Strategy](../adr/ADR-054_ENTITY_VERSIONING_STRATEGY.md) - If future implementation required
- [TECH_STACK.md: Graphiti Integration](../TECH_STACK.md) - Temporal memory architecture

---

## Trigger Criteria for Implementation

This TD moves to ACTIVE if any of these occur:

1. **Customer Requirement:** "SLA requirement for temporal queries" in contract
2. **Compliance Need:** Audit trail required for compliance certification
3. **Data Recovery:** Data corruption incident requires rollback capability
4. **Feature Request:** ≥3 users request time-travel in same quarter
5. **Executive Decision:** Business stakeholder prioritizes versioning

---

## Archive Criteria

This TD can be archived when:
1. Customer requirement emerges AND all 3 features implemented, OR
2. Sprint 120 reached with no requests (defer 10+ sprints → archive as "decided against")

---

## Story Point Breakdown

| Feature | Full | Minimal | Implementation Markers |
|---------|------|---------|------------------------|
| Time Travel Tab | 8 SP | - | TODO-TD120-1, TD120-2 |
| Version Comparison | 13 SP | - | TODO-TD120-3, TD120-4, TD120-5 |
| Entity Changelog | 10 SP | 10 SP | TODO-TD120-6, TD120-7, TD120-8 |
| **Total** | **31 SP** | **10 SP** | **8 Markers** |

---

**Decision Owner:** Technical Steering Committee
**Next Review:** Sprint 98 or on customer trigger
**Document Status:** DEFERRED (Indefinite Hold)
