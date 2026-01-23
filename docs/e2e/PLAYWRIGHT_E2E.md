# AegisRAG Playwright E2E Testing Guide

**Last Updated:** 2026-01-23 (Sprint 118 - Follow-up Questions Bugs Fixed)
**Framework:** Playwright + TypeScript
**Test Environment:** http://192.168.178.10 (Docker Container)
**Auth Credentials:** admin / admin123
**Documentation:** This file is the authoritative source for all E2E testing information

---

## 🆕 Sprint 118: Bug Fixes & Test Stabilization

**Date:** 2026-01-21 | **Status:** In Progress

### Bugs Fixed (Sprint 118)

| Bug ID | Test File | Issue | Root Cause | Fix | Commit |
|--------|-----------|-------|------------|-----|--------|
| **BUG-118.1** | followup/*.spec.ts | Follow-up questions timeout (SSE polling 30x LLM calls) | SSE endpoint called `generate_followup_questions_async()` every 2s instead of checking Redis cache | Check `{session_id}:followup` cache FIRST before LLM fallback | `03b8d0e` |
| **BUG-118.2** | edge-filters.spec.ts | data-testid mismatch: `edge-filter-relates_to` vs `edge-filter-relates-to` | Component generated underscore, tests expected hyphen | Added `.replace(/_/g, '-')` in GraphFilters.tsx | `2971987` |
| **BUG-118.3** | memory-management.spec.ts | Mock URL mismatch: `/consolidate/status` vs `/consolidation/status` | E2E tests mocked wrong endpoint path | Updated mock URL to match frontend API call | `c0adc2b` |
| **BUG-118.4** | followup/*.spec.ts | Test timeout too short (10s) for LLM generation (20-60s) | `RetryPresets.PATIENT` (5×2s=10s) was far too short for Nemotron3 follow-up generation | Added `RetryPresets.FOLLOWUP_QUESTIONS` (30×2s=60s) preset | ✅ FIXED |
| **BUG-118.5** | followup/*.spec.ts | Follow-up generation **never triggered** in non-streaming API | `process_query()` (line 277) had NO code for follow-up generation - only existed in `_run_chain()` for streaming! | Added `_generate_followup_async()` call to `process_query()` | ✅ FIXED |
| **BUG-118.6** | followup/*.spec.ts | SSE URL uses wrong env var → goes to port 80 | `FollowUpQuestions.tsx` used `VITE_API_URL` (doesn't exist) with fallback `''` → relative URL to port 80 | Changed to `VITE_API_BASE_URL` | ✅ FIXED |
| **BUG-118.7** | followup/*.spec.ts | FollowUpQuestions NOT rendered in ConversationView/HomePage | Component only used in SearchResultsPage.tsx via StreamingAnswer - never in main chat UI! | Added FollowUpQuestions to ConversationView.tsx | ✅ FIXED |

### Code Changes (Sprint 118)

#### BUG-118.1: SSE Cache Fix (src/api/v1/chat.py)

```python
# Sprint 118 Fix: Check cache FIRST - coordinator stores questions here
cached_questions = await redis_memory.retrieve(key=cache_key, namespace="cache")

if cached_questions:
    # Extract value from Redis wrapper
    if isinstance(cached_questions, dict) and "value" in cached_questions:
        cached_questions = cached_questions["value"]

    questions = cached_questions.get("questions", [])
    if questions and len(questions) > 0:
        # Questions ready from cache - send and close
        event_data = {
            "questions": questions,
            "count": len(questions),
            "elapsed_seconds": elapsed,
            "from_cache": True,
        }
        yield f"event: questions\ndata: {json.dumps(event_data)}\n\n"
        return
```

**Impact:** Prevents 30x redundant LLM calls per follow-up question request.

#### BUG-118.2: data-testid Fix (frontend/src/components/graph/GraphFilters.tsx)

```typescript
// Sprint 118: Convert underscores to hyphens for consistent test IDs
data-testid={`edge-filter-${option.value.toLowerCase().replace(/_/g, '-')}`}
```

**Impact:** Edge filter tests now find correct elements.

#### BUG-118.3: Memory Endpoint URL Fix (frontend/e2e/tests/admin/memory-management.spec.ts)

```typescript
// ❌ WRONG (old)
await page.route('**/api/v1/memory/consolidate/status', ...)

// ✅ CORRECT (new)
await page.route('**/api/v1/memory/consolidation/status', ...)
```

**Impact:** Memory consolidation tests now mock the correct endpoint.

#### BUG-118.4: Follow-up Test Timeout Fix (frontend/e2e/utils/retry.ts)

**Root Cause Analysis:**
- Follow-up generation on Nemotron3/DGX Spark takes **20-60 seconds**
- SSE endpoint has 60s max wait time
- Test used `RetryPresets.PATIENT` = 5 retries × 2s = **10 seconds** ❌
- Tests failed immediately because LLM hadn't finished generating

**Fix:** Added new retry preset for LLM-based features:

```typescript
// frontend/e2e/utils/retry.ts
export const RetryPresets = {
  // ...existing presets...

  /**
   * Sprint 118: Follow-up questions retries (30 retries, 2s delay = 60s total)
   * Matches SSE endpoint max_wait_seconds of 60s.
   * Nemotron3 Nano follow-up generation takes 20-60s on DGX Spark.
   */
  FOLLOWUP_QUESTIONS: { maxRetries: 30, retryDelay: 2000, logAttempts: false },
};
```

**Updated Test Files:**
- `frontend/e2e/followup/follow-up-context.spec.ts` - Uses `RetryPresets.FOLLOWUP_QUESTIONS`
- `frontend/e2e/followup/followup.spec.ts` - Uses `FOLLOWUP_TIMEOUT = 60000`

**Key Learning:** Always match test timeout to the slowest component in the chain (LLM generation).

#### BUG-118.5: Missing Follow-up Generation in Non-Streaming API (src/agents/coordinator.py)

**Root Cause Analysis:**
- `process_query()` (non-streaming, line 277) had **NO follow-up generation code**
- `_run_chain()` (streaming, line 831) had the follow-up code: `asyncio.create_task(self._generate_followup_async(...))`
- The non-streaming chat endpoint `/api/v1/chat/` calls `process_query()` → no follow-ups ever generated!
- Log analysis confirmed: `followup_generation_task_started` was NEVER logged for non-streaming requests

**Fix:** Added follow-up generation to `process_query()`:

```python
# Sprint 118 BUG-118.5: Generate follow-up questions asynchronously
# This was missing in the non-streaming path! (only existed in _run_chain)
answer = final_state.get("answer", "")
if not answer:
    messages = final_state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            answer = msg.content
            break

