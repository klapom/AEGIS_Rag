/**
 * Reasoning Types
 * Sprint 46 Feature 46.2: Transparent Reasoning Panel
 * Sprint 48 Feature 48.6: Phase Event Types for Real-Time Thinking Indicator
 *
 * TypeScript interfaces for the reasoning/retrieval chain display
 */

/**
 * Source types for retrieval steps
 */
export type RetrievalSource =
  | 'qdrant'
  | 'bm25'
  | 'neo4j'
  | 'redis'
  | 'rrf_fusion'
  | 'reranker';

/**
 * Intent types for query classification
 */
export type IntentType = 'factual' | 'keyword' | 'exploratory' | 'summary';

/**
 * Individual retrieval step in the chain
 */
export interface RetrievalStep {
  /** Step number in the retrieval sequence (1-based) */
  step: number;
  /** Source system that performed this retrieval */
  source: RetrievalSource;
  /** Duration of this step in milliseconds */
  duration_ms: number;
  /** Number of results returned by this step */
  result_count: number;
  /** Additional details specific to the source type */
  details: RetrievalStepDetails;
}

/**
 * Source-specific details for retrieval steps
 */
export interface RetrievalStepDetails {
  /** Top relevance score (for Qdrant vector search) */
  top_score?: number;
  /** Number of entities found (for Neo4j graph query) */
  entities?: number;
  /** Number of relations traversed (for Neo4j graph query) */
  relations?: number;
  /** Whether memory was found (for Redis memory check) */
  found?: boolean;
  /** Session ID for memory lookup (for Redis) */
  session_id?: string;
  /** Number of merged results (for RRF fusion) */
  merged_count?: number;
  /** Fusion weights used (for RRF fusion) */
  weights?: Record<string, number>;
  /** Query terms used (for BM25 keyword search) */
  query_terms?: string[];
  /** Reranker model used */
  model?: string;
  /** Any additional unstructured details */
  [key: string]: unknown;
}

/**
 * Intent classification information
 */
export interface IntentInfo {
  /** Classified intent type */
  intent: IntentType;
  /** Confidence score (0-1) */
  confidence: number;
  /** Optional reasoning for the classification */
  reasoning?: string;
}

/**
 * Sprint 52: Channel sample result for detailed display
 * Sprint 52: Added keywords, matched_entities, community_id for channel-specific metadata
 */
export interface ChannelSample {
  /** Truncated text content */
  text: string;
  /** Relevance score */
  score: number;
  /** Source document ID */
  document_id: string;
  /** Document title */
  title: string;
  /** BM25: Keywords used for the search */
  keywords?: string[];
  /** Graph Local/Global: Matched entities from the graph */
  matched_entities?: string[];
  /** Graph Global: Community ID */
  community_id?: string | number;
}

/**
 * Sprint 52: 4-Way Hybrid Search Channel Results
 */
export interface FourWayResults {
  /** Vector/embedding search results count */
  vector_count: number;
  /** BM25/keyword search results count */
  bm25_count: number;
  /** Graph local (entity → chunk) results count */
  graph_local_count: number;
  /** Graph global (community → entity → chunk) results count */
  graph_global_count: number;
  /** Total results across all channels */
  total_count?: number;
}

/**
 * Sprint 52: Per-channel sample results for detailed display
 */
export interface ChannelSamples {
  vector: ChannelSample[];
  bm25: ChannelSample[];
  graph_local: ChannelSample[];
  graph_global: ChannelSample[];
}

/**
 * Sprint 52: Intent weights for 4-way channels
 */
export interface IntentWeights {
  vector: number;
  bm25: number;
  local: number;
  global: number;
}

/**
 * Complete reasoning data for a response
 * Sprint 51: Added phaseEvents for persistent phase display after answer
 * Sprint 52: Added 4-way search metadata for expandable UI display
 * Sprint 63: Added tool_steps for tool execution visualization
 */
export interface ReasoningData {
  /** Intent classification for the query */
  intent: IntentInfo;
  /** Ordered list of retrieval steps */
  retrieval_steps: RetrievalStep[];
  /** List of tools that were invoked */
  tools_used: string[];
  /** Total processing time in milliseconds */
  total_duration_ms?: number;
  /** Sprint 51: Phase events from the thinking process (optional, for display after answer) */
  phase_events?: PhaseEvent[];
  /** Sprint 52: 4-way channel results */
  four_way_results?: FourWayResults;
  /** Sprint 52: Intent-based weights used for RRF fusion */
  intent_weights?: IntentWeights;
  /** Sprint 52: Method used for intent classification (llm or rule-based) */
  intent_method?: string;
  /** Sprint 52: Latency of intent classification in ms */
  intent_latency_ms?: number;
  /** Sprint 52: Per-channel sample results for detailed display */
  channel_samples?: ChannelSamples;
  /** Sprint 63: Tool execution steps for visualization */
  tool_steps?: ToolExecutionStep[];
}

