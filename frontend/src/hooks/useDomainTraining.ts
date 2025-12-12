/**
 * useDomainTraining Hook
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * Custom hooks for domain training operations with API client integration
 */

import { useState, useEffect, useCallback } from 'react';
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

export interface TrainingSample {
  input: string;
  output: string;
  metadata?: Record<string, unknown>;
}

export interface TrainingRequest {
  samples: TrainingSample[];
}

export interface TrainingStatusResponse {
  status: 'pending' | 'training' | 'ready' | 'failed';
  progress?: number;
  logs?: string[];
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
 */
export function useDomains() {
  const [data, setData] = useState<Domain[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchDomains = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<DomainsResponse>('/admin/domains');
      setData(response.domains);
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
 */
export function useCreateDomain() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(async (data: CreateDomainRequest): Promise<Domain> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.post<Domain>('/admin/domains', data);
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
 * Start training for a domain
 */
export function useStartTraining() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutateAsync = useCallback(
    async (data: { domain: string; dataset: TrainingSample[] }): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        await apiClient.post<void>(`/admin/domains/${data.domain}/train`, {
          samples: data.dataset,
        });
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

  const fetchStatus = useCallback(async () => {
    if (!enabled || !domainName) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<TrainingStatusResponse>(
        `/admin/domains/${domainName}/training-status`
      );
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch training status'));
    } finally {
      setIsLoading(false);
    }
  }, [domainName, enabled]);

  useEffect(() => {
    if (!enabled) return;

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
