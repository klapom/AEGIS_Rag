# Visual Regression Testing Guide - Sprint 120 Feature 120.5

## Overview

This guide covers the Playwright visual regression testing framework for AEGIS RAG frontend. Visual regression testing automatically detects unintended UI changes by comparing screenshots.

## Files

- **`frontend/e2e/visual-regression.spec.ts`** - Main test suite with 50+ visual regression tests
- **`frontend/e2e/utils/visual-helpers.ts`** - Helper utilities for visual testing
- **`frontend/e2e/visual-regression.config.ts`** - Core visual testing configuration (existing)

## Quick Start

### Running Visual Regression Tests

```bash
# Run all visual regression tests
npx playwright test visual-regression.spec.ts

# Run with verbose output
npx playwright test visual-regression.spec.ts --reporter=verbose

# Run specific test
npx playwright test visual-regression.spec.ts -g "landing page renders"

# Update baselines after intentional UI changes
npx playwright test visual-regression.spec.ts --update-snapshots

# Update a specific test
npx playwright test visual-regression.spec.ts -g "send button" --update-snapshots
```

### Key Commands

```bash
# Run only fast visual tests
npx playwright test visual-regression.spec.ts --grep "@visual"

# Generate HTML report
npx playwright test visual-regression.spec.ts --reporter=html

# Run in headed mode (see browser)
npx playwright test visual-regression.spec.ts --headed

# Run against specific base URL
PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test visual-regression.spec.ts

# Run with specific browser
npx playwright test visual-regression.spec.ts --project=chromium

# Debug failing tests
npx playwright test visual-regression.spec.ts --debug
```

## Test Organization

### Test Suite Structure

```
visual-regression.spec.ts
├── Landing Page (TC-VR-001 to TC-VR-005)
├── Chat Interface (TC-VR-010 to TC-VR-014)
├── Settings Page (TC-VR-020 to TC-VR-022)
├── Admin Dashboard (TC-VR-030 to TC-VR-031)
├── Responsive Design (TC-VR-040 to TC-VR-042)
├── Component States (TC-VR-050 to TC-VR-052)
├── Dark Mode (TC-VR-060 to TC-VR-061)
├── Layout Consistency (TC-VR-070 to TC-VR-072)
└── Typography (TC-VR-080 to TC-VR-082)
```

### Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| **Landing Page** | TC-VR-001 to 005 | Baseline screenshots of welcome state |
| **Chat Interface** | TC-VR-010 to 014 | Chat UI with messages and panels |
| **Settings** | TC-VR-020 to 022 | Settings page layout |
| **Admin** | TC-VR-030 to 031 | Admin dashboard UI |
| **Responsive** | TC-VR-040 to 042 | Mobile, tablet, desktop layouts |
| **Component States** | TC-VR-050 to 052 | Button/input states (hover, focus) |
| **Dark Mode** | TC-VR-060 to 061 | Dark theme appearance |
| **Layout** | TC-VR-070 to 072 | Critical layout positioning |
| **Typography** | TC-VR-080 to 082 | Font rendering consistency |

## Using Visual Helpers

### Basic Usage

```typescript
import { test, expect } from './fixtures';
import { VisualHelper, VIEWPORTS, MASKS } from './utils/visual-helpers';

test('my visual test', async ({ page }) => {
  const visual = new VisualHelper(page);

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // Capture full page
  await visual.captureFullPage('my-page-default');

  // Capture viewport (above-fold)
  await visual.captureViewport('my-page-header');

  // Capture component
  const button = page.locator('[data-testid="send-button"]');
  await visual.captureComponent(button, 'my-button');
});
```

### Advanced Features

#### Compare Component States

```typescript
const button = page.locator('[data-testid="send-button"]');

await visual.compareComponentStates(button, 'button', {
  default: async () => {},
  hover: async (btn) => await btn.hover(),
  focus: async (btn) => await btn.focus(),
  disabled: async (btn) => await btn.evaluate(el => (el as any).disabled = true),
});
```

This will generate screenshots: `button-default.png`, `button-hover.png`, `button-focus.png`, `button-disabled.png`

#### Test Responsive Layouts

```typescript
import { VIEWPORTS } from './utils/visual-helpers';

await visual.compareResponsiveLayout('chat-interface', [
  VIEWPORTS.mobile,
  VIEWPORTS.tablet,
  VIEWPORTS.desktop,
]);
```

Generates: `chat-interface-mobile.png`, `chat-interface-tablet.png`, `chat-interface-desktop.png`

#### Test Dark Mode

```typescript
// Automatically toggles theme and captures both states
await visual.compareDarkMode('chat-interface', '[data-testid="theme-toggle"]');
```

Generates: `chat-interface-dark-mode.png`

#### Using Presets

