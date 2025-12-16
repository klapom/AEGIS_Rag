/**
 * useDomainTraining Hook
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * Custom hooks for domain training operations with API client integration
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '../lib/api';

// ============================================================================
// Types
// ============================================================================

export interface Domain {
  id?: string;
  name: string;
  description: string;
  llm_model: string | null;
  status: 'pending' | 'training' | 'ready' | 'failed';
  created_at?: string;
  updated_at?: string;
}

// Training sample format - matches API directly
export interface TrainingSample {
  text: string;
  entities: string[];
  relations?: Array<{ subject: string; predicate: string; object: string }>;
}

export interface TrainingRequest {
  samples: TrainingSample[];
}

export interface TrainingStatusResponse {
  status: 'pending' | 'training' | 'ready' | 'failed';
  progress_percent?: number;
  current_step?: string;
  logs?: string[];
  metrics?: Record<string, unknown>;
  error?: string;
}

export interface AvailableModelsResponse {
  models: string[];
}

export interface CreateDomainRequest {
  name: string;
  description: string;
  llm_model?: string;
}

export interface DomainsResponse {
  domains: Domain[];
}

export interface ClassificationResult {
  domain: string;
  score: number;
}

export interface ClassifyDocumentRequest {
  text: string;
}

export interface ClassifyDocumentResponse {
  recommended: string;
  confidence: number;
  classifications: ClassificationResult[];
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Fetch all domains
 *
 * Note: The API endpoint requires a trailing slash (/admin/domains/)
 * and returns a direct array of Domain objects, not wrapped in { domains: [...] }
 */
export function useDomains() {
  const [data, setData] = useState<Domain[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchDomains = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // API returns Domain[] directly (not wrapped in { domains: [...] })
      // Trailing slash is required by FastAPI router configuration
      const response = await apiClient.get<Domain[]>('/admin/domains/');
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch domains'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDomains();
  }, [fetchDomains]);

  return { data, isLoading, error, refetch: fetchDomains };
}

/**
 * Create a new domain
 *
 * Note: The API endpoint requires a trailing slash (/admin/domains/)
 */
