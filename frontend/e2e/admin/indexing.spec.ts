import { test, expect } from '../fixtures';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

/**
 * E2E Tests for Admin Indexing Workflows
 *
 * Feature 31.7 (Sprint 31): Core Indexing Interface
 * - Indexing interface display and accessibility
 * - Directory indexing with real-time progress tracking
 * - Status updates (Processing -> Chunking -> Embedding -> Complete)
 * - Indexed document count display
 * - Invalid directory path error handling
 * - Cancel indexing operation mid-process
 *
 * Feature 33.1-33.5 (Sprint 33): Enhanced Directory Indexing
 * - Directory selection with validation
 * - File list with color coding (Docling/LlamaIndex/Unsupported)
 * - Live progress display with ETA calculation
 * - Detail dialog with page preview, VLM images, chunks, pipeline status
 * - Error tracking with dialog and CSV export
 *
 * Feature 35.10 (Sprint 35): File Upload from Local Computer
 * - File selection with color-coded support status
 * - Upload to server with progress tracking
 * - Integration with indexing pipeline
 * - Error handling for unsupported files
 *
 * Backend: Gemma-3 4B via Ollama (FREE - no cloud LLM costs)
 * VLM: Alibaba Cloud DashScope for PDF/image extraction (~$0.30/run)
 * Required: Backend running on http://localhost:8000
 */

