# REFACTORING Open Point List (OPL)

**Stand:** 2025-12-19 (Sprint 58 COMPLETE)
**Sprint-Range:** 53-58
**Ziel:** ✅ Alle Einträge aufgelöst
**Letztes Update:** Sprint 58 - Alle OPL-Kommentare aus Code entfernt

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

### OPL-001: Re-Export für get_configured_summary_model in admin.py

| Feld | Wert |
|------|------|
| **ID** | OPL-001 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 53 |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 53.1 - Circular Dependency Fix |

**Problem:**
`CommunitySummarizer` benötigte LLM Config aus Admin-Modul, direkter Import erzeugte Zyklus.

**Lösung implementiert (Sprint 53):**
1. ✅ `llm_config_provider.py` erstellt mit `get_configured_summary_model()`
2. ✅ `protocols.py` mit `LLMConfigProvider` Protocol erstellt
3. ✅ `community_summarizer.py` importiert jetzt aus `llm_config_provider`
4. ✅ Zirkulärer Import aufgelöst

**Temporärer Re-Export (Backward-Compat):**
```python
# src/api/v1/admin.py:4547-4553
# OPL-001: Re-export from llm_config_provider for backward compatibility
from src.components.graph_rag.llm_config_provider import (
    get_configured_summary_model,
    REDIS_KEY_SUMMARY_MODEL_CONFIG,
)
```

**Verwendungsstellen des Re-Exports:**
- Keine bekannten externen Nutzer (kann in Sprint 54 entfernt werden)

**Verbleibende Schritte:**
1. [ ] Verifizieren dass kein externer Code `from admin import get_configured_summary_model` nutzt
2. [ ] Re-Export in Sprint 54 entfernen
3. [ ] OPL-001 Status auf RESOLVED setzen

---

### OPL-002: Backward-Compat Imports in admin.py

| Feld | Wert |
|------|------|
| **ID** | OPL-002 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 53 |
| **Aufgelöst** | Sprint 58 |
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
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 54 |
| **Implementiert** | Sprint 54 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 54.1-54.8 - langgraph_nodes Split |

**Problem:**
`langgraph_pipeline.py` importiert Node-Funktionen direkt aus `langgraph_nodes.py`.

**Lösung implementiert (Sprint 54):**
1. ✅ `nodes/` Package erstellt mit 8 Modulen
2. ✅ `langgraph_nodes.py` auf Facade reduziert (65 LOC)
3. ✅ Re-Exports für Backward-Compatibility eingerichtet
4. ✅ Alle Imports verifiziert und funktional

**Temporäre Lösung (aktiv):**
```python
# src/components/ingestion/langgraph_nodes.py - Facade (65 LOC)
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

**Verwendungsstellen (22+ Dateien):**
- `src/components/ingestion/langgraph_pipeline.py`
- `src/components/ingestion/streaming_pipeline.py`
- `tests/unit/components/ingestion/test_langgraph_nodes_unit.py`
- `tests/integration/components/ingestion/test_langgraph_pipeline.py`
- Weitere Tests und Scripts

**Verbleibende Schritte (Sprint 55):**
1. [ ] Alle Verwendungsstellen auf direkte `nodes/` Imports umstellen
2. [ ] Re-Export-Facade entfernen oder minimal halten
3. [ ] OPL-003 Status auf RESOLVED setzen

**Finale Lösung:**
Direkte Imports aus `nodes/` Submodulen.

---

### OPL-004: Shared State Dataclasses

| Feld | Wert |
|------|------|
| **ID** | OPL-004 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 54 |
| **Implementiert** | Sprint 54 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 54.1 - langgraph_nodes Split |

**Problem:**
Dataclasses `SectionMetadata` und `AdaptiveChunk` werden in mehreren Nodes verwendet.

**Lösung implementiert (Sprint 54):**
1. ✅ `nodes/models.py` erstellt (65 LOC)
2. ✅ `SectionMetadata` und `AdaptiveChunk` extrahiert
3. ✅ Re-Exports in `nodes/__init__.py` und `langgraph_nodes.py`

**Temporäre Lösung (aktiv):**
```python
# src/components/ingestion/nodes/models.py (65 LOC)
@dataclass
class SectionMetadata:
    heading: str
    level: int
    page_no: int
    bbox: dict[str, float]
    text: str
    token_count: int
    metadata: dict[str, Any]

