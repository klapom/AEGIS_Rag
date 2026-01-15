/**
 * OrchestrationTimeline Component
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 *
 * Displays active skill orchestration workflows with phase progress.
 *
 * Features:
 * - List all active orchestrations
 * - Show phase progress and skill status
 * - View detailed trace timeline
 * - Auto-refresh every 5 seconds
 */

import { useState, useEffect, useCallback } from 'react';
import { GitBranch, Clock, AlertCircle, CheckCircle, Loader2, XCircle } from 'lucide-react';
import {
  fetchActiveOrchestrations,
  fetchOrchestrationTrace,
  type ActiveOrchestration,
  type OrchestrationTraceResponse,
} from '../../api/agentCommunication';

interface OrchestrationTimelineProps {
  className?: string;
}

/**
 * Skill status icons
 */
const SKILL_STATUS_ICONS = {
  pending: <Clock className="w-3 h-3 text-gray-400" />,
  running: <Loader2 className="w-3 h-3 text-blue-600 animate-spin" />,
  completed: <CheckCircle className="w-3 h-3 text-green-600" />,
  failed: <XCircle className="w-3 h-3 text-red-600" />,
};

export function OrchestrationTimeline({ className = '' }: OrchestrationTimelineProps) {
  const [orchestrations, setOrchestrations] = useState<ActiveOrchestration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedTrace, setSelectedTrace] = useState<OrchestrationTraceResponse | null>(null);
  const [loadingTrace, setLoadingTrace] = useState(false);

  /**
   * Load active orchestrations
   */
  const loadOrchestrations = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchActiveOrchestrations();
      setOrchestrations(response.orchestrations);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch orchestrations'));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void loadOrchestrations();
  }, [loadOrchestrations]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      void loadOrchestrations();
    }, 5000);

    return () => clearInterval(interval);
  }, [loadOrchestrations]);

  /**
   * Load orchestration trace timeline
   */
  const loadTrace = async (orchestrationId: string) => {
    setLoadingTrace(true);

    try {
      const trace = await fetchOrchestrationTrace(orchestrationId);
      setSelectedTrace(trace);
    } catch (err) {
      console.error('Failed to load trace:', err);
    } finally {
      setLoadingTrace(false);
    }
  };

  /**
   * Format duration
   */
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  /**
   * Get status badge color
   */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      case 'paused':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'completed':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400';
    }
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
            <GitBranch className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Active Orchestrations
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {orchestrations.length} running workflows
            </p>
          </div>
        </div>

        <button
          onClick={loadOrchestrations}
          className="px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors text-sm"
          data-testid="refresh-orchestrations-button"
        >
          Refresh
        </button>
      </div>

      {/* Orchestrations List */}
      <div className="space-y-4 max-h-96 overflow-y-auto">
        {loading && orchestrations.length === 0 && (
          <div className="text-center py-8 text-gray-500">Loading orchestrations...</div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error.message}</span>
          </div>
        )}

        {!loading && !error && orchestrations.length === 0 && (
          <div className="text-center py-8 text-gray-500">No active orchestrations</div>
        )}

        {orchestrations.map((orchestration) => (
          <div
            key={orchestration.orchestration_id}
            className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
            data-testid={`orchestration-${orchestration.orchestration_id}`}
          >
            {/* Orchestration Header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {orchestration.workflow_name}
                </div>
                <div className="text-xs font-mono text-gray-500 dark:text-gray-400 mt-1">
                  {orchestration.orchestration_id}
                </div>
              </div>

              <span
                className={`text-xs px-2 py-1 rounded font-medium ${getStatusColor(orchestration.status)}`}
              >
                {orchestration.status}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="mb-3">
              <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                <span>
                  Phase {orchestration.current_phase}/{orchestration.total_phases}
                </span>
                <span>{orchestration.progress_pct}% complete</span>
              </div>
              <div className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-300"
                  style={{ width: `${orchestration.progress_pct}%` }}
                />
              </div>
            </div>

            {/* Skills Status */}
            <div className="space-y-1 mb-3">
              <div className="text-xs font-medium text-gray-700 dark:text-gray-300">Skills:</div>
              <div className="flex flex-wrap gap-2">
                {orchestration.skills.map((skill, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-1 px-2 py-1 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600 text-xs"
                  >
                    {SKILL_STATUS_ICONS[skill.status]}
                    <span className="text-gray-700 dark:text-gray-300">{skill.skill_name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Duration & Actions */}
            <div className="flex items-center justify-between">
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Started {new Date(orchestration.started_at).toLocaleTimeString()}
                {orchestration.duration_ms && ` • ${formatDuration(orchestration.duration_ms)}`}
              </div>

              <button
                onClick={() => loadTrace(orchestration.orchestration_id)}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                data-testid={`view-trace-${orchestration.orchestration_id}`}
              >
                View Timeline
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Trace Timeline Modal */}
      {selectedTrace && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedTrace(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-3xl w-full max-h-[80vh] overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Orchestration Timeline
              </h3>
              <button
                onClick={() => setSelectedTrace(null)}
                className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            {loadingTrace && <div className="text-center py-8">Loading trace...</div>}

            {!loadingTrace && (
              <div className="space-y-4">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Total Duration: {formatDuration(selectedTrace.total_duration_ms)}
                </div>

                <div className="space-y-2">
                  {selectedTrace.events.map((event, index) => (
                    <div
                      key={index}
                      className="flex gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                    >
                      <div className="text-xs font-mono text-gray-500 dark:text-gray-400 w-20">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {event.event_type}
                          {event.skill_name && ` - ${event.skill_name}`}
                        </div>
                        {event.duration_ms && (
                          <div className="text-xs text-gray-600 dark:text-gray-400">
                            Duration: {formatDuration(event.duration_ms)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
