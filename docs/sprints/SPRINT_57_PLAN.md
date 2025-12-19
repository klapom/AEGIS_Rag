# Sprint 57: Interfaces & Protocols

**Status:** PLANNED
**Branch:** `sprint-57-interfaces-protocols`
**Start Date:** TBD (nach Sprint 56)
**Estimated Duration:** 5 Tage
**Total Story Points:** 35 SP

---

## Sprint Overview

Sprint 57 definiert Protocol-basierte Interfaces für alle Domains.
Dies verbessert Testbarkeit, ermöglicht Dependency Injection und reduziert Coupling.

**Voraussetzung:** Sprint 56 abgeschlossen (Domain Boundaries etabliert)

**Referenzen:**
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **MUSS bei jeder Änderung aktualisiert werden!**

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 57.1 | Knowledge Graph Protocols | 8 | P1 | Ja (Agent 1) |
| 57.2 | Document Processing Protocols | 6 | P1 | Ja (Agent 2) |
| 57.3 | LLM Integration Protocols | 6 | P1 | Ja (Agent 3) |
| 57.4 | Vector Search Protocols | 5 | P1 | Ja (Agent 4) |
| 57.5 | Memory Protocols | 5 | P1 | Nach Wave 1 |
| 57.6 | Dependency Injection Container | 5 | P0 | Final |
| 57.7 | OPL Final Cleanup | 3 | P0 | Final |

**Total: 35 SP**

---

## Feature Details

### Feature 57.1: Knowledge Graph Protocols (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 1

**OPL-Pflicht:** OPL-007 in REFACTORING_OPL.md dokumentieren!

**Neue Datei:** `src/domains/knowledge_graph/protocols.py`

```python
"""Knowledge Graph Domain Protocols.

Sprint 57 Feature 57.1: Protocol definitions for graph operations.
Enables dependency injection and improves testability.
"""

from typing import Protocol, Any, AsyncIterator
from dataclasses import dataclass


class EntityExtractor(Protocol):
    """Protocol for entity extraction from text."""

    async def extract_entities(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract entities from text.

        Args:
            text: Source text
            metadata: Optional metadata for context

        Returns:
            List of extracted entities
        """
        ...


class RelationExtractor(Protocol):
    """Protocol for relation extraction."""

    async def extract_relations(
        self,
        entities: list[dict[str, Any]],
        text: str,
    ) -> list[dict[str, Any]]:
        """Extract relations between entities."""
        ...


class GraphStorage(Protocol):
    """Protocol for graph persistence."""

    async def upsert_entity(self, entity: dict[str, Any]) -> str:
        """Upsert an entity to the graph."""
        ...

    async def upsert_relation(self, relation: dict[str, Any]) -> str:
        """Upsert a relation to the graph."""
        ...

    async def query(self, cypher: str, params: dict | None = None) -> list[Any]:
        """Execute a Cypher query."""
        ...


class GraphQueryService(Protocol):
    """Protocol for graph querying."""

    async def query_local(self, query: str, top_k: int = 10) -> dict[str, Any]:
        """Execute local (entity-focused) query."""
        ...

    async def query_global(self, query: str, top_k: int = 10) -> dict[str, Any]:
        """Execute global (community-focused) query."""
        ...

    async def query_hybrid(self, query: str, top_k: int = 10) -> dict[str, Any]:
        """Execute hybrid query."""
        ...


class CommunityService(Protocol):
    """Protocol for community detection and summarization."""

    async def detect_communities(self) -> list[dict[str, Any]]:
        """Detect communities in the graph."""
        ...

    async def summarize_community(
        self,
        community_id: str,
        llm_config_provider: "LLMConfigProvider",
    ) -> str:
        """Generate summary for a community."""
        ...


class LLMConfigProvider(Protocol):
    """Protocol for LLM configuration.

    Resolves OPL-001 circular dependency.
    """

    async def get_community_summary_model(self) -> str:
        """Get configured model for community summaries."""
        ...

    async def get_extraction_model(self) -> str:
        """Get configured model for entity extraction."""
        ...
```

**Verwendungsstellen:**
- `src/domains/knowledge_graph/extraction/factory.py`
- `src/domains/knowledge_graph/communities/detector.py`
- `src/domains/knowledge_graph/communities/summarizer.py`
- `tests/unit/` - Mock implementations

**Acceptance Criteria:**
- [ ] Alle Protocols definiert
- [ ] Bestehende Klassen implementieren Protocols
- [ ] OPL-001 final aufgelöst (LLMConfigProvider)

