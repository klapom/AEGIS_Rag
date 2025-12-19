# TD-069: Multihop Endpoint Status Review

**Status:** OPEN (Review Required)
**Priority:** LOW
**Story Points:** 3
**Created:** Sprint 60 Planning
**Target:** Sprint 60 (Review Only)

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

## Review Tasks

### 1. Funktionalitäts-Check
- [ ] Endpoint erreichbar? (`/api/v1/query/multihop`)
- [ ] Gibt es Unit/Integration Tests?
- [ ] Funktioniert die Multi-Hop Logik?

### 2. Usage Analysis
- [ ] Wird der Endpoint vom Frontend genutzt?
- [ ] Gibt es Logs/Metriken zur Nutzung?
- [ ] Ist die Funktionalität in Maximum Hybrid Search integriert?

### 3. Architecture Decision
- [ ] Behalten und in neue Architektur migrieren?
- [ ] Entfernen (Dead Code)?
- [ ] In Agentic Search (Sprint 59) integrieren?

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

## Acceptance Criteria

- [ ] Status dokumentiert (funktional/nicht funktional)
- [ ] Usage dokumentiert (genutzt/ungenutzt)
- [ ] Entscheidung getroffen (keep/migrate/remove)
- [ ] docs/api/MULTI_HOP_ENDPOINTS.md aktualisiert oder archiviert

---

## References

- [docs/api/MULTI_HOP_ENDPOINTS.md](../api/MULTI_HOP_ENDPOINTS.md)
- Sprint 34 Plan
