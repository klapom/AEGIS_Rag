# Sprint 60: Documentation Consolidation & Technical Investigations

**Status:** PLANNED
**Branch:** `sprint-60-docs-consolidation`
**Start Date:** TBD (nach Sprint 59)
**Estimated Duration:** 5-7 Tage
**Total Story Points:** 45 SP

---

## Sprint Overview

Sprint 60 fokussiert auf **Dokumentations-Konsolidierung** nach Abschluss des Refactorings
und führt mehrere **technische Voruntersuchungen** durch.

**Ziele:**
1. Dokumentation auf aktuellen Stand bringen
2. Veraltete Dokumentation entfernen/archivieren
3. Technische Investigations für Performance-Optimierungen
4. GRAPHITI_REFERENCE.md Analyse für Temporal Queries

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 60.1 | Core Documentation Consolidation | 13 | P0 | Ja (Agent 1) |
| 60.2 | GRAPHITI Temporal Queries Analysis | 8 | P1 | Ja (Agent 2) |
| 60.3 | Section Nodes Implementation Review | 3 | P1 | Ja (Agent 3) |
| 60.4 | TD-069: Multihop Endpoint Review | 3 | P2 | Ja (Agent 4) |
| 60.5 | TD-071: vLLM Investigation | 5 | P2 | Nach 60.1 |
| 60.6 | TD-072: Sentence-Transformers Reranking | 5 | P2 | Nach 60.1 |
| 60.7 | TD-073: Sentence-Transformers Embeddings | 5 | P2 | Nach 60.1 |
| 60.8 | Subdirectory Cleanup | 3 | P2 | Final |

**Total: 45 SP**

---

## Feature Details

### Feature 60.1: Core Documentation Consolidation (13 SP)

**Priority:** P0
**Parallelisierung:** Agent 1

**Ziel:** Die 7 Haupt-Dokumentationsdateien auf aktuellen Stand bringen und konsolidieren.

#### Zu aktualisierende/konsolidierende Dateien:

| Aktuelle Datei | Aktion | Ziel |
|----------------|--------|------|
| `ARCHITECTURE_EVOLUTION.md` | Aktualisieren | Neue DDD-Struktur (Sprint 56) |
| `COMPONENT_INTERACTION_MAP.md` | Aktualisieren | Domains statt Components |
| `DECISION_LOG.md` | Aktualisieren | Sprint 53-59 Entscheidungen |
| `DEPENDENCY_RATIONALE.md` | Aktualisieren/Merge | → TECH_STACK.md |
| `NAMING_CONVENTIONS.md` | Aktualisieren | Domains, Protocols |
| `STRUCTURE.md` | Neu schreiben | Neue Verzeichnisstruktur |
| `TECH_STACK.md` | Erweitern | + DGX Spark, + Dependencies |

#### Konsolidierungs-Vorschlag:

```
VORHER (7 Dateien):
├── ARCHITECTURE_EVOLUTION.md
├── COMPONENT_INTERACTION_MAP.md
├── DECISION_LOG.md
├── DEPENDENCY_RATIONALE.md
├── NAMING_CONVENTIONS.md
├── STRUCTURE.md
└── TECH_STACK.md

NACHHER (4 Dateien):
├── ARCHITECTURE.md          # Merge: Evolution + Component Map + Structure
├── TECH_STACK.md             # Merge: + Dependency Rationale + DGX Spark
├── CONVENTIONS.md            # Rename: Naming Conventions
└── DECISION_LOG.md           # Keep: Important history
```

#### Zusätzliche Integration:

| Zu integrierende Datei | Ziel |
|------------------------|------|
| `CLAUDE_zusatzinfos.md` | → TECH_STACK.md (DGX Spark Section) |
| `DGX_SPARK_SM121_REFERENCE.md` | → TECH_STACK.md (DGX Spark Section) |

#### ARCHITECTURE.md Struktur (neu):

```markdown
# AegisRAG Architecture

## Overview
- High-level system diagram
- Domain boundaries

## Domain Structure (Sprint 56)
- knowledge_graph/
- document_processing/
- vector_search/
- memory/
- llm_integration/

## Component Interactions
- Sequence diagrams
- Data flow

## Evolution History
- Key milestones (merged from ARCHITECTURE_EVOLUTION.md)
```

