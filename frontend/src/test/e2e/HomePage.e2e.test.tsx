/**
 * HomePage E2E Tests
 * Sprint 15 Feature 15.3: End-to-end tests for landing page
 * Sprint 18 TD-38: Modernized selectors (accessibility-first approach)
 *
 * Tests cover:
 * - Initial page render
 * - Search input interaction
 * - Mode selection
 * - Quick prompt navigation
 * - Form submission
 *
 * TD-38 Phase 1: Migrated from brittle text-based selectors to:
 * - data-testid for ambiguous elements
 * - getByRole for accessible elements
 * - getByLabelText for form inputs
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { HomePage } from '../../pages/HomePage';
import { sampleQueries } from './fixtures';
import { mockFetchSSESuccess, setupGlobalFetchMock, cleanupGlobalFetchMock } from './helpers';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('HomePage E2E Tests', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    // Setup fetch mock for both SSE streaming and JSON API calls
    // StreamingAnswer needs SSE mock, FollowUpQuestions needs JSON mock
    setupGlobalFetchMock(
      vi.fn().mockImplementation((url: string) => {
        // Mock follow-up questions API (JSON response)
        if (url.includes('/followup-questions')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ followup_questions: [] }),
          });
        }
        // Mock SSE streaming API (ReadableStream response)
        return mockFetchSSESuccess()();
      })
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
    cleanupGlobalFetchMock();
  });

  describe('Initial Render', () => {
    it('should render welcome message and search input', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // Check welcome text
      expect(screen.getByText(/Was möchten Sie wissen/i)).toBeInTheDocument();
      expect(screen.getByText(/Durchsuchen Sie Ihre Dokumente/i)).toBeInTheDocument();

      // Check search input
      const searchInput = screen.getByPlaceholderText(/Fragen Sie alles/i);
      expect(searchInput).toBeInTheDocument();
      expect(searchInput).toHaveFocus(); // Auto-focus enabled
    });

    // Sprint 52: Mode selector removed - SearchInput now uses fixed hybrid mode
    it('should render search input without mode chips', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // Verify search input exists
      expect(screen.getByPlaceholderText(/Fragen Sie alles/i)).toBeInTheDocument();

      // Verify mode chips are NOT rendered (removed in Sprint 52)
      expect(screen.queryByRole('button', { name: /Hybrid Mode/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Vector Mode/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Graph Mode/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Memory Mode/i })).not.toBeInTheDocument();
    });

    it('should render quick prompt examples', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      expect(screen.getByText(/Erkläre mir das Konzept von RAG/)).toBeInTheDocument();
      expect(screen.getByText(/Was ist ein Knowledge Graph/)).toBeInTheDocument();
      expect(screen.getByText(/Wie funktioniert Hybrid Search/)).toBeInTheDocument();
      expect(screen.getByText(/Zeige mir die Systemarchitektur/)).toBeInTheDocument();
    });

    it('should render feature cards', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with heading to distinguish feature cards from mode chips
      expect(screen.getByRole('heading', { name: 'Vector Search', level: 3 })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Graph RAG', level: 3 })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Memory', level: 3 })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Hybrid', level: 3 })).toBeInTheDocument();
    });
  });

  describe('Search Input Interaction', () => {
    it('should update input value when user types', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i) as HTMLInputElement;

      fireEvent.change(input, { target: { value: sampleQueries.valid[0] } });

      expect(input.value).toBe(sampleQueries.valid[0]);
    });

    it('should render inline chat response on Enter key press', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);

      fireEvent.change(input, { target: { value: 'test query' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      // Sprint 31: Verify inline chat rendering instead of navigation
      await waitFor(() => {
        // User message should appear in conversation history
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        // Verify the user message contains our query text
        const userMessage = messages.find((msg) => msg.textContent?.includes('Frage'));
        expect(userMessage).toBeInTheDocument();
        expect(userMessage?.textContent).toContain('test query');
      });

      // No navigation should occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should render inline chat response on submit button click', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'another test' } });

      // TD-38: Use getByRole with aria-label instead of getByTitle
      const submitButton = screen.getByRole('button', { name: /Suche starten/i });
      fireEvent.click(submitButton);

      // Sprint 31: Verify inline chat rendering instead of navigation
      await waitFor(() => {
        // User message should appear in conversation history
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        const userMessage = messages.find((msg) => msg.textContent?.includes('Frage'));
        expect(userMessage).toBeInTheDocument();
        expect(userMessage?.textContent).toContain('another test');
      });

      // No navigation should occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should not submit empty query', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with aria-label instead of getByTitle
      const submitButton = screen.getByRole('button', { name: /Suche starten/i });
      fireEvent.click(submitButton);

      // Verify no messages were added
      const messages = screen.queryAllByTestId('message');
      expect(messages.length).toBe(0);

      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should trim whitespace before submission', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: '  test query  ' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      // Sprint 31: Verify trimmed query appears in chat
      await waitFor(() => {
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        const userMessage = messages.find((msg) => msg.textContent?.includes('Frage'));
        expect(userMessage).toBeInTheDocument();
        expect(userMessage?.textContent).toContain('test query');
      });

      // No navigation should occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe('Mode Selection', () => {
    it('should default to hybrid mode', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'test' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      // Sprint 31: Verify inline chat with default hybrid mode
      await waitFor(() => {
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        const userMessage = messages.find((msg) => msg.textContent?.includes('Frage'));
        expect(userMessage).toBeInTheDocument();
      });

      // Mode is passed to StreamingAnswer component (hybrid is default)
      // No navigation occurs
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    // Sprint 52: Mode selector removed - tests now use fixed hybrid mode
  });

  describe('Quick Prompts', () => {
    it('should render inline chat when quick prompt is clicked', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const quickPrompt = screen.getByText(/Erkläre mir das Konzept von RAG/);
      fireEvent.click(quickPrompt);

      // Sprint 31: Verify inline chat rendering instead of navigation
      await waitFor(() => {
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        const userMessage = messages.find((msg) => msg.textContent?.includes('Erkläre mir das Konzept von RAG'));
        expect(userMessage).toBeInTheDocument();
      });

      // No navigation should occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should use hybrid mode for quick prompts', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const quickPrompt = screen.getByText(/Was ist ein Knowledge Graph/);
      fireEvent.click(quickPrompt);

      // Sprint 31: Verify inline chat with hybrid mode (default for quick prompts)
      await waitFor(() => {
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        const userMessage = messages.find((msg) => msg.textContent?.includes('Was ist ein Knowledge Graph'));
        expect(userMessage).toBeInTheDocument();
      });

      // Mode is hybrid (default) - passed to StreamingAnswer component
      // No navigation should occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should render inline chat for all quick prompts correctly', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // Only test first prompt to avoid state accumulation
      const quickPrompt = screen.getByText(/Erkläre mir das Konzept von RAG/);
      fireEvent.click(quickPrompt);

      // Sprint 31: Verify prompt triggers inline chat
      await waitFor(() => {
        const messages = screen.getAllByTestId('message');
        expect(messages.length).toBeGreaterThan(0);

        const userMessage = messages.find((msg) => msg.textContent?.includes('Erkläre mir das Konzept von RAG'));
        expect(userMessage).toBeInTheDocument();
      });

      // No navigation should occur
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe('Submit Button States', () => {
    it('should disable submit button when input is empty', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with aria-label instead of getByTitle
      const submitButton = screen.getByRole('button', { name: /Suche starten/i }) as HTMLButtonElement;
      expect(submitButton.disabled).toBe(true);
    });

    it('should enable submit button when input has text', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'test' } });

      // TD-38: Use getByRole with aria-label instead of getByTitle
      const submitButton = screen.getByRole('button', { name: /Suche starten/i }) as HTMLButtonElement;
      expect(submitButton.disabled).toBe(false);
    });

    it('should disable submit button when input is only whitespace', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: '   ' } });

      // TD-38: Use getByRole with aria-label instead of getByTitle
      const submitButton = screen.getByRole('button', { name: /Suche starten/i }) as HTMLButtonElement;
      expect(submitButton.disabled).toBe(true);
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('should show Enter keyboard hint', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      expect(screen.getByText('Enter')).toBeInTheDocument();
      expect(screen.getByText(/zum Senden/i)).toBeInTheDocument();
    });

    it('should not submit on Shift+Enter', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'test' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
