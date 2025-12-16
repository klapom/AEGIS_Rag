/**
 * useStreamChat Hook
 * Sprint 46: Extracted streaming logic from StreamingAnswer component
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

  // Handle SSE streaming
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
            onSessionIdReceived?.(sessionIdFromMetadata as string);
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
            setSources((prev) => [...prev, chunk.source!]);
          }
          break;

        case 'token':
          if (chunk.content) {
            setAnswer((prev) => prev + chunk.content);
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
  }, [query, mode, namespaces, initialSessionId, onSessionIdReceived]);

  // Call onComplete when streaming finishes
  useEffect(() => {
    if (!isStreaming && answer && onComplete && !hasCalledOnComplete.current) {
      hasCalledOnComplete.current = true;
      onComplete(answer, sources, currentReasoningData.current);
    }
  }, [isStreaming, answer, sources, onComplete]);

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
