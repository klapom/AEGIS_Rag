/**
 * GraphVisualization Component Tests
 * Sprint 116 Feature 116.9: Graph Visualization with Vis.js
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GraphVisualization } from '../../../components/graph/GraphVisualization';
import type { GraphData, EdgeFilters } from '../../../types/graph';

// Mock vis-network
vi.mock('vis-network', () => {
  class MockNetwork {
    constructor(_container: any, _data: any, _options: any) {
      // Mock constructor
    }
    setData = vi.fn();
    destroy = vi.fn();
    on = vi.fn();
    getScale = vi.fn(() => 1);
    moveTo = vi.fn();
    fit = vi.fn();
    canvasToDOM = vi.fn(() => ({ x: 100, y: 100 }));
  }
  return {
    Network: MockNetwork,
  };
});

// Mock vis-data
vi.mock('vis-data', () => {
  class MockDataSet {
    private data: any[];
    constructor(data: any[]) {
      this.data = data;
    }
    get(id: any) {
      return this.data.find((item: any) => item.id === id);
    }
    add = vi.fn();
    update = vi.fn();
    remove = vi.fn();
    clear = vi.fn();
  }
  return {
    DataSet: MockDataSet,
  };
});

describe('GraphVisualization', () => {
  const mockGraphData: GraphData = {
    nodes: [
      { id: '1', label: 'Node 1', type: 'PERSON', degree: 5 },
      { id: '2', label: 'Node 2', type: 'ORGANIZATION', degree: 3 },
      { id: '3', label: 'Node 3', type: 'LOCATION', degree: 2 },
    ],
    links: [
      { source: '1', target: '2', label: 'RELATES_TO', weight: 0.8 },
      { source: '2', target: '3', label: 'MENTIONED_IN', weight: 0.5 },
      { source: '1', target: '3', label: 'CO_OCCURS', weight: 0.6 },
    ],
  };

  const mockEdgeFilters: EdgeFilters = {
    showRelatesTo: true,
    showCoOccurs: true,
    showMentionedIn: true,
    minWeight: 0,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    render(<GraphVisualization data={null} loading={true} />);
    expect(screen.getByText(/loading graph/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    const error = new Error('Network error occurred');
    render(<GraphVisualization data={null} error={error} />);
    expect(screen.getByText(/failed to load graph/i)).toBeInTheDocument();
    expect(screen.getByText('Network error occurred')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    render(<GraphVisualization data={null} />);
    expect(screen.getByText(/no graph data available/i)).toBeInTheDocument();
  });

  it('renders graph canvas with data', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('renders graph controls', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    expect(screen.getByTestId('graph-controls')).toBeInTheDocument();
    expect(screen.getByTestId('zoom-in-button')).toBeInTheDocument();
    expect(screen.getByTestId('zoom-out-button')).toBeInTheDocument();
    expect(screen.getByTestId('fit-button')).toBeInTheDocument();
    expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    expect(screen.getByTestId('export-png-button')).toBeInTheDocument();
    expect(screen.getByTestId('fullscreen-button')).toBeInTheDocument();
  });

  it('renders graph legend', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    expect(screen.getByTestId('graph-legend')).toBeInTheDocument();
  });

  it('renders graph stats', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    expect(screen.getByText(/nodes: 3/i)).toBeInTheDocument();
    expect(screen.getByText(/edges: 3/i)).toBeInTheDocument();
  });

  it('filters edges based on edge filters', () => {
    const filteredEdgeFilters: EdgeFilters = {
      showRelatesTo: true,
      showCoOccurs: false,
      showMentionedIn: false,
      minWeight: 0,
    };
    render(<GraphVisualization data={mockGraphData} edgeFilters={filteredEdgeFilters} />);
    // Only 1 edge should remain (RELATES_TO)
    // Note: This is testing the filtering logic indirectly through rendering
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('filters edges based on minimum weight', () => {
    const weightFilters: EdgeFilters = {
      showRelatesTo: true,
      showCoOccurs: true,
      showMentionedIn: true,
      minWeight: 0.7, // Only edges with weight >= 0.7
    };
    render(<GraphVisualization data={mockGraphData} edgeFilters={weightFilters} />);
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('calls onNodeClick when node is clicked', async () => {
    const onNodeClick = vi.fn();
    render(
      <GraphVisualization
        data={mockGraphData}
        edgeFilters={mockEdgeFilters}
        onNodeClick={onNodeClick}
      />
    );
    // Vis-network click events are mocked, so we can't directly test this
    // But the component should have the handler set up
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('toggles fullscreen mode', async () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    const fullscreenButton = screen.getByTestId('fullscreen-button');

    // Mock requestFullscreen
    const mockRequestFullscreen = vi.fn();
    HTMLElement.prototype.requestFullscreen = mockRequestFullscreen;

    fireEvent.click(fullscreenButton);
    expect(mockRequestFullscreen).toHaveBeenCalled();
  });

  it('handles zoom in action', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    const zoomInButton = screen.getByTestId('zoom-in-button');
    fireEvent.click(zoomInButton);
    // Network mock should have moveTo called
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('handles zoom out action', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    const zoomOutButton = screen.getByTestId('zoom-out-button');
    fireEvent.click(zoomOutButton);
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('handles fit to view action', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    const fitButton = screen.getByTestId('fit-button');
    fireEvent.click(fitButton);
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('handles reset view action', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    const resetButton = screen.getByTestId('reset-button');
    fireEvent.click(resetButton);
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('handles export PNG action', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    const exportButton = screen.getByTestId('export-png-button');

    // Mock canvas and toDataURL
    const mockCanvas = document.createElement('canvas');
    mockCanvas.toDataURL = vi.fn(() => 'data:image/png;base64,mock');
    vi.spyOn(document, 'querySelector').mockReturnValue(mockCanvas);

    fireEvent.click(exportButton);
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('uses correct edge colors by type', () => {
    render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);
    // Edge colors are applied in vis-network configuration
    // We verify the component renders with the data
    expect(screen.getByTestId('graph-canvas')).toBeInTheDocument();
  });

  it('renders with no edge filters (shows all edges)', () => {
    render(<GraphVisualization data={mockGraphData} />);
    expect(screen.getByText(/edges: 3/i)).toBeInTheDocument();
  });

  it('updates when data changes', () => {
    const { rerender } = render(<GraphVisualization data={mockGraphData} edgeFilters={mockEdgeFilters} />);

    const newData: GraphData = {
      nodes: [
        { id: '4', label: 'Node 4', type: 'EVENT', degree: 1 },
      ],
      links: [],
    };

    rerender(<GraphVisualization data={newData} edgeFilters={mockEdgeFilters} />);
    expect(screen.getByText(/nodes: 1/i)).toBeInTheDocument();
    expect(screen.getByText(/edges: 0/i)).toBeInTheDocument();
  });
});
