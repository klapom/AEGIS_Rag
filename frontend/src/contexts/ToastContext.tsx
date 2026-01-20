/**
 * Toast Context and Provider
 * Sprint 116 Feature 116.2: API Error Handling
 *
 * Global toast notification system for error messages and other notifications
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { ToastNotification, ErrorSeverity } from '../types/errors';

interface ToastContextValue {
  /** Show a toast notification */
  showToast: (message: string, severity?: ErrorSeverity, duration?: number) => string;
  /** Dismiss a toast by ID */
  dismissToast: (id: string) => void;
  /** Dismiss all toasts */
  dismissAll: () => void;
  /** Active toasts */
  toasts: ToastNotification[];
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

interface ToastProviderProps {
  children: ReactNode;
  /** Maximum number of simultaneous toasts */
  maxToasts?: number;
}

/**
 * Toast Provider Component
 *
 * Wrap your app with this provider to enable toast notifications
 */
export function ToastProvider({ children, maxToasts = 3 }: ToastProviderProps) {
  const [toasts, setToasts] = useState<ToastNotification[]>([]);

  const showToast = useCallback(
    (message: string, severity: ErrorSeverity = 'info' as ErrorSeverity, duration: number = 5000): string => {
      const id = `toast-${Date.now()}-${Math.random()}`;
      const toast: ToastNotification = {
        id,
        message,
        severity,
        duration,
      };

      setToasts((prev) => {
        // Remove oldest toast if at max capacity
        const newToasts = prev.length >= maxToasts ? prev.slice(1) : prev;
        return [...newToasts, toast];
      });

      // Auto-dismiss after duration
      if (duration > 0) {
        setTimeout(() => {
          dismissToast(id);
        }, duration);
      }

      return id;
    },
    [maxToasts]
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast, dismissToast, dismissAll, toasts }}>
      {children}
    </ToastContext.Provider>
  );
}

/**
 * Hook to access toast context
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}
