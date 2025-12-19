# REFACTORING Open Point List (OPL)

**Stand:** 2025-12-19
**Sprint-Range:** 53-58
**Ziel:** Alle Einträge bis Ende Sprint 58 aufgelöst

---

## Zweck dieses Dokuments

Diese OPL dokumentiert **alle temporären Lösungen** (Workarounds, Backward-Compatibility Shims,
Lazy Imports), die während des Refactorings eingeführt werden.

**KRITISCH:** Am Ende von Sprint 58 dürfen hier **keine offenen Einträge** mehr existieren.

---

## Status-Legende

| Status | Bedeutung |
|--------|-----------|
| OPEN | Temporäre Lösung aktiv, noch nicht aufgelöst |
| IN_PROGRESS | Auflösung in Arbeit |
| RESOLVED | Aufgelöst, kann entfernt werden |
| REMOVED | Code und OPL-Eintrag entfernt |

---

## Sprint 53: Quick Wins

### OPL-001: Lazy Import für LLM Config Provider

| Feld | Wert |
|------|------|
| **ID** | OPL-001 |
| **Status** | OPEN |
| **Erstellt** | Sprint 53 |
| **Auflösung geplant** | Sprint 53 (Ende) |
| **Feature** | 53.1 - Circular Dependency Fix |

**Problem:**
`CommunitySummarizer` benötigt LLM Config aus Admin-Modul, aber direkter Import erzeugt Zyklus.

**Temporäre Lösung:**
```python
# src/components/graph_rag/community_summarizer.py
# OPL-001: Lazy Import bis Protocol implementiert
def _get_llm_config() -> str:
    from src.api.v1.admin_llm import get_community_summary_model_config
    return get_community_summary_model_config()
```

**Verwendungsstellen:**
- `src/components/graph_rag/community_summarizer.py:50`

**Finale Lösung:**
Protocol-basierte Dependency Injection via `LLMConfigProvider`.

**Auflösungsschritte:**
1. [ ] `protocols.py` mit `LLMConfigProvider` erstellen
2. [ ] `CommunitySummarizer.__init__` auf DI umstellen
3. [ ] Lazy Import entfernen
4. [ ] Tests anpassen
5. [ ] OPL-001 Status auf RESOLVED setzen

---

### OPL-002: Backward-Compat Imports in admin.py

| Feld | Wert |
|------|------|
| **ID** | OPL-002 |
| **Status** | OPEN |
| **Erstellt** | Sprint 53 |
| **Auflösung geplant** | Sprint 54 |
| **Feature** | 53.3-53.6 - Admin Split |

**Problem:**
Nach Split von admin.py könnten externe Scripts/Tests alte Imports verwenden.

**Temporäre Lösung:**
```python
# src/api/v1/admin.py - Reduced file after split
# OPL-002: Backward-compatibility re-exports until Sprint 54
from src.api.v1.admin_indexing import (
    reindex_documents,
    get_reindex_status,
)
from src.api.v1.admin_costs import (
    get_cost_stats,
    get_cost_history,
)
# ... weitere Re-Exports
```

**Verwendungsstellen:**
- `scripts/archive/*` - Alte Scripts
- `tests/api/v1/test_admin_*.py` - Tests mit alten Imports

**Finale Lösung:**
Alle Imports auf neue Module umstellen, Re-Exports entfernen.

**Auflösungsschritte:**
1. [ ] Alle Verwendungsstellen identifizieren (grep)
2. [ ] Imports auf neue Module umstellen
3. [ ] Re-Exports aus admin.py entfernen
4. [ ] Tests validieren
5. [ ] OPL-002 Status auf RESOLVED setzen

---

## Sprint 54: langgraph_nodes Refactoring

### OPL-003: Legacy Node Function Aliases

