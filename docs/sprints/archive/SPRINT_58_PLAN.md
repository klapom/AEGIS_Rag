# Sprint 58: Test Coverage 80% & OPL Cleanup

**Status:** IN PROGRESS
**Branch:** `main`
**Start Date:** 2025-12-19
**Estimated Duration:** 5 Tage
**Total Story Points:** 45 SP

---

## Sprint Overview

Sprint 58 ist der **letzte Sprint der Refactoring-Initiative** (ADR-046).
Ziel ist 80% Test Coverage und vollständige Auflösung aller OPL-Einträge.

**KRITISCH:** Nach Sprint 58 dürfen in REFACTORING_OPL.md **keine OPEN-Einträge** mehr existieren!

**Voraussetzung:** Sprint 57 abgeschlossen

**Referenzen:**
- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **FINALE CLEANUP!**

---

## Features

| # | Feature | SP | Priority | Parallelisierbar |
|---|---------|-----|----------|------------------|
| 58.1 | OPL Final Resolution | 8 | P0 | Nein (First) |
| 58.2 | domain_training/ Tests | 10 | P1 | Ja (Agent 1) |
| 58.3 | ingestion/ Tests | 10 | P1 | Ja (Agent 2) |
| 58.4 | api/v1/ Tests | 8 | P1 | Ja (Agent 3) |
| 58.5 | llm_proxy/ Tests | 5 | P1 | Ja (Agent 4) |
| 58.6 | Benchmark & Coverage Report | 4 | P2 | Final |

**Total: 45 SP**

---

## Coverage Targets

| Komponente | Aktuell | Ziel | Fehlende Module |
|------------|---------|------|-----------------|
| domain_training/ | ~30% | 80% | 8 Module |
| ingestion/ (nodes/) | ~50% | 80% | 7 Module |
| api/v1/ (split) | ~40% | 80% | 7 Module |
| llm_proxy/ | ~45% | 80% | 5 Module |
| **Gesamt** | **54.8%** | **80%** | **27 Module** |

---

## Feature Details

### Feature 58.1: OPL Final Resolution (8 SP)

**Priority:** P0 (BLOCKER - muss zuerst abgeschlossen werden!)
**Parallelisierung:** Nein

**OPL-Pflicht:** ALLE Einträge müssen auf RESOLVED oder REMOVED gesetzt werden!

**Expected OPL Status am Ende von Sprint 58:**

| OPL-ID | Current | Action | Target |
|--------|---------|--------|--------|
| OPL-001 | RESOLVED | Verify | REMOVED |
| OPL-002 | RESOLVED | Remove re-exports | REMOVED |
| OPL-003 | RESOLVED | Remove re-exports | REMOVED |
| OPL-004 | RESOLVED | Verify | REMOVED |
| OPL-005 | IN_PROGRESS | Complete DI migration | RESOLVED |
| OPL-006 | IN_PROGRESS | Remove backward-compat | RESOLVED |
| OPL-007 | OPEN | Complete Protocol impl | RESOLVED |

**Aufgaben:**

1. **OPL-001, OPL-002, OPL-003, OPL-004:** Code-Kommentare entfernen, re-exports löschen
2. **OPL-005:** Alle Singleton-Nutzungen auf DI umstellen
3. **OPL-006:** Alle cross-domain backward-compat imports entfernen
4. **OPL-007:** Alle konkreten Typen durch Protocols ersetzen

**Verification Script:**

```bash
# Keine OPL-Kommentare mehr im Code
grep -r "OPL-00" src/ --include="*.py" | wc -l
# Expected: 0

# Keine backward-compat re-exports
grep -r "backward.compat" src/ --include="*.py" | wc -l
# Expected: 0
```

**REFACTORING_OPL.md Final State:**

```markdown
## Summary

| Sprint | OPL-IDs | Status |
|--------|---------|--------|
| 53 | OPL-001, OPL-002 | REMOVED |
| 54 | OPL-003, OPL-004 | REMOVED |
| 55 | OPL-005 | RESOLVED |
| 56 | OPL-006 | RESOLVED |
| 57 | OPL-007 | RESOLVED |
| 58 | Cleanup | COMPLETE |

**Total Open:** 0
**Refactoring Complete:** Yes
```

