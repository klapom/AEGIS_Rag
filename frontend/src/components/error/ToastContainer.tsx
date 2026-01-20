/**
 * Toast Container Component
 * Sprint 116 Feature 116.2: API Error Handling
 *
 * Renders active toast notifications at the top-right of the screen
 */

import { useEffect } from 'react';
import { X, AlertTriangle, CheckCircle, Info, AlertCircle } from 'lucide-react';
import { useToast } from '../../contexts/ToastContext';
import { ErrorSeverity } from '../../types/errors';

/**
 * Toast Container Component
 *
 * Place this component at the root of your app to display toasts
 */
export function ToastContainer() {
  const { toasts, dismissToast } = useToast();

  return (
    <div
      className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full pointer-events-none"
      data-testid="toast-container"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          id={toast.id}
          message={toast.message}
          severity={toast.severity}
          onDismiss={() => dismissToast(toast.id)}
        />
      ))}
    </div>
  );
}

interface ToastProps {
  id: string;
  message: string;
  severity: ErrorSeverity;
  onDismiss: () => void;
}

function Toast({ id, message, severity, onDismiss }: ToastProps) {
  // Auto-dismiss animation
  useEffect(() => {
    const timer = setTimeout(() => {
      const element = document.getElementById(id);
      element?.classList.add('toast-exit');
    }, 4700); // Start exit animation 300ms before actual dismiss

    return () => clearTimeout(timer);
  }, [id]);

  // Color scheme and icon based on severity
  const config = {
    [ErrorSeverity.CRITICAL]: {
      bg: 'bg-red-600',
      icon: AlertCircle,
      iconClass: 'text-white',
    },
    [ErrorSeverity.ERROR]: {
      bg: 'bg-red-500',
      icon: AlertTriangle,
      iconClass: 'text-white',
    },
    [ErrorSeverity.WARNING]: {
      bg: 'bg-orange-500',
      icon: AlertTriangle,
      iconClass: 'text-white',
    },
    [ErrorSeverity.INFO]: {
      bg: 'bg-blue-500',
      icon: Info,
      iconClass: 'text-white',
    },
  };

  const { bg, icon: Icon, iconClass } = config[severity] || config[ErrorSeverity.INFO];

  return (
    <div
      id={id}
      className={`${bg} text-white rounded-lg shadow-lg p-4 toast-enter pointer-events-auto`}
      data-testid="toast"
      role="alert"
    >
      <div className="flex items-start space-x-3">
        {/* Icon */}
        <Icon className={`w-5 h-5 ${iconClass} flex-shrink-0 mt-0.5`} />

        {/* Message */}
        <p className="flex-1 text-sm font-medium leading-relaxed">{message}</p>

        {/* Dismiss Button */}
        <button
          onClick={onDismiss}
          className="flex-shrink-0 p-1 rounded hover:bg-white/20 transition-colors"
          aria-label="Dismiss notification"
          data-testid="toast-dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="mt-2 h-1 bg-white/30 rounded-full overflow-hidden">
        <div className="h-full bg-white/60 toast-progress" />
      </div>
    </div>
  );
}

// Add these styles to your global CSS
const styles = `
@keyframes toast-slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes toast-slide-out {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

@keyframes toast-progress {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

.toast-enter {
  animation: toast-slide-in 0.3s ease-out;
}

.toast-exit {
  animation: toast-slide-out 0.3s ease-in;
}

.toast-progress {
  animation: toast-progress 5s linear;
}
`;

// Export styles for injection
export const TOAST_STYLES = styles;
