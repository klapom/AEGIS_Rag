# Sprint 101 Plan: API Contract Fixes & Sprint 99 Integration Completion

**Sprint Duration:** TBD (Flexible, after Sprint 100)
**Sprint Goal:** Fix all remaining API contract mismatches from Sprint 99 integration and complete backend testing
**Total Story Points:** 24 SP
**Priority:** P0 (Blocker for Production)

---

## Sprint Context

**Background:**
Sprint 99 implemented 24 backend API endpoints (Features 99.1-99.4). Integration testing with Playwright MCP on 2026-01-15 revealed **8 critical contract mismatches** between Sprint 97-98 frontend and Sprint 99 backend.

**Already Fixed in Sprint 99:**
- ✅ Bug #1-#5: Route mismatches (404 errors)
- ✅ Bug #6: Missing activate/deactivate endpoints (2 SP)
- ✅ Bug #7: Agent Hierarchy D3.js format mismatch (8 SP)
- ✅ Bug #8: SkillSummary interface mismatch (`status` → `is_active`) (2 SP)

**Remaining:** 8 contract mismatches discovered by automated contract analysis agent

---

## Feature 101.1: HIGH-RISK Contract Fixes (12 SP)

**Priority:** P0 (Blocker)
**Risk:** High - Will cause runtime errors (404, 422, TypeErrors)

### Mismatch #1: Skills List Response Format (3 SP)

**Issue:** Frontend expects pagination metadata in response but backend only provides in query params.

**Current:**
```python
# Backend returns: List[SkillSummary]
return paginated_skills
```

**Fix:** Return proper `SkillListResponse` with `total`, `total_pages`, `page`, `page_size`.

---

### Mismatch #2: GDPR Consent List - Field Name (2 SP)

**Issue:** Backend returns `items`, frontend expects `consents`.

**Fix:** Standardize on `items` field across all list endpoints (GDPR, Audit, Skills).

---

### Mismatch #3: Audit Events List - Field Name (2 SP)

**Issue:** Backend returns `items`, frontend expects `events`.

**Fix:** Frontend changes to use `items` field.

---

### Mismatch #4: Audit Reports Query Parameters (3 SP)

**Issue:** Frontend sends `timeRange`, backend expects `start_time` & `end_time`.

**Fix:** Frontend calculates ISO 8601 timestamps from `timeRange` selection.

---

### Mismatch #5: Agent Hierarchy Status Enum (2 SP)

**Issue:** Backend uses `AgentStatus` enum, frontend expects lowercase string literals.

**Fix:** Backend serializes enum values to lowercase strings.

---

## Feature 101.2: MEDIUM-RISK Contract Fixes (8 SP)

**Priority:** P1 (Important)

### Mismatch #6: GDPR Consent Status Enum (2 SP)

**Issue:** Backend `granted`, frontend expects `active`.

**Fix:** Frontend maps `granted` → `active` in display logic.

---

### Mismatch #7: Agent Details Field Names (3 SP)

**Issues:**
- Backend: `name`, Frontend: `agent_name`
- Backend: lowercase `level`, Frontend: UPPERCASE
- Backend: decimal success_rate, Frontend: percentage
- Missing: `p95_latency_ms`, `current_load`, `max_concurrent_tasks`

**Fix:** Frontend adapts to backend field names + calculates derived values.

---

### Mismatch #8: Missing Config Validation Endpoint (3 SP)

**Issue:** Frontend calls `POST /skills/{name}/config/validate` but endpoint doesn't exist.

**Fix:** Implement config validation endpoint in backend.

---

## Feature 101.3: Integration Testing (4 SP)

- Playwright E2E tests for all 8 fixes (2 SP)
- Documentation updates (2 SP)

---

## Success Criteria

1. ✅ All 8 contract mismatches fixed
2. ✅ E2E tests pass (100%)
3. ✅ Zero API errors (404/422/TypeError)
4. ✅ All UI displays correct data

---

## Implementation Priority

**Phase 1:** HIGH-RISK fixes (12 SP) - Days 1-3
**Phase 2:** MEDIUM-RISK fixes (8 SP) - Days 4-5
**Phase 3:** Testing & Docs (4 SP) - Days 6-7

---

**Created:** 2026-01-15
**Source:** Sprint 99 Playwright MCP testing + Automated contract analysis
**Detailed Findings:** See contract analysis agent output (490KB report)

---

## Detailed Mismatch Summary

| # | Endpoint | Issue | Risk | Type |
|---|----------|-------|------|------|
| 1 | GET /skills/registry | Pagination format | HIGH | Logic Error |
| 2 | GET /gdpr/consents | Field: items vs consents | HIGH | 404 Data |
| 3 | GET /audit/events | Field: items vs events | HIGH | 404 Data |
| 4 | GET /audit/reports | Query param format | HIGH | 422 Error |
| 5 | GET /agents/hierarchy | Status enum case | MEDIUM | Type Error |
| 6 | GET /gdpr/consents | Status: granted vs active | MEDIUM | Display |
| 7 | GET /agents/:id/details | Field names | MEDIUM | Render Error |
| 8 | POST /skills/:name/config/validate | Missing endpoint | MEDIUM | 404 Error |

---

**Total SP:** 24
**Risk Level:** P0 (Production Blocker)
**Dependencies:** Sprint 99 Bug #6-#8 fixes must be merged first
