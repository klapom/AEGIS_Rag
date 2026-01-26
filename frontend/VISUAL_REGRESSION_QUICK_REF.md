# Visual Regression Testing - Quick Reference

## Essential Commands

```bash
# Run tests
npx playwright test visual-regression.spec.ts

# Update baselines
npx playwright test visual-regression.spec.ts --update-snapshots

# Run with options
npx playwright test visual-regression.spec.ts --headed -g "button" --reporter=verbose
```

## Test File Locations

```
frontend/e2e/
├── visual-regression.spec.ts          # Main test suite (50+ tests)
├── utils/visual-helpers.ts             # Helper utilities
├── visual-regression.config.ts         # Configuration
└── __screenshots__/                    # Baselines (generated)
```

## Basic Test

```typescript
import { test } from './fixtures';
import { VisualHelper } from './utils/visual-helpers';

test('page renders consistently', async ({ page }) => {
  const visual = new VisualHelper(page);

  await page.goto('/');
  await visual.captureFullPage('my-page');
});
```

## Helper Methods

| Method | Purpose | Example |
|--------|---------|---------|
| `captureFullPage()` | Full page screenshot | `await visual.captureFullPage('page')` |
| `captureViewport()` | Viewport-height only | `await visual.captureViewport('header')` |
| `captureComponent()` | Element screenshot | `await visual.captureComponent(button, 'btn')` |
| `compareComponentStates()` | Test multiple states | `await visual.compareComponentStates(btn, 'btn', {default: async () => {}})` |
| `compareResponsiveLayout()` | Multi-viewport test | `await visual.compareResponsiveLayout('page', [VIEWPORTS.mobile, ...])` |
| `compareDarkMode()` | Light/dark comparison | `await visual.compareDarkMode('page', '[data-testid="theme-toggle"]')` |

## Configuration Presets

```typescript
// Strict: 1% threshold, no animations
const visual = createVisualHelper(page, 'strict');

// Relaxed: 5% threshold, allows animations
const visual = createVisualHelper(page, 'relaxed');

// Custom thresholds
const visual = new VisualHelper(page, {
  fullPageThreshold: 0.02,
  componentThreshold: 0.01,
});
```

## Common Viewports

```typescript
import { VIEWPORTS } from './utils/visual-helpers';

VIEWPORTS.mobile          // 375x667
VIEWPORTS.tablet          // 768x1024
VIEWPORTS.desktop         // 1920x1080
VIEWPORTS.ultrawide       // 2560x1440
VIEWPORTS.small           // 320x568
```

## Masking Dynamic Content

```typescript
import { MASKS } from './utils/visual-helpers';

// Preset masks
[MASKS.timestamps, MASKS.loadingSpinners, MASKS.radixIds]

// Custom mask
['[data-testid="dynamic-id"]']

// Mask while testing
await visual.maskElements('[data-testid="tooltip"]');
```

## Test Categories (50 tests)

| Category | Tests | Example |
|----------|-------|---------|
| Landing Page | 5 | `TC-VR-001: landing page renders` |
| Chat Interface | 5 | `TC-VR-010: chat with message` |
| Settings | 3 | `TC-VR-020: settings layout` |
| Admin | 2 | `TC-VR-030: admin dashboard` |
| Responsive | 3 | `TC-VR-040: landing responsive` |
| States | 3 | `TC-VR-050: button states` |
| Dark Mode | 2 | `TC-VR-060: dark mode` |
| Layout | 3 | `TC-VR-070: layout consistency` |
| Typography | 3 | `TC-VR-080: typography` |

## Workflow

### First Time (Create Baselines)

```bash
cd frontend
npx playwright test visual-regression.spec.ts --update-snapshots
# Snapshots created in: e2e/__screenshots__/visual-regression.spec.ts/
git add e2e/__screenshots__/
git commit -m "test: Add visual regression baselines (Feature 120.5)"
```

### After UI Changes (Update Baselines)

```bash
# Make UI changes
npx playwright test visual-regression.spec.ts
# Review failures
npx playwright test visual-regression.spec.ts -g "specific-test" --update-snapshots
# Review changes
git diff e2e/__screenshots__/
git add e2e/__screenshots__/
git commit -m "test: Update visual regression baselines"
```

### In CI (Automatic Checks)

- Runs on every PR
- Compares against baselines
- Fails if visual differences detected
- Shows diff in test report

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Test timeout | Increase timeout in `playwright.config.ts` |
| Threshold too strict | Use `createVisualHelper(page, 'relaxed')` |
| Dynamic content failing | Mask with custom selectors |
| Different renders per browser | Use same browser preset |
| Font differences | May be OS-specific, increase threshold slightly |

## File Sizes

- Full page snapshot: ~100KB (compressed)
- Component snapshot: ~10KB (compressed)
- Test suite total: ~50-100MB

## Performance

- Single test: ~3-5s
- Full suite: ~10-15 minutes
- Parallel execution: Use `-j` flag

## Debug Failed Tests

```bash
# Run test in debug mode
npx playwright test visual-regression.spec.ts --debug

# See the diff
npx playwright test visual-regression.spec.ts --reporter=html
# Open: playwright-report/index.html

# Compare snapshots manually
diff e2e/__screenshots__/test-name.png e2e/__screenshots__/test-name-actual.png
```

## Example: Complete Test

```typescript
test('chat interface visual regression', async ({ chatPage }) => {
  const visual = new VisualHelper(chatPage.page);

  // Load page
  await chatPage.page.waitForLoadState('networkidle');

  // Test responsive
  await visual.compareResponsiveLayout('chat', [
    { width: 375, height: 667, name: 'mobile' },
    { width: 1920, height: 1080, name: 'desktop' },
  ]);

  // Test dark mode
  await visual.compareDarkMode('chat');

  // Test component states
  const button = chatPage.page.locator('[data-testid="send-button"]');
  await visual.compareComponentStates(button, 'send-btn', {
    default: async () => {},
    hover: async (b) => await b.hover(),
    focus: async (b) => await b.focus(),
  });
});
```

## Integration Points

- **Fixtures**: Uses existing `fixtures` setup
- **Page Objects**: Integrates with ChatPage, AdminPage, etc.
- **Config**: Uses `playwright.config.ts` settings
- **CI/CD**: Runs in GitHub Actions on PR
- **Reports**: HTML report with diffs

## Documentation

- Full guide: `frontend/VISUAL_REGRESSION_GUIDE.md`
- Test code: `frontend/e2e/visual-regression.spec.ts`
- Helpers: `frontend/e2e/utils/visual-helpers.ts`
- Config: `frontend/e2e/visual-regression.config.ts`

## Related Features

- **Sprint 120.1**: UI Component Library
- **Sprint 120.2**: Accessibility Testing
- **Sprint 120.3**: Performance Testing
- **Sprint 120.4**: Snapshot Testing
- **Sprint 120.5**: Visual Regression (this)

---

*Last Updated: Sprint 120 | Feature 120.5*
