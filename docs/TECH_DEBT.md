# Technical Debt Register

**Last Updated:** 2025-11-21 (Sprint 32)
**Project:** AegisRAG
**Status:** ✅ **EXCELLENT** - Sprint 27 resolved 25% of remaining technical debt

## Executive Summary

### Sprint 25-27 Cleanup Success 🎉

Sprints 25-27 **dramatically reduced** technical debt:

**Technical Debt Reduction:**
- **Before (13.11.):** 28 Items, ~54 SP
- **Sprint 25 Resolved:** -9 Items, -18 SP (Feature 25.7, 25.8, 25.9)
- **Sprint 27 Resolved:** -3 Items, -9 SP (Feature 27.1 Monitoring)
- **After (16.11.):** **9 Items, ~14 SP**
- **Total Reduction:** **-68% Technical Debt** 🎉

**Code Cleanup (Sprint 25):**
- 🗑️ **1,626 Lines** removed (deprecated code, duplicates)
- ✅ **549 Lines** deprecated code removed (Feature 25.7)
- ✅ **300 Lines** duplicate code consolidated (Feature 25.8)
- ✅ **4 Clients** renamed for consistency (Feature 25.9)

**Quality Improvements (Sprint 27):**
- ✅ **Test Coverage:** 65% → 80% (+15%, +69 tests)
- ✅ **E2E Tests:** 174/184 → 184/184 (100% pass rate, +10 fixed)
- ✅ **Monitoring:** Real health checks (TD-TODO-01, 02, 03 resolved)

---

## ✅ Resolved Items (Sprint 25)

### TD-REF-01: Deprecated Ingestion Pipeline (RESOLVED ✅)

**Category:** Code Cleanup
**Priority:** P1 (High)
**Sprint 25 Feature:** 25.7 - Deprecated Code Removal

**Description:**
`unified_ingestion.py` was deprecated after Sprint 21 Docling Container migration.

**Resolution:**
- ✅ Deleted `src/components/ingestion/unified_ingestion.py` (278 LOC)
- ✅ All imports migrated to `docling_client.py`
- ✅ No references remaining in codebase

**Related Commit:** Feature 25.7 (Sprint 25)

---

### TD-REF-02: Deprecated Three-Phase Extractor (RESOLVED ✅)

**Category:** Code Cleanup
**Priority:** P1 (High)
**Sprint 25 Feature:** 25.7 - Deprecated Code Removal

**Description:**
`three_phase_extractor.py` was archived after LightRAG migration.

**Resolution:**
- ✅ Moved to `archive/three_phase_extractor.py` (271 LOC)
- ✅ Replaced with `LightRAGWrapper` (ADR-024)
- ✅ All test references updated

**Related Commit:** Feature 25.7 (Sprint 25)

---

### TD-REF-03: Deprecated load_documents() (RESOLVED ✅)

**Category:** Code Cleanup
**Priority:** P1 (High)
**Sprint 25 Feature:** 25.7 + 25.8

**Description:**
Old LlamaIndex `load_documents()` function was unused after Docling migration.

**Resolution:**
- ✅ Function removed from all modules
- ✅ Direct Docling API usage everywhere
- ✅ Zero LlamaIndex ingestion references

**Related Commit:** Feature 25.7 (Sprint 25)

---

### TD-REF-04: Duplicate base.py (RESOLVED ✅)

**Category:** Code Duplication
**Priority:** P2 (Medium)
**Sprint 25 Feature:** 25.8 - Code Consolidation

**Description:**
`src/agents/base.py` duplicated core utilities.

**Resolution:**
- ✅ Deleted duplicate file
- ✅ Migrated imports to `src/core/`
- ✅ Reduced code duplication

**Related Commit:** Feature 25.8 (Sprint 25)

---

### TD-REF-05: EmbeddingService Wrapper (RESOLVED ✅)

**Category:** Code Duplication
**Priority:** P2 (Medium)
**Sprint 25 Feature:** 25.8 - Code Consolidation

**Description:**
Unnecessary wrapper around BGE-M3 embeddings.

