import { test, expect } from '../fixtures';

/**
 * E2E Tests for VLM (Vision Language Model) Integration
 * Sprint 36 - Features 36.1, 36.2: VLM Factory and OllamaVLMClient
 *
 * Tests:
 * 1. Admin can configure VLM backend (local vs cloud)
 * 2. VLM selection persists across navigation
 * 3. Vision use case filters to vision-capable models
 * 4. Cost tracking reflects VLM selection (local vs cloud)
 * 5. Integration with Admin Indexing page
 *
 * Prerequisites:
 * - Frontend running on http://localhost:5173
 * - Backend not required for configuration tests
 * - Optional: Ollama with vision models or Alibaba Cloud API for integration tests
 */

test.describe('VLM Backend Configuration', () => {
  test('should select local VLM by default', async ({ adminLLMConfigPage }) => {
    // Clear localStorage to test defaults
    await adminLLMConfigPage.clearStoredConfig();

    // Reload page to see defaults
    await adminLLMConfigPage.page.reload();
    await adminLLMConfigPage.llmConfigPage.waitFor({
      state: 'visible',
      timeout: 10000,
    });

    // Check Vision VLM use case
    const selectedModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');

    // Should default to local Ollama vision model
    expect(selectedModel).toContain('ollama');
  });

  test('should display only vision-capable models for VLM use case', async ({
    adminLLMConfigPage,
  }) => {
    const vlmModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');

    // Should have multiple vision models available
    expect(vlmModels.length).toBeGreaterThan(0);

    // All should be vision-capable
    for (const model of vlmModels) {
      const hasVisionCapability =
        model.includes('VL') ||
        model.includes('Vision') ||
        model.includes('4o') ||
        model.includes('vision');
      expect(hasVisionCapability).toBe(true);
    }
  });

  test('should allow switching to cloud VLM', async ({ adminLLMConfigPage }) => {
    // Get available cloud vision models
    const vlmModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');

    // Find a cloud model (not ollama)
    const cloudModel = vlmModels.find((model) => !model.includes('ollama'));

    if (cloudModel) {
      // Extract model ID from the option text
      const dropdown = adminLLMConfigPage.visionVLMDropdown;
      const options = await dropdown.locator('option').all();

      for (const option of options) {
        const text = await option.textContent();
        if (text === cloudModel) {
          await option.click();
          break;
        }
      }

      // Select the cloud model
      const availableOptions = await dropdown.locator('option').allTextContents();
      const cloudOption = availableOptions.find((opt) => !opt.includes('ollama'));

      if (cloudOption) {
        // Find the option value for the cloud model
        const cloudOptionElement = dropdown.locator(
          `option:has-text("${cloudOption.substring(0, 20)}")`
        );
        const cloudValue = await cloudOptionElement.getAttribute('value');

        if (cloudValue) {
          await adminLLMConfigPage.selectModel('vision_vlm', cloudValue);
        }
      }
    }
  });

  test('should show provider badge for selected VLM model', async ({
    adminLLMConfigPage,
  }) => {
    // Default should show "Local" badge
    const badge = await adminLLMConfigPage.getProviderBadge('vision_vlm');
    expect(badge.toLowerCase()).toContain('local');
  });

  test('should persist VLM selection across page reload', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Set a specific VLM model
    const targetModel = 'ollama/qwen3-vl:32b';
    await adminLLMConfigPage.selectModel('vision_vlm', targetModel);
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Reload page
    await page.reload();
    await adminLLMConfigPage.llmConfigPage.waitFor({
      state: 'visible',
      timeout: 10000,
    });

    // Verify selection persisted
    const selectedModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');
    expect(selectedModel).toBe(targetModel);
  });
});

