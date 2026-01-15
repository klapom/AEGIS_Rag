/**
 * HierarchyTree Component
 * Sprint 98 Feature 98.2: Agent Hierarchy Visualizer
 *
 * Interactive D3.js tree visualization of agent hierarchy.
 * Shows Executive→Manager→Worker structure with pan/zoom.
 *
 * Features:
 * - D3.js tree layout with automatic positioning
 * - Pan and zoom navigation
 * - Click nodes to view details
 * - Highlight delegation chains
 * - Responsive SVG rendering
 */

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import type { HierarchyNode } from '../../api/agentHierarchy';

interface HierarchyTreeProps {
  data: HierarchyNode | null;
  onNodeClick?: (agentId: string) => void;
  highlightedAgents?: string[];
  className?: string;
}

/**
 * Agent level colors
 */
const LEVEL_COLORS = {
  EXECUTIVE: '#3b82f6', // blue-600
  MANAGER: '#10b981', // green-600
  WORKER: '#8b5cf6', // purple-600
};

export function HierarchyTree({
  data,
  onNodeClick,
  highlightedAgents = [],
  className = '',
}: HierarchyTreeProps) {
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
    if (!svgRef.current || !data) return;

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
    const treeLayout = d3.tree<HierarchyNode>().size([innerHeight, innerWidth]);

    // Create hierarchy from data
    const root = d3.hierarchy(data);
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
          .linkHorizontal<d3.HierarchyLink<HierarchyNode>, d3.HierarchyPointNode<HierarchyNode>>()
          .x((d) => d.y)
          .y((d) => d.x)
      );

    // Add nodes
    const nodes = g
      .selectAll('.node')
      .data(treeData.descendants())
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('transform', (d) => `translate(${d.y},${d.x})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        if (onNodeClick) {
          onNodeClick(d.data.agent_id);
        }
      });

    // Add node circles
    nodes
      .append('circle')
      .attr('r', 8)
      .attr('fill', (d) => {
        if (highlightedAgents.includes(d.data.agent_id)) {
          return '#f59e0b'; // amber-500 for highlighted
        }
        return LEVEL_COLORS[d.data.agent_level] || '#6b7280';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    // Add node labels
    nodes
      .append('text')
      .attr('dy', 25)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('fill', '#1f2937') // gray-800
      .text((d) => d.data.agent_name);

    // Add skill badges (small text below name)
    nodes
      .append('text')
      .attr('dy', 38)
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('fill', '#6b7280') // gray-500
      .text((d) => {
        const skills = d.data.skills.slice(0, 2);
        return skills.length > 0 ? `[${skills.join(', ')}]` : '';
      });

    // Add legend
    const legend = svg
      .append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(20, 20)`);

    const legendItems = [
      { label: 'Executive', color: LEVEL_COLORS.EXECUTIVE },
      { label: 'Manager', color: LEVEL_COLORS.MANAGER },
      { label: 'Worker', color: LEVEL_COLORS.WORKER },
    ];

    legendItems.forEach((item, i) => {
      const legendItem = legend.append('g').attr('transform', `translate(0, ${i * 20})`);

      legendItem.append('circle').attr('r', 6).attr('fill', item.color).attr('stroke', '#fff').attr('stroke-width', 1);

      legendItem
        .append('text')
        .attr('x', 15)
        .attr('y', 4)
        .attr('font-size', '12px')
        .attr('fill', '#1f2937')
        .text(item.label);
    });
  }, [data, dimensions, onNodeClick, highlightedAgents]);

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
          data-testid="zoom-in-button"
        >
          <ZoomIn className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors shadow-sm"
          title="Zoom Out"
          data-testid="zoom-out-button"
        >
          <ZoomOut className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={handleResetZoom}
          className="p-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors shadow-sm"
          title="Reset Zoom"
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
      {data && (
        <div className="absolute bottom-4 left-4 text-xs text-gray-600 dark:text-gray-400 bg-white/90 dark:bg-gray-800/90 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700">
          Click nodes to view details • Pan: Drag • Zoom: Scroll or buttons
        </div>
      )}

      {/* No Data State */}
      {!data && (
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