**Acceptance Criteria:**
- [ ] Alle OPL RESOLVED oder REMOVED
- [ ] Keine OPL-Kommentare im Code
- [ ] Keine backward-compat re-exports
- [ ] REFACTORING_OPL.md zeigt 0 OPEN

---

### Feature 58.2: domain_training/ Tests (10 SP)

**Priority:** P1
**Parallelisierung:** Agent 1 (nach 58.1)

**OPL-Pflicht:** Wenn Testprobleme OPL-Einträge betreffen → dokumentieren!

**Ungetestete Module:**
1. `domain_training/classifier.py`
2. `domain_training/trainer.py`
3. `domain_training/dataset_loader.py`
4. `domain_training/dspy_integration.py`
5. `domain_training/evaluation.py`
6. `domain_training/optimizer.py`
7. `domain_training/metrics.py`
8. `domain_training/model_registry.py`

**Test-Strategie:**
- Unit Tests mit Mocked LLM
- Integration Tests mit DSPy
- Fixtures für Training Datasets

**Neue Test-Dateien:**

```
tests/unit/domain_training/
├── test_classifier.py
├── test_trainer.py
├── test_dataset_loader.py
├── test_dspy_integration.py
├── test_evaluation.py
├── test_optimizer.py
├── test_metrics.py
└── test_model_registry.py
```

**Acceptance Criteria:**
- [ ] 8 Test-Dateien erstellt
- [ ] Coverage domain_training/ ≥ 80%
- [ ] Alle Tests passieren

---

### Feature 58.3: ingestion/ Tests (10 SP)

**Priority:** P1
**Parallelisierung:** Agent 2 (nach 58.1)

**OPL-Pflicht:** Wenn Testprobleme OPL-Einträge betreffen → dokumentieren!

**Ungetestete/Untergetestete Module (nach Sprint 54 nodes/ Split):**
1. `nodes/memory_management.py` - Teilweise
2. `nodes/document_parsers.py` - Teilweise
3. `nodes/image_enrichment.py` - Minimal
4. `nodes/adaptive_chunking.py` - Teilweise
5. `nodes/vector_embedding.py` - Teilweise
6. `nodes/graph_extraction.py` - Minimal
7. `parallel_orchestrator.py` - Minimal

**Test-Strategie:**
- Unit Tests für jeden Node
- Integration Tests für Pipeline
- Mocked Docling Container
- Mocked LLM für VLM

**Acceptance Criteria:**
- [ ] Coverage ingestion/ ≥ 80%
- [ ] Alle Node Tests vorhanden
- [ ] Pipeline Integration Tests

---

### Feature 58.4: api/v1/ Tests (8 SP)

**Priority:** P1
**Parallelisierung:** Agent 3 (nach 58.1)

**OPL-Pflicht:** Wenn Testprobleme OPL-Einträge betreffen → dokumentieren!

**Ungetestete Module (nach Sprint 53 admin Split):**
1. `admin_indexing.py`
2. `admin_costs.py`
3. `admin_llm.py`
4. `admin_graph.py`
5. `chat_streaming.py`
6. `chat_persistence.py`
7. `chat_analytics.py`

**Test-Strategie:**
- Unit Tests mit TestClient
- Mocked Services
- SSE Streaming Tests

**Neue Test-Dateien:**

```
tests/unit/api/v1/
├── test_admin_indexing.py
├── test_admin_costs.py
├── test_admin_llm.py
├── test_admin_graph.py
├── test_chat_streaming.py
├── test_chat_persistence.py
└── test_chat_analytics.py
```

**Acceptance Criteria:**
- [ ] 7 Test-Dateien erstellt
- [ ] Coverage api/v1/ ≥ 80%
- [ ] SSE Streaming getestet

---

### Feature 58.5: llm_proxy/ Tests (5 SP)

**Priority:** P1
**Parallelisierung:** Agent 4 (nach 58.1)

**OPL-Pflicht:** Wenn Testprobleme OPL-Einträge betreffen → dokumentieren!

**Ungetestete Module:**
1. `aegis_llm_proxy.py` - Routing Logic
2. `routing.py` - Provider Selection
3. `cost_tracker.py` - Cost Calculation
4. `config.py` - YAML Config Loading
5. `providers/` - Provider Implementations

