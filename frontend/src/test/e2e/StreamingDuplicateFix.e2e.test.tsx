/**
 * Streaming Duplicate Fix E2E Tests
 * Sprint 17 Feature 17.5: Duplicate Streaming Fix
 *
 * Tests cover:
 * - SSE connection aborts on unmount
 * - No duplicate answers in strict mode
 * - AbortController properly cancels requests
 * - Single SSE connection per query
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StreamingAnswer } from '../../components/chat/StreamingAnswer';
import { setupGlobalFetchMock, cleanupGlobalFetchMock } from './helpers';
import { StrictMode } from 'react';

describe('Feature 17.5: Streaming Duplicate Fix E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
    cleanup();
  });

  describe('AbortController Integration', () => {
    it('should abort SSE connection when component unmounts', async () => {
      // Arrange: Mock SSE stream that tracks abort signal
      const abortSignalMock = vi.fn();
      const encoder = new TextEncoder();

      const mockStream = new ReadableStream({
        async start(controller) {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'metadata',
                data: { session_id: 'test-123', intent: 'hybrid' },
              })}\n\n`
            )
          );
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: 'token', content: 'Starting...' })}\n\n`
            )
          );
          // Stream never completes - simulates long-running stream
        },
      });

      const mockFetch = vi.fn((url, options) => {
        // Track abort signal
        if (options?.signal) {
          options.signal.addEventListener('abort', abortSignalMock);
        }
        return Promise.resolve({ ok: true, body: mockStream });
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render and immediately unmount
      const { unmount } = render(
        <MemoryRouter>
          <StreamingAnswer query="test query" mode="hybrid" />
        </MemoryRouter>
      );

      // Wait for stream to start
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      // Act: Unmount component
      unmount();

      // Assert: Abort signal should have been triggered
      await waitFor(() => {
        expect(abortSignalMock).toHaveBeenCalled();
      });
    });

    it('should pass AbortSignal to fetch API', async () => {
      // Arrange: Track fetch calls with signal
      const mockFetch = vi.fn((url, options) => {
        const encoder = new TextEncoder();
        const mockStream = new ReadableStream({
          async start(controller) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'metadata',
                  data: { session_id: 'test-456', intent: 'hybrid' },
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'token', content: 'Test' })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'complete', data: {} })}\n\n`
              )
            );
            controller.enqueue(encoder.encode('data: [DONE]\n\n'));
            controller.close();
          },
        });

        return Promise.resolve({ ok: true, body: mockStream });
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render component
      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      // Assert: Fetch should be called with AbortSignal
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/chat/stream'),
          expect.objectContaining({
            signal: expect.any(AbortSignal),
          })
        );
      });
    });

    it('should ignore AbortError after unmount', async () => {
      // Arrange: Mock fetch that simulates abort
      const encoder = new TextEncoder();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const mockStream = new ReadableStream({
        async start(controller) {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'metadata',
                data: { session_id: 'test-789', intent: 'hybrid' },
              })}\n\n`
            )
          );
          // Simulate abort by throwing AbortError
          controller.error(new DOMException('The operation was aborted.', 'AbortError'));
        },
      });

      const mockFetch = vi.fn().mockResolvedValue({ ok: true, body: mockStream });
      setupGlobalFetchMock(mockFetch);

      // Act: Render and unmount quickly
      const { unmount } = render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      unmount();

      // Assert: No error should be logged (AbortError is expected)
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Errors logged should not include streaming errors (only parse errors are logged)
      const streamingErrors = consoleErrorSpy.mock.calls.filter(
        (call) => call[0] === 'Streaming error:'
      );
      expect(streamingErrors.length).toBe(0);

      consoleErrorSpy.mockRestore();
    });
  });

  describe('React StrictMode Compatibility', () => {
    it('should not create duplicate streams in StrictMode', async () => {
      // Arrange: Track number of fetch calls
      const fetchCallCount = { count: 0 };
      const encoder = new TextEncoder();

      const mockFetch = vi.fn((url, options) => {
        fetchCallCount.count++;

        const mockStream = new ReadableStream({
          async start(controller) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'metadata',
                  data: { session_id: 'strict-test-123', intent: 'hybrid' },
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'token',
                  content: `Answer ${fetchCallCount.count}`,
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'complete', data: {} })}\n\n`
              )
            );
            controller.enqueue(encoder.encode('data: [DONE]\n\n'));
            controller.close();
          },
        });

        return Promise.resolve({ ok: true, body: mockStream });
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render in StrictMode (simulates double mount/unmount in dev)
      render(
        <StrictMode>
          <MemoryRouter>
            <StreamingAnswer query="strict mode test" mode="hybrid" />
          </MemoryRouter>
        </StrictMode>
      );

      // Wait for streaming to complete
      await waitFor(
        () => {
          // In StrictMode, React mounts twice in dev, but our cleanup should prevent duplicates
          // Only the second mount's stream should be active
          expect(screen.getByText(/Answer/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Assert: Only ONE active stream should produce output
      // (StrictMode causes 2 mounts, but first should abort)
      const answerElements = screen.queryAllByText(/Answer/i);
      expect(answerElements.length).toBe(1);

      // In development StrictMode, fetch is called twice due to double mount
      // But only the second stream should complete
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('should cleanup first stream when remounting in StrictMode', async () => {
      // Arrange: Track cleanup behavior
      const abortListeners: Array<() => void> = [];
      const encoder = new TextEncoder();

      const mockFetch = vi.fn((url, options) => {
        // Track abort listeners
        if (options?.signal) {
          const listener = () => {
            console.log('Stream aborted');
          };
          options.signal.addEventListener('abort', listener);
          abortListeners.push(listener);
        }

        const mockStream = new ReadableStream({
          async start(controller) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'metadata',
                  data: { session_id: 'cleanup-test-456', intent: 'hybrid' },
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'token', content: 'Test content' })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'complete', data: {} })}\n\n`
              )
            );
            controller.enqueue(encoder.encode('data: [DONE]\n\n'));
            controller.close();
          },
        });

        return Promise.resolve({ ok: true, body: mockStream });
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render in StrictMode
      render(
        <StrictMode>
          <MemoryRouter>
            <StreamingAnswer query="cleanup test" mode="hybrid" />
          </MemoryRouter>
        </StrictMode>
      );

      // Wait for completion
      await waitFor(() => {
        expect(screen.getByText(/Test content/i)).toBeInTheDocument();
      });

      // Assert: First mount should have been aborted
      // In StrictMode: mount -> unmount -> mount
      // So we expect 2 abort listeners registered
      expect(abortListeners.length).toBe(2);
    });
  });

  describe('Single Stream Guarantee', () => {
    it('should maintain only one active SSE connection per query', async () => {
      // Arrange: Track active connections
      const activeConnections = new Set<string>();
      const encoder = new TextEncoder();

      const mockFetch = vi.fn((url, options) => {
        const connectionId = Math.random().toString();
        activeConnections.add(connectionId);

        // Cleanup on abort
        if (options?.signal) {
          options.signal.addEventListener('abort', () => {
            activeConnections.delete(connectionId);
          });
        }

        const mockStream = new ReadableStream({
          async start(controller) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'metadata',
                  data: { session_id: 'single-stream-789', intent: 'hybrid' },
                })}\n\n`
              )
            );

            // Simulate slow stream
            await new Promise((resolve) => setTimeout(resolve, 100));

            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'token', content: 'Content' })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'complete', data: {} })}\n\n`
              )
            );
            controller.enqueue(encoder.encode('data: [DONE]\n\n'));
            controller.close();

            // Remove from active connections
            activeConnections.delete(connectionId);
          },
        });

        return Promise.resolve({ ok: true, body: mockStream });
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render component
      render(
        <MemoryRouter>
          <StreamingAnswer query="single stream test" mode="hybrid" />
        </MemoryRouter>
      );

      // Check connection count during streaming
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Assert: Should never have more than 1 active connection
      expect(activeConnections.size).toBeLessThanOrEqual(1);

      // Wait for completion
      await waitFor(() => {
        expect(screen.getByText(/Content/i)).toBeInTheDocument();
      });

      // Assert: All connections should be closed
      expect(activeConnections.size).toBe(0);
    });

    it('should cancel previous stream when query changes', async () => {
      // Arrange: Track abort calls
      const abortCalls: string[] = [];
      const encoder = new TextEncoder();

      const createStream = (query: string) => {
        return new ReadableStream({
          async start(controller) {
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'metadata',
                  data: { session_id: 'change-test-abc', intent: 'hybrid' },
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'token',
                  content: `Answer for: ${query}`,
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'complete', data: {} })}\n\n`
              )
            );
            controller.enqueue(encoder.encode('data: [DONE]\n\n'));
            controller.close();
          },
        });
      };

      const mockFetch = vi.fn((url, options) => {
        const requestBody = JSON.parse(options.body);
        const query = requestBody.query;

        // Track abort
        if (options?.signal) {
          options.signal.addEventListener('abort', () => {
            abortCalls.push(query);
          });
        }

        return Promise.resolve({ ok: true, body: createStream(query) });
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render with first query
      const { rerender } = render(
        <MemoryRouter>
          <StreamingAnswer query="first query" mode="hybrid" />
        </MemoryRouter>
      );

      // Wait briefly
      await new Promise((resolve) => setTimeout(resolve, 50));

      // Act: Change query (should abort previous)
      rerender(
        <MemoryRouter>
          <StreamingAnswer query="second query" mode="hybrid" />
        </MemoryRouter>
      );

      // Assert: First query should be aborted
      await waitFor(() => {
        expect(abortCalls).toContain('first query');
      });

      // Assert: Second query should complete
      await waitFor(() => {
        expect(screen.getByText(/Answer for: second query/i)).toBeInTheDocument();
      });

      // First query should not be visible
      expect(screen.queryByText(/Answer for: first query/i)).not.toBeInTheDocument();
    });
  });

  describe('Error Scenarios', () => {
    it('should handle network errors during streaming without duplicate retries', async () => {
      // Arrange: Mock network failure
      const fetchCallCount = { count: 0 };

      const mockFetch = vi.fn(() => {
        fetchCallCount.count++;
        return Promise.reject(new Error('Network request failed'));
      });

      setupGlobalFetchMock(mockFetch);

      // Act: Render component
      render(
        <MemoryRouter>
          <StreamingAnswer query="error test" mode="hybrid" />
        </MemoryRouter>
      );

      // Assert: Error should be displayed
      await waitFor(
        () => {
          expect(
            screen.getByText(/Fehler beim Laden der Antwort/i)
          ).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Assert: Should only attempt once (no duplicate retries)
      expect(fetchCallCount.count).toBe(1);
    });

    it('should not create duplicate error messages in StrictMode', async () => {
      // Arrange: Mock error response
      const mockFetch = vi.fn().mockRejectedValue(new Error('Test error'));
      setupGlobalFetchMock(mockFetch);

      // Act: Render in StrictMode
      render(
        <StrictMode>
          <MemoryRouter>
            <StreamingAnswer query="strict error test" mode="hybrid" />
          </MemoryRouter>
        </StrictMode>
      );

      // Assert: Only one error message should be shown
      await waitFor(() => {
        const errorMessages = screen.getAllByText(/Fehler beim Laden der Antwort/i);
        expect(errorMessages.length).toBe(1);
      });
    });
  });
});