---

### Feature 57.2: Document Processing Protocols (6 SP)

**Priority:** P1
**Parallelisierung:** Agent 2

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Neue Datei:** `src/domains/document_processing/protocols.py`

```python
"""Document Processing Domain Protocols.

Sprint 57 Feature 57.2: Protocol definitions for document ingestion.
"""

from typing import Protocol, Any, AsyncIterator
from pathlib import Path


class DocumentParser(Protocol):
    """Protocol for document parsing."""

    async def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse a document and extract content."""
        ...

    async def extract_sections(self, parsed_doc: dict) -> list[dict[str, Any]]:
        """Extract sections from parsed document."""
        ...


class ChunkingService(Protocol):
    """Protocol for text chunking."""

    def chunk(
        self,
        text: str,
        min_tokens: int = 800,
        max_tokens: int = 1800,
    ) -> list[dict[str, Any]]:
        """Chunk text into optimal segments."""
        ...


class ImageEnricher(Protocol):
    """Protocol for image enrichment via VLM."""

    async def enrich_images(
        self,
        images: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate descriptions for images."""
        ...


class IngestionPipeline(Protocol):
    """Protocol for document ingestion pipeline."""

    async def ingest(
        self,
        file_path: Path,
        namespace: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Ingest a document with progress events."""
        ...
```

**WICHTIG für Sprint 59:**
Diese Protocols müssen für Sprint 59 erweiterbar sein:
- `CodeExecutor` Protocol für Bash/Python
- `SandboxedRunner` Protocol

**Acceptance Criteria:**
- [ ] Alle Protocols definiert
- [ ] Pipeline Nodes implementieren Protocols
- [ ] Erweiterbar für Sprint 59

---

### Feature 57.3: LLM Integration Protocols (6 SP)

**Priority:** P1
**Parallelisierung:** Agent 3

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Neue Datei:** `src/domains/llm_integration/protocols.py`

```python
"""LLM Integration Domain Protocols.

Sprint 57 Feature 57.3: Protocol definitions for LLM operations.
"""

from typing import Protocol, Any, AsyncIterator
from enum import Enum


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from prompt."""
        ...

    async def stream(
        self,
        prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream text generation."""
        ...


class LLMRouter(Protocol):
    """Protocol for multi-cloud LLM routing."""

    async def route(
        self,
        task_type: str,
        preferred_provider: str | None = None,
    ) -> "LLMProvider":
        """Route request to optimal provider."""
        ...


class CostTracker(Protocol):
    """Protocol for LLM cost tracking."""

    async def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record LLM usage for cost tracking."""
        ...

    async def get_total_cost(self, period: str = "day") -> float:
        """Get total cost for period."""
        ...


class ToolExecutor(Protocol):
    """Protocol for LLM tool execution.

    IMPORTANT: Required for Sprint 59 Agentic Features!
    """

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool with given parameters."""
        ...

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools with schemas."""
        ...
```

**WICHTIG für Sprint 59:**
`ToolExecutor` Protocol ist die Grundlage für:
- Bash/Python Execution
- Agentic Search
- Deep Research

**Acceptance Criteria:**
- [ ] Alle Protocols definiert
- [ ] AegisLLMProxy implementiert Protocols
- [ ] ToolExecutor für Sprint 59 vorbereitet

---

### Feature 57.4: Vector Search Protocols (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 4

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Neue Datei:** `src/domains/vector_search/protocols.py`

```python
"""Vector Search Domain Protocols.

Sprint 57 Feature 57.4: Protocol definitions for vector operations.
"""

from typing import Protocol, Any


class EmbeddingService(Protocol):
    """Protocol for embedding generation."""

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...


class VectorStore(Protocol):
    """Protocol for vector storage."""

    async def upsert(
        self,
        vectors: list[dict[str, Any]],
        collection: str,
    ) -> None:
        """Upsert vectors to collection."""
        ...

    async def search(
        self,
        query_vector: list[float],
        collection: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        ...


class HybridSearchService(Protocol):
    """Protocol for hybrid search."""

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Execute hybrid search (vector + BM25)."""
        ...
```

**Acceptance Criteria:**
- [ ] Alle Protocols definiert
- [ ] Qdrant Client implementiert VectorStore
- [ ] BGE-M3 Service implementiert EmbeddingService

---

### Feature 57.5: Memory Protocols (5 SP)

**Priority:** P1
**Parallelisierung:** Nach Wave 1

