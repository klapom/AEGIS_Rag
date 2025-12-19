# ADR-046: Comprehensive Refactoring Strategy

## Status
**Proposed** (2025-12-19)

## Context

Nach 52+ Sprints intensiver Feature-Entwicklung hat das AegisRAG-Projekt signifikante Technical Debt akkumuliert:

- **6 Hot-Spot Dateien** mit >1000 LOC
- **2 zirkuläre Dependencies** zwischen Modulen
- **45.2% ungetestete Module**
- **Fragmentierte Architektur** ohne klare Domain Boundaries

Der Analyse-Sprint hat folgende kritische Probleme identifiziert:

1. `langgraph_nodes.py` (2227 LOC) - 6 verschiedene Verantwortlichkeiten
2. `lightrag_wrapper.py` (1822 LOC) - 6 vermischte Concerns
3. `api/v1/admin.py` (4796 LOC) - God Object
4. Business Logic in `core/` statt in Domain-Modulen
5. Keine klaren Interface-Definitionen

## Decision

Wir implementieren ein **3-Phasen Refactoring** über 6 Sprints (53-58):

### Phase 1: Quick Wins (Sprint 53)
- Zirkuläre Dependencies auflösen
- Dead Code entfernen
- `admin.py` in 4 Module aufteilen

### Phase 2: Hot-Spot Refactoring (Sprint 54-55)
- `langgraph_nodes.py` → 6 spezialisierte Module
- `lightrag_wrapper.py` → 6 spezialisierte Module
- `chat.py` → 3 Module

### Phase 3: Domain Boundaries (Sprint 56-57)
- Domain-Driven Design Struktur etablieren
- Interface-Extraktionen für Testbarkeit
- Test Coverage auf 80% erhöhen

## Alternatives Considered

### 1. Big-Bang Refactoring (4 Wochen Feature-Freeze)
**Pro:**
- Konsistentere Architektur
- Schnellerer Gesamtabschluss

**Contra:**
- Hohes Risiko (keine Auslieferung)
- Team-Stillstand
- Merge-Konflikte mit Feature-Branches

### 2. Kein Refactoring (Status Quo)
**Pro:**
- Keine Unterbrechung der Feature-Entwicklung
- Kein unmittelbares Risiko

**Contra:**
- Wachsende Technical Debt
- Sinkende Entwicklerproduktivität
- Schwierigere Onboarding

### 3. Rewrite from Scratch
**Pro:**
- Saubere Architektur
- Moderne Patterns von Anfang an

**Contra:**
- 52 Sprints Wissen verloren
- 87k LOC neu schreiben
- 18+ Monate geschätzt

## Rationale

**Inkrementelles Refactoring** ist optimal weil:

1. **Risikominimierung:** Jeder Sprint liefert lauffähigen Code
2. **Rückwärtskompatibilität:** Bestehende Funktionalität bleibt erhalten
3. **Messbarkeit:** Klare Metriken pro Phase
4. **Flexibilität:** Anpassung basierend auf Learnings möglich

## Implementation

### Ziel-Architektur

```
src/
├── domains/                    # Business Logic
│   ├── query/                  # Query Execution
│   ├── knowledge_graph/        # Graph Reasoning
│   ├── vector_search/          # Vector Retrieval
│   ├── document_processing/    # Ingestion
│   ├── memory/                 # 3-Layer Memory
│   └── llm_integration/        # LLM Provisioning
├── infrastructure/             # Cross-Cutting
├── api/                        # Thin HTTP Layer
├── agents/                     # LangGraph Orchestration
└── evaluation/                 # Testing
```

### Modul-Splitting Strategie

**langgraph_nodes.py (2227 LOC) → 6 Module:**
```
nodes/
├── memory_management.py      [125 LOC]
├── document_parsers.py       [385 LOC]
├── image_enrichment.py       [275 LOC]
├── adaptive_chunking.py      [280 LOC]
├── vector_embedding.py       [240 LOC]
└── graph_extraction.py       [525 LOC]
```

**lightrag_wrapper.py (1822 LOC) → 6 Module:**
```
lightrag/
├── client.py               [210 LOC]
├── initialization.py       [180 LOC]
├── ingestion.py            [320 LOC]
├── converters.py           [200 LOC]
├── neo4j_storage.py        [340 LOC]
└── types.py                [50 LOC]
```

### Circular Dependency Resolution

**Cycle 1 Fix:**
```python
# Vorher: community_summarizer importiert admin
# Nachher: Dependency Injection
class CommunitySummarizer:
    def __init__(self, llm_config_provider: LLMConfigProvider):
        self.llm_config = llm_config_provider
```

**Cycle 2 Fix:**
```python
# Vorher: Self-import in lightrag_wrapper
# Nachher: Lazy import oder Interface
```

## Consequences

### Positive
- Reduzierte Dateigrößen (max 1000 LOC)
- Keine zirkulären Dependencies
- Bessere Testbarkeit (80%+ Coverage)
- Klare Domain Boundaries
- Einfacheres Onboarding

### Negative
- 6 Sprints Refactoring-Aufwand
- Temporäre Import-Änderungen
- Potenzielle Regressionen

### Mitigations
- Umfangreiche Integration Tests vor jedem Refactoring-Schritt
- Backward-Compatibility Layer für kritische Pfade
- Feature Flags für graduelle Umstellung
- Rollback-Plan pro Sprint

## Success Metrics

| Metrik | Aktuell | Ziel |
|--------|---------|------|
| Max. Datei-LOC | 4796 | <1000 |
| Zirkuläre Dependencies | 2 | 0 |
| Test Coverage | 54.8% | 80% |
| Avg. Complexity | 22.8 | <15 |

## Timeline

| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| 53 | Quick Wins | Cycles fixed, admin.py split |
| 54 | langgraph_nodes | 6 neue Module |
| 55 | lightrag_wrapper | 6 neue Module |
| 56 | Domain Boundaries | DDD Struktur |
| 57 | Interfaces | Protocol Definitions |
| 58 | Test Coverage | 80% erreicht |

## References

- [ANALYSIS_SPRINT_REPORT.md](../refactoring/ANALYSIS_SPRINT_REPORT.md)
- [ADR-001: LangGraph als Orchestrierung](ADR_INDEX.md)
- [TD_INDEX.md](../technical-debt/TD_INDEX.md)
