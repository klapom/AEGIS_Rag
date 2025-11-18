/**
 * GraphExplorerExample Component
 * Sprint 29 Feature 29.5: Example integration of all search and filter components
 *
 * This is a reference implementation showing how to use:
 * - GraphSearch
 * - GraphFilters
 * - CommunityHighlight
 * - GraphViewer
 *
 * NOT FOR PRODUCTION - This is a documentation/example component
 */

import { useState } from 'react';
import { GraphViewer } from './GraphViewer';
import { GraphSearch } from './GraphSearch';
import { GraphFilters, type GraphFilterValues } from './GraphFilters';
import { CommunityHighlight, type Community } from './CommunityHighlight';
import { NodeDetailsPanel } from './NodeDetailsPanel';
import { useGraphData } from '../../hooks/useGraphData';
import { useGraphFilter } from '../../hooks/useGraphSearch';
import type { ForceGraphNode } from '../../types/graph';

/**
 * Complete graph explorer with search, filters, and community highlighting
 * Feature 29.6: Includes NodeDetailsPanel for document search
 */
export function GraphExplorerExample() {
  const [selectedNode, setSelectedNode] = useState<ForceGraphNode | null>(null);
  const [selectedCommunity, setSelectedCommunity] = useState<string | null>(null);
  const [filters, setFilters] = useState<GraphFilterValues>({
    entityTypes: ['PERSON', 'ORGANIZATION', 'LOCATION', 'EVENT'],
    minDegree: 1,
    maxNodes: 100,
  });

  // Fetch graph data
  const { data, loading, error } = useGraphData({
    maxNodes: filters.maxNodes,
    entityTypes: filters.entityTypes,
  });

  // Apply filters to graph data
  const filteredData = useGraphFilter(data || { nodes: [], links: [] }, {
    entityTypes: filters.entityTypes,
    minDegree: filters.minDegree,
    communityId: selectedCommunity,
  });

  // Mock communities (in real app, fetch from API)
  const communities: Community[] = [
    { id: 'comm-1', topic: 'Technology & AI', size: 42, description: 'Entities related to AI and tech' },
    { id: 'comm-2', topic: 'Business & Finance', size: 38 },
    { id: 'comm-3', topic: 'Healthcare', size: 27 },
    { id: 'comm-4', topic: 'Education', size: 19 },
  ];

  // Extract unique entity types from data
  const availableEntityTypes = data
    ? Array.from(new Set(data.nodes.map((node) => node.type.toUpperCase())))
    : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-600">Loading graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">Error: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar with Filters */}
      <div className="w-80 bg-white border-r border-gray-200 p-6 space-y-6 overflow-y-auto">
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-4">Graph Explorer</h2>
          <p className="text-sm text-gray-600 mb-6">
            Search entities, filter by type, and highlight communities
          </p>
        </div>

        {/* Search */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Search</h3>
          <GraphSearch
            data={filteredData}
            onNodeSelect={(nodeId) => {
              const node = filteredData.nodes.find((n) => n.id === nodeId);
              if (node) setSelectedNode(node as ForceGraphNode);
              console.log('Selected node:', nodeId);
            }}
          />
        </div>

        {/* Filters */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Filters</h3>
          <GraphFilters
            entityTypes={availableEntityTypes}
            value={filters}
            onChange={setFilters}
          />
        </div>

        {/* Community Highlight */}
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Communities</h3>
          <CommunityHighlight
            communities={communities}
            selectedCommunity={selectedCommunity}
            onCommunitySelect={setSelectedCommunity}
          />
        </div>

        {/* Stats */}
        <div className="pt-6 border-t border-gray-200">
          <div className="text-sm space-y-2">
            <div className="flex justify-between text-gray-600">
              <span>Nodes:</span>
              <span className="font-semibold text-gray-900">{filteredData.nodes.length}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Edges:</span>
              <span className="font-semibold text-gray-900">{filteredData.links.length}</span>
            </div>
            {selectedNode && (
              <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                Selected: {selectedNode.label}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Graph Viewer */}
      <div className="flex-1 p-6">
        <div className="h-full bg-white rounded-lg shadow-lg overflow-hidden relative">
          <GraphViewer
            maxNodes={filters.maxNodes}
            entityTypes={filters.entityTypes}
            highlightCommunities={selectedCommunity ? [selectedCommunity] : undefined}
            onNodeClick={(node) => {
              setSelectedNode(node);
              console.log('Clicked node:', node);
            }}
          />

          {/* Node Details Panel - Feature 29.6 */}
          <NodeDetailsPanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Compact version for modal or embedded use
 * Feature 29.6: Includes NodeDetailsPanel
 */
export function GraphExplorerCompact() {
  const [selectedNode, setSelectedNode] = useState<ForceGraphNode | null>(null);
  const { data, loading } = useGraphData({ maxNodes: 50 });

  if (loading || !data) {
    return <div className="text-center p-8 text-gray-600">Loading...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      <div className="px-4 pt-4">
        <GraphSearch
          data={data}
          onNodeSelect={(nodeId) => {
            const node = data.nodes.find((n) => n.id === nodeId);
            if (node) setSelectedNode(node as ForceGraphNode);
          }}
        />
      </div>

      {/* Graph */}
      <div className="h-[500px] relative">
        <GraphViewer
          maxNodes={50}
          onNodeClick={(node) => setSelectedNode(node)}
        />

        {/* Node Details Panel */}
        <NodeDetailsPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
}
