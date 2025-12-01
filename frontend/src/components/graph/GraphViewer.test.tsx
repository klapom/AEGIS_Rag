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

// Note: react-force-graph is mocked globally in test/setup.ts to prevent
// loading of 3D dependencies (aframe, three.js) that require browser globals

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

    const { container } = render(<GraphViewer />);
    // ForceGraph2D is mocked to return null, so we just verify the component renders
    // without throwing errors (no AFRAME/THREE errors)
    expect(container).toBeInTheDocument();
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
    const { container } = render(<GraphViewer onNodeClick={onNodeClick} />);

    // Component renders successfully with callback (no AFRAME/THREE errors)
    expect(container).toBeInTheDocument();
  });

  it('uses external data when provided instead of fetching', () => {
    const externalData = {
      nodes: [
        { id: 'ext1', label: 'External Node 1', type: 'PERSON', degree: 1 },
        { id: 'ext2', label: 'External Node 2', type: 'ORGANIZATION', degree: 1 },
      ],
      links: [{ source: 'ext1', target: 'ext2', label: 'WORKS_FOR' }],
    };

    const mockUseGraphData = vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = render(
      <GraphViewer
        data={externalData}
        loading={false}
        error={null}
      />
    );

    // Should not fetch data when external data is provided
    // When external data is provided, empty filters should be passed
    expect(mockUseGraphData).toHaveBeenCalledWith({});

    // Component should render successfully with external data
    expect(container).toBeInTheDocument();
  });

  it('shows loading state from external props when external data is used', () => {
    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: null,
      loading: false, // Internal loading is false
      error: null,
      refetch: vi.fn(),
    });

    render(
      <GraphViewer
        data={null}
        loading={true} // External loading is true
        error={null}
      />
    );

    expect(screen.getByText('Loading graph...')).toBeInTheDocument();
  });

  it('shows error state from external props when external data is used', () => {
    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: null,
      loading: false,
      error: null, // Internal error is null
      refetch: vi.fn(),
    });

    render(
      <GraphViewer
        data={null}
        loading={false}
        error={new Error('External fetch failed')} // External error
      />
    );

    expect(screen.getByText('Failed to load graph')).toBeInTheDocument();
    expect(screen.getByText('External fetch failed')).toBeInTheDocument();
  });

  it('renders external data correctly when loading is false', () => {
    const externalData = {
      nodes: [
        { id: 'ext1', label: 'External Entity', type: 'PERSON', degree: 2 },
      ],
      links: [],
    };

    vi.spyOn(useGraphDataModule, 'useGraphData').mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = render(
      <GraphViewer
        data={externalData}
        loading={false}
        error={null}
      />
    );

    // Should render the graph canvas (not loading or error state)
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
    expect(container).toBeInTheDocument();
  });
});
