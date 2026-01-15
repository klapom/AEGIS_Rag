/**
 * DelegationChainTracer Component
 * Sprint 98 Feature 98.2: Agent Hierarchy Visualizer
 *
 * Traces and displays task delegation chains through the agent hierarchy.
 *
 * Features:
 * - Select task to view delegation path
 * - Visual delegation chain display
 * - Highlight path in hierarchy tree
 * - Show timing and skill information
 */

import { useState, useCallback } from 'react';
import { GitBranch, Clock, AlertCircle, Search } from 'lucide-react';
import {
  fetchTaskDelegationChain,
  type DelegationChainResponse,
} from '../../api/agentHierarchy';

interface DelegationChainTracerProps {
  onHighlightAgents?: (agentIds: string[]) => void;
  className?: string;
}

export function DelegationChainTracer({
  onHighlightAgents,
  className = '',
}: DelegationChainTracerProps) {
  const [taskId, setTaskId] = useState('');
  const [chain, setChain] = useState<DelegationChainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  /**
   * Load delegation chain for task
   */
  const loadDelegationChain = useCallback(async () => {
    if (!taskId.trim()) {
      setError(new Error('Please enter a task ID'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const chainData = await fetchTaskDelegationChain(taskId.trim());
      setChain(chainData);

      // Highlight agents in hierarchy tree
      if (onHighlightAgents) {
        const agentIds = chainData.chain.map((step) => step.agent_id);
        onHighlightAgents(agentIds);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load delegation chain'));
      setChain(null);
    } finally {
      setLoading(false);
    }
  }, [taskId, onHighlightAgents]);

  /**
   * Clear delegation chain and highlights
   */
  const clearChain = () => {
    setTaskId('');
    setChain(null);
    setError(null);
    if (onHighlightAgents) {
      onHighlightAgents([]);
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
   * Agent level colors
   */
  const LEVEL_COLORS = {
    EXECUTIVE: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    MANAGER: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    WORKER: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center">
          <GitBranch className="w-5 h-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Task Delegation Tracer
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Trace delegation path through agent hierarchy
          </p>
        </div>
      </div>

      {/* Task ID Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Task ID:
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                void loadDelegationChain();
              }
            }}
            placeholder="Enter task ID (e.g., research_workflow_7a2b)"
            className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
            data-testid="task-id-input"
          />
          <button
            onClick={loadDelegationChain}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors flex items-center gap-2"
            data-testid="trace-button"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Tracing...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Trace
              </>
            )}
          </button>
          {chain && (
            <button
              onClick={clearChain}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
              data-testid="clear-button"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          <span className="text-sm text-red-700 dark:text-red-300">{error.message}</span>
        </div>
      )}

      {/* Delegation Chain Display */}
      {chain && (
        <div className="space-y-4">
          {/* Chain Summary */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
              {chain.task_name}
            </div>
            <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400">
              <div className="flex items-center gap-1">
                <GitBranch className="w-3 h-3" />
                <span>{chain.total_delegation_hops} delegation hops</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>Total: {formatDuration(chain.total_duration_ms)}</span>
              </div>
            </div>
          </div>

          {/* Chain Steps */}
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Delegation Chain:
            </div>
            {chain.chain.map((step, index) => (
              <div
                key={index}
                className="relative"
                data-testid={`delegation-step-${index}`}
              >
                {/* Connector Line */}
                {index < chain.chain.length - 1 && (
                  <div className="absolute left-4 top-12 w-0.5 h-6 bg-gray-300 dark:bg-gray-600" />
                )}

                {/* Step Card */}
                <div className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                  {/* Step Number */}
                  <div className="w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-gray-700 dark:text-gray-300">
                      {index + 1}
                    </span>
                  </div>

                  {/* Step Details */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {step.agent_name}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-medium ${LEVEL_COLORS[step.agent_level]}`}
                      >
                        {step.agent_level}
                      </span>
                    </div>

                    <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                      <div>Agent ID: {step.agent_id}</div>
                      {step.skill_invoked && <div>Skill: {step.skill_invoked}</div>}
                      {step.duration_ms && (
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Duration: {formatDuration(step.duration_ms)}
                        </div>
                      )}
                      <div>Delegated: {new Date(step.delegated_at).toLocaleString()}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Instructions */}
          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
            <p className="text-xs text-amber-700 dark:text-amber-300">
              The highlighted agents in the hierarchy tree show the delegation path for this task.
            </p>
          </div>
        </div>
      )}

      {/* Instructions (No Chain) */}
      {!chain && !error && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <GitBranch className="w-12 h-12 mx-auto mb-3 text-gray-400" />
          <p className="text-sm">Enter a task ID to trace its delegation chain</p>
        </div>
      )}
    </div>
  );
}
