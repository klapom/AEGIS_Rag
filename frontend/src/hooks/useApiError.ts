/**
 * useApiError Hook
 * Sprint 116 Feature 116.2: API Error Handling
 *
 * Centralized error handling hook for API calls with retry logic
 */

import { useState, useCallback, useRef } from 'react';
import { useToast } from '../contexts/ToastContext';
import {
  ApiError,
  ErrorSeverity,
  type RetryConfig,
  DEFAULT_RETRY_CONFIG,
} from '../types/errors';

interface UseApiErrorOptions {
  /** Show toast notification on error */
  showToast?: boolean;
  /** Custom error message */
  customMessage?: string;
  /** Retry configuration */
  retryConfig?: Partial<RetryConfig>;
  /** Callback when error occurs */
  onError?: (error: Error) => void;
}

interface UseApiErrorReturn {
  /** Current error state */
  error: Error | ApiError | null;
  /** Whether currently loading */
  isLoading: boolean;
  /** Whether currently retrying */
  isRetrying: boolean;
  /** Number of retry attempts */
  retryCount: number;
  /** Execute API call with error handling */
  execute: <T>(apiCall: () => Promise<T>) => Promise<T | null>;
  /** Manually retry the last failed call */
  retry: () => Promise<void>;
  /** Clear error state */
  clearError: () => void;
  /** Set error state manually */
  setError: (error: Error | ApiError) => void;
}

/**
 * Hook for handling API errors with retry logic
 *
 * Usage:
 * ```tsx
 * const { execute, error, retry, isLoading } = useApiError({
 *   showToast: true,
 *   retryConfig: { maxRetries: 3 }
 * });
 *
 * const handleSubmit = async () => {
 *   const result = await execute(() => apiClient.post('/endpoint', data));
 *   if (result) {
 *     // Success
 *   }
 * };
 * ```
 */
export function useApiError(options: UseApiErrorOptions = {}): UseApiErrorReturn {
  const {
    showToast = true,
    customMessage,
    retryConfig: customRetryConfig,
    onError,
  } = options;

  const { showToast: showToastNotification } = useToast();
  const [error, setErrorState] = useState<Error | ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Store last API call for retry
  const lastApiCall = useRef<(() => Promise<unknown>) | null>(null);

  // Merge retry config with defaults
  const retryConfig: RetryConfig = {
    ...DEFAULT_RETRY_CONFIG,
    ...customRetryConfig,
  };

  /**
   * Calculate delay with exponential backoff
   */
  const calculateDelay = useCallback(
    (attempt: number): number => {
      const delay = Math.min(
        retryConfig.baseDelay * Math.pow(retryConfig.backoffMultiplier, attempt),
        retryConfig.maxDelay
      );
      return delay;
    },
    [retryConfig]
  );

  /**
   * Set error and show toast if enabled
   */
  const setError = useCallback(
    (err: Error | ApiError) => {
      setErrorState(err);

      // Call custom error handler
      onError?.(err);

      // Show toast notification
      if (showToast) {
        const isApiError = err instanceof ApiError;
        const message =
          customMessage ||
          (isApiError ? ApiError.getUserMessage(err.status) : err.message);

        const severity = isApiError
          ? ApiError.getSeverity(err.status)
          : ErrorSeverity.ERROR;

        showToastNotification(message, severity);
      }
    },
    [showToast, customMessage, onError, showToastNotification]
  );

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setErrorState(null);
    setRetryCount(0);
  }, []);

  /**
   * Execute API call with error handling and retry logic
   */
  const execute = useCallback(
    async <T,>(apiCall: () => Promise<T>): Promise<T | null> => {
      // Store for potential retry
      lastApiCall.current = apiCall;

      // Reset state
      clearError();
      setIsLoading(true);

      let lastError: Error | ApiError | null = null;

      // Attempt with retries
      for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
        try {
          const result = await apiCall();
          setIsLoading(false);
          setIsRetrying(false);
          return result;
        } catch (err) {
          lastError = err instanceof Error ? err : new Error(String(err));

          // Check if error is retryable
          const isRetryable =
            err instanceof ApiError
              ? err.retryable
              : err instanceof Error && ApiError.isRetryable(500);

          // Don't retry if not retryable or max retries reached
          if (!isRetryable || attempt >= retryConfig.maxRetries) {
            break;
          }

          // Update retry state
          setRetryCount(attempt + 1);
          setIsRetrying(true);

          // Wait before retry with exponential backoff
          const delay = calculateDelay(attempt);
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }

      // All retries failed
      setIsLoading(false);
      setIsRetrying(false);

      if (lastError) {
        setError(lastError);
      }

      return null;
    },
    [clearError, retryConfig, calculateDelay, setError]
  );

  /**
   * Manually retry the last failed API call
   */
  const retry = useCallback(async (): Promise<void> => {
    if (!lastApiCall.current) {
      console.warn('No API call to retry');
      return;
    }

    await execute(lastApiCall.current);
  }, [execute]);

  return {
    error,
    isLoading,
    isRetrying,
    retryCount,
    execute,
    retry,
    clearError,
    setError,
  };
}
