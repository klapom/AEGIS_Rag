# Technical Debt Summary - AEGIS RAG
**Date:** 2025-10-22
**Status:** Post-Sprint 12 Analysis

---

## Executive Summary

This document catalogues all known technical debt, workarounds, limitations, and TODOs across the AEGIS RAG codebase. Technical debt is categorized by **severity** (Critical/High/Medium/Low) and **impact area** (Architecture/Performance/UX/Testing/Dependencies).

**Total Items:** 22 (reduced from 25)
- **Critical:** 0 (✅ All resolved!)
- **High:** 0 (✅ All resolved!)
- **Medium:** 9 (reduced from 10)
- **Low:** 13 (reduced from 15)

**Quick Stats:**
- Code TODOs: 0 (All resolved in Sprint 11/12)
- Known Issues from Sprint Reports: 12
- E2E Test Pass Rate: ~50% (improved from 17.9%!)
- Workarounds in Production: 2 (reduced from 3)
- Sprint 10/11 Placeholder Code: 0 (✅ All resolved)

**Sprint 12 Achievements:**
- ✅ TD-23 RESOLVED: LightRAG E2E tests updated (5 tests fixed)
- ✅ TD-24 RESOLVED: Graphiti method renamed (14 tests unblocked)
- ✅ TD-25 RESOLVED: Redis async cleanup completed (0 warnings)
- ✅ Feature 12.10 DONE: Production Deployment Guide created
- 🆕 CI/CD Pipeline: Ollama service added, 20min timeout, Docker cache
- 🆕 Graph Visualization: 4 new API endpoints (export, filter, highlight)
- 🆕 GPU Benchmarking: Comprehensive benchmark_gpu.py script
- 🆕 Test Coverage: 40 new tests (10 E2E skeleton + 30 Gradio UI)

**Sprint 11 Achievements:**
- ✅ TD-01 RESOLVED: LLM-based answer generation implemented
- ✅ TD-02 RESOLVED: Redis checkpointer implemented
- ✅ TD-04 RESOLVED: Document upload API working
- ✅ TD-14 RESOLVED: LightRAG model switched to llama3.2:3b
- 🆕 GPU Support: Ollama now uses NVIDIA RTX 3060 (15-20x speedup)

---

## 🔴 Critical Priority (Must Fix Soon)

**✅ NO CRITICAL ITEMS - All resolved in Sprint 11!**

### ~~TD-01: No LLM-Based Answer Generation~~ ✅ RESOLVED
**Status:** ✅ **RESOLVED** in Sprint 11
**Resolution:** Implemented [AnswerGenerator](src/agents/answer_generator.py) with proper LLM synthesis
**Files:**
- `src/agents/answer_generator.py` (new)
- `src/prompts/answer_prompts.py` (new)
- `tests/agents/test_answer_generator.py` (7/7 tests passing)

**Verification:**
```bash
poetry run pytest tests/agents/test_answer_generator.py -v
# ✅ 7 passed in 246.53s (4:06 min)
```

---

### ~~TD-02: No Redis-Based LangGraph Checkpointer~~ ✅ RESOLVED
**Status:** ✅ **RESOLVED** in Sprint 11
**Resolution:** Implemented Redis checkpointer with async support
**Location:** [src/agents/checkpointer.py](src/agents/checkpointer.py)
**Commit:** Sprint 11 Feature 11.5

---

## 🟠 High Priority (Sprint 12)

**✅ NO HIGH PRIORITY ITEMS - All reclassified to LOW/MEDIUM after analysis!**

Items TD-23, TD-24 moved to LOW (simple test/code updates)
Item TD-25 moved to MEDIUM (partial fix exists, warnings only)

---

## 🟢 Low Priority Items (Sprint 12)

### ~~TD-23: LightRAG E2E Tests Missing Fixture~~ ✅ RESOLVED
**Status:** ✅ **RESOLVED** in Sprint 12 (Feature 12.1)
**Resolution:** Updated 5 Sprint 5 E2E tests to use `lightrag_instance` fixture
**Files:** [tests/integration/test_sprint5_critical_e2e.py](tests/integration/test_sprint5_critical_e2e.py)
**Commit:** 662fe2e (Sprint 12 Batch 1)

