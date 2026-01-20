/**
 * DomainClassificationBadge Component
 * Sprint 117 Feature 117.10: Upload Dialog Classification Display
 *
 * Shows domain name with confidence percentage and color coding.
 */

import { ClassificationPathIcon } from './ClassificationPathIcon';

interface DomainClassificationBadgeProps {
  domainName: string;
  confidence: number;
  classificationPath: 'fast' | 'verified' | 'fallback';
  className?: string;
}

/**
 * Badge displaying domain classification with confidence.
 *
 * Color coding:
 * - Green: confidence >= 0.85 (high)
 * - Yellow: 0.60 <= confidence < 0.85 (medium)
 * - Red: confidence < 0.60 (low)
 *
 * @param domainName - Human-readable domain name
 * @param confidence - Classification confidence (0.0-1.0)
 * @param classificationPath - Path used for classification
 * @param className - Additional CSS classes
 */
export function DomainClassificationBadge({
  domainName,
  confidence,
  classificationPath,
  className = '',
}: DomainClassificationBadgeProps) {
  // Determine color coding based on confidence
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.85) {
      return {
        bg: 'bg-green-50',
        border: 'border-green-200',
        text: 'text-green-800',
        badge: 'bg-green-100 text-green-700',
      };
    } else if (conf >= 0.6) {
      return {
        bg: 'bg-yellow-50',
        border: 'border-yellow-200',
        text: 'text-yellow-800',
        badge: 'bg-yellow-100 text-yellow-700',
      };
    } else {
      return {
        bg: 'bg-red-50',
        border: 'border-red-200',
        text: 'text-red-800',
        badge: 'bg-red-100 text-red-700',
      };
    }
  };

  const colors = getConfidenceColor(confidence);
  const confidencePercent = (confidence * 100).toFixed(1);

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border ${colors.bg} ${colors.border} ${className}`}
      data-testid="domain-classification-badge"
    >
      <span className={`text-sm font-semibold ${colors.text}`}>{domainName}</span>
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.badge}`}>
        {confidencePercent}%
      </span>
      <ClassificationPathIcon path={classificationPath} />
    </div>
  );
}
