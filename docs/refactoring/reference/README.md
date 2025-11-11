# Refactoring Reference Documentation

Diese Dokumente enthalten die **detaillierte Analyse** der Subagenten (backend-agent, api-agent, testing-agent) und dienen als Referenz für tiefgehende technische Details.

**Für die aktuelle Sprint-Planung:** Siehe `../SPRINT_22_HYBRID_APPROACH_PLAN.md` (DER actionable Plan)

---

## Dokumente in diesem Verzeichnis

### 1. REFACTORING_PLAN_CONSOLIDATED_V1.md (14 KB)
**Zweck:** Originaler konsolidierter Plan (Pre-Production Ansatz)
**Inhalt:** Alle P1-P4 Items, vollständige 3-Wochen Roadmap, Success Criteria
**Status:** Superseded by SPRINT_22_HYBRID_APPROACH_PLAN.md (verwendet nur kritische P1 Items)
**Nutzen:** Referenz für P2-P4 Items (Woche 3-4 nach Hybrid Ingestion)

---

### 2. BACKEND_REFACTORING_PLAN.md (32 KB)
**Zweck:** Backend-Agent Analyse (47 Refactoring Items)
**Inhalt:** Detaillierte Backend-Analyse mit Code-Duplikaten, Deprecated Code, Architektur-Verbesserungen
**Status:** Referenz für P2-P4 Backend Items
**Nutzen:**
- Code-Beispiele für BaseClient, BaseRetriever
- Dependency Injection Patterns
- Error Handling Standardisierung

**Sections:**
- Priority 1: Deprecated Code (10 items, 16-20h)
- Priority 2: Duplications (12 items, 20-24h)
- Priority 3: Architecture (15 items, 12-16h)
- Priority 4: Code Quality (10 items)

---

### 3. API_REFACTORING_PLAN_V1.md (16 KB)
**Zweck:** API-Agent Analyse (21 Refactoring Items)
**Inhalt:** API-Layer Security, Validation, Consistency Issues
**Status:** P1 Items in SPRINT_22_HYBRID_APPROACH_PLAN.md integriert, P2-P4 hier als Referenz
**Nutzen:**
- P1 Security Fixes (CORS, Rate Limiting, Auth, SSE, Error Responses)
- P2 Validation (File Upload, Pagination, Request ID)
- P3 Code Quality (Helper Functions, Logging, OpenAPI)

**Sections:**
- Priority 1: Critical Security (5 items, 8-12h)
- Priority 2: Validation & Consistency (5 items, 10-16h)
- Priority 3: Code Quality (6 items, 8-14h)
- Priority 4: Future Enhancements (5 items, 10-15h)

---

### 4. TESTING_STRATEGY.md (41 KB)
**Zweck:** Testing-Agent Analyse (17 Test Gaps)
**Inhalt:** Welche Tests vor/während/nach Refactoring schreiben
**Status:** Kritische Tests (3-4) in SPRINT_22_HYBRID_APPROACH_PLAN.md, Rest hier als Referenz
**Nutzen:**
- Pre-Refactoring Baseline Tests (7 critical gaps)
- Test Refactoring Patterns
- Coverage Targets (≥85%)
- Golden Dataset Strategy

**Sections:**
- Pre-Refactoring Assessment
- Critical Test Gaps (7 items, 18-26h)
- Refactoring Safety Strategy
- Test Refactoring Needs
- Post-Refactoring Validation

---

### 5. PRIORITY_1_IMPLEMENTATION_GUIDE.md (22 KB)
**Zweck:** Schritt-für-Schritt Code-Beispiele für P1 Items
**Inhalt:** Migration Scripts, Code Snippets, Testing Procedures
**Status:** Referenz für konkrete Implementierung
**Nutzen:**
- Code-Beispiele für unified_ingestion.py Removal
- Migration Scripts für three_phase_extractor.py
- Test Procedures für jede Änderung

**Sections:**
- Step 1: Remove unified_ingestion.py
- Step 2: Archive three_phase_extractor.py
- Step 3: Update LlamaIndex Deprecation
- Step 4: Remove base.py duplicate

---

### 6. REFACTORING_SUMMARY.md (7.2 KB)
**Zweck:** Executive Summary, Quick Win Opportunities
**Inhalt:** Metrics, Sprint 22 Recommended Plan (jetzt veraltet durch Hybrid Approach)
**Status:** Obsolete (durch SPRINT_22_HYBRID_APPROACH_PLAN.md ersetzt)
**Nutzen:** Historisch, zeigt ursprüngliche Planung

---

## Wann diese Dokumente nutzen?

### Während Sprint 22 (Woche 1-2)
✅ **Nutze:** `../SPRINT_22_HYBRID_APPROACH_PLAN.md` (Der actionable Plan)

**Referenz bei Bedarf:**
- API_REFACTORING_PLAN_V1.md → P1 Security Details (CORS, Rate Limiting, Auth)
- TESTING_STRATEGY.md → Welche 3-4 Tests kritisch sind
- PRIORITY_1_IMPLEMENTATION_GUIDE.md → Code-Beispiele für unified_ingestion Removal

### Während Sprint 22 (Woche 3-4) - Nach Hybrid Ingestion
✅ **Nutze:** Diese Referenz-Dokumente für P2-P4 Items

**Relevante Sections:**
- BACKEND_REFACTORING_PLAN.md → P2-P4 Backend Items (BaseClient, Error Handling)
- API_REFACTORING_PLAN_V1.md → P2-P4 API Items (Pagination, Model Consolidation)
- TESTING_STRATEGY.md → Remaining 7-10 Test Gaps

---

## Migration Path

**Von diesen Referenz-Docs → Sprint 22 Hybrid Plan:**
1. P1 Backend (unified_ingestion, LlamaIndex Deprecation Update) → Woche 1
2. P1 API (CORS, Error Responses, Rate Limiting, Auth) → Woche 1
3. 3-4 Critical Tests → Woche 1
4. Hybrid Ingestion (Format Router, LlamaIndex Fallback) → Woche 2
5. P2-P4 Items → Woche 3-4 (zurück zu diesen Docs)

---

## Zusammenfassung

Diese Dokumente sind **Referenz-Material** mit allen technischen Details der Subagenten-Analyse. Der **actionable Sprint-Plan** ist:

📋 **`../SPRINT_22_HYBRID_APPROACH_PLAN.md`**

Dieser Plan konsolidiert die kritischen P1 Items + Hybrid Ingestion zu einem 2-Wochen-Plan mit sofortigem User Value.
