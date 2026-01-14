# Technical Debt Index

**Last Updated:** 2026-01-13 (Sprint 87/89 - LightRAG CRUD Gap)
**Total Open Items:** 6
**Total Story Points:** ~121 SP
**Archived Items:** [28 items](archive/ARCHIVE_INDEX.md) (TD-074, TD-103 resolved Sprint 87)
**Sprint 51 Review:** [Analysis & Archival Decisions](SPRINT_51_REVIEW_ANALYSIS.md)
**Sprint 52:** Community Summaries, Async Follow-ups, Admin Dashboard, CI/CD
**Sprint 53-58:** Refactoring Initiative (ADR-046)
**Sprint 59:** Agentic Features, Tool Use
**Sprint 60:** ✅ Documentation Consolidation, Technical Investigations (COMPLETE)
**Sprint 70:** ✅ MCP Tool Use in Chat & Research (COMPLETE)
**Sprint 71:** Anti-Hallucination Prompt Hardening (TD-080 Phase 1)
**Sprint 75:** 🔴 **CRITICAL Architecture Gaps Discovered** (TD-084, TD-085)
**Sprint 76:** ✅ **TD-084 & TD-085 RESOLVED** - Namespace & Domain Integration (34 SP Recovered)

---

## Summary by Priority

| Priority | Count | Story Points |
|----------|-------|--------------|
| CRITICAL | 1     | 21 SP        |
| HIGH     | 1     | ~18 SP       |
| MEDIUM   | 2     | ~19 SP       |
| LOW      | 2     | ~55 SP       |
| PARTIAL  | 1     | ~6 SP        |

**Sprint 81:** TD-096, TD-097 RESOLVED (8 SP) - Settings UI Integration complete
**Sprint 83:** TD-044, TD-046, TD-052, TD-079, TD-099 RESOLVED (27 SP) - Logging improvements, namespace fixes, user upload, intent classifier
**Sprint 84:** TD-059, TD-075, TD-077, TD-083, TD-100 RESOLVED (31 SP) - Code analysis revealed features already implemented but not archived
**Sprint 85:** 🔴 **TD-101 DISCOVERED** (21 SP) - Community Summarization Bottleneck (Full Graph Re-Summarization)
**Sprint 87:** ✅ **TD-074, TD-103 RESOLVED** (26 SP) - BGE-M3 Native Hybrid eliminates BM25 pickle (sync guaranteed)
**Sprint 89:** 🔴 **TD-104 PLANNED** (11 SP) - LightRAG CRUD Feature Gap (Entity/Relation CRUD, Data Export, Doc Deletion)

---

## Archived Items

Resolved items have been moved to [archive/](archive/ARCHIVE_INDEX.md):

