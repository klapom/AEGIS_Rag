/**
 * GraphViewer Component
 * Sprint 29 Feature 29.1: Interactive Graph Visualization
 *
 * Features:
 * - Force-directed layout with react-force-graph-2d
 * - Pan and zoom controls
 * - Node hover tooltips
 * - Node click highlighting
 * - Color by entity type
 * - Size by node degree
 * - Directional edges with arrow heads
 */

import { useRef, useCallback, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useGraphData } from '../../hooks/useGraphData';
import type { GraphFilters, ForceGraphNode } from '../../types/graph';

interface GraphViewerProps {
  maxNodes?: number;
  entityTypes?: string[];
  highlightCommunities?: string[];
  onNodeClick?: (node: ForceGraphNode) => void;
}

export function GraphViewer({
  maxNodes = 100,
  entityTypes,
  highlightCommunities,
  onNodeClick,
}: GraphViewerProps) {
  const filters: GraphFilters = { maxNodes, entityTypes, highlightCommunities };
  const { data, loading, error } = useGraphData(filters);
  const graphRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<ForceGraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<ForceGraphNode | null>(null);

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
        return '#f59e0b'; // Amber
      }

      return '#d1d5db'; // Gray
    },
    [selectedNode]
  );

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

  return (
    <div className="relative w-full h-full bg-white rounded-lg border border-gray-200">
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
      <div className="absolute bottom-4 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 border border-gray-200">
        <div className="text-sm space-y-1">
          <div className="font-semibold text-gray-900">Graph Stats</div>
          <div className="text-gray-600">Nodes: {data.nodes.length}</div>
          <div className="text-gray-600">Edges: {data.links.length}</div>
        </div>
      </div>

      {/* Legend Overlay */}
      <div className="absolute bottom-4 right-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 border border-gray-200">
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
        </div>
      </div>

      {/* Force Graph */}
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        nodeLabel={getNodeLabel}
        nodeColor={getNodeColor}
        nodeVal={getNodeSize}
        nodeRelSize={4}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        linkColor={getLinkColor}
        linkWidth={1.5}
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
