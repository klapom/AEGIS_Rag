# Sprint 58.7: Deprecated Code Cleanup Candidates

**Status:** PENDING REVIEW
**Erstellt:** 2025-12-19
**Review vor Durchführung erforderlich!**

---

## Zusammenfassung

Analyse aller "backward", "compat", "legacy", "deprecated" Marker im Code.
Cleanup erst nach detaillierter Prüfung durchführen.

---

## Kategorie 1: Deprecated Dateien (Komplett entfernen)

### 1.1 `src/components/vector_search/embeddings.py`

**Deprecation:** Sprint 25 Feature 25.8
**Grund:** Ersetzt durch `src/components/shared/embedding_service.py`
**Aktuelle Nutzung prüfen:**
```bash
grep -r "from src.components.vector_search.embeddings import" src/ tests/
grep -r "from src.components.vector_search import.*EmbeddingService" src/ tests/
```

**Inhalt:**
- Re-exports von `shared/embedding_service.py`
- Deprecation warning bei Import

---

### 1.2 `src/components/vector_search/ingestion.py`

**Deprecation:** Sprint 21/25 (ADR-028)
**Grund:** Ersetzt durch LangGraph Pipeline
**Aktuelle Nutzung prüfen:**
```bash
grep -r "from src.components.vector_search.ingestion import" src/ tests/
grep -r "DocumentIngestionPipeline" src/ tests/
```

**Inhalt:**
- `DocumentIngestionPipeline` class
- `index_documents()` deprecated method
- LlamaIndex-basierte Ingestion

---

### 1.3 `src/api/v1/retrieval.py`

**Deprecation:** 2025-12-07 (nicht vom Frontend verwendet)
**Grund:** Frontend nutzt `/api/v1/chat` stattdessen
**Aktuelle Nutzung prüfen:**
```bash
grep -r "retrieval_router" src/
grep -r "/api/v1/retrieval" frontend/
```

**Inhalt:**
- `/retrieve` endpoint
- Standalone retrieval ohne Chat-Kontext

---

## Kategorie 2: Deprecated Endpoints (In bestehenden Dateien)

### 2.1 `src/api/routers/graph_viz.py` - 5 Endpoints

| Zeile | Endpoint | Status |
|-------|----------|--------|
| 338 | Nicht identifiziert | DEPRECATED |
| 365 | Nicht identifiziert | DEPRECATED |
| 422 | Nicht identifiziert | DEPRECATED |
| 750 | Nicht identifiziert | DEPRECATED |
| 887 | Nicht identifiziert | DEPRECATED |

**Prüfen:**
```bash
grep -r "graph_viz" frontend/
```

---

## Kategorie 3: Deprecated Aliases (Niedrige Priorität)

### 3.1 `src/components/ingestion/nodes/document_parsers.py:215`

**Alias:** `docling_parse_node` → `docling_extraction_node`
**Deprecation:** Sprint 54
**Nutzung prüfen:**
```bash
grep -r "docling_parse_node" src/ tests/
```

---

### 3.2 `src/components/graph_rag/lightrag_wrapper.py:41-46`

**Aliases:**
- `LightRAGWrapper` → `LightRAGClient`
- `get_lightrag_wrapper` → `get_lightrag_client`
- `get_lightrag_wrapper_async` → `get_lightrag_client_async`

**Deprecation:** Sprint 55
**Nutzung prüfen:**
```bash
grep -r "LightRAGWrapper" src/ tests/
grep -r "get_lightrag_wrapper" src/ tests/
```

---

## Kategorie 4: Legacy Features (BEHALTEN)

Diese Features sind absichtlich für Kompatibilität/Testing:

| Feature | Datei | Grund |
|---------|-------|-------|
| `enable_legacy_extraction` | core/config.py | A/B Testing |
| `lightrag_default` mode | core/config.py | Baseline |
| `LegacyLightRAGExtractor` | extraction_factory.py | A/B Testing |
| `LEGACY_UNSUPPORTED` | format_router.py | .doc/.xls/.ppt Warnung |
| Legacy namespace | core/namespace.py | Existing data |

---

## Kategorie 5: Backward-Compat Facades (BEHALTEN)

Diese Facades sind absichtlich für Sprint 56 DDD Migration:

- `components/llm_proxy/__init__.py` → `domains/llm_integration`
- `components/ingestion/langgraph_nodes.py` → `nodes/`
- `components/graph_rag/lightrag_wrapper.py` → `lightrag/`
- `infrastructure/*` → `core/`

**NICHT ENTFERNEN** - Diese ermöglichen schrittweise Migration.

---

## Review-Checkliste vor Cleanup

- [ ] Alle `grep` Befehle ausführen
- [ ] Frontend-Nutzung verifizieren
- [ ] Test-Abhängigkeiten prüfen
- [ ] Import-Pfade in externen Scripts prüfen
- [ ] CI/CD Pipeline grün nach Änderungen

---

## Cleanup-Reihenfolge (nach Review)

1. **Priorität 1:** Unbenutzte Dateien entfernen
2. **Priorität 2:** Deprecated Endpoints entfernen
3. **Priorität 3:** Aliases aufräumen (nach Migration)

---

**WICHTIG:** Dieses Dokument dient als Referenz.
Cleanup erst nach expliziter Bestätigung durchführen!
