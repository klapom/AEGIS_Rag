/**
 * ApiErrorDisplay Component Tests
 * Sprint 116 Feature 116.2: API Error Handling
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiErrorDisplay } from './ApiErrorDisplay';
import { ApiError } from '../../types/errors';

describe('ApiErrorDisplay', () => {
  it('renders nothing when error is null', () => {
    render(<ApiErrorDisplay error={null} />);
    expect(screen.queryByTestId('api-error-inline')).not.toBeInTheDocument();
  });

  it('renders inline error for standard Error', () => {
    const error = new Error('Test error');
    render(<ApiErrorDisplay error={error} />);

    expect(screen.getByTestId('api-error-inline')).toBeInTheDocument();
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('renders inline error for ApiError', () => {
    const error = new ApiError('Custom message', 500, null, false);
    render(<ApiErrorDisplay error={error} />);

    expect(screen.getByTestId('api-error-inline')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument();
  });

  it('renders page variant when variant is page', () => {
    const error = new ApiError('Error', 404, null, false);
    render(<ApiErrorDisplay error={error} variant="page" />);

    expect(screen.getByTestId('api-error-page')).toBeInTheDocument();
    expect(screen.getByText('Error 404')).toBeInTheDocument();
  });

  it('shows retry button for retryable errors', () => {
    const error = new ApiError('Error', 503, null, true);
    const onRetry = vi.fn();

    render(<ApiErrorDisplay error={error} onRetry={onRetry} />);

    const retryButton = screen.getByTestId('error-retry-button');
    expect(retryButton).toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup();
    const error = new ApiError('Error', 503, null, true);
    const onRetry = vi.fn();

    render(<ApiErrorDisplay error={error} onRetry={onRetry} />);

    const retryButton = screen.getByTestId('error-retry-button');
    await user.click(retryButton);

    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('shows dismiss button when onDismiss is provided', () => {
    const error = new Error('Test error');
    const onDismiss = vi.fn();

    render(<ApiErrorDisplay error={error} onDismiss={onDismiss} />);

    const dismissButton = screen.getByTestId('error-dismiss-button');
    expect(dismissButton).toBeInTheDocument();
  });

  it('calls onDismiss when dismiss button is clicked', async () => {
    const user = userEvent.setup();
    const error = new Error('Test error');
    const onDismiss = vi.fn();

    render(<ApiErrorDisplay error={error} onDismiss={onDismiss} />);

    const dismissButton = screen.getByTestId('error-dismiss-button');
    await user.click(dismissButton);

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('displays custom message when provided', () => {
    const error = new ApiError('Error', 500, null, false);
    render(<ApiErrorDisplay error={error} message="Custom error message" />);

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
  });

  it('displays user-friendly message for 413 Payload Too Large', () => {
    const error = new ApiError('Error', 413, null, false);
    render(<ApiErrorDisplay error={error} />);

    expect(screen.getByText('File is too large. Maximum size is 50 MB.')).toBeInTheDocument();
  });

  it('displays user-friendly message for 504 Gateway Timeout', () => {
    const error = new ApiError('Error', 504, null, true);
    render(<ApiErrorDisplay error={error} />);

    expect(screen.getByText('Request timed out. The server is busy.')).toBeInTheDocument();
  });

  it('displays user-friendly message for 500 Internal Server Error', () => {
    const error = new ApiError('Error', 500, null, true);
    render(<ApiErrorDisplay error={error} />);

    expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument();
  });
});
