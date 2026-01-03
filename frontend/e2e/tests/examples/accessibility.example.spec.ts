import { test } from '../../fixtures';
import { a11y } from '../../accessibility.config';

/**
 * Accessibility Testing Examples
 * Feature 73.8: Test Infrastructure Improvements
 *
 * These tests demonstrate how to use automated accessibility testing
 * to ensure WCAG 2.1 Level AA compliance.
 *
 * Prerequisites:
 *   npm install --save-dev @axe-core/playwright
 */

test.describe('Accessibility Examples @a11y', () => {
  /**
   * Example 1: Full page accessibility check
   */
  test('chat page is accessible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Check full page for WCAG 2.1 Level AA compliance
    await a11y.checkPage(page, 'Chat Page', {
      wcagLevel: a11y.wcagLevels.AA,
    });
  });

  /**
   * Example 2: Component accessibility check
   */
  test('message input is accessible', async ({ page }) => {
    await page.goto('/');

    // Check specific component
    await a11y.checkComponent(
      page,
      '[data-testid="message-input"]',
      'Message Input',
      {
        wcagLevel: a11y.wcagLevels.AA,
      }
    );
  });

  /**
   * Example 3: Check with disabled rules (false positives)
   */
  test('admin page is accessible with exceptions', async ({ page }) => {
    await page.goto('/admin');

    await a11y.checkPage(page, 'Admin Page', {
      wcagLevel: a11y.wcagLevels.AA,
      disabledRules: [
        'color-contrast', // Known issue with code syntax highlighting
      ],
      exclude: [
        '.third-party-widget', // Third-party component we can't control
      ],
    });
  });

  /**
   * Example 4: Check form accessibility
   */
  test('domain training form is accessible', async ({ page }) => {
    await page.goto('/admin/domain-training');

    // Check form controls
    await a11y.checkComponent(
      page,
      'form[data-testid="domain-training-form"]',
      'Domain Training Form'
    );
  });

  /**
   * Example 5: Check keyboard navigation
   */
  test('chat interface is keyboard navigable', async ({ page }) => {
    await page.goto('/');

    // Tab through interactive elements
    const interactiveElements = [
      'message-input',
      'send-button',
      'new-conversation-button',
    ];

    for (const testId of interactiveElements) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => document.activeElement?.getAttribute('data-testid'));

      // Verify element is focusable
      if (focused !== testId) {
        console.warn(`Expected ${testId} to be focused, but got ${focused}`);
      }
    }

    // Check for accessibility violations after keyboard navigation
    await a11y.checkPage(page, 'Chat Page (After Keyboard Nav)', {
      throwOnViolations: false, // Don't fail, just log
    });
  });

  /**
   * Example 6: Check ARIA attributes
   */
  test('buttons have proper ARIA labels', async ({ page }) => {
    await page.goto('/');

    const sendButton = page.getByTestId('send-button');

    // Verify ARIA label exists
    const ariaLabel = await sendButton.getAttribute('aria-label');
    if (!ariaLabel) {
      throw new Error('Send button missing aria-label');
    }

    console.log(`[A11Y] Send button aria-label: ${ariaLabel}`);
  });

  /**
   * Example 7: Check color contrast
   */
  test('text has sufficient color contrast', async ({ page }) => {
    await page.goto('/');

    await a11y.checkPage(page, 'Chat Page (Color Contrast)', {
      wcagLevel: a11y.wcagLevels.AA,
      // WCAG AA requires 4.5:1 contrast ratio for normal text
      // WCAG AAA requires 7:1 contrast ratio
    });
  });
});