if session_id and answer:
    sources = [ctx for ctx in final_state.get("retrieved_contexts", []) if isinstance(ctx, dict)]
    asyncio.create_task(
        self._generate_followup_async(
            session_id=session_id,
            query=query,
            answer=answer,
            sources=sources,
        )
    )
    logger.info("followup_generation_task_started", session_id=session_id, query_preview=query[:50])
```

**Impact:** Non-streaming API now generates follow-up questions like streaming API.

#### BUG-118.7: FollowUpQuestions Not Integrated into Main Chat UI (frontend/src/components/chat/ConversationView.tsx)

**Root Cause Analysis:**
- `FollowUpQuestions` component was only used in `StreamingAnswer.tsx` (line 328)
- `StreamingAnswer` was only used in `SearchResultsPage.tsx`
- **Main chat interface** (`HomePage.tsx`) uses `ConversationView.tsx` which had NO FollowUpQuestions!
- E2E tests run against HomePage → follow-up questions never rendered

**Fix:** Added `FollowUpQuestions` to `ConversationView.tsx`:

```typescript
// ConversationView.tsx - Added import
import { FollowUpQuestions } from './FollowUpQuestions';

// ConversationView.tsx - Added props
interface ConversationViewProps {
  // ... existing props
  /** Sprint 118: Session ID for follow-up questions */
  sessionId?: string;
  /** Sprint 118: Callback when a follow-up question is clicked */
  onFollowUpQuestion?: (question: string) => void;
}

// ConversationView.tsx - Added render (after typing indicator, before scroll anchor)
{sessionId && !isStreaming && messages.length > 0 && onFollowUpQuestion && (
  <div className="px-6 py-4">
    <FollowUpQuestions
      sessionId={sessionId}
      answerComplete={!isStreaming && messages.length > 0}
      onQuestionClick={onFollowUpQuestion}
    />
  </div>
)}
```

**HomePage.tsx** - Updated to pass new props:

```typescript
<ConversationView
  // ... existing props
  sessionId={activeSessionId}
  onFollowUpQuestion={(question) => {
    // Sprint 118: Handle follow-up question click by submitting as new query
    const graphConfig = loadGraphExpansionConfig();
    handleSearch(question, currentMode, currentNamespaces, graphConfig);
  }}
/>
```

**Impact:** Follow-up questions now appear in the main chat interface after each response.

### Verified Fixes (Sprint 118 - Post Container Rebuild)

| Bug | Test File | Result | Evidence |
|-----|-----------|--------|----------|
| **BUG-118.2** | edge-filters.spec.ts | ✅ VERIFIED | 13/33 tests pass (all Filter Visibility tests) |
| **BUG-118.3** | memory-management.spec.ts | ⚠️ PARTIAL | Mock URL fixed, but auth timeout issues |
| **BUG-118.4** | followup/*.spec.ts | ✅ VERIFIED | All 5 followup.spec.ts tests pass |
| **BUG-118.5** | followup/*.spec.ts | ✅ VERIFIED | Redis shows 5 questions generated for each session |
| **BUG-118.6** | followup/*.spec.ts | ✅ VERIFIED | SSE connects to correct port 8000 |
| **BUG-118.7** | followup/*.spec.ts | ✅ VERIFIED | FollowUpQuestions now renders in main chat UI |

### Test Results (Sprint 118 - Follow-up Questions)

| Test File | Passed | Failed | Notes |
|-----------|--------|--------|-------|
| **followup.spec.ts** | 5/5 | 0 | ✅ **ALL PASS** |
| **follow-up-context.spec.ts** | 8/14 | 6 | Context preservation tests (unrelated to rendering) |

**Follow-up Questions Core Tests (100% pass rate):**
- ✅ should generate 3-5 follow-up questions (7.1s)
- ✅ should display follow-up questions as clickable chips (6.7s)
- ✅ should send follow-up question on click (7.6s)
- ✅ should generate contextual follow-ups (7.2s)
- ✅ should show loading state while generating follow-ups (47.3s)

### Remaining Issues (Sprint 118)

| Issue | Test File | Status | Description |
|-------|-----------|--------|-------------|
| Context Preservation | follow-up-context.spec.ts | 🟡 PARTIAL | 6/14 fail - content/context logic, not rendering |
| Graph Interactions | edge-filters.spec.ts (6-19) | 🟡 EXPECTED | Tests need graph data - not a bug |
| Auth Timeout | memory-management.spec.ts | 🔴 FAILING | setupAuthMocking timeout (3min) |

### Investigation Notes (Follow-up Questions)

**Root Cause Identified (BUG-118.4):**
- SSE endpoint has 60s max wait time ✅
- **But tests only waited 10s** (5 retries × 2s) ❌
- LLM generation takes 20-60s on Nemotron3/DGX Spark
- Fix: Created `RetryPresets.FOLLOWUP_QUESTIONS` (30 retries × 2s = 60s)

**Timeline of Fixes:**
1. BUG-118.1: SSE now checks Redis cache first (avoids 30x LLM calls)
2. BUG-118.4: Test timeout increased from 10s to 60s (matches SSE)

**Next Steps:**
- [x] Added `RetryPresets.FOLLOWUP_QUESTIONS` preset (60s)
- [x] Updated follow-up-context.spec.ts to use new preset
- [x] Updated followup.spec.ts to use 60s timeout
- [x] Verify fix with E2E test run
- [x] BUG-118.5: Added follow-up generation to non-streaming API
- [x] BUG-118.6: Fixed env variable in FollowUpQuestions.tsx
- [x] BUG-118.7: Integrated FollowUpQuestions into ConversationView
- [x] **All 5 followup.spec.ts tests now pass!**

---

## 🆕 Sprint 117/118: Test Categories & Prioritization

### Test Categories (Sprint 118 Feature)

**New Playwright Projects for prioritized test execution:**

| Category | Tests | Files | Priority | Command |
|----------|-------|-------|----------|---------|
| **enduser** | 313 | 23 | ⬆️ HIGH | `npx playwright test --project=enduser` |
| **admin** | 293 | 17 | Normal | `npx playwright test --project=admin` |

**End-User Tests (Higher Priority):**
- `chat/`, `citations/`, `errors/`, `followup/`, `graph/`, `history/`, `ingestion/`, `memory/`
- `smoke.spec.ts`
- `group01-10` (Core user-facing features)

**Admin Tests (Lower Priority):**
- `admin/` directory
- `group11-17` (Admin/config features)

**Usage:**
```bash
# Run high-priority end-user tests first
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --project=enduser

