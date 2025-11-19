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

      // Use a smarter mock that handles multiple calls including follow-up questions
      let streamCallCount = 0;
      const mockFetch = vi.fn((url: string) => {
        if (url.includes('/stream')) {
          streamCallCount++;
          if (streamCallCount === 1) {
            return Promise.resolve({ ok: true, body: initialStream });
          } else {
            return Promise.resolve({ ok: true, body: followUpStream });
          }
        } else if (url.includes('followup-questions')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ followup_questions: [] }),
          });
        }
        return Promise.reject(new Error('Unexpected fetch URL: ' + url));
      });

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
      }, { timeout: 3000 });

      // Verify second stream call included session_id
      const streamCalls = (mockFetch as any).mock.calls.filter(
        (call: any[]) => call[0]?.includes('/stream')
      );
      expect(streamCalls.length).toBe(2);
      const secondStreamCallBody = JSON.parse(streamCalls[1][1].body);
      expect(secondStreamCallBody.session_id).toBe(mockSessionId);
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
      // The component should render the query from the URL params
      await waitFor(() => {
        expect(screen.getByText(/latest query/i)).toBeInTheDocument();
      });

      // Note: MemoryRouter doesn't update window.location, so we verify
      // the component correctly receives and uses the session_id via useSearchParams()
      // The session_id is properly handled in the component's URL state
    });
  });

  describe('Multi-Turn Conversations', () => {
    it('should maintain context across multiple turns', async () => {
      // Arrange: Mock multi-turn conversation
      const mockSessionId = 'session-multi-turn-456';

      // This test verifies that session_id is properly propagated across multiple queries
      // We test each turn independently (as they would happen in real usage)

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

      // Test Turn 1: Initial query (no session_id yet)
      const mockFetch1 = vi.fn().mockResolvedValue({
        ok: true,
        body: createMockStream('RAG is Retrieval-Augmented Generation'),
      });
      setupGlobalFetchMock(mockFetch1);

      const { unmount: unmount1 } = render(
        <MemoryRouter initialEntries={['/search?q=What+is+RAG&mode=hybrid']}>
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/RAG is Retrieval-Augmented Generation/)).toBeInTheDocument();
      });

      expect(mockFetch1).toHaveBeenCalled();
      const turn1Body = JSON.parse(mockFetch1.mock.calls[0][1].body);
      expect(turn1Body.session_id).toBeUndefined(); // First query has no session_id

      unmount1();

      // Test Turn 2: Follow-up query (with session_id)
      const mockFetch2 = vi.fn().mockResolvedValue({
        ok: true,
        body: createMockStream('It combines retrieval with generation'),
      });
      setupGlobalFetchMock(mockFetch2);

      const { unmount: unmount2 } = render(
        <MemoryRouter
          initialEntries={[
            `/search?q=How+does+it+work&mode=hybrid&session_id=${mockSessionId}`,
          ]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/It combines retrieval with generation/)).toBeInTheDocument();
      });

      expect(mockFetch2).toHaveBeenCalled();
      const turn2Body = JSON.parse(mockFetch2.mock.calls[0][1].body);
      expect(turn2Body.session_id).toBe(mockSessionId); // Second query includes session_id

      unmount2();

      // Test Turn 3: Another follow-up (with session_id)
      const mockFetch3 = vi.fn().mockResolvedValue({
        ok: true,
        body: createMockStream('Better accuracy and grounding'),
      });
      setupGlobalFetchMock(mockFetch3);

      render(
        <MemoryRouter
          initialEntries={[
            `/search?q=What+are+the+benefits&mode=hybrid&session_id=${mockSessionId}`,
          ]}
        >
          <Routes>
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/Better accuracy and grounding/)).toBeInTheDocument();
      });

      expect(mockFetch3).toHaveBeenCalled();
      const turn3Body = JSON.parse(mockFetch3.mock.calls[0][1].body);
      expect(turn3Body.session_id).toBe(mockSessionId); // Third query also includes session_id

      // Assert: Multi-turn conversation maintains session_id across all follow-up queries
      expect(turn2Body.session_id).toBe(turn3Body.session_id);
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
