/**
 * useStreamChat Hook Tests
 * Sprint 48 Feature 48.6: Phase event handling tests
 * Sprint 48 Feature 48.10: Request timeout and cancel tests
 *
 * Tests for the enhanced useStreamChat hook with phase event tracking
 * and timeout/cancel functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useStreamChat, TIMEOUT_CONFIG } from './useStreamChat';
import * as chatApi from '../api/chat';

// Mock the chat API
vi.mock('../api/chat', () => ({
  streamChat: vi.fn(),
}));

describe('useStreamChat - Sprint 48', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('TIMEOUT_CONFIG', () => {
    it('exports correct warning threshold', () => {
      expect(TIMEOUT_CONFIG.WARNING_THRESHOLD_MS).toBe(30000);
    });

    it('exports correct timeout value', () => {
      expect(TIMEOUT_CONFIG.TIMEOUT_MS).toBe(90000);
    });
  });

  describe('Initial state', () => {
    it('initializes with null currentPhase', () => {
      const { result } = renderHook(() =>
        useStreamChat({ query: null, mode: 'hybrid' })
      );
      expect(result.current.currentPhase).toBeNull();
    });

    it('initializes with empty phaseEvents array', () => {
      const { result } = renderHook(() =>
        useStreamChat({ query: null, mode: 'hybrid' })
      );
      expect(result.current.phaseEvents).toEqual([]);
    });

    it('initializes with showTimeoutWarning as false', () => {
      const { result } = renderHook(() =>
        useStreamChat({ query: null, mode: 'hybrid' })
      );
      expect(result.current.showTimeoutWarning).toBe(false);
    });

    it('provides cancelRequest function', () => {
      const { result } = renderHook(() =>
        useStreamChat({ query: null, mode: 'hybrid' })
      );
      expect(typeof result.current.cancelRequest).toBe('function');
    });

    // Sprint 51 Feature 51.1: totalPhases initial state
    it('initializes with undefined totalPhases', () => {
      const { result } = renderHook(() =>
        useStreamChat({ query: null, mode: 'hybrid' })
      );
      expect(result.current.totalPhases).toBeUndefined();
    });

    // Sprint 51 Feature 51.2: isGeneratingAnswer initial state
    it('initializes with isGeneratingAnswer as false', () => {
      const { result } = renderHook(() =>
        useStreamChat({ query: null, mode: 'hybrid' })
      );
      expect(result.current.isGeneratingAnswer).toBe(false);
    });
  });

  describe('Phase event handling', () => {
    it('updates currentPhase when in_progress event received', async () => {
      const mockStream = (async function* () {
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'in_progress',
              start_time: new Date().toISOString(),
            },
          },
        };
        // Keep stream open briefly
        await new Promise((resolve) => setTimeout(resolve, 100));
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.currentPhase).toBe('vector_search');
    });

    it('clears currentPhase when completed event received', async () => {
      const mockStream = (async function* () {
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'in_progress',
              start_time: new Date().toISOString(),
            },
          },
        };
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'completed',
              start_time: new Date().toISOString(),
              end_time: new Date().toISOString(),
              duration_ms: 100,
            },
          },
        };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.currentPhase).toBeNull();
    });

    it('accumulates phase events in phaseEvents array', async () => {
      const mockStream = (async function* () {
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'intent_classification',
              status: 'completed',
              start_time: new Date().toISOString(),
              duration_ms: 50,
            },
          },
        };
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'in_progress',
              start_time: new Date().toISOString(),
            },
          },
        };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.phaseEvents).toHaveLength(2);
      expect(result.current.phaseEvents[0].phase_type).toBe('intent_classification');
      expect(result.current.phaseEvents[1].phase_type).toBe('vector_search');
    });

    it('updates existing phase event rather than duplicating', async () => {
      const mockStream = (async function* () {
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'in_progress',
              start_time: new Date().toISOString(),
            },
          },
        };
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'completed',
              start_time: new Date().toISOString(),
              end_time: new Date().toISOString(),
              duration_ms: 200,
            },
          },
        };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.phaseEvents).toHaveLength(1);
      expect(result.current.phaseEvents[0].status).toBe('completed');
    });
  });

  describe('Timeout warning', () => {
    it('shows timeout warning after WARNING_THRESHOLD_MS', async () => {
      const mockStream = (async function* () {
        // Simulate a long-running stream
        await new Promise((resolve) => setTimeout(resolve, 60000));
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      // Initially false
      expect(result.current.showTimeoutWarning).toBe(false);

      // Advance past warning threshold
      await act(async () => {
        await vi.advanceTimersByTimeAsync(TIMEOUT_CONFIG.WARNING_THRESHOLD_MS + 100);
      });

      expect(result.current.showTimeoutWarning).toBe(true);
    });

    it('clears timeout warning on stream completion', async () => {
      const mockStream = (async function* () {
        await new Promise((resolve) => setTimeout(resolve, 35000));
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      // Advance past warning threshold
      await act(async () => {
        await vi.advanceTimersByTimeAsync(TIMEOUT_CONFIG.WARNING_THRESHOLD_MS + 100);
      });

      expect(result.current.showTimeoutWarning).toBe(true);

      // Let stream complete
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10000);
      });

      expect(result.current.showTimeoutWarning).toBe(false);
    });
  });

  describe('Cancel request', () => {
    it('cancelRequest aborts the stream', async () => {
      const mockStream = (async function* () {
        await new Promise((resolve) => setTimeout(resolve, 60000));
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      // Wait for streaming to start
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(result.current.isStreaming).toBe(true);

      // Cancel the request
      act(() => {
        result.current.cancelRequest();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.showTimeoutWarning).toBe(false);
    });

    it('cancelRequest clears currentPhase', async () => {
      const mockStream = (async function* () {
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'in_progress',
              start_time: new Date().toISOString(),
            },
          },
        };
        await new Promise((resolve) => setTimeout(resolve, 60000));
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.currentPhase).toBe('vector_search');

      act(() => {
        result.current.cancelRequest();
      });

      expect(result.current.currentPhase).toBeNull();
    });
  });

  describe('Auto-timeout', () => {
    it('automatically cancels request after TIMEOUT_MS', async () => {
      const mockStream = (async function* () {
        // This stream never completes
        await new Promise((resolve) => setTimeout(resolve, 120000));
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      // Wait for streaming to start
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(result.current.isStreaming).toBe(true);

      // Advance past timeout
      await act(async () => {
        await vi.advanceTimersByTimeAsync(TIMEOUT_CONFIG.TIMEOUT_MS);
      });

      // Should have set error and stopped streaming
      expect(result.current.error).toBeTruthy();
    });

    it('sets appropriate error message on timeout', async () => {
      const mockStream = (async function* () {
        await new Promise((resolve) => setTimeout(resolve, 120000));
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(TIMEOUT_CONFIG.TIMEOUT_MS + 100);
      });

      expect(result.current.error).toContain('Timeout');
    });
  });

  describe('State reset on new query', () => {
    it('resets phase state on new query', async () => {
      const mockStream1 = (async function* () {
        yield {
          type: 'metadata',
          data: {
            phase_event: {
              phase_type: 'vector_search',
              status: 'completed',
              start_time: new Date().toISOString(),
              duration_ms: 100,
            },
          },
        };
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream1);

      const { result, rerender } = renderHook(
        ({ query }) => useStreamChat({ query, mode: 'hybrid' }),
        { initialProps: { query: 'first query' } }
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.phaseEvents).toHaveLength(1);

      // New query should reset state
      const mockStream2 = (async function* () {
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream2);

      rerender({ query: 'second query' });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.phaseEvents).toHaveLength(0);
    });
  });

  // Sprint 51 Feature 51.1: Dynamic total phases from backend
  describe('Total phases from backend', () => {
    it('extracts totalPhases from metadata', async () => {
      const mockStream = (async function* () {
        yield {
          type: 'metadata',
          data: {
            total_phases: 7,
          },
        };
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.totalPhases).toBe(7);
    });

    it('resets totalPhases on new query', async () => {
      const mockStream1 = (async function* () {
        yield {
          type: 'metadata',
          data: { total_phases: 5 },
        };
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream1);

      const { result, rerender } = renderHook(
        ({ query }) => useStreamChat({ query, mode: 'hybrid' }),
        { initialProps: { query: 'first query' } }
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.totalPhases).toBe(5);

      // New query should reset totalPhases
      const mockStream2 = (async function* () {
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream2);

      rerender({ query: 'second query' });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.totalPhases).toBeUndefined();
    });
  });

  // Sprint 51 Feature 51.2: Token generation state for streaming cursor
  describe('Token generation state', () => {
    it('sets isGeneratingAnswer to true when receiving tokens', async () => {
      const mockStream = (async function* () {
        yield { type: 'token', content: 'Hello' };
        await new Promise((resolve) => setTimeout(resolve, 100));
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.isGeneratingAnswer).toBe(true);
    });

    it('sets isGeneratingAnswer to false on complete', async () => {
      const mockStream = (async function* () {
        yield { type: 'token', content: 'Hello' };
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.isGeneratingAnswer).toBe(false);
    });

    it('sets isGeneratingAnswer to false on error', async () => {
      const mockStream = (async function* () {
        yield { type: 'token', content: 'Hello' };
        yield { type: 'error', error: 'Test error' };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.isGeneratingAnswer).toBe(false);
    });

    it('accumulates tokens in answer', async () => {
      const mockStream = (async function* () {
        yield { type: 'token', content: 'Hello' };
        yield { type: 'token', content: ' World' };
        yield { type: 'complete', data: {} };
      })();

      vi.mocked(chatApi.streamChat).mockReturnValue(mockStream);

      const { result } = renderHook(() =>
        useStreamChat({ query: 'test query', mode: 'hybrid' })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.answer).toBe('Hello World');
    });
  });
});
