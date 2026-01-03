/**
 * Accessibility Testing Configuration
 * Feature 73.8: Test Infrastructure Improvements
 *
 * Configuration for automated accessibility (a11y) testing using axe-core.
 *
 * Usage:
 *   import { checkA11y } from './accessibility.config';
 *   await checkA11y(page, 'Chat Page');
 *
 * Standards:
 * - WCAG 2.1 Level AA compliance
 * - Automated detection of common issues
 * - Custom rules for AEGIS RAG specific patterns
 */

import { Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Accessibility check options
 */
export interface A11yOptions {
  /**
   * WCAG level to test against
   * @default 'wcag2aa'
   */
  wcagLevel?: 'wcag2a' | 'wcag2aa' | 'wcag21aa' | 'wcag22aa';

  /**
   * Rules to disable (e.g., for false positives)
   */
  disabledRules?: string[];

  /**
   * Elements to exclude from testing (CSS selectors)
   */
  exclude?: string[];

  /**
   * Whether to throw on violations
   * @default true
   */
  throwOnViolations?: boolean;
}

/**
 * Default accessibility rules to disable
 * (These may have false positives in our specific context)
 */
const DEFAULT_DISABLED_RULES = [
  // Disable color contrast for code blocks (syntax highlighting may vary)
  // 'color-contrast', // Uncomment if needed
];

/**
 * Run accessibility checks on a page
 *
 * @param page - Playwright page object
 * @param context - Test context name for reporting
 * @param options - Accessibility testing options
 *
 * @example
 * ```typescript
 * test('chat page is accessible', async ({ page }) => {
 *   await page.goto('/');
 *   await checkA11y(page, 'Chat Page');
 * });
 * ```
 */
export async function checkA11y(
  page: Page,
  context: string,
  options: A11yOptions = {}
): Promise<void> {
  const {
    wcagLevel = 'wcag2aa',
    disabledRules = [],
    exclude = [],
    throwOnViolations = true,
  } = options;

  console.log(`[A11Y] Checking accessibility for: ${context}`);

  // Build axe analyzer
  let builder = new AxeBuilder({ page })
    .withTags([wcagLevel])
    .disableRules([...DEFAULT_DISABLED_RULES, ...disabledRules]);

  // Exclude elements if specified
  if (exclude.length > 0) {
    exclude.forEach(selector => {
      builder = builder.exclude(selector);
    });
  }

  // Run analysis
  const results = await builder.analyze();

  // Log results
  if (results.violations.length === 0) {
    console.log(`[A11Y] ✓ No violations found for: ${context}`);
  } else {
    console.log(`[A11Y] ✗ Found ${results.violations.length} violations for: ${context}`);

    results.violations.forEach((violation, index) => {
      console.log(`\n[A11Y] Violation ${index + 1}:`);
      console.log(`  Rule: ${violation.id}`);
      console.log(`  Impact: ${violation.impact}`);
      console.log(`  Description: ${violation.description}`);
      console.log(`  Help: ${violation.helpUrl}`);
      console.log(`  Affected elements: ${violation.nodes.length}`);

      violation.nodes.forEach((node, nodeIndex) => {
        console.log(`    Element ${nodeIndex + 1}:`);
        console.log(`      HTML: ${node.html}`);
        console.log(`      Target: ${node.target.join(', ')}`);
      });
    });

    if (throwOnViolations) {
      throw new Error(`[A11Y] Found ${results.violations.length} accessibility violations for: ${context}`);
    }
  }

  // Log incomplete checks (may need manual review)
  if (results.incomplete.length > 0) {
    console.log(`[A11Y] ℹ Found ${results.incomplete.length} incomplete checks (require manual review)`);
  }
}

/**
 * Check specific component for accessibility
 *
 * @param page - Playwright page object
 * @param selector - CSS selector for component to test
 * @param context - Test context name
 * @param options - Accessibility options
 *
 * @example
 * ```typescript
 * test('message input is accessible', async ({ page }) => {
 *   await page.goto('/');
 *   await checkComponentA11y(page, '[data-testid="message-input"]', 'Message Input');
 * });
 * ```
 */
export async function checkComponentA11y(
  page: Page,
  selector: string,
  context: string,
  options: A11yOptions = {}
): Promise<void> {
  console.log(`[A11Y] Checking component accessibility: ${context} (${selector})`);

  const builder = new AxeBuilder({ page })
    .withTags([options.wcagLevel || 'wcag2aa'])
    .disableRules([...DEFAULT_DISABLED_RULES, ...(options.disabledRules || [])])
    .include(selector);

  const results = await builder.analyze();

  if (results.violations.length > 0) {
    console.log(`[A11Y] ✗ Found ${results.violations.length} violations in component: ${context}`);
    results.violations.forEach(violation => {
      console.log(`  - ${violation.id}: ${violation.description}`);
    });

    if (options.throwOnViolations !== false) {
      throw new Error(`[A11Y] Component ${context} has accessibility violations`);
    }
  } else {
    console.log(`[A11Y] ✓ Component ${context} is accessible`);
  }
}

/**
 * Accessibility testing utilities
 */
export const a11y = {
  /**
   * Check full page accessibility
   */
  checkPage: checkA11y,

  /**
   * Check specific component
   */
  checkComponent: checkComponentA11y,

  /**
   * Common WCAG levels
   */
  wcagLevels: {
    A: 'wcag2a' as const,
    AA: 'wcag2aa' as const,
    AAA: 'wcag2aaa' as const,
  },

  /**
   * Common elements to exclude
   */
  commonExclusions: {
    thirdPartyWidgets: [
      '[data-third-party]',
      '.third-party-widget',
    ],
    decorativeImages: [
      '[role="presentation"]',
      '[aria-hidden="true"]',
    ],
  },
};
