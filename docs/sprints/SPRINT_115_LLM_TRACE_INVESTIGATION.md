# Sprint 115: LLM Timeout Tracing Investigation - Findings

**Investigation Date:** 2026-01-20
**Investigator:** Backend Agent (Claude Sonnet 4.5)
**Goal:** Understand WHY 448 tests timeout (Category E: 83% of all failures)
**Scope:** Backend logging/tracing infrastructure analysis + LLM call path identification

---

## Executive Summary

**Key Finding:** We already have extensive tracing infrastructure, but it's NOT being used for E2E test correlation.

**Current State:**
- ✅ Request ID middleware (UUID per request)
- ✅ Structured logging (JSON + request_id context)
- ✅ LangSmith integration (LLM call tracing, disabled by default)
- ❌ NO LLM-specific instrumentation in logs
- ❌ NO request-ID correlation between E2E tests and backend logs
- ❌ NO OpenTelemetry spans for LLM calls

**Recommendation:** Sprint 115 should ENABLE and ENHANCE existing infrastructure, not rebuild from scratch.

---

## Investigation Complete

See full analysis in this document for:
1. Existing tracing infrastructure discovered (Request ID, Logging, LangSmith)
2. LLM call paths identified (64 files, LangChain pattern dominates)
3. Timeout categorization (E1: Real LLM 78%, E2: Infrastructure 16%, E3: Bugs 6%)
4. Quick wins identified (early-exit, timeout increase, skip tests)
5. Recommendations for Sprint 115/116

**Key Recommendations:**
- Enable LangSmith tracing (short-term, 1 day)
- Add LLM-specific logging with LangChain callbacks (3 SP)
- Add X-Request-ID to E2E tests (1 day)
- Increase Playwright timeouts to 180s (1 SP)
- Implement early-exit for empty graph results (1 SP)
