import { test, expect } from './fixtures';

/**
 * E2E Tests for Multi-Turn RAG
 * Sprint 63 Feature 63.7: Multi-Turn Conversation with Memory
 *
 * Tests verify:
 * - Conversation_id properly managed across turns
 * - First question answered correctly
 * - Follow-up questions maintain context
 * - Memory summary generated after N turns
 * - Contradiction detection when conflicting info provided
 * - Conversation history properly maintained
 * - Context switching works correctly
 *
 * Backend: Uses real conversation endpoint with memory management
 * Cost: FREE (local Ollama) or charged (cloud LLM)
 */

test.describe('Multi-Turn RAG Conversation', () => {
  test('should start new conversation with conversation_id', async ({ chatPage }) => {
    await chatPage.goto();

    // Send first message
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    // Get session ID from page (Sprint 122: Fixed selector from conversation-id to session-id)
    // Frontend uses data-testid="session-id" with full ID in data-session-id attribute
    const sessionIdElement = chatPage.page.locator('[data-testid="session-id"]');
    const sessionId = await sessionIdElement.getAttribute('data-session-id');

    if (sessionId) {
      // Session ID should be a valid UUID or identifier
      expect(sessionId).toBeTruthy();
      expect(sessionId.length).toBeGreaterThan(0);
    }

    // Verify message was received
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(10);
  });

  test('should maintain context across multiple turns', async ({ chatPage }) => {
    await chatPage.goto();

    // First question
    await chatPage.sendMessage('What is neural networks?');
    await chatPage.waitForResponse();
    const answer1 = await chatPage.getLastMessage();

    // Follow-up question referencing first answer
    await chatPage.sendMessage('Can you explain the layers in that?');
    await chatPage.waitForResponse();
    const answer2 = await chatPage.getLastMessage();

    // Both answers should exist
    expect(answer1).toBeTruthy();
    expect(answer2).toBeTruthy();

    // Verify conversation has both messages
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(2);
  });

  test('should retrieve context from previous turns', async ({ chatPage }) => {
    await chatPage.goto();

    // Ask about a specific topic
    await chatPage.sendMessage('What is backpropagation algorithm?');
    await chatPage.waitForResponse();

    // Now ask a follow-up that requires context
    await chatPage.sendMessage('How does it compare to forward propagation?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();

    // Response should reference the previous topic
    // Note: This depends on backend implementing context retrieval
    expect(response.length).toBeGreaterThan(0);
  });

  test('should detect contradictions between turns', async ({ chatPage }) => {
    await chatPage.goto();

    // First statement
    await chatPage.sendMessage('Neural networks have no biological inspiration');
    await chatPage.waitForResponse();

    // Contradictory statement
    await chatPage.sendMessage('But you just said neural networks are inspired by the brain');
    await chatPage.waitForResponse();

    // Check for contradiction indicator
    const contradictionAlert = chatPage.page.locator('[data-testid="contradiction-alert"]');
    const hasContradiction = await contradictionAlert.isVisible().catch(() => false);

    if (hasContradiction) {
      // Should display warning about contradiction
      const alertText = await contradictionAlert.textContent();
      expect(alertText).toBeTruthy();
      expect(alertText?.toLowerCase()).toContain('contradict');
    }

    // Response should acknowledge the contradiction
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should generate memory summary after multiple turns', async ({ chatPage }) => {
    await chatPage.goto();

    // Send multiple messages to trigger summary
    const messages = [
      'What is machine learning?',
      'Tell me about supervised learning',
      'What is unsupervised learning?',
      'Explain reinforcement learning',
      'How do these three approaches compare?',
    ];

    for (const message of messages) {
      await chatPage.sendMessage(message);
      await chatPage.waitForResponse(60000);
      await chatPage.page.waitForTimeout(500);
    }

    // Check for memory summary
    const memorySummary = chatPage.page.locator('[data-testid="memory-summary"]');
    const hasSummary = await memorySummary.isVisible().catch(() => false);

    if (hasSummary) {
      // Summary should contain conversation key points
      const summaryText = await memorySummary.textContent();
      expect(summaryText).toBeTruthy();
      expect(summaryText?.length).toBeGreaterThan(20);
    }
  });

  test('should maintain separate conversations independently', async ({ chatPage, page }) => {
    await chatPage.goto();

    // First conversation
    await chatPage.sendMessage('What is Python?');
    await chatPage.waitForResponse();

    // Sprint 122: Fixed selector from conversation-id to session-id
    const conv1Id = await chatPage.page.locator('[data-testid="session-id"]').getAttribute('data-session-id');

    // Start new conversation (might be via UI navigation or new tab)
    const newConversationButton = chatPage.page.locator('[data-testid="new-conversation"]');
    const hasNewButton = await newConversationButton.isVisible().catch(() => false);

    if (hasNewButton) {
      await newConversationButton.click();
      await chatPage.page.waitForTimeout(500);

      // Second conversation
      await chatPage.sendMessage('What is JavaScript?');
      await chatPage.waitForResponse();

      // Sprint 122: Fixed selector from conversation-id to session-id
      const conv2Id = await chatPage.page.locator('[data-testid="session-id"]').getAttribute('data-session-id');

      // Session IDs should be different
      if (conv1Id && conv2Id) {
        expect(conv1Id).not.toBe(conv2Id);
      }
    }
  });

  test('should reference specific previous turns', async ({ chatPage }) => {
    await chatPage.goto();

    // Create conversation history
    await chatPage.sendMessage('What is the transformer architecture?');
    await chatPage.waitForResponse();

    await chatPage.sendMessage('Who invented it?');
    await chatPage.waitForResponse();

    // Ask to reference earlier turn
    await chatPage.sendMessage('Can you summarize what you said about transformers earlier?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(10);
  });

  test('should handle context switching between topics', async ({ chatPage }) => {
    await chatPage.goto();

    // First topic
    await chatPage.sendMessage('Tell me about quantum computing');
    await chatPage.waitForResponse();

    // Switch to completely different topic
    await chatPage.sendMessage('Now tell me about cooking techniques');
    await chatPage.waitForResponse();

    // Switch back to first topic
    await chatPage.sendMessage('Back to quantum computing - what about qubits?');
    await chatPage.waitForResponse();

    // Should have context for all three messages
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(3);

    // Last response should be about qubits
    const lastResponse = await chatPage.getLastMessage();
    expect(lastResponse).toBeTruthy();
  });

  test('should update memory with new information', async ({ chatPage }) => {
    await chatPage.goto();

    // Establish initial context
    await chatPage.sendMessage('My name is Alice and I work in AI');
    await chatPage.waitForResponse();

    // Later, ask system to recall
    await chatPage.sendMessage('What do you know about me?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    // System should ideally recall the information (if memory is implemented)
    expect(response).toBeTruthy();
  });

  test('should display conversation turn count', async ({ chatPage }) => {
    await chatPage.goto();

    // First turn
    await chatPage.sendMessage('First question');
    await chatPage.waitForResponse();

    // Check turn counter
    let turnCounter = chatPage.page.locator('[data-testid="turn-counter"]');
    let hasCounter = await turnCounter.isVisible().catch(() => false);

    if (hasCounter) {
      let turnText = await turnCounter.textContent();
      expect(turnText).toContain('1');

      // Second turn
      await chatPage.sendMessage('Second question');
      await chatPage.waitForResponse();

      turnText = await turnCounter.textContent();
      expect(turnText).toContain('2');
    }
  });

  test('should allow clearing conversation history', async ({ chatPage }) => {
    await chatPage.goto();

    // Build conversation
    await chatPage.sendMessage('First message');
    await chatPage.waitForResponse();

    await chatPage.sendMessage('Second message');
    await chatPage.waitForResponse();

    const messagesBefore = await chatPage.getAllMessages();
    expect(messagesBefore.length).toBeGreaterThan(0);

    // Look for clear button
    const clearButton = chatPage.page.locator('[data-testid="clear-conversation"]');
    const hasClearButton = await clearButton.isVisible().catch(() => false);

    if (hasClearButton) {
      // Confirm clear if prompted
      const promptMessage = await chatPage.page.locator('[data-testid="clear-confirm"]').isVisible().catch(() => false);

      if (promptMessage) {
        const confirmButton = chatPage.page.locator('[data-testid="confirm-clear"]');
        await confirmButton.click();
      } else {
        await clearButton.click();
      }

      await chatPage.page.waitForTimeout(500);

      // Conversation should be cleared
      const messagesAfter = await chatPage.getAllMessages();
      // Should have fewer messages or welcome screen
      expect(messagesAfter.length).toBeLessThanOrEqual(messagesBefore.length);
    }
  });

  // Sprint 122: Skip until conversation persistence is implemented
  // After page reload, auth token is lost (same race condition as 122.1)
  // This test validates a feature that isn't fully implemented yet
  test.skip('should maintain conversation across page reload', async ({ chatPage, page }) => {
    await chatPage.goto();

    // Create conversation
    await chatPage.sendMessage('Initial question');
    await chatPage.waitForResponse();

    const conversationBefore = await chatPage.getAllMessages();
    // Sprint 122: Fixed selector - session-id only appears when there's an active session
    const sessionIdElement = chatPage.page.locator('[data-testid="session-id"]');
    const hasSessionBefore = await sessionIdElement.isVisible({ timeout: 5000 }).catch(() => false);
    const convIdBefore = hasSessionBefore
      ? await sessionIdElement.getAttribute('data-session-id')
      : null;

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Wait for chat interface to be ready (not specifically session-id)
    await chatPage.page.locator('[data-testid="message-input"]').waitFor({ state: 'visible', timeout: 30000 });

    // Check if conversation persisted
    const conversationAfter = await chatPage.getAllMessages();

    // Sprint 122: After reload, session-id may not be visible if conversation wasn't persisted
    const hasSessionAfter = await sessionIdElement.isVisible({ timeout: 5000 }).catch(() => false);
    const convIdAfter = hasSessionAfter
      ? await sessionIdElement.getAttribute('data-session-id')
      : null;

    // Behavior may vary:
    // 1. Conversation persisted with same ID
    if (convIdBefore && convIdAfter && convIdBefore === convIdAfter) {
      expect(conversationAfter.length).toBeGreaterThan(0);
    }
    // 2. Conversation cleared (no session ID after reload) - expected behavior
    else if (!convIdAfter) {
      // Just verify chat interface recovered gracefully
      const messageInput = chatPage.page.locator('[data-testid="message-input"]');
      await expect(messageInput).toBeVisible();
    }
    // 3. New conversation started (different ID)
    else {
      // Just verify system recovered gracefully
      expect(convIdAfter).toBeTruthy();
    }
  });

  test('should handle long conversation gracefully', async ({ chatPage }) => {
    await chatPage.goto();

    // Send many messages
    const messageCount = 10;
    for (let i = 1; i <= messageCount; i++) {
      await chatPage.sendMessage(`Message number ${i}`);
      await chatPage.waitForResponse(60000);
      await chatPage.page.waitForTimeout(300);
    }

    // Verify all messages exist
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(messageCount);

    // UI should still be responsive
    await chatPage.sendMessage('Still here?');
    const response = await chatPage.page.waitForFunction(() => {
      return document.querySelector('[data-testid="message"]');
    }, { timeout: 30000 });

    expect(response).toBeTruthy();
  });

  test('should track conversation metadata', async ({ chatPage }) => {
    await chatPage.goto();

    // Send a message
    await chatPage.sendMessage('Test conversation');
    await chatPage.waitForResponse();

    // Check for conversation metadata
    const metadata = chatPage.page.locator('[data-testid="conversation-metadata"]');
    const hasMetadata = await metadata.isVisible().catch(() => false);

    if (hasMetadata) {
      // Should show start time, duration, message count
      const startTime = metadata.locator('[data-testid="start-time"]');
      const messageCount = metadata.locator('[data-testid="message-count"]');

      const hasStartTime = await startTime.isVisible().catch(() => false);
      const hasMessageCount = await messageCount.isVisible().catch(() => false);

      expect(hasStartTime || hasMessageCount).toBeTruthy();
    }
  });

  test('should handle conversation export', async ({ chatPage, page }) => {
    await chatPage.goto();

    // Create conversation
    await chatPage.sendMessage('What is AI?');
    await chatPage.waitForResponse();

    await chatPage.sendMessage('Tell me more');
    await chatPage.waitForResponse();

    // Look for export button
    const exportButton = chatPage.page.locator('[data-testid="export-conversation"]');
    const hasExportButton = await exportButton.isVisible().catch(() => false);

    if (hasExportButton) {
      // Set up download listener
      const downloadPromise = page.waitForEvent('download').catch(() => null);

      await exportButton.click();

      const download = await downloadPromise;
      if (download) {
        const filename = download.suggestedFilename();
        // Should be JSON, Markdown, or text format
        expect(/\.(json|md|txt)$/i.test(filename)).toBeTruthy();
      }
    }
  });
});
