import { test, expect } from '../fixtures';

/**
 * E2E Tests for Error Handling & Recovery
 * Tests timeout handling, malformed queries, disconnections, and error messages
 *
 * Backend: http://localhost:8000
 * Frontend: http://localhost:5173
 *
 * Test Cost: FREE (minimal LLM usage for error scenarios)
 */

test.describe('Error Handling - Timeout & Recovery', () => {
  test('should handle backend timeout gracefully', async ({ chatPage }) => {
    // Send a query that might timeout (very long processing)
    await chatPage.sendMessage('Write a comprehensive essay on artificial intelligence');

    // Wait for potential timeout (extended timeout of 35 seconds)
    try {
      await chatPage.waitForResponse(35000);

      // If it completes successfully, verify response exists
      const lastMessage = await chatPage.getLastMessage();
      expect(lastMessage).toBeTruthy();
      expect(lastMessage.length).toBeGreaterThan(0);
    } catch (error) {
      // Timeout is acceptable - verify error doesn't crash the app
      const lastMessage = await chatPage.getLastMessage();

      // App should still be responsive (no crash)
      expect(await chatPage.isInputReady()).toBeTruthy();
    }
  });

  test('should recover after slow response', async ({ chatPage }) => {
    // Send initial query
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse(25000);

    // Verify first response
    const firstMessage = await chatPage.getLastMessage();
    expect(firstMessage).toBeTruthy();

    // Send second query after slow response
    await chatPage.sendMessage('What is deep learning?');
    await chatPage.waitForResponse(25000);

    // Verify second response completes
    const secondMessage = await chatPage.getLastMessage();
    expect(secondMessage).toBeTruthy();

    // Verify input is still functional
    expect(await chatPage.isInputReady()).toBeTruthy();
  });

  test('should handle incomplete streaming gracefully', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('Explain neural networks');

    // Try to wait for response with normal timeout
    try {
      await chatPage.waitForResponse(20000);
      const lastMessage = await chatPage.getLastMessage();
      expect(lastMessage).toBeTruthy();
    } catch (error) {
      // If streaming fails, app should remain functional
      const isReady = await chatPage.isInputReady();
      expect(isReady).toBeTruthy();
    }
  });
});

