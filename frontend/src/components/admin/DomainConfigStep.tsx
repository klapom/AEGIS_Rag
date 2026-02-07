/**
 * DomainConfigStep Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 * Updated Sprint 45 Feature 45.12: Added Metric Configuration
 *
 * Step 1 of domain wizard: Configure domain name, description, model, and metrics
 */

import { useState, useCallback } from 'react';
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
  entity_sub_type_mapping?: Record<string, string>;
  relation_hints?: string[];
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
          onChange={(e) => {
            // Sanitize: lowercase, replace spaces/hyphens with underscore, remove invalid chars
            const sanitized = e.target.value
              .toLowerCase()
              .replace(/[\s-]+/g, '_')
              .replace(/[^a-z0-9_]/g, '');
            onChange({ ...config, name: sanitized });
          }}
          placeholder="e.g., finance, legal, medical"
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="mt-1 text-sm text-gray-500">
          Lowercase letters, numbers, and underscores only (e.g., omnitracker_docs)
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

      {/* Entity Sub-Type Mapping (Sprint 126) */}
      <EntitySubTypeMappingEditor
        mapping={config.entity_sub_type_mapping || {}}
        onChange={(mapping) => onChange({ ...config, entity_sub_type_mapping: mapping })}
      />

      {/* Relation Hints (Sprint 126) */}
      <div>
        <label
          htmlFor="relation-hints"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          Relation Hints (Optional)
        </label>
        <textarea
          id="relation-hints"
          data-testid="relation-hints-input"
          value={(config.relation_hints || []).join('\n')}
          onChange={(e) => {
            const lines = e.target.value.split('\n').filter((l) => l.trim() !== '');
            onChange({ ...config, relation_hints: lines.length > 0 ? lines : undefined });
          }}
          placeholder={"TREATS\nDIAGNOSES\nINHIBITS\n(one relation verb per line)"}
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
        />
        <p className="mt-1 text-sm text-gray-500">
          Domain-specific relation verbs, one per line (e.g., TREATS, DIAGNOSES)
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

/**
 * Key-value editor for entity sub-type → universal type mapping.
 * Each row: sub_type input → universal_type dropdown.
 */
const UNIVERSAL_ENTITY_TYPES = [
  'PERSON', 'ORGANIZATION', 'LOCATION', 'EVENT', 'CONCEPT',
  'TECHNOLOGY', 'DOCUMENT', 'METRIC', 'TEMPORAL', 'MATERIAL',
  'PROCESS', 'REGULATION', 'PRODUCT', 'SERVICE', 'INFRASTRUCTURE',
];

function EntitySubTypeMappingEditor({
  mapping,
  onChange,
}: {
  mapping: Record<string, string>;
  onChange: (mapping: Record<string, string>) => void;
}) {
  const entries = Object.entries(mapping);

  const handleAdd = useCallback(() => {
    onChange({ ...mapping, '': 'CONCEPT' });
  }, [mapping, onChange]);

  const handleRemove = useCallback(
    (key: string) => {
      const next = { ...mapping };
      delete next[key];
      onChange(next);
    },
    [mapping, onChange]
  );

  const handleKeyChange = useCallback(
    (oldKey: string, newKey: string) => {
      const sanitized = newKey.toUpperCase().replace(/[^A-Z0-9_]/g, '');
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(mapping)) {
        next[k === oldKey ? sanitized : k] = v;
      }
      onChange(next);
    },
    [mapping, onChange]
  );

  const handleValueChange = useCallback(
    (key: string, value: string) => {
      onChange({ ...mapping, [key]: value });
    },
    [mapping, onChange]
  );

  return (
    <div data-testid="entity-sub-type-mapping-editor">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Entity Sub-Type Mapping (Optional)
      </label>
      <p className="text-sm text-gray-500 mb-3">
        Map domain-specific entity types to universal types (e.g., PROTEIN → MATERIAL)
      </p>

      {entries.length > 0 && (
        <div className="space-y-2 mb-3">
          {entries.map(([key, value], idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                value={key}
                onChange={(e) => handleKeyChange(key, e.target.value)}
                placeholder="SUB_TYPE"
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid={`mapping-key-${idx}`}
              />
              <span className="text-gray-400 text-sm">→</span>
              <select
                value={value}
                onChange={(e) => handleValueChange(key, e.target.value)}
                className="flex-1 px-3 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                data-testid={`mapping-value-${idx}`}
              >
                {UNIVERSAL_ENTITY_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => handleRemove(key)}
                className="p-1.5 text-red-500 hover:bg-red-50 rounded"
                aria-label="Remove mapping"
                data-testid={`mapping-remove-${idx}`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={handleAdd}
        className="px-3 py-1.5 text-sm text-blue-600 border border-blue-300 rounded hover:bg-blue-50 transition-colors"
        data-testid="add-mapping-button"
      >
        + Add Mapping
      </button>
    </div>
  );
}