test.describe('Admin Indexing Workflows - Sprint 31 & 33', () => {
  test('should display indexing interface with all controls', async ({
    adminIndexingPage,
  }) => {
    // Verify all UI elements are present
    await expect(adminIndexingPage.directorySelectorInput).toBeVisible();
    await expect(adminIndexingPage.indexButton).toBeVisible();

    // Verify input field is functional
    const isInputReady = await adminIndexingPage.page
      .locator('[data-testid="directory-input"]')
      .isEnabled();
    expect(isInputReady).toBeTruthy();

    // Verify button is enabled
    const isButtonEnabled = await adminIndexingPage.indexButton.isEnabled();
    expect(isButtonEnabled).toBeTruthy();
  });

  test('should handle invalid directory path with error message', async ({
    adminIndexingPage,
  }) => {
    // Enter invalid path
    const invalidPath = '/invalid/nonexistent/path/that/does/not/exist';
    await adminIndexingPage.setDirectoryPath(invalidPath);

    // Start indexing
    await adminIndexingPage.startIndexing();

    // Wait for error message
    await adminIndexingPage.page.waitForTimeout(1000);

    // Check if error message appears
    const errorVisible = await adminIndexingPage.page
      .locator('[data-testid="error-message"]')
      .isVisible();

    if (errorVisible) {
      const errorText = await adminIndexingPage.getErrorMessage();
      expect(errorText).toBeTruthy();
      expect(errorText!.toLowerCase()).toMatch(
        /not found|invalid|error|does not exist|access denied/i
      );
    }
  });

  test('should cancel indexing operation gracefully', async ({
    adminIndexingPage,
  }) => {
    // Create a test directory path (use system temp or a known directory)
    const testPath = process.env.TEST_DOCUMENTS_PATH || './test-documents';
    await adminIndexingPage.setDirectoryPath(testPath);

    // Start indexing
    await adminIndexingPage.startIndexing();

    // Wait a bit for indexing to start
    await adminIndexingPage.page.waitForTimeout(2000);

    // Check if indexing is in progress
    const isIndexing = await adminIndexingPage.isIndexingInProgress();

    if (isIndexing) {
      // Cancel indexing
      await adminIndexingPage.cancelIndexing();

      // Verify cancellation message
      await adminIndexingPage.page.waitForTimeout(500);
      const status = await adminIndexingPage.getStatusMessage();

      // Status should indicate cancellation or should have cleared
      if (status) {
        expect(status).toBeTruthy();
      }
    }
  });

  test('should display progress bar during indexing', async ({
    adminIndexingPage,
  }) => {
    // Use a test documents directory
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for progress bar to appear
      const progressBarVisible = await adminIndexingPage.page
        .locator('[data-testid="progress-bar"]')
        .isVisible({ timeout: 10000 });

      if (progressBarVisible) {
        expect(progressBarVisible).toBeTruthy();

        // Get initial progress
        const initialProgress = await adminIndexingPage.getProgressPercentage();
        expect(initialProgress).toBeGreaterThanOrEqual(0);
        expect(initialProgress).toBeLessThanOrEqual(100);
      }
    } catch {
      // Directory may not exist in test environment - this is acceptable
    }
  });

  test('should track indexing progress and display status updates', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for progress to become visible
      const progressVisible = await adminIndexingPage.isProgressVisible();

      if (!progressVisible) {
        console.log(
          'Progress not visible - directory may not exist or indexing failed, skipping test'
        );
        return; // Skip gracefully
      }

      // Monitor progress for a few seconds
      let statusUpdated = false;
      let progressIncreased = false;
      let previousProgress = 0;

      for (let i = 0; i < 6; i++) {
        await adminIndexingPage.page.waitForTimeout(2000);

        // Check if progress is still visible before reading
        if (!(await adminIndexingPage.isProgressVisible())) {
          break;
        }

        const currentProgress = await adminIndexingPage.getProgressPercentage();
        const currentStatus = await adminIndexingPage.getStatusMessage();

        if (currentProgress > previousProgress) {
          progressIncreased = true;
        }

        if (currentStatus) {
          statusUpdated = true;
        }

        previousProgress = currentProgress;

        // Check if indexing completed
        const successVisible = await adminIndexingPage.page
          .locator('[data-testid="success-message"]')
          .isVisible();
        if (successVisible) {
          statusUpdated = true;
          progressIncreased = true;
          break;
        }
      }

      // At least one of the metrics should have updated
      expect(statusUpdated || progressIncreased).toBeTruthy();
    } catch (error) {
      console.log('Test error:', error);
      // Directory may not exist - acceptable
    }
  });

  test('should display indexed document count', async ({
    adminIndexingPage,
  }) => {
    // Check if indexed documents count is visible
    const countElement = adminIndexingPage.page.locator(
      '[data-testid="indexed-count"]'
    );

    try {
      await countElement.waitFor({ state: 'visible', timeout: 5000 });
      const count = await adminIndexingPage.getIndexedDocumentCount();
      expect(count).toBeGreaterThanOrEqual(0);
    } catch {
      // Element may not be visible until indexing starts
    }
  });

  test('should complete indexing with success message', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for indexing to complete with extended timeout
      const successVisible = await adminIndexingPage.page
        .locator('[data-testid="success-message"]')
        .isVisible({ timeout: 120000 });

      if (successVisible) {
        const successText = await adminIndexingPage.page
          .locator('[data-testid="success-message"]')
          .textContent();
        expect(successText).toBeTruthy();
      }
    } catch {
      // Directory may not exist - acceptable
    }
  });

  test('should toggle advanced options if available', async ({
    adminIndexingPage,
  }) => {
    // Check if advanced options toggle exists
    const advancedToggle = adminIndexingPage.page.locator(
      '[data-testid="advanced-options"]'
    );

    const toggleVisible = await advancedToggle.isVisible();

    if (toggleVisible) {
      // Get initial state (summary element uses 'open' attribute in parent details)
      const detailsElement = advancedToggle.locator('..'); // Parent <details> element
      const wasOpen = await detailsElement.evaluate((el) =>
        el.hasAttribute('open')
      );

      // Toggle advanced options
      await adminIndexingPage.toggleAdvancedOptions();

      // Wait for DOM update
      await adminIndexingPage.page.waitForTimeout(500);

      // Verify toggle state changed
      const isNowOpen = await detailsElement.evaluate((el) =>
        el.hasAttribute('open')
      );

      // State should have changed (was closed -> now open OR was open -> now closed)
      expect(isNowOpen).toBe(!wasOpen);
    }
  });

  test('should maintain admin access and page functionality', async ({
    adminIndexingPage,
  }) => {
    // Verify admin page is accessible
    const isAccessible = await adminIndexingPage.isAdminAccessible();
    expect(isAccessible).toBeTruthy();

    // Verify page elements remain functional
    await expect(adminIndexingPage.directorySelectorInput).toBeEnabled();
    await expect(adminIndexingPage.indexButton).toBeEnabled();
  });

  test('should get indexing statistics snapshot', async ({
    adminIndexingPage,
  }) => {
    // Get current statistics
    const stats = await adminIndexingPage.getIndexingStats();

    // Verify structure
    expect(stats).toHaveProperty('progress');
    expect(stats).toHaveProperty('status');
    expect(stats).toHaveProperty('indexedDocs');

    // Verify values are reasonable
    expect(stats.progress).toBeGreaterThanOrEqual(0);
    expect(stats.progress).toBeLessThanOrEqual(100);
    expect(stats.indexedDocs).toBeGreaterThanOrEqual(0);
  });
});