# Then run admin tests
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --project=admin

# Run all tests (default behavior)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test
```

### Sprint 117: Domain Training API Complete ✅

**Date:** 2026-01-20 | **Story Points:** 69 SP | **Features:** 12

Sprint 117 implemented the complete Domain Training API with:
- Domain CRUD Operations (117.1)
- C-LARA Hybrid Classification (117.2)
- Domain Auto-Discovery (117.3)
- Data Augmentation (117.4)
- Batch Ingestion (117.5)
- Training Status/Progress (117.6)
- Domain Validation (117.7)
- Response Format Standardization (117.8)
- Default Domain Seeding (117.9)
- Upload Classification Display (117.10)
- Manual Domain Override (117.11)
- LLM Model Selection per Domain (117.12)

**API Response Format Fix (117.8):**
```typescript
// Frontend hook updated to handle new ApiResponse wrapper
interface ApiResponse<T> {
  success: boolean;
  data: T;
  metadata?: Record<string, unknown>;
}

// useDomains hook handles both formats for backwards compatibility
const domains = Array.isArray(response) ? response : response.data;
```

---

## 🔴 Sprint 114/115: Full E2E Test Suite Results

**Date:** 2026-01-20 | **Duration:** 184 minutes (3+ hours)

### Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Total Tests** | 1099 | - |
| **Passed** | 511 | 46.5% |
| **Failed** | 538 | 49.0% |
| **Skipped** | 50 | 4.5% |
| **Duration** | 184 min | ⚠️ Too long |

### Failure Categorization

| Category | Count | % of Failures | Description |
|----------|-------|---------------|-------------|
| **TIMEOUT (Cat. E)** | 448 | 83.3% | Tests exceed 60s, mostly 120-183s |
| **OTHER** | 48 | 8.9% | Various issues |
| **ASSERTION** | 40 | 7.4% | Test logic failures |
| **API** | 1 | 0.2% | API call failures |
| **SELECTOR** | 1 | 0.2% | Element not found |

### Category E: Long-Running Tests (>60s) - 394 Tests

**Need Backend Tracing to Identify Root Cause:**

| Duration | Test File | Issue Type |
|----------|-----------|------------|
| 183.8s | chat-multi-turn.spec.ts | ⏱️ TIMEOUT |
| 183.6s | chat-multi-turn.spec.ts | ⏱️ TIMEOUT |
| 121.9s | error-handling.spec.ts | ⏱️ TIMEOUT |
| 121.8s | intent.spec.ts | ⏱️ TIMEOUT |
| 121.8s | section-citations.spec.ts | ⏱️ TIMEOUT |
| 121.7s | history.spec.ts | ⏱️ TIMEOUT |
| 121.7s | namespace-isolation.spec.ts | ⏱️ TIMEOUT |

**Investigation Required:**
- Distinguish between actual long-running LLM calls vs bug-induced delays
- Full backend trace needed for each Category E test
- Potential mock infrastructure for CI/CD speed

### Top 20 Failing Test Files

| Rank | File | Failures | Category |
|------|------|----------|----------|
| 1 | test_domain_training_flow.spec.ts | 26 | UI/Timeout |
| 2 | pipeline-progress.spec.ts | 25 | SSE/UI |
| 3 | conversation-ui.spec.ts | 21 | LLM Timeout |
| 4 | structured-output.spec.ts | 20 | UI |
| 5 | graph-visualization.spec.ts | 19 | Graph UI |
| 6 | error-handling.spec.ts | 17 | Error UI |
| 7 | tool-output-viz.spec.ts | 16 | UI |
| 8 | edge-filters.spec.ts | 15 | Graph UI |
| 9 | group19-llm-config.spec.ts | 15 | Config |
| 10 | multi-turn-rag.spec.ts | 15 | LLM Timeout |
| 11 | intent.spec.ts | 15 | Intent |
| 12 | search.spec.ts | 14 | Search |
| 13 | memory-management.spec.ts | 14 | Admin UI |
| 14 | vlm-integration.spec.ts | 13 | VLM |
| 15 | test_domain_upload_integration.spec.ts | 12 | Upload |
| 16 | single-document-test.spec.ts | 12 | Ingestion |
| 17 | graph-visualization.spec.ts | 12 | Graph UI |
| 18 | namespace-isolation.spec.ts | 11 | Namespace |
| 19 | graph-communities.spec.ts | 11 | Graph |
| 20 | conversation-search.spec.ts | 11 | Search |

---

## ✅ Sprint 114: E2E Test Stabilization Phase 2 (COMPLETED)

**Sprint Plan:** [docs/sprints/SPRINT_114_PLAN.md](../sprints/SPRINT_114_PLAN.md)

### New Patterns Discovered (Sprint 114)

#### P-006: Hardcoded URL Pattern

**Problem:** Tests hardcode `http://localhost:5179` but tests run against Docker at `http://192.168.178.10`

```typescript
// ❌ WRONG - Hardcoded URL
expect(url).toContain('http://localhost:5179');

// ✅ CORRECT - Use environment variable
const expectedBase = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5179';
expect(url).toContain(expectedBase.replace(/\/$/, ''));
```

#### P-007: MIME Type vs Extension Pattern

**Problem:** Tests expect MIME types (`text/plain`) but UI uses file extensions (`.txt`)

```typescript
// ❌ WRONG - Expects MIME type
expect(acceptAttr).toContain('text/plain');

// ✅ CORRECT - Check for extension OR MIME type
const acceptsTxt = acceptAttr?.includes('.txt') || acceptAttr?.includes('text/plain');
expect(acceptsTxt).toBeTruthy();
```

#### P-008: Auth Timeout Pattern

