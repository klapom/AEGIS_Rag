/**
 * MemoryStatsCard Component
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * Displays memory statistics for all 3 layers (Redis, Qdrant, Graphiti)
 * with real-time metrics and visual indicators.
 * Auto-refreshes every 30 seconds.
 */

import { useState, useEffect, useCallback } from 'react';
import { Database, HardDrive, Network, RefreshCw } from 'lucide-react';
import type { MemoryStats } from '../../types/admin';
import { getMemoryStats } from '../../api/admin';

/**
 * Props for MemoryStatsCard component
 */
interface MemoryStatsCardProps {
  /** Optional callback when stats are loaded */
  onStatsLoaded?: (stats: MemoryStats) => void;
  /** Disable auto-refresh */
  disableAutoRefresh?: boolean;
}

/**
 * Progress bar component for displaying metrics
 */
function ProgressBar({
  value,
  max,
  label,
  color = 'blue',
}: {
  value: number;
  max: number;
  label: string;
  color?: 'blue' | 'green' | 'purple' | 'orange';
}) {
  const percentage = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    orange: 'bg-orange-500',
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
        <span>{label}</span>
        <span>{value.toLocaleString()}</span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClasses[color]} rounded-full transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Metric display component
 */
function MetricDisplay({
  label,
  value,
  unit,
  subtext,
}: {
  label: string;
  value: string | number;
  unit?: string;
  subtext?: string;
}) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        {typeof value === 'number' ? value.toLocaleString() : value}
        {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      {subtext && <div className="text-xs text-gray-400 dark:text-gray-500">{subtext}</div>}
    </div>
  );
}

/**
 * MemoryStatsCard - Displays memory statistics for all layers
 */
export function MemoryStatsCard({ onStatsLoaded, disableAutoRefresh = false }: MemoryStatsCardProps) {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMemoryStats();
      setStats(data);
      setLastRefresh(new Date());
      onStatsLoaded?.(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load memory stats'));
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

  if (loading && !stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 animate-pulse"
          >
            <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-4" />
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-6">
        <div className="flex items-center gap-3">
          <div className="text-red-500 text-2xl">!</div>
          <div>
            <h3 className="font-semibold text-red-700 dark:text-red-400">Failed to Load Memory Stats</h3>
            <p className="text-sm text-red-600 dark:text-red-300">{error.message}</p>
          </div>
          <button
            onClick={() => void loadStats()}
            className="ml-auto px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
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
    <div className="space-y-4" data-testid="memory-stats-card">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Memory Layer Statistics</h3>
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

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Redis Stats */}
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          data-testid="redis-stats"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
              <Database className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Redis</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">Session Cache</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <MetricDisplay label="Keys" value={stats.redis.keys} />
              <MetricDisplay label="Memory" value={stats.redis.memory_mb.toFixed(1)} unit="MB" />
            </div>
            <ProgressBar
              value={stats.redis.hit_rate * 100}
              max={100}
              label="Cache Hit Rate"
              color="green"
            />
            <div className="text-center">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  stats.redis.hit_rate >= 0.8
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                    : stats.redis.hit_rate >= 0.5
                    ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                }`}
              >
                {(stats.redis.hit_rate * 100).toFixed(1)}% Hit Rate
              </span>
            </div>
          </div>
        </div>

        {/* Qdrant Stats */}
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          data-testid="qdrant-stats"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Qdrant</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">Vector Store</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <MetricDisplay label="Documents" value={stats.qdrant.documents} />
              <MetricDisplay label="Size" value={stats.qdrant.size_mb.toFixed(1)} unit="MB" />
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {stats.qdrant.avg_search_latency_ms.toFixed(1)} ms
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Avg Search Latency</div>
            </div>
            <div className="text-center">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  stats.qdrant.avg_search_latency_ms <= 50
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                    : stats.qdrant.avg_search_latency_ms <= 200
                    ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                }`}
              >
                {stats.qdrant.avg_search_latency_ms <= 50
                  ? 'Excellent'
                  : stats.qdrant.avg_search_latency_ms <= 200
                  ? 'Good'
                  : 'Slow'}
              </span>
            </div>
          </div>
        </div>

        {/* Graphiti Stats */}
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          data-testid="graphiti-stats"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Network className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Graphiti</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">Temporal Memory</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <MetricDisplay label="Episodes" value={stats.graphiti.episodes} />
              <MetricDisplay label="Entities" value={stats.graphiti.entities} />
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                {stats.graphiti.avg_search_latency_ms.toFixed(1)} ms
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">Avg Search Latency</div>
            </div>
            <div className="text-center">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  stats.graphiti.avg_search_latency_ms <= 100
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                    : stats.graphiti.avg_search_latency_ms <= 300
                    ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                }`}
              >
                {stats.graphiti.avg_search_latency_ms <= 100
                  ? 'Excellent'
                  : stats.graphiti.avg_search_latency_ms <= 300
                  ? 'Good'
                  : 'Slow'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default MemoryStatsCard;
