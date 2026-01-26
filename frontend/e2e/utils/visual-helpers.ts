/**
 * Visual Regression Testing Helpers - Sprint 120 Feature 120.5
 *
 * Utility functions for visual regression testing with Playwright
 * Provides helpers for:
 * - Screenshot capture and comparison
 * - Dynamic content masking
 * - Responsive layout testing
 * - Component state testing
 *
 * Usage:
 *   import { VisualHelper } from './visual-helpers';
 *   const visual = new VisualHelper(page);
 *   await visual.captureFullPage('my-test');
 *   await visual.compareComponentState(button, 'button-states');
 */

import { Page, Locator, expect } from '@playwright/test';

/**
 * Configuration for visual regression comparisons
 */
export interface VisualRegressionConfig {
  // Threshold for full page comparisons (0-1)
  fullPageThreshold?: number;
  // Threshold for component comparisons (0-1)
  componentThreshold?: number;
  // Wait time before screenshot (ms)
  waitBeforeScreenshot?: number;
  // CSS selectors to mask (hide dynamic content)
  defaultMasks?: string[];
  // Allow animations in screenshots
  allowAnimations?: boolean;
}

/**
 * Visual regression testing helper class
 * Simplifies visual regression test setup and execution
 */
export class VisualHelper {
  private page: Page;
  private config: Required<VisualRegressionConfig>;

  constructor(page: Page, config: VisualRegressionConfig = {}) {
    this.page = page;
    this.config = {
      fullPageThreshold: config.fullPageThreshold ?? 0.02,
      componentThreshold: config.componentThreshold ?? 0.01,
      waitBeforeScreenshot: config.waitBeforeScreenshot ?? 500,
      defaultMasks: config.defaultMasks ?? [
        '[data-testid*="timestamp"]',
        '[data-testid*="timing"]',
        '.animate-spin',
        '.animate-pulse',
      ],
      allowAnimations: config.allowAnimations ?? false,
    };
  }

  /**
   * Capture full page screenshot
   *
   * @param name - Screenshot name (without extension)
   * @param customMasks - Additional CSS selectors to mask
   * @param options - Additional screenshot options
   *
   * @example
   * ```typescript
   * await visual.captureFullPage('landing-page-default');
   * await visual.captureFullPage('chat-interface', ['[data-testid="loading"]']);
   * ```
   */
  async captureFullPage(
    name: string,
    customMasks: string[] = [],
    options: {
      waitMs?: number;
      omitBackground?: boolean;
    } = {}
  ): Promise<void> {
    const { waitMs = this.config.waitBeforeScreenshot, omitBackground = false } = options;

    // Wait for animations
    await this.page.waitForTimeout(waitMs);

    // Combine masks
    const allMasks = [...this.config.defaultMasks, ...customMasks];

    // Take screenshot
    await expect(this.page).toHaveScreenshot(`${name}.png`, {
      fullPage: true,
      mask: allMasks.map(selector => this.page.locator(selector)),
      threshold: this.config.fullPageThreshold,
      animations: this.config.allowAnimations ? 'allow' : 'disabled',
      omitBackground,
    });

    console.log(`✓ Full page screenshot: ${name}`);
  }

  /**
   * Capture viewport-height screenshot (typically above-fold content)
   *
   * @param name - Screenshot name
   * @param customMasks - Additional CSS selectors to mask
   *
   * @example
   * ```typescript
   * await visual.captureViewport('landing-page-header');
   * ```
   */
  async captureViewport(
    name: string,
    customMasks: string[] = []
  ): Promise<void> {
    const allMasks = [...this.config.defaultMasks, ...customMasks];

    await this.page.waitForTimeout(this.config.waitBeforeScreenshot);

    await expect(this.page).toHaveScreenshot(`${name}.png`, {
      fullPage: false,
      mask: allMasks.map(selector => this.page.locator(selector)),
      threshold: this.config.fullPageThreshold,
      animations: this.config.allowAnimations ? 'allow' : 'disabled',
    });

    console.log(`✓ Viewport screenshot: ${name}`);
  }

  /**
   * Capture component/element screenshot
   *
   * @param locator - Element locator
   * @param name - Screenshot name
   * @param customMasks - Additional CSS selectors to mask
   *
   * @example
   * ```typescript
   * const button = page.locator('[data-testid="send-button"]');
   * await visual.captureComponent(button, 'send-button-default');
   * ```
   */
  async captureComponent(
    locator: Locator,
    name: string,
    customMasks: string[] = []
  ): Promise<void> {
    const allMasks = [...this.config.defaultMasks, ...customMasks];

    await this.page.waitForTimeout(this.config.waitBeforeScreenshot);

    await expect(locator).toHaveScreenshot(`${name}.png`, {
      mask: allMasks.map(selector => this.page.locator(selector)),
      threshold: this.config.componentThreshold,
      animations: this.config.allowAnimations ? 'allow' : 'disabled',
    });

    console.log(`✓ Component screenshot: ${name}`);
  }

