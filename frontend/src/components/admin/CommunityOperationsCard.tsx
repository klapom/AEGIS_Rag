/**
 * CommunityOperationsCard Component
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 *
 * Provides UI for triggering community summarization:
 * - Button to trigger batch summarization
 * - Progress indicator during operation
 * - Success/Error notifications
 * - Namespace filtering option
 * - Force regeneration toggle
 */

import { useState } from 'react';
import { Play, AlertCircle, CheckCircle2, Loader2, RefreshCcw, Layers } from 'lucide-react';
import {
  triggerCommunitySummarization,
  type CommunitySummarizationResponse,
  type NamespaceInfo,
} from '../../api/graphOperations';

interface CommunityOperationsCardProps {
  /** Available namespaces for filtering */
  namespaces: NamespaceInfo[];
  /** Currently selected namespace */
  selectedNamespace: string | null;
  /** Callback when namespace changes */
  onNamespaceChange: (namespace: string | null) => void;
  /** Callback after successful operation to refresh stats */
  onOperationComplete: () => void;
}

type OperationStatus = 'idle' | 'running' | 'success' | 'error';

interface OperationResult {
  status: OperationStatus;
  response: CommunitySummarizationResponse | null;
  error: string | null;
}

/**
 * CommunityOperationsCard provides controls for community summarization.
 *
 * Features:
 * - Start summarization button
 * - Force regeneration toggle
 * - Progress indicator during operation
 * - Result display (success/error)
 * - Namespace filtering
 */
export function CommunityOperationsCard({
  namespaces,
  selectedNamespace,
  onNamespaceChange,
  onOperationComplete,
}: CommunityOperationsCardProps) {
  const [forceRegenerate, setForceRegenerate] = useState(false);
  const [result, setResult] = useState<OperationResult>({
    status: 'idle',
    response: null,
    error: null,
  });

  /**
   * Handle triggering community summarization
   */
  const handleSummarize = async () => {
    setResult({ status: 'running', response: null, error: null });

    try {
      const response = await triggerCommunitySummarization({
        namespace: selectedNamespace,
        force: forceRegenerate,
        batch_size: 10,
      });

      setResult({
        status: response.status === 'no_work' ? 'success' : 'success',
        response,
        error: null,
      });

      // Refresh stats after operation completes
      onOperationComplete();
    } catch (err) {
      setResult({
        status: 'error',
        response: null,
        error: err instanceof Error ? err.message : 'Unknown error occurred',
      });
    }
  };

  /**
   * Reset result state to allow new operation
   */
  const handleReset = () => {
    setResult({ status: 'idle', response: null, error: null });
  };

  const isRunning = result.status === 'running';

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border-2 border-gray-200 dark:border-gray-700 p-6"
      data-testid="community-operations-card"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
          <Layers className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Community Summarization
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Generate LLM-powered summaries for graph communities
          </p>
        </div>
      </div>

      {/* Namespace Selector */}
      <div className="mb-4">
        <label
          htmlFor="namespace-select"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Namespace Filter
        </label>
        <select
          id="namespace-select"
          value={selectedNamespace ?? ''}
          onChange={(e) => onNamespaceChange(e.target.value || null)}
          disabled={isRunning}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="namespace-selector"
        >
          <option value="">All namespaces</option>
          {namespaces.map((ns) => (
            <option key={ns.namespace_id} value={ns.namespace_id}>
              {ns.namespace_id} ({ns.document_count} docs)
            </option>
          ))}
        </select>
      </div>

      {/* Force Regenerate Toggle */}
      <div className="mb-6">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={forceRegenerate}
            onChange={(e) => setForceRegenerate(e.target.checked)}
            disabled={isRunning}
            className="w-4 h-4 text-blue-600 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 disabled:opacity-50"
            data-testid="force-regenerate-checkbox"
          />
          <div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Force Regeneration
            </span>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Regenerate all summaries including existing ones
            </p>
          </div>
        </label>
      </div>

      {/* Action Button */}
      {result.status === 'idle' && (
        <button
          onClick={handleSummarize}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          data-testid="summarize-button"
        >
          <Play className="w-5 h-5" />
          Summarize Communities
        </button>
      )}

      {/* Running State */}
      {result.status === 'running' && (
        <div
          className="w-full flex flex-col items-center gap-3 py-4"
          data-testid="summarization-running"
        >
          <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Generating community summaries...
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-500">
            This may take several minutes for large graphs
          </p>
        </div>
      )}

      {/* Success State */}
      {result.status === 'success' && result.response && (
        <div className="space-y-4" data-testid="summarization-success">
          <div className="flex items-start gap-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                {result.response.status === 'no_work'
                  ? 'No Communities to Summarize'
                  : 'Summarization Complete'}
              </p>
              <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                {result.response.message}
              </p>
            </div>
          </div>

          {/* Result Details */}
          {result.response.status === 'complete' && (
            <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Communities Processed</p>
                <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {result.response.total_communities}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Summaries Generated</p>
                <p className="text-lg font-bold text-green-600 dark:text-green-400">
                  {result.response.summaries_generated}
                </p>
              </div>
              {result.response.failed !== null && result.response.failed > 0 && (
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Failed</p>
                  <p className="text-lg font-bold text-red-600 dark:text-red-400">
                    {result.response.failed}
                  </p>
                </div>
              )}
              {result.response.total_time_s !== null && (
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Time</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
                    {result.response.total_time_s.toFixed(1)}s
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Reset Button */}
          <button
            onClick={handleReset}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 font-medium rounded-lg transition-colors"
            data-testid="reset-button"
          >
            <RefreshCcw className="w-4 h-4" />
            Run Another Summarization
          </button>
        </div>
      )}

      {/* Error State */}
      {result.status === 'error' && (
        <div className="space-y-4" data-testid="summarization-error">
          <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Summarization Failed
              </p>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">{result.error}</p>
            </div>
          </div>

          {/* Retry Button */}
          <div className="flex gap-3">
            <button
              onClick={handleSummarize}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
              data-testid="retry-button"
            >
              <RefreshCcw className="w-4 h-4" />
              Retry
            </button>
            <button
              onClick={handleReset}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 font-medium rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Info Note */}
      <div className="mt-6 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800">
        <p className="text-xs text-blue-700 dark:text-blue-300">
          <strong>Note:</strong> Community summaries enable semantic search over graph communities
          in LightRAG global mode. Generating summaries for large graphs may take several minutes.
        </p>
      </div>
    </div>
  );
}
