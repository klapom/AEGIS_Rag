/**
 * DashboardStatsCard Component
 * Sprint 116 Feature 116.1: Admin Dashboard Stats Cards
 *
 * Displays high-level system statistics in visually appealing cards:
 * - Total Documents
 * - Total Entities
 * - Total Relations
 * - Total Chunks
 * - Active Domains
 * - Storage Used
 *
 * Auto-refreshes every 30 seconds.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  CircleDot,
  Link2,
  Database,
  Folders,
  HardDrive,
  RefreshCw,
} from 'lucide-react';
import type { DashboardStats } from '../../types/admin';
import { getDashboardStats } from '../../api/admin';

/**
 * Props for DashboardStatsCard component
 */
interface DashboardStatsCardProps {
  /** Optional callback when stats are loaded */
  onStatsLoaded?: (stats: DashboardStats) => void;
  /** Disable auto-refresh */
  disableAutoRefresh?: boolean;
}

/**
 * Individual stat card component
 */
function StatCard({
  icon: Icon,
  label,
  value,
  color,
  subtext,
  testId,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  subtext?: string;
  testId?: string;
}) {
  // Color class mappings
  const colorClasses: Record<string, string> = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
  };

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
      data-testid={testId}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{label}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-gray-100" data-testid={`${testId}-value`}>
            {typeof value === 'number' ? value.toLocaleString() : value}
          </p>
          {subtext && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1" data-testid={`${testId}-subtext`}>
              {subtext}
            </p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

/**
 * DashboardStatsCard - Displays system overview statistics
 */
export function DashboardStatsCard({
  onStatsLoaded,
  disableAutoRefresh = false,
}: DashboardStatsCardProps) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDashboardStats();
      setStats(data);
      setLastRefresh(new Date());
      onStatsLoaded?.(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load dashboard stats'));
    } finally {
      setLoading(false);
    }
  }, [onStatsLoaded]);

  // Initial load and auto-refresh
  useEffect(() => {
    void loadStats();

    if (!disableAutoRefresh) {
      const interval = setInterval(() => {
        void loadStats();
      }, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [loadStats, disableAutoRefresh]);

  // Loading skeleton
  if (loading && !stats) {
    return (
      <div className="space-y-4" data-testid="dashboard-stats-loading">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">System Overview</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 animate-pulse"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 space-y-3">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
                  <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                </div>
                <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg" />
              </div>
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
        className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-6"
        data-testid="dashboard-stats-error"
      >
        <div className="flex items-center gap-3">
          <div className="text-red-500 text-2xl">⚠️</div>
          <div>
            <h3 className="font-semibold text-red-700 dark:text-red-400">
              Failed to Load Dashboard Statistics
            </h3>
            <p className="text-sm text-red-600 dark:text-red-300">{error.message}</p>
          </div>
          <button
            onClick={() => void loadStats()}
            className="ml-auto px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            data-testid="retry-button"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="space-y-4" data-testid="dashboard-stats-card">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">System Overview</h3>
        <div className="flex items-center gap-4">
          {lastRefresh && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={() => void loadStats()}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
            data-testid="refresh-stats-button"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          icon={FileText}
          label="Total Documents"
          value={stats.total_documents}
          color="blue"
          subtext="Indexed across all namespaces"
          testId="stat-documents"
        />
        <StatCard
          icon={CircleDot}
          label="Total Entities"
          value={stats.total_entities}
          color="green"
          subtext="In knowledge graph"
          testId="stat-entities"
        />
        <StatCard
          icon={Link2}
          label="Total Relations"
          value={stats.total_relations}
          color="purple"
          subtext="Graph relationships"
          testId="stat-relations"
        />
        <StatCard
          icon={Database}
          label="Total Chunks"
          value={stats.total_chunks}
          color="orange"
          subtext="Vector embeddings in Qdrant"
          testId="stat-chunks"
        />
        <StatCard
          icon={Folders}
          label="Active Domains"
          value={stats.active_domains}
          color="indigo"
          subtext="Configured domain models"
          testId="stat-domains"
        />
        <StatCard
          icon={HardDrive}
          label="Storage Used"
          value={`${stats.storage_used_mb.toFixed(1)} MB`}
          color="red"
          subtext="Approximate vector storage"
          testId="stat-storage"
        />
      </div>
    </div>
  );
}

export default DashboardStatsCard;
