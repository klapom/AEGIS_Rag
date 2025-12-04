/**
 * TypingIndicator Component
 * Sprint 35 Feature 35.6: Loading States & Animations
 *
 * Displays a ChatGPT-style typing indicator with three bouncing dots.
 * Used to show that the assistant is "thinking" or generating a response.
 */

import { BotAvatar } from './BotAvatar';

interface TypingIndicatorProps {
  /**
   * Optional text to display alongside the dots.
   * Default: "AegisRAG is thinking..."
   */
  text?: string;
  /**
   * Whether to show the full message layout with avatar.
   * If false, only shows the dots inline.
   */
  showAvatar?: boolean;
}

/**
 * TypingIndicator provides a professional "thinking" animation.
 * Features:
 * - Three bouncing dots with staggered animation
 * - Optional avatar and text label
 * - Matches ChatMessage layout when showAvatar=true
 */
export function TypingIndicator({
  text = 'AegisRAG is thinking...',
  showAvatar = true,
}: TypingIndicatorProps) {
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

  // Inline version (no avatar, just dots)
  if (!showAvatar) {
    return dotsElement;
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

        {/* Typing animation with text */}
        <div className="flex items-center gap-3">
          {dotsElement}
          {text && <span className="text-sm text-gray-500">{text}</span>}
        </div>
      </div>
    </div>
  );
}
