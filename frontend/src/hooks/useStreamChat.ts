/**
 * useStreamChat Hook
 * Sprint 46: Extracted streaming logic from StreamingAnswer component
 * Sprint 47: Fixed infinite re-render loop (Maximum update depth exceeded)
 * Sprint 48 Feature 48.6: Phase event handling for real-time thinking indicator
 * Sprint 48 Feature 48.10: Request timeout and cancel functionality
 *
 * This hook manages SSE streaming for chat responses and returns
 * state that can be used with ConversationView.
 *
 * Features:
 * - Token-by-token streaming
 * - Source collection
 * - Metadata extraction (session_id, intent, citations)
 * - Error handling
 * - AbortController support for cleanup
 * - Phase event tracking (Sprint 48)
 * - Timeout warning and auto-cancel (Sprint 48)
 *
 * Bug Fix (Sprint 47):
 * - Use refs for callbacks to prevent dependency array changes
 * - Capture final state with refs before calling onComplete
 * - Remove unstable callbacks from useEffect dependency arrays
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { streamChat, type ChatChunk } from '../api/chat';
import type { Source } from '../types/chat';
import type { ReasoningData, IntentType, RetrievalStep as RetrievalStepType, PhaseEvent, PhaseType } from '../types/reasoning';

/**
 * Sprint 48 Feature 48.10: Timeout configuration
 */
export const TIMEOUT_CONFIG = {
  /** Warning threshold in milliseconds (30 seconds) */
  WARNING_THRESHOLD_MS: 30000,
  /** Auto-cancel timeout in milliseconds (90 seconds) */
  TIMEOUT_MS: 90000,
} as const;

/**
 * Streaming state returned by the hook
 */
export interface StreamingState {
  /** Accumulated answer text */
  answer: string;
  /** Collected sources */
  sources: Source[];
  /** Whether currently streaming */
  isStreaming: boolean;
  /** Error message if any */
  error: string | null;
  /** Intent classification */
  intent: string;
  /** Session ID from the response */
  sessionId: string | undefined;
  /** Citation map from metadata */
  citationMap: Record<number, Source> | null;
  /** Reasoning data for ReasoningPanel */
  reasoningData: ReasoningData | null;
  /** Metadata from the response */
  metadata: Record<string, unknown> | null;
  /** Sprint 48: Current phase being processed */
  currentPhase: PhaseType | null;
  /** Sprint 48: List of all phase events received */
  phaseEvents: PhaseEvent[];
  /** Sprint 48: Whether timeout warning should be shown */
  showTimeoutWarning: boolean;
  /** Sprint 48: Function to cancel the current request */
  cancelRequest: () => void;
}

interface UseStreamChatOptions {
  /** Query to send */
  query: string | null;
  /** Search mode (hybrid, vector, graph, memory) */
  mode: string;
  /** Optional namespace filter */
  namespaces?: string[];
  /** Optional existing session ID */
  sessionId?: string;
  /** Callback when session ID is received */
  onSessionIdReceived?: (sessionId: string) => void;
  /** Callback when streaming completes */
  onComplete?: (answer: string, sources: Source[], reasoningData: ReasoningData | null) => void;
}

/**
 * Hook for managing SSE chat streaming
 *
 * Sprint 47 Fix: Use refs for callbacks to avoid infinite re-render loops.
 * Callbacks passed as props often get recreated on every render, which would
 * cause useEffect to re-run, triggering state updates, causing re-renders,
 * creating new callback references, and so on (infinite loop).
 */
