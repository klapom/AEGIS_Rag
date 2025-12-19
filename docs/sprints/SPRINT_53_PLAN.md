# Sprint 53: Quick Wins - Circular Dependencies & Admin Refactoring

**Status:** PLANNED
**Branch:** `sprint-53-refactoring-quick-wins`
**Start Date:** TBD
**Estimated Duration:** 5 Tage
**Total Story Points:** 34 SP

---

## Sprint Overview

Sprint 53 startet die **Refactoring-Initiative (ADR-046)** mit Quick Wins:
- Auflösung zirkulärer Dependencies (2 kritische Zyklen)
- Aufteilung des God-Object `admin.py` (4796 LOC)
- Dead Code Entfernung
- Grundlagen für folgende Refactoring-Sprints

**Referenz:** [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 53.1 | Circular Dependency Fix: Admin → CommunitySummarizer | 5 | P0 | Nein (Blocker) |
| 53.2 | Circular Dependency Fix: Extraction Factory Self-Import | 3 | P0 | Ja |
| 53.3 | Admin.py Split: Indexing Module | 8 | P1 | Ja (Agent 1) |
| 53.4 | Admin.py Split: Cost Module | 5 | P1 | Ja (Agent 2) |
| 53.5 | Admin.py Split: LLM Config Module | 5 | P1 | Ja (Agent 3) |
| 53.6 | Admin.py Split: Graph Analytics Module | 5 | P1 | Ja (Agent 4) |
| 53.7 | Dead Code Removal | 3 | P2 | Nach 53.1-53.6 |

**Total: 34 SP**

---

## Feature Details

### Feature 53.1: Circular Dependency Fix - Admin → CommunitySummarizer (5 SP)

**Priority:** P0 (Blocker)
**Problem:**
```
api.v1.admin
  → components.ingestion.parallel_orchestrator
    → components.ingestion.langgraph_pipeline
      → components.ingestion.langgraph_nodes
        → components.graph_rag.community_detector
          → components.graph_rag.community_summarizer
            → api.v1.admin  ← ZYKLUS!
```

**Root Cause:**
- `community_summarizer.py` importiert Admin-Settings für LLM Model Selection
- Admin-Settings sollten über Dependency Injection kommen

**Lösung: Protocol-basierte Dependency Injection**

```python
# src/components/graph_rag/protocols.py (NEW)
from typing import Protocol

class LLMConfigProvider(Protocol):
    """Protocol for LLM configuration providers."""

    async def get_community_summary_model(self) -> str:
        """Get the configured model for community summary generation."""
        ...

    async def get_extraction_model(self) -> str:
        """Get the configured model for entity extraction."""
        ...
```

**Betroffene Dateien:**

| Datei | Aktion | Zeilen |
|-------|--------|--------|
| `src/components/graph_rag/protocols.py` | CREATE | ~30 |
| `src/components/graph_rag/community_summarizer.py:46-80` | UPDATE | DI statt direkter Import |
| `src/api/v1/admin.py` | UPDATE | Implementiert LLMConfigProvider |
| `src/components/graph_rag/__init__.py` | UPDATE | Export Protocol |

**Verwendungsstellen:**
- `src/components/graph_rag/community_summarizer.py:46` - Constructor
- `src/components/graph_rag/community_detector.py:45` - Uses summarizer
- `src/components/ingestion/langgraph_nodes.py:45` - Imports community_detector

**Zwischenlösung (OPL-001):**
```python
# REFACTORING: OPL-001 - Lazy Import bis Sprint 53 abgeschlossen
# Nach Sprint 53: Ersetze durch Protocol-basierte DI
def _get_llm_config() -> str:
    from src.api.v1.admin import get_community_summary_model_config
    return get_community_summary_model_config()
```

**Acceptance Criteria:**
- [ ] Kein zirkulärer Import mehr bei `python -c "from src.api.v1.admin import router"`
- [ ] CommunitySummarizer nutzt Protocol für Config
- [ ] Alle Tests passieren
- [ ] OPL-001 dokumentiert und markiert

---

### Feature 53.2: Circular Dependency Fix - Extraction Factory (3 SP)

**Priority:** P0
**Problem:**
```
components.graph_rag.extraction_factory
  → components.graph_rag.lightrag_wrapper
    → components.graph_rag.lightrag_wrapper  ← SELF-IMPORT
```

**Root Cause:**
- Singleton Pattern mit Self-Import für Lazy Initialization

**Lösung: Separate Singleton Registry**

```python
# src/components/graph_rag/registry.py (NEW)
"""Singleton registry for graph components."""
from typing import Any

_instances: dict[str, Any] = {}

def get_instance(key: str) -> Any | None:
    return _instances.get(key)

def set_instance(key: str, instance: Any) -> None:
    _instances[key] = instance

def clear_instances() -> None:
    _instances.clear()
```

**Betroffene Dateien:**

| Datei | Aktion | Zeilen |
|-------|--------|--------|
| `src/components/graph_rag/registry.py` | CREATE | ~25 |
| `src/components/graph_rag/lightrag_wrapper.py:600-650` | UPDATE | Nutze Registry |
| `src/components/graph_rag/extraction_factory.py:28-40` | UPDATE | Nutze Registry |

**Verwendungsstellen:**
- `src/components/graph_rag/extraction_factory.py:28` - get_lightrag_wrapper_async
- `src/api/v1/admin.py:21` - Import wrapper
- `src/components/retrieval/maximum_hybrid_search.py` - Query execution
- 40+ Dateien nutzen lightrag_wrapper (siehe Grep-Ergebnis)

**Acceptance Criteria:**
- [ ] Kein Self-Import in lightrag_wrapper.py
- [ ] Registry ist thread-safe
- [ ] Singleton-Verhalten bleibt erhalten

---

### Feature 53.3: Admin.py Split - Indexing Module (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 1

**Ziel:** Extrahiere alle Re-Indexing Funktionalität in eigenes Modul.

**Neue Datei:** `src/api/v1/admin_indexing.py`

**Zu extrahierende Endpunkte:**
- `POST /admin/reindex` - Full re-index with SSE
- `POST /admin/reindex-incremental` - Incremental re-index
- `GET /admin/reindex-status` - Current indexing status
- `POST /admin/reindex-cancel` - Cancel ongoing re-index
- `GET /admin/last-reindex` - Last re-index timestamp

**Betroffene Code-Bereiche in admin.py:**
- Zeilen 43-95: Redis-basierte Timestamp-Funktionen
- Zeilen 100-350: Re-Indexing SSE Endpoint
- Zeilen 350-500: Incremental Re-Indexing
- Zeilen 500-600: Status und Cancel Endpoints

**Router-Integration:**

```python
# src/api/v1/admin_indexing.py
from fastapi import APIRouter
router = APIRouter(prefix="/admin", tags=["admin-indexing"])

# src/api/v1/__init__.py (UPDATE)
from src.api.v1.admin_indexing import router as admin_indexing_router
```

**Verwendungsstellen:**
- `src/api/main.py:45` - Router registration
- `frontend/src/hooks/useIndexing.ts` - API calls
- `frontend/src/pages/admin/IndexingPage.tsx` - UI
- `tests/api/v1/test_admin_reindex.py` - Tests

**Acceptance Criteria:**
- [ ] Alle Indexing-Endpoints in admin_indexing.py
- [ ] Router in main.py registriert
- [ ] Frontend funktioniert ohne Änderung (gleiche API Pfade)
- [ ] Tests passieren

---

### Feature 53.4: Admin.py Split - Cost Module (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 2

**Ziel:** Extrahiere Cost Tracking und Budget Management.

**Neue Datei:** `src/api/v1/admin_costs.py`

**Zu extrahierende Endpunkte:**
- `GET /admin/costs` - Cost statistics
- `GET /admin/costs/history` - Cost history over time
- `GET /admin/costs/by-provider` - Costs per LLM provider
- `GET /admin/budget-status` - Budget alerts

**Betroffene Code-Bereiche in admin.py:**
- Import `CostStats`, `ProviderCost`, `ModelCost`, `BudgetStatus`, `CostHistory`
- Cost-related endpoints (ca. Zeilen 700-1000)

**Verwendungsstellen:**
- `frontend/src/pages/admin/CostDashboardPage.tsx`
- `frontend/src/hooks/useCostTracking.ts`
- `tests/api/v1/test_admin_costs.py`

**Acceptance Criteria:**
- [ ] Alle Cost-Endpoints in admin_costs.py
- [ ] Pydantic Models bleiben in `src/api/models/cost_stats.py`
- [ ] Frontend funktioniert ohne Änderung

---

### Feature 53.5: Admin.py Split - LLM Config Module (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 3

**Ziel:** Extrahiere LLM Configuration und Model Management.

**Neue Datei:** `src/api/v1/admin_llm.py`

**Zu extrahierende Endpunkte:**
- `GET /admin/llm-config` - Current LLM configuration
- `PUT /admin/llm-config` - Update LLM settings
- `POST /admin/llm-test` - Test LLM connection
- `GET /admin/llm-models` - Available models
- `GET /admin/community-summary-model` - Model for summaries (Feature 52.1)
- `PUT /admin/community-summary-model` - Set summary model

**Betroffene Code-Bereiche:**
- LLM Configuration endpoints (ca. Zeilen 1200-1500)
- Community summary model config (Sprint 52 Feature)

**WICHTIG für Sprint 59:**
Diese Endpoints werden in Sprint 59 erweitert für Tool Use und Agentic Features.
Stelle sicher, dass die Struktur erweiterbar ist.

**Verwendungsstellen:**
- `frontend/src/pages/admin/AdminLLMConfigPage.tsx`
- `src/components/graph_rag/community_summarizer.py` (nach 53.1 Fix)

**Acceptance Criteria:**
- [ ] Alle LLM-Config Endpoints in admin_llm.py
- [ ] Erweiterbar für Sprint 59 Features

---

### Feature 53.6: Admin.py Split - Graph Analytics Module (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 4

**Ziel:** Extrahiere Graph Analytics und Neo4j Statistics.

**Neue Datei:** `src/api/v1/admin_graph.py`

**Zu extrahierende Endpunkte:**
- `GET /admin/graph/stats` - Entity/Relationship counts
- `GET /admin/graph/communities` - Community list with stats
- `GET /admin/graph/health` - Graph health metrics
- `POST /admin/graph/detect-communities` - Trigger detection
- `GET /admin/graph/export` - Export graph data

**Betroffene Code-Bereiche:**
- Graph statistics endpoints (ca. Zeilen 1500-1800)
- Community management (Sprint 52 Feature 52.2)

**Verwendungsstellen:**
- `frontend/src/pages/admin/GraphAnalyticsPage.tsx`
- `tests/e2e/test_e2e_graph_analytics.py`

**Acceptance Criteria:**
- [ ] Alle Graph-Endpoints in admin_graph.py
- [ ] Community Detection aufrufbar

---

### Feature 53.7: Dead Code Removal (3 SP)

**Priority:** P2
**Abhängigkeit:** Nach 53.1-53.6

**Zu entfernender Dead Code (Vulture-Analyse):**

| Datei | Zeile | Element | Confidence |
|-------|-------|---------|------------|
| `title_generator.py` | 17 | `max_length` unused | 90% |
| `progress_events.py` | 209 | `base_message` unused | 90% |
| `ingestion.py` | 340 | `required_exts` unused | 80% |
| `semantic_relation_deduplicator.py` | 30 | `cosine` unused import | 100% |
| `progress_events.py` | 33 | `timezone` unused import | 100% |

**Context Manager Boilerplate (6 Dateien):**
- Ersetze ungenutzte `exc_type, exc_val, exc_tb` mit `*_`

**Acceptance Criteria:**
- [ ] Alle identifizierten Dead Code Elemente entfernt
- [ ] Keine neuen Ruff/MyPy Fehler
- [ ] Tests passieren

---

## Parallel Execution Strategy

### Wave 1 (Tag 1): Circular Dependencies (Sequential)

```
Agent 1: Feature 53.1 - CommunitySummarizer DI Fix
         → Blockt alle anderen Features

Nach Abschluss 53.1:
Agent 2: Feature 53.2 - Extraction Factory Fix (parallel möglich)
```

### Wave 2 (Tag 2-4): Admin Split (4 Agents parallel)

```
┌─────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                    │
├──────────────┬──────────────┬──────────────┬────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │  Agent 4   │
│   53.3       │   53.4       │   53.5       │  53.6      │
│   Indexing   │   Costs      │   LLM Config │  Graph     │
│   8 SP       │   5 SP       │   5 SP       │  5 SP      │
└──────────────┴──────────────┴──────────────┴────────────┘
```

### Wave 3 (Tag 5): Cleanup & Integration

```
Agent 1: Feature 53.7 - Dead Code Removal
Agent 2: Integration Tests
Agent 3: Documentation Updates
Agent 4: Router Consolidation in main.py
```

---

## Router Consolidation (main.py)

Nach dem Split muss `src/api/main.py` aktualisiert werden:

```python
# src/api/main.py - Nach Sprint 53
from src.api.v1.admin import router as admin_router  # Core admin (reduced)
from src.api.v1.admin_indexing import router as admin_indexing_router
from src.api.v1.admin_costs import router as admin_costs_router
from src.api.v1.admin_llm import router as admin_llm_router
from src.api.v1.admin_graph import router as admin_graph_router

# Register all admin routers
app.include_router(admin_router, prefix="/api/v1")
app.include_router(admin_indexing_router, prefix="/api/v1")
app.include_router(admin_costs_router, prefix="/api/v1")
app.include_router(admin_llm_router, prefix="/api/v1")
app.include_router(admin_graph_router, prefix="/api/v1")
```

---

## Refactoring OPL Entries

Die folgenden temporären Lösungen werden in REFACTORING_OPL.md dokumentiert:

| OPL-ID | Feature | Beschreibung | Auflösung in |
|--------|---------|--------------|--------------|
| OPL-001 | 53.1 | Lazy Import für LLM Config Provider | Sprint 53 |
| OPL-002 | 53.3-53.6 | Backward-Compat Imports in admin.py | Sprint 54 |

---

## Acceptance Criteria (Sprint Complete)

- [ ] 0 zirkuläre Dependencies (`python -c "from src.api.main import app"` erfolgreich)
- [ ] admin.py < 500 LOC (von 4796)
- [ ] 4 neue Admin-Module erstellt
- [ ] Alle Frontend-Features funktionieren
- [ ] Alle Tests passieren (Unit + Integration + E2E)
- [ ] REFACTORING_OPL.md dokumentiert temporäre Lösungen
- [ ] ADR-046 Status auf "In Progress"

---

## Risk Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Import-Fehler nach Split | Medium | High | Schrittweise Migration, Tests nach jedem Modul |
| Frontend-Breakage | Low | High | API-Pfade bleiben identisch |
| Circular Dep nicht vollständig aufgelöst | Low | Critical | Protocol-Pattern, umfangreiche Tests |

---

## Definition of Done

### Per Feature
- [ ] Implementation abgeschlossen
- [ ] Unit Tests angepasst/erweitert
- [ ] Integration Tests passieren
- [ ] Code Review
- [ ] Dokumentation aktualisiert

### Sprint Complete
- [ ] Alle Features merged
- [ ] CI/CD Pipeline grün
- [ ] Sprint Summary erstellt
- [ ] REFACTORING_OPL.md aktuell
- [ ] ADR-046 aktualisiert

---

---

## Subagent-Anweisungen: OPL & Dead Code

**WICHTIG:** Jeder Subagent MUSS bei Refactoring-Arbeiten folgende Dokumente pflegen:

### 1. REFACTORING_OPL.md (Zwischenlösungen)

Bei **temporären Lösungen** (Lazy Imports, Re-Exports, Backward-Compat):
- Neuen OPL-XXX Eintrag erstellen
- Code-Kommentar: `# OPL-XXX: Beschreibung`
- Verwendungsstellen dokumentieren
- Auflösungs-Sprint angeben

### 2. Dead Code Tracking (DC-XXX)

Bei **Code der ersetzt wird** aber noch nicht gelöscht werden kann:
- Neuen DC-XXX Eintrag in REFACTORING_OPL.md erstellen
- Kategorie wählen: ORPHANED / DEPRECATED / LEGACY_COMPAT
- Verification-Script dokumentieren
- Entfernungs-Sprint angeben

**Beispiel für Sprint 53:**
```
Nach admin.py Split:
- Alte Funktionen → DC-001 (DEPRECATED, Entfernung Sprint 54)
- Vulture Findings → DC-005 (ORPHANED, Entfernung Sprint 53)
```

### 3. Verification vor Entfernung

```bash
# Standard-Check vor Dead Code Entfernung
grep -r "from <old_module> import" src/ tests/ --include="*.py"
# Ergebnis: 0 → sicher zu entfernen
```

### 4. Checkliste pro Feature

- [ ] Feature implementiert
- [ ] OPL-Eintrag erstellt (falls Zwischenlösung)
- [ ] DC-Eintrag erstellt (falls Code ersetzt)
- [ ] Code-Kommentare mit OPL/DC-IDs
- [ ] REFACTORING_OPL.md aktualisiert

---

## References

- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [ANALYSIS_SPRINT_REPORT.md](../refactoring/ANALYSIS_SPRINT_REPORT.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **OPL + Dead Code Tracking**

---

**END OF SPRINT 53 PLAN**