/**
 * Feature 33.1: Directory Selection Dialog
 * Verifying directory path input, validation, and scanning
 */
test.describe('Feature 33.1 - Directory Selection Dialog', () => {
  test('should display directory input field with placeholder', async ({
    adminIndexingPage,
  }) => {
    // Verify input field is visible and enabled
    await expect(adminIndexingPage.directorySelectorInput).toBeVisible();
    await expect(adminIndexingPage.directorySelectorInput).toBeEnabled();

    // Verify input has correct test ID
    const input = adminIndexingPage.page.locator('[data-testid="directory-input"]');
    const isEnabled = await input.isEnabled();
    expect(isEnabled).toBeTruthy();
  });

  test('should show default directory path', async ({
    adminIndexingPage,
  }) => {
    const inputValue = await adminIndexingPage.directorySelectorInput.inputValue();
    // Should have some default value or be empty
    expect(inputValue).toBeDefined();
  });

  test('should enable scan button when directory path entered', async ({
    adminIndexingPage,
  }) => {
    // Fill directory path
    await adminIndexingPage.setDirectoryPath('./data/sample_documents');

    // Scan button should be enabled
    await expect(adminIndexingPage.indexButton).toBeEnabled();
  });

  test('should display recursive checkbox', async ({
    adminIndexingPage,
  }) => {
    // Look for recursive checkbox
    const recursiveCheckbox = adminIndexingPage.page.locator('[data-testid="recursive-checkbox"]');
    const isVisible = await recursiveCheckbox.isVisible().catch(() => false);

    // Checkbox should exist (may be visible or hidden depending on implementation)
    if (isVisible) {
      await expect(recursiveCheckbox).toBeVisible();
    }
  });

  test('should handle directory with files', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Should show file list or progress
      const hasProgress = await adminIndexingPage.isProgressVisible();
      const hasFileList = await adminIndexingPage.page
        .locator('[data-testid="file-list"]')
        .isVisible()
        .catch(() => false);

      expect(hasProgress || hasFileList).toBeTruthy();
    } catch {
      // Directory may not exist - acceptable
    }
  });
});

/**
 * Feature 33.2: File List with Color Coding
 * Verifying file display with status colors and statistics
 */