export function useStreamChat({
  query,
  mode,
  namespaces,
  sessionId: initialSessionId,
  onSessionIdReceived,
  onComplete,
}: UseStreamChatOptions): StreamingState {
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState('');
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const [citationMap, setCitationMap] = useState<Record<number, Source> | null>(null);
  const [metadata, setMetadata] = useState<Record<string, unknown> | null>(null);
  const [reasoningData, setReasoningData] = useState<ReasoningData | null>(null);

  // Sprint 48 Feature 48.6: Phase event state
  const [currentPhase, setCurrentPhase] = useState<PhaseType | null>(null);
  const [phaseEvents, setPhaseEvents] = useState<PhaseEvent[]>([]);

  // Sprint 48 Feature 48.10: Timeout state
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false);

  const hasCalledOnComplete = useRef(false);
  const currentReasoningData = useRef<ReasoningData | null>(null);

  // Sprint 48 Feature 48.10: Refs for timeout/cancel management
  const abortControllerRef = useRef<AbortController | null>(null);
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timeoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sprint 47 Fix: Store callbacks in refs to avoid triggering useEffect on every render
  // This prevents the infinite re-render loop caused by unstable callback references
  const onSessionIdReceivedRef = useRef(onSessionIdReceived);
  const onCompleteRef = useRef(onComplete);

  // Keep refs in sync with latest callback values
  useEffect(() => {
    onSessionIdReceivedRef.current = onSessionIdReceived;
  }, [onSessionIdReceived]);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Sprint 47 Fix: Store final answer and sources in refs for onComplete callback
  // This ensures we capture the final state when streaming completes
  const finalAnswerRef = useRef('');
  const finalSourcesRef = useRef<Source[]>([]);
  // Sprint 51 Fix: Track final phase events for onComplete callback
  const finalPhaseEventsRef = useRef<PhaseEvent[]>([]);

  /**
   * Sprint 48 Feature 48.10: Clear all timers
   */
  const clearTimers = useCallback(() => {
    if (warningTimerRef.current) {
      clearTimeout(warningTimerRef.current);
      warningTimerRef.current = null;
    }
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current);
      timeoutTimerRef.current = null;
    }
  }, []);

  /**
   * Sprint 48 Feature 48.10: Cancel the current request
   */
  const cancelRequest = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
    setShowTimeoutWarning(false);
    setCurrentPhase(null);
    clearTimers();
  }, [clearTimers]);

  // Handle SSE streaming
  // Sprint 47 Fix: Remove onSessionIdReceived from dependency array to prevent infinite loop.
  // Use onSessionIdReceivedRef.current inside the effect to call the latest callback.
  useEffect(() => {
    if (!query) {
      return;
    }

    // Sprint 48: Create new AbortController and store in ref
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    let isAborted = false;

    const fetchStream = async () => {
      // Reset state for new query
      setAnswer('');
      setSources([]);
      setError(null);
      setIntent('');
      setIsStreaming(true);
      setCitationMap(null);
      setMetadata(null);
      setReasoningData(null);
      currentReasoningData.current = null;
      hasCalledOnComplete.current = false;
      // Sprint 47 Fix: Reset final state refs
      finalAnswerRef.current = '';
      finalSourcesRef.current = [];
      // Sprint 51 Fix: Reset final phase events ref
      finalPhaseEventsRef.current = [];

      // Sprint 48 Feature 48.6: Reset phase state
      setCurrentPhase(null);
      setPhaseEvents([]);
      setShowTimeoutWarning(false);

      // Sprint 48 Feature 48.10: Set up timeout timers
      warningTimerRef.current = setTimeout(() => {
        setShowTimeoutWarning(true);
      }, TIMEOUT_CONFIG.WARNING_THRESHOLD_MS);

      timeoutTimerRef.current = setTimeout(() => {
        abortController.abort();
        setError('Anfrage-Timeout: Die Verarbeitung dauerte zu lange.');
      }, TIMEOUT_CONFIG.TIMEOUT_MS);

      try {
        for await (const chunk of streamChat(
          {
            query,
            intent: mode,
            session_id: initialSessionId,
            include_sources: true,
            namespaces: namespaces && namespaces.length > 0 ? namespaces : undefined,
          },
          abortController.signal
        )) {
          if (isAborted) break;
          handleChunk(chunk);
        }
      } catch (err) {
        if (isAborted) return;

        const isAbortError =
          (err instanceof Error && err.name === 'AbortError') ||
          (err instanceof DOMException && err.name === 'AbortError');

        if (isAbortError) {
          // Sprint 48: Clear timers on abort
          clearTimers();
          return;
        }

        console.error('Streaming error:', err);
        setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten');
        setIsStreaming(false);
        // Sprint 48: Clear timers on error
        clearTimers();
      }
    };

    const handleChunk = (chunk: ChatChunk) => {
      switch (chunk.type) {
        case 'metadata': {
          const data = chunk.data || {};
          setMetadata(data as Record<string, unknown>);

          if (data.intent) {
            setIntent(data.intent as string);
          }

          // Extract session ID from data or chunk
          const sessionIdFromMetadata = data.session_id || chunk.session_id;
          if (sessionIdFromMetadata) {
            setSessionId(sessionIdFromMetadata as string);
            // Sprint 47 Fix: Use ref to call callback without triggering re-render loop
            onSessionIdReceivedRef.current?.(sessionIdFromMetadata as string);
          }

          // Extract citation map
          if (data.citation_map) {
            setCitationMap(data.citation_map as Record<number, Source>);
          }

          // Extract reasoning data if present
          if (data.reasoning) {
            const rd = data.reasoning as ReasoningData;
            setReasoningData(rd);
            currentReasoningData.current = rd;
          }

          // Sprint 48 Feature 48.6: Handle phase_event in metadata
          if (data.phase_event) {
            handlePhaseEvent(data.phase_event as PhaseEvent);
          }
          break;
        }

        // Sprint 48 Feature 48.6: Handle phase_event chunk type
        case 'phase_event' as ChatChunk['type']: {
          const phaseData = chunk.data as unknown as PhaseEvent;
          if (phaseData) {
            handlePhaseEvent(phaseData);
          }
          break;
        }

        case 'source':
          if (chunk.source) {
            setSources((prev) => {
              const newSources = [...prev, chunk.source!];
              // Sprint 47 Fix: Track final sources in ref for onComplete
              finalSourcesRef.current = newSources;
              return newSources;
            });
          }
          break;

        case 'token':
          if (chunk.content) {
            setAnswer((prev) => {
              const newAnswer = prev + chunk.content;
              // Sprint 47 Fix: Track final answer in ref for onComplete
              finalAnswerRef.current = newAnswer;
              return newAnswer;
            });
          }
          break;

        // Sprint 51 Fix: Handle answer_chunk from backend (contains full answer)
        case 'answer_chunk' as ChatChunk['type']: {
          const answerData = chunk.data as { answer?: string; citation_map?: Record<number, Source> };
          if (answerData?.answer) {
            setAnswer(answerData.answer);
            finalAnswerRef.current = answerData.answer;
          }
          if (answerData?.citation_map) {
            setCitationMap(answerData.citation_map);
            // Sprint 51 Fix: Convert citation_map to sources array for MarkdownWithCitations
            // Backend sends citation_map instead of individual source events
            const sourcesFromCitationMap = Object.entries(answerData.citation_map)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([, source]) => source);
            setSources(sourcesFromCitationMap);
            finalSourcesRef.current = sourcesFromCitationMap;
          }
          break;
        }

        case 'complete': {
          const completeData = chunk.data;
          if (completeData) {
            setMetadata(completeData as Record<string, unknown>);
            if (completeData.citation_map) {
              setCitationMap(completeData.citation_map as Record<number, Source>);
              // Sprint 51 Fix: Convert citation_map to sources if not already populated
              if (finalSourcesRef.current.length === 0) {
                const sourcesFromCitationMap = Object.entries(completeData.citation_map as Record<number, Source>)
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([, source]) => source);
                setSources(sourcesFromCitationMap);
                finalSourcesRef.current = sourcesFromCitationMap;
              }
            }
            // Extract reasoning data from complete event if not already set
            if (completeData.reasoning && !currentReasoningData.current) {
              const rd = completeData.reasoning as ReasoningData;
              setReasoningData(rd);
              currentReasoningData.current = rd;
            }
          }
          setIsStreaming(false);
          setCurrentPhase(null);
          setShowTimeoutWarning(false);

          // Sprint 48: Clear timers on successful completion
          clearTimers();

          // Sprint 47 Fix: Call onComplete immediately when streaming completes
          // Use refs to get the final values and avoid dependency array issues
          // Sprint 51 Fix: Include phaseEvents in reasoningData so phases persist in history
          if (!hasCalledOnComplete.current && finalAnswerRef.current) {
            hasCalledOnComplete.current = true;
            // Build final reasoningData with phaseEvents included
            const finalReasoningData = buildReasoningData(
              completeData as Record<string, unknown> | null,
              '', // intent already in metadata
              finalPhaseEventsRef.current
            ) || currentReasoningData.current;
            onCompleteRef.current?.(
              finalAnswerRef.current,
              finalSourcesRef.current,
              finalReasoningData
            );
          }
          break;
        }

        case 'error':
          setError(chunk.error || 'Unknown error');
          setIsStreaming(false);
          setCurrentPhase(null);
          setShowTimeoutWarning(false);
          // Sprint 48: Clear timers on error
          clearTimers();
          break;
      }
    };

    /**
     * Sprint 48 Feature 48.6: Handle phase event updates
     * Sprint 51 Fix: Also track in ref for onComplete callback
     */
    const handlePhaseEvent = (event: PhaseEvent) => {
      // Update current phase based on status
      if (event.status === 'in_progress') {
        setCurrentPhase(event.phase_type);
      } else if (event.status === 'completed' || event.status === 'failed' || event.status === 'skipped') {
        // Clear current phase if the completed phase matches
        setCurrentPhase((current) =>
          current === event.phase_type ? null : current
        );
      }

      // Update phase events list (state for UI)
      setPhaseEvents((prev) => {
        const existingIndex = prev.findIndex(
          (e) => e.phase_type === event.phase_type
        );

        let newEvents: PhaseEvent[];
        if (existingIndex >= 0) {
          // Update existing event
          newEvents = [...prev];
          newEvents[existingIndex] = event;
        } else {
          // Add new event
          newEvents = [...prev, event];
        }

        // Sprint 51 Fix: Also update ref for onComplete callback
        finalPhaseEventsRef.current = newEvents;

        return newEvents;
      });
    };

    fetchStream();

    return () => {
      isAborted = true;
      abortController.abort();
      // Sprint 48: Clear timers on cleanup
      clearTimers();
    };
    // Sprint 47 Fix: Removed onSessionIdReceived from dependencies - use ref instead
    // Sprint 48: Added clearTimers to dependencies
  }, [query, mode, namespaces, initialSessionId, clearTimers]);

  // Sprint 47 Fix: Fallback onComplete call when streaming finishes
  // This handles edge cases where the 'complete' event might be missed
  // Uses refs to avoid triggering infinite loops from unstable dependencies
  // Sprint 51 Fix: Include phaseEvents in reasoningData so phases persist in history
  useEffect(() => {
    if (!isStreaming && finalAnswerRef.current && !hasCalledOnComplete.current) {
      hasCalledOnComplete.current = true;
      // Build final reasoningData with phaseEvents included
      const finalReasoningData = buildReasoningData(
        null, // metadata not available in fallback
        '', // intent already in metadata
        finalPhaseEventsRef.current
      ) || currentReasoningData.current;
      onCompleteRef.current?.(
        finalAnswerRef.current,
        finalSourcesRef.current,
        finalReasoningData
      );
    }
    // Sprint 47 Fix: Only depend on isStreaming to avoid re-running on every token/source
    // The refs contain the final values when streaming completes
  }, [isStreaming]);

  return {
    answer,
    sources,
    isStreaming,
    error,
    intent,
    sessionId,
    citationMap,
    reasoningData,
    metadata,
    // Sprint 48 Feature 48.6: Phase event state
    currentPhase,
    phaseEvents,
    // Sprint 48 Feature 48.10: Timeout and cancel
    showTimeoutWarning,
    cancelRequest,
  };
}

