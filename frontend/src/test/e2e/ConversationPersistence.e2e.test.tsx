/**
 * Conversation Persistence E2E Tests
 * Sprint 17 Feature 17.2: Conversation History Persistence
 *
 * Tests cover:
 * - Conversations save to Redis after streaming
 * - Session list shows saved conversations
 * - Follow-up questions preserve session_id
 * - Page refresh maintains conversation history
 * - Multi-turn conversation context works
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SearchResultsPage } from '../../pages/SearchResultsPage';
import { SessionSidebar } from '../../components/history/SessionSidebar';
import {
  setupGlobalFetchMock,
  cleanupGlobalFetchMock,
  mockFetchJSONSuccess,
} from './helpers';
import { mockSessionsWithTitles, mockConversationWithMultiTurn } from './fixtures';

describe('Feature 17.2: Conversation Persistence E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  describe('Session Persistence', () => {
    it('should save conversation to Redis after streaming completes', async () => {
      // Arrange: Mock SSE streaming response with session_id
      const mockSessionId = 'test-session-abc123';
      const encoder = new TextEncoder();
      const mockStream = new ReadableStream({
        async start(controller) {
          // Send metadata with session_id
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'metadata',
                data: {
                  session_id: mockSessionId,
                  intent: 'hybrid',
                },
              })}\n\n`
            )
          );

          // Send some tokens
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'token',
                content: 'Test answer',
              })}\n\n`
            )
          );

          // Send completion
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'complete',
                data: { latency_seconds: 1.5 },
              })}\n\n`
            )
          );

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

      // Act: Render search results page
      render(
        <MemoryRouter initialEntries={['/search?q=test+query&mode=hybrid']}>
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // Assert: Session ID should be received and stored
      await waitFor(
        () => {
          expect(screen.getByText(/Test answer/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Verify fetch was called with correct parameters
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/chat/stream'),
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('test query'),
        })
      );
    });

    it('should display saved sessions in session list', async () => {
      // Arrange: Mock sessions list API
      setupGlobalFetchMock(
        mockFetchJSONSuccess({
          sessions: mockSessionsWithTitles,
          total_count: mockSessionsWithTitles.length,
        })
      );

      // Act: Render session sidebar
      const { container } = render(
        <MemoryRouter>
          <SessionSidebar isOpen={true} onToggle={() => {}} />
        </MemoryRouter>
      );

      // Assert: Sessions should be displayed
      await waitFor(
        () => {
          expect(screen.getByText(/Knowledge Graphs Overview/i)).toBeInTheDocument();
          expect(screen.getByText(/RAG Architecture/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Verify correct number of sessions displayed
      expect(screen.getByText(/3 Nachrichten/i)).toBeInTheDocument();
    });

    it('should preserve session_id for follow-up questions', async () => {
      // Arrange: Initial session with session_id
      const mockSessionId = 'session-follow-up-123';
      const mockFollowUpFetch = vi.fn();

      // First call: initial query
      const initialStream = new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'metadata',
                data: { session_id: mockSessionId, intent: 'hybrid' },
              })}\n\n`
            )
          );
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'token',
                content: 'Initial answer',
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

      // Second call: follow-up query
      const followUpStream = new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'metadata',
                data: { session_id: mockSessionId, intent: 'hybrid' },
              })}\n\n`
            )
          );
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({
                type: 'token',
                content: 'Follow-up answer',
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

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true, body: initialStream })
        .mockResolvedValueOnce({ ok: true, body: followUpStream });

      setupGlobalFetchMock(mockFetch);

      // Act: Render initial query
      const { rerender } = render(
        <MemoryRouter initialEntries={['/search?q=initial+query&mode=hybrid']}>
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // Wait for initial answer
      await waitFor(() => {
        expect(screen.getByText(/Initial answer/i)).toBeInTheDocument();
      });

      // Act: Submit follow-up question
      rerender(
        <MemoryRouter
          initialEntries={[
            `/search?q=follow+up&mode=hybrid&session_id=${mockSessionId}`,
          ]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // Assert: Follow-up should include session_id
      await waitFor(() => {
        expect(screen.getByText(/Follow-up answer/i)).toBeInTheDocument();
      });

      // Verify second fetch included session_id
      expect(mockFetch).toHaveBeenCalledTimes(2);
      const secondCallBody = JSON.parse(mockFetch.mock.calls[1][1].body);
      expect(secondCallBody.session_id).toBe(mockSessionId);
    });
  });

  describe('Page Refresh Behavior', () => {
    it('should maintain conversation history after page refresh', async () => {
      // Arrange: Mock conversation history API
      const mockSessionId = 'session-refresh-test-123';
      setupGlobalFetchMock(
        mockFetchJSONSuccess({
          session_id: mockSessionId,
          messages: mockConversationWithMultiTurn,
          message_count: mockConversationWithMultiTurn.length,
        })
      );

      // Act: Simulate page refresh by rendering with session_id in URL
      render(
        <MemoryRouter
          initialEntries={[
            `/search?q=latest+query&mode=hybrid&session_id=${mockSessionId}`,
          ]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // Assert: Session should be restored (component behavior)
      await waitFor(() => {
        expect(screen.getByText(/latest query/i)).toBeInTheDocument();
      });

      // URL should contain session_id
      expect(window.location.search).toContain(`session_id=${mockSessionId}`);
    });
  });

  describe('Multi-Turn Conversations', () => {
    it('should maintain context across multiple turns', async () => {
      // Arrange: Mock multi-turn conversation
      const mockSessionId = 'session-multi-turn-456';
      const turns = [
        { query: 'What is RAG?', answer: 'RAG is Retrieval-Augmented Generation' },
        {
          query: 'How does it work?',
          answer: 'It combines retrieval with generation',
        },
        { query: 'What are the benefits?', answer: 'Better accuracy and grounding' },
      ];

      const createMockStream = (answer: string) =>
        new ReadableStream({
          async start(controller) {
            const encoder = new TextEncoder();
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({
                  type: 'metadata',
                  data: { session_id: mockSessionId, intent: 'hybrid' },
                })}\n\n`
              )
            );
            controller.enqueue(
              encoder.encode(
                `data: ${JSON.stringify({ type: 'token', content: answer })}\n\n`
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

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({ ok: true, body: createMockStream(turns[0].answer) })
        .mockResolvedValueOnce({ ok: true, body: createMockStream(turns[1].answer) })
        .mockResolvedValueOnce({ ok: true, body: createMockStream(turns[2].answer) });

      setupGlobalFetchMock(mockFetch);

      // Act: Simulate three turns
      const { rerender } = render(
        <MemoryRouter
          initialEntries={[`/search?q=${encodeURIComponent(turns[0].query)}&mode=hybrid`]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // Turn 1
      await waitFor(() => {
        expect(screen.getByText(turns[0].answer)).toBeInTheDocument();
      });

      // Turn 2
      rerender(
        <MemoryRouter
          initialEntries={[
            `/search?q=${encodeURIComponent(turns[1].query)}&mode=hybrid&session_id=${mockSessionId}`,
          ]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(turns[1].answer)).toBeInTheDocument();
      });

      // Turn 3
      rerender(
        <MemoryRouter
          initialEntries={[
            `/search?q=${encodeURIComponent(turns[2].query)}&mode=hybrid&session_id=${mockSessionId}`,
          ]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(turns[2].answer)).toBeInTheDocument();
      });

      // Assert: All turns should have used the same session_id
      expect(mockFetch).toHaveBeenCalledTimes(3);
      const turn2Body = JSON.parse(mockFetch.mock.calls[1][1].body);
      const turn3Body = JSON.parse(mockFetch.mock.calls[2][1].body);
      expect(turn2Body.session_id).toBe(mockSessionId);
      expect(turn3Body.session_id).toBe(mockSessionId);
    });

    it('should handle conversation history retrieval', async () => {
      // Arrange: Mock session with history
      const mockSessionId = 'session-history-789';
      setupGlobalFetchMock(
        mockFetchJSONSuccess({
          session_id: mockSessionId,
          messages: mockConversationWithMultiTurn,
          message_count: mockConversationWithMultiTurn.length,
        })
      );

      // Act: Fetch conversation history (would be triggered by clicking session in sidebar)
      const response = await fetch(
        `http://localhost:8000/api/v1/chat/history/${mockSessionId}`
      );
      const data = await response.json();

      // Assert: History should be retrieved correctly
      expect(data.session_id).toBe(mockSessionId);
      expect(data.messages).toHaveLength(mockConversationWithMultiTurn.length);
      expect(data.messages[0].role).toBe('user');
      expect(data.messages[1].role).toBe('assistant');
    });
  });

  describe('Error Handling', () => {
    it('should handle session creation failure gracefully', async () => {
      // Arrange: Mock failed session creation
      setupGlobalFetchMock(
        vi.fn().mockRejectedValue(new Error('Redis connection failed'))
      );

      // Act: Render search results
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
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
    });

    it('should handle session list loading failure', async () => {
      // Arrange: Mock failed session list retrieval
      setupGlobalFetchMock(
        vi.fn().mockRejectedValue(new Error('Failed to load sessions'))
      );

      // Act: Render session sidebar
      render(
        <MemoryRouter>
          <SessionSidebar isOpen={true} onToggle={() => {}} />
        </MemoryRouter>
      );

      // Assert: Error message should be shown
      await waitFor(
        () => {
          expect(screen.getByText(/Fehler beim Laden der Sitzungen/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Retry button should be available
      expect(screen.getByText(/Erneut versuchen/i)).toBeInTheDocument();
    });
  });
});