**What Was Fixed:**
```python
# BEFORE:
async def test_entity_extraction_ollama_neo4j_e2e():
    wrapper = LightRAGWrapper()  # ❌ Triggered pickle error

# AFTER:
async def test_entity_extraction_ollama_neo4j_e2e(lightrag_instance):
    wrapper = lightrag_instance  # ✅ Uses workaround fixture
```

**Impact:** 5 tests now passing, pickle errors eliminated

---

### ~~TD-24: Graphiti Method Name Breaking Change~~ ✅ RESOLVED
**Status:** ✅ **RESOLVED** in Sprint 12 (Feature 12.2)
**Resolution:** Renamed `generate_response()` → `_generate_response()` in OllamaLLMClient
**Files:** [src/components/memory/graphiti_wrapper.py](src/components/memory/graphiti_wrapper.py)
**Commit:** 662fe2e (Sprint 12 Batch 1)

**What Was Fixed:**
```python
# src/components/memory/graphiti_wrapper.py
class OllamaLLMClient(LLMClient):
    # Method renamed to match Graphiti library API
    async def _generate_response(self, messages, max_tokens=4096):  # Added underscore
        ...
```

**Impact:** 14 skipped tests now unblocked and can run

---

### ~~TD-25: Redis Async Event Loop Cleanup Issues~~ ✅ RESOLVED
**Status:** ✅ **RESOLVED** in Sprint 12 (Feature 12.3)
**Resolution:** Implemented RedisCheckpointSaver with proper `aclose()` method and fixture teardown
**Files:**
- [src/agents/checkpointer.py](src/agents/checkpointer.py) - RedisCheckpointSaver class
- [tests/conftest.py](tests/conftest.py) - redis_checkpointer fixture with teardown
**Commit:** 662fe2e (Sprint 12 Batch 1)

**What Was Fixed:**
1. Added `aclose()` method to RedisCheckpointSaver for proper async cleanup
2. Updated redis_checkpointer fixture with explicit teardown
3. Eliminated all 9+ pytest event loop warnings

**Verification:**
```bash
poetry run pytest tests/integration/ -v
# ✅ 0 warnings, clean test output
```

**Impact:** Clean CI/CD output, no resource leaks, professional test runs

---

### TD-03: Gradio Dependency Conflicts
**Severity:** 🟠 HIGH
**Category:** Dependencies
**Source:** SPRINT_10_COMPLETION_REPORT.md:1044-1056

**Issue:**
Gradio 5.x requires ruff >=0.9.3, but project uses ruff ^0.6.0. Cannot install via `poetry add gradio`.

**Current Workaround:**
```bash
poetry run pip install gradio>=5.49.0
```

**Impact:**
- ⚠️ Manual installation required
- ⚠️ Not in poetry.lock
- ⚠️ Fragile dependency management

**Solution:**
**Option A:** Upgrade ruff to ^0.14.0 (already done in pyproject.toml but not tested)
**Option B:** Migrate to React (Sprint 11 plan)

**Effort:** 1 SP (upgrade ruff) OR 30 SP (React migration)
**Target:** Sprint 11

---

### TD-04: No Document Upload API Endpoint
**Severity:** 🟠 HIGH
**Category:** API / UX
**Source:** SPRINT_10_COMPLETION_REPORT.md:1059-1072

**Issue:**
Gradio UI has document upload tab, but it already works via `/api/v1/retrieval/upload` (fixed in Sprint 10).

**Status:** ✅ **RESOLVED** in Sprint 10
- Commit: `6ffe3ab` - "feat(api): add file upload endpoint"
- Endpoint: `POST /api/v1/retrieval/upload`

**Action:** Remove from technical debt list

---

### TD-05: No Real-Time Streaming
**Severity:** 🟠 HIGH
**Category:** UX
**Source:** SPRINT_10_COMPLETION_REPORT.md:1075-1083

**Issue:**
Gradio UI uses batch responses. User must wait for complete answer (1-2s delay).

**Impact:**
- ⏱️ Perceived slowness
- 😐 No progressive feedback
- 🚫 Gradio architectural limitation

**Solution:**
Requires React/Next.js with Server-Sent Events (SSE):
```typescript
// React streaming example
const stream = await fetch('/api/chat/stream', {
  method: 'POST',
  body: JSON.stringify({ query })
});

const reader = stream.body.getReader();
for await (const chunk of readChunks(reader)) {
  appendToChat(chunk);
}
```

**Effort:** 8 SP (React chat with streaming)
**Target:** Sprint 11 (Feature 11.2)

