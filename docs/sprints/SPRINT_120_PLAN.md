# Sprint 120 Plan: UI Polish, Test Stabilization & Infrastructure

**Date:** 2026-01-26 (Planning)
**Status:** 📝 Planned
**Total Story Points:** ~64 SP estimated
**Predecessor:** Sprint 119 (Skipped E2E Test Analysis & Stabilization)
**Successor:** Sprint 121

---

## Executive Summary

Sprint 120 combines **Skills/Tools activation** with **UI polish & stabilization** following Sprint 119 (71 SP). Focus areas:

1. **P0: Skills/Tools End-to-End Activation** — Connect the full pipeline: prompts → detection → execution → SSE → UI (12 SP)
2. **P1: User-Reported UI Bugs** — Critical UX issues in research/chat flow (14 SP)
3. **P2: Test Infrastructure** — Visual regression framework, performance tests (23 SP)
4. **P3: Feature Gaps** — Bash execution UI, memory management data-testids, admin indexing (15 SP)

---

## Feature Breakdown

### 🔴 P1 — User-Reported UI Bugs (14 SP)

| # | Feature | Description | SP | Priority |
|---|---------|-------------|----|----------|
| **120.1** | Deep Research Results Display | Research results should render in the **normal chat window**, not separate panel | 5 | CRITICAL |
| **120.2** | Research Progress Dismissable | Research progress panel should be **closeable/dismissable** after completion | 3 | CRITICAL |
| **120.3** | Source Count Fix | 20 source numbers displayed as badges but only **10 sources shown/expanded** | 3 | HIGH |
| **120.4** | Error Display in Chat | `setError()` in `useStreamChat` sets state but **never rendered** in UI | 3 | HIGH |

#### 120.1: Deep Research Results Display (5 SP)

**Current Behavior:** Deep research results may display in a separate panel or format.
**Expected Behavior:** Results should integrate into the normal chat message flow.

**Investigation Areas:**
- `frontend/src/pages/HomePage.tsx` — Research state handling
- `frontend/src/components/chat/ConversationView.tsx` — Message rendering pipeline
- `frontend/src/hooks/useStreamChat.ts` — Research event processing

#### 120.2: Research Progress Dismissable (3 SP)

**Current Behavior:** Research progress panel stays visible after research completes.
**Expected Behavior:** Add close/dismiss button, or auto-collapse on completion.

**Implementation:**
- Add `onClose` callback to research progress component
- Auto-minimize after completion with optional expand

#### 120.3: Source Count Fix (3 SP)

**Current Behavior:** 20 source reference numbers shown, but only 10 sources actually displayed/expandable.
**Expected Behavior:** All referenced sources should be accessible.

**Investigation Areas:**
- Source rendering limit (hard-coded `slice(0, 10)`?)
- Source data pipeline (do all 20 sources arrive from backend?)
- UI pagination/expansion logic

#### 120.4: Error Display in Chat (3 SP)

**Current Behavior:** `streamingState.error` is set via `setError()` in `useStreamChat` but never rendered.
**Expected Behavior:** Errors should display as a message bubble or inline notification.

**Root Cause (Sprint 119 finding):**
```typescript
// HomePage.tsx does NOT render streamingState.error anywhere
// Need to add error display component
```

---

### 🟡 P2 — Test Infrastructure (23 SP, carry-over from Sprint 118)

| # | Feature | Description | SP | Priority |
|---|---------|-------------|----|----------|
| **120.5** | Visual Regression Framework | Screenshot comparison infra for UI regression testing | 5 | HIGH |
| **120.6** | Performance Regression Tests | Full performance test suite with metrics endpoints | 13 | HIGH |
| **120.7** | Admin Indexing UI (119.6) | Upload/index buttons, status indicators, progress feedback | 5 | MEDIUM |

#### 120.5: Visual Regression Framework (5 SP)

**Scope:**
- Playwright screenshot comparison setup
- Baseline screenshot capture for key pages
- CI integration for visual diff detection

#### 120.6: Performance Regression Tests (13 SP)

**Scope:**
- Metrics endpoints (`/admin/metrics`)
- Performance benchmark tests (P95 latency targets)
- Load testing framework setup
- ~15 tests in `performance-regression.spec.ts`

#### 120.7: Admin Indexing UI Improvements (5 SP)

**Missing data-testids (from Sprint 119 analysis):**
```typescript
[data-testid="upload-files-button"]
[data-testid="index-button"]
[data-testid="upload-status"]
[data-testid="indexing-progress"]
```