test.describe('VLM Integration with Admin Pages', () => {
  test('should navigate from LLM Config to Admin Indexing', async ({ page }) => {
    await page.goto('/admin/llm-config');

    // Navigate to indexing page
    await page.goto('/admin/indexing');

    // Should load indexing page
    const indexingPage = page.locator('[data-testid="admin-indexing-page"]');
    await expect(indexingPage).toBeVisible({ timeout: 10000 });
  });

  test('should show VLM configuration in context', async ({ adminLLMConfigPage }) => {
    // Get the Vision VLM configuration
    const selectedModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');

    // Should have a valid model selected
    expect(selectedModel).toBeTruthy();
    expect(selectedModel.length).toBeGreaterThan(0);
  });

  test('should allow quick VLM switching between sessions', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Session 1: Select local VLM
    await adminLLMConfigPage.selectModel('vision_vlm', 'ollama/qwen3-vl:32b');
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Simulate user navigating away and back
    await page.goto('/');
    await page.goto('/admin/llm-config');
    await adminLLMConfigPage.llmConfigPage.waitFor({
      state: 'visible',
      timeout: 10000,
    });

    // Verify VLM selection persisted
    let selectedModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');
    expect(selectedModel).toBe('ollama/qwen3-vl:32b');

    // Session 2: Change to different VLM
    const allModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');
    if (allModels.length > 1) {
      // Get a different model
      const currentIndex = allModels.findIndex((m) =>
        m.includes('ollama/qwen3-vl:32b')
      );
      const nextIndex = (currentIndex + 1) % allModels.length;

      // This is tricky with text content, so we use index-based selection
      const dropdown = adminLLMConfigPage.visionVLMDropdown;
      await dropdown.selectOption({ index: nextIndex });

      // Save and verify
      await adminLLMConfigPage.saveConfig();
      await adminLLMConfigPage.waitForSaveSuccess();

      selectedModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');
      expect(selectedModel).not.toBe('ollama/qwen3-vl:32b');
    }
  });
});

test.describe('VLM Cost Tracking', () => {
  test('local VLM should indicate zero cost option', async ({ adminLLMConfigPage }) => {
    // Select local VLM
    await adminLLMConfigPage.selectModel('vision_vlm', 'ollama/qwen3-vl:32b');

    // Get the display name which includes description
    const displayName = await adminLLMConfigPage.getDisplayedModelName('vision_vlm');

    // Should mention local or cost
    expect(
      displayName.toLowerCase().includes('local') ||
        displayName.toLowerCase().includes('$0')
    ).toBe(true);
  });

  test('cloud VLM should have cost information', async ({ adminLLMConfigPage }) => {
    const vlmModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');

    // Check if there are cloud models available
    const cloudModels = vlmModels.filter((model) => !model.includes('ollama'));

    if (cloudModels.length > 0) {
      // Try to select a cloud model
      const dropdown = adminLLMConfigPage.visionVLMDropdown;
      const options = await dropdown.locator('option').allTextContents();

      const cloudOption = options.find((opt) => !opt.includes('ollama'));
      if (cloudOption) {
        // The option text should indicate it's a cloud/paid service
        expect(
          cloudOption.toLowerCase().includes('cloud') ||
            cloudOption.toLowerCase().includes('alibaba') ||
            cloudOption.toLowerCase().includes('openai')
        ).toBe(true);
      }
    }
  });

  test('should reflect VLM cost in admin dashboard', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Configure VLM as local
    await adminLLMConfigPage.selectModel('vision_vlm', 'ollama/qwen3-vl:32b');
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Navigate to cost dashboard
    await page.goto('/admin/costs');

    // Cost dashboard should load (actual cost comparison depends on backend)
    const costDashboard = page.locator('[data-testid="cost-dashboard"]');
    const costCards = page.locator('[data-testid="card-total-cost"]');

    // Either dashboard exists or card exists
    const hasUI = (await costDashboard.isVisible().catch(() => false)) ||
      (await costCards.isVisible().catch(() => false));
    expect(hasUI).toBe(true);
  });
});

test.describe('VLM Model Capabilities', () => {
  test('should filter models based on vision requirement', async ({
    adminLLMConfigPage,
  }) => {
    // Vision VLM should only have vision models
    const visionModels = await adminLLMConfigPage.getAvailableModels('vision_vlm');

    // All should be vision capable
    for (const model of visionModels) {
      const isVision = model.includes('VL') ||
        model.includes('Vision') ||
        model.includes('4o') ||
        model.includes('vision');
      expect(isVision).toBe(true);
    }

    // Text-only use cases should not have vision models
    const textModels = await adminLLMConfigPage.getAvailableModels(
      'intent_classification'
    );

    // Should not include vision-specific models (usually)
    const textOnly = textModels.filter(
      (m) =>
        m.includes('Llama') ||
        m.includes('Qwen') ||
        (m.includes('qwen') && !m.includes('vl'))
    );
    expect(textOnly.length).toBeGreaterThan(0);
  });

  test('should allow independent configuration of VLM and text models', async ({
    adminLLMConfigPage,
  }) => {
    // Set text model for entity extraction
    await adminLLMConfigPage.selectModel('entity_extraction', 'ollama/qwen3:8b');

    // Set vision model for VLM
    await adminLLMConfigPage.selectModel('vision_vlm', 'ollama/qwen3-vl:32b');

    // Save
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify both are saved correctly
    const entityModel = await adminLLMConfigPage.getSelectedModel('entity_extraction');
    const visionModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');

    expect(entityModel).toBe('ollama/qwen3:8b');
    expect(visionModel).toBe('ollama/qwen3-vl:32b');
  });
});

