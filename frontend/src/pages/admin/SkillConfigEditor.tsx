/**
 * SkillConfigEditor Page Component
 * Sprint 97 Feature 97.2: Skill Configuration Editor (10 SP)
 *
 * Features:
 * - YAML editor for config.yaml
 * - Real-time validation
 * - Live preview of parsed configuration
 * - Save/Reset functionality
 * - Error and warning display
 *
 * Route: /admin/skills/:skillName/config
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Save, RotateCcw, AlertTriangle, CheckCircle, Zap, Shield } from 'lucide-react';
import {
  getSkillConfig,
  updateSkillConfig,
  validateSkillConfig,
  getSkill,
  getResolvedTools,
} from '../../api/skills';
import type { ConfigValidationResult, SkillDetail, ResolvedToolsResponse } from '../../types/skills';
import yaml from 'js-yaml';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

export function SkillConfigEditor() {
  const { skillName } = useParams<{ skillName: string }>();

  // Editor state
  const [yamlContent, setYamlContent] = useState('');
  const [originalYaml, setOriginalYaml] = useState('');
  const [parsedConfig, setParsedConfig] = useState<Record<string, unknown> | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Validation state
  const [validation, setValidation] = useState<ConfigValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  // Skill detail state (triggers, tools, permissions)
  const [skillDetail, setSkillDetail] = useState<SkillDetail | null>(null);

  // Sprint 121: Resolved tools state (ADR-058)
  const [resolvedTools, setResolvedTools] = useState<ResolvedToolsResponse | null>(null);

  // Loading and error state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load configuration and skill details
  const loadConfig = useCallback(async () => {
    if (!skillName) return;

    setLoading(true);
    setError(null);

    try {
      const [config, detail, resolved] = await Promise.all([
        getSkillConfig(skillName),
        getSkill(skillName).catch(() => null),
        getResolvedTools(skillName).catch(() => null),
      ]);
      const yamlString = yaml.dump(config, { indent: 2, lineWidth: 100 });
      setYamlContent(yamlString);
      setOriginalYaml(yamlString);
      setParsedConfig(config);
      setSkillDetail(detail);
      setResolvedTools(resolved);
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  }, [skillName]);

  // Initial load
  useEffect(() => {
    void loadConfig();
  }, [loadConfig]);

  // Handle YAML content change
  const handleYamlChange = (newContent: string) => {
    setYamlContent(newContent);
    setIsDirty(newContent !== originalYaml);

    // Try to parse YAML
    try {
      const parsed = yaml.load(newContent) as Record<string, unknown>;
      setParsedConfig(parsed);

      // Trigger validation
      if (skillName) {
        void validateConfig(parsed);
      }
    } catch (err) {
      setParsedConfig(null);
      setValidation({
        valid: false,
        errors: [`YAML syntax error: ${err instanceof Error ? err.message : 'Invalid YAML'}`],
        warnings: [],
      });
    }
  };

  // Validate configuration
  const validateConfig = async (config: Record<string, unknown>) => {
    if (!skillName) return;

    setValidating(true);

    try {
      const result = await validateSkillConfig(skillName, config);
      setValidation(result);
    } catch (err) {
      console.error('Validation error:', err);
    } finally {
      setValidating(false);
    }
  };

  // Save configuration
  const handleSave = async () => {
    if (!skillName || !parsedConfig) return;

    setSaving(true);
    setError(null);

    try {
      await updateSkillConfig(skillName, parsedConfig);
      setOriginalYaml(yamlContent);
      setIsDirty(false);
      alert('Configuration saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  // Reset to original
  const handleReset = () => {
    if (window.confirm('Discard all changes and reset to original configuration?')) {
      setYamlContent(originalYaml);
      setIsDirty(false);

      // Re-parse original
      try {
        const parsed = yaml.load(originalYaml) as Record<string, unknown>;
        setParsedConfig(parsed);
        if (skillName) {
          void validateConfig(parsed);
        }
      } catch (err) {
        console.error('Failed to parse original YAML:', err);
      }
    }
  };

  if (!skillName) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <p className="text-lg text-gray-600 dark:text-gray-400">Skill name is required</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mb-4">
        <AdminNavigationBar />
      </div>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin/skills/registry"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Registry
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Skill Configuration: {skillName}
              </h1>
              <div className="flex items-center gap-4 mt-2">
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 pb-1">
                  Config
                </span>
                <Link
                  to={`/admin/skills/${skillName}/tools`}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 pb-1"
                >
                  Tools
                </Link>
                <Link
                  to={`/admin/skills/${skillName}/logs`}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 pb-1"
                >
                  Logs
                </Link>
                <Link
                  to={`/admin/skills/${skillName}/skill-md`}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 pb-1"
                >
                  SKILL.md
                </Link>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleReset}
                disabled={!isDirty || saving}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={handleSave}
                disabled={!isDirty || !validation?.valid || saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid={`skill-save-${skillName}`}
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div
            data-testid="save-error"
            className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6"
          >
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-gray-600 dark:text-gray-400">Loading configuration...</p>
          </div>
        )}

        {/* Editor */}
        {!loading && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* YAML Editor */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
              <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                config.yaml
              </h3>
              <textarea
                value={yamlContent}
                onChange={(e) => handleYamlChange(e.target.value)}
                className="w-full h-[600px] font-mono text-sm bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg border border-gray-300 dark:border-gray-600 p-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                spellCheck={false}
                data-testid={`skill-config-${skillName}`}
              />
            </div>

            {/* Preview and Validation */}
            <div className="space-y-6">
              {/* Validation Status */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                  Validation
                </h3>

                {validating && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">Validating...</p>
                )}

                {!validating && validation && (
                  <div className="space-y-3">
                    {/* Valid Status */}
                    {validation.valid && (
                      <div
                        className="flex items-center gap-2 text-green-700 dark:text-green-400"
                        data-testid="validation-status"
                      >
                        <CheckCircle className="w-5 h-5" />
                        <span className="font-medium">YAML syntax valid</span>
                      </div>
                    )}

                    {/* Errors */}
                    {validation.errors.length > 0 && (
                      <div className="space-y-2" data-testid="validation-errors">
                        <h4 className="font-medium text-red-700 dark:text-red-400">
                          Errors ({validation.errors.length})
                        </h4>
                        {validation.errors.map((error, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded p-2"
                          >
                            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            <span>{error}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Warnings */}
                    {validation.warnings.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="font-medium text-yellow-700 dark:text-yellow-400">
                          Warnings ({validation.warnings.length})
                        </h4>
                        {validation.warnings.map((warning, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2 text-sm text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 rounded p-2"
                          >
                            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                            <span>{warning}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Preview */}
              <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                  Preview
                </h3>

                {parsedConfig ? (
                  <div className="space-y-2">
                    {Object.entries(parsedConfig).map(([key, value]) => (
                      <div key={key} className="text-sm">
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {key}:
                        </span>{' '}
                        <span className="text-gray-600 dark:text-gray-400">
                          {typeof value === 'object'
                            ? JSON.stringify(value, null, 2)
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Fix YAML syntax errors to see preview
                  </p>
                )}
              </div>

              {/* Sprint 121: Triggers Panel */}
              {skillDetail && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
                      🎯 Triggers ({skillDetail.triggers.length})
                    </h3>
                    <Link
                      to={`/admin/skills/${skillName}/skill-md`}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800"
                    >
                      Edit in SKILL.md →
                    </Link>
                  </div>
                  {skillDetail.triggers.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {skillDetail.triggers.map((trigger) => (
                        <span
                          key={trigger}
                          className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm border border-blue-200 dark:border-blue-800"
                        >
                          {trigger}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No triggers defined</p>
                  )}
                </div>
              )}

              {/* Sprint 121: Tools Panel */}
              {skillDetail && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
                      🔧 Tools ({skillDetail.tools.length})
                    </h3>
                    <Link
                      to={`/admin/skills/${skillName}/tools`}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800"
                    >
                      Manage Authorizations →
                    </Link>
                  </div>
                  {skillDetail.tools.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {skillDetail.tools.map((tool) => (
                        <span
                          key={tool}
                          className="px-3 py-1 bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full text-sm border border-purple-200 dark:border-purple-800"
                        >
                          {tool}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No tools configured</p>
                  )}
                </div>
              )}

              {/* Sprint 121: Permissions Panel */}
              {skillDetail && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                    🔒 Permissions ({skillDetail.permissions.length})
                  </h3>
                  {skillDetail.permissions.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {skillDetail.permissions.map((perm) => (
                        <span
                          key={perm}
                          className="px-3 py-1 bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full text-sm border border-amber-200 dark:border-amber-800"
                        >
                          {perm}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No permissions required</p>
                  )}
                </div>
              )}

              {/* Sprint 121: Auto-Resolved Tools Panel (ADR-058) */}
              {resolvedTools && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-emerald-200 dark:border-emerald-800 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Zap className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                      <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
                        Auto-Resolved Tools ({resolvedTools.total})
                      </h3>
                    </div>
                    <span className="text-xs px-2 py-1 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 rounded-full">
                      ADR-058
                    </span>
                  </div>

                  {resolvedTools.permissions.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Declared Permissions:</p>
                      <div className="flex flex-wrap gap-1">
                        {resolvedTools.permissions.map((perm) => (
                          <span
                            key={perm}
                            className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs"
                          >
                            {perm}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {resolvedTools.resolved_tools.length > 0 ? (
                    <div className="space-y-2">
                      {resolvedTools.resolved_tools.map((tool) => (
                        <div
                          key={tool.tool_name}
                          className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700"
                        >
                          <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-emerald-500" />
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {tool.tool_name}
                            </span>
                            <span className="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                              {tool.capability}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                              tool.source === 'static'
                                ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                                : tool.source === 'llm_cached'
                                ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300'
                                : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                            }`}>
                              {tool.source === 'static' ? 'Static' : tool.source === 'llm_cached' ? 'LLM' : 'Override'}
                            </span>
                            {tool.confidence < 1.0 && (
                              <span className="text-xs text-gray-400">
                                {Math.round(tool.confidence * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      No tools resolved. Add permissions to SKILL.md frontmatter to enable auto-resolve.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default SkillConfigEditor;
