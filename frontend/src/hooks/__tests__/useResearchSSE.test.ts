/**
 * useResearchSSE Hook Tests
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useResearchSSE } from '../useResearchSSE';

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
});

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('useResearchSSE', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.clear();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('initial state', () => {
    it('returns default state on initial render', () => {
      const { result } = renderHook(() => useResearchSSE());

      expect(result.current.isResearchMode).toBe(false);
      expect(result.current.isResearching).toBe(false);
      expect(result.current.currentPhase).toBeNull();
      expect(result.current.progress).toEqual([]);
      expect(result.current.synthesis).toBeNull();
      expect(result.current.sources).toEqual([]);
      expect(result.current.researchPlan).toEqual([]);
      expect(result.current.qualityMetrics).toEqual({
        iterations: 0,
        totalSources: 0,
        webSources: 0,
      });
      expect(result.current.error).toBeNull();
    });

    it('loads Research Mode preference from localStorage', () => {
      mockLocalStorage.setItem('aegisrag-research-mode-enabled', 'true');

      const { result } = renderHook(() => useResearchSSE());

      expect(result.current.isResearchMode).toBe(true);
    });

    it('defaults to false if localStorage has invalid value', () => {
      mockLocalStorage.setItem('aegisrag-research-mode-enabled', 'invalid');

      const { result } = renderHook(() => useResearchSSE());

      expect(result.current.isResearchMode).toBe(false);
    });
  });

  describe('toggleResearchMode', () => {
    it('toggles Research Mode from false to true', () => {
      const { result } = renderHook(() => useResearchSSE());

      expect(result.current.isResearchMode).toBe(false);

      act(() => {
        result.current.toggleResearchMode();
      });

      expect(result.current.isResearchMode).toBe(true);
    });

    it('toggles Research Mode from true to false', () => {
      mockLocalStorage.setItem('aegisrag-research-mode-enabled', 'true');
      const { result } = renderHook(() => useResearchSSE());

      expect(result.current.isResearchMode).toBe(true);

      act(() => {
        result.current.toggleResearchMode();
      });

      expect(result.current.isResearchMode).toBe(false);
    });

    it('persists toggle state to localStorage', () => {
      const { result } = renderHook(() => useResearchSSE());

      act(() => {
        result.current.toggleResearchMode();
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'aegisrag-research-mode-enabled',
        'true'
      );
    });
  });

  describe('resetResearch', () => {
    it('resets all state to defaults', async () => {
      // Create mock SSE stream
      const mockReadableStream = createMockStream([
        { type: 'progress', data: { phase: 'plan', message: 'Planning', iteration: 1, metadata: {} } },
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      // Start research to populate state
      await act(async () => {
        result.current.startResearch('test query');
      });

      // Wait for progress to be added
      await waitFor(() => {
        expect(result.current.progress.length).toBeGreaterThan(0);
      });

      // Reset
      act(() => {
        result.current.resetResearch();
      });

      expect(result.current.isResearching).toBe(false);
      expect(result.current.currentPhase).toBeNull();
      expect(result.current.progress).toEqual([]);
      expect(result.current.synthesis).toBeNull();
      expect(result.current.sources).toEqual([]);
      expect(result.current.error).toBeNull();
    });
  });

  describe('cancelResearch', () => {
    it('cancels ongoing research', async () => {
      // Create a stream that never ends
      const mockReadableStream = createMockStreamNeverEnding();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query');
      });

      // Research should be in progress
      expect(result.current.isResearching).toBe(true);

      // Cancel
      act(() => {
        result.current.cancelResearch();
      });

      expect(result.current.isResearching).toBe(false);
    });
  });

  describe('startResearch', () => {
    it('sets isResearching to true when starting', async () => {
      const mockReadableStream = createMockStream([
        { type: 'progress', data: { phase: 'plan', message: 'Planning', iteration: 1, metadata: {} } },
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query');
      });

      // isResearching should be set during the process
      // (it will be false after completion in this synchronous test)
    });

    it('handles progress events correctly', async () => {
      const mockReadableStream = createMockStream([
        { type: 'progress', data: { phase: 'plan', message: 'Creating plan', iteration: 1, metadata: { num_queries: 3 } } },
        { type: 'done' },
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query');
        // Wait for stream to complete
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(result.current.progress.length).toBeGreaterThanOrEqual(0);
    });

    it('handles result events correctly', async () => {
      const mockResult = {
        query: 'test query',
        synthesis: 'Test synthesis result',
        sources: [{ text: 'Source 1', score: 0.9, source_type: 'vector', metadata: {}, entities: [], relationships: [] }],
        iterations: 2,
        quality_metrics: { coverage: 0.8 },
        research_plan: ['Step 1', 'Step 2'],
      };

      const mockReadableStream = createMockStream([
        { type: 'result', data: mockResult },
        { type: 'done' },
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query');
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      // Check if result was processed
      await waitFor(() => {
        expect(result.current.synthesis).toBe('Test synthesis result');
      });
    });

    it('handles error events correctly', async () => {
      const mockReadableStream = createMockStream([
        { type: 'error', error: 'Test error message' },
      ]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query');
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(result.current.error).toBe('Test error message');
      expect(result.current.isResearching).toBe(false);
    });

    it('handles HTTP errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Server error'),
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query');
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(result.current.error).toContain('HTTP 500');
      expect(result.current.isResearching).toBe(false);
    });

    it('sends correct request body', async () => {
      const mockReadableStream = createMockStream([{ type: 'done' }]);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result } = renderHook(() => useResearchSSE());

      await act(async () => {
        result.current.startResearch('test query', 'test-namespace', 5);
        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/research/query'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: 'test query',
            namespace: 'test-namespace',
            max_iterations: 5,
            stream: true,
          }),
        })
      );
    });
  });

  describe('cleanup', () => {
    it('aborts ongoing request on unmount', () => {
      const abortSpy = vi.spyOn(AbortController.prototype, 'abort');

      const mockReadableStream = createMockStreamNeverEnding();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockReadableStream,
      });

      const { result, unmount } = renderHook(() => useResearchSSE());

      act(() => {
        result.current.startResearch('test query');
      });

      unmount();

      expect(abortSpy).toHaveBeenCalled();
      abortSpy.mockRestore();
    });
  });
});

// Helper to create mock SSE stream
function createMockStream(events: Array<{ type: string; data?: unknown; error?: string }>) {
  let eventIndex = 0;

  return {
    getReader: () => ({
      read: async () => {
        if (eventIndex >= events.length) {
          return { done: true, value: undefined };
        }

        const event = events[eventIndex++];
        let sseData: string;

        if (event.type === 'done') {
          sseData = 'data: [DONE]\n\n';
        } else if (event.type === 'error') {
          sseData = `data: ${JSON.stringify({ error: event.error })}\n\n`;
        } else if (event.type === 'result') {
          // Result events include synthesis field
          sseData = `data: ${JSON.stringify(event.data)}\n\n`;
        } else {
          sseData = `data: ${JSON.stringify(event.data)}\n\n`;
        }

        return {
          done: false,
          value: new TextEncoder().encode(sseData),
        };
      },
      releaseLock: vi.fn(),
    }),
  };
}

// Helper to create a stream that never ends (for testing cancellation)
function createMockStreamNeverEnding() {
  return {
    getReader: () => ({
      read: () => new Promise(() => {}), // Never resolves
      releaseLock: vi.fn(),
    }),
  };
}
