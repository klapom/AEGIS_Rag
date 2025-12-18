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
 * Complete reasoning data for a response
 * Sprint 51: Added phaseEvents for persistent phase display after answer
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
