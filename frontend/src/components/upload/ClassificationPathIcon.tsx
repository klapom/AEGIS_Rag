/**
 * ClassificationPathIcon Component
 * Sprint 117 Feature 117.10: Upload Dialog Classification Display
 *
 * Shows an icon indicating which classification path was used.
 */

import { Zap, CheckCircle, Search } from 'lucide-react';

interface ClassificationPathIconProps {
  path: 'fast' | 'verified' | 'fallback';
  className?: string;
}

/**
 * Icon component for classification path display.
 *
 * @param path - Classification path used (fast, verified, fallback)
 * @param className - Additional CSS classes
 */
export function ClassificationPathIcon({ path, className = '' }: ClassificationPathIconProps) {
  const iconMap = {
    fast: {
      Icon: Zap,
      label: 'Fast Classification',
      color: 'text-blue-600',
      tooltip: 'Fast path classification using C-LARA SetFit model',
    },
    verified: {
      Icon: CheckCircle,
      label: 'Verified Classification',
      color: 'text-green-600',
      tooltip: 'Verified classification with high confidence',
    },
    fallback: {
      Icon: Search,
      label: 'Full Classification',
      color: 'text-amber-600',
      tooltip: 'Full classification pipeline with entity matching',
    },
  };

  const { Icon, label, color, tooltip } = iconMap[path];

  return (
    <div className={`inline-flex items-center gap-1 ${className}`} title={tooltip}>
      <Icon className={`w-4 h-4 ${color}`} aria-label={label} />
      <span className={`text-xs font-medium ${color}`}>{label}</span>
    </div>
  );
}
