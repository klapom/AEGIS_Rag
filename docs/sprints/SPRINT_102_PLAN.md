# Sprint 102 Plan: Complete E2E Production Validation

**Sprint Duration:** 2026-01-15 → 2026-01-16 (Overnight)
**Total Story Points:** 45 SP
**Priority:** P0 (Production Readiness)
**Status:** 📝 In Progress

---

## Sprint Goal

**Complete Playwright E2E testing of ALL features (except RAGAS & Domain Training) grouped by functional area. Fix issues, document results. Goal: Production readiness validation.**

---

## Scope

### ✅ In Scope (15 Functional Groups)

1. **MCP Tool Management** - Tool Registry, Permissions, Enable/Disable
2. **Bash Tool Execution** - Docker sandbox, security validation
3. **Python Tool Execution** - AST validation, code execution
4. **Browser Tools** - Playwright MCP (navigate, click, screenshot)
5. **Skills Management** - Registry, Config Editor, YAML validation
6. **Skills Using Tools** - Skills invoke MCP tools end-to-end
7. **Memory Management** - Redis, Graphiti, 3-Layer, Clear/Export
8. **Deep Research Mode** - Multi-step, LangGraph, tool integration
9. **Long Context Features** - Recursive LLM, Adaptive Scoring (Sprint 90/91/92)
10. **Hybrid Search** - BGE-M3 Dense+Sparse, RRF fusion
11. **Document Upload** - Fast upload, 3-Rank Cascade, Gleaning
12. **Graph Communities** - Summarization, API, UI
13. **Agent Hierarchy** - Tree, status, details, performance
14. **GDPR/Audit** - Consents, Events, Reports, PII Settings
15. **Explainability/Certification** - Decision paths, transparency

### ❌ Out of Scope

- RAGAS Evaluation (deferred)
- Domain Training (deferred)

---

## Features

### Group 1: MCP Tool Management (3 SP)

**E2E Test Coverage:**
- Tool Registry page loads
- List all available tools (bash, python, browser, etc.)
- Tool permissions display
- Enable/Disable tool toggle
- Tool configuration modal

**Acceptance Criteria:**
- ✅ All tools visible in registry
- ✅ Permissions correctly displayed
- ✅ Enable/Disable functional
- ✅ No API errors

---

### Group 2: Bash Tool Execution (3 SP)

**E2E Test Coverage:**
- Execute simple bash command (echo, ls, pwd)
- Security validation (blocked commands)
- Docker sandbox isolation
- Output capture and display
- Error handling (timeout, invalid command)

**Acceptance Criteria:**
- ✅ Commands execute successfully
- ✅ Dangerous commands blocked
- ✅ Output displayed correctly
- ✅ Timeouts handled gracefully

---

### Group 3: Python Tool Execution (3 SP)

**E2E Test Coverage:**
- Execute simple Python code (print, math)
- AST validation (blocked imports)
- Restricted globals enforcement
- Output capture and display
- Error handling (syntax errors, timeouts)

**Acceptance Criteria:**
- ✅ Code executes successfully
- ✅ Dangerous imports blocked
- ✅ Output displayed correctly
- ✅ Errors handled gracefully

---

### Group 4: Browser Tools (3 SP)

**E2E Test Coverage:**
- Navigate to URL
- Click element
- Take screenshot
- Evaluate JavaScript
- Handle dialogs

**Acceptance Criteria:**
- ✅ All browser actions functional
- ✅ Screenshots captured
- ✅ JS evaluation works
- ✅ Error handling robust

---

### Group 5: Skills Management (3 SP)

**E2E Test Coverage:**
- Skills Registry loads
- List all skills (5 skills expected)
- Skill config editor opens
- YAML validation (valid/invalid)
- Enable/Disable skill
- Save configuration