#### TECH_STACK.md Erweiterungen:

```markdown
# Technology Stack

## Core Stack
- (existing content)

## DGX Spark Deployment (NEW - from DGX_SPARK_SM121_REFERENCE.md)
- Hardware specs
- CUDA 13.0 configuration
- Framework compatibility
- Flash Attention workaround

## Dependency Rationale (from DEPENDENCY_RATIONALE.md)
- Why each major dependency
- Version pinning strategy

## Claude Code Integration (from CLAUDE_zusatzinfos.md)
- Development workflow tips
- Useful commands
```

**Acceptance Criteria:**
- [ ] 7 Dateien auf 4 konsolidiert
- [ ] Alle Inhalte aktuell (Sprint 53-59 berücksichtigt)
- [ ] DGX Spark Infos in TECH_STACK.md
- [ ] CLAUDE_zusatzinfos.md archiviert/entfernt

---

### Feature 60.2: GRAPHITI Temporal Queries Analysis (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 2

**Ziel:** Analyse von `GRAPHITI_REFERENCE.md` bezüglich Temporal Queries und
Aufwandsschätzung für Implementation.

#### Analyse-Fragen:

1. **Feature-Scope:**
   - Welche Temporal Query Features bietet Graphiti?
   - Bi-temporal vs. Application-time vs. System-time?
   - Time-Travel Queries?

2. **Integration Complexity:**
   - Kompatibilität mit aktuellem Neo4j Schema?
   - Änderungen an Entity/Relation Modellen nötig?
   - Impact auf bestehende Queries?

3. **Implementation Aufwand:**
   - Story Points Schätzung
   - Voraussetzungen (Schema Migration?)
   - Abhängigkeiten (TD-064: Temporal Community Summaries)

4. **Use Cases:**
   - "Was wusste das System am Datum X?"
   - "Wie hat sich Entity Y über Zeit verändert?"
   - "Zeige Graph-Zustand vom letzten Monat"

#### Deliverables:

1. **Analyse-Dokument:** `docs/analysis/TEMPORAL_QUERIES_ANALYSIS.md`
2. **Feature TD (falls lohnend):** `TD-074_TEMPORAL_QUERIES_GRAPHITI.md`
3. **Empfehlung:** Implement / Defer / Skip

**Acceptance Criteria:**
- [ ] GRAPHITI_REFERENCE.md vollständig analysiert
- [ ] Temporal Query Features dokumentiert
- [ ] Aufwandsschätzung (SP) erstellt
- [ ] Empfehlung mit Begründung
- [ ] Ggf. TD-074 erstellt

---

### Feature 60.3: Section Nodes Implementation Review (3 SP)

**Priority:** P1
**Parallelisierung:** Agent 3

**Ziel:** Prüfen ob die in `docs/features/SECTION_NODES_QUERIES.md` beschriebene
Funktionalität implementiert wurde.

#### Review-Tasks:

1. **Code-Analyse:**
   - Existiert `section_nodes` Funktionalität?
   - Wo ist sie implementiert?
   - Wird sie aktiv genutzt?

2. **Feature-Status:**
   | Feature | Beschrieben | Implementiert | Aktiv |
   |---------|-------------|---------------|-------|
   | Section Node Creation | ? | ? | ? |
   | Section-based Queries | ? | ? | ? |
   | Section Hierarchy | ? | ? | ? |
   | Section Metadata | ? | ? | ? |

3. **Entscheidung:**
   - Feature vollständig → Dokumentation aktualisieren
   - Feature teilweise → TD erstellen für Completion
   - Feature nicht implementiert → Entscheiden: Implement oder Remove Docs

#### Zu durchsuchende Dateien:

```bash
# Code-Suche
grep -r "section_node\|SectionNode\|section_query" src/
grep -r "section" src/components/graph_rag/
grep -r "section" src/api/v1/

# Test-Suche
grep -r "section" tests/
```

**Deliverables:**
- Status-Report in `SECTION_NODES_QUERIES.md` (updated)
- Ggf. TD für Completion/Removal

**Acceptance Criteria:**
- [ ] Implementation Status dokumentiert
- [ ] Code-Referenzen identifiziert
- [ ] Empfehlung: Complete / Remove / Keep as-is

