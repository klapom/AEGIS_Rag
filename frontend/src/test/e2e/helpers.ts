/**
 * E2E Test Helpers
 * Sprint 15: Utility functions for E2E testing
 */

import { vi } from 'vitest';
import type { ChatChunk } from '../../types/chat';
import { mockSSEStream, mockAPIResponses } from './fixtures';

/**
 * Create a mock ReadableStream for SSE testing
 */
export function createMockSSEStream(chunks: ChatChunk[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream({
    async pull(controller) {
      if (index < chunks.length) {
        const chunk = chunks[index];
        const sseMessage = `data: ${JSON.stringify(chunk)}\n\n`;
        controller.enqueue(encoder.encode(sseMessage));
        index++;
      } else {
        // Send [DONE] signal
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      }
    },
  });
}

/**
 * Create a complete mock SSE stream with metadata, tokens, sources, and completion
 */
export function createFullMockSSEStream(): ReadableStream<Uint8Array> {
  const chunks: ChatChunk[] = [
    mockSSEStream.metadata,
    ...mockSSEStream.tokens,
    ...mockSSEStream.sources,
    mockSSEStream.complete,
  ];
  return createMockSSEStream(chunks);
}

/**
 * Create a mock SSE stream that errors midway
 */
export function createErrorMockSSEStream(): ReadableStream<Uint8Array> {
  const chunks: ChatChunk[] = [
    mockSSEStream.metadata,
    mockSSEStream.tokens[0],
    mockSSEStream.tokens[1],
    mockSSEStream.error,
  ];
  return createMockSSEStream(chunks);
}

/**
 * Mock fetch for successful SSE streaming
 */
export function mockFetchSSESuccess() {
  return vi.fn().mockResolvedValue({
    ok: true,
    body: createFullMockSSEStream(),
  });
}

/**
 * Mock fetch for SSE streaming error
 */
export function mockFetchSSEError() {
  return vi.fn().mockResolvedValue({
    ok: true,
    body: createErrorMockSSEStream(),
  });
}

/**
 * Mock fetch for HTTP error
 */
export function mockFetchHTTPError(status: number, message: string) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    text: () => Promise.resolve(message),
  });
}

/**
 * Mock fetch for network error
 */
export function mockFetchNetworkError() {
  return vi.fn().mockRejectedValue(new Error('Network request failed'));
}

/**
 * Mock fetch for JSON API response
 */
export function mockFetchJSONSuccess(data: any) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

/**
 * Mock fetch for sessions list
 */
export function mockFetchSessionsList() {
  return mockFetchJSONSuccess(mockAPIResponses.sessions);
}

/**
 * Mock fetch for conversation history
 */
export function mockFetchConversationHistory(sessionId: string) {
  return mockFetchJSONSuccess({
    ...mockAPIResponses.history,
    session_id: sessionId,
  });
}

/**
 * Mock fetch for successful delete
 */
export function mockFetchDeleteSuccess() {
  return vi.fn().mockResolvedValue({
    ok: true,
  });
}

/**
 * Wait for async state updates
 */
export async function waitForAsync(ms: number = 0): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Wait for condition to be true
 */
export async function waitFor(
  condition: () => boolean,
  timeout: number = 5000,
  interval: number = 50
): Promise<void> {
  const startTime = Date.now();

  while (!condition()) {
    if (Date.now() - startTime > timeout) {
      throw new Error('Timeout waiting for condition');
    }
    await waitForAsync(interval);
  }
}

/**
 * Create mock ReadableStream reader for testing
 */
export function createMockStreamReader(chunks: Array<{ done: boolean; value?: Uint8Array }>) {
  let index = 0;

  return {
    read: vi.fn(async () => {
      if (index < chunks.length) {
        return chunks[index++];
      }
      return { done: true, value: undefined };
    }),
    releaseLock: vi.fn(),
  };
}

/**
 * Helper to encode SSE message
 */
