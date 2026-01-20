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
  /* Sprint 115.4: Enable retries for all environments to handle flaky LLM tests
   * Local: 1 retry (quick feedback loop)
   * CI: 2 retries (more resilience for nightly runs)
   */
  retries: process.env.CI ? 2 : 1,
  workers: 1,

  /* Shared settings for all reporters */
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  /* Shared timeout for all tests
   * Sprint 106: 30s for real auth flow
   * Sprint 113: Increased to 180s for full flow:
   *   - Auth Login: 30s
   *   - Entity Expansion: 8.5s (Neo4j bottleneck identified)
   *   - LLM Generation: 60-90s (Nemotron3 Nano)
   *   - Buffer & React: 30s
   */
  timeout: 180 * 1000,

  /* Shared expectation timeout
   * Sprint 115: Increased from 150s to 180s (matching backend timeout)
   * The expect() assertions in waitForResponse() need the full LLM generation time:
   *   - Entity Expansion: ~8.5s
   *   - LLM Generation: 60-90s
   *   - Memory Consolidation: +30s
   *   - Streaming Complete: +30s buffer
   * Backend chat timeout: 180s (src/api/v1/chat.py)
   */
  expect: {
    timeout: 180 * 1000,
  },

  use: {
    /* Use base URL for all requests */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5179',

    /* Collect trace when retrying failed tests */
    trace: 'retain-on-failure',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',
  },

  /* Configure projects for test tiers (Sprint 115.4)
   *
   * Test Tiers:
   * - @fast: Smoke tests, basic UI checks (30s timeout) - run with: npx playwright test --grep @fast
   * - @standard: Regular E2E tests (180s timeout) - default
   * - @full: Multi-turn, integration, LLM-heavy tests (300s timeout) - run with: npx playwright test --grep @full
   *
   * Usage in tests:
   *   test('my test', { tag: '@fast' }, async ({ page }) => { ... });
   *   test.describe('suite', { tag: '@full' }, () => { ... });
   */
  projects: [
    /* Fast tier: Smoke tests, basic UI (30s timeout) */
    {
      name: 'fast',
      testMatch: /smoke\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      timeout: 30 * 1000,
      expect: { timeout: 10 * 1000 },
    },
    /* Standard tier: Regular E2E tests (180s timeout) - default */
    {
      name: 'chromium',
      testIgnore: [/smoke\.spec\.ts/, /chat-multi-turn\.spec\.ts/],
      use: { ...devices['Desktop Chrome'] },
    },
    /* Full tier: Multi-turn, integration tests (300s timeout) */
    {
      name: 'full',
      testMatch: /chat-multi-turn\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      timeout: 300 * 1000,
      expect: { timeout: 180 * 1000 },
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
   *    - Waits for: http://localhost:5179
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