| TD# | Title | Resolution Sprint | SP |
|-----|-------|-------------------|----|
| TD-084 | **Namespace Isolation in Ingestion** | **Sprint 76** | **13** |
| TD-085 | **DSPy Domain Prompts Integration** | **Sprint 76** | **21** |
| TD-043 | Async Follow-up Questions | Sprint 52 | 5 |
| TD-043_FIX_SUMMARY | Follow-up Questions Fix Summary | Sprint 35 | - |
| TD-044 | DoclingParsedDocument Interface Fix | **Sprint 83** | **8** |
| TD-045 | entity_id Property Migration | Sprint 34 | 3 |
| TD-046 | RELATES_TO Relationship Extraction | Sprint 42 | 5 |
| TD-047 | Critical Path E2E Tests | Sprint 51 | 8 |
| TD-048 | Graph Extraction with Unified Chunks | Sprint 49 | 5 |
| TD-050 | Duplicate Answer Streaming | Sprint 47 | 3 |
| TD-052 | User Document Upload | **Sprint 83** | **5** |
| TD-057 (Sprint 42) | 4-Way Hybrid RRF Retrieval | Sprint 42 | 13 |
| TD-058 | Community Summary Generation | Sprint 52 | 8 |
| **TD-059** | **Reranking Disabled in Container** | **Sprint 61** (Code Analysis Sprint 84) | **5** |
| TD-060 | Unified Chunk IDs | Sprint 42 | 8 |
| TD-061 | Ollama GPU Docker Config | Sprint 42 | 3 |
| TD-062 | Multi-Criteria Entity Deduplication | Sprint 43 | 5 |
| TD-063 | Relation Deduplication | Sprint 49 | 5 |
| TD-069 | Multihop Endpoint Review | Sprint 60 | 8 |
| TD-071 | vLLM vs Ollama Investigation | Sprint 60 | 5 |
| TD-072 | Sentence-Transformers Reranking Investigation | Sprint 60 | 3 |
| TD-073 | Sentence-Transformers Embeddings Investigation | Sprint 60 | 3 |
| **TD-075** | **VLM Image Descriptions → Chunks Integration** | **Sprint 64** (Code Analysis Sprint 84) | **8** |
| **TD-077** | **VLM Admin UI Integration** | **Sprint 66** | **0** |
| TD-079 | LLM Intent Classifier (C-LARA) | **Sprint 81** | **13** |
| **TD-083** | **SetFit Intent Classifier Training (C-LARA)** | **Sprint 67+81** (Code Analysis Sprint 84) | **13** |
| TD-096 | Chunking Parameters UI Integration | **Sprint 81** | **5** |
| TD-097 | Sprint 80 Settings UI/DB Integration | **Sprint 81** | **3** |
| TD-099 | Namespace Not Set During RAGAS Ingestion | **Sprint 81** | **3** |
| **TD-100** | **Gleaning Multi-Pass Extraction** | **Sprint 83** (Code Analysis Sprint 84) | **5** |
| **TD-074** | **BM25 Cache Discrepancy** | **Sprint 87** (BGE-M3 Native Hybrid) | **5** |
| **TD-103** | **BM25 Index Desync** | **Sprint 87** (BGE-M3 Native Hybrid) | **21** |

---

## Active Technical Debt Items

### 🔴 CRITICAL Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-101](TD-101_COMMUNITY_SUMMARIZATION_BOTTLENECK.md) | **Community Summarization Bottleneck** | 🔴 OPEN | 21 | **Sprint 86 URGENT** |

**TD-101 Discovery (Sprint 85):** Multi-format ingestion testing revealed that EVERY document upload triggers community summarization for the ENTIRE Neo4j graph (~2000+ communities), not just new entities. This causes 40-60 minute ingestion times for small files.

### HIGH Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-102](TD-102_RELATION_EXTRACTION_IMPROVEMENT.md) | **Relation Extraction Improvement** | 🔴 OPEN | 18 | **Sprint 86-88** |
| [TD-080](TD-080_CONTEXT_RELEVANCE_GUARD.md) | Context Relevance Guard (Anti-Hallucination) | PHASE 1 COMPLETE | 5 | **Sprint 71-73** |
| [TD-078](TD-078_SECTION_EXTRACTION_PERFORMANCE.md) | Section Extraction Performance | ✅ O(n²) FIX DONE | 18 | **Sprint 67-68** |

**TD-102 Discovery (Sprint 85):** Multi-format ingestion testing revealed Relation Ratio of only 0.27-0.61 (target: ≥1.0). Root causes: SpaCy only as fallback, generic RELATES_TO prompts, no Gleaning. 5 iterations planned: SpaCy-first → Typed Relations → Gleaning → DSPy → KG Hygiene.

### MEDIUM Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-104](TD-104_LIGHTRAG_CRUD_FEATURE_GAP.md) | **LightRAG CRUD Feature Gap** | 🔴 OPEN | 11 | **Sprint 89** |
| [TD-098](TD-098_CROSS_ENCODER_FINE_TUNING.md) | Cross-Encoder Fine-tuning | OPEN | 8 | **Sprint 85+** |
| [TD-070](TD-070_INGESTION_PERFORMANCE_TUNING.md) | Ingestion Performance Tuning | **PHASE 1 COMPLETE (Sprint 83.1)** | 13 | **Sprint 85** |
| [TD-074](TD-074_BM25_CACHE_DISCREPANCY.md) | BM25 Cache Discrepancy | ✅ **RESOLVED Sprint 87** | 5 | **Sprint 87** |

