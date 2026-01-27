# TD-070: Ingestion Performance Tuning

**Status:** OPEN
**Priority:** MEDIUM
**Story Points:** 13
**Created:** Sprint 60 Planning
**Target:** Sprint 61+

---

## Problem Statement

Die Ingestion-Pipeline zeigt Performance-Probleme bei größeren Dokumenten und Batch-Verarbeitung.
Eine detaillierte Analyse wurde bereits durchgeführt.

---

## Analysis Reference

| Dokument | Inhalt |
|----------|--------|
| `docs/analysis/INGESTION_PERFORMANCE_ANALYSIS.md` | Detaillierte Performance-Analyse |

---

## Key Findings (aus Analyse)

### Bottlenecks (vermutlich)
1. **Docling Parsing** - GPU-intensive, VRAM-Limits
2. **Embedding Generation** - Batch-Size nicht optimal
3. **Neo4j Writes** - Transaktions-Overhead
4. **Sequential Processing** - Keine Parallelisierung zwischen Dokumenten

### Performance Targets
| Metrik | Aktuell | Ziel |
|--------|---------|------|
| Single Doc (10 pages) | ~30s | <15s |
| Batch (10 docs) | ~5min | <2min |
| Throughput | ~2 docs/min | >5 docs/min |

---

## Optimization Areas

### 1. Docling Optimization (5 SP)
- VRAM Management verbessern
- Container Warm-Up
- Batch Page Processing

### 2. Embedding Batch Optimization (3 SP)
- Optimale Batch-Size ermitteln
- GPU Memory Management
- Async Embedding Generation

### 3. Neo4j Write Optimization (3 SP)
- Bulk Writes statt einzelne Transaktionen
- UNWIND für Batch Inserts
- Index-Nutzung prüfen

### 4. Pipeline Parallelization (5 SP)
- Document-Level Parallelism
- Stage-Level Pipelining
- Worker Pool Management

---

## Implementation Plan

### Phase 1: Profiling (2 SP)
- Instrumentierung der Pipeline
- Bottleneck-Identifikation
- Baseline-Metriken

### Phase 2: Quick Wins (5 SP)
- Batch-Size Tuning
- Neo4j Bulk Writes
- VRAM Management

### Phase 3: Architecture (8 SP)
- Pipeline Parallelization
- Async Processing
- Worker Pool

---

## Acceptance Criteria

- [ ] Performance Baseline dokumentiert
- [ ] Bottlenecks identifiziert
- [ ] 50% Performance-Verbesserung erreicht
- [ ] Throughput >5 docs/min
- [ ] Benchmarks dokumentiert

---

## Dependencies

- Sprint 54: langgraph_nodes Refactoring
- Sprint 55: lightrag_wrapper Refactoring

---

## References

- [docs/analysis/INGESTION_PERFORMANCE_ANALYSIS.md](../analysis/INGESTION_PERFORMANCE_ANALYSIS.md)
- ADR-027: Docling CUDA Integration
