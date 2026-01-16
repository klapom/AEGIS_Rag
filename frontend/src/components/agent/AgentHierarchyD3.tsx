/**
 * AgentHierarchyD3 Component
 * Sprint 99 Bug #7 Fix (Option B)
 *
 * D3.js tree visualization using flat nodes+edges format.
 * Transforms D3HierarchyResponse (nodes[], edges[]) into hierarchical tree.
 *
 * Features:
 * - D3.js tree layout with automatic positioning
 * - Pan and zoom navigation
 * - Click nodes to view details
 * - Highlight delegation chains
 * - Responsive SVG rendering
 * - Color-coded by agent level
 */

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import type { D3HierarchyNode, D3HierarchyEdge } from '../../api/agentHierarchy';

interface AgentHierarchyD3Props {
  nodes: D3HierarchyNode[];
  edges: D3HierarchyEdge[];
  onNodeClick?: (agentId: string) => void;
  highlightedAgents?: string[];
  className?: string;
}

/**
 * Agent level colors (lowercase to match D3HierarchyNode.level)
 */
const LEVEL_COLORS = {
  executive: '#ef4444', // red-500
  manager: '#3b82f6', // blue-500
  worker: '#10b981', // green-500
};

/**
 * Nested node interface for D3 hierarchy
 */
interface NestedNode extends D3HierarchyNode {
  children?: NestedNode[];
}

/**
 * Transform flat nodes+edges into nested hierarchy structure
 */
function transformToNestedHierarchy(
  nodes: D3HierarchyNode[],
  edges: D3HierarchyEdge[]
): NestedNode | null {
  if (nodes.length === 0) return null;

  // Create map of nodes by ID
  const nodeMap = new Map<string, NestedNode>();
  nodes.forEach((node) => {
    nodeMap.set(node.agent_id, { ...node, children: [] });
  });

  // Build parent-child relationships
  const childrenMap = new Map<string, string[]>();
  edges.forEach((edge) => {
    const children = childrenMap.get(edge.parent_id) || [];
    children.push(edge.child_id);
    childrenMap.set(edge.parent_id, children);
  });

  // Attach children to parents
  childrenMap.forEach((childIds, parentId) => {
    const parent = nodeMap.get(parentId);
    if (parent) {
      parent.children = childIds
        .map((childId) => nodeMap.get(childId))
        .filter((child): child is NestedNode => child !== undefined);
    }
  });

  // Find root node (node with no parent)
  const childIds = new Set(edges.map((e) => e.child_id));
  const rootNode = nodes.find((node) => !childIds.has(node.agent_id));

  if (!rootNode) {
    console.warn('No root node found in hierarchy');
    return nodeMap.get(nodes[0].agent_id) || null;
  }

  return nodeMap.get(rootNode.agent_id) || null;
}