**Problem:** Auth setup timeout (30s) too short when Ollama is warming up

```typescript
// ❌ WRONG - 30s timeout
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 30000 });

// ✅ CORRECT - 60s timeout for slow auth scenarios
await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 60000 });
```

**Location:** `e2e/fixtures/index.ts:78`

#### P-009: Wrong Element Type Pattern

**Problem:** `setInputFiles()` called on `<div>` drag-drop area instead of `<input type="file">`

```typescript
// ❌ WRONG - setInputFiles on div element
const uploadArea = page.locator('[data-testid="domain-discovery-upload-area"]');
await uploadArea.setInputFiles({ ... });  // Error: Node is not an HTMLInputElement

// ✅ CORRECT - Use actual file input element
const fileInput = page.locator('[data-testid="domain-discovery-file-input"]');
await fileInput.setInputFiles({ ... });
```

### Test Results (After Sprint 114 Fixes)

| Test Suite | Passed | Skipped | Pass Rate |
|------------|--------|---------|-----------|
| Smoke Tests | 12 | 0 | **100%** ✅ |
| Domain Training API | 0 | 31 | **(Skipped)** |
| Admin Dashboard | 14 | 1 | **100%** ✅ |

### Category B: Skipped Tests (Missing Features)

| Feature | Test File | Tests | Reason |
|---------|-----------|-------|--------|
| Domain Training API | test_domain_training_api.spec.ts | 31 | `/api/v1/admin/domains/` returns 404 |
| Admin Domain Stats | admin-dashboard.spec.ts:338 | 1 | TC-46.8.9 depends on unimplemented stats |

---

## ✅ Sprint 113 Feature 113.0: Graph Search Early-Exit Fix (COMPLETED)

**Fix Applied:** 2026-01-19 | **ADR:** [ADR-056](../adr/ADR-056-graph-search-early-exit.md)

### Performance Improvement

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Graph Search (empty NS)** | 13,376ms | 6.8ms | **-99.9%** |
| **Hybrid API (empty NS)** | 13.77s | 16ms | **-99.9%** |

### Test Results After Fix

| Test Suite | Passed | Failed | Pass Rate |
|------------|--------|--------|-----------|
| Smoke Tests | 11 | 1 | **91.7%** |
| ReasoningPanel | 10 | 2 | **83.3%** |
| ConversationUI | 11 | 2 | **84.6%** |
| Chat Interface | 2 | 0 | **100%** |

### Bugs Fixed (Sprint 113)

| Bug | Test | Issue | Fix |
|-----|------|-------|-----|
| ✅ BUG-113.1 | TC-46.2.2 | Test didn't handle `defaultExpanded=true` | Test now checks initial state |
| ✅ BUG-113.2 | TC-46.2.3 | Same (depends on 113.1) | Same fix applied |
| ✅ BUG-113.3 | TC-46.1.5 | Test expected `flex-shrink-0` but component uses `absolute` | Updated test to check `absolute bottom-0` |
| ✅ BUG-113.4 | TC-46.1.9 | Race condition - message count checked too early | Added explicit `toHaveCount()` wait |

### Pattern Fixes Applied (Preventive)

Added `toHaveCount()` timeouts to prevent race conditions:

| File | Lines Fixed | Original | Fixed |
|------|-------------|----------|-------|
| `entity-changelog.spec.ts` | 95, 170, 178, 262 | `toHaveCount(n)` | `toHaveCount(n, { timeout: 10000-15000 })` |
| `version-compare.spec.ts` | 139, 197, 200 | `toHaveCount(n)` | `toHaveCount(n, { timeout: 10000 })` |
| `memory-management.spec.ts` | 416 | `toHaveCount(n)` | `toHaveCount(n, { timeout: 10000 })` |

**Note:** These tests currently fail due to **missing UI components**, not the pattern fix. The timeout fix is preventive.

### Updated Test Results (2026-01-19 Post Bug Fixes)

| Test Suite | Passed | Failed | Pass Rate | Notes |
|------------|--------|--------|-----------|-------|
| **TC-46.x (ConversationUI + ReasoningPanel)** | 25 | 0 | **100%** | All bugs fixed! |
| entity-changelog.spec.ts | 0 | 9 | 0% | Missing Component |
| version-compare.spec.ts | 0 | 10 | 0% | Missing Component |
| memory-management.spec.ts | 1 | 14 | 7% | Missing data-testids |

### Test Failure Classification

| Category | Count | Root Cause | Fix Location |
|----------|-------|------------|--------------|
| **Test Pattern Bugs** | 4 | Race conditions, state assumptions, CSS changes | Tests (FIXED ✅) |
| **Missing UI Components** | 19+ | Features not implemented (39.5, 39.6, 39.7) | Frontend Components |
| **Missing data-testids** | 14+ | Components exist but lack test attributes | Frontend Components |
| **LLM Timeouts** | 300+ | Ollama response time 11-15min | Feature 113.1 |

### Remaining Issues

| Issue | Test | Description |
|-------|------|-------------|
| Missing EntityChangelogPanel | entity-changelog.spec.ts | Feature 39.6 never implemented |
| Missing VersionCompare | version-compare.spec.ts | Feature 39.7 never implemented |
| Missing data-testids | memory-management.spec.ts | MemoryManagementPage needs data-testids |
| LLM Timeout | Various | Intermittent timeout waiting for LLM response (>150s) |

---

## ⚠️ Sprint 113 Original Finding: LLM Response Time Crisis

**Full Test Suite Run (2026-01-19 BEFORE Fix):**
| Metric | Value | Status |
|--------|-------|--------|
| **Total Tests** | 1099 | - |
| **Passed** | 538 | 49% |
| **Failed** | 544 | 50% |
| **Skipped** | 17 | 1% |
| **Duration** | 3.1 hours | - |

**Root Cause Analysis:**
- **60% of failures** (328 tests) due to LLM response timeout
- **Ollama `/api/chat` takes 11-15 MINUTES** (expected: <60s)
- Tests timeout at 11-30 seconds, LLM responds after 660-890s
- Nemotron 3 Nano 30B model is slow on DGX Spark (cold requests)
- **FIXED:** Graph Search Early-Exit now skips LLM calls for empty namespaces

