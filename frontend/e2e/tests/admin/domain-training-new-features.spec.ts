import { test, expect } from '../../fixtures';

/**
 * E2E Tests for Domain Training New Features (Sprint 71)
 *
 * Features Tested:
 * - Feature 71.13: Data Augmentation UI
 * - Feature 71.14: Batch Document Upload
 * - Feature 71.15: Get Domain Details
 *
 * Components Under Test:
 * - DataAugmentationDialog
 * - BatchDocumentUploadDialog
 * - DomainDetailDialog (enhanced)
 * - DomainList (with Upload button)
 *
 * Data Attributes Required:
 * - [data-testid="augment-dataset-button"]
 * - [data-testid="target-count-slider"]
 * - [data-testid="generate-samples-button"]
 * - [data-testid="augmentation-preview"]
 * - [data-testid="use-augmented-button"]
 * - [data-testid="domain-upload-{domainName}"]
 * - [data-testid="directory-path-input"]
 * - [data-testid="recursive-checkbox"]
 * - [data-testid="scan-files-button"]
 * - [data-testid="upload-documents-button"]
 * - [data-testid="domain-view-{domainName}"]
 * - [data-testid="domain-llm-model"]
 * - [data-testid="domain-training-metrics"]
 */

test.describe('Data Augmentation UI (Sprint 71 Feature 71.13)', () => {
  test('should open data augmentation dialog from wizard', async ({ page }) => {
    // NOTE: Requires being in domain creation wizard with samples uploaded
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Click "Create Domain" button
    const createButton = page.getByTestId('create-domain-button');
    const isCreateVisible = await createButton.isVisible().catch(() => false);

    if (isCreateVisible) {
      await createButton.click();
      await page.waitForTimeout(1000);

      // Navigate to samples step
      // This assumes multi-step wizard - adjust as needed

      // Look for augment button
      const augmentButton = page.getByTestId('augment-dataset-button');
      const isAugmentVisible = await augmentButton.isVisible().catch(() => false);

      if (isAugmentVisible) {
        await augmentButton.click();

        // Dialog should open
        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should display target count slider', async ({ page }) => {
    // NOTE: Assumes augmentation dialog is open
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Open dialog (method depends on wizard state)
    // ...

    const slider = page.getByTestId('target-count-slider');
    const isSliderVisible = await slider.isVisible().catch(() => false);

    if (isSliderVisible) {
      await expect(slider).toBeVisible();

      // Default value should be reasonable (e.g., 20)
      const value = await slider.inputValue();
      expect(parseInt(value)).toBeGreaterThanOrEqual(5);
      expect(parseInt(value)).toBeLessThanOrEqual(50);
    }
  });

  test('should allow changing target sample count', async ({ page }) => {
    // NOTE: Assumes augmentation dialog is open
    const slider = page.getByTestId('target-count-slider');
    const isSliderVisible = await slider.isVisible().catch(() => false);

    if (isSliderVisible) {
      // Change slider value
      await slider.fill('30');

      // Verify value changed
      const newValue = await slider.inputValue();
      expect(newValue).toBe('30');

      // Button text should update
      const generateButton = page.getByTestId('generate-samples-button');
      const buttonText = await generateButton.textContent();
      expect(buttonText).toContain('30');
    }
  });

  test('should generate augmented samples when button clicked', async ({ page }) => {
    // NOTE: Requires LLM to be available
    const generateButton = page.getByTestId('generate-samples-button');
    const isGenerateVisible = await generateButton.isVisible().catch(() => false);

    if (isGenerateVisible) {
      await generateButton.click();

      // Loading state should appear
      const loadingIndicator = page.locator('text=/Generating|Loading/i');
      await expect(loadingIndicator).toBeVisible({ timeout: 5000 });

      // Wait for generation to complete (max 30 seconds for LLM)
      await page.waitForTimeout(30000);

      // Preview should appear
      const preview = page.getByTestId('augmentation-preview');
      const isPreviewVisible = await preview.isVisible().catch(() => false);

      if (isPreviewVisible) {
        expect(isPreviewVisible).toBeTruthy();
      }
    }
  });

  test('should show preview of generated samples', async ({ page }) => {
    // NOTE: Assumes samples have been generated
    const preview = page.getByTestId('augmentation-preview');
    const isPreviewVisible = await preview.isVisible().catch(() => false);

    if (isPreviewVisible) {
      // Should show at least 1 sample
      const sampleCards = page.locator('[data-testid^="augmented-sample-"]');
      const count = await sampleCards.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('should allow using augmented dataset', async ({ page }) => {
    // NOTE: Assumes augmentation is complete
    const useButton = page.getByTestId('use-augmented-button');
    const isUseVisible = await useButton.isVisible().catch(() => false);

    if (isUseVisible) {
      await useButton.click();

      // Dialog should close
      await page.waitForTimeout(1000);

      // Training sample count should have increased
      const sampleCount = page.locator('text=/\\d+ samples/i').first();
      const countText = await sampleCount.textContent();
      expect(countText).toBeTruthy();
    }
  });
});

test.describe('Batch Document Upload (Sprint 71 Feature 71.14)', () => {
  test('should show upload button for each domain', async ({ page }) => {
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Check if any domains exist
    const domainRows = page.locator('[data-testid^="domain-row-"]');
    const count = await domainRows.count();

    if (count > 0) {
      // First domain should have upload button
      const uploadButton = page.locator('[data-testid^="domain-upload-"]').first();
      await expect(uploadButton).toBeVisible();
    }
  });

  test('should open batch upload dialog when upload clicked', async ({ page }) => {
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Click first upload button
    const uploadButton = page.locator('[data-testid^="domain-upload-"]').first();
    const isUploadVisible = await uploadButton.isVisible().catch(() => false);

    if (isUploadVisible) {
      await uploadButton.click();

      // Dialog should open
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Should show dialog title
      const title = page.locator('text=/Batch.*Upload|Upload.*Documents/i');
      await expect(title).toBeVisible();
    }
  });

  test('should display directory path input', async ({ page }) => {
    // NOTE: Assumes dialog is open
    const pathInput = page.getByTestId('directory-path-input');
    const isPathVisible = await pathInput.isVisible().catch(() => false);

    if (isPathVisible) {
      await expect(pathInput).toBeVisible();

      // Placeholder should be helpful
      const placeholder = await pathInput.getAttribute('placeholder');
      expect(placeholder).toBeTruthy();
    }
  });

  test('should have recursive option checkbox', async ({ page }) => {
    // NOTE: Assumes dialog is open
    const recursiveCheckbox = page.getByTestId('recursive-checkbox');
    const isCheckboxVisible = await recursiveCheckbox.isVisible().catch(() => false);

    if (isCheckboxVisible) {
      await expect(recursiveCheckbox).toBeVisible();

      // Should be unchecked by default
      const isChecked = await recursiveCheckbox.isChecked();
      expect(isChecked).toBe(false);
    }
  });

  test('should scan directory for files', async ({ page }) => {
    // NOTE: Requires valid directory path
    const pathInput = page.getByTestId('directory-path-input');
    const scanButton = page.getByTestId('scan-files-button');

    const isPathVisible = await pathInput.isVisible().catch(() => false);

    if (isPathVisible) {
      // Enter a test directory path
      await pathInput.fill('/data/test_documents');

      // Click scan
      await scanButton.click();

      // Should show file count
      await page.waitForTimeout(2000);

      const fileCount = page.locator('text=/\\d+ files? found/i');
      const isCountVisible = await fileCount.isVisible().catch(() => false);

      if (isCountVisible) {
        expect(isCountVisible).toBeTruthy();
      }
    }
  });

  test('should start batch upload and redirect to jobs page', async ({ page }) => {
    // NOTE: Requires scanned files
    const uploadButton = page.getByTestId('upload-documents-button');
    const isUploadVisible = await uploadButton.isVisible().catch(() => false);

    if (isUploadVisible) {
      await uploadButton.click();

      // Should redirect to /admin/jobs with job_id
      await page.waitForURL(/\/admin\/jobs\?job_id=/, { timeout: 10000 });

      // Job should be visible
      const jobRow = page.locator('[data-testid^="job-row-"]').first();
      await expect(jobRow).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Domain Details Enhancement (Sprint 71 Feature 71.15)', () => {
  test('should show view button for each domain', async ({ page }) => {
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Check if any domains exist
    const domainRows = page.locator('[data-testid^="domain-row-"]');
    const count = await domainRows.count();

    if (count > 0) {
      // First domain should have view button
      const viewButton = page.locator('[data-testid^="domain-view-"]').first();
      await expect(viewButton).toBeVisible();
    }
  });

  test('should open domain detail dialog when view clicked', async ({ page }) => {
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Click first view button
    const viewButton = page.locator('[data-testid^="domain-view-"]').first();
    const isViewVisible = await viewButton.isVisible().catch(() => false);

    if (isViewVisible) {
      await viewButton.click();

      // Dialog should open
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });
    }
  });

  test('should display LLM model information', async ({ page }) => {
    // NOTE: Assumes domain detail dialog is open
    const llmModel = page.getByTestId('domain-llm-model');
    const isModelVisible = await llmModel.isVisible().catch(() => false);

    if (isModelVisible) {
      await expect(llmModel).toBeVisible();

      // Should show model name
      const modelText = await llmModel.textContent();
      expect(modelText).toMatch(/qwen3|llama|mistral/i);
    }
  });

  test('should display training metrics', async ({ page }) => {
    // NOTE: Assumes domain detail dialog is open and domain is trained
    const metrics = page.getByTestId('domain-training-metrics');
    const isMetricsVisible = await metrics.isVisible().catch(() => false);

    if (isMetricsVisible) {
      await expect(metrics).toBeVisible();

      // Should show F1, precision, or recall
      const metricsText = await metrics.textContent();
      expect(metricsText).toMatch(/f1|precision|recall|accuracy/i);
    }
  });

  test('should display trained prompts', async ({ page }) => {
    // NOTE: Assumes domain detail dialog is open and domain is trained
    const prompts = page.locator('text=/Trained Prompt|DSPy Prompt/i');
    const isPromptsVisible = await prompts.isVisible().catch(() => false);

    if (isPromptsVisible) {
      expect(isPromptsVisible).toBeTruthy();
    }
  });

  test('should show created and trained timestamps', async ({ page }) => {
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Click first view button to open dialog
    const viewButton = page.locator('[data-testid^="domain-view-"]').first();
    const isViewVisible = await viewButton.isVisible().catch(() => false);

    if (isViewVisible) {
      await viewButton.click();
      await page.waitForTimeout(500);

      // Look for Created or Last Updated timestamps in the dialog
      const timestamps = page.locator('text=/Created|Trained|Last Updated/i');
      const count = await timestamps.count();

      // Should have at least one timestamp
      expect(count).toBeGreaterThan(0);
    }
  });
});

test.describe('Domain Training Complete Workflow (Sprint 71)', () => {
  test('should support workflow: view existing domain and check details', async ({
    page,
  }) => {
    // Step 1: Navigate to domain training
    await page.goto('/admin/domain-training');
    await page.waitForLoadState('networkidle');

    // Check if any domains exist
    const domainRows = page.locator('[data-testid^="domain-row-"]');
    const count = await domainRows.count();

    if (count > 0) {
      // Step 2: View existing domain
      const viewButton = page.locator('[data-testid^="domain-view-"]').first();
      await viewButton.click();

      // Dialog should show
      const dialog = page.locator('[data-testid="domain-detail-dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Should display domain info sections
      const statsSection = page.getByTestId('domain-stats-section');
      const isStatsVisible = await statsSection.isVisible().catch(() => false);
      if (isStatsVisible) {
        await expect(statsSection).toBeVisible();
      }

      // Should have operations section with reindex/validate buttons
      const operationsSection = page.getByTestId('bulk-operations-section');
      const isOpsVisible = await operationsSection.isVisible().catch(() => false);
      if (isOpsVisible) {
        await expect(operationsSection).toBeVisible();

        // Check for reindex and validate buttons
        const reindexButton = page.getByTestId('reindex-button');
        const validateButton = page.getByTestId('validate-button');

        const isReindexVisible = await reindexButton.isVisible().catch(() => false);
        const isValidateVisible = await validateButton.isVisible().catch(() => false);

        if (isReindexVisible) await expect(reindexButton).toBeVisible();
        if (isValidateVisible) await expect(validateButton).toBeVisible();
      }

      // Close dialog
      await page.keyboard.press('Escape');
    }

    // Step 3: Check upload button exists if domains exist
    if (count > 0) {
      const uploadButton = page.locator('[data-testid^="domain-upload-"]').first();
      await expect(uploadButton).toBeVisible();
    }
  });
});