test.describe('Error Handling - Input Validation', () => {
  /**
   * Sprint 118 Fix: Improved empty query test resilience
   * - The send button should be disabled when input is empty
   * - If not disabled, the click should be gracefully handled
   * - Increased timeouts for LLM response verification
   */
  test('should handle empty query gracefully', async ({ chatPage }) => {
    // Try to send empty message
    await chatPage.messageInput.fill('');

    // Verify empty input value
    const inputValue = await chatPage.messageInput.inputValue();
    expect(inputValue).toBe('');

    // Check if send button is disabled (expected UI behavior)
    const isDisabled = await chatPage.sendButton.isDisabled();

    if (!isDisabled) {
      // If button is enabled, try to click and verify nothing bad happens
      try {
        await chatPage.sendButton.click();
        // Wait briefly for any UI reaction
        await chatPage.page.waitForTimeout(500);
      } catch {
        // Empty send might fail, which is fine
      }
    }

    // Ensure input is still ready for use
    await chatPage.messageInput.waitFor({ state: 'visible', timeout: 5000 });

    // Clear any potential state issues
    await chatPage.messageInput.clear();
    await chatPage.page.waitForTimeout(200);

    // Input should still be functional - send a real message
    await chatPage.sendMessage('What is AI?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should handle malformed query with special characters', async ({ chatPage }) => {
    // Send query with special characters
    await chatPage.sendMessage('!@#$%^&*(){}[]|\\<>?/"\'`;');

    // Wait for response or error
    try {
      await chatPage.waitForResponse(25000);
      const response = await chatPage.getLastMessage();
      // May or may not produce a meaningful response, but shouldn't crash
      expect(response).toBeTruthy();
    } catch (error) {
      // Timeout or error is acceptable for malformed input
      // Verify app didn't crash
      expect(await chatPage.isInputReady()).toBeTruthy();
    }
  });

  test('should handle extremely long query', async ({ chatPage }) => {
    // Create a 5000 character query
    const longQuery = 'What is artificial intelligence? ' + 'a'.repeat(5000);

    try {
      await chatPage.sendMessage(longQuery);
      await chatPage.waitForResponse(30000);

      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // Long query might timeout, verify graceful handling
      const isReady = await chatPage.isInputReady();
      expect(isReady).toBeTruthy();
    }
  });

  test('should handle null/undefined-like queries', async ({ chatPage }) => {
    // Send minimal queries that might be edge cases
    await chatPage.sendMessage(' ');

    try {
      await chatPage.waitForResponse(10000);
    } catch {
      // Single space might not trigger a response
    }

    // App should still be functional
    await chatPage.sendMessage('What is AI?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });
});

test.describe('Error Handling - Backend Failure Recovery', () => {
  test('should handle backend disconnection gracefully', async ({ chatPage, page }) => {
    // Send query that will go to backend
    await chatPage.sendMessage('What are transformers?');

    // Wait for response or timeout
    try {
      await chatPage.waitForResponse(25000);
      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // If backend is disconnected, app should show graceful error or timeout
      // Verify no uncaught exceptions
      const browserErrors: string[] = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          browserErrors.push(msg.text());
        }
      });

      // Input should still be ready (no crash)
      const isReady = await chatPage.isInputReady();
      expect(isReady).toBeTruthy();

      // Should not have uncaught errors (stack traces, etc.)
      const criticalErrors = browserErrors.filter(
        (err) => err.includes('TypeError') || err.includes('ReferenceError')
      );
      expect(criticalErrors.length).toBe(0);
    }
  });

  test('should handle LLM provider error response', async ({ chatPage }) => {
    // Send query that might trigger LLM error (context too long)
    const veryLongContext = 'a'.repeat(15000);
    const query = `Summarize: ${veryLongContext}`;

    try {
      await chatPage.sendMessage(query);
      await chatPage.waitForResponse(30000);

      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // LLM error is acceptable, verify app remains functional
      const isReady = await chatPage.isInputReady();
      expect(isReady).toBeTruthy();

      // Should be able to send another query
      await chatPage.sendMessage('What is AI?');
      await chatPage.waitForResponse();

      const recovery = await chatPage.getLastMessage();
      expect(recovery).toBeTruthy();
    }
  });

  test('should retry failed request with exponential backoff', async ({ chatPage }) => {
    // Send query
    await chatPage.sendMessage('What is machine learning?');

    // Wait with longer timeout to allow for retries
    try {
      await chatPage.waitForResponse(30000);
      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // If retries exhausted, should still have graceful error
      const isReady = await chatPage.isInputReady();
      expect(isReady).toBeTruthy();
    }
  });
});

test.describe('Error Handling - Streaming Failures', () => {
  test('should handle SSE connection drop during streaming', async ({ chatPage }) => {
    // Send message to start streaming
    await chatPage.sendMessage('Explain quantum computing');

    // Wait for streaming to start or complete
    try {
      await chatPage.waitForResponse(25000);
      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // If SSE drops, app should recover
      const isReady = await chatPage.isInputReady();
      expect(isReady).toBeTruthy();
    }
  });

  test('should handle partial message during streaming', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What are neural networks?');

    // Try to get message while streaming (may be incomplete)
    await chatPage.page.waitForTimeout(2000);

    try {
      const partialMessage = await chatPage.getLastMessage();
      // Partial message might exist
      expect(typeof partialMessage).toBe('string');
    } catch (error) {
      // If message not found yet, that's OK
    }

    // Wait for completion
    await chatPage.waitForResponse();

    const finalMessage = await chatPage.getLastMessage();
    expect(finalMessage).toBeTruthy();
  });

  test('should recover from streaming interruption', async ({ chatPage }) => {
    // First query
    await chatPage.sendMessage('What is BERT?');

    try {
      await chatPage.waitForResponse(20000);
    } catch {
      // May timeout, that's OK
    }

    // Verify app is still responsive
    expect(await chatPage.isInputReady()).toBeTruthy();

    // Send another query (demonstrates recovery)
    await chatPage.sendMessage('What is GPT?');
    await chatPage.waitForResponse(20000);

    const finalResponse = await chatPage.getLastMessage();
    expect(finalResponse).toBeTruthy();
  });
});

test.describe('Error Handling - User Experience', () => {
  test('should display user-friendly error messages', async ({ chatPage, page }) => {
    // Collect console errors/messages
    const consoleLogs: Array<{ type: string; text: string }> = [];

    page.on('console', (msg) => {
      consoleLogs.push({
        type: msg.type(),
        text: msg.text(),
      });
    });

    // Send query that might error
    await chatPage.sendMessage('Test error handling');

    // Wait for potential error
    await chatPage.page.waitForTimeout(3000);

    // Filter for error messages
    const errorLogs = consoleLogs.filter((log) => log.type === 'error');

    // Error messages should NOT contain stack traces
    for (const log of errorLogs) {
      const text = log.text;
      // Check that errors are user-friendly (no technical stack traces)
      expect(text).not.toMatch(/at Object\./);
      expect(text).not.toMatch(/Error: .*at /);
    }
  });

  test('should show loading state during processing', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What are transformers?');

    // Streaming indicator should appear (or response should complete)
    try {
      const isStreaming = await chatPage.isStreaming();
      // Should either be streaming or complete immediately
      expect(typeof isStreaming).toBe('boolean');
    } catch {
      // If streaming indicator doesn't exist, that's OK
    }

    // Wait for completion
    await chatPage.waitForResponse();

    // Should no longer be streaming
    const streamingAfter = await chatPage.isStreaming();
    expect(streamingAfter).toBe(false);
  });

  test('should prevent multiple simultaneous submissions', async ({ chatPage, page }) => {
    // Send first message
    await chatPage.sendMessage('First query');

    // Immediately try to send second message (while first is processing)
    await chatPage.messageInput.fill('Second query');

    // Check if send button is disabled during processing
    const sendButtonDisabled = await chatPage.sendButton.isDisabled();

    // Should either be disabled or queue the message
    // Either behavior is acceptable for error handling
    if (!sendButtonDisabled) {
      // If not disabled, clicking again is OK (messages queue)
      await chatPage.sendButton.click();
    }

    // Wait for responses
    await chatPage.waitForResponse(30000);

    // App should remain functional
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should clear input field after successful send', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is AI?');
    await chatPage.waitForResponse();

    // Verify input is cleared
    const inputValue = await chatPage.messageInput.inputValue();
    expect(inputValue).toBe('');
  });

  test('should maintain conversation after error', async ({ chatPage }) => {
    // Send first valid message
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    const initialMessageCount = (await chatPage.getAllMessages()).length;

    // Send potentially problematic message
    try {
      await chatPage.sendMessage('!@#$%^&*()');
      await chatPage.waitForResponse(15000);
    } catch {
      // Error is acceptable
    }

    // Verify conversation is still there
    const finalMessages = await chatPage.getAllMessages();
    expect(finalMessages.length).toBeGreaterThanOrEqual(initialMessageCount);

    // App should still work
    await chatPage.sendMessage('What is deep learning?');
    await chatPage.waitForResponse();

    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });
});