**TD-104 Discovery (Sprint 87):** LightRAG vs AegisRAG comparison revealed 18+ LightRAG methods not exposed by our wrapper, including Entity/Relation CRUD, Data Export (CSV/Excel/MD), and Document Deletion. Planned for Sprint 89.

### LOW Priority

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md) | MCP Client Implementation | OPEN | 21 | Sprint 90+ |
| [TD-056](TD-056_PROJECT_COLLABORATION_SYSTEM.md) | Project Collaboration System | PLANNED | 34 | Sprint 90+ |
| [TD-064](TD-064_TEMPORAL_COMMUNITY_SUMMARIES.md) | Temporal Community Summaries | BACKLOG | 13 | Sprint 90+ (Optional) |

### PARTIAL (Refactoring)

| TD# | Title | Status | SP | Target Sprint |
|-----|-------|--------|-----|---------------|
| [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md) | Unified Chunking Service | Section-Aware ✅, Unified Service ❌ | 6 | Sprint 85+ |

---

## Sprint 60 (Completed - Documentation Consolidation & Technical Investigations)

**Focus:** Documentation consolidation post-refactoring (Sprint 53-59) + Technical investigations
**Story Points:** 45 SP
**Status:** ✅ COMPLETE

**Achievements:**
- 7 consolidated documentation files created (ARCHITECTURE.md, TECH_STACK.md, CONVENTIONS.md, 4 analysis docs)
- 17 files archived (6 from Wave 1, 11 from Wave 3)
- 4 technical investigations completed (TD-069, TD-071, TD-072, TD-073)
- Clear recommendations for Sprint 61+ (2 migrations recommended, 1 removal recommended, 1 keep Ollama)



**Investigation Results:**
- **TD-069:** ✅ RESOLVED - Remove multihop endpoints (unused, deprecated)
- **TD-071:** ✅ RESOLVED - Keep Ollama (vLLM not justified at current scale)
- **TD-072:** 🔄 MIGRATE - Cross-Encoder reranking recommended (50x faster)
- **TD-073:** 🔄 MIGRATE - Native Sentence-Transformers recommended (3-5x faster)

---

## Sprint 51 (Completed - E2E Test Coverage & TD Review)

**Focus:** E2E test coverage for unutilized features + Technical Debt Review
**Story Points:** 39 SP (without Mem0 optional feature)
**Status:** ✅ COMPLETE

**Achievements:**
- 111 E2E tests implemented and passing (vs. 40 planned)
- 4 TDs reviewed and updated (TD-045, TD-046, TD-047, TD-059)
- Root documentation reorganized (13 files moved/archived)
- Production confidence improved to >90%

| Feature | SP | Status |
|---------|-----|--------|
| 51.1 | 13 | ✅ Bi-Temporal Queries E2E Tests |
| 51.2 | 8 | ✅ Secure Shell Sandbox E2E Tests |
| 51.3 | 5 | ✅ Dynamic LLM Model Configuration E2E |
| 51.4 | 5 | ✅ Graph Relationship Type Filtering E2E |
| 51.5 | 3 | ✅ Historical Phase Events Display E2E |
| 51.6 | 5 | ✅ Index Consistency Validation UI + E2E |
| TD Review | N/A | ✅ 4 TDs reviewed and status updated |
| Doc Org | N/A | ✅ Root docs reorganized |

---

## Recommended Sprint Allocation

### Sprint 61 (CURRENT - Performance & Ollama Optimization + Bugfixes)
**Duration:** 1-2 weeks | **Story Points:** 29 SP | **Status:** READY

