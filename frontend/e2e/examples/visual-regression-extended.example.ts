/**
 * Extended Visual Regression Testing Examples - Sprint 120 Feature 120.5
 *
 * Advanced patterns for visual regression testing with custom implementations,
 * integration with Page Object Models, and specialized test scenarios.
 *
 * Note: This is an example file showing patterns. Copy snippets to your tests.
 *
 * @example
 * npx playwright test examples/visual-regression-extended.example.ts --headed
 */

import { test, expect } from '../fixtures';
import {
  VisualHelper,
  createVisualHelper,
  VIEWPORTS,
  MASKS,
  COMPONENT_STATES,
} from '../utils/visual-helpers';
import { Page, Locator } from '@playwright/test';

/**
 * Example 1: Integration with Page Object Model
 * Shows how to integrate visual helpers with existing page objects
 */
test.describe('Example 1: Visual Testing with Page Objects', () => {
  /**
   * Custom page class with visual testing methods
   */
  class ChatPageWithVisuals {
    private visual: VisualHelper;

    constructor(page: Page) {
      this.page = page;
      this.visual = createVisualHelper(page, 'strict');
    }

    private page: Page;

    async goto() {
      await this.page.goto('/');
      await this.page.waitForLoadState('networkidle');
    }

    async captureInitialState() {
      await this.visual.captureFullPage('chat-initial-state');
    }

    async sendMessage(text: string) {
      const input = this.page.locator('[data-testid="message-input"]');
      await input.fill(text);

      const button = this.page.locator('[data-testid="send-button"]');
      await button.click();

      // Wait for response
      await this.page.waitForLoadState('networkidle');
      await this.page.waitForTimeout(500);

      // Capture after message sent
      await this.visual.captureFullPage('chat-with-message');
    }

    async captureResponsive() {
      await this.visual.compareResponsiveLayout('chat-page', [
        VIEWPORTS.mobile,
        VIEWPORTS.tablet,
        VIEWPORTS.desktop,
      ]);
    }
  }

  test('TC-EXT-001: page object visual integration', async ({ page }) => {
    const chatPage = new ChatPageWithVisuals(page);

    await chatPage.goto();
    await chatPage.captureInitialState();

    // Send message and capture
    // Note: May timeout if backend not responding
    // await chatPage.sendMessage('Hello AegisRAG');

    // Capture responsive
    // await chatPage.captureResponsive();
  });
});

/**
 * Example 2: Custom Visual Comparison with A/B Testing
 * Compare two versions of the same component
 */
test.describe('Example 2: A/B Testing with Visual Regression', () => {
  test('TC-EXT-002: compare button variants', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // Capture original button
    const button = page.locator('[data-testid="send-button"]').first();
    if (await button.isVisible().catch(() => false)) {
      await visual.captureComponent(button, 'button-variant-original');

      // Simulate CSS change (in real scenario, would be an actual style change)
      await button.evaluate(el => {
        (el as HTMLElement).style.backgroundColor = 'blue';
      });
      await page.waitForTimeout(300);

      // Capture modified version
      await visual.captureComponent(button, 'button-variant-modified');

      // Restore original
      await button.evaluate(el => {
        (el as HTMLElement).style.backgroundColor = '';
      });
    }
  });
});

/**
 * Example 3: Advanced State Testing with Custom Setup
 * Test component states with complex setup/teardown
 */
test.describe('Example 3: Complex State Testing', () => {
  test('TC-EXT-003: modal states lifecycle', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // This would test a modal component if available
    // Pattern shows how to test complex state transitions

    const modal = page.locator('[role="dialog"]').first();

    // States: closed, opening, opened, closing
    const states = {
      closed: async () => {
        // Modal not visible - skip capture if not present
        const visible = await modal.isVisible().catch(() => false);
        if (!visible) {
          test.skip();
        }
      },
      opening: async () => {
        // Would need to trigger modal open
        // await page.locator('[data-testid="open-modal"]').click();
        // await visual.waitForAnimations(modal, 300);
      },
      opened: async () => {
        // Modal fully visible
        // Already open from previous state
      },
      closing: async () => {
        // Would need to trigger modal close
        // await page.locator('[data-testid="close-button"]').click();
        // await visual.waitForAnimations(modal, 300);
      },
    };

    // Test only if modal exists
    if (await modal.isVisible().catch(() => false)) {
      for (const [stateName, setup] of Object.entries(states)) {
        await setup();
        // Would capture here if states were properly set up
      }
    }
  });
});

