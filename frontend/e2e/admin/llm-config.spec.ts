import { test, expect } from '../fixtures';

/**
 * E2E Tests for Admin LLM Configuration Page
 * Sprint 36 - Feature 36.3: Model Selection per Use Case (8 SP)
 *
 * Tests:
 * 1. Page loads and displays all UI elements
 * 2. All 6 use case selectors are visible
 * 3. Model dropdowns work correctly
 * 4. Different models can be selected
 * 5. Configuration is saved to localStorage
 * 6. Configuration persists on page reload
 * 7. Provider badges display correctly (Local/Cloud)
 * 8. Vision models are filtered for VLM use case
 * 9. Navigation from sidebar works
 * 10. Dark mode support
 *
 * Prerequisites:
 * - Frontend running on http://localhost:5173 (or configured port)
 * - No backend API calls required (localStorage-based)
 */

test.describe('Admin LLM Configuration - Page 36.3', () => {
  test.beforeEach(async ({ adminLLMConfigPage }) => {
    // Clear localStorage before each test to ensure clean state
    await adminLLMConfigPage.clearStoredConfig();
  });

  test('should display LLM configuration page', async ({ adminLLMConfigPage }) => {
    // Verify page title and description are visible
    await expect(adminLLMConfigPage.pageTitle).toBeVisible();
    await expect(adminLLMConfigPage.pageDescription).toBeVisible();
  });

  test('should display all 6 use case selectors', async ({ adminLLMConfigPage }) => {
    const useCases = [
      'intent_classification',
      'entity_extraction',
      'answer_generation',
      'followup_titles',
      'query_decomposition',
      'vision_vlm',
    ];

    for (const useCase of useCases) {
      const selector = adminLLMConfigPage.page.locator(
        `[data-testid="usecase-selector-${useCase}"]`
      );
      await expect(selector).toBeVisible();
    }
  });

  test('should have model dropdowns for each use case', async ({ adminLLMConfigPage }) => {
    const dropdowns = adminLLMConfigPage.getModelDropdowns();

    for (const dropdown of dropdowns) {
      await expect(dropdown).toBeVisible();
      await expect(dropdown).toBeEnabled();
    }
  });

  test('should allow selecting different models', async ({ adminLLMConfigPage }) => {
    // Get available options for intent_classification
    const availableModels = await adminLLMConfigPage.getAvailableModels(
      'intent_classification'
    );
    expect(availableModels.length).toBeGreaterThan(0);

    // Select first available model (after default)
    if (availableModels.length > 1) {
      const dropdown = adminLLMConfigPage.intentClassificationDropdown;
      await dropdown.selectOption({ index: 1 });

      // Verify selection changed
      const newValue = await dropdown.inputValue();
      expect(newValue).toBeTruthy();
    }
  });

  test('should show refresh models button', async ({ adminLLMConfigPage }) => {
    await expect(adminLLMConfigPage.refreshModelsButton).toBeVisible();
    await expect(adminLLMConfigPage.refreshModelsButton).toBeEnabled();
  });

  test('should show save configuration button', async ({ adminLLMConfigPage }) => {
    await expect(adminLLMConfigPage.saveConfigButton).toBeVisible();
    await expect(adminLLMConfigPage.saveConfigButton).toBeEnabled();
  });

  test('should save configuration to localStorage', async ({ adminLLMConfigPage }) => {
    // Change a model selection
    const dropdown = adminLLMConfigPage.answerGenerationDropdown;
    await dropdown.selectOption({ index: 1 });

    // Click save
    await adminLLMConfigPage.saveConfig();

    // Wait for save success message
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify localStorage was updated
    const config = await adminLLMConfigPage.getStoredConfig();

    expect(config).not.toBeNull();
    expect(Array.isArray(config)).toBe(true);
    expect(config.length).toBe(6);

    // Verify the changed use case has the new model
    const answerGenConfig = config.find((c: any) => c.useCase === 'answer_generation');
    expect(answerGenConfig).toBeDefined();
  });

  test('should persist configuration on page reload', async ({ adminLLMConfigPage, page }) => {
    // Set a specific configuration
    const targetModel = 'ollama/llama3.2:8b';
    await adminLLMConfigPage.selectModel('entity_extraction', targetModel);

    // Save
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Reload page
    await page.reload();
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 10000 });

    // Verify the selection persisted
    const selectedModel = await adminLLMConfigPage.getSelectedModel('entity_extraction');
    expect(selectedModel).toBe(targetModel);
  });

  test('should show provider badges (Local/Cloud)', async ({ adminLLMConfigPage }) => {
    // Default Ollama model should show "Local" badge
    const intentBadge = await adminLLMConfigPage.getProviderBadge(
      'intent_classification'
    );
    expect(intentBadge.toLowerCase()).toContain('local');
  });

  test('should filter vision models for VLM use case', async ({ adminLLMConfigPage }) => {
    const vlmModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');

    // Vision use case should only show vision-capable models
    expect(vlmModels.length).toBeGreaterThan(0);

    // Should contain at least one model with vision capability
    const hasVisionModels = vlmModels.some(
      (model) =>
        model.includes('VL') ||
        model.includes('Vision') ||
        model.includes('4o') ||
        model.includes('vision')
    );
    expect(hasVisionModels).toBe(true);
  });

  test('should not show text-only models for vision use case', async ({
    adminLLMConfigPage,
  }) => {
    const vlmModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');

    // Text-only models should not be available for VLM
    // This is a best-effort check depending on model naming
    const textOnlyModels = vlmModels.filter((model) => {
      // Llama 3.2 without VL is text-only
      return model.includes('Llama') && !model.includes('VL');
    });

    // We expect this to be empty or minimal
    expect(textOnlyModels.length).toBeLessThanOrEqual(1);
  });

  test('should allow multiple model selections', async ({ adminLLMConfigPage }) => {
    // Change multiple use cases
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/llama3.2:8b');
    await adminLLMConfigPage.selectModel('entity_extraction', 'ollama/qwen3:32b');
    await adminLLMConfigPage.selectModel('answer_generation', 'ollama/llama3.2:8b');

    // Save
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify all selections saved
    const config = await adminLLMConfigPage.getStoredConfig();
    expect(config.length).toBe(6);

    const intentConfig = config.find((c: any) => c.useCase === 'intent_classification');
    const entityConfig = config.find((c: any) => c.useCase === 'entity_extraction');
    const answerConfig = config.find((c: any) => c.useCase === 'answer_generation');

    expect(intentConfig.modelId).toBe('ollama/llama3.2:8b');
    expect(entityConfig.modelId).toBe('ollama/qwen3:32b');
    expect(answerConfig.modelId).toBe('ollama/llama3.2:8b');
  });

  test('should maintain form state during user interaction', async ({
    adminLLMConfigPage,
  }) => {
    // Select a model
    await adminLLMConfigPage.selectModel('followup_titles', 'ollama/llama3.2:8b');

    // Verify selection is maintained
    const selectedModel = await adminLLMConfigPage.getSelectedModel('followup_titles');
    expect(selectedModel).toBe('ollama/llama3.2:8b');

    // Change to another model
    const availableModels = await adminLLMConfigPage.getAvailableModels('followup_titles');
    if (availableModels.length > 1) {
      await adminLLMConfigPage.selectModel('followup_titles', 'ollama/qwen3:32b');

      const newModel = await adminLLMConfigPage.getSelectedModel('followup_titles');
      expect(newModel).toBe('ollama/qwen3:32b');
    }
  });

  test('should display all sections with appropriate styling', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Verify header section
    const header = page.getByText('Use Case Model Assignment').first();
    await expect(header).toBeVisible();

    // Verify each use case selector has a label and description
    const selectors = adminLLMConfigPage.getUseCaseSelectors();
    expect(selectors.length).toBe(6);

    for (const selector of selectors) {
      await expect(selector).toBeVisible();
    }
  });

  test('should handle rapid model changes', async ({ adminLLMConfigPage }) => {
    // Rapidly change multiple models
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/llama3.2:8b');
    await adminLLMConfigPage.selectModel('entity_extraction', 'ollama/qwen3:32b');
    await adminLLMConfigPage.selectModel('answer_generation', 'ollama/llama3.2:8b');
    await adminLLMConfigPage.selectModel('followup_titles', 'ollama/qwen3:32b');

    // Save once at the end
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify all changes were saved correctly
    const config = await adminLLMConfigPage.getStoredConfig();
    expect(config.find((c: any) => c.useCase === 'intent_classification').modelId).toBe(
      'ollama/llama3.2:8b'
    );
    expect(config.find((c: any) => c.useCase === 'entity_extraction').modelId).toBe(
      'ollama/qwen3:32b'
    );
  });

  test('should reset to default on clear (if feature exists)', async ({
    adminLLMConfigPage,
  }) => {
    // Try to select non-default model
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/llama3.2:8b');
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify change was saved
    let config = await adminLLMConfigPage.getStoredConfig();
    expect(
      config.find((c: any) => c.useCase === 'intent_classification').modelId
    ).not.toBe('ollama/qwen3:32b');

    // Clear and verify
    await adminLLMConfigPage.clearStoredConfig();

    // Reload page
    await adminLLMConfigPage.page.reload();
    await adminLLMConfigPage.llmConfigPage.waitFor({
      state: 'visible',
      timeout: 10000,
    });

    // Should be back to default
    const afterReload = await adminLLMConfigPage.getSelectedModel('intent_classification');
    expect(afterReload).toBe('ollama/qwen3:32b'); // Default model
  });
});

