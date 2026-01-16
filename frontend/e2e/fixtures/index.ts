import { test as base, expect, Page } from '@playwright/test';
import { ChatPage } from '../pom/ChatPage';
import { HistoryPage } from '../pom/HistoryPage';
import { SettingsPage } from '../pom/SettingsPage';
import { AdminIndexingPage } from '../pom/AdminIndexingPage';
import { AdminGraphPage } from '../pom/AdminGraphPage';
import { AdminDashboardPage } from '../pom/AdminDashboardPage';
import { CostDashboardPage } from '../pom/CostDashboardPage';
import { AdminLLMConfigPage } from '../pom/AdminLLMConfigPage';
import { AdminDomainTrainingPage } from '../pom/AdminDomainTrainingPage';

/**
 * Custom Playwright test fixtures for AEGIS RAG
 *
 * These fixtures provide Page Object Models pre-configured for each page
 * usage: test('test name', async ({ chatPage, historyPage, ... }) => { ... })
 *
 * Sprint 38: Added authentication support for protected routes
 */

/**
 * Test credentials for real authentication
 * Sprint 106: Use real login instead of mocking for more robust tests
 */
const TEST_CREDENTIALS = {
  username: 'admin',
  password: 'admin123',
};

/**
 * Mock auth data (fallback for some tests)
 */
const TEST_USER = {
  username: 'admin',
  email: 'admin@aegis.local',
  created_at: '2024-01-01T00:00:00Z',
};

const TEST_TOKEN = {
  access_token: 'test-jwt-token-for-e2e-tests',
  token_type: 'bearer',
  expires_in: 3600,
  user: TEST_USER,
};

/**
 * Setup authentication mocking for a page
 * This mocks the auth endpoints and sets up localStorage with auth token
 *
 * IMPORTANT: Token storage key is 'aegis_auth_token' (from src/lib/api.ts)
 * Token format: { token: string, expiresAt: number }
 *
 * Sprint 66 Fix: Navigate to valid origin BEFORE setting localStorage
 * Sprint 106 Note: Real login attempted but too slow for test timeouts
 */
async function setupAuthMocking(page: Page): Promise<void> {
  // Mock auth endpoints
  await page.route('**/api/v1/auth/me', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(TEST_USER),
    });
  });

  await page.route('**/api/v1/auth/refresh', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(TEST_TOKEN),
    });
  });

  await page.goto('/');

  // Set auth token in localStorage
  // Format must match TokenData: { token: string, expiresAt: number }
  await page.evaluate(() => {
    const tokenData = {
      token: 'test-jwt-token-for-e2e-tests',
      expiresAt: Date.now() + 3600 * 1000, // 1 hour from now (as timestamp)
    };
    localStorage.setItem('aegis_auth_token', JSON.stringify(tokenData));
  });
}

type Fixtures = {
  chatPage: ChatPage;
  historyPage: HistoryPage;
  settingsPage: SettingsPage;
  adminIndexingPage: AdminIndexingPage;
  adminGraphPage: AdminGraphPage;
  adminDashboardPage: AdminDashboardPage;
  costDashboardPage: CostDashboardPage;
  adminLLMConfigPage: AdminLLMConfigPage;
  adminDomainTrainingPage: AdminDomainTrainingPage;
  /** Authenticated page - use for protected routes */
  authenticatedPage: Page;
  /** Authenticated chat page - with auth mocking */
  authChatPage: ChatPage;
};

export const test = base.extend<Fixtures>({
  /**
   * Chat Page Fixture
   * Navigates to / and provides ChatPage object
   * Sprint 46: Added authentication mocking for protected home route
   */
  chatPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    await use(chatPage);
  },

  /**
   * History Page Fixture
   * Navigates to /history and provides HistoryPage object
   * Sprint 46: Added authentication mocking for protected route
   */
  historyPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const historyPage = new HistoryPage(page);
    await historyPage.goto();
    await use(historyPage);
  },

  /**
   * Settings Page Fixture
   * Navigates to /settings and provides SettingsPage object
   * Sprint 46: Added authentication mocking for protected route
   */
  settingsPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await use(settingsPage);
  },

  /**
   * Admin Indexing Page Fixture
   * Navigates to /admin/indexing and provides AdminIndexingPage object
   * Sprint 38: Added authentication mocking for protected admin route
   */
  adminIndexingPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const adminIndexingPage = new AdminIndexingPage(page);
    await adminIndexingPage.goto();
    await use(adminIndexingPage);
  },

  /**
   * Admin Graph Page Fixture
   * Navigates to /admin/graph and provides AdminGraphPage object
   * Sprint 38: Added authentication mocking for protected admin route
   */
  adminGraphPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const adminGraphPage = new AdminGraphPage(page);
    await adminGraphPage.goto();
    await use(adminGraphPage);
  },

  /**
   * Admin Dashboard Page Fixture
   * Navigates to /admin and provides AdminDashboardPage object
   * Sprint 46: Unified admin interface with sections (domains, indexing, settings)
   */
  adminDashboardPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const adminDashboardPage = new AdminDashboardPage(page);
    await adminDashboardPage.goto();
    await use(adminDashboardPage);
  },

  /**
   * Cost Dashboard Page Fixture
   * Navigates to /dashboard/costs and provides CostDashboardPage object
   * Sprint 38: Added authentication mocking for protected admin route
   */
  costDashboardPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const costDashboardPage = new CostDashboardPage(page);
    // Tests handle navigation
    await use(costDashboardPage);
  },

  /**
   * Admin LLM Config Page Fixture
   * Navigates to /admin/llm-config and provides AdminLLMConfigPage object
   * Sprint 38: Added authentication mocking for protected admin route
   */
  adminLLMConfigPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const adminLLMConfigPage = new AdminLLMConfigPage(page);
    await adminLLMConfigPage.goto();
    await use(adminLLMConfigPage);
  },

  /**
   * Admin Domain Training Page Fixture
   * Navigates to /admin/domain-training and provides AdminDomainTrainingPage object
   * Sprint 45: Domain Training System (Features 45.3, 45.10, 45.12)
   */
  adminDomainTrainingPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const adminDomainTrainingPage = new AdminDomainTrainingPage(page);
    await adminDomainTrainingPage.goto();
    await use(adminDomainTrainingPage);
  },

  /**
   * Authenticated Page Fixture
   * Sets up auth mocking for protected routes
   * Sprint 38: JWT Authentication support
   */
  authenticatedPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    await use(page);
  },

  /**
   * Authenticated Chat Page Fixture
   * Chat page with auth mocking for protected routes
   * Sprint 38: JWT Authentication support
   */
  authChatPage: async ({ page }, use) => {
    await setupAuthMocking(page);
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    await use(chatPage);
  },
});

// Export setupAuthMocking for use in individual test files
export { expect, setupAuthMocking };