**Impact:** 12 E2E tests in `single-document-test.spec.ts` currently conditional skip

---

### 🟢 P3 — Feature Gaps & Test Enablement (15 SP)

| # | Feature | Description | Tests Enabled | SP | Priority |
|---|---------|-------------|---------------|----|---------:|
| **120.8** | Bash Execution UI | Security sandbox execution interface in chat | 6 tests | 8 | MEDIUM |
| **120.9** | Memory Management data-testids | Add test attributes to memory management UI | 11 tests | 5 | MEDIUM |
| **120.10** | E2E Suite Verification Run | Full test suite + pass rate documentation | — | 2 | LOW |

#### 120.8: Bash Execution UI (8 SP)

**Test File:** `group02-bash-execution.spec.ts` (6 tests currently skipped)
**Scope:**
- Security sandbox UI for command execution
- Input sanitization and validation
- Output display with syntax highlighting
- Permission/approval workflow before execution

**Required Components:**
```typescript
[data-testid="bash-input"]
[data-testid="bash-execute-button"]
[data-testid="bash-output"]
[data-testid="bash-approval-dialog"]
```

#### 120.9: Memory Management data-testids (5 SP)

**Test File:** Group 07 memory management tests (11 failures due to missing data-testids)
**Scope:**
- Add `data-testid` attributes to existing memory management components
- Verify test locators match component structure

**Required data-testids:**
```typescript
[data-testid="memory-list"]
[data-testid="memory-item"]
[data-testid="memory-search"]
[data-testid="memory-delete"]
[data-testid="memory-consolidation-status"]
```

#### 120.10: E2E Suite Verification Run (2 SP)

**Scope:**
- Full E2E test suite run after all Sprint 120 changes
- Document pass rate improvement from Sprint 119 baseline
- Update `docs/e2e/PLAYWRIGHT_E2E.md` with results

---

### 🔴 P0 — Skills/Tools End-to-End Activation (12 SP)

| # | Feature | Description | SP | Priority |
|---|---------|-------------|----|----------|
| **120.11** | Tool-Aware Prompts | Add `[TOOL:]`/`[SEARCH:]`/`[FETCH:]` instruction to LLM prompts | 3 | CRITICAL |
| **120.12** | Hybrid Detection Strategy | Switch from `markers` to `hybrid` (markers + LLM fallback) | 2 | CRITICAL |
| **120.13** | MCP Server Auto-Connect | Enable `auto_connect: true` + Redis `enable_chat_tools: true` | 2 | CRITICAL |
| **120.14** | SSE Tool Events in Chat Stream | Emit `tool_use`, `tool_result`, `tool_progress` events in `/chat/stream` | 5 | CRITICAL |

#### 120.11: Tool-Aware Prompts (3 SP)

**Problem:** LLM prompts in `src/prompts/answer_prompts.py` contain no instruction about tool markers.
The LLM doesn't know it can/should emit `[TOOL:action]`, `[SEARCH:query]`, or `[FETCH:url]`.

**Solution:** Add conditional tool awareness instruction to answer prompts:
```python
TOOL_AWARENESS_INSTRUCTION = """
**Verfügbare Werkzeuge:**
Falls die Quellen nicht ausreichen:
- Web-Suche: [SEARCH:suchbegriff]
- URL abrufen: [FETCH:https://url]
- Tool ausführen: [TOOL:aktion]
Nutze Tools NUR wenn die Quellen die Frage nicht beantworten können.
"""
```

**Files:**
- `src/prompts/answer_prompts.py` — Add TOOL_AWARENESS_INSTRUCTION
- `src/agents/answer_generator.py` — Inject instruction when `tools_enabled=True`
- `src/agents/graph.py` — Pass `tools_enabled` state to llm_answer_node

#### 120.12: Hybrid Detection Strategy (2 SP)

**Problem:** Default strategy `markers` requires LLM to emit exact markers (~0ms but unreliable).
`llm` strategy is intelligent but adds +50-200ms to every query.

**Solution:** Switch to `hybrid` — markers first (0ms), then LLM only when action hints detected.
- 90%+ queries: 0ms overhead (no hints → no LLM call)
- Tool candidates: +50-200ms (intelligent decision)

**Files:**
- `src/components/tools_config/tools_config_service.py` — Change default to `"hybrid"`
- Redis key `admin:tools_config` — Update configuration

