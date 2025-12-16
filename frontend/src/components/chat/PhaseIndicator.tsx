/**
 * PhaseIndicator Component
 * Sprint 48 Feature 48.6: Real-Time Phase Display
 *
 * Displays the current processing phase and a list of completed/pending phases
 * during the RAG reasoning process. Shows progress bar and timing information.
 *
 * Features:
 * - Progress bar showing overall completion
 * - Current phase indicator with spinner
 * - List of phases with status icons and durations
 * - Error display for failed phases
 * - Accessibility support with ARIA labels
 */

import type { PhaseEvent, PhaseType } from '../../types/reasoning';
import { PHASE_NAMES, TOTAL_PHASES } from '../../types/reasoning';

/**
 * Props for the PhaseIndicator component
 */
export interface PhaseIndicatorProps {
  /** Currently active phase (null if none in progress) */
  currentPhase: PhaseType | null;
  /** List of all phase events received */
  phaseEvents: PhaseEvent[];
  /** Whether to show the detailed phase list */
  showDetails?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get status icon for a phase
 */
function getStatusIcon(status: PhaseEvent['status']): string {
  switch (status) {
    case 'completed':
      return '\u2713'; // checkmark
    case 'in_progress':
      return '\u25CF'; // filled circle (will be animated)
    case 'failed':
      return '\u2717'; // X mark
    case 'skipped':
      return '\u2014'; // em dash
    case 'pending':
    default:
      return '\u25CB'; // empty circle
  }
}

/**
 * Get CSS class for phase status
 */
function getStatusClass(status: PhaseEvent['status']): string {
  switch (status) {
    case 'completed':
      return 'text-green-600';
    case 'in_progress':
      return 'text-blue-600 animate-pulse';
    case 'failed':
      return 'text-red-600';
    case 'skipped':
      return 'text-gray-400';
    case 'pending':
    default:
      return 'text-gray-300';
  }
}

/**
 * Format duration in milliseconds to human-readable string
 */
function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * PhaseIndicator displays real-time progress through RAG processing phases.
 * Provides visual feedback during the "thinking" phase before answer streaming begins.
 */
export function PhaseIndicator({
  currentPhase,
  phaseEvents,
  showDetails = true,
  className = '',
}: PhaseIndicatorProps) {
  // Calculate progress based on completed phases
  const completedPhases = phaseEvents.filter(
    (e) => e.status === 'completed' || e.status === 'skipped'
  ).length;
  const progress = Math.round((completedPhases / TOTAL_PHASES) * 100);

  // Get current phase display name
  const currentPhaseName = currentPhase ? PHASE_NAMES[currentPhase] : null;

  return (
    <div
      className={`phase-indicator ${className}`}
      role="status"
      aria-label="Verarbeitungsfortschritt"
      aria-live="polite"
    >
      {/* Progress bar */}
      <div
        className="h-1 bg-gray-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${progress}% abgeschlossen`}
      >
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Current phase display */}
      {currentPhaseName && (
        <div className="flex items-center gap-2 mt-2" data-testid="current-phase-display">
          <div
            className="w-3 h-3 rounded-full bg-blue-500 animate-pulse"
            aria-hidden="true"
          />
          <span className="text-sm text-gray-700 font-medium">
            {currentPhaseName}
          </span>
        </div>
      )}

      {/* Progress summary */}
      <div className="mt-1 text-xs text-gray-500" data-testid="phase-progress-summary">
        {completedPhases} von {TOTAL_PHASES} Phasen abgeschlossen
      </div>

      {/* Detailed phase list */}
      {showDetails && phaseEvents.length > 0 && (
        <div
          className="mt-3 space-y-1"
          role="list"
          aria-label="Phasenliste"
          data-testid="phase-list"
        >
          {phaseEvents.map((event) => (
            <div
              key={event.phase_type}
              className={`flex items-center justify-between text-xs ${getStatusClass(event.status)}`}
              role="listitem"
              data-testid={`phase-item-${event.phase_type}`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-4 text-center ${event.status === 'in_progress' ? 'animate-spin' : ''}`}
                  aria-hidden="true"
                >
                  {getStatusIcon(event.status)}
                </span>
                <span className={event.status === 'completed' ? 'text-gray-700' : ''}>
                  {PHASE_NAMES[event.phase_type] || event.phase_type}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {event.duration_ms !== undefined && event.status === 'completed' && (
                  <span className="font-mono text-gray-500" data-testid={`phase-duration-${event.phase_type}`}>
                    {formatDuration(event.duration_ms)}
                  </span>
                )}
                {event.status === 'failed' && event.error && (
                  <span
                    className="text-red-500 truncate max-w-[150px]"
                    title={event.error}
                    data-testid={`phase-error-${event.phase_type}`}
                  >
                    {event.error}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PhaseIndicator;
