/**
 * CommunicationMetrics Component
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 *
 * Displays performance metrics for agent communication system.
 *
 * Features:
 * - Message latency statistics
 * - Orchestration performance
 * - Blackboard write frequency
 * - Error rate monitoring
 * - Auto-refresh every 10 seconds
 */

import { useState, useEffect, useCallback } from 'react';
import { Activity, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { fetchCommunicationMetrics, type CommunicationMetrics } from '../../api/agentCommunication';

interface CommunicationMetricsProps {
  className?: string;
}

/**
 * Metric card component
 */
function MetricCard({
  title,
  value,
  unit,
  subtitle,
  trend,
  color = 'blue',
}: {
  title: string;
  value: number | string;
  unit?: string;
  subtitle?: string;
  trend?: 'up' | 'down';
  color?: 'blue' | 'green' | 'yellow' | 'red';
}) {
  const colorClasses = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
  };

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
      <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">{title}</div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</span>
        {unit && <span className="text-sm text-gray-600 dark:text-gray-400">{unit}</span>}
        {trend && (
          <div className={`ml-auto ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
            {trend === 'up' ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
          </div>
        )}
      </div>
      {subtitle && (
        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">{subtitle}</div>
      )}
    </div>
  );
}

export function CommunicationMetrics({ className = '' }: CommunicationMetricsProps) {
  const [metrics, setMetrics] = useState<CommunicationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Load communication metrics
   */
  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchCommunicationMetrics();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch communication metrics'));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      void loadMetrics();
    }, 10000);

    return () => clearInterval(interval);
  }, [loadMetrics]);

  /**
   * Get health status based on metrics
   */
  const getHealthStatus = (): {
    status: 'healthy' | 'warning' | 'critical';
    message: string;
  } => {
    if (!metrics) return { status: 'warning', message: 'No data' };

    if (metrics.error_rate_pct > 10) {
      return { status: 'critical', message: 'High error rate detected' };
    }

    if (metrics.message_latency_p95_ms > 100 || metrics.orchestration_duration_p95_ms > 5000) {
      return { status: 'warning', message: 'Elevated latency detected' };
    }

    return { status: 'healthy', message: 'All systems operational' };
  };

  const healthStatus = getHealthStatus();

  const healthColorClasses = {
    healthy: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Performance Metrics
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">Real-time system health</p>
          </div>
        </div>

        <button
          onClick={loadMetrics}
          className="px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors text-sm"
          data-testid="refresh-metrics-button"
        >
          Refresh
        </button>
      </div>

      {/* Health Status Banner */}
      {metrics && (
        <div
          className={`mb-4 p-3 rounded-lg flex items-center gap-2 ${healthColorClasses[healthStatus.status]}`}
        >
          {healthStatus.status === 'critical' && <AlertCircle className="w-5 h-5" />}
          <span className="font-medium">{healthStatus.message}</span>
        </div>
      )}

      {/* Metrics Grid */}
      {loading && !metrics && (
        <div className="text-center py-8 text-gray-500">Loading metrics...</div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <span className="text-red-700 dark:text-red-300">{error.message}</span>
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <MetricCard
            title="Message Latency (P95)"
            value={metrics.message_latency_p95_ms}
            unit="ms"
            subtitle={`Avg: ${metrics.message_latency_avg_ms}ms`}
            color={metrics.message_latency_p95_ms < 50 ? 'green' : 'yellow'}
          />

          <MetricCard
            title="Orchestration Duration (Avg)"
            value={(metrics.orchestration_duration_avg_ms / 1000).toFixed(1)}
            unit="s"
            subtitle={`P95: ${(metrics.orchestration_duration_p95_ms / 1000).toFixed(1)}s`}
            color={metrics.orchestration_duration_avg_ms < 2000 ? 'green' : 'yellow'}
          />

          <MetricCard
            title="Blackboard Writes"
            value={metrics.blackboard_writes_last_hour}
            subtitle="Last hour"
            color="blue"
          />

          <MetricCard
            title="Active Orchestrations"
            value={metrics.active_orchestrations}
            subtitle="Currently running"
            color="blue"
          />

          <MetricCard
            title="Messages Per Second"
            value={metrics.messages_per_second.toFixed(1)}
            unit="msg/s"
            color="blue"
          />

          <MetricCard
            title="Error Rate"
            value={metrics.error_rate_pct.toFixed(1)}
            unit="%"
            color={metrics.error_rate_pct < 1 ? 'green' : metrics.error_rate_pct < 5 ? 'yellow' : 'red'}
          />
        </div>
      )}

      {/* Info Footer */}
      {metrics && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Metrics are updated every 10 seconds. P95 = 95th percentile (95% of requests are faster
            than this value).
          </p>
        </div>
      )}
    </div>
  );
}