/**
 * Example 4: Responsive Testing with Content Variations
 * Test same component across viewports with different content
 */
test.describe('Example 4: Responsive with Content Variations', () => {
  test('TC-EXT-004: input field responsive variants', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');
    const input = page.locator('[data-testid="message-input"]');

    if (!(await input.isVisible().catch(() => false))) {
      test.skip();
    }

    const testContent = [
      'Short text',
      'This is a longer message that might wrap on smaller screens',
      'Multi-line\nexample\ntext',
    ];

    for (const content of testContent) {
      // Test across viewports
      for (const viewport of [VIEWPORTS.mobile, VIEWPORTS.desktop]) {
        await page.setViewportSize({
          width: viewport.width,
          height: viewport.height,
        });
        await page.waitForTimeout(300);

        await input.fill(content);
        await page.waitForTimeout(200);

        const safeName = `input-${content.substring(0, 5).replace(/\s/g, '-')}-${viewport.name}`;
        await visual.captureComponent(input, safeName);
      }
    }
  });
});

/**
 * Example 5: Accessibility Visual Testing
 * Capture high-contrast, focus visible, and reduced-motion states
 */
test.describe('Example 5: Accessibility Visual States', () => {
  test('TC-EXT-005: focus-visible state', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');
    const button = page.locator('button').first();

    if (!(await button.isVisible().catch(() => false))) {
      test.skip();
    }

    // Simulate keyboard focus (shows focus-visible styles)
    await button.focus();
    await page.keyboard.press('Tab');
    await page.waitForTimeout(300);

    await visual.captureComponent(button, 'button-focus-visible');
  });

  test('TC-EXT-006: high contrast mode (simulated)', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // Simulate high contrast by adding CSS
    await page.evaluate(() => {
      const style = document.createElement('style');
      style.textContent = `
        body {
          filter: contrast(1.5);
        }
      `;
      document.head.appendChild(style);
    });
    await page.waitForTimeout(300);

    await visual.captureViewport('page-high-contrast');

    // Cleanup
    await page.evaluate(() => {
      document.querySelectorAll('style').forEach(el => {
        if (el.textContent?.includes('contrast')) {
          el.remove();
        }
      });
    });
  });
});

/**
 * Example 6: Custom Masking Patterns
 * Advanced masking strategies for different scenarios
 */
test.describe('Example 6: Custom Masking Patterns', () => {
  test('TC-EXT-007: selective masking', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // Mask only specific dynamic elements
    const customMasks = [
      '[data-testid="request-id"]', // API request IDs
      '.generated-hash', // Generated values
      '[aria-label*="Loading"]', // Loading indicators
    ];

    await visual.captureFullPage('page-with-selective-masks', customMasks);
  });

  test('TC-EXT-008: nested element masking', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // Mask nested elements within a container
    const containerMasks = [
      '[data-testid="chat-history"] [data-testid="timestamp"]', // Timestamps in history
      '[data-testid="messages"] .loading-indicator', // Loading in messages
    ];

    await visual.captureFullPage('page-with-nested-masks', containerMasks);
  });
});

/**
 * Example 7: Theme Switching with Multiple Variants
 * Test light, dark, and custom theme modes
 */
test.describe('Example 7: Theme Variant Testing', () => {
  test('TC-EXT-009: light theme capture', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');
    await visual.captureFullPage('page-light-theme');
  });

  test('TC-EXT-010: dark theme capture', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // Toggle dark mode if available
    const themeToggle = page.locator('[data-testid*="theme"]').first();
    if (await themeToggle.isVisible().catch(() => false)) {
      await themeToggle.click();
      await page.waitForTimeout(500);

      await visual.captureFullPage('page-dark-theme');

      // Restore light mode
      await themeToggle.click();
    }
  });
});

/**
 * Example 8: Performance-Aware Visual Testing
 * Capture pages at different network conditions / load states
 */
test.describe('Example 8: Performance States', () => {
  test('TC-EXT-011: initial load state', async ({ page }) => {
    const visual = new VisualHelper(page);

    // Simulate slow network
    await page.route('**/*', route => {
      // Add 500ms delay to all requests
      setTimeout(() => route.continue(), 500);
    });

    await page.goto('/');

    // Capture loading state
    const loadingIndicator = page.locator('.loading, [data-testid*="loading"]').first();
    if (await loadingIndicator.isVisible().catch(() => false)) {
      await visual.captureComponent(loadingIndicator, 'loading-state');
    }

    // Wait for network idle (will take longer due to throttling)
    await page.waitForLoadState('networkidle');
    await visual.captureFullPage('page-loaded');
  });
});