---

### Feature 60.4: TD-069 Multihop Endpoint Review (3 SP)

**Priority:** P2
**Parallelisierung:** Agent 4

**Siehe:** [TD-069_MULTIHOP_ENDPOINT_REVIEW.md](../technical-debt/TD-069_MULTIHOP_ENDPOINT_REVIEW.md)

**Tasks:**
1. [ ] Endpoint-Existenz prüfen
2. [ ] Funktionalität testen
3. [ ] Usage analysieren
4. [ ] Entscheidung dokumentieren

**Acceptance Criteria:**
- [ ] TD-069 Status aktualisiert
- [ ] `docs/api/MULTI_HOP_ENDPOINTS.md` aktualisiert oder archiviert

---

### Feature 60.5: TD-071 vLLM Investigation (5 SP)

**Priority:** P2
**Parallelisierung:** Nach 60.1 (braucht DGX Spark Doku)

**Siehe:** [TD-071_VLLM_VS_OLLAMA_INVESTIGATION.md](../technical-debt/TD-071_VLLM_VS_OLLAMA_INVESTIGATION.md)

**Tasks:**
1. [ ] vLLM auf DGX Spark installieren
2. [ ] Kompatibilität prüfen (cu130, sm_121)
3. [ ] Benchmarks durchführen
4. [ ] Ergebnisse dokumentieren

**Acceptance Criteria:**
- [ ] TD-071 mit Ergebnissen aktualisiert
- [ ] Empfehlung: Migrate / Keep Ollama

---

### Feature 60.6: TD-072 Sentence-Transformers Reranking (5 SP)

**Priority:** P2
**Parallelisierung:** Nach 60.1

**Siehe:** [TD-072_SENTENCE_TRANSFORMERS_RERANKING.md](../technical-debt/TD-072_SENTENCE_TRANSFORMERS_RERANKING.md)

**Tasks:**
1. [ ] Cross-Encoder Models evaluieren
2. [ ] Benchmarks: Latency, Quality
3. [ ] Vergleich mit Ollama Reranker
4. [ ] Ergebnisse dokumentieren

**Acceptance Criteria:**
- [ ] TD-072 mit Ergebnissen aktualisiert
- [ ] Empfehlung: Migrate / Keep Ollama

---

### Feature 60.7: TD-073 Sentence-Transformers Embeddings (5 SP)

**Priority:** P2
**Parallelisierung:** Nach 60.1

**Siehe:** [TD-073_SENTENCE_TRANSFORMERS_EMBEDDINGS.md](../technical-debt/TD-073_SENTENCE_TRANSFORMERS_EMBEDDINGS.md)

**Tasks:**
1. [ ] Native BGE-M3 auf DGX Spark testen
2. [ ] Benchmarks: Latency, Throughput
3. [ ] Quality-Vergleich (Embedding Similarity)
4. [ ] Ergebnisse dokumentieren

**Acceptance Criteria:**
- [ ] TD-073 mit Ergebnissen aktualisiert
- [ ] Empfehlung: Migrate / Keep Ollama

---

### Feature 60.8: Subdirectory Cleanup (3 SP)

**Priority:** P2
**Parallelisierung:** Nach allen anderen Features (Final)

**Ziel:** Nach Abarbeitung aller Analysen und TDs die Unterverzeichnisse aufräumen.

#### docs/analysis/ Cleanup

| Datei | Status nach Sprint 60 | Aktion |
|-------|----------------------|--------|
| `CLOUD_LLM_DECISION_MATRIX.md` | → TD-068 | Archivieren |
| `CLOUD_LLM_INGESTION_ANALYSIS.md` | → TD-068 | Archivieren |
| `INGESTION_PERFORMANCE_ANALYSIS.md` | → TD-070 | Archivieren |

#### docs/api/ Cleanup

| Datei | Status | Aktion |
|-------|--------|--------|
| `MULTI_HOP_ENDPOINTS.md` | → TD-069 geprüft | Archivieren oder Update |

#### docs/components/ Cleanup

| Datei | Status | Aktion |
|-------|--------|--------|
| `OLLAMA_RERANKER.md` | → TD-072 geprüft | Archivieren oder Update |

#### docs/features/ Cleanup