**Focus:** Critical performance migrations from Sprint 60 investigations + Sprint 59 bugfixes
- **61.1: Native Sentence-Transformers Embeddings (8 SP)** - from TD-073
  - 3-5x faster embeddings, 60% less VRAM, identical quality
- **61.2: Cross-Encoder Reranking (9 SP)** - from TD-072
  - 50x faster reranking (120ms vs 2000ms), comparable quality
- **61.3: Remove Deprecated Multihop Endpoints (2 SP)** - from TD-069
  - Clean up 5 deprecated graph_viz endpoints
- **61.4: Ollama Configuration Optimization (3 SP)**
  - OLLAMA_NUM_PARALLEL=4 for +30% throughput
- **61.5: Ollama Request Batching (3 SP, conditional)**
  - Only if sustained load >30 QPS
- **61.6: Fix Chat Endpoint Timeout (3 SP)** - P0 Critical
  - /api/v1/chat/ hangs >49s, production blocker
- **61.7: Update Tool Framework Documentation (1 SP)** - ✅ COMPLETE
  - Fix outdated API endpoints in TOOL_FRAMEWORK_USER_JOURNEY.md

**Expected Impact:**
- Query latency: -100ms (embeddings -80ms, reranking -20ms)
- Ingestion speed: +1500% (batch embeddings 16x faster)
- Ollama throughput: +30-50%
- Chat endpoint reliability: Fixed (no hanging requests)

### Sprint 62 (Section-Aware Features + Research Endpoint)
**Duration:** 2-3 weeks | **Story Points:** 38 SP | **Status:** PLANNED

**Focus:** Activate dormant section-aware infrastructure (currently ~20% utilized) + Missing features
- **62.1: Section-Aware Graph Queries (5 SP)**
- **62.2: Multi-Section Metadata in Vector Search (3 SP)**
- **62.3: VLM Image Integration with Sections (5 SP)**
- **62.4: Section-Aware Citations (3 SP)**
- **62.5: Section-Aware Reranking Integration (2 SP)**
- **62.6: HAS_SUBSECTION Hierarchical Links (3 SP)**
- **62.7: Document Type Support for Sections (5 SP)** - Markdown, DOCX, TXT
- **62.8: Section-Based Community Detection (3 SP)**
- **62.9: Section Analytics Endpoint (2 SP, optional)**
- **62.10: Implement Research Endpoint (8 SP)** - P1 High
  - /api/v1/chat/research documented but not implemented

**Expected Impact:**
- Section utilization: 20% → 95%
- Citation precision: +40% (section-level vs document-level)
- Document type coverage: +3 formats
- Agentic research workflows: Available (LangGraph multi-step search)

### Sprint 63 (Conversational Intelligence & Temporal + Testing)
**Duration:** 2 weeks | **Story Points:** 41 SP | **Status:** PLANNED

**Focus:** Multi-turn conversations + basic audit trail + structured output + Test coverage
- **63.1: Multi-Turn RAG Template (13 SP)** - NEW FEATURE
  - Memory Summarizer (5 SP)
  - Enhanced Prompt Template (3 SP)
  - Contradiction Detection (3 SP)
  - Answer Generator Integration (2 SP)
- **63.2: Basic Temporal Audit Trail (8 SP)**
  - "Who changed what and when" for entities/relations
  - Change log table + temporal query API
- **63.3: Redis Prompt Caching (5 SP, conditional)**
  - Cache frequent prompts for +20% speedup (only if >100 QPS)
- **63.4: Structured Output Formatting (5 SP)** - NEW FEATURE
  - Response templates by intent (factual, comparison, explanation, summary)
  - Markdown formatting, metadata footer, contradiction warnings
  - Professional, consistent output for all query types
- **63.5: Section-Based Community Detection (3 SP)** - from Sprint 62 overflow
- **63.6: Playwright E2E Tests (5 SP)** - P1 High
  - Missing E2E test coverage for tool framework (0/4 journeys)
  - tests/e2e/test_tool_framework_journeys.py (new file)