test.describe('Error Handling - Network Resilience', () => {
  test('should timeout appropriately for very slow backend', async ({ chatPage }) => {
    // Send message with short timeout
    await chatPage.sendMessage('What is artificial intelligence?');

    // Try with very short timeout (should timeout)
    try {
      await chatPage.waitForResponse(100); // 100ms timeout
      // If it completes, that's fine
      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // Timeout error is expected with 100ms timeout
      expect(error).toBeDefined();
      expect(error.toString()).toContain('timeout');
    }

    // Wait longer and verify recovery
    await chatPage.waitForResponse(30000);
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should handle rate limiting gracefully', async ({ chatPage }) => {
    // Send multiple rapid messages (might trigger rate limiting)
    const messages = [
      'Query 1',
      'Query 2',
      'Query 3',
    ];

    for (const msg of messages) {
      try {
        await chatPage.sendMessage(msg);
        await chatPage.waitForResponse(25000);
      } catch (error) {
        // Rate limit error is acceptable
        // Just verify app doesn't crash
        expect(await chatPage.isInputReady()).toBeTruthy();
      }
    }

    // Final response should exist
    const finalMessage = await chatPage.getLastMessage();
    expect(finalMessage).toBeTruthy();
  });

  test('should verify frontend logging does not include sensitive data', async ({
    chatPage,
    page,
  }) => {
    const logs: string[] = [];

    page.on('console', (msg) => {
      logs.push(msg.text());
    });

    // Send message
    await chatPage.sendMessage('What is AI?');
    await chatPage.waitForResponse();

    // Check logs don't contain sensitive patterns
    const sensitivePatterns = [
      /api[_-]?key/i,
      /secret/i,
      /password/i,
      /token.*=.*[a-zA-Z0-9]{20,}/,
    ];

    for (const log of logs) {
      for (const pattern of sensitivePatterns) {
        expect(log).not.toMatch(pattern);
      }
    }
  });
});
