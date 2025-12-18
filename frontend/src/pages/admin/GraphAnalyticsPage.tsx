/**
 * GraphAnalyticsPage Component
 * Sprint 29 Feature 29.3: Admin Graph Analytics View
 * Sprint 52 Feature 52.2.1: Enhanced Graph Analytics Dashboard
 *
 * Features:
 * - Admin-only route with role check
 * - Tabbed interface: Analytics Dashboard + Graph Visualization
 * - Analytics Dashboard: Summary cards, distribution charts, health metrics
 * - Graph Visualization: Filters, community explorer, export
 * - Responsive layout with collapsible sidebar
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { GraphViewer } from '../../components/graph/GraphViewer';
import { GraphFilters, type GraphFilterValues } from '../../components/graph/GraphFilters';
import { CommunityHighlight } from '../../components/graph/CommunityHighlight';
import { GraphExportButton } from '../../components/graph/GraphExportButton';
import { useGraphStatistics } from '../../hooks/useGraphStatistics';
import { useCommunities } from '../../hooks/useCommunities';
import { fetchGraphStats, type GraphStats } from '../../api/admin';
import type { GraphFilters as GraphFiltersType, EdgeFilters } from '../../types/graph';

type TabView = 'analytics' | 'visualization';

/**
 * Admin Graph Analytics Page
 *
 * Provides comprehensive graph visualization and analytics tools for administrators.
 * Sprint 52.2.1: Added enhanced analytics dashboard with charts and health metrics.
 */
export function GraphAnalyticsPage() {
  // Admin access check (simple implementation - can be enhanced with JWT/auth context)
  const [isAdmin] = useState<boolean>(true); // TODO: Replace with actual auth check
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<TabView>('analytics');

  // Sprint 52.2.1: Enhanced graph stats from new admin endpoint
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [graphStatsLoading, setGraphStatsLoading] = useState(true);
  const [graphStatsError, setGraphStatsError] = useState<Error | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  // Fetch statistics and communities (for visualization tab)
  const { stats, loading: statsLoading, error: statsError, refetch: refetchStats } = useGraphStatistics();
  const { communities, loading: communitiesLoading } = useCommunities(20);

  // Fetch enhanced graph stats
  const loadGraphStats = useCallback(async () => {
    setGraphStatsLoading(true);
    setGraphStatsError(null);
    try {
      const data = await fetchGraphStats();
      setGraphStats(data);
      setLastRefresh(new Date());
    } catch (err) {
      setGraphStatsError(err instanceof Error ? err : new Error('Failed to fetch graph stats'));
    } finally {
      setGraphStatsLoading(false);
    }
  }, []);

  // Initial load and auto-refresh every 30 seconds
  useEffect(() => {
    void loadGraphStats();
    const interval = setInterval(() => {
      void loadGraphStats();
    }, 30000);
    return () => clearInterval(interval);
  }, [loadGraphStats]);

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

  // Edge filter state for relationship type filtering
  const [edgeFilters, setEdgeFilters] = useState<EdgeFilters>({
    showRelatesTo: true,
    showCoOccurs: true,
    showMentionedIn: true,
    minWeight: 0,
  });

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

  // Handle manual refresh
  const handleRefresh = () => {
    void loadGraphStats();
    refetchStats();
  };

  // Admin access check (placeholder)
  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-6xl mb-4">X</div>
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
        <Link
          to="/admin"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 mb-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Admin
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Knowledge Graph Analytics</h1>
            <p className="text-sm text-gray-600 mt-1">
              Comprehensive analytics and visualization for your knowledge graph
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Tab Buttons */}
            <div className="flex bg-gray-100 rounded-lg p-1" role="tablist">
              <button
                role="tab"
                aria-selected={activeTab === 'analytics'}
                onClick={() => setActiveTab('analytics')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'analytics'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Analytics
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'visualization'}
                onClick={() => setActiveTab('visualization')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === 'visualization'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Visualization
              </button>
            </div>
            {activeTab === 'visualization' && (
              <button
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className="lg:hidden px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100
                           hover:bg-gray-200 rounded-lg transition-colors"
                aria-label={sidebarCollapsed ? 'Show filters' : 'Hide filters'}
              >
                {sidebarCollapsed ? 'Show Filters' : 'Hide Filters'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      {activeTab === 'analytics' ? (
        <AnalyticsDashboard
          stats={graphStats}
          loading={graphStatsLoading}
          error={graphStatsError}
          lastRefresh={lastRefresh}
          onRefresh={handleRefresh}
        />
      ) : (
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
                  <span className="text-2xl mr-2" aria-hidden="true">*</span>
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
                  <div className="space-y-3" data-testid="entity-type-stats">
                    <StatItem label="Total Nodes" value={stats.node_count.toLocaleString()} testid="stat-nodes" />
                    <StatItem label="Total Edges" value={stats.edge_count.toLocaleString()} testid="stat-edges" />
                    <StatItem label="Communities" value={stats.community_count.toLocaleString()} testid="stat-communities" />
                    <StatItem label="Avg Degree" value={stats.avg_degree.toFixed(2)} testid="stat-avg-degree" />
                    <StatItem
                      label="Orphaned Nodes"
                      value={stats.orphaned_nodes.toLocaleString()}
                      testid="stat-orphaned"
                    />
                  </div>
                ) : null}
              </section>

              {/* Divider */}
              <div className="border-t-2 border-gray-200" />

              {/* Filters Section */}
              <section data-testid="graph-filters-section">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="text-2xl mr-2" aria-hidden="true">?</span>
                  Graph Filters
                </h2>
                <GraphFilters
                  entityTypes={availableEntityTypes}
                  value={filters}
                  onChange={setFilters}
                  edgeFilters={edgeFilters}
                  onEdgeFilterChange={setEdgeFilters}
                />
              </section>

              {/* Divider */}
              <div className="border-t-2 border-gray-200" />

              {/* Community Highlight Section */}
              <section>
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="text-2xl mr-2" aria-hidden="true">#</span>
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
                  <span className="text-2xl mr-2" aria-hidden="true">&gt;</span>
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
              edgeFilters={edgeFilters}
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
      )}
    </div>
  );
}

