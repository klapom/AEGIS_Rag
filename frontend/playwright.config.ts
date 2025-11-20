import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Configuration for AEGIS RAG Frontend
 *
 * IMPORTANT: CI/CD DISABLED
 * This configuration is designed for LOCAL-ONLY execution to avoid cloud LLM costs
 *
 * Manual startup required:
 * Terminal 1: Backend
 *   cd .. && poetry run python -m src.api.main
 * Terminal 2: Frontend
 *   npm run dev
 * Terminal 3: Tests
 *   npm run test:e2e
 */

export default defineConfig({
  testDir: './e2e',

  /* Run tests sequentially to avoid LLM rate limits */
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,

  /* Shared settings for all reporters */
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  /* Shared timeout for all tests (30s for LLM responses) */
  timeout: 30 * 1000,

  /* Shared expectation timeout */
  expect: {
    timeout: 10 * 1000,
  },

  use: {
    /* Use base URL for all requests */
    baseURL: 'http://localhost:5173',

    /* Collect trace when retrying failed tests */
    trace: 'retain-on-failure',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    /* Uncomment for multi-browser testing (requires more resources)
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    */
  ],

  /* IMPORTANT: Web servers disabled for local testing
   *
   * This allows you to manually manage backend/frontend startup
   * across multiple terminals to ensure proper service initialization
   * and avoid port conflicts.
   *
   * If you want automatic startup, uncomment the webServer section
   * and ensure both services are properly configured.
   *
   * Manual startup steps:
   * 1. Terminal 1: Start Backend API
   *    cd .. && poetry run python -m src.api.main
   *    - Waits for: http://localhost:8000/health
   *    - LLM: Ollama (local) + Alibaba Cloud (optional)
   *
   * 2. Terminal 2: Start Frontend Dev Server
   *    npm run dev
   *    - Waits for: http://localhost:5173
   *    - Vite with HMR enabled
   *
   * 3. Terminal 3: Run Tests
   *    npm run test:e2e
   *    - Connects to existing servers
   *
   * This approach avoids:
   * - Premature test execution before services are ready
   * - Port conflicts with existing services
   * - Unnecessary service restarts between test runs
   * - Accidental CI/CD execution (cost control!)
   */

  /* webServer: [
    {
      command: 'cd .. && poetry run python -m src.api.main',
      url: 'http://localhost:8000/health',
      timeout: 30 * 1000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      timeout: 30 * 1000,
      reuseExistingServer: !process.env.CI,
    },
  ], */
});
