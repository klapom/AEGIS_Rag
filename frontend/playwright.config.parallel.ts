import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Configuration - PARALLEL EXECUTION MODE
 *
 * Feature 73.8: Test Infrastructure Improvements
 *
 * This configuration enables parallel test execution for faster CI/CD pipelines.
 * Use this for E2E tests with mocked APIs (no live backend required).
 *
 * Usage:
 *   npx playwright test --config=playwright.config.parallel.ts
 *
 * Features:
 * - Parallel execution (max 4 workers)
 * - Multiple browser support (Chromium, Firefox, WebKit)
 * - Visual regression testing enabled
 * - Enhanced HTML reporting with screenshots
 * - Accessibility testing support
 *
 * IMPORTANT: Use standard playwright.config.ts for integration tests
 * that require live backend services.
 */

export default defineConfig({
  testDir: './e2e',

  /* Parallel execution for speed */
  fullyParallel: true,
  forbidOnly: !!process.env.CI,

  /* Retry failed tests in CI */
  retries: process.env.CI ? 2 : 0,

  /* Use multiple workers for parallel execution */
  workers: process.env.CI ? 2 : 4, // CI: 2 workers, Local: 4 workers

  /* Enhanced reporting */
  reporter: [
    ['html', {
      outputFolder: 'playwright-report',
      open: process.env.CI ? 'never' : 'on-failure'
    }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'], // Console output
    ...(process.env.CI ? [['github' as const]] : []), // GitHub Actions annotations
  ],

  /* Test timeout (reduced for mocked tests) */
  timeout: 30 * 1000,

  /* Expectation timeout */
  expect: {
    timeout: 10 * 1000,

    /* Visual regression tolerance (Feature 73.8) */
    toHaveScreenshot: {
      maxDiffPixels: 100, // Allow 100 pixels difference
      threshold: 0.2, // 20% threshold
    },
  },

  use: {
    /* Base URL */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5179',

    /* Trace collection */
    trace: process.env.CI ? 'retain-on-failure' : 'on-first-retry',

    /* Screenshot settings */
    screenshot: 'only-on-failure',

    /* Video recording (disabled by default for speed) */
    video: process.env.RECORD_VIDEO === 'true' ? 'retain-on-failure' : 'off',

    /* Viewport size */
    viewport: { width: 1280, height: 720 },

    /* Ignore HTTPS errors in local development */
    ignoreHTTPSErrors: true,
  },

  /* Multi-browser testing */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Enable Chrome DevTools Protocol for accessibility testing
        launchOptions: {
          args: ['--disable-dev-shm-usage'], // Prevent /dev/shm issues in CI
        },
      },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    /* Mobile testing (optional) */
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },

    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  /* Folder structure */
  outputDir: 'test-results',
  snapshotDir: 'e2e/__screenshots__',

  /* Global setup/teardown (optional) */
  // globalSetup: require.resolve('./e2e/global-setup.ts'),
  // globalTeardown: require.resolve('./e2e/global-teardown.ts'),
});