- **63.7: MCP Authentication Guide (2 SP)** - P2 Medium
  - JWT auth documentation for MCP tools
  - docs/api/AUTHENTICATION.md + scripts/generate_test_token.py

**Expected Impact:**
- Multi-turn context retention: 0% → 95%
- Response consistency: +60% (structured templates)
- Contradiction detection in sources
- Full audit trail for all changes
- E2E test coverage: 0% → 100% (4/4 journeys)
- Developer experience: JWT auth documented

### Sprint 67 (Secure Shell Sandbox + Agents Adaptation + LLM Intent Classifier)
**Duration:** 12 days | **Story Points:** 75 SP | **Status:** IN PROGRESS

**Focus:** Deepagents sandbox integration, Tool-level adaptation framework, C-LARA intent classification
- **67.1-67.4: Secure Shell Sandbox (deepagents)** - 15 SP
  - BubblewrapSandboxBackend implementation
  - Multi-language CodeAct (Bash + Python)
  - Integration & testing
- **67.5-67.9: Agents Adaptation Framework** - 45 SP
  - Unified Trace & Telemetry (8 SP)
  - Eval Harness (10 SP)
  - Dataset Builder (8 SP)
  - Adaptive Reranker v1 (13 SP)
  - Query Rewriter v1 (6 SP)
- **67.10-67.13: LLM Intent Classifier (C-LARA)** - 13 SP (TD-079) ✅ RESOLVED Sprint 81
  - ✅ 67.10: Data generation with Qwen2.5:7b (COMPLETE)
  - ✅ 81.7: Multi-Teacher training (4 models, 1040 examples) (COMPLETE)
  - ✅ Model deployed to models/intent_classifier/
  - ✅ Integration verified (USE_SETFIT_CLASSIFIER=true)
- **67.14: Section Extraction Quick Wins** - 7 SP (TD-078 Phase 1)
  - Profiling + batch tokenization + regex optimization

**Expected Impact:**
- Secure code execution in isolated sandbox
- Tool-level adaptation (retriever, reranker, query-rewriter)
- Intent classification accuracy: 60% → 85-92%
- Section extraction: 2-3x faster

**Progress:** 3 SP complete (67.10), 72 SP remaining

### Sprint 68 (Production Hardening + Performance + Section Features)
**Duration:** 10 days | **Story Points:** 62 SP | **Status:** PLANNED

**Focus:** E2E test completion, performance optimization, section community detection
- **68.1-68.3: E2E Test Completion** - 13 SP
  - Fix critical E2E failures (594 tests → 100%)
  - Performance test infrastructure
- **68.4-68.7: Performance Optimization** - 21 SP
  - Section extraction parallelization (TD-078 Phase 2, 11 SP)
  - BM25 cache auto-refresh (TD-074, 5 SP)
  - Ingestion performance tuning (TD-070, 5 SP)
- **68.8: Section Community Detection** - 10 SP
  - Louvain/Leiden algorithms for section-based communities
  - Integration with hybrid search
- **68.9-68.10: Advanced Adaptation** - 18 SP
  - Memory-Write Policy (10 SP)
  - Tool-Execution Reward Loop (8 SP)
- **Deferred (Optional):** TD-064 Temporal Community Summaries (13 SP)

**Expected Impact:**
- E2E test pass rate: 57% → 100%
- Query latency P95: 500ms → 350ms (-30%)
- Section extraction: 5-10x total speedup
- Memory usage: -30%, Throughput: +25%

### Sprint 69+ (Deferred Features)
- TD-044: DoclingParsedDocument Interface (8 SP)
- TD-054: Unified Chunking Service (6 SP)
- TD-055: MCP Client (21 SP)
- TD-056: Project Collaboration (34 SP)

---

## Items by Category

### Architecture
- [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md): Unified Chunking Service
- [TD-051](TD-051_MEMORY_CONSOLIDATION_PIPELINE.md): Memory Consolidation Pipeline

