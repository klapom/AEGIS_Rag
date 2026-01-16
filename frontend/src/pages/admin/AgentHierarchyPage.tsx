/**
 * AgentHierarchyPage Component
 * Sprint 98 Feature 98.2: Agent Hierarchy Visualizer
 *
 * Admin page for visualizing agent hierarchy with interactive D3.js tree.
 * Shows Executive→Manager→Worker structure with delegation tracing.
 *
 * Route: /admin/agent-hierarchy
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Network, Shield, AlertCircle } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { AgentHierarchyD3 } from '../../components/agent/AgentHierarchyD3';
import { AgentDetailsPanel } from '../../components/agent/AgentDetailsPanel';
import { DelegationChainTracer } from '../../components/agent/DelegationChainTracer';
import {
  fetchAgentHierarchy,
  type D3HierarchyResponse,
} from '../../api/agentHierarchy';

/**
 * AgentHierarchyPage provides interactive visualization of agent hierarchy.
 *
 * Features:
 * - Admin-only access
 * - D3.js tree visualization with pan/zoom
 * - Agent details panel on node click
 * - Task delegation chain tracing
 * - Highlight delegation paths in tree
 * - Responsive layout
 * - Dark mode support
 */
export function AgentHierarchyPage() {
  const { isAuthenticated } = useAuth();
  const [hierarchyData, setHierarchyData] = useState<D3HierarchyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [highlightedAgents, setHighlightedAgents] = useState<string[]>([]);

  /**
   * Load agent hierarchy
   */
  const loadHierarchy = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchAgentHierarchy();
      setHierarchyData(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch agent hierarchy'));
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void loadHierarchy();
  }, [loadHierarchy]);

  /**
   * Handle node click from tree
   */
  const handleNodeClick = (agentId: string) => {
    setSelectedAgentId(agentId);
  };

  /**
   * Handle delegation chain highlight
   */
  const handleHighlightAgents = (agentIds: string[]) => {
    setHighlightedAgents(agentIds);
  };

  /**
   * Calculate hierarchy statistics from nodes
   */
  const getHierarchyStats = () => {
    if (!hierarchyData) {
      return { total: 0, executive: 0, manager: 0, worker: 0 };
    }

    const stats = {
      total: hierarchyData.nodes.length,
      executive: hierarchyData.nodes.filter((n) => n.level === 'executive').length,
      manager: hierarchyData.nodes.filter((n) => n.level === 'manager').length,
      worker: hierarchyData.nodes.filter((n) => n.level === 'worker').length,
    };

    return stats;
  };

  // Unauthorized state
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div
          className="text-center max-w-md p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg"
          data-testid="unauthorized-message"
        >
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
            <Shield className="w-8 h-8 text-red-600 dark:text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            Access Denied
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            You need to be logged in to access the Agent Hierarchy page.
          </p>
          <Link
            to="/login"
            className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900" data-testid="agent-hierarchy-page">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Admin
          </Link>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <Network className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  Agent Hierarchy
                </h1>
                <div className="text-sm text-gray-600 dark:text-gray-400" data-testid="hierarchy-stats">
                  {hierarchyData
                    ? (() => {
                        const stats = getHierarchyStats();
                        return (
                          <>
                            <span data-testid="stat-total-agents">{stats.total}</span> agents (
                            <span data-testid="stat-executive-count">{stats.executive}</span> Executive,
                            <span data-testid="stat-manager-count">{stats.manager}</span> Managers,
                            <span data-testid="stat-worker-count">{stats.worker}</span> Workers)
                          </>
                        );
                      })()
                    : 'Visualize agent organization and delegation'}
                </div>
              </div>
            </div>

            <button
              onClick={loadHierarchy}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              data-testid="refresh-hierarchy-button"
            >
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Loading State */}
        {loading && !hierarchyData && (
          <div className="text-center py-12">
            <div className="w-12 h-12 mx-auto mb-4 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-600 dark:text-gray-400">Loading agent hierarchy...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div
            className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg mb-6"
            data-testid="empty-state"
          >
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{error.message}</span>
          </div>
        )}

        {/* Main Layout */}
        {hierarchyData && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column: Hierarchy Tree (2/3 width) */}
            <div className="lg:col-span-2 space-y-6">
              <div data-testid="agent-hierarchy-tree">
                <AgentHierarchyD3
                  nodes={hierarchyData.nodes}
                  edges={hierarchyData.edges}
                  onNodeClick={handleNodeClick}
                  highlightedAgents={highlightedAgents}
                />
              </div>

              {/* Info Card */}
              <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  About Agent Hierarchy
                </h3>
                <div className="space-y-4 text-sm text-gray-600 dark:text-gray-400">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-blue-600 dark:text-blue-400 font-bold">1</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Executive Director
                      </p>
                      <p>
                        Top-level agent responsible for planning and orchestrating complex
                        workflows. Delegates tasks to specialized managers.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-green-600 dark:text-green-400 font-bold">2</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Manager Agents
                      </p>
                      <p>
                        Domain-specific managers (Research, Analysis, Synthesis) that coordinate
                        worker agents within their specialty.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-purple-600 dark:text-purple-400 font-bold">3</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        Worker Agents
                      </p>
                      <p>
                        Specialized worker agents that execute specific skills (retrieval,
                        web_search, fact_check, etc.).
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Details & Tracer (1/3 width) */}
            <div className="space-y-6">
              <div data-testid="agent-details">
                <AgentDetailsPanel agentId={selectedAgentId} />
              </div>
              <div data-testid="delegation-chain-tracer">
                <DelegationChainTracer onHighlightAgents={handleHighlightAgents} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