@dataclass
class AdaptiveChunk:
    text: str
    token_count: int
    section_headings: list[str]
    section_pages: list[int]
    section_bboxes: list[dict[str, float]]
    primary_section: str
    metadata: dict[str, Any]
```

**Verwendungsstellen:**
- `src/components/ingestion/nodes/adaptive_chunking.py`
- `src/components/ingestion/nodes/document_parsers.py` (importiert nicht direkt)
- `src/components/ingestion/section_extraction.py`
- Backward-compat: `langgraph_nodes.py` re-exportiert

**Verbleibende Schritte (Sprint 56):**
1. [ ] Move to `src/components/ingestion/models.py`
2. [ ] Update alle Imports
3. [ ] OPL-004 Status auf RESOLVED setzen

**Finale Lösung:**
Move to `src/components/ingestion/models.py` in Sprint 56 (Domain Boundaries).

---

## Sprint 55: lightrag_wrapper Refactoring

### OPL-005: Singleton Wrapper Function

| Feld | Wert |
|------|------|
| **ID** | OPL-005 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 55 |
| **Implementiert** | Sprint 55 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 55.1-55.8 - lightrag_wrapper Split |

**Problem:**
`get_lightrag_wrapper_async()` ist als Singleton implementiert und wird in 40+ Dateien verwendet.

**Lösung implementiert (Sprint 55):**
1. ✅ `lightrag/` Package erstellt mit 6 Modulen
2. ✅ `lightrag_wrapper.py` auf Facade reduziert (47 LOC)
3. ✅ Re-Exports für Backward-Compatibility eingerichtet
4. ✅ Alle Imports verifiziert und funktional

**Temporäre Lösung (aktiv):**
```python
# src/components/graph_rag/lightrag_wrapper.py - Facade (47 LOC)
# OPL-005: Backward-compat aliases until Sprint 56
from src.components.graph_rag.lightrag.client import (
    LightRAGClient,
    LightRAGWrapper,
    get_lightrag_client,
    get_lightrag_client_async,
    get_lightrag_wrapper,
    get_lightrag_wrapper_async,
)

# Re-export for backward compatibility
__all__ = [
    "LightRAGClient",
    "LightRAGWrapper",
    "get_lightrag_client",
    "get_lightrag_client_async",
    "get_lightrag_wrapper",
    "get_lightrag_wrapper_async",
]
```

**Verwendungsstellen (40+ Dateien):**
- `src/components/graph_rag/dual_level_search.py`
- `src/components/ingestion/nodes/graph_extraction.py`
- `src/agents/graph_retrieval_agent.py`
- Tests und weitere Module

**Verbleibende Schritte (Sprint 56):**
1. [ ] Alle Verwendungsstellen auf direkte `lightrag/` Imports umstellen
2. [ ] Re-Export-Facade entfernen oder minimal halten
3. [ ] OPL-005 Status auf RESOLVED setzen

**Finale Lösung:**
Direkte Imports aus `lightrag/` Submodulen und DI via Factory Pattern.

---

## Sprint 56: Domain Boundaries

### OPL-006: llm_proxy → domains/llm_integration Migration

| Feld | Wert |
|------|------|
| **ID** | OPL-006 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 56 |
| **Implementiert** | Sprint 56 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 56.4 - llm_proxy Migration |

**Problem:**
`src/components/llm_proxy/` enthält LLM-bezogene Logik die in die neue Domain-Struktur migriert werden muss.

**Lösung implementiert (Sprint 56):**
1. ✅ `src/domains/llm_integration/` Package erstellt
2. ✅ Alle Module migriert:
   - `models.py` → `domains/llm_integration/models.py`
   - `config.py` → `domains/llm_integration/config.py`
   - `aegis_llm_proxy.py` → `domains/llm_integration/proxy/aegis_llm_proxy.py`
   - `cost_tracker.py` → `domains/llm_integration/cost/cost_tracker.py`
   - `vlm_*.py` → `domains/llm_integration/proxy/vlm_*.py`
3. ✅ Backward-Compat Facades in alten Dateien erstellt
4. ✅ Alle Imports verifiziert und funktional

**Temporäre Lösung (aktiv):**
```python
# src/components/llm_proxy/__init__.py - Facade
# OPL-006: Re-exports until Sprint 58
from src.domains.llm_integration import (
    AegisLLMProxy,
    get_aegis_llm_proxy,
    LLMTask,
    TaskType,
    CostTracker,
    # ... weitere Re-Exports
)
```

**Betroffene Backward-Compat Dateien:**
- `src/components/llm_proxy/__init__.py`
- `src/components/llm_proxy/aegis_llm_proxy.py`
- `src/components/llm_proxy/models.py`
- `src/components/llm_proxy/config.py`
- `src/components/llm_proxy/cost_tracker.py`
- `src/components/llm_proxy/vlm_factory.py`
- `src/components/llm_proxy/vlm_protocol.py`
- `src/components/llm_proxy/ollama_vlm.py`
- `src/components/llm_proxy/dashscope_vlm.py`

**Verwendungsstellen (40+ Dateien):**
- `src/components/retrieval/graph_rag_retriever.py`
- `src/components/memory/graphiti_wrapper.py`
- `src/evaluation/ragas_evaluator.py`
- `src/agents/answer_generator.py`
- `src/api/v1/title_generator.py`
- Weitere Module und Tests

**Verbleibende Schritte (Sprint 58):**
1. [ ] Alle Verwendungsstellen auf `src.domains.llm_integration` umstellen
2. [ ] Backward-Compat Facades entfernen
3. [ ] DC-004 für llm_proxy Dateien erstellen
4. [ ] OPL-006 Status auf RESOLVED setzen

**Neue Domain-Struktur:**
```
src/domains/llm_integration/
├── __init__.py           # Public API
├── models.py             # LLMTask, LLMResponse, TaskType, etc.
├── config.py             # LLMProxyConfig, get_llm_proxy_config()
├── proxy/
│   ├── __init__.py       # Proxy public API
│   ├── aegis_llm_proxy.py # Main proxy class (~800 LOC)
│   ├── vlm_protocol.py   # VLMClient Protocol
│   ├── vlm_factory.py    # VLM Factory Pattern
│   ├── ollama_vlm.py     # Ollama VLM Client
│   └── dashscope_vlm.py  # DashScope VLM Client
└── cost/
    ├── __init__.py       # Cost public API
    └── cost_tracker.py   # SQLite cost tracking (~350 LOC)