/**
 * Example 9: Snapshot Diff Analysis
 * Helper for analyzing what changed between snapshots
 */
test.describe('Example 9: Visual Diff Analysis', () => {
  test('TC-EXT-012: capture and analyze changes', async ({ page }) => {
    const visual = new VisualHelper(page);

    await page.goto('/');

    // Capture baseline
    await visual.captureFullPage('baseline-state');

    // Simulate some UI interaction
    const input = page.locator('[data-testid="message-input"]');
    if (await input.isVisible().catch(() => false)) {
      await input.focus();
      await input.type('Test query');
      await page.waitForTimeout(300);

      // Capture after interaction
      await visual.captureFullPage('after-interaction');

      // The diff will be shown in the Playwright report
      // Green areas = new/changed
      // Red areas = removed
      // Yellow areas = moved
    }
  });
});

/**
 * Example 10: Framework Extension
 * Creating custom visual testing class for specific use cases
 */
class ChatVisualTester {
  constructor(private visual: VisualHelper, private page: Page) {}

  async captureMessageVariants() {
    const messages = this.page.locator('[data-testid="message"]');
    const count = await messages.count();

    for (let i = 0; i < Math.min(count, 3); i++) {
      const message = messages.nth(i);
      if (await message.isVisible().catch(() => false)) {
        await this.visual.captureComponent(message, `message-variant-${i}`);
      }
    }
  }

  async captureUIStates() {
    const states: Record<string, () => Promise<void>> = {
      idle: async () => {
        // Default state
      },
      loading: async () => {
        // Would add loading class
        // await this.page.locator('body').evaluate(el =>
        //   el.classList.add('loading')
        // );
      },
      error: async () => {
        // Would add error class
        // await this.page.locator('body').evaluate(el =>
        //   el.classList.add('error')
        // );
      },
    };

    for (const [state, setup] of Object.entries(states)) {
      await setup();
      // await this.visual.captureFullPage(`chat-${state}`);
    }
  }

  async captureResponsiveDesign() {
    await this.visual.compareResponsiveLayout('chat-responsive', [
      VIEWPORTS.mobile,
      VIEWPORTS.tablet,
      VIEWPORTS.desktop,
      VIEWPORTS.ultrawide,
    ]);
  }
}

test.describe('Example 10: Custom Framework Extension', () => {
  test('TC-EXT-013: using custom visual tester', async ({ chatPage }) => {
    const visual = createVisualHelper(chatPage.page, 'strict');
    const tester = new ChatVisualTester(visual, chatPage.page);

    // Use custom methods
    // await tester.captureMessageVariants();
    // await tester.captureUIStates();
    // await tester.captureResponsiveDesign();

    // Placeholder - tests would fail without backend
    test.skip();
  });
});

/**
 * Example 11: Batch Visual Testing
 * Test multiple pages/components in a single test
 */
test.describe('Example 11: Batch Visual Testing', () => {
  test('TC-EXT-014: capture critical pages', async ({ page }) => {
    const visual = createVisualHelper(page, 'relaxed');

    const criticalPages = [
      { path: '/', name: 'landing' },
      { path: '/settings', name: 'settings' },
      // { path: '/admin', name: 'admin' },
    ];

    for (const { path, name } of criticalPages) {
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(300);

      await visual.captureFullPage(`batch-${name}`);
    }
  });
});

/**
 * Example 12: Pixel Precision Testing
 * Test specific pixel measurements and alignments
 */
test.describe('Example 12: Pixel Precision', () => {
  test('TC-EXT-015: button alignment and spacing', async ({ page }) => {
    const visual = createVisualHelper(page, 'strict');

    await page.goto('/');

    const button = page.locator('[data-testid="send-button"]').first();
    if (!(await button.isVisible().catch(() => false))) {
      test.skip();
    }

    // Get button dimensions
    const box = await button.boundingBox();
    expect(box).not.toBeNull();

    if (box) {
      // Verify minimum size for accessibility
      expect(box.width).toBeGreaterThanOrEqual(44); // WCAG min
      expect(box.height).toBeGreaterThanOrEqual(44); // WCAG min

      // Capture for visual verification
      await visual.captureComponent(button, 'button-sizing');
    }
  });
});

/**
 * Export custom classes for reuse in other tests
 */
export { ChatVisualTester };
