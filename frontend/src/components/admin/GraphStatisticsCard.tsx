/**
 * GraphStatisticsCard Component
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 *
 * Displays read-only graph statistics in a card layout:
 * - Total Entities count
 * - Total Relationships count
 * - Total Communities count
 * - Community Summary Status (generated/pending)
 */

import { RefreshCw, CircleDot, Link2, Users, FileText } from 'lucide-react';
import type { GraphOperationsStats } from '../../api/graphOperations';

interface GraphStatisticsCardProps {
  /** Graph statistics data */
  stats: GraphOperationsStats | null;
  /** Loading state */
  loading: boolean;
  /** Error state */
  error: Error | null;
  /** Last refresh timestamp */
  lastRefresh: Date | null;
  /** Callback to trigger manual refresh */
  onRefresh: () => void;
}

/**
 * GraphStatisticsCard displays key graph metrics in a clean card layout.
 *
 * Features:
 * - Total entities, relationships, communities counts
 * - Community summary generation status (progress bar)
 * - Graph health indicator
 * - Manual refresh button with loading animation
 * - Last updated timestamp
 */
export function GraphStatisticsCard({
  stats,
  loading,
  error,
  lastRefresh,
  onRefresh,
}: GraphStatisticsCardProps) {
  // Loading skeleton
  if (loading && !stats) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6"
        data-testid="graph-statistics-loading"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-40 animate-pulse" />
          <div className="h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20 animate-pulse" />
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-16 animate-pulse" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="bg-red-50 dark:bg-red-900/20 rounded-xl border-2 border-red-200 dark:border-red-800 p-6"
        data-testid="graph-statistics-error"
      >
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            Failed to Load Statistics
          </h3>
          <button
            onClick={onRefresh}
            className="p-2 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
            aria-label="Retry loading statistics"
            data-testid="graph-statistics-retry"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-red-600 dark:text-red-400">{error.message}</p>
      </div>
    );
  }

  // No data state
  if (!stats) {
    return (
      <div
        className="bg-gray-50 dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 text-center"
        data-testid="graph-statistics-empty"
      >
        <p className="text-gray-500 dark:text-gray-400">No statistics available</p>
        <button
          onClick={onRefresh}
          className="mt-2 px-4 py-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          Load Statistics
        </button>
      </div>
    );
  }

  // Calculate summary progress
  const totalSummaries = stats.summary_status.generated + stats.summary_status.pending;
  const summaryProgress =
    totalSummaries > 0 ? (stats.summary_status.generated / totalSummaries) * 100 : 0;

  // Health color mapping
  const healthColors: Record<string, string> = {
    healthy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  };

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6"
      data-testid="graph-statistics-card"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Graph Statistics
          </h3>
          {lastRefresh && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Health Badge */}
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full ${healthColors[stats.graph_health] || healthColors.unknown}`}
            data-testid="graph-health-badge"
          >
            {stats.graph_health}
          </span>
          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            aria-label="Refresh statistics"
            data-testid="graph-statistics-refresh"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {/* Total Entities */}
        <div className="space-y-1" data-testid="stat-entities">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <CircleDot className="w-4 h-4" />
            <span className="text-sm font-medium">Entities</span>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.total_entities.toLocaleString()}
          </p>
        </div>

        {/* Total Relationships */}
        <div className="space-y-1" data-testid="stat-relationships">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <Link2 className="w-4 h-4" />
            <span className="text-sm font-medium">Relationships</span>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.total_relationships.toLocaleString()}
          </p>
        </div>

        {/* Total Communities */}
        <div className="space-y-1" data-testid="stat-communities">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <Users className="w-4 h-4" />
            <span className="text-sm font-medium">Communities</span>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.community_count.toLocaleString()}
          </p>
        </div>

        {/* Summaries Generated */}
        <div className="space-y-1" data-testid="stat-summaries">
          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
            <FileText className="w-4 h-4" />
            <span className="text-sm font-medium">Summaries</span>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {stats.summary_status.generated}/{totalSummaries}
          </p>
        </div>
      </div>

      {/* Summary Progress Bar */}
      <div className="mt-6">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-600 dark:text-gray-400">Community Summaries</span>
          <span className="text-gray-900 dark:text-gray-100 font-medium">
            {summaryProgress.toFixed(0)}% complete
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
          <div
            className="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${summaryProgress}%` }}
            data-testid="summary-progress-bar"
            role="progressbar"
            aria-valuenow={summaryProgress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>{stats.summary_status.generated} generated</span>
          <span>{stats.summary_status.pending} pending</span>
        </div>
      </div>
    </div>
  );
}
