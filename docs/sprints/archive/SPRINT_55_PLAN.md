# Sprint 55: lightrag_wrapper.py Refactoring

**Status:** ✅ COMPLETE
**Branch:** `main`
**Start Date:** 2025-12-19
**End Date:** 2025-12-19
**Duration:** 1 Tag
**Total Story Points:** 38 SP

---

## Sprint Overview

Sprint 55 zerlegt `lightrag_wrapper.py` (1822 LOC) in 6 spezialisierte Module.
Dies ist Phase 2b des Refactoring-Plans (ADR-046).

**Voraussetzung:** Sprint 54 abgeschlossen

**Referenzen:**
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **MUSS bei jeder Änderung aktualisiert werden!**

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 55.1 | Create lightrag/ Package Structure | 3 | P0 | Nein (Foundation) |
| 55.2 | Extract types.py (Data Models) | 3 | P1 | Ja (Agent 1) |
| 55.3 | Extract initialization.py | 5 | P1 | Ja (Agent 2) |
| 55.4 | Extract ingestion.py | 8 | P1 | Ja (Agent 3) |
| 55.5 | Extract converters.py | 5 | P1 | Ja (Agent 4) |
| 55.6 | Extract neo4j_storage.py | 8 | P1 | Nach Wave 1 |
| 55.7 | Extract client.py (Facade) | 5 | P1 | Nach Wave 1 |
| 55.8 | OPL Update & Cleanup Sprint 54 | 3 | P0 | Final |

**Total: 38 SP**

---

## Ziel-Struktur

```
src/components/graph_rag/
├── lightrag/                       # NEW Package
│   ├── __init__.py                 # Re-exports LightRAGClient
│   ├── types.py                    # [50 LOC] Feature 55.2
│   ├── initialization.py           # [180 LOC] Feature 55.3
│   ├── ingestion.py                # [320 LOC] Feature 55.4
│   ├── converters.py               # [200 LOC] Feature 55.5
│   ├── neo4j_storage.py            # [340 LOC] Feature 55.6
│   └── client.py                   # [210 LOC] Feature 55.7 (Facade)
├── lightrag_wrapper.py             # [~30 LOC] Backward-compat (OPL-005)
├── registry.py                     # From Sprint 53
└── ...
```

---

## Feature Details

### Feature 55.1: Create lightrag/ Package Structure (3 SP)

**Priority:** P0 (Foundation)
**Parallelisierung:** Nein - blockt alle anderen Features

**OPL-Pflicht:** REFACTORING_OPL.md prüfen, OPL-005 vorbereiten!

**Aufgaben:**
1. Erstelle `src/components/graph_rag/lightrag/` Directory
2. Erstelle `__init__.py` mit Exports
3. Plane Modul-Abhängigkeiten

**Neue Dateien:**

```python
# src/components/graph_rag/lightrag/__init__.py
"""LightRAG Integration Package.

Sprint 55: Modularized LightRAG wrapper for better maintainability.
Provides graph-based knowledge retrieval with Neo4j backend.

Usage:
    from src.components.graph_rag.lightrag import LightRAGClient

    client = await get_lightrag_client()
    result = await client.query("What is machine learning?")
"""

from src.components.graph_rag.lightrag.client import LightRAGClient
from src.components.graph_rag.lightrag.types import (
    GraphQueryResult,
    LightRAGConfig,
    IngestionResult,
)

__all__ = [
    "LightRAGClient",
    "GraphQueryResult",
    "LightRAGConfig",
    "IngestionResult",
]
```

**Acceptance Criteria:**
- [ ] Package-Struktur erstellt
- [ ] Dependencies geplant
- [ ] OPL-005 in REFACTORING_OPL.md eingetragen

---

### Feature 55.2: Extract types.py (Data Models) (3 SP)

