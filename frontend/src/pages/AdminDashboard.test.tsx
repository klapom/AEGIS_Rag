/**
 * AdminDashboard Page Tests
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AdminDashboard } from './AdminDashboard';
import * as adminApi from '../api/admin';
import type { SystemStats } from '../types/admin';

// Mock the admin API
vi.mock('../api/admin', () => ({
  getSystemStats: vi.fn(),
}));

// Mock the useDomains hook
vi.mock('../hooks/useDomainTraining', () => ({
  useDomains: () => ({
    data: [
      { id: '1', name: 'omnitracker', description: 'Test', llm_model: 'qwen3:32b', status: 'ready' },
      { id: '2', name: 'legal', description: 'Legal', llm_model: null, status: 'training' },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Helper: Create mock SystemStats
function createMockStats(): SystemStats {
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
  };
}

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.getSystemStats as ReturnType<typeof vi.fn>).mockResolvedValue(createMockStats());
    localStorageMock.getItem.mockReturnValue(null);
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <AdminDashboard />
      </BrowserRouter>
    );
  };

  describe('page structure', () => {
    it('should render the admin dashboard container', async () => {
      renderComponent();

      expect(screen.getByTestId('admin-dashboard')).toBeInTheDocument();
    });

    it('should display page title', async () => {
      renderComponent();

      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    });

    it('should display page description', async () => {
      renderComponent();

      expect(
        screen.getByText('Manage domains, indexing, and system configuration')
      ).toBeInTheDocument();
    });
  });

  describe('sections', () => {
    it('should render DomainSection', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-domain-section')).toBeInTheDocument();
      });
    });

    it('should render IndexingSection', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-indexing-section')).toBeInTheDocument();
      });
    });

    it('should render SettingsSection', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-settings-section')).toBeInTheDocument();
      });
    });

    it('should display domains in DomainSection when expanded', async () => {
      renderComponent();

      // DomainSection is collapsed by default, need to expand it
      await waitFor(() => {
        expect(screen.getByTestId('admin-domain-section')).toBeInTheDocument();
      });

      // Click the section header to expand it
      const sectionHeader = screen.getByTestId('admin-domain-section').querySelector('[role="button"]');
      if (sectionHeader) {
        fireEvent.click(sectionHeader);
      }

      await waitFor(() => {
        expect(screen.getByText('omnitracker')).toBeInTheDocument();
        expect(screen.getByText('legal')).toBeInTheDocument();
      });
    });

    it('should have DomainSection collapsed by default', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-domain-section')).toBeInTheDocument();
      });

      // The section content should not be visible when collapsed
      // Check that the aria-expanded is false on the header button
      const sectionHeader = screen.getByTestId('admin-domain-section').querySelector('[role="button"]');
      expect(sectionHeader).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('navigation bar', () => {
    it('should render navigation bar at top', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-navigation-bar')).toBeInTheDocument();
      });
    });

    it('should render all navigation links', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-nav-graph')).toBeInTheDocument();
        expect(screen.getByTestId('admin-nav-costs')).toBeInTheDocument();
        expect(screen.getByTestId('admin-nav-llm')).toBeInTheDocument();
        expect(screen.getByTestId('admin-nav-health')).toBeInTheDocument();
        expect(screen.getByTestId('admin-nav-training')).toBeInTheDocument();
        expect(screen.getByTestId('admin-nav-indexing')).toBeInTheDocument();
      });
    });

    it('should have correct href for navigation links', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('admin-nav-graph')).toHaveAttribute('href', '/admin/graph');
        expect(screen.getByTestId('admin-nav-costs')).toHaveAttribute('href', '/admin/costs');
        expect(screen.getByTestId('admin-nav-llm')).toHaveAttribute('href', '/admin/llm-config');
        expect(screen.getByTestId('admin-nav-health')).toHaveAttribute('href', '/admin/health');
        expect(screen.getByTestId('admin-nav-training')).toHaveAttribute(
          'href',
          '/admin/domain-training'
        );
        expect(screen.getByTestId('admin-nav-indexing')).toHaveAttribute('href', '/admin/indexing');
      });
    });
  });

  describe('data display', () => {
    it('should display document counts from IndexingSection', async () => {
      renderComponent();

      await waitFor(() => {
        // Look for the document count in the indexing section (appears multiple times)
        const elements = screen.getAllByText('450');
        expect(elements.length).toBeGreaterThan(0);
      });
    });

    it('should display embedding model from SettingsSection', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('bge-m3')).toBeInTheDocument();
      });
    });
  });

  describe('accessibility', () => {
    it('should have proper heading structure', async () => {
      renderComponent();

      const mainHeading = screen.getByRole('heading', { level: 1 });
      expect(mainHeading).toHaveTextContent('Admin Dashboard');
    });

    it('should have section headings', async () => {
      renderComponent();

      await waitFor(() => {
        // Each AdminSection has an h2
        const sectionHeadings = screen.getAllByRole('heading', { level: 2 });
        expect(sectionHeadings.length).toBeGreaterThanOrEqual(3);
      });
    });
  });
});
