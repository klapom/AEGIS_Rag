# Migration Guide: graph/analytics/* Endpoints Deprecation

**Sprint:** 72 (Feature 72.4 - Dead Code Removal)
**Date:** 2026-01-06
**Status:** 🟡 **DEPRECATED** (Removal planned for Sprint 73)

---

## Executive Summary

The `/api/v1/graph/analytics/*` endpoints are **deprecated** as of Sprint 72 and will be **removed in Sprint 73**.

**Reason:** These endpoints were implemented but **never integrated into the frontend**. No production code uses them.

---

## Deprecated Endpoints

| Endpoint | Method | Replacement | Status |
|----------|--------|-------------|--------|
| `/api/v1/graph/analytics/centrality/{entity_id}` | GET | None (unused) | 🔴 DEPRECATED |
| `/api/v1/graph/analytics/pagerank` | GET | None (unused) | 🔴 DEPRECATED |
| `/api/v1/graph/analytics/influential` | GET | None (unused) | 🔴 DEPRECATED |
| `/api/v1/graph/analytics/gaps` | GET | None (unused) | 🔴 DEPRECATED |
| `/api/v1/graph/analytics/recommendations/{entity_id}` | GET | None (unused) | 🔴 DEPRECATED |
| `/api/v1/graph/analytics/statistics` | GET | `/api/v1/graph/viz/statistics` | ✅ REPLACEMENT EXISTS |

---

## Migration Path

### For `/api/v1/graph/analytics/statistics`

**Old Endpoint:**
```http
GET /api/v1/graph/analytics/statistics
```

**New Endpoint:**
```http
GET /api/v1/graph/viz/statistics
```

**Response Model:**
```typescript
interface GraphStatistics {
  node_count: number;
  edge_count: number;
  community_count: number;
  avg_degree: number;
  entity_type_distribution: Record<string, number>;
  orphaned_nodes: number;
  timestamp: string;
}
```

**Frontend Code Update:**
```typescript
// OLD (deprecated):
const stats = await fetch('/api/v1/graph/analytics/statistics');

// NEW (use instead):
const stats = await fetch('/api/v1/graph/viz/statistics');
```

---

### For Other Endpoints (No Replacement)

The following endpoints have **no replacement** because they were never used in production:

- `/api/v1/graph/analytics/centrality/{entity_id}` - Centrality metrics
- `/api/v1/graph/analytics/pagerank` - PageRank scores
- `/api/v1/graph/analytics/influential` - Influential entities
- `/api/v1/graph/analytics/gaps` - Knowledge gaps
- `/api/v1/graph/analytics/recommendations/{entity_id}` - Entity recommendations

**If you need these features in the future:**
1. Re-implement in `/api/v1/graph/viz/*` namespace (standardized location)
2. Integrate into frontend UI (graphs page)
3. Add E2E tests for frontend integration

---

## Impact Analysis

### Backend Impact
- **Code:** `src/api/graph_analytics.py` (286 lines)
- **Tests:**
  - `tests/api/test_graph_analytics.py` (unit tests)
  - `tests/e2e/test_e2e_graph_analytics.py` (E2E tests)
- **Dependencies:**
  - `src/components/graph_rag/analytics_engine.py`
  - `src/components/graph_rag/recommendation_engine.py`

**Action:** Mark tests as deprecated, but don't delete (preserves knowledge)

### Frontend Impact
- **Code:** ✅ No frontend code uses these endpoints (verified via grep)
- **Tests:** ✅ No E2E tests reference these endpoints

**Action:** No frontend changes needed

### Database Impact
- **Neo4j:** ✅ No schema changes needed (analytics are read-only queries)

**Action:** No database migration needed

---

## Deprecation Timeline

| Sprint | Action |
|--------|--------|
| **72** (Current) | Add deprecation warnings to endpoints |
| **73** (Next) | Remove `graph_analytics.py` + tests |
| **73** (Next) | Remove analytics_engine.py + recommendation_engine.py (if unused elsewhere) |

---

## Deprecation Warnings (Sprint 72)

All endpoints now return deprecation warnings in response headers:

```http
HTTP/1.1 200 OK
Warning: 299 - "DEPRECATED: This endpoint will be removed in Sprint 73. See docs/sprints/SPRINT_72_MIGRATION_GUIDE_GRAPH_ANALYTICS.md"
X-Deprecation-Date: 2026-01-06
X-Removal-Sprint: 73
```

---

## Rollback Plan

If deprecation causes issues:

1. **Immediate:** Remove deprecation warnings (revert changes to `graph_analytics.py`)
2. **Investigation:** Identify unexpected usage (check logs for API calls)
3. **Decision:**
   - If usage found → defer removal to Sprint 74+
   - If no usage → proceed with Sprint 73 removal

**Risk:** ✅ **LOW** - No frontend code uses these endpoints

---

## References

- **Deprecation Issue:** SPRINT_72_PLAN.md Feature 72.4
- **Old Endpoints:** `src/api/graph_analytics.py`
- **New Endpoints:** `src/api/routers/graph_viz.py`
- **Tests:** `tests/api/test_graph_analytics.py`

---

## Approval

- **Tech Lead:** Klaus Pommer ✅
- **Sprint:** 72 (Feature 72.4)
- **Deprecation Date:** 2026-01-06
- **Planned Removal:** Sprint 73 (2026-01-13+)

---

**Last Updated:** 2026-01-06
**Status:** 🟡 **ACTIVE DEPRECATION**
