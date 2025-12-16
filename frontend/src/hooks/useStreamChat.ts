/**
 * useStreamChat Hook
 * Sprint 46: Extracted streaming logic from StreamingAnswer component
 * Sprint 47: Fixed infinite re-render loop (Maximum update depth exceeded)
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
 *
 * Bug Fix (Sprint 47):
 * - Use refs for callbacks to prevent dependency array changes
 * - Capture final state with refs before calling onComplete
 * - Remove unstable callbacks from useEffect dependency arrays
 */

import { useState, useEffect, useRef } from 'react';
import { streamChat, type ChatChunk } from '../api/chat';
import type { Source } from '../types/chat';
import type { ReasoningData, IntentType, RetrievalStep as RetrievalStepType } from '../types/reasoning';

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

  const hasCalledOnComplete = useRef(false);
  const currentReasoningData = useRef<ReasoningData | null>(null);

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

  // Handle SSE streaming
  // Sprint 47 Fix: Remove onSessionIdReceived from dependency array to prevent infinite loop.
  // Use onSessionIdReceivedRef.current inside the effect to call the latest callback.
  useEffect(() => {
    if (!query) {
      return;
    }

    const abortController = new AbortController();
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

        if (isAbortError) return;

        console.error('Streaming error:', err);
        setError(err instanceof Error ? err.message : 'Ein Fehler ist aufgetreten');
        setIsStreaming(false);
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

        case 'complete': {
          const completeData = chunk.data;
          if (completeData) {
            setMetadata(completeData as Record<string, unknown>);
            if (completeData.citation_map) {
              setCitationMap(completeData.citation_map as Record<number, Source>);
            }
            // Extract reasoning data from complete event if not already set
            if (completeData.reasoning && !currentReasoningData.current) {
              const rd = completeData.reasoning as ReasoningData;
              setReasoningData(rd);
              currentReasoningData.current = rd;
            }
          }
          setIsStreaming(false);

          // Sprint 47 Fix: Call onComplete immediately when streaming completes
          // Use refs to get the final values and avoid dependency array issues
          if (!hasCalledOnComplete.current && finalAnswerRef.current) {
            hasCalledOnComplete.current = true;
            onCompleteRef.current?.(
              finalAnswerRef.current,
              finalSourcesRef.current,
              currentReasoningData.current
            );
          }
          break;
        }

        case 'error':
          setError(chunk.error || 'Unknown error');
          setIsStreaming(false);
          break;
      }
    };

    fetchStream();

    return () => {
      isAborted = true;
      abortController.abort();
    };
    // Sprint 47 Fix: Removed onSessionIdReceived from dependencies - use ref instead
  }, [query, mode, namespaces, initialSessionId]);

  // Sprint 47 Fix: Fallback onComplete call when streaming finishes
  // This handles edge cases where the 'complete' event might be missed
  // Uses refs to avoid triggering infinite loops from unstable dependencies
  useEffect(() => {
    if (!isStreaming && finalAnswerRef.current && !hasCalledOnComplete.current) {
      hasCalledOnComplete.current = true;
      onCompleteRef.current?.(
        finalAnswerRef.current,
        finalSourcesRef.current,
        currentReasoningData.current
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
  };
}

/**
 * Build reasoning data from metadata if not directly provided
 * This handles cases where the backend sends reasoning info in different formats
 */
export function buildReasoningData(
  metadata: Record<string, unknown> | null,
  intent: string
): ReasoningData | null {
  if (!metadata) return null;

  // If reasoning data is directly available, use it
  if (metadata.reasoning) {
    return metadata.reasoning as ReasoningData;
  }

  // Build from individual fields if available
  const intentType = (metadata.intent_type || intent || 'factual') as IntentType;
  const confidence = (metadata.intent_confidence as number) || 0.8;
  const retrievalSteps = (metadata.retrieval_steps as RetrievalStepType[]) || [];
  const toolsUsed = (metadata.tools_used as string[]) || [];
  const totalDuration = metadata.latency_seconds
    ? (metadata.latency_seconds as number) * 1000
    : undefined;

  // Only return if we have meaningful data
  if (!retrievalSteps.length && !toolsUsed.length) {
    return null;
  }

  return {
    intent: {
      intent: intentType,
      confidence,
      reasoning: metadata.intent_reasoning as string | undefined,
    },
    retrieval_steps: retrievalSteps,
    tools_used: toolsUsed,
    total_duration_ms: totalDuration,
  };
}