### Performance (Sprint 67-68)
- [TD-078](TD-078_SECTION_EXTRACTION_PERFORMANCE.md): Section Extraction Performance (Sprint 67-68, 18 SP)
- [TD-070](TD-070_INGESTION_PERFORMANCE_TUNING.md): Ingestion Performance Tuning (Sprint 68, 13 SP)
- [TD-074](TD-074_BM25_CACHE_DISCREPANCY.md): BM25 Cache Discrepancy (Sprint 68, 5 SP)

### Adaptation & Intelligence (Sprint 67)
- [TD-079](TD-079_LLM_INTENT_CLASSIFIER_CLARA.md): LLM Intent Classifier (Sprint 67, 13 SP)

### Data Model & Architecture
- [TD-044](TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md): DoclingParsedDocument Interface (Sprint 69+, 8 SP)
- [TD-054](TD-054_UNIFIED_CHUNKING_SERVICE.md): Unified Chunking Service (Sprint 69+, 6 SP)
- [TD-064](TD-064_TEMPORAL_COMMUNITY_SUMMARIES.md): Temporal Community Summaries (Sprint 68 optional, 13 SP)

### Features (Future)
- [TD-055](TD-055_MCP_CLIENT_IMPLEMENTATION.md): MCP Client (Sprint 69+, 21 SP)
- [TD-056](TD-056_PROJECT_COLLABORATION_SYSTEM.md): Project Collaboration (Sprint 69+, 34 SP)

---

## Dependency Graph

```
TD-044 (Docling Interface)
    └─→ TD-054 (Unified Chunking) ─→ TD-048 ✓ DONE (Sprint 49)

TD-043 (Follow-up Questions)
    └─→ TD-049 (User Profiling)

TD-045 (entity_id Migration)
    └─→ TD-046 (RELATES_TO) ✓ DONE (Sprint 34)

TD-048 (Graph Extraction) ✓ DONE (Sprint 49)
TD-059 (Reranking) ✓ DONE (Sprint 48)
TD-063 (Relation Dedup) ✓ DONE (Sprint 49)
```

---

## Metrics

### Velocity Required (to clear backlog)
- Total remaining: ~139 SP
- Sprint 67-68 planned: 75 + 62 = 137 SP
- After Sprint 68: ~55 SP remaining (deferred features)

### Sprint 67-68 Allocation
- Sprint 67: 75 SP (Sandbox, Adaptation, Intent Classifier, Section Quick Wins)
- Sprint 68: 62 SP (E2E Tests, Performance, Section Features, Advanced Adaptation)
- Total: 137 SP across 22 days

---

## Notes

1. **Sprint 67 Planning Complete** - 75 SP sprint with 3 epics (Sandbox, Adaptation, Intent Classifier)
2. **Sprint 68 Planning Complete** - 62 SP production hardening sprint (E2E tests, performance, sections)
3. **18 items archived** - 7 additional TDs archived (043, 047, 058, 069, 071, 072, 073)
4. **TD-047 exceeded baseline** - 608 Playwright tests vs. 40 planned (Sprint 51) - ARCHIVED
5. **Sprint 60 investigations complete** - TD-071 (vLLM), TD-072 (Reranking), TD-073 (Embeddings) - ARCHIVED
6. **TD-078 & TD-079 prioritized** - Section extraction (18 SP) + Intent classifier (13 SP) for Sprint 67-68
7. **Active TD count reduced** - 16 → 9 items (-44% cleanup)
8. **Story points reduced** - 264 SP → 139 SP (-47% backlog reduction)
9. **Sprint 67-68 addresses 98% of backlog** - 137 SP planned vs. 139 SP total
10. **Thematic alignment** - Performance TDs (078, 070, 074) grouped in Sprint 68
11. **TD-064 optional** - Temporal Community Summaries deferred unless capacity available

---

**Document maintained by:** Technical Debt Tracking System
**Review frequency:** Every sprint planning
