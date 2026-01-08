/**
 * Graph Operations API Client
 * Sprint 79 Feature 79.7: Admin Graph Operations UI
 *
 * Provides API functions for:
 * - Community summarization (batch generation)
 * - Graph statistics retrieval
 * - Namespace management
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Community summarization request parameters
 */
export interface CommunitySummarizationRequest {
  namespace?: string | null;
  force?: boolean;
  batch_size?: number;
}

/**
 * Community summarization response
 */
export interface CommunitySummarizationResponse {
  status: 'started' | 'complete' | 'no_work';
  total_communities: number;
  summaries_generated: number | null;
  failed: number | null;
  total_time_s: number | null;
  avg_time_per_summary_s: number | null;
  message: string;
}

/**
 * Graph statistics for admin dashboard
 */
export interface GraphOperationsStats {
  total_entities: number;
  total_relationships: number;
  entity_types: Record<string, number>;
  relationship_types: Record<string, number>;
  community_count: number;
  community_sizes: number[];
  orphan_nodes: number;
  avg_degree: number;
  summary_status: {
    generated: number;
    pending: number;
  };
  graph_health: 'healthy' | 'warning' | 'critical' | 'unknown';
  timestamp: string;
}

/**
 * Namespace information
 */
export interface NamespaceInfo {
  namespace_id: string;
  namespace_type: string;
  document_count: number;
  description: string;
}

/**
 * Namespace list response
 */
export interface NamespaceListResponse {
  namespaces: NamespaceInfo[];
  total_count: number;
}

/**
 * Trigger community summarization batch job
 *
 * POST /api/v1/admin/graph/communities/summarize
 *
 * @param request - Summarization parameters (namespace, force, batch_size)
 * @returns CommunitySummarizationResponse with job status and statistics
 */
export async function triggerCommunitySummarization(
  request: CommunitySummarizationRequest = {}
): Promise<CommunitySummarizationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/communities/summarize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      namespace: request.namespace ?? null,
      force: request.force ?? false,
      batch_size: request.batch_size ?? 10,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Fetch graph statistics for operations dashboard
 *
 * GET /api/v1/admin/graph/stats
 *
 * @returns GraphOperationsStats with comprehensive graph metrics
 */
export async function fetchGraphOperationsStats(): Promise<GraphOperationsStats> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/graph/stats`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Fetch available namespaces for filtering
 *
 * GET /api/v1/admin/namespaces
 *
 * @returns NamespaceListResponse with all available namespaces
 */
export async function fetchNamespaces(): Promise<NamespaceListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/namespaces`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}
