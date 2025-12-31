# Sprint 56: Domain Boundaries (DDD Structure)

**Status:** PLANNED
**Branch:** `sprint-56-domain-boundaries`
**Start Date:** TBD (nach Sprint 55)
**Estimated Duration:** 5 Tage
**Total Story Points:** 40 SP

---

## Sprint Overview

Sprint 56 etabliert Domain-Driven Design Boundaries und reorganisiert die Codebase
gemäß der Ziel-Architektur aus ADR-046.

**Voraussetzung:** Sprint 55 abgeschlossen

**Referenzen:**
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **MUSS bei jeder Änderung aktualisiert werden!**

---

## Ziel-Architektur

```
src/
├── domains/                        # Business Logic (NEW)
│   ├── query/                      # Query Execution
│   ├── knowledge_graph/            # Graph Reasoning (from graph_rag/)
│   │   ├── extraction/
│   │   ├── deduplication/
│   │   ├── communities/
│   │   ├── querying/
│   │   └── persistence/
│   ├── vector_search/              # Vector Retrieval
│   ├── document_processing/        # Ingestion (from ingestion/)
│   ├── memory/                     # 3-Layer Memory
│   └── llm_integration/            # LLM Provisioning (from llm_proxy/)
├── infrastructure/                 # Cross-Cutting (from core/)
├── api/                            # Thin HTTP Layer
├── agents/                         # LangGraph Orchestration
└── evaluation/                     # Testing & Benchmarks
```

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 56.1 | Create domains/ Directory Structure | 5 | P0 | Nein (Foundation) |
| 56.2 | Migrate graph_rag/ → domains/knowledge_graph/ | 10 | P1 | Ja (Agent 1) |
| 56.3 | Migrate ingestion/ → domains/document_processing/ | 8 | P1 | Ja (Agent 2) |
| 56.4 | Migrate llm_proxy/ → domains/llm_integration/ | 5 | P1 | Ja (Agent 3) |
| 56.5 | Create infrastructure/ from core/ | 5 | P1 | Ja (Agent 4) |
| 56.6 | OPL Cleanup & Cross-Domain Imports | 5 | P0 | Final |
| 56.7 | chat.py Split (3 Modules) | 5 | P2 | Parallel |

**Total: 40 SP**

---

## Feature Details

### Feature 56.1: Create domains/ Directory Structure (5 SP)

**Priority:** P0 (Foundation)
**Parallelisierung:** Nein - blockt alle anderen Features

**OPL-Pflicht:** OPL-006 in REFACTORING_OPL.md vorbereiten!

**Aufgaben:**
1. Erstelle `src/domains/` Directory
2. Erstelle Subdirectories für jede Domain
3. Erstelle `__init__.py` mit Public API Exports
4. Definiere Domain Boundaries

**Neue Struktur:**

```
src/domains/
├── __init__.py
├── knowledge_graph/
│   ├── __init__.py           # Public API
│   ├── extraction/           # Entity/Relation Extraction
│   ├── deduplication/        # Semantic Deduplication
│   ├── communities/          # Community Detection & Summary
│   ├── querying/             # Graph Queries
│   └── persistence/          # Neo4j Storage
├── document_processing/
│   ├── __init__.py
│   ├── parsing/              # Docling Integration
│   ├── chunking/             # Adaptive Chunking
│   ├── enrichment/           # Image/VLM Enrichment
│   └── pipeline/             # LangGraph Pipeline
├── vector_search/
│   ├── __init__.py
│   ├── qdrant/               # Qdrant Client
│   ├── hybrid/               # Hybrid Search
│   └── embedding/            # BGE-M3 Service
├── memory/
│   ├── __init__.py
│   ├── redis/                # Redis Memory
│   ├── graphiti/             # Graphiti Integration
│   └── conversation/         # Conversation History
└── llm_integration/
    ├── __init__.py
    ├── proxy/                # AegisLLMProxy
    ├── routing/              # Multi-Cloud Routing
    └── cost/                 # Cost Tracking
```

**Domain Public API Pattern:**

