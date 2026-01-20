/**
 * LangSmith Configuration for Playwright E2E Tests
 *
 * Purpose: Enable LangSmith tracing ONLY for local Playwright E2E tests
 * to observe LLM call chains, token counts, and latency breakdown.
 *
 * IMPORTANT: This setup is NEVER used in CI/CD pipelines!
 * CI/CD workflows explicitly disable LangSmith to prevent unnecessary traces.
 *
 * Usage:
 * 1. Enable LangSmith in docker-compose.dgx-spark.yml:
 *    LANGSMITH_TRACING=true
 *    LANGSMITH_API_KEY=<your-key>
 *
 * 2. Run Playwright tests locally:
 *    PLAYWRIGHT_BASE_URL=http://192.168.178.10 npx playwright test
 *
 * 3. View traces at: https://smith.langchain.com
 *
 * Features:
 * - Auto-detects LangSmith configuration from environment
 * - Validates API key before tests start
 * - Logs LangSmith status to console
 * - Provides helper functions for trace URLs
 */

import { test as base } from '@playwright/test';

interface LangSmithConfig {
  enabled: boolean;
  apiKey?: string;
  project?: string;
  endpoint?: string;
}

/**
 * Get LangSmith configuration from environment
 */
function getLangSmithConfig(): LangSmithConfig {
  const enabled = process.env.LANGSMITH_TRACING === 'true';
  const apiKey = process.env.LANGSMITH_API_KEY;
  const project = process.env.LANGSMITH_PROJECT || 'aegis-rag-e2e';
  const endpoint = process.env.LANGSMITH_ENDPOINT || 'https://api.smith.langchain.com';

  return {
    enabled,
    apiKey: enabled ? apiKey : undefined,
    project,
    endpoint,
  };
}

/**
 * Validate LangSmith configuration
 * Throws error if LANGSMITH_TRACING=true but API key is missing
 */
function validateLangSmithConfig(config: LangSmithConfig): void {
  if (!config.enabled) {
    console.log('ℹ️  LangSmith tracing: DISABLED');
    console.log('   To enable: Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in environment');
    return;
  }

  if (!config.apiKey) {
    throw new Error(
      'LangSmith tracing enabled (LANGSMITH_TRACING=true) but API key missing. ' +
        'Set LANGSMITH_API_KEY environment variable or disable with LANGSMITH_TRACING=false'
    );
  }

  console.log('✅ LangSmith tracing: ENABLED');
  console.log(`   Project: ${config.project}`);
  console.log(`   Endpoint: ${config.endpoint}`);
  console.log('   View traces: https://smith.langchain.com');
}

/**
 * Create a test fixture that provides LangSmith helpers
 */
export const test = base.extend<{ langsmith: typeof createLangSmithHelpers }>({
  langsmith: async ({}, use) => {
    const config = getLangSmithConfig();
    validateLangSmithConfig(config);

    const helpers = createLangSmithHelpers(config);
    await use(helpers);
  },
});

/**
 * Create helper functions for LangSmith operations
 */
function createLangSmithHelpers(config: LangSmithConfig) {
  return {
    /**
     * Get the URL to view this test's traces in LangSmith
     * Constructs: https://smith.langchain.com/projects/PROJECTNAME?tab=runs
     */
    getProjectUrl(): string {
      if (!config.enabled) {
        return 'LangSmith tracing disabled';
      }
      return `https://smith.langchain.com/projects/${encodeURIComponent(config.project)}?tab=runs`;
    },

    /**
     * Check if LangSmith tracing is enabled
     */
    isEnabled(): boolean {
      return config.enabled;
    },

    /**
     * Log LangSmith status for this test
     */
    logStatus(testName: string): void {
      if (!config.enabled) {
        console.log(`[${testName}] LangSmith tracing: disabled`);
        return;
      }
      console.log(`[${testName}] LangSmith tracing: enabled`);
      console.log(`  View traces: ${this.getProjectUrl()}`);
    },

    /**
     * Get environment variables needed for LangSmith
     * Use in API calls to ensure backend has correct config
     */
    getEnvironmentVariables(): Record<string, string> {
      if (!config.enabled || !config.apiKey) {
        return {
          LANGSMITH_TRACING: 'false',
          LANGCHAIN_TRACING_V2: 'false',
        };
      }
      return {
        LANGSMITH_TRACING: 'true',
        LANGSMITH_API_KEY: config.apiKey,
        LANGSMITH_PROJECT: config.project,
        LANGSMITH_ENDPOINT: config.endpoint,
        LANGCHAIN_TRACING_V2: 'true',
        LANGCHAIN_API_KEY: config.apiKey,
        LANGCHAIN_PROJECT: config.project,
        LANGCHAIN_ENDPOINT: config.endpoint,
      };
    },
  };
}

export { test as default };
