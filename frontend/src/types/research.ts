/**
 * Research Mode Types
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 *
 * TypeScript interfaces for the Research Mode feature with real-time
 * progress tracking via SSE.
 */

/**
 * Research phase types matching backend phases
 */
export type ResearchPhase = 'start' | 'plan' | 'search' | 'evaluate' | 'synthesize' | 'complete';

/**
 * Research phase status
 */
export type ResearchPhaseStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/**
 * Progress event received from SSE stream
 * Matches backend ResearchProgress model
 */
export interface ResearchProgress {
  /** Current research phase */
  phase: ResearchPhase;
  /** Human-readable progress message */
  message: string;
  /** Current iteration number (1-based) */
  iteration: number;
  /** Phase-specific metadata */
  metadata: {
    /** Number of queries in the research plan (plan phase) */
    num_queries?: number;
    /** Number of sources found (search/synthesize phases) */
    sources_found?: number;
    /** Number of results available (synthesize phase) */
    num_results?: number;
    /** Quality score from evaluation (evaluate phase) */
    quality_score?: number;
    /** Detailed plan steps (plan phase) */
    plan_steps?: string[];
    /** Query being processed */
    query?: string;
    /** Namespace being searched */
    namespace?: string;
    /** Coverage score (evaluate phase) */
    coverage?: number;
    /** Diversity score (evaluate phase) */
    diversity?: number;
    /** Completeness score (evaluate phase) */
    completeness?: number;
    /** Additional metadata fields */
    [key: string]: unknown;
  };
}

/**
 * Source document from research results
 * Matches backend Source model
 */
export interface ResearchSource {
  /** Source text content */
  text: string;
  /** Relevance score (0-1) */
  score: number;
  /** Source type (vector, graph, web) */
  source_type: string;
  /** Additional metadata */
  metadata: Record<string, unknown>;
  /** Extracted entities */
  entities: string[];
  /** Extracted relationships */
  relationships: string[];
}

/**
 * Complete research response
 * Matches backend ResearchQueryResponse model
 */
export interface ResearchQueryResponse {
  /** Original research question */
  query: string;
  /** Synthesized research answer */
  synthesis: string;
  /** Source documents used */
  sources: ResearchSource[];
  /** Number of search iterations performed */
  iterations: number;
  /** Quality metrics from evaluation */
  quality_metrics: {
    coverage?: number;
    diversity?: number;
    completeness?: number;
    overall_score?: number;
    [key: string]: unknown;
  };
  /** List of search queries executed */
  research_plan: string[];
}

/**
 * Research request configuration
 * Matches backend ResearchQueryRequest model
 */
export interface ResearchQueryRequest {
  /** Research question */
  query: string;
  /** Namespace to search in */
  namespace?: string;
  /** Maximum search iterations (1-5) */
  max_iterations?: number;
  /** Enable SSE streaming */
  stream?: boolean;
}

/**
 * Research state for UI management
 * Tracks the complete state of a research session
 */
export interface ResearchState {
  /** Whether Research Mode is enabled */
  isResearchMode: boolean;
  /** Whether research is currently in progress */
  isResearching: boolean;
  /** Current research phase */
  currentPhase: ResearchPhase | null;
  /** List of all progress events received */
  progress: ResearchProgress[];
  /** Final synthesis result */
  synthesis: string | null;
  /** All sources from research */
  sources: ResearchSource[];
  /** Research plan steps */
  researchPlan: string[];
  /** Quality metrics from evaluation */
  qualityMetrics: {
    iterations: number;
    totalSources: number;
    webSources: number;
    coverage?: number;
    diversity?: number;
    completeness?: number;
    overall_score?: number;
  };
  /** Error message if research failed */
  error: string | null;
}

/**
 * Hook return type for useResearchSSE
 */
export interface UseResearchSSEReturn extends ResearchState {
  /** Start a new research query */
  startResearch: (query: string, namespace?: string, maxIterations?: number) => void;
  /** Cancel the current research */
  cancelResearch: () => void;
  /** Reset research state */
  resetResearch: () => void;
  /** Toggle Research Mode on/off */
  toggleResearchMode: () => void;
}

/**
 * Props for ResearchProgressTracker component
 */
export interface ResearchProgressTrackerProps {
  /** List of progress events to display */
  progress: ResearchProgress[];
  /** Current phase being processed */
  currentPhase: ResearchPhase | null;
  /** Whether research is in progress */
  isResearching: boolean;
  /** Error message if any */
  error: string | null;
  /** Optional callback when a phase is clicked (for expansion) */
  onPhaseClick?: (phase: ResearchPhase) => void;
}

/**
 * Props for ResearchModeToggle component
 */
export interface ResearchModeToggleProps {
  /** Whether Research Mode is enabled */
  isEnabled: boolean;
  /** Callback when toggle is clicked */
  onToggle: () => void;
  /** Optional className for styling */
  className?: string;
  /** Whether toggle is disabled */
  disabled?: boolean;
}

