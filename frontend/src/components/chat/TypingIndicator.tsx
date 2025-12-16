/**
 * TypingIndicator Component
 * Sprint 35 Feature 35.6: Loading States & Animations
 * Sprint 47: Enhanced with elapsed time display and phase information
 *
 * Displays a ChatGPT-style typing indicator with three bouncing dots.
 * Used to show that the assistant is "thinking" or generating a response.
 *
 * Features:
 * - Bouncing dots animation
 * - Elapsed time display (shows how long thinking has been in progress)
 * - Optional phase/step information
 * - Avatar with message layout
 */

import { useState, useEffect } from 'react';
import { BotAvatar } from './BotAvatar';

interface TypingIndicatorProps {
  /**
   * Optional text to display alongside the dots.
   * Default: "AegisRAG denkt nach..."
   */
  text?: string;
  /**
   * Whether to show the full message layout with avatar.
   * If false, only shows the dots inline.
   */
  showAvatar?: boolean;
  /**
   * Start time for elapsed time calculation (timestamp in ms).
   * If provided, shows elapsed time counter.
   */
  startTime?: number;
  /**
   * Current phase/step being executed.
   * Examples: "Retrieval", "Graph Query", "Reranking", "LLM Generation"
   */
  phase?: string;
  /**
   * Current progress percentage (0-100).
   * If provided, shows a progress indicator.
   */
  progress?: number;
  /**
   * Additional details about what's being processed.
   */
  details?: string;
}

/**
 * Format elapsed time in seconds/minutes.
 * @param ms - Elapsed time in milliseconds
 * @returns Formatted string like "2.3s" or "1:23"
 */
function formatElapsedTime(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const decimal = Math.floor((ms % 1000) / 100);

  if (seconds < 60) {
    return `${seconds}.${decimal}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

/**
 * TypingIndicator provides a professional "thinking" animation with timing.
 * Features:
 * - Three bouncing dots with staggered animation
 * - Elapsed time counter that updates every 100ms
 * - Optional phase and progress display
 * - Optional avatar and text label
 * - Matches ChatMessage layout when showAvatar=true
 */
export function TypingIndicator({
  text = 'AegisRAG denkt nach...',
  showAvatar = true,
  startTime,
  phase,
  progress,
  details,
}: TypingIndicatorProps) {
  // Elapsed time state - updates every 100ms when startTime is provided
  const [elapsedTime, setElapsedTime] = useState(0);

  // Timer effect to update elapsed time
  useEffect(() => {
    if (!startTime) {
      setElapsedTime(0);
      return;
    }

    // Calculate initial elapsed time
    setElapsedTime(Date.now() - startTime);

    // Update every 100ms for smooth display
    const intervalId = setInterval(() => {
      setElapsedTime(Date.now() - startTime);
    }, 100);

    return () => clearInterval(intervalId);
  }, [startTime]);

  // Dots animation element
  const dotsElement = (
    <div className="flex items-center gap-1" data-testid="typing-indicator">
      <div
        className="w-2 h-2 bg-primary rounded-full animate-bounce"
        style={{ animationDelay: '0ms', animationDuration: '1s' }}
      />
      <div
        className="w-2 h-2 bg-primary rounded-full animate-bounce"
        style={{ animationDelay: '150ms', animationDuration: '1s' }}
      />
      <div
        className="w-2 h-2 bg-primary rounded-full animate-bounce"
        style={{ animationDelay: '300ms', animationDuration: '1s' }}
      />
    </div>
  );

  // Time and phase display
  const statusElement = (
    <div className="flex items-center gap-2">
      {/* Main text */}
      {text && <span className="text-sm text-gray-500">{text}</span>}

      {/* Elapsed time badge */}
      {startTime && (
        <span
          className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded"
          data-testid="elapsed-time"
        >
          {formatElapsedTime(elapsedTime)}
        </span>
      )}
    </div>
  );

  // Phase and progress display (when available)
  const phaseElement = (phase || progress !== undefined) && (
    <div className="mt-2 flex items-center gap-2">
      {/* Phase chip */}
      {phase && (
        <span
          className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full"
          data-testid="current-phase"
        >
          {phase}
        </span>
      )}

      {/* Progress bar */}
      {progress !== undefined && progress > 0 && (
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
          <span className="text-xs text-gray-500">{Math.round(progress)}%</span>
        </div>
      )}
    </div>
  );

  // Details line (additional context)
  const detailsElement = details && (
    <div className="mt-1 text-xs text-gray-400 truncate" data-testid="thinking-details">
      {details}
    </div>
  );

  // Inline version (no avatar, just dots and optional text)
  if (!showAvatar) {
    return (
      <div className="flex flex-col">
        <div className="flex items-center gap-2">
          {dotsElement}
          {statusElement}
        </div>
        {phaseElement}
        {detailsElement}
      </div>
    );
  }

  // Full message layout with avatar (matches ChatMessage structure)
  return (
    <div
      className="flex gap-4 py-6 border-b border-gray-100 last:border-b-0"
      data-testid="typing-indicator-message"
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <BotAvatar />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Name label */}
        <div className="text-sm font-semibold text-gray-700 mb-2">AegisRAG</div>

        {/* Typing animation with status */}
        <div className="flex items-center gap-3">
          {dotsElement}
          {statusElement}
        </div>

        {/* Phase and progress */}
        {phaseElement}

        {/* Additional details */}
        {detailsElement}
      </div>
    </div>
  );
}
