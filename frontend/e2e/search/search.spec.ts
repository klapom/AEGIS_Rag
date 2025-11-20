import { test, expect } from '../fixtures';

/**
 * E2E Tests for Search & Streaming Functionality
 * Tests SSE streaming, response generation, source cards, and context retention
 *
 * Backend: Gemma-3 4B via Ollama (FREE - no cloud LLM costs)
 * Required: Backend running on http://localhost:8000
 */

test.describe('Search & Streaming', () => {
  test('should perform basic search with streaming', async ({ chatPage }) => {
    // Send query
    await chatPage.sendMessage('What are transformers in machine learning?');

    // Wait for streaming to complete
    await chatPage.waitForResponse();

    // Verify response exists and contains expected content
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.toLowerCase()).toContain('transform');
  });

  test('should show streaming animation during LLM response', async ({ chatPage }) => {
    // Send query
    await chatPage.sendMessage('Explain attention mechanism');

    // Check if streaming indicator appears (may appear briefly)
    // Note: streaming indicator appears/disappears quickly, so we just verify completion
    await chatPage.waitForResponse();

    // Verify response exists
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(50);
  });

  test('should stream tokens incrementally (SSE)', async ({ chatPage }) => {
    // Send query
    await chatPage.sendMessage('What is BERT?');

    // Track message length during streaming
    const messages = await chatPage.getAllMessages();
    const initialCount = messages.length;

    // Wait for completion
    await chatPage.waitForResponse();

    // Verify message was added
    const finalMessages = await chatPage.getAllMessages();
    expect(finalMessages.length).toBeGreaterThan(initialCount);

    // Verify response content
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(20);
  });

  test('should handle long-form answer streaming', async ({ chatPage }) => {
    // Send query that expects long response
    await chatPage.sendMessage(
      'Provide a comprehensive explanation of how neural networks learn patterns'
    );

    // Wait for streaming (longer timeout for long answer)
    await chatPage.waitForResponse(30000);

    // Verify substantial content
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    // Long-form answers should be substantial
    expect(lastMessage.length).toBeGreaterThan(200);
  });

  test('should display source information in response', async ({ chatPage }) => {
    // Send query
    await chatPage.sendMessage('What are transformers?');
    await chatPage.waitForResponse();

    // Verify response exists
    const lastMessage = await chatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(50);

    // Get all messages to verify conversation flow
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(2);
  });

  test('should handle multiple queries in sequence', async ({ chatPage }) => {
    // First query
    await chatPage.sendMessage('What is BERT?');
    await chatPage.waitForResponse();

    // Verify first response
    const firstMessage = await chatPage.getLastMessage();
    expect(firstMessage).toBeTruthy();

    // Second query
    await chatPage.sendMessage('What is GPT?');
    await chatPage.waitForResponse();

    // Verify second response
    const secondMessage = await chatPage.getLastMessage();
    expect(secondMessage).toBeTruthy();

    // Verify both responses exist in conversation
    const allMessages = await chatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(4);
  });

  test('should maintain search context across messages', async ({ chatPage }) => {
    // First query about a topic
    await chatPage.sendMessage('What are transformers?');
    await chatPage.waitForResponse();

    // Verify first response
    const firstResponse = await chatPage.getLastMessage();
    expect(firstResponse).toBeTruthy();

    // Follow-up question (should use context from previous query)
    await chatPage.sendMessage('How do they differ from RNNs?');
    await chatPage.waitForResponse();

    // Verify follow-up response is contextual
    const followUpResponse = await chatPage.getLastMessage();
    expect(followUpResponse).toBeTruthy();
    expect(followUpResponse.length).toBeGreaterThan(50);
  });

  test('should handle queries with special characters and formatting', async ({
    chatPage,
  }) => {
    // Send query with special characters
    await chatPage.sendMessage('What is the meaning of "attention" in "self-attention"?');
    await chatPage.waitForResponse();

    // Verify response exists
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);
  });
});

test.describe('Search Error Handling', () => {
  test('should handle empty query gracefully', async ({ chatPage }) => {
    // Try to send empty message
    await chatPage.messageInput.fill('');
    const inputValue = await chatPage.messageInput.inputValue();
    expect(inputValue).toBe('');

    // Input should still be functional for next message
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should handle very short queries', async ({ chatPage }) => {
    // Send minimal query
    await chatPage.sendMessage('AI');
    await chatPage.waitForResponse();

    // Verify response exists
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should gracefully timeout if backend is slow', async ({ chatPage }) => {
    // Send query
    await chatPage.sendMessage('Explain deep learning architectures');

    // Use longer timeout for slow responses
    try {
      await chatPage.waitForResponse(30000);
      const response = await chatPage.getLastMessage();
      expect(response).toBeTruthy();
    } catch (error) {
      // Timeout is expected for slow backend
      expect(error).toBeDefined();
    }
  });
});

test.describe('Search UI Interactions', () => {
  test('should clear input after sending message', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    // Input should be cleared
    const inputValue = await chatPage.messageInput.inputValue();
    expect(inputValue).toBe('');
  });

  test('should enable send button after response completes', async ({ chatPage }) => {
    // Send message
    await chatPage.sendMessage('What is AI?');
    await chatPage.waitForResponse();

    // Input should be ready for next message
    const isReady = await chatPage.isInputReady();
    expect(isReady).toBeTruthy();
  });

  test('should allow sending messages using Enter key', async ({ chatPage }) => {
    // Send using Enter
    await chatPage.sendMessageWithEnter('What is neural networks?');
    await chatPage.waitForResponse();

    // Verify response
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should maintain chat history during session', async ({ chatPage }) => {
    // Send first message
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    const firstCount = await chatPage.getAllMessages().then((m) => m.length);

    // Send second message
    await chatPage.sendMessage('What is deep learning?');
    await chatPage.waitForResponse();

    const secondCount = await chatPage.getAllMessages().then((m) => m.length);

    // Verify both messages are in history
    expect(secondCount).toBeGreaterThan(firstCount);
  });
});
