/**
 * AdminPage Component
 * Sprint 17 Feature 17.1: Admin UI for Directory Indexing (13 SP)
 *
 * Features:
 * - Directory input with validation
 * - Dry-run toggle
 * - Real-time SSE progress streaming
 * - System statistics dashboard
 * - Responsive design
 */

import { useState, useEffect, useCallback } from 'react';
import { streamReindex, getSystemStats } from '../api/admin';
import type { ReindexProgressChunk, SystemStats } from '../types/admin';

export function AdminPage() {
  // Form state
  const [directory, setDirectory] = useState('data/sample_documents');
  const [dryRun, setDryRun] = useState(false);

  // Re-indexing state
  const [isReindexing, setIsReindexing] = useState(false);
  const [progress, setProgress] = useState<ReindexProgressChunk | null>(null);
  const [progressHistory, setProgressHistory] = useState<ReindexProgressChunk[]>([]);
  const [reindexError, setReindexError] = useState<string | null>(null);

  // Statistics state
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);

  // Load statistics on mount
  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setStatsLoading(true);
    setStatsError(null);
    try {
      const data = await getSystemStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setStatsError(err instanceof Error ? err.message : 'Failed to load statistics');
    } finally {
      setStatsLoading(false);
    }
  };

  const handleReindex = useCallback(async () => {
    // Validation
    if (!directory.trim()) {
      setReindexError('Please enter a directory path');
      return;
    }

    // Confirmation for non-dry-run
    if (!dryRun) {
      const confirmed = window.confirm(
        'WARNING: This will delete all existing indexes (Qdrant, BM25, Neo4j) and re-index from scratch.\n\n' +
        'Are you sure you want to proceed?'
      );
      if (!confirmed) {
        return;
      }
    }

    // Start re-indexing
    setIsReindexing(true);
    setProgress(null);
    setProgressHistory([]);
    setReindexError(null);

    const abortController = new AbortController();

    try {
      for await (const chunk of streamReindex(
        {
          input_dir: directory,
          dry_run: dryRun,
          confirm: !dryRun, // Auto-confirm if not dry-run (already confirmed above)
        },
        abortController.signal
      )) {
        setProgress(chunk);
        setProgressHistory((prev) => [...prev, chunk]);

        // Handle completion
        if (chunk.status === 'completed') {
          setIsReindexing(false);
          // Auto-refresh stats on successful completion
          setTimeout(() => loadStats(), 1000);
        }

        // Handle errors
        if (chunk.status === 'error') {
          setReindexError(chunk.error || chunk.message);
          setIsReindexing(false);
        }
      }
    } catch (err) {
      console.error('Re-indexing error:', err);
      if (err instanceof Error && err.name !== 'AbortError') {
        setReindexError(err.message);
      }
      setIsReindexing(false);
    }

    return () => {
      abortController.abort();
    };
  }, [directory, dryRun]);

  const isFormValid = directory.trim().length > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-6 space-y-8">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">Admin Dashboard</h1>
          <p className="text-gray-600">
            Re-index documents and monitor system statistics
          </p>
        </div>

        {/* Re-indexing Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold text-gray-900">
              Directory Re-Indexing
            </h2>
            <p className="text-sm text-gray-600">
              Re-index all documents from a specified directory into Qdrant, BM25, and Neo4j.
            </p>
          </div>

          {/* Form */}
          <div className="space-y-4">
            {/* Directory Input */}
            <div>
              <label
                htmlFor="directory"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Document Directory
              </label>
              <input
                id="directory"
                type="text"
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="e.g., data/sample_documents"
                disabled={isReindexing}
                className="
                  w-full px-4 py-3 rounded-lg border border-gray-300
                  focus:ring-2 focus:ring-primary focus:border-transparent
                  disabled:bg-gray-100 disabled:cursor-not-allowed
                  transition-all
                "
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter the path to the directory containing documents to index (.pdf, .txt, .md, .docx, .csv, .pptx)
              </p>
            </div>

            {/* Dry Run Toggle */}
            <div className="flex items-center space-x-3">
              <input
                id="dry-run"
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                disabled={isReindexing}
                className="
                  w-5 h-5 rounded border-gray-300 text-primary
                  focus:ring-2 focus:ring-primary
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              />
              <label htmlFor="dry-run" className="text-sm font-medium text-gray-700">
                Dry Run (simulate without making changes)
              </label>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleReindex}
              disabled={!isFormValid || isReindexing}
              className="
                w-full px-6 py-3 rounded-lg font-semibold
                bg-primary text-white
                hover:bg-primary-hover
                disabled:bg-gray-300 disabled:cursor-not-allowed
                transition-all
              "
            >
              {isReindexing ? (
                <span className="flex items-center justify-center space-x-2">
                  <LoadingSpinner />
                  <span>Re-indexing in progress...</span>
                </span>
              ) : dryRun ? (
                'Simulate Re-Index (Dry Run)'
              ) : (
                'Start Re-Index'
              )}
            </button>
          </div>

          {/* Progress Display */}
          {(isReindexing || progress) && (
            <ProgressDisplay
              progress={progress}
              progressHistory={progressHistory}
              error={reindexError}
            />
          )}
        </div>

        {/* Statistics Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <h2 className="text-2xl font-semibold text-gray-900">
                System Statistics
              </h2>
              <p className="text-sm text-gray-600">
                Current state of all system components
              </p>
            </div>
            <button
              onClick={loadStats}
              disabled={statsLoading}
              className="
                px-4 py-2 rounded-lg border border-gray-300
                hover:bg-gray-50 transition-all
                disabled:opacity-50 disabled:cursor-not-allowed
                flex items-center space-x-2
              "
            >
              {statsLoading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>Refreshing...</span>
                </>
              ) : (
                <>
                  <RefreshIcon />
                  <span>Refresh</span>
                </>
              )}
            </button>
          </div>

          {statsError ? (
            <ErrorDisplay error={statsError} />
          ) : stats ? (
            <StatisticsGrid stats={stats} />
          ) : (
            <SkeletonStats />
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Progress Display Component
// ============================================================================

interface ProgressDisplayProps {
  progress: ReindexProgressChunk | null;
  progressHistory: ReindexProgressChunk[];
  error: string | null;
}

function ProgressDisplay({ progress, progressHistory, error }: ProgressDisplayProps) {
  if (error) {
    return <ErrorDisplay error={error} />;
  }

  if (!progress) {
    return null;
  }

  const percentage = progress.progress_percent || 0;
  const isComplete = progress.status === 'completed';

  return (
    <div className="space-y-4 pt-4 border-t border-gray-200">
      {/* Phase Badge */}
      {progress.phase && (
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <PhaseBadge phase={progress.phase} />
            {progress.current_document && (
              <span className="text-sm text-gray-600">
                {progress.current_document}
              </span>
            )}
          </div>
          {progress.eta_seconds && (
            <span className="text-sm text-gray-500">
              ETA: {formatETA(progress.eta_seconds)}
            </span>
          )}
        </div>
      )}

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">{progress.message}</span>
          <span className="text-gray-600">{percentage.toFixed(0)}%</span>
        </div>
        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`
              h-full transition-all duration-300 rounded-full
              ${isComplete ? 'bg-green-500' : 'bg-primary'}
            `}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* Document Progress */}
      {progress.documents_total && progress.documents_total > 0 && (
        <div className="text-sm text-gray-600">
          Documents: {progress.documents_processed || 0} / {progress.documents_total}
        </div>
      )}

      {/* Progress History Log */}
      {progressHistory.length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900">
            View Progress Log ({progressHistory.length} events)
          </summary>
          <div className="mt-3 max-h-64 overflow-y-auto space-y-1 text-xs font-mono bg-gray-50 rounded-lg p-3">
            {progressHistory.map((chunk, i) => (
              <div key={i} className="text-gray-600">
                <span className="text-gray-400">[{chunk.phase || 'unknown'}]</span>{' '}
                {chunk.message}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Completion Message */}
      {isComplete && (
        <div className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg">
          <svg
            className="w-5 h-5 text-green-600"
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
            Re-indexing completed successfully!
          </span>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Statistics Grid Component
// ============================================================================

interface StatisticsGridProps {
  stats: SystemStats;
}

function StatisticsGrid({ stats }: StatisticsGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* Qdrant Stats */}
      <StatCard
        title="Qdrant Vector Store"
        icon="🔍"
        stats={[
          { label: 'Total Chunks', value: stats.qdrant_total_chunks.toLocaleString() },
          { label: 'Collection', value: stats.qdrant_collection_name },
          { label: 'Dimension', value: stats.qdrant_vector_dimension },
        ]}
      />

      {/* Neo4j Stats */}
      <StatCard
        title="Neo4j Knowledge Graph"
        icon="🕸️"
        stats={[
          {
            label: 'Entities',
            value: stats.neo4j_total_entities?.toLocaleString() || 'N/A',
          },
          {
            label: 'Relations',
            value: stats.neo4j_total_relations?.toLocaleString() || 'N/A',
          },
          {
            label: 'Chunks',
            value: stats.neo4j_total_chunks?.toLocaleString() || 'N/A',
          },
        ]}
      />

      {/* BM25 Stats */}
      <StatCard
        title="BM25 Keyword Search"
        icon="📝"
        stats={[
          {
            label: 'Corpus Size',
            value: stats.bm25_corpus_size?.toLocaleString() || 'N/A',
          },
        ]}
      />

      {/* Redis Stats */}
      <StatCard
        title="Redis Memory Store"
        icon="💾"
        stats={[
          {
            label: 'Conversations',
            value: stats.total_conversations?.toLocaleString() || 'N/A',
          },
        ]}
      />

      {/* Embedding Model */}
      <StatCard
        title="Embedding Model"
        icon="🤖"
        stats={[{ label: 'Model', value: stats.embedding_model }]}
      />

      {/* Last Re-index */}
      <StatCard
        title="Last Re-Index"
        icon="🔄"
        stats={[
          {
            label: 'Timestamp',
            value: stats.last_reindex_timestamp
              ? new Date(stats.last_reindex_timestamp).toLocaleString()
              : 'Never',
          },
        ]}
      />
    </div>
  );
}

// ============================================================================
// Utility Components
// ============================================================================

interface StatCardProps {
  title: string;
  icon: string;
  stats: Array<{ label: string; value: string | number }>;
}

function StatCard({ title, icon, stats }: StatCardProps) {
  return (
    <div className="p-5 bg-gray-50 rounded-lg border border-gray-200 space-y-3">
      <div className="flex items-center space-x-2">
        <span className="text-2xl">{icon}</span>
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      </div>
      <div className="space-y-2">
        {stats.map((stat, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className="text-sm text-gray-600">{stat.label}</span>
            <span className="text-sm font-semibold text-gray-900">{stat.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface PhaseBadgeProps {
  phase: string;
}

function PhaseBadge({ phase }: PhaseBadgeProps) {
  const colors = {
    initialization: 'bg-blue-100 text-blue-700',
    deletion: 'bg-red-100 text-red-700',
    chunking: 'bg-yellow-100 text-yellow-700',
    embedding: 'bg-purple-100 text-purple-700',
    indexing: 'bg-indigo-100 text-indigo-700',
    validation: 'bg-green-100 text-green-700',
    completed: 'bg-green-100 text-green-700',
  };

  const colorClass = colors[phase as keyof typeof colors] || 'bg-gray-100 text-gray-700';

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

function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const sizeClass = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';
  return (
    <svg
      className={`${sizeClass} animate-spin`}
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

function RefreshIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );
}

function ErrorDisplay({ error }: { error: string }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
      <div className="flex items-center space-x-2 text-red-700">
        <svg
          className="w-5 h-5"
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
        <h3 className="font-semibold">Error</h3>
      </div>
      <p className="text-sm text-red-600">{error}</p>
    </div>
  );
}

function SkeletonStats() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div key={i} className="p-5 bg-gray-50 rounded-lg border border-gray-200 space-y-3">
          <div className="h-6 bg-gray-200 rounded animate-pulse w-3/4" />
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

function formatETA(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${minutes}m ${secs}s`;
}
