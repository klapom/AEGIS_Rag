/**
 * GraphAnalyticsPage URL Persistence Tests
 * Sprint 116 Feature 116.8: Edge Filter URL Persistence
 *
 * Tests URL parameter parsing and persistence for edge filters.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { GraphAnalyticsPage } from './GraphAnalyticsPage';

// Mock the hooks and API calls
vi.mock('../../hooks/useGraphStatistics', () => ({
  useGraphStatistics: () => ({
    stats: {
      node_count: 100,
      edge_count: 200,
      community_count: 10,
      avg_degree: 2.0,
      entity_type_distribution: { PERSON: 50, ORGANIZATION: 30, LOCATION: 20 },
      orphaned_nodes: 5,
      timestamp: '2024-01-01T00:00:00Z',
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../../hooks/useCommunities', () => ({
  useCommunities: () => ({
    communities: [],
    loading: false,
  }),
}));

vi.mock('../../api/admin', () => ({
  fetchGraphStats: vi.fn().mockResolvedValue({
    total_entities: 100,
    total_relationships: 200,
    community_count: 10,
    orphan_nodes: 5,
    graph_health: 'healthy',
    entity_types: { PERSON: 50, ORGANIZATION: 30 },
    relationship_types: { RELATES_TO: 100, CO_OCCURS: 80 },
    community_sizes: [10, 8, 6],
    summary_status: { generated: 8, pending: 2 },
    avg_degree: 2.0,
    timestamp: '2024-01-01T00:00:00Z',
  }),
}));

// Mock GraphViewer component
vi.mock('../../components/graph/GraphViewer', () => ({
  GraphViewer: ({ edgeFilters }: { edgeFilters: any }) => (
    <div data-testid="graph-viewer" data-edge-filters={JSON.stringify(edgeFilters)}>
      Mock Graph Viewer
    </div>
  ),
}));

// Mock GraphFilters component
vi.mock('../../components/graph/GraphFilters', () => ({
  GraphFilters: ({ edgeFilters, onEdgeFilterChange }: any) => (
    <div data-testid="graph-filters">
      <button
        data-testid="toggle-relates-to"
        onClick={() =>
          onEdgeFilterChange({
            ...edgeFilters,
            showRelatesTo: !edgeFilters.showRelatesTo,
          })
        }
      >
        Toggle RELATES_TO
      </button>
      <button
        data-testid="set-weight"
        onClick={() =>
          onEdgeFilterChange({
            ...edgeFilters,
            minWeight: 0.5,
          })
        }
      >
        Set Weight 0.5
      </button>
    </div>
  ),
}));

// Mock other components
vi.mock('../../components/graph/CommunityHighlight', () => ({
  CommunityHighlight: () => <div>Mock Community Highlight</div>,
}));

vi.mock('../../components/graph/GraphExportButton', () => ({
  GraphExportButton: () => <div>Mock Export Button</div>,
}));

vi.mock('../../components/admin/SectionCommunitiesDialog', () => ({
  SectionCommunitiesDialog: () => <div>Mock Section Dialog</div>,
}));

vi.mock('../../components/admin/CommunityComparisonDialog', () => ({
  CommunityComparisonDialog: () => <div>Mock Comparison Dialog</div>,
}));

describe('GraphAnalyticsPage - URL Persistence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('parses edge filters from URL parameters on mount', async () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/admin/graph?showRelatesTo=false&showCoOccurs=true&minWeight=0.3',
        ]}
      >
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      expect(edgeFilters.showRelatesTo).toBe(false);
      expect(edgeFilters.showCoOccurs).toBe(true);
      expect(edgeFilters.minWeight).toBe(0.3);
    });
  });

  it('defaults to all edge types enabled when no URL params', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/graph']}>
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      expect(edgeFilters.showRelatesTo).toBe(true);
      expect(edgeFilters.showCoOccurs).toBe(true);
      expect(edgeFilters.showMentionedIn).toBe(true);
      expect(edgeFilters.minWeight).toBe(0);
    });
  });

  it('parses extended edge types from URL', async () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/admin/graph?showHasSection=true&showDefines=false&showBelongsTo=true',
        ]}
      >
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      expect(edgeFilters.showHasSection).toBe(true);
      expect(edgeFilters.showDefines).toBe(false);
      expect(edgeFilters.showBelongsTo).toBe(true);
    });
  });

  it('handles invalid minWeight URL parameter gracefully', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/graph?minWeight=invalid']}>
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      // Should default to 0 for invalid values
      expect(edgeFilters.minWeight).toBe(0);
    });
  });

  it('handles missing optional edge type parameters', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/graph?showRelatesTo=false']}>
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      // Explicitly set parameter
      expect(edgeFilters.showRelatesTo).toBe(false);

      // Missing optional parameters should default to true
      expect(edgeFilters.showHasSection).toBe(true);
      expect(edgeFilters.showDefines).toBe(true);
    });
  });

  it('persists all edge filter combinations', async () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/admin/graph?showRelatesTo=false&showCoOccurs=true&showMentionedIn=false&showHasSection=true&showDefines=false&minWeight=0.75',
        ]}
      >
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      expect(edgeFilters.showRelatesTo).toBe(false);
      expect(edgeFilters.showCoOccurs).toBe(true);
      expect(edgeFilters.showMentionedIn).toBe(false);
      expect(edgeFilters.showHasSection).toBe(true);
      expect(edgeFilters.showDefines).toBe(false);
      expect(edgeFilters.minWeight).toBe(0.75);
    });
  });

  it('handles edge type parameters with boolean string values', async () => {
    render(
      <MemoryRouter
        initialEntries={[
          '/admin/graph?showRelatesTo=false&showCoOccurs=true&showMentionedIn=false',
        ]}
      >
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      // "false" string should be parsed as false
      expect(edgeFilters.showRelatesTo).toBe(false);
      expect(edgeFilters.showMentionedIn).toBe(false);

      // "true" string or missing should be parsed as true
      expect(edgeFilters.showCoOccurs).toBe(true);
    });
  });

  it('maintains URL parameters when switching tabs', async () => {
    const { container } = render(
      <MemoryRouter
        initialEntries={['/admin/graph?showRelatesTo=false&minWeight=0.5']}
      >
        <Routes>
          <Route path="/admin/graph" element={<GraphAnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Switch to visualization tab
    const vizTab = screen.getByTestId('tab-visualization');
    vizTab.click();

    await waitFor(() => {
      expect(screen.getByTestId('graph-viewer')).toBeInTheDocument();
    });

    // Switch back to analytics tab
    const analyticsTab = screen.getByTestId('tab-analytics');
    analyticsTab.click();

    await waitFor(() => {
      expect(screen.getByTestId('analytics-dashboard')).toBeInTheDocument();
    });

    // Switch back to visualization - URL params should persist
    vizTab.click();

    await waitFor(() => {
      const graphViewer = screen.getByTestId('graph-viewer');
      const edgeFilters = JSON.parse(graphViewer.getAttribute('data-edge-filters') || '{}');

      expect(edgeFilters.showRelatesTo).toBe(false);
      expect(edgeFilters.minWeight).toBe(0.5);
    });
  });
});
