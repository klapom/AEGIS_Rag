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
 * Setup authentication for a page using real UI login
 *
 * Sprint 106 Fix: Perform actual login via UI form instead of localStorage manipulation
 * This ensures the auth state is properly managed by the React app
 */
async function setupAuthMocking(page: Page): Promise<void> {
  // Navigate to login page
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // Wait for login form to be visible (React might need time to render)
  const usernameInput = page.getByPlaceholder('Enter your username');
  const passwordInput = page.getByPlaceholder('Enter your password');
  const signInButton = page.getByRole('button', { name: 'Sign In' });

  await usernameInput.waitFor({ state: 'visible', timeout: 5000 });
  await passwordInput.waitFor({ state: 'visible', timeout: 5000 });

  // Fill login form
  await usernameInput.fill(TEST_CREDENTIALS.username);
  await passwordInput.fill(TEST_CREDENTIALS.password);

  // Wait for button to be enabled (form validates on input)
  await signInButton.waitFor({ state: 'visible', timeout: 5000 });
  await expect(signInButton).toBeEnabled({ timeout: 5000 });

  // Click Sign In button
  await signInButton.click();

  // Wait for navigation away from login page (auth success)
  // Sprint 113: Increased from 10s to 30s for slow auth with LLM warmup
  // Sprint 114: Increased from 30s to 60s for Ollama warmup scenarios (P-008 fix)
  // Sprint 115: Increased from 60s to 180s for full LLM generation during auth
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 180000 });
  await page.waitForLoadState('networkidle');
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

/**
 * Navigate to a protected route with proper auth handling
 *
 * Sprint 106 Discovery: When navigating directly to a protected route,
 * the app saves the target URL and redirects back after login.
 * No need for complex navigation - just login and the app handles the redirect.
 */
async function navigateClientSide(page: Page, path: string): Promise<void> {
  // Navigate directly to target - will redirect to login with returnUrl
  await page.goto(path);
  await page.waitForLoadState('networkidle');

  // If redirected to login, perform login
  if (page.url().includes('/login')) {
    await page.getByPlaceholder('Enter your username').fill('admin');
    await page.getByPlaceholder('Enter your password').fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Wait for redirect back to the target page (app remembers the intended destination)
    // Sprint 113: Increased from 10s to 30s for slow auth with LLM warmup
    // Sprint 115: Increased from 30s to 180s for full LLM generation during auth
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 180000 });
    await page.waitForLoadState('networkidle');
  }

  // Give React a moment to fully render the page
  await page.waitForTimeout(500);
}

// Export expect, setupAuthMocking and navigateClientSide for use in individual test files
// Note: 'test' is already exported above via 'export const test = base.extend<Fixtures>({...})'
export { expect, setupAuthMocking, navigateClientSide };
