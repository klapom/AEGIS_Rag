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
  });

  afterEach(() => {
    vi.clearAllMocks();
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

    it('should render all mode chips (Hybrid, Vector, Graph, Memory)', () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with accessible names instead of ambiguous getByText
      expect(screen.getByRole('button', { name: /Hybrid Mode/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Vector Mode/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Graph Mode/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Memory Mode/i })).toBeInTheDocument();
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

    it('should navigate to search page on Enter key press', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);

      fireEvent.change(input, { target: { value: 'test query' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('/search?q=test%20query&mode=hybrid')
        );
      });
    });

    it('should navigate to search page on submit button click', async () => {
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

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('/search?q=another%20test&mode=hybrid')
        );
      });
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

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('q=test%20query')
        );
      });
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

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=hybrid')
        );
      });
    });

    it('should switch to vector mode when Vector chip is clicked', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with accessible name instead of getByText
      const vectorChip = screen.getByRole('button', { name: /Vector Mode/i });
      fireEvent.click(vectorChip);

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'test' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=vector')
        );
      });
    });

    it('should switch to graph mode when Graph chip is clicked', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with accessible name instead of getByText
      const graphChip = screen.getByRole('button', { name: /Graph Mode/i });
      fireEvent.click(graphChip);

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'test' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=graph')
        );
      });
    });

    it('should switch to memory mode when Memory chip is clicked', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Use getByRole with accessible name instead of getByText
      const memoryChip = screen.getByRole('button', { name: /Memory Mode/i });
      fireEvent.click(memoryChip);

      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'test' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=memory')
        );
      });
    });

    it('should maintain selected mode across multiple submissions', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      // TD-38: Select vector mode with accessible selector
      const vectorChip = screen.getByRole('button', { name: /Vector Mode/i });
      fireEvent.click(vectorChip);

      // First submission
      const input = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(input, { target: { value: 'first query' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=vector')
        );
      });

      mockNavigate.mockClear();

      // Second submission (mode should still be vector)
      fireEvent.change(input, { target: { value: 'second query' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=vector')
        );
      });
    });
  });

  describe('Quick Prompts', () => {
    it('should navigate with quick prompt when clicked', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const quickPrompt = screen.getByText(/Erkläre mir das Konzept von RAG/);
      fireEvent.click(quickPrompt);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('Erkl%C3%A4re%20mir%20das%20Konzept%20von%20RAG')
        );
      });
    });

    it('should use hybrid mode for quick prompts', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const quickPrompt = screen.getByText(/Was ist ein Knowledge Graph/);
      fireEvent.click(quickPrompt);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=hybrid')
        );
      });
    });

    it('should navigate with all quick prompts correctly', async () => {
      render(
        <BrowserRouter>
          <HomePage />
        </BrowserRouter>
      );

      const prompts = [
        'Erkläre mir das Konzept von RAG',
        'Was ist ein Knowledge Graph?',
        'Wie funktioniert Hybrid Search?',
        'Zeige mir die Systemarchitektur',
      ];

      for (const promptText of prompts) {
        mockNavigate.mockClear();

        const prompt = screen.getByText(promptText);
        fireEvent.click(prompt);

        await waitFor(() => {
          expect(mockNavigate).toHaveBeenCalled();
        });
      }
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
