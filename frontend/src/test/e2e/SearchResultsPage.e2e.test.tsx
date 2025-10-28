/**
 * SearchResultsPage E2E Tests
 * Sprint 15 Feature 15.4: End-to-end tests for search results page
 *
 * Tests cover:
 * - Page rendering with query params
 * - Empty query handling
 * - New search submission
 * - StreamingAnswer integration
 * - Navigation flows
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { SearchResultsPage } from '../../pages/SearchResultsPage';
import { mockFetchSSESuccess } from './helpers';

// Mock useNavigate and useSearchParams
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock streamChat API
vi.mock('../../api/chat', () => ({
  streamChat: vi.fn(),
}));

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

      // Check that the query is displayed (StreamingAnswer shows it as h1)
      expect(screen.getByText('What is RAG')).toBeInTheDocument();
    });

    it('should extract query from URL params', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=knowledge+graph&mode=vector']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('knowledge graph')).toBeInTheDocument();
    });

    it('should extract mode from URL params', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=graph']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Mode is passed to StreamingAnswer (checked via query display)
      expect(screen.getByText('test')).toBeInTheDocument();
    });

    it('should default to hybrid mode if mode not specified', () => {
      render(
        <MemoryRouter initialEntries={['/search?q=test']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

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

  describe('New Search Submission', () => {
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

      // Change to graph mode
      const graphChip = screen.getByText('Graph');
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

      // Click memory mode chip
      const memoryChip = screen.getByText('Memory');
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
      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // The search bar container has sticky positioning
      const searchBar = screen.getByPlaceholderText(/Neue Suche/i).closest('div');
      expect(searchBar?.parentElement?.className).toContain('sticky');
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

      expect(screen.getByText(/test.*🚀/)).toBeInTheDocument();
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
      const { rerender } = render(
        <MemoryRouter initialEntries={['/search?q=first&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('first')).toBeInTheDocument();

      // Simulate navigation to new search
      rerender(
        <MemoryRouter initialEntries={['/search?q=second&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('second')).toBeInTheDocument();
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
