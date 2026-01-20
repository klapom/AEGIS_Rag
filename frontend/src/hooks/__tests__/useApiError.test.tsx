/**
 * useApiError Hook Tests
 * Sprint 116 Feature 116.2: API Error Handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { type ReactNode } from 'react';
import { useApiError } from '../useApiError';
import { ToastProvider } from '../../contexts/ToastContext';
import { ApiError } from '../../types/errors';

// Wrapper component for hooks that need ToastProvider
const wrapper = ({ children }: { children: ReactNode }) => {
  return <ToastProvider>{children}</ToastProvider>;
};

describe('useApiError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with no error', () => {
    const { result } = renderHook(() => useApiError(), { wrapper });

    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isRetrying).toBe(false);
    expect(result.current.retryCount).toBe(0);
  });

  it('executes successful API call', async () => {
    const { result } = renderHook(() => useApiError(), { wrapper });
    const mockApiCall = vi.fn().mockResolvedValue({ data: 'success' });

    const response = await result.current.execute(mockApiCall);

    expect(response).toEqual({ data: 'success' });
    expect(result.current.error).toBeNull();
    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });

  it('handles API error and sets error state', async () => {
    const { result } = renderHook(() => useApiError({ showToast: false }), { wrapper });
    const error = new ApiError('Error', 500, null, false);
    const mockApiCall = vi.fn().mockRejectedValue(error);

    const response = await result.current.execute(mockApiCall);

    expect(response).toBeNull();
    expect(result.current.error).toBe(error);
  });

  it('retries retryable errors', async () => {
    const { result } = renderHook(
      () =>
        useApiError({
          showToast: false,
          retryConfig: { maxRetries: 2, baseDelay: 10, maxDelay: 100, backoffMultiplier: 2 },
        }),
      { wrapper }
    );

    const error = new ApiError('Error', 503, null, true);
    const mockApiCall = vi.fn().mockRejectedValue(error);

    const response = await result.current.execute(mockApiCall);

    await waitFor(() => {
      expect(response).toBeNull();
      expect(mockApiCall).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
    });
  });

  it('does not retry non-retryable errors', async () => {
    const { result } = renderHook(
      () =>
        useApiError({
          showToast: false,
          retryConfig: { maxRetries: 2, baseDelay: 10, maxDelay: 100, backoffMultiplier: 2 },
        }),
      { wrapper }
    );

    const error = new ApiError('Error', 400, null, false);
    const mockApiCall = vi.fn().mockRejectedValue(error);

    const response = await result.current.execute(mockApiCall);

    expect(response).toBeNull();
    expect(mockApiCall).toHaveBeenCalledTimes(1); // No retries
  });

  it('succeeds on retry after initial failure', async () => {
    const { result } = renderHook(
      () =>
        useApiError({
          showToast: false,
          retryConfig: { maxRetries: 2, baseDelay: 10, maxDelay: 100, backoffMultiplier: 2 },
        }),
      { wrapper }
    );

    const error = new ApiError('Error', 503, null, true);
    const mockApiCall = vi
      .fn()
      .mockRejectedValueOnce(error)
      .mockResolvedValue({ data: 'success' });

    const response = await result.current.execute(mockApiCall);

    await waitFor(() => {
      expect(response).toEqual({ data: 'success' });
      expect(mockApiCall).toHaveBeenCalledTimes(2); // 1 failure + 1 success
    });
  });

  it('clears error state', async () => {
    const { result } = renderHook(() => useApiError({ showToast: false }), { wrapper });
    const error = new ApiError('Error', 500, null, false);
    const mockApiCall = vi.fn().mockRejectedValue(error);

    await result.current.execute(mockApiCall);
    expect(result.current.error).toBe(error);

    result.current.clearError();
    expect(result.current.error).toBeNull();
  });

  it('manually retries last failed call', async () => {
    const { result } = renderHook(() => useApiError({ showToast: false }), { wrapper });
    const mockApiCall = vi
      .fn()
      .mockRejectedValueOnce(new ApiError('Error', 500, null, true))
      .mockResolvedValue({ data: 'success' });

    // First call fails
    await result.current.execute(mockApiCall);
    expect(result.current.error).toBeTruthy();

    // Manual retry succeeds
    await result.current.retry();

    await waitFor(() => {
      expect(result.current.error).toBeNull();
    });
  });

  it('calls onError callback when error occurs', async () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useApiError({ showToast: false, onError }), { wrapper });
    const error = new ApiError('Error', 500, null, false);
    const mockApiCall = vi.fn().mockRejectedValue(error);

    await result.current.execute(mockApiCall);

    expect(onError).toHaveBeenCalledWith(error);
  });

  it('sets loading state during API call', async () => {
    const { result } = renderHook(() => useApiError(), { wrapper });
    const mockApiCall = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: 'success' }), 100))
    );

    const promise = result.current.execute(mockApiCall);

    expect(result.current.isLoading).toBe(true);

    await promise;

    expect(result.current.isLoading).toBe(false);
  });
});
