# TD-121: Neo4j Graph Versioning UI (Features 39.5-39.7)

**Status:** OPEN
**Priority:** LOW
**Story Points:** 21 SP
**Target Sprint:** DEFERRED (Sprint 122+)
**Created:** 2026-01-26
**Discovered During:** Sprint 119 (E2E Test Analysis)

---

## Summary

E2E test analysis in Sprint 119 identified 28 skipped tests across 3 test files that require Neo4j graph versioning features not yet implemented. These features (39.5-39.7) would enable time-travel graph queries, entity changelogs, and version comparison through the UI.

---

## Problem Statement

The E2E test suite includes 28 tests for graph versioning capabilities that are currently skipped with `test.describe.skip()`:

| Test File | Feature | Tests | What It Tests |
|-----------|---------|-------|---------------|
| `time-travel.spec.ts` | 39.5 | 9 | Historical graph state queries |
| `entity-changelog.spec.ts` | 39.6 | 9 | Entity change history viewer |
| `version-compare.spec.ts` | 39.7 | 10 | Side-by-side version comparison |

These tests remain skipped because the backend API endpoints and frontend UI components do not exist.

---

## Required Implementation

### Backend API Endpoints

```
POST /api/v1/graph/time-travel        # Query graph at specific point in time
GET  /api/v1/graph/entity/{id}/changelog  # Get entity change history
POST /api/v1/graph/version-compare    # Compare two graph snapshots
GET  /api/v1/graph/snapshots          # List available graph snapshots
```

### Frontend Components

- Time-travel query UI (date picker + graph visualization)
- Entity changelog viewer (timeline of changes)
- Version comparison UI (diff view for graph states)
- Graph state snapshot management

### Data Layer

- Neo4j temporal properties for entity versioning
- Snapshot storage mechanism (periodic or event-driven)
- Efficient diff computation between graph states

---

## Relationship to TD-120

**TD-120** covers **Graphiti** (Redis memory layer) time-travel and entity versioning.
**TD-121** covers **Neo4j** (knowledge graph) versioning with visual UI.

These are complementary but independent features:
- TD-120: Memory-layer temporal queries (Redis + Graphiti)
- TD-121: Knowledge graph versioning (Neo4j + Frontend)

---

## Decision

**Deferred to Sprint 122+** based on:

1. **No immediate user demand** — Graph visualization works without versioning
2. **High complexity** — 21 SP including API + UI + data layer
3. **Test coverage** — 28 tests already written, ready for implementation
4. **Dependency** — May benefit from TD-120 patterns if implemented first

**Trigger for implementation:** Customer requirement for graph audit trail or compliance needs.

---

## References

- Sprint 119 Plan: [SPRINT_119_PLAN.md](../sprints/SPRINT_119_PLAN.md) (Feature 119.2 analysis)
- Related TD: [TD-120](TD-120_GRAPHITI_TIMETRAVEL_VERSIONING.md) (Graphiti Time-Travel)
- Test files: `frontend/e2e/graph/time-travel.spec.ts`, `entity-changelog.spec.ts`, `version-compare.spec.ts`
