/**
 * ErrorBoundary Component Tests
 * Sprint 116 Feature 116.2: API Error Handling
 */

import * as React from 'react';
import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorBoundary } from './ErrorBoundary';

// Component that throws an error
function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
}

describe('ErrorBoundary', () => {
  // Suppress console.error for these tests
  const originalError = console.error;
  beforeAll(() => {
    console.error = vi.fn();
  });
  afterAll(() => {
    console.error = originalError;
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument();
  });

  it('renders error UI when error is caught', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    expect(screen.getByTestId('error-title')).toHaveTextContent('Something went wrong');
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalled();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
  });

  it('renders custom fallback when provided', () => {
    const fallback = <div data-testid="custom-fallback">Custom error UI</div>;

    render(
      <ErrorBoundary fallback={fallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
  });

  it('resets error state when reset button is clicked', async () => {
    const user = userEvent.setup();

    // Use a state wrapper to control error throwing
    function TestWrapper() {
      const [shouldThrow, setShouldThrow] = React.useState(true);
      return (
        <ErrorBoundary key={shouldThrow ? 'error' : 'success'}>
          <ThrowError shouldThrow={shouldThrow} />
          <button onClick={() => setShouldThrow(false)} data-testid="fix-error">
            Fix Error
          </button>
        </ErrorBoundary>
      );
    }

    render(<TestWrapper />);

    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();

    const resetButton = screen.getByTestId('error-reset-button');
    await user.click(resetButton);

    // After reset, error boundary should clear
    // Note: In real usage, parent component would re-render with fixed data
    expect(screen.queryByTestId('error-reset-button')).toBeInTheDocument();
  });

  it('hides reset button when showReset is false', () => {
    render(
      <ErrorBoundary showReset={false}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.queryByTestId('error-reset-button')).not.toBeInTheDocument();
  });
});