**Sprint 113 Plan:** [docs/sprints/SPRINT_113_PLAN.md](../sprints/SPRINT_113_PLAN.md) - 108 SP across 10 features

---

## Quick Start

```bash
# Navigate to frontend directory
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Run high-priority end-user tests first (Sprint 118)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --project=enduser --reporter=list

# Run admin tests (lower priority)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --project=admin --reporter=list

# Run all tests against production Docker container
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list

# Run specific group
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test e2e/group09-long-context.spec.ts --reporter=list

# Run domain-related tests only
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --grep "domain" --reporter=list

# Run with parallel workers
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --workers=3 --reporter=list
```

---

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Total Test Files** | 59 spec files | - |
| **Total Tests** | 1099 tests | - |
| **Full Suite Pass Rate** | 538/1099 (49%) | ⚠️ Sprint 113 |
| **Primary Issue** | LLM Timeout (60% of failures) | 🔴 P0 |
| **Sprint 111 Groups** | Groups 01-03, 09, 13-17 | ✅ 118/118 |
| **Sprint 113 Target** | ≥85% pass rate | 🎯 Planned |

### Sprint 111 Verified Groups (Still Passing)

| Metric | Value | Status |
|--------|-------|--------|
| **Groups 01-03** | Auth Pattern Fixed | ✅ 46/46 (100%) |
| **Group 09** | Long Context UI | ✅ 23/23 (100%) |
| **Groups 13-16** | Enterprise Features | ✅ 41/41 (100%) |
| **Group 17** | Token Usage Chart | ✅ 8/8 (100%) |

---

## Sprint 113 Failure Analysis (2026-01-19)

### Failure Categories

| Category | Count | % of Failures | Root Cause |
|----------|-------|---------------|------------|
| **LLM Response Timeout** | 328 | 60% | Ollama 11-15min response vs 11-30s test timeout |
| **UI Element Not Found** | 112 | 21% | Missing data-testids, late rendering |
| **API Errors** | 62 | 11% | Unexpected error responses |
| **Other** | 42 | 8% | Various issues |

### Top Failing Test Files

| File | Failures | Category | Priority |
|------|----------|----------|----------|
| conversation-ui.spec.ts | 26 | LLM Timeout | P0 |
| test_domain_training_flow.spec.ts | 26 | UI/Timeout | P1 |
| pipeline-progress.spec.ts | 22 | SSE/UI | P1 |
| error-handling.spec.ts | 21 | Error UI | P2 |
| test_domain_training_api.spec.ts | 21 | API | P1 |
| structured-output.spec.ts | 20 | UI | P2 |
| graph-visualization.spec.ts | 19+12 | Graph UI | P2 |
| tool-output-viz.spec.ts | 16 | UI | P2 |
| search.spec.ts | 15 | Search | P1 |
| intent.spec.ts | 15 | Intent | P1 |
| multi-turn-rag.spec.ts | 15 | LLM Timeout | P0 |
| memory-management.spec.ts | 14 | Admin UI | P2 |
| vlm-integration.spec.ts | 14 | VLM | P2 |
| research-mode.spec.ts | 12 | LLM Timeout | P0 |
| single-document-test.spec.ts | 12 | Ingestion | P1 |
| group19-llm-config.spec.ts | 12 | Config | P2 |

### Sprint 113 Fix Plan

See **[SPRINT_113_PLAN.md](../sprints/SPRINT_113_PLAN.md)** for detailed fix plan (108 SP):

| Feature | Story Points | Priority | Impact |
|---------|--------------|----------|--------|
| 113.1 LLM Performance | 20 SP | P0 | 328 tests (60%) |
| 113.2 Chat UI Tests | 15 SP | P0 | 26 tests |
| 113.3 Domain Training | 12 SP | P1 | 47+ tests |
| 113.4 Graph Visualization | 15 SP | P2 | 31+ tests |
| 113.5 Pipeline/Admin UI | 10 SP | P1 | 36+ tests |
| 113.6 Search/Intent | 8 SP | P1 | 30+ tests |
| 113.7 Error/Structured | 10 SP | P2 | 41+ tests |
| 113.8 Mock Infrastructure | 8 SP | P0 | Cross-cutting |
| 113.9 Timeout Config | 5 SP | P1 | Cross-cutting |
| 113.10 CI/CD Updates | 5 SP | P2 | Automation |

---

## Test Groups Status Overview

### Sprint 109 - COMPLETE ✅ (Groups 04-08, 10-12)

| Group | Feature | Tests | Pass Rate | Notes |
|-------|---------|-------|-----------|-------|
| **04** | Browser Tools | 6 | **100%** (6/6) | Auth + API mocks fixed |
| **05** | Skills Management | 8 | **100%** (8/8) | API format + selectors fixed |
| **06** | Skills Using Tools | 9 | **DEFERRED** | Requires chat integration |
| **07** | Memory Management | 15 | **100%** (15/15) | Auth + strict mode fixed |
| **08** | Deep Research | 11 | **90.9%** (10/11) | 1 intentional skip |
| **10** | Hybrid Search | 13 | **100%** (13/13) | Already passing |
| **11** | Document Upload | 15 | **100%** (15/15) | Already passing |
| **12** | Graph Communities | 16 | **93.75%** (15/16) | 1 intentional skip |

### Sprint 111 - E2E Fixes COMPLETE ✅ (Groups 13-16)

| Group | Feature | Tests | Pass Rate | Notes |
|-------|---------|-------|-----------|-------|
| **13** | Agent Hierarchy | 8 | **100%** (8/8) | Zoom controls aria-labels, skills badges D3 format |
| **14** | GDPR & Audit | 14 | **100%** (14/14) | Pagination controls, rights description, audit events |
| **15** | Explainability | 13 | **100%** (13/13) | Model info section, audit trail link, decision paths |
| **16** | MCP Marketplace | 6 | **100%** (6/6) | data-testid fix |

### Sprint 111 - COMPLETE ✅ (Groups 01-03, 09, 17)

| Group | Feature | Tests | Pass Rate | Notes |
|-------|---------|-------|-----------|-------|
| **01** | MCP Tools | 16 | **100%** (16/16) | Auth pattern fixed |
| **02** | Bash Execution | 15 | **100%** (15/15) | Command sandbox |
| **03** | Python Execution | 15 | **100%** (15/15) | Code execution |
| **09** | Long Context | 23 | **100%** (23/23) | Large document handling (Feature 111.1) |
| **17** | Token Usage Chart | 8 | **100%** (8/8) | Cost dashboard chart (Feature 111.2) |

