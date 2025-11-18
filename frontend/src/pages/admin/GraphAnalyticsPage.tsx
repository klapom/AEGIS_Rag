/**
 * GraphAnalyticsPage Component
 * Sprint 29 Feature 29.3: Admin Graph Analytics View
 *
 * Features:
 * - Admin-only route with role check
 * - Left sidebar: Filters + Statistics + Community Highlight + Export
 * - Main area: Full-screen GraphViewer
 * - Responsive layout with collapsible sidebar
 */

import { useState, useEffect } from 'react';
import { GraphViewer } from '../../components/graph/GraphViewer';
import { GraphFilters, type GraphFilterValues } from '../../components/graph/GraphFilters';
import { CommunityHighlight } from '../../components/graph/CommunityHighlight';
import { GraphExportButton } from '../../components/graph/GraphExportButton';
import { useGraphStatistics } from '../../hooks/useGraphStatistics';
import { useCommunities } from '../../hooks/useCommunities';
import type { GraphFilters as GraphFiltersType } from '../../types/graph';

/**
 * Admin Graph Analytics Page
 *
 * Provides comprehensive graph visualization and analytics tools for administrators.
 * Includes advanced filtering, statistics, community exploration, and export capabilities.
 */
export function GraphAnalyticsPage() {
  // Admin access check (simple implementation - can be enhanced with JWT/auth context)
  const [isAdmin] = useState<boolean>(true); // TODO: Replace with actual auth check
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Fetch statistics and communities
  const { stats, loading: statsLoading, error: statsError } = useGraphStatistics();
  const { communities, loading: communitiesLoading } = useCommunities(20);

  // Extract available entity types from statistics
  const availableEntityTypes = stats
    ? Object.keys(stats.entity_type_distribution)
    : ['PERSON', 'ORGANIZATION', 'LOCATION', 'EVENT', 'DATE', 'PRODUCT'];

  // Filter state
  const [filters, setFilters] = useState<GraphFilterValues>({
    entityTypes: availableEntityTypes,
    minDegree: 1,
    maxNodes: 100,
  });

  const [selectedCommunity, setSelectedCommunity] = useState<string | null>(null);

  // Update entity types when statistics load
  useEffect(() => {
    if (stats && stats.entity_type_distribution) {
      const types = Object.keys(stats.entity_type_distribution);
      setFilters((prev) => ({
        ...prev,
        entityTypes: types,
      }));
    }
  }, [stats]);

  // Admin access check (placeholder)
  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-6xl mb-4">🔒</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">
            You need administrator privileges to access this page.
          </p>
          <a
            href="/"
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
          >
            Return to Home
          </a>
        </div>
      </div>
    );
  }

  // Construct graph filters for GraphViewer
  const graphFilters: GraphFiltersType = {
    maxNodes: filters.maxNodes,
    entityTypes: filters.entityTypes,
    highlightCommunities: selectedCommunity ? [selectedCommunity] : undefined,
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b-2 border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Knowledge Graph Analytics</h1>
            <p className="text-sm text-gray-600 mt-1">
              Explore and analyze the complete knowledge graph with advanced filters and statistics
            </p>
          </div>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="lg:hidden px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100
                       hover:bg-gray-200 rounded-lg transition-colors"
            aria-label={sidebarCollapsed ? 'Show filters' : 'Hide filters'}
          >
            {sidebarCollapsed ? 'Show Filters' : 'Hide Filters'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-grow flex overflow-hidden">
        {/* Sidebar */}
        <div
          className={`flex-shrink-0 bg-white border-r-2 border-gray-200 overflow-y-auto transition-all duration-300 ${
            sidebarCollapsed ? 'w-0' : 'w-96'
          }`}
        >
          <div className={`p-6 space-y-6 ${sidebarCollapsed ? 'hidden' : 'block'}`}>
            {/* Statistics Section */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="text-2xl mr-2">📊</span>
                Graph Statistics
              </h2>
              {statsLoading ? (
                <div className="p-4 bg-gray-50 rounded-lg text-center">
                  <div className="animate-pulse text-gray-500">Loading statistics...</div>
                </div>
              ) : statsError ? (
                <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg text-center">
                  <div className="text-sm text-red-600">Failed to load statistics</div>
                </div>
              ) : stats ? (
                <div className="space-y-3">
                  <StatItem label="Total Nodes" value={stats.node_count.toLocaleString()} />
                  <StatItem label="Total Edges" value={stats.edge_count.toLocaleString()} />
                  <StatItem label="Communities" value={stats.community_count.toLocaleString()} />
                  <StatItem label="Avg Degree" value={stats.avg_degree.toFixed(2)} />
                  <StatItem
                    label="Orphaned Nodes"
                    value={stats.orphaned_nodes.toLocaleString()}
                  />
                </div>
              ) : null}
            </section>

            {/* Divider */}
            <div className="border-t-2 border-gray-200" />

            {/* Filters Section */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="text-2xl mr-2">🔍</span>
                Graph Filters
              </h2>
              <GraphFilters
                entityTypes={availableEntityTypes}
                value={filters}
                onChange={setFilters}
              />
            </section>

            {/* Divider */}
            <div className="border-t-2 border-gray-200" />

            {/* Community Highlight Section */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="text-2xl mr-2">👥</span>
                Communities
              </h2>
              {communitiesLoading ? (
                <div className="p-4 bg-gray-50 rounded-lg text-center">
                  <div className="animate-pulse text-gray-500">Loading communities...</div>
                </div>
              ) : (
                <CommunityHighlight
                  communities={communities}
                  selectedCommunity={selectedCommunity}
                  onCommunitySelect={setSelectedCommunity}
                />
              )}
            </section>

            {/* Divider */}
            <div className="border-t-2 border-gray-200" />

            {/* Export Section */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="text-2xl mr-2">💾</span>
                Export Graph
              </h2>
              <GraphExportButton filters={graphFilters} />
            </section>
          </div>
        </div>

        {/* Main Graph Area */}
        <div className="flex-grow relative">
          <GraphViewer
            maxNodes={filters.maxNodes}
            entityTypes={filters.entityTypes}
            highlightCommunities={selectedCommunity ? [selectedCommunity] : undefined}
          />

          {/* Collapse Button (Desktop) */}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden lg:block absolute top-4 left-4 z-20 p-2 bg-white/90 backdrop-blur-sm
                       rounded-lg shadow-lg border border-gray-200 hover:bg-white transition-all"
            aria-label={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
            title={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
          >
            <svg
              className={`w-5 h-5 text-gray-700 transition-transform ${
                sidebarCollapsed ? 'rotate-0' : 'rotate-180'
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Statistic Item Component
 */
interface StatItemProps {
  label: string;
  value: string | number;
}

function StatItem({ label, value }: StatItemProps) {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <span className="text-lg font-bold text-gray-900">{value}</span>
    </div>
  );
}