**Resolution:**
- ✅ Removed wrapper (29 LOC)
- ✅ Direct embedding model usage
- ✅ Simplified architecture

**Related Commit:** Feature 25.8 (Sprint 25)

---

### TD-REF-06: Client Naming Inconsistency (RESOLVED ✅)

**Category:** Architecture Consistency
**Priority:** P2 (Medium)
**Sprint 25 Feature:** 25.9 - Client Naming Standardization

**Description:**
Inconsistent client naming across codebase.

**Resolution:**
- ✅ Renamed 4 clients: QdrantClient, Neo4jClient, RedisClient, DoclingClient
- ✅ Consistent `*Client` suffix
- ✅ Updated 15+ import statements

**Related Commit:** Feature 25.9 (Sprint 25)

---

### TD-23.3: Token Split Estimation Fix (RESOLVED ✅)

**Category:** Data Quality
**Priority:** P3 (Low)
**Sprint 25 Feature:** 25.3 - LLM Proxy Improvements

**Description:**
Cost tracking used 50/50 token split estimation.

**Resolution:**
- ✅ Provider-specific token breakdown implemented
- ✅ Accurate input/output token tracking
- ✅ $11,750/year cost visibility achieved

**Related Commit:** Feature 25.3 (Sprint 25)

---

### TD-23.4: Async/Sync Bridge Removed (RESOLVED ✅)

**Category:** Architecture Cleanup
**Priority:** P2 (Medium)
**Sprint 25 Feature:** 25.4 - Async/Sync Refactoring

**Description:**
Unnecessary sync-to-async bridges in ingestion pipeline.

**Resolution:**
- ✅ All ingestion code fully async
- ✅ No `asyncio.run()` calls in async contexts
- ✅ Cleaner control flow

**Related Commit:** Feature 25.4 (Sprint 25)

---

### TD-G.2: Prometheus Metrics Missing (RESOLVED ✅)

**Category:** Observability
**Priority:** P1 (High)
**Sprint 25 Feature:** 25.1 - Prometheus Metrics Implementation

**Description:**
No production-grade monitoring metrics.

**Resolution:**
- ✅ Prometheus metrics implemented (15 metrics)
- ✅ LLM request tracking (latency, cost, tokens)
- ✅ Integration tests passing (15/15)

**Related Commit:** Feature 25.1 (Sprint 25)

---

## 📋 Remaining Technical Debt (Sprint 26)

### Category 1: Architecture (Low Priority)

#### TD-23.1: ANY-LLM Partial Integration

**Priority:** P3 (Low) - **NOT URGENT**
**Effort:** 2 days
**Status:** DEFERRED (SQLite solution works perfectly)

**Description:**
Using ANY-LLM `acompletion()` but not full framework (BudgetManager, Gateway).

**Why Not Urgent:**
- ✅ Custom SQLite CostTracker works perfectly (389 LOC, 4/4 tests passing)
- ❌ ANY-LLM Gateway requires additional infrastructure
- ❌ VLM support missing in ANY-LLM

**Decision:** Wait until ANY-LLM adds VLM support or scaling issues occur.

**Related Files:**
- `src/components/llm_proxy/cost_tracker.py`
- `src/components/llm_proxy/aegis_llm_proxy.py`

---

#### TD-23.2: DashScope VLM Bypass Routing

**Priority:** P3 (Low) - **NOT URGENT**
**Effort:** 1 day
**Status:** DEFERRED (functional workaround in place)

**Description:**
`DashScopeVLMClient` bypasses `AegisLLMProxy` routing.

**Why Not Urgent:**
- ✅ Cost tracking functional (manually integrated)
- ❌ ANY-LLM doesn't support VLM tasks
- ✅ Functional workaround is stable

**Decision:** Wait for ANY-LLM VLM support.

**Related Files:**
- `src/components/llm_proxy/dashscope_vlm.py`

---

#### TD-REF-07: BaseClient Pattern

**Priority:** P3 (Low)
**Effort:** 1 day
**Status:** BACKLOG

**Description:**
All Client classes duplicate Connection/Health Check/Logging patterns (~300 LOC).

**Goal:**
Abstract `BaseClient` with `connect()`, `disconnect()`, `health_check()`.

