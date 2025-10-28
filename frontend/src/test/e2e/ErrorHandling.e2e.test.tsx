/**
 * Error Handling E2E Tests
 * Sprint 15: Comprehensive error handling scenarios
 *
 * Tests cover:
 * - Network errors
 * - HTTP errors (4xx, 5xx)
 * - Timeout errors
 * - API response errors
 * - Invalid data handling
 * - Error recovery
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { StreamingAnswer } from '../../components/chat/StreamingAnswer';
import {
  mockFetchHTTPError,
  mockFetchNetworkError,
  setupGlobalFetchMock,
  cleanupGlobalFetchMock,
  createMockSSEStream,
} from './helpers';
import { mockErrors } from './fixtures';
import type { ChatChunk } from '../../types/chat';

describe('Error Handling E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  describe('Network Errors', () => {
    it('should display error message on network failure', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Fehler beim Laden der Antwort/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should show network error details', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Network request failed/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should show retry button on network error', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          const retryButton = screen.getByText(/Erneut versuchen/i);
          expect(retryButton).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should reload page when retry button clicked', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      // Mock window.location.reload
      const reloadMock = vi.fn();
      Object.defineProperty(window, 'location', {
        value: { reload: reloadMock },
        writable: true,
      });

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Erneut versuchen/i)).toBeInTheDocument();
      });

      const retryButton = screen.getByText(/Erneut versuchen/i);
      fireEvent.click(retryButton);

      expect(reloadMock).toHaveBeenCalled();
    });
  });

  describe('HTTP Errors', () => {
    it('should handle 400 Bad Request', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(400, 'Bad Request: Invalid query'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 400/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 401 Unauthorized', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(401, 'Unauthorized'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 401/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 403 Forbidden', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(403, 'Forbidden'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 403/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 404 Not Found', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(404, 'Endpoint not found'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 404/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 429 Too Many Requests', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(429, 'Rate limit exceeded'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 429/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 500 Internal Server Error', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(500, 'Internal Server Error'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 500/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 502 Bad Gateway', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(502, 'Bad Gateway'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 502/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle 503 Service Unavailable', async () => {
      setupGlobalFetchMock(mockFetchHTTPError(503, 'Service temporarily unavailable'));

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/HTTP 503/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should display custom error message from server', async () => {
      setupGlobalFetchMock(
        mockFetchHTTPError(400, 'Custom error: Query too long')
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Custom error: Query too long/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Streaming Errors', () => {
    it('should handle error chunk during streaming', async () => {
      const chunks: ChatChunk[] = [
        { type: 'metadata', session_id: 'test-123' },
        { type: 'token', content: 'This is ' },
        { type: 'error', error: 'Streaming error occurred', code: 'STREAM_ERROR' },
      ];

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: createMockSSEStream(chunks),
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Streaming error occurred/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle null response body', async () => {
      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: null,
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Response body is null/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle stream read errors', async () => {
      const mockStream = new ReadableStream({
        async start(controller) {
          controller.error(new Error('Stream read failed'));
        },
      });

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: mockStream,
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Fehler beim Laden der Antwort/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle incomplete streams', async () => {
      const encoder = new TextEncoder();
      const mockStream = new ReadableStream({
        async start(controller) {
          controller.enqueue(encoder.encode('data: {"type":"metadata","session_id":"123"}\n\n'));
          controller.enqueue(encoder.encode('data: {"type":"token","content":"Hello"}\n\n'));
          // Abruptly close without [DONE]
          controller.close();
        },
      });

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: mockStream,
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      // Should still display partial content
      await waitFor(
        () => {
          expect(screen.getByText(/Hello/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Invalid Data Handling', () => {
    it('should skip malformed JSON chunks', async () => {
      const encoder = new TextEncoder();
      const mockStream = new ReadableStream({
        async start(controller) {
          controller.enqueue(encoder.encode('data: {"type":"metadata","session_id":"123"}\n\n'));
          controller.enqueue(encoder.encode('data: {invalid json}\n\n'));
          controller.enqueue(encoder.encode('data: {"type":"token","content":"Valid"}\n\n'));
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        },
      });

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: mockStream,
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Valid/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle chunks with missing required fields', async () => {
      const chunks: ChatChunk[] = [
        { type: 'metadata' } as any, // Missing session_id
        { type: 'token' } as any, // Missing content
        { type: 'source' } as any, // Missing source
        { type: 'complete', data: {} },
      ];

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: createMockSSEStream(chunks),
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      // Should not crash, should complete
      await waitFor(
        () => {
          expect(screen.queryByText(/Suche läuft/i)).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle unexpected chunk types', async () => {
      const chunks: any[] = [
        { type: 'metadata', session_id: '123' },
        { type: 'unknown_type', data: 'something' }, // Unknown type
        { type: 'token', content: 'Hello' },
        { type: 'complete', data: {} },
      ];

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: createMockSSEStream(chunks),
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(
        () => {
          expect(screen.getByText(/Hello/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Error Display UI', () => {
    it('should show error icon in error display', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      const { container } = render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        const errorIcon = container.querySelector('svg');
        expect(errorIcon).toBeInTheDocument();
      });
    });

    it('should apply error styling', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      const { container } = render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        const errorContainer = container.querySelector('.bg-red-50');
        expect(errorContainer).toBeInTheDocument();
      });
    });

    it('should show error heading', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Fehler beim Laden der Antwort/i)).toBeInTheDocument();
      });
    });

    it('should show error message in red text', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      const { container } = render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        const errorText = container.querySelector('.text-red-600');
        expect(errorText).toBeInTheDocument();
      });
    });

    it('should style retry button correctly', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      const { container } = render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        const retryButton = container.querySelector('.bg-red-600');
        expect(retryButton).toBeInTheDocument();
      });
    });
  });

  describe('Error Recovery', () => {
    it('should clear error state on successful retry', async () => {
      const mockFetch = vi
        .fn()
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          body: createMockSSEStream([
            { type: 'metadata', session_id: '123' },
            { type: 'token', content: 'Success' },
            { type: 'complete', data: {} },
          ]),
        });

      setupGlobalFetchMock(mockFetch);

      const { rerender } = render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      // Wait for error
      await waitFor(() => {
        expect(screen.getByText(/Network error/i)).toBeInTheDocument();
      });

      // Trigger re-render (simulating retry)
      rerender(
        <MemoryRouter>
          <StreamingAnswer query="test2" mode="hybrid" />
        </MemoryRouter>
      );

      // Should show success content
      await waitFor(
        () => {
          expect(screen.getByText(/Success/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should preserve error state until user retries', async () => {
      setupGlobalFetchMock(mockFetchNetworkError());

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Network request failed/i)).toBeInTheDocument();
      });

      // Error should persist
      expect(screen.getByText(/Network request failed/i)).toBeInTheDocument();
    });
  });

  describe('Console Error Logging', () => {
    it('should log streaming errors to console', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      setupGlobalFetchMock(mockFetchNetworkError());

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalledWith(
          'Streaming error:',
          expect.any(Error)
        );
      });

      consoleErrorSpy.mockRestore();
    });

    it('should log JSON parse errors to console', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const encoder = new TextEncoder();
      const mockStream = new ReadableStream({
        async start(controller) {
          controller.enqueue(encoder.encode('data: {invalid}\n\n'));
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        },
      });

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: mockStream,
        })
      );

      render(
        <MemoryRouter>
          <StreamingAnswer query="test" mode="hybrid" />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      consoleErrorSpy.mockRestore();
    });
  });
});
