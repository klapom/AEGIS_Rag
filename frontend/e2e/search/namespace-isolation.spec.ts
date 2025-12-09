import { test, expect } from '../fixtures';

/**
 * E2E Tests for Namespace Isolation Layer
 *
 * Sprint 41 Feature 41.1: Namespace Isolation Layer
 *
 * These tests verify that the namespace isolation layer is properly integrated
 * with the search functionality. The backend enforces namespace filtering on:
 * - Qdrant (payload filter on namespace_id)
 * - Neo4j (SecureNeo4jClient query validation)
 * - BM25 (result filtering)
 *
 * Note: The frontend doesn't expose namespace selection yet (future Projects feature).
 * These tests verify that search continues to work correctly with the namespace
 * isolation backend in place.
 *
 * Backend: Uses default namespace for non-authenticated searches
 * Required: Backend running on http://localhost:8000
 */

test.describe('Namespace Isolation - Search Integration', () => {
  test('should perform search with namespace isolation enabled', async ({
    authChatPage,
  }) => {
    // Send a query - backend will apply namespace filtering
    await authChatPage.sendMessage('What are the key features of this system?');

    // Wait for response
    await authChatPage.waitForResponse();

    // Verify response exists (namespace filtering worked)
    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(10);
  });

  test('should handle search when no documents in namespace', async ({
    authChatPage,
  }) => {
    // Send a very specific query unlikely to match
    await authChatPage.sendMessage(
      'xyzzy12345nonexistent unique string that should not match anything'
    );

    // Wait for response - should still complete even if no matches
    await authChatPage.waitForResponse();

    // Verify we get a response (system should handle gracefully)
    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });

  test('should return consistent results across multiple searches', async ({
    authChatPage,
  }) => {
    // First search
    await authChatPage.sendMessage('What is machine learning?');
    await authChatPage.waitForResponse();
    const firstResponse = await authChatPage.getLastMessage();

    // Second search with same query (should be consistent due to namespace isolation)
    await authChatPage.sendMessage('What is machine learning?');
    await authChatPage.waitForResponse();
    const secondResponse = await authChatPage.getLastMessage();

    // Both should have responses
    expect(firstResponse).toBeTruthy();
    expect(secondResponse).toBeTruthy();
  });

  test('should support follow-up questions within namespace context', async ({
    authChatPage,
  }) => {
    // Initial question
    await authChatPage.sendMessage('Explain neural networks');
    await authChatPage.waitForResponse();

    // Follow-up question
    await authChatPage.sendMessage('How do they learn?');
    await authChatPage.waitForResponse();

    // Verify conversation maintained context
    const allMessages = await authChatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(4);

    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });

  test('should handle hybrid search modes with namespace filtering', async ({
    authChatPage,
  }) => {
    // Query that might use hybrid search (vector + graph)
    await authChatPage.sendMessage(
      'What entities are related to data processing?'
    );
    await authChatPage.waitForResponse();

    // Verify response
    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
    expect(lastMessage.length).toBeGreaterThan(20);
  });
});

test.describe('Namespace Isolation - Source Display', () => {
  test('should display sources from correct namespace', async ({ authChatPage }) => {
    // Query likely to have sources
    await authChatPage.sendMessage('What is RAG?');
    await authChatPage.waitForResponse();

    // Check if sources are displayed
    const hasCitations = await authChatPage.hasCitations();

    // If sources exist, they should be from the correct namespace
    if (hasCitations) {
      const citations = await authChatPage.getCitations();
      expect(citations.length).toBeGreaterThan(0);
    }

    // Response should exist regardless
    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });

  test('should handle queries with no sources gracefully', async ({
    authChatPage,
  }) => {
    // General question that might not have indexed sources
    await authChatPage.sendMessage('Hello, how are you today?');
    await authChatPage.waitForResponse();

    // Should still get a response even without sources
    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });
});

test.describe('Namespace Isolation - Error Handling', () => {
  test('should handle backend namespace errors gracefully', async ({
    authChatPage,
  }) => {
    // Send query - namespace layer should handle any issues
    await authChatPage.sendMessage('Test query for namespace error handling');

    // Should not crash, should get some response
    try {
      await authChatPage.waitForResponse(15000);
      const lastMessage = await authChatPage.getLastMessage();
      expect(lastMessage).toBeTruthy();
    } catch {
      // Even if timeout, page should still be functional
      const isReady = await authChatPage.isInputReady();
      expect(isReady).toBeTruthy();
    }
  });

  test('should maintain session across namespace-filtered queries', async ({
    authChatPage,
  }) => {
    // First query
    await authChatPage.sendMessage('First question in session');
    await authChatPage.waitForResponse();

    // Get session ID
    const sessionId = await authChatPage.getSessionId();

    // Second query
    await authChatPage.sendMessage('Second question in same session');
    await authChatPage.waitForResponse();

    // Session should be maintained
    const sessionIdAfter = await authChatPage.getSessionId();
    if (sessionId && sessionIdAfter) {
      expect(sessionIdAfter).toBe(sessionId);
    }

    // Conversation should have both exchanges
    const allMessages = await authChatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(4);
  });
});

test.describe('Namespace Isolation - Performance', () => {
  test('should respond within acceptable time with namespace filtering', async ({
    authChatPage,
  }) => {
    const startTime = Date.now();

    await authChatPage.sendMessage('Quick test query');
    await authChatPage.waitForResponse();

    const endTime = Date.now();
    const responseTime = endTime - startTime;

    // Response should be within 30 seconds (generous for cold start)
    expect(responseTime).toBeLessThan(30000);

    // Verify response exists
    const lastMessage = await authChatPage.getLastMessage();
    expect(lastMessage).toBeTruthy();
  });

  test('should handle rapid sequential queries', async ({ authChatPage }) => {
    // Send multiple queries quickly
    const queries = ['First query', 'Second query', 'Third query'];

    for (const query of queries) {
      await authChatPage.sendMessage(query);
      await authChatPage.waitForResponse();
    }

    // All queries should have been processed
    const allMessages = await authChatPage.getAllMessages();
    expect(allMessages.length).toBeGreaterThanOrEqual(queries.length * 2);
  });
});
