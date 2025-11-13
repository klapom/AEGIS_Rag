# Technical Debt Register

**Last Updated:** 2025-11-13
**Project:** AegisRAG
**Sprint:** Sprint 23 (Day 2)

## Overview

This document tracks known technical debt, workarounds, and areas for future improvement. Items are prioritized by impact and effort.

---

## Sprint 23 - Multi-Cloud LLM Integration

### TD-23.1: ANY-LLM Framework Not Fully Integrated

**Category:** Architecture
**Priority:** P2 (Medium)
**Effort:** 3 days
**Sprint:** Sprint 23

**Description:**
We're using ANY-LLM's `acompletion()` function for text generation but NOT using the full ANY-LLM framework features:
- ❌ ANY-LLM BudgetManager (built-in)
- ❌ ANY-LLM CostTracker (built-in)
- ❌ ANY-LLM ConnectionPooling
- ❌ ANY-LLM Gateway (centralized proxy)

**Current Workaround:**
- Custom SQLite `CostTracker` (389 LOC)
- Manual budget checking in `aegis_llm_proxy.py`
- Direct `httpx.AsyncClient` for DashScope VLM

**Why We Did This:**
- ANY-LLM Core Library doesn't have VLM support
- ANY-LLM Gateway requires separate server deployment
- We needed VLM-specific parameters (`enable_thinking`, `vl_high_resolution_images`)
- SQLite gives us full control over schema and queries

**Future Resolution:**
- Option 1: Deploy ANY-LLM Gateway as microservice (adds infrastructure complexity)
- Option 2: Keep custom SQLite solution (simpler, working well)
- Option 3: Contribute VLM support to ANY-LLM upstream

**Decision:** Keep custom solution for now. Re-evaluate if ANY-LLM adds VLM support.

**Related Files:**
- `src/components/llm_proxy/cost_tracker.py`
- `src/components/llm_proxy/dashscope_vlm.py`
- `src/components/llm_proxy/aegis_llm_proxy.py`

---

### TD-23.2: DashScope VLM Client Not Using AegisLLMProxy

**Category:** Architecture
**Priority:** P3 (Low)
**Effort:** 2 days
**Sprint:** Sprint 23

**Description:**
`DashScopeVLMClient` is a separate client that bypasses `AegisLLMProxy` routing logic. VLM requests don't go through the unified routing system.

**Current Workaround:**
Direct DashScope API calls in `dashscope_vlm.py` with manual fallback logic.

**Why We Did This:**
- ANY-LLM `acompletion()` doesn't support image inputs
- VLM requires base64 image encoding and special parameters
- Faster to implement direct integration

**Impact:**
- VLM cost tracking works (manual integration)
- No unified routing metrics for VLM vs text tasks
- Code duplication between `aegis_llm_proxy.py` and `dashscope_vlm.py`

**Future Resolution:**
- Extend `AegisLLMProxy` with VLM-specific generate method
- Unified interface: `proxy.generate(task)` for both text and vision
- Consolidate cost tracking in one place

**Related Files:**
- `src/components/llm_proxy/dashscope_vlm.py`
- `src/components/ingestion/image_processor.py`

---

### TD-23.3: Token Split Estimation (50/50) in Cost Tracking

**Category:** Data Quality
**Priority:** P3 (Low)
**Effort:** 1 day
**Sprint:** Sprint 23

**Description:**
When tracking costs in `aegis_llm_proxy.py`, we estimate input/output tokens as 50/50 split because ANY-LLM response doesn't provide detailed token breakdown.

**Current Code:**
```python
# Estimate 50/50 split for input/output tokens if not available
tokens_input = result.tokens_used // 2
tokens_output = result.tokens_used - tokens_input
```

**Impact:**
- Cost calculations are correct (based on total tokens)
- But input/output token breakdown in SQLite is approximate
- Alibaba Cloud charges different rates for input vs output

**Future Resolution:**
- Extract detailed token usage from API responses
- Alibaba Cloud returns `prompt_tokens` and `completion_tokens`
- Update `aegis_llm_proxy.py` to parse response.usage properly

**Related Files:**
- `src/components/llm_proxy/aegis_llm_proxy.py` (line 495-497)

---

### TD-23.4: Async/Sync Bridge in ImageProcessor

**Category:** Code Quality
**Priority:** P3 (Low)
**Effort:** 2 days
**Sprint:** Sprint 23

**Description:**
`ImageProcessor.process_image()` is synchronous but calls async `generate_vlm_description_with_dashscope()`. We use `asyncio.run()` with thread pool executor to bridge sync/async.