| Feld | Wert |
|------|------|
| **ID** | OPL-003 |
| **Status** | OPEN |
| **Erstellt** | Sprint 54 |
| **Auflösung geplant** | Sprint 55 |
| **Feature** | 54.1-54.6 - langgraph_nodes Split |

**Problem:**
`langgraph_pipeline.py` importiert Node-Funktionen direkt aus `langgraph_nodes.py`.

**Temporäre Lösung:**
```python
# src/components/ingestion/langgraph_nodes.py - After split
# OPL-003: Backward-compat aliases until Sprint 55
from src.components.ingestion.nodes.memory_management import memory_check_node
from src.components.ingestion.nodes.document_parsers import docling_parse_node
from src.components.ingestion.nodes.image_enrichment import image_enrichment_node
from src.components.ingestion.nodes.adaptive_chunking import chunking_node
from src.components.ingestion.nodes.vector_embedding import embedding_node
from src.components.ingestion.nodes.graph_extraction import graph_extraction_node

# Re-export for backward compatibility
__all__ = [
    "memory_check_node",
    "docling_parse_node",
    "image_enrichment_node",
    "chunking_node",
    "embedding_node",
    "graph_extraction_node",
]
```

**Verwendungsstellen:**
- `src/components/ingestion/langgraph_pipeline.py:35-45`
- `src/components/ingestion/streaming_pipeline.py:20-30`
- `tests/unit/components/ingestion/test_langgraph_nodes_unit.py`
- 22+ Dateien (siehe Analyse)

**Finale Lösung:**
Direkte Imports aus `nodes/` Submodulen.

---

### OPL-004: Shared State Dataclasses

| Feld | Wert |
|------|------|
| **ID** | OPL-004 |
| **Status** | OPEN |
| **Erstellt** | Sprint 54 |
| **Auflösung geplant** | Sprint 56 |
| **Feature** | 54.1 - langgraph_nodes Split |

**Problem:**
Dataclasses `SectionMetadata` und `AdaptiveChunk` werden in mehreren Nodes verwendet.

**Temporäre Lösung:**
Dataclasses in separates Modul, aber noch in `langgraph_nodes.py` re-exportiert.

**Verwendungsstellen:**
- `src/components/ingestion/nodes/adaptive_chunking.py`
- `src/components/ingestion/nodes/document_parsers.py`
- `src/components/ingestion/section_extraction.py`

**Finale Lösung:**
Move to `src/components/ingestion/models.py` in Sprint 56 (Domain Boundaries).

---

## Sprint 55: lightrag_wrapper Refactoring

### OPL-005: Singleton Wrapper Function

| Feld | Wert |
|------|------|
| **ID** | OPL-005 |
| **Status** | OPEN |
| **Erstellt** | Sprint 55 |
| **Auflösung geplant** | Sprint 56 |
| **Feature** | 55.1-55.6 - lightrag_wrapper Split |

**Problem:**
`get_lightrag_wrapper_async()` ist als Singleton implementiert und wird in 40+ Dateien verwendet.

**Temporäre Lösung:**
```python
# src/components/graph_rag/lightrag_wrapper.py - Facade
# OPL-005: Singleton wrapper for backward compat until Sprint 56
from src.components.graph_rag.lightrag.client import LightRAGClient
from src.components.graph_rag.registry import get_instance, set_instance

async def get_lightrag_wrapper_async() -> LightRAGClient:
    """Backward-compatible singleton accessor."""
    instance = get_instance("lightrag_client")
    if instance is None:
        from src.components.graph_rag.lightrag.initialization import create_lightrag_client
        instance = await create_lightrag_client()
        set_instance("lightrag_client", instance)
    return instance
```

**Verwendungsstellen:**
- 40+ Dateien (siehe Analyse)

**Finale Lösung:**
Dependency Injection via Factory Pattern in Sprint 56.

---

## Sprint 56: Domain Boundaries

### OPL-006: Cross-Domain Imports

