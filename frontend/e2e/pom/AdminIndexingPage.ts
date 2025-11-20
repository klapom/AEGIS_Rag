import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * Page Object for Admin Indexing
 * Handles document indexing, directory management, and progress tracking
 */
export class AdminIndexingPage extends BasePage {
  readonly indexButton: Locator;
  readonly directorySelectorInput: Locator;
  readonly filePickerButton: Locator;
  readonly progressBar: Locator;
  readonly progressPercentage: Locator;
  readonly statusMessage: Locator;
  readonly indexedDocumentsCount: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;
  readonly cancelButton: Locator;
  readonly advancedOptionsToggle: Locator;

  constructor(page: Page) {
    super(page);
    this.indexButton = page.locator('[data-testid="start-indexing"]');
    this.directorySelectorInput = page.locator('[data-testid="directory-input"]');
    this.filePickerButton = page.locator('[data-testid="browse-directory"]');
    this.progressBar = page.locator('[data-testid="progress-bar"]');
    this.progressPercentage = page.locator('[data-testid="progress-percentage"]');
    this.statusMessage = page.locator('[data-testid="indexing-status"]');
    this.indexedDocumentsCount = page.locator('[data-testid="indexed-count"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.successMessage = page.locator('[data-testid="success-message"]');
    this.cancelButton = page.locator('[data-testid="cancel-indexing"]');
    this.advancedOptionsToggle = page.locator('[data-testid="advanced-options"]');
  }

  /**
   * Navigate to admin indexing page
   */
  async goto() {
    await super.goto('/admin/indexing');
    await this.waitForNetworkIdle();
  }

  /**
   * Enter directory path
   */
  async setDirectoryPath(path: string) {
    await this.directorySelectorInput.fill(path);
  }

  /**
   * Start indexing
   */
  async startIndexing() {
    await this.indexButton.click();
    await this.page.waitForTimeout(1000); // Wait for indexing to start
  }

  /**
   * Wait for indexing to complete
   */
  async waitForIndexingComplete(timeout = 120000) {
    try {
      await this.successMessage.waitFor({ state: 'visible', timeout });
    } catch {
      // Check for error instead
      const hasError = await this.errorMessage.isVisible();
      if (hasError) {
        const errorText = await this.errorMessage.textContent();
        throw new Error(`Indexing failed: ${errorText}`);
      }
      throw new Error(`Indexing timeout after ${timeout}ms`);
    }
  }

  /**
   * Get current progress percentage
   */
  async getProgressPercentage(): Promise<number> {
    const text = await this.progressPercentage.textContent();
    const match = text?.match(/(\d+)%/);
    return match ? parseInt(match[1]) : 0;
  }

  /**
   * Get status message
   */
  async getStatusMessage(): Promise<string | null> {
    return await this.statusMessage.textContent();
  }

  /**
   * Get number of indexed documents
   */
  async getIndexedDocumentCount(): Promise<number> {
    const text = await this.indexedDocumentsCount.textContent();
    const match = text?.match(/(\d+)/);
    return match ? parseInt(match[1]) : 0;
  }

  /**
   * Get error message if indexing fails
   */
  async getErrorMessage(): Promise<string | null> {
    return await this.errorMessage.textContent();
  }

  /**
   * Cancel ongoing indexing
   */
  async cancelIndexing() {
    if (await this.cancelButton.isVisible()) {
      await this.cancelButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  /**
   * Check if indexing is in progress
   */
  async isIndexingInProgress(): Promise<boolean> {
    try {
      await this.progressBar.waitFor({ state: 'visible', timeout: 1000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Toggle advanced options
   */
  async toggleAdvancedOptions() {
    await this.advancedOptionsToggle.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Set advanced option (e.g., chunk size, model)
   */
  async setAdvancedOption(optionName: string, value: string) {
    const input = this.page.locator(
      `[data-testid="advanced-option-${optionName}"]`
    );
    await input.fill(value);
  }

  /**
   * Get indexing statistics
   */
  async getIndexingStats(): Promise<{
    progress: number;
    status: string | null;
    indexedDocs: number;
  }> {
    return {
      progress: await this.getProgressPercentage(),
      status: await this.getStatusMessage(),
      indexedDocs: await this.getIndexedDocumentCount(),
    };
  }

  /**
   * Monitor indexing progress periodically
   */
  async monitorIndexingProgress(interval = 5000, maxWait = 120000) {
    const startTime = Date.now();
    const progressHistory: number[] = [];

    while (Date.now() - startTime < maxWait) {
      const progress = await this.getProgressPercentage();
      progressHistory.push(progress);

      if (progress === 100 || (await this.successMessage.isVisible())) {
        return progressHistory;
      }

      await this.page.waitForTimeout(interval);
    }

    throw new Error(`Indexing monitoring timeout after ${maxWait}ms`);
  }

  /**
   * Check if admin page is accessible
   */
  async isAdminAccessible(): Promise<boolean> {
    try {
      const title = await this.page.title();
      return title.includes('Admin') || title.includes('Indexing');
    } catch {
      return false;
    }
  }
}
