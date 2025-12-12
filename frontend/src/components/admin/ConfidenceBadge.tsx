/**
 * ConfidenceBadge Component
 * Sprint 45 Feature 45.7: Upload Page Domain Suggestion
 *
 * Visual indicator for domain classification confidence
 */

interface ConfidenceBadgeProps {
  score: number;
}

export function ConfidenceBadge({ score }: ConfidenceBadgeProps) {
  // Determine color and label based on score
  const getColorAndLabel = (score: number) => {
    if (score > 0.8) {
      return {
        color: 'green',
        label: 'High',
        classes: 'bg-green-100 text-green-800',
      };
    } else if (score > 0.5) {
      return {
        color: 'yellow',
        label: 'Medium',
        classes: 'bg-yellow-100 text-yellow-800',
      };
    } else {
      return {
        color: 'red',
        label: 'Low',
        classes: 'bg-red-100 text-red-800',
      };
    }
  };

  const { classes, label } = getColorAndLabel(score);
  const percentage = (score * 100).toFixed(0);

  return (
    <span
      className={`px-2 py-1 rounded text-xs font-semibold ${classes}`}
      data-testid="confidence-badge"
      title={`Confidence: ${percentage}%`}
    >
      {label} ({percentage}%)
    </span>
  );
}