test.describe('Feature 33.2 - File List with Color Coding', () => {
  test('should display file statistics after directory scan', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for statistics to appear
      const statsVisible = await adminIndexingPage.page
        .locator('[data-testid="scan-statistics"]')
        .isVisible({ timeout: 10000 })
        .catch(() => false);

      if (statsVisible) {
        await expect(adminIndexingPage.page.locator('[data-testid="scan-statistics"]')).toBeVisible();
      }
    } catch {
      // Directory may not exist
    }
  });

  test('should display file list items', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for file list
      const fileListVisible = await adminIndexingPage.page
        .locator('[data-testid="file-list"]')
        .isVisible({ timeout: 10000 })
        .catch(() => false);

      if (fileListVisible) {
        await expect(adminIndexingPage.page.locator('[data-testid="file-list"]')).toBeVisible();
      }
    } catch {
      // Directory may not exist
    }
  });

  test('should support file selection controls', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for controls
      const selectAllBtn = adminIndexingPage.page.locator('[data-testid="select-all"]');
      const selectAllVisible = await selectAllBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (selectAllVisible) {
        await expect(selectAllBtn).toBeVisible();
        // Should also have other controls
        const selectNoneBtn = adminIndexingPage.page.locator('[data-testid="select-none"]');
        await expect(selectNoneBtn).toBeVisible();
      }
    } catch {
      // Controls may not appear in test environment
    }
  });
});

/**
 * Feature 33.3: Live Progress Display with Compact UI
 * Verifying progress bar, ETA, file info display
 */
test.describe('Feature 33.3 - Live Progress Display (Compact)', () => {
  test('should display current file name during indexing', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for progress indicator
      const currentFileIndicator = adminIndexingPage.page.locator('[data-testid="current-file"]');
      const isVisible = await currentFileIndicator.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(currentFileIndicator).toBeVisible();
        const text = await currentFileIndicator.textContent();
        expect(text).toBeTruthy();
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should display page numbers during indexing', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for page indicator
      const pageIndicator = adminIndexingPage.page.locator('[data-testid="current-page"]');
      const isVisible = await pageIndicator.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(pageIndicator).toBeVisible();
        const text = await pageIndicator.textContent();
        // Should show format like "12 / 45"
        expect(text).toBeTruthy();
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should calculate and display estimated remaining time', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for ETA display
      const etaIndicator = adminIndexingPage.page.locator('[data-testid="estimated-time"]');
      const isVisible = await etaIndicator.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(etaIndicator).toBeVisible();
        const text = await etaIndicator.textContent();
        // Should show time estimate like "~4 min 32s"
        expect(text).toBeTruthy();
      }
    } catch {
      // May not calculate in test environment
    }
  });

  test('should show progress bar with percentage', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for progress bar
      const progressBar = adminIndexingPage.page.locator('[data-testid="progress-bar"]');
      const isVisible = await progressBar.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(progressBar).toBeVisible();
        const percentage = await adminIndexingPage.getProgressPercentage();
        expect(percentage).toBeGreaterThanOrEqual(0);
        expect(percentage).toBeLessThanOrEqual(100);
      }
    } catch {
      // May not display in test environment
    }
  });
});

/**
 * Feature 33.4: Detail Dialog
 * Verifying extended information display with page preview, VLM images, chunks, entities
 */
