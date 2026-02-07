/**
 * SkillLifecycle Page Component
 * Sprint 97 Feature 97.4: Skill Lifecycle Dashboard (6 SP)
 *
 * Features:
 * - Real-time metrics (active skills, tool calls)
 * - Performance charts (latency, errors)
 * - Execution history timeline
 * - Policy violation alerts
 * - Top tool usage statistics
 *
 * Route: /admin/skills/lifecycle
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, AlertTriangle, TrendingUp, RefreshCw } from 'lucide-react';
import { getLifecycleMetrics } from '../../api/skills';
import type { LifecycleDashboardMetrics } from '../../types/skills';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

export function SkillLifecycleDashboard() {
  // Data state
  const [metrics, setMetrics] = useState<LifecycleDashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  // Load metrics
  const loadMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getLifecycleMetrics();
      setMetrics(data);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load lifecycle metrics');
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mb-4">
        <AdminNavigationBar />
      </div>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin/skills/registry"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Registry
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Skill Lifecycle Dashboard
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {lastRefresh && `Last updated: ${lastRefresh.toLocaleTimeString()}`}
              </p>
            </div>
            <button
              onClick={loadMetrics}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && !metrics && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-gray-600 dark:text-gray-400">Loading metrics...</p>
          </div>
        )}

        {/* Dashboard */}
        {metrics && (
          <div className="space-y-6">
            {/* Key Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Active Skills */}
              <MetricCard
                title="Active Skills"
                value={`${metrics.active_skills_count}/${metrics.total_skills_count}`}
                subtitle={`${Math.round((metrics.active_skills_count / metrics.total_skills_count) * 100)}% active`}
                icon={<Activity className="w-6 h-6" />}
                color="blue"
              />

              {/* Tool Calls (24h) */}
              <MetricCard
                title="Tool Calls (24h)"
                value={metrics.tool_calls_24h.toLocaleString()}
                subtitle={
                  metrics.tool_calls_change_percent >= 0
                    ? `+${metrics.tool_calls_change_percent.toFixed(0)}% vs yesterday`
                    : `${metrics.tool_calls_change_percent.toFixed(0)}% vs yesterday`
                }
                icon={<TrendingUp className="w-6 h-6" />}
                color="green"
              />

              {/* Policy Alerts */}
              <MetricCard
                title="Policy Alerts"
                value={metrics.policy_alerts.length.toString()}
                subtitle={
                  metrics.policy_alerts.filter((a) => a.severity === 'critical').length > 0
                    ? `${metrics.policy_alerts.filter((a) => a.severity === 'critical').length} critical`
                    : 'All systems normal'
                }
                icon={<AlertTriangle className="w-6 h-6" />}
                color={metrics.policy_alerts.length > 0 ? 'red' : 'gray'}
              />
            </div>

            {/* Activation Timeline */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
              <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                Skill Activation Timeline (Last 24 Hours)
              </h3>

              {metrics.skill_activation_timeline.length > 0 ? (
                <div className="space-y-2">
                  {/* Group activations by skill */}
                  {Object.entries(
                    metrics.skill_activation_timeline.reduce((acc, entry) => {
                      if (!acc[entry.skill_name]) {
                        acc[entry.skill_name] = [];
                      }
                      acc[entry.skill_name].push(entry);
                      return acc;
                    }, {} as Record<string, typeof metrics.skill_activation_timeline>)
                  ).map(([skillName, entries]) => (
                    <div key={skillName} className="flex items-center gap-4">
                      <span className="w-32 text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {skillName}
                      </span>
                      <div className="flex-1 h-8 bg-gray-100 dark:bg-gray-700 rounded relative overflow-hidden">
                        {entries.map((entry, i) => {
                          const timestamp = new Date(entry.timestamp);
                          const now = new Date();
                          const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                          const position = ((timestamp.getTime() - dayAgo.getTime()) / (24 * 60 * 60 * 1000)) * 100;
                          const width = Math.max(1, (entry.duration_ms / 1000 / 60) * 0.1); // Rough approximation

                          return (
                            <div
                              key={i}
                              className="absolute h-full bg-blue-500"
                              style={{
                                left: `${position}%`,
                                width: `${width}%`,
                              }}
                              title={`${timestamp.toLocaleTimeString()} - ${entry.duration_ms}ms`}
                            />
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">No activations in the last 24 hours</p>
              )}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Tool Usage */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                  Top Tool Usage
                </h3>

                {metrics.top_tools.length > 0 ? (
                  <div className="space-y-3">
                    {metrics.top_tools.map((tool, i) => (
                      <div key={tool.tool_name} className="flex items-center gap-3">
                        <span className="w-6 text-sm font-medium text-gray-500 dark:text-gray-400">
                          {i + 1}.
                        </span>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {tool.tool_name}
                            </span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              {tool.call_count.toLocaleString()} calls
                            </span>
                          </div>
                          <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500"
                              style={{
                                width: `${(tool.call_count / metrics.top_tools[0].call_count) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No tool usage data</p>
                )}
              </div>

              {/* Recent Policy Violations */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                  Recent Policy Violations
                </h3>

                {metrics.policy_alerts.length > 0 ? (
                  <div className="space-y-3">
                    {metrics.policy_alerts.slice(0, 5).map((alert) => (
                      <div
                        key={alert.id}
                        className={`p-3 rounded-lg border ${
                          alert.severity === 'critical'
                            ? 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
                            : 'bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <AlertTriangle
                            className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                              alert.severity === 'critical'
                                ? 'text-red-600 dark:text-red-400'
                                : 'text-yellow-600 dark:text-yellow-400'
                            }`}
                          />
                          <div className="flex-1 min-w-0">
                            <p
                              className={`text-sm font-medium ${
                                alert.severity === 'critical'
                                  ? 'text-red-800 dark:text-red-200'
                                  : 'text-yellow-800 dark:text-yellow-200'
                              }`}
                            >
                              {alert.type.replace(/_/g, ' ').toUpperCase()}
                            </p>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{alert.message}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                              {alert.skill_name} → {alert.tool_name} • {new Date(alert.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <Activity className="w-5 h-5" />
                    <p className="text-sm font-medium">All systems operating normally</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ============================================================================
// MetricCard Component
// ============================================================================

interface MetricCardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'red' | 'gray';
}

function MetricCard({ title, value, subtitle, icon, color }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    gray: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
      <div>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
        <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">{value}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>
      </div>
    </div>
  );
}

export default SkillLifecycleDashboard;
