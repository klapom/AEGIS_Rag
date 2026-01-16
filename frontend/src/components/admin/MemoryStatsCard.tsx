/**
 * MemoryStatsCard Component
 * Sprint 72 Feature 72.3: Memory Management UI
 * Sprint 106 Fix: Aligned with actual backend API response structure
 *
 * Displays memory statistics for all 3 layers (Redis, Qdrant, Graphiti)
 * with real-time metrics and visual indicators.
 * Auto-refreshes every 30 seconds.
 */

import { useState, useEffect, useCallback } from 'react';
import { Database, HardDrive, Network, RefreshCw, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
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
 * Status badge component
 */
function StatusBadge({ connected, label }: { connected: boolean; label: string }) {
  const icon = connected ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />;
  const bgColor = connected ? 'bg-green-100 dark:bg-green-900/30' : 'bg-red-100 dark:bg-red-900/30';
  const textColor = connected ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400';

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${bgColor} ${textColor}`}
    >
      {icon}
      {label}
    </span>
  );
}

/**
 * Metric display component
 */
function MetricDisplay({
  label,
  value,
  subtext,
}: {
  label: string;
  value: string | number;
  subtext?: string;
}) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        {typeof value === 'number' ? value.toLocaleString() : value}
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
          <div className="text-red-500 text-2xl">⚠️</div>
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

  // Extract Redis key count from keyspace_info
  const redisKeys = stats.short_term.keyspace_info?.db0?.keys || 0;

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
        {/* Redis (Short-term) Stats */}
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          data-testid="redis-stats"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
              <Database className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Redis (Layer 1)</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">Short-term session cache</p>
            </div>
          </div>
          <div className="space-y-4">
            <StatusBadge
              connected={stats.short_term.connected}
              label={stats.short_term.connected ? 'Connected' : 'Disconnected'}
            />
            <div className="grid grid-cols-1 gap-4">
              <MetricDisplay label="Keys Stored" value={redisKeys} />
              {stats.short_term.default_ttl_seconds && (
                <MetricDisplay
                  label="Default TTL"
                  value={`${Math.floor(stats.short_term.default_ttl_seconds / 60)} min`}
                />
              )}
            </div>
            {stats.short_term.connection_url && (
              <div className="text-xs text-gray-400 dark:text-gray-500 font-mono truncate">
                {stats.short_term.connection_url}
              </div>
            )}
          </div>
        </div>

        {/* Qdrant (Long-term) Stats */}
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          data-testid="qdrant-stats"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Qdrant (Layer 2)</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">Vector store for semantic search</p>
            </div>
          </div>
          <div className="space-y-4">
            <StatusBadge
              connected={stats.long_term.available}
              label={stats.long_term.available ? 'Available' : 'Unavailable'}
            />
            {stats.long_term.note && (
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
                <p className="text-xs text-blue-600 dark:text-blue-400">{stats.long_term.note}</p>
              </div>
            )}
          </div>
        </div>

        {/* Graphiti (Episodic) Stats */}
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          data-testid="graphiti-stats"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Network className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100">Graphiti (Layer 3)</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">Temporal memory graph</p>
            </div>
          </div>
          <div className="space-y-4">
            <StatusBadge
              connected={stats.episodic.enabled && stats.episodic.available}
              label={stats.episodic.enabled ? 'Enabled' : 'Disabled'}
            />
            {stats.episodic.error && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-yellow-700 dark:text-yellow-300">{stats.episodic.error}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Consolidation Status */}
      {stats.consolidation && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-gray-600 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">Memory Consolidation</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
              <span>
                Status: <span className={stats.consolidation.enabled ? 'text-green-600' : 'text-gray-500'}>
                  {stats.consolidation.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </span>
              {stats.consolidation.interval_minutes && (
                <span>Interval: {stats.consolidation.interval_minutes} min</span>
              )}
              {stats.consolidation.min_access_count && (
                <span>Min access: {stats.consolidation.min_access_count}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MemoryStatsCard;
