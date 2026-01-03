/**
 * Visual Regression Testing Configuration
 * Feature 73.8: Test Infrastructure Improvements
 *
 * Utilities for visual regression testing using Playwright's built-in screenshot comparison.
 *
 * Usage:
 *   import { captureScreenshot, compareScreenshot } from './visual-regression.config';
 *   await compareScreenshot(page, 'chat-page-default-state');
 *
 * Features:
 * - Automatic screenshot capture and comparison
 * - Custom thresholds per component
 * - Masked elements (dynamic content)
 * - Multiple viewport sizes
 */

import { Page, Locator, expect } from '@playwright/test';

/**
 * Visual regression options
 */
export interface VisualRegressionOptions {
  /**
   * Maximum number of differing pixels allowed
   * @default 100
   */
  maxDiffPixels?: number;

  /**
   * Threshold for pixel difference (0-1)
   * @default 0.2 (20%)
   */
  threshold?: number;

  /**
   * Elements to mask (hide dynamic content)
   * CSS selectors or Locators
   */
  mask?: Array<string | Locator>;

  /**
   * Wait for animations to complete before screenshot
   * @default true
   */
  animations?: 'disabled' | 'allow';

  /**
   * Full page screenshot
   * @default false
   */
  fullPage?: boolean;

  /**
   * Omit background (transparent)
   * @default false
   */
  omitBackground?: boolean;
}

/**
 * Default masking selectors for dynamic content
 */
const DEFAULT_MASKS = [
  '[data-testid="timing-elapsed"]', // Elapsed time counters
  '[data-testid="timing-remaining"]', // Remaining time counters
  '[data-testid="timestamp"]', // Timestamps
  '.animate-spin', // Loading spinners
  '.animate-pulse', // Pulsing animations
];

/**
 * Capture and compare screenshot
 *
 * @param page - Playwright page object
 * @param name - Screenshot name (without extension)
 * @param options - Visual regression options
 *
 * @example
 * ```typescript
 * test('chat page renders correctly', async ({ page }) => {
 *   await page.goto('/');
 *   await compareScreenshot(page, 'chat-page-default');
 * });
 * ```
 */
export async function compareScreenshot(
  page: Page,
  name: string,
  options: VisualRegressionOptions = {}
): Promise<void> {
  const {
    maxDiffPixels = 100,
    threshold = 0.2,
    mask = [],
    animations = 'disabled',
    fullPage = false,
    omitBackground = false,
  } = options;

  console.log(`[VISUAL] Capturing screenshot: ${name}`);

  // Combine default and custom masks
  const allMasks = [...DEFAULT_MASKS, ...mask];

  // Convert string selectors to Locators
  const maskLocators = allMasks.map(m =>
    typeof m === 'string' ? page.locator(m) : m
  );

  // Take screenshot and compare
  await expect(page).toHaveScreenshot(`${name}.png`, {
    maxDiffPixels,
    threshold,
    mask: maskLocators,
    animations,
    fullPage,
    omitBackground,
  });

  console.log(`[VISUAL] ✓ Screenshot comparison passed: ${name}`);
}

/**
 * Capture component screenshot
 *
 * @param locator - Playwright locator for component
 * @param name - Screenshot name
 * @param options - Visual regression options
 *
 * @example
 * ```typescript
 * test('message input renders correctly', async ({ page }) => {
 *   await page.goto('/');
 *   const input = page.getByTestId('message-input');
 *   await compareComponentScreenshot(input, 'message-input-default');
 * });
 * ```
 */
export async function compareComponentScreenshot(
  locator: Locator,
  name: string,
  options: VisualRegressionOptions = {}
): Promise<void> {
  const {
    maxDiffPixels = 50, // Stricter for components
    threshold = 0.1, // 10% for components
    mask = [],
    animations = 'disabled',
  } = options;

  console.log(`[VISUAL] Capturing component screenshot: ${name}`);

  await expect(locator).toHaveScreenshot(`${name}.png`, {
    maxDiffPixels,
    threshold,
    mask: mask as Locator[],
    animations,
  });

  console.log(`[VISUAL] ✓ Component screenshot comparison passed: ${name}`);
}

/**
 * Test responsive layouts across multiple viewports
 *
 * @param page - Playwright page object
 * @param name - Base screenshot name
 * @param viewports - Array of viewport configurations
 *
 * @example
 * ```typescript
 * test('chat page is responsive', async ({ page }) => {
 *   await page.goto('/');
 *   await compareResponsiveScreenshots(page, 'chat-page', [
 *     { width: 375, height: 667, name: 'mobile' },
 *     { width: 768, height: 1024, name: 'tablet' },
 *     { width: 1920, height: 1080, name: 'desktop' },
 *   ]);
 * });
 * ```
 */
export async function compareResponsiveScreenshots(
  page: Page,
  baseName: string,
  viewports: Array<{ width: number; height: number; name: string }>,
  options: VisualRegressionOptions = {}
): Promise<void> {
  for (const viewport of viewports) {
    console.log(`[VISUAL] Testing ${viewport.name} viewport (${viewport.width}x${viewport.height})`);

    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.waitForTimeout(500); // Allow layout to settle

    await compareScreenshot(page, `${baseName}-${viewport.name}`, options);
  }
}

/**
 * Visual regression testing utilities
 */
export const visual = {
  /**
   * Capture and compare page screenshot
   */
  comparePage: compareScreenshot,

  /**
   * Capture and compare component screenshot
   */
  compareComponent: compareComponentScreenshot,

  /**
   * Test responsive layouts
   */
  compareResponsive: compareResponsiveScreenshots,

  /**
   * Common viewport sizes
   */
  viewports: {
    mobile: { width: 375, height: 667, name: 'mobile' },
    tablet: { width: 768, height: 1024, name: 'tablet' },
    desktop: { width: 1920, height: 1080, name: 'desktop' },
    ultrawide: { width: 2560, height: 1440, name: 'ultrawide' },
  },

  /**
   * Common masking patterns
   */
  masks: {
    timestamps: '[data-testid*="timestamp"]',
    timers: '[data-testid*="timing"]',
    spinners: '.animate-spin',
    pulses: '.animate-pulse',
    randomIds: '[id^="radix-"]', // Radix UI generated IDs
  },
};
