/**
 * GraphVisualization Component
 * Sprint 116 Feature 116.9: Graph Visualization with Vis.js
 *
 * Features:
 * - Vis.js network library for graph rendering
 * - Force-directed layout with physics
 * - Pan and zoom controls
 * - Edge colors by relationship type
 * - Node hover and click interactions
 * - Export to PNG functionality
 * - Fullscreen mode
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { GraphLegend } from './GraphLegend';
import { GraphControls } from './GraphControls';
import { EdgeTooltip } from './EdgeTooltip';
import type { GraphData, EdgeFilters } from '../../types/graph';

interface GraphVisualizationProps {
  data: GraphData | null;
  loading?: boolean;
  error?: Error | null;
  edgeFilters?: EdgeFilters;
  onNodeClick?: (nodeId: string) => void;
}

// Edge type color mapping (Sprint 116.9 requirement)
const EDGE_COLORS: Record<string, string> = {
  RELATES_TO: '#3B82F6', // blue
  MENTIONED_IN: '#22C55E', // green
  CONTAINS: '#F97316', // orange
  PART_OF: '#A855F7', // purple
  SIMILAR_TO: '#06B6D4', // cyan
  CO_OCCURS: '#EAB308', // yellow
  REFERENCES: '#EC4899', // pink
  HAS_SECTION: '#10B981', // green
  DEFINES: '#F59E0B', // amber
  BELONGS_TO: '#06B6D4', // cyan
  WORKS_FOR: '#EC4899', // pink
  LOCATED_IN: '#EF4444', // red
  DEFAULT: '#6B7280', // gray
};

// Get edge color by type
function getEdgeColor(edgeType: string): string {
  const type = edgeType.toUpperCase();
  return EDGE_COLORS[type] || EDGE_COLORS.DEFAULT;
}

// Filter edges based on EdgeFilters
function filterEdges(data: GraphData, edgeFilters?: EdgeFilters): GraphData {
  if (!edgeFilters) return data;

  const filteredLinks = data.links.filter((link) => {
    const linkType = (link.label || '').toUpperCase();

    // Filter by type
    if (linkType === 'RELATES_TO' && !edgeFilters.showRelatesTo) return false;
    if (linkType === 'CO_OCCURS' && !edgeFilters.showCoOccurs) return false;
    if (linkType === 'MENTIONED_IN' && !edgeFilters.showMentionedIn) return false;
    if (linkType === 'HAS_SECTION' && edgeFilters.showHasSection === false) return false;
    if (linkType === 'DEFINES' && edgeFilters.showDefines === false) return false;
    if (linkType === 'BELONGS_TO' && edgeFilters.showBelongsTo === false) return false;
    if (linkType === 'WORKS_FOR' && edgeFilters.showWorksFor === false) return false;
    if (linkType === 'LOCATED_IN' && edgeFilters.showLocatedIn === false) return false;

    // Filter by weight
    if (link.weight !== undefined && link.weight < edgeFilters.minWeight) {
      return false;
    }

    return true;
  });

  return {
    nodes: data.nodes,
    links: filteredLinks,
  };
}

export function GraphVisualization({
  data,
  loading = false,
  error = null,
  edgeFilters,
  onNodeClick,
}: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<{
    id: string;
    label: string;
    weight?: number;
    properties?: Record<string, unknown>;
    x: number;
    y: number;
  } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [visibleEdgeTypes, setVisibleEdgeTypes] = useState<Set<string>>(
    new Set(Object.keys(EDGE_COLORS).filter((k) => k !== 'DEFAULT'))
  );

  // Sprint 124 Fix: Separate network initialization from data updates
  // This prevents vis.js DOM conflicts when data changes

  // Initialize network once on mount
  useEffect(() => {
    return () => {
      // Cleanup network ONLY on unmount
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, []); // Empty deps = only runs on mount/unmount

  // Update network data when data/filters change
  useEffect(() => {
    if (!containerRef.current || !data || loading) return;

    // Filter edges based on current filters
    const filteredData = filterEdges(data, edgeFilters);

    // Convert graph data to vis-network format
    const nodes = new DataSet(
      filteredData.nodes.map((node) => ({
        id: node.id,
        label: node.label,
        title: `${node.label}\nType: ${node.type}\nDegree: ${node.degree || 0}`,
        group: node.type,
        value: (node.degree || 1) * 2, // Size by degree
      }))
    );

    const edges = new DataSet(
      filteredData.links
        .filter((link) => {
          const edgeType = (link.label || 'DEFAULT').toUpperCase();
          return visibleEdgeTypes.has(edgeType);
        })
        .map((link, idx) => {
          const edgeType = link.label || 'DEFAULT';
          return {
            id: `edge-${idx}`,
            from: typeof link.source === 'string' ? link.source : link.source.id,
            to: typeof link.target === 'string' ? link.target : link.target.id,
            label: edgeType,
            title: `${edgeType}${link.weight ? ` (${Math.round(link.weight * 100)}%)` : ''}`,
            color: {
              color: getEdgeColor(edgeType),
              hover: getEdgeColor(edgeType),
              highlight: getEdgeColor(edgeType),
            },
            width: link.weight ? 1 + link.weight * 3 : 2,
            arrows: {
              to: {
                enabled: true,
                scaleFactor: 0.5,
              },
            },
            // Sprint 118 Fix: Include required smooth properties for vis-network Edge type
            smooth: {
              enabled: true,
              type: 'continuous',
              roundness: 0.5,
            },
          };
        })
    );

    const options = {
      nodes: {
        shape: 'dot',
        size: 16,
        font: {
          size: 12,
          color: '#374151',
        },
        borderWidth: 2,
        borderWidthSelected: 3,
      },
      edges: {
        font: {
          size: 10,
          align: 'middle',
        },
        selectionWidth: 2,
      },
      physics: {
        enabled: true,
        stabilization: {
          iterations: 100,
          updateInterval: 25,
        },
        barnesHut: {
          gravitationalConstant: -2000,
          centralGravity: 0.3,
          springLength: 95,
          springConstant: 0.04,
          damping: 0.09,
          avoidOverlap: 0.1,
        },
      },
      interaction: {
        hover: true,
        navigationButtons: false,
        keyboard: true,
        tooltipDelay: 200,
      },
      groups: {
        PERSON: { color: { background: '#3b82f6', border: '#2563eb' } },
        ORGANIZATION: { color: { background: '#10b981', border: '#059669' } },
        LOCATION: { color: { background: '#ef4444', border: '#dc2626' } },
        EVENT: { color: { background: '#f59e0b', border: '#d97706' } },
        DATE: { color: { background: '#ec4899', border: '#db2777' } },
        PRODUCT: { color: { background: '#8b5cf6', border: '#7c3aed' } },
        CHUNK: { color: { background: '#06b6d4', border: '#0891b2' } },
      },
    };

    // Create network if it doesn't exist
    if (!networkRef.current) {
      networkRef.current = new Network(containerRef.current, { nodes, edges }, options);

      // Event handlers
      networkRef.current.on('click', (params) => {
        if (params.nodes.length > 0 && onNodeClick) {
          onNodeClick(params.nodes[0] as string);
        }
      });

      networkRef.current.on('hoverEdge', (params) => {
        // Sprint 118 Fix: Handle DataSet.get() return type properly
        const edgeResult = edges.get(params.edge);
        // get() with a single ID returns the item directly, not an array
        const edge = Array.isArray(edgeResult) ? edgeResult[0] : edgeResult;
        if (edge) {
          const canvasPos = networkRef.current?.canvasToDOM({
            x: params.pointer.canvas.x,
            y: params.pointer.canvas.y,
          });
          setHoveredEdge({
            id: String(edge.id),
            label: String(edge.label || ''),
            weight: typeof edge.width === 'number' ? (edge.width - 1) / 3 : undefined,
            properties: edge.title ? { description: String(edge.title) } : undefined,
            x: canvasPos?.x || 0,
            y: canvasPos?.y || 0,
          });
        }
      });

      networkRef.current.on('blurEdge', () => {
        setHoveredEdge(null);
      });
    } else {
      // Update existing network with new data
      networkRef.current.setData({ nodes, edges });
    }
  }, [data, loading, edgeFilters, visibleEdgeTypes, onNodeClick]);

  // Control handlers
  const handleZoomIn = useCallback(() => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale * 1.2 });
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale / 1.2 });
    }
  }, []);

  const handleFit = useCallback(() => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: true });
    }
  }, []);

  const handleReset = useCallback(() => {
    if (networkRef.current) {
      networkRef.current.moveTo({ scale: 1, position: { x: 0, y: 0 } });
    }
  }, []);

  const handleExportPNG = useCallback(() => {
    if (containerRef.current) {
      const canvas = containerRef.current.querySelector('canvas');
      if (canvas) {
        const url = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.download = `graph-${new Date().toISOString()}.png`;
        link.href = url;
        link.click();
      }
    }
  }, []);

  const handleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  const handleToggleEdgeType = useCallback((edgeType: string) => {
    setVisibleEdgeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(edgeType)) {
        next.delete(edgeType);
      } else {
        next.add(edgeType);
      }
      return next;
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full p-8">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600 mb-4"></div>
          <div className="text-gray-600">Loading graph...</div>
        </div>
      </div>
    );
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
    <div className={`relative w-full h-full ${isFullscreen ? 'bg-white' : ''}`}>
      {/* Graph Canvas */}
      <div ref={containerRef} className="w-full h-full" data-testid="graph-canvas" />

      {/* Controls Overlay */}
      <div className="absolute top-4 right-4 z-10">
        <GraphControls
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onFit={handleFit}
          onReset={handleReset}
          onExportPNG={handleExportPNG}
          onFullscreen={handleFullscreen}
          isFullscreen={isFullscreen}
        />
      </div>

      {/* Legend Overlay */}
      <div className="absolute bottom-4 right-4 z-10">
        <GraphLegend
          edgeColors={EDGE_COLORS}
          visibleEdgeTypes={visibleEdgeTypes}
          onToggleEdgeType={handleToggleEdgeType}
        />
      </div>

      {/* Edge Tooltip */}
      {hoveredEdge && (
        <EdgeTooltip
          edgeLabel={hoveredEdge.label}
          weight={hoveredEdge.weight}
          properties={hoveredEdge.properties}
          x={hoveredEdge.x}
          y={hoveredEdge.y}
        />
      )}

      {/* Graph Stats */}
      {data && (
        <div className="absolute bottom-4 left-4 z-10 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3 border border-gray-200">
          <div className="text-sm space-y-1">
            <div className="font-semibold text-gray-900">Graph Stats</div>
            <div className="text-gray-600">Nodes: {data.nodes.length}</div>
            <div className="text-gray-600">Edges: {data.links.length}</div>
          </div>
        </div>
      )}
    </div>
  );
}