**Priority:** P1
**Parallelisierung:** Agent 1 (nach 55.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Zu extrahierende Elemente:**
- `LightRAGConfig` Dataclass
- `IngestionResult` Dataclass
- Type Aliases
- Enums für Query Modes

**Neue Datei:** `src/components/graph_rag/lightrag/types.py`

```python
"""LightRAG type definitions.

Sprint 55 Feature 55.2: Shared types for LightRAG integration.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class QueryMode(Enum):
    """LightRAG query modes."""
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    NAIVE = "naive"


@dataclass
class LightRAGConfig:
    """Configuration for LightRAG client."""
    working_dir: str
    llm_model: str
    embedding_model: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    document_id: str
    entities_created: int
    relations_created: int
    chunks_processed: int
    duration_ms: float
```

**Verwendungsstellen:**
- `lightrag_wrapper.py:44-54` - LightRAGClient Config
- `src/core/models.py:GraphQueryResult` - Query Result

**Acceptance Criteria:**
- [ ] `types.py` erstellt
- [ ] Alle Typen verwendbar
- [ ] MyPy keine Fehler

---

### Feature 55.3: Extract initialization.py (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 2 (nach 55.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `lightrag_wrapper.py:56-210` (ca. 155 LOC)

**Zu extrahierende Elemente:**
- `__init__` Methode Logic
- Lazy Initialization
- LightRAG Instance Creation
- Ollama LLM Function Setup
- Neo4j Connection Setup

**Neue Datei:** `src/components/graph_rag/lightrag/initialization.py`

```python
"""LightRAG initialization and configuration.

Sprint 55 Feature 55.3: Handles LightRAG instance creation and setup.
"""

from pathlib import Path
from typing import Any

import structlog

from src.components.graph_rag.lightrag.types import LightRAGConfig
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def create_lightrag_instance(config: LightRAGConfig) -> Any:
    """Create and initialize a LightRAG instance.

    Args:
        config: LightRAG configuration

    Returns:
        Initialized LightRAG instance
    """
    # Implementation from lightrag_wrapper.py:100-210
    ...


def setup_ollama_llm_functions(model: str) -> dict[str, Any]:
    """Configure Ollama LLM functions for LightRAG.

    Args:
        model: Ollama model name

    Returns:
        Dict of LLM functions for LightRAG
    """
    ...
```

**Verwendungsstellen:**
| Datei | Zeile | Funktion |
|-------|-------|----------|
| `lightrag_wrapper.py` | 100 | `_ensure_initialized()` |
| `extraction_factory.py` | 35 | Creates wrapper |

**Acceptance Criteria:**
- [ ] `initialization.py` erstellt
- [ ] Lazy Init funktioniert
- [ ] Neo4j Connection Setup korrekt

---

### Feature 55.4: Extract ingestion.py (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 3 (nach 55.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `lightrag_wrapper.py:300-785` (ca. 485 LOC)

**Zu extrahierende Elemente:**
- `insert_document()` Method
- `insert_chunks()` Method
- Chunk Processing Logic
- Entity/Relation Extraction Calls
- Progress Tracking

**Neue Datei:** `src/components/graph_rag/lightrag/ingestion.py`

**Abhängigkeiten:**
- `ExtractionPipelineFactory`
- `SemanticDeduplicator`
- `RelationDeduplicator`
- Neo4j Client

**WICHTIG für Sprint 59:**
Ingestion wird in Sprint 59 erweitert für Tool-basierte Dokumentenverarbeitung.

**Verwendungsstellen:**
| Datei | Zeile | Methode |
|-------|-------|---------|
| `langgraph_nodes.py:graph_extraction` | 450 | `insert_chunks()` |
| `parallel_orchestrator.py` | 200 | `insert_document()` |
| 40+ Test-Dateien | - | Various inserts |

**Acceptance Criteria:**
- [ ] `ingestion.py` erstellt
- [ ] Chunk Processing funktioniert
- [ ] Deduplication integriert
- [ ] Progress Events emittiert

---

### Feature 55.5: Extract converters.py (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 4 (nach 55.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `lightrag_wrapper.py:785-980` (ca. 195 LOC)

**Zu extrahierende Elemente:**
- Format Conversion Functions
- Context Parsing
- Entity/Relation to Dict Conversion
- Neo4j Result Formatting

**Neue Datei:** `src/components/graph_rag/lightrag/converters.py`

```python
"""LightRAG format converters.

Sprint 55 Feature 55.5: Conversion utilities for LightRAG data.
"""

from typing import Any

from src.components.graph_rag.lightrag.types import GraphQueryResult


def parse_lightrag_context(context: str) -> dict[str, Any]:
    """Parse LightRAG context string to structured data."""
    ...


def entity_to_dict(entity: Any) -> dict[str, Any]:
    """Convert LightRAG entity to dictionary."""
    ...


def relation_to_dict(relation: Any) -> dict[str, Any]:
    """Convert LightRAG relation to dictionary."""
    ...
```

**Verwendungsstellen:**
- `maximum_hybrid_search.py:150` - Context Parsing
- `lightrag_context_parser.py:30` - Parse results

**Acceptance Criteria:**
- [ ] `converters.py` erstellt
- [ ] Context Parsing funktioniert
- [ ] Format Conversions korrekt

---

### Feature 55.6: Extract neo4j_storage.py (8 SP)

**Priority:** P1
**Parallelisierung:** Nach Wave 1

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `lightrag_wrapper.py:980-1285` (ca. 305 LOC)

**Zu extrahierende Elemente:**
- Neo4j CRUD Operations
- Entity Storage
- Relation Storage
- MENTIONED_IN Links
- RELATES_TO Links
- Transaction Handling

**Neue Datei:** `src/components/graph_rag/lightrag/neo4j_storage.py`

**Abhängigkeiten:**
- `Neo4jClient`
- Transaction Context Managers

**KRITISCH:**
Dies enthält die Neo4j Transaktions-Logik. Besondere Sorgfalt!

**Verwendungsstellen:**
| Datei | Zeile | Operation |
|-------|-------|-----------|
| `ingestion.py` (neu) | 150 | Entity Upsert |
| `community_detector.py` | 80 | Community Query |
| `graph_extraction_node.py` | 200 | Relation Creation |

**Acceptance Criteria:**
- [ ] `neo4j_storage.py` erstellt
- [ ] Transaktionen thread-safe
- [ ] RELATES_TO korrekt erstellt
- [ ] MENTIONED_IN korrekt erstellt

---

### Feature 55.7: Extract client.py (Facade) (5 SP)

**Priority:** P1
**Parallelisierung:** Nach Wave 1

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Ziel:** Schlanke Facade-Klasse, die alle Module orchestriert.

**Neue Datei:** `src/components/graph_rag/lightrag/client.py`

```python
"""LightRAG Client - Main Facade.

Sprint 55 Feature 55.7: Unified interface for LightRAG operations.
Orchestrates initialization, ingestion, querying, and storage.
"""

from typing import Any

import structlog

from src.components.graph_rag.lightrag.ingestion import (
    insert_document,
    insert_chunks,
)
from src.components.graph_rag.lightrag.initialization import (
    create_lightrag_instance,
)
from src.components.graph_rag.lightrag.neo4j_storage import Neo4jStorage
from src.components.graph_rag.lightrag.types import (
    GraphQueryResult,
    LightRAGConfig,
    QueryMode,
)

logger = structlog.get_logger(__name__)


class LightRAGClient:
    """Async wrapper for LightRAG with Neo4j backend.

    Provides:
    - Document ingestion and graph construction
    - Dual-level retrieval (local/global/hybrid)
    - Entity and relationship extraction
    """

    def __init__(self, config: LightRAGConfig | None = None):
        """Initialize LightRAG client."""
        self._config = config or self._load_default_config()
        self._rag: Any = None
        self._storage: Neo4jStorage | None = None

    async def query(
        self,
        query: str,
        mode: QueryMode = QueryMode.HYBRID,
        only_need_context: bool = False,
    ) -> GraphQueryResult:
        """Execute a query against the knowledge graph."""
        ...

    async def insert_document(self, document: str, **kwargs) -> dict:
        """Insert a document into the knowledge graph."""
        ...

    # ... weitere Methoden
```

**Verwendungsstellen (40+ Dateien):**
Diese werden via OPL-005 (Singleton Wrapper) weiter unterstützt.

**Acceptance Criteria:**
- [ ] `client.py` erstellt
- [ ] Facade Pattern implementiert
- [ ] Query Methoden funktionieren
- [ ] Insert Methoden funktionieren

---

### Feature 55.8: OPL Update & Cleanup Sprint 54 (3 SP)

**Priority:** P0 (Final)
**Parallelisierung:** Nach allen anderen Features

**OPL-Pflicht:** REFACTORING_OPL.md MUSS aktualisiert werden!

**Aufgaben:**
1. `lightrag_wrapper.py` auf Facade reduzieren (OPL-005)
2. OPL-003 aus Sprint 54 prüfen und ggf. schließen
3. OPL-005 dokumentieren
4. Alle 40+ Verwendungsstellen verifizieren

**lightrag_wrapper.py nach Refactoring:**

```python
"""LightRAG Wrapper - Legacy Compatibility Layer.

Sprint 55: This file provides backward compatibility.
Prefer direct imports from src.components.graph_rag.lightrag/

OPL-005: Diese Wrapper-Funktion wird in Sprint 56 ersetzt.
Siehe: docs/refactoring/REFACTORING_OPL.md
"""

# OPL-005: Backward-compatible singleton accessor
from src.components.graph_rag.lightrag import LightRAGClient
from src.components.graph_rag.registry import get_instance, set_instance


async def get_lightrag_wrapper_async() -> LightRAGClient:
    """Get or create LightRAG client singleton.

    OPL-005: Deprecated - use DI pattern in Sprint 56.
    """
    instance = get_instance("lightrag_client")
    if instance is None:
        from src.components.graph_rag.lightrag.initialization import (
            create_lightrag_client,
        )
        instance = await create_lightrag_client()
        set_instance("lightrag_client", instance)
    return instance


# OPL-005: Alias for backward compatibility
LightRAGWrapper = LightRAGClient

__all__ = [
    "LightRAGClient",
    "LightRAGWrapper",  # Deprecated alias
    "get_lightrag_wrapper_async",
]
```

**REFACTORING_OPL.md Updates:**
- OPL-003: Status auf RESOLVED wenn Sprint 54 Imports bereinigt
- OPL-005: Vollständig dokumentieren

**Acceptance Criteria:**
- [ ] `lightrag_wrapper.py` < 50 LOC
- [ ] OPL-003 Status aktualisiert
- [ ] OPL-005 dokumentiert
- [ ] Alle 40+ Verwendungsstellen funktionieren

---

## Parallel Execution Strategy

### Wave 1 (Tag 1): Foundation
```
Agent 1: Feature 55.1 - Package Structure (BLOCKER)
```

### Wave 2 (Tag 2-3): Core Modules (4 Agents parallel)
```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │   Agent 4      │
│   55.2       │   55.3       │   55.4       │   55.5         │
│   Types      │   Init       │   Ingestion  │   Converters   │
│   3 SP       │   5 SP       │   8 SP       │   5 SP         │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Wave 3 (Tag 4): Dependent Modules
```
┌─────────────────────────────────────────┐
│           PARALLEL EXECUTION             │
├───────────────────┬─────────────────────┤
│      Agent 1      │      Agent 2        │
│      55.6         │      55.7           │
│      Neo4j Store  │      Client Facade  │
│      8 SP         │      5 SP           │
└───────────────────┴─────────────────────┘
```

### Wave 4 (Tag 5): Finalization
```
Agent 1: Feature 55.8 - OPL Update
Agent 2: Integration Tests
Agent 3: Documentation
Agent 4: Verification of 40+ imports
```

---

## Acceptance Criteria (Sprint Complete)

- [x] `lightrag_wrapper.py` von 1822 LOC auf <50 LOC reduziert (47 LOC achieved)
- [x] 7 neue Module in `lightrag/` Package (including __init__.py)
- [x] Singleton-Funktion funktioniert (OPL-005)
- [x] Alle Imports verifiziert
- [x] Alle Integration Tests passieren
- [x] REFACTORING_OPL.md aktualisiert (OPL-005, DC-003)
- [x] OPL-005 documented with implementation details

---

## Risk Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Neo4j Transaction Fehler | Medium | High | Extensive Integration Tests |
| Singleton Race Condition | Low | Medium | Thread-safe Registry |
| LightRAG API Breaking | Low | High | Abstraction Layer |
| 40+ Import Failures | Medium | Medium | OPL-005 Backward Compat |

---

## Definition of Done

### Per Feature
- [x] Modul extrahiert und funktional
- [x] Imports verifiziert
- [x] Import in `__init__.py`
- [x] REFACTORING_OPL.md geprüft

### Sprint Complete
- [x] Alle 7 Module erstellt (6 + __init__.py)
- [x] Legacy Wrapper funktional (47 LOC facade)
- [x] CI/CD grün
- [x] OPL-005 dokumentiert (IN_PROGRESS)
- [x] DC-003 Status aktualisiert (IMPLEMENTIERT)

---

---

## Subagent-Anweisungen: OPL & Dead Code

**WICHTIG:** Jeder Subagent MUSS bei Refactoring-Arbeiten folgende Dokumente pflegen:

### 1. OPL-Einträge (Zwischenlösungen)

**Sprint 55 OPL-Einträge:**
- OPL-005: Singleton Wrapper `get_lightrag_wrapper_async()`

**Zu prüfende OPL aus vorherigen Sprints:**
- OPL-003: Kann in Sprint 55 auf RESOLVED gesetzt werden?

### 2. Dead Code Tracking (DC-XXX)

**Sprint 55 DC-Einträge:**
- DC-003: lightrag_wrapper.py Originale → Entfernung Sprint 56

**Zu entfernender Dead Code aus Sprint 54:**
- DC-002: langgraph_nodes.py → Verification + Entfernung

### 3. Verification vor Entfernung (DC-002)

```bash
# Vor Entfernung der alten langgraph_nodes.py Implementierungen
grep -r "from src.components.ingestion.langgraph_nodes import" src/ --include="*.py"

# Erwartete Ergebnisse:
# - src/components/ingestion/nodes/__init__.py (OK - Re-Export)
# - src/components/ingestion/langgraph_pipeline.py (→ auf nodes/ umstellen)
```

### 4. Code-Kommentare

```python
# OPL-005: Singleton accessor until DI in Sprint 56
# Siehe: docs/refactoring/REFACTORING_OPL.md
async def get_lightrag_wrapper_async() -> LightRAGClient:
    ...

# DC-003: DEPRECATED - wird in Sprint 56 entfernt
# Komplette Klasse nach Extraktion in lightrag/
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
- [Sprint 54 Plan](SPRINT_54_PLAN.md)

---

**END OF SPRINT 55 PLAN**
