# Sprint 104: Aggressive Production Readiness (93%+ Ziel)

**Erstellt:** 2026-01-16
**Sprint:** 104
**Scope:** **25 SP** (erweitert von 20 SP)
**Ziel:** **180+/194 tests** (93%+) statt 175/194 (90%)

---

## 🎯 Warum "Aggressive Targets"?

**Ursprünglicher Plan:** 20 SP, 90% pass rate (175/194 tests)
**Problem:** Zu konservativ! Viele "Easy Wins" nicht eingeplant
**Erweitert:** +5 SP für:
- **Phase 3.5 (Easy Wins):** Groups 2, 9, 11, 12 auf 100% bringen (+6 tests, +2 SP)
- **Aggressive Partial Fixes:** Alle Partial Groups weiter pushen (+7 tests, +3 SP)

---

## 📊 Neue Ziele: Gruppen-Übersicht

### 🎯 Perfect Groups (100% Pass Rate)

| Group | Aktuell | Ziel | Feature | Aufwand |
|-------|---------|------|---------|---------|
| **Group 2 (Bash)** | 15/16 (94%) | **16/16** | 104.12 Easy Wins | Low |
| **Group 4 (Browser)** | 0/6 (0%) | **6/6** | 104.1 Browser UI | High |
| **Group 5 (Skills)** | 0/8 (0%) | **8/8** | 104.2 Skills UI | High |
| **Group 6 (Skills+Tools)** | 0/9 (0%) | **9/9** | 104.3 Integration | High |
| **Group 9 (Long Context)** | 11/13 (85%) | **13/13** | 104.12 Easy Wins | Low |
| **Group 11 (Upload)** | 13/15 (87%) | **15/15** | 104.12 Easy Wins | Low |
| **Group 12 (Communities)** | 14/15 (93%) | **15/15** | 104.12 Easy Wins | Low |
| **Group 13 (Agent Hier)** | 2/8 (25%) | **8/8** | 104.5 UI Complete | Medium |

**Total Perfect Groups:** 2 → **10 groups** (+8 groups!)

### ⚠️ High Performance (>80%, aber nicht 100%)

| Group | Aktuell | Ziel | Feature | Grund für <100% |
|-------|---------|------|---------|-----------------|
| **Group 1 (MCP Tools)** | 13/19 (68%) | **18/19 (95%)** | 104.7 Test IDs | 1 Edge Case |
| **Group 7 (Memory)** | 3/15 (20%) | **14/15 (93%)** | 104.4 DOM Fix | 1 Edge Case |
| **Group 10 (Hybrid Search)** | 5/13 (38%) | **11/13 (85%)** | 104.8 Mocks | 2 Complex Cases |
| **Group 14 (GDPR/Audit)** | 3/14 (21%) | **12/14 (86%)** | 104.6 API Fixes | 2 Complex Cases |
| **Group 15 (Explainability)** | 4/13 (31%) | **11/13 (85%)** | 104.9 Integration | 2 Complex Cases |

---

## 📈 Test Impact Breakdown

### Fixes nach Feature

| Feature | Gruppe(n) | Tests Fixed | Aufwand (SP) |
|---------|-----------|-------------|--------------|
| **104.1** Browser Tools UI | Group 4 | +6 | 3 |
| **104.2** Skills Management UI | Group 5 | +8 | 3 |
| **104.3** Skills-Tools Integration | Group 6 | +9 | 2 |
| **104.4** Memory Management Fix | Group 7 | +11 | 2 |
| **104.5** Agent Hierarchy UI | Group 13 | +6 | 2 |
| **104.6** GDPR/Audit API Fixes | Group 14 | +9 | 2 |
| **104.7** MCP Tools Test IDs | Group 1 | +5 | 2 |
| **104.8** Hybrid Search Mocks | Group 10 | +6 | 2 |
| **104.9** Explainability Integration | Group 15 | +7 | 2 |
| **104.12** Easy Wins | Groups 2,9,11,12 | +6 | 2 |
| **TOTAL** | | **+73 tests** | **22 SP** |

**Plus 3 SP für Testing & Docs = 25 SP total**

---

## 🔢 Mathematik: Von 81 → 8 Failures

### Aktuelle Failures (Sprint 103)
```
81 Total Failures =
  6 (Group 1)  + 1 (Group 2)  + 6 (Group 4)  + 8 (Group 5)  + 9 (Group 6)  +
 12 (Group 7)  + 2 (Group 9)  + 8 (Group 10) + 2 (Group 11) + 1 (Group 12) +
  6 (Group 13) + 11 (Group 14) + 9 (Group 15)
```

### Nach Sprint 104 (Aggressive Targets)
```
8 Remaining Failures =
  1 (Group 1 - edge case) +
  1 (Group 7 - edge case) +
  2 (Group 10 - complex) +
  2 (Group 14 - complex) +
  2 (Group 15 - complex)
```

### Rechnung
- **81 failures** aktuell
- **-73 tests** fixiert durch Sprint 104
- **= 8 failures** verbleibend
- **Pass Rate: (107 + 73) / 194 = 180 / 194 = 92.8%** ✅

---

## 💡 Warum diese Targets erreichbar sind

### 1. Easy Wins (6 tests, 2 SP)
**Groups 2, 9, 11, 12** sind bereits bei 85-94% pass rate. Jede Gruppe hat nur 1-2 failures übrig.