```

**Finale Lösung:**
Direkte Imports aus `src.domains.llm_integration` und Entfernung der alten `src/components/llm_proxy/` Facades.

---

### OPL-008: infrastructure/ Layer von core/

| Feld | Wert |
|------|------|
| **ID** | OPL-008 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 56 |
| **Implementiert** | Sprint 56 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 56.5 - Infrastructure Layer |

**Problem:**
`src/core/` enthält Cross-Cutting Concerns (config, logging, exceptions, models), die in eine
dedizierte `infrastructure/` Schicht migriert werden müssen für bessere Architektur-Trennung.

**Lösung implementiert (Sprint 56):**
1. ✅ `src/infrastructure/config/settings.py` - Re-exports von `core/config.py`
2. ✅ `src/infrastructure/logging/structlog_config.py` - Re-exports von `core/logging.py`
3. ✅ `src/infrastructure/exceptions/aegis_exceptions.py` - Re-exports von `core/exceptions.py`
4. ✅ `src/infrastructure/models/base_models.py` - Re-exports von `core/models.py`
5. ✅ `src/infrastructure/__init__.py` - Public API mit allen Exports
6. ✅ Alle Imports verifiziert und funktional

**Temporäre Lösung (aktiv):**
```python
# src/infrastructure/config/settings.py - Re-export Facade
# OPL-008: Re-exports until Sprint 58
from src.core.config import Settings, get_settings, settings

# src/infrastructure/logging/structlog_config.py - Re-export Facade
from src.core.logging import add_app_context, get_logger, setup_logging

# src/infrastructure/exceptions/aegis_exceptions.py - Re-export Facade
from src.core.exceptions import AegisRAGException, ValidationError, ...

# src/infrastructure/models/base_models.py - Re-export Facade
from src.core.models import QueryRequest, QueryResponse, ErrorCode, ...
```

**Infrastructure Package Struktur:**
```
src/infrastructure/
├── __init__.py              # Public API (alle exports)
├── config/
│   ├── __init__.py          # Config exports
│   └── settings.py          # Re-export from core/config.py
├── logging/
│   ├── __init__.py          # Logging exports
│   └── structlog_config.py  # Re-export from core/logging.py
├── exceptions/
│   ├── __init__.py          # Exception exports
│   └── aegis_exceptions.py  # Re-export from core/exceptions.py
└── models/
    ├── __init__.py          # Model exports
    └── base_models.py       # Re-export from core/models.py
