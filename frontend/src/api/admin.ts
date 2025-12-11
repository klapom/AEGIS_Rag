/**
 * Admin API Client
 * Sprint 17 Feature 17.1: Admin UI for Directory Indexing
 * Sprint 31 Feature 31.10b: Cost Dashboard API Integration
 * Sprint 33 Feature 33.1: Directory Scanning API
 * Sprint 42: Namespace Management API
 */

import type {
  ReindexProgressChunk,
  ReindexRequest,
  SystemStats,
  ScanDirectoryRequest,
  ScanDirectoryResponse,
} from '../types/admin';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Stream re-indexing progress using Server-Sent Events (SSE)
 *
 * @param request Re-index request with directory, dry_run, and confirm flags
 * @param signal Optional AbortSignal to cancel the stream
 * @yields ReindexProgressChunk objects with progress updates
 */
export async function* streamReindex(
  request: ReindexRequest,
  signal?: AbortSignal
): AsyncGenerator<ReindexProgressChunk> {
  const params = new URLSearchParams();
  params.append('input_dir', request.input_dir);
  if (request.dry_run !== undefined) {
    params.append('dry_run', String(request.dry_run));
  }
  if (request.confirm !== undefined) {
    params.append('confirm', String(request.confirm));
  }

  const url = `${API_BASE_URL}/api/v1/admin/reindex?${params.toString()}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'text/event-stream',
    },
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Split by newlines to get individual SSE messages
      const lines = buffer.split('\n');

      // Keep the last incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        // SSE messages start with "data: "
        if (line.startsWith('data: ')) {
          const data = line.slice(6); // Remove "data: " prefix

          try {
            const chunk: ReindexProgressChunk = JSON.parse(data);
            yield chunk;
          } catch (e) {
            console.error('Failed to parse SSE chunk:', e, 'Data:', data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Get comprehensive system statistics for admin dashboard
 *
 * @returns SystemStats with Qdrant, Neo4j, BM25, and Redis statistics
 */
export async function getSystemStats(): Promise<SystemStats> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/stats`, {
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
 * Cost Tracking Types (Sprint 31 Feature 31.10b)
 */
export interface ProviderCost {
  cost_usd: number;
  tokens: number;
  calls: number;
  avg_cost_per_call: number;
}

export interface ModelCost {
  provider: string;
  cost_usd: number;
  tokens: number;
  calls: number;
}

export interface BudgetStatus {
  limit_usd: number;
  spent_usd: number;
  utilization_percent: number;
  status: 'ok' | 'warning' | 'critical';
  remaining_usd: number;
}

export interface CostStats {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  avg_cost_per_call: number;
  by_provider: Record<string, ProviderCost>;
  by_model: Record<string, ModelCost>;
  budgets: Record<string, BudgetStatus>;
  time_range: string;
}

/**
 * Get cost statistics for admin dashboard
 * Sprint 31 Feature 31.10b: Cost Dashboard API
 *
 * @param timeRange Time range for cost stats: '7d', '30d', or 'all'
 * @returns CostStats with provider, model, and budget breakdown
 */
export async function getCostStats(
  timeRange: '7d' | '30d' | 'all' = '7d'
): Promise<CostStats> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/costs/stats?time_range=${timeRange}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Sprint 33 Feature 33.1: Directory Scanning API
// ============================================================================

/**
 * Scan a directory for indexable files
 * Sprint 33 Feature 33.1: Directory Selector
 *
 * @param request Directory path and recursive flag
 * @returns ScanDirectoryResponse with file list and statistics
 */
export async function scanDirectory(
  request: ScanDirectoryRequest
): Promise<ScanDirectoryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/indexing/scan-directory`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Upload Types (Sprint 35 Feature 35.10)
 */
export interface UploadFileInfo {
  filename: string;
  file_path: string;
  file_size_bytes: number;
  file_extension: string;
}

export interface UploadResponse {
  upload_dir: string;
  files: UploadFileInfo[];
  total_size_bytes: number;
}

/**
 * Upload files to the server for indexing
 * Sprint 35 Feature 35.10: File Upload for Admin Indexing
 *
 * @param files Array of File objects to upload
 * @returns UploadResponse with upload directory and file information
 */
export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/admin/indexing/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Stream document addition progress using Server-Sent Events (SSE)
 * ADD-only mode: Documents are added to existing index without deletion
 *
 * @param filePaths Array of file paths to add to the index
 * @param dryRun If true, simulates the operation without making changes
 * @param signal Optional AbortSignal to cancel the stream
 * @yields ReindexProgressChunk objects with progress updates
 */
export async function* streamAddDocuments(
  filePaths: string[],
  dryRun: boolean = false,
  signal?: AbortSignal
): AsyncGenerator<ReindexProgressChunk> {
  const params = new URLSearchParams();
  for (const path of filePaths) {
    params.append('file_paths', path);
  }
  if (dryRun) {
    params.append('dry_run', 'true');
  }

  const url = `${API_BASE_URL}/api/v1/admin/indexing/add?${params.toString()}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Accept': 'text/event-stream',
    },
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Split by newlines to get individual SSE messages
      const lines = buffer.split('\n');

      // Keep the last incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        // SSE messages start with "data: "
        if (line.startsWith('data: ')) {
          const data = line.slice(6); // Remove "data: " prefix

          try {
            const chunk: ReindexProgressChunk = JSON.parse(data);
            yield chunk;
          } catch (e) {
            console.error('Failed to parse SSE chunk:', e, 'Data:', data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============================================================================
// Sprint 42: Namespace Management API
// ============================================================================

/**
 * Namespace information
 */
export interface NamespaceInfo {
  namespace_id: string;
  namespace_type: string;
  document_count: number;
  description: string;
}

export interface NamespaceListResponse {
  namespaces: NamespaceInfo[];
  total_count: number;
}

/**
 * Get available namespaces for search filtering
 * Sprint 42: Namespace/Project selection in search UI
 *
 * @returns NamespaceListResponse with all available namespaces
 */
export async function getNamespaces(): Promise<NamespaceListResponse> {
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
