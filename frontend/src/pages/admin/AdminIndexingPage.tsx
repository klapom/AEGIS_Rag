/**
 * Admin Indexing Page Component
 * Sprint 31 Feature 31.7: Admin Indexing E2E Tests - UI Implementation
 *
 * Features:
 * - Directory path input with validation
 * - Start/Cancel indexing controls
 * - Real-time SSE progress tracking
 * - Progress bar with percentage display
 * - Status message updates (Processing -> Chunking -> Embedding -> Complete)
 * - Indexed document count display
 * - Error handling for invalid paths
 *
 * All data-testid attributes match E2E test expectations from AdminIndexingPage POM
 */

import { useState, useCallback } from 'react';
import { streamReindex } from '../../api/admin';
import type { ReindexProgressChunk } from '../../types/admin';

export function AdminIndexingPage() {
  // Form state
  const [directory, setDirectory] = useState('data/sample_documents');

  // Indexing state
  const [isIndexing, setIsIndexing] = useState(false);
  const [progress, setProgress] = useState<ReindexProgressChunk | null>(null);
  const [progressHistory, setProgressHistory] = useState<ReindexProgressChunk[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const handleStartIndexing = useCallback(async () => {
    // Validation
    if (!directory.trim()) {
      setError('Please enter a directory path');
      return;
    }

    // Confirmation
    const confirmed = window.confirm(
      'WARNING: This will delete all existing indexes and re-index from scratch.\n\n' +
        'Are you sure you want to proceed?'
    );
    if (!confirmed) {
      return;
    }

    // Reset state
    setIsIndexing(true);
    setProgress(null);
    setProgressHistory([]);
    setError(null);

    const controller = new AbortController();
    setAbortController(controller);

    try {
      for await (const chunk of streamReindex(
        {
          input_dir: directory,
          dry_run: false,
          confirm: true,
        },
        controller.signal
      )) {
        setProgress(chunk);
        setProgressHistory((prev) => [...prev, chunk]);

        // Handle completion
        if (chunk.status === 'completed') {
          setIsIndexing(false);
          setAbortController(null);
        }

        // Handle errors
        if (chunk.status === 'error') {
          setError(chunk.error || chunk.message);
          setIsIndexing(false);
          setAbortController(null);
        }
      }
    } catch (err) {
      console.error('Indexing error:', err);
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message);
      }
      setIsIndexing(false);
      setAbortController(null);
    }
  }, [directory]);

  const handleCancelIndexing = useCallback(() => {
    if (abortController) {
      abortController.abort();
      setIsIndexing(false);
      setAbortController(null);
      setError('Indexing cancelled by user');
    }
  }, [abortController]);

  const percentage = progress?.progress_percent || 0;
  const isComplete = progress?.status === 'completed';
  const documentsProcessed = progress?.documents_processed || 0;
  const documentsTotal = progress?.documents_total || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">Document Indexing</h1>
          <p className="text-gray-600">
            Index documents from a directory into the knowledge base
          </p>
        </div>

        {/* Indexing Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
          {/* Directory Input */}
          <div>
            <label
              htmlFor="directory-input"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Document Directory Path
            </label>
            <input
              id="directory-input"
              data-testid="directory-input"
              type="text"
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              placeholder="e.g., data/sample_documents"
              disabled={isIndexing}
              className="
                w-full px-4 py-3 rounded-lg border border-gray-300
                focus:ring-2 focus:ring-blue-500 focus:border-transparent
                disabled:bg-gray-100 disabled:cursor-not-allowed
                transition-all
              "
            />
            <p className="mt-1 text-xs text-gray-500">
              Enter the path to the directory containing documents to index
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4">
            <button
              data-testid="start-indexing"
              onClick={handleStartIndexing}
              disabled={!directory.trim() || isIndexing}
              className="
                flex-1 px-6 py-3 rounded-lg font-semibold
                bg-blue-600 text-white
                hover:bg-blue-700
                disabled:bg-gray-300 disabled:cursor-not-allowed
                transition-all
                flex items-center justify-center space-x-2
              "
            >
              {isIndexing ? (
                <>
                  <LoadingSpinner />
                  <span>Indexing in Progress...</span>
                </>
              ) : (
                <span>Start Indexing</span>
              )}
            </button>

            {isIndexing && (
              <button
                data-testid="cancel-indexing"
                onClick={handleCancelIndexing}
                className="
                  px-6 py-3 rounded-lg font-semibold
                  bg-red-600 text-white
                  hover:bg-red-700
                  transition-all
                "
              >
                Cancel
              </button>
            )}
          </div>

          {/* Progress Display */}
          {isIndexing && progress && (
            <div className="space-y-4 pt-4 border-t border-gray-200">
              {/* Status Message */}
              <div
                data-testid="indexing-status"
                className="text-sm font-medium text-gray-700"
              >
                {progress.message || 'Processing...'}
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Progress</span>
                  <span data-testid="progress-percentage" className="font-semibold">
                    {percentage.toFixed(0)}%
                  </span>
                </div>
                <div
                  data-testid="progress-bar"
                  className="w-full h-3 bg-gray-200 rounded-full overflow-hidden"
                >
                  <div
                    className={`
                      h-full transition-all duration-300 rounded-full
                      ${isComplete ? 'bg-green-500' : 'bg-blue-600'}
                    `}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>

              {/* Document Count */}
              {documentsTotal > 0 && (
                <div
                  data-testid="indexed-count"
                  className="text-sm text-gray-600"
                >
                  Documents: {documentsProcessed} / {documentsTotal}
                </div>
              )}

              {/* Phase Badge */}
              {progress.phase && (
                <div className="flex items-center space-x-2">
                  <PhaseBadge phase={progress.phase} />
                  {progress.current_document && (
                    <span className="text-sm text-gray-600 truncate">
                      {progress.current_document}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Success Message */}
          {isComplete && (
            <div
              data-testid="success-message"
              className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg"
            >
              <svg
                className="w-5 h-5 text-green-600 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-sm font-medium text-green-800">
                Indexing completed successfully! {documentsProcessed} documents processed.
              </span>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div
              data-testid="error-message"
              className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg"
            >
              <svg
                className="w-5 h-5 text-red-600 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="text-sm font-medium text-red-800">{error}</span>
            </div>
          )}

          {/* Progress History (Collapsible) */}
          {progressHistory.length > 0 && (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
                View Progress Log ({progressHistory.length} events)
              </summary>
              <div className="mt-3 max-h-64 overflow-y-auto space-y-1 text-xs font-mono bg-gray-50 rounded-lg p-3">
                {progressHistory.map((chunk, i) => (
                  <div key={i} className="text-gray-600">
                    <span className="text-gray-400">[{chunk.phase || 'unknown'}]</span>{' '}
                    {chunk.message} {chunk.progress_percent ? `(${chunk.progress_percent.toFixed(0)}%)` : ''}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>

        {/* Advanced Options (Optional - for future enhancements) */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <details>
            <summary
              data-testid="advanced-options"
              className="cursor-pointer text-lg font-semibold text-gray-900 hover:text-blue-600"
            >
              Advanced Options
            </summary>
            <div className="mt-4 space-y-4 text-sm text-gray-600">
              <p>Advanced indexing options will be available in a future release.</p>
              <p>
                Current settings: BGE-M3 embeddings, 1800-token chunks, Gemma-3-4B extraction
              </p>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Utility Components
// ============================================================================

interface PhaseBadgeProps {
  phase: string;
}

function PhaseBadge({ phase }: PhaseBadgeProps) {
  const colors: Record<string, string> = {
    initialization: 'bg-blue-100 text-blue-700',
    deletion: 'bg-red-100 text-red-700',
    chunking: 'bg-yellow-100 text-yellow-700',
    embedding: 'bg-purple-100 text-purple-700',
    indexing: 'bg-indigo-100 text-indigo-700',
    validation: 'bg-green-100 text-green-700',
    completed: 'bg-green-100 text-green-700',
  };

  const colorClass = colors[phase] || 'bg-gray-100 text-gray-700';

  return (
    <span
      className={`
        px-3 py-1 rounded-full text-xs font-semibold uppercase
        ${colorClass}
      `}
    >
      {phase}
    </span>
  );
}

function LoadingSpinner() {
  return (
    <svg
      className="w-5 h-5 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}
