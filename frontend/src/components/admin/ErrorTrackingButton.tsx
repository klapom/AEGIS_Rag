/**
 * Error Tracking Button Component
 * Sprint 33 Feature 33.5: Error-Tracking mit Button (5 SP)
 *
 * Displays error count and opens dialog with error list
 * Supports CSV export of all errors
 *
 * Error Categories:
 * - ERROR (red): File skipped, critical issue
 * - WARNING (orange): Problem but processing continued
 * - INFO (blue): Informational message (e.g., fallback used)
 *
 * All data-testid attributes for E2E testing
 */

import { useState } from 'react';
import type { IngestionError } from '../../types/admin';

interface ErrorTrackingButtonProps {
  errors: IngestionError[];
  onExportCSV: () => void;
}

export function ErrorTrackingButton({ errors, onExportCSV }: ErrorTrackingButtonProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const errorCount = errors.filter((e) => e.type === 'error').length;
  const warningCount = errors.filter((e) => e.type === 'warning').length;
  const infoCount = errors.filter((e) => e.type === 'info').length;

  const hasErrors = errors.length > 0;
  const hasCriticalErrors = errorCount > 0;

  return (
    <>
      {/* Error Button */}
      <button
        data-testid="error-button"
        onClick={() => setIsDialogOpen(true)}
        className={`
          relative px-4 py-2 rounded-lg font-semibold
          transition-all
          ${
            hasCriticalErrors
              ? 'bg-red-600 text-white hover:bg-red-700'
              : hasErrors
                ? 'bg-orange-500 text-white hover:bg-orange-600'
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
          }
        `}
      >
        <span>Errors</span>
        {hasErrors && (
          <span
            data-testid="error-count-badge"
            className={`
              ml-2 px-2 py-0.5 rounded-full text-xs font-bold
              ${
                hasCriticalErrors
                  ? 'bg-red-800 text-white'
                  : 'bg-orange-700 text-white'
              }
            `}
          >
            {errors.length}
          </span>
        )}
      </button>

      {/* Error Dialog */}
      {isDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={() => setIsDialogOpen(false)}
        >
          <div
            data-testid="error-dialog"
            className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden m-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="bg-gray-50 border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Indexing Errors</h2>
                <div className="flex items-center space-x-4 mt-1 text-sm">
                  <span className="flex items-center space-x-1">
                    <span className="text-red-600 font-semibold">{errorCount}</span>
                    <span className="text-gray-600">Errors</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <span className="text-orange-600 font-semibold">{warningCount}</span>
                    <span className="text-gray-600">Warnings</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <span className="text-blue-600 font-semibold">{infoCount}</span>
                    <span className="text-gray-600">Info</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  data-testid="error-export-csv"
                  onClick={onExportCSV}
                  disabled={!hasErrors}
                  className="
                    px-4 py-2 rounded-lg font-semibold text-sm
                    bg-blue-600 text-white
                    hover:bg-blue-700
                    disabled:bg-gray-300 disabled:cursor-not-allowed
                    transition-all
                    flex items-center space-x-2
                  "
                >
                  <DownloadIcon />
                  <span>Export CSV</span>
                </button>

                <button
                  onClick={() => setIsDialogOpen(false)}
                  className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
                  aria-label="Close dialog"
                >
                  <CloseIcon />
                </button>
              </div>
            </div>

            {/* Error List */}
            <div
              data-testid="error-list"
              className="overflow-y-auto max-h-[calc(80vh-8rem)] p-6"
            >
              {errors.length === 0 ? (
                <div className="text-center py-12">
                  <SuccessIcon />
                  <p className="mt-4 text-lg font-medium text-gray-900">
                    No errors detected
                  </p>
                  <p className="mt-2 text-sm text-gray-600">
                    All files processed successfully!
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {errors.map((error, idx) => (
                    <ErrorListItem key={idx} error={error} />
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end">
              <button
                onClick={() => setIsDialogOpen(false)}
                className="px-6 py-2 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ============================================================================
// Utility Components
// ============================================================================

interface ErrorListItemProps {
  error: IngestionError;
}

function ErrorListItem({ error }: ErrorListItemProps) {
  const typeConfig = {
    error: {
      symbol: '❌',
      color: 'bg-red-500',
      borderColor: 'border-red-300',
      bgColor: 'bg-red-50',
      textColor: 'text-red-800',
      label: 'ERROR',
    },
    warning: {
      symbol: '⚠️',
      color: 'bg-orange-500',
      borderColor: 'border-orange-300',
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-800',
      label: 'WARNING',
    },
    info: {
      symbol: 'ℹ️',
      color: 'bg-blue-500',
      borderColor: 'border-blue-300',
      bgColor: 'bg-blue-50',
      textColor: 'text-blue-800',
      label: 'INFO',
    },
  };

  const config = typeConfig[error.type];

  return (
    <div className={`border-2 ${config.borderColor} ${config.bgColor} rounded-lg p-4`}>
      {/* Header */}
      <div className="flex items-start space-x-3 mb-2">
        <span className="text-2xl flex-shrink-0">{config.symbol}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <span className={`px-2 py-1 ${config.color} text-white rounded text-xs font-bold`}>
              {config.label}
            </span>
            <span className="text-xs text-gray-500">
              {formatTimestamp(error.timestamp)}
            </span>
          </div>

          <div className={`font-semibold ${config.textColor}`}>
            {error.file_name}
            {error.page_number !== undefined && (
              <span className="ml-2 text-sm font-normal opacity-80">
                (Page {error.page_number})
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Message */}
      <div className={`text-sm ${config.textColor} ml-11`}>
        {error.message}
      </div>

      {/* Details (collapsible) */}
      {error.details && (
        <details className="ml-11 mt-2">
          <summary className="cursor-pointer text-xs font-medium text-gray-700 hover:text-gray-900">
            Show details
          </summary>
          <div className="mt-2 text-xs font-mono bg-white rounded p-3 border border-gray-200 max-h-32 overflow-y-auto">
            {error.details}
          </div>
        </details>
      )}
    </div>
  );
}

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('de-DE', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

function CloseIcon() {
  return (
    <svg
      className="w-6 h-6 text-gray-600"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

function DownloadIcon() {
  return (
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
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
      />
    </svg>
  );
}

function SuccessIcon() {
  return (
    <svg
      className="w-16 h-16 text-green-500 mx-auto"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
