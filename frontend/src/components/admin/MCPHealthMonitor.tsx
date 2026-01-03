/**
 * MCPHealthMonitor Component
 * Sprint 72 Feature 72.1: MCP Tool Management UI
 *
 * Real-time health status display for MCP servers.
 * Auto-refreshes every 30 seconds with green/yellow/red status indicators.
 */

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Server, Wrench, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { getMCPHealth } from '../../api/admin';
import type { MCPHealthStatus } from '../../types/admin';

/**
 * MCPHealthMonitor - Real-time health status display
 *
 * Features:
 * - Overall health indicator (healthy/degraded/unhealthy)
 * - Server count and connection status
 * - Tool count
 * - Auto-refresh every 30 seconds
 * - Manual refresh button
 */
export function MCPHealthMonitor() {
  const [health, setHealth] = useState<MCPHealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getMCPHealth();
      setHealth(data);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and auto-refresh every 30 seconds
  useEffect(() => {
    void fetchHealth();
    const interval = setInterval(() => {
      void fetchHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const getStatusColor = (): { bg: string; border: string; text: string } => {
    if (!health) {
      return { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600' };
    }
    if (health.healthy && health.connected_servers === health.total_servers) {
      return { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700' };
    }
    if (health.connected_servers > 0) {
      return { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700' };
    }
    return { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700' };
  };

  const getStatusIcon = () => {
    if (!health) {
      return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
    if (health.healthy && health.connected_servers === health.total_servers) {
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    }
    if (health.connected_servers > 0) {
      return <AlertCircle className="w-5 h-5 text-yellow-500" />;
    }
    return <XCircle className="w-5 h-5 text-red-500" />;
  };

  const getStatusText = (): string => {
    if (!health) return 'Unknown';
    if (health.healthy && health.connected_servers === health.total_servers) {
      return 'All Systems Operational';
    }
    if (health.connected_servers > 0) {
      return 'Partially Connected';
    }
    return 'No Connections';
  };

  const colors = getStatusColor();

  if (error && !health) {
    return (
      <div
        className="rounded-xl border-2 border-red-200 bg-red-50 p-4"
        data-testid="mcp-health-monitor-error"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="font-medium text-red-700">Health Check Failed</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          </div>
          <button
            onClick={() => void fetchHealth()}
            disabled={loading}
            className="p-2 rounded-lg hover:bg-red-100 transition-colors"
            aria-label="Retry health check"
          >
            <RefreshCw className={`w-4 h-4 text-red-500 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border-2 ${colors.border} ${colors.bg} p-4`}
      data-testid="mcp-health-monitor"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <h3 className={`font-semibold ${colors.text}`}>MCP Status</h3>
            <p className={`text-sm ${colors.text} opacity-80`}>{getStatusText()}</p>
          </div>
        </div>
        <button
          onClick={() => void fetchHealth()}
          disabled={loading}
          className="p-2 rounded-lg hover:bg-white/50 transition-colors"
          aria-label="Refresh health status"
          data-testid="mcp-health-refresh"
        >
          <RefreshCw className={`w-4 h-4 ${colors.text} ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {health && (
        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-gray-500" />
            <div>
              <p className="text-xs text-gray-500">Servers</p>
              <p className="font-semibold text-gray-900">
                {health.connected_servers}/{health.total_servers}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Wrench className="w-4 h-4 text-gray-500" />
            <div>
              <p className="text-xs text-gray-500">Tools</p>
              <p className="font-semibold text-gray-900">{health.total_tools}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4 text-gray-500" />
            <div>
              <p className="text-xs text-gray-500">Last Check</p>
              <p className="font-semibold text-gray-900 text-sm">
                {lastRefresh ? lastRefresh.toLocaleTimeString() : '--'}
              </p>
            </div>
          </div>
        </div>
      )}

      {loading && !health && (
        <div className="flex items-center justify-center py-4">
          <RefreshCw className="w-5 h-5 text-gray-400 animate-spin" />
          <span className="ml-2 text-sm text-gray-500">Loading health status...</span>
        </div>
      )}
    </div>
  );
}

export default MCPHealthMonitor;