  /**
   * Test component across multiple states
   *
   * @param locator - Element locator
   * @param baseName - Base name for all screenshots
   * @param states - State names and setup functions
   *
   * @example
   * ```typescript
   * const button = page.locator('[data-testid="send-button"]');
   * await visual.compareComponentStates(button, 'button', {
   *   default: async () => {},
   *   hover: async (btn) => await btn.hover(),
   *   focus: async (btn) => await btn.focus(),
   * });
   * ```
   */
  async compareComponentStates(
    locator: Locator,
    baseName: string,
    states: Record<string, (locator: Locator) => Promise<void>>
  ): Promise<void> {
    for (const [stateName, setupFn] of Object.entries(states)) {
      // Reset element state
      await locator.evaluate(el => {
        el.blur();
        el.style.opacity = '1';
      });
      await this.page.waitForTimeout(300);

      // Apply state
      await setupFn(locator);
      await this.page.waitForTimeout(this.config.waitBeforeScreenshot);

      // Capture
      await this.captureComponent(locator, `${baseName}-${stateName}`);
    }
  }

  /**
   * Test responsive layout at multiple viewport sizes
   *
   * @param name - Screenshot base name
   * @param viewports - Viewport configurations
   * @param customMasks - Additional CSS selectors to mask
   * @param options - Capture options
   *
   * @example
   * ```typescript
   * await visual.compareResponsiveLayout('chat-interface', [
   *   { width: 375, height: 667, name: 'mobile' },
   *   { width: 768, height: 1024, name: 'tablet' },
   *   { width: 1920, height: 1080, name: 'desktop' },
   * ]);
   * ```
   */
  async compareResponsiveLayout(
    name: string,
    viewports: Array<{ width: number; height: number; name: string }>,
    customMasks: string[] = [],
    options: { fullPage?: boolean } = {}
  ): Promise<void> {
    const { fullPage = false } = options;

    for (const viewport of viewports) {
      console.log(`Testing responsive layout: ${viewport.name} (${viewport.width}x${viewport.height})`);

      await this.page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await this.page.waitForTimeout(500); // Allow layout to settle

      const allMasks = [...this.config.defaultMasks, ...customMasks];

      await expect(this.page).toHaveScreenshot(`${name}-${viewport.name}.png`, {
        fullPage,
        mask: allMasks.map(selector => this.page.locator(selector)),
        threshold: this.config.fullPageThreshold,
        animations: this.config.allowAnimations ? 'allow' : 'disabled',
      });

      console.log(`✓ Responsive layout: ${name}-${viewport.name}`);
    }
  }

  /**
   * Test dark mode appearance
   * Assumes theme toggle exists with common test id
   *
   * @param pageName - Name for screenshots
   * @param themeToggleSelector - CSS selector for theme toggle button
   * @param captureFullPage - Capture full page or viewport
   *
   * @example
   * ```typescript
   * await visual.compareDarkMode('chat-interface', '[data-testid="theme-toggle"]');
   * ```
   */
  async compareDarkMode(
    pageName: string,
    themeToggleSelector: string = '[data-testid*="theme"], [data-testid*="dark"]',
    captureFullPage: boolean = true
  ): Promise<void> {
    // Find toggle
    const toggle = this.page.locator(themeToggleSelector).first();
    if (!(await toggle.isVisible().catch(() => false))) {
      console.log(`⊘ Dark mode toggle not found: ${themeToggleSelector}`);
      return;
    }

    // Click to enable dark mode
    await toggle.click();
    await this.page.waitForTimeout(500); // Allow theme transition

    // Capture dark mode
    if (captureFullPage) {
      await this.captureFullPage(`${pageName}-dark-mode`);
    } else {
      await this.captureViewport(`${pageName}-dark-mode`);
    }

    // Restore light mode
    await toggle.click();
    await this.page.waitForTimeout(500);

    console.log(`✓ Dark mode comparison: ${pageName}-dark-mode`);
  }

  /**
   * Mask dynamic content in comparison
   * Temporarily hides elements that match selectors
   *
   * @param selector - CSS selector for elements to mask
   *
   * @example
   * ```typescript
   * await visual.maskElements('[data-testid*="timestamp"]');
   * await visual.captureFullPage('page-with-masked-timestamps');
   * ```
   */
  async maskElements(selector: string): Promise<void> {
    await this.page.evaluate((sel) => {
      document.querySelectorAll(sel).forEach(el => {
        const element = el as HTMLElement;
        element.style.visibility = 'hidden';
      });
    }, selector);

    this.config.defaultMasks.push(selector);
  }

  /**
   * Unmask elements (restore visibility)
   *
   * @param selector - CSS selector for elements to unmask
   */
  async unmaskElements(selector: string): Promise<void> {
    await this.page.evaluate((sel) => {
      document.querySelectorAll(sel).forEach(el => {
        const element = el as HTMLElement;
        element.style.visibility = '';
      });
    }, selector);

    const index = this.config.defaultMasks.indexOf(selector);
    if (index > -1) {
      this.config.defaultMasks.splice(index, 1);
    }
  }