---

## Sprint 109 Execution Summary ✅

### Phase 1: Browser Tools ✅
- Fixed tool execution endpoint mocks (`/api/v1/mcp/tools/{toolName}/execute`)
- Added auth setup (setupAuthMocking + navigateClientSide)
- All 6 tests passing (100%)

### Phase 2: Memory & Research ✅
- Group 07: Memory Management - 15/15 tests (100%)
- Group 08: Deep Research - 10/11 tests (90.9%)
- Fixed auth setup, resolved Playwright strict mode violations

### Phase 3: Core RAG Features ✅
- Group 10: Hybrid Search - 13/13 tests (100%)
- Group 11: Document Upload - 15/15 tests (100%)
- Group 12: Graph Communities - 15/16 tests (93.75%)

**Sprint 109 Total:** 82/83 tests passing (98.8%)

---

## Sprint 111 Execution Summary (Groups 13-16) ✅

### Feature 111.0: E2E Test Fixes

**Date:** 2026-01-18
**Result:** 41/41 tests passing (100%)

#### Group 13: Agent Hierarchy (8/8)
- Fixed zoom controls aria-labels (lowercase)
- Fixed skills badges D3 format in mock data

**Files Modified:**
- `AgentHierarchyD3.tsx`: Lowercase aria-labels for zoom controls
- `group13-agent-hierarchy.spec.ts`: Fixed skills test mock format

#### Group 14: GDPR & Audit (14/14)
- Added pagination controls (10 items/page) in ConsentRegistry
- Added rights description text in DataSubjectRights
- Fixed audit events mock with complete fields

**Files Modified:**
- `ConsentRegistry.tsx`: Client-side pagination (ITEMS_PER_PAGE = 10)
- `DataSubjectRights.tsx`: Added rights description section
- `group14-gdpr-audit.spec.ts`: Fixed mocks (25 consents for pagination, complete audit event fields)

#### Group 15: Explainability (13/13)
- Added model info section with data-testid
- Added audit trail link to /admin/audit
- Fixed API endpoint mocks (use /recent instead of /decision-paths)

**Files Modified:**
- `ExplainabilityPage.tsx`: Model info section, audit trail link, decision-path testid
- `group15-explainability.spec.ts`: Fixed endpoint mocks, CSS selector parsing

#### Group 16: MCP Marketplace (6/6)
- Changed data-testid to `mcp-server-browser`

**Files Modified:**
- `MCPServerBrowser.tsx`: Fixed data-testid attribute

---

## Sprint 111 Feature Implementation Summary ✅

### Feature 111.1: Long Context UI (10 SP)

**Date:** 2026-01-18
**Result:** 23/23 tests passing (100%)

#### New Components Created
- `ContextWindowIndicator.tsx` - Visual gauge for context usage (0-100%)
- `ChunkExplorer.tsx` - Interactive chunk navigation with search
- `RelevanceScoreDisplay.tsx` - Score visualization with distribution
- `ContextCompressionPanel.tsx` - Compression strategy selector
- `LongContextPage.tsx` - Admin page at `/admin/long-context`

#### Test Coverage (Group 09)
- Large document upload and processing
- Context window indicators (current/max tokens)
- Chunk preview with navigation
- Relevance score visualization
- Long context search functionality
- Context compression strategies
- Multi-document context merging
- Context overflow handling
- Quality metrics display
- Context export (JSON/Markdown)

### Feature 111.2: Token Usage Chart (8 SP)

**Date:** 2026-01-18
**Result:** 8/8 tests passing (100%)

#### New Components Created
- `TimeRangeSlider.tsx` - Time range with presets (1d-3y)
- `ChartControls.tsx` - Aggregation/provider/scale controls
- `TokenUsageChart.tsx` - Main chart with Recharts

#### Integration
- Added to `CostDashboardPage.tsx`
- Uses Recharts library (AreaChart, ResponsiveContainer)
- Fetches from `/api/v1/admin/costs/timeseries`

#### Test Coverage (Group 17)
- Chart renders with data
- Slider changes time range
- Provider filter works
- Aggregation toggle (daily/weekly/monthly)
- Empty state handling
- Loading state display
- Error state handling
- Export chart as PNG

### Groups 01-03: Auth Pattern Fix

**Date:** 2026-01-18
**Result:** 46/46 tests passing (100%)

Tests already had proper auth setup but needed Docker container rebuild for latest frontend code.

---

## Working Test Pattern (Reference) ⭐

**Group 03 Python Execution** and **Group 05 Skills Management** achieve **100% pass rates** and should be used as reference patterns.

### Key Pattern Elements

```typescript
import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';

const MCP_TOOLS_URL = '/admin/tools';

test.describe('Feature Tests', () => {
  // 1. Setup auth and ALL mocks in beforeEach
  test.beforeEach(async ({ page }) => {
    // Setup auth first
    await setupAuthMocking(page);

    // Setup ALL API mocks with proper data
    await page.route('**/api/v1/mcp/servers', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([mockServer]),
      });
    });

    await page.route('**/api/v1/mcp/tools', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockTools),
      });
    });
  });

  // 2. Tests use navigateClientSide for reliable navigation
  test('should execute action', async ({ page }) => {
    // Test-specific execution mock
    await page.route('**/api/v1/mcp/tools/tool_name/execute', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, result: { ... } }),
      });
    });

    // Navigate using client-side routing
    await navigateClientSide(page, MCP_TOOLS_URL);
    await page.waitForLoadState('networkidle');

    // 3. Use scoped selectors for clarity
    const tool = page.locator('[data-testid="tool-name"]');
    await tool.click();

    // 4. Wait for result with explicit timeout
    await expect(page.locator('text=/expected/i')).toBeVisible({ timeout: 5000 });
  });
});
```

### Why This Pattern Works

1. **Comprehensive beforeEach mocking:** All common API routes mocked upfront
2. **navigateClientSide():** More reliable than page.goto() for React Router
3. **Explicit waits:** `waitForLoadState('networkidle')` ensures page is ready
4. **Scoped selectors:** Clear, unambiguous element selection
5. **Proper timeout handling:** Explicit timeouts for async operations
6. **Realistic mock data:** Mock responses match actual backend structure