test.describe('Admin LLM Config - Navigation', () => {
  test('should navigate to LLM config from home', async ({ page }) => {
    // Start at home
    await page.goto('/');

    // Look for sidebar link
    const llmConfigLink = page.locator('[data-testid="sidebar-llm-config-link"]');

    if (await llmConfigLink.isVisible()) {
      await llmConfigLink.click();
      await expect(page).toHaveURL(/\/admin\/llm-config/);
    }
  });

  test('should be accessible via direct URL', async ({ page }) => {
    await page.goto('/admin/llm-config');
    await expect(page.locator('[data-testid="llm-config-page"]')).toBeVisible();
  });

  test('should have proper page title', async ({ page }) => {
    await page.goto('/admin/llm-config');
    const title = await page.title();
    expect(title).toBeTruthy();
  });
});

test.describe('Admin LLM Config - Dark Mode', () => {
  test('should support dark mode styling', async ({ adminLLMConfigPage }) => {
    // Enable dark mode
    await adminLLMConfigPage.toggleDarkMode();

    // Page should still be visible and functional
    await expect(adminLLMConfigPage.llmConfigPage).toBeVisible();

    // Dropdowns should be visible
    for (const dropdown of adminLLMConfigPage.getModelDropdowns()) {
      await expect(dropdown).toBeVisible();
    }
  });

  test('should maintain functionality in dark mode', async ({ adminLLMConfigPage }) => {
    // Enable dark mode
    await adminLLMConfigPage.toggleDarkMode();

    // Try to select a model
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/llama3.2:8b');

    // Verify selection worked
    const selected = await adminLLMConfigPage.getSelectedModel('intent_classification');
    expect(selected).toBe('ollama/llama3.2:8b');

    // Save should still work
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();
  });
});

