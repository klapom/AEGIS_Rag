/**
 * GraphExpansionSettings Component
 * Sprint 79 Feature 79.6: UI Settings for Graph Expansion
 *
 * Provides controls for the 3-Stage Semantic Search:
 * - Enable/Disable toggle
 * - N-hop depth slider (1-3)
 * - Synonym threshold slider (5-20)
 * - Max synonyms per entity slider (1-5)
 *
 * Settings persist to localStorage and are sent with chat requests.
 */

import { useState, useEffect, useCallback } from 'react';
import { Network, RotateCcw, ChevronDown, ChevronUp, Info } from 'lucide-react';
import {
  type GraphExpansionConfig,
  DEFAULT_GRAPH_EXPANSION_CONFIG,
  GRAPH_EXPANSION_STORAGE_KEY,
} from '../../types/settings';

/**
 * Props for GraphExpansionSettings component
 */
export interface GraphExpansionSettingsProps {
  /** Current configuration (controlled mode) */
  config?: GraphExpansionConfig;
  /** Callback when configuration changes */
  onChange?: (config: GraphExpansionConfig) => void;
  /** Whether to show as collapsed/compact initially */
  defaultCollapsed?: boolean;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Load graph expansion settings from localStorage
 */
export function loadGraphExpansionConfig(): GraphExpansionConfig {
  try {
    const stored = localStorage.getItem(GRAPH_EXPANSION_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to handle missing properties
      return { ...DEFAULT_GRAPH_EXPANSION_CONFIG, ...parsed };
    }
  } catch (error) {
    console.error('Failed to load graph expansion settings:', error);
  }
  return DEFAULT_GRAPH_EXPANSION_CONFIG;
}

/**
 * Save graph expansion settings to localStorage
 */
export function saveGraphExpansionConfig(config: GraphExpansionConfig): void {
  try {
    localStorage.setItem(GRAPH_EXPANSION_STORAGE_KEY, JSON.stringify(config));
  } catch (error) {
    console.error('Failed to save graph expansion settings:', error);
  }
}

/**
 * GraphExpansionSettings Component
 *
 * Provides a collapsible panel with settings for graph-based search expansion.
 *
 * @example
 * ```tsx
 * // Uncontrolled mode - manages its own state
 * <GraphExpansionSettings />
 *
 * // Controlled mode
 * <GraphExpansionSettings
 *   config={myConfig}
 *   onChange={(newConfig) => setMyConfig(newConfig)}
 * />
 * ```
 */
export function GraphExpansionSettings({
  config: controlledConfig,
  onChange,
  defaultCollapsed = true,
  className = '',
}: GraphExpansionSettingsProps) {
  // Internal state for uncontrolled mode
  const [internalConfig, setInternalConfig] = useState<GraphExpansionConfig>(
    () => loadGraphExpansionConfig()
  );
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

  // Use controlled or uncontrolled config
  const config = controlledConfig ?? internalConfig;

  // Update handler that works for both modes
  const updateConfig = useCallback(
    (updates: Partial<GraphExpansionConfig>) => {
      const newConfig = { ...config, ...updates };

      if (controlledConfig) {
        // Controlled mode - call parent onChange
        onChange?.(newConfig);
      } else {
        // Uncontrolled mode - update internal state and persist
        setInternalConfig(newConfig);
        saveGraphExpansionConfig(newConfig);
      }
    },
    [config, controlledConfig, onChange]
  );

  // Persist changes in uncontrolled mode
  useEffect(() => {
    if (!controlledConfig) {
      saveGraphExpansionConfig(internalConfig);
    }
  }, [internalConfig, controlledConfig]);

  // Reset to defaults
  const handleReset = useCallback(() => {
    updateConfig(DEFAULT_GRAPH_EXPANSION_CONFIG);
  }, [updateConfig]);

  // Toggle enabled state
  const handleToggleEnabled = useCallback(() => {
    updateConfig({ enabled: !config.enabled });
  }, [config.enabled, updateConfig]);

  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 ${className}`}
      data-testid="graph-expansion-settings"
    >
      {/* Header - clickable to expand/collapse */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
        aria-expanded={!isCollapsed}
        aria-controls="graph-expansion-content"
        data-testid="graph-expansion-header"
      >
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-primary" />
          <span className="font-medium text-gray-900 text-sm">Graph Expansion</span>
          {/* Status badge */}
          <span
            className={`px-2 py-0.5 text-xs rounded-full ${
              config.enabled
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {config.enabled ? 'Aktiv' : 'Inaktiv'}
          </span>
        </div>
        {isCollapsed ? (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronUp className="h-5 w-5 text-gray-400" />
        )}
      </button>

      {/* Collapsible content */}
      {!isCollapsed && (
        <div
          id="graph-expansion-content"
          className="px-4 pb-4 space-y-4 border-t border-gray-100"
          data-testid="graph-expansion-content"
        >
          {/* Enable/Disable Toggle */}
          <div className="flex items-center justify-between pt-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">
                Graph Expansion aktivieren
              </span>
              <button
                type="button"
                className="text-gray-400 hover:text-gray-600"
                title="Erweitert Suchanfragen durch Graph-Traversierung und semantische Expansion"
              >
                <Info className="h-4 w-4" />
              </button>
            </div>
            <button
              onClick={handleToggleEnabled}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary ${
                config.enabled ? 'bg-primary' : 'bg-gray-300'
              }`}
              role="switch"
              aria-checked={config.enabled}
              aria-label={config.enabled ? 'Graph Expansion deaktivieren' : 'Graph Expansion aktivieren'}
              data-testid="graph-expansion-toggle"
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  config.enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Settings - only shown when enabled */}
          {config.enabled && (
            <div className="space-y-4">
              {/* Graph Traversal Depth Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="graph-expansion-hops"
                    className="text-sm font-medium text-gray-700"
                  >
                    Graph-Traversierungstiefe
                  </label>
                  <span className="text-sm font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
                    {config.graphExpansionHops} {config.graphExpansionHops === 1 ? 'Hop' : 'Hops'}
                  </span>
                </div>
                <input
                  id="graph-expansion-hops"
                  type="range"
                  min={1}
                  max={3}
                  step={1}
                  value={config.graphExpansionHops}
                  onChange={(e) =>
                    updateConfig({ graphExpansionHops: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
                  aria-valuemin={1}
                  aria-valuemax={3}
                  aria-valuenow={config.graphExpansionHops}
                  data-testid="graph-expansion-hops-slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1 (Schnell)</span>
                  <span>2</span>
                  <span>3 (Umfassend)</span>
                </div>
                <p className="text-xs text-gray-500">
                  Wie viele Verbindungen von Entities traversiert werden
                </p>
              </div>

              {/* Synonym Threshold Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="min-entities-threshold"
                    className="text-sm font-medium text-gray-700"
                  >
                    Synonym-Fallback Schwelle
                  </label>
                  <span className="text-sm font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
                    {config.minEntitiesThreshold} Entities
                  </span>
                </div>
                <input
                  id="min-entities-threshold"
                  type="range"
                  min={5}
                  max={20}
                  step={1}
                  value={config.minEntitiesThreshold}
                  onChange={(e) =>
                    updateConfig({ minEntitiesThreshold: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
                  aria-valuemin={5}
                  aria-valuemax={20}
                  aria-valuenow={config.minEntitiesThreshold}
                  data-testid="min-entities-threshold-slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>5 (Mehr Synonyme)</span>
                  <span>20 (Weniger Synonyme)</span>
                </div>
                <p className="text-xs text-gray-500">
                  Mindestanzahl Entities bevor LLM-Synonyme generiert werden
                </p>
              </div>

              {/* Max Synonyms Per Entity Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="max-synonyms-per-entity"
                    className="text-sm font-medium text-gray-700"
                  >
                    Max. Synonyme pro Entity
                  </label>
                  <span className="text-sm font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
                    {config.maxSynonymsPerEntity}
                  </span>
                </div>
                <input
                  id="max-synonyms-per-entity"
                  type="range"
                  min={1}
                  max={5}
                  step={1}
                  value={config.maxSynonymsPerEntity}
                  onChange={(e) =>
                    updateConfig({ maxSynonymsPerEntity: parseInt(e.target.value, 10) })
                  }
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
                  aria-valuemin={1}
                  aria-valuemax={5}
                  aria-valuenow={config.maxSynonymsPerEntity}
                  data-testid="max-synonyms-slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1 (Minimal)</span>
                  <span>3</span>
                  <span>5 (Maximal)</span>
                </div>
                <p className="text-xs text-gray-500">
                  Anzahl der Synonyme die pro Entity generiert werden
                </p>
              </div>

              {/* Reset Button */}
              <div className="pt-2 border-t border-gray-100">
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                  data-testid="graph-expansion-reset"
                >
                  <RotateCcw className="h-4 w-4" />
                  Auf Standardwerte zurücksetzen
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact version of GraphExpansionSettings for inline use
 * Shows only enable/disable toggle with expandable details
 */
export function GraphExpansionSettingsCompact({
  config: controlledConfig,
  onChange,
  className = '',
}: Omit<GraphExpansionSettingsProps, 'defaultCollapsed'>) {
  const [internalConfig, setInternalConfig] = useState<GraphExpansionConfig>(
    () => loadGraphExpansionConfig()
  );
  const [showDetails, setShowDetails] = useState(false);

  const config = controlledConfig ?? internalConfig;

  const updateConfig = useCallback(
    (updates: Partial<GraphExpansionConfig>) => {
      const newConfig = { ...config, ...updates };
      if (controlledConfig) {
        onChange?.(newConfig);
      } else {
        setInternalConfig(newConfig);
        saveGraphExpansionConfig(newConfig);
      }
    },
    [config, controlledConfig, onChange]
  );

  return (
    <div
      className={`flex items-center gap-2 ${className}`}
      data-testid="graph-expansion-settings-compact"
    >
      {/* Toggle button with icon */}
      <button
        onClick={() => updateConfig({ enabled: !config.enabled })}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg transition-colors ${
          config.enabled
            ? 'bg-primary/10 text-primary border border-primary/30'
            : 'bg-gray-100 text-gray-500 border border-gray-200 hover:bg-gray-200'
        }`}
        title={
          config.enabled
            ? `Graph Expansion aktiv (${config.graphExpansionHops} Hops)`
            : 'Graph Expansion aktivieren'
        }
        aria-pressed={config.enabled}
        data-testid="graph-expansion-compact-toggle"
      >
        <Network className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Graph</span>
        {config.enabled && (
          <span className="font-semibold">{config.graphExpansionHops}H</span>
        )}
      </button>

      {/* Settings popover trigger */}
      {config.enabled && (
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="p-1 text-gray-400 hover:text-gray-600 rounded"
          title="Graph Expansion Einstellungen"
          aria-expanded={showDetails}
          data-testid="graph-expansion-settings-trigger"
        >
          <ChevronDown
            className={`h-4 w-4 transition-transform ${
              showDetails ? 'rotate-180' : ''
            }`}
          />
        </button>
      )}

      {/* Settings dropdown */}
      {showDetails && config.enabled && (
        <div
          className="absolute top-full left-0 mt-2 w-72 bg-white rounded-lg border border-gray-200 shadow-lg z-50"
          data-testid="graph-expansion-dropdown"
        >
          <GraphExpansionSettings
            config={config}
            onChange={updateConfig}
            defaultCollapsed={false}
            className="border-0 shadow-none"
          />
        </div>
      )}
    </div>
  );
}