---

## API Contract-First Development (Sprint 112+)

### Best Practice: OpenAPI Specification First

**Before implementing frontend features with new API calls:**

1. **Define OpenAPI spec** in `docs/api/openapi/`
2. **Implement backend** endpoints matching spec
3. **Generate TypeScript types** from spec (optional)
4. **Implement frontend** using real APIs
5. **E2E tests** validate against real responses

**OpenAPI Specs:**
- `docs/api/openapi/context-api.yaml` - Long Context API (Sprint 112)

### Anti-Pattern: Demo Data Fallbacks

**❌ Don't:** Use catch blocks to generate fake data
```typescript
// BAD - Masks missing APIs, E2E tests pass but API doesn't exist!
} catch (err) {
  console.error('API Error:', err);
  setData(generateDemoData()); // Tests pass with fake data
}
```

**✅ Do:** Fail explicitly, fix the API
```typescript
// GOOD - Surfaces missing APIs, forces implementation
} catch (err) {
  setError(`API Error: ${err.message}`);
  // E2E test will fail, prompting API implementation
}
```

### Contract Validation Strategy

Use Playwright API mocking **only** for:
- ❌ Network error simulation (500, 503, timeout)
- ❌ Edge case testing (empty responses, malformed data)
- ❌ Rate limiting scenarios

For happy-path tests, **prefer real API calls**:
```typescript
// ✅ Happy path - use real API (no mocking)
test('should load real documents', async ({ page }) => {
  await navigateClientSide(page, '/admin/long-context');
  // Data comes from actual Qdrant + ingested Sprint docs
  await expect(page.locator('text=SPRINT_111_PLAN.md')).toBeVisible();
});

// ✅ Error path - use mocking
test('should handle API error', async ({ page }) => {
  await page.route('**/api/v1/context/documents', (route) => {
    route.fulfill({ status: 500, body: JSON.stringify({ detail: 'Server error' }) });
  });
  await navigateClientSide(page, '/admin/long-context');
  await expect(page.locator('[data-testid="error-banner"]')).toBeVisible();
});
```

### Real Test Data Strategy

**Problem:** E2E tests with mocked data don't validate real integration.

**Solution:** Use actual project documents as test data:

```bash
# Index Sprint Plan documents into Qdrant
python scripts/ingest_sprint_docs.py --namespace sprint_docs
```

**Benefits:**
- Tests validate real API responses
- Known content allows specific assertions
- Documents grow with project (22 files, ~275K tokens)

**Example assertion on real data:**
```typescript
test('should show indexed Sprint 111', async ({ page }) => {
  // No mocking - real API call
  await navigateClientSide(page, '/admin/long-context');

  // Assert on actual indexed document
  const doc = page.locator('[data-testid^="document-item-"]', {
    hasText: 'SPRINT_111_PLAN.md'
  });
  await expect(doc).toBeVisible();
  await expect(doc.locator('text=/tokens/')).toBeVisible();
});
```

---

## Common Issues & Fixes

### Issue 1: API Response Format Mismatch

**Example:** Skills returned array instead of `SkillListResponse` object

**Fix:** Update mock to match TypeScript interface:
```typescript
// ❌ Wrong
body: JSON.stringify([skill1, skill2])

// ✅ Correct
body: JSON.stringify({
  items: [skill1, skill2],
  total: 2,
  page: 1,
  page_size: 12,
  total_pages: 1
})
```

### Issue 2: Selector Specificity

**Example:** `text=/Active/i` matched dropdown AND badges

**Fix:** Scope selector to specific container:
```typescript
// ❌ Too broad
page.locator('text=/Active/i')

// ✅ Scoped
page.locator('[data-testid^="skill-card-"]').locator('text=/Active/i')
```

### Issue 3: React Router Navigation Unreliable

**Example:** Config editor navigation via link click failed

**Fix:** Use direct navigation:
```typescript
// ❌ Indirect
await page.locator('[data-testid="skill-edit-link"]').click();

// ✅ Direct
await navigateClientSide(page, '/admin/skills/web_search/config');
```

### Issue 4: Missing data-testid Attributes

**Example:** Error message had no testid

**Fix:** Add data-testid to component:
```typescript
<div data-testid="save-error" className="bg-red-50...">
  <p>{error}</p>
</div>
```

### Issue 5: TypeScript Import Errors at Runtime

**Symptom:** `The requested module does not provide an export named 'InterfaceName'`

**Solution:**
1. Create `types/*.ts` file for shared interfaces
2. Move interface to types file
3. Update imports to `import type { InterfaceName }`

---

## E2E Testing Best Practices

### Critical Rules

1. **Always verify backend APIs first** before assuming missing endpoints
   - Sprint 108: ALL backend APIs were correct, failures were frontend issues

2. **Rebuild Docker containers after code changes**
   ```bash
   cd /home/admin/projects/aegisrag/AEGIS_Rag
   docker compose -f docker-compose.dgx-spark.yml build --no-cache frontend
   docker compose -f docker-compose.dgx-spark.yml build --no-cache api
   docker compose -f docker-compose.dgx-spark.yml up -d
   ```

3. **TypeScript type safety**
   - Never export interfaces from component files (runtime code)
   - Use dedicated `types/*.ts` files for shared type definitions
   - Use `import type { }` syntax for type-only imports

4. **E2E timing tolerances**
   - Add 50-100% overhead for E2E tests vs API-only tests
   - Network latency, UI rendering, DOM mutations all add time
   - Example: API responds in 5s → E2E test needs 8-15s timeout

5. **Selector strategies**
   - Use scoped selectors: `parent.getByTestId('child')`
   - Avoid global selectors when multiple elements exist

6. **Mock API graceful fallbacks**
   - Components may cache data and skip redundant API calls
   - Don't require API mock to be called - make it optional

7. **Hidden file inputs**
   - Custom upload UIs hide native file inputs
   - Use `.count()` to check DOM existence, not `.toBeVisible()`

8. **Playwright buffer limits**
   - File operations have 50MB buffer limit
   - Test with smaller file sizes (10-20MB instead of 60MB)

---

## Test Execution Workflow

### Standard Test Run

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Full test suite (~15-20 minutes)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list