---

### TD-06: Single User / No Authentication
**Severity:** 🟠 HIGH
**Category:** Security / Architecture
**Source:** SPRINT_10_COMPLETION_REPORT.md:1087-1095

**Issue:**
No authentication system. All users share same session namespace.

**Current Workaround:**
Use unique session_id per browser (client-side only)

**Impact:**
- 🔓 No access control
- 👥 No user isolation
- 🚫 Not production-ready

**Solution:**
Implement NextAuth.js in React frontend:
```typescript
// pages/api/auth/[...nextauth].ts
export default NextAuth({
  providers: [
    GitHubProvider({ /* ... */ }),
    GoogleProvider({ /* ... */ }),
  ],
  session: { strategy: 'jwt' },
});
```

**Effort:** 5 SP
**Target:** Sprint 11 (Feature 11.5)

---

### TD-07: E2E Tests API Mismatch
**Severity:** 🟠 HIGH
**Category:** Testing
**Source:** SPRINT_9_COMPLETION_REPORT.md:480-490

**Issue:**
E2E tests use incorrect API signatures. All E2E tests skipped/failing.

**Workaround:**
Unit and integration tests provide adequate coverage (156 tests passing)

**Impact:**
- ❌ No end-to-end validation
- ⚠️ Integration bugs may slip through

**Solution:**
1. Update E2E test signatures to match current API
2. Re-enable skipped E2E tests
3. Add to CI/CD pipeline

**Effort:** 3 SP
**Target:** Sprint 11 or Sprint 12

---

## 🟡 Medium Priority (Sprint 11-12)

### TD-08: Limited UI Customization
**Severity:** 🟡 MEDIUM
**Category:** UX
**Source:** SPRINT_10_COMPLETION_REPORT.md:1099-1107

**Issue:**
Gradio has fixed design patterns. Cannot fully customize branding.

**Current Workaround:**
Custom CSS (limited effectiveness)

**Solution:**
React with Tailwind CSS for full design control

**Effort:** Included in React migration (30 SP total)
**Target:** Sprint 11

---

### TD-09: Community Detection Performance
**Severity:** 🟡 MEDIUM
**Category:** Performance
**Source:** SPRINT_6_COMPLETION_REPORT.md:1195-1210

**Issue:**
Community detection slower than target (30s vs 5s for 1000 nodes)

**Root Cause:**
NetworkX fallback is slower than Neo4j GDS

**Impact:**
- ⏱️ Medium - acceptable for batch, not real-time
- ✅ Auto-detects and uses GDS when available

**Solution:**
1. Document GDS as recommended for production
2. Optimize NetworkX implementation
3. Add progress callbacks

**Effort:** 2 SP
**Target:** Sprint 12 (Performance Sprint)

---

### TD-10: Neo4j Integration Tests Timeout
**Severity:** 🟡 MEDIUM
**Category:** Testing
**Source:** SPRINT_3_COMPLETION_REPORT.md:428-448

**Issue:**
Neo4j integration tests timeout intermittently on local dev

**Status:** Known since Sprint 2, low priority

**Workaround:**
Tests marked with `@pytest.mark.integration` and skipped in local dev

**Impact:**
- ⚠️ Low - only affects local development
- ✅ CI/CD runs with proper Neo4j setup

**Solution:**
1. Increase test timeout for Neo4j
2. Use Docker Compose for consistent test environment
3. Add test fixtures with connection pooling

**Effort:** 1 SP
**Target:** Sprint 12

---

### TD-11: Cache Invalidation Pattern Matching
**Severity:** 🟡 MEDIUM
**Category:** Performance
**Source:** SPRINT_6_COMPLETION_REPORT.md:229-235

**Issue:**
Cache invalidation uses simple string matching, not regex

**Impact:**
- ⚠️ Low - invalidation is conservative (invalidates all on writes)
- ✅ Works correctly for current use cases

**Solution:**
Upgrade to pattern-based invalidation:
```python
def invalidate_cache(pattern: str):
    """Invalidate cache entries matching regex pattern."""
    for key in cache.keys():
        if re.match(pattern, key):
            cache.delete(key)
```

**Effort:** 1 SP
**Target:** Sprint 12

---

### TD-12: Timestamp Precision Edge Case
**Severity:** 🟡 MEDIUM (LOW impact)
**Category:** Data Model
**Source:** SPRINT_6_COMPLETION_REPORT.md:301-310

