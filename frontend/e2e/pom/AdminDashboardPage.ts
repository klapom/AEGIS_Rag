import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';
import { navigateClientSide } from '../fixtures';

/**
 * Page Object for Admin Dashboard
 * Unified admin interface for domain management, indexing, settings, and monitoring
 * Sprint 46 Feature 46.8
 */
export class AdminDashboardPage extends BasePage {
  // Main sections
  readonly dashboardHeading: Locator;
  readonly domainsSection: Locator;
  readonly indexingSection: Locator;
  readonly settingsSection: Locator;

  // Domain section
  readonly domainList: Locator;
  readonly domainItems: Locator;
  readonly addDomainButton: Locator;

  // Indexing section
  readonly indexingStats: Locator;
  readonly indexingProgressBar: Locator;

  // Settings section
  readonly settingItems: Locator;
  readonly embeddingModel: Locator;

  // Common elements
  readonly loadingSpinner: Locator;
  readonly errorMessage: Locator;
  readonly refreshButton: Locator;
  readonly lastUpdatedTime: Locator;

  constructor(page: Page) {
    super(page);
    // Main sections
    this.dashboardHeading = page.getByRole('heading', { name: /admin|dashboard/i });
    this.domainsSection = page.locator('[data-testid="dashboard-section-domains"]');
    this.indexingSection = page.locator('[data-testid="dashboard-section-indexing"]');
    this.settingsSection = page.locator('[data-testid="dashboard-section-settings"]');

    // Domain section
    this.domainList = page.locator('[data-testid="dashboard-domain-list"]');
    this.domainItems = page.locator('[data-testid="dashboard-domain-item"]');
    this.addDomainButton = page.locator('[data-testid="add-domain-button"]');

    // Indexing section
    this.indexingStats = page.locator('[data-testid="dashboard-indexing-stat"]');
    this.indexingProgressBar = page.locator('[data-testid="indexing-progress"]');

    // Settings section
    this.settingItems = page.locator('[data-testid="dashboard-setting-item"]');
    this.embeddingModel = page.locator('[data-testid="embedding-model-setting"]');

    // Common elements
    this.loadingSpinner = page.locator('[data-testid="dashboard-loading"]');
    this.errorMessage = page.locator('[data-testid="dashboard-error"]');
    this.refreshButton = page.locator('[data-testid="dashboard-refresh-button"]');
    this.lastUpdatedTime = page.locator('[data-testid="dashboard-last-updated"]');
  }

  /**
   * Navigate to admin dashboard
   * Sprint 123.7: Use navigateClientSide to preserve auth state
   */
  async goto() {
    await navigateClientSide(this.page, '/admin');
    await this.waitForNetworkIdle();
  }

  /**
   * Wait for dashboard to load (heading to be visible)
   */
  async waitForDashboard(timeout = 10000) {
    await this.dashboardHeading.waitFor({ state: 'visible', timeout });
  }

  /**
   * Click on a section header to toggle collapse/expand
   */
  async toggleSection(sectionName: 'domains' | 'indexing' | 'settings') {
    const header = this.page.locator(`[data-testid="dashboard-section-header-${sectionName}"]`);
    await header.click();
    await this.page.waitForTimeout(300); // Wait for animation
  }

  /**
   * Get number of domains in the list
   */
  async getDomainCount(): Promise<number> {
    return await this.domainItems.count();
  }

  /**
   * Get domain names from the list
   */
  async getDomainNames(): Promise<string[]> {
    const names: string[] = [];
    const count = await this.domainItems.count();
    for (let i = 0; i < count; i++) {
      const name = await this.domainItems.nth(i).locator('[data-testid="domain-name"]').textContent();
      if (name) names.push(name.trim());
    }
    return names;
  }

  /**
   * Get indexing statistics
   */
  async getIndexingStats() {
    const statElements = await this.indexingStats.all();
    const stats: Record<string, string> = {};
    for (const element of statElements) {
      const label = await element.locator('[data-testid="stat-label"]').textContent();
      const value = await element.locator('[data-testid="stat-value"]').textContent();
      if (label && value) {
        stats[label.trim()] = value.trim();
      }
    }
    return stats;
  }

  /**
   * Click refresh button to reload dashboard
   */
  async refresh() {
    await this.refreshButton.click();
    await this.waitForNetworkIdle();
  }

  /**
   * Check if dashboard is in loading state
   */
  async isLoading(): Promise<boolean> {
    return await this.loadingSpinner.isVisible({ timeout: 2000 }).catch(() => false);
  }

  /**
   * Check if error message is displayed
   */
  async hasError(): Promise<boolean> {
    return await this.errorMessage.isVisible({ timeout: 2000 }).catch(() => false);
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string | null> {
    const isError = await this.hasError();
    if (isError) {
      return await this.errorMessage.textContent();
    }
    return null;
  }

  /**
   * Click on a domain to view details
   */
  async clickDomain(index: number) {
    const domain = this.domainItems.nth(index);
    await domain.click();
    await this.waitForNetworkIdle();
  }

  /**
   * Click on a domain by name
   */
  async clickDomainByName(name: string) {
    const domain = this.page.locator(`[data-testid="dashboard-domain-item"] >> text="${name}"`);
    await domain.click();
    await this.waitForNetworkIdle();
  }

  /**
   * Get last updated timestamp
   */
  async getLastUpdated(): Promise<string | null> {
    const visible = await this.lastUpdatedTime.isVisible().catch(() => false);
    if (visible) {
      return await this.lastUpdatedTime.textContent();
    }
    return null;
  }
}
