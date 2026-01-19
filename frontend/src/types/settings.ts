/**
 * Settings Types
 * Sprint 28 Feature 28.3: User settings and preferences
 */

export type Theme = 'light' | 'dark' | 'auto';
export type Language = 'de' | 'en';
export type CloudProvider = 'local' | 'alibaba' | 'openai';
export type RetrievalMethod = 'hybrid' | 'vector' | 'bm25';

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

  // Retrieval Settings (Sprint 74 Feature 74.3)
  retrievalMethod: RetrievalMethod;

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

  // Models (Sprint 112: Updated to match actual deployment)
  ollamaBaseUrl: 'http://localhost:11434',
  defaultModel: 'nemotron-3-nano',
  cloudProvider: 'local',

  // Retrieval (Sprint 74 Feature 74.3)
  retrievalMethod: 'hybrid',

  // Advanced
  enableDebugMode: false,
  maxTokens: 2048,
  temperature: 0.7,
};

/**
 * Available LLM models
 * Sprint 112: Updated to match actual deployed models from llm_config.yml
 */
export const AVAILABLE_MODELS = [
  'nemotron-3-nano',    // DGX Spark: NVIDIA Nemotron 3 Nano 30B-3A (Primary)
  'qwen3:32b',          // Ollama: Qwen 3 32B (Fallback)
  'gpt-oss:20b',        // Ollama: GPT-OSS 20B (Fast extraction)
  'qwen-turbo',         // Alibaba Cloud: Qwen Turbo
  'qwen-plus',          // Alibaba Cloud: Qwen Plus
  'gpt-4o',             // OpenAI: GPT-4o (Premium)
] as const;

/**
 * System LLM Capability Mapping
 * Sprint 112: Shows which LLMs are used for TOP 3 system capabilities
 */
export interface LLMCapability {
  name: string;
  description: string;
  model: string;
  provider: string;
  icon: 'chat' | 'graph' | 'search';
}

export const SYSTEM_LLM_CAPABILITIES: LLMCapability[] = [
  {
    name: 'Textgenerierung',
    description: 'Chat-Antworten, Zusammenfassungen, Analysen',
    model: 'Nemotron 3 Nano (30B)',
    provider: 'DGX Spark / Ollama',
    icon: 'chat',
  },
  {
    name: 'Entity-Extraktion',
    description: 'Wissensgraph: Entitäten & Relationen',
    model: '3-Rank Cascade',
    provider: 'Nemotron → GPT-OSS → SpaCy',
    icon: 'graph',
  },
  {
    name: 'Semantische Suche',
    description: 'Vektorsuche mit Dense + Sparse Embeddings',
    model: 'BGE-M3 (1024D)',
    provider: 'FlagEmbedding / Qdrant',
    icon: 'search',
  },
];

export const CLOUD_PROVIDERS = [
  { value: 'local', label: 'Local (Ollama)', requiresApiKey: false },
  { value: 'alibaba', label: 'Alibaba Cloud', requiresApiKey: true },
  { value: 'openai', label: 'OpenAI', requiresApiKey: true },
] as const;

export const RETRIEVAL_METHODS = [
  {
    value: 'hybrid',
    label: 'Hybrid (Vector + Sparse)',
    description: 'Best overall: Combines semantic search and lexical matching using RRF fusion',
  },
  {
    value: 'vector',
    label: 'Vector (Semantic)',
    description: 'Best for conceptual queries: Uses BGE-M3 embeddings for semantic similarity',
  },
  {
    value: 'bm25',
    label: 'Sparse (Lexikalisch)',
    description: 'Best for exact matches: BGE-M3 learned lexical weights for specific terms/numbers',
  },
] as const;

/**
 * Graph Expansion Configuration
 * Sprint 79 Feature 79.6: UI Settings for Graph Expansion
 *
 * Controls the 3-Stage Semantic Search behavior:
 * - Stage 1: LLM entity extraction
 * - Stage 2: Graph N-hop traversal
 * - Stage 3: LLM synonym fallback
 * - Stage 4: BGE-M3 semantic reranking
 */
export interface GraphExpansionConfig {
  /** Enable/disable graph expansion feature */
  enabled: boolean;
  /** Number of hops for graph traversal (1-3) */
  graphExpansionHops: number;
  /** Minimum entities before LLM synonym fallback (5-20) */
  minEntitiesThreshold: number;
  /** Maximum synonyms to generate per entity (1-5) */
  maxSynonymsPerEntity: number;
}

/**
 * Default graph expansion settings
 * Values match backend defaults in src/core/config.py
 */
export const DEFAULT_GRAPH_EXPANSION_CONFIG: GraphExpansionConfig = {
  enabled: true,
  graphExpansionHops: 1,
  minEntitiesThreshold: 10,
  maxSynonymsPerEntity: 3,
};

/**
 * localStorage key for graph expansion settings
 */
export const GRAPH_EXPANSION_STORAGE_KEY = 'aegis_graph_expansion_settings';
