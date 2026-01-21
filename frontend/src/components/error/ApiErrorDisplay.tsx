/**
 * API Error Display Component
 * Sprint 116 Feature 116.2: API Error Handling
 *
 * Displays API errors with user-friendly messages and retry options
 */

import { AlertTriangle, RefreshCw, XCircle } from 'lucide-react';
import { ApiError, ErrorSeverity } from '../../types/errors';

interface ApiErrorDisplayProps {
  /** Error to display */
  error: Error | ApiError | null;
  /** Optional custom message */
  message?: string;
  /** Whether to show retry button */
  onRetry?: () => void;
  /** Whether to show dismiss button */
  onDismiss?: () => void;
  /** Whether to show as inline message or full-page error */
  variant?: 'inline' | 'page';
}

/**
 * API Error Display Component
 *
 * Usage:
 * ```tsx
 * <ApiErrorDisplay
 *   error={error}
 *   onRetry={handleRetry}
 *   onDismiss={handleDismiss}
 * />
 * ```
 */
export function ApiErrorDisplay({
  error,
  message,
  onRetry,
  onDismiss,
  variant = 'inline',
}: ApiErrorDisplayProps) {
  if (!error) return null;

  // Extract error details
  const isApiError = error instanceof ApiError;
  const status = isApiError ? error.status : 500;
  const severity = isApiError
    ? ApiError.getSeverity(status)
    : ErrorSeverity.ERROR;
  const userMessage =
    message || (isApiError ? ApiError.getUserMessage(status) : error.message);
  const canRetry = isApiError ? error.retryable : ApiError.isRetryable(status);

  // Color scheme based on severity
  const colorScheme = {
    [ErrorSeverity.CRITICAL]: {
      bg: 'bg-red-50',
      border: 'border-red-300',
      text: 'text-red-800',
      icon: 'text-red-600',
      button: 'bg-red-600 hover:bg-red-700',
    },
    [ErrorSeverity.ERROR]: {
      bg: 'bg-red-50',
      border: 'border-red-300',
      text: 'text-red-800',
      icon: 'text-red-600',
      button: 'bg-red-600 hover:bg-red-700',
    },
    [ErrorSeverity.WARNING]: {
      bg: 'bg-orange-50',
      border: 'border-orange-300',
      text: 'text-orange-800',
      icon: 'text-orange-600',
      button: 'bg-orange-600 hover:bg-orange-700',
    },
    [ErrorSeverity.INFO]: {
      bg: 'bg-blue-50',
      border: 'border-blue-300',
      text: 'text-blue-800',
      icon: 'text-blue-600',
      button: 'bg-blue-600 hover:bg-blue-700',
    },
  };

  const colors = colorScheme[severity];

  if (variant === 'page') {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-gray-50 px-4"
        data-testid="api-error-page"
      >
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
          {/* Error Icon */}
          <div
            className={`flex items-center justify-center w-12 h-12 rounded-full ${colors.bg} mb-4 mx-auto`}
          >
            <XCircle className={`w-6 h-6 ${colors.icon}`} />
          </div>

          {/* Error Message */}
          <h2 className="text-xl font-bold text-gray-900 text-center mb-2">
            Error {status}
          </h2>
          <p className="text-sm text-gray-600 text-center mb-6">{userMessage}</p>

          {/* Error Details (Development only) */}
          {import.meta.env.DEV && (
            <details className="mb-6 text-xs">
              <summary className="cursor-pointer font-medium text-gray-700 hover:text-gray-900 mb-2">
                Show error details
              </summary>
              <div className="bg-gray-50 rounded p-3 border border-gray-200 overflow-auto max-h-48">
                <p className="font-mono text-gray-600">{error.message}</p>
                {isApiError && error.data && (
                  <pre className="mt-2 font-mono text-xs text-gray-500 overflow-auto">
                    {JSON.stringify(error.data, null, 2)}
                  </pre>
                )}
              </div>
            </details>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-2">
            {canRetry && onRetry && (
              <button
                onClick={onRetry}
                className={`flex-1 flex items-center justify-center space-x-2 px-4 py-2 ${colors.button} text-white rounded-lg font-semibold transition-colors`}
                data-testid="error-retry-button"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Try Again</span>
              </button>
            )}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
                data-testid="error-dismiss-button"
              >
                Dismiss
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Inline variant
  return (
    <div
      className={`border-2 ${colors.border} ${colors.bg} rounded-lg p-4`}
      data-testid="api-error-inline"
      role="alert"
    >
      <div className="flex items-start space-x-3">
        {/* Icon */}
        <AlertTriangle className={`w-5 h-5 ${colors.icon} flex-shrink-0 mt-0.5`} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className={`font-semibold ${colors.text}`}>
            {severity === ErrorSeverity.CRITICAL ? 'Critical Error' : 'Error'}
          </p>
          <p className={`text-sm ${colors.text} mt-1`}>{userMessage}</p>

          {/* Error Details (Development only) */}
          {import.meta.env.DEV && (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs font-medium opacity-80 hover:opacity-100">
                Show details
              </summary>
              <div className="mt-2 text-xs font-mono bg-white rounded p-2 border border-current opacity-80 max-h-32 overflow-auto">
                {error.message}
              </div>
            </details>
          )}

          {/* Action Buttons */}
          {(onRetry || onDismiss) && (
            <div className="flex space-x-2 mt-3">
              {canRetry && onRetry && (
                <button
                  onClick={onRetry}
                  className={`flex items-center space-x-1 px-3 py-1.5 ${colors.button} text-white rounded text-sm font-semibold transition-colors`}
                  data-testid="error-retry-button"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Retry</span>
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded text-sm font-semibold hover:bg-gray-300 transition-colors"
                  data-testid="error-dismiss-button"
                >
                  Dismiss
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