/**
 * Props for the ReasoningPanel component
 */
export interface ReasoningPanelProps {
  /** Reasoning data to display */
  data: ReasoningData | null;
  /** Whether the panel is initially expanded */
  defaultExpanded?: boolean;
  /** Callback when panel expansion state changes */
  onToggle?: (expanded: boolean) => void;
}

/**
 * Props for the RetrievalStep component
 */
export interface RetrievalStepProps {
  /** The retrieval step data to display */
  step: RetrievalStep;
  /** Whether this is the last step (for styling) */
  isLast?: boolean;
}

/**
 * Sprint 48 Feature 48.6: Phase Event Types
 * Represents a phase event from the SSE stream for real-time thinking indicator
 */

/**
 * Phase type enumeration matching backend phase types
 */
export type PhaseType =
  | 'intent_classification'
  | 'vector_search'
  | 'bm25_search'
  | 'rrf_fusion'
  | 'reranking'
  | 'graph_query'
  | 'memory_retrieval'
  | 'llm_generation'
  | 'follow_up_questions';

/**
 * Phase status enumeration
 */
export type PhaseStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';

/**
 * Phase event data from SSE stream
 */
export interface PhaseEvent {
  /** Type of phase being processed */
  phase_type: PhaseType;
  /** Current status of the phase */
  status: PhaseStatus;
  /** ISO timestamp when phase started */
  start_time: string;
  /** ISO timestamp when phase ended (only for completed/failed/skipped) */
  end_time?: string;
  /** Duration in milliseconds (only for completed phases) */
  duration_ms?: number;
  /** Additional metadata specific to the phase */
  metadata?: Record<string, unknown>;
  /** Error message if phase failed */
  error?: string;
}

/**
 * Human-readable phase names in German
 */
export const PHASE_NAMES: Record<PhaseType, string> = {
  intent_classification: 'Intent analysieren',
  vector_search: 'Vektor-Suche',
  bm25_search: 'BM25-Suche',
  rrf_fusion: 'Ergebnisse fusionieren',
  reranking: 'Reranking',
  graph_query: 'Graph durchsuchen',
  memory_retrieval: 'Erinnerungen abrufen',
  llm_generation: 'Antwort generieren',
  follow_up_questions: 'Fragen vorschlagen',
};

/**
 * Sprint 51 Feature 51.1: Dynamic Phase State
 * Track phases dynamically based on backend events rather than hardcoded count.
 * The backend determines the actual phases for each query (some phases may be skipped).
 */
export interface PhaseState {
  /** List of phases received from backend */
  phases: PhaseEvent[];
  /** Number of completed phases */
  completedCount: number;
  /** Total number of phases (determined dynamically by backend) */
  totalCount: number;
}

/**
 * Sprint 63 Feature 63.10: Tool Execution Types
 * Types for displaying tool execution results (bash, python) in Chat UI
 */

/**
 * Tool name types for tool execution
 */
export type ToolName = 'bash' | 'python' | string;

/**
 * Input data for tool execution
 */
export interface ToolExecutionInput {
  /** Shell command for bash tool */
  command?: string;
  /** Python code for python tool */
  code?: string;
  /** Generic arguments for other tools */
  arguments?: Record<string, unknown>;
}

/**
 * Output data from tool execution
 */
export interface ToolExecutionOutput {
  /** Standard output from the tool */
  stdout?: string;
  /** Standard error from the tool */
  stderr?: string;
  /** Exit code (0 = success, non-zero = error) */
  exit_code?: number;
  /** Whether the execution was successful */
  success: boolean;
  /** Error message if execution failed */
  error?: string;
}

/**
 * Individual tool execution step
 */
export interface ToolExecutionStep {
  /** Name of the tool executed (bash, python, etc.) */
  tool_name: ToolName;
  /** Server/environment where the tool was executed */
  server: string;
  /** Input data passed to the tool */
  input: ToolExecutionInput;
  /** Output data from the tool execution */
  output: ToolExecutionOutput;
  /** Duration of execution in milliseconds */
  duration_ms?: number;
  /** ISO timestamp when the tool was executed */
  timestamp: string;
}

/**
 * Props for ToolExecutionDisplay component
 */
export interface ToolExecutionDisplayProps {
  /** The tool execution step to display */
  step: ToolExecutionStep;
}