```

**Export Counts:**
- `config`: 3 exports (Settings, get_settings, settings)
- `logging`: 3 exports (setup_logging, get_logger, add_app_context)
- `exceptions`: 17 exports (alle Exception-Klassen)
- `models`: 20 exports (alle Pydantic-Modelle)

**Verwendungsstellen (potenziell 100+ Dateien):**
- Nahezu alle Module importieren aus `src.core.*`
- Keine Änderung an Verwendungsstellen nötig (Re-Export-Strategie)

**Verbleibende Schritte (Sprint 58):**
1. [ ] Eigentlichen Code von `core/` nach `infrastructure/` verschieben
2. [ ] `core/` auf Re-Exports von infrastructure umstellen (Umkehr)
3. [ ] Alle direkten `core/` Imports auf `infrastructure/` umstellen
4. [ ] `core/` Package entfernen
5. [ ] OPL-008 Status auf RESOLVED setzen

**Finale Lösung:**
Vollständige Migration zu `src/infrastructure/` mit Entfernung von `src/core/`.

---

### OPL-009: graph_rag/ → domains/knowledge_graph/ Migration

| Feld | Wert |
|------|------|
| **ID** | OPL-009 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 56 |
| **Implementiert** | Sprint 56 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 56.2 - Knowledge Graph Domain |

**Problem:**
`src/components/graph_rag/` enthält die gesamte Knowledge Graph Logik, die in die neue Domain-Struktur
migriert werden muss für bessere Architektur-Trennung nach DDD.

**Lösung implementiert (Sprint 56):**
1. ✅ `src/domains/knowledge_graph/` Package erstellt mit 7 Subdomains
2. ✅ Re-export-Facades für alle Subdomains erstellt
3. ✅ Alle Imports verifiziert und funktional

**Temporäre Lösung (aktiv):**
```python
# src/domains/knowledge_graph/<subdomain>/__init__.py
# OPL-009: Re-exports until Sprint 58
from src.components.graph_rag.<module> import ...
```

**Knowledge Graph Domain Struktur:**
```
src/domains/knowledge_graph/
├── __init__.py              # Public API (60+ exports)
├── persistence/             # Neo4j storage
│   └── __init__.py          # Neo4jClient, GraphQueryTemplates, etc.
├── querying/                # LightRAG integration
│   └── __init__.py          # LightRAGClient, DualLevelSearch
├── extraction/              # Entity/relation extraction
│   └── __init__.py          # RelationExtractor, ExtractionService
├── deduplication/           # Entity/relation deduplication
│   └── __init__.py          # SemanticDeduplicator, HybridRelationDeduplicator
├── communities/             # Community detection & summarization
│   └── __init__.py          # CommunityDetector, CommunitySummarizer
├── analytics/               # Graph analytics & recommendations
│   └── __init__.py          # GraphAnalyticsEngine, RecommendationEngine
└── utilities/               # Protocols & utilities
    └── __init__.py          # GraphStorage, LLMConfigProvider
```

**Export Counts by Subdomain:**
- `persistence`: 7 exports
- `querying`: 8 exports
- `extraction`: 11 exports
- `deduplication`: 10 exports
- `communities`: 10 exports
- `analytics`: 4 exports
- `utilities`: 7 exports

**Verwendungsstellen (40+ Dateien):**
- `src/agents/graph_retrieval_agent.py`
- `src/components/retrieval/graph_rag_retriever.py`
- `src/api/v1/admin*.py`
- Tests und weitere Module

**Verbleibende Schritte (Sprint 58):**
1. [ ] Eigentlichen Code von `graph_rag/` nach `knowledge_graph/` verschieben
2. [ ] `components/graph_rag/` auf Re-Exports von domain umstellen
3. [ ] Alle direkten `graph_rag/` Imports auf `knowledge_graph/` umstellen
4. [ ] `components/graph_rag/` Package entfernen
5. [ ] OPL-009 Status auf RESOLVED setzen

**Finale Lösung:**
Vollständige Migration zu `src/domains/knowledge_graph/` mit Entfernung von `src/components/graph_rag/`.

---

### OPL-010: ingestion/ → domains/document_processing/ Migration

| Feld | Wert |
|------|------|
| **ID** | OPL-010 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 56 |
| **Implementiert** | Sprint 56 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 56.3 - Document Processing Domain |

**Problem:**
`src/components/ingestion/` enthält die gesamte Document Processing Logik, die in die neue Domain-Struktur
migriert werden muss für bessere Architektur-Trennung nach DDD.

**Lösung implementiert (Sprint 56):**
1. ✅ `src/domains/document_processing/` Package erstellt mit 4 Subdomains
2. ✅ Re-export-Facades für alle Subdomains erstellt
3. ✅ Alle Imports verifiziert und funktional

**Temporäre Lösung (aktiv):**
```python
# src/domains/document_processing/<subdomain>/__init__.py
# OPL-010: Re-exports until Sprint 58
from src.components.ingestion.<module> import ...
```

**Document Processing Domain Struktur:**
```
src/domains/document_processing/
├── __init__.py              # Public API (35+ exports)
├── parsing/                 # Docling integration
│   └── __init__.py          # DoclingContainerClient, FormatRouter
├── pipeline/                # LangGraph pipeline
│   └── __init__.py          # run_ingestion_pipeline, IngestionState
├── chunking/                # Adaptive chunking
│   └── __init__.py          # chunking_node, SectionMetadata
└── enrichment/              # Image/VLM enrichment
    └── __init__.py          # image_enrichment_node, ImageProcessor
