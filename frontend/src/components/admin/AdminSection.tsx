/**
 * AdminSection Component
 * Sprint 46 Feature 46.8: Admin Area Consolidation
 *
 * Reusable collapsible section for admin dashboard with consistent styling.
 * Follows atomic design principles as a molecule component.
 */

import { useState, useCallback, type ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export interface AdminSectionProps {
  /** Section title displayed in the header */
  title: string;
  /** Icon component displayed before the title */
  icon: ReactNode;
  /** Optional action button/component displayed on the right side of header */
  action?: ReactNode;
  /** Whether the section is expanded by default */
  defaultExpanded?: boolean;
  /** Section content */
  children: ReactNode;
  /** Optional test ID for testing */
  testId?: string;
  /** Optional loading state */
  isLoading?: boolean;
  /** Optional error message */
  error?: string | null;
}

/**
 * Collapsible admin section with header, icon, and optional action button.
 * Used to organize the consolidated admin dashboard into logical sections.
 */
export function AdminSection({
  title,
  icon,
  action,
  defaultExpanded = true,
  children,
  testId,
  isLoading = false,
  error = null,
}: AdminSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleToggle();
      }
    },
    [handleToggle]
  );

  return (
    <section
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden"
      data-testid={testId}
      aria-labelledby={`${testId}-title`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-600 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-controls={`${testId}-content`}
      >
        <div className="flex items-center gap-3">
          {/* Expand/Collapse Icon */}
          <span className="text-gray-500 dark:text-gray-400">
            {expanded ? (
              <ChevronDown className="w-5 h-5" aria-hidden="true" />
            ) : (
              <ChevronRight className="w-5 h-5" aria-hidden="true" />
            )}
          </span>

          {/* Section Icon */}
          <span className="text-gray-600 dark:text-gray-300">{icon}</span>

          {/* Title */}
          <h2
            id={`${testId}-title`}
            className="text-lg font-semibold text-gray-900 dark:text-gray-100"
          >
            {title}
          </h2>
        </div>

        {/* Action Button */}
        {action && (
          <div
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => e.stopPropagation()}
            role="presentation"
          >
            {action}
          </div>
        )}
      </div>

      {/* Content */}
      {expanded && (
        <div
          id={`${testId}-content`}
          className="p-4"
          role="region"
          aria-labelledby={`${testId}-title`}
        >
          {isLoading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState error={error} />
          ) : (
            children
          )}
        </div>
      )}
    </section>
  );
}

/**
 * Loading state placeholder
 */
function LoadingState() {
  return (
    <div className="flex items-center justify-center py-8" data-testid="admin-section-loading">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <span className="text-gray-600 dark:text-gray-400">Loading...</span>
      </div>
    </div>
  );
}

/**
 * Error state display
 */
function ErrorState({ error }: { error: string }) {
  return (
    <div
      className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
      data-testid="admin-section-error"
      role="alert"
    >
      <svg
        className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
    </div>
  );
}

export default AdminSection;