```python
# src/domains/knowledge_graph/__init__.py
"""Knowledge Graph Domain - Public API.

Sprint 56: Domain boundary for graph-based knowledge management.

Usage:
    from src.domains.knowledge_graph import (
        extract_entities,
        query_graph,
        detect_communities,
    )
"""

# Public API
from src.domains.knowledge_graph.extraction import extract_entities
from src.domains.knowledge_graph.querying import query_graph
from src.domains.knowledge_graph.communities import detect_communities

__all__ = [
    "extract_entities",
    "query_graph",
    "detect_communities",
]
```

**Acceptance Criteria:**
- [ ] domains/ Struktur erstellt
- [ ] Alle Subdirectories mit `__init__.py`
- [ ] OPL-006 dokumentiert

---

### Feature 56.2: Migrate graph_rag/ → domains/knowledge_graph/ (10 SP)

**Priority:** P1
**Parallelisierung:** Agent 1 (nach 56.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Migration Map:**

| Source | Destination |
|--------|-------------|
| `graph_rag/extraction_factory.py` | `knowledge_graph/extraction/` |
| `graph_rag/entity_extractor.py` | `knowledge_graph/extraction/` |
| `graph_rag/semantic_deduplicator.py` | `knowledge_graph/deduplication/` |
| `graph_rag/relation_deduplicator.py` | `knowledge_graph/deduplication/` |
| `graph_rag/community_detector.py` | `knowledge_graph/communities/` |
| `graph_rag/community_summarizer.py` | `knowledge_graph/communities/` |
| `graph_rag/lightrag/` (Sprint 55) | `knowledge_graph/querying/` |
| `graph_rag/neo4j_client.py` | `knowledge_graph/persistence/` |

**Backward Compatibility (OPL-006):**

```python
# src/components/graph_rag/__init__.py
"""Graph RAG - Compatibility Layer.

OPL-006: Re-exports for backward compatibility.
Migrate to src.domains.knowledge_graph imports.
Siehe: docs/refactoring/REFACTORING_OPL.md
"""

# OPL-006: Backward compatibility re-exports
from src.domains.knowledge_graph.extraction import (
    extract_entities,
    ExtractionPipelineFactory,
)
from src.domains.knowledge_graph.communities import (
    CommunityDetector,
    CommunitySummarizer,
)
# ... weitere Re-Exports

__all__ = [...]
```

**Verwendungsstellen (zu aktualisieren):**
- `src/components/ingestion/langgraph_nodes.py:45`
- `src/api/v1/admin.py:21`
- `src/components/retrieval/maximum_hybrid_search.py`
- 40+ weitere Dateien

**Acceptance Criteria:**
- [ ] Alle graph_rag Module migriert
- [ ] Backward-Compat Layer funktioniert
- [ ] Public API definiert
- [ ] OPL-006 dokumentiert

---

### Feature 56.3: Migrate ingestion/ → domains/document_processing/ (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 2 (nach 56.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Migration Map:**

| Source | Destination |
|--------|-------------|
| `ingestion/docling_client.py` | `document_processing/parsing/` |
| `ingestion/nodes/` (Sprint 54) | `document_processing/pipeline/` |
| `ingestion/image_processor.py` | `document_processing/enrichment/` |
| `ingestion/section_extraction.py` | `document_processing/chunking/` |
| `ingestion/langgraph_pipeline.py` | `document_processing/pipeline/` |

**WICHTIG für Sprint 59:**
Document Processing wird in Sprint 59 erweitert für:
- Bash/Python Execution in Documents
- Sandboxed Code Evaluation

Stelle sicher, dass die Struktur erweiterbar ist!

**Acceptance Criteria:**
- [ ] Alle ingestion Module migriert
- [ ] Backward-Compat Layer
- [ ] Sprint 59 Erweiterbarkeit

---

### Feature 56.4: Migrate llm_proxy/ → domains/llm_integration/ (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 3 (nach 56.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Migration Map:**

| Source | Destination |
|--------|-------------|
| `llm_proxy/aegis_llm_proxy.py` | `llm_integration/proxy/` |
| `llm_proxy/routing.py` | `llm_integration/routing/` |
| `llm_proxy/cost_tracker.py` | `llm_integration/cost/` |
| `llm_proxy/config.py` | `llm_integration/` |

**WICHTIG für Sprint 59:**
LLM Integration wird in Sprint 59 erweitert für:
- Tool Use
- Agentic Search
- Deep Research

Stelle sicher, dass die Struktur erweiterbar ist!

**Acceptance Criteria:**
- [ ] Alle llm_proxy Module migriert
- [ ] AegisLLMProxy funktioniert
- [ ] Sprint 59 Erweiterbarkeit

---

### Feature 56.5: Create infrastructure/ from core/ (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 4 (nach 56.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Migration Map:**

| Source | Destination | Notes |
|--------|-------------|-------|
| `core/config.py` | `infrastructure/config/` | Settings |
| `core/logging.py` | `infrastructure/logging/` | Structlog |
| `core/exceptions.py` | `infrastructure/exceptions/` | Custom Exceptions |
| `core/models.py` | Bleibt oder → domains/ | Domain-spezifisch |
| `core/chunking_service.py` | `domains/document_processing/` | Business Logic |
| `core/namespace.py` | `domains/user_management/` | Future Domain |

**Entscheidung für core/models.py:**
- Domain Models → jeweilige Domain
- Shared/Base Models → `infrastructure/models/`

**Acceptance Criteria:**
- [ ] infrastructure/ erstellt
- [ ] Config korrekt migriert
- [ ] Logging funktioniert
- [ ] Exceptions verfügbar

---

### Feature 56.6: OPL Cleanup & Cross-Domain Imports (5 SP)

**Priority:** P0 (Final)
**Parallelisierung:** Nach allen anderen Features

**OPL-Pflicht:** REFACTORING_OPL.md MUSS aktualisiert werden!

**Aufgaben:**
1. Alle OPL-003, OPL-004 Einträge prüfen
2. OPL-005 Status prüfen
3. OPL-006 finalisieren
4. Cross-Domain Import Rules dokumentieren

**Cross-Domain Import Rules:**

```python
# ERLAUBT: Import von Domain Public API
from src.domains.knowledge_graph import query_graph

# VERBOTEN: Import von Domain Internals
from src.domains.knowledge_graph.persistence.neo4j import _internal_method

# ERLAUBT: Import von Infrastructure
from src.infrastructure.config import settings

# ERLAUBT: Import innerhalb einer Domain
# In src/domains/knowledge_graph/communities/detector.py:
from src.domains.knowledge_graph.persistence import Neo4jClient
```

**REFACTORING_OPL.md Updates:**
- OPL-003: Status → RESOLVED (wenn Imports bereinigt)
- OPL-004: Status → RESOLVED (Models migriert)
- OPL-005: Status prüfen
- OPL-006: Vollständig dokumentieren

**Acceptance Criteria:**
- [ ] Alle OPL-Einträge geprüft
- [ ] Cross-Domain Rules dokumentiert
- [ ] Keine zyklischen Domain-Imports

---

### Feature 56.7: chat.py Split (3 Modules) (5 SP)

**Priority:** P2
**Parallelisierung:** Parallel zu anderen Features

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Ziel:** Zerlege `api/v1/chat.py` (2034 LOC) in 3 Module.

**Neue Struktur:**

```
src/api/v1/
├── chat.py                 # [~100 LOC] Router + Facade
├── chat_streaming.py       # [~700 LOC] SSE Streaming
├── chat_persistence.py     # [~500 LOC] Session Storage
└── chat_analytics.py       # [~400 LOC] Usage Analytics
```

**Verwendungsstellen:**
- `src/api/main.py:50` - Router
- `frontend/src/hooks/useStreamChat.ts`
- `tests/integration/api/test_stream_api_integration.py`

**Acceptance Criteria:**
- [ ] chat.py < 200 LOC
- [ ] 3 neue Module erstellt
- [ ] Streaming funktioniert
- [ ] Sessions persistent

---

## Parallel Execution Strategy

### Wave 1 (Tag 1): Foundation
```
Agent 1: Feature 56.1 - Directory Structure (BLOCKER)
```

### Wave 2 (Tag 2-4): Domain Migration (4 Agents parallel)
```
┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                            │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │   Agent 4         │
│   56.2       │   56.3       │   56.4       │   56.5            │
│   Graph      │   Document   │   LLM        │   Infrastructure  │
│   10 SP      │   8 SP       │   5 SP       │   5 SP            │
└──────────────┴──────────────┴──────────────┴───────────────────┘

Agent 5: Feature 56.7 - chat.py Split (parallel)
```

### Wave 3 (Tag 5): Finalization
```
Agent 1: Feature 56.6 - OPL Cleanup
Agent 2: Integration Tests
Agent 3: Documentation
Agent 4: Import Verification
```

---

## Acceptance Criteria (Sprint Complete)

- [ ] `src/domains/` Struktur vollständig
- [ ] 4 Domains etabliert (knowledge_graph, document_processing, llm_integration, memory)
- [ ] `src/infrastructure/` erstellt
- [ ] Alle Backward-Compat Layers funktionieren
- [ ] Cross-Domain Import Rules definiert
- [ ] OPL-003, OPL-004, OPL-005 Status aktualisiert
- [ ] OPL-006 dokumentiert
- [ ] chat.py aufgeteilt

---

## Risk Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Import-Chaos | High | High | Strikte OPL-Dokumentation |
| Performance-Regression | Low | Medium | Benchmarks |
| Zyklische Imports | Medium | High | Domain Rules |
| Test-Failures | Medium | Medium | Schrittweise Migration |

---

## Definition of Done

### Per Feature
- [ ] Domain/Package migriert
- [ ] Backward-Compat Layer
- [ ] Public API definiert
- [ ] REFACTORING_OPL.md aktualisiert

### Sprint Complete
- [ ] Domains etabliert
- [ ] Infrastructure erstellt
- [ ] OPL Status aktuell
- [ ] CI/CD grün

---

---

## Subagent-Anweisungen: OPL & Dead Code

**WICHTIG:** Jeder Subagent MUSS bei Refactoring-Arbeiten folgende Dokumente pflegen:

### 1. OPL-Einträge (Zwischenlösungen)

**Sprint 56 OPL-Einträge:**
- OPL-006: Cross-Domain Imports (Backward-Compat Re-Exports)

**Zu prüfende OPL aus vorherigen Sprints:**
- OPL-003: RESOLVED? → Re-Exports entfernen
- OPL-004: RESOLVED? → Models in Domains
- OPL-005: Status prüfen (DI Migration)

### 2. Dead Code Tracking (DC-XXX)

**Sprint 56 DC-Einträge:**
- DC-004: Backward-Compat Re-Exports in `__init__.py` → Entfernung Sprint 58

**Zu entfernender Dead Code aus Sprint 55:**
- DC-003: lightrag_wrapper.py → Verification + Entfernung

### 3. Verification vor Entfernung (DC-003)

```bash
# Vor Entfernung der alten lightrag_wrapper.py Implementierungen
grep -r "from src.components.graph_rag.lightrag_wrapper import" src/ --include="*.py"

# Erwartete Ergebnisse nach Migration:
# - Nur get_lightrag_wrapper_async (OPL-005)
# - Keine direkten LightRAGClient Imports mehr
```

### 4. Domain Migration Tracking

Bei Migration zu `src/domains/`:
```python
# src/components/graph_rag/__init__.py
# OPL-006: Backward-compat re-exports until Sprint 58
# DC-004: Diese Re-Exports werden in Sprint 58 entfernt
from src.domains.knowledge_graph import (
    CommunityDetector,
    CommunitySummarizer,
)
```

### 5. Checkliste pro Feature

- [ ] Feature implementiert
- [ ] OPL-Eintrag erstellt (falls Zwischenlösung)
- [ ] DC-Eintrag erstellt (falls Code ersetzt)
- [ ] Vorherige DC-Einträge geprüft und entfernt
- [ ] REFACTORING_OPL.md aktualisiert

---

## References

- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **OPL + Dead Code Tracking**
- [Sprint 55 Plan](SPRINT_55_PLAN.md)

---

**END OF SPRINT 56 PLAN**
