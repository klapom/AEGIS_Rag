/**
 * MetricConfigPanel Component
 * Sprint 45 Feature 45.12: Metric Configuration UI
 *
 * Provides UI for configuring training metric optimization strategy
 */

interface MetricConfig {
  preset: 'balanced' | 'precision_focused' | 'recall_focused' | 'custom';
  entity_weight: number; // 0-1
  relation_weight: number; // 0-1
  entity_metric: 'f1' | 'precision' | 'recall';
  relation_metric: 'f1' | 'precision' | 'recall';
}

interface MetricConfigPanelProps {
  value: MetricConfig;
  onChange: (config: MetricConfig) => void;
}

const PRESETS: Record<string, Omit<MetricConfig, 'preset'>> = {
  balanced: {
    entity_weight: 0.5,
    relation_weight: 0.5,
    entity_metric: 'f1',
    relation_metric: 'f1',
  },
  precision_focused: {
    entity_weight: 0.6,
    relation_weight: 0.4,
    entity_metric: 'precision',
    relation_metric: 'precision',
  },
  recall_focused: {
    entity_weight: 0.4,
    relation_weight: 0.6,
    entity_metric: 'recall',
    relation_metric: 'recall',
  },
};

export function MetricConfigPanel({ value, onChange }: MetricConfigPanelProps) {
  const handlePresetChange = (preset: MetricConfig['preset']) => {
    if (preset === 'custom') {
      onChange({ ...value, preset });
    } else {
      onChange({ ...PRESETS[preset], preset });
    }
  };

  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-4" data-testid="metric-config-panel">
      <h3 className="font-medium">Training Metric Configuration</h3>

      {/* Preset Selection */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">Optimization Strategy</label>
        <div className="grid grid-cols-4 gap-2">
          {['balanced', 'precision_focused', 'recall_focused', 'custom'].map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => handlePresetChange(preset as MetricConfig['preset'])}
              className={`px-3 py-2 text-sm rounded border ${
                value.preset === preset
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white hover:bg-gray-50 border-gray-300'
              }`}
              data-testid={`preset-${preset}`}
            >
              {preset.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* Custom Configuration */}
      {value.preset === 'custom' && (
        <div className="space-y-4 pt-4 border-t">
          {/* Entity/Relation Weight Slider */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Entity Weight: {Math.round(value.entity_weight * 100)}%</span>
              <span>Relation Weight: {Math.round(value.relation_weight * 100)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={value.entity_weight * 100}
              onChange={(e) => {
                const entityWeight = parseInt(e.target.value) / 100;
                onChange({
                  ...value,
                  entity_weight: entityWeight,
                  relation_weight: 1 - entityWeight,
                });
              }}
              className="w-full"
              data-testid="weight-slider"
            />
          </div>

          {/* Entity Metric Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Entity Optimization Metric
            </label>
            <select
              value={value.entity_metric}
              onChange={(e) =>
                onChange({ ...value, entity_metric: e.target.value as 'f1' | 'precision' | 'recall' })
              }
              className="w-full border rounded px-3 py-2"
              data-testid="entity-metric-select"
            >
              <option value="f1">F1 Score (Balanced)</option>
              <option value="precision">Precision (Fewer false positives)</option>
              <option value="recall">Recall (Fewer missed entities)</option>
            </select>
          </div>

          {/* Relation Metric Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Relation Optimization Metric
            </label>
            <select
              value={value.relation_metric}
              onChange={(e) =>
                onChange({
                  ...value,
                  relation_metric: e.target.value as 'f1' | 'precision' | 'recall',
                })
              }
              className="w-full border rounded px-3 py-2"
              data-testid="relation-metric-select"
            >
              <option value="f1">F1 Score (Balanced)</option>
              <option value="precision">Precision (Accurate relations)</option>
              <option value="recall">Recall (Complete extraction)</option>
            </select>
          </div>
        </div>
      )}

      {/* Explanation */}
      <div className="text-sm text-gray-600 bg-blue-50 p-3 rounded">
        <strong>Current Strategy:</strong> {getStrategyDescription(value)}
      </div>
    </div>
  );
}

function getStrategyDescription(config: MetricConfig): string {
  switch (config.preset) {
    case 'balanced':
      return 'Balanced optimization for both entities and relations using F1 score.';
    case 'precision_focused':
      return 'Prioritizes accuracy - extracted items are more likely to be correct, but may miss some.';
    case 'recall_focused':
      return 'Prioritizes completeness - less likely to miss entities/relations, may have more false positives.';
    case 'custom':
      return `Custom: ${Math.round(config.entity_weight * 100)}% entity (${config.entity_metric}), ${Math.round(config.relation_weight * 100)}% relation (${config.relation_metric})`;
  }
}

export default MetricConfigPanel;