**WICHTIG für Sprint 59:**
Diese Tests müssen die Grundlage für Sprint 59 Tool Use bieten!

**Test-Strategie:**
- Unit Tests mit Mocked Providers
- Cost Tracking Validation
- Routing Decision Tests

**Acceptance Criteria:**
- [ ] Coverage llm_proxy/ ≥ 80%
- [ ] Routing Tests
- [ ] Cost Tracking Tests

---

### Feature 58.6: Benchmark & Coverage Report (4 SP)

**Priority:** P2
**Parallelisierung:** Nach allen anderen Features

**OPL-Pflicht:** Finale Dokumentation!

**Aufgaben:**
1. Coverage Report generieren
2. Performance Benchmarks vor/nach Refactoring
3. Finale Metriken dokumentieren
4. ADR-046 Status auf IMPLEMENTED setzen

**Coverage Report:**

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/

# Generate summary
pytest --cov=src --cov-report=term-missing tests/ > coverage_report.txt
```

**Finale Metriken (Ziel):**

| Metrik | Start (Sprint 52) | Ziel (Sprint 58) | Erreicht |
|--------|-------------------|------------------|----------|
| Max. Datei-LOC | 4796 | <1000 | [ ] |
| Zirkuläre Dependencies | 2 | 0 | [ ] |
| Test Coverage | 54.8% | 80% | [ ] |
| Avg. Complexity | 22.8 | <15 | [ ] |
| Hot-Spots (>1000 LOC) | 6 | 0 | [ ] |
| OPL OPEN | 7 | 0 | [ ] |

**ADR-046 Update:**

```markdown
## Status
**Implemented** (Sprint 58)

## Results
- All hot-spots resolved
- Domain boundaries established
- Protocol-based interfaces
- 80% test coverage achieved
- All OPL entries resolved
```

**Acceptance Criteria:**
- [ ] Coverage Report erstellt
- [ ] Alle Metriken dokumentiert
- [ ] ADR-046 auf IMPLEMENTED
- [ ] Benchmark-Vergleich

---

## Parallel Execution Strategy

### Wave 1 (Tag 1): OPL Cleanup (BLOCKER)
```
Agent 1: Feature 58.1 - OPL Final Resolution
         Alle anderen warten!
```

### Wave 2 (Tag 2-4): Test Implementation (4 Agents parallel)
```
┌─────────────────────────────────────────────────────────────┐
│                    PARALLEL EXECUTION                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Agent 1    │   Agent 2    │   Agent 3    │   Agent 4      │
│   58.2       │   58.3       │   58.4       │   58.5         │
│   domain_    │   ingestion  │   api/v1     │   llm_proxy    │
│   training   │              │              │                │
│   10 SP      │   10 SP      │   8 SP       │   5 SP         │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Wave 3 (Tag 5): Finalization
```
Agent 1: Feature 58.6 - Benchmark & Report
Agent 2: Coverage Verification
Agent 3: Documentation
Agent 4: Final CI/CD Run
```

---

## Acceptance Criteria (Sprint Complete)

- [ ] **REFACTORING_OPL.md: 0 OPEN Einträge**
- [ ] Test Coverage ≥ 80%
- [ ] Alle Hot-Spots < 1000 LOC
- [ ] 0 zirkuläre Dependencies
- [ ] ADR-046 Status: IMPLEMENTED
- [ ] Coverage Report vorhanden
- [ ] CI/CD Pipeline grün

---

## Risk Assessment

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| 80% Coverage nicht erreichbar | Medium | High | Priorisiere kritische Pfade |
| OPL nicht vollständig auflösbar | Low | Critical | Eskalation an Tech Lead |
| Test-Flakiness | Medium | Medium | Retry Logic, Determinismus |
| Performance Regression | Low | Medium | Benchmarks validieren |

---

## Definition of Done

### Per Feature
- [ ] Tests geschrieben
- [ ] Coverage ≥ 80% für Modul
- [ ] REFACTORING_OPL.md aktualisiert

### Sprint Complete
- [ ] Gesamt-Coverage ≥ 80%
- [ ] 0 OPL OPEN
- [ ] ADR-046 IMPLEMENTED
- [ ] CI/CD grün
- [ ] Refactoring COMPLETE

