/**
 * Example: Using LangSmith Tracing in Playwright E2E Tests
 *
 * This file demonstrates how to use the LangSmith setup to enable tracing
 * for debugging LLM call chains, token counts, and latency bottlenecks.
 *
 * IMPORTANT: This is an EXAMPLE FILE - do not run it directly!
 * Copy patterns to your actual test files.
 *
 * Setup Steps:
 * 1. Enable LangSmith in docker-compose.dgx-spark.yml:
 *    - LANGSMITH_TRACING=true
 *    - LANGSMITH_API_KEY=your-api-key
 *
 * 2. Run API with: docker compose -f docker-compose.dgx-spark.yml up -d api
 *
 * 3. Run frontend with: cd frontend && npm run dev
 *
 * 4. Run tests with:
 *    PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test \
 *      frontend/e2e/setup/langsmith.example.spec.ts
 *
 * 5. View traces at: https://smith.langchain.com
 */

import { test } from './langsmith';
import { expect } from '@playwright/test';

// ============================================================================
// Example 1: Basic Test with LangSmith Status Logging
// ============================================================================
test('example: show langsmith status', async ({ page, langsmith }) => {
  // Log whether LangSmith is enabled
  langsmith.logStatus('example-langsmith-status');

  // If enabled, print the project URL
  if (langsmith.isEnabled()) {
    console.log(`View traces at: ${langsmith.getProjectUrl()}`);
  }

  // Navigate to page (this creates LangSmith traces if enabled)
  await page.goto('/');
  await expect(page).toHaveTitle(/AEGIS RAG/);
});

// ============================================================================
// Example 2: Test with Environment Variable Verification
// ============================================================================
test('example: verify langsmith environment variables', async ({ page, langsmith }) => {
  langsmith.logStatus('example-env-vars');

  const envVars = langsmith.getEnvironmentVariables();
  console.log('Backend environment variables:', envVars);

  // In a real test, you could verify these are set:
  // - Check response headers for X-Langsmith-Project
  // - Verify API calls include tracing metadata
  // - etc.

  await page.goto('/');
  await expect(page).toHaveTitle(/AEGIS RAG/);
});

// ============================================================================
// Example 3: Test with Explicit LangSmith Status Check
// ============================================================================
test('example: conditional behavior based on langsmith', async ({ page, langsmith }) => {
  // Skip expensive tracing setup if LangSmith is disabled
  if (!langsmith.isEnabled()) {
    test.skip();
    return;
  }

  // This test only runs when LangSmith tracing is enabled
  console.log('Running test with LangSmith tracing enabled');
  console.log(`Project: ${langsmith.getProjectUrl()}`);

  await page.goto('/');
  await expect(page).toHaveTitle(/AEGIS RAG/);
});

// ============================================================================
// Example 4: Using in Test Suite with Multiple Tests
// ============================================================================
test.describe('LangSmith Integration Suite', () => {
  test('setup: log langsmith configuration', async ({ langsmith }) => {
    console.log('\n========== LangSmith Configuration ==========');
    console.log(`Enabled: ${langsmith.isEnabled()}`);

    if (langsmith.isEnabled()) {
      console.log(`Project URL: ${langsmith.getProjectUrl()}`);
      const vars = langsmith.getEnvironmentVariables();
      console.log(`API Key: ${vars.LANGSMITH_API_KEY?.substring(0, 10)}...`);
      console.log(`Project: ${vars.LANGSMITH_PROJECT}`);
    } else {
      console.log('LangSmith tracing is DISABLED');
      console.log('To enable:');
      console.log('  1. Set LANGSMITH_TRACING=true in docker-compose');
      console.log('  2. Set LANGSMITH_API_KEY with your API key');
      console.log('  3. Restart API: docker compose up -d api');
    }
    console.log('==========================================\n');
  });

  test('example: chat with tracing', async ({ page, langsmith }) => {
    langsmith.logStatus('chat-with-tracing');

    // Navigate and perform chat
    await page.goto('/chat');
    await expect(page.locator('input[placeholder*="Message"]')).toBeVisible();

    // Send a simple message
    const chatInput = page.locator('textarea, input[type="text"]').first();
    await chatInput.fill('Hello');
    await page.keyboard.press('Enter');

    // Wait for response
    await page.waitForTimeout(5000);

    // Check response received
    await expect(page.locator('text=Response')).toBeVisible({ timeout: 30000 });

    // If LangSmith is enabled, instructions appear in console
    if (langsmith.isEnabled()) {
      console.log(`Check LangSmith for traces: ${langsmith.getProjectUrl()}`);
    }
  });
});
