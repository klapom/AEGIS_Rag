/**
 * MetricResultsDisplay Component
 * Sprint 45 Feature 45.12: Metric Configuration UI
 *
 * Displays training metric results with visual progress bars
 */

interface MetricResults {
  entity_precision?: number;
  entity_recall?: number;
  entity_f1?: number;
  relation_precision?: number;
  relation_recall?: number;
  relation_f1?: number;
}

interface MetricResultsDisplayProps {
  results: MetricResults;
}

export function MetricResultsDisplay({ results }: MetricResultsDisplayProps) {
  return (
    <div className="bg-white rounded-lg border p-4" data-testid="metric-results">
      <h3 className="font-medium mb-4">Training Results</h3>

      <div className="grid grid-cols-2 gap-6">
        {/* Entity Metrics */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Entity Extraction</h4>
          <div className="space-y-2">
            <MetricBar label="Precision" value={results.entity_precision} />
            <MetricBar label="Recall" value={results.entity_recall} />
            <MetricBar label="F1 Score" value={results.entity_f1} highlight />
          </div>
        </div>

        {/* Relation Metrics */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Relation Extraction</h4>
          <div className="space-y-2">
            <MetricBar label="Precision" value={results.relation_precision} />
            <MetricBar label="Recall" value={results.relation_recall} />
            <MetricBar label="F1 Score" value={results.relation_f1} highlight />
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricBar({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value?: number;
  highlight?: boolean;
}) {
  const percentage = value ? Math.round(value * 100) : 0;
  const color =
    percentage >= 80 ? 'bg-green-500' : percentage >= 60 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2" data-testid={`metric-bar-${label.toLowerCase()}`}>
      <span className={`text-sm w-20 ${highlight ? 'font-medium' : ''}`}>{label}</span>
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all`}
          style={{ width: `${percentage}%` }}
          data-testid={`metric-bar-fill-${label.toLowerCase()}`}
        />
      </div>
      <span className={`text-sm w-12 text-right ${highlight ? 'font-medium' : 'text-gray-600'}`}>
        {value !== undefined ? `${percentage}%` : '-'}
      </span>
    </div>
  );
}

export default MetricResultsDisplay;