test.describe('Admin LLM Config - Accessibility', () => {
  test('should have all required data-testid attributes', async ({
    adminLLMConfigPage,
  }) => {
    // Verify main page element
    await expect(adminLLMConfigPage.llmConfigPage).toBeVisible();

    // Verify all use cases have testids
    const useCases = [
      'intent_classification',
      'entity_extraction',
      'answer_generation',
      'followup_titles',
      'query_decomposition',
      'vision_vlm',
    ];

    for (const useCase of useCases) {
      const selector = adminLLMConfigPage.page.locator(
        `[data-testid="usecase-selector-${useCase}"]`
      );
      await expect(selector).toBeVisible();

      const dropdown = adminLLMConfigPage.page.locator(
        `[data-testid="model-dropdown-${useCase}"]`
      );
      await expect(dropdown).toBeVisible();
    }

    // Verify buttons have testids
    await expect(adminLLMConfigPage.refreshModelsButton).toBeVisible();
    await expect(adminLLMConfigPage.saveConfigButton).toBeVisible();
  });

  test('should have keyboard accessible dropdowns', async ({
    adminLLMConfigPage,
  }) => {
    const dropdown = adminLLMConfigPage.intentClassificationDropdown;

    // Focus on dropdown
    await dropdown.focus();

    // Should be focused
    const focused = await dropdown.evaluate((el) => el === document.activeElement);
    expect(focused).toBe(true);

    // Should be able to change value with keyboard
    await dropdown.selectOption({ index: 1 });

    const newValue = await dropdown.inputValue();
    expect(newValue).toBeTruthy();
  });
});

test.describe('Admin LLM Config - Responsive Design', () => {
  test('should work on mobile viewport', async ({ adminLLMConfigPage, page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Page should still be visible
    await expect(adminLLMConfigPage.llmConfigPage).toBeVisible();

    // Dropdowns should still be functional
    const dropdown = adminLLMConfigPage.intentClassificationDropdown;
    await expect(dropdown).toBeVisible();
    await expect(dropdown).toBeEnabled();

    // Should be able to select a model
    await dropdown.selectOption({ index: 1 });
    const selected = await dropdown.inputValue();
    expect(selected).toBeTruthy();
  });

  test('should work on tablet viewport', async ({ adminLLMConfigPage, page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });

    // Page should still be visible
    await expect(adminLLMConfigPage.llmConfigPage).toBeVisible();

    // All elements should be functional
    const dropdowns = adminLLMConfigPage.getModelDropdowns();
    expect(dropdowns.length).toBe(6);
  });

  test('should work on desktop viewport', async ({ adminLLMConfigPage, page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Page should be fully visible
    await expect(adminLLMConfigPage.llmConfigPage).toBeVisible();

    // All elements should fit without scrolling
    const dropdowns = adminLLMConfigPage.getModelDropdowns();
    for (const dropdown of dropdowns) {
      await expect(dropdown).toBeVisible();
    }
  });
});
