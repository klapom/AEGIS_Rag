/**
 * KnowledgeGraphDashboard Component
 * Sprint 29 Feature 29.4: Knowledge Graph Dashboard
 *
 * Main dashboard page displaying high-level statistics and insights about the knowledge graph
 * Includes:
 * - 4 stat cards: Nodes, Edges, Communities, Avg Degree
 * - 2 chart placeholders: Entity type distribution, Growth timeline
 * - Top 10 communities table
 * - Health metrics section
 * - Auto-refresh every 30 seconds (optional)
 */

import { useState, useEffect } from 'react';
import { useGraphStatistics } from '../../hooks/useGraphStatistics';
import { useTopCommunities } from '../../hooks/useTopCommunities';
import { GraphStatistics } from './GraphStatistics';
import { TopCommunities } from './TopCommunities';

interface KnowledgeGraphDashboardProps {
  autoRefresh?: boolean; // Enable auto-refresh every 30 seconds
  onCommunityClick?: (communityId: string) => void;
}

export function KnowledgeGraphDashboard({
  autoRefresh = false,
  onCommunityClick,
}: KnowledgeGraphDashboardProps) {
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Fetch statistics with optional auto-refresh (30 seconds)
  const { stats, loading: statsLoading, error: statsError, refetch: refetchStats } =
    useGraphStatistics(autoRefresh ? 30000 : undefined);

  // Fetch top 10 communities
  const { communities, loading: communitiesLoading, error: communitiesError, refetch: refetchCommunities } =
    useTopCommunities(10);

  // Update last refresh timestamp when data changes
  useEffect(() => {
    if (stats) {
      setLastRefresh(new Date());
    }
  }, [stats]);

  // Manual refresh handler
  const handleRefresh = () => {
    refetchStats();
    refetchCommunities();
    setLastRefresh(new Date());
  };

  const loading = statsLoading || communitiesLoading;
  const error = statsError || communitiesError;

  if (loading && !stats) {
    return <DashboardSkeleton />;
  }

  if (error) {
    return <ErrorDisplay error={error} onRetry={handleRefresh} />;
  }

  if (!stats) {
    return <EmptyState />;
  }

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Knowledge Graph Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {lastRefresh.toLocaleTimeString('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            })}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover
                     transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                     flex items-center space-x-2"
        >
          <span className={loading ? 'animate-spin' : ''}>🔄</span>
          <span>Refresh</span>
        </button>
      </div>

      {/* Quick Stats Grid */}
      <GraphStatistics stats={stats} />

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Entity Type Distribution */}
        <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Entity Types</h2>
          <EntityTypeDistribution distribution={stats.entity_type_distribution} />
        </div>

        {/* Growth Timeline Placeholder */}
        <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Graph Growth (Last 30 Days)
          </h2>
          <GrowthTimelinePlaceholder />
        </div>
      </div>

      {/* Top Communities */}
      <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Top 10 Communities</h2>
          <p className="text-sm text-gray-500 mt-1">
            Largest communities by member count
          </p>
        </div>
        <TopCommunities
          communities={communities}
          onCommunityClick={onCommunityClick}
        />
      </div>

      {/* Health Metrics */}
      <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Graph Health</h2>
        <HealthMetrics
          orphanedNodes={stats.orphaned_nodes}
          disconnectedComponents={stats.disconnected_components}
          largestComponentSize={stats.largest_component_size}
        />
      </div>
    </div>
  );
}

// Skeleton loader for initial loading state
function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen animate-pulse">
      <div className="h-12 bg-gray-200 rounded w-1/3" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-gray-200 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <div key={i} className="h-64 bg-gray-200 rounded-xl" />
        ))}
      </div>
      <div className="h-96 bg-gray-200 rounded-xl" />
    </div>
  );
}

