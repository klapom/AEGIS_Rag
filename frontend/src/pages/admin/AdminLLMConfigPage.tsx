/**
 * AdminLLMConfigPage Component
 * Sprint 36 Feature 36.3: Model Selection per Use Case (8 SP)
 *
 * Features:
 * - Configure LLM models for each use case
 * - Support for Ollama (local), Alibaba Cloud, and OpenAI providers
 * - localStorage persistence (Phase 1)
 * - Responsive design with dark mode support
 */

import { useState, useEffect } from 'react';
import { Settings, RefreshCw, CheckCircle, AlertCircle, Cpu } from 'lucide-react';

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

// ============================================================================
// Default Model Options
// ============================================================================

const defaultModelOptions: ModelOption[] = [
  // Ollama (Local)
  {
    id: 'ollama/qwen3:32b',
    provider: 'ollama',
    name: 'Qwen3 32B (Local)',
    description: '32B params, local inference, $0 cost',
    capabilities: ['text'],
  },
  {
    id: 'ollama/qwen3-vl:32b',
    provider: 'ollama',
    name: 'Qwen3-VL 32B (Local)',
    description: '32B params, vision, local',
    capabilities: ['text', 'vision'],
  },
  {
    id: 'ollama/llama3.2:8b',
    provider: 'ollama',
    name: 'Llama 3.2 8B (Local)',
    description: '8B params, fast, local',
    capabilities: ['text'],
  },
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

// ============================================================================
// Main Component
// ============================================================================

export function AdminLLMConfigPage() {
  const [config, setConfig] = useState<UseCaseConfig[]>(defaultConfig);
  const [modelOptions] = useState<ModelOption[]>(defaultModelOptions);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load config from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(LLM_CONFIG_KEY);
    if (stored) {
      try {
        setConfig(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to parse stored LLM config:', e);
      }
    }
  }, []);

  const handleModelChange = (useCase: UseCaseType, modelId: string) => {
    setConfig((prev) =>
      prev.map((c) => (c.useCase === useCase ? { ...c, modelId } : c))
    );
    setSaveStatus('idle');
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Save to localStorage
      localStorage.setItem(LLM_CONFIG_KEY, JSON.stringify(config));

      // TODO: Also save to backend API
      // await fetch('/api/v1/admin/llm/config', {
      //   method: 'PUT',
      //   body: JSON.stringify({ useCases: config }),
      // });

      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (e) {
      console.error('Failed to save config:', e);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRefreshModels = async () => {
    setIsRefreshing(true);
    try {
      // TODO: Fetch available models from backend
      // const response = await fetch('/api/v1/admin/llm/models');
      // const models = await response.json();
      // setModelOptions(models);
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulated delay
    } finally {
      setIsRefreshing(false);
    }
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
