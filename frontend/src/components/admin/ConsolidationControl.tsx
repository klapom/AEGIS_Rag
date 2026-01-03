/**
 * ConsolidationControl Component
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * Manual consolidation trigger with status display and history log.
 * Shows the last 10 consolidation runs with their results.
 */

import { useState, useEffect, useCallback } from 'react';
import { Play, Clock, CheckCircle, XCircle, AlertCircle, Download, RefreshCw } from 'lucide-react';
import type { ConsolidationStatus, ConsolidationHistoryEntry } from '../../types/admin';
import { triggerConsolidation, getConsolidationStatus, exportMemory } from '../../api/admin';

/**
 * Props for ConsolidationControl component
 */
interface ConsolidationControlProps {
  /** Session ID for export functionality */
  sessionId?: string;
}

/**
 * Status badge for consolidation entry
 */
function StatusBadge({ status }: { status: 'running' | 'completed' | 'failed' }) {
  const config = {
    running: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-700 dark:text-blue-400',
      icon: RefreshCw,
      label: 'Running',
    },
    completed: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-400',
      icon: CheckCircle,
      label: 'Completed',
    },
    failed: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-700 dark:text-red-400',
      icon: XCircle,
      label: 'Failed',
    },
  };

  const { bg, text, icon: Icon, label } = config[status];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      <Icon className={`w-3 h-3 ${status === 'running' ? 'animate-spin' : ''}`} />
      {label}
    </span>
  );
}

/**
 * History entry row component
 */
function HistoryRow({ entry }: { entry: ConsolidationHistoryEntry }) {
  const startTime = new Date(entry.started_at);
  const endTime = entry.completed_at ? new Date(entry.completed_at) : null;
  const duration = endTime ? Math.round((endTime.getTime() - startTime.getTime()) / 1000) : null;

  return (
    <div
      className="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700 last:border-b-0"
      data-testid="consolidation-history-row"
    >
      <div className="flex items-center gap-4">
        <StatusBadge status={entry.status} />
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {startTime.toLocaleString()}
          </div>
          {entry.error && (
            <div className="text-xs text-red-600 dark:text-red-400 mt-0.5">{entry.error}</div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div className="text-right">
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {entry.items_processed.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Processed</div>
        </div>
        <div className="text-right">
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {entry.items_consolidated.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Consolidated</div>
        </div>
        {duration !== null && (
          <div className="text-right">
            <div className="font-medium text-gray-900 dark:text-gray-100">{duration}s</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Duration</div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ConsolidationControl - Manual consolidation trigger and status
 */
export function ConsolidationControl({ sessionId }: ConsolidationControlProps) {
  const [status, setStatus] = useState<ConsolidationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [exporting, setExporting] = useState(false);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getConsolidationStatus();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load consolidation status'));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  // Poll while running
  useEffect(() => {
    if (status?.is_running) {
      const interval = setInterval(() => {
        void loadStatus();
      }, 5000); // Poll every 5 seconds
      return () => clearInterval(interval);
    }
  }, [status?.is_running, loadStatus]);

  const handleTrigger = useCallback(async () => {
    setTriggering(true);
    setError(null);
    try {
      const data = await triggerConsolidation();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to trigger consolidation'));
    } finally {
      setTriggering(false);
    }
  }, []);

  const handleExport = useCallback(async () => {
    if (!sessionId) {
      setError(new Error('No session ID provided for export'));
      return;
    }

    setExporting(true);
    setError(null);
    try {
      await exportMemory(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Export failed'));
    } finally {
      setExporting(false);
    }
  }, [sessionId]);

  if (loading && !status) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="consolidation-control">
      {/* Main Control Card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Memory Consolidation</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Consolidate short-term memories into long-term storage for improved retrieval
            </p>
          </div>
          <div className="flex items-center gap-2">
            {sessionId && (
              <button
                onClick={() => void handleExport()}
                disabled={exporting}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
                data-testid="export-memory-button"
              >
                <Download className="w-4 h-4" />
                {exporting ? 'Exporting...' : 'Export'}
              </button>
            )}
            <button
              onClick={() => void loadStatus()}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
              data-testid="refresh-status-button"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Status Display */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Current Status */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              {status?.is_running ? (
                <>
                  <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                  <span className="text-sm font-medium text-blue-700 dark:text-blue-400">
                    Consolidation in progress...
                  </span>
                </>
              ) : (
                <>
                  <div className="w-3 h-3 bg-green-500 rounded-full" />
                  <span className="text-sm font-medium text-green-700 dark:text-green-400">Idle</span>
                </>
              )}
            </div>
            <button
              onClick={() => void handleTrigger()}
              disabled={triggering || status?.is_running}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              data-testid="trigger-consolidation-button"
            >
              {triggering || status?.is_running ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {status?.is_running ? 'Running...' : 'Starting...'}
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Trigger Consolidation
                </>
              )}
            </button>
          </div>

          {/* Last Run Info */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Last Run</span>
            </div>
            {status?.last_run ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
                  <StatusBadge status={status.last_run.status} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Time</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {new Date(status.last_run.started_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Items</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {status.last_run.items_consolidated} / {status.last_run.items_processed}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <AlertCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">No consolidation runs yet</p>
              </div>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              <p className="text-sm text-red-700 dark:text-red-400">{error.message}</p>
            </div>
          </div>
        )}
      </div>

      {/* History Log */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Consolidation History</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Last 10 consolidation runs</p>
        </div>
        <div className="px-6 py-2" data-testid="consolidation-history">
          {status?.history && status.history.length > 0 ? (
            status.history.map((entry) => <HistoryRow key={entry.id} entry={entry} />)
          ) : (
            <div className="py-8 text-center">
              <Clock className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No consolidation history available</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                Trigger a consolidation to see results here
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConsolidationControl;