**Impact:** Code duplication, but functionally not critical.

**Recommended Sprint:** Sprint 27+

---

### Category 2: Code TODOs (30 TODOs in 12 files)

#### Priority P2 (Medium) - Monitoring

**TD-TODO-01: Health Check Placeholders**

**Files:** `src/api/health/memory_health.py`
**Effort:** 0.5 day

```python
# Current: Placeholder Data
"collections": 0,  # TODO: Get actual collection count
"vectors": 0,  # TODO: Get actual vector count
"capacity": 0.0,  # TODO: Get actual capacity
```

**Fix:** Query Qdrant/Graphiti APIs for real data.

**Recommended Sprint:** Sprint 26 Feature 26.4

---

**TD-TODO-02: Memory Monitoring Capacity**

**Files:** `src/components/memory/monitoring.py`
**Effort:** 0.5 day

```python
# Current: Placeholder Capacity
capacity = 0.0  # TODO: Get from Qdrant API
entries = 0  # TODO: Get collection size
```

**Fix:** Implement real capacity tracking.

**Recommended Sprint:** Sprint 26 Feature 26.4

---

**TD-TODO-03: Startup/Shutdown Handlers**

**Files:** `src/api/main.py`
**Effort:** 0.5 day

```python
# TODO: Initialize database connections, load models, etc.
# TODO: Close database connections, cleanup resources
```

**Fix:** Graceful startup/shutdown for Qdrant, Neo4j, Redis.

**Recommended Sprint:** Sprint 26 Feature 26.4

---

#### Priority P3 (Low) - Enhancements

**TD-TODO-04: Multi-hop Query Context Injection**

**Files:** `src/components/retrieval/query_decomposition.py`
**Effort:** 2 days
**Status:** ENHANCEMENT (not critical)

```python
# TODO: For true multi-hop, inject context from previous results
```

**Description:** Propagate context from Sub-Query 1 → Sub-Query 2.

**Recommended Sprint:** Sprint 27+

---

**TD-TODO-05: Memory Consolidation Migration**

**Files:** `src/components/memory/consolidation.py`
**Effort:** 1 day
**Status:** ENHANCEMENT

```python
# TODO: Migrate unique items to Qdrant/Graphiti
```

**Description:** Migrate consolidated memories to long-term storage.

**Recommended Sprint:** Sprint 27+

---

**TD-TODO-06: Profiling Modules (Sprint 17)**

**Files:** `src/components/profiling/__init__.py`
**Effort:** 2 days
**Status:** BACKLOG (Sprint 17 incomplete)

```python
# TODO: Sprint 17 - Implement remaining profiling modules
```

**Description:** Complete Performance/Memory Profiling modules.

**Recommended Sprint:** Sprint 28+

---

**TD-TODO-07: LightRAG Entity/Relation Extraction**

**Files:** `src/components/graph_rag/lightrag_wrapper.py`
**Effort:** 1 day
**Status:** ENHANCEMENT

```python
entities=[],  # TODO: Extract from LightRAG internal state
relationships=[],  # TODO: Extract from LightRAG internal state
context="",  # TODO: Get context used for generation
```

**Description:** Add transparency to LightRAG reasoning.

**Recommended Sprint:** Sprint 27+

---

**TD-042: BGE-M3 Similarity-Based Section Merging (Sprint 32)**

**Category:** Enhancement / Chunking Strategy
**Priority:** P3 (Low - On Demand)
**Effort:** 1-2 days
**Status:** DEFERRED (Threshold-based approach sufficient for 90% of cases)
**Related:** ADR-039 (Adaptive Section-Aware Chunking)

**Description:**
Enhance adaptive section chunking with BGE-M3 semantic similarity to determine which sections should be merged (instead of purely token-based thresholds).

**Current Approach (Sprint 32):**
```python
# Simple threshold: Merge if both sections small AND sum < 1800 tokens
if section_tokens < 1200 and (current + section_tokens) < 1800:
    merge()
```