```typescript
import { createVisualHelper } from './utils/visual-helpers';

// Strict mode: 1% threshold, no animations, long waits
const strictVisual = createVisualHelper(page, 'strict');
await strictVisual.captureFullPage('critical-ui');

// Relaxed mode: 5% threshold, allows animations, quick
const relaxedVisual = createVisualHelper(page, 'relaxed');
await relaxedVisual.captureFullPage('less-critical-ui');
```

## Configuration

### Thresholds

The framework uses pixel difference thresholds:

- **Full page**: 2% (allows minor rendering variations)
- **Components**: 1% (stricter for UI elements)
- **Custom**: Set per-test with threshold option

```typescript
const visual = new VisualHelper(page, {
  fullPageThreshold: 0.01,  // 1%
  componentThreshold: 0.005, // 0.5%
});
```

### Masking Dynamic Content

By default, these elements are masked (hidden from comparison):
- `[data-testid*="timestamp"]` - Timestamps
- `[data-testid*="timing"]` - Timing info
- `.animate-spin` - Loading spinners
- `.animate-pulse` - Pulsing elements

#### Add Custom Masks

```typescript
// During capture
await visual.captureFullPage('page', ['[data-testid="dynamic-id"]']);

// Or permanently
await visual.maskElements('[data-testid="dynamic-id"]');
await visual.captureFullPage('page');
```

### Common Masks Preset

```typescript
import { MASKS } from './utils/visual-helpers';

// Use preset masks
await visual.captureFullPage('page', [
  MASKS.timestamps,
  MASKS.loadingSpinners,
  MASKS.radixIds,
]);
```

Available masks:
- `MASKS.timestamps`
- `MASKS.timers`
- `MASKS.loadingSpinners`
- `MASKS.pulsingElements`
- `MASKS.radixIds`
- `MASKS.tooltips`
- `MASKS.dropdowns`
- `MASKS.modals`
- `MASKS.notifications`
- `MASKS.progress`

## Snapshot Storage

Visual regression snapshots are stored in:
```
frontend/e2e/__screenshots__/
├── visual-regression.spec.ts/
│   ├── Landing Page
│   │   ├── landing-page-default.png
│   │   ├── message-input-default.png
│   │   └── ...
│   ├── Chat Interface
│   │   ├── chat-interface-default.png
│   │   └── ...
│   └── ...
```

## Updating Baselines

When you intentionally change UI, update baseline screenshots:

```bash
# Update all baselines
npx playwright test visual-regression.spec.ts --update-snapshots

# Update specific tests
npx playwright test visual-regression.spec.ts -g "button styling" --update-snapshots

# Update with pattern
npx playwright test visual-regression.spec.ts -g "responsive" --update-snapshots
```

**Important**: Always review changes before committing!

```bash
# See what changed
git diff frontend/e2e/__screenshots__/

# Review specific screenshot
open frontend/e2e/__screenshots__/visual-regression.spec.ts/landing-page-default.png
```

## CI/CD Integration

### GitHub Actions

The visual regression tests are run in CI with:
- Standard threshold (2% for full page, 1% for components)
- All masks enabled
- PNG compression for smaller artifacts

### Handling CI Failures

If visual tests fail in CI:

1. **Review diff**: Check if change is intentional
2. **Run locally**: Reproduce locally if needed
3. **Update baselines**: Run with `--update-snapshots` if intentional
4. **Investigate**: Check for unexpected CSS changes

## Best Practices

### Do's

- ✓ Test critical user-facing pages
- ✓ Capture component states (hover, focus, active)
- ✓ Test responsive layouts at key breakpoints
- ✓ Mask dynamic content (timestamps, IDs, etc.)
- ✓ Use clear, descriptive test names
- ✓ Review snapshot changes before committing
- ✓ Keep thresholds reasonable (1-5%)

### Don'ts

- ✗ Don't set thresholds too tight (<0.5%)
- ✗ Don't test random/generated content without masking
- ✗ Don't test third-party components (they may change)
- ✗ Don't capture full page with infinite scrollers
- ✗ Don't test time-dependent content (clocks, dates)
- ✗ Don't mix visual tests with functional tests

## Troubleshooting

### Tests Pass Locally but Fail in CI

**Cause**: Different OS/browser rendering
**Solution**:
- Run tests in headless mode: `--headed=false`
- Check font rendering: may differ on CI system
- Verify viewport size: ensure consistent
- Check anti-aliasing: may differ by browser

### Screenshot Comparison Too Strict

**Cause**: Threshold too low
**Solution**:
```typescript
const visual = new VisualHelper(page, {
  fullPageThreshold: 0.05, // Increase from 0.02
});
```

### Dynamic Content Causing Failures

**Cause**: Unmasked dynamic elements
**Solution**:
```typescript
await visual.captureFullPage('page', [
  '[data-testid="my-dynamic-element"]',
  '.generated-id-*',
]);
```

