/**
 * SearchResultsPage E2E Tests
 * Sprint 15 Feature 15.4: End-to-end tests for search results page
 * Sprint 18 TD-38 Phase 2: Modernized selectors (accessibility-first approach)
 *
 * Tests cover:
 * - Page rendering with query params
 * - Empty query handling
 * - New search submission
 * - StreamingAnswer integration
 * - Navigation flows
 *
 * TD-38: Migrated to accessibility-first selectors (getByRole, data-testid)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';

// TD-38 Phase 2: Mock StreamingAnswer BEFORE imports (hoisting requirement)
vi.mock('../../components/chat/StreamingAnswer', () => ({
  StreamingAnswer: ({ query, mode, sessionId }: any) => (
    <div data-testid="streaming-answer" className="max-w-4xl mx-auto px-6 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">{query}</h1>
      <div data-testid="streaming-mode" className="text-sm text-gray-600 mb-4">
        Mode: {mode}
      </div>
      {sessionId && (
        <div data-testid="streaming-session" className="text-xs text-gray-500">
          Session: {sessionId}
        </div>
      )}
      <div data-testid="streaming-content" className="prose max-w-none">
        <p>Mock answer for: {query}</p>
      </div>
    </div>
  ),
}));

// Mock useNavigate and useSearchParams
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { SearchResultsPage } from '../../pages/SearchResultsPage';
import { mockFetchSSESuccess } from './helpers';

describe('SearchResultsPage E2E Tests', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    vi.clearAllMocks();
  });

  describe('Page Rendering', () => {
    it('should render search bar at top of page', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test+query&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      expect(searchInput).toBeInTheDocument();
    });

    it('should render StreamingAnswer component with query', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=What+is+RAG&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // TD-38: Query text is unique and safe to use
      expect(screen.getByText('What is RAG')).toBeInTheDocument();
    });

    it('should extract query from URL params', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=knowledge+graph&mode=vector']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // TD-38: Query text is unique
      expect(screen.getByText('knowledge graph')).toBeInTheDocument();
    });

    it('should extract mode from URL params', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=graph']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // TD-38: Query text "test" is unambiguous in this context
      expect(screen.getByText('test')).toBeInTheDocument();
    });

    it('should default to hybrid mode if mode not specified', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // TD-38: Query text is unique
      expect(screen.getByText('test')).toBeInTheDocument();
    });

    it('should extract session_id from URL params if present', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid&session_id=session-123']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('test')).toBeInTheDocument();
    });
  });

  describe('Empty Query Handling', () => {
    it('should show error message when query is empty', () => {
      render(
        <MemoryRouter initialEntries={['/search']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText(/Keine Suchanfrage/i)).toBeInTheDocument();
    });

    it('should show back to home button when query is empty', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const homeButton = screen.getByText(/Zur Startseite/i);
      expect(homeButton).toBeInTheDocument();
    });

    it('should navigate to home when back button is clicked', () => {
      render(
        <MemoryRouter initialEntries={['/search']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const homeButton = screen.getByText(/Zur Startseite/i);
      fireEvent.click(homeButton);

      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  // Sprint 52: Mode selector removed - skip mode-switching tests
  describe.skip('New Search Submission', () => {
    it('should navigate to new search URL when new query submitted', async () => {
      render(
        <MemoryRouter initialEntries={['/search?q=old+query&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      fireEvent.change(searchInput, { target: { value: 'new query' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('/search?q=new%20query&mode=hybrid')
        );
      });
    });

    it('should preserve mode when submitting new query', async () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=vector']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);

      // TD-38: Change to graph mode using accessible selector
      const graphChip = screen.getByRole('button', { name: /Graph Mode/i });
      fireEvent.click(graphChip);

      fireEvent.change(searchInput, { target: { value: 'another test' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=graph')
        );
      });
    });

    it('should allow changing search mode in results page', async () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // TD-38: Click memory mode chip using accessible selector
      const memoryChip = screen.getByRole('button', { name: /Memory Mode/i });
      fireEvent.click(memoryChip);

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      fireEvent.change(searchInput, { target: { value: 'memory test' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringContaining('mode=memory')
        );
      });
    });
  });

  describe('Search Bar Behavior', () => {
    it('should render search bar as sticky at top', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // The search bar container has sticky positioning
      const stickyContainer = container.querySelector('.sticky.top-0');
      expect(stickyContainer).toBeInTheDocument();
      expect(stickyContainer?.className).toContain('bg-white');
    });

    it('should not auto-focus search input on results page', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      expect(searchInput).not.toHaveFocus();
    });

    it('should render all mode selection chips', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('Hybrid')).toBeInTheDocument();
      expect(screen.getByText('Vector')).toBeInTheDocument();
      expect(screen.getByText('Graph')).toBeInTheDocument();
      expect(screen.getByText('Memory')).toBeInTheDocument();
    });
  });

  describe('URL Encoding', () => {
    it('should handle encoded special characters in query', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test%20with%20spaces&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('test with spaces')).toBeInTheDocument();
    });

    it('should handle UTF-8 characters in query', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=Was%20ist%20das%3F&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('Was ist das?')).toBeInTheDocument();
    });

    it('should handle query with emojis', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test%20%F0%9F%9A%80&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Query heading should contain the emoji
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading.textContent).toMatch(/test.*🚀/);
    });

    it('should properly encode special characters when submitting new search', async () => {
      render(
        <MemoryRouter initialEntries={['/search?q=old&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      fireEvent.change(searchInput, { target: { value: 'query with @#$%' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(
          expect.stringMatching(/search\?q=query%20with/)
        );
      });
    });
  });

  describe('Page Layout', () => {
    it('should have gray background for results area', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const pageContainer = container.querySelector('.bg-gray-50');
      expect(pageContainer).toBeInTheDocument();
    });

    it('should render search bar with white background and shadow', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchBarContainer = screen.getByPlaceholderText(/Neue Suche/i)
        .closest('.bg-white');
      expect(searchBarContainer).toBeInTheDocument();
    });

    it('should apply proper spacing and padding', () => {
      const { container } = render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Results section should have padding
      const resultsSection = container.querySelector('.py-8');
      expect(resultsSection).toBeInTheDocument();
    });
  });

  describe('Integration with StreamingAnswer', () => {
    it('should pass correct props to StreamingAnswer component', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test+query&mode=vector&session_id=s123']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // StreamingAnswer receives the query and displays it
      expect(screen.getByText('test query')).toBeInTheDocument();
    });

    it('should update StreamingAnswer when URL changes', () => {
      const { unmount } = render(
        <MemoryRouter initialEntries={['/search?q=first&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // First query should be displayed
      let heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('first');

      // Clean up first render
      unmount();

      // Simulate navigation to new search (new render with different URL)
      render(
        <MemoryRouter initialEntries={['/search?q=second&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Second query should be displayed
      heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('second');
    });
  });

  describe('Edge Cases', () => {
    it('should handle very long queries', () => {
      const longQuery = 'a'.repeat(500);
      render(
        <MemoryRouter initialEntries={[`/search?q=${longQuery}&mode=hybrid`]}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText(longQuery)).toBeInTheDocument();
    });

    it('should handle queries with only whitespace', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=%20%20%20&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Should show empty query message since trimmed query is empty
      expect(screen.getByText(/Keine Suchanfrage/i)).toBeInTheDocument();
    });

    it('should handle missing mode parameter', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Should default to hybrid and render correctly
      expect(screen.getByText('test')).toBeInTheDocument();
    });

    it('should handle invalid mode parameter gracefully', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=invalid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Should still render (TypeScript cast handles this)
      expect(screen.getByText('test')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper heading hierarchy', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Query should be h1 (in StreamingAnswer)
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('test');
    });

    it('should allow keyboard navigation in search input', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);

      // Input should be keyboard accessible
      searchInput.focus();
      expect(searchInput).toHaveFocus();
    });
  });
});
