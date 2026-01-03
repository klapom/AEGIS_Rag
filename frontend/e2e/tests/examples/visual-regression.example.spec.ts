import { test, expect } from '../../fixtures';
import { visual } from '../../visual-regression.config';

/**
 * Visual Regression Testing Examples
 * Feature 73.8: Test Infrastructure Improvements
 *
 * These tests demonstrate how to use visual regression testing
 * to catch unintended UI changes.
 *
 * To update snapshots after intentional changes:
 *   npm run test:visual:update
 */

test.describe('Visual Regression Examples @visual', () => {
  /**
   * Example 1: Full page screenshot comparison
   */
  test('chat page renders consistently', async ({ page }) => {
    // Setup: Navigate and authenticate
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Compare full page screenshot
    await visual.comparePage(page, 'chat-page-default', {
      fullPage: true,
      mask: [
        // Mask dynamic content
        visual.masks.timestamps,
        visual.masks.timers,
      ],
    });
  });

  /**
   * Example 2: Component screenshot comparison
   */
  test('message input renders consistently', async ({ page }) => {
    await page.goto('/');

    const messageInput = page.getByTestId('message-input');
    await expect(messageInput).toBeVisible();

    await visual.compareComponent(messageInput, 'message-input-default', {
      threshold: 0.1, // Strict 10% threshold for components
    });
  });

  /**
   * Example 3: Responsive layout testing
   */
  test('chat page is responsive across viewports', async ({ page }) => {
    await page.goto('/');

    await visual.compareResponsive(page, 'chat-page-responsive', [
      visual.viewports.mobile,
      visual.viewports.tablet,
      visual.viewports.desktop,
    ], {
      mask: [visual.masks.timestamps],
    });
  });

  /**
   * Example 4: State-based visual testing
   */
  test('button states render correctly', async ({ page }) => {
    await page.goto('/');

    const sendButton = page.getByTestId('send-button');

    // Default state
    await visual.compareComponent(sendButton, 'send-button-default');

    // Hover state
    await sendButton.hover();
    await visual.compareComponent(sendButton, 'send-button-hover');

    // Focus state
    await sendButton.focus();
    await visual.compareComponent(sendButton, 'send-button-focus');

    // Disabled state (if applicable)
    await page.evaluate(() => {
      const btn = document.querySelector('[data-testid="send-button"]') as HTMLButtonElement;
      if (btn) btn.disabled = true;
    });
    await visual.compareComponent(sendButton, 'send-button-disabled');
  });

  /**
   * Example 5: Dark mode visual regression
   */
  test('chat page renders correctly in dark mode', async ({ page }) => {
    await page.goto('/');

    // Toggle dark mode (adjust selector as needed)
    const darkModeToggle = page.locator('[data-testid="theme-toggle"]');
    if (await darkModeToggle.isVisible().catch(() => false)) {
      await darkModeToggle.click();
      await page.waitForTimeout(500); // Allow theme transition

      await visual.comparePage(page, 'chat-page-dark-mode', {
        fullPage: true,
      });
    } else {
      test.skip();
    }
  });
});