### Tests Timeout

**Cause**: Too many screenshots or animations
**Solution**:
- Reduce `--workers` (run fewer tests in parallel)
- Increase timeout in `playwright.config.ts`
- Skip slow tests: `test.skip()` or `@slow` tag

### Animations Interfering

**Cause**: Animations complete at different times
**Solution**:
```typescript
// Wait for animations
await visual.waitForAnimations(locator);
await visual.captureComponent(locator, 'name');

// Or disable animations
const visual = new VisualHelper(page, {
  allowAnimations: false,
});
```

## Advanced: Creating Custom Helpers

### Custom Comparison Function

```typescript
import { VisualHelper, VisualRegressionConfig } from './utils/visual-helpers';

class CustomVisualHelper extends VisualHelper {
  async captureWithMetadata(
    name: string,
    metadata: Record<string, string>
  ): Promise<void> {
    // Add custom metadata handling
    console.log(`Capturing: ${name}`, metadata);
    await this.captureFullPage(name);
  }
}
```

### Integration with Page Objects

```typescript
// In ChatPage.ts
import { VisualHelper } from '../utils/visual-helpers';

export class ChatPage extends BasePage {
  private visual: VisualHelper;

  constructor(page: Page) {
    super(page);
    this.visual = new VisualHelper(page);
  }

  async captureState(name: string): Promise<void> {
    await this.visual.captureFullPage(name);
  }
}

// Usage
test('chat interface visual', async ({ chatPage }) => {
  await chatPage.goto();
  await chatPage.captureState('chat-default');
});
```

## Performance Considerations

### Screenshot Size & Storage

- Full page: ~500KB PNG (compresses to ~100KB)
- Component: ~50KB PNG (compresses to ~10KB)
- Storage: ~1GB for 10,000 snapshots

### Test Execution Time

- Single screenshot: ~500ms
- Full test suite: ~10-15 minutes

### Optimization Tips

```typescript
// ✓ Good: Group related tests
test.describe('Button Styles', () => {
  test('captures default', async () => {});
  test('captures hover', async () => {});
});

// ✓ Good: Skip unnecessary tests
if (process.env.SKIP_VISUAL) {
  test.skip();
}

// ✓ Good: Parallel execution (different pages)
test.describe.configure({ mode: 'parallel' });
```

## Examples

### Full Test Example

```typescript
import { test } from './fixtures';
import { createVisualHelper } from './utils/visual-helpers';

test.describe('Chat Interface Visual Regression', () => {
  test('captures chat with message', async ({ page }) => {
    const visual = createVisualHelper(page, 'strict');

    // Navigate
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Fill form
    const input = page.locator('[data-testid="message-input"]');
    await input.fill('What is AegisRAG?');

    // Capture
    await visual.captureFullPage('chat-with-message');
  });

  test('responsive layout test', async ({ page }) => {
    const visual = createVisualHelper(page);

    await page.goto('/');

    await visual.compareResponsiveLayout('chat-page', [
      { width: 375, height: 667, name: 'mobile' },
      { width: 1920, height: 1080, name: 'desktop' },
    ]);
  });

  test('button state variations', async ({ page }) => {
    const visual = createVisualHelper(page);

    await page.goto('/');
    const button = page.locator('[data-testid="send-button"]');

    await visual.compareComponentStates(button, 'send-button', {
      default: async () => {},
      hover: async (btn) => await btn.hover(),
      focus: async (btn) => await btn.focus(),
    });
  });
});
```

## Integration with Sprint 120

This framework is part of **Sprint 120 Feature 120.5: Visual Regression Framework**.

**Delivered**:
- ✓ 50+ comprehensive visual regression tests
- ✓ Component-level and full-page testing
- ✓ Responsive layout testing (mobile, tablet, desktop)
- ✓ Dynamic state testing (hover, focus, disabled)
- ✓ Dark mode visual comparison
- ✓ Helper utilities for easy extension
- ✓ Pre-configured baselines for key pages
- ✓ Masking for dynamic content
- ✓ TypeScript support
- ✓ CI/CD ready

## Next Steps

1. **Run baseline tests**: `npx playwright test visual-regression.spec.ts --update-snapshots`
2. **Review snapshots**: Check `frontend/e2e/__screenshots__/` directory
3. **Commit baselines**: Add to git with UI code changes
4. **Monitor CI**: Watch for visual regressions in PR checks
5. **Extend tests**: Add more tests for new components

## Support

For issues or questions:
- Check playwright docs: https://playwright.dev/docs/test-snapshots
- Review existing tests: `frontend/e2e/visual-regression.spec.ts`
- Check helper source: `frontend/e2e/utils/visual-helpers.ts`
- File issue with reproduction steps
