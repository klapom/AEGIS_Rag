/**
 * Error Boundary Component
 * Sprint 116 Feature 116.2: API Error Handling
 *
 * React Error Boundary to catch and display errors in component tree
 * Provides fallback UI and error recovery mechanisms
 */

import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

// ErrorInfo type for React Error Boundaries
interface ErrorInfo {
  componentStack?: string;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback UI */
  fallback?: ReactNode;
  /** Callback when error occurs */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Whether to show reset button */
  showReset?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary component
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary onError={logError}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console
    console.error('ErrorBoundary caught error:', error, errorInfo);

    // Update state
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler
    this.props.onError?.(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback, showReset = true } = this.props;

    if (hasError) {
      // Use custom fallback if provided
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <div
          className="min-h-screen flex items-center justify-center bg-gray-50 px-4"
          data-testid="error-boundary"
        >
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
            {/* Error Icon */}
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-100 mb-4 mx-auto">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>

            {/* Error Message */}
            <h2
              className="text-xl font-bold text-gray-900 text-center mb-2"
              data-testid="error-title"
            >
              Something went wrong
            </h2>
            <p className="text-sm text-gray-600 text-center mb-6">
              An unexpected error occurred. We&apos;re sorry for the inconvenience.
            </p>

            {/* Error Details (Development only) */}
            {import.meta.env.DEV && error && (
              <details className="mb-6 text-xs">
                <summary className="cursor-pointer font-medium text-gray-700 hover:text-gray-900 mb-2">
                  Show error details
                </summary>
                <div className="bg-gray-50 rounded p-3 border border-gray-200 overflow-auto max-h-48">
                  <p className="font-mono text-red-600 mb-2">{error.toString()}</p>
                  {errorInfo?.componentStack && (
                    <pre className="font-mono text-gray-600 text-xs overflow-auto">
                      {errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            {/* Reset Button */}
            {showReset && (
              <button
                onClick={this.handleReset}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                data-testid="error-reset-button"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Try Again</span>
              </button>
            )}

            {/* Contact Support */}
            <p className="mt-4 text-xs text-gray-500 text-center">
              If this problem persists, please contact support.
            </p>
          </div>
        </div>
      );
    }

    return children;
  }
}
