/**
 * PipelineProgressVisualization Component
 * Sprint 37 Feature 37.4: Visual Pipeline Progress Component
 *
 * Main container component for displaying visual pipeline progress with:
 * - Pipeline stage flow diagram
 * - Worker pool status
 * - Live metrics (entities, relations, database writes)
 * - Timing information (elapsed, ETA)
 */

import React from 'react';
import { StageProgressBar } from './StageProgressBar';
import { WorkerPoolDisplay } from './WorkerPoolDisplay';
import type { PipelineProgressData } from '../../types/admin';

interface PipelineProgressVisualizationProps {
  progress: PipelineProgressData | null;
  isProcessing: boolean;
}

/**
 * Format milliseconds to human-readable time string
 */
function formatTime(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }

  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export const PipelineProgressVisualization: React.FC<PipelineProgressVisualizationProps> = ({
  progress,
  isProcessing,
}) => {
  // Show placeholder if no progress data
  if (!progress) {
    return (
      <div
        className="bg-gray-50 rounded-md p-6 text-center text-gray-500"
        data-testid="pipeline-progress-container"
      >
        {isProcessing ? (
          <div className="flex flex-col items-center space-y-2">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
            <p className="text-sm">Initializing pipeline...</p>
          </div>
        ) : (
          <p className="text-sm">No active pipeline processing</p>
        )}
      </div>
    );
  }

  const { stages, worker_pool, metrics, timing, document_name, total_chunks, total_images, overall_progress_percent } = progress;

  return (
    <div
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4"
      data-testid="pipeline-progress-container"
    >
      {/* Header Section */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <h2
            className="text-sm font-semibold text-gray-900 truncate"
            data-testid="document-name"
            title={document_name}
          >
            {document_name}
          </h2>
          <div
            className="text-lg font-bold text-blue-600"
            data-testid="overall-progress"
          >
            {overall_progress_percent.toFixed(0)}%
          </div>
        </div>

        {/* Document Statistics */}
        <div className="flex items-center space-x-3 text-xs text-gray-600">
          <div data-testid="total-chunks">
            Chunks: <span className="font-semibold text-gray-900">{total_chunks}</span>
          </div>
          <div className="w-px h-3 bg-gray-300" />
          <div data-testid="total-images">
            Images: <span className="font-semibold text-gray-900">{total_images}</span>
          </div>
          <div className="w-px h-3 bg-gray-300" />
          <div data-testid="timing-elapsed">
            Elapsed: <span className="font-semibold text-gray-900">{formatTime(timing.elapsed_ms)}</span>
          </div>
          <div className="w-px h-3 bg-gray-300" />
          <div data-testid="timing-remaining">
            ETA:{' '}
            <span className="font-semibold text-gray-900">
              {timing.estimated_remaining_ms > 0 ? formatTime(timing.estimated_remaining_ms) : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* Pipeline Stages Section */}
      <div className="bg-gray-50 rounded-md p-4">
        <h3 className="text-xs font-semibold text-gray-700 mb-3 uppercase tracking-wide">
          Pipeline Stages
        </h3>

        {/* Desktop View: Horizontal Flow */}
        <div className="hidden md:flex items-center justify-start space-x-0 overflow-x-auto pb-1">
          <StageProgressBar stage={stages.parsing} showArrow />
          <StageProgressBar stage={stages.vlm} showArrow />
          <StageProgressBar stage={stages.chunking} showArrow />
          <StageProgressBar stage={stages.embedding} showArrow />

          {/* Extraction with flow from Embedding */}
          <div className="flex flex-col items-center">
            {/* Down Arrow from Embedding */}
            <div className="text-gray-400 mb-1">
              <svg
                className="w-4 h-4 transform rotate-90"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 14l-7 7m0 0l-7-7m7 7V3"
                />
              </svg>
            </div>
            <StageProgressBar stage={stages.extraction} />
          </div>
        </div>

        {/* Mobile View: Vertical Stack */}
        <div className="md:hidden space-y-3">
          <StageProgressBar stage={stages.parsing} />
          <StageProgressBar stage={stages.vlm} />
          <StageProgressBar stage={stages.chunking} />
          <StageProgressBar stage={stages.embedding} />
          <StageProgressBar stage={stages.extraction} />
        </div>
      </div>

      {/* Worker Pool Section */}
      <WorkerPoolDisplay
        workers={worker_pool.workers}
        queueDepth={worker_pool.queue_depth}
        maxWorkers={worker_pool.max}
      />

      {/* Live Metrics Section */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-md p-3 border border-blue-200">
        <h3 className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
          Live Metrics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {/* Entities */}
          <div className="bg-white rounded-md p-2 shadow-sm" data-testid="metrics-entities">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Entities</div>
            <div className="text-lg font-bold text-indigo-600">{metrics.entities_total}</div>
          </div>

          {/* Relations */}
          <div className="bg-white rounded-md p-2 shadow-sm" data-testid="metrics-relations">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Relations</div>
            <div className="text-lg font-bold text-purple-600">{metrics.relations_total}</div>
          </div>

          {/* Qdrant Writes */}
          <div className="bg-white rounded-md p-2 shadow-sm" data-testid="metrics-qdrant">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Qdrant</div>
            <div className="text-lg font-bold text-green-600">{metrics.qdrant_writes}</div>
          </div>

          {/* Neo4j Writes */}
          <div className="bg-white rounded-md p-2 shadow-sm" data-testid="metrics-neo4j">
            <div className="text-xs text-gray-600 uppercase tracking-wide">Neo4j</div>
            <div className="text-lg font-bold text-blue-600">{metrics.neo4j_writes}</div>
          </div>
        </div>
      </div>

      {/* Overall Progress Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-gray-700">Overall Progress</span>
          <span className="font-bold text-gray-900">{overall_progress_percent.toFixed(1)}%</span>
        </div>
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`
              h-full transition-all duration-300 rounded-full
              ${overall_progress_percent >= 100 ? 'bg-green-500' : 'bg-blue-600'}
            `}
            style={{ width: `${Math.min(100, overall_progress_percent)}%` }}
          />
        </div>
      </div>
    </div>
  );
};
