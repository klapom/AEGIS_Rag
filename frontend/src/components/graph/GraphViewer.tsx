/**
 * GraphViewer Component
 * Sprint 29 Feature 29.1: Interactive Graph Visualization
 * Sprint 34 Features 34.3-34.4: Edge-Type Visualization
 * Sprint 34 Feature 34.6: Graph Edge Filter Controls
 * Sprint 35 Fix: External Data Support for GraphModal Integration
 *
 * Features:
 * - Force-directed layout with react-force-graph-2d
 * - Pan and zoom controls
 * - Node hover tooltips
 * - Node click highlighting
 * - Color by entity type
 * - Size by node degree
 * - Directional edges with arrow heads
 * - Edge colors by relationship type (RELATES_TO: blue, MENTIONED_IN: gray)
 * - Edge width based on relationship weight (1-3px)
 * - Edge hover tooltips with type, weight, and description
 * - Legend for both entity types and relationship types
 * - Edge type filtering (show/hide RELATES_TO, MENTIONED_IN)
 * - Relationship weight threshold filtering
 * - External data support: Can accept pre-fetched graph data (for GraphModal)
 */

import { useRef, useCallback, useState, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useGraphData } from '../../hooks/useGraphData';
import type { GraphData, GraphFilters, ForceGraphNode, EdgeFilters } from '../../types/graph';

interface GraphViewerProps {
  /** Optional pre-fetched graph data (if provided, internal fetching is skipped) */
  data?: GraphData | null;
  /** Loading state (only used when data prop is provided) */
  loading?: boolean;
  /** Error state (only used when data prop is provided) */
  error?: Error | null;
  maxNodes?: number;
  entityTypes?: string[];
  highlightCommunities?: string[];
  onNodeClick?: (node: ForceGraphNode) => void;
  // Sprint 34 Feature 34.6: Edge filters
  edgeFilters?: EdgeFilters;
}

