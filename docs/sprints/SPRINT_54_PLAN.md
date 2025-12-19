# Sprint 54: langgraph_nodes.py Refactoring

**Status:** PLANNED
**Branch:** `sprint-54-langgraph-nodes-split`
**Start Date:** TBD (nach Sprint 53)
**Estimated Duration:** 5 Tage
**Total Story Points:** 42 SP

---

## Sprint Overview

Sprint 54 zerlegt das größte Hot-Spot Modul `langgraph_nodes.py` (2227 LOC) in 6 spezialisierte Module.
Dies ist Phase 2 des Refactoring-Plans (ADR-046).

**Voraussetzung:** Sprint 53 abgeschlossen (Circular Dependencies aufgelöst)

**Referenzen:**
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **MUSS bei jeder Änderung aktualisiert werden!**

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 54.1 | Create nodes/ Package Structure | 3 | P0 | Nein (Foundation) |
| 54.2 | Extract memory_management Node | 5 | P1 | Ja (Agent 1) |
| 54.3 | Extract document_parsers Node | 8 | P1 | Ja (Agent 2) |
| 54.4 | Extract image_enrichment Node | 6 | P1 | Ja (Agent 3) |
| 54.5 | Extract adaptive_chunking Node | 6 | P1 | Ja (Agent 4) |
| 54.6 | Extract vector_embedding Node | 5 | P1 | Nach Wave 1 |
| 54.7 | Extract graph_extraction Node | 8 | P1 | Nach Wave 1 |
| 54.8 | Legacy Wrapper & OPL Update | 3 | P0 | Final |

**Total: 42 SP**

---

## Ziel-Struktur

```
src/components/ingestion/
├── nodes/                          # NEW Package
│   ├── __init__.py                 # Re-exports all nodes
│   ├── memory_management.py        # [125 LOC] Feature 54.2
│   ├── document_parsers.py         # [385 LOC] Feature 54.3
│   ├── image_enrichment.py         # [275 LOC] Feature 54.4
│   ├── adaptive_chunking.py        # [280 LOC] Feature 54.5
│   ├── vector_embedding.py         # [240 LOC] Feature 54.6
│   └── graph_extraction.py         # [525 LOC] Feature 54.7
├── langgraph_nodes.py              # [~50 LOC] Facade with re-exports (OPL-003)
├── langgraph_pipeline.py           # UNCHANGED (imports from nodes/)
└── ...
```

---

## Feature Details

### Feature 54.1: Create nodes/ Package Structure (3 SP)

**Priority:** P0 (Foundation)
**Parallelisierung:** Nein - blockt alle anderen Features

**OPL-Pflicht:** REFACTORING_OPL.md prüfen und OPL-003 vorbereiten.

**Aufgaben:**
1. Erstelle `src/components/ingestion/nodes/` Directory
2. Erstelle `src/components/ingestion/nodes/__init__.py`
3. Definiere gemeinsame Imports und Type Hints
4. Erstelle Shared Models Module

**Neue Dateien:**

```python
# src/components/ingestion/nodes/__init__.py
"""LangGraph Ingestion Pipeline Nodes.

Sprint 54: Modularized node functions for better maintainability.
Each node handles one specific stage of document ingestion.

Usage:
    from src.components.ingestion.nodes import (
        memory_check_node,
        docling_parse_node,
        image_enrichment_node,
        chunking_node,
        embedding_node,
        graph_extraction_node,
    )
"""

from src.components.ingestion.nodes.memory_management import memory_check_node
from src.components.ingestion.nodes.document_parsers import docling_parse_node
from src.components.ingestion.nodes.image_enrichment import image_enrichment_node
from src.components.ingestion.nodes.adaptive_chunking import chunking_node
from src.components.ingestion.nodes.vector_embedding import embedding_node
from src.components.ingestion.nodes.graph_extraction import graph_extraction_node

__all__ = [
    "memory_check_node",
    "docling_parse_node",
    "image_enrichment_node",
    "chunking_node",
    "embedding_node",
    "graph_extraction_node",
]
```

```python
# src/components/ingestion/nodes/models.py
"""Shared data models for ingestion nodes.

OPL-004: Diese Dataclasses werden temporär hier definiert.
Finale Location: src/components/ingestion/models.py (Sprint 56)
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SectionMetadata:
    """Section metadata extracted from Docling JSON."""
    heading: str
    level: int
    page_no: int
    bbox: dict[str, float]
    text: str
    token_count: int
    metadata: dict[str, Any]


@dataclass
class AdaptiveChunk:
    """Chunk with multi-section metadata."""
    chunk_id: str
    text: str
    sections: list[SectionMetadata]
    token_count: int
    metadata: dict[str, Any]
```

