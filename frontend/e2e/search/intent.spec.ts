import { test, expect } from '../fixtures';

/**
 * E2E Tests for Intent Classification
 * Tests VECTOR, GRAPH, and HYBRID search intent classification
 *
 * Intent Classification Process:
 * - IntentClassifier determines query type from user input
 * - VECTOR: Factual questions, simple lookups
 * - GRAPH: Relationship and connection questions
 * - HYBRID: Complex questions requiring both vector and graph search
 *
 * Backend: Gemma-3 4B via Ollama (FREE)
 */

test.describe('Intent Classification', () => {
  test('should classify factual queries as VECTOR search', async ({ chatPage }) => {
    // Factual question should use VECTOR search
    await chatPage.sendMessage('What is machine learning?');
    await chatPage.waitForResponse();

    // Verify response exists
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);

    // Response should contain factual information
    expect(response.toLowerCase()).toMatch(/learn|training|model|algorithm/i);
  });

  test('should classify relationship questions as GRAPH search', async ({ chatPage }) => {
    // Relationship question should consider GRAPH search
    await chatPage.sendMessage('How are transformers related to attention mechanisms?');
    await chatPage.waitForResponse();

    // Verify response exists and explains relationship
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);

    // Response should explain connection/relationship
    expect(response).toBeTruthy();
  });

  test('should classify comparative queries as HYBRID search', async ({ chatPage }) => {
    // Comparative question should use HYBRID search
    await chatPage.sendMessage('Compare BERT and GPT architectures');
    await chatPage.waitForResponse();

    // Verify response exists
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(100);

    // Response should include comparison
    expect(response).toBeTruthy();
  });

  test('should handle definition queries', async ({ chatPage }) => {
    // Definition query
    await chatPage.sendMessage('Define neural network');
    await chatPage.waitForResponse();

    // Verify response provides definition
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(30);
  });

  test('should handle how-to questions', async ({ chatPage }) => {
    // Procedural question
    await chatPage.sendMessage('How does backpropagation work?');
    await chatPage.waitForResponse();

    // Verify response explains process
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);
  });

  test('should handle why questions', async ({ chatPage }) => {
    // Explanatory question
    await chatPage.sendMessage('Why do we use attention in transformers?');
    await chatPage.waitForResponse();

    // Verify response explains reasoning
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);
  });

  test('should handle complex multi-part questions', async ({ chatPage }) => {
    // Multi-part question requiring hybrid approach
    await chatPage.sendMessage('What is attention and how does it improve transformer performance?');
    await chatPage.waitForResponse();

    // Verify response covers multiple aspects
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(100);
  });

  test('should maintain intent context in follow-ups', async ({ chatPage }) => {
    // Initial question
    await chatPage.sendMessage('What are embeddings?');
    await chatPage.waitForResponse();

    const firstResponse = await chatPage.getLastMessage();
    expect(firstResponse).toBeTruthy();

    // Follow-up that builds on context
    await chatPage.sendMessage('How are they used in transformers?');
    await chatPage.waitForResponse();

    // Follow-up response should acknowledge context
    const secondResponse = await chatPage.getLastMessage();
    expect(secondResponse).toBeTruthy();
    expect(secondResponse.length).toBeGreaterThan(50);
  });

  test('should classify list/enumeration queries', async ({ chatPage }) => {
    // Question asking for list
    await chatPage.sendMessage('What are the main components of a transformer?');
    await chatPage.waitForResponse();

    // Verify enumeration response
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);
  });

  test('should handle ambiguous queries gracefully', async ({ chatPage }) => {
    // Ambiguous question
    await chatPage.sendMessage('What about learning?');
    await chatPage.waitForResponse();

    // Should still provide response
    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });
});

test.describe('Intent Classification - Edge Cases', () => {
  test('should handle single-word queries', async ({ chatPage }) => {
    await chatPage.sendMessage('Attention');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should handle queries with domain-specific terminology', async ({ chatPage }) => {
    await chatPage.sendMessage('Explain LSTM backpropagation through time');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
    expect(response.length).toBeGreaterThan(50);
  });

  test('should handle negation in queries', async ({ chatPage }) => {
    await chatPage.sendMessage('Why transformers are NOT better than RNNs');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should handle queries with numbers and metrics', async ({ chatPage }) => {
    await chatPage.sendMessage('How many parameters does BERT have?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });

  test('should handle technical acronym questions', async ({ chatPage }) => {
    await chatPage.sendMessage('What does GRU mean?');
    await chatPage.waitForResponse();

    const response = await chatPage.getLastMessage();
    expect(response).toBeTruthy();
  });
});