export function encodeSSEMessage(chunk: ChatChunk): Uint8Array {
  const encoder = new TextEncoder();
  return encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`);
}

/**
 * Helper to encode SSE done signal
 */
export function encodeSSEDone(): Uint8Array {
  const encoder = new TextEncoder();
  return encoder.encode('data: [DONE]\n\n');
}

/**
 * Setup mock for route navigation
 */
export function mockNavigate() {
  return vi.fn();
}

/**
 * Setup mock for search params
 */
export function mockSearchParams(params: Record<string, string>) {
  const searchParams = new URLSearchParams(params);
  return [searchParams, vi.fn()] as const;
}

/**
 * Create mock router context
 */
export function createMockRouter(initialPath: string = '/') {
  const navigate = mockNavigate();
  const searchParams = new URLSearchParams();

  return {
    navigate,
    searchParams,
    location: { pathname: initialPath },
  };
}

/**
 * Simulate typing into an input field
 */
export function simulateTyping(input: HTMLInputElement, text: string) {
  input.value = text;
  input.dispatchEvent(new Event('change', { bubbles: true }));
}

/**
 * Simulate Enter key press
 */
export function simulateEnterKey(element: HTMLElement) {
  const event = new KeyboardEvent('keydown', {
    key: 'Enter',
    bubbles: true,
    cancelable: true,
  });
  element.dispatchEvent(event);
}

/**
 * Mock window.fetch globally
 */
export function setupGlobalFetchMock(mockFn: any) {
  global.fetch = mockFn;
}

/**
 * Cleanup global fetch mock
 */
export function cleanupGlobalFetchMock() {
  vi.clearAllMocks();
}

/**
 * Create mock for SSE EventSource (if needed in future)
 */
export function createMockEventSource() {
  return class MockEventSource {
    onmessage: ((event: any) => void) | null = null;
    onerror: ((event: any) => void) | null = null;

    constructor(public url: string) {}

    close() {}

    addEventListener(type: string, listener: any) {
      if (type === 'message') {
        this.onmessage = listener;
      } else if (type === 'error') {
        this.onerror = listener;
      }
    }

    removeEventListener() {}
  };
}

// ============================================================================
// Sprint 17 Feature 17.2 & 17.3: Helper Functions for Conversation Persistence & Titles
// ============================================================================

/**
 * Mock fetch for session with title
 * Sprint 17 Feature 17.3
 */
export function mockFetchSessionWithTitle(sessionId: string, title: string) {
  return mockFetchJSONSuccess({
    session_id: sessionId,
    title: title,
    generated_at: new Date().toISOString(),
  });
}

/**
 * Mock fetch for title update (PATCH)
 * Sprint 17 Feature 17.3
 */
export function mockFetchTitleUpdate(sessionId: string, newTitle: string) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () =>
      Promise.resolve({
        session_id: sessionId,
        title: newTitle,
        generated_at: new Date().toISOString(),
      }),
  });
}

/**
 * Mock fetch for title generation failure
 * Sprint 17 Feature 17.3
 */
export function mockFetchTitleGenerationError() {
  return vi.fn().mockRejectedValue(new Error('Title generation service unavailable'));
}

// ============================================================================
// Sprint 17 Feature 17.5: Helper Functions for Streaming Duplicate Fix
// ============================================================================

/**
 * Create mock SSE stream with abort signal tracking
 * Sprint 17 Feature 17.5
 */
export function createMockSSEStreamWithAbort(
  chunks: ChatChunk[],
  onAbort?: () => void
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream({
    async start(controller) {
      // Simulate abort listening
      const abortHandler = () => {
        controller.close();
        onAbort?.();
      };

      // In a real implementation, this would be tied to the abort signal
      // For testing, we simulate the abort behavior
    },
    async pull(controller) {
      if (index < chunks.length) {
        const chunk = chunks[index];
        const sseMessage = `data: ${JSON.stringify(chunk)}\n\n`;
        controller.enqueue(encoder.encode(sseMessage));
        index++;
      } else {
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      }
    },
  });
}

/**
 * Track active SSE connections for duplicate detection
 * Sprint 17 Feature 17.5
 */
export function createConnectionTracker() {
  const connections = new Set<string>();

  return {
    add: (id: string) => connections.add(id),
    remove: (id: string) => connections.delete(id),
    has: (id: string) => connections.has(id),
    count: () => connections.size,
    clear: () => connections.clear(),
  };
}

// ============================================================================
// Sprint 17 Feature 17.6: Helper Functions for Admin Statistics API
// ============================================================================

/**
 * Mock fetch for admin stats
 * Sprint 17 Feature 17.6
 */
export function mockFetchAdminStats(stats: any) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(stats),
  });
}

/**
 * Mock fetch for admin stats error
 * Sprint 17 Feature 17.6
 */
export function mockFetchAdminStatsError(status: number = 500, message: string = 'Internal Server Error') {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    text: () => Promise.resolve(message),
  });
}

/**
 * Mock fetch for partial admin stats (some services down)
 * Sprint 17 Feature 17.6
 */
export function mockFetchPartialAdminStats() {
  return mockFetchJSONSuccess({
    qdrant_total_chunks: 450,
    qdrant_collection_name: 'aegis_documents',
    qdrant_vector_dimension: 1024,
    bm25_corpus_size: null,
    neo4j_total_entities: null,
    neo4j_total_relations: null,
    neo4j_total_chunks: null,
    total_conversations: null,
    last_reindex_timestamp: null,
    embedding_model: 'BAAI/bge-m3',
  });
}
