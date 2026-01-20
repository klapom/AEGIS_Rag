/**
 * ToolConfigModal Component
 * Sprint 116 Feature 116.5: MCP Tool Management UI
 *
 * Modal dialog for viewing and editing tool configuration.
 * Displays current settings and allows JSON-based configuration updates.
 */

import { useState, useEffect } from 'react';
import { X, Save, Settings, AlertCircle, CheckCircle } from 'lucide-react';
import { getToolConfig, updateToolConfig } from '../../api/admin';
import type { MCPTool } from '../../types/admin';

/**
 * Props for ToolConfigModal
 */
interface ToolConfigModalProps {
  tool: MCPTool | null;
  isOpen: boolean;
  onClose: () => void;
  onSave?: (config: Record<string, unknown>) => void;
}

/**
 * ToolConfigModal - Configuration editor modal
 *
 * Features:
 * - Load current configuration from API
 * - JSON editor for configuration
 * - Validation of JSON syntax
 * - Save configuration to backend
 * - Success/error feedback
 */
export function ToolConfigModal({ tool, isOpen, onClose, onSave }: ToolConfigModalProps) {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [configText, setConfigText] = useState('{}');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Load configuration when modal opens
  useEffect(() => {
    if (isOpen && tool) {
      void loadConfig();
    }
  }, [isOpen, tool]);

  const loadConfig = async () => {
    if (!tool) return;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await getToolConfig(tool.name);
      setConfig(response.config);
      setConfigText(JSON.stringify(response.config, null, 2));
      setJsonError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleConfigChange = (value: string) => {
    setConfigText(value);
    setJsonError(null);
    setSuccess(false);

    // Validate JSON
    try {
      const parsed = JSON.parse(value);
      setConfig(parsed);
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  const handleSave = async () => {
    if (!tool || jsonError) return;

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await updateToolConfig(tool.name, config);
      setSuccess(true);
      onSave?.(config);

      // Auto-close after success
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setConfig({});
    setConfigText('{}');
    setError(null);
    setSuccess(false);
    setJsonError(null);
    onClose();
  };

  if (!isOpen || !tool) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="tool-config-modal"
      onClick={handleClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/50 rounded-lg flex items-center justify-center">
              <Settings className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Tool Configuration
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">{tool.name}</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Close modal"
            data-testid="close-modal-button"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              <span className="ml-3 text-gray-500">Loading configuration...</span>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div
              className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg p-4"
              data-testid="config-error"
            >
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-700 dark:text-red-400">Error</p>
                  <p className="text-sm text-red-600 dark:text-red-300">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Success Display */}
          {success && (
            <div
              className="bg-green-50 dark:bg-green-900/20 border-2 border-green-200 dark:border-green-800 rounded-lg p-4"
              data-testid="config-success"
            >
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-green-700 dark:text-green-400">Success</p>
                  <p className="text-sm text-green-600 dark:text-green-300">
                    Configuration saved successfully
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Configuration Editor */}
          {!loading && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Configuration (JSON)
                </label>
                {jsonError && (
                  <span className="text-xs text-red-500 dark:text-red-400">{jsonError}</span>
                )}
              </div>
              <textarea
                value={configText}
                onChange={(e) => handleConfigChange(e.target.value)}
                rows={12}
                className={`w-full px-4 py-3 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 ${
                  jsonError
                    ? 'border-red-300 dark:border-red-700'
                    : 'border-gray-300 dark:border-gray-600'
                }`}
                placeholder='{\n  "timeout": 60,\n  "max_retries": 3\n}'
                data-testid="config-editor"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Edit the configuration as a JSON object. Changes will be validated before saving.
              </p>
            </div>
          )}

          {/* Tool Description */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <p className="text-sm text-blue-800 dark:text-blue-200">{tool.description}</p>
            <p className="text-xs text-blue-600 dark:text-blue-300 mt-2">
              Server: {tool.server_name}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            data-testid="cancel-button"
          >
            Cancel
          </button>
          <button
            onClick={() => void handleSave()}
            disabled={saving || loading || !!jsonError}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="save-config-button"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Configuration
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ToolConfigModal;
