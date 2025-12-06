/**
 * StageProgressBar Component
 * Sprint 37 Feature 37.4: Visual Pipeline Progress Component
 *
 * Displays individual stage progress with animated progress bar, status indicators, and counters
 */

import React from 'react';
import type { StageProgress } from '../../types/admin';

interface StageProgressBarProps {
  stage: StageProgress;
  showArrow?: boolean;
}

/**
 * Get status color classes based on stage status
 */
function getStatusColor(status: StageProgress['status']): {
  bg: string;
  border: string;
  text: string;
} {
  switch (status) {
    case 'pending':
      return {
        bg: 'bg-gray-200',
        border: 'border-gray-300',
        text: 'text-gray-600',
      };
    case 'in_progress':
      return {
        bg: 'bg-blue-500',
        border: 'border-blue-600',
        text: 'text-blue-900',
      };
    case 'completed':
      return {
        bg: 'bg-green-500',
        border: 'border-green-600',
        text: 'text-green-900',
      };
    case 'error':
      return {
        bg: 'bg-red-500',
        border: 'border-red-600',
        text: 'text-red-900',
      };
    default:
      return {
        bg: 'bg-gray-200',
        border: 'border-gray-300',
        text: 'text-gray-600',
      };
  }
}

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(durationMs: number): string {
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  const seconds = Math.floor(durationMs / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export const StageProgressBar: React.FC<StageProgressBarProps> = ({ stage, showArrow = false }) => {
  const colors = getStatusColor(stage.status);
  const progressPercent = Math.min(100, Math.max(0, stage.progress_percent));
  const isActive = stage.status === 'in_progress';

  return (
    <div className="relative flex items-center">
      {/* Stage Box */}
      <div
        className={`
          flex flex-col items-center bg-white rounded-lg p-4 border-2
          ${colors.border} shadow-sm transition-all duration-300
          ${isActive ? 'ring-2 ring-blue-300 ring-opacity-50' : ''}
          min-w-[120px]
        `}
        data-testid={`stage-${stage.name.toLowerCase()}`}
      >
        {/* Stage Name */}
        <div className={`text-xs font-semibold uppercase mb-2 ${colors.text}`}>
          {stage.name}
        </div>

        {/* Progress Bar Container */}
        <div
          className="w-full h-3 bg-gray-200 rounded-full overflow-hidden mb-2"
          data-testid={`stage-progress-bar-${stage.name.toLowerCase()}`}
        >
          <div
            className={`h-full transition-all duration-300 rounded-full ${colors.bg}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Counter */}
        <div
          className="flex items-center space-x-1 text-xs font-medium text-gray-700"
          data-testid={`stage-counter-${stage.name.toLowerCase()}`}
        >
          <span>{stage.processed}</span>
          <span>/</span>
          <span>{stage.total}</span>

          {/* In-Flight Indicator */}
          {stage.in_flight > 0 && (
            <span className="ml-1 text-blue-600" title="Currently processing">
              (+{stage.in_flight})
            </span>
          )}

          {/* Completion Checkmark */}
          {stage.is_complete && (
            <svg
              className="w-4 h-4 text-green-600 ml-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-label="Completed"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
        </div>

        {/* Duration (if available) */}
        {stage.duration_ms > 0 && (
          <div className="text-xs text-gray-500 mt-1">
            {formatDuration(stage.duration_ms)}
          </div>
        )}
      </div>

      {/* Arrow to Next Stage */}
      {showArrow && (
        <div className="mx-2 text-gray-400">
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M14 5l7 7m0 0l-7 7m7-7H3"
            />
          </svg>
        </div>
      )}
    </div>
  );
};