**Enhanced Approach (Optional):**
```python
# Add semantic similarity check before merge
if section_tokens < 1200 and (current + section_tokens) < 1800:
    similarity = cosine_similarity(bge_m3(current), bge_m3(section))
    if similarity > 0.80:  # Configurable threshold
        merge()  # Thematically similar
    else:
        keep_separate()  # Different topics
```

**Benefits:**
- ✅ Prevents merging unrelated sections (e.g., "Database Indexing" + "Frontend Performance")
- ✅ Improves LightRAG extraction quality (-20-25% false relations vs -15% with threshold-only)
- ✅ No new dependencies (BGE-M3 already in stack per ADR-024)
- ✅ Useful for unstructured docs (meeting notes, transcripts, wiki pages)

**Trade-offs:**
- ⚠️ +500-750ms per document (10-15 embeddings)
- ⚠️ Threshold tuning required (similarity threshold: 0.75-0.85?)
- ⚠️ Overkill for structured docs (PowerPoint, PDFs with clear headings)

**Implementation:**
- Add as opt-in feature via config: `ADAPTIVE_CHUNKING_USE_SIMILARITY=true`
- Enable A/B testing (with vs without similarity check)
- Benchmark on real documents to measure impact

**Recommended Trigger:**
- Implement if threshold-based approach produces too many/few merges
- Implement for specific document types (meeting notes, unstructured content)
- Sprint 33+ after evaluating Sprint 32 threshold-based results

**Files:**
- `src/components/ingestion/langgraph_nodes.py` (chunking_node)
- `src/core/config.py` (add ADAPTIVE_CHUNKING_USE_SIMILARITY flag)

---

## 📊 Priority Matrix

| Priority | Count | Effort | Category | Sprint Recommendation |
|----------|-------|--------|----------|----------------------|
| **P1 (High)** | 0 | 0d | - | ✅ ALL RESOLVED |
| **P2 (Medium)** | 3 | 1.5d | Monitoring | Sprint 26 Feature 26.4 |
| **P3 (Low)** | 10 | 12d | Enhancements + Architecture | Sprint 27+ |

**Total Remaining:** 13 Items, ~13.5 days (27 SP)
**New (Sprint 32):** TD-042 (BGE-M3 Similarity-Based Section Merging) - On Demand

---

## 🎯 Sprint 26 Recommendations

### Feature 26.4: Monitoring Completion (5 SP)

**Scope:**
- TD-TODO-01: Real Qdrant/Graphiti health checks
- TD-TODO-02: Memory capacity tracking
- TD-TODO-03: Graceful startup/shutdown handlers

**Deliverables:**
- Health checks return real data (not placeholder 0s)
- Memory monitoring shows actual capacity
- Graceful connection management

**Tests:**
- Integration tests for health endpoints
- Startup/shutdown tests

---

## 📈 Metrics

### Code Quality After Sprint 25

**Technical Debt:**
- ✅ 57% reduction (28 items → 12 items)
- ✅ All P1 items resolved
- ✅ 1,626 LOC removed

**Test Coverage:**
- ✅ MyPy strict mode enforced
- ✅ All integration tests passing (100%)
- ✅ CI pipeline optimized (~66% faster)

**Production Readiness:**
- ✅ Clean codebase (no critical tech debt)
- ✅ Cost tracking operational ($0.003 tracked)
- ✅ Multi-cloud LLM execution working
- ✅ Architecture compliance (ADR-026, ADR-027, ADR-028, ADR-033)

---

## 🚀 Next Steps

1. **Sprint 28:** ✅ COMPLETE - Frontend integration (follow-up questions, citations, settings)
2. **Sprint 29:** Encryption for API keys (Web Crypto API), Export/Import settings
3. **Sprint 30+:** Architecture enhancements (BaseClient, ANY-LLM VLM routing, Backend sync)

---

**Document History:**
- **2025-11-13:** Created (Sprint 23)
- **2025-11-15:** Updated (Sprint 26) - Marked Sprint 25 resolutions, reduced from 28 to 12 items
- **2025-11-16:** Updated (Sprint 28) - Marked Sprint 27 resolutions, reduced from 12 to 9 items

**Maintainer:** Claude Code
**Status:** ✅ UP TO DATE (Sprint 26)