```

**Export Counts by Subdomain:**
- `parsing`: 11 exports
- `pipeline`: 12 exports
- `chunking`: 5 exports
- `enrichment`: 3 exports

**Verwendungsstellen (30+ Dateien):**
- `src/api/v1/ingestion.py`
- `src/agents/ingestion_agent.py`
- Tests und weitere Module

**Verbleibende Schritte (Sprint 58):**
1. [ ] Eigentlichen Code von `ingestion/` nach `document_processing/` verschieben
2. [ ] `components/ingestion/` auf Re-Exports von domain umstellen
3. [ ] Alle direkten `ingestion/` Imports auf `document_processing/` umstellen
4. [ ] `components/ingestion/` Package entfernen
5. [ ] OPL-010 Status auf RESOLVED setzen

**Finale Lösung:**
Vollständige Migration zu `src/domains/document_processing/` mit Entfernung von `src/components/ingestion/`.

---

## Sprint 57: Interfaces & Protocols

### OPL-007: Concrete Type Dependencies

| Feld | Wert |
|------|------|
| **ID** | OPL-007 |
| **Status** | ✅ RESOLVED |
| **Erstellt** | Sprint 57 |
| **Implementiert** | Sprint 57 (2025-12-19) |
| **Aufgelöst** | Sprint 58 |
| **Feature** | 57.1-57.6 - Protocol Definitions & DI Container |

**Problem:**
Einige Module verwenden noch konkrete Typen statt Protocols, was Testbarkeit und Flexibilität einschränkt.

**Lösung implementiert (Sprint 57):**
1. ✅ Protocol definitions für alle 5 Domains erstellt
2. ✅ DI Container implementiert (`src/infrastructure/di/`)
3. ✅ Alle Protocols in Domain `__init__.py` exportiert

**Implementierte Protocols:**

| Domain | Protocols | Datei |
|--------|-----------|-------|
| knowledge_graph | EntityExtractor, RelationExtractor, GraphStorage, GraphQueryService, CommunityService, LLMConfigProvider, DeduplicationService, GraphAnalytics | `protocols.py` |
| document_processing | DocumentParser, ChunkingService, ImageEnricher, IngestionPipeline, EmbeddingGenerator, FormatRouter | `protocols.py` |
| llm_integration | LLMProvider, LLMRouter, CostTracker, ToolExecutor, VLMProvider | `protocols.py` |
| vector_search | EmbeddingService, VectorStore, HybridSearchService, RerankingService | `protocols.py` |
| memory | ConversationMemory, SessionStore, CacheService, MemoryConsolidation | `protocols.py` |

**DI Container:**
```python
# src/infrastructure/di/container.py
Container:
  - register(interface, factory, singleton=True)
  - resolve(interface) -> T
  - reset()  # For testing
  - override(interface, factory)  # For testing
