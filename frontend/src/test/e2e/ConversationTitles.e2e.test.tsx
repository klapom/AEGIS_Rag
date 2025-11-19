/**
 * Conversation Titles E2E Tests
 * Sprint 17 Feature 17.3: Auto-Generated Conversation Titles
 *
 * Tests cover:
 * - Title auto-generates after first answer
 * - Title appears in session list
 * - User can edit title inline
 * - Title changes persist to Redis
 * - Enter key saves, Escape cancels edit
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { SessionItem } from '../../components/history/SessionItem';
import { SessionSidebar } from '../../components/history/SessionSidebar';
import { StreamingAnswer } from '../../components/chat/StreamingAnswer';
import {
  setupGlobalFetchMock,
  cleanupGlobalFetchMock,
  mockFetchJSONSuccess,
} from './helpers';
import { mockSessionsWithTitles, mockTitleResponse } from './fixtures';

describe('Feature 17.3: Auto-Generated Titles E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  describe('Auto-Title Generation', () => {
    it('should auto-generate title after first answer completes', async () => {
      // Arrange: Mock streaming response + title generation
      const mockSessionId = 'session-auto-title-123';
      const encoder = new TextEncoder();

      const streamResponse = new ReadableStream({
        async start(controller) {
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
                content: 'This is a comprehensive answer about knowledge graphs and how they work in RAG systems.',
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

      // Mock fetch to return stream first, then handle follow-up questions and title generation
      const mockFetch = vi.fn((url: string) => {
        if (url.includes('/stream')) {
          return Promise.resolve({ ok: true, body: streamResponse });
        } else if (url.includes('generate-title')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                session_id: mockSessionId,
                title: 'Knowledge Graphs in RAG',
                generated_at: '2025-10-29T10:00:00Z',
              }),
          });
        } else if (url.includes('followup-questions')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ followup_questions: [] }),
          });
        }
        return Promise.reject(new Error('Unexpected fetch URL: ' + url));
      });

      setupGlobalFetchMock(mockFetch);

      // Track title callback
      const onTitleGenerated = vi.fn();

      // Act: Render streaming answer
      render(
        <MemoryRouter>
          <StreamingAnswer
            query="What are knowledge graphs?"
            mode="hybrid"
            sessionId={mockSessionId}
            onTitleGenerated={onTitleGenerated}
          />
        </MemoryRouter>
      );

      // Assert: Answer should complete
      await waitFor(
        () => {
          expect(
            screen.getByText(/This is a comprehensive answer about knowledge graphs/i)
          ).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Title generation should be triggered
      await waitFor(
        () => {
          expect(mockFetch).toHaveBeenCalledWith(
            expect.stringContaining(
              `/api/v1/chat/sessions/${mockSessionId}/generate-title`
            ),
            expect.objectContaining({ method: 'POST' })
          );
        },
        { timeout: 2000 }
      );

      // Callback should be invoked
      await waitFor(() => {
        expect(onTitleGenerated).toHaveBeenCalledWith('Knowledge Graphs in RAG');
      });
    });

    it('should not auto-generate title for very short answers', async () => {
      // Arrange: Mock streaming with short answer (< 50 chars)
      const mockSessionId = 'session-short-answer-456';
      const encoder = new TextEncoder();

      const streamResponse = new ReadableStream({
        async start(controller) {
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
                content: 'Yes.',
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

      const mockFetch = vi.fn().mockResolvedValue({ ok: true, body: streamResponse });
      setupGlobalFetchMock(mockFetch);

      const onTitleGenerated = vi.fn();

      // Act: Render streaming answer with short content
      render(
        <MemoryRouter>
          <StreamingAnswer
            query="Simple question?"
            mode="hybrid"
            sessionId={mockSessionId}
            onTitleGenerated={onTitleGenerated}
          />
        </MemoryRouter>
      );

      // Assert: Short answer should be displayed
      await waitFor(() => {
        expect(screen.getByText(/Yes./i)).toBeInTheDocument();
      });

      // Wait a bit longer to ensure no title generation call
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Title generation should NOT be called for short answers
      // Note: mockFetch might be called 1-2 times (stream + follow-up questions)
      // but should NOT include a call to generate-title endpoint
      const titleGenerationCalls = (mockFetch as any).mock.calls.filter(
        (call: any[]) => call[0]?.includes('generate-title')
      );
      expect(titleGenerationCalls.length).toBe(0);
      expect(onTitleGenerated).not.toHaveBeenCalled();
    });

    it('should display auto-generated title in session list', async () => {
      // Arrange: Mock sessions with auto-generated titles
      setupGlobalFetchMock(
        mockFetchJSONSuccess({
          sessions: mockSessionsWithTitles,
          total_count: mockSessionsWithTitles.length,
        })
      );

      // Act: Render session sidebar
      render(
        <MemoryRouter>
          <SessionSidebar isOpen={true} onToggle={() => {}} />
        </MemoryRouter>
      );

      // Assert: Titles should be displayed
      await waitFor(
        () => {
          expect(screen.getByText(/Knowledge Graphs Overview/i)).toBeInTheDocument();
          expect(screen.getByText(/RAG Architecture/i)).toBeInTheDocument();
          expect(screen.getByText(/Hybrid Search Explained/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Inline Title Editing', () => {
    it('should allow user to edit title inline', async () => {
      // Arrange: Render session item with title
      const mockSession = mockSessionsWithTitles[0];
      const onDelete = vi.fn();
      const onTitleUpdate = vi.fn();

      // Mock PATCH response for title update
      setupGlobalFetchMock(
        mockFetchJSONSuccess({
          session_id: mockSession.session_id,
          title: 'Updated Title',
          generated_at: '2025-10-29T10:30:00Z',
        })
      );

      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <SessionItem
            session={mockSession}
            onDelete={onDelete}
            onTitleUpdate={onTitleUpdate}
          />
        </MemoryRouter>
      );

      // Act: Click on title to enter edit mode
      const titleElement = screen.getByText(mockSession.title!);
      await user.click(titleElement);

      // Assert: Input field should be visible
      await waitFor(() => {
        const input = screen.getByDisplayValue(mockSession.title!);
        expect(input).toBeInTheDocument();
        expect(input).toHaveFocus();
      });

      // Act: Change title text
      const input = screen.getByDisplayValue(mockSession.title!) as HTMLInputElement;
      await user.clear(input);
      await user.type(input, 'Updated Title');

      // Act: Blur to save (simulating Enter or click outside)
      fireEvent.blur(input);

      // Assert: PATCH request should be made
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining(`/api/v1/chat/sessions/${mockSession.session_id}`),
          expect.objectContaining({
            method: 'PATCH',
            body: JSON.stringify({ title: 'Updated Title' }),
          })
        );
      });

      // Assert: Callback should be invoked
      await waitFor(() => {
        expect(onTitleUpdate).toHaveBeenCalledWith(
          mockSession.session_id,
          'Updated Title'
        );
      });
    });

    it('should save title on Enter key press', async () => {
      // Arrange
      const mockSession = mockSessionsWithTitles[1];
      const onDelete = vi.fn();
      const onTitleUpdate = vi.fn();

      setupGlobalFetchMock(
        mockFetchJSONSuccess({
          session_id: mockSession.session_id,
          title: 'New Title via Enter',
          generated_at: '2025-10-29T10:35:00Z',
        })
      );

      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <SessionItem
            session={mockSession}
            onDelete={onDelete}
            onTitleUpdate={onTitleUpdate}
          />
        </MemoryRouter>
      );

      // Act: Enter edit mode
      const titleElement = screen.getByText(mockSession.title!);
      await user.click(titleElement);

      // Wait for input to be focused
      await waitFor(() => {
        expect(screen.getByDisplayValue(mockSession.title!)).toHaveFocus();
      });

      // Act: Type new title and press Enter
      const input = screen.getByDisplayValue(mockSession.title!) as HTMLInputElement;
      await user.clear(input);
      await user.type(input, 'New Title via Enter');
      await user.keyboard('{Enter}');

      // Assert: PATCH request should be made
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining(`/api/v1/chat/sessions/${mockSession.session_id}`),
          expect.objectContaining({
            method: 'PATCH',
            body: JSON.stringify({ title: 'New Title via Enter' }),
          })
        );
      });

      // Assert: Title update callback invoked
      await waitFor(() => {
        expect(onTitleUpdate).toHaveBeenCalledWith(
          mockSession.session_id,
          'New Title via Enter'
        );
      });
    });

    it('should cancel edit on Escape key press', async () => {
      // Arrange
      const mockSession = mockSessionsWithTitles[2];
      const originalTitle = mockSession.title!;
      const onDelete = vi.fn();
      const onTitleUpdate = vi.fn();

      const mockFetch = vi.fn();
      setupGlobalFetchMock(mockFetch);

      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <SessionItem
            session={mockSession}
            onDelete={onDelete}
            onTitleUpdate={onTitleUpdate}
          />
        </MemoryRouter>
      );

      // Act: Enter edit mode
      const titleElement = screen.getByText(originalTitle);
      await user.click(titleElement);

      await waitFor(() => {
        expect(screen.getByDisplayValue(originalTitle)).toHaveFocus();
      });

      // Act: Type something and press Escape
      const input = screen.getByDisplayValue(originalTitle) as HTMLInputElement;
      await user.type(input, ' Modified');
      await user.keyboard('{Escape}');

      // Assert: No PATCH request should be made
      expect(mockFetch).not.toHaveBeenCalled();

      // Assert: Original title should be restored
      await waitFor(() => {
        expect(screen.getByText(originalTitle)).toBeInTheDocument();
      });

      // Assert: Callback should not be invoked
      expect(onTitleUpdate).not.toHaveBeenCalled();
    });

    it('should not save if title is unchanged', async () => {
      // Arrange
      const mockSession = mockSessionsWithTitles[0];
      const originalTitle = mockSession.title!;
      const onDelete = vi.fn();
      const onTitleUpdate = vi.fn();

      const mockFetch = vi.fn();
      setupGlobalFetchMock(mockFetch);

      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <SessionItem
            session={mockSession}
            onDelete={onDelete}
            onTitleUpdate={onTitleUpdate}
          />
        </MemoryRouter>
      );

      // Act: Enter edit mode
      const titleElement = screen.getByText(originalTitle);
      await user.click(titleElement);

      await waitFor(() => {
        expect(screen.getByDisplayValue(originalTitle)).toHaveFocus();
      });

      // Act: Blur without changing (simulating Enter on unchanged title)
      const input = screen.getByDisplayValue(originalTitle);
      fireEvent.blur(input);

      // Assert: No PATCH request should be made
      expect(mockFetch).not.toHaveBeenCalled();
      expect(onTitleUpdate).not.toHaveBeenCalled();

      // Assert: Edit mode should exit
      await waitFor(() => {
        expect(screen.getByText(originalTitle)).toBeInTheDocument();
      });
    });

    it('should show loading indicator while saving title', async () => {
      // Arrange
      const mockSession = mockSessionsWithTitles[1];
      const onDelete = vi.fn();
      const onTitleUpdate = vi.fn();

      // Mock slow response to test loading state
      const mockFetch = vi.fn(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: () =>
                Promise.resolve({
                  session_id: mockSession.session_id,
                  title: 'Slow Update',
                  generated_at: '2025-10-29T10:40:00Z',
                }),
            });
          }, 500);
        });
      });

      setupGlobalFetchMock(mockFetch);

      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <SessionItem
            session={mockSession}
            onDelete={onDelete}
            onTitleUpdate={onTitleUpdate}
          />
        </MemoryRouter>
      );

      // Act: Enter edit mode and change title
      const titleElement = screen.getByText(mockSession.title!);
      await user.click(titleElement);

      const input = screen.getByDisplayValue(mockSession.title!) as HTMLInputElement;
      await user.clear(input);
      await user.type(input, 'Slow Update');
      await user.keyboard('{Enter}');

      // Assert: Loading spinner should appear
      await waitFor(() => {
        const spinner = screen.getByRole('img', { hidden: true });
        expect(spinner).toBeInTheDocument();
      });

      // Wait for completion
      await waitFor(
        () => {
          expect(onTitleUpdate).toHaveBeenCalledWith(
            mockSession.session_id,
            'Slow Update'
          );
        },
        { timeout: 2000 }
      );
    });
  });

  describe('Error Handling', () => {
    it('should handle title generation API failure gracefully', async () => {
      // Arrange: Mock streaming success but title generation failure
      const mockSessionId = 'session-title-error-789';
      const encoder = new TextEncoder();

      const streamResponse = new ReadableStream({
        async start(controller) {
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
                content:
                  'This is a long answer that should trigger title generation but will fail.',
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
        .mockResolvedValueOnce({ ok: true, body: streamResponse })
        .mockRejectedValueOnce(new Error('Title generation service unavailable'));

      setupGlobalFetchMock(mockFetch);

      const onTitleGenerated = vi.fn();

      // Act: Render streaming answer
      render(
        <MemoryRouter>
          <StreamingAnswer
            query="Test query"
            mode="hybrid"
            sessionId={mockSessionId}
            onTitleGenerated={onTitleGenerated}
          />
        </MemoryRouter>
      );

      // Assert: Answer should still complete successfully
      await waitFor(() => {
        expect(
          screen.getByText(/This is a long answer that should trigger title generation/i)
        ).toBeInTheDocument();
      });

      // Title generation failure should not break the UI
      // Callback should not be invoked
      await new Promise((resolve) => setTimeout(resolve, 500));
      expect(onTitleGenerated).not.toHaveBeenCalled();
    });

    it('should handle title update API failure with error message', async () => {
      // Arrange
      const mockSession = mockSessionsWithTitles[0];
      const onDelete = vi.fn();
      const onTitleUpdate = vi.fn();

      // Mock failed PATCH request
      setupGlobalFetchMock(
        vi.fn().mockRejectedValue(new Error('Failed to update title'))
      );

      // Mock alert
      global.alert = vi.fn();

      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <SessionItem
            session={mockSession}
            onDelete={onDelete}
            onTitleUpdate={onTitleUpdate}
          />
        </MemoryRouter>
      );

      // Act: Edit and try to save
      const titleElement = screen.getByText(mockSession.title!);
      await user.click(titleElement);

      const input = screen.getByDisplayValue(mockSession.title!);
      await user.clear(input);
      await user.type(input, 'Failed Update');
      await user.keyboard('{Enter}');

      // Assert: Error alert should be shown
      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith(
          'Fehler beim Aktualisieren des Titels'
        );
      });

      // Title should revert to original
      await waitFor(() => {
        expect(screen.getByText(mockSession.title!)).toBeInTheDocument();
      });

      // Callback should not be invoked
      expect(onTitleUpdate).not.toHaveBeenCalled();
    });
  });
});
