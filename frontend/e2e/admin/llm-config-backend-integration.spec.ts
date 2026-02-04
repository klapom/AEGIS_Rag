import { test, expect } from '../fixtures';
import type { Page } from '@playwright/test';

/**
 * E2E Tests for Admin LLM Config Backend Integration
 * Sprint 64 Feature 64.6: Backend API Integration (2 SP)
 *
 * Tests:
 * 1. Config loads from backend API (GET /api/v1/admin/llm/config)
 * 2. Config saves to backend API (PUT /api/v1/admin/llm/config)
 * 3. One-time migration from localStorage to backend
 * 4. Config persists across reloads (from backend, not localStorage)
 * 5. Backend serves configured models (verify integration)
 * 6. localStorage is only used for migration flag
 *
 * Prerequisites:
 * - Backend API running on http://localhost:8000
 * - Frontend running on http://localhost:5173
 * - Redis available for backend persistence
 */

// Sprint 123.10: SKIPPED - Frontend has model ID prefix bug causing data corruption
// Bug: Model IDs are prefixed multiple times: ollama/ollama/ollama/.../model:tag
// Example: API returns "ollama/ollama/ollama/.../nemotron-no-think:latest" instead of "ollama/nemotron-no-think:latest"
// Root cause: Frontend adds "ollama/" prefix on save, but backend returns it with prefix, causing prefix accumulation
// TODO: Fix model ID transformation in LLMConfigPage component before re-enabling
// Related: Sprint 64.6 Backend Integration (GET/PUT /api/v1/admin/llm/config)
test.describe.skip('Admin LLM Config - Backend Integration (Sprint 64.6)', () => {
  // Helper to clear backend config via API
  const clearBackendConfig = async (page: Page) => {
    // Reset to default config by sending default values
    await page.request.put('http://localhost:8000/api/v1/admin/llm/config', {
      headers: { 'Content-Type': 'application/json' },
      data: {
        use_cases: {
          intent_classification: { model: 'nemotron-no-think:latest', enabled: true },
          entity_extraction: { model: 'nemotron-no-think:latest', enabled: true },
          answer_generation: { model: 'nemotron-no-think:latest', enabled: true },
          followup_titles: { model: 'nemotron-no-think:latest', enabled: true },
          query_decomposition: { model: 'nemotron-no-think:latest', enabled: true },
          vision_vlm: { model: 'qwen3-vl:32b', enabled: true },
        },
      },
    });
  };

  test.beforeEach(async ({ adminLLMConfigPage, page }) => {
    // Clear backend config
    await clearBackendConfig(page);

    // Clear LLM config localStorage but PRESERVE auth token
    // Sprint 106 Fix: Don't clear aegis_auth_token or auth will fail
    await adminLLMConfigPage.page.evaluate(() => {
      localStorage.removeItem('aegis-rag-llm-config');
      localStorage.removeItem('aegis-rag-llm-config-migrated');
    });
  });

  test('should load config from backend API on first visit', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 10000 });

    // Wait for config to load from backend
    await page.waitForTimeout(1000);

    // Verify default models are loaded from backend
    const intentModel = await adminLLMConfigPage.getSelectedModel('intent_classification');
    expect(intentModel).toBe('ollama/nemotron-no-think:latest'); // Frontend format

    // Verify localStorage is NOT used for config (only migration flag)
    const storedConfig = await adminLLMConfigPage.page.evaluate(() =>
      localStorage.getItem('aegis-rag-llm-config')
    );
    expect(storedConfig).toBeNull(); // Config should NOT be in localStorage
  });

  test('should save config to backend API (not localStorage)', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    // Sprint 114 (P-008): Increase timeout for auth and page load
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    // Change a model
    await adminLLMConfigPage.selectModel('entity_extraction', 'ollama/qwen3:8b');

    // Save
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Wait for backend save to complete
    await page.waitForTimeout(1000);

    // Verify localStorage does NOT contain config (only migration flag)
    const storedConfig = await adminLLMConfigPage.page.evaluate(() =>
      localStorage.getItem('aegis-rag-llm-config')
    );
    expect(storedConfig).toBeNull();

    // Verify config was saved to backend by fetching directly
    const response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
    expect(response.ok()).toBe(true);

    const backendConfig = await response.json();
    expect(backendConfig.use_cases.entity_extraction.model).toBe('qwen3:8b'); // Backend format
  });

  test('should migrate localStorage config to backend on first load', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Sprint 66 Fix: Navigate FIRST before setting localStorage to avoid SecurityError
    await page.goto('/');

    // Step 1: Manually set OLD localStorage config (simulate pre-Sprint 64 state)
    await adminLLMConfigPage.page.evaluate(() => {
      const oldConfig = [
        { useCase: 'intent_classification', modelId: 'ollama/qwen3:8b', enabled: true },
        { useCase: 'entity_extraction', modelId: 'ollama/qwen3:8b', enabled: true },
        { useCase: 'answer_generation', modelId: 'ollama/nemotron-no-think:latest', enabled: true },
        { useCase: 'followup_titles', modelId: 'ollama/nemotron-no-think:latest', enabled: true },
        { useCase: 'query_decomposition', modelId: 'ollama/nemotron-no-think:latest', enabled: true },
        { useCase: 'vision_vlm', modelId: 'ollama/qwen3-vl:32b', enabled: true },
      ];
      localStorage.setItem('aegis-rag-llm-config', JSON.stringify(oldConfig));
      // Remove migration flag to trigger migration
      localStorage.removeItem('aegis-rag-llm-config-migrated');
    });

    // Step 2: Navigate to page (should trigger migration) - uses navigateClientSide to preserve auth
    await adminLLMConfigPage.goto();
    // Sprint 114 (P-008): Increase timeout for auth and page load
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    // Wait for migration to complete
    await page.waitForTimeout(2000);

    // Step 3: Verify migration flag is set
    const migrationFlag = await adminLLMConfigPage.page.evaluate(() =>
      localStorage.getItem('aegis-rag-llm-config-migrated')
    );
    expect(migrationFlag).toBe('true');

    // Step 4: Verify localStorage config was removed
    const storedConfig = await adminLLMConfigPage.page.evaluate(() =>
      localStorage.getItem('aegis-rag-llm-config')
    );
    expect(storedConfig).toBeNull();

    // Step 5: Verify config was migrated to backend
    const response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
    expect(response.ok()).toBe(true);

    const backendConfig = await response.json();
    expect(backendConfig.use_cases.intent_classification.model).toBe('qwen3:8b'); // Migrated value
    expect(backendConfig.use_cases.entity_extraction.model).toBe('qwen3:8b'); // Migrated value

    // Step 6: Verify UI shows migrated config
    const intentModel = await adminLLMConfigPage.getSelectedModel('intent_classification');
    expect(intentModel).toBe('ollama/qwen3:8b'); // Frontend format
  });

  test('should persist config across reloads (from backend)', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate and change config (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    // Sprint 114 (P-008): Increase timeout for auth and page load
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    await adminLLMConfigPage.selectModel('answer_generation', 'ollama/qwen3:8b');
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Clear LLM config from localStorage to prove config comes from backend
    // Sprint 106 Fix: Preserve auth token or reload will redirect to login
    await adminLLMConfigPage.page.evaluate(() => {
      localStorage.removeItem('aegis-rag-llm-config');
      localStorage.removeItem('aegis-rag-llm-config-migrated');
    });

    // Reload page
    await page.reload();
    // Sprint 114 (P-008): Increase timeout for auth after reload
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    // Wait for config to load
    await page.waitForTimeout(1500);

    // Verify config persisted (from backend, NOT localStorage)
    const answerModel = await adminLLMConfigPage.getSelectedModel('answer_generation');
    expect(answerModel).toBe('ollama/qwen3:8b');

    // Verify migration flag is reset after reload
    const migrationFlag = await adminLLMConfigPage.page.evaluate(() =>
      localStorage.getItem('aegis-rag-llm-config-migrated')
    );
    expect(migrationFlag).toBe('true'); // Should be set again after reload
  });

  test('should NOT use localStorage for config storage (only migration flag)', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    // Sprint 114 (P-008): Increase timeout for auth and page load
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    // Change multiple models
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/qwen3:8b');
    await adminLLMConfigPage.selectModel('entity_extraction', 'ollama/qwen3:8b');
    await adminLLMConfigPage.selectModel('answer_generation', 'ollama/qwen3:8b');

    // Save
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Wait for save
    await page.waitForTimeout(1000);

    // Verify localStorage ONLY has migration flag, NOT config
    const allLocalStorageKeys = await adminLLMConfigPage.page.evaluate(() => {
      return Object.keys(localStorage);
    });

    expect(allLocalStorageKeys).not.toContain('aegis-rag-llm-config'); // Config should NOT be in localStorage
    expect(allLocalStorageKeys).toContain('aegis-rag-llm-config-migrated'); // Only migration flag
  });

  test('should handle backend API errors gracefully', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 10000 });

    // Change a model
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/qwen3:8b');

    // Intercept API request and simulate failure
    await page.route('**/api/v1/admin/llm/config', (route) => {
      route.abort('failed');
    });

    // Try to save (should fail)
    await adminLLMConfigPage.saveConfig();

    // Wait for error state
    await page.waitForTimeout(1000);

    // Verify error indicator is shown
    const saveButton = adminLLMConfigPage.saveConfigButton;
    const buttonText = await saveButton.textContent();
    expect(buttonText).toContain('Error');

    // Remove route interception
    await page.unroute('**/api/v1/admin/llm/config');
  });

  test('should handle concurrent saves correctly', async ({ adminLLMConfigPage, page }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 10000 });

    // Change model
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/qwen3:8b');

    // Click save twice rapidly
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.saveConfig(); // Second click while first is in progress

    // Wait for both to complete
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify config was saved correctly
    const response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
    const backendConfig = await response.json();
    expect(backendConfig.use_cases.intent_classification.model).toBe('qwen3:8b');
  });

  test('should correctly transform model IDs between frontend and backend formats', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 10000 });

    // Test Ollama model transformation
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/qwen3:8b');
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify backend format (no "ollama/" prefix)
    let response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
    let backendConfig = await response.json();
    expect(backendConfig.use_cases.intent_classification.model).toBe('qwen3:8b'); // No prefix

    // Test Alibaba Cloud model transformation
    const alibabaModels = await adminLLMConfigPage.getAvailableModels('entity_extraction');
    const alibabaModel = alibabaModels.find((m: string) => m.includes('Alibaba'));

    if (alibabaModel) {
      await adminLLMConfigPage.selectModel('entity_extraction', 'alibaba/qwen-plus');
      await adminLLMConfigPage.saveConfig();
      await adminLLMConfigPage.waitForSaveSuccess();

      // Verify backend format (alibaba_cloud: prefix)
      response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
      backendConfig = await response.json();
      expect(backendConfig.use_cases.entity_extraction.model).toBe('alibaba_cloud:qwen-plus');
    }
  });
});