| Datei | Status | Aktion |
|-------|--------|--------|
| `SECTION_NODES_QUERIES.md` | → 60.3 geprüft | Archivieren oder Update |
| `FEATURE_51.4_DOMAIN_DELETE.md` | Sprint 51 Done | Archivieren |

#### docs/reference/ Consolidation

| Datei | Aktion |
|-------|--------|
| `API_CONVERSATION_ARCHIVING.md` | → docs/api/ oder entfernen |
| `E2E_TESTS_PHASE1_SUMMARY.md` | Archivieren (Sprint 50) |
| `ENFORCEMENT_GUIDE.md` | Prüfen: relevant? |
| `FORMAT_SUPPORT_MATRIX.md` | Behalten (nützlich) |
| `MODERNIZATION_QUICK_REFERENCE.md` | Prüfen: aktuell? |
| `GRAPHITI_REFERENCE.md` | Behalten (60.2 Analyse) |

**Acceptance Criteria:**
- [ ] docs/analysis/ aufgeräumt
- [ ] docs/api/ aufgeräumt
- [ ] docs/components/ aufgeräumt
- [ ] docs/features/ aufgeräumt
- [ ] docs/reference/ konsolidiert
- [ ] Archivierte Dateien in `docs/archive/` verschoben

---

## Parallel Execution Strategy

### Wave 1 (Tag 1-3): Core Tasks (4 Agents parallel)
```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │   Agent 4      │
│   60.1       │   60.2       │   60.3       │   60.4         │
│   Docs       │   GRAPHITI   │   Section    │   Multihop     │
│   Consolid.  │   Analysis   │   Nodes      │   Review       │
│   13 SP      │   8 SP       │   3 SP       │   3 SP         │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Wave 2 (Tag 4-5): Technical Investigations
```
┌─────────────────────────────────────────────────────┐
│                PARALLEL EXECUTION                    │
├──────────────┬──────────────┬──────────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3            │
│   60.5       │   60.6       │   60.7               │
│   vLLM       │   Reranking  │   Embeddings         │
│   5 SP       │   5 SP       │   5 SP               │
└──────────────┴──────────────┴──────────────────────┘
```

### Wave 3 (Tag 6): Cleanup
```
Agent 1: Feature 60.8 - Subdirectory Cleanup
Agent 2: TD_INDEX.md Update
Agent 3: Final Review
```

---

## Neue TDs (erstellt für Sprint 60)

| TD# | Title | Type | SP |
|-----|-------|------|-----|
| TD-068 | Cloud LLM Support (AnyLLM/Dashscope) | Feature | 13 |
| TD-069 | Multihop Endpoint Review | Review | 3 |
| TD-070 | Ingestion Performance Tuning | Performance | 13 |
| TD-071 | vLLM vs Ollama Investigation | Investigation | 5 |
| TD-072 | Sentence-Transformers Reranking | Investigation | 5 |
| TD-073 | Sentence-Transformers Embeddings | Investigation | 5 |

---

## Acceptance Criteria (Sprint Complete)

- [ ] Core Docs konsolidiert (7 → 4 Dateien)
- [ ] TECH_STACK.md mit DGX Spark Infos
- [ ] GRAPHITI Temporal Queries analysiert
- [ ] Section Nodes Status dokumentiert
- [ ] TD-069 Review abgeschlossen
- [ ] TD-071, 072, 073 Investigations abgeschlossen
- [ ] Subdirectories aufgeräumt
- [ ] TD_INDEX.md aktualisiert

---

## Definition of Done

### Per Feature
- [ ] Task abgeschlossen
- [ ] Dokumentation aktualisiert
- [ ] Ggf. TDs erstellt/aktualisiert

### Sprint Complete
- [ ] Alle Docs konsolidiert
- [ ] Alle Investigations dokumentiert
- [ ] Cleanup abgeschlossen
- [ ] TD_INDEX.md aktuell

---

## References

- [ADR-046: Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [TD_INDEX.md](../technical-debt/TD_INDEX.md)
- [GRAPHITI_REFERENCE.md](../reference/GRAPHITI_REFERENCE.md)
- [Sprint 59 Plan](SPRINT_59_PLAN.md)

---

**END OF SPRINT 60 PLAN**
