/**
 * AgentDetailsPanel Component
 * Sprint 98 Feature 98.2: Agent Hierarchy Visualizer
 *
 * Displays detailed information for a selected agent.
 *
 * Features:
 * - Agent metadata (level, skills, status)
 * - Performance metrics (success rate, latency)
 * - Active and completed tasks
 * - Parent/child relationships
 */

import { useEffect, useState, useCallback } from 'react';
import {
  User,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import {
  fetchAgentDetails,
  fetchAgentCurrentTasks,
  type AgentDetails,
  type CurrentTask,
} from '../../api/agentHierarchy';

interface AgentDetailsPanelProps {
  agentId: string | null;
  onClose?: () => void;
  className?: string;
}

/**
 * Agent status colors
 */
const STATUS_COLORS = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  idle: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  busy: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  offline: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

/**
 * Agent level colors
 */
const LEVEL_COLORS = {
  EXECUTIVE: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  MANAGER: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  WORKER: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
};

export function AgentDetailsPanel({ agentId, onClose, className = '' }: AgentDetailsPanelProps) {
  const [details, setDetails] = useState<AgentDetails | null>(null);
  const [tasks, setTasks] = useState<CurrentTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Load agent details and tasks
   */
  const loadAgentData = useCallback(async () => {
    if (!agentId) return;

    setLoading(true);
    setError(null);

    try {
      const [detailsData, tasksData] = await Promise.all([
        fetchAgentDetails(agentId),
        fetchAgentCurrentTasks(agentId),
      ]);

      setDetails(detailsData);
      setTasks(tasksData.tasks);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load agent data'));
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  // Load data when agent changes
  useEffect(() => {
    void loadAgentData();
  }, [loadAgentData]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    if (!agentId) return;

    const interval = setInterval(() => {
      void loadAgentData();
    }, 5000);

    return () => clearInterval(interval);
  }, [agentId, loadAgentData]);

  /**
   * Format timestamp
   */
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!agentId) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}
      >
        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
          <User className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p className="text-sm">Select an agent from the hierarchy tree to view details</p>
        </div>
      </div>
    );
  }

  if (loading && !details) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}
      >
        <div className="text-center text-gray-500 dark:text-gray-400 py-8">
          <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin" />
          <p className="text-sm">Loading agent details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}
      >
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <span className="text-red-700 dark:text-red-300">{error.message}</span>
        </div>
      </div>
    );
  }

  if (!details) return null;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}
      data-testid={`agent-details-${details.agent_id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
            <User className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100" data-testid="agent-name">
              {details.agent_name}
            </h3>
            <p className="text-xs font-mono text-gray-500 dark:text-gray-400">{details.agent_id}</p>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            data-testid="close-details-button"
          >
            ✕
          </button>
        )}
      </div>

      {/* Status Badges */}
      <div className="flex gap-2 mb-4">
        <span className={`text-xs px-2 py-1 rounded font-medium ${LEVEL_COLORS[details.agent_level]}`} data-testid="agent-level">
          {details.agent_level.toUpperCase()}
        </span>
        <span className={`text-xs px-2 py-1 rounded font-medium ${STATUS_COLORS[details.status]}`} data-testid="agent-status">
          {details.status.toLowerCase()}
        </span>
      </div>

      {/* Skills */}
      <div className="mb-4">
        <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Skills:</div>
        <div className="flex flex-wrap gap-1" data-testid="agent-skills">
          {details.skills.map((skill, index) => (
            <span
              key={index}
              className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
              data-testid={`agent-skill-${skill}`}
            >
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Performance Metrics */}
      <div
        className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-700"
        data-testid="performance-metrics"
      >
        <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">
          Performance:
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center justify-center gap-1 mb-1">
              <CheckCircle className="w-3 h-3 text-green-600" />
              <span className="text-xs text-gray-600 dark:text-gray-400">Success Rate</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100" data-testid="success-rate">
              {details.success_rate_pct.toFixed(1)}%
            </div>
          </div>

          <div className="text-center p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Clock className="w-3 h-3 text-blue-600" />
              <span className="text-xs text-gray-600 dark:text-gray-400">Avg Latency</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {details.avg_latency_ms}ms
            </div>
          </div>

          <div className="text-center p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center justify-center gap-1 mb-1">
              <TrendingUp className="w-3 h-3 text-purple-600" />
              <span className="text-xs text-gray-600 dark:text-gray-400">Tasks Done</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {details.completed_tasks}
            </div>
          </div>

          <div className="text-center p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center justify-center gap-1 mb-1">
              <XCircle className="w-3 h-3 text-red-600" />
              <span className="text-xs text-gray-600 dark:text-gray-400">Failed</span>
            </div>
            <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {details.failed_tasks}
            </div>
          </div>
        </div>

        <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
          <div className="flex justify-between">
            <span>Current Load:</span>
            <span className="font-medium">
              {details.current_load}/{details.max_concurrent_tasks}
            </span>
          </div>
          <div className="flex justify-between mt-1">
            <span>P95 Latency:</span>
            <span className="font-medium">{details.p95_latency_ms}ms</span>
          </div>
        </div>
      </div>

      {/* Active Tasks */}
      <div className="mb-4">
        <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
          Active Tasks ({tasks.length}):
        </div>
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {tasks.length === 0 && (
            <div className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
              No active tasks
            </div>
          )}
          {tasks.map((task) => (
            <div
              key={task.task_id}
              className="text-xs p-2 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600"
            >
              <div className="font-medium text-gray-900 dark:text-gray-100">{task.task_name}</div>
              <div className="text-gray-600 dark:text-gray-400 mt-1">
                Skill: {task.assigned_skill} • Started {formatTime(task.started_at)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Last Active */}
      <div className="text-xs text-gray-600 dark:text-gray-400 pt-3 border-t border-gray-200 dark:border-gray-700">
        Last active: {formatTime(details.last_active)}
      </div>
    </div>
  );
}