/**
 * Props for ResearchResponseDisplay component
 */
export interface ResearchResponseDisplayProps {
  /** Synthesis text to display */
  synthesis: string | null;
  /** Research sources */
  sources: ResearchSource[];
  /** Research plan steps */
  researchPlan: string[];
  /** Quality metrics */
  qualityMetrics: ResearchState['qualityMetrics'];
  /** Whether response is loading */
  isLoading: boolean;
}

/**
 * Human-readable phase names in German
 */
export const RESEARCH_PHASE_NAMES: Record<ResearchPhase, string> = {
  start: 'Recherche starten',
  plan: 'Plan erstellen',
  search: 'Quellen durchsuchen',
  evaluate: 'Ergebnisse bewerten',
  synthesize: 'Zusammenfassung erstellen',
  complete: 'Abgeschlossen',
};

/**
 * Phase descriptions in German
 */
export const RESEARCH_PHASE_DESCRIPTIONS: Record<ResearchPhase, string> = {
  start: 'Initialisiere Recherche-Workflow',
  plan: 'Erstelle Suchstrategie und Abfragen',
  search: 'Durchsuche Vector- und Graph-Stores',
  evaluate: 'Bewerte Qualitaet und Vollstaendigkeit',
  synthesize: 'Erstelle umfassende Zusammenfassung',
  complete: 'Recherche erfolgreich abgeschlossen',
};

/**
 * Default research state
 */
export const DEFAULT_RESEARCH_STATE: ResearchState = {
  isResearchMode: false,
  isResearching: false,
  currentPhase: null,
  progress: [],
  synthesis: null,
  sources: [],
  researchPlan: [],
  qualityMetrics: {
    iterations: 0,
    totalSources: 0,
    webSources: 0,
  },
  error: null,
};

/**
 * LocalStorage key for Research Mode persistence
 */
export const RESEARCH_MODE_STORAGE_KEY = 'aegisrag-research-mode-enabled';

/**
 * Sprint 116.10: Deep Research Multi-Step Types
 */

/**
 * Deep research status values
 */
export type DeepResearchStatusValue =
  | 'pending'
  | 'decomposing'
  | 'retrieving'
  | 'analyzing'
  | 'synthesizing'
  | 'complete'
  | 'error'
  | 'cancelled';

/**
 * Execution step in deep research workflow
 * Matches backend ExecutionStepModel
 */
export interface ExecutionStep {
  /** Name of the step */
  step_name: string;
  /** Step start time (ISO 8601) */
  started_at: string;
  /** Step completion time (ISO 8601) */
  completed_at: string | null;
  /** Duration in milliseconds */
  duration_ms: number | null;
  /** Step status */
  status: 'running' | 'completed' | 'failed';
  /** Step result data */
  result: Record<string, unknown>;
  /** Error message if failed */
  error: string | null;
}

/**
 * Source document (alias for compatibility)
 * Matches backend Source model
 */
export interface Source {
  /** Source text content */
  text: string;
  /** Relevance score (0-1) */
  score: number;
  /** Source type (vector, graph) */
  source_type: string;
  /** Additional metadata */
  metadata: Record<string, unknown>;
  /** Extracted entities */
  entities: string[];
  /** Extracted relationships */
  relationships: string[];
}

/**
 * Intermediate answer for a sub-question
 * Matches backend IntermediateAnswer model
 */
export interface IntermediateAnswer {
  /** Sub-question being answered */
  sub_question: string;
  /** Intermediate answer */
  answer: string;
  /** Number of contexts used */
  contexts_count: number;
  /** Sources used for this sub-question */
  sources: Source[];
  /** Confidence score (0-1) */
  confidence: number;
}

/**
 * Deep research response
 * Matches backend DeepResearchResponse model
 */
export interface DeepResearchResponse {
  /** Unique research ID */
  id: string;
  /** Original research question */
  query: string;
  /** Current status */
  status: DeepResearchStatusValue;
  /** Generated sub-questions */
  sub_questions: string[];
  /** Intermediate answers for sub-questions */
  intermediate_answers: IntermediateAnswer[];
  /** Final synthesized answer */
  final_answer: string;
  /** All sources used */
  sources: Source[];
  /** Execution step history */
  execution_steps: ExecutionStep[];
  /** Total execution time in milliseconds */
  total_time_ms: number;
  /** Creation timestamp (ISO 8601) */
  created_at: string;
  /** Completion timestamp (ISO 8601) */
  completed_at: string | null;
  /** Error message if failed */
  error: string | null;
}

/**
 * Deep research status response
 * Matches backend DeepResearchStatusResponse model
 */
export interface DeepResearchStatus {
  /** Research ID */
  id: string;
  /** Current status */
  status: DeepResearchStatusValue;
  /** Current step name */
  current_step: string;
  /** Progress percentage (0-100) */
  progress_percent: number;
  /** Estimated time remaining in milliseconds */
  estimated_time_remaining_ms: number | null;
  /** Completed execution steps */
  execution_steps: ExecutionStep[];
}
