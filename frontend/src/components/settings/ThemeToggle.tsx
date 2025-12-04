/**
 * ThemeToggle Component
 * Sprint 35 Feature 35.7: Dark Mode Preparation
 *
 * Provides a toggle button for switching between light and dark themes.
 * Can be integrated into settings pages or headers.
 */

import { Moon, Sun } from 'lucide-react';
import { useDarkMode } from '../../hooks/useDarkMode';

/**
 * ThemeToggle component props
 */
export interface ThemeToggleProps {
  /** Optional CSS class name */
  className?: string;
  /** Show label text next to icon */
  showLabel?: boolean;
  /** Variant style */
  variant?: 'button' | 'switch';
}

/**
 * ThemeToggle Component
 *
 * Renders a button or switch to toggle between light and dark mode.
 *
 * @example
 * ```tsx
 * // Simple icon button
 * <ThemeToggle />
 *
 * // With label
 * <ThemeToggle showLabel />
 *
 * // Switch variant (for settings pages)
 * <ThemeToggle variant="switch" showLabel />
 * ```
 */
export function ThemeToggle({
  className = '',
  showLabel = false,
  variant = 'button',
}: ThemeToggleProps) {
  const { isDark, toggle } = useDarkMode();

  if (variant === 'switch') {
    return (
      <div
        className={`flex items-center justify-between gap-4 ${className}`}
        data-testid="theme-toggle-switch"
      >
        {showLabel && (
          <div className="flex items-center gap-2">
            {isDark ? (
              <Moon className="h-5 w-5 text-gray-400" />
            ) : (
              <Sun className="h-5 w-5 text-gray-600" />
            )}
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              {isDark ? 'Dark Mode' : 'Light Mode'}
            </span>
          </div>
        )}

        <button
          onClick={toggle}
          className={`
            relative inline-flex h-6 w-11 items-center rounded-full
            transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2
            ${isDark ? 'bg-primary' : 'bg-gray-200'}
            focus:ring-primary
          `}
          role="switch"
          aria-checked={isDark}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          data-testid="theme-toggle-button"
        >
          <span
            className={`
              inline-block h-4 w-4 transform rounded-full bg-white
              transition-transform
              ${isDark ? 'translate-x-6' : 'translate-x-1'}
            `}
          />
        </button>
      </div>
    );
  }

  // Button variant (default)
  return (
    <button
      onClick={toggle}
      className={`
        inline-flex items-center gap-2 rounded-lg px-3 py-2
        transition-colors hover:bg-gray-100 dark:hover:bg-gray-800
        focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2
        ${className}
      `}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      data-testid="theme-toggle-button"
    >
      {isDark ? (
        <>
          <Sun className="h-5 w-5" style={{ color: 'var(--text-secondary)' }} />
          {showLabel && (
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Light Mode
            </span>
          )}
        </>
      ) : (
        <>
          <Moon className="h-5 w-5" style={{ color: 'var(--text-secondary)' }} />
          {showLabel && (
            <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              Dark Mode
            </span>
          )}
        </>
      )}
    </button>
  );
}

/**
 * Standalone theme toggle for use in headers or toolbars
 */
export function ThemeToggleIcon({ className = '' }: { className?: string }) {
  const { isDark, toggle } = useDarkMode();

  return (
    <button
      onClick={toggle}
      className={`
        rounded-lg p-2 transition-colors
        hover:bg-gray-100 dark:hover:bg-gray-800
        focus:outline-none focus:ring-2 focus:ring-primary
        ${className}
      `}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      data-testid="theme-toggle-icon"
    >
      {isDark ? (
        <Sun className="h-5 w-5" style={{ color: 'var(--text-secondary)' }} />
      ) : (
        <Moon className="h-5 w-5" style={{ color: 'var(--text-secondary)' }} />
      )}
    </button>
  );
}