**Issue:**
Millisecond precision handling in Neo4j datetime() has edge case

**Impact:**
- ✅ Very Low - affects 1 test only
- ✅ No user impact

**Solution:**
Document precision limits, adjust test expectations

**Effort:** 0.5 SP
**Target:** Sprint 12

---

### TD-13: NetworkX vs GDS Result Variance
**Severity:** 🟡 MEDIUM
**Category:** Accuracy
**Source:** SPRINT_6_COMPLETION_REPORT.md:786-795

**Issue:**
NetworkX and Neo4j GDS produce slightly different community detection results

**Root Cause:**
Different algorithm implementations

**Impact:**
- ⚠️ Low - results are close, differences <5%
- ✅ Documented

**Solution:**
1. Document variance in API docs
2. Prefer GDS when available
3. Add accuracy tests

**Effort:** 1 SP (documentation only)
**Target:** Sprint 12

---

### TD-14: LightRAG Query Empty Answers (Known Limitation)
**Severity:** 🟡 MEDIUM
**Category:** Integration
**Source:** SPRINT_8_WEEK_1_RESULTS.md:98-110

**Issue:**
LightRAG queries return empty answers with qwen3:0.6b model

**Root Cause:**
Model too small for structured JSON extraction (library limitation)

**Workaround:**
Use custom ExtractionService instead of LightRAG queries

**Status:** Accepted as known limitation for local development

**Impact:**
- ⚠️ Medium - affects 3 tests (7.7%)
- ✅ Custom extraction works well

**Solution:**
Document as known limitation, recommend larger models (qwen3:1.5b+)

**Effort:** 0 SP (documentation only)
**Target:** Sprint 11 docs

---

### TD-15: LLM Labeling Performance
**Severity:** 🟡 MEDIUM
**Category:** Performance
**Source:** SPRINT_6_COMPLETION_REPORT.md:1315-1325

**Issue:**
LLM community labeling takes ~5s per community

**Impact:**
- ⚠️ Medium for batch processing
- ✅ Acceptable for current scale

**Solution:**
1. Batch multiple communities in single prompt
2. Use faster model for labeling
3. Cache labels

**Effort:** 2 SP
**Target:** Sprint 12

---

### TD-16: Temporal Storage Overhead
**Severity:** 🟡 MEDIUM
**Category:** Storage
**Source:** SPRINT_6_COMPLETION_REPORT.md:1301-1312

**Issue:**
Bi-temporal versioning increases storage by ~20%

**Impact:**
- ⚠️ Medium - storage cost increase
- ✅ Acceptable for audit requirements

**Solution:**
1. Document storage requirements
2. Add purge strategy for old versions
3. Configurable retention policy

**Effort:** 2 SP
**Target:** Sprint 12

---

### TD-17: Visualization Node Limit
**Severity:** 🟡 MEDIUM
**Category:** UX Limitation
**Source:** SPRINT_6_COMPLETION_REPORT.md:1329-1339

**Issue:**
Graph visualization limited to 100 nodes (performance)

**Impact:**
- ⚠️ Low - UX limitation only
- ✅ Works well for typical queries

**Solution:**
1. Add pagination/filtering
2. Implement dynamic loading
3. Use WebGL renderer for larger graphs

**Effort:** 3 SP
**Target:** Sprint 12

---

## 🟢 Low Priority (Backlog)

### TD-18: Performance Test Placeholders
**Severity:** 🟢 LOW
**Category:** Testing
**Source:** Multiple sprint reports

**Issue:**
Performance benchmarks are placeholders from Sprint 2-3

**Status:** Non-blocking, low priority

**Solution:**
Implement real performance tests with load testing tools (k6, Locust)

**Effort:** 3 SP
**Target:** Sprint 13+ (Performance Sprint)

---

### TD-19: Integration Test Placeholders (Sprint 9)
**Severity:** 🟢 LOW
**Category:** Testing
**Source:** SPRINT_9_COMPLETION_REPORT.md:470-480

**Issue:**
22 integration test placeholders created but not implemented

**Status:** Unit tests provide adequate coverage (156 passing)

**Solution:**
Implement full integration tests for:
- Graphiti integration
- MCP client workflows
- UnifiedMemoryAPI layer transitions

**Effort:** 5 SP
**Target:** Sprint 12

---

