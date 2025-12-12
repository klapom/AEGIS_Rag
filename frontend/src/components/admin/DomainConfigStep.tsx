/**
 * DomainConfigStep Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Updated Sprint 45 Feature 45.12: Added Metric Configuration
 *
 * Step 1 of domain wizard: Configure domain name, description, model, and metrics
 */

import { useState } from 'react';
import { MetricConfigPanel } from './MetricConfigPanel';

interface MetricConfig {
  preset: 'balanced' | 'precision_focused' | 'recall_focused' | 'custom';
  entity_weight: number;
  relation_weight: number;
  entity_metric: 'f1' | 'precision' | 'recall';
  relation_metric: 'f1' | 'precision' | 'recall';
}

interface DomainConfig {
  name: string;
  description: string;
  llm_model: string;
  metricConfig?: MetricConfig;
}

interface DomainConfigStepProps {
  config: DomainConfig;
  models: string[] | null;
  onChange: (config: DomainConfig) => void;
  onNext: () => void;
  onCancel: () => void;
}

export function DomainConfigStep({
  config,
  models,
  onChange,
  onNext,
  onCancel,
}: DomainConfigStepProps) {
  const isValid = config.name.trim() !== '' && config.description.trim() !== '';

  // Initialize metric config with default balanced preset
  const [metricConfig, setMetricConfig] = useState<MetricConfig>(
    config.metricConfig || {
      preset: 'balanced',
      entity_weight: 0.5,
      relation_weight: 0.5,
      entity_metric: 'f1',
      relation_metric: 'f1',
    }
  );

  // Update parent config when metric config changes
  const handleMetricConfigChange = (newMetricConfig: MetricConfig) => {
    setMetricConfig(newMetricConfig);
    onChange({ ...config, metricConfig: newMetricConfig });
  };

  return (
    <div className="space-y-6" data-testid="domain-config-step">
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">Create New Domain</h2>
        <p className="text-gray-600">Step 1 of 3: Configure domain settings</p>
      </div>

      {/* Domain Name */}
      <div>
        <label htmlFor="domain-name" className="block text-sm font-medium text-gray-700 mb-2">
          Domain Name <span className="text-red-500">*</span>
        </label>
        <input
          id="domain-name"
          data-testid="domain-name-input"
          type="text"
          value={config.name}
          onChange={(e) => onChange({ ...config, name: e.target.value })}
          placeholder="e.g., finance, legal, medical"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-sm text-gray-500">
          Unique identifier for this domain (lowercase, no spaces)
        </p>
      </div>

      {/* Description */}
      <div>
        <label
          htmlFor="domain-description"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Description <span className="text-red-500">*</span>
        </label>
        <textarea
          id="domain-description"
          data-testid="domain-description-input"
          value={config.description}
          onChange={(e) => onChange({ ...config, description: e.target.value })}
          placeholder="Describe the domain and what types of queries it handles"
          rows={4}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* LLM Model */}
      <div>
        <label htmlFor="domain-model" className="block text-sm font-medium text-gray-700 mb-2">
          LLM Model (Optional)
        </label>
        <select
          id="domain-model"
          data-testid="domain-model-select"
          value={config.llm_model}
          onChange={(e) => onChange({ ...config, llm_model: e.target.value })}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">Use default model</option>
          {models?.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
        <p className="mt-1 text-sm text-gray-500">
          Select a specific model for this domain, or use the default
        </p>
      </div>

      {/* Metric Configuration */}
      <MetricConfigPanel value={metricConfig} onChange={handleMetricConfigChange} />

      {/* Actions */}
      <div className="flex justify-end space-x-4 pt-4 border-t">
        <button
          onClick={onCancel}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          data-testid="domain-config-cancel"
        >
          Cancel
        </button>
        <button
          onClick={onNext}
          disabled={!isValid}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          data-testid="domain-config-next"
        >
          Next: Upload Dataset
        </button>
      </div>
    </div>
  );
}