**OPL-Pflicht:** Bei Zwischenlösungen → REFACTORING_OPL.md aktualisieren!

**Neue Datei:** `src/domains/memory/protocols.py`

```python
"""Memory Domain Protocols.

Sprint 57 Feature 57.5: Protocol definitions for memory operations.
"""

from typing import Protocol, Any


class ConversationMemory(Protocol):
    """Protocol for conversation memory."""

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Add message to conversation."""
        ...

    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get conversation history."""
        ...


class SessionStore(Protocol):
    """Protocol for session storage."""

    async def create_session(self, user_id: str | None = None) -> str:
        """Create new session."""
        ...

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        ...

    async def delete_session(self, session_id: str) -> None:
        """Delete session."""
        ...


class CacheService(Protocol):
    """Protocol for caching."""

    async def get(self, key: str) -> Any | None:
        """Get cached value."""
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set cached value."""
        ...
```

**Acceptance Criteria:**
- [ ] Alle Protocols definiert
- [ ] Redis Memory implementiert Protocols
- [ ] Graphiti Integration vorbereitet

---

### Feature 57.6: Dependency Injection Container (5 SP)

**Priority:** P0 (Wichtig für Testbarkeit)
**Parallelisierung:** Nach allen Protocol-Features

**OPL-Pflicht:** REFACTORING_OPL.md aktualisieren!

**Neue Datei:** `src/infrastructure/di/container.py`

```python
"""Dependency Injection Container.

Sprint 57 Feature 57.6: Central DI container for service registration.
Replaces singleton patterns and enables testing with mocks.
"""

from typing import Type, TypeVar, Any, Callable
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class Container:
    """Simple dependency injection container."""

    _instance: "Container | None" = None
    _registrations: dict[Type, Callable] = {}
    _singletons: dict[Type, Any] = {}

    @classmethod
    def get(cls) -> "Container":
        """Get container singleton."""
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    def register(
        self,
        interface: Type[T],
        factory: Callable[[], T],
        singleton: bool = True,
    ) -> None:
        """Register a service factory."""
        self._registrations[interface] = (factory, singleton)

    async def resolve(self, interface: Type[T]) -> T:
        """Resolve a service instance."""
        if interface in self._singletons:
            return self._singletons[interface]

        if interface not in self._registrations:
            raise KeyError(f"No registration for {interface}")

        factory, is_singleton = self._registrations[interface]
        instance = await factory() if asyncio.iscoroutinefunction(factory) else factory()

        if is_singleton:
            self._singletons[interface] = instance

        return instance

    def reset(self) -> None:
        """Reset container (for testing)."""
        self._singletons.clear()


# Convenience functions
def get_container() -> Container:
    return Container.get()


async def resolve(interface: Type[T]) -> T:
    return await Container.get().resolve(interface)
```

**Service Registration:**

```python
# src/infrastructure/di/setup.py
"""Service registration for production."""

from src.infrastructure.di.container import Container
from src.domains.knowledge_graph.protocols import (
    GraphStorage,
    EntityExtractor,
)
from src.domains.knowledge_graph.persistence import Neo4jStorage
from src.domains.knowledge_graph.extraction import LLMEntityExtractor


def setup_production_container() -> Container:
    """Configure container for production."""
    container = Container.get()

    # Knowledge Graph
    container.register(GraphStorage, Neo4jStorage.create, singleton=True)
    container.register(EntityExtractor, LLMEntityExtractor.create, singleton=True)

    # ... weitere Registrierungen

    return container
```

**Resolves OPL-005:**
```python
# Statt:
client = await get_lightrag_wrapper_async()  # OPL-005 Singleton

# Jetzt:
from src.infrastructure.di import resolve
from src.domains.knowledge_graph.protocols import GraphQueryService

client = await resolve(GraphQueryService)
```

**Acceptance Criteria:**
- [ ] DI Container implementiert
- [ ] Production Setup konfiguriert
- [ ] OPL-005 auflösbar

---

### Feature 57.7: OPL Final Cleanup (3 SP)

**Priority:** P0 (Final)
**Parallelisierung:** Nach allen anderen Features

**OPL-Pflicht:** ALLE OPL-Einträge prüfen und aktualisieren!

**Aufgaben:**
1. Alle OPL-001 bis OPL-006 Status prüfen
2. OPL-007 dokumentieren (letzte konkrete Typen)
3. Verwendungsstellen bereinigen
4. Backward-Compat Layer prüfen

**Expected OPL Status nach Sprint 57:**