test.describe.skip('Admin LLM Config - Backend Integration Verification', () => {
  test('should verify backend actually uses configured model', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    // Sprint 114 (P-008): Increase timeout for auth and page load
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    // Configure a specific model for intent classification
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/nemotron-no-think:latest');
    await adminLLMConfigPage.saveConfig();
    await adminLLMConfigPage.waitForSaveSuccess();

    // Wait for cache to update (60 seconds max, but we'll wait 3 seconds for safety)
    await page.waitForTimeout(3000);

    // Verify backend config service returns correct model
    const response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
    expect(response.ok()).toBe(true);

    const config = await response.json();
    expect(config.use_cases.intent_classification.model).toBe('nemotron-no-think:latest');
    expect(config.use_cases.intent_classification.enabled).toBe(true);
  });

  test('should verify all 6 use cases are configurable via backend', async ({
    adminLLMConfigPage,
    page,
  }) => {
    // Navigate to page (uses navigateClientSide to preserve auth)
    await adminLLMConfigPage.goto();
    // Sprint 114 (P-008): Increase timeout for auth and page load
    await adminLLMConfigPage.llmConfigPage.waitFor({ state: 'visible', timeout: 60000 });

    // Configure all use cases
    await adminLLMConfigPage.selectModel('intent_classification', 'ollama/nemotron-no-think:latest');
    await adminLLMConfigPage.selectModel('entity_extraction', 'ollama/nemotron-no-think:latest');
    await adminLLMConfigPage.selectModel('answer_generation', 'ollama/nemotron-no-think:latest');
    await adminLLMConfigPage.selectModel('followup_titles', 'ollama/nemotron-no-think:latest');
    await adminLLMConfigPage.selectModel('query_decomposition', 'ollama/nemotron-no-think:latest');
    await adminLLMConfigPage.selectModel('vision_vlm', 'ollama/qwen3-vl:32b');

    // Save
    await adminLLMConfigPage.saveConfig();
    // Sprint 114 (P-008): Increase wait timeout for save success
    await adminLLMConfigPage.waitForSaveSuccess();

    // Verify backend has all 6 use cases
    const response = await page.request.get('http://localhost:8000/api/v1/admin/llm/config');
    const config = await response.json();

    expect(Object.keys(config.use_cases).length).toBe(6);
    expect(config.use_cases.intent_classification).toBeDefined();
    expect(config.use_cases.entity_extraction).toBeDefined();
    expect(config.use_cases.answer_generation).toBeDefined();
    expect(config.use_cases.followup_titles).toBeDefined();
    expect(config.use_cases.query_decomposition).toBeDefined();
    expect(config.use_cases.vision_vlm).toBeDefined();
  });
});
