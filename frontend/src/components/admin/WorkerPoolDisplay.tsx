/**
 * WorkerPoolDisplay Component
 * Sprint 37 Feature 37.4: Visual Pipeline Progress Component
 *
 * Displays worker pool status with individual worker indicators and queue depth
 */

import React from 'react';
import type { WorkerInfo } from '../../types/admin';

interface WorkerPoolDisplayProps {
  workers: WorkerInfo[];
  queueDepth: number;
  maxWorkers: number;
}

/**
 * Get worker status color classes
 */
function getWorkerStatusColor(status: WorkerInfo['status']): {
  bg: string;
  border: string;
} {
  switch (status) {
    case 'idle':
      return {
        bg: 'bg-gray-300',
        border: 'border-gray-400',
      };
    case 'processing':
      return {
        bg: 'bg-blue-500',
        border: 'border-blue-600',
      };
    case 'error':
      return {
        bg: 'bg-red-500',
        border: 'border-red-600',
      };
    default:
      return {
        bg: 'bg-gray-300',
        border: 'border-gray-400',
      };
  }
}

/**
 * Individual worker indicator component
 */
const WorkerIndicator: React.FC<{ worker: WorkerInfo }> = ({ worker }) => {
  const colors = getWorkerStatusColor(worker.status);
  const progressPercent = Math.min(100, Math.max(0, worker.progress_percent));

  return (
    <div
      className="flex flex-col items-center space-y-1"
      data-testid={`worker-${worker.id}`}
    >
      {/* Worker Label */}
      <div className="text-xs font-medium text-gray-700">
        W{worker.id}
      </div>

      {/* Worker Bar with Progress */}
      <div
        className={`
          relative w-16 h-6 rounded border-2 overflow-hidden
          ${colors.border} bg-white transition-all duration-300
        `}
        title={
          worker.status === 'processing'
            ? `Processing: ${worker.current_chunk || 'unknown chunk'}`
            : worker.status === 'idle'
            ? 'Idle'
            : 'Error'
        }
        data-testid={`worker-status-${worker.id}`}
      >
        {/* Progress Bar */}
        <div
          className={`h-full transition-all duration-300 ${colors.bg}`}
          style={{ width: `${progressPercent}%` }}
        />

        {/* Status Icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          {worker.status === 'processing' && (
            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
          )}
          {worker.status === 'error' && (
            <svg
              className="w-3 h-3 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Progress Percentage (if processing) */}
      {worker.status === 'processing' && (
        <div className="text-xs text-gray-600">
          {progressPercent.toFixed(0)}%
        </div>
      )}
    </div>
  );
};

export const WorkerPoolDisplay: React.FC<WorkerPoolDisplayProps> = ({
  workers,
  queueDepth,
  maxWorkers,
}) => {
  const activeWorkers = workers.filter((w) => w.status === 'processing').length;

  return (
    <div
      className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm"
      data-testid="worker-pool-container"
    >
      <div className="flex items-center justify-between mb-3">
        {/* Title */}
        <h3 className="text-sm font-semibold text-gray-900">
          Worker Pool ({activeWorkers}/{maxWorkers})
        </h3>

        {/* Queue Depth */}
        <div
          className="flex items-center space-x-2 text-sm"
          data-testid="queue-depth"
        >
          <span className="text-gray-600">Queue:</span>
          <span
            className={`
              font-semibold px-2 py-0.5 rounded
              ${
                queueDepth > 10
                  ? 'bg-yellow-100 text-yellow-800'
                  : queueDepth > 0
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-700'
              }
            `}
          >
            {queueDepth}
          </span>
        </div>
      </div>

      {/* Worker Indicators */}
      <div className="flex flex-wrap gap-3">
        {workers.map((worker) => (
          <WorkerIndicator key={worker.id} worker={worker} />
        ))}
      </div>

      {/* Status Summary */}
      <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-600">
        <div className="flex items-center justify-between">
          <span>
            {activeWorkers} active, {workers.filter((w) => w.status === 'idle').length} idle
            {workers.filter((w) => w.status === 'error').length > 0 &&
              `, ${workers.filter((w) => w.status === 'error').length} error`}
          </span>
          {queueDepth > 0 && (
            <span className="text-blue-600">
              {queueDepth} chunk{queueDepth !== 1 ? 's' : ''} queued
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
