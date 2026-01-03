# Graph Communities E2E Tests - Quick Reference

## What Changed?

Fixed 4 skipped E2E tests in `/frontend/e2e/tests/admin/graph-communities.spec.ts`

| Line | Test Name | Status |
|------|-----------|--------|
| 580 | should fetch and display communities when analyze clicked | ✓ ACTIVE |
| 661 | should show community details when expanded | ✓ ACTIVE |
| 909 | should compare communities when button clicked | ✓ ACTIVE |
| 992 | should display overlap matrix when comparison complete | ✓ ACTIVE |

## How to Run

```bash
# Run graph communities tests
cd frontend
npm run test:e2e -- e2e/tests/admin/graph-communities.spec.ts

# Run all E2E tests
npm run test:e2e

# Run with visual debugger
npm run test:e2e:ui -- e2e/tests/admin/graph-communities.spec.ts
```

## Test Structure

Each test:
1. Calls `setupAuthMocking(page)` for authentication
2. Mocks API endpoints with realistic data
3. Navigates to `/admin/graph`
4. Performs user interactions (click, fill, select)
5. Verifies UI elements appear

## Mock Data

**3 Communities Created** (18 entities total):
- Community 0: Machine Learning concepts (6 entities)
- Community 1: Evaluation metrics (7 entities)
- Community 2: Optimization algorithms (5 entities)

**Comparison Data** (2 sections):
- Section 1: Complete Document (18 entities)
- Section 2: Introduction (12 entities)
- Shared: 5 entities between sections

## Mocked Endpoints

```
GET  /api/v1/graph/documents
GET  /api/v1/graph/documents/{doc_id}/sections
GET  /api/v1/graph/communities/{doc_id}/sections/{section_id}
POST /api/v1/graph/communities/compare
```

## Key Points

- [x] No backend services required
- [x] No Neo4j database needed
- [x] No Docker compose needed
- [x] Runs in <30 seconds per test
- [x] Deterministic (same result every run)
- [x] Works in CI/CD pipeline
- [x] Follows established patterns

## Test Details

### Test 1: Fetch Communities
- Tests community detection API
- Shows 3 community cards
- Verifies card visibility

### Test 2: Show Details
- Extends Test 1
- Clicks expand button
- Shows entity details

### Test 3: Compare Communities
- Tests comparison API
- Compares 2 sections
- Shows overlap results

### Test 4: Display Matrix
- Extends Test 3
- Verifies results table
- Shows shared entities

## Files

- **Test File:** `/frontend/e2e/tests/admin/graph-communities.spec.ts`
- **Documentation:** `SPRINT_72_GRAPH_COMMUNITIES_E2E_FIX.md`
- **Full Report:** `GRAPH_COMMUNITIES_E2E_FINAL_REPORT.md`

## Common Issues & Solutions

**Problem:** Tests not found
**Solution:** Ensure no `test.skip()` prefix on test names

**Problem:** API mocks not working
**Solution:** Verify route pattern matches exactly (use wildcards `**/api/v1/...`)

**Problem:** Timeout waiting for element
**Solution:** Check timeout is sufficient (use `{ timeout: 10000 }`)

**Problem:** Cannot find test element
**Solution:** Verify `data-testid` attribute matches exactly

## Performance

- Total 4 tests: <2 minutes
- Individual test: <30 seconds
- Mock response: <1ms
- No database queries

## Maintenance

When updating tests:
1. Update corresponding mock data if API schema changes
2. Keep mock data realistic (same as backend responses)
3. Use consistent naming for entities/communities
4. Add comments for complex mock structures
5. Document new API endpoints

## Version Info

- **Feature:** Sprint 71 Feature 71.16 (Graph Communities)
- **Test Fix:** Sprint 72 Feature 72.6
- **Completed:** January 3, 2026
- **Status:** Production Ready ✓

## Contact

Refer to:
- Sprint documentation: `/docs/sprints/SPRINT_72_GRAPH_COMMUNITIES_E2E_FIX.md`
- API spec: `/src/api/v1/graph_communities.py`
- Fixtures: `/frontend/e2e/fixtures/index.ts`