**Current Code:**
```python
try:
    loop = asyncio.get_running_loop()
    # Already in event loop - use ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, generate_vlm_description_with_dashscope(...))
        description = future.result()
except RuntimeError:
    # Not in event loop - use asyncio.run
    description = asyncio.run(generate_vlm_description_with_dashscope(...))
```

**Impact:**
- Works correctly in both sync and async contexts
- But adds complexity and potential performance overhead
- Thread pool creates extra overhead

**Why We Did This:**
- `ImageProcessor` is called from both sync and async code
- Needed to support both contexts without breaking existing callers

**Future Resolution:**
- Make entire ingestion pipeline async
- Refactor `ImageProcessor.process_image()` to be async
- Update all callers to use `await`

**Related Files:**
- `src/components/ingestion/image_processor.py` (lines 414-434)

---

## Sprint 22 - Hybrid Ingestion

### TD-22.1: LlamaIndex Partial Deprecation

**Category:** Architecture
**Priority:** P2 (Medium)
**Effort:** Already addressed
**Sprint:** Sprint 22

**Description:**
LlamaIndex deprecated as primary ingestion framework but kept as fallback parser.

**Status:** ✅ RESOLVED in Sprint 21/22
**Resolution:** ADR-028 documented the deprecation strategy.

**Related Files:**
- `docs/adr/ADR-028-llamaindex-deprecation.md`

---

## General Tech Debt

### TD-G.1: Windows-Only Development Environment

**Category:** DevOps
**Priority:** P2 (Medium)
**Effort:** 1 week
**Sprint:** Future

**Description:**
Development currently Windows-only. Production will be Linux (Kubernetes).

**Impact:**
- Path handling differences
- Line ending differences (CRLF vs LF)
- Shell script compatibility

**Mitigation:**
- Use `pathlib.Path` for cross-platform paths
- Git configured for LF line endings
- Poetry for consistent dependency management

**Future Resolution:**
- Add Linux CI/CD pipeline
- Test on Linux before production deployment

---

### TD-G.2: No Prometheus Metrics Yet

**Category:** Observability
**Priority:** P2 (Medium)
**Effort:** 3 days
**Sprint:** Sprint 24

**Description:**
Cost tracking logs structured metrics but doesn't export to Prometheus.

**Current State:**
```python
# TODO: Add Prometheus metrics when metrics module is available
# from src.core.metrics import llm_requests_total, llm_latency_seconds, llm_cost_usd
# llm_requests_total.labels(provider=provider, task_type=task.task_type).inc()
```

**Future Resolution:**
- Implement `src/core/metrics.py` with prometheus_client
- Export metrics endpoint `/metrics`
- Create Grafana dashboards

**Related Files:**
- `src/components/llm_proxy/aegis_llm_proxy.py` (lines 514-518)

---

## Priority Matrix

| ID | Description | Priority | Effort | Sprint |
|----|-------------|----------|--------|--------|
| TD-23.1 | ANY-LLM partial integration | P2 | 3 days | Future |
| TD-23.2 | DashScope VLM bypass routing | P3 | 2 days | Future |
| TD-23.3 | Token split estimation | P3 | 1 day | Sprint 24 |
| TD-23.4 | Async/sync bridge | P3 | 2 days | Sprint 24 |
| TD-G.1 | Windows-only dev env | P2 | 1 week | Future |
| TD-G.2 | No Prometheus metrics | P2 | 3 days | Sprint 24 |

---

## Decision Log

### Why Custom SQLite Cost Tracker Instead of ANY-LLM?

**Date:** 2025-11-13
**Decision Maker:** Klaus Pommer (with Claude Code)

**Context:**
ANY-LLM has built-in BudgetManager and cost tracking, but:
1. ANY-LLM Core Library doesn't include these features
2. ANY-LLM Gateway requires separate server deployment
3. We needed immediate persistent cost tracking

**Decision:**
Implement custom SQLite `CostTracker` (~400 LOC) with:
- Per-request tracking (timestamp, provider, tokens, cost)
- Monthly aggregations
- CSV/JSON export
- Full control over schema

**Alternatives Considered:**
1. Deploy ANY-LLM Gateway → Rejected (too complex for MVP)
2. Use LiteLLM BudgetManager → Rejected (different framework)
3. No cost tracking → Rejected (business requirement)

**Outcome:**
✅ Working perfectly
✅ 4/4 tests passing
✅ Database at `data/cost_tracking.db`
✅ Cost: $0.003 tracked so far

**Re-evaluation Trigger:**
- ANY-LLM adds VLM support
- We need multi-tenant cost tracking
- Database grows beyond 100MB

---

## Notes

- This register should be updated at the end of each sprint
- Prioritization: P0 (Critical) → P1 (High) → P2 (Medium) → P3 (Low)
- Effort: Person-days for resolution
- Items marked ✅ RESOLVED should remain for historical context