export function GraphViewer({
  data: externalData,
  loading: externalLoading,
  error: externalError,
  maxNodes = 100,
  entityTypes,
  highlightCommunities,
  onNodeClick,
  edgeFilters,
}: GraphViewerProps) {
  // Determine if we should use external data or fetch our own
  const useExternalData = externalData !== undefined;

  const filters: GraphFilters = { maxNodes, entityTypes, highlightCommunities };

  // Only fetch data if not provided externally
  // When external data is provided, pass empty filters to avoid unnecessary fetching
  const { data: fetchedData, loading: fetchedLoading, error: fetchedError } = useGraphData(
    useExternalData ? {} : filters
  );

  // Use external data if provided, otherwise use fetched data
  const data = useExternalData ? externalData : fetchedData;
  const loading = useExternalData ? (externalLoading ?? false) : fetchedLoading;
  const error = useExternalData ? (externalError ?? null) : fetchedError;

  const graphRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<ForceGraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<ForceGraphNode | null>(null);

  // Sprint 34 Feature 34.6: Filter graph data by edge types
  const filteredData = useMemo(() => {
    if (!data) return null;

    // Default edge filters: show all edges
    const filters = edgeFilters || { showRelatesTo: true, showMentionedIn: true, minWeight: 0 };

    const filteredLinks = data.links.filter((link) => {
      const linkType = (link.label || '').toUpperCase();

      // Filter by type
      if (linkType === 'RELATES_TO' && !filters.showRelatesTo) return false;
      if (linkType === 'MENTIONED_IN' && !filters.showMentionedIn) return false;

      // Filter by weight (only for RELATES_TO which has meaningful weights)
      if (linkType === 'RELATES_TO' && link.weight !== undefined) {
        if (link.weight < filters.minWeight) return false;
      }

      return true;
    });

    return {
      nodes: data.nodes,
      links: filteredLinks,
    };
  }, [data, edgeFilters]);

  // Entity type color mapping
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getNodeColor = useCallback(
    (node: any) => {
      // Highlight selected node
      if (selectedNode && node.id === selectedNode.id) {
        return '#f59e0b'; // Amber
      }

      // Highlight community if specified
      if (highlightCommunities && node.community && highlightCommunities.includes(node.community)) {
        return '#8b5cf6'; // Purple
      }

      // Color by entity type
      const nodeType = (node.type || '').toString().toUpperCase();
      switch (nodeType) {
        case 'PERSON':
          return '#3b82f6'; // Blue
        case 'ORGANIZATION':
          return '#10b981'; // Green
        case 'LOCATION':
          return '#ef4444'; // Red
        case 'EVENT':
          return '#f59e0b'; // Amber
        case 'DATE':
          return '#ec4899'; // Pink
        case 'PRODUCT':
          return '#8b5cf6'; // Purple
        default:
          return '#6b7280'; // Gray
      }
    },
    [selectedNode, highlightCommunities]
  );

  // Node size based on degree (number of connections)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getNodeSize = useCallback((node: any) => {
    const baseSize = 4;
    const scaleFactor = 0.5;
    return baseSize + ((node.degree as number) || 0) * scaleFactor;
  }, []);

  // Handle node click
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback(
    (node: any) => {
      setSelectedNode(node as ForceGraphNode);
      if (onNodeClick) {
        onNodeClick(node as ForceGraphNode);
      }
    },
    [onNodeClick]
  );

  // Handle background click (deselect)
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Node hover tooltip
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getNodeLabel = useCallback((node: any) => {
    const label = node.label || node.id || 'Unknown';
    const type = node.type || 'Unknown';
    const degree = node.degree || 0;
    const community = node.community;
    return `${label}\nType: ${type}\nConnections: ${degree}${
      community ? `\nCommunity: ${community}` : ''
    }`;
  }, []);

  // Handle node hover
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeHover = useCallback((node: any) => {
    setHoveredNode(node as ForceGraphNode | null);
  }, []);

  // Link color and opacity
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkColor = useCallback(
    (link: any) => {
      const source = typeof link.source === 'object' ? link.source : null;
      const target = typeof link.target === 'object' ? link.target : null;

      // Highlight links connected to selected node
      if (selectedNode && (source?.id === selectedNode.id || target?.id === selectedNode.id)) {
        return '#f59e0b'; // Amber for selected
      }

      // Color by relationship type
      const linkType = (link.label || link.type || '').toUpperCase();
      switch (linkType) {
        case 'RELATES_TO':
          return '#3B82F6'; // Blue
        case 'MENTIONED_IN':
          return '#9CA3AF'; // Gray
        case 'HAS_SECTION':
          return '#10B981'; // Green
        case 'DEFINES':
          return '#F59E0B'; // Amber
        default:
          return '#d1d5db'; // Light gray
      }
    },
    [selectedNode]
  );

  // Link width based on relationship type and weight
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkWidth = useCallback((link: any) => {
    const linkType = (link.label || link.type || '').toUpperCase();

    // RELATES_TO edges vary by weight
    if (linkType === 'RELATES_TO' && typeof link.weight === 'number') {
      return 1 + link.weight * 2; // 1-3px based on weight 0-1
    }

    return 1.5; // Default width
  }, []);

  // Link hover tooltip
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getLinkLabel = useCallback((link: any) => {
    const type = link.label || link.type || 'Unknown';
    const desc = link.description || '';
    const weight = link.weight ? ` (${Math.round(link.weight * 100)}%)` : '';
    return `${type}${weight}${desc ? `\n${desc}` : ''}`;
  }, []);

  if (loading) {
    return <GraphSkeleton />;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-2">Failed to load graph</div>
          <div className="text-gray-600">{error.message}</div>
        </div>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center text-gray-500">
          <div className="text-xl mb-2">No graph data available</div>
          <div>Try adjusting your filters or ingest some documents</div>
        </div>
      </div>
    );
  }

  if (!filteredData || filteredData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center text-gray-500">
          <div className="text-xl mb-2">No nodes match the current filters</div>
          <div>Try adjusting your filters</div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="relative w-full h-full bg-white rounded-lg border border-gray-200"
      data-testid="graph-canvas"
    >
      {/* Graph Controls Overlay */}
      <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 border border-gray-200">
        <div className="text-sm space-y-1">
          <div className="font-semibold text-gray-900">Graph Controls</div>
          <div className="text-gray-600">Pan: Click + Drag</div>
          <div className="text-gray-600">Zoom: Mouse Wheel</div>
          <div className="text-gray-600">Select: Click Node</div>
        </div>
      </div>

      {/* Node Info Overlay (when node is selected or hovered) */}
      {(selectedNode || hoveredNode) && (
        <div className="absolute top-4 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 border border-gray-200 max-w-xs">
          <div className="space-y-2">
            <div className="font-semibold text-gray-900 text-lg">
              {(selectedNode || hoveredNode)?.label}
            </div>
            <div className="text-sm space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Type:</span>
                <span className="font-medium">{(selectedNode || hoveredNode)?.type}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Connections:</span>
                <span className="font-medium">{(selectedNode || hoveredNode)?.degree || 0}</span>
              </div>
              {(selectedNode || hoveredNode)?.community && (
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Community:</span>
                  <span className="font-medium">{(selectedNode || hoveredNode)?.community}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Graph Stats Overlay */}
      <div className="absolute bottom-4 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 border border-gray-200" data-testid="graph-stats">
        <div className="text-sm space-y-1">
          <div className="font-semibold text-gray-900">Graph Stats</div>
          <div className="text-gray-600" data-testid="graph-node-count">Nodes: {filteredData.nodes.length}</div>
          <div className="text-gray-600" data-testid="graph-edge-count">
            Edges: {filteredData.links.length}
            {data.links.length !== filteredData.links.length && (
              <span className="text-gray-500"> / {data.links.length}</span>
            )}
          </div>
        </div>
      </div>

      {/* Legend Overlay */}
      <div
        className="absolute bottom-4 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 border border-gray-200"
        data-testid="graph-legend"
      >
        <div className="text-sm space-y-2">
          <div className="font-semibold text-gray-900">Entity Types</div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-gray-600">Person</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-gray-600">Organization</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-gray-600">Location</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-amber-500"></div>
              <span className="text-gray-600">Event</span>
            </div>
          </div>

          <div className="border-t border-gray-200 pt-2 mt-2">
            <div className="font-semibold text-gray-900">Relationships</div>
            <div className="space-y-1 mt-1">
              <div
                className="flex items-center space-x-2"
                data-testid="legend-item-relates-to"
              >
                <div className="w-6 h-0.5 bg-blue-500"></div>
                <span className="text-gray-600">RELATES_TO</span>
              </div>
              <div
                className="flex items-center space-x-2"
                data-testid="legend-item-mentioned-in"
              >
                <div className="w-6 h-0.5 bg-gray-400"></div>
                <span className="text-gray-600">MENTIONED_IN</span>
              </div>
              <div
                className="flex items-center space-x-2"
                data-testid="legend-item-has-section"
              >
                <div className="w-6 h-0.5 bg-green-500"></div>
                <span className="text-gray-600">HAS_SECTION</span>
              </div>
              <div
                className="flex items-center space-x-2"
                data-testid="legend-item-defines"
              >
                <div className="w-6 h-0.5 bg-amber-500"></div>
                <span className="text-gray-600">DEFINES</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Force Graph */}
      <ForceGraph2D
        ref={graphRef}
        graphData={filteredData}
        nodeLabel={getNodeLabel}
        nodeColor={getNodeColor}
        nodeVal={getNodeSize}
        nodeRelSize={4}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkColor={getLinkColor}
        linkWidth={getLinkWidth}
        linkLabel={getLinkLabel}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={handleBackgroundClick}
        cooldownTicks={100}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        width={undefined} // Auto-size to container
        height={undefined} // Auto-size to container
      />
    </div>
  );
}

/**
 * Loading skeleton for graph viewer
 */
function GraphSkeleton() {
  return (
    <div className="w-full h-full bg-gray-50 rounded-lg border border-gray-200 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-primary mb-4"></div>
        <div className="text-gray-600">Loading graph...</div>
      </div>
    </div>
  );
}