**Typische Ursachen (low-hanging fruit):**
- Timeout-Werte zu kurz (5s → 10s)
- Assertion Format mismatch (`result.data` vs `result.items`)
- Mock data missing 1 field
- CSS selector slightly wrong

**Estimated Time per Test:** 20-30 Minuten
**Total Time for 6 tests:** 2-3 Stunden = 2 SP ✅

---

### 2. Aggressive Partial Fixes (7 additional tests, +3 SP)

**Ursprüngliche Ziele waren zu konservativ:**
- Group 1: 68% → 89% (nur +4/6 tests)
- Group 7: 20% → 80% (nur +9/12 tests)
- Group 10: 38% → 77% (nur +5/8 tests)

**Neue Aggressive Targets:**
- Group 1: 68% → **95%** (+5/6 tests) - nur 1 mehr!
- Group 7: 20% → **93%** (+11/12 tests) - nur 2 mehr!
- Group 10: 38% → **85%** (+6/8 tests) - nur 1 mehr!
- Groups 13-15: Push auf 100% (13) bzw 85% (14,15)

**Why achievable:**
- Hauptprobleme bereits gelöst (Test IDs, API contracts)
- Verbleibende Failures sind wahrscheinlich small variations
- +3 SP gibt genug Puffer für "one more fix" pro Gruppe

---

### 3. Parallele Execution (Zeit-Effizienz)

**Phase 1 (8 SP):** 3 Frontend-Agents parallel → 3-4 Stunden
**Phase 2 (6 SP):** 3 Agents parallel → 2-3 Stunden
**Phase 3 (4 SP):** 3 Agents parallel → 1-2 Stunden
**Phase 3.5 (2 SP):** 1 Agent sequential → 2-3 Stunden (parallel zu Phase 3 möglich)
**Phase 4 (2 SP):** Testing & Docs → 1 Stunde

**Total Estimated Time:** 6-8 Stunden (innerhalb 1 Arbeitstag) ✅

---

## 🎯 Sprint 104 Summary

### Was ändert sich?

| Metrik | Original (20 SP) | Aggressive (25 SP) | Delta |
|--------|------------------|-------------------|-------|
| **Story Points** | 20 SP | **25 SP** | +5 SP |
| **Pass Rate Ziel** | 90% (175/194) | **93% (180/194)** | +3pp |
| **Tests Fixed** | 68 tests | **73 tests** | +5 tests |
| **Perfect Groups** | 6 groups | **10 groups** | +4 groups |
| **Failures Remaining** | ~19 | **~8** | -11 |

### Neue Features

- **Feature 104.12:** Perfect Groups Polish (2 SP)
  - Group 2: 94% → 100%
  - Group 9: 85% → 100%
  - Group 11: 87% → 100%
  - Group 12: 93% → 100%

### Erhöhte Targets (existing features)

- Feature 104.4 (Memory): 80% → **93%** (+2 tests)
- Feature 104.5 (Agent Hier): 75% → **100%** (+2 tests)
- Feature 104.6 (GDPR/Audit): 71% → **86%** (+2 tests)
- Feature 104.7 (MCP Tools): 89% → **95%** (+1 test)
- Feature 104.8 (Hybrid Search): 77% → **85%** (+1 test)
- Feature 104.9 (Explainability): 69% → **85%** (+2 tests)

---

## ✅ Acceptance Criteria (Updated)

Sprint 104 ist nur dann "Complete", wenn:

1. ✅ **180+/194 E2E tests** passing (93%+)
2. ✅ **Alle Gruppen** >80% pass rate (außer bekannte Edge Cases)
3. ✅ **10 Perfect Groups** (100% pass rate)
4. ✅ **0 Blocker-Gruppen** (keine Gruppe <50%)
5. ✅ **<10 failures** verbleibend (aktuell: 81)
6. ✅ **Vollständige Dokumentation** aller Fixes

**Failure Mode:** Falls nach Phase 1-3 nur 175/194 erreicht werden, dann ist Phase 3.5 (Easy Wins) MANDATORY um auf 180+ zu kommen.

---

## 🚀 Go/No-Go Entscheidung

**GO für Sprint 104 mit 25 SP?**

✅ **JA** wenn:
- Ziel ist maximale Production Readiness (93%+)
- Zeit vorhanden (6-8 Stunden)
- Parallel Execution möglich (3+ Agents)
- Easy Wins sind tatsächlich "easy" (Low-hanging fruit)

⚠️ **FALLBACK zu 20 SP** wenn:
- Zeit begrenzt (<6 Stunden)
- Nur 1-2 Agents verfügbar (sequential execution)
- 90% pass rate ausreichend für jetzt

---

## 📋 Nächste Schritte

**Wenn User zustimmt:**
1. Update SPRINT_104_PLAN.md mit allen Änderungen ✅
2. Erstelle Todo-Liste mit allen 12 Features
3. Starte Phase 1 mit 3 Frontend-Agents parallel
4. Nach Phase 1-3: Evaluate ob Phase 3.5 (Easy Wins) nötig ist
5. Final E2E Test Run + Documentation

**Geschätzte Fertigstellung:** 6-8 Stunden (innerhalb 1 Tag)
