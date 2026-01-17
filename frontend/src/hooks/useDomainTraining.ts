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
 * Fetch all domains with auto-refresh
 * Sprint 51 Feature 51.4: Auto-refresh domain status
 *
 * Note: The API endpoint requires a trailing slash (/admin/domains/)
 * and returns a direct array of Domain objects, not wrapped in { domains: [...] }
 *
 * @param options.refetchInterval - Polling interval in ms (default: 5000)
 * @param options.enabled - Whether to enable auto-refresh (default: true)
 */
export function useDomains(options?: { refetchInterval?: number; enabled?: boolean }) {
  const { refetchInterval = 5000, enabled = true } = options || {};
  const [data, setData] = useState<Domain[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isFirstLoad = useRef(true);

  const fetchDomains = useCallback(async () => {
    // Only show loading on first fetch, not on polls (prevents flickering)
    if (isFirstLoad.current) {
      setIsLoading(true);
    }
    setError(null);
    try {
      // API returns Domain[] directly (not wrapped in { domains: [...] })
      // Trailing slash is required by FastAPI router configuration
      const response = await apiClient.get<Domain[]>('/admin/domains/');
      setData(response);
      isFirstLoad.current = false;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch domains'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    isFirstLoad.current = true;
    fetchDomains();

    // Poll at configured interval for auto-refresh (default: 5 seconds)
    const intervalId = setInterval(fetchDomains, refetchInterval);

    return () => clearInterval(intervalId);
  }, [fetchDomains, refetchInterval, enabled]);

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
 * Delete domain response
 * Sprint 51 Feature 51.4: Domain deletion
 */
export interface DeleteDomainResponse {
  message: string;
  domain: string;
}

/**
 * Delete a domain
 * Sprint 51 Feature 51.4: Domain deletion
 *
 * Calls DELETE /admin/domains/{domain_id}
 * This will remove all indexed documents for the domain
 */
export function useDeleteDomain() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(async (domainId: string): Promise<DeleteDomainResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.delete<DeleteDomainResponse>(
        `/admin/domains/${domainId}`
      );
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to delete domain');
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
 * Response from LLM models endpoint
 * Sprint 110 Feature 110.4: Fixed to use /admin/llm/models endpoint
 */
interface OllamaModelsResponse {
  models: Array<{
    name: string;
    size: number;
    digest: string;
    modified_at: string;
  }>;
  ollama_available: boolean;
  error: string | null;
}

/**
 * Get available LLM models
 * Sprint 110 Feature 110.4: Fixed to use /admin/llm/models endpoint
 *
 * Previously called /admin/domains/available-models (404 NOT FOUND)
 * Now calls /admin/llm/models which returns all Ollama models
 */
export function useAvailableModels() {
  const [data, setData] = useState<string[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchModels = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Sprint 110 Fix: Use /admin/llm/models endpoint (returns OllamaModelsResponse)
      const response = await apiClient.get<OllamaModelsResponse>(
        '/admin/llm/models'
      );
      // Extract model names from the response
      if (response.ollama_available && response.models) {
        setData(response.models.map(m => m.name));
      } else {
        setError(new Error(response.error || 'Ollama not available'));
        setData([]);
      }
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
// Domain Stats Types & Hook (Feature 52.2.2)
// ============================================================================

/**
 * Domain statistics response
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 */
export interface DomainStatsResponse {
  domain_name: string;
  documents: number;
  chunks: number;
  entities: number;
  relationships: number;
  last_indexed: string | null;
  indexing_progress: number;
  error_count: number;
  errors: string[];
  health_status: 'healthy' | 'degraded' | 'error' | 'empty' | 'indexing';
}

/**
 * Re-index domain response
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 */
export interface ReindexDomainResponse {
  message: string;
  domain_name: string;
  documents_queued: number;
}

/**
 * Validate domain response
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 */
export interface ValidateDomainResponse {
  domain_name: string;
  is_valid: boolean;
  validation_errors: string[];
  recommendations: string[];
}

/**
 * Fetch domain statistics
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 *
 * @param domainName - Domain name to get stats for
 * @param enabled - Whether to enable fetching (default: true)
 * @param refetchInterval - Polling interval in ms (default: 10000)
 */
export function useDomainStats(
  domainName: string,
  enabled = true,
  refetchInterval = 10000
) {
  const [data, setData] = useState<DomainStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const isFirstLoad = useRef(true);

  const fetchStats = useCallback(async () => {
    if (!enabled || !domainName) {
      setIsLoading(false);
      return;
    }

    // Only show loading on first fetch
    if (isFirstLoad.current) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const response = await apiClient.get<DomainStatsResponse>(
        `/admin/domains/${domainName}/stats`
      );
      setData(response);
      isFirstLoad.current = false;
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch domain stats'));
    } finally {
      setIsLoading(false);
    }
  }, [domainName, enabled]);

  useEffect(() => {
    if (!enabled) return;

    isFirstLoad.current = true;
    fetchStats();

    // Poll at configured interval for auto-refresh
    const intervalId = setInterval(fetchStats, refetchInterval);

    return () => clearInterval(intervalId);
  }, [fetchStats, refetchInterval, enabled]);

  return { data, isLoading, error, refetch: fetchStats };
}

/**
 * Re-index domain mutation
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 */
export function useReindexDomain() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(async (domainName: string): Promise<ReindexDomainResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.post<ReindexDomainResponse>(
        `/admin/domains/${domainName}/reindex`
      );
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to re-index domain');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutateAsync, isLoading, error };
}

/**
 * Validate domain mutation
 * Sprint 52 Feature 52.2.2: Domain Management Enhancement
 */
export function useValidateDomain() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(async (domainName: string): Promise<ValidateDomainResponse> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.post<ValidateDomainResponse>(
        `/admin/domains/${domainName}/validate`
      );
      return response;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to validate domain');
      setError(error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

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

// ============================================================================
// Sprint 71 Feature 71.13-71.15: Missing Domain Training APIs
// ============================================================================

/**
 * Augmentation request
 * Sprint 71 Feature 71.13: Data Augmentation UI
 */
export interface AugmentationRequest {
  seed_samples: TrainingSample[];
  target_count: number;
}

/**
 * Augmentation response
 * Sprint 71 Feature 71.13: Data Augmentation UI
 */
export interface AugmentationResponse {
  generated_samples: TrainingSample[];
  seed_count: number;
  generated_count: number;
  validation_rate: number;
}

/**
 * Augment training data using LLM
 * Sprint 71 Feature 71.13: Data Augmentation UI
 *
 * Expands a small dataset (5-10 samples) into a larger one (20+) using LLM-based
 * paraphrasing and synonym replacement.
 */
export function useAugmentTrainingData() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(
    async (data: AugmentationRequest): Promise<AugmentationResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post<AugmentationResponse>(
          '/admin/domains/augment',
          data
        );
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to augment training data');
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
 * Batch ingestion request
 * Sprint 71 Feature 71.14: Batch Document Upload
 */
export interface BatchIngestionRequest {
  domain_name: string;
  file_paths: string[];
  recursive: boolean;
}

/**
 * Batch ingestion response
 * Sprint 71 Feature 71.14: Batch Document Upload
 */
export interface BatchIngestionResponse {
  job_id: string;
  domain_name: string;
  documents_queued: number;
  message: string;
}

/**
 * Ingest batch of documents to a domain
 * Sprint 71 Feature 71.14: Batch Document Upload
 *
 * Upload multiple documents to a domain for processing. Returns job_id for
 * tracking progress via IngestionJobList.
 */
export function useIngestBatch() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(
    async (data: BatchIngestionRequest): Promise<BatchIngestionResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.post<BatchIngestionResponse>(
          '/admin/domains/ingest-batch',
          data
        );
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to ingest batch');
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
 * Get full domain details
 * Sprint 71 Feature 71.15: Get Domain Details
 *
 * Fetch complete domain configuration including prompts, trained metrics, and metadata.
 * Different from useDomainStats which only returns statistics.
 */
export function useDomainDetails(domainName: string, enabled = true) {
  const [data, setData] = useState<Domain | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchDetails = useCallback(async () => {
    if (!enabled || !domainName) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<Domain>(
        `/admin/domains/${domainName}`
      );
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch domain details'));
    } finally {
      setIsLoading(false);
    }
  }, [domainName, enabled]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  return { data, isLoading, error, refetch: fetchDetails };
}

/**
 * Connectivity evaluation request
 * Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
 */
export interface ConnectivityEvaluationRequest {
  namespace_id: string;
  domain_type: 'factual' | 'narrative' | 'technical' | 'academic';
}

/**
 * Connectivity evaluation response
 * Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
 */
export interface ConnectivityEvaluationResponse {
  namespace_id: string;
  domain_type: string;
  total_entities: number;
  total_relationships: number;
  total_communities: number;
  relations_per_entity: number;
  entities_per_community: number;
  benchmark_min: number;
  benchmark_max: number;
  within_benchmark: boolean;
  benchmark_status: 'below' | 'within' | 'above';
  recommendations: string[];
}

/**
 * Evaluate entity connectivity metrics for a namespace
 * Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric
 *
 * Evaluates knowledge graph connectivity and compares it to domain-specific benchmarks.
 * Returns metrics, benchmark comparison, and actionable recommendations.
 *
 * @param namespace_id - Namespace to evaluate (e.g., "hotpotqa_large")
 * @param domain_type - Domain type for benchmark (factual, narrative, technical, academic)
 * @param enabled - Whether to fetch connectivity metrics
 */
export function useConnectivityMetrics(
  namespace_id: string,
  domain_type: 'factual' | 'narrative' | 'technical' | 'academic' = 'factual',
  enabled = true
) {
  const [data, setData] = useState<ConnectivityEvaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchMetrics = useCallback(async () => {
    if (!enabled || !namespace_id) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.post<ConnectivityEvaluationResponse>(
        '/admin/domains/connectivity/evaluate',
        {
          namespace_id,
          domain_type,
        }
      );
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch connectivity metrics'));
    } finally {
      setIsLoading(false);
    }
  }, [namespace_id, domain_type, enabled]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return { data, isLoading, error, refetch: fetchMetrics };
}
