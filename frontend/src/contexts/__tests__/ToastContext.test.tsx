/**
 * ToastContext Tests
 * Sprint 116 Feature 116.2: API Error Handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { type ReactNode } from 'react';
import { ToastProvider, useToast } from '../ToastContext';
import { ErrorSeverity } from '../../types/errors';

const wrapper = ({ children }: { children: ReactNode }) => {
  return <ToastProvider>{children}</ToastProvider>;
};

describe('ToastContext', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws error when used outside ToastProvider', () => {
    // Suppress console.error for this test
    const originalError = console.error;
    console.error = vi.fn();

    expect(() => renderHook(() => useToast())).toThrow(
      'useToast must be used within ToastProvider'
    );

    console.error = originalError;
  });

  it('initializes with empty toasts array', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    expect(result.current.toasts).toEqual([]);
  });

  it('shows toast notification', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.showToast('Test message', ErrorSeverity.INFO);
    });

    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Test message');
    expect(result.current.toasts[0].severity).toBe(ErrorSeverity.INFO);
  });

  it('auto-dismisses toast after duration', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.showToast('Test message', ErrorSeverity.INFO, 3000);
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('dismisses toast by ID', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    let toastId: string;
    act(() => {
      toastId = result.current.showToast('Test message');
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      result.current.dismissToast(toastId!);
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('dismisses all toasts', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.showToast('Message 1');
      result.current.showToast('Message 2');
      result.current.showToast('Message 3');
    });

    expect(result.current.toasts).toHaveLength(3);

    act(() => {
      result.current.dismissAll();
    });

    expect(result.current.toasts).toHaveLength(0);
  });

  it('limits number of simultaneous toasts', () => {
    const customWrapper = ({ children }: { children: ReactNode }) => (
      <ToastProvider maxToasts={2}>{children}</ToastProvider>
    );
    const { result } = renderHook(() => useToast(), {
      wrapper: customWrapper,
    });

    act(() => {
      result.current.showToast('Message 1');
      result.current.showToast('Message 2');
      result.current.showToast('Message 3');
    });

    expect(result.current.toasts).toHaveLength(2);
    expect(result.current.toasts[0].message).toBe('Message 2');
    expect(result.current.toasts[1].message).toBe('Message 3');
  });

  it('does not auto-dismiss when duration is 0', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    act(() => {
      result.current.showToast('Test message', ErrorSeverity.INFO, 0);
    });

    expect(result.current.toasts).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(result.current.toasts).toHaveLength(1);
  });

  it('generates unique IDs for each toast', () => {
    const { result } = renderHook(() => useToast(), { wrapper });

    let id1: string;
    let id2: string;

    act(() => {
      id1 = result.current.showToast('Message 1');
      id2 = result.current.showToast('Message 2');
    });

    expect(id1).not.toBe(id2);
  });
});
