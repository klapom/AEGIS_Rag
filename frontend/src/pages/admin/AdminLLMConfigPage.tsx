/**
 * AdminLLMConfigPage Component
 * Sprint 36 Feature 36.3: Model Selection per Use Case (8 SP)
 * Sprint 51: Dynamic Ollama model loading
 * Sprint 52 Feature 52.1: Community Summary Model Selection
 * Sprint 64 Feature 64.6: Backend API Integration (2 SP)
 * Sprint 70 Feature 70.7: Tool Use Configuration (3 SP)
 *
 * Features:
 * - Configure LLM models for each use case
 * - Support for Ollama (local), Alibaba Cloud, and OpenAI providers
 * - Dynamic loading of locally available Ollama models
 * - Backend API persistence with Redis (Sprint 64)
 * - One-time migration from localStorage to backend
 * - Backend-persisted community summary model config (Sprint 52)
 * - Tool use enable/disable toggles (Sprint 70)
 * - Responsive design with dark mode support
 */

import { useState, useEffect } from 'react';
import { Settings, RefreshCw, CheckCircle, AlertCircle, Cpu, ArrowLeft, FileText, Wrench } from 'lucide-react';
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

// Sprint 70 Feature 70.7: Tool Use Configuration
// Sprint 70 Feature 70.11: LLM-based Tool Detection
interface ToolsConfig {
  enable_chat_tools: boolean;
  enable_research_tools: boolean;
  tool_detection_strategy: string; // "markers" | "llm" | "hybrid"
  explicit_tool_markers: string[];
  action_hint_phrases: string[];
  updated_at: string | null;
  version: number;
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

