import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Page Object for Settings
 * Handles theme, display, and export/import settings
 */
export class SettingsPage extends BasePage {
  readonly themeToggle: Locator;
  readonly darkModeToggle: Locator;
  readonly lightModeButton: Locator;
  readonly darkModeButton: Locator;
  readonly exportButton: Locator;
  readonly importButton: Locator;
  readonly fileInput: Locator;
  readonly settingsTabs: Locator;
  readonly clearDataButton: Locator;
  readonly confirmButton: Locator;
  readonly cancelButton: Locator;

  constructor(page: Page) {
    super(page);
    this.themeToggle = page.locator('[data-testid="theme-toggle"]');
    this.darkModeToggle = page.locator('[data-testid="dark-mode-toggle"]');
    this.lightModeButton = page.locator('[data-testid="light-mode"]');
    this.darkModeButton = page.locator('[data-testid="dark-mode"]');
    this.exportButton = page.locator('[data-testid="export-settings"]');
    this.importButton = page.locator('[data-testid="import-settings"]');
    this.fileInput = page.locator('input[type="file"]');
    this.settingsTabs = page.locator('[data-testid="settings-tab"]');
    this.clearDataButton = page.locator('[data-testid="clear-data"]');
    this.confirmButton = page.locator('[data-testid="confirm-button"]');
    this.cancelButton = page.locator('[data-testid="cancel-button"]');
  }

  /**
   * Navigate to settings page
   */
  async goto() {
    await super.goto('/settings');
    await this.waitForNetworkIdle();
  }

  /**
   * Toggle dark mode
   */
  async toggleDarkMode() {
    await this.darkModeToggle.click();
    await this.page.waitForTimeout(300); // Animation delay
  }

  /**
   * Set theme to light
   */
  async setLightMode() {
    await this.lightModeButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Set theme to dark
   */
  async setDarkMode() {
    await this.darkModeButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Get current theme
   */
  async getCurrentTheme(): Promise<'light' | 'dark'> {
    const html = this.page.locator('html');
    const darkClass = await html.evaluate((el) =>
      el.classList.contains('dark')
    );
    return darkClass ? 'dark' : 'light';
  }

  /**
   * Export settings to file
   */
  async exportSettings() {
    const downloadPromise = this.page.waitForEvent('download');
    await this.exportButton.click();
    const download = await downloadPromise;
    return download.path();
  }

  /**
   * Import settings from file
   */
  async importSettings(filePath: string) {
    await this.fileInput.setInputFiles(filePath);
    await this.page.waitForTimeout(500);
  }

  /**
   * Click settings tab
   */
  async clickSettingsTab(tabName: string) {
    const tab = this.page.locator(`[data-testid="settings-tab-${tabName}"]`);
    await tab.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Clear all data
   */
  async clearAllData() {
    await this.clearDataButton.click();

    // Confirm in dialog
    const confirmBtn = this.page.locator('[data-testid="confirm-delete-data"]');
    if (await confirmBtn.isVisible()) {
      await confirmBtn.click();
    }

    await this.waitForNetworkIdle();
  }

  /**
   * Check if dark mode is enabled
   */
  async isDarkModeEnabled(): Promise<boolean> {
    const html = this.page.locator('html');
    const hasDarkClass = await html.evaluate((el) =>
      el.classList.contains('dark')
    );
    return hasDarkClass;
  }

  /**
   * Get settings value
   */
  async getSettingValue(key: string): Promise<string | null> {
    return await this.page.evaluate((k) => {
      return localStorage.getItem(k);
    }, key);
  }

  /**
   * Set settings value
   */
  async setSettingValue(key: string, value: string) {
    await this.page.evaluate(
      ({ k, v }) => {
        localStorage.setItem(k, v);
      },
      { k: key, v: value }
    );

    // Reload to apply changes
    await this.page.reload();
    await this.waitForNetworkIdle();
  }

  /**
   * Check if settings page is visible
   */
  async isSettingsPageVisible(): Promise<boolean> {
    return await this.isVisible('[data-testid="settings-page"]');
  }
}
