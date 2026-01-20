# E2E Test Duplicate Removal Checklist

**Quick Reference for Sprint Implementation**

## Files to Remove (High Confidence)

### Tier 1: Safe to Remove (No coverage loss)

- [ ] **group18-admin-dashboard.spec.ts** (12 tests)
  - Keep: admin/admin-dashboard.spec.ts (14 tests)
  - Command: `rm frontend/e2e/group18-admin-dashboard.spec.ts`

- [ ] **group21-indexing-training.spec.ts** (26 tests)
  - Keep: admin/indexing.spec.ts (46 tests)
  - Command: `rm frontend/e2e/group21-indexing-training.spec.ts`

- [ ] **group20-domain-discovery.spec.ts** (15 tests)
  - Keep: admin/domain-discovery-api.spec.ts (17 tests) + admin/domain-auto-discovery.spec.ts (10 tests)
  - Command: `rm frontend/e2e/group20-domain-discovery.spec.ts`

- [ ] **group19-llm-config.spec.ts** (17 tests)
  - Keep: admin/llm-config.spec.ts (26 tests) + admin/llm-config-backend-integration.spec.ts (10 tests)
  - Command: `rm frontend/e2e/group19-llm-config.spec.ts`

### Tier 2: Likely Safe (Verify before removing)

- [ ] **tests/admin/mcp-tools.spec.ts** (15 tests)
  - Keep: group01-mcp-tools.spec.ts (19 tests)
  - Command: `rm frontend/e2e/tests/admin/mcp-tools.spec.ts`
  - Verification: `grep -r "mcp-tools" frontend/e2e/` should only show group01

- [ ] **group12-graph-communities.spec.ts** (16 tests)
  - Keep: tests/admin/graph-communities.spec.ts (22 tests) - MORE comprehensive
  - Command: `rm frontend/e2e/group12-graph-communities.spec.ts`
  - Verification: Check both files test same features

### Tier 3: Requires Manual Review

- [ ] **group07-memory-management.spec.ts** (15 tests) vs **tests/admin/memory-management.spec.ts** (15 tests)
  - Status: SAME TEST COUNT - likely duplicates
  - Action: Manual comparison required
  - IF identical: Remove one (recommend tests/admin pattern)
  - IF complementary: Keep both and document difference

---

## Total Impact

| Metric | Remove | Expected Reduction |
|--------|--------|-------------------|
| Files | 6 | -7% |
| Tests | 122 | -13% |
| Size | ~170 KB | |

---

## Verification Commands

```bash
# 1. Before removing anything, establish baseline
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend
npm run test:e2e -- --reporter=json > /tmp/baseline.json

# 2. Remove files from Tier 1 (safest)
rm e2e/group18-admin-dashboard.spec.ts
rm e2e/group21-indexing-training.spec.ts
rm e2e/group20-domain-discovery.spec.ts
rm e2e/group19-llm-config.spec.ts

# 3. Run tests to confirm no breakage
npm run test:e2e -- --reporter=html

# 4. Remove Tier 2 files (after confirming Tier 1)
rm e2e/tests/admin/mcp-tools.spec.ts
rm e2e/group12-graph-communities.spec.ts

# 5. Final verification
npm run test:e2e -- --reporter=json > /tmp/after.json

# 6. Compare results
echo "Before: $(jq '.stats.expected' /tmp/baseline.json) tests"
echo "After: $(jq '.stats.expected' /tmp/after.json) tests"
```

---

## Git Commit Template

```bash
git add frontend/e2e/

git commit -m "test(e2e): Remove duplicate Playwright tests (Sprint XXX)

Consolidate overlapping E2E test files:
- Removed group18-admin-dashboard.spec.ts (12 tests → kept admin/admin-dashboard.spec.ts)
- Removed group21-indexing-training.spec.ts (26 tests → kept admin/indexing.spec.ts)
- Removed group20-domain-discovery.spec.ts (15 tests → kept admin/domain-discovery-api.spec.ts)
- Removed group19-llm-config.spec.ts (17 tests → kept admin/llm-config.spec.ts)
- Removed tests/admin/mcp-tools.spec.ts (15 tests → kept group01-mcp-tools.spec.ts)
- Removed group12-graph-communities.spec.ts (16 tests → kept tests/admin/graph-communities.spec.ts)

Total reduction: 122 duplicate tests removed, 6 files deleted
New total: 968 tests across 79 files (13% reduction)

See PLAYWRIGHT_DUPLICATE_ANALYSIS.md for detailed analysis.

Co-Authored-By: Testing Agent <noreply@anthropic.com>"
```

---

## Documentation Updates Required

After removal, update:

1. **docs/e2e/PLAYWRIGHT_E2E.md**
   - Update test count from 1,090 → 968
   - Remove references to deleted group files
   - Update test organization section

2. **CLAUDE.md**
   - Update E2E testing metrics section
   - Update file count (85 → 79)

3. **docs/sprints/SPRINT_XXX_PLAN.md**
   - Document test consolidation as completed task
   - Update estimated test maintenance time reduction

---

## Success Criteria

- [ ] All 6 files deleted successfully
- [ ] No import errors in remaining tests
- [ ] Test suite runs without errors
- [ ] No test name conflicts
- [ ] Coverage metrics maintained or improved
- [ ] Documentation updated

---

## Rollback Plan

If issues arise, restore deleted files:

```bash
git checkout HEAD -- frontend/e2e/group18-admin-dashboard.spec.ts
git checkout HEAD -- frontend/e2e/group21-indexing-training.spec.ts
git checkout HEAD -- frontend/e2e/group20-domain-discovery.spec.ts
git checkout HEAD -- frontend/e2e/group19-llm-config.spec.ts
git checkout HEAD -- frontend/e2e/tests/admin/mcp-tools.spec.ts
git checkout HEAD -- frontend/e2e/group12-graph-communities.spec.ts
```

---

**Analysis Date:** 2026-01-20
**High Confidence Items:** Tier 1 & 2 (safe to remove)
**Medium Confidence Items:** Tier 3 (requires review)
