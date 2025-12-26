/**
 * AdminLLMConfigPage Component
 * Sprint 36 Feature 36.3: Model Selection per Use Case (8 SP)
 * Sprint 51: Dynamic Ollama model loading
 * Sprint 52 Feature 52.1: Community Summary Model Selection
 * Sprint 64 Feature 64.6: Backend API Integration (2 SP)
 *
 * Features:
 * - Configure LLM models for each use case
 * - Support for Ollama (local), Alibaba Cloud, and OpenAI providers
 * - Dynamic loading of locally available Ollama models
 * - Backend API persistence with Redis (Sprint 64)
 * - One-time migration from localStorage to backend
 * - Backend-persisted community summary model config (Sprint 52)
 * - Responsive design with dark mode support
 */

import { useState, useEffect } from 'react';
import { Settings, RefreshCw, CheckCircle, AlertCircle, Cpu, ArrowLeft, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

interface ModelOption {
  id: string;
  provider: 'ollama' | 'alibaba_cloud' | 'openai';
  name: string;
  description: string;
  capabilities: ('text' | 'vision' | 'embedding')[];
}

interface UseCaseConfig {
  useCase: UseCaseType;
  modelId: string;
  enabled: boolean;
}

type UseCaseType =
  | 'intent_classification'
  | 'entity_extraction'
  | 'answer_generation'
  | 'followup_titles'
  | 'query_decomposition'
  | 'vision_vlm';

interface OllamaModel {
  name: string;
  size: number;
  digest: string;
  modified_at: string;
}

interface OllamaModelsResponse {
  models: OllamaModel[];
  ollama_available: boolean;
  error: string | null;
}

// Sprint 52 Feature 52.1: Community Summary Model Configuration
interface SummaryModelConfig {
  model_id: string;
  updated_at: string | null;
}

// ============================================================================
// Cloud Model Options (static)
// ============================================================================

const cloudModelOptions: ModelOption[] = [
  // Alibaba Cloud
  {
    id: 'alibaba/qwen-turbo',
    provider: 'alibaba_cloud',
    name: 'Qwen Turbo (Cloud)',
    description: 'Fast, cost-effective',
    capabilities: ['text'],
  },
  {
    id: 'alibaba/qwen-plus',
    provider: 'alibaba_cloud',
    name: 'Qwen Plus (Cloud)',
    description: 'High quality',
    capabilities: ['text'],
  },
  {
    id: 'alibaba/qwen3-vl-30b',
    provider: 'alibaba_cloud',
    name: 'Qwen3-VL 30B (Cloud)',
    description: 'Vision model, cloud',
    capabilities: ['text', 'vision'],
  },
  // OpenAI
  {
    id: 'openai/gpt-4o',
    provider: 'openai',
    name: 'GPT-4o (Cloud)',
    description: 'Best quality, highest cost',
    capabilities: ['text', 'vision'],
  },
  {
    id: 'openai/gpt-4o-mini',
    provider: 'openai',
    name: 'GPT-4o Mini (Cloud)',
    description: 'Cost-effective',
    capabilities: ['text'],
  },
];

// Helper to determine model capabilities based on name
function getModelCapabilities(modelName: string): ('text' | 'vision' | 'embedding')[] {
  const name = modelName.toLowerCase();
  if (name.includes('embed') || name.includes('bge')) {
    return ['embedding'];
  }
  if (name.includes('vl') || name.includes('vision') || name.includes('llava')) {
    return ['text', 'vision'];
  }
  return ['text'];
}

// Helper to format model size
function formatModelSize(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)}GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)}MB`;
  return `${bytes}B`;
}

// ============================================================================
// Use Case Definitions
// ============================================================================

const useCaseDefinitions: Record<
  UseCaseType,
  { label: string; description: string; requiresVision: boolean }
> = {
  intent_classification: {
    label: 'Intent Classification',
    description: 'Query → VECTOR/GRAPH/HYBRID routing',
    requiresVision: false,
  },
  entity_extraction: {
    label: 'Entity/Relation Extraction',
    description: 'Document → Entities + Relations',
    requiresVision: false,
  },
  answer_generation: {
    label: 'Answer Generation',
    description: 'Context → Final Answer',
    requiresVision: false,
  },
  followup_titles: {
    label: 'Follow-Up & Titles',
    description: 'Generate follow-up questions and titles',
    requiresVision: false,
  },
  query_decomposition: {
    label: 'Query Decomposition',
    description: 'Complex Query → Sub-Queries',
    requiresVision: false,
  },
  vision_vlm: {
    label: 'Vision (VLM)',
    description: 'Image → Text Description',
    requiresVision: true,
  },
};

// ============================================================================
// Default Configuration
// ============================================================================

const defaultConfig: UseCaseConfig[] = [
  { useCase: 'intent_classification', modelId: 'ollama/qwen3:32b', enabled: true },
  { useCase: 'entity_extraction', modelId: 'ollama/qwen3:32b', enabled: true },
  { useCase: 'answer_generation', modelId: 'ollama/qwen3:32b', enabled: true },
  { useCase: 'followup_titles', modelId: 'ollama/qwen3:32b', enabled: true },
  { useCase: 'query_decomposition', modelId: 'ollama/qwen3:32b', enabled: true },
  { useCase: 'vision_vlm', modelId: 'ollama/qwen3-vl:32b', enabled: true },
];

const LLM_CONFIG_KEY = 'aegis-rag-llm-config';
const MIGRATION_FLAG_KEY = 'aegis-rag-llm-config-migrated';

// ============================================================================
// Model ID Transformation Helpers (Sprint 64 Feature 64.6)
// ============================================================================

/**
 * Convert frontend model ID format to backend format
 * Frontend: "ollama/qwen3:32b", "alibaba/qwen-plus", "openai/gpt-4o"
 * Backend: "qwen3:32b", "alibaba_cloud:qwen-plus", "openai:gpt-4o"
 */
function frontendToBackend(modelId: string): string {
  if (modelId.startsWith('ollama/')) {
    return modelId.replace('ollama/', ''); // "ollama/qwen3:32b" → "qwen3:32b"
  }
  if (modelId.startsWith('alibaba/')) {
    return modelId.replace('alibaba/', 'alibaba_cloud:'); // "alibaba/qwen-plus" → "alibaba_cloud:qwen-plus"
  }
  // OpenAI: "openai/gpt-4o" → "openai:gpt-4o"
  return modelId.replace('/', ':');
}

/**
 * Convert backend model format to frontend model ID format
 * Backend: "qwen3:32b", "alibaba_cloud:qwen-plus", "openai:gpt-4o"
 * Frontend: "ollama/qwen3:32b", "alibaba/qwen-plus", "openai/gpt-4o"
 */
function backendToFrontend(model: string): string {
  if (model.startsWith('alibaba_cloud:')) {
    return model.replace('alibaba_cloud:', 'alibaba/'); // "alibaba_cloud:qwen-plus" → "alibaba/qwen-plus"
  }
  if (model.startsWith('openai:')) {
    return model.replace(':', '/'); // "openai:gpt-4o" → "openai/gpt-4o"
  }
  // Ollama (no prefix): "qwen3:32b" → "ollama/qwen3:32b"
  return `ollama/${model}`;
}

// ============================================================================
// Main Component
// ============================================================================

export function AdminLLMConfigPage() {
  const [config, setConfig] = useState<UseCaseConfig[]>(defaultConfig);
  const [modelOptions, setModelOptions] = useState<ModelOption[]>(cloudModelOptions);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [ollamaStatus, setOllamaStatus] = useState<'loading' | 'available' | 'unavailable'>('loading');
  const [ollamaError, setOllamaError] = useState<string | null>(null);

  // Sprint 52 Feature 52.1: Community Summary Model State
  const [summaryModelConfig, setSummaryModelConfig] = useState<SummaryModelConfig>({
    model_id: 'ollama/qwen3:32b',
    updated_at: null,
  });
  const [isSavingSummaryModel, setIsSavingSummaryModel] = useState(false);
  const [summaryModelSaveStatus, setSummaryModelSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // Sprint 64 Feature 64.6: Fetch LLM config from backend
  const fetchLLMConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/llm/config`);
      if (response.ok) {
        const data = await response.json();

        // Convert backend format to frontend format
        const frontendConfig: UseCaseConfig[] = Object.entries(data.use_cases).map(
          ([useCase, config]: [string, any]) => ({
            useCase: useCase as UseCaseType,
            modelId: backendToFrontend(config.model),
            enabled: config.enabled,
          })
        );

        setConfig(frontendConfig);
        console.log('LLM config loaded from backend:', frontendConfig);
      } else {
        console.error('Failed to fetch LLM config from backend');
      }
    } catch (e) {
      console.error('Failed to fetch LLM config:', e);
    }
  };

  // Sprint 64 Feature 64.6: One-time migration from localStorage to backend
  const migrateFromLocalStorage = async () => {
    const migrated = localStorage.getItem(MIGRATION_FLAG_KEY);
    if (migrated === 'true') {
      return; // Already migrated
    }

    const stored = localStorage.getItem(LLM_CONFIG_KEY);
    if (stored) {
      try {
        const localConfig: UseCaseConfig[] = JSON.parse(stored);
        console.log('Migrating localStorage config to backend:', localConfig);

        // Convert to backend format
        const backendConfig: Record<string, { model: string; enabled: boolean }> = {};
        localConfig.forEach((uc) => {
          backendConfig[uc.useCase] = {
            model: frontendToBackend(uc.modelId),
            enabled: uc.enabled,
          };
        });

        // Save to backend
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/llm/config`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ use_cases: backendConfig }),
        });

        if (response.ok) {
          console.log('localStorage config migrated to backend successfully');
          localStorage.setItem(MIGRATION_FLAG_KEY, 'true');
          localStorage.removeItem(LLM_CONFIG_KEY); // Clean up
        } else {
          console.error('Failed to migrate config to backend');
        }
      } catch (e) {
        console.error('Failed to migrate localStorage config:', e);
      }
    } else {
      // No localStorage config to migrate, mark as migrated
      localStorage.setItem(MIGRATION_FLAG_KEY, 'true');
    }
  };

  // Fetch Ollama models, summary model config, and LLM config on mount
  useEffect(() => {
    const initializeConfig = async () => {
      await migrateFromLocalStorage(); // Migrate first
      await fetchLLMConfig(); // Then load from backend
    };

    fetchOllamaModels();
    fetchSummaryModelConfig();
    initializeConfig();
  }, []);

  const fetchOllamaModels = async () => {
    setIsRefreshing(true);
    setOllamaStatus('loading');
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/llm/models`);
      const data: OllamaModelsResponse = await response.json();

      if (data.ollama_available && data.models.length > 0) {
        // Convert Ollama models to ModelOption format
        const ollamaModels: ModelOption[] = data.models.map((m) => ({
          id: `ollama/${m.name}`,
          provider: 'ollama' as const,
          name: `${m.name} (Local)`,
          description: `${formatModelSize(m.size)}, local inference, $0 cost`,
          capabilities: getModelCapabilities(m.name),
        }));

        // Combine Ollama models with cloud options
        setModelOptions([...ollamaModels, ...cloudModelOptions]);
        setOllamaStatus('available');
        setOllamaError(null);
      } else {
        setModelOptions(cloudModelOptions);
        setOllamaStatus('unavailable');
        setOllamaError(data.error || 'No Ollama models found');
      }
    } catch (e) {
      console.error('Failed to fetch Ollama models:', e);
      setModelOptions(cloudModelOptions);
      setOllamaStatus('unavailable');
      setOllamaError(e instanceof Error ? e.message : 'Failed to connect');
    } finally {
      setIsRefreshing(false);
    }
  };

  // Sprint 52 Feature 52.1: Fetch summary model config from backend
  const fetchSummaryModelConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/llm/summary-model`);
      if (response.ok) {
        const data: SummaryModelConfig = await response.json();
        setSummaryModelConfig(data);
      }
    } catch (e) {
      console.error('Failed to fetch summary model config:', e);
    }
  };

  // Sprint 52 Feature 52.1: Save summary model config to backend
  const handleSaveSummaryModel = async () => {
    setIsSavingSummaryModel(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/llm/summary-model`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ model_id: summaryModelConfig.model_id }),
      });

      if (response.ok) {
        const data: SummaryModelConfig = await response.json();
        setSummaryModelConfig(data);
        setSummaryModelSaveStatus('success');
        setTimeout(() => setSummaryModelSaveStatus('idle'), 3000);
      } else {
        setSummaryModelSaveStatus('error');
      }
    } catch (e) {
      console.error('Failed to save summary model config:', e);
      setSummaryModelSaveStatus('error');
    } finally {
      setIsSavingSummaryModel(false);
    }
  };

  const handleSummaryModelChange = (modelId: string) => {
    setSummaryModelConfig((prev) => ({ ...prev, model_id: modelId }));
    setSummaryModelSaveStatus('idle');
  };

  const handleModelChange = (useCase: UseCaseType, modelId: string) => {
    setConfig((prev) =>
      prev.map((c) => (c.useCase === useCase ? { ...c, modelId } : c))
    );
    setSaveStatus('idle');
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Sprint 64 Feature 64.6: Save to backend API (replaces localStorage)
      // Sprint 65 Fix: Use correct backend schema (model_id + use_case, not just model)
      const backendConfig: Record<string, { use_case: string; model_id: string; enabled: boolean }> = {};
      config.forEach((uc) => {
        backendConfig[uc.useCase] = {
          use_case: uc.useCase,  // Sprint 65 Fix: Add use_case field
          model_id: uc.modelId,  // Sprint 65 Fix: Send frontend format (ollama/qwen3:32b)
          enabled: uc.enabled,
        };
      });

      const response = await fetch(`${API_BASE_URL}/api/v1/admin/llm/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ use_cases: backendConfig }),
      });

      if (response.ok) {
        console.log('LLM config saved to backend:', backendConfig);
        setSaveStatus('success');
        setTimeout(() => setSaveStatus('idle'), 3000);
      } else {
        console.error('Failed to save LLM config to backend');
        setSaveStatus('error');
      }
    } catch (e) {
      console.error('Failed to save config:', e);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRefreshModels = async () => {
    await fetchOllamaModels();
  };

  const getFilteredModels = (useCase: UseCaseType) => {
    const def = useCaseDefinitions[useCase];
    if (def.requiresVision) {
      return modelOptions.filter((m) => m.capabilities.includes('vision'));
    }
    return modelOptions.filter((m) => m.capabilities.includes('text'));
  };

  const getProviderBadgeColor = (provider: string) => {
    switch (provider) {
      case 'ollama':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'alibaba_cloud':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'openai':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div
      className="min-h-screen bg-gray-50 dark:bg-gray-900"
      data-testid="llm-config-page"
    >
      <div className="max-w-4xl mx-auto p-4">
        {/* Back Link */}
        <Link
          to="/admin"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Admin
        </Link>

        {/* Header */}
        <div className="mb-4">
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
            <Cpu className="w-4 h-4" />
            LLM Configuration
          </h1>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
            Configure which model to use for each use case
          </p>
        </div>

        {/* Ollama Status Banner */}
        {ollamaStatus === 'loading' && (
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <p className="text-sm text-blue-700 dark:text-blue-300 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Loading Ollama models...
            </p>
          </div>
        )}
        {ollamaStatus === 'available' && (
          <div className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
            <p className="text-sm text-green-700 dark:text-green-300 flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              {modelOptions.filter(m => m.provider === 'ollama').length} local Ollama models available
            </p>
          </div>
        )}
        {ollamaStatus === 'unavailable' && (
          <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
            <p className="text-sm text-yellow-700 dark:text-yellow-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Ollama not available: {ollamaError}. Using cloud models only.
            </p>
          </div>
        )}

        {/* Use Case Model Assignment */}
        <div className="bg-white dark:bg-gray-800 rounded-md shadow-sm p-4 mb-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-1.5">
            <Settings className="w-4 h-4" />
            Use Case Model Assignment
          </h2>

          <div className="space-y-3">
            {config.map((useCaseConfig) => {
              const def = useCaseDefinitions[useCaseConfig.useCase];
              const currentModel = modelOptions.find(
                (m) => m.id === useCaseConfig.modelId
              );
              const availableModels = getFilteredModels(useCaseConfig.useCase);

              return (
                <div
                  key={useCaseConfig.useCase}
                  className="border dark:border-gray-700 rounded-md p-3"
                  data-testid={`usecase-selector-${useCaseConfig.useCase}`}
                >
                  <div className="flex justify-between items-start mb-1.5">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {def.label}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {def.description}
                      </p>
                    </div>
                    {currentModel && (
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded ${getProviderBadgeColor(
                          currentModel.provider
                        )}`}
                      >
                        {currentModel.provider === 'ollama' ? 'Local' : 'Cloud'}
                      </span>
                    )}
                  </div>

                  <select
                    value={useCaseConfig.modelId}
                    onChange={(e) =>
                      handleModelChange(useCaseConfig.useCase, e.target.value)
                    }
                    className="w-full mt-1.5 p-1.5 text-sm border dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    data-testid={`model-dropdown-${useCaseConfig.useCase}`}
                  >
                    {availableModels.map((model) => (
                      <option
                        key={model.id}
                        value={model.id}
                        data-testid={`model-option-${model.id}`}
                      >
                        {model.name} - {model.description}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>
        </div>

        {/* Sprint 52 Feature 52.1: Community Summary Model Configuration */}
        <div className="bg-white dark:bg-gray-800 rounded-md shadow-sm p-4 mb-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-1.5">
            <FileText className="w-4 h-4" />
            Graph Community Summary Model
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Select the LLM model used for generating community summaries in LightRAG global search mode.
            This setting is persisted to the backend and takes effect immediately.
          </p>

          <div
            className="border dark:border-gray-700 rounded-md p-3"
            data-testid="summary-model-selector"
          >
            <div className="flex justify-between items-start mb-1.5">
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Community Summary Generation
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Graph Community Entities + Relations to Summary Text
                </p>
              </div>
              {summaryModelConfig.model_id && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    summaryModelConfig.model_id.startsWith('ollama/')
                      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                  }`}
                >
                  {summaryModelConfig.model_id.startsWith('ollama/') ? 'Local' : 'Cloud'}
                </span>
              )}
            </div>

            <select
              value={summaryModelConfig.model_id}
              onChange={(e) => handleSummaryModelChange(e.target.value)}
              className="w-full mt-1.5 p-1.5 text-sm border dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              data-testid="model-dropdown-community_summary"
            >
              {modelOptions
                .filter((m) => m.capabilities.includes('text'))
                .map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} - {model.description}
                  </option>
                ))}
            </select>

            {summaryModelConfig.updated_at && (
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                Last updated: {new Date(summaryModelConfig.updated_at).toLocaleString()}
              </p>
            )}

            <div className="mt-3 flex gap-2">
              <button
                onClick={handleSaveSummaryModel}
                disabled={isSavingSummaryModel}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                data-testid="save-summary-model-button"
              >
                {isSavingSummaryModel ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : summaryModelSaveStatus === 'success' ? (
                  <CheckCircle className="w-3 h-3" />
                ) : summaryModelSaveStatus === 'error' ? (
                  <AlertCircle className="w-3 h-3" />
                ) : null}
                {summaryModelSaveStatus === 'success'
                  ? 'Saved!'
                  : summaryModelSaveStatus === 'error'
                  ? 'Error'
                  : 'Save Summary Model'}
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 items-center">
          <button
            onClick={handleRefreshModels}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 text-gray-900 dark:text-gray-100"
            data-testid="refresh-models-button"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh Models
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            data-testid="save-config-button"
          >
            {isSaving ? (
              <RefreshCw className="w-3 h-3 animate-spin" />
            ) : saveStatus === 'success' ? (
              <CheckCircle className="w-3 h-3" />
            ) : saveStatus === 'error' ? (
              <AlertCircle className="w-3 h-3" />
            ) : null}
            {saveStatus === 'success'
              ? 'Saved!'
              : saveStatus === 'error'
              ? 'Error'
              : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}