**Acceptance Criteria:**
- [ ] Package-Struktur erstellt
- [ ] `__init__.py` mit Placeholder-Imports
- [ ] Shared Models definiert
- [ ] OPL-003 und OPL-004 in REFACTORING_OPL.md eingetragen

---

### Feature 54.2: Extract memory_management Node (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 1 (nach 54.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `langgraph_nodes.py:64-190` (ca. 125 LOC)

**Zu extrahierende Elemente:**
- `memory_check_node()` Funktion
- RAM/VRAM Monitoring Utilities
- Container Restart Logic

**Neue Datei:** `src/components/ingestion/nodes/memory_management.py`

```python
"""Memory management node for ingestion pipeline.

Checks RAM/VRAM availability before each processing stage.
Implements container restart logic for memory leak mitigation.

Sprint 54 Feature 54.2: Extracted from langgraph_nodes.py
"""

import subprocess
from typing import TYPE_CHECKING

import structlog

from src.components.ingestion.ingestion_state import IngestionState, add_error
from src.core.config import settings

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


async def memory_check_node(state: IngestionState) -> IngestionState:
    """Check RAM/VRAM availability.

    Monitors system memory before each processing stage.
    Triggers container restart if VRAM exceeds threshold.

    Args:
        state: Current ingestion state

    Returns:
        Updated IngestionState with memory check results
    """
    # Implementation extracted from langgraph_nodes.py:64-190
    ...
```

**Verwendungsstellen aktualisieren:**
- `src/components/ingestion/langgraph_pipeline.py:35` - Import ändern
- `tests/unit/components/ingestion/test_langgraph_nodes_unit.py` - Tests anpassen

**Acceptance Criteria:**
- [ ] `memory_management.py` erstellt mit vollständiger Implementierung
- [ ] Import in `nodes/__init__.py` funktioniert
- [ ] Unit Tests passieren
- [ ] REFACTORING_OPL.md geprüft

---

### Feature 54.3: Extract document_parsers Node (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 2 (nach 54.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `langgraph_nodes.py:190-575` (ca. 385 LOC)

**Zu extrahierende Elemente:**
- `docling_parse_node()` Funktion
- Section Extraction Logic
- BBox Mapping
- Page Dimension Handling

**Neue Datei:** `src/components/ingestion/nodes/document_parsers.py`

**Abhängigkeiten:**
- `DoclingContainerClient`
- `SectionMetadata` (aus nodes/models.py)

**Verwendungsstellen:**
| Datei | Zeile | Import |
|-------|-------|--------|
| `langgraph_pipeline.py` | 38 | `docling_parse_node` |
| `streaming_pipeline.py` | 25 | `docling_parse_node` |
| `test_langgraph_nodes_unit.py` | 15 | Test imports |

**Acceptance Criteria:**
- [ ] `document_parsers.py` erstellt
- [ ] Section Extraction funktioniert
- [ ] BBox Mapping korrekt
- [ ] Integration Tests passieren

---

### Feature 54.4: Extract image_enrichment Node (6 SP)