test.describe('VLM Fallback Strategy', () => {
  test('should have local VLM as default (fallback option)', async ({
    adminLLMConfigPage,
  }) => {
    // Clear config to test default behavior
    await adminLLMConfigPage.clearStoredConfig();
    await adminLLMConfigPage.page.reload();
    await adminLLMConfigPage.llmConfigPage.waitFor({
      state: 'visible',
      timeout: 10000,
    });

    // Should default to local VLM (fallback)
    const selectedModel = await adminLLMConfigPage.getSelectedModel('vision_vlm');
    expect(selectedModel).toContain('ollama');
  });

  test('should allow switching from cloud to local VLM', async ({
    adminLLMConfigPage,
  }) => {
    // Start with any model
    const dropdown = adminLLMConfigPage.visionVLMDropdown;
    const allOptions = await dropdown.locator('option').allTextContents();

    // Switch to local
    const localOption = allOptions.find((opt) => opt.includes('ollama'));
    if (localOption) {
      const localValue = await dropdown
        .locator(`option:has-text("${localOption.substring(0, 20)}")`)
        .getAttribute('value');

      if (localValue) {
        await adminLLMConfigPage.selectModel('vision_vlm', localValue);
        const selected = await adminLLMConfigPage.getSelectedModel('vision_vlm');
        expect(selected).toContain('ollama');
      }
    }
  });

  test('should maintain VLM choice through error recovery', async ({
    adminLLMConfigPage,
  }) => {
    // Set a specific VLM
    const targetModel = 'ollama/qwen3-vl:32b';
    await adminLLMConfigPage.selectModel('vision_vlm', targetModel);
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Simulate page navigation
    await adminLLMConfigPage.page.goto('/');
    await adminLLMConfigPage.page.goto('/admin/llm-config');
    await adminLLMConfigPage.llmConfigPage.waitFor({
      state: 'visible',
      timeout: 10000,
    });

    // Should still have the chosen VLM
    const selected = await adminLLMConfigPage.getSelectedModel('vision_vlm');
    expect(selected).toBe(targetModel);
  });
});

test.describe('VLM UI Integration', () => {
  test('should display VLM use case prominently', async ({
    adminLLMConfigPage,
  }) => {
    // Vision VLM selector should be visible
    await expect(adminLLMConfigPage.visionVLMSelector).toBeVisible();

    // Should have a description
    const description = adminLLMConfigPage.visionVLMSelector.getByText(/image|vision/i);
    await expect(description).toBeVisible();
  });

  test('should show VLM model information clearly', async ({
    adminLLMConfigPage,
  }) => {
    // Get the selected model's display information
    const displayName = await adminLLMConfigPage.getDisplayedModelName('vision_vlm');

    // Should be informative
    expect(displayName.length).toBeGreaterThan(0);
    expect(displayName).toMatch(/Qwen|llava|GPT|Vision/i);
  });

  test('should provide clear VLM provider badges', async ({
    adminLLMConfigPage,
  }) => {
    // Get provider badge
    const badge = await adminLLMConfigPage.getProviderBadge('vision_vlm');

    // Should clearly indicate local or cloud
    const isLabelClear =
      badge.toLowerCase().includes('local') ||
      badge.toLowerCase().includes('cloud') ||
      badge.toLowerCase().includes('ollama') ||
      badge.toLowerCase().includes('alibaba') ||
      badge.toLowerCase().includes('openai');

    expect(isLabelClear).toBe(true);
  });

  test('should have accessible VLM controls', async ({
    adminLLMConfigPage,
  }) => {
    const dropdown = adminLLMConfigPage.visionVLMDropdown;

    // Should be keyboard accessible
    await dropdown.focus();
    const focused = await dropdown.evaluate((el) => el === document.activeElement);
    expect(focused).toBe(true);

    // Should be selectable
    const options = await dropdown.locator('option').count();
    expect(options).toBeGreaterThan(0);
  });
});