// Error display component
function ErrorDisplay({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div className="p-6 flex items-center justify-center min-h-screen bg-gray-50">
      <div className="max-w-md w-full bg-white border-2 border-red-200 rounded-xl p-8 text-center">
        <div className="text-6xl mb-4">⚠️</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load Dashboard</h2>
        <p className="text-gray-600 mb-6">{error.message}</p>
        <button
          onClick={onRetry}
          className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

// Empty state component
function EmptyState() {
  return (
    <div className="p-6 flex items-center justify-center min-h-screen bg-gray-50">
      <div className="max-w-md w-full bg-white border-2 border-gray-200 rounded-xl p-8 text-center">
        <div className="text-6xl mb-4">📊</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">No Graph Data Available</h2>
        <p className="text-gray-600">
          The knowledge graph is empty. Start by ingesting some documents.
        </p>
      </div>
    </div>
  );
}

// Entity type distribution component (simple bar chart)
function EntityTypeDistribution({ distribution }: { distribution: Record<string, number> }) {
  const types = Object.entries(distribution).sort((a, b) => b[1] - a[1]);
  const maxCount = Math.max(...types.map(([, count]) => count), 1);

  if (types.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No entity types found</p>
      </div>
    );
  }

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      PERSON: 'bg-blue-500',
      ORGANIZATION: 'bg-purple-500',
      LOCATION: 'bg-green-500',
      DATE: 'bg-orange-500',
      EVENT: 'bg-red-500',
      CONCEPT: 'bg-yellow-500',
    };
    return colors[type.toUpperCase()] || 'bg-gray-500';
  };

  return (
    <div className="space-y-4">
      {types.map(([type, count]) => (
        <div key={type}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-gray-700">{type}</span>
            <span className="text-sm text-gray-600">{count.toLocaleString()}</span>
          </div>
          <div className="h-6 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${getTypeColor(type)} transition-all duration-500`}
              style={{ width: `${(count / maxCount) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// Growth timeline placeholder (will be replaced with actual chart in future)
function GrowthTimelinePlaceholder() {
  return (
    <div className="flex items-center justify-center h-64 border-2 border-dashed border-gray-300 rounded-lg">
      <div className="text-center text-gray-500">
        <div className="text-4xl mb-2">📈</div>
        <p className="text-sm">Growth timeline chart</p>
        <p className="text-xs mt-1">(Coming soon)</p>
      </div>
    </div>
  );
}

// Health metrics component
interface HealthMetricsProps {
  orphanedNodes: number;
  disconnectedComponents?: number;
  largestComponentSize?: number;
}

function HealthMetrics({
  orphanedNodes,
  disconnectedComponents,
  largestComponentSize,
}: HealthMetricsProps) {
  const getHealthStatus = () => {
    if (orphanedNodes === 0 && (disconnectedComponents || 0) <= 1) {
      return { status: 'Excellent', color: 'text-green-600', emoji: '✅' };
    }
    if (orphanedNodes < 10 && (disconnectedComponents || 0) <= 3) {
      return { status: 'Good', color: 'text-blue-600', emoji: '👍' };
    }
    if (orphanedNodes < 50 && (disconnectedComponents || 0) <= 5) {
      return { status: 'Fair', color: 'text-yellow-600', emoji: '⚠️' };
    }
    return { status: 'Needs Attention', color: 'text-red-600', emoji: '❌' };
  };

  const health = getHealthStatus();

  return (
    <div className="space-y-4">
      {/* Overall Health Status */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-3xl">{health.emoji}</span>
            <div>
              <div className="text-sm text-gray-500">Overall Health</div>
              <div className={`text-lg font-semibold ${health.color}`}>
                {health.status}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Orphaned Nodes */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="text-sm text-gray-500 mb-1">Orphaned Nodes</div>
          <div className="text-2xl font-bold text-gray-900">{orphanedNodes}</div>
          <div className="text-xs text-gray-500 mt-1">Nodes with no connections</div>
        </div>

        {/* Disconnected Components */}
        {disconnectedComponents !== undefined && (
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-500 mb-1">Disconnected Components</div>
            <div className="text-2xl font-bold text-gray-900">{disconnectedComponents}</div>
            <div className="text-xs text-gray-500 mt-1">Isolated graph clusters</div>
          </div>
        )}

        {/* Largest Component */}
        {largestComponentSize !== undefined && (
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="text-sm text-gray-500 mb-1">Largest Component</div>
            <div className="text-2xl font-bold text-gray-900">{largestComponentSize}</div>
            <div className="text-xs text-gray-500 mt-1">Nodes in main cluster</div>
          </div>
        )}
      </div>
    </div>
  );
}
