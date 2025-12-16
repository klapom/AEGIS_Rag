/**
 * Reasoning Types
 * Sprint 46 Feature 46.2: Transparent Reasoning Panel
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
