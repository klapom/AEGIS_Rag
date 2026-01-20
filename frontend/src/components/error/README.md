# Error Handling Components

Sprint 116 Feature 116.2: API Error Handling

## Overview

This directory contains comprehensive error handling components for graceful API error management with user-friendly messages, toast notifications, and retry mechanisms.

## Components

### 1. ErrorBoundary

React Error Boundary component to catch and display errors in the component tree.

**Usage:**
```tsx
import { ErrorBoundary } from './components/error/ErrorBoundary';

<ErrorBoundary onError={logError}>
  <YourComponent />
</ErrorBoundary>
```

**Props:**
- `children`: React components to wrap
- `fallback?`: Custom fallback UI to display on error
- `onError?`: Callback function when error occurs
- `showReset?`: Whether to show reset button (default: true)

### 2. ApiErrorDisplay

Component to display API errors with user-friendly messages and retry options.

**Usage:**
```tsx
import { ApiErrorDisplay } from './components/error/ApiErrorDisplay';

<ApiErrorDisplay
  error={error}
  onRetry={handleRetry}
  onDismiss={handleDismiss}
  variant="inline" // or "page"
/>
```

**Props:**
- `error`: Error or ApiError object to display
- `message?`: Custom error message override
- `onRetry?`: Retry button click handler
- `onDismiss?`: Dismiss button click handler
- `variant?`: Display style - 'inline' (default) or 'page'

### 3. ToastContainer

Renders toast notifications at the top-right of the screen.

**Usage:**
```tsx
import { ToastContainer } from './components/error/ToastContainer';

// Place at root of app
<ToastProvider>
  <ToastContainer />
  <App />
</ToastProvider>
```

## Hooks

### useApiError

Centralized error handling hook with retry logic.

**Usage:**
```tsx
import { useApiError } from './hooks/useApiError';

function MyComponent() {
  const { execute, error, retry, isLoading, isRetrying } = useApiError({
    showToast: true,
    retryConfig: { maxRetries: 3 }
  });

  const handleSubmit = async () => {
    const result = await execute(() =>
      apiClient.post('/endpoint', data)
    );

    if (result) {
      // Success - result contains the response data
    }
    // Error is automatically handled
  };

  return (
    <div>
      {error && <ApiErrorDisplay error={error} onRetry={retry} />}
      <button onClick={handleSubmit} disabled={isLoading}>
        {isLoading ? 'Loading...' : 'Submit'}
      </button>
    </div>
  );
}
```

**Options:**
- `showToast`: Show toast notification on error (default: true)
- `customMessage`: Custom error message override
- `retryConfig`: Retry configuration
  - `maxRetries`: Maximum retry attempts (default: 3)
  - `baseDelay`: Base delay in ms (default: 1000)
  - `maxDelay`: Maximum delay in ms (default: 10000)
  - `backoffMultiplier`: Exponential backoff multiplier (default: 2)
- `onError`: Callback when error occurs

**Return Values:**
- `error`: Current error state
- `isLoading`: Whether currently loading
- `isRetrying`: Whether currently retrying
- `retryCount`: Number of retry attempts
- `execute`: Execute API call with error handling
- `retry`: Manually retry last failed call
- `clearError`: Clear error state
- `setError`: Set error state manually

### useToast

Hook to access toast notification context.

**Usage:**
```tsx
import { useToast } from './contexts/ToastContext';

function MyComponent() {
  const { showToast } = useToast();

  const handleClick = () => {
    showToast('Operation successful!', 'info', 5000);
  };

  return <button onClick={handleClick}>Show Toast</button>;
}
```

## Types

### ApiError

Custom error class with additional metadata.

```tsx
import { ApiError } from './types/errors';

throw new ApiError(
  'User-friendly message',
  500, // HTTP status code
  { details: 'additional data' },
  true // retryable
);
```

**Static Methods:**
- `ApiError.getUserMessage(status)`: Get user-friendly message for status code
- `ApiError.getSeverity(status)`: Get error severity level
- `ApiError.isRetryable(status)`: Check if error is retryable

### Error Severity Levels

```tsx
enum ErrorSeverity {
  CRITICAL = 'critical',  // Critical errors requiring immediate attention
  ERROR = 'error',        // Errors that prevent normal operation
  WARNING = 'warning',    // Warnings that don't prevent operation
  INFO = 'info',          // Informational messages
}
```

## HTTP Status Code Mappings

The system provides user-friendly messages for common HTTP errors:

- **400 Bad Request**: "Invalid request. Please check your input."
- **401 Unauthorized**: "You are not authorized. Please log in again."
- **403 Forbidden**: "You do not have permission to perform this action."
- **404 Not Found**: "The requested resource was not found."
- **413 Payload Too Large**: "File is too large. Maximum size is 50 MB."
- **500 Internal Server Error**: "Something went wrong. Please try again."
- **502 Bad Gateway**: "Service temporarily unavailable. Please try again."
- **503 Service Unavailable**: "Service is currently unavailable. Please try again later."
- **504 Gateway Timeout**: "Request timed out. The server is busy."

## Complete Example

```tsx
import { useState } from 'react';
import { useApiError } from './hooks/useApiError';
import { ApiErrorDisplay } from './components/error/ApiErrorDisplay';
import { apiClient } from './lib/api';

function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null);
  const { execute, error, retry, isLoading, clearError } = useApiError({
    showToast: true,
    retryConfig: { maxRetries: 3 },
  });

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const result = await execute(() =>
      apiClient.post('/api/v1/upload', formData)
    );

    if (result) {
      console.log('Upload successful:', result);
      setFile(null);
      clearError();
    }
  };

  return (
    <div>
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />

      <button onClick={handleUpload} disabled={isLoading || !file}>
        {isLoading ? 'Uploading...' : 'Upload'}
      </button>

      {error && (
        <ApiErrorDisplay
          error={error}
          onRetry={retry}
          onDismiss={clearError}
        />
      )}
    </div>
  );
}
```

## Testing

All components and hooks include comprehensive unit tests:

- `ErrorBoundary.test.tsx`: Error boundary component tests
- `ApiErrorDisplay.test.tsx`: API error display tests
- `useApiError.test.ts`: Error handling hook tests
- `ToastContext.test.tsx`: Toast notification context tests

Run tests:
```bash
npm run test:unit
```

## Integration with Existing Code

The error handling system is automatically integrated into:

1. **API Client** (`src/lib/api.ts`): All API calls throw `ApiError` with proper status codes
2. **App Component** (`src/App.tsx`): Wrapped with `ErrorBoundary` and `ToastProvider`
3. **Toast Notifications**: Global toast container rendered at app root

No changes required to existing components - errors are automatically handled!
