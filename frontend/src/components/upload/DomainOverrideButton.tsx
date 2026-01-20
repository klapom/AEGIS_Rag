/**
 * DomainOverrideButton Component
 * Sprint 117 Feature 117.11: Manual Domain Override Button
 *
 * Button to trigger manual domain override modal.
 */

import { Edit2 } from 'lucide-react';

interface DomainOverrideButtonProps {
  onClick: () => void;
  showAlways?: boolean; // Show button even for high confidence
  confidence?: number;
  className?: string;
}

/**
 * Button component for triggering domain override modal.
 *
 * Shows:
 * - Edit icon
 * - "Override" or "Edit Domain" text
 * - Appears when confidence < 0.60 OR showAlways=true
 *
 * @param onClick - Handler for button click (opens modal)
 * @param showAlways - Whether to always show button (default: false)
 * @param confidence - Classification confidence (0.0-1.0)
 * @param className - Additional CSS classes
 */
export function DomainOverrideButton({
  onClick,
  showAlways = false,
  confidence,
  className = '',
}: DomainOverrideButtonProps) {
  // Only show if confidence < 0.60 OR showAlways=true
  const shouldShow = showAlways || (confidence !== undefined && confidence < 0.6);

  if (!shouldShow) {
    return null;
  }

  const isLowConfidence = confidence !== undefined && confidence < 0.6;

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
        isLowConfidence
          ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border border-yellow-300'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
      } ${className}`}
      data-testid="domain-override-button"
    >
      <Edit2 className="w-4 h-4" />
      {isLowConfidence ? 'Override' : 'Edit Domain'}
    </button>
  );
}
