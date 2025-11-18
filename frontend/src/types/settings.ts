/**
 * Settings Types
 * Sprint 28 Feature 28.3: User settings and preferences
 */

export type Theme = 'light' | 'dark' | 'auto';
export type Language = 'de' | 'en';
export type CloudProvider = 'local' | 'alibaba' | 'openai';

export interface UserSettings {
  // General Settings
  theme: Theme;
  language: Language;
  autoSaveConversations: boolean;

  // Model Settings
  ollamaBaseUrl: string;
  defaultModel: string;
  cloudProvider: CloudProvider;
  cloudApiKey?: string;

  // Advanced Settings
  enableDebugMode?: boolean;
  maxTokens?: number;
  temperature?: number;
}

export const DEFAULT_SETTINGS: UserSettings = {
  // General
  theme: 'auto',
  language: 'de',
  autoSaveConversations: true,

  // Models
  ollamaBaseUrl: 'http://localhost:11434',
  defaultModel: 'llama3.2:3b',
  cloudProvider: 'local',

  // Advanced
  enableDebugMode: false,
  maxTokens: 2048,
  temperature: 0.7,
};

export const AVAILABLE_MODELS = [
  'llama3.2:3b',
  'llama3.2:8b',
  'gemma-3-4b-it-Q8_0',
  'llava:7b-v1.6-mistral-q2_K',
] as const;

export const CLOUD_PROVIDERS = [
  { value: 'local', label: 'Local (Ollama)', requiresApiKey: false },
  { value: 'alibaba', label: 'Alibaba Cloud', requiresApiKey: true },
  { value: 'openai', label: 'OpenAI', requiresApiKey: true },
] as const;