export function useCreateDomain() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(async (data: CreateDomainRequest): Promise<Domain> => {
    setIsLoading(true);
    setError(null);
    try {
      // Trailing slash is required by FastAPI router configuration
      const response = await apiClient.post<Domain>('/admin/domains/', data);
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create domain');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutateAsync, isLoading, error };
}

/**
 * Response from starting training
 */
export interface StartTrainingResponse {
  training_run_id: string;
  status: string;
  domain: string;
  message: string;
}

/**
 * Start training for a domain
 * Feature 45.13: Supports optional log_path for JSONL event logging
 */
export function useStartTraining() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(
    async (data: {
      domain: string;
      dataset: TrainingSample[];
      log_path?: string;
    }): Promise<StartTrainingResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        // Send samples directly - format already matches API
        // Include log_path for JSONL event logging (Feature 45.13)
        const response = await apiClient.post<StartTrainingResponse>(
          `/admin/domains/${data.domain}/train`,
          {
            samples: data.dataset,
            log_path: data.log_path || null,
          }
        );
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to start training');
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { mutateAsync, isLoading, error };
}

/**
 * Get available LLM models
 */
export function useAvailableModels() {
  const [data, setData] = useState<string[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchModels = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<AvailableModelsResponse>(
        '/admin/domains/available-models'
      );
      setData(response.models);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch available models'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  return { data, isLoading, error, refetch: fetchModels };
}

/**
 * Get training status for a domain
 */
export function useTrainingStatus(domainName: string, enabled = true) {
  const [data, setData] = useState<TrainingStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isFirstLoad = useRef(true);

  const fetchStatus = useCallback(async () => {
    if (!enabled || !domainName) {
      setIsLoading(false);
      return;
    }

    // Only show loading on first fetch, not on polls (prevents flickering)
    if (isFirstLoad.current) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const response = await apiClient.get<TrainingStatusResponse>(
        `/admin/domains/${domainName}/training-status`
      );
      setData(response);
      isFirstLoad.current = false;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch training status'));
    } finally {
      setIsLoading(false);
    }
  }, [domainName, enabled]);

  useEffect(() => {
    if (!enabled) return;

    isFirstLoad.current = true;
    fetchStatus();

    // Poll every 2 seconds during training
    const intervalId = setInterval(fetchStatus, 2000);

    return () => clearInterval(intervalId);
  }, [fetchStatus, enabled]);

  return { data, isLoading, error, refetch: fetchStatus };
}

/**
 * Classify document to suggest domain
 * Sprint 45 Feature 45.7
 */
export function useClassifyDocument() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(
    async (data: ClassifyDocumentRequest): Promise<ClassifyDocumentResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post<ClassifyDocumentResponse>(
          '/admin/domains/classify',
          data
        );
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to classify document');
        setError(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  return { mutateAsync, isLoading, error };
}

// ============================================================================
// SSE Training Stream Types & Hook (Feature 45.13)
// ============================================================================

/**
 * Event types from the training stream
 */
export type TrainingEventType =
  | 'started'
  | 'phase_changed'
  | 'progress_update'
  | 'completed'
  | 'failed'
  | 'llm_request'
  | 'llm_response'
  | 'sample_processing'
  | 'sample_result'
  | 'evaluation_start'
  | 'evaluation_result'
  | 'bootstrap_iteration'
  | 'demo_selected'
  | 'error';

/**
 * Training event from SSE stream
 * Content is FULL (NOT truncated) - includes complete prompts and responses
 */
export interface TrainingEvent {
  event_type: TrainingEventType;
  timestamp: string;
  training_run_id: string;
  domain: string;
  progress_percent: number;
  phase: string;
  message: string;
  data: Record<string, unknown>;
}

/**
 * State for the training stream
 */
export interface TrainingStreamState {
  isConnected: boolean;
  events: TrainingEvent[];
  latestEvent: TrainingEvent | null;
  error: Error | null;
  progress: number;
  phase: string;
  isComplete: boolean;
  isFailed: boolean;
}

/**
 * SSE Training Stream Hook
 * Sprint 45 Feature 45.13: Real-time Training Progress with SSE
 *
 * Connects to the training SSE endpoint and streams events in real-time.
 * All content (prompts, responses, evaluations) is delivered FULL (NOT truncated).
 *
 * @param domainName - Domain being trained
 * @param trainingRunId - Training run ID to stream
 * @param enabled - Whether to connect to the stream
 * @param maxEvents - Maximum events to keep in memory (default: 1000)
 */
export function useTrainingStream(
  domainName: string,
  trainingRunId: string | null,
  enabled = true,
  maxEvents = 1000
): TrainingStreamState & { disconnect: () => void } {
  const [state, setState] = useState<TrainingStreamState>({
    isConnected: false,
    events: [],
    latestEvent: null,
    error: null,
    progress: 0,
    phase: '',
    isComplete: false,
    isFailed: false,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setState((prev) => ({ ...prev, isConnected: false }));
    }
  }, []);

  useEffect(() => {
    if (!enabled || !trainingRunId || !domainName) {
      disconnect();
      return;
    }

    let retryCount = 0;
    const maxRetries = 10;
    const retryDelay = 1000; // 1 second
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      // Build SSE URL - domain training router is mounted WITHOUT /api/v1 prefix
      const apiHost = import.meta.env.VITE_API_HOST || 'http://localhost:8000';
      const sseUrl = `${apiHost}/admin/domains/${domainName}/training-stream?training_run_id=${trainingRunId}`;

      console.log(`[SSE] Connecting to: ${sseUrl} (attempt ${retryCount + 1}/${maxRetries})`);

      // Create EventSource connection
      const eventSource = new EventSource(sseUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('[SSE] Connected successfully');
        retryCount = 0; // Reset retry count on successful connection
        setState((prev) => ({
          ...prev,
          isConnected: true,
          error: null,
        }));
      };

      eventSource.onmessage = (event) => {
        console.log('[SSE] Received event:', event.data.slice(0, 200));
        try {
          const data = JSON.parse(event.data) as TrainingEvent;

          setState((prev) => {
            // Keep only maxEvents in memory
            const events = [...prev.events, data];
            if (events.length > maxEvents) {
              events.shift();
            }

            const isComplete = data.event_type === 'completed';
            const isFailed = data.event_type === 'failed' || data.event_type === 'error';

            // Auto-disconnect on completion or failure
            if (isComplete || isFailed) {
              setTimeout(() => disconnect(), 100);
            }

            return {
              ...prev,
              events,
              latestEvent: data,
              progress: data.progress_percent,
              phase: data.phase,
              isComplete,
              isFailed: isFailed || prev.isFailed,
            };
          });
        } catch (err) {
          console.error('Failed to parse SSE event:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('[SSE] Connection error:', err, 'readyState:', eventSource.readyState);
        eventSource.close();
        eventSourceRef.current = null;

        // Retry if stream not ready yet (race condition with backend)
        if (retryCount < maxRetries) {
          retryCount++;
          console.log(`[SSE] Retrying in ${retryDelay}ms... (${retryCount}/${maxRetries})`);
          retryTimeout = setTimeout(connect, retryDelay);
        } else {
          setState((prev) => ({
            ...prev,
            isConnected: false,
            error: new Error('Training stream connection failed after retries'),
          }));
        }
      };
    };

    // Start connection with small delay to allow backend to initialize
    retryTimeout = setTimeout(connect, 500);

    return () => {
      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
      disconnect();
    };
  }, [domainName, trainingRunId, enabled, maxEvents, disconnect]);

  return { ...state, disconnect };
}
