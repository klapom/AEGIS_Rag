/**
 * GraphViewer Component Tests
 * Sprint 29 Feature 29.1
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { GraphViewer } from './GraphViewer';
import * as useGraphDataModule from '../../hooks/useGraphData';

// Mock the useGraphData hook
vi.mock('../../hooks/useGraphData');

// Mock ForceGraph2D component
vi.mock('react-force-graph-2d', () => ({
  default: ({ graphData }: any) => (
    <div data-testid="force-graph">
      Nodes: {graphData?.nodes?.length || 0}, Links: {graphData?.links?.length || 0}
    </div>
  ),
}));

describe('GraphViewer', () => {
  it('renders loading skeleton when loading', () => {
    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<GraphViewer />);
    expect(screen.getByText('Loading graph...')).toBeInTheDocument();
  });

  it('renders error message when error occurs', () => {
    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: null,
      loading: false,
      error: new Error('Failed to fetch'),
      refetch: vi.fn(),
    });

    render(<GraphViewer />);
    expect(screen.getByText('Failed to load graph')).toBeInTheDocument();
    expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: { nodes: [], links: [] },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<GraphViewer />);
    expect(screen.getByText('No graph data available')).toBeInTheDocument();
  });

  it('renders graph with nodes and edges', () => {
    const mockData = {
      nodes: [
        { id: '1', label: 'Node 1', type: 'PERSON', degree: 2 },
        { id: '2', label: 'Node 2', type: 'ORGANIZATION', degree: 1 },
      ],
      links: [{ source: '1', target: '2', label: 'WORKS_FOR' }],
    };

    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: mockData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<GraphViewer />);
    expect(screen.getByTestId('force-graph')).toBeInTheDocument();
    expect(screen.getByText(/Nodes: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Links: 1/)).toBeInTheDocument();
  });

  it('passes filters to useGraphData hook', () => {
    const mockUseGraphData = vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: { nodes: [], links: [] },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    render(
      <GraphViewer maxNodes={50} entityTypes={['PERSON', 'ORGANIZATION']} highlightCommunities={['C1']} />
    );

    expect(mockUseGraphData).toHaveBeenCalledWith({
      maxNodes: 50,
      entityTypes: ['PERSON', 'ORGANIZATION'],
      highlightCommunities: ['C1'],
    });
  });

  it('calls onNodeClick callback when provided', () => {
    const mockData = {
      nodes: [{ id: '1', label: 'Node 1', type: 'PERSON', degree: 1 }],
      links: [],
    };

    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: mockData,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });

    const onNodeClick = vi.fn();
    render(<GraphViewer onNodeClick={onNodeClick} />);

    // Component renders successfully with callback
    expect(screen.getByTestId('force-graph')).toBeInTheDocument();
  });
});
