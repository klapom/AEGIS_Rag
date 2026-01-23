/**
 * Retry Utilities for E2E Tests
 * Sprint 69 Feature 69.1: E2E Test Stabilization
 *
 * Provides robust retry logic for flaky test assertions
 * - Configurable retry count and delay
 * - Exponential backoff support
 * - Detailed error reporting
 */

import { expect, Page, Locator } from '@playwright/test';

/**
 * Retry configuration options
 */
export interface RetryOptions {
  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number;
  /** Delay between retries in ms (default: 1000) */
  retryDelay?: number;
  /** Use exponential backoff (default: false) */
  exponentialBackoff?: boolean;
  /** Log retry attempts (default: true) */
  logAttempts?: boolean;
  /** Custom error message prefix */
  errorPrefix?: string;
}

/**
 * Default retry options
 */
const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  retryDelay: 1000,
  exponentialBackoff: false,
  logAttempts: true,
  errorPrefix: 'Retry failed',
};

/**
 * Retry a function until it succeeds or max retries reached
 *
 * @param fn - Function to retry
 * @param options - Retry configuration
 * @returns Result of the function
 * @throws Error if all retries fail
 *
 * @example
 * ```typescript
 * const result = await retryAsync(
 *   async () => {
 *     const count = await page.locator('.item').count();
 *     if (count === 0) throw new Error('No items found');
 *     return count;
 *   },
 *   { maxRetries: 5, retryDelay: 500 }
 * );
 * ```
 */
