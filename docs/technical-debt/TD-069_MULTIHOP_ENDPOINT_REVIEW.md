# TD-069: Multihop Endpoint Status Review

**Status:** ✅ RESOLVED (Sprint 60 Feature 60.4)
**Priority:** LOW
**Story Points:** 3
**Created:** Sprint 60 Planning
**Completed:** Sprint 60 (2025-12-21)
**Resolution:** REMOVE endpoints in Sprint 61

---

## Problem Statement

Der Multihop Query Endpoint wurde in Sprint 34 implementiert. Es ist unklar, ob dieser Endpoint:
1. Noch funktional ist
2. Aktiv genutzt wird
3. In die neue Architektur (Sprint 53-58) integriert werden soll

---

## Analysis Reference

| Dokument | Inhalt |
|----------|--------|
| `docs/api/MULTI_HOP_ENDPOINTS.md` | Original Endpoint Dokumentation |

---

## Review Tasks ✅ COMPLETE

### 1. Funktionalitäts-Check
- [x] Endpoint erreichbar? ✅ YES (`/api/v1/graph/viz/multi-hop`)
- [x] Gibt es Unit/Integration Tests? ⚠️ PARTIAL (query logic tests, not API endpoint tests)
- [x] Funktioniert die Multi-Hop Logik? ✅ YES (fully functional, production-ready)

### 2. Usage Analysis
- [x] Wird der Endpoint vom Frontend genutzt? ❌ NO (zero frontend integration)
- [x] Gibt es Logs/Metriken zur Nutzung? ❌ NO (marked DEPRECATED 2025-12-07)
- [x] Ist die Funktionalität in Maximum Hybrid Search integriert? ❌ NO

### 3. Architecture Decision
- [x] Behalten und in neue Architektur migrieren? ❌ NO
- [x] Entfernen (Dead Code)? ✅ YES - **RECOMMENDED for Sprint 61**
- [x] In Agentic Search (Sprint 59) integrieren? ❌ NO (agents use LightRAG)

---

## Possible Outcomes

| Outcome | Action |
|---------|--------|
| Funktional + Genutzt | Migration zu `src/domains/query/` |
| Funktional + Ungenutzt | Entscheidung: Keep or Remove |
| Nicht funktional | Fix oder Remove |

---

## Related Files (to investigate)

```
src/api/v1/query.py (or similar)
src/agents/multi_hop_agent.py (if exists)
tests/*/test_multihop*.py
frontend/src/*multihop* (if exists)
```

---

## Acceptance Criteria ✅ ALL MET

- [x] Status dokumentiert ✅ FUNKTIONAL (production-ready but unused)
- [x] Usage dokumentiert ✅ UNGENUTZT (zero frontend usage for 12+ months)
- [x] Entscheidung getroffen ✅ REMOVE in Sprint 61
- [x] docs/api/MULTI_HOP_ENDPOINTS.md aktualisiert ✅ Will be archived in Sprint 61

---

## References

- [docs/api/MULTI_HOP_ENDPOINTS.md](../api/MULTI_HOP_ENDPOINTS.md)
- Sprint 34 Plan
- **[Comprehensive Review](../analysis/MULTIHOP_ENDPOINT_REVIEW.md)** ← Sprint 60 Feature 60.4 Output

---

## Review Summary (Sprint 60)

**Endpoints Found:**
- `POST /api/v1/graph/viz/multi-hop` (lines 752-884 in `graph_viz.py`)
- `POST /api/v1/graph/viz/shortest-path` (lines 889-960 in `graph_viz.py`)

**Status:**
- ✅ Fully functional, production-ready implementation
- ✅ Comprehensive Pydantic models and error handling
- ❌ Zero frontend usage (never integrated into UI)
- ❌ Zero backend usage (agents use LightRAG, not REST API)
- 🔴 Marked DEPRECATED on 2025-12-07

**Decision:** **REMOVE in Sprint 61**

**Rationale:**
1. No frontend integration after 12+ months
2. Backend agents use LightRAG directly, don't call REST API
3. Graph traversal handled client-side in frontend
4. Reduces API surface area and maintenance burden
5. Can re-implement from archived code if needed

**Sprint 61 Actions:**
1. Remove endpoints from `src/api/routers/graph_viz.py`
2. Remove Pydantic models (MultiHopRequest, MultiHopResponse, etc.)
3. Archive documentation to `docs/archive/`
4. Keep integration tests (`test_multi_hop_query.py` tests query logic, not API)

**See:** [docs/analysis/MULTIHOP_ENDPOINT_REVIEW.md](../analysis/MULTIHOP_ENDPOINT_REVIEW.md) for full analysis
