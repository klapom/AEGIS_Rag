# Group 5 Skills Management Tests - Quick Reference
## Sprint 123.10

**Status:** ✓ Complete (7/7 Tests Fixed)
**File:** `frontend/e2e/group05-skills-management.spec.ts`
**Time to Fix:** 1 hour
**Documentation:** 2,200+ lines

---

## Quick Summary

| Test | Issue | Fix | Status |
|------|-------|-----|--------|
| Load Registry | None | Removed skip | ✓ PASS |
| Valid YAML | Race condition | Added element wait | ✓ PASS |
| Invalid YAML | Selector too generic | Scoped to validation panel | ✓ PASS |
| Schema Errors | Timing + selectors | Used data-testid container | ✓ PASS |
| Toggle Skill | Wrong endpoint path | Changed to /registry/ | ✓ PASS |
| Save Config | Dialog timing | Handler before action | ✓ PASS |
| Error Handling | Element timing | Extended timeout | ✓ PASS |

---

## Key Fixes (Code Patterns)

### Pattern 1: Element Visibility Wait
```typescript
// Always wait for element before interacting
await page.waitForSelector('[data-testid="skill-card-web_search"]', {
  state: 'visible',
  timeout: 10000
});
```

### Pattern 2: Scoped Selectors
```typescript
// Instead of: page.locator('text=/error/i')
// Use:
const validationErrors = page.locator('[data-testid="validation-errors"]');
await expect(validationErrors).toContainText(/error/i);
```

### Pattern 3: API Endpoint Paths
```typescript
// Correct paths:
POST /api/v1/skills/registry/{skillName}/activate
POST /api/v1/skills/registry/{skillName}/deactivate
```

### Pattern 4: Event Handler Order
```typescript
// Handler BEFORE action
page.on('dialog', handler);
await button.click();
```

---

## All Data-TestIDs Used

```
Skills Registry:
  [data-testid="skill-card-{skillName}"]        # Card container
  [data-testid="skill-toggle-{skillName}"]      # Toggle button
  [data-testid="skill-edit-{skillName}"]        # Edit link
  [data-testid="skill-status-{skillName}"]      # Status badge

Config Editor:
  [data-testid="skill-config-{skillName}"]      # YAML textarea
  [data-testid="validation-status"]             # Success badge
  [data-testid="validation-errors"]             # Errors container
  [data-testid="save-error"]                    # Error display
```

---

## Running Tests

### All tests:
```bash
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test group05-skills-management.spec.ts
```

### Single test:
```bash
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test group05-skills-management.spec.ts -k "should load"
```

### With HTML report:
```bash
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test group05-skills-management.spec.ts --reporter=html
npx playwright show-report
```

---

## Common Issues & Quick Fixes

| Problem | Solution |
|---------|----------|
| "Element not found" | Add `waitForSelector()` before interaction |
| "Wrong element matched" | Use `[data-testid="..."]` instead of text selectors |
| "API call failed" | Verify endpoint path includes `/registry/` |
| "Dialog not captured" | Set up handler BEFORE clicking button |
| "Error not visible" | Increase timeout to 5000ms, ensure mock is set up |

---

## Files

**Modified:**
- `frontend/e2e/group05-skills-management.spec.ts` (105 lines changed)

**Created:**
- `docs/e2e/SKILLS_MANAGEMENT_TEST_ANALYSIS.md` (comprehensive analysis)
- `docs/e2e/GROUP05_FIXES_SUMMARY.md` (detailed before/after)
- `docs/e2e/GROUP05_QUICK_REFERENCE.md` (this file)
- `TESTING_FIXES_REPORT.md` (executive summary)

---

## Verification

All fixes verified against:
- ✓ SkillRegistry.tsx (component implements all data-testids)
- ✓ SkillConfigEditor.tsx (component implements all data-testids)
- ✓ skills.ts API client (endpoints match backend)
- ✓ Test mocks (response formats match backend)

---

## Next

See full analysis in `docs/e2e/SKILLS_MANAGEMENT_TEST_ANALYSIS.md` for:
- Line-by-line code explanations
- Component architecture details
- Testing patterns and best practices
- Recommended improvements

---

**Status: Ready for Merge ✓**