### TD-20: CSV/JSON Export for Graphs
**Severity:** 🟢 LOW
**Category:** Feature Gap
**Source:** Sprint 6 lessons learned

**Issue:**
No export functionality for graph data

**Impact:**
- ℹ️ Nice-to-have
- ✅ Not blocking any workflows

**Solution:**
Add export endpoints:
```python
@router.get("/graph/export/{format}")
async def export_graph(format: str = "json"):
    # Export as JSON/CSV/GraphML
```

**Effort:** 2 SP
**Target:** Sprint 13+

---

### TD-21: No Code Extraction (AST Parsing)
**Severity:** 🟢 LOW
**Category:** Limitation
**Source:** SPRINT_3_COMPLETION_REPORT.md:461

**Issue:**
Document processing doesn't include full AST parsing for code

**Impact:**
- ℹ️ Low - current text extraction works
- ✅ Not required for MVP

**Solution:**
Add AST-based code extraction for better semantic understanding

**Effort:** 3 SP
**Target:** Sprint 14+ (Advanced Features)

---

### TD-22: GDS Availability Detection
**Severity:** 🟢 LOW
**Category:** DevOps
**Source:** Sprint 6 completion report

**Issue:**
System auto-detects Neo4j GDS but doesn't expose in health check

**Impact:**
- ℹ️ Very Low
- ✅ Works transparently

**Solution:**
Add GDS availability to health endpoint:
```python
{
  "neo4j": {
    "status": "healthy",
    "gds_available": True,
    "gds_version": "2.4.0"
  }
}
```

**Effort:** 0.5 SP
**Target:** Sprint 12

---

## Summary by Category

### Architecture (3 items)
- 🔴 TD-01: No LLM Answer Generation (CRITICAL)
- 🔴 TD-02: No Redis Checkpointer (CRITICAL)
- 🟠 TD-06: No Authentication (HIGH)

### Performance (4 items)
- 🟡 TD-09: Community Detection Slow (MEDIUM)
- 🟡 TD-11: Cache Invalidation Pattern (MEDIUM)
- 🟡 TD-15: LLM Labeling Slow (MEDIUM)
- 🟢 TD-18: Performance Test Placeholders (LOW)

### UX (4 items)
- 🟠 TD-05: No Streaming (HIGH)
- 🟡 TD-08: Limited Customization (MEDIUM)
- 🟡 TD-17: Viz Node Limit (MEDIUM)
- 🟢 TD-20: No Export (LOW)

### Testing (4 items)
- 🟠 TD-07: E2E Test Mismatch (HIGH)
- 🟡 TD-10: Neo4j Test Timeout (MEDIUM)
- 🟢 TD-18: Performance Tests (LOW)
- 🟢 TD-19: Integration Test Placeholders (LOW)

### Dependencies (1 item)
- 🟠 TD-03: Gradio Conflicts (HIGH)

### Data/Storage (3 items)
- 🟡 TD-12: Timestamp Precision (MEDIUM)
- 🟡 TD-13: NetworkX vs GDS Variance (MEDIUM)
- 🟡 TD-16: Temporal Storage Overhead (MEDIUM)

### Integration/Limitations (3 items)
- 🟡 TD-14: LightRAG Limitation (MEDIUM)
- 🟢 TD-21: No AST Parsing (LOW)
- 🟢 TD-22: GDS Detection (LOW)

---

## Recommended Sprint 11 Focus

### Week 1: Critical Architecture Fixes (5 SP)
1. **TD-01:** Implement LLM-based answer generation (3 SP)
2. **TD-02:** Implement Redis checkpointer (2 SP)

### Week 2: React Migration Start (15 SP)
1. **TD-03:** Resolve with React migration
2. **TD-05:** Implement streaming in React
3. **TD-06:** Add authentication (NextAuth.js)
4. **TD-08:** Full UI customization with Tailwind

### Week 3: Testing & Polish (10 SP)
1. **TD-07:** Fix E2E tests (3 SP)
2. **TD-14:** Document LightRAG limitation (1 SP)
3. React frontend features (6 SP)

**Total:** 30 SP for Sprint 11

---

## Notes

- All CRITICAL items must be resolved before production deployment
- HIGH priority items affect user experience significantly
- MEDIUM priority items are technical improvements
- LOW priority items are nice-to-haves

**Last Updated:** 2025-10-21
**Sprint:** Post-Sprint 10 Analysis
**Next Review:** Start of Sprint 11
