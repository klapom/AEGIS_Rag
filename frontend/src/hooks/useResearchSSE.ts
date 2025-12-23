/**
 * useResearchSSE Hook
 * Sprint 63 Feature 63.8: Full Research UI with Progress Tracking
 *
 * Custom hook for managing Research Mode SSE streaming with real-time
 * progress tracking, state management, and localStorage persistence.
 *
 * Features:
 * - SSE connection to /api/v1/research/query
 * - Real-time progress event handling
 * - Research Mode toggle with localStorage persistence
 * - AbortController support for cleanup and cancellation
 * - Error handling and timeout management
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamResearch } from '../api/research';
import type {
  ResearchState,
  UseResearchSSEReturn,
  ResearchPhase,
  ResearchProgress,
  ResearchQueryResponse,
  ResearchSource,
} from '../types/research';

/**
 * Timeout configuration for research
 */
export const RESEARCH_TIMEOUT_CONFIG = {
  /** Total timeout in milliseconds (3 minutes) */
  TIMEOUT_MS: 180000,
  /** Warning threshold in milliseconds (2 minutes) */
  WARNING_THRESHOLD_MS: 120000,
} as const;


/**
 * Load Research Mode preference from localStorage
 */
function loadResearchModePreference(): boolean {
  try {
    const stored = localStorage.getItem('aegisrag-research-mode-enabled');
    return stored === 'true';
  } catch {
    return false;
  }
}

/**
 * Save Research Mode preference to localStorage
 */
function saveResearchModePreference(enabled: boolean): void {
  try {
    localStorage.setItem('aegisrag-research-mode-enabled', String(enabled));
  } catch {
    // Ignore localStorage errors
  }
}

/**
 * Hook for managing Research Mode SSE streaming
 *
 * @returns Research state and control functions
 */
export function useResearchSSE(): UseResearchSSEReturn {
  // Initialize Research Mode from localStorage
  const [isResearchMode, setIsResearchMode] = useState<boolean>(loadResearchModePreference);
  const [isResearching, setIsResearching] = useState<boolean>(false);
  const [currentPhase, setCurrentPhase] = useState<ResearchPhase | null>(null);
  const [progress, setProgress] = useState<ResearchProgress[]>([]);
  const [synthesis, setSynthesis] = useState<string | null>(null);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [researchPlan, setResearchPlan] = useState<string[]>([]);
  const [qualityMetrics, setQualityMetrics] = useState<ResearchState['qualityMetrics']>({
    iterations: 0,
    totalSources: 0,
    webSources: 0,
  });
  const [error, setError] = useState<string | null>(null);

  // Refs for cleanup and abort handling
  const abortControllerRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Clear timeout
   */
  const clearTimeoutRef = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  /**
   * Toggle Research Mode on/off
   */
  const toggleResearchMode = useCallback(() => {
    setIsResearchMode((prev) => {
      const newValue = !prev;
      saveResearchModePreference(newValue);
      return newValue;
    });
  }, []);

  /**
   * Reset research state to defaults
   */
  const resetResearch = useCallback(() => {
    setIsResearching(false);
    setCurrentPhase(null);
    setProgress([]);
    setSynthesis(null);
    setSources([]);
    setResearchPlan([]);
    setQualityMetrics({
      iterations: 0,
      totalSources: 0,
      webSources: 0,
    });
    setError(null);
    clearTimeoutRef();
  }, [clearTimeoutRef]);

  /**
   * Cancel the current research
   */
  const cancelResearch = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsResearching(false);
    setCurrentPhase(null);
    clearTimeoutRef();
  }, [clearTimeoutRef]);

  /**
   * Handle progress chunk from SSE stream
   */
  const handleProgressChunk = useCallback((progressData: ResearchProgress) => {
    setCurrentPhase(progressData.phase);
    setProgress((prev) => [...prev, progressData]);

    // Update research plan if available
    if (progressData.phase === 'plan' && progressData.metadata.plan_steps) {
      setResearchPlan(progressData.metadata.plan_steps);
    } else if (progressData.phase === 'plan' && progressData.metadata.num_queries) {
      // Plan steps might be in a different format
      const numQueries = progressData.metadata.num_queries;
      if (typeof numQueries === 'number' && numQueries > 0) {
        // Placeholder for plan steps until we get actual content
        setResearchPlan((prev) =>
          prev.length === 0
            ? Array.from({ length: numQueries }, (_, i) => `Search query ${i + 1}`)
            : prev
        );
      }
    }

    // Update quality metrics from evaluate phase
    if (progressData.phase === 'evaluate') {
      setQualityMetrics((prev) => ({
        ...prev,
        coverage: progressData.metadata.coverage,
        diversity: progressData.metadata.diversity,
        completeness: progressData.metadata.completeness,
        overall_score: progressData.metadata.quality_score,
      }));
    }
  }, []);

  /**
   * Handle result chunk from SSE stream
   */
  const handleResultChunk = useCallback((result: ResearchQueryResponse) => {
    setSynthesis(result.synthesis);
    setSources(result.sources);
    setResearchPlan(result.research_plan);
    setQualityMetrics((prev) => ({
      ...prev,
      iterations: result.iterations,
      totalSources: result.sources.length,
      webSources: result.sources.filter((s) => s.source_type === 'web').length,
      ...result.quality_metrics,
    }));
    setCurrentPhase('complete');
    setIsResearching(false);
    clearTimeoutRef();
  }, [clearTimeoutRef]);

  /**
   * Start a new research query
   */
  const startResearch = useCallback(
    async (query: string, namespace?: string, maxIterations?: number) => {
      // Reset state
      resetResearch();
      setIsResearching(true);
      setError(null);

      // Create new abort controller
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // Set timeout
      timeoutRef.current = setTimeout(() => {
        abortController.abort();
        setError('Research timeout: Die Verarbeitung dauerte zu lange.');
        setIsResearching(false);
      }, RESEARCH_TIMEOUT_CONFIG.TIMEOUT_MS);

      try {
        for await (const chunk of streamResearch(
          {
            query,
            namespace,
            max_iterations: maxIterations,
          },
          abortController.signal
        )) {
          // Handle chunk based on type
          switch (chunk.type) {
            case 'progress':
              if (chunk.data) {
                handleProgressChunk(chunk.data as ResearchProgress);
              }
              break;

            case 'result':
              if (chunk.data) {
                handleResultChunk(chunk.data as ResearchQueryResponse);
              }
              break;

            case 'error':
              setError(chunk.error || 'Unknown research error');
              setIsResearching(false);
              clearTimeoutRef();
              break;

            case 'done':
              setIsResearching(false);
              setCurrentPhase('complete');
              clearTimeoutRef();
              break;
          }
        }
      } catch (err) {
        // Ignore abort errors
        const isAbortError =
          (err instanceof Error && err.name === 'AbortError') ||
          (err instanceof DOMException && err.name === 'AbortError');

        if (!isAbortError) {
          console.error('Research streaming error:', err);
          setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten');
        }

        setIsResearching(false);
        clearTimeoutRef();
      }
    },
    [resetResearch, handleProgressChunk, handleResultChunk, clearTimeoutRef]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      clearTimeoutRef();
    };
  }, [clearTimeoutRef]);

  return {
    // State
    isResearchMode,
    isResearching,
    currentPhase,
    progress,
    synthesis,
    sources,
    researchPlan,
    qualityMetrics,
    error,
    // Actions
    startResearch,
    cancelResearch,
    resetResearch,
    toggleResearchMode,
  };
}
