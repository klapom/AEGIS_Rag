/**
 * Error Types
 * Sprint 116 Feature 116.2: API Error Handling
 *
 * Type definitions for error handling system
 */

/**
 * HTTP Error Status Codes
 */
export enum HttpStatus {
  BAD_REQUEST = 400,
  UNAUTHORIZED = 401,
  FORBIDDEN = 403,
  NOT_FOUND = 404,
  PAYLOAD_TOO_LARGE = 413,
  INTERNAL_SERVER_ERROR = 500,
  BAD_GATEWAY = 502,
  SERVICE_UNAVAILABLE = 503,
  GATEWAY_TIMEOUT = 504,
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  /** Critical errors requiring immediate attention */
  CRITICAL = 'critical',
  /** Errors that prevent normal operation */
  ERROR = 'error',
  /** Warnings that don't prevent operation */
  WARNING = 'warning',
  /** Informational messages */
  INFO = 'info',
}

/**
 * Custom API Error class
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown,
    public retryable: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /**
   * Check if error is retryable based on status code
   */
  static isRetryable(status: number): boolean {
    return [408, 429, 500, 502, 503, 504].includes(status);
  }

  /**
   * Get user-friendly message for status code
   */
  static getUserMessage(status: number): string {
    switch (status) {
      case HttpStatus.BAD_REQUEST:
        return 'Invalid request. Please check your input.';
      case HttpStatus.UNAUTHORIZED:
        return 'You are not authorized. Please log in again.';
      case HttpStatus.FORBIDDEN:
        return 'You do not have permission to perform this action.';
      case HttpStatus.NOT_FOUND:
        return 'The requested resource was not found.';
      case HttpStatus.PAYLOAD_TOO_LARGE:
        return 'File is too large. Maximum size is 50 MB.';
      case HttpStatus.INTERNAL_SERVER_ERROR:
        return 'Something went wrong. Please try again.';
      case HttpStatus.BAD_GATEWAY:
        return 'Service temporarily unavailable. Please try again.';
      case HttpStatus.SERVICE_UNAVAILABLE:
        return 'Service is currently unavailable. Please try again later.';
      case HttpStatus.GATEWAY_TIMEOUT:
        return 'Request timed out. The server is busy.';
      default:
        if (status >= 500) {
          return 'Server error. Please try again later.';
        }
        return 'An unexpected error occurred.';
    }
  }

  /**
   * Get error severity based on status code
   */
  static getSeverity(status: number): ErrorSeverity {
    if (status >= 500) return ErrorSeverity.CRITICAL;
    if (status >= 400) return ErrorSeverity.ERROR;
    return ErrorSeverity.WARNING;
  }
}

/**
 * Toast notification type
 */
export interface ToastNotification {
  id: string;
  message: string;
  severity: ErrorSeverity;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

/**
 * Error display configuration
 */
export interface ErrorDisplayConfig {
  /** Show error in toast notification */
  showToast: boolean;
  /** Show full-page error state */
  showFullPage: boolean;
  /** Allow retry */
  allowRetry: boolean;
  /** Custom error message */
  customMessage?: string;
}

/**
 * Retry configuration
 */
export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Base delay in milliseconds */
  baseDelay: number;
  /** Maximum delay in milliseconds */
  maxDelay: number;
  /** Exponential backoff multiplier */
  backoffMultiplier: number;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
};
