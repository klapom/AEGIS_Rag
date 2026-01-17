/**
 * E2E Tests for Sprint 102 - Group 4: Browser Tools
 *
 * Tests browser MCP tool integration:
 * - Browser tools available in UI
 * - Navigate to URL command
 * - Click element command
 * - Take screenshot command
 * - Evaluate JavaScript command
 *
 * Prerequisites:
 * - Backend running on http://localhost:8000
 * - Frontend running on http://localhost:80
 * - MCP browser server connected and active
 *
 * Test Data Location: /home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/fixtures/test-data.ts
 */

import { test, expect, setupAuthMocking, navigateClientSide } from './fixtures';
import { Page } from '@playwright/test';

// Test configuration
const BACKEND_URL = 'http://localhost:8000';
const TIMEOUT = 30000; // 30s for LLM responses

/**
 * Helper: Navigate to MCP Tools page
 * Sprint 106 Fix: Use correct URL /admin/tools and navigateClientSide for auth
 */
async function navigateToMCPTools(page: Page) {
  await navigateClientSide(page, '/admin/tools');
  await page.waitForLoadState('networkidle');

  // Verify page loaded - accept various title formats
  const pageTitle = await page.locator('h1').textContent({ timeout: 5000 }).catch(() => '');
  if (!pageTitle?.includes('MCP') && !pageTitle?.includes('Tools')) {
    console.log('Page title:', pageTitle, '- may not match expected "MCP Tools"');
  }
}

/**
 * Helper: Wait for tool execution to complete
 */
async function waitForToolExecution(page: Page) {
  // Wait for loading state to disappear
  await page.waitForSelector('[data-testid="tool-execution-loading"]', {
    state: 'hidden',
    timeout: TIMEOUT
  });

  // Wait for result to appear
  await page.waitForSelector('[data-testid="tool-execution-result"]', {
    state: 'visible',
    timeout: TIMEOUT
  });
}

/**
 * Helper: Check if browser tools are available
 */
async function checkBrowserToolsAvailable(page: Page): Promise<boolean> {
  // Look for browser tools in the tool list
  const browserTools = [
    'browser_navigate',
    'browser_click',
    'browser_snapshot',
    'browser_evaluate'
  ];

  let foundTools = 0;
  for (const toolName of browserTools) {
    const tool = await page.locator(`[data-testid="tool-${toolName}"]`).count();
    if (tool > 0) foundTools++;
  }

  return foundTools >= 2; // At least 2 browser tools should be available
}

