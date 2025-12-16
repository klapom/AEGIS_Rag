/**
 * IndexingSection Component Tests
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { IndexingSection } from './IndexingSection';
import * as adminApi from '../../api/admin';
import type { SystemStats } from '../../types/admin';

// Mock the admin API
vi.mock('../../api/admin', () => ({
  getSystemStats: vi.fn(),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Helper: Create mock SystemStats
function createMockStats(overrides?: Partial<SystemStats>): SystemStats {
  return {
    qdrant_total_chunks: 450,
    qdrant_collection_name: 'documents',
    qdrant_vector_dimension: 1024,
    bm25_corpus_size: 100,
    neo4j_total_entities: 500,
    neo4j_total_relations: 1200,
    last_reindex_timestamp: '2024-12-15T10:30:00Z',
    embedding_model: 'BAAI/bge-m3',
    total_conversations: 50,
    ...overrides,
  };
}

describe('IndexingSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockResolvedValue(createMockStats());
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <IndexingSection />
      </BrowserRouter>
    );
  };

  describe('loading state', () => {
    it('should show loading state initially', () => {
      // Don't resolve the promise immediately
      (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise(() => {})
      );

      renderComponent();

      expect(screen.getByTestId('admin-section-loading')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('should show error message when API fails', async () => {
      (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Failed to fetch stats')
      );

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-section-error')).toBeInTheDocument();
      });
      expect(screen.getByText('Failed to fetch stats')).toBeInTheDocument();
    });
  });

  describe('stats display', () => {
    it('should display document count', async () => {
      renderComponent();

      await waitFor(() => {
        // The count appears in multiple places (indexed count and Qdrant stat)
        const elements = screen.getAllByText('450');
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it('should display quick stats for Qdrant, Neo4j, and BM25', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('quick-stat-qdrant')).toBeInTheDocument();
        expect(screen.getByTestId('quick-stat-neo4j')).toBeInTheDocument();
        expect(screen.getByTestId('quick-stat-bm25')).toBeInTheDocument();
      });
    });

    it('should display last reindex timestamp', async () => {
      renderComponent();

      await waitFor(() => {
        // German locale format: 15.12.2024, 11:30
        expect(screen.getByText(/15\.12\.2024/)).toBeInTheDocument();
      });
    });

    it('should display "Never" when no last reindex timestamp', async () => {
      (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockResolvedValue(
        createMockStats({ last_reindex_timestamp: null })
      );

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Never')).toBeInTheDocument();
      });
    });
  });

  describe('navigation', () => {
    it('should navigate to indexing page on Index Dir button click', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('index-directory-button')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('index-directory-button'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/indexing');
    });

    it('should navigate to indexing page on status card click', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('indexing-status-card')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('indexing-status-card'));

      expect(mockNavigate).toHaveBeenCalledWith('/admin/indexing');
    });

    it('should navigate on Enter key press', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('indexing-status-card')).toBeInTheDocument();
      });

      const card = screen.getByTestId('indexing-status-card');
      fireEvent.keyDown(card, { key: 'Enter' });

      expect(mockNavigate).toHaveBeenCalled();
    });
  });

  describe('section header', () => {
    it('should display Indexing title', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('Indexing')).toBeInTheDocument();
      });
    });

    it('should render Index Dir button', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('index-directory-button')).toBeInTheDocument();
        expect(screen.getByText('Index Dir')).toBeInTheDocument();
      });
    });
  });
});
