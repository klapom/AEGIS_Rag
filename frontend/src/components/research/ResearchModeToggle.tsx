/**
 * ResearchModeToggle Component
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 *
 * A toggle switch for enabling/disabling Research Mode in the chat UI.
 * Features a microscope/search icon and persists state to localStorage.
 *
 * Features:
 * - Toggle switch with icon
 * - Label with tooltip
 * - Keyboard accessibility
 * - Visual feedback on state change
 */

import { Microscope } from 'lucide-react';
import type { ResearchModeToggleProps } from '../../types/research';

/**
 * ResearchModeToggle Component
 */
export function ResearchModeToggle({
  isEnabled,
  onToggle,
  className = '',
  disabled = false,
}: ResearchModeToggleProps) {
  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      data-testid="research-mode-toggle"
    >
      {/* Icon */}
      <Microscope
        className={`w-4 h-4 transition-colors ${
          isEnabled ? 'text-blue-600' : 'text-gray-400'
        }`}
        aria-hidden="true"
      />

      {/* Label */}
      <span
        className={`text-sm font-medium transition-colors ${
          isEnabled ? 'text-blue-700' : 'text-gray-600'
        }`}
      >
        Research Mode
      </span>

      {/* Toggle Switch */}
      <button
        type="button"
        role="switch"
        aria-checked={isEnabled}
        aria-label="Research Mode aktivieren/deaktivieren"
        disabled={disabled}
        onClick={onToggle}
        className={`
          relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
          transition-colors duration-200 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${isEnabled ? 'bg-blue-600' : 'bg-gray-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        data-testid="research-mode-switch"
      >
        {/* Toggle knob */}
        <span
          className={`
            pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0
            transition duration-200 ease-in-out
            ${isEnabled ? 'translate-x-4' : 'translate-x-0'}
          `}
          aria-hidden="true"
        />
      </button>

      {/* Tooltip / Description (hidden by default, shown on hover) */}
      <div className="relative group">
        <button
          type="button"
          className="text-gray-400 hover:text-gray-600 focus:outline-none"
          aria-label="Info zu Research Mode"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </button>

        {/* Tooltip content */}
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-xs
                     bg-gray-900 text-white rounded-lg shadow-lg
                     opacity-0 invisible group-hover:opacity-100 group-hover:visible
                     transition-all duration-200 whitespace-nowrap z-50"
          role="tooltip"
        >
          Aktiviert mehrstufige Recherche mit mehreren Such-Iterationen
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      </div>
    </div>
  );
}

/**
 * Compact version of the toggle for inline use
 */
export function ResearchModeToggleCompact({
  isEnabled,
  onToggle,
  className = '',
  disabled = false,
}: ResearchModeToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={`
        flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
        transition-all duration-200
        ${isEnabled
          ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        }
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        ${className}
      `}
      aria-pressed={isEnabled}
      aria-label={`Research Mode ${isEnabled ? 'deaktivieren' : 'aktivieren'}`}
      data-testid="research-mode-toggle-compact"
    >
      <Microscope className="w-3.5 h-3.5" aria-hidden="true" />
      <span>Research</span>
      {isEnabled && (
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" aria-hidden="true" />
      )}
    </button>
  );
}