/**
 * Build reasoning data from metadata if not directly provided
 * This handles cases where the backend sends reasoning info in different formats
 * Sprint 51: Added phaseEvents parameter to preserve phases after answer appears
 */
export function buildReasoningData(
  metadata: Record<string, unknown> | null,
  intent: string,
  phaseEvents?: PhaseEvent[]
): ReasoningData | null {
  if (!metadata && !phaseEvents?.length) return null;

  // If reasoning data is directly available, use it (but add phaseEvents)
  if (metadata?.reasoning) {
    const existingData = metadata.reasoning as ReasoningData;
    return {
      ...existingData,
      phase_events: phaseEvents || existingData.phase_events,
    };
  }

  // Build from individual fields if available
  const intentType = (metadata?.intent_type || intent || 'factual') as IntentType;
  const confidence = (metadata?.intent_confidence as number) || 0.8;
  const retrievalSteps = (metadata?.retrieval_steps as RetrievalStepType[]) || [];
  const toolsUsed = (metadata?.tools_used as string[]) || [];
  const totalDuration = metadata?.latency_seconds
    ? (metadata.latency_seconds as number) * 1000
    : undefined;

  // Sprint 51: Return data if we have phase events, even without retrieval steps
  if (!retrievalSteps.length && !toolsUsed.length && !phaseEvents?.length) {
    return null;
  }

  return {
    intent: {
      intent: intentType,
      confidence,
      reasoning: metadata?.intent_reasoning as string | undefined,
    },
    retrieval_steps: retrievalSteps,
    tools_used: toolsUsed,
    total_duration_ms: totalDuration,
    phase_events: phaseEvents,
  };
}
