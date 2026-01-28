# TD-123: Tool Display Component Merge

**Created:** 2026-01-28 (Sprint 121)
**Status:** 🔴 OPEN
**Priority:** LOW
**Story Points:** 3 SP
**Target Sprint:** Sprint 123+

---

## Problem

Two separate components display tool execution results:

1. **`ToolExecutionDisplay.tsx`** (Sprint 63, 319 lines) — Detailed post-execution display:
   - SyntaxHighlighter with bash/python/text detection
   - stdout/stderr separation
   - Copy buttons per section
   - Exit code badge with color coding
   - Collapsible sections
   - Full tool metadata display

2. **`ToolExecutionPanel.tsx`** (Sprint 119 + 121 upgrade, ~280 lines) — Streaming in-chat display:
   - Progress bar and live status
   - Tool-type icons (Terminal/Code/Search/Globe/Wrench)
   - Input display (collapsible)
   - Syntax-aware highlighting
   - Copy-to-clipboard button
   - Dark mode support

Sprint 121 upgraded ToolExecutionPanel to have most of ToolExecutionDisplay's features, but they remain separate components with overlapping functionality.

## Root Cause

Incremental development: Display was built first for post-execution viewing (Sprint 63), Panel was built later for streaming (Sprint 119). Each evolved independently.

## Impact

- ~600 lines of code with significant overlap
- Bug fixes / style changes need to be applied in two places
- Slightly different formatting between streaming and post-execution views

## Proposed Solution

Merge into a single `ToolExecution` component family:
1. **`ToolExecutionCard.tsx`** — Shared container with header, icons, status
2. **`ToolExecutionContent.tsx`** — Shared output rendering (syntax highlight, copy, sections)
3. **`ToolExecutionPanel.tsx`** — Thin wrapper for streaming context (progress bar, live updates)
4. **`ToolExecutionDisplay.tsx`** — Thin wrapper for post-execution context (stdout/stderr split)

### Files to Modify/Create

| Action | File | Description |
|--------|------|-------------|
| CREATE | `frontend/src/components/chat/ToolExecutionCard.tsx` | Shared container |
| CREATE | `frontend/src/components/chat/ToolExecutionContent.tsx` | Shared content renderer |
| MODIFY | `frontend/src/components/chat/ToolExecutionPanel.tsx` | Slim down to streaming wrapper |
| MODIFY | `frontend/src/components/chat/ToolExecutionDisplay.tsx` | Slim down to post-exec wrapper |

## Acceptance Criteria

- [ ] Shared styling between streaming and post-execution views
- [ ] No visual regression in either usage context
- [ ] Total LOC reduced by ~40%
- [ ] Single source of truth for syntax highlighting logic

---

**Document maintained by:** Technical Debt Tracking System
