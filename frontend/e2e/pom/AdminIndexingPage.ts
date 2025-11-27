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
   * Check if progress display is visible
   */
  async isProgressVisible(): Promise<boolean> {
    try {
      return await this.progressPercentage.isVisible({ timeout: 2000 });
    } catch {
      return false;
    }
  }

  /**
   * Get current progress percentage
   * Returns 0 if progress is not visible
   */
  async getProgressPercentage(): Promise<number> {
    try {
      const isVisible = await this.isProgressVisible();
      if (!isVisible) return 0;

      const text = await this.progressPercentage.textContent({ timeout: 5000 });
      const match = text?.match(/(\d+)%/);
      return match ? parseInt(match[1]) : 0;
    } catch {
      return 0; // Graceful degradation
    }
  }

  /**
   * Get status message
   */
  async getStatusMessage(): Promise<string | null> {
    try {
      const isVisible = await this.statusMessage.isVisible({ timeout: 2000 });
      if (!isVisible) return null;
      return await this.statusMessage.textContent({ timeout: 5000 });
    } catch {
      return null; // Graceful degradation
    }
  }

  /**
   * Get number of indexed documents
   */
  async getIndexedDocumentCount(): Promise<number> {
    try {
      const isVisible = await this.indexedDocumentsCount.isVisible({ timeout: 2000 });
      if (!isVisible) return 0;
      const text = await this.indexedDocumentsCount.textContent({ timeout: 5000 });
      const match = text?.match(/(\d+)/);
      return match ? parseInt(match[1]) : 0;
    } catch {
      return 0; // Graceful degradation
    }
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
   * Returns default values if elements are not visible
   */
  async getIndexingStats(): Promise<{
    progress: number;
    status: string | null;
    indexedDocs: number;
  }> {
    return {
      progress: await this.getProgressPercentage(), // Already has graceful fallback
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
   * Verifies page is on /admin/indexing and key elements are visible
   */
  async isAdminAccessible(): Promise<boolean> {
    try {
      // Check URL
      const url = this.page.url();
      if (!url.includes('/admin/indexing')) {
        return false;
      }

      // Check key elements are present
      const inputVisible = await this.directorySelectorInput.isVisible({ timeout: 2000 });
      const buttonVisible = await this.indexButton.isVisible({ timeout: 2000 });

      return inputVisible && buttonVisible;
    } catch {
      return false;
    }
  }

  /**
   * Feature 33.1: Get file statistics after directory scan
   * Returns counts of different file types found
   */
  async getFileStatistics(): Promise<{
    total: number;
    docling_supported: number;
    llamaindex_supported: number;
    unsupported: number;
  } | null> {
    try {
      const statsText = await this.page
        .locator('[data-testid="scan-statistics"]')
        .textContent({ timeout: 5000 });

      if (!statsText) return null;

      // Parse statistics from text (format depends on UI)
      // This is a placeholder - adjust based on actual format
      return {
        total: 0,
        docling_supported: 0,
        llamaindex_supported: 0,
        unsupported: 0,
      };
    } catch {
      return null;
    }
  }

  /**
   * Feature 33.2: Get list of files with their support status
   */
  async getFileList(): Promise<
    Array<{
      name: string;
      size: string;
      type: 'docling' | 'llamaindex' | 'unsupported';
    }>
  > {
    try {
      const fileItems = await this.page.locator('[data-testid="file-item-"]').all();

      const files: Array<{
        name: string;
        size: string;
        type: 'docling' | 'llamaindex' | 'unsupported';
      }> = [];

      for (const item of fileItems) {
        const name = await item.locator('[data-testid*="file-name"]').textContent();
        const size = await item.locator('[data-testid*="file-size"]').textContent();
        const classes = await item.evaluate((el) => el.className);

        let type: 'docling' | 'llamaindex' | 'unsupported' = 'unsupported';
        if (classes.includes('bg-green-700')) {
          type = 'docling';
        } else if (classes.includes('bg-green-400')) {
          type = 'llamaindex';
        }

        if (name && size) {
          files.push({
            name: name.trim(),
            size: size.trim(),
            type,
          });
        }
      }

      return files;
    } catch {
      return [];
    }
  }

  /**
   * Feature 33.3: Get current progress details
   */
  async getProgressDetails(): Promise<{
    currentFile: string | null;
    currentPage: string | null;
    totalPages: string | null;
    filesProcessed: string | null;
    totalFiles: string | null;
    percentage: number;
    estimatedTime: string | null;
  }> {
    return {
      currentFile: await this.page
        .locator('[data-testid="current-file"]')
        .textContent()
        .catch(() => null),
      currentPage: await this.page
        .locator('[data-testid="current-page"]')
        .textContent()
        .catch(() => null),
      totalPages: await this.page
        .locator('[data-testid="total-pages"]')
        .textContent()
        .catch(() => null),
      filesProcessed: await this.page
        .locator('[data-testid="files-processed"]')
        .textContent()
        .catch(() => null),
      totalFiles: await this.page
        .locator('[data-testid="total-files"]')
        .textContent()
        .catch(() => null),
      percentage: await this.getProgressPercentage(),
      estimatedTime: await this.page
        .locator('[data-testid="estimated-time"]')
        .textContent()
        .catch(() => null),
    };
  }

  /**
   * Feature 33.4: Open detail dialog
   */
  async openDetailDialog(): Promise<boolean> {
    try {
      const detailsBtn = this.page.locator('button:has-text("Details")');
      const isVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await detailsBtn.click();
        // Wait for dialog to open
        await this.page.waitForTimeout(500);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  /**
   * Feature 33.4: Close detail dialog
   */
  async closeDetailDialog(): Promise<void> {
    try {
      const closeBtn = this.page.locator('[data-testid="detail-dialog"] button:has-text("Close")');
      await closeBtn.click();
    } catch {
      // Dialog may not have close button - use Escape key
      await this.page.press('Escape');
    }
  }

  /**
   * Feature 33.4: Get detail dialog information
   */
  async getDetailDialogInfo(): Promise<{
    hasPagePreview: boolean;
    hasVLMImages: boolean;
    hasChunks: boolean;
    hasPipelineStatus: boolean;
    hasEntities: boolean;
  }> {
    return {
      hasPagePreview: await this.page
        .locator('[data-testid="detail-page-preview"]')
        .isVisible({ timeout: 2000 })
        .catch(() => false),
      hasVLMImages: await this.page
        .locator('[data-testid="detail-vlm-images"]')
        .isVisible({ timeout: 2000 })
        .catch(() => false),
      hasChunks: await this.page
        .locator('[data-testid="detail-chunk-preview"]')
        .isVisible({ timeout: 2000 })
        .catch(() => false),
      hasPipelineStatus: await this.page
        .locator('[data-testid="detail-pipeline-status"]')
        .isVisible({ timeout: 2000 })
        .catch(() => false),
      hasEntities: await this.page
        .locator('[data-testid="detail-entities"]')
        .isVisible({ timeout: 2000 })
        .catch(() => false),
    };
  }

  /**
   * Feature 33.5: Open error dialog
   */
  async openErrorDialog(): Promise<boolean> {
    try {
      const errorBtn = this.page.locator('[data-testid="error-button"]');
      const isVisible = await errorBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await errorBtn.click();
        // Wait for dialog to open
        await this.page.waitForTimeout(500);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  /**
   * Feature 33.5: Get error count
   */
  async getErrorCount(): Promise<number> {
    try {
      const text = await this.page
        .locator('[data-testid="error-count-badge"]')
        .textContent({ timeout: 2000 });
      const match = text?.match(/(\d+)/);
      return match ? parseInt(match[1]) : 0;
    } catch {
      return 0;
    }
  }

  /**
   * Feature 33.5: Get list of errors
   */
  async getErrorList(): Promise<
    Array<{
      type: 'ERROR' | 'WARNING' | 'INFO';
      timestamp: string | null;
      file: string | null;
      message: string;
    }>
  > {
    try {
      const errorItems = await this.page.locator('[data-testid^="error-item-"]').all();

      const errors: Array<{
        type: 'ERROR' | 'WARNING' | 'INFO';
        timestamp: string | null;
        file: string | null;
        message: string;
      }> = [];

      for (const item of errorItems) {
        const text = await item.textContent();
        const classes = await item.evaluate((el) => el.className);

        let type: 'ERROR' | 'WARNING' | 'INFO' = 'INFO';
        if (classes.includes('error')) type = 'ERROR';
        else if (classes.includes('warning')) type = 'WARNING';

        if (text) {
          errors.push({
            type,
            timestamp: null, // Extract from text if format known
            file: null, // Extract from text if format known
            message: text.trim(),
          });
        }
      }

      return errors;
    } catch {
      return [];
    }
  }

  /**
   * Feature 33.5: Export errors as CSV
   */
  async exportErrorsAsCSV(): Promise<boolean> {
    try {
      const exportBtn = this.page.locator('[data-testid="error-export-csv"]');
      const isVisible = await exportBtn.isVisible({ timeout: 2000 }).catch(() => false);

      if (isVisible) {
        await exportBtn.click();
        // Wait for download
        await this.page.waitForTimeout(1000);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  /**
   * Select/deselect specific files
   */
  async selectFile(fileName: string, selected: boolean): Promise<void> {
    const checkbox = this.page.locator(`[data-testid="file-checkbox-${fileName}"]`);
    const isChecked = await checkbox.isChecked().catch(() => false);

    if (selected && !isChecked) {
      await checkbox.check();
    } else if (!selected && isChecked) {
      await checkbox.uncheck();
    }
  }

  /**
   * Get all selected files
   */
  async getSelectedFiles(): Promise<string[]> {
    try {
      const checkboxes = await this.page.locator('[data-testid^="file-checkbox-"]:checked').all();

      const files: string[] = [];
      for (const checkbox of checkboxes) {
        const testId = await checkbox.getAttribute('data-testid');
        if (testId) {
          const fileName = testId.replace('file-checkbox-', '');
          files.push(fileName);
        }
      }

      return files;
    } catch {
      return [];
    }
  }
}
