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
import type { GraphExpansionConfig } from '../types/settings';
import type { ReasoningData, IntentType, RetrievalStep as RetrievalStepType, PhaseEvent, PhaseType, FourWayResults, IntentWeights, ChannelSamples } from '../types/reasoning';
import type {
  SkillActivationEvent,
  ToolUseEvent,
  ToolProgressEvent,
  ToolResultEvent,
  ToolErrorEvent,
  ToolTimeoutEvent,
  SkillActivationFailedEvent,
  ToolExecutionState,
} from '../types/skills-events';

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
 * Sprint 51 Feature 51.1 + 51.2: Added totalPhases and isGeneratingAnswer
 * Sprint 119 Feature 119.1: Added skill activation and tool execution tracking
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
  /**
   * Sprint 51 Feature 51.1: Total number of expected phases from backend.
   * This is dynamically determined based on the query type.
   */
  totalPhases: number | undefined;
  /**
   * Sprint 51 Feature 51.2: Whether tokens are being actively generated.
   * True when receiving token events, used for streaming cursor display.
   */
  isGeneratingAnswer: boolean;
  /**
   * Sprint 119 Feature 119.1: Skill activation events (e.g., bash_executor activated)
   */
  skillActivations: SkillActivationEvent[];
  /**
   * Sprint 119 Feature 119.1: Tool execution states (running, completed, failed, etc.)
   * Map of execution_id to ToolExecutionState for tracking concurrent executions
   */
  toolExecutions: Map<string, ToolExecutionState>;
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
  /** Sprint 79 Feature 79.6: Graph expansion configuration */
  graphExpansionConfig?: GraphExpansionConfig;
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
  graphExpansionConfig,
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

  // Sprint 51 Feature 51.1: Dynamic total phases from backend
  const [totalPhases, setTotalPhases] = useState<number | undefined>(undefined);

  // Sprint 51 Feature 51.2: Track when tokens are being actively generated
  const [isGeneratingAnswer, setIsGeneratingAnswer] = useState(false);

  // Sprint 119 Feature 119.1: Skill/Tool execution state
  const [skillActivations, setSkillActivations] = useState<SkillActivationEvent[]>([]);
  const [toolExecutions, setToolExecutions] = useState<Map<string, ToolExecutionState>>(new Map());

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

      // Sprint 51 Feature 51.1 + 51.2: Reset new state
      setTotalPhases(undefined);
      setIsGeneratingAnswer(false);

      // Sprint 119 Feature 119.1: Reset skill/tool state
      setSkillActivations([]);
      setToolExecutions(new Map());

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
          abortController.signal,
          // Sprint 79 Feature 79.6: Pass graph expansion config
          { graphExpansionConfig }
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

          // Sprint 51 Feature 51.1: Extract total phases count from backend
          if (data.total_phases !== undefined) {
            setTotalPhases(data.total_phases as number);
          }
          break;
        }

        // Sprint 48 Feature 48.6: Handle phase_event chunk type
        case 'phase_event': {
          const phaseData = chunk.data as PhaseEvent;
          if (phaseData) {
            handlePhaseEvent(phaseData);
          }
          break;
        }

        // Sprint 52: Handle reasoning_complete to capture all phase events
        case 'reasoning_complete': {
          const reasoningCompleteData = chunk.data as { phase_events?: PhaseEvent[] };
          if (reasoningCompleteData?.phase_events) {
            // Only process COMPLETED events from the summary to preserve duration_ms
            // IN_PROGRESS events have duration_ms: null and would overwrite the correct values
            for (const event of reasoningCompleteData.phase_events) {
              if (event.status === 'completed' || event.status === 'failed') {
                handlePhaseEvent(event);
              }
            }
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
            // Sprint 51 Feature 51.2: Mark that we're actively generating answer tokens
            setIsGeneratingAnswer(true);
            setAnswer((prev) => {
              const newAnswer = prev + chunk.content;
              // Sprint 47 Fix: Track final answer in ref for onComplete
              finalAnswerRef.current = newAnswer;
              return newAnswer;
            });
          }
          // Sprint 52: Also handle token in data format from LangGraph stream
          if (chunk.data?.content) {
            setIsGeneratingAnswer(true);
            setAnswer((prev) => {
              const newAnswer = prev + chunk.data!.content;
              finalAnswerRef.current = newAnswer;
              return newAnswer;
            });
          }
          break;

        // Sprint 52: Handle citation_map event streamed before tokens
        case 'citation_map': {
          const citationMapData = chunk.data as Record<number, Source>;
          if (citationMapData) {
            setCitationMap(citationMapData);
            // Convert to sources array for display
            const sourcesFromCitationMap = Object.entries(citationMapData)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([, source]) => source);
            setSources(sourcesFromCitationMap);
            finalSourcesRef.current = sourcesFromCitationMap;
          }
          break;
        }

        // Sprint 51 Fix: Handle answer_chunk from backend (contains full answer)
        // Sprint 52 Fix: Also extract metadata including 4-way search results
        case 'answer_chunk': {
          const answerData = chunk.data as {
            answer?: string;
            citation_map?: Record<number, Source>;
            intent?: string;
            intent_confidence?: number;
            intent_weights?: Record<string, number>;
            metadata?: Record<string, unknown>;
          };
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
          // Sprint 52 Fix: Set metadata from answer_chunk for 4-way display
          // The answer_chunk now contains all metadata including four_way_results
          setMetadata(answerData as Record<string, unknown>);

          // Sprint 52 Fix: Also build and set reasoningData immediately
          // so the 4-way section renders without waiting for stream end
          const updatedReasoningData = buildReasoningData(
            answerData as Record<string, unknown>,
            answerData.intent || '',
            finalPhaseEventsRef.current,
            answerData.intent_weights
          );
          if (updatedReasoningData) {
            setReasoningData(updatedReasoningData);
            currentReasoningData.current = updatedReasoningData;
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
          // Sprint 51 Feature 51.2: Clear generating state on completion
          setIsGeneratingAnswer(false);

          // Sprint 48: Clear timers on successful completion
          clearTimers();

          // Sprint 47 Fix: Call onComplete immediately when streaming completes
          // Use refs to get the final values and avoid dependency array issues
          // Sprint 51 Fix: Include phaseEvents in reasoningData so phases persist in history
          if (!hasCalledOnComplete.current && finalAnswerRef.current) {
            hasCalledOnComplete.current = true;
            // Build final reasoningData with phaseEvents included
            // Sprint 52: Pass intent_weights for 4-way search display
            // Sprint 52 Fix: Preserve 4-way data from answer_chunk if complete event doesn't have it
            let finalReasoningData = buildReasoningData(
              completeData as Record<string, unknown> | null,
              '', // intent already in metadata
              finalPhaseEventsRef.current,
              completeData?.intent_weights as Record<string, number> | undefined
            );

            // If we built new data but it's missing 4-way info or correct intent, merge from previous
            if (finalReasoningData && currentReasoningData.current) {
              // Sprint 52 Fix: Merge intent if final has 'factual' but current has the real intent
              const shouldMergeIntent =
                finalReasoningData.intent.intent === 'factual' &&
                currentReasoningData.current.intent.intent !== 'factual';

              if (!finalReasoningData.four_way_results && currentReasoningData.current.four_way_results) {
                finalReasoningData = {
                  ...finalReasoningData,
                  four_way_results: currentReasoningData.current.four_way_results,
                  intent_weights: currentReasoningData.current.intent_weights,
                  intent_method: currentReasoningData.current.intent_method,
                  intent_latency_ms: currentReasoningData.current.intent_latency_ms,
                  channel_samples: currentReasoningData.current.channel_samples,
                };
              }

              // Sprint 52 Fix: Preserve the correct intent from answer_chunk
              if (shouldMergeIntent) {
                finalReasoningData = {
                  ...finalReasoningData,
                  intent: currentReasoningData.current.intent,
                };
              }
            }

            // Fall back to current if we couldn't build new data
            finalReasoningData = finalReasoningData || currentReasoningData.current;

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
          // Sprint 51 Feature 51.2: Clear generating state on error
          setIsGeneratingAnswer(false);
          // Sprint 48: Clear timers on error
          clearTimers();
          break;

        // Sprint 119 Feature 119.1: Skill activation event (single skill)
        case 'skill_activated': {
          const skillData = chunk.data as SkillActivationEvent;
          if (skillData) {
            setSkillActivations((prev) => [...prev, {
              ...skillData,
              timestamp: skillData.timestamp || new Date().toISOString(),
            }]);
          }
          break;
        }

        // Sprint 120: Skill activation event (multiple skills array)
        case 'skill_activation': {
          const activationData = chunk.data as {
            skills?: string[];
            skill_count?: number;
            instruction_tokens?: number;
            intent?: string;
            timestamp?: string;
          };
          if (activationData?.skills && Array.isArray(activationData.skills)) {
            // Convert array format to individual SkillActivationEvents
            const timestamp = activationData.timestamp || new Date().toISOString();
            const newActivations = activationData.skills.map((skill) => ({
              skill,
              timestamp,
              reason: `Activated for ${activationData.intent || 'query'} (${activationData.skill_count || activationData.skills?.length || 1} skills, ${activationData.instruction_tokens || 0} tokens)`,
            }));
            setSkillActivations((prev) => [...prev, ...newActivations]);
          }
          break;
        }

        // Sprint 119 Feature 119.1: Skill activation failed event
        case 'skill_activation_failed': {
          const failData = chunk.data as SkillActivationFailedEvent;
          if (failData) {
            setError(`Skill activation failed: ${failData.reason}`);
          }
          break;
        }

        // Sprint 119 Feature 119.1: Tool use event (tool starts executing)
        case 'tool_use': {
          const toolData = chunk.data as ToolUseEvent;
          if (toolData) {
            const execId = toolData.execution_id || toolData.tool;
            setToolExecutions((prev) => {
              const next = new Map(prev);
              next.set(execId, {
                tool: toolData.tool,
                server: toolData.server || 'unknown',
                status: 'running',
                input: toolData.parameters,
                startTime: toolData.timestamp || new Date().toISOString(),
                execution_id: execId,
              });
              return next;
            });
          }
          break;
        }

        // Sprint 119 Feature 119.1: Tool progress event
        case 'tool_progress': {
          const progressData = chunk.data as ToolProgressEvent;
          if (progressData) {
            const execId = progressData.execution_id || progressData.tool;
            setToolExecutions((prev) => {
              const next = new Map(prev);
              const existing = next.get(execId);
              if (existing) {
                next.set(execId, {
                  ...existing,
                  progress: progressData.progress,
                  progressMessage: progressData.message,
                });
              }
              return next;
            });
          }
          break;
        }

        // Sprint 119 Feature 119.1: Tool result event (tool completed)
        case 'tool_result': {
          const resultData = chunk.data as ToolResultEvent;
          if (resultData) {
            const execId = resultData.execution_id || resultData.tool;
            setToolExecutions((prev) => {
              const next = new Map(prev);
              const existing = next.get(execId);
              if (existing) {
                next.set(execId, {
                  ...existing,
                  status: resultData.success ? 'success' : 'error',
                  output: resultData.result,
                  error: resultData.error,
                  duration_ms: resultData.duration_ms,
                  endTime: resultData.timestamp || new Date().toISOString(),
                });
              } else {
                // Create new entry if tool_use wasn't received
                next.set(execId, {
                  tool: resultData.tool,
                  server: resultData.server || 'unknown',
                  status: resultData.success ? 'success' : 'error',
                  input: {},
                  output: resultData.result,
                  error: resultData.error,
                  duration_ms: resultData.duration_ms,
                  startTime: resultData.timestamp || new Date().toISOString(),
                  endTime: resultData.timestamp || new Date().toISOString(),
                  execution_id: execId,
                });
              }
              return next;
            });
          }
          break;
        }

        // Sprint 119 Feature 119.1: Tool error event
        case 'tool_error': {
          const errorData = chunk.data as ToolErrorEvent;
          if (errorData) {
            const execId = errorData.execution_id || errorData.tool;
            setToolExecutions((prev) => {
              const next = new Map(prev);
              const existing = next.get(execId);
              if (existing) {
                next.set(execId, {
                  ...existing,
                  status: 'error',
                  error: errorData.error,
                  endTime: errorData.timestamp || new Date().toISOString(),
                });
              } else {
                // Create new entry if tool_use wasn't received
                next.set(execId, {
                  tool: errorData.tool,
                  server: 'unknown',
                  status: 'error',
                  input: {},
                  error: errorData.error,
                  startTime: errorData.timestamp || new Date().toISOString(),
                  endTime: errorData.timestamp || new Date().toISOString(),
                  execution_id: execId,
                });
              }
              return next;
            });
          }
          break;
        }

        // Sprint 119 Feature 119.1: Tool timeout event
        case 'tool_timeout': {
          const timeoutData = chunk.data as ToolTimeoutEvent;
          if (timeoutData) {
            const execId = timeoutData.execution_id || timeoutData.tool;
            setToolExecutions((prev) => {
              const next = new Map(prev);
              const existing = next.get(execId);
              if (existing) {
                next.set(execId, {
                  ...existing,
                  status: 'timeout',
                  error: `Tool execution timed out after ${timeoutData.timeout} seconds`,
                  endTime: timeoutData.timestamp || new Date().toISOString(),
                });
              } else {
                // Create new entry if tool_use wasn't received
                next.set(execId, {
                  tool: timeoutData.tool,
                  server: 'unknown',
                  status: 'timeout',
                  input: {},
                  error: `Tool execution timed out after ${timeoutData.timeout} seconds`,
                  startTime: timeoutData.timestamp || new Date().toISOString(),
                  endTime: timeoutData.timestamp || new Date().toISOString(),
                  execution_id: execId,
                });
              }
              return next;
            });
          }
          break;
        }
      }
    };

    /**
     * Sprint 48 Feature 48.6: Handle phase event updates
     * Sprint 51 Fix: Also track in ref for onComplete callback
     * Sprint 52 Fix: Preserve duration_ms - never overwrite COMPLETED with IN_PROGRESS
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
          const existing = prev[existingIndex];

          // Sprint 52 Fix: Never overwrite a COMPLETED event with IN_PROGRESS
          // Also preserve duration_ms if the existing event has it
          const shouldUpdate =
            event.status === 'completed' ||
            event.status === 'failed' ||
            (existing.status !== 'completed' && existing.status !== 'failed');

          if (shouldUpdate) {
            // If existing has duration_ms but new doesn't, preserve it
            const mergedEvent = {
              ...event,
              duration_ms: event.duration_ms ?? existing.duration_ms,
            };
            newEvents = [...prev];
            newEvents[existingIndex] = mergedEvent;
          } else {
            // Keep existing event (don't overwrite COMPLETED with IN_PROGRESS)
            newEvents = prev;
          }
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
    // Sprint 79: Added graphExpansionConfig to dependencies
  }, [query, mode, namespaces, initialSessionId, clearTimers, graphExpansionConfig]);

  // Sprint 47 Fix: Fallback onComplete call when streaming finishes
  // This handles edge cases where the 'complete' event might be missed
  // Uses refs to avoid triggering infinite loops from unstable dependencies
  // Sprint 51 Fix: Include phaseEvents in reasoningData so phases persist in history
  useEffect(() => {
    if (!isStreaming && finalAnswerRef.current && !hasCalledOnComplete.current) {
      hasCalledOnComplete.current = true;
      // Build final reasoningData with phaseEvents included
      // Sprint 52 Fix: Preserve 4-way data from currentReasoningData if available
      let finalReasoningData = buildReasoningData(
        null, // metadata not available in fallback
        '', // intent already in metadata
        finalPhaseEventsRef.current
      );

      // Merge 4-way data from current if available
      if (finalReasoningData && currentReasoningData.current?.four_way_results) {
        finalReasoningData = {
          ...finalReasoningData,
          four_way_results: currentReasoningData.current.four_way_results,
          intent_weights: currentReasoningData.current.intent_weights,
          intent_method: currentReasoningData.current.intent_method,
          intent_latency_ms: currentReasoningData.current.intent_latency_ms,
          channel_samples: currentReasoningData.current.channel_samples,
        };
      }

      // Fall back to current if we couldn't build new data
      finalReasoningData = finalReasoningData || currentReasoningData.current;

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
    // Sprint 51 Feature 51.1: Dynamic total phases from backend
    totalPhases,
    // Sprint 51 Feature 51.2: Token generation state for streaming cursor
    isGeneratingAnswer,
    // Sprint 119 Feature 119.1: Skill/Tool execution state
    skillActivations,
    toolExecutions,
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
  phaseEvents?: PhaseEvent[],
  intentWeights?: Record<string, number>
): ReasoningData | null {
  // Sprint 52 Debug: Log input parameters
  console.log('[buildReasoningData] Input:', {
    hasMetadata: !!metadata,
    metadataKeys: metadata ? Object.keys(metadata) : [],
    intent,
    phaseEventsCount: phaseEvents?.length,
    intentWeights,
  });

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
  // Sprint 52 Fix: Backend sends 'intent', not 'intent_type'
  const intentType = (metadata?.intent || metadata?.intent_type || intent || 'factual') as IntentType;
  const confidence = (metadata?.intent_confidence as number) || 0.8;
  const retrievalSteps = (metadata?.retrieval_steps as RetrievalStepType[]) || [];
  const toolsUsed = (metadata?.tools_used as string[]) || [];
  const totalDuration = metadata?.latency_seconds
    ? (metadata.latency_seconds as number) * 1000
    : metadata?.total_latency_ms as number | undefined;

  // Sprint 52: Extract 4-way search results from nested metadata
  // Backend sends: completeData.metadata.four_way_results
  const nestedMetadata = metadata?.metadata as Record<string, unknown> | undefined;
  const fourWayMetadata = nestedMetadata?.four_way_results as FourWayResults | undefined;
  const intentMethodData = nestedMetadata?.intent_method as string | undefined;
  const intentLatencyData = nestedMetadata?.intent_latency_ms as number | undefined;
  // Sprint 52: Extract channel samples (text snippets per channel)
  const channelSamplesData = nestedMetadata?.channel_samples as ChannelSamples | undefined;

  // Sprint 52 Debug: Log 4-way extraction
  console.log('[buildReasoningData] 4-way extraction:', {
    nestedMetadataKeys: nestedMetadata ? Object.keys(nestedMetadata) : [],
    fourWayMetadata,
    intentMethodData,
    intentLatencyData,
    hasChannelSamples: !!channelSamplesData,
  });
  const intentWeightsData = intentWeights ? {
    vector: intentWeights.vector || 0,
    bm25: intentWeights.bm25 || 0,
    local: intentWeights.local || 0,
    global: intentWeights.global_ || intentWeights.global || 0,
  } as IntentWeights : undefined;

  // Sprint 51: Return data if we have phase events, even without retrieval steps
  if (!retrievalSteps.length && !toolsUsed.length && !phaseEvents?.length && !fourWayMetadata) {
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
    // Sprint 52: 4-way search metadata
    four_way_results: fourWayMetadata,
    intent_weights: intentWeightsData,
    intent_method: intentMethodData,
    intent_latency_ms: intentLatencyData,
    // Sprint 52: Channel samples (text snippets per channel)
    channel_samples: channelSamplesData,
  };
}