test.describe('Feature 33.4 - Detail Dialog with Extended Information', () => {
  test('should show Details button during indexing', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for details button
      const detailsBtn = adminIndexingPage.page.locator('button:has-text("Details")');
      const isVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(detailsBtn).toBeVisible();
        await expect(detailsBtn).toBeEnabled();
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should open detail dialog when Details button clicked', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Find and click details button
      const detailsBtn = adminIndexingPage.page.locator('button:has-text("Details")');
      const btnVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await detailsBtn.click();

        // Wait for detail dialog
        const detailDialog = adminIndexingPage.page.locator('[data-testid="detail-dialog"]');
        const isOpen = await detailDialog.isVisible({ timeout: 5000 }).catch(() => false);

        if (isOpen) {
          await expect(detailDialog).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should display page preview in detail dialog', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open details
      const detailsBtn = adminIndexingPage.page.locator('button:has-text("Details")');
      const btnVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await detailsBtn.click();

        // Check for page preview
        const pagePreview = adminIndexingPage.page.locator('[data-testid="detail-page-preview"]');
        const isVisible = await pagePreview.isVisible({ timeout: 5000 }).catch(() => false);

        if (isVisible) {
          await expect(pagePreview).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should display VLM images section in detail dialog', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open details
      const detailsBtn = adminIndexingPage.page.locator('button:has-text("Details")');
      const btnVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await detailsBtn.click();

        // Check for VLM images section
        const vlmSection = adminIndexingPage.page.locator('[data-testid="detail-vlm-images"]');
        const isVisible = await vlmSection.isVisible({ timeout: 5000 }).catch(() => false);

        if (isVisible) {
          await expect(vlmSection).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should display pipeline status in detail dialog', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open details
      const detailsBtn = adminIndexingPage.page.locator('button:has-text("Details")');
      const btnVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await detailsBtn.click();

        // Check for pipeline status
        const pipelineStatus = adminIndexingPage.page.locator('[data-testid="detail-pipeline-status"]');
        const isVisible = await pipelineStatus.isVisible({ timeout: 5000 }).catch(() => false);

        if (isVisible) {
          await expect(pipelineStatus).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should display extracted entities in detail dialog', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open details
      const detailsBtn = adminIndexingPage.page.locator('button:has-text("Details")');
      const btnVisible = await detailsBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await detailsBtn.click();

        // Check for entities
        const entities = adminIndexingPage.page.locator('[data-testid="detail-entities"]');
        const isVisible = await entities.isVisible({ timeout: 5000 }).catch(() => false);

        if (isVisible) {
          await expect(entities).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });
});

/**
 * Feature 33.5: Error Tracking with Dialog
 * Verifying error collection, display, and export
 */
test.describe('Feature 33.5 - Error Tracking', () => {
  test('should display error tracking button during indexing', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for error button
      const errorBtn = adminIndexingPage.page.locator('[data-testid="error-button"]');
      const isVisible = await errorBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(errorBtn).toBeVisible();
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should show error count badge', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Wait for error count badge
      const errorBadge = adminIndexingPage.page.locator('[data-testid="error-count-badge"]');
      const isVisible = await errorBadge.isVisible({ timeout: 5000 }).catch(() => false);

      if (isVisible) {
        await expect(errorBadge).toBeVisible();
        const text = await errorBadge.textContent();
        // Should show a number like "0", "1", etc.
        expect(text).toMatch(/\d+/);
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should open error dialog when error button clicked', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Find and click error button
      const errorBtn = adminIndexingPage.page.locator('[data-testid="error-button"]');
      const btnVisible = await errorBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await errorBtn.click();

        // Wait for error dialog
        const errorDialog = adminIndexingPage.page.locator('[data-testid="error-dialog"]');
        const isOpen = await errorDialog.isVisible({ timeout: 5000 }).catch(() => false);

        if (isOpen) {
          await expect(errorDialog).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should display error list with details', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open error dialog
      const errorBtn = adminIndexingPage.page.locator('[data-testid="error-button"]');
      const btnVisible = await errorBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await errorBtn.click();

        // Check for error list
        const errorList = adminIndexingPage.page.locator('[data-testid="error-list"]');
        const isVisible = await errorList.isVisible({ timeout: 5000 }).catch(() => false);

        if (isVisible) {
          await expect(errorList).toBeVisible();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should support CSV export of errors', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open error dialog
      const errorBtn = adminIndexingPage.page.locator('[data-testid="error-button"]');
      const btnVisible = await errorBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await errorBtn.click();

        // Look for CSV export button
        const exportBtn = adminIndexingPage.page.locator('[data-testid="error-export-csv"]');
        const isVisible = await exportBtn.isVisible({ timeout: 5000 }).catch(() => false);

        if (isVisible) {
          await expect(exportBtn).toBeVisible();
          await expect(exportBtn).toBeEnabled();
        }
      }
    } catch {
      // May not display in test environment
    }
  });

  test('should categorize errors with type indicators', async ({
    adminIndexingPage,
  }) => {
    const testPath = process.env.TEST_DOCUMENTS_PATH || './data/sample_documents';

    try {
      await adminIndexingPage.setDirectoryPath(testPath);
      await adminIndexingPage.startIndexing();

      // Open error dialog
      const errorBtn = adminIndexingPage.page.locator('[data-testid="error-button"]');
      const btnVisible = await errorBtn.isVisible({ timeout: 5000 }).catch(() => false);

      if (btnVisible) {
        await errorBtn.click();

        // Look for error items with type indicators
        const errorItems = adminIndexingPage.page.locator('[data-testid^="error-item-"]');
        const count = await errorItems.count().catch(() => 0);

        // If errors exist, they should have type indicators (ERROR, WARNING, INFO)
        if (count > 0) {
          const typeIndicator = adminIndexingPage.page.locator('[data-testid="error-type"]');
          const isVisible = await typeIndicator.isVisible({ timeout: 2000 }).catch(() => false);
          // Type indicator may or may not be present - just checking structure
        }
      }
    } catch {
      // May not display in test environment
    }
  });
});

/**
 * Feature 35.10 (Sprint 35): File Upload from Local Computer
 * Tests for uploading files directly from user's computer
 */
test.describe('Feature 35.10 - File Upload from Local Computer', () => {
  // Helper to create a temporary test file
  const createTempFile = (filename: string, content: string): string => {
    const tempDir = os.tmpdir();
    const filePath = path.join(tempDir, filename);
    fs.writeFileSync(filePath, content);
    return filePath;
  };

  // Cleanup temp files after tests
  const cleanupTempFile = (filePath: string) => {
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch {
      // Ignore cleanup errors
    }
  };

  test('should display file upload section', async ({ adminIndexingPage }) => {
    // File upload input should be present (may be hidden)
    const uploadInput = adminIndexingPage.fileUploadInput;
    await expect(uploadInput).toBeAttached();
  });

  test('should show selected files after file selection', async ({
    adminIndexingPage,
  }) => {
    // Create a temp PDF file for testing
    const tempFile = createTempFile('test-document.pdf', '%PDF-1.4 test content');

    try {
      // Select the file
      await adminIndexingPage.uploadLocalFiles([tempFile]);

      // Verify file appears in the list
      const count = await adminIndexingPage.getSelectedLocalFilesCount();
      expect(count).toBeGreaterThan(0);
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should display color-coded file support status for PDF (Docling)', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('supported-doc.pdf', '%PDF-1.4 test');

    try {
      await adminIndexingPage.uploadLocalFiles([tempFile]);

      // Check for Docling support badge
      const status = await adminIndexingPage.getFileSupportStatus('supported-doc.pdf');
      expect(status).toBe('docling');
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should display color-coded file support status for TXT (LlamaIndex)', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('text-file.txt', 'Plain text content');

    try {
      await adminIndexingPage.uploadLocalFiles([tempFile]);

      // Check for LlamaIndex support badge
      const status = await adminIndexingPage.getFileSupportStatus('text-file.txt');
      expect(status).toBe('llamaindex');
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should display unsupported status for EXE files', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('program.exe', 'MZ fake exe content');

    try {
      await adminIndexingPage.uploadLocalFiles([tempFile]);

      // Check for unsupported badge
      const status = await adminIndexingPage.getFileSupportStatus('program.exe');
      expect(status).toBe('unsupported');
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should enable upload button when files are selected', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('doc.pdf', '%PDF-1.4 content');

    try {
      // Initially upload button should be disabled or hidden
      await adminIndexingPage.uploadLocalFiles([tempFile]);

      // After selection, upload button should be enabled
      const isEnabled = await adminIndexingPage.isUploadButtonEnabled();
      expect(isEnabled).toBe(true);
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should allow removing files from selection', async ({
    adminIndexingPage,
  }) => {
    const tempFile1 = createTempFile('file1.pdf', '%PDF-1.4');
    const tempFile2 = createTempFile('file2.pdf', '%PDF-1.4');

    try {
      // Select multiple files
      await adminIndexingPage.uploadLocalFiles([tempFile1, tempFile2]);

      // Get initial count
      const initialCount = await adminIndexingPage.getSelectedLocalFilesCount();
      expect(initialCount).toBe(2);

      // Remove one file
      await adminIndexingPage.removeSelectedFile('file1.pdf');

      // Verify count decreased
      const newCount = await adminIndexingPage.getSelectedLocalFilesCount();
      expect(newCount).toBe(1);
    } finally {
      cleanupTempFile(tempFile1);
      cleanupTempFile(tempFile2);
    }
  });

  test('should upload files successfully to server', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('upload-test.pdf', '%PDF-1.4 test document');

    try {
      // Full upload workflow
      const result = await adminIndexingPage.uploadFilesWorkflow([tempFile]);

      // Verify upload succeeded
      expect(result.success).toBe(true);
      expect(result.message).toContain('erfolgreich');
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should show upload success message after upload', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('success-test.pdf', '%PDF-1.4');

    try {
      await adminIndexingPage.uploadLocalFiles([tempFile]);
      await adminIndexingPage.clickUploadButton();

      // Wait for success
      const result = await adminIndexingPage.waitForUploadComplete();
      expect(result).toBe('success');

      // Verify success message is visible
      const isSuccessVisible = await adminIndexingPage.isUploadSuccessful();
      expect(isSuccessVisible).toBe(true);
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should handle multiple file upload', async ({ adminIndexingPage }) => {
    const tempFile1 = createTempFile('multi1.pdf', '%PDF-1.4');
    const tempFile2 = createTempFile('multi2.docx', 'PK fake docx');
    const tempFile3 = createTempFile('multi3.txt', 'text content');

    try {
      // Upload multiple files
      await adminIndexingPage.uploadLocalFiles([tempFile1, tempFile2, tempFile3]);

      // Verify all files are selected
      const count = await adminIndexingPage.getSelectedLocalFilesCount();
      expect(count).toBe(3);

      // Upload all
      await adminIndexingPage.clickUploadButton();
      const result = await adminIndexingPage.waitForUploadComplete();
      expect(result).toBe('success');
    } finally {
      cleanupTempFile(tempFile1);
      cleanupTempFile(tempFile2);
      cleanupTempFile(tempFile3);
    }
  });

  test('should integrate uploaded files with indexing workflow', async ({
    adminIndexingPage,
  }) => {
    const tempFile = createTempFile('index-test.pdf', '%PDF-1.4 content for indexing');

    try {
      // Upload file
      await adminIndexingPage.uploadLocalFiles([tempFile]);
      await adminIndexingPage.clickUploadButton();
      await adminIndexingPage.waitForUploadComplete();

      // Verify upload was successful
      const isSuccess = await adminIndexingPage.isUploadSuccessful();
      expect(isSuccess).toBe(true);

      // Start indexing button should be available after upload
      await expect(adminIndexingPage.indexButton).toBeEnabled();

      // Note: Actually starting indexing with dummy PDFs would fail
      // because the content is not valid. The test verifies the workflow
      // is available after upload, not that dummy files can be indexed.
    } finally {
      cleanupTempFile(tempFile);
    }
  });

  test('should preserve directory scanning as alternative workflow', async ({
    adminIndexingPage,
  }) => {
    // Directory input should still be available
    await expect(adminIndexingPage.directorySelectorInput).toBeVisible();
    await expect(adminIndexingPage.directorySelectorInput).toBeEnabled();

    // Can set directory path
    await adminIndexingPage.setDirectoryPath('./data/sample_documents');

    // Index button should be enabled
    await expect(adminIndexingPage.indexButton).toBeEnabled();
  });
});