**Priority:** P1
**Parallelisierung:** Agent 3 (nach 54.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `langgraph_nodes.py:575-850` (ca. 275 LOC)

**Zu extrahierende Elemente:**
- `image_enrichment_node()` Funktion
- VLM Integration (Qwen3-VL)
- Image Description Generation
- Embedding für Bilder

**Neue Datei:** `src/components/ingestion/nodes/image_enrichment.py`

**Abhängigkeiten:**
- `ImageProcessor`
- `AegisLLMProxy` für VLM

**WICHTIG für Sprint 59:**
Image Enrichment wird in Sprint 59 erweitert für multimodale Agentic Features.

**Acceptance Criteria:**
- [ ] `image_enrichment.py` erstellt
- [ ] VLM Integration funktioniert
- [ ] Bilder werden korrekt verarbeitet

---

### Feature 54.5: Extract adaptive_chunking Node (6 SP)

**Priority:** P1
**Parallelisierung:** Agent 4 (nach 54.1)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `langgraph_nodes.py:850-1130` (ca. 280 LOC)

**Zu extrahierende Elemente:**
- `chunking_node()` Funktion
- Adaptive Section Chunking Algorithm
- Token Counting
- Chunk Merging Logic

**Neue Datei:** `src/components/ingestion/nodes/adaptive_chunking.py`

**Abhängigkeiten:**
- `ChunkingService`
- `AdaptiveChunk` Dataclass

**Verwendungsstellen:**
| Datei | Zeile | Import |
|-------|-------|--------|
| `langgraph_pipeline.py` | 40 | `chunking_node` |
| `section_extraction.py` | 10 | Uses chunking logic |
| `test_adaptive_chunking.py` | 5 | Test imports |

**Acceptance Criteria:**
- [ ] `adaptive_chunking.py` erstellt
- [ ] Token Limits (800-1800) eingehalten
- [ ] Section Merging korrekt

---

### Feature 54.6: Extract vector_embedding Node (5 SP)

**Priority:** P1
**Parallelisierung:** Nach Wave 1 (braucht 54.5)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `langgraph_nodes.py:1130-1370` (ca. 240 LOC)

**Zu extrahierende Elemente:**
- `embedding_node()` Funktion
- BGE-M3 Embedding Generation
- Qdrant Upsert Logic
- Provenance Metadata

**Neue Datei:** `src/components/ingestion/nodes/vector_embedding.py`

**Abhängigkeiten:**
- `EmbeddingService`
- `QdrantClientWrapper`
- Chunks von `adaptive_chunking`

**Acceptance Criteria:**
- [ ] `vector_embedding.py` erstellt
- [ ] BGE-M3 Embeddings generiert
- [ ] Qdrant Upsert funktioniert
- [ ] Provenance Metadata korrekt

---

### Feature 54.7: Extract graph_extraction Node (8 SP)

**Priority:** P1
**Parallelisierung:** Nach Wave 1 (größtes Modul)

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Quellcode-Bereich:** `langgraph_nodes.py:1370-1900` (ca. 525 LOC)

**Zu extrahierende Elemente:**
- `graph_extraction_node()` Funktion
- Entity/Relationship Extraction
- Neo4j Upsert Logic
- Community Detection Trigger
- RELATES_TO / MENTIONED_IN Creation

**Neue Datei:** `src/components/ingestion/nodes/graph_extraction.py`

**Abhängigkeiten:**
- `LightRAGClient`
- `CommunityDetector`
- `Neo4jClient`

**WICHTIG:**
Dies ist das kritischste Modul - enthält die LightRAG Integration.
Besondere Sorgfalt bei der Extraktion!

**Acceptance Criteria:**
- [ ] `graph_extraction.py` erstellt
- [ ] Entity Extraction funktioniert
- [ ] RELATES_TO Relationen korrekt
- [ ] Community Detection wird getriggert
- [ ] Neo4j Daten konsistent

---

### Feature 54.8: Legacy Wrapper & OPL Update (3 SP)

**Priority:** P0 (Final)
**Parallelisierung:** Nach allen anderen Features

**OPL-Pflicht:** REFACTORING_OPL.md MUSS aktualisiert werden!

**Aufgaben:**
1. Reduziere `langgraph_nodes.py` auf Facade
2. Implementiere Backward-Compat Re-Exports (OPL-003)
3. Aktualisiere REFACTORING_OPL.md
4. Dokumentiere alle Verwendungsstellen

**langgraph_nodes.py nach Refactoring:**

```python
"""LangGraph Ingestion Pipeline Nodes - Legacy Facade.

Sprint 54: This file is now a facade for backward compatibility.
Direct imports from src.components.ingestion.nodes/ preferred.

OPL-003: Diese Re-Exports werden in Sprint 55 entfernt.
Siehe: docs/refactoring/REFACTORING_OPL.md
"""

# OPL-003: Backward-compatibility re-exports
from src.components.ingestion.nodes import (
    memory_check_node,
    docling_parse_node,
    image_enrichment_node,
    chunking_node,
    embedding_node,
    graph_extraction_node,
)

# OPL-004: Dataclass re-exports
from src.components.ingestion.nodes.models import (
    SectionMetadata,
    AdaptiveChunk,
)

__all__ = [
    "memory_check_node",
    "docling_parse_node",
    "image_enrichment_node",
    "chunking_node",
    "embedding_node",
    "graph_extraction_node",
    "SectionMetadata",
    "AdaptiveChunk",
]
```

**REFACTORING_OPL.md Update:**
- OPL-003: Status prüfen, Verwendungsstellen aktualisieren
- OPL-004: Status prüfen

**Acceptance Criteria:**
- [ ] `langgraph_nodes.py` < 100 LOC
- [ ] Alle Re-Exports funktionieren
- [ ] REFACTORING_OPL.md aktualisiert
- [ ] Alle 22+ Verwendungsstellen dokumentiert

---

## Parallel Execution Strategy

### Wave 1 (Tag 1): Foundation
```
Agent 1: Feature 54.1 - Package Structure (BLOCKER)
```

### Wave 2 (Tag 2-3): Core Nodes (4 Agents parallel)
```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │   Agent 4      │
│   54.2       │   54.3       │   54.4       │   54.5         │
│   Memory     │   Parsers    │   Image      │   Chunking     │
│   5 SP       │   8 SP       │   6 SP       │   6 SP         │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Wave 3 (Tag 4): Dependent Nodes
```
┌─────────────────────────────────────────┐
│           PARALLEL EXECUTION             │
├───────────────────┬─────────────────────┤
│      Agent 1      │      Agent 2        │
│      54.6         │      54.7           │
│      Embedding    │      Graph Extract  │
│      5 SP         │      8 SP           │
└───────────────────┴─────────────────────┘
```

### Wave 4 (Tag 5): Finalization
```
Agent 1: Feature 54.8 - Legacy Wrapper
Agent 2: Integration Tests
Agent 3: Documentation
Agent 4: OPL Update & Verification
```

---

## Verwendungsstellen-Matrix

| Datei | memory | parsers | image | chunking | embedding | graph |
|-------|--------|---------|-------|----------|-----------|-------|
| `langgraph_pipeline.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `streaming_pipeline.py` | ✓ | ✓ | - | ✓ | ✓ | ✓ |
| `section_extraction.py` | - | - | - | ✓ | - | - |
| `test_langgraph_nodes_unit.py` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `test_streaming_pipeline.py` | ✓ | ✓ | - | ✓ | ✓ | ✓ |
| `test_vlm_enrichment_node.py` | - | - | ✓ | - | - | - |

---

## Acceptance Criteria (Sprint Complete)

- [ ] `langgraph_nodes.py` von 2227 LOC auf <100 LOC reduziert
- [ ] 6 neue Node-Module in `nodes/` Package
- [ ] Alle Imports funktionieren (direkt und via Facade)
- [ ] Alle Unit Tests passieren
- [ ] Alle Integration Tests passieren
- [ ] REFACTORING_OPL.md aktualisiert (OPL-003, OPL-004)
- [ ] Keine neuen zirkulären Dependencies

---

## Risk Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| LangGraph State-Fehler | Medium | High | State-Typ unverändert lassen |
| Import-Fehler | Medium | Medium | Facade für Backward-Compat |
| Performance-Regression | Low | Medium | Benchmarks vor/nach |
| Community Detection Break | Low | High | Extensive Tests |

---

## Definition of Done

### Per Feature
- [ ] Node-Modul extrahiert und funktional
- [ ] Unit Tests angepasst
- [ ] Import in `__init__.py`
- [ ] REFACTORING_OPL.md geprüft

### Sprint Complete
- [ ] Alle 6 Node-Module erstellt
- [ ] Legacy Facade funktional
- [ ] CI/CD grün
- [ ] OPL-003, OPL-004 dokumentiert

---

---

## Subagent-Anweisungen: OPL & Dead Code

**WICHTIG:** Jeder Subagent MUSS bei Refactoring-Arbeiten folgende Dokumente pflegen:

### 1. OPL-Einträge (Zwischenlösungen)

| Situation | Aktion |
|-----------|--------|
| Backward-Compat Re-Export | OPL-XXX erstellen |
| Lazy Import | OPL-XXX erstellen |
| Temporärer Wrapper | OPL-XXX erstellen |

**Sprint 54 OPL-Einträge:**
- OPL-003: Node Function Aliases in langgraph_nodes.py
- OPL-004: Shared Dataclasses in nodes/models.py

### 2. Dead Code Tracking (DC-XXX)

| Situation | Kategorie | Aktion |
|-----------|-----------|--------|
| Extrahierter Code | DEPRECATED | DC-XXX, Entfernung nächster Sprint |
| Unused nach Analyse | ORPHANED | DC-XXX, sofort entfernen |

**Sprint 54 DC-Einträge:**
- DC-002: langgraph_nodes.py Originale → Entfernung Sprint 55

### 3. Code-Kommentare

```python
# OPL-003: Backward-compat alias until Sprint 55
# Siehe: docs/refactoring/REFACTORING_OPL.md
from src.components.ingestion.nodes import memory_check_node

# DC-002: DEPRECATED - wird in Sprint 55 entfernt
# Original-Implementierung nach Extraktion
```

### 4. Verification vor Dead Code Entfernung

```bash
# Vor Entfernung von DC-002 (langgraph_nodes Originale)
grep -r "from src.components.ingestion.langgraph_nodes import" src/ --include="*.py"
# Erwartung: Nur nodes/__init__.py importiert
```

### 5. Checkliste pro Feature

- [ ] Feature implementiert
- [ ] OPL-Eintrag erstellt (falls Zwischenlösung)
- [ ] DC-Eintrag erstellt (falls Code ersetzt)
- [ ] Code-Kommentare mit OPL/DC-IDs
- [ ] REFACTORING_OPL.md aktualisiert

---

## References

- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **OPL + Dead Code Tracking**
- [Sprint 53 Plan](SPRINT_53_PLAN.md)

---

**END OF SPRINT 54 PLAN**