# Specific group
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test e2e/group07-memory-management.spec.ts --reporter=list

# Parallel execution (3 workers, faster)
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --workers=3 --reporter=list

# Save results to file
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test --reporter=list 2>&1 | tee test-results/results-$(date +%Y%m%d-%H%M%S).log
```

### After Test Run - Documentation Update

1. **Update this file (PLAYWRIGHT_E2E.md):**
   - Update "Test Groups Status Overview" table
   - Add new bugs/fixes to sprint section
   - Update remaining issues

2. **Update Sprint Plan:**
   - Document test-related tasks in `docs/sprints/SPRINT_XXX_PLAN.md`

---

## File Organization

### Test Files Location

```
frontend/e2e/
├── group01-mcp-tools.spec.ts           # MCP Tools Management
├── group02-bash-execution.spec.ts      # Bash Tool Execution
├── group03-python-execution.spec.ts    # Python Tool (⭐ Reference)
├── group04-browser-tools.spec.ts       # Browser MCP Tools
├── group05-skills-management.spec.ts   # Skills Management (⭐ Reference)
├── group06-skills-using-tools.spec.ts  # Skills Using Tools (deferred)
├── group07-memory-management.spec.ts   # Memory Management
├── group08-deep-research.spec.ts       # Deep Research Mode
├── group09-long-context.spec.ts        # Long Context (Sprint 111)
├── group10-hybrid-search.spec.ts       # BGE-M3 Hybrid Search
├── group11-document-upload.spec.ts     # Document Upload
├── group12-graph-communities.spec.ts   # Graph Communities
├── group13-agent-hierarchy.spec.ts     # Agent Hierarchy
├── group14-gdpr-audit.spec.ts          # GDPR/Audit
├── group15-explainability.spec.ts      # Explainability
├── group16-mcp-marketplace.spec.ts     # MCP Marketplace
├── group17-token-usage-chart.spec.ts   # Token Usage Chart (Sprint 111)
└── fixtures/index.ts                   # Shared test utilities
```

### Documentation Location

```
docs/e2e/
├── PLAYWRIGHT_E2E.md                   # THIS FILE (authoritative guide)
├── TESTING_PATTERNS.md                 # Test patterns & best practices
├── USER_JOURNEYS_AND_TEST_PLAN.md      # User journey definitions
├── TOOL_FRAMEWORK_USER_JOURNEY.md      # Tool framework journeys
└── archive/                            # Archived/outdated documents
```

---

## Test Group Descriptions

### Group 01-03: Tool Execution
- **MCP Tools:** Server connection, tool discovery, execution
- **Bash Execution:** Command sandbox, security validation
- **Python Execution:** Code execution, AST validation

### Group 04-06: Skills & Tools
- **Browser Tools:** Browser automation via MCP
- **Skills Management:** Registry, config editor, lifecycle
- **Skills Using Tools:** Chat + skill invocation (requires integration)

### Group 07-08: Memory & Research
- **Memory Management:** 3-layer stats, search, consolidation
- **Deep Research:** Multi-step research, progress tracking

### Group 09: Long Context (Sprint 111)
- Large document handling (>100K tokens)
- Context window management UI
- Document chunking visualization
- Context relevance scoring

### Group 10-12: Core RAG
- **Hybrid Search:** Vector + Graph + Sparse search
- **Document Upload:** Upload, processing, management
- **Graph Communities:** Community detection, visualization

### Group 13-16: Enterprise
- **Agent Hierarchy:** Executive→Manager→Worker visualization
- **GDPR & Audit:** Consent management, audit trails
- **Explainability:** Decision traces, source attribution
- **MCP Marketplace:** Server discovery, installation

### Group 17: Cost Analytics (Sprint 111)
- **Token Usage Chart:** Time series visualization with Recharts
- Time range slider (1d-3y) with logarithmic scale
- Provider filtering, aggregation controls (daily/weekly/monthly)
- Export chart as PNG functionality

---

## Success Metrics

### Sprint 113 Full Suite Run (2026-01-19)

| Metric | Tests | Status |
|--------|-------|--------|
| **Total Tests** | 1099 | - |
| **Passed** | 538 | 49% ⚠️ |
| **Failed** | 544 | 50% |
| **Skipped** | 17 | 1% |

### Sprint 111 Groups (Still Verified)

| Group | Tests | Status |
|-------|-------|--------|
| Groups 01-03 | 46/46 | ✅ 100% |
| Group 09 Long Context | 23/23 | ✅ 100% |
| Groups 13-16 | 41/41 | ✅ 100% |
| Group 17 Token Chart | 8/8 | ✅ 100% |
| **Sprint 111 Total** | **118/118** | **✅ 100%** |

### Sprint 113 Target Goals

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **Overall Pass Rate** | 49% | ≥85% | +36% |
| **Critical Path (Chat/Search/Admin)** | ~40% | ≥95% | +55% |
| **Test Duration** | 3.1h | <30min fast / <2h full | - |
| **LLM Response Time** | 11-15min | <60s (mock: <500ms) | - |

### End Goal (Sprint 113)
- All critical paths: >95% pass rate
- Overall: >85% pass rate (935+ of 1099 tests)
- Mock LLM for non-integration tests
- Test suite tiers: fast (10min), integration (30min), full (2h)

---

## Related Documentation

- **Sprint Plans:** `docs/sprints/SPRINT_XXX_PLAN.md`
- **CLAUDE.md:** E2E Testing Strategy section
- **Testing Patterns:** `docs/e2e/TESTING_PATTERNS.md`
- **User Journeys:** `docs/e2e/USER_JOURNEYS_AND_TEST_PLAN.md`
- **Archive:** `docs/e2e/archive/` - Outdated E2E documentation

---

**Last Test Run:** 2026-01-21 (Sprint 117 End-User Tests: In Progress)
**Test Categories:** enduser (313 tests, HIGH priority) | admin (293 tests, Normal priority)
**Critical Finding:** LLM Response Timeout (60% of failures) - Ollama takes 11-15min per request
**Sprint 117 Complete:** Domain Training API with 12 features (69 SP)
**Sprint 118 In Progress:** Test Categories, Visual Regression, Performance Tests
**Target:** ≥85% pass rate (935+ tests passing)
**Maintained By:** Claude Code + Sprint Team
