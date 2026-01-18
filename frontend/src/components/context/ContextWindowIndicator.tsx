/**
 * ContextWindowIndicator Component
 * Sprint 111 Feature 111.1: Long Context UI
 *
 * Visual gauge component showing context window usage (0-100%)
 * with color-coded status indicators:
 * - Green: 0-60% (healthy)
 * - Yellow: 60-80% (warning)
 * - Red: 80-100% (near capacity)
 */

import { useMemo } from 'react';
import { CircleAlert, CheckCircle2, AlertTriangle } from 'lucide-react';

interface ContextWindowIndicatorProps {
  currentTokens: number;
  maxTokens: number;
  className?: string;
}

export function ContextWindowIndicator({
  currentTokens,
  maxTokens,
  className = '',
}: ContextWindowIndicatorProps) {
  const percentage = useMemo(() => {
    if (maxTokens <= 0) return 0;
    return Math.min(100, Math.round((currentTokens / maxTokens) * 100));
  }, [currentTokens, maxTokens]);

  const status = useMemo(() => {
    if (percentage < 60) return 'healthy';
    if (percentage < 80) return 'warning';
    return 'critical';
  }, [percentage]);

  const colors = {
    healthy: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-300',
      progress: 'bg-green-500',
      icon: CheckCircle2,
    },
    warning: {
      bg: 'bg-yellow-100 dark:bg-yellow-900/30',
      text: 'text-yellow-700 dark:text-yellow-300',
      progress: 'bg-yellow-500',
      icon: AlertTriangle,
    },
    critical: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-700 dark:text-red-300',
      progress: 'bg-red-500',
      icon: CircleAlert,
    },
  };

  const currentColors = colors[status];
  const Icon = currentColors.icon;

  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
    return tokens.toString();
  };

  return (
    <div
      className={`rounded-lg p-4 ${currentColors.bg} ${className}`}
      data-testid="context-window-indicator"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 ${currentColors.text}`} />
          <span className={`font-semibold ${currentColors.text}`}>
            Context Window Usage
          </span>
        </div>
        <span className={`text-lg font-bold ${currentColors.text}`} data-testid="context-percentage">
          {percentage}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full ${currentColors.progress} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
          data-testid="context-progress-bar"
        />
      </div>

      {/* Token counts */}
      <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
        <span data-testid="context-current-tokens">
          {formatTokens(currentTokens)} tokens used
        </span>
        <span data-testid="context-max-tokens">
          {formatTokens(maxTokens)} max
        </span>
      </div>
    </div>
  );
}