---

## Post-Refactoring Validation

Nach Sprint 58 sollten folgende Checks bestanden werden:

```bash
# 1. Import Check
python -c "from src.api.main import app; print('OK')"

# 2. Circular Dependency Check
python -c "import src.domains; print('OK')"

# 3. Coverage Check
pytest --cov=src --cov-fail-under=80 tests/

# 4. OPL Check
grep -c "OPEN" docs/refactoring/REFACTORING_OPL.md
# Expected: 0

# 5. Hot-Spot Check
find src -name "*.py" -exec wc -l {} \; | sort -rn | head -5
# All should be < 1000 LOC
```

---

---

## Subagent-Anweisungen: OPL & Dead Code - FINALE CLEANUP

**KRITISCH:** Sprint 58 ist der letzte Refactoring-Sprint!
Nach Abschluss dürfen **KEINE OPEN OPL oder DC Einträge** mehr existieren!

### 1. OPL Final Resolution

**Alle OPL-Einträge MÜSSEN aufgelöst werden:**

| OPL-ID | Current | Required Action | Target |
|--------|---------|-----------------|--------|
| OPL-001 | RESOLVED | Code-Kommentare entfernen | REMOVED |
| OPL-002 | RESOLVED | Re-Exports entfernen | REMOVED |
| OPL-003 | RESOLVED | Re-Exports entfernen | REMOVED |
| OPL-004 | RESOLVED | Verifizieren | REMOVED |
| OPL-005 | IN_PROGRESS | DI Migration abschließen | RESOLVED |
| OPL-006 | IN_PROGRESS | Backward-Compat entfernen | RESOLVED |
| OPL-007 | OPEN | Protocol impl abschließen | RESOLVED |

### 2. Dead Code Final Removal

**Alle DC-Einträge MÜSSEN entfernt werden:**

| DC-ID | Status | Action |
|-------|--------|--------|
| DC-001 | REMOVED | Verify |
| DC-002 | REMOVED | Verify |
| DC-003 | REMOVED | Verify |
| DC-004 | OPEN | **Backward-Compat Re-Exports entfernen** |
| DC-005 | REMOVED | Verify |

### 3. Final Verification Scripts

```bash
# 1. Keine OPL-Kommentare mehr im Code
grep -r "OPL-00" src/ --include="*.py" | wc -l
# Expected: 0

# 2. Keine DC-Kommentare mehr im Code
grep -r "DC-00" src/ --include="*.py" | wc -l
# Expected: 0

# 3. Keine backward-compat re-exports
grep -r "backward.compat\|Backward.compat\|DEPRECATED" src/ --include="*.py" | wc -l
# Expected: 0

# 4. Vulture Clean
vulture src/ --min-confidence 90
# Expected: No output
```

### 4. REFACTORING_OPL.md Final State

Nach Sprint 58 sollte die Datei zeigen:
```markdown
## Summary
**Total OPEN:** 0
**Total RESOLVED:** 7 (archived)
**Total DC REMOVED:** 5
**Refactoring Status:** COMPLETE
```

### 5. Checkliste Sprint 58 Complete

- [ ] Alle OPL RESOLVED oder REMOVED
- [ ] Alle DC REMOVED
- [ ] Keine OPL/DC Kommentare im Code
- [ ] Vulture zeigt keinen Dead Code
- [ ] REFACTORING_OPL.md Final State dokumentiert
- [ ] ADR-046 Status: IMPLEMENTED

---

## References

- [ADR-046: Comprehensive Refactoring Strategy](../adr/ADR-046_COMPREHENSIVE_REFACTORING_STRATEGY.md)
- [REFACTORING_OPL.md](../refactoring/REFACTORING_OPL.md) - **FINALE CLEANUP**
- [Sprint 57 Plan](SPRINT_57_PLAN.md)

---

**END OF SPRINT 58 PLAN**

---

## REFACTORING INITIATIVE COMPLETE

Nach Abschluss von Sprint 58 ist die Refactoring-Initiative (ADR-046) abgeschlossen.
Die Codebase ist bereit für neue Feature-Entwicklung (Sprint 59+).
