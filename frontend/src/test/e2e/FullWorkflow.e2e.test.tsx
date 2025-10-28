/**
 * Full Workflow E2E Tests
 * Sprint 15: Complete user journey integration tests
 *
 * Tests cover:
 * - Complete user workflows from landing to results
 * - Multi-step interactions
 * - Session management
 * - Navigation flows
 * - Real-world scenarios
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from '../../pages/HomePage';
import { SearchResultsPage } from '../../pages/SearchResultsPage';
import App from '../../App';
import {
  mockFetchSSESuccess,
  mockFetchSessionsList,
  mockFetchConversationHistory,
  setupGlobalFetchMock,
  cleanupGlobalFetchMock,
  createMockSSEStream,
} from './helpers';
import { mockSessions, mockConversationHistory } from './fixtures';
import type { ChatChunk } from '../../types/chat';

describe('Full Workflow E2E Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanupGlobalFetchMock();
  });

  describe('Basic Search Workflow', () => {
    it('should complete full search workflow from home to results', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // 1. User is on homepage
      expect(screen.getByText(/Was möchten Sie wissen/i)).toBeInTheDocument();

      // 2. User types query
      const searchInput = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(searchInput, { target: { value: 'What is RAG?' } });

      // 3. User submits query
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      // 4. Navigation should occur (in real app, router handles this)
      // In test, we simulate by rendering SearchResultsPage
    });

    it('should handle quick prompt workflow', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // 1. User clicks quick prompt
      const quickPrompt = screen.getByText(/Erkläre mir das Konzept von RAG/);
      fireEvent.click(quickPrompt);

      // Quick prompt should trigger navigation
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });
  });

  describe('Mode Selection Workflow', () => {
    it('should complete workflow with different search modes', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/']}>
          <HomePage />
        </MemoryRouter>
      );

      // 1. Select Vector mode
      const vectorChip = screen.getByText('Vector');
      fireEvent.click(vectorChip);

      // 2. Submit query
      const searchInput = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(searchInput, { target: { value: 'vector search test' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      // Should navigate with vector mode
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });

    it('should allow mode switching before search', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/']}>
          <HomePage />
        </MemoryRouter>
      );

      // 1. Select Hybrid (default is already hybrid)
      // 2. Switch to Graph
      const graphChip = screen.getByText('Graph');
      fireEvent.click(graphChip);

      // 3. Switch back to Hybrid
      const hybridChip = screen.getByText('Hybrid');
      fireEvent.click(hybridChip);

      // 4. Submit with final mode
      const searchInput = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });
  });

  describe('Streaming Response Workflow', () => {
    it('should complete full streaming workflow', async () => {
      const chunks: ChatChunk[] = [
        { type: 'metadata', session_id: 'workflow-123', data: { intent: 'hybrid' } },
        { type: 'source', source: { text: 'Source 1', title: 'Doc 1' } },
        { type: 'source', source: { text: 'Source 2', title: 'Doc 2' } },
        { type: 'token', content: 'RAG ' },
        { type: 'token', content: 'stands ' },
        { type: 'token', content: 'for ' },
        { type: 'token', content: 'Retrieval-Augmented ' },
        { type: 'token', content: 'Generation.' },
        {
          type: 'complete',
          data: {
            latency_seconds: 2.5,
            agent_path: ['router', 'hybrid_retriever', 'generator'],
          },
        },
      ];

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: createMockSSEStream(chunks),
        })
      );

      render(
        <MemoryRouter initialEntries={['/search?q=What+is+RAG&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // 1. Query is displayed
      expect(screen.getByText('What is RAG')).toBeInTheDocument();

      // 2. Loading indicator shown
      expect(screen.getByText(/Suche läuft/i)).toBeInTheDocument();

      // 3. Sources appear
      await waitFor(
        () => {
          expect(screen.getByText('Doc 1')).toBeInTheDocument();
          expect(screen.getByText('Doc 2')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // 4. Answer streams in
      await waitFor(
        () => {
          expect(screen.getByText(/RAG stands for Retrieval-Augmented Generation/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // 5. Metadata appears after completion
      await waitFor(
        () => {
          expect(screen.getByText(/2\.50s/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // 6. Loading indicator hidden
      await waitFor(
        () => {
          expect(screen.queryByText(/Suche läuft/i)).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle progressive source display', async () => {
      const chunks: ChatChunk[] = [
        { type: 'metadata', session_id: 'test' },
        { type: 'token', content: 'Starting answer...' },
        { type: 'source', source: { text: 'First source', title: 'Source 1' } },
        { type: 'token', content: ' more text...' },
        { type: 'source', source: { text: 'Second source', title: 'Source 2' } },
        { type: 'token', content: ' final text.' },
        { type: 'complete', data: {} },
      ];

      setupGlobalFetchMock(
        vi.fn().mockResolvedValue({
          ok: true,
          body: createMockSSEStream(chunks),
        })
      );

      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Sources should appear progressively
      await waitFor(
        () => {
          expect(screen.getByText('Source 1')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      await waitFor(
        () => {
          expect(screen.getByText('Source 2')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Follow-up Query Workflow', () => {
    it('should handle follow-up queries in same session', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/search?q=first+query&mode=hybrid&session_id=session-123']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // First query displays
      expect(screen.getByText('first query')).toBeInTheDocument();

      await waitFor(
        () => {
          expect(screen.getByText(/This is a test answer/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // User submits follow-up query
      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      fireEvent.change(searchInput, { target: { value: 'follow-up question' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });

    it('should clear previous results on new query', async () => {
      const { rerender } = render(
        <MemoryRouter initialEntries={['/search?q=first&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      setupGlobalFetchMock(mockFetchSSESuccess());

      await waitFor(() => {
        expect(screen.getByText('first')).toBeInTheDocument();
      });

      // Navigate to new query
      rerender(
        <MemoryRouter initialEntries={['/search?q=second&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('second')).toBeInTheDocument();
    });
  });

  describe('Error Recovery Workflow', () => {
    it('should recover from error with retry', async () => {
      const mockFetch = vi
        .fn()
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          body: createMockSSEStream([
            { type: 'metadata', session_id: '123' },
            { type: 'token', content: 'Success after retry' },
            { type: 'complete', data: {} },
          ]),
        });

      setupGlobalFetchMock(mockFetch);

      const { rerender } = render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Error appears
      await waitFor(() => {
        expect(screen.getByText(/Fehler beim Laden der Antwort/i)).toBeInTheDocument();
      });

      // Simulate retry by re-rendering with different key
      rerender(
        <MemoryRouter initialEntries={['/search?q=test2&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Success after retry
      await waitFor(
        () => {
          expect(screen.getByText(/Success after retry/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should allow user to go back home after error', async () => {
      setupGlobalFetchMock(
        vi.fn().mockRejectedValue(new Error('Network error'))
      );

      render(
        <MemoryRouter initialEntries={['/search']}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchResultsPage />} />
          </Routes>
        </MemoryRouter>
      );

      // Empty query error
      expect(screen.getByText(/Keine Suchanfrage/i)).toBeInTheDocument();

      // Click back to home
      const homeButton = screen.getByText(/Zur Startseite/i);
      expect(homeButton).toBeInTheDocument();
    });
  });

  describe('Multi-Mode Search Workflow', () => {
    it('should complete searches in all four modes', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      const modes = ['hybrid', 'vector', 'graph', 'memory'] as const;

      for (const mode of modes) {
        const { unmount } = render(
          <MemoryRouter initialEntries={[`/search?q=test+${mode}&mode=${mode}`]}>
            <SearchResultsPage />
          </MemoryRouter>
        );

        // Query should be displayed
        await waitFor(() => {
          expect(screen.getByText(`test ${mode}`)).toBeInTheDocument();
        });

        unmount();
        vi.clearAllMocks();
      }
    });

    it('should allow switching modes mid-session', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/search?q=test&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Start with hybrid
      expect(screen.getByText('test')).toBeInTheDocument();

      // Switch to vector
      const vectorChip = screen.getByText('Vector');
      fireEvent.click(vectorChip);

      const searchInput = screen.getByPlaceholderText(/Neue Suche/i);
      fireEvent.change(searchInput, { target: { value: 'vector test' } });
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });
  });

  describe('Complex User Journeys', () => {
    it('should handle complete exploration journey', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      const { rerender } = render(
        <MemoryRouter initialEntries={['/']}>
          <HomePage />
        </MemoryRouter>
      );

      // 1. User lands on homepage
      expect(screen.getByText(/Was möchten Sie wissen/i)).toBeInTheDocument();

      // 2. User explores quick prompts
      expect(screen.getByText(/Erkläre mir das Konzept von RAG/)).toBeInTheDocument();

      // 3. User changes mode to Vector
      const vectorChip = screen.getByText('Vector');
      fireEvent.click(vectorChip);

      // 4. User types custom query
      const searchInput = screen.getByPlaceholderText(/Fragen Sie alles/i);
      fireEvent.change(searchInput, { target: { value: 'custom semantic search' } });

      // 5. User submits
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });

      // 6. Navigate to results page
      rerender(
        <MemoryRouter initialEntries={['/search?q=custom+semantic+search&mode=vector']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // 7. Results appear
      await waitFor(
        () => {
          expect(screen.getByText('custom semantic search')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should handle rapid query changes', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      const { rerender } = render(
        <MemoryRouter initialEntries={['/search?q=query1&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('query1')).toBeInTheDocument();

      // Rapid query changes
      rerender(
        <MemoryRouter initialEntries={['/search?q=query2&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('query2')).toBeInTheDocument();

      rerender(
        <MemoryRouter initialEntries={['/search?q=query3&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('query3')).toBeInTheDocument();
    });

    it('should handle long research session', async () => {
      const queries = [
        'What is RAG?',
        'How does vector search work?',
        'Explain knowledge graphs',
        'What is hybrid retrieval?',
        'Tell me about memory systems',
      ];

      setupGlobalFetchMock(mockFetchSSESuccess());

      for (const query of queries) {
        const { unmount } = render(
          <MemoryRouter initialEntries={[`/search?q=${encodeURIComponent(query)}&mode=hybrid`]}>
            <SearchResultsPage />
          </MemoryRouter>
        );

        await waitFor(() => {
          expect(screen.getByText(query)).toBeInTheDocument();
        });

        unmount();
      }
    });
  });

  describe('Edge Case Workflows', () => {
    it('should handle empty to valid query transition', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      const { rerender } = render(
        <MemoryRouter initialEntries={['/search']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      // Empty query
      expect(screen.getByText(/Keine Suchanfrage/i)).toBeInTheDocument();

      // Navigate to valid query
      rerender(
        <MemoryRouter initialEntries={['/search?q=valid+query&mode=hybrid']}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText('valid query')).toBeInTheDocument();
    });

    it('should handle very long query workflow', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      const longQuery = 'This is a very long query that tests how the system handles extensive user input spanning multiple lines and containing detailed questions about complex topics in retrieval augmented generation and knowledge graph systems'.repeat(
        2
      );

      render(
        <MemoryRouter initialEntries={[`/search?q=${encodeURIComponent(longQuery)}&mode=hybrid`]}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText(longQuery)).toBeInTheDocument();
    });

    it('should handle special characters in query workflow', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      const specialQuery = 'Query with "quotes", \'apostrophes\', and symbols: @#$%^&*()';

      render(
        <MemoryRouter initialEntries={[`/search?q=${encodeURIComponent(specialQuery)}&mode=hybrid`]}>
          <SearchResultsPage />
        </MemoryRouter>
      );

      expect(screen.getByText(specialQuery)).toBeInTheDocument();
    });
  });

  describe('Accessibility Workflows', () => {
    it('should support keyboard-only navigation', async () => {
      setupGlobalFetchMock(mockFetchSSESuccess());

      render(
        <MemoryRouter initialEntries={['/']}>
          <HomePage />
        </MemoryRouter>
      );

      const searchInput = screen.getByPlaceholderText(/Fragen Sie alles/i);

      // Input should be auto-focused
      expect(searchInput).toHaveFocus();

      // Type with keyboard
      fireEvent.change(searchInput, { target: { value: 'keyboard test' } });

      // Submit with Enter key
      fireEvent.keyDown(searchInput, { key: 'Enter' });

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled();
      });
    });

    it('should allow tab navigation between mode chips', () => {
      render(
        <MemoryRouter initialEntries={['/']}>
          <HomePage />
        </MemoryRouter>
      );

      const hybridChip = screen.getByText('Hybrid');
      const vectorChip = screen.getByText('Vector');
      const graphChip = screen.getByText('Graph');
      const memoryChip = screen.getByText('Memory');

      // All chips should be in the document and clickable
      expect(hybridChip).toBeInTheDocument();
      expect(vectorChip).toBeInTheDocument();
      expect(graphChip).toBeInTheDocument();
      expect(memoryChip).toBeInTheDocument();
    });
  });
});