/**
 * Analytics Dashboard Component
 * Sprint 52 Feature 52.2.1: Comprehensive graph analytics view
 */
interface AnalyticsDashboardProps {
  stats: GraphStats | null;
  loading: boolean;
  error: Error | null;
  lastRefresh: Date | null;
  onRefresh: () => void;
}

function AnalyticsDashboard({ stats, loading, error, lastRefresh, onRefresh }: AnalyticsDashboardProps) {
  if (loading && !stats) {
    return (
      <div className="flex-grow p-6 overflow-y-auto">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Loading Skeletons */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white rounded-xl border-2 border-gray-200 p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
                <div className="h-8 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-1/3" />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white rounded-xl border-2 border-gray-200 p-6 animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
                <div className="h-48 bg-gray-100 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-grow p-6 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4 text-red-500">!</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Failed to Load Analytics</h2>
          <p className="text-gray-600 mb-4">{error.message}</p>
          <button
            onClick={onRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex-grow p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4 text-gray-400">?</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Data Available</h2>
          <p className="text-gray-600">Graph statistics are not yet available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-grow p-6 overflow-y-auto" data-testid="analytics-dashboard">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header with Refresh */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Graph Overview</h2>
            {lastRefresh && (
              <p className="text-sm text-gray-500">
                Last updated: {lastRefresh.toLocaleTimeString()}
              </p>
            )}
          </div>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            data-testid="refresh-button"
          >
            <svg
              className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Refresh
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            title="Total Entities"
            value={stats.total_entities}
            icon={<EntityIcon />}
            testId="summary-entities"
          />
          <SummaryCard
            title="Total Relationships"
            value={stats.total_relationships}
            icon={<RelationshipIcon />}
            testId="summary-relationships"
          />
          <SummaryCard
            title="Communities"
            value={stats.community_count}
            icon={<CommunityIcon />}
            testId="summary-communities"
          />
          <SummaryCard
            title="Orphan Nodes"
            value={stats.orphan_nodes}
            icon={<OrphanIcon />}
            status={stats.graph_health}
            testId="summary-orphans"
          />
        </div>

        {/* Graph Health Banner */}
        <GraphHealthBanner health={stats.graph_health} orphanRatio={stats.orphan_nodes / stats.total_entities} />

        {/* Distribution Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Entity Type Distribution */}
          <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Entity Types</h3>
            <DistributionChart
              data={stats.entity_types}
              colorScheme="blue"
              testId="entity-type-chart"
            />
          </div>

          {/* Relationship Type Distribution */}
          <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Relationship Types</h3>
            <DistributionChart
              data={stats.relationship_types}
              colorScheme="purple"
              testId="relationship-type-chart"
            />
          </div>
        </div>

        {/* Community Sizes Chart */}
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Community Size Distribution</h3>
          <CommunitySizeChart sizes={stats.community_sizes} testId="community-size-chart" />
        </div>

        {/* Community Summary Status */}
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Community Summary Status</h3>
          <SummaryStatusCard status={stats.summary_status} testId="summary-status" />
        </div>

        {/* Additional Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Average Degree"
            value={stats.avg_degree.toFixed(2)}
            description="Average connections per node"
            testId="metric-avg-degree"
          />
          <MetricCard
            title="Graph Density"
            value={((stats.total_relationships / (stats.total_entities * (stats.total_entities - 1) / 2)) * 100).toFixed(3) + '%'}
            description="Percentage of possible connections"
            testId="metric-density"
          />
          <MetricCard
            title="Timestamp"
            value={new Date(stats.timestamp).toLocaleString()}
            description="Data collection time"
            testId="metric-timestamp"
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Summary Card Component
 */
interface SummaryCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  status?: string;
  testId?: string;
}

function SummaryCard({ title, value, icon, status, testId }: SummaryCardProps) {
  const statusColors: Record<string, string> = {
    healthy: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    critical: 'bg-red-50 border-red-200',
  };

  const baseClass = status && statusColors[status]
    ? statusColors[status]
    : 'bg-white';

  return (
    <div
      className={`rounded-xl border-2 border-gray-200 p-6 transition-all hover:shadow-md ${baseClass}`}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-500">{icon}</span>
        {status && (
          <span className={`text-xs font-medium px-2 py-1 rounded-full ${
            status === 'healthy' ? 'bg-green-100 text-green-700' :
            status === 'warning' ? 'bg-yellow-100 text-yellow-700' :
            status === 'critical' ? 'bg-red-100 text-red-700' :
            'bg-gray-100 text-gray-700'
          }`}>
            {status}
          </span>
        )}
      </div>
      <div className="text-3xl font-bold text-gray-900 mb-1">
        {value.toLocaleString()}
      </div>
      <div className="text-sm font-medium text-gray-500">{title}</div>
    </div>
  );
}

/**
 * Metric Card Component
 */
interface MetricCardProps {
  title: string;
  value: string;
  description: string;
  testId?: string;
}

function MetricCard({ title, value, description, testId }: MetricCardProps) {
  return (
    <div
      className="bg-white rounded-xl border-2 border-gray-200 p-4"
      data-testid={testId}
    >
      <div className="text-sm font-medium text-gray-500 mb-1">{title}</div>
      <div className="text-xl font-bold text-gray-900 mb-1">{value}</div>
      <div className="text-xs text-gray-400">{description}</div>
    </div>
  );
}

/**
 * Graph Health Banner Component
 */
interface GraphHealthBannerProps {
  health: string;
  orphanRatio: number;
}

function GraphHealthBanner({ health, orphanRatio }: GraphHealthBannerProps) {
  const bannerConfig: Record<string, { bg: string; border: string; text: string; message: string }> = {
    healthy: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      text: 'text-green-800',
      message: 'Your knowledge graph is healthy with good connectivity.',
    },
    warning: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      text: 'text-yellow-800',
      message: `Warning: ${(orphanRatio * 100).toFixed(1)}% of nodes are disconnected. Consider reviewing orphan entities.`,
    },
    critical: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-800',
      message: `Critical: ${(orphanRatio * 100).toFixed(1)}% of nodes are orphaned. Graph connectivity needs attention.`,
    },
  };

  const config = bannerConfig[health] || bannerConfig.healthy;

  return (
    <div
      className={`rounded-xl border-2 p-4 ${config.bg} ${config.border}`}
      data-testid="graph-health-banner"
    >
      <div className="flex items-center gap-3">
        <div className={`text-2xl ${config.text}`}>
          {health === 'healthy' ? 'OK' : health === 'warning' ? '!' : 'X'}
        </div>
        <div>
          <div className={`font-semibold ${config.text}`}>
            Graph Health: {health.charAt(0).toUpperCase() + health.slice(1)}
          </div>
          <div className={`text-sm ${config.text} opacity-80`}>{config.message}</div>
        </div>
      </div>
    </div>
  );
}

/**
 * Distribution Chart Component (Bar Chart)
 * Uses pure CSS for chart visualization (no external library needed)
 */
interface DistributionChartProps {
  data: Record<string, number>;
  colorScheme: 'blue' | 'purple' | 'green';
  testId?: string;
}

function DistributionChart({ data, colorScheme, testId }: DistributionChartProps) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const maxValue = Math.max(...entries.map(([, v]) => v), 1);

  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    green: 'bg-green-500',
  };

  if (entries.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500" data-testid={testId}>
        No data available
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid={testId}>
      {entries.map(([label, count]) => (
        <div key={label} className="flex items-center gap-3">
          <div className="w-28 text-sm font-medium text-gray-700 truncate" title={label}>
            {label || 'Unknown'}
          </div>
          <div className="flex-grow bg-gray-100 rounded-full h-6 relative overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${colorClasses[colorScheme]}`}
              style={{ width: `${(count / maxValue) * 100}%` }}
            />
            <span className="absolute inset-0 flex items-center justify-end pr-2 text-xs font-medium text-gray-700">
              {count.toLocaleString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Community Size Chart Component
 */
interface CommunitySizeChartProps {
  sizes: number[];
  testId?: string;
}

function CommunitySizeChart({ sizes, testId }: CommunitySizeChartProps) {
  if (sizes.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500" data-testid={testId}>
        No communities detected
      </div>
    );
  }

  // Show top 10 communities by size
  const topSizes = sizes.slice(0, 10);
  const maxSize = Math.max(...topSizes, 1);

  return (
    <div data-testid={testId}>
      <div className="flex items-end gap-2 h-48 mb-4">
        {topSizes.map((size, index) => (
          <div
            key={index}
            className="flex-1 bg-indigo-500 rounded-t transition-all hover:bg-indigo-600"
            style={{ height: `${(size / maxSize) * 100}%`, minHeight: '4px' }}
            title={`Community ${index + 1}: ${size} members`}
          />
        ))}
      </div>
      <div className="flex justify-between text-xs text-gray-500">
        <span>Top {topSizes.length} communities by size</span>
        <span>Total: {sizes.length} communities</span>
      </div>
      {sizes.length > 10 && (
        <div className="mt-2 text-xs text-gray-400">
          Showing largest {topSizes.length} of {sizes.length} communities
        </div>
      )}
    </div>
  );
}

/**
 * Summary Status Card Component
 */
interface SummaryStatusCardProps {
  status: { generated: number; pending: number };
  testId?: string;
}

function SummaryStatusCard({ status, testId }: SummaryStatusCardProps) {
  const total = status.generated + status.pending;
  const percentage = total > 0 ? (status.generated / total) * 100 : 0;

  return (
    <div data-testid={testId}>
      <div className="flex items-center gap-6 mb-4">
        <div className="flex-1">
          <div className="text-sm text-gray-500 mb-1">Generated</div>
          <div className="text-2xl font-bold text-green-600">{status.generated}</div>
        </div>
        <div className="flex-1">
          <div className="text-sm text-gray-500 mb-1">Pending</div>
          <div className="text-2xl font-bold text-yellow-600">{status.pending}</div>
        </div>
        <div className="flex-1">
          <div className="text-sm text-gray-500 mb-1">Completion</div>
          <div className="text-2xl font-bold text-blue-600">{percentage.toFixed(0)}%</div>
        </div>
      </div>
      <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className="bg-green-500 h-full rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Icon Components
 */
function EntityIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" strokeWidth={2} />
      <circle cx="12" cy="12" r="3" strokeWidth={2} />
    </svg>
  );
}

function RelationshipIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
  );
}

function CommunityIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  );
}

function OrphanIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
    </svg>
  );
}

/**
 * Statistic Item Component (for visualization sidebar)
 */
interface StatItemProps {
  label: string;
  value: string | number;
  testid?: string;
}

function StatItem({ label, value, testid }: StatItemProps) {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200" data-testid={testid ? `relationship-type-stats-${testid}` : undefined}>
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <span className="text-lg font-bold text-gray-900">{value}</span>
    </div>
  );
}
