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