| Feld | Wert |
|------|------|
| **ID** | OPL-006 |
| **Status** | OPEN |
| **Erstellt** | Sprint 56 |
| **Auflösung geplant** | Sprint 57 |
| **Feature** | 56.x - Domain Boundaries |

**Problem:**
Während Domain-Restrukturierung werden temporäre Cross-Domain Imports benötigt.

**Temporäre Lösung:**
Explicit re-exports in Domain `__init__.py` files.

**Finale Lösung:**
Interface-basierte Kommunikation zwischen Domains (Sprint 57).

---

## Sprint 57: Interfaces & Protocols

### OPL-007: Concrete Type Dependencies

| Feld | Wert |
|------|------|
| **ID** | OPL-007 |
| **Status** | OPEN |
| **Erstellt** | Sprint 57 |
| **Auflösung geplant** | Sprint 58 |
| **Feature** | 57.x - Interface Extraction |

**Problem:**
Einige Module verwenden noch konkrete Typen statt Protocols.

**Temporäre Lösung:**
Graduelle Migration mit `# type: ignore` wo nötig.

**Finale Lösung:**
Vollständige Protocol-Implementierung.

---

## Sprint 58: Test Coverage & Cleanup

**Ziel Sprint 58:** Alle verbleibenden OPL-Einträge auflösen.

Nach Sprint 58 sollte diese Datei nur noch REMOVED-Einträge enthalten (als Dokumentation).

---

## Zusammenfassung

| Sprint | OPL-IDs | Status |
|--------|---------|--------|
| 53 | OPL-001, OPL-002 | OPEN |
| 54 | OPL-003, OPL-004 | OPEN |
| 55 | OPL-005 | OPEN |
| 56 | OPL-006 | OPEN |
| 57 | OPL-007 | OPEN |
| 58 | Cleanup | - |

**Total Open:** 7
**Target End Sprint 58:** 0

---

## Anweisungen für Subagenten

**WICHTIG:** Jeder Subagent muss bei Refactoring-Arbeiten:

1. **Prüfen:** Existiert bereits ein OPL-Eintrag für diese Änderung?
2. **Erstellen:** Neue temporäre Lösung? → Neuen OPL-Eintrag anlegen
3. **Markieren:** Code-Kommentar mit OPL-ID: `# OPL-XXX: Beschreibung`
4. **Dokumentieren:** Alle Verwendungsstellen auflisten
5. **Planen:** Auflösung in welchem Sprint?

**Code-Kommentar Format:**
```python
# OPL-XXX: [Kurzbeschreibung]
# Temporäre Lösung bis Sprint YY
# Siehe: docs/refactoring/REFACTORING_OPL.md
```

---

---

## Dead Code Tracking

### Strategie

Dead Code wird in 3 Kategorien eingeteilt:

| Kategorie | Beschreibung | Retention | Aktion |
|-----------|--------------|-----------|--------|
| **DEPRECATED** | Ersetzt durch neue Implementierung | 1 Sprint | Entfernen nach Verification |
| **ORPHANED** | Keine Verwendung gefunden | Sofort | Entfernen mit PR |
| **LEGACY_COMPAT** | Backward-Compatibility | Bis OPL resolved | Mit OPL entfernen |

### Dead Code Register

#### DC-001: Alte Admin-Funktionen (Sprint 53)

| Feld | Wert |
|------|------|
| **ID** | DC-001 |
| **Kategorie** | DEPRECATED |
| **Erstellt** | Sprint 53 |
| **Entfernung** | Sprint 54 |
| **Dateien** | `src/api/v1/admin.py` (nach Split) |

**Betroffene Elemente:**
- Originale Endpoint-Funktionen (nach Extraktion in admin_*.py)
- Lokale Helper-Funktionen die nicht mehr gebraucht werden

**Verification vor Entfernung:**
```bash
# Prüfe ob alte Imports noch verwendet werden
grep -r "from src.api.v1.admin import" src/ tests/ --include="*.py"
```

