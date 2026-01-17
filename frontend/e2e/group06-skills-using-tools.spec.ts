/**
 * E2E Tests for Sprint 102 - Group 6: Skills Using Tools
 *
 * Tests end-to-end flows of skills invoking MCP tools:
 * - Skill can invoke bash tool
 * - Skill can invoke python tool
 * - Skill can invoke browser tool
 * - End-to-end flow (skill → tool → result)
 * - Error handling when tool fails
 *
 * Prerequisites:
 * - Backend running on http://localhost:8000
 * - Frontend running on http://localhost:80
 * - MCP servers (bash, python, browser) connected
 * - Skills service with active skills
 *
 * Test Strategy:
 * - Use chat interface to trigger skills
 * - Skills should automatically invoke appropriate tools
 * - Verify tool execution results appear in chat
 */

import { test, expect, setupAuthMocking } from './fixtures';
import { Page } from '@playwright/test';

// Test configuration
const BACKEND_URL = 'http://localhost:8000';
const TIMEOUT = 30000; // 30s for LLM + tool execution

/**
 * Helper: Navigate to chat page
 */
async function navigateToChat(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // Verify chat interface loaded
  const messageInput = page.locator('[data-testid="message-input"]');
  await expect(messageInput).toBeVisible({ timeout: 10000 });
}

/**
 * Helper: Send chat message and wait for response
 */
async function sendChatMessage(page: Page, message: string) {
  const messageInput = page.locator('[data-testid="message-input"]');
  const sendButton = page.locator('[data-testid="send-button"]');

  await messageInput.fill(message);
  await sendButton.click();

  // Wait for response to appear
  await page.waitForSelector('[data-testid^="message-"]', {
    state: 'visible',
    timeout: TIMEOUT
  });
}

/**
 * Helper: Wait for tool execution to complete in chat
 */
async function waitForToolExecutionInChat(page: Page, toolName: string) {
  // Wait for tool execution indicator
  await page.waitForSelector(`[data-testid="tool-execution-${toolName}"]`, {
    state: 'visible',
    timeout: TIMEOUT
  });

  // Wait for tool execution to complete
  await page.waitForSelector(`[data-testid="tool-execution-${toolName}"][data-status="completed"]`, {
    timeout: TIMEOUT
  });
}