**Acceptance Criteria:**
- ✅ All skills visible
- ✅ Config editor functional
- ✅ YAML validation works (Sprint 100 Fix #8)
- ✅ Enable/Disable toggle works

---

### Group 6: Skills Using Tools (4 SP)

**E2E Test Coverage:**
- Skill invokes bash tool
- Skill invokes python tool
- Skill invokes browser tool
- End-to-end flow from skill → tool → result
- Error handling when tool fails

**Acceptance Criteria:**
- ✅ Skills can invoke all tool types
- ✅ Tool results returned to skill
- ✅ Errors propagated correctly
- ✅ Full trace visible in logs

---

### Group 7: Memory Management (3 SP)

**E2E Test Coverage:**
- Memory Management page loads
- View Redis memory
- View Graphiti memory
- 3-Layer memory display
- Clear memory function
- Export memory function

**Acceptance Criteria:**
- ✅ All memory layers accessible
- ✅ Clear memory works
- ✅ Export memory works
- ✅ No data leakage between namespaces

---

### Group 8: Deep Research Mode (3 SP)

**E2E Test Coverage:**
- Enable Deep Research mode
- Multi-step query execution
- LangGraph state machine progression
- Tool integration (search, retrieval)
- Final answer synthesis
- Research trace display

**Acceptance Criteria:**
- ✅ Multi-step execution works
- ✅ Tools invoked correctly
- ✅ State transitions logged
- ✅ Final answer coherent

---

### Group 9: Long Context Features (4 SP)

**E2E Test Coverage (Sprint 90/91/92):**
- Recursive LLM Scoring (ADR-052)
- Adaptive Context Expansion
- 3-Stage Scoring (Threshold, Confidence, Adaptive)
- Long query handling (>2000 tokens)
- Context window management

**Acceptance Criteria:**
- ✅ Recursive scoring triggers correctly
- ✅ Context expands adaptively
- ✅ Long queries handled without truncation
- ✅ Performance <2s for recursive scoring

---

### Group 10: Hybrid Search (3 SP)

**E2E Test Coverage:**
- BGE-M3 Dense search
- BGE-M3 Sparse search
- Hybrid search (Dense + Sparse)
- RRF fusion (server-side Qdrant)
- Search mode toggle (Vector/Graph/Hybrid)
- Results display with scores

**Acceptance Criteria:**
- ✅ All search modes functional (Sprint 87)
- ✅ RRF fusion working
- ✅ Scores displayed correctly
- ✅ No 0ms timing metrics (Sprint 96 fix)

---

### Group 11: Document Upload (3 SP)

**E2E Test Coverage:**
- Fast upload endpoint (2-5s response)
- 3-Rank LLM Cascade (Nemotron3→GPT-OSS→SpaCy)
- Gleaning (iterative extraction)
- Upload status tracking
- Background processing
- Multiple file formats (PDF, TXT, DOCX)

**Acceptance Criteria:**
- ✅ Fast upload <5s (Sprint 83)
- ✅ 3-Rank Cascade 99.9% success
- ✅ Status tracking works
- ✅ All formats supported

---

### Group 12: Graph Communities (2 SP)

**E2E Test Coverage:**
- Graph communities page loads
- Community list display
- Community summarization
- API endpoint working
- UI rendering correct

**Acceptance Criteria:**
- ✅ Communities visible (Sprint 79)
- ✅ Summaries generated
- ✅ API returns correct data
- ✅ UI displays properly

---

### Group 13: Agent Hierarchy (2 SP)

**E2E Test Coverage:**
- Agent Hierarchy page loads
- Tree structure displays (Executive, Managers, Workers)
- Agent status badges (active/inactive)
- Agent details panel
- Performance metrics (success rate, latency)

**Acceptance Criteria:**
- ✅ Tree renders correctly (Sprint 100 Fix #5)
- ✅ Status lowercase (not UPPERCASE)
- ✅ Details panel functional (Sprint 100 Fix #7)
- ✅ Metrics display correctly

---

### Group 14: GDPR/Audit (2 SP)

**E2E Test Coverage:**
- GDPR Consent Management page loads
- Consents list display (`items` field)
- Status mapping (granted → active)
- Data Subject Rights tab
- Audit Events page loads
- Events list display (`items` field)
- Compliance Reports generation (ISO 8601 timestamps)

**Acceptance Criteria:**
- ✅ GDPR page loads (Sprint 101 fix)
- ✅ All Sprint 100 fixes validated (#2, #3, #4, #6)
- ✅ No TypeErrors
- ✅ API calls return 200

---

### Group 15: Explainability/Certification (2 SP)

**E2E Test Coverage:**
- Explainability page loads
- Decision paths display
- Certification status
- Transparency metrics
- Audit trail links

**Acceptance Criteria:**
- ✅ Page loads correctly (Sprint 98)
- ✅ Decision paths visible
- ✅ Certification functional
- ✅ Links to audit trail work

---

## Testing Strategy

### Playwright E2E Tests

**Test Organization:**
```
frontend/e2e/
├── group01-mcp-tools.spec.ts
├── group02-bash-execution.spec.ts
├── group03-python-execution.spec.ts
├── group04-browser-tools.spec.ts
├── group05-skills-management.spec.ts
├── group06-skills-using-tools.spec.ts
├── group07-memory-management.spec.ts
├── group08-deep-research.spec.ts
├── group09-long-context.spec.ts
├── group10-hybrid-search.spec.ts
├── group11-document-upload.spec.ts
├── group12-graph-communities.spec.ts
├── group13-agent-hierarchy.spec.ts
├── group14-gdpr-audit.spec.ts
└── group15-explainability.spec.ts
```

**Test Execution:**
```bash
# Run all groups
npx playwright test frontend/e2e/group*.spec.ts

# Run specific group
npx playwright test frontend/e2e/group05-skills-management.spec.ts

# Run with UI
npx playwright test --ui
```

---

## Fix Strategy

**When Tests Fail:**

1. **Identify Root Cause:**
   - Frontend bug (React component)
   - Backend bug (API endpoint)
   - API contract mismatch (Sprint 100 issue)
   - Missing feature

2. **Decision Required?**
   - ✅ No decision → Fix immediately
   - ⚠️ Decision required → Skip test, document in SPRINT_102_DEFERRED.md

3. **Fix Implementation:**
   - Frontend fix: Edit React component
   - Backend fix: Edit FastAPI endpoint
   - API contract: Update both sides

4. **Re-run Test:**
   - Verify fix works
   - Document in SPRINT_102_COMPLETE.md

---

## Documentation

### SPRINT_102_COMPLETE.md Structure

```markdown
# Sprint 102 Complete: E2E Production Validation

## Group 1: MCP Tool Management
- Test Results: X/Y PASSED
- Issues Fixed: [list]
- Deferred: [list if any]

## Group 2: Bash Tool Execution
...

## Summary
- Total Tests: XXX
- Passed: XXX (XX%)
- Failed: XXX (XX%)
- Deferred: XXX (decisions required)
- Bugs Fixed: XXX
- Production Ready: YES/NO
```

---

## Success Metrics

**Production Readiness Criteria:**

- ✅ All 15 functional groups tested
- ✅ >95% test pass rate (excluding deferred)
- ✅ All critical bugs fixed
- ✅ Documentation complete
- ✅ No P0/P1 blockers remaining

**Timeline:**

- Start: 2026-01-15 evening
- End: 2026-01-16 morning
- Duration: ~12 hours (overnight)

---

## Risk Mitigation

**Known Risks:**

1. **Chat Endpoint Timeout (49s+)** - May block Deep Research tests
   - Mitigation: Skip if unfixable without decision

2. **Agent Services Not Running (503/404)** - May block Agent Hierarchy details
   - Mitigation: Test UI logic only, document limitation

3. **GDPR Endpoints 500 Errors** - May block some GDPR tests
   - Mitigation: Test what works, document gaps

---

**Sprint 102 Status:** 📝 In Progress (2026-01-15)
**Estimated Delivery:** 2026-01-16 morning
**Total Story Points:** 45 SP
