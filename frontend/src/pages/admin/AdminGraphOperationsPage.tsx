/**
 * AdminGraphOperationsPage Component
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 *
 * Admin page for graph maintenance operations:
 * - Community Summarization (batch job trigger)
 * - Graph Statistics (read-only display)
 * - Namespace filtering
 *
 * Route: /admin/graph-operations
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Database, Shield } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { GraphStatisticsCard } from '../../components/admin/GraphStatisticsCard';
import { CommunityOperationsCard } from '../../components/admin/CommunityOperationsCard';
import {
  fetchGraphOperationsStats,
  fetchNamespaces,
  type GraphOperationsStats,
  type NamespaceInfo,
} from '../../api/graphOperations';

/**
 * AdminGraphOperationsPage provides UI for graph maintenance operations.
 *
 * Features:
 * - Admin-only access (checks authentication)
 * - Graph statistics display with auto-refresh
 * - Community summarization trigger
 * - Namespace filtering for operations
 * - Loading and error states
 * - Dark mode support
 */
export function AdminGraphOperationsPage() {
  const { isAuthenticated } = useAuth();

  // Graph statistics state
  const [stats, setStats] = useState<GraphOperationsStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<Error | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  // Namespace state
  const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
  const [namespacesLoading, setNamespacesLoading] = useState(true);
  const [selectedNamespace, setSelectedNamespace] = useState<string | null>(null);

  /**
   * Fetch graph statistics
   */
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    setStatsError(null);

    try {
      const data = await fetchGraphOperationsStats();
      setStats(data);
      setLastRefresh(new Date());
    } catch (err) {
      setStatsError(err instanceof Error ? err : new Error('Failed to fetch graph statistics'));
    } finally {
      setStatsLoading(false);
    }
  }, []);

  /**
   * Fetch available namespaces
   */
  const loadNamespaces = useCallback(async () => {
    setNamespacesLoading(true);

    try {
      const data = await fetchNamespaces();
      setNamespaces(data.namespaces);
    } catch (err) {
      console.error('Failed to fetch namespaces:', err);
      // Don't show error - namespaces are optional
      setNamespaces([]);
    } finally {
      setNamespacesLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    void loadStats();
    void loadNamespaces();
  }, [loadStats, loadNamespaces]);

  // Auto-refresh stats every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      void loadStats();
    }, 30000);

    return () => clearInterval(interval);
  }, [loadStats]);

  /**
   * Handle namespace selection change
   */
  const handleNamespaceChange = (namespace: string | null) => {
    setSelectedNamespace(namespace);
  };

  /**
   * Handle operation completion - refresh stats
   */
  const handleOperationComplete = () => {
    void loadStats();
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
            You need to be logged in to access the Admin Graph Operations page.
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
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
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Database className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Graph Operations
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Manage knowledge graph maintenance tasks
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Graph Statistics */}
          <div className="space-y-6">
            <GraphStatisticsCard
              stats={stats}
              loading={statsLoading}
              error={statsError}
              lastRefresh={lastRefresh}
              onRefresh={loadStats}
            />

            {/* Additional Info Card */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                About Graph Operations
              </h3>
              <div className="space-y-4 text-sm text-gray-600 dark:text-gray-400">
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-green-600 dark:text-green-400 font-bold">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      Community Detection
                    </p>
                    <p>
                      Communities are detected during document ingestion using the Louvain algorithm.
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-green-600 dark:text-green-400 font-bold">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      Summary Generation
                    </p>
                    <p>
                      Summaries are generated using LLM to enable semantic search over communities.
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="text-green-600 dark:text-green-400 font-bold">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">Graph-Global Mode</p>
                    <p>
                      Community summaries power the Graph-Global search mode in LightRAG for high-level
                      queries.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Operations */}
          <div>
            <CommunityOperationsCard
              namespaces={namespacesLoading ? [] : namespaces}
              selectedNamespace={selectedNamespace}
              onNamespaceChange={handleNamespaceChange}
              onOperationComplete={handleOperationComplete}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