// Sprint 106: Skip all - Tests rely on skill-tool integration UI that doesn't match expectations
// Bug: Chat skill invocation flow doesn't match test expectations
test.describe('Group 6: Skills Using Tools', () => {
  test.beforeEach(async ({ page }) => {
    // Setup authentication
    await setupAuthMocking(page);

    // Mock MCP health - all servers connected
    await page.route('**/api/v1/mcp/health', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          servers: {
            'bash': {
              status: 'connected',
              tools_count: 8,
              last_heartbeat: new Date().toISOString()
            },
            'python': {
              status: 'connected',
              tools_count: 5,
              last_heartbeat: new Date().toISOString()
            },
            'browser': {
              status: 'connected',
              tools_count: 15,
              last_heartbeat: new Date().toISOString()
            }
          }
        })
      });
    });

    // Mock skills list - all active
    await page.route('**/api/v1/skills', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              name: 'bash_executor',
              is_active: true,
              tools: ['bash', 'shell_execute']
            },
            {
              name: 'python_runner',
              is_active: true,
              tools: ['python_exec', 'notebook_run']
            },
            {
              name: 'web_navigator',
              is_active: true,
              tools: ['browser_navigate', 'browser_click', 'browser_snapshot']
            }
          ],
          total: 3
        })
      });
    });
  });

  test('should invoke bash tool via skill', async ({ page }) => {
    // Mock chat endpoint with bash tool execution
    await page.route('**/api/v1/chat/stream', (route) => {
      // Simulate streaming response with tool execution
      const events = [
        { type: 'message_start', message: 'Executing bash command...' },
        { type: 'tool_use', tool: 'bash', parameters: { command: 'echo "Hello from bash"' } },
        { type: 'tool_result', tool: 'bash', result: 'Hello from bash\n', success: true },
        { type: 'message_complete', message: 'Bash command executed successfully. Output: Hello from bash' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message that should trigger bash skill
    await sendChatMessage(page, 'Run bash command: echo "Hello from bash"');

    // Wait for tool execution indicator
    const toolExecution = page.locator('[data-testid*="tool-bash"]');
    await expect(toolExecution).toBeVisible({ timeout: TIMEOUT });

    // Verify bash command was executed
    await expect(page.locator('text=/Hello from bash/i')).toBeVisible({ timeout: 5000 });

    // Verify success indicator
    const successIcon = page.locator('[data-testid="tool-status-success"]');
    await expect(successIcon).toBeVisible();
  });

  test('should invoke python tool via skill', async ({ page }) => {
    // Mock chat endpoint with python tool execution
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Executing Python code...' },
        { type: 'tool_use', tool: 'python_exec', parameters: { code: 'print(2 + 2)' } },
        { type: 'tool_result', tool: 'python_exec', result: '4\n', success: true },
        { type: 'message_complete', message: 'Python code executed. Result: 4' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message that should trigger python skill
    await sendChatMessage(page, 'Run Python: print(2 + 2)');

    // Wait for tool execution indicator
    const toolExecution = page.locator('[data-testid*="tool-python"]');
    await expect(toolExecution).toBeVisible({ timeout: TIMEOUT });

    // Verify python code was executed and result shown
    await expect(page.locator('text=/Result: 4/i')).toBeVisible({ timeout: 5000 });

    // Verify success indicator
    const successIcon = page.locator('[data-testid="tool-status-success"]');
    await expect(successIcon).toBeVisible();
  });

  test('should invoke browser tool via skill', async ({ page }) => {
    // Mock chat endpoint with browser tool execution
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Navigating to website...' },
        { type: 'tool_use', tool: 'browser_navigate', parameters: { url: 'https://example.com' } },
        { type: 'tool_result', tool: 'browser_navigate', result: { url: 'https://example.com', title: 'Example Domain' }, success: true },
        { type: 'message_complete', message: 'Successfully navigated to Example Domain' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message that should trigger browser skill
    await sendChatMessage(page, 'Navigate to https://example.com');

    // Wait for tool execution indicator
    const toolExecution = page.locator('[data-testid*="tool-browser"]');
    await expect(toolExecution).toBeVisible({ timeout: TIMEOUT });

    // Verify browser navigation result
    await expect(page.locator('text=/Example Domain/i')).toBeVisible({ timeout: 5000 });

    // Verify success indicator
    const successIcon = page.locator('[data-testid="tool-status-success"]');
    await expect(successIcon).toBeVisible();
  });

  test('should handle end-to-end flow: skill → tool → result', async ({ page }) => {
    // Mock complete E2E flow with multiple tool invocations
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Analyzing request...' },
        { type: 'skill_activated', skill: 'bash_executor', reason: 'User requested file listing' },
        { type: 'tool_use', tool: 'bash', parameters: { command: 'ls -la /tmp' } },
        { type: 'tool_result', tool: 'bash', result: 'total 8\ndrwxrwxrwt 10 root root 4096 Jan 15 12:00 .\ndrwxr-xr-x 20 root root 4096 Jan 15 11:00 ..', success: true },
        { type: 'message_complete', message: 'Found 10 items in /tmp directory.' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message
    await sendChatMessage(page, 'List files in /tmp directory');

    // 1. Verify skill activation indicator
    const skillActivation = page.locator('[data-testid="skill-activated-bash_executor"]');
    await expect(skillActivation).toBeVisible({ timeout: 10000 });

    // 2. Verify tool execution indicator
    const toolExecution = page.locator('[data-testid*="tool-bash"]');
    await expect(toolExecution).toBeVisible({ timeout: 10000 });

    // 3. Verify tool result is displayed
    await expect(page.locator('text=/drwxrwxrwt/i')).toBeVisible({ timeout: 5000 });

    // 4. Verify final message
    await expect(page.locator('text=/Found 10 items/i')).toBeVisible({ timeout: 5000 });

    // Take screenshot of complete flow
    await page.screenshot({
      path: 'test-results/group06-e2e-flow-success.png',
      fullPage: true
    });
  });

  test('should handle tool execution errors gracefully', async ({ page }) => {
    // Mock chat endpoint with tool execution error
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Executing bash command...' },
        { type: 'tool_use', tool: 'bash', parameters: { command: 'nonexistent-command' } },
        { type: 'tool_result', tool: 'bash', result: '', error: 'Command not found: nonexistent-command', success: false },
        { type: 'error', message: 'Tool execution failed. The command could not be found.' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message that will cause tool error
    await sendChatMessage(page, 'Run bash: nonexistent-command');

    // Wait for tool execution indicator
    const toolExecution = page.locator('[data-testid*="tool-bash"]');
    await expect(toolExecution).toBeVisible({ timeout: TIMEOUT });

    // Verify error indicator is shown
    const errorIcon = page.locator('[data-testid="tool-status-error"]');
    await expect(errorIcon).toBeVisible({ timeout: 5000 });

    // Verify error message is displayed
    await expect(page.locator('text=/Command not found/i')).toBeVisible({ timeout: 5000 });

    // Take screenshot of error state
    await page.screenshot({
      path: 'test-results/group06-tool-error.png',
      fullPage: true
    });
  });

  test('should handle skill activation failures', async ({ page }) => {
    // Mock chat endpoint with skill activation failure
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Analyzing request...' },
        { type: 'skill_activation_failed', skill: 'bash_executor', reason: 'Skill is currently disabled' },
        { type: 'error', message: 'Unable to execute request. The required skill is not available.' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message that requires unavailable skill
    await sendChatMessage(page, 'Run bash command: echo test');

    // Verify error message about skill not available
    await expect(page.locator('text=/skill is not available/i')).toBeVisible({ timeout: 10000 });

    // Verify no tool execution occurred
    const toolExecution = page.locator('[data-testid*="tool-bash"]');
    await expect(toolExecution).not.toBeVisible();
  });

  test('should handle timeout during tool execution', async ({ page }) => {
    // Mock chat endpoint with timeout
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Executing long-running task...' },
        { type: 'tool_use', tool: 'python_exec', parameters: { code: 'import time; time.sleep(60)' } },
        { type: 'tool_timeout', tool: 'python_exec', timeout: 30 },
        { type: 'error', message: 'Tool execution timed out after 30 seconds.' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message that will timeout
    await sendChatMessage(page, 'Run Python: import time; time.sleep(60)');

    // Wait for tool execution indicator
    const toolExecution = page.locator('[data-testid*="tool-python"]');
    await expect(toolExecution).toBeVisible({ timeout: TIMEOUT });

    // Verify timeout message is displayed
    await expect(page.locator('text=/timed out/i')).toBeVisible({ timeout: TIMEOUT });

    // Verify timeout indicator
    const timeoutIcon = page.locator('[data-testid="tool-status-timeout"]');
    await expect(timeoutIcon).toBeVisible();
  });

  test('should display tool execution progress indicators', async ({ page }) => {
    // Mock chat endpoint with progress updates
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Starting task...' },
        { type: 'tool_use', tool: 'bash', parameters: { command: 'complex-script.sh' } },
        { type: 'tool_progress', tool: 'bash', progress: 25, message: 'Initializing...' },
        { type: 'tool_progress', tool: 'bash', progress: 50, message: 'Processing...' },
        { type: 'tool_progress', tool: 'bash', progress: 75, message: 'Finalizing...' },
        { type: 'tool_result', tool: 'bash', result: 'Task completed successfully', success: true },
        { type: 'message_complete', message: 'All done!' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message
    await sendChatMessage(page, 'Run complex script');

    // Verify progress indicator appears
    const progressBar = page.locator('[data-testid="tool-progress-bar"]');
    await expect(progressBar).toBeVisible({ timeout: 10000 });

    // Verify progress updates (may be too fast to catch all stages)
    await expect(page.locator('text=/Processing/i')).toBeVisible({ timeout: 5000 });

    // Verify completion
    await expect(page.locator('text=/All done/i')).toBeVisible({ timeout: 5000 });
  });

  test('should handle multiple concurrent tool executions', async ({ page }) => {
    // Mock chat endpoint with parallel tool executions
    await page.route('**/api/v1/chat/stream', (route) => {
      const events = [
        { type: 'message_start', message: 'Executing multiple tasks in parallel...' },
        { type: 'tool_use', tool: 'bash', parameters: { command: 'task1.sh' }, execution_id: 'exec1' },
        { type: 'tool_use', tool: 'python_exec', parameters: { code: 'task2()' }, execution_id: 'exec2' },
        { type: 'tool_result', tool: 'bash', result: 'Task 1 complete', success: true, execution_id: 'exec1' },
        { type: 'tool_result', tool: 'python_exec', result: 'Task 2 complete', success: true, execution_id: 'exec2' },
        { type: 'message_complete', message: 'Both tasks completed successfully.' }
      ];

      const stream = events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('');
      route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: stream
      });
    });

    await navigateToChat(page);

    // Send message requesting parallel execution
    await sendChatMessage(page, 'Run task1.sh and task2() in parallel');

    // Verify both tool executions appear
    const bashTool = page.locator('[data-testid*="tool-bash"]');
    const pythonTool = page.locator('[data-testid*="tool-python"]');

    await expect(bashTool).toBeVisible({ timeout: TIMEOUT });
    await expect(pythonTool).toBeVisible({ timeout: TIMEOUT });

    // Verify both results appear
    await expect(page.locator('text=/Task 1 complete/i')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=/Task 2 complete/i')).toBeVisible({ timeout: 5000 });

    // Take screenshot of parallel execution
    await page.screenshot({
      path: 'test-results/group06-parallel-execution.png',
      fullPage: true
    });
  });
});