#### 120.13: MCP Server Auto-Connect (2 SP)

**Problem:** All MCP servers have `auto_connect: false` in `config/mcp_servers.yaml`.
Even with tools enabled, no servers are connected to execute them.

**Solution:**
- Set `auto_connect: true` for production-ready servers
- Set Redis `enable_chat_tools: true`
- Add admin UI toggle for tools on/off

**Files:**
- `config/mcp_servers.yaml` — Enable auto_connect
- Redis key `admin:tools_config` — Enable tools

#### 120.14: SSE Tool Events in Chat Stream (5 SP)

**Problem:** `src/api/v1/chat.py` SSE handler only emits `phase_event`, `token`, `citation_map`.
Tool execution events (`tool_use`, `tool_result`, `tool_progress`) are never sent to frontend.

**Solution:** Add tool event emission in `generate_stream()`:
- Capture tool events from LangGraph's `tools_node()` via `writer` parameter
- Map to SSE events: `tool_use`, `tool_result`, `tool_progress`, `tool_error`, `tool_timeout`
- Frontend `useStreamChat` already handles these events (Sprint 119.1)

**Files:**
- `src/api/v1/chat.py` — Add tool event handling in SSE stream
- `src/agents/tools/tool_integration.py` — Emit structured events via writer

---

## Technical Debt Updates

### TD-121: Graph Versioning UI — DEFERRED ✅

**Decision:** Moved to Technical Debt (TD-121) per Sprint 120 planning.
- 28 E2E tests remain skipped (`time-travel.spec.ts`, `entity-changelog.spec.ts`, `version-compare.spec.ts`)
- 21 SP estimated implementation
- Target: Sprint 122+ or customer-triggered
- See: `docs/technical-debt/TD-121_GRAPH_VERSIONING_UI.md`

---

## Sprint Metrics

| Metric | Target |
|--------|--------|
| Story Points | ~64 SP |
| P0 Tools Activation | 4/4 features |
| P1 UI Bugs Fixed | 4/4 |
| New Tests Enabled | ~29 (6 bash + 11 memory + 12 indexing) |
| E2E Pass Rate | >80% (from ~73.5%) |

---

## Execution Plan

### Phase 0: Skills/Tools Activation (Day 1-2) — HIGHEST PRIORITY
- [ ] 120.11: Tool-aware prompts (answer_prompts.py, answer_generator.py)
- [ ] 120.12: Hybrid detection strategy (tools_config default change)
- [ ] 120.13: MCP server auto-connect (mcp_servers.yaml, Redis config)
- [ ] 120.14: SSE tool events in chat stream (chat.py, tool_integration.py)

### Phase 1: UI Bug Fixes (Day 3-4)
- [ ] 120.1: Deep Research results in chat
- [ ] 120.2: Research progress dismissable
- [ ] 120.3: Source count mismatch fix
- [ ] 120.4: Error display in chat

### Phase 2: Feature Gaps (Day 5-6)
- [ ] 120.8: Bash Execution UI
- [ ] 120.9: Memory Management data-testids
- [ ] 120.7: Admin Indexing UI improvements

### Phase 3: Test Infrastructure (Day 7-8)
- [ ] 120.5: Visual Regression Framework
- [ ] 120.6: Performance Regression Tests
- [ ] 120.10: Full E2E verification run

---

## Dependencies

| Feature | Depends On | Blocks |
|---------|------------|--------|
| 120.1 | useStreamChat research events | 120.10 |
| 120.4 | useStreamChat error state | 120.10 |
| 120.6 | Backend metrics endpoints | None |
| 120.8 | Backend bash execution API | None |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance endpoints not implemented | Medium | 120.6 blocked | Implement stub endpoints |
| Bash execution security concerns | Medium | 120.8 scope creep | Limit to sandboxed execution |
| Visual regression CI integration | Low | 120.5 delayed | Use local-only initially |

---

## References

- [Sprint 119 Plan](SPRINT_119_PLAN.md) — Predecessor
- [Sprint 118 Plan](SPRINT_118_PLAN.md) — Carry-over source
- [E2E Testing Guide](../e2e/PLAYWRIGHT_E2E.md) — Test documentation
- [TD-121](../technical-debt/TD-121_GRAPH_VERSIONING_UI.md) — Deferred Graph Versioning
- [TD Index](../technical-debt/TD_INDEX.md) — Technical debt tracking
