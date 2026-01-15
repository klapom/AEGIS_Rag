/**
 * PIIRedactionSettings Component
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Configure PII detection and redaction settings.
 */

import { useState } from 'react';
import { Shield, Eye, EyeOff } from 'lucide-react';
import type { PIIRedactionSettings, DataCategory } from '../../types/gdpr';

interface PIIRedactionSettingsProps {
  settings: PIIRedactionSettings;
  onSave: (settings: PIIRedactionSettings) => void;
}

const dataCategoryOptions: DataCategory[] = [
  'identifier',
  'contact',
  'financial',
  'health',
  'biometric',
  'location',
];

export function PIIRedactionSettings({ settings, onSave }: PIIRedactionSettingsProps) {
  const [formData, setFormData] = useState<PIIRedactionSettings>(settings);
  const [hasChanges, setHasChanges] = useState(false);

  const handleChange = (updates: Partial<PIIRedactionSettings>) => {
    setFormData({ ...formData, ...updates });
    setHasChanges(true);
  };

  const handleToggleCategory = (category: DataCategory) => {
    const newCategories = formData.enabledCategories.includes(category)
      ? formData.enabledCategories.filter((c) => c !== category)
      : [...formData.enabledCategories, category];
    handleChange({ enabledCategories: newCategories });
  };

  const handleSave = () => {
    onSave(formData);
    setHasChanges(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            PII Detection & Redaction
          </h3>
        </div>
        {hasChanges && (
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Save Changes
          </button>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-6">
        {/* Enable PII Detection */}
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900 dark:text-gray-100">
              Enable PII Detection
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Automatically detect personally identifiable information
            </p>
          </div>
          <button
            onClick={() => handleChange({ enabled: !formData.enabled })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              formData.enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                formData.enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Auto-Redact */}
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-gray-900 dark:text-gray-100">
              Auto-Redact PII
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Automatically redact detected PII in responses
            </p>
          </div>
          <button
            onClick={() => handleChange({ autoRedact: !formData.autoRedact })}
            disabled={!formData.enabled}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
              formData.autoRedact ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                formData.autoRedact ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Redaction Character */}
        <div>
          <label htmlFor="redactionChar" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Redaction Character
          </label>
          <input
            id="redactionChar"
            type="text"
            maxLength={1}
            value={formData.redactionChar}
            onChange={(e) => handleChange({ redactionChar: e.target.value || '*' })}
            disabled={!formData.enabled}
            className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
            Example: "John Doe" → "******** ****"
          </p>
        </div>

        {/* Detection Threshold */}
        <div>
          <label htmlFor="detectionThreshold" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Detection Confidence Threshold: {(formData.detectionThreshold * 100).toFixed(0)}%
          </label>
          <input
            id="detectionThreshold"
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={formData.detectionThreshold}
            onChange={(e) => handleChange({ detectionThreshold: parseFloat(e.target.value) })}
            disabled={!formData.enabled}
            className="w-full disabled:opacity-50"
          />
          <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
            <span>Less strict (0%)</span>
            <span>More strict (100%)</span>
          </div>
        </div>

        {/* Enabled Categories */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Detect Categories
          </label>
          <div className="grid grid-cols-2 gap-2">
            {dataCategoryOptions.map((category) => (
              <label
                key={category}
                className={`flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
                  !formData.enabled ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.enabledCategories.includes(category)}
                  onChange={() => handleToggleCategory(category)}
                  disabled={!formData.enabled}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed"
                />
                <span className="text-sm text-gray-900 dark:text-gray-100 capitalize">
                  {category}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Status Indicator */}
        <div
          className={`flex items-center gap-2 p-3 rounded-lg ${
            formData.enabled
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
              : 'bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600'
          }`}
        >
          {formData.enabled ? (
            <>
              <Eye className="w-5 h-5 text-green-600 dark:text-green-400" />
              <span className="text-sm text-green-700 dark:text-green-300">
                PII Detection Active
              </span>
            </>
          ) : (
            <>
              <EyeOff className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                PII Detection Disabled
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