test.describe('Group 4: Browser MCP Tools', () => {
  test.beforeEach(async ({ page }) => {
    // Setup authentication
    await setupAuthMocking(page);

    // Mock MCP health endpoint - browser server connected
    await page.route('**/api/v1/mcp/health', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          servers: {
            'browser': {
              status: 'connected',
              tools_count: 15,
              last_heartbeat: new Date().toISOString()
            }
          }
        })
      });
    });

    // Mock MCP servers list - returns browser server with tools
    await page.route('**/api/v1/mcp/servers', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            name: 'browser',
            status: 'connected',
            description: 'Browser automation tools',
            url: 'stdio://browser-mcp',
            tools: [
              {
                name: 'browser_navigate',
                description: 'Navigate to a URL in the browser',
                server_name: 'browser',
                parameters: [
                  { name: 'url', type: 'string', description: 'The URL to navigate to', required: true }
                ]
              },
              {
                name: 'browser_click',
                description: 'Click an element in the browser',
                server_name: 'browser',
                parameters: [
                  { name: 'element', type: 'string', description: 'Element selector', required: true },
                  { name: 'ref', type: 'string', description: 'Element reference', required: false }
                ]
              },
              {
                name: 'browser_take_screenshot',
                description: 'Take a screenshot of the current page',
                server_name: 'browser',
                parameters: [
                  { name: 'filename', type: 'string', description: 'Screenshot filename', required: false },
                  { name: 'type', type: 'string', description: 'Image type (png/jpg)', required: false }
                ]
              },
              {
                name: 'browser_evaluate',
                description: 'Evaluate JavaScript in the browser',
                server_name: 'browser',
                parameters: [
                  { name: 'function', type: 'string', description: 'JavaScript function to execute', required: true }
                ]
              }
            ],
            last_connected: new Date().toISOString()
          }
        ])
      });
    });

    // Mock MCP tools list (GET) - populates tool dropdown
    await page.route('**/api/v1/mcp/tools', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            name: 'browser_navigate',
            description: 'Navigate to a URL in the browser',
            server_name: 'browser',
            parameters: [
              { name: 'url', type: 'string', description: 'The URL to navigate to', required: true }
            ]
          },
          {
            name: 'browser_click',
            description: 'Click an element in the browser',
            server_name: 'browser',
            parameters: [
              { name: 'element', type: 'string', description: 'Element selector', required: true },
              { name: 'ref', type: 'string', description: 'Element reference', required: false }
            ]
          },
          {
            name: 'browser_take_screenshot',
            description: 'Take a screenshot of the current page',
            server_name: 'browser',
            parameters: [
              { name: 'filename', type: 'string', description: 'Screenshot filename', required: false },
              { name: 'type', type: 'string', description: 'Image type (png/jpg)', required: false }
            ]
          },
          {
            name: 'browser_evaluate',
            description: 'Evaluate JavaScript in the browser',
            server_name: 'browser',
            parameters: [
              { name: 'function', type: 'string', description: 'JavaScript function to execute', required: true }
            ]
          }
        ])
      });
    });
  });

  // Sprint 106: Skip - UI data-testids don't match (mcp-server-browser not found)
  // Bug: MCP Tools page lacks expected browser server data-testid attributes
  test('should display browser MCP tools in UI', async ({ page }) => {
    await navigateToMCPTools(page);

    // Check if browser server is listed
    const browserServer = page.locator('[data-testid="mcp-server-browser"]');
    await expect(browserServer).toBeVisible({ timeout: 10000 });

    // Verify status badge shows "connected"
    const statusBadge = browserServer.locator('[data-testid="server-status"]');
    await expect(statusBadge).toContainText('connected', { ignoreCase: true });

    // Expand browser server to show tools
    const toggleToolsButton = page.locator('[data-testid="toggle-tools-browser"]');
    await toggleToolsButton.click();
    await page.waitForSelector('[data-testid="tools-list-browser"]', { state: 'visible' });

    // Check for browser tools in the tool list
    const toolsAvailable = await checkBrowserToolsAvailable(page);

    if (!toolsAvailable) {
      // Take screenshot for debugging
      await page.screenshot({
        path: 'test-results/group04-browser-tools-not-found.png',
        fullPage: true
      });

      // Log available tools for debugging
      const allTools = await page.locator('[data-testid^="tool-"]').allTextContents();
      console.log('Available tools:', allTools);
    }

    expect(toolsAvailable).toBeTruthy();
  });

  // Sprint 106: Skip - UI data-testids don't match (tool-browser_navigate not found)
  test('should execute navigate to URL command', async ({ page }) => {
    // Mock tool execution endpoint
    await page.route('**/api/v1/mcp/tools/execute', (route) => {
      const request = route.request();
      const postData = request.postDataJSON();

      if (postData.tool_name === 'browser_navigate') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            result: {
              url: postData.parameters.url,
              title: 'Example Domain',
              status: 200
            },
            execution_time: 1.2
          })
        });
      } else {
        route.continue();
      }
    });

    await navigateToMCPTools(page);

    // Select browser_navigate tool from dropdown in execution panel
    const toolSelector = page.locator('[data-testid="tool-selector"]');
    await toolSelector.selectOption('browser_navigate');

    // Wait for tool parameters to load
    await page.waitForSelector('[data-testid="param-url"]', { state: 'visible', timeout: 10000 });

    // Fill in URL parameter
    const urlInput = page.locator('[data-testid="param-url"]');
    await urlInput.fill('https://example.com');

    // Execute tool
    const executeButton = page.locator('[data-testid="execute-tool-button"]');
    await executeButton.click();

    // Wait for execution to complete
    await waitForToolExecution(page);

    // Verify result displays URL and title
    const result = page.locator('[data-testid="tool-execution-result"]');
    await expect(result).toContainText('example.com');
    await expect(result).toContainText('Example Domain');
  });

  // Sprint 106: Skip - UI data-testids don't match (tool-browser_click not found)
  test('should execute click element command', async ({ page }) => {
    // Mock tool execution endpoint
    await page.route('**/api/v1/mcp/tools/execute', (route) => {
      const request = route.request();
      const postData = request.postDataJSON();

      if (postData.tool_name === 'browser_click') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            result: {
              element: postData.parameters.element,
              clicked: true,
              ref: postData.parameters.ref
            },
            execution_time: 0.5
          })
        });
      } else {
        route.continue();
      }
    });

    await navigateToMCPTools(page);

    // Select browser_click tool from dropdown in execution panel
    const toolSelector = page.locator('[data-testid="tool-selector"]');
    await toolSelector.selectOption('browser_click');

    // Wait for tool parameters to load
    await page.waitForSelector('[data-testid="param-element"]', { state: 'visible', timeout: 10000 });

    // Fill in element selector parameter
    const elementInput = page.locator('[data-testid="param-element"]');
    await elementInput.fill('Submit button');

    const refInput = page.locator('[data-testid="param-ref"]');
    await refInput.fill('button[type="submit"]');

    // Execute tool
    const executeButton = page.locator('[data-testid="execute-tool-button"]');
    await executeButton.click();

    // Wait for execution to complete
    await waitForToolExecution(page);

    // Verify result shows click succeeded
    const result = page.locator('[data-testid="tool-execution-result"]');
    await expect(result).toContainText('clicked');
  });

  // Sprint 106: Skip - UI data-testids don't match (tool-browser_take_screenshot not found)
  test('should execute take screenshot command', async ({ page }) => {
    // Mock tool execution endpoint
    await page.route('**/api/v1/mcp/tools/execute', (route) => {
      const request = route.request();
      const postData = request.postDataJSON();

      if (postData.tool_name === 'browser_take_screenshot') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            result: {
              filename: postData.parameters.filename || 'page-1234567890.png',
              path: '/tmp/screenshots/page-1234567890.png',
              size_bytes: 45678,
              type: postData.parameters.type || 'png'
            },
            execution_time: 0.8
          })
        });
      } else {
        route.continue();
      }
    });

    await navigateToMCPTools(page);

    // Select browser_take_screenshot tool from dropdown in execution panel
    const toolSelector = page.locator('[data-testid="tool-selector"]');
    await toolSelector.selectOption('browser_take_screenshot');

    // Wait for execute button to be enabled (screenshot has optional params)
    await page.waitForSelector('[data-testid="execute-tool-button"]', { state: 'visible', timeout: 10000 });

    // Fill in filename parameter (optional)
    const filenameInput = page.locator('[data-testid="param-filename"]');
    if (await filenameInput.isVisible()) {
      await filenameInput.fill('test-screenshot.png');
    }

    // Execute tool
    const executeButton = page.locator('[data-testid="execute-tool-button"]');
    await executeButton.click();

    // Wait for execution to complete
    await waitForToolExecution(page);

    // Verify result shows screenshot path
    const result = page.locator('[data-testid="tool-execution-result"]');
    await expect(result).toContainText('.png');
  });

  // Sprint 106: Skip - UI data-testids don't match (tool-browser_evaluate not found)
  test('should execute evaluate JavaScript command', async ({ page }) => {
    // Mock tool execution endpoint
    await page.route('**/api/v1/mcp/tools/execute', (route) => {
      const request = route.request();
      const postData = request.postDataJSON();

      if (postData.tool_name === 'browser_evaluate') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            result: {
              return_value: 'Hello from browser!',
              type: 'string'
            },
            execution_time: 0.3
          })
        });
      } else {
        route.continue();
      }
    });

    await navigateToMCPTools(page);

    // Select browser_evaluate tool from dropdown in execution panel
    const toolSelector = page.locator('[data-testid="tool-selector"]');
    await toolSelector.selectOption('browser_evaluate');

    // Wait for tool parameters to load
    await page.waitForSelector('[data-testid="param-function"]', { state: 'visible', timeout: 10000 });

    // Fill in JavaScript function parameter
    const functionInput = page.locator('[data-testid="param-function"]');
    await functionInput.fill('() => { return "Hello from browser!"; }');

    // Execute tool
    const executeButton = page.locator('[data-testid="execute-tool-button"]');
    await executeButton.click();

    // Wait for execution to complete
    await waitForToolExecution(page);

    // Verify result shows evaluated return value
    const result = page.locator('[data-testid="tool-execution-result"]');
    await expect(result).toContainText('Hello from browser!');
  });

  // Sprint 106: Skip - UI data-testids don't match (tool-browser_navigate not found)
  test('should handle tool execution errors gracefully', async ({ page }) => {
    // Mock tool execution endpoint with error
    await page.route('**/api/v1/mcp/tools/execute', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'Browser context not available',
          details: 'No active browser session found'
        })
      });
    });

    await navigateToMCPTools(page);

    // Select browser_navigate tool from dropdown in execution panel
    const toolSelector = page.locator('[data-testid="tool-selector"]');
    await toolSelector.selectOption('browser_navigate');

    // Wait for tool parameters to load
    await page.waitForSelector('[data-testid="param-url"]', { state: 'visible', timeout: 10000 });

    const urlInput = page.locator('[data-testid="param-url"]');
    await urlInput.fill('https://example.com');

    // Execute tool
    const executeButton = page.locator('[data-testid="execute-tool-button"]');
    await executeButton.click();

    // Wait for error message
    const errorMessage = page.locator('[data-testid="tool-execution-error"]');
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
    await expect(errorMessage).toContainText('Browser context not available');

    // Take screenshot for debugging
    await page.screenshot({
      path: 'test-results/group04-browser-tool-error.png',
      fullPage: true
    });
  });
});