| OPL-ID | Expected Status | Notes |
|--------|-----------------|-------|
| OPL-001 | RESOLVED | LLMConfigProvider Protocol |
| OPL-002 | RESOLVED | Admin Imports migriert |
| OPL-003 | RESOLVED | Node Imports migriert |
| OPL-004 | RESOLVED | Models in Domains |
| OPL-005 | IN_PROGRESS | DI Container ersetzt Singletons |
| OPL-006 | IN_PROGRESS | Cross-Domain Imports |
| OPL-007 | OPEN | Letzte konkrete Typen |

**Acceptance Criteria:**
- [ ] Alle OPL Status aktuell
- [ ] OPL-001 bis OPL-004 RESOLVED
- [ ] Plan für OPL-005, OPL-006, OPL-007 in Sprint 58

---

## Parallel Execution Strategy

### Wave 1 (Tag 1-3): Domain Protocols (4 Agents parallel)
```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │   Agent 4      │
│   57.1       │   57.2       │   57.3       │   57.4         │
│   Graph      │   Document   │   LLM        │   Vector       │
│   8 SP       │   6 SP       │   6 SP       │   5 SP         │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Wave 2 (Tag 4): Remaining Protocols
```
Agent 1: Feature 57.5 - Memory Protocols
Agent 2: Feature 57.6 - DI Container (parallel)
```

### Wave 3 (Tag 5): Finalization
```
Agent 1: Feature 57.7 - OPL Cleanup
Agent 2: Integration Tests
Agent 3: Documentation
Agent 4: Type Checking (MyPy)
```

---

## Acceptance Criteria (Sprint Complete)

- [ ] Alle 5 Domain Protocols definiert
- [ ] DI Container funktional
- [ ] Bestehende Klassen implementieren Protocols
- [ ] MyPy strict Mode passiert
- [ ] OPL-001 bis OPL-004 RESOLVED
- [ ] OPL-007 dokumentiert

---

## Definition of Done

### Per Feature
- [ ] Protocols definiert
- [ ] Implementierungen angepasst
- [ ] Unit Tests mit Mocks
- [ ] REFACTORING_OPL.md aktualisiert

### Sprint Complete
- [ ] Alle Protocols vorhanden
- [ ] DI Container ready
- [ ] CI/CD grün
- [ ] OPL Status aktuell

---

---

## Subagent-Anweisungen: OPL & Dead Code

**WICHTIG:** Jeder Subagent MUSS bei Refactoring-Arbeiten folgende Dokumente pflegen:

### 1. OPL-Einträge (Zwischenlösungen)

**Sprint 57 OPL-Einträge:**
- OPL-007: Concrete Type Dependencies (graduell durch Protocols ersetzen)

**Zu prüfende OPL aus vorherigen Sprints:**
- OPL-001: RESOLVED (LLMConfigProvider Protocol)
- OPL-002: RESOLVED (Admin Imports)
- OPL-003: RESOLVED (Node Imports)
- OPL-004: RESOLVED (Models migriert)
- OPL-005: IN_PROGRESS (DI Container ersetzt Singletons)
- OPL-006: IN_PROGRESS (Cross-Domain Imports)

### 2. Dead Code Status

**Kein neuer Dead Code in Sprint 57** - Fokus auf Interfaces.

**Zu verifizierende DC-Einträge:**
- DC-001: REMOVED (Sprint 54)
- DC-002: REMOVED (Sprint 55)
- DC-003: REMOVED (Sprint 56)
- DC-004: OPEN (Entfernung Sprint 58)

### 3. Protocol Implementation Tracking

Bei Umstellung auf Protocols:
```python
# Vorher (OPL-007: Concrete Type)
def process(client: LightRAGClient) -> None:
    ...

# Nachher (Protocol-based)
def process(client: GraphQueryService) -> None:
    ...
```

### 4. OPL Resolution Checkliste

Für jeden OPL-Eintrag der RESOLVED wird:
- [ ] Code-Kommentare entfernen (`# OPL-XXX`)
- [ ] Re-Exports entfernen (falls applicable)
- [ ] Status in REFACTORING_OPL.md updaten
- [ ] Verification-Script ausführen

### 5. Checkliste pro Feature

- [ ] Protocol definiert
- [ ] Implementierungen angepasst
- [ ] OPL-Einträge geprüft
- [ ] REFACTORING_OPL.md aktualisiert

---

## References

- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **OPL + Dead Code Tracking**
- [Sprint 56 Plan](SPRINT_56_PLAN.md)

---

**END OF SPRINT 57 PLAN**
