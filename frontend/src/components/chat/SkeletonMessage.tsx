/**
 * SkeletonMessage Component
 * Sprint 35 Feature 35.6: Loading States & Animations
 *
 * Displays a placeholder loading state while a chat message is being fetched.
 * Matches the ChatMessage layout with animated skeleton elements.
 */

interface SkeletonMessageProps {
  /**
   * Whether this skeleton represents a user or assistant message.
   * Used to show the correct avatar placeholder.
   */
  role?: 'user' | 'assistant';
}

/**
 * SkeletonMessage provides a professional loading placeholder for chat messages.
 * Features:
 * - Animated pulse effect for avatar and text lines
 * - Matches ChatMessage layout structure
 * - Configurable role (user/assistant)
 */
export function SkeletonMessage({ role = 'assistant' }: SkeletonMessageProps) {
  const isUser = role === 'user';

  return (
    <div
      className="flex gap-4 py-6 border-b border-gray-100 last:border-b-0 animate-pulse"
      data-testid="skeleton-message"
      data-role={role}
    >
      {/* Avatar Skeleton */}
      <div className="flex-shrink-0">
        <div
          className={`
            w-10 h-10 rounded-full
            ${
              isUser
                ? 'bg-blue-200'
                : 'bg-gradient-to-br from-primary/30 to-teal-300/30'
            }
          `}
        />
      </div>

      {/* Content Skeleton */}
      <div className="flex-1 min-w-0 space-y-3">
        {/* Name label skeleton */}
        <div className="h-4 w-20 bg-gray-200 rounded" />

        {/* Message content skeleton - 3 lines with varying widths */}
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-11/12" />
          <div className="h-4 bg-gray-200 rounded w-3/4" />
        </div>
      </div>
    </div>
  );
}