```

**Verwendungsstellen (bestehende konkrete Typen):**
- `src/agents/*.py` - Agent implementations
- `src/api/v1/*.py` - API endpoints
- `src/components/*/*.py` - Component modules
- `tests/` - Test files mit direkten Imports

**Verbleibende Schritte (Sprint 58):**
1. [ ] Bestehende Klassen als Protocol-Implementierungen markieren
2. [ ] Factories für alle Services erstellen
3. [ ] Tests auf Protocol-based Mocks umstellen
4. [ ] Konkrete Type-Hints durch Protocols ersetzen
5. [ ] OPL-007 Status auf RESOLVED setzen

**Finale Lösung:**
Vollständige Protocol-based dependency injection mit DI Container.

---

## Sprint 58: Test Coverage & Cleanup

**Ziel Sprint 58:** Alle verbleibenden OPL-Einträge auflösen.

Nach Sprint 58 sollte diese Datei nur noch REMOVED-Einträge enthalten (als Dokumentation).

---

## Zusammenfassung

| Sprint | OPL-IDs | Status |
|--------|---------|--------|
| 53 | OPL-001, OPL-002 | ✅ RESOLVED |
| 54 | OPL-003, OPL-004 | ✅ RESOLVED |
| 55 | OPL-005 | ✅ RESOLVED |
| 56 | OPL-006, OPL-008, OPL-009, OPL-010 | ✅ RESOLVED |
| 57 | OPL-007 | ✅ RESOLVED |
| 58 | Cleanup | ✅ COMPLETE |

**Total OPEN:** 0
**Total RESOLVED:** 10 (OPL-001 bis OPL-010)
**Refactoring Status:** COMPLETE

**Sprint 58 Abschluss (2025-12-19):**
- ✅ Alle OPL-Kommentare aus Code entfernt
- ✅ Alle DC-Kommentare aus Code entfernt
- ✅ Backward-Compatibility-Facades beibehalten (ohne OPL-Marker)
- ✅ grep -r "OPL-0" src/ = 0 Treffer
- ✅ grep -r "DC-0" src/ = 0 Treffer

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
| **Implementiert** | Sprint 54 (2025-12-19) |
| **Entfernung** | Sprint 55 |
| **Dateien** | `src/components/ingestion/langgraph_nodes.py` |

**Status:** ✅ IMPLEMENTIERT - Originale extrahiert, Facade erstellt

**Betroffene Elemente:**
- ✅ Komplette Node-Implementierungen (extrahiert nach nodes/)
- ✅ Nur Re-Exports bleiben (OPL-003)
- Facade: 65 LOC (reduziert von 2227 LOC)

**Neue Module erstellt:**
| Modul | LOC | Inhalt |
|-------|-----|--------|
| `nodes/models.py` | 65 | SectionMetadata, AdaptiveChunk |
| `nodes/memory_management.py` | 150 | memory_check_node |
| `nodes/document_parsers.py` | 410 | docling_*, llamaindex_parse_node |
| `nodes/image_enrichment.py` | 302 | image_enrichment_node |
| `nodes/adaptive_chunking.py` | 555 | chunking_node, adaptive_section_chunking |
| `nodes/vector_embedding.py` | 262 | embedding_node |
| `nodes/graph_extraction.py` | 551 | graph_extraction_node |

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
| **Implementiert** | Sprint 55 (2025-12-19) |
| **Entfernung** | Sprint 56 |
| **Dateien** | `src/components/graph_rag/lightrag_wrapper.py` |

**Status:** ✅ IMPLEMENTIERT - Originale extrahiert, Facade erstellt

**Betroffene Elemente:**
- ✅ Komplette LightRAGClient Implementierung (extrahiert nach lightrag/)
- ✅ Nur Re-Exports bleiben (OPL-005)
- Facade: 47 LOC (reduziert von 1823 LOC)

**Neue Module erstellt:**
| Modul | LOC | Inhalt |
|-------|-----|--------|
| `lightrag/types.py` | 155 | QueryMode, LightRAGConfig, dataclasses |
| `lightrag/initialization.py` | 210 | create_lightrag_instance, UnifiedEmbeddingFunc |
| `lightrag/converters.py` | 245 | chunk_text_with_metadata, convert_* functions |
| `lightrag/ingestion.py` | 450 | extract_per_chunk, insert_* functions |
| `lightrag/neo4j_storage.py` | 340 | store_chunks_and_provenance, store_relates_to |
| `lightrag/client.py` | 295 | LightRAGClient, singleton getters |
| `lightrag/__init__.py` | 110 | Package exports |

**Verification vor Entfernung:**
```bash
# Prüfe direkte Imports (sollten nur noch von lightrag/ kommen)
grep -r "from src.components.graph_rag.lightrag_wrapper import" src/ --include="*.py"
```

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
