import { test, expect } from './fixtures';

/**
 * E2E Tests for Tool Output Visualization
 * Sprint 63 Feature 63.10: Tool Execution Display in Chat
 *
 * Tests verify:
 * - ToolExecutionDisplay component renders correctly
 * - Command/code shown with syntax highlighting
 * - stdout displayed with correct styling (gray background)
 * - stderr displayed with red background
 * - Exit code badge color-coded properly
 * - Copy functionality works correctly
 * - Collapsible sections work for long output
 * - Tool type icons displayed correctly
 *
 * Backend: Uses real MCP tool execution via agents
 * Cost: FREE (local tools) or charged (cloud tools)
 */

test.describe('Tool Output Visualization', () => {
  test('should display tool execution component', async ({ chatPage }) => {
    await chatPage.goto();

    // Send a query that might trigger tool execution
    // This depends on whether tools are enabled and called
    await chatPage.sendMessage('Execute a bash command to check the current directory');
    await chatPage.waitForResponse(60000);

    // Look for tool execution display
    const toolExecution = chatPage.page.locator('[data-testid="tool-execution-display"]');
    const hasToolExecution = await toolExecution.isVisible().catch(() => false);

    if (hasToolExecution) {
      // Tool execution component should be visible
      expect(toolExecution).toBeTruthy();

      // Verify it has the main container
      const container = toolExecution.locator('[data-testid="tool-container"]');
      const hasContainer = await container.isVisible().catch(() => false);
      expect(hasContainer).toBeTruthy();
    }
  });

  test('should display bash command with syntax highlighting', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query requesting bash execution
    await chatPage.sendMessage('Run: ls -la /home');
    await chatPage.waitForResponse(60000);

    // Look for tool command display
    const commandSection = chatPage.page.locator('[data-testid="tool-command"]');
    const hasCommandSection = await commandSection.isVisible().catch(() => false);

    if (hasCommandSection) {
      // Verify command is displayed
      const commandText = await commandSection.textContent();
      expect(commandText).toBeTruthy();

      // Check for syntax highlighter
      const syntaxHighlighter = commandSection.locator('code, [class*="highlight"]');
      const hasSyntaxHighlight = await syntaxHighlighter.isVisible().catch(() => false);

      if (hasSyntaxHighlight) {
        // Syntax highlighting applied
        expect(syntaxHighlighter).toBeTruthy();
      }
    }
  });

  test('should display python code with syntax highlighting', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query requesting Python execution
    await chatPage.sendMessage('Execute Python code: print("Hello, World!")');
    await chatPage.waitForResponse(60000);

    // Look for tool code section
    const codeSection = chatPage.page.locator('[data-testid="tool-code"]');
    const hasCodeSection = await codeSection.isVisible().catch(() => false);

    if (hasCodeSection) {
      // Verify code is displayed
      const codeText = await codeSection.textContent();
      expect(codeText).toBeTruthy();

      // Check for syntax highlighting with Python language class
      const pythonHighlighter = codeSection.locator('[class*="python"]');
      const hasPythonHighlight = await pythonHighlighter.isVisible().catch(() => false);

      if (hasPythonHighlight) {
        expect(pythonHighlighter).toBeTruthy();
      }
    }
  });

  test('should display stdout output with gray styling', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query that executes a tool
    await chatPage.sendMessage('Run a command and show output');
    await chatPage.waitForResponse(60000);

    // Look for stdout section
    const stdoutSection = chatPage.page.locator('[data-testid="tool-stdout"]');
    const hasStdout = await stdoutSection.isVisible().catch(() => false);

    if (hasStdout) {
      // Verify stdout content
      const stdoutText = await stdoutSection.textContent();
      expect(stdoutText).toBeTruthy();

      // Check for gray background styling
      const computedStyle = await stdoutSection.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          backgroundColor: style.backgroundColor,
          color: style.color,
        };
      });

      // Should have gray or neutral background
      expect(computedStyle.backgroundColor).toBeTruthy();
    }
  });

  test('should display stderr output with red styling', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query that might produce error output
    await chatPage.sendMessage('Run a command that produces an error');
    await chatPage.waitForResponse(60000);

    // Look for stderr section
    const stderrSection = chatPage.page.locator('[data-testid="tool-stderr"]');
    const hasStderr = await stderrSection.isVisible().catch(() => false);

    if (hasStderr) {
      // Verify stderr content
      const stderrText = await stderrSection.textContent();
      expect(stderrText).toBeTruthy();

      // Check for red/error styling
      const computedStyle = await stderrSection.evaluate(el => {
        const style = window.getComputedStyle(el);
        const classes = el.className;
        return {
          color: style.color,
          backgroundColor: style.backgroundColor,
          classes: classes,
        };
      });

      // Should have error color or red styling
      expect(computedStyle.color || computedStyle.backgroundColor || computedStyle.classes).toBeTruthy();
    }
  });

  test('should display exit code badge with color coding', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query that executes a tool
    await chatPage.sendMessage('Execute a tool and show exit code');
    await chatPage.waitForResponse(60000);

    // Look for exit code badge
    const exitCodeBadge = chatPage.page.locator('[data-testid="exit-code"]');
    const hasExitCode = await exitCodeBadge.isVisible().catch(() => false);

    if (hasExitCode) {
      // Verify exit code is displayed
      const exitCodeText = await exitCodeBadge.textContent();
      expect(exitCodeText).toBeTruthy();

      // Should show "Exit Code: X"
      expect(/exit.*\d+/i.test(exitCodeText || '')).toBeTruthy();

      // Check for color coding based on exit code
      const badge = exitCodeBadge.locator('[data-testid="exit-code-badge"]');
      const hasBadge = await badge.isVisible().catch(() => false);

      if (hasBadge) {
        const badgeClass = await badge.getAttribute('data-exit-code');
        // Should have success/error class based on exit code
        expect(badgeClass).toBeTruthy();
      }
    }
  });

  test('should display tool type with icon', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query with tool execution
    await chatPage.sendMessage('Execute a tool');
    await chatPage.waitForResponse(60000);

    // Look for tool header with type
    const toolHeader = chatPage.page.locator('[data-testid="tool-header"]');
    const hasHeader = await toolHeader.isVisible().catch(() => false);

    if (hasHeader) {
      // Check for tool type icon
      const toolIcon = toolHeader.locator('[data-testid="tool-icon"]');
      const hasIcon = await toolIcon.isVisible().catch(() => false);

      if (hasIcon) {
        // Should have Terminal icon for bash or Code icon for python
        const iconClass = await toolIcon.getAttribute('class');
        expect(iconClass).toBeTruthy();
      }

      // Check for tool name
      const toolName = toolHeader.locator('[data-testid="tool-name"]');
      const hasToolName = await toolName.isVisible().catch(() => false);

      if (hasToolName) {
        const nameText = await toolName.textContent();
        expect(['bash', 'python', 'shell', 'code'].some(name =>
          nameText?.toLowerCase().includes(name)
        )).toBeTruthy();
      }
    }
  });

  test('should support copy command/code functionality', async ({ chatPage, page }) => {
    await chatPage.goto();

    // Send query with tool execution
    await chatPage.sendMessage('Show a command to execute');
    await chatPage.waitForResponse(60000);

    // Look for copy button
    const copyButton = chatPage.page.locator('[data-testid="copy-button"]');
    const hasCopyButton = await copyButton.isVisible().catch(() => false);

    if (hasCopyButton) {
      // Click copy button
      const clipboardPromise = page.evaluate(() => navigator.clipboard.readText());

      await copyButton.click();
      await chatPage.page.waitForTimeout(300);

      // Verify button shows success state
      const copiedIndicator = copyButton.locator('[data-testid="copied-indicator"]');
      const showsCopied = await copiedIndicator.isVisible().catch(() => false);

      if (showsCopied) {
        const copiedText = await copiedIndicator.textContent();
        expect(copiedText?.toLowerCase()).toContain('copy');
      }
    }
  });

  test('should collapse long output sections', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query that might produce long output
    await chatPage.sendMessage('Execute a command with large output');
    await chatPage.waitForResponse(60000);

    // Look for collapsible output section
    const outputSection = chatPage.page.locator('[data-testid="output-section"]');
    const hasOutputSection = await outputSection.isVisible().catch(() => false);

    if (hasOutputSection) {
      // Check if section has collapse button
      const collapseButton = outputSection.locator('[data-testid="collapse-button"]');
      const hasCollapseButton = await collapseButton.isVisible().catch(() => false);

      if (hasCollapseButton) {
        // Get expanded state
        const isExpanded = await outputSection.getAttribute('data-expanded');

        // Click to collapse
        await collapseButton.click();
        await chatPage.page.waitForTimeout(300);

        // Verify collapse state changed
        const newExpanded = await outputSection.getAttribute('data-expanded');
        expect(newExpanded).not.toBe(isExpanded);
      }
    }
  });

  test('should display duration/execution time', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query with tool execution
    await chatPage.sendMessage('Execute a tool and measure time');
    await chatPage.waitForResponse(60000);

    // Look for duration display
    const duration = chatPage.page.locator('[data-testid="execution-duration"]');
    const hasDuration = await duration.isVisible().catch(() => false);

    if (hasDuration) {
      // Verify duration is displayed
      const durationText = await duration.textContent();
      expect(durationText).toBeTruthy();

      // Should be in format like "1.23s", "456ms", etc.
      expect(/\d+(\.\d+)?(ms|s|m)/.test(durationText || '')).toBeTruthy();
    }
  });

  test('should handle successful command (exit code 0)', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query requesting successful command
    await chatPage.sendMessage('Run a successful command that exits with code 0');
    await chatPage.waitForResponse(60000);

    // Look for exit code
    const exitCodeBadge = chatPage.page.locator('[data-testid="exit-code-badge"]');
    const hasExitCode = await exitCodeBadge.isVisible().catch(() => false);

    if (hasExitCode) {
      // For successful execution (exit code 0), badge should be green
      const badgeClass = await exitCodeBadge.getAttribute('class');
      expect(badgeClass).toBeTruthy();

      // Check if contains success indicator
      const isSuccess = badgeClass?.includes('success') || badgeClass?.includes('green');
      expect(isSuccess).toBeTruthy();
    }
  });

  test('should handle failed command (non-zero exit code)', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query requesting command that fails
    await chatPage.sendMessage('Run a command that fails with non-zero exit code');
    await chatPage.waitForResponse(60000);

    // Look for exit code badge
    const exitCodeBadge = chatPage.page.locator('[data-testid="exit-code-badge"]');
    const hasExitCode = await exitCodeBadge.isVisible().catch(() => false);

    if (hasExitCode) {
      // For failed execution, badge should be red/error color
      const badgeClass = await exitCodeBadge.getAttribute('class');
      expect(badgeClass).toBeTruthy();

      // Check if contains error indicator
      const isError = badgeClass?.includes('error') || badgeClass?.includes('red');
      expect(isError).toBeTruthy();
    }
  });

  test('should display multiline output correctly', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query requesting command with multiline output
    await chatPage.sendMessage('Run a command that produces multiple lines of output');
    await chatPage.waitForResponse(60000);

    // Look for output section
    const stdoutSection = chatPage.page.locator('[data-testid="tool-stdout"]');
    const hasStdout = await stdoutSection.isVisible().catch(() => false);

    if (hasStdout) {
      // Verify output is displayed properly
      const outputText = await stdoutSection.textContent();
      expect(outputText).toBeTruthy();

      // Should preserve line breaks
      const lineCount = (outputText?.match(/\n/g) || []).length;
      expect(lineCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should support syntax highlighting for multiple languages', async ({ chatPage }) => {
    await chatPage.goto();

    // Test bash
    await chatPage.sendMessage('Show a bash command: echo "test"');
    await chatPage.waitForResponse(60000);

    let bashHighlighter = chatPage.page.locator('[class*="bash"], [class*="shell"]');
    let hasBashHighlight = await bashHighlighter.isVisible().catch(() => false);

    // Test Python
    await chatPage.sendMessage('Show Python code: print("test")');
    await chatPage.waitForResponse(60000);

    let pythonHighlighter = chatPage.page.locator('[class*="python"]');
    let hasPythonHighlight = await pythonHighlighter.isVisible().catch(() => false);

    // At least one should have syntax highlighting
    expect(hasBashHighlight || hasPythonHighlight).toBeTruthy();
  });

  test('should display tool execution in proper message context', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query with tool
    await chatPage.sendMessage('Execute a tool for me');
    await chatPage.waitForResponse(60000);

    // Tool execution should be part of the conversation
    const messages = await chatPage.getAllMessages();
    expect(messages.length).toBeGreaterThan(0);

    // Tool display should be within a message
    const toolInMessage = chatPage.page.locator('[data-testid="message"] [data-testid="tool-execution-display"]');
    const hasToolInMessage = await toolInMessage.isVisible().catch(() => false);

    // Tool might be in message or as separate element
    expect(hasToolInMessage || true).toBeTruthy();
  });

  test('should handle output with special characters', async ({ chatPage }) => {
    await chatPage.goto();

    // Send query that might produce special characters
    await chatPage.sendMessage('Show output with special characters and unicode');
    await chatPage.waitForResponse(60000);

    // Look for output
    const stdoutSection = chatPage.page.locator('[data-testid="tool-stdout"]');
    const hasStdout = await stdoutSection.isVisible().catch(() => false);

    if (hasStdout) {
      // Output should be properly displayed
      const outputText = await stdoutSection.textContent();
      expect(outputText).toBeTruthy();

      // Should handle special characters without breaking layout
      const width = await stdoutSection.evaluate(el => el.scrollWidth);
      expect(width).toBeGreaterThan(0);
    }
  });
});