  /**
   * Wait for element animations to complete
   *
   * @param locator - Element to wait for
   * @param timeoutMs - Maximum wait time
   *
   * @example
   * ```typescript
   * await visual.waitForAnimations(page.locator('.modal'));
   * await visual.captureComponent(modal, 'modal-opened');
   * ```
   */
  async waitForAnimations(locator: Locator, timeoutMs: number = 1000): Promise<void> {
    try {
      await locator.evaluate((el) => {
        return new Promise<void>(resolve => {
          const element = el as HTMLElement;
          if ('getAnimations' in element) {
            const animations = (element.getAnimations() as any[]) || [];
            if (animations.length === 0) {
              resolve();
            } else {
              Promise.all(
                animations.map(anim =>
                  anim.finished ? Promise.resolve(anim.finished) : Promise.resolve()
                )
              ).then(() => resolve());
            }
          } else {
            resolve();
          }
        });
      });
    } catch {
      // Fallback to fixed wait
      await this.page.waitForTimeout(timeoutMs);
    }
  }

  /**
   * Get visual test summary
   *
   * @returns Summary of visual test configuration
   */
  getConfig(): VisualRegressionConfig {
    return {
      fullPageThreshold: this.config.fullPageThreshold,
      componentThreshold: this.config.componentThreshold,
      waitBeforeScreenshot: this.config.waitBeforeScreenshot,
      defaultMasks: [...this.config.defaultMasks],
      allowAnimations: this.config.allowAnimations,
    };
  }

  /**
   * Reset configuration to defaults
   */
  resetConfig(): void {
    this.config.defaultMasks = [
      '[data-testid*="timestamp"]',
      '[data-testid*="timing"]',
      '.animate-spin',
      '.animate-pulse',
    ];
  }
}

/**
 * Common viewport presets for responsive testing
 */
export const VIEWPORTS = {
  mobile: { width: 375, height: 667, name: 'mobile' },
  mobileLandscape: { width: 667, height: 375, name: 'mobile-landscape' },
  tablet: { width: 768, height: 1024, name: 'tablet' },
  tabletLandscape: { width: 1024, height: 768, name: 'tablet-landscape' },
  desktop: { width: 1920, height: 1080, name: 'desktop' },
  ultrawide: { width: 2560, height: 1440, name: 'ultrawide' },
  small: { width: 320, height: 568, name: 'small' },
  large: { width: 1440, height: 900, name: 'large' },
};

/**
 * Common masking patterns for dynamic content
 */
export const MASKS = {
  timestamps: '[data-testid*="timestamp"]',
  timers: '[data-testid*="timing"]',
  loadingSpinners: '.animate-spin',
  pulsingElements: '.animate-pulse',
  radixIds: '[id^="radix-"]',
  tooltips: '[role="tooltip"]',
  dropdowns: '[role="listbox"], [role="menu"]',
  modals: '[role="dialog"]',
  notifications: '[role="alert"]',
  progress: '[role="progressbar"]',
};

/**
 * Component state testing helpers
 */
export const COMPONENT_STATES = {
  default: async (locator: Locator) => {
    await locator.blur();
  },
  hover: async (locator: Locator) => {
    await locator.hover();
  },
  focus: async (locator: Locator) => {
    await locator.focus();
  },
  active: async (locator: Locator) => {
    await locator.evaluate(el => {
      (el as HTMLElement).classList.add('active');
    });
  },
  disabled: async (locator: Locator) => {
    await locator.evaluate((el: any) => {
      el.disabled = true;
    });
  },
  loading: async (locator: Locator) => {
    await locator.evaluate(el => {
      (el as HTMLElement).classList.add('loading');
    });
  },
  error: async (locator: Locator) => {
    await locator.evaluate(el => {
      (el as HTMLElement).classList.add('error');
    });
  },
};

/**
 * Factory function to create VisualHelper with common configuration
 *
 * @param page - Playwright page object
 * @param preset - Configuration preset ('strict' | 'relaxed' | 'custom')
 * @returns VisualHelper instance
 *
 * @example
 * ```typescript
 * const visual = createVisualHelper(page, 'strict');
 * await visual.captureFullPage('critical-ui');
 *
 * const relaxedVisual = createVisualHelper(page, 'relaxed');
 * await relaxedVisual.captureFullPage('less-critical-ui');
 * ```
 */
export function createVisualHelper(
  page: Page,
  preset: 'strict' | 'relaxed' | 'custom' = 'custom',
  customConfig?: VisualRegressionConfig
): VisualHelper {
  let config: VisualRegressionConfig;

  switch (preset) {
    case 'strict':
      // Strict: 1% threshold, no animation allowance, long wait
      config = {
        fullPageThreshold: 0.01,
        componentThreshold: 0.005,
        waitBeforeScreenshot: 1000,
        allowAnimations: false,
      };
      break;

    case 'relaxed':
      // Relaxed: 5% threshold, allow animations, shorter wait
      config = {
        fullPageThreshold: 0.05,
        componentThreshold: 0.02,
        waitBeforeScreenshot: 300,
        allowAnimations: true,
      };
      break;

    case 'custom':
    default:
      config = customConfig || {};
      break;
  }

  return new VisualHelper(page, config);
}
