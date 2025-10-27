/**
 * Chat API Client Tests
 * Sprint 15 Feature 15.1 & 15.4
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { streamChat, listSessions, deleteSession } from './chat';

// Mock fetch
global.fetch = vi.fn();

describe('streamChat', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should yield chat chunks from SSE stream', async () => {
    const mockReadableStream = {
      getReader: () => ({
        read: vi.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"metadata","session_id":"123"}\n\n'),
          })
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"token","content":"Hello"}\n\n'),
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

    (global.fetch as any).mockResolvedValue({
      ok: true,
      body: mockReadableStream,
    });

    const chunks = [];
    for await (const chunk of streamChat({ query: 'test' })) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(2);
    expect(chunks[0].type).toBe('metadata');
    expect(chunks[1].type).toBe('token');
    expect(chunks[1].content).toBe('Hello');
  });

  it('should throw error on HTTP error', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Server error'),
    });

    await expect(async () => {
      for await (const _ of streamChat({ query: 'test' })) {
        // Should throw before yielding
      }
    }).rejects.toThrow('HTTP 500');
  });

  it('should throw error when response body is null', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
      body: null,
    });

    await expect(async () => {
      for await (const _ of streamChat({ query: 'test' })) {
        // Should throw before yielding
      }
    }).rejects.toThrow('Response body is null');
  });
});

describe('listSessions', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should return list of sessions', async () => {
    const mockSessions = {
      sessions: [
        {
          session_id: '123',
          message_count: 5,
          last_message: 'Test message',
          updated_at: '2025-01-01T00:00:00Z',
        },
      ],
      total_count: 1,
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSessions),
    });

    const result = await listSessions();

    expect(result.sessions).toHaveLength(1);
    expect(result.sessions[0].session_id).toBe('123');
    expect(result.total_count).toBe(1);
  });

  it('should throw error on HTTP error', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Not found'),
    });

    await expect(listSessions()).rejects.toThrow('HTTP 404');
  });
});

describe('deleteSession', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should successfully delete session', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: true,
    });

    await expect(deleteSession('123')).resolves.toBeUndefined();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/chat/history/123'),
      expect.objectContaining({
        method: 'DELETE',
      })
    );
  });

  it('should throw error on HTTP error', async () => {
    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Server error'),
    });

    await expect(deleteSession('123')).rejects.toThrow('HTTP 500');
  });
});