export function AgentHierarchyD3({
  nodes,
  edges,
  onNodeClick,
  highlightedAgents = [],
  className = '',
}: AgentHierarchyD3Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  /**
   * Update dimensions on container resize
   */
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });

    resizeObserver.observe(containerRef.current);

    return () => resizeObserver.disconnect();
  }, []);

  /**
   * Render D3.js tree
   */
  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    // Transform flat structure to nested hierarchy
    const hierarchyData = transformToNestedHierarchy(nodes, edges);
    if (!hierarchyData) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove(); // Clear previous render

    const { width, height } = dimensions;
    const margin = { top: 40, right: 120, bottom: 40, left: 120 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    zoomRef.current = zoom as d3.ZoomBehavior<SVGSVGElement, unknown>;
    svg.call(zoom);

    // Create main group with initial transform
    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create tree layout
    const treeLayout = d3.tree<NestedNode>().size([innerHeight, innerWidth]);

    // Create hierarchy from data
    const root = d3.hierarchy(hierarchyData);
    const treeData = treeLayout(root);

    // Add links (edges)
    g.selectAll('.link')
      .data(treeData.links())
      .enter()
      .append('path')
      .attr('class', 'link')
      .attr('fill', 'none')
      .attr('stroke', '#94a3b8') // gray-400
      .attr('stroke-width', 2)
      .attr(
        'd',
        d3
          .linkHorizontal<d3.HierarchyLink<NestedNode>, d3.HierarchyPointNode<NestedNode>>()
          .x((d) => d.y)
          .y((d) => d.x)
      );

    // Add nodes
    const nodeGroups = g
      .selectAll('.node')
      .data(treeData.descendants())
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('data-testid', (d) => `agent-node-${d.data.agent_id}`)
      .attr('transform', (d) => `translate(${d.y},${d.x})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        if (onNodeClick) {
          onNodeClick(d.data.agent_id);
        }
      });

    // Add node circles
    nodeGroups
      .append('circle')
      .attr('r', 8)
      .attr('fill', (d) => {
        if (highlightedAgents.includes(d.data.agent_id)) {
          return '#f59e0b'; // amber-500 for highlighted
        }
        return LEVEL_COLORS[d.data.level] || '#6b7280';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    // Add node labels (agent name)
    nodeGroups
      .append('text')
      .attr('dy', 25)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('fill', '#1f2937') // gray-800
      .text((d) => d.data.name);

    // Add capability badges (small text below name)
    nodeGroups
      .append('text')
      .attr('dy', 38)
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('fill', '#6b7280') // gray-500
      .text((d) => {
        const capabilities = d.data.capabilities.slice(0, 2);
        return capabilities.length > 0 ? `[${capabilities.join(', ')}]` : '';
      });

    // Add legend
    const legend = svg
      .append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(20, 20)`);

    const legendItems = [
      { label: 'Executive', color: LEVEL_COLORS.executive },
      { label: 'Manager', color: LEVEL_COLORS.manager },
      { label: 'Worker', color: LEVEL_COLORS.worker },
    ];

    legendItems.forEach((item, i) => {
      const legendItem = legend.append('g').attr('transform', `translate(0, ${i * 20})`);

      legendItem
        .append('circle')
        .attr('r', 6)
        .attr('fill', item.color)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1);

      legendItem
        .append('text')
        .attr('x', 15)
        .attr('y', 4)
        .attr('font-size', '12px')
        .attr('fill', '#1f2937')
        .text(item.label);
    });
  }, [nodes, edges, dimensions, onNodeClick, highlightedAgents]);

  /**
   * Zoom controls
   */
  const handleZoomIn = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.3);
  };

  const handleZoomOut = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.7);
  };

  const handleResetZoom = () => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(zoomRef.current.transform, d3.zoomIdentity);
  };

  return (
    <div
      ref={containerRef}
      className={`relative bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 overflow-hidden ${className}`}
      style={{ height: '600px' }}
    >
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <button
          onClick={handleZoomIn}
          className="p-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors shadow-sm"
          title="Zoom In"
          aria-label="Zoom in"
          data-testid="zoom-in-button"
        >
          <ZoomIn className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors shadow-sm"
          title="Zoom Out"
          aria-label="Zoom out"
          data-testid="zoom-out-button"
        >
          <ZoomOut className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={handleResetZoom}
          className="p-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors shadow-sm"
          title="Reset Zoom"
          aria-label="Reset zoom"
          data-testid="reset-zoom-button"
        >
          <Maximize2 className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
      </div>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        className="bg-gray-50 dark:bg-gray-900/50"
        data-testid="hierarchy-tree-svg"
      />

      {/* Instructions */}
      {nodes.length > 0 && (
        <div className="absolute bottom-4 left-4 text-xs text-gray-600 dark:text-gray-400 bg-white/90 dark:bg-gray-800/90 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700">
          Click nodes to view details • Pan: Drag • Zoom: Scroll or buttons
        </div>
      )}

      {/* No Data State */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <p className="text-lg font-medium mb-2">No hierarchy data</p>
            <p className="text-sm">Waiting for agent hierarchy to load...</p>
          </div>
        </div>
      )}
    </div>
  );
}
