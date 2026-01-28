# TD-122: Tool Progress Streaming (Backend Emission)

**Created:** 2026-01-28 (Sprint 121)
**Status:** 🔴 OPEN
**Priority:** LOW
**Story Points:** 5 SP
**Target Sprint:** Sprint 123+

---

## Problem

The `tool_progress` SSE event type is a **"sleeping feature"** — the frontend handler exists in `useStreamChat.ts` (lines 608-625) and correctly processes incoming progress events, but the backend **never emits** this event type.

Currently, the `tools_node` in `src/agents/tools/tool_integration.py` emits only:
- `TOOL_EXECUTION` with `IN_PROGRESS` status (start)
- `TOOL_EXECUTION` with `COMPLETED/FAILED` status (end)

There is no intermediate progress reporting during long-running tool executions (e.g., bash commands, web searches).

## Root Cause

The backend `tools_node` was built for fast tool calls. No intermediate progress reporting was implemented because most MCP tools complete in <2s. However, for bash commands, web browsing, and data processing tools, progress streaming would improve UX significantly.

## Impact

- Users see a spinner with no feedback during long-running tool executions (>5s)
- No way to distinguish "still running" from "hung" for bash/python tools
- Frontend has working handler but receives no data

## Proposed Solution

Add intermediate `tool_progress` PhaseEvent emissions in `tools_node`:
1. For bash/python tools: Stream stdout/stderr lines as they arrive
2. For web tools: Report connection/fetching/parsing stages
3. For search tools: Report query/ranking/filtering stages

### Files to Modify

| File | Change |
|------|--------|
| `src/agents/tools/tool_integration.py` | Add `tool_progress` PhaseEvent emissions during execution |
| `src/api/v1/chat.py` | Add SSE handler for `tool_progress` events (already prepared in Sprint 121) |
| `src/models/phase_event.py` | Add `TOOL_PROGRESS` PhaseType if needed (or reuse `TOOL_EXECUTION` with `progress` metadata) |

## Acceptance Criteria

- [ ] Long-running bash commands stream stdout line-by-line to frontend
- [ ] Frontend `tool_progress` handler receives and displays updates
- [ ] Progress percentage shown for tools that support it
- [ ] No performance regression for fast tool calls (<2s)

---

**Document maintained by:** Technical Debt Tracking System
