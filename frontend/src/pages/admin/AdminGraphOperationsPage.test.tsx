/**
 * AdminGraphOperationsPage Component Tests
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AdminGraphOperationsPage } from './AdminGraphOperationsPage';
import * as graphOperationsApi from '../../api/graphOperations';
import type { GraphOperationsStats, NamespaceInfo } from '../../api/graphOperations';

// Mock the API
vi.mock('../../api/graphOperations', () => ({
  fetchGraphOperationsStats: vi.fn(),
  fetchNamespaces: vi.fn(),
}));

// Mock useAuth hook
const mockAuthContext = {
  isAuthenticated: true,
  user: { username: 'admin', email: 'admin@test.com' },
  login: vi.fn(),
  logout: vi.fn(),
  isLoading: false,
};

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => mockAuthContext,
}));

// Helper: Create mock stats
function createMockStats(): GraphOperationsStats {
  return {
    total_entities: 1500,
    total_relationships: 3200,
    entity_types: { PERSON: 500, ORGANIZATION: 400, LOCATION: 300, EVENT: 200, PRODUCT: 100 },
    relationship_types: { RELATES_TO: 2000, MENTIONED_IN: 1000, CO_OCCURS: 200 },
    community_count: 92,
    community_sizes: [45, 30, 20, 15, 10, 8, 5, 5, 4, 3],
    orphan_nodes: 50,
    avg_degree: 4.27,
    summary_status: {
      generated: 80,
      pending: 12,
    },
    graph_health: 'healthy',
    timestamp: '2026-01-08T10:30:00Z',
  };
}

// Helper: Create mock namespaces
function createMockNamespaces(): NamespaceInfo[] {
  return [
    {
      namespace_id: 'default',
      namespace_type: 'general',
      document_count: 100,
      description: 'Default namespace',
    },
    {
      namespace_id: 'hotpotqa_large',
      namespace_type: 'qa',
      document_count: 50,
      description: 'HotpotQA dataset',
    },
  ];
}

describe('AdminGraphOperationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthContext.isAuthenticated = true;
    (graphOperationsApi.fetchGraphOperationsStats as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockStats()
    );
    (graphOperationsApi.fetchNamespaces as ReturnType<typeof vi.fn>).mockResolvedValue({
      namespaces: createMockNamespaces(),
      total_count: 2,
    });
  });

  const renderPage = () => {
    return render(
      <BrowserRouter>
        <AdminGraphOperationsPage />
      </BrowserRouter>
    );
  };

  describe('authentication', () => {
    it('should show unauthorized message when not authenticated', () => {
      mockAuthContext.isAuthenticated = false;

      renderPage();

      expect(screen.getByTestId('unauthorized-message')).toBeInTheDocument();
      expect(screen.getByText('Access Denied')).toBeInTheDocument();
      expect(
        screen.getByText('You need to be logged in to access the Admin Graph Operations page.')
      ).toBeInTheDocument();
    });

    it('should show login link when not authenticated', () => {
      mockAuthContext.isAuthenticated = false;

      renderPage();

      const loginLink = screen.getByRole('link', { name: 'Go to Login' });
      expect(loginLink).toHaveAttribute('href', '/login');
    });
  });

  describe('page layout', () => {
    it('should render page header with title', async () => {
      renderPage();

      expect(screen.getByText('Graph Operations')).toBeInTheDocument();
      expect(screen.getByText('Manage knowledge graph maintenance tasks')).toBeInTheDocument();
    });

    it('should render back to admin link', () => {
      renderPage();

      const backLink = screen.getByRole('link', { name: /Back to Admin/i });
      expect(backLink).toHaveAttribute('href', '/admin');
    });

    it('should render both cards', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId('graph-statistics-card')).toBeInTheDocument();
      });
      expect(screen.getByTestId('community-operations-card')).toBeInTheDocument();
    });
  });

  describe('data loading', () => {
    it('should fetch stats on mount', async () => {
      renderPage();

      await waitFor(() => {
        expect(graphOperationsApi.fetchGraphOperationsStats).toHaveBeenCalledTimes(1);
      });
    });

    it('should fetch namespaces on mount', async () => {
      renderPage();

      await waitFor(() => {
        expect(graphOperationsApi.fetchNamespaces).toHaveBeenCalledTimes(1);
      });
    });

    it('should display stats after loading', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId('graph-statistics-card')).toBeInTheDocument();
        // Check that stats are displayed (via stat-entities test id)
        // Use regex to handle locale differences (1,500 or 1.500)
        expect(screen.getByTestId('stat-entities')).toHaveTextContent(/1[,.]?500/);
      });
    });

    it('should show loading state initially', () => {
      // Make API calls take time
      (graphOperationsApi.fetchGraphOperationsStats as ReturnType<typeof vi.fn>).mockImplementation(
        () => new Promise(() => {})
      );

      renderPage();

      expect(screen.getByTestId('graph-statistics-loading')).toBeInTheDocument();
    });
  });

  describe('error handling', () => {
    it('should handle stats API error gracefully', async () => {
      (graphOperationsApi.fetchGraphOperationsStats as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Failed to fetch stats')
      );

      renderPage();

      await waitFor(() => {
        expect(screen.getByTestId('graph-statistics-error')).toBeInTheDocument();
      });
    });

    it('should handle namespace API error gracefully (no crash)', async () => {
      (graphOperationsApi.fetchNamespaces as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Failed to fetch namespaces')
      );

      renderPage();

      // Should still render the page without crashing
      await waitFor(() => {
        expect(screen.getByTestId('community-operations-card')).toBeInTheDocument();
      });

      // Namespace selector should still be there, just empty
      expect(screen.getByTestId('namespace-selector')).toBeInTheDocument();
    });
  });

  describe('about section', () => {
    it('should render About Graph Operations section', () => {
      renderPage();

      expect(screen.getByText('About Graph Operations')).toBeInTheDocument();
      expect(screen.getByText('Community Detection')).toBeInTheDocument();
      expect(screen.getByText('Summary Generation')).toBeInTheDocument();
      expect(screen.getByText('Graph-Global Mode')).toBeInTheDocument();
    });
  });
});