---

#### DC-002: langgraph_nodes.py Originale (Sprint 54)

| Feld | Wert |
|------|------|
| **ID** | DC-002 |
| **Kategorie** | DEPRECATED |
| **Erstellt** | Sprint 54 |
| **Entfernung** | Sprint 55 |
| **Dateien** | `src/components/ingestion/langgraph_nodes.py` |

**Betroffene Elemente:**
- Komplette Node-Implementierungen (nach Extraktion in nodes/)
- Nur Re-Exports bleiben (OPL-003)

**Verification vor Entfernung:**
```bash
# Prüfe direkte Imports (sollten nur noch von nodes/ kommen)
grep -r "from src.components.ingestion.langgraph_nodes import" src/ --include="*.py"
```

---

#### DC-003: lightrag_wrapper.py Originale (Sprint 55)

| Feld | Wert |
|------|------|
| **ID** | DC-003 |
| **Kategorie** | DEPRECATED |
| **Erstellt** | Sprint 55 |
| **Entfernung** | Sprint 56 |
| **Dateien** | `src/components/graph_rag/lightrag_wrapper.py` |

**Betroffene Elemente:**
- LightRAGClient Implementierung (nach Migration zu lightrag/)
- Nur Singleton-Funktion bleibt (OPL-005)

---

#### DC-004: Backward-Compat Re-Exports (Sprint 56)

| Feld | Wert |
|------|------|
| **ID** | DC-004 |
| **Kategorie** | LEGACY_COMPAT |
| **Erstellt** | Sprint 56 |
| **Entfernung** | Sprint 58 |
| **Dateien** | Alle `__init__.py` mit OPL Re-Exports |

**Betroffene Elemente:**
- `src/components/graph_rag/__init__.py` - OPL-006 Re-Exports
- `src/components/ingestion/__init__.py` - OPL-003 Re-Exports
- `src/api/v1/admin.py` - OPL-002 Re-Exports

---

#### DC-005: Vulture-identifizierter Dead Code (Sprint 53)

| Feld | Wert |
|------|------|
| **ID** | DC-005 |
| **Kategorie** | ORPHANED |
| **Erstellt** | Sprint 53 |
| **Entfernung** | Sprint 53 (Feature 53.7) |

**Betroffene Elemente (aus Analyse):**

| Datei | Zeile | Element | Confidence |
|-------|-------|---------|------------|
| `title_generator.py` | 17 | `max_length` | 90% |
| `progress_events.py` | 209 | `base_message` | 90% |
| `ingestion.py` | 340 | `required_exts` | 80% |
| `semantic_relation_deduplicator.py` | 30 | `cosine` import | 100% |
| `progress_events.py` | 33 | `timezone` import | 100% |

---

### Dead Code Removal Prozess

1. **Identifizieren:** Vulture/Ruff in CI integrieren
2. **Registrieren:** DC-XXX Eintrag erstellen
3. **Verification:** Prüfscript ausführen
4. **PR erstellen:** Mit DC-XXX Referenz
5. **Entfernen:** Nach Review mergen
6. **Status:** DC-XXX auf REMOVED setzen

### CI Integration

```yaml
# .github/workflows/dead-code-check.yml
name: Dead Code Check
on: [push, pull_request]
jobs:
  vulture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install vulture
      - run: vulture src/ --min-confidence 90
```

### Metriken

| Sprint | DC Einträge | REMOVED | Verbleibend |
|--------|-------------|---------|-------------|
| 53 | DC-001, DC-005 | DC-005 | 1 |
| 54 | DC-002 | DC-001 | 2 |
| 55 | DC-003 | DC-002 | 2 |
| 56 | DC-004 | DC-003 | 2 |
| 58 | - | DC-004 | 0 |

**Ziel Sprint 58:** 0 Dead Code Einträge

---

**END OF REFACTORING_OPL.md**
