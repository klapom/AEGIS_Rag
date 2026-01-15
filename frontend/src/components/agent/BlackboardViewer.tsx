/**
 * BlackboardViewer Component
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 *
 * Displays shared memory (Blackboard) state across all agent namespaces.
 *
 * Features:
 * - View all namespace states
 * - Expand/collapse namespace details
 * - Auto-refresh every 5 seconds
 * - JSON viewer for complex state objects
 */

import { useState, useEffect, useCallback } from 'react';
import { Database, ChevronDown, ChevronRight, AlertCircle } from 'lucide-react';
import {
  fetchBlackboardState,
  type BlackboardNamespace,
} from '../../api/agentCommunication';

interface BlackboardViewerProps {
  className?: string;
}

export function BlackboardViewer({ className = '' }: BlackboardViewerProps) {
  const [namespaces, setNamespaces] = useState<BlackboardNamespace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [expandedNamespaces, setExpandedNamespaces] = useState<Set<string>>(new Set());

  /**
   * Load blackboard state
   */
  const loadBlackboardState = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetchBlackboardState();
      setNamespaces(response.namespaces);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch blackboard state'));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void loadBlackboardState();
  }, [loadBlackboardState]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      void loadBlackboardState();
    }, 5000);

    return () => clearInterval(interval);
  }, [loadBlackboardState]);

  /**
   * Toggle namespace expansion
   */
  const toggleNamespace = (namespace: string) => {
    setExpandedNamespaces((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(namespace)) {
        newSet.delete(namespace);
      } else {
        newSet.add(namespace);
      }
      return newSet;
    });
  };

  /**
   * Format timestamp for display
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

  /**
   * Get a brief summary of the state
   */
  const getStateSummary = (state: Record<string, unknown>) => {
    const keys = Object.keys(state);
    if (keys.length === 0) return 'Empty';
    if (keys.length <= 3) return keys.join(', ');
    return `${keys.slice(0, 3).join(', ')}, +${keys.length - 3} more`;
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
            <Database className="w-5 h-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Blackboard State
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {namespaces.length} active namespaces
            </p>
          </div>
        </div>

        <button
          onClick={loadBlackboardState}
          className="px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors text-sm"
          data-testid="refresh-blackboard-button"
        >
          Refresh
        </button>
      </div>

      {/* Namespaces List */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {loading && namespaces.length === 0 && (
          <div className="text-center py-8 text-gray-500">Loading blackboard state...</div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error.message}</span>
          </div>
        )}

        {!loading && !error && namespaces.length === 0 && (
          <div className="text-center py-8 text-gray-500">No blackboard namespaces found</div>
        )}

        {namespaces.map((namespace) => {
          const isExpanded = expandedNamespaces.has(namespace.namespace);

          return (
            <div
              key={namespace.namespace}
              className="bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600 overflow-hidden"
              data-testid={`namespace-${namespace.namespace}`}
            >
              {/* Namespace Header */}
              <button
                onClick={() => toggleNamespace(namespace.namespace)}
                className="w-full p-4 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-500" />
                  )}
                  <div className="text-left">
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {namespace.namespace}
                    </div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      {getStateSummary(namespace.state)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                  {namespace.agent_id && (
                    <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded">
                      {namespace.agent_id}
                    </span>
                  )}
                  <span>{formatTime(namespace.last_updated)}</span>
                </div>
              </button>

              {/* Expanded State Details */}
              {isExpanded && (
                <div className="p-4 border-t border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800">
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Last Updated:
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {new Date(namespace.last_updated).toLocaleString()}
                      </div>
                    </div>

                    {namespace.agent_id && (
                      <div>
                        <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Owner Agent:
                        </div>
                        <div className="text-sm font-mono text-gray-600 dark:text-gray-400">
                          {namespace.agent_id}
                        </div>
                      </div>
                    )}

                    <div>
                      <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                        State Data:
                      </div>
                      <pre className="bg-gray-100 dark:bg-gray-900 p-3 rounded-lg overflow-x-auto text-xs">
                        {JSON.stringify(namespace.state, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Info Footer */}
      {namespaces.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Blackboard provides shared memory for agent coordination. Each namespace represents a
            different aspect of the agent workflow (retrieval, synthesis, reflection, etc.).
          </p>
        </div>
      )}
    </div>
  );
}
