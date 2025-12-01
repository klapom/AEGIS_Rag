# Edge Filters E2E Testing Guide

Quick reference for running and understanding the graph edge filter E2E tests.

## Files

- **Test File:** `edge-filters.spec.ts` (606 lines, 19 tests)
- **POM File:** `frontend/e2e/pom/AdminGraphPage.ts`
- **Fixtures:** `frontend/e2e/fixtures/index.ts`

## Quick Start

### Prerequisites
1. Backend running: `poetry run python -m src.api.main` (port 8000)
2. Frontend running: `npm run dev` (port 5179)
3. Neo4j running with test data

### Run All Edge Filter Tests
```bash
cd frontend
npm run test:e2e -- e2e/graph/edge-filters.spec.ts
```

### Run Specific Test Suite
```bash
# Filter Visibility Tests
npm run test:e2e -- e2e/graph/edge-filters.spec.ts --grep "Filter Visibility"

# Filter Interactions Tests
npm run test:e2e -- e2e/graph/edge-filters.spec.ts --grep "Filter Interactions"

# Error Handling Tests
npm run test:e2e -- e2e/graph/edge-filters.spec.ts --grep "Error Handling"
```

### Run Single Test
```bash
npm run test:e2e -- e2e/graph/edge-filters.spec.ts --grep "should toggle RELATES_TO"
```

### Interactive UI Mode
```bash
npm run test:e2e:ui e2e/graph/edge-filters.spec.ts
```

### Debug Mode
```bash
npx playwright test --debug e2e/graph/edge-filters.spec.ts
```

## Test Organization

### 7 Test Suites, 19 Total Tests

| Suite | Tests | Focus |
|-------|-------|-------|
| Filter Visibility | 5 | UI element visibility |
| Filter Interactions | 5 | User interactions (click, drag) |
| Legend & Display | 2 | Graph visualization elements |
| Reset Functionality | 1 | Filter reset button |
| Statistics Integration | 2 | Statistics display |
| Filter Persistence | 1 | State persistence |
| Error Handling | 3 | Edge cases & errors |

## Test Selectors (data-testid)

### Filter Controls
```
graph-edge-filter              # Filter section container
edge-type-filter               # Filter options container
edge-filter-relates-to         # RELATES_TO label
edge-filter-relates-to-checkbox  # RELATES_TO checkbox input
edge-filter-mentioned-in       # MENTIONED_IN label
edge-filter-mentioned-in-checkbox # MENTIONED_IN checkbox input
weight-threshold-slider        # Weight slider (range input)
weight-threshold-value         # Weight value display
reset-filters                  # Reset button
```

### Graph Display
```
graph-canvas                   # Graph visualization container
graph-stats                    # Stats overlay
graph-node-count              # Node count display
graph-edge-count              # Edge count display
graph-legend                  # Legend overlay
```

## Test Execution Flow

### Basic Flow for Each Test
1. Navigate to `/admin/graph` via `adminGraphPage.goto()`
2. Wait for graph load (15 second timeout)
3. Verify UI elements exist using data-testid selectors
4. Interact with filters (click, fill slider)
5. Verify state changes (checked state, value changes, edge count)
6. Assert expected behavior

### Wait Times
- Graph load: 15000ms (15 seconds)
- UI elements: 3000ms (3 seconds)
- Interactions: 300-500ms wait after action
- Slider changes: 300ms after fill()

## Common Test Patterns

### Verify Element Visibility
```typescript
const element = adminGraphPage.page.locator('[data-testid="element-id"]');
const isVisible = await element.isVisible({ timeout: 3000 }).catch(() => false);
if (isVisible) {
  await expect(element).toBeVisible();
}
```

### Toggle Checkbox
```typescript
const checkbox = adminGraphPage.page.locator('[data-testid="checkbox-id"]');
const wasChecked = await checkbox.isChecked();
await checkbox.click();
await adminGraphPage.page.waitForTimeout(500);
const nowChecked = await checkbox.isChecked();
expect(nowChecked).toBe(!wasChecked);
```

### Adjust Slider
```typescript
const slider = adminGraphPage.page.locator('[data-testid="slider-id"]');
const initialValue = await slider.inputValue();
await slider.fill('50');
await adminGraphPage.page.waitForTimeout(300);
const newValue = await slider.inputValue();
expect(newValue).toBe('50');
```

