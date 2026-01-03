/**
 * IngestionJobList Component
 * Sprint 71 Feature 71.8: Ingestion Job Monitoring UI
 *
 * Displays list of ingestion jobs with real-time SSE progress updates.
 * Shows overall progress, current step, and parallel document processing.
 */

import { useEffect, useState, useCallback } from 'react';
import { Clock, CheckCircle2, XCircle, AlertCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import {
  listIngestionJobs,
  cancelIngestionJob,
  streamBatchProgress,
} from '../../api/admin';
import type {
  IngestionJobResponse,
  BatchProgress,
  DocumentProgress,
} from '../../types/admin';

/**
 * Format timestamp to relative time (e.g., "2 minutes ago")
 */
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

/**
 * Get status badge styles
 */
function getStatusStyles(status: string) {
  switch (status) {
    case 'running':
      return {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-700 dark:text-blue-300',
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
      };
    case 'completed':
      return {
        bg: 'bg-green-100 dark:bg-green-900/30',
        text: 'text-green-700 dark:text-green-300',
        icon: <CheckCircle2 className="w-4 h-4" />,
      };
    case 'failed':
      return {
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-700 dark:text-red-300',
        icon: <XCircle className="w-4 h-4" />,
      };
    case 'cancelled':
      return {
        bg: 'bg-gray-100 dark:bg-gray-700',
        text: 'text-gray-700 dark:text-gray-300',
        icon: <AlertCircle className="w-4 h-4" />,
      };
    default:
      return {
        bg: 'bg-gray-100 dark:bg-gray-700',
        text: 'text-gray-700 dark:text-gray-300',
        icon: <Clock className="w-4 h-4" />,
      };
  }
}

/**
 * Get step label for current processing step
 */
function getStepLabel(step?: string | null): string {
  if (!step) return 'Processing';

  const stepLabels: Record<string, string> = {
    parsing: 'Parsing Document',
    chunking: 'Creating Chunks',
    embedding: 'Generating Embeddings',
    graph_extraction: 'Extracting Knowledge Graph',
  };

  return stepLabels[step] || step;
}

/**
 * Individual Document Progress Item
 */
interface DocumentProgressItemProps {
  doc: DocumentProgress;
}

function DocumentProgressItem({ doc }: DocumentProgressItemProps) {
  const statusStyles = getStatusStyles(doc.status);

  return (
    <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg" data-testid={`document-progress-${doc.document_id}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className={`${statusStyles.bg} ${statusStyles.text} p-1 rounded`}>
            {statusStyles.icon}
          </span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {doc.document_name}
          </span>
        </div>
        <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
          {Math.round(doc.progress_percent)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${
            doc.status === 'error'
              ? 'bg-red-500'
              : doc.status === 'completed'
              ? 'bg-green-500'
              : 'bg-blue-500'
          }`}
          style={{ width: `${doc.progress_percent}%` }}
        />
      </div>

      {/* Current Step */}
      {doc.current_step && doc.status === 'processing' && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1" data-testid={`job-current-step-${doc.document_id}`}>
          {getStepLabel(doc.current_step)}
        </p>
      )}

      {/* Statistics */}
      <div className="flex gap-4 text-xs text-gray-600 dark:text-gray-400">
        <span>Chunks: {doc.chunks_created}</span>
        <span>Entities: {doc.entities_extracted}</span>
        <span>Relations: {doc.relations_extracted}</span>
      </div>

      {/* Error Message */}
      {doc.error && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">
          Error: {doc.error}
        </p>
      )}
    </div>
  );
}

/**
 * Single Job Card with Expandable Details
 */
interface JobCardProps {
  job: IngestionJobResponse;
  batchProgress?: BatchProgress;
  onCancel: (jobId: string) => void;
}

function JobCard({ job, batchProgress, onCancel }: JobCardProps) {
  const [isExpanded, setIsExpanded] = useState(job.status === 'running');
  const statusStyles = getStatusStyles(job.status);

  // Calculate overall progress
  const overallProgress = batchProgress
    ? batchProgress.overall_progress_percent
    : (job.processed_files / job.total_files) * 100;

  // Get currently processing documents
  const processingDocs = batchProgress?.documents.filter(d => d.status === 'processing') || [];
  const completedDocs = batchProgress?.completed || job.processed_files;
  const failedDocs = batchProgress?.failed || job.failed_files;

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-4"
      data-testid={`job-card-${job.job_id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`${statusStyles.bg} ${statusStyles.text} px-2 py-1 rounded text-xs font-medium flex items-center gap-1`} data-testid={`job-status-${job.job_id}`}>
              {statusStyles.icon}
              {job.status}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {formatRelativeTime(job.created_at)}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {job.directory_path}
          </p>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
          data-testid={`expand-job-${job.job_id}`}
        >
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </button>
      </div>

      {/* Overall Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-700 dark:text-gray-300 font-medium">
            Overall Progress
          </span>
          <span className="text-gray-600 dark:text-gray-400" data-testid={`job-overall-progress-${job.job_id}`}>
            {completedDocs}/{job.total_files} documents ({Math.round(overallProgress)}%)
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${
              job.status === 'failed'
                ? 'bg-red-500'
                : job.status === 'completed'
                ? 'bg-green-500'
                : 'bg-blue-500'
            }`}
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Statistics Row */}
      <div className="flex gap-6 text-sm mb-3">
        <div>
          <span className="text-gray-500 dark:text-gray-400">Completed: </span>
          <span className="text-green-600 dark:text-green-400 font-medium">{completedDocs}</span>
        </div>
        {batchProgress && (
          <div>
            <span className="text-gray-500 dark:text-gray-400">In Progress: </span>
            <span className="text-blue-600 dark:text-blue-400 font-medium">{batchProgress.in_progress}</span>
          </div>
        )}
        {failedDocs > 0 && (
          <div>
            <span className="text-gray-500 dark:text-gray-400">Failed: </span>
            <span className="text-red-600 dark:text-red-400 font-medium">{failedDocs}</span>
          </div>
        )}
      </div>

      {/* Expandable Details */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          {/* Currently Processing Documents */}
          {processingDocs.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                ⚡ Currently Processing ({processingDocs.length}/{batchProgress?.parallel_limit || 3} slots)
              </h3>
              <div className="space-y-2">
                {processingDocs.map((doc) => (
                  <DocumentProgressItem key={doc.document_id} doc={doc} />
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            {job.status === 'running' && (
              <button
                onClick={() => onCancel(job.job_id)}
                className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                data-testid={`cancel-job-${job.job_id}`}
              >
                Cancel Job
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * IngestionJobList - Main component
 */
export function IngestionJobList() {
  const [jobs, setJobs] = useState<IngestionJobResponse[]>([]);
  const [batchProgresses, setBatchProgresses] = useState<Map<string, BatchProgress>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load jobs on mount
  const loadJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const jobList = await listIngestionJobs({ limit: 50 });
      setJobs(jobList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();

    // Refresh jobs every 10 seconds
    const interval = setInterval(loadJobs, 10000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  // Setup SSE for running jobs
  useEffect(() => {
    const controllers = new Map<string, AbortController>();

    for (const job of jobs) {
      if (job.status === 'running') {
        const controller = new AbortController();
        controllers.set(job.job_id, controller);

        // Start SSE stream
        (async () => {
          try {
            for await (const progress of streamBatchProgress(job.job_id, controller.signal)) {
              setBatchProgresses((prev) => new Map(prev).set(job.job_id, progress));
            }
          } catch (err) {
            if (err instanceof Error && err.name !== 'AbortError') {
              console.error(`SSE stream error for job ${job.job_id}:`, err);
            }
          }
        })();
      }
    }

    // Cleanup
    return () => {
      for (const controller of controllers.values()) {
        controller.abort();
      }
    };
  }, [jobs]);

  // Handle job cancellation
  const handleCancel = useCallback(async (jobId: string) => {
    try {
      await cancelIngestionJob(jobId);
      await loadJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to cancel job:', err);
      alert(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  }, [loadJobs]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-200">{error}</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center">
        <p className="text-gray-600 dark:text-gray-400">No ingestion jobs found</p>
      </div>
    );
  }

  // Separate running and completed jobs
  const runningJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending');
  const completedJobs = jobs.filter(j => j.status !== 'running' && j.status !== 'pending');

  return (
    <div className="space-y-6" data-testid="ingestion-jobs-list">
      {/* Active Jobs */}
      {runningJobs.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Active Jobs ({runningJobs.length})
          </h2>
          <div className="space-y-4">
            {runningJobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                batchProgress={batchProgresses.get(job.job_id)}
                onCancel={handleCancel}
              />
            ))}
          </div>
        </div>
      )}

      {/* Completed Jobs */}
      {completedJobs.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Completed Jobs ({completedJobs.length})
          </h2>
          <div className="space-y-4">
            {completedJobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                batchProgress={batchProgresses.get(job.job_id)}
                onCancel={handleCancel}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default IngestionJobList;
