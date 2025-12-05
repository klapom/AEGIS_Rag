import { test as base, expect } from '@playwright/test';
import { ChatPage } from '../pom/ChatPage';
import { HistoryPage } from '../pom/HistoryPage';
import { SettingsPage } from '../pom/SettingsPage';
import { AdminIndexingPage } from '../pom/AdminIndexingPage';
import { AdminGraphPage } from '../pom/AdminGraphPage';
import { CostDashboardPage } from '../pom/CostDashboardPage';
import { AdminLLMConfigPage } from '../pom/AdminLLMConfigPage';

/**
 * Custom Playwright test fixtures for AEGIS RAG
 *
 * These fixtures provide Page Object Models pre-configured for each page
 * usage: test('test name', async ({ chatPage, historyPage, ... }) => { ... })
 */

type Fixtures = {
  chatPage: ChatPage;
  historyPage: HistoryPage;
  settingsPage: SettingsPage;
  adminIndexingPage: AdminIndexingPage;
  adminGraphPage: AdminGraphPage;
  costDashboardPage: CostDashboardPage;
  adminLLMConfigPage: AdminLLMConfigPage;
};

export const test = base.extend<Fixtures>({
  /**
   * Chat Page Fixture
   * Navigates to / and provides ChatPage object
   */
  chatPage: async ({ page }, use) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    await use(chatPage);
  },

  /**
   * History Page Fixture
   * Navigates to /history and provides HistoryPage object
   */
  historyPage: async ({ page }, use) => {
    const historyPage = new HistoryPage(page);
    await historyPage.goto();
    await use(historyPage);
  },

  /**
   * Settings Page Fixture
   * Navigates to /settings and provides SettingsPage object
   */
  settingsPage: async ({ page }, use) => {
    const settingsPage = new SettingsPage(page);
    await settingsPage.goto();
    await use(settingsPage);
  },

  /**
   * Admin Indexing Page Fixture
   * Navigates to /admin/indexing and provides AdminIndexingPage object
   */
  adminIndexingPage: async ({ page }, use) => {
    const adminIndexingPage = new AdminIndexingPage(page);
    await adminIndexingPage.goto();
    await use(adminIndexingPage);
  },

  /**
   * Admin Graph Page Fixture
   * Navigates to /admin/graph and provides AdminGraphPage object
   */
  adminGraphPage: async ({ page }, use) => {
    const adminGraphPage = new AdminGraphPage(page);
    await adminGraphPage.goto();
    await use(adminGraphPage);
  },

  /**
   * Cost Dashboard Page Fixture
   * Navigates to /dashboard/costs and provides CostDashboardPage object
   */
  costDashboardPage: async ({ page }, use) => {
    const costDashboardPage = new CostDashboardPage(page);
    // Tests handle navigation
    await use(costDashboardPage);
  },

  /**
   * Admin LLM Config Page Fixture
   * Navigates to /admin/llm-config and provides AdminLLMConfigPage object
   */
  adminLLMConfigPage: async ({ page }, use) => {
    const adminLLMConfigPage = new AdminLLMConfigPage(page);
    await adminLLMConfigPage.goto();
    await use(adminLLMConfigPage);
  },
});

export { expect };