  // Sprint 70 Feature 70.7: Tool Use Configuration State
  // Sprint 70 Feature 70.11: LLM-based Tool Detection State
  const [toolsConfig, setToolsConfig] = useState<ToolsConfig>({
    enable_chat_tools: false,
    enable_research_tools: false,
    tool_detection_strategy: 'markers',
    explicit_tool_markers: ['[TOOL:', '[SEARCH:', '[FETCH:'],
    action_hint_phrases: [
      'need to', 'haben zu', 'muss',
      'check', 'search', 'look up', 'prüfen', 'suchen',
      'current', 'latest', 'aktuell',
      "I'll need to access", 'Let me check',
    ],
    updated_at: null,
    version: 2,
  });
  const [isSavingToolsConfig, setIsSavingToolsConfig] = useState(false);
  const [toolsConfigSaveStatus, setToolsConfigSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

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

  // Fetch Ollama models, summary model config, LLM config, and tools config on mount
  useEffect(() => {
    const initializeConfig = async () => {
      await migrateFromLocalStorage(); // Migrate first
      await fetchLLMConfig(); // Then load from backend
    };

    fetchOllamaModels();
    fetchSummaryModelConfig();
    fetchToolsConfig();  // Sprint 70 Feature 70.7
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

  // Sprint 70 Feature 70.7: Fetch tools config from backend
  const fetchToolsConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/tools/config`);
      if (response.ok) {
        const data: ToolsConfig = await response.json();
        setToolsConfig(data);
        console.log('Tools config loaded from backend:', data);
      }
    } catch (e) {
      console.error('Failed to fetch tools config:', e);
    }
  };

  // Sprint 70 Feature 70.7: Save tools config to backend
  const handleSaveToolsConfig = async () => {
    setIsSavingToolsConfig(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/tools/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(toolsConfig),
      });

      if (response.ok) {
        const data: ToolsConfig = await response.json();
        setToolsConfig(data);
        setToolsConfigSaveStatus('success');
        console.log('Tools config saved to backend:', data);
        setTimeout(() => setToolsConfigSaveStatus('idle'), 3000);
      } else {
        setToolsConfigSaveStatus('error');
      }
    } catch (e) {
      console.error('Failed to save tools config:', e);
      setToolsConfigSaveStatus('error');
    } finally {
      setIsSavingToolsConfig(false);
    }
  };

  const handleToolsConfigChange = (field: 'enable_chat_tools' | 'enable_research_tools', value: boolean) => {
    setToolsConfig((prev) => ({ ...prev, [field]: value }));
    setToolsConfigSaveStatus('idle');
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

        {/* Sprint 70 Feature 70.7: Tool Use Configuration */}
        <div className="bg-white dark:bg-gray-800 rounded-md shadow-sm p-4 mb-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3 flex items-center gap-1.5">
            <Wrench className="w-4 h-4" />
            Tool Use Configuration
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Enable or disable MCP tool use in different modes. Changes take effect within 60 seconds
            without service restart.
          </p>

          <div className="space-y-3">
            {/* Chat Tools Toggle */}
            <div
              className="border dark:border-gray-700 rounded-md p-3"
              data-testid="chat-tools-toggle"
            >
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Enable Tools in Normal Chat
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Allow MCP tool use (web search, file access) in chat conversations
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={toolsConfig.enable_chat_tools}
                    onChange={(e) =>
                      handleToolsConfigChange('enable_chat_tools', e.target.checked)
                    }
                    className="sr-only peer"
                    data-testid="chat-tools-checkbox"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                </label>
              </div>
            </div>

            {/* Research Tools Toggle */}
            <div
              className="border dark:border-gray-700 rounded-md p-3"
              data-testid="research-tools-toggle"
            >
              <div className="flex justify-between items-center">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    Enable Tools in Deep Research
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Allow MCP tool use in deep research supervisor graph
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={toolsConfig.enable_research_tools}
                    onChange={(e) =>
                      handleToolsConfigChange('enable_research_tools', e.target.checked)
                    }
                    className="sr-only peer"
                    data-testid="research-tools-checkbox"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                </label>
              </div>
            </div>

            {/* Sprint 70 Feature 70.11: Tool Detection Strategy Selector */}
            <div className="border dark:border-gray-700 rounded-md p-3 mt-3">
              <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                Tool Detection Strategy
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Choose how the system detects when to use tools
              </p>

              <div className="space-y-2">
                {/* Markers Strategy */}
                <label className="flex items-center gap-2 p-2 border dark:border-gray-600 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700">
                  <input
                    type="radio"
                    name="tool_detection_strategy"
                    value="markers"
                    checked={toolsConfig.tool_detection_strategy === 'markers'}
                    onChange={(e) => {
                      setToolsConfig(prev => ({ ...prev, tool_detection_strategy: e.target.value }));
                      setToolsConfigSaveStatus('idle');
                    }}
                    className="w-4 h-4 text-blue-600"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Only Markers (Fast, ~0ms)
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Use explicit markers like [TOOL:], [SEARCH:] - fragile but instant
                    </div>
                  </div>
                </label>

                {/* LLM Strategy */}
                <label className="flex items-center gap-2 p-2 border dark:border-gray-600 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700">
                  <input
                    type="radio"
                    name="tool_detection_strategy"
                    value="llm"
                    checked={toolsConfig.tool_detection_strategy === 'llm'}
                    onChange={(e) => {
                      setToolsConfig(prev => ({ ...prev, tool_detection_strategy: e.target.value }));
                      setToolsConfigSaveStatus('idle');
                    }}
                    className="w-4 h-4 text-blue-600"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Only LLM (Smart, +50-200ms)
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      LLM intelligently decides when tools needed - multilingual, context-aware
                    </div>
                  </div>
                </label>

                {/* Hybrid Strategy */}
                <label className="flex items-center gap-2 p-2 border dark:border-gray-600 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700">
                  <input
                    type="radio"
                    name="tool_detection_strategy"
                    value="hybrid"
                    checked={toolsConfig.tool_detection_strategy === 'hybrid'}
                    onChange={(e) => {
                      setToolsConfig(prev => ({ ...prev, tool_detection_strategy: e.target.value }));
                      setToolsConfigSaveStatus('idle');
                    }}
                    className="w-4 h-4 text-blue-600"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      Hybrid (Balanced, 0-200ms)
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      Check markers first, then LLM if action hints present - best of both worlds
                    </div>
                  </div>
                </label>
              </div>
            </div>

            {/* Sprint 70 Feature 70.11: Editable Marker Lists (conditional rendering) */}
            {toolsConfig.tool_detection_strategy !== 'llm' && (
              <>
                {/* Explicit Tool Markers */}
                <div className="border dark:border-gray-700 rounded-md p-3 mt-3">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                    Explicit Tool Markers
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                    Markers that immediately trigger tool use (e.g., [TOOL:], [SEARCH:])
                  </p>

                  <div className="space-y-2">
                    {toolsConfig.explicit_tool_markers.map((marker, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <input
                          type="text"
                          value={marker}
                          onChange={(e) => {
                            const newMarkers = [...toolsConfig.explicit_tool_markers];
                            newMarkers[idx] = e.target.value;
                            setToolsConfig(prev => ({ ...prev, explicit_tool_markers: newMarkers }));
                            setToolsConfigSaveStatus('idle');
                          }}
                          className="flex-1 px-2 py-1 text-sm border dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          placeholder="e.g., [TOOL:"
                        />
                        <button
                          onClick={() => {
                            const newMarkers = toolsConfig.explicit_tool_markers.filter((_, i) => i !== idx);
                            setToolsConfig(prev => ({ ...prev, explicit_tool_markers: newMarkers }));
                            setToolsConfigSaveStatus('idle');
                          }}
                          className="px-2 py-1 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                        >
                          Remove
                        </button>
                      </div>
                    ))}

                    <button
                      onClick={() => {
                        setToolsConfig(prev => ({
                          ...prev,
                          explicit_tool_markers: [...prev.explicit_tool_markers, ''],
                        }));
                        setToolsConfigSaveStatus('idle');
                      }}
                      className="w-full px-2 py-1 text-xs text-blue-600 dark:text-blue-400 border border-blue-600 dark:border-blue-400 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                    >
                      + Add Marker
                    </button>
                  </div>
                </div>

                {/* Action Hint Phrases (only for hybrid mode) */}
                {toolsConfig.tool_detection_strategy === 'hybrid' && (
                  <div className="border dark:border-gray-700 rounded-md p-3 mt-3">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      Action Hint Phrases
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                      Phrases that trigger LLM tool decision (e.g., "need to", "check", "search")
                    </p>

                    <div className="space-y-2">
                      {toolsConfig.action_hint_phrases.map((phrase, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            type="text"
                            value={phrase}
                            onChange={(e) => {
                              const newPhrases = [...toolsConfig.action_hint_phrases];
                              newPhrases[idx] = e.target.value;
                              setToolsConfig(prev => ({ ...prev, action_hint_phrases: newPhrases }));
                              setToolsConfigSaveStatus('idle');
                            }}
                            className="flex-1 px-2 py-1 text-sm border dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                            placeholder="e.g., need to"
                          />
                          <button
                            onClick={() => {
                              const newPhrases = toolsConfig.action_hint_phrases.filter((_, i) => i !== idx);
                              setToolsConfig(prev => ({ ...prev, action_hint_phrases: newPhrases }));
                              setToolsConfigSaveStatus('idle');
                            }}
                            className="px-2 py-1 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                          >
                            Remove
                          </button>
                        </div>
                      ))}

                      <button
                        onClick={() => {
                          setToolsConfig(prev => ({
                            ...prev,
                            action_hint_phrases: [...prev.action_hint_phrases, ''],
                          }));
                          setToolsConfigSaveStatus('idle');
                        }}
                        className="w-full px-2 py-1 text-xs text-blue-600 dark:text-blue-400 border border-blue-600 dark:border-blue-400 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20"
                      >
                        + Add Phrase
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {toolsConfig.updated_at && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
              Last updated: {new Date(toolsConfig.updated_at).toLocaleString()}
            </p>
          )}

          <div className="mt-3 flex gap-2">
            <button
              onClick={handleSaveToolsConfig}
              disabled={isSavingToolsConfig}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              data-testid="save-tools-config-button"
            >
              {isSavingToolsConfig ? (
                <RefreshCw className="w-3 h-3 animate-spin" />
              ) : toolsConfigSaveStatus === 'success' ? (
                <CheckCircle className="w-3 h-3" />
              ) : toolsConfigSaveStatus === 'error' ? (
                <AlertCircle className="w-3 h-3" />
              ) : null}
              {toolsConfigSaveStatus === 'success'
                ? 'Saved!'
                : toolsConfigSaveStatus === 'error'
                ? 'Error'
                : 'Save Tools Configuration'}
            </button>
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