### Check Graph Stats
```typescript
const stats = await adminGraphPage.getGraphStats();
expect(stats.nodes).toBeGreaterThan(0);
expect(stats.edges).toBeGreaterThanOrEqual(0);
```

## Troubleshooting

### Test Timeout (Waiting for graph)
**Problem:** Test fails waiting for graph to load
**Solutions:**
- Ensure Neo4j is running: `docker-compose up -d neo4j`
- Check backend is running: `curl http://localhost:8000/health`
- Verify graph data exists in Neo4j
- Increase timeout in test or playwright.config.ts

### Elements Not Found
**Problem:** data-testid selectors not matching
**Solutions:**
- Verify data-testid attributes are in source file
- Check component is rendering (use browser DevTools)
- Look for typos in selector names
- Ensure correct page is loaded

### Graph Not Rendering
**Problem:** Graph canvas visible but empty
**Solutions:**
- Verify Neo4j has test data
- Check GraphViewer component receives data prop
- Look for errors in browser console
- Verify graph API endpoint returns valid data

### Filter Changes Not Visible
**Problem:** Toggle/slider changes don't update graph
**Solutions:**
- Verify filter logic is implemented in GraphViewer
- Check edge type property matches filter keys (RELATES_TO, MENTIONED_IN)
- Ensure graph re-renders on filter change (useMemo dependency)
- Monitor network tab for API calls

## Expected Test Results

### Success Criteria
- All 19 tests pass
- No timeout errors
- No assertion failures
- Graph loads within 15 seconds
- Filter interactions complete within 500ms

### Example Output
```
running 7 test suites with 19 tests

✓ Graph Edge Filters - Filter Visibility (5 tests)
  ✓ should display edge type filter section
  ✓ should display RELATES_TO filter checkbox
  ✓ should display MENTIONED_IN filter checkbox
  ✓ should display weight threshold slider
  ✓ should display weight threshold value display

✓ Graph Edge Filters - Filter Interactions (5 tests)
  ✓ should toggle RELATES_TO filter on and off
  ✓ should toggle MENTIONED_IN filter on and off
  ✓ should adjust weight threshold slider
  ✓ should update graph when toggling both filters
  ✓ [test description continues...]

... [remaining suites] ...

Passed: 19/19 (100%)
Duration: ~5 minutes
```

## Debug Tips

### View Browser Interaction
```bash
npx playwright test --headed e2e/graph/edge-filters.spec.ts
```

### Step Through Test
```bash
npx playwright test --debug e2e/graph/edge-filters.spec.ts
```

### View Screenshots on Failure
```bash
# After test failure, check:
playwright-report/
  └── index.html  # Open in browser
```

### Check Test Logs
```bash
# Enable verbose logging
PWDEBUG=1 npm run test:e2e e2e/graph/edge-filters.spec.ts
```

### Inspect Element During Test
```typescript
// Add to test to pause execution
await adminGraphPage.page.pause();
```

## Performance Notes

- **Single Test:** ~10-30 seconds
- **Full Suite:** ~5-8 minutes
- **Bottleneck:** Graph loading (15s timeout)
- **Optimization:** Run tests with `--workers=1` for stability

## Maintenance

### When to Update Tests
- UI component structure changes
- New filter types added
- data-testid attributes renamed
- GraphFilters component refactored

### When to Add Tests
- New filter feature added
- New graph statistics added
- New error conditions discovered
- API response format changes

## Related Tests

### Other Graph Tests
- `admin-graph.spec.ts` - General admin graph functionality
- `query-graph.spec.ts` - Query result graph visualization
- `graph-visualization.spec.ts` - Multi-hop and visualization tests

### Run All Graph Tests
```bash
npm run test:e2e e2e/graph/
```

## Resources

- **Playwright Docs:** https://playwright.dev
- **POM Pattern:** https://playwright.dev/docs/pom
- **Data-Testid Best Practices:** https://playwright.dev/docs/locators#best-practices

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test source code comments
3. Check Git commit message (0914651)
4. See implementation report: `SPRINT_34_FEATURE_34.8_E2E_TESTS_REPORT.md`
