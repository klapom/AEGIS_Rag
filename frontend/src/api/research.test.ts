/**
 * Research API Client Tests
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { streamResearch, research, checkResearchHealth } from './research';

// Mock fetch
global.fetch = vi.fn();

describe('streamResearch', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should yield progress chunks from SSE stream', async () => {
    const progressEvent = {
      phase: 'plan',
      message: 'Creating research plan',
      iteration: 1,
      metadata: { num_queries: 3 },
    };

    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode(`data: ${JSON.stringify(progressEvent)}\n\n`),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: [DONE]\n\n'),
          })
          .mockResolvedValueOnce({
            done: true,
            value: undefined,
          }),
        releaseLock: vi.fn(),
      }),
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    const chunks = [];
    for await (const chunk of streamResearch({ query: 'test query' })) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(2);
    expect(chunks[0].type).toBe('progress');
    expect(chunks[0].data).toEqual(progressEvent);
    expect(chunks[1].type).toBe('done');
  });

  it('should yield result chunks with synthesis', async () => {
    const resultEvent = {
      query: 'test query',
      synthesis: 'Test synthesis result',
      sources: [],
      iterations: 2,
      quality_metrics: {},
      research_plan: [],
    };

    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode(`data: ${JSON.stringify(resultEvent)}\n\n`),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: [DONE]\n\n'),
          })
          .mockResolvedValueOnce({
            done: true,
            value: undefined,
          }),
        releaseLock: vi.fn(),
      }),
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    const chunks = [];
    for await (const chunk of streamResearch({ query: 'test query' })) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(2);
    expect(chunks[0].type).toBe('result');
    expect(chunks[0].data).toEqual(resultEvent);
  });

  it('should yield error chunks', async () => {
    const errorEvent = { error: 'Test error message' };

    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode(`data: ${JSON.stringify(errorEvent)}\n\n`),
          })
          .mockResolvedValueOnce({
            done: true,
            value: undefined,
          }),
        releaseLock: vi.fn(),
      }),
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    const chunks = [];
    for await (const chunk of streamResearch({ query: 'test query' })) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(1);
    expect(chunks[0].type).toBe('error');
    expect(chunks[0].error).toBe('Test error message');
  });

  it('should throw error on HTTP error', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Server error'),
    });

    await expect(async () => {
      for await (const _ of streamResearch({ query: 'test' })) {
        // Should throw before yielding
      }
    }).rejects.toThrow('HTTP 500');
  });

  it('should throw error when response body is null', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: null,
    });

    await expect(async () => {
      for await (const _ of streamResearch({ query: 'test' })) {
        // Should throw before yielding
      }
    }).rejects.toThrow('Response body is null');
  });

  it('should send correct request body with defaults', async () => {
    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: [DONE]\n\n'),
          })
          .mockResolvedValueOnce({
            done: true,
            value: undefined,
          }),
        releaseLock: vi.fn(),
      }),
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    for await (const _ of streamResearch({ query: 'test query' })) {
      // consume stream
    }

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/research/query'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'test query',
          namespace: 'default',
          max_iterations: 3,
          stream: true,
        }),
      })
    );
  });

  it('should send correct request body with custom options', async () => {
    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: [DONE]\n\n'),
          })
          .mockResolvedValueOnce({
            done: true,
            value: undefined,
          }),
        releaseLock: vi.fn(),
      }),
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    for await (const _ of streamResearch({
      query: 'test query',
      namespace: 'custom-namespace',
      max_iterations: 5,
    })) {
      // consume stream
    }

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/research/query'),
      expect.objectContaining({
        body: JSON.stringify({
          query: 'test query',
          namespace: 'custom-namespace',
          max_iterations: 5,
          stream: true,
        }),
      })
    );
  });

  it('should pass abort signal to fetch', async () => {
    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: [DONE]\n\n'),
          })
          .mockResolvedValueOnce({
            done: true,
            value: undefined,
          }),
        releaseLock: vi.fn(),
      }),
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    const abortController = new AbortController();

    for await (const _ of streamResearch({ query: 'test' }, abortController.signal)) {
      // consume stream
    }

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        signal: abortController.signal,
      })
    );
  });
});

describe('research', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should return research response', async () => {
    const mockResponse = {
      query: 'test query',
      synthesis: 'Test synthesis',
      sources: [],
      iterations: 2,
      quality_metrics: { coverage: 0.8 },
      research_plan: ['Step 1'],
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await research({ query: 'test query' });

    expect(result).toEqual(mockResponse);
  });

  it('should send stream=false for non-streaming request', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await research({ query: 'test query' });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({
          query: 'test query',
          namespace: 'default',
          max_iterations: 3,
          stream: false,
        }),
      })
    );
  });

  it('should throw error on HTTP error', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Server error'),
    });

    await expect(research({ query: 'test' })).rejects.toThrow('HTTP 500');
  });
});

describe('checkResearchHealth', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should return health status', async () => {
    const mockHealth = { status: 'healthy', service: 'research' };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockHealth),
    });

    const result = await checkResearchHealth();

    expect(result).toEqual(mockHealth);
  });

  it('should call correct endpoint', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy', service: 'research' }),
    });

    await checkResearchHealth();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/research/health'),
      expect.objectContaining({
        method: 'GET',
      })
    );
  });

  it('should throw error on HTTP error', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 503,
    });

    await expect(checkResearchHealth()).rejects.toThrow('Research health check failed');
  });
});