export async function retryAsync<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const opts = { ...DEFAULT_RETRY_OPTIONS, ...options };
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= opts.maxRetries; attempt++) {
    try {
      const result = await fn();
      if (opts.logAttempts && attempt > 1) {
        console.log(`✓ Retry succeeded on attempt ${attempt}`);
      }
      return result;
    } catch (error) {
      lastError = error as Error;

      if (opts.logAttempts) {
        console.log(`✗ Attempt ${attempt}/${opts.maxRetries} failed: ${lastError.message}`);
      }

      if (attempt < opts.maxRetries) {
        const delay = opts.exponentialBackoff
          ? opts.retryDelay * Math.pow(2, attempt - 1)
          : opts.retryDelay;

        if (opts.logAttempts) {
          console.log(`  Retrying in ${delay}ms...`);
        }

        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw new Error(
    `${opts.errorPrefix}: All ${opts.maxRetries} attempts failed. Last error: ${lastError?.message}`
  );
}

/**
 * Retry an assertion until it passes or max retries reached
 *
 * @param assertion - Assertion function (should throw if fails)
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await retryAssertion(
 *   async () => {
 *     const count = await page.locator('.item').count();
 *     expect(count).toBe(5);
 *   },
 *   { maxRetries: 5, retryDelay: 500 }
 * );
 * ```
 */
export async function retryAssertion(
  assertion: () => Promise<void>,
  options: RetryOptions = {}
): Promise<void> {
  return retryAsync(assertion, {
    ...options,
    errorPrefix: options.errorPrefix || 'Assertion failed after retries',
  });
}

/**
 * Wait for a locator to meet a condition with retries
 *
 * @param locator - Playwright locator
 * @param condition - Condition to check (e.g., 'visible', 'hidden', 'enabled')
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await waitForLocator(page.locator('.loading'), 'hidden', {
 *   maxRetries: 10,
 *   retryDelay: 500
 * });
 * ```
 */
export async function waitForLocator(
  locator: Locator,
  condition: 'visible' | 'hidden' | 'enabled' | 'disabled' | 'attached' | 'detached',
  options: RetryOptions = {}
): Promise<void> {
  const conditionChecks = {
    visible: () => locator.isVisible(),
    hidden: () => locator.isHidden(),
    enabled: () => locator.isEnabled(),
    disabled: () => locator.isDisabled(),
    attached: async () => (await locator.count()) > 0,
    detached: async () => (await locator.count()) === 0,
  };

  await retryAsync(
    async () => {
      const result = await conditionChecks[condition]();
      if (!result) {
        throw new Error(`Locator did not meet condition: ${condition}`);
      }
    },
    {
      ...options,
      errorPrefix: options.errorPrefix || `Locator condition '${condition}' not met`,
    }
  );
}

/**
 * Wait for a count to match expected value with retries
 *
 * @param getCount - Function that returns current count
 * @param expectedCount - Expected count value
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await waitForCount(
 *   () => page.locator('.item').count(),
 *   5,
 *   { maxRetries: 10 }
 * );
 * ```
 */
export async function waitForCount(
  getCount: () => Promise<number>,
  expectedCount: number,
  options: RetryOptions = {}
): Promise<void> {
  await retryAsync(
    async () => {
      const count = await getCount();
      if (count !== expectedCount) {
        throw new Error(`Count mismatch: expected ${expectedCount}, got ${count}`);
      }
    },
    {
      ...options,
      errorPrefix: options.errorPrefix || 'Count condition not met',
    }
  );
}

/**
 * Wait for text to appear in a locator with retries
 *
 * @param locator - Playwright locator
 * @param expectedText - Text or regex pattern to match
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await waitForText(
 *   page.locator('.status'),
 *   /complete/i,
 *   { maxRetries: 5 }
 * );
 * ```
 */
export async function waitForText(
  locator: Locator,
  expectedText: string | RegExp,
  options: RetryOptions = {}
): Promise<void> {
  await retryAsync(
    async () => {
      const text = (await locator.textContent()) || '';
      const matches =
        typeof expectedText === 'string'
          ? text.includes(expectedText)
          : expectedText.test(text);

      if (!matches) {
        throw new Error(
          `Text mismatch: expected "${expectedText}", got "${text.substring(0, 100)}..."`
        );
      }
    },
    {
      ...options,
      errorPrefix: options.errorPrefix || 'Text condition not met',
    }
  );
}

/**
 * Wait for network idle state with retries
 *
 * @param page - Playwright page
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await waitForNetworkIdle(page, { maxRetries: 5, retryDelay: 2000 });
 * ```
 */
export async function waitForNetworkIdle(
  page: Page,
  options: RetryOptions = {}
): Promise<void> {
  await retryAsync(
    async () => {
      await page.waitForLoadState('networkidle', {
        timeout: options.retryDelay || 5000,
      });
    },
    {
      ...options,
      errorPrefix: options.errorPrefix || 'Network did not become idle',
    }
  );
}

/**
 * Retry a Playwright expect assertion with custom retry logic
 *
 * This is useful for assertions that may fail temporarily due to async updates
 *
 * @param assertion - Expect assertion function
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await retryExpect(
 *   () => expect(page.locator('.count')).toHaveText('5'),
 *   { maxRetries: 5 }
 * );
 * ```
 */
export async function retryExpect(
  assertion: () => Promise<void>,
  options: RetryOptions = {}
): Promise<void> {
  return retryAssertion(assertion, {
    ...options,
    errorPrefix: options.errorPrefix || 'Expect assertion failed after retries',
  });
}

/**
 * Wait for a condition to be true with custom polling
 *
 * @param condition - Condition function that returns boolean or Promise<boolean>
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await waitForCondition(
 *   async () => {
 *     const count = await page.locator('.item').count();
 *     return count > 0 && count < 10;
 *   },
 *   { maxRetries: 10, retryDelay: 500 }
 * );
 * ```
 */
export async function waitForCondition(
  condition: () => boolean | Promise<boolean>,
  options: RetryOptions = {}
): Promise<void> {
  await retryAsync(
    async () => {
      const result = await condition();
      if (!result) {
        throw new Error('Condition not met');
      }
    },
    {
      ...options,
      errorPrefix: options.errorPrefix || 'Condition not met after retries',
    }
  );
}

/**
 * Retry a page action (click, fill, etc.) with automatic waiting
 *
 * @param action - Action function to retry
 * @param options - Retry configuration
 *
 * @example
 * ```typescript
 * await retryAction(
 *   () => page.locator('.submit-btn').click(),
 *   { maxRetries: 3 }
 * );
 * ```
 */
export async function retryAction(
  action: () => Promise<void>,
  options: RetryOptions = {}
): Promise<void> {
  return retryAsync(action, {
    ...options,
    errorPrefix: options.errorPrefix || 'Action failed after retries',
    retryDelay: options.retryDelay || 500, // Shorter delay for actions
  });
}

/**
 * Wait for API response with retries
 *
 * @param page - Playwright page
 * @param urlPattern - URL pattern to match (string or regex)
 * @param options - Retry configuration
 * @returns Response object
 *
 * @example
 * ```typescript
 * const response = await waitForResponse(
 *   page,
 *   /\/api\/v1\/chat/,
 *   { maxRetries: 5 }
 * );
 * ```
 */
export async function waitForResponse(
  page: Page,
  urlPattern: string | RegExp,
  options: RetryOptions = {}
): Promise<any> {
  return retryAsync(
    async () => {
      const response = await page.waitForResponse(
        (resp) => {
          const url = resp.url();
          return typeof urlPattern === 'string'
            ? url.includes(urlPattern)
            : urlPattern.test(url);
        },
        { timeout: options.retryDelay || 5000 }
      );

      if (!response.ok()) {
        throw new Error(`Response not OK: ${response.status()}`);
      }

      return response;
    },
    {
      ...options,
      errorPrefix: options.errorPrefix || 'Response not received',
    }
  );
}

/**
 * Utility to create a custom retry function with preset options
 *
 * @param defaultOptions - Default retry options to use
 * @returns Custom retry function
 *
 * @example
 * ```typescript
 * const retryWithBackoff = createRetryFunction({
 *   maxRetries: 5,
 *   retryDelay: 1000,
 *   exponentialBackoff: true
 * });
 *
 * await retryWithBackoff(async () => {
 *   // Your test logic
 * });
 * ```
 */
export function createRetryFunction(defaultOptions: RetryOptions) {
  return <T>(fn: () => Promise<T>, overrideOptions?: RetryOptions): Promise<T> => {
    return retryAsync(fn, { ...defaultOptions, ...overrideOptions });
  };
}

/**
 * Presets for common retry scenarios
 */
export const RetryPresets = {
  /** Quick retries for fast-changing UI (3 retries, 500ms delay) */
  QUICK: { maxRetries: 3, retryDelay: 500, logAttempts: false },

  /** Standard retries for normal async operations (3 retries, 1s delay) */
  STANDARD: { maxRetries: 3, retryDelay: 1000 },

  /** Patient retries for slow operations (5 retries, 2s delay) */
  PATIENT: { maxRetries: 5, retryDelay: 2000 },

  /** Aggressive retries with backoff (10 retries, exponential backoff) */
  AGGRESSIVE: { maxRetries: 10, retryDelay: 500, exponentialBackoff: true },

  /** LLM response retries (3 retries, 5s delay) */
  LLM_RESPONSE: { maxRetries: 3, retryDelay: 5000 },

  /** Network retries (5 retries, 2s delay, backoff) */
  NETWORK: { maxRetries: 5, retryDelay: 2000, exponentialBackoff: true },

  /**
   * Sprint 118: Follow-up questions retries (30 retries, 2s delay = 60s total)
   * Matches SSE endpoint max_wait_seconds of 60s.
   * Nemotron3 Nano follow-up generation takes 20-60s on DGX Spark.
   */
  FOLLOWUP_QUESTIONS: { maxRetries: 30, retryDelay: 2000, logAttempts: false },
};
