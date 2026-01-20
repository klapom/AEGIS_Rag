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
  DashboardStats,
  ScanDirectoryRequest,
  ScanDirectoryResponse,
  IngestionJobResponse,
  IngestionEventResponse,
  BatchProgress,
  MCPServer,
  MCPTool,
  MCPExecutionResult,
  MCPHealthStatus,
  MCPToolPermission,
  MemoryStats,
  MemorySearchRequest,
  MemorySearchResponse,
  SessionMemory,
  ConsolidationStatus,
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
 * Get dashboard statistics for admin overview cards
 * Sprint 116 Feature 116.1: Dashboard Stats Cards
 *
 * @returns DashboardStats with high-level metrics for dashboard cards
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/dashboard/stats`, {
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
  namespaceId: string = 'default',
  domainId: string | null = null,
  signal?: AbortSignal
): AsyncGenerator<ReindexProgressChunk> {
  const params = new URLSearchParams();
  for (const path of filePaths) {
    params.append('file_paths', path);
  }
  if (dryRun) {
    params.append('dry_run', 'true');
  }
  // Sprint 76 Feature 76.1 (TD-084): Multi-tenant namespace isolation
  params.append('namespace_id', namespaceId);
  // Sprint 76 Feature 76.2 (TD-085): DSPy domain prompts
  if (domainId) {
    params.append('domain_id', domainId);
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

// ============================================================================
// Sprint 52: Graph Analytics Stats API
// Feature 52.2.1: Graph Analytics Page
// ============================================================================

/**
 * Graph statistics for admin dashboard
 * Sprint 52 Feature 52.2.1
 */
export interface GraphStats {
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
 * Fetch comprehensive graph statistics for admin dashboard
 * Sprint 52 Feature 52.2.1: Graph Analytics Page
 *
 * @returns GraphStats with entity/relationship counts, community statistics, and health metrics
 */
export async function fetchGraphStats(): Promise<GraphStats> {
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

// ============================================================================
// Sprint 71 Feature 71.8: Ingestion Job Monitoring API
// ============================================================================

/**
 * List all ingestion jobs with optional filtering
 */
export async function listIngestionJobs(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<IngestionJobResponse[]> {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.append('status', params.status);
  if (params?.limit !== undefined) queryParams.append('limit', String(params.limit));
  if (params?.offset !== undefined) queryParams.append('offset', String(params.offset));

  const url = `${API_BASE_URL}/api/v1/admin/ingestion/jobs?${queryParams.toString()}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get ingestion job details by ID
 */
export async function getIngestionJob(jobId: string): Promise<IngestionJobResponse> {
  const url = `${API_BASE_URL}/api/v1/admin/ingestion/jobs/${jobId}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Cancel a running ingestion job
 */
export async function cancelIngestionJob(jobId: string): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/admin/ingestion/jobs/${jobId}/cancel`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
}

/**
 * Get ingestion events for a job
 */
export async function getJobEvents(
  jobId: string,
  params?: {
    level?: 'INFO' | 'WARNING' | 'ERROR';
    limit?: number;
    offset?: number;
  }
): Promise<IngestionEventResponse[]> {
  const queryParams = new URLSearchParams();
  if (params?.level) queryParams.append('level', params.level);
  if (params?.limit !== undefined) queryParams.append('limit', String(params.limit));
  if (params?.offset !== undefined) queryParams.append('offset', String(params.offset));

  const url = `${API_BASE_URL}/api/v1/admin/ingestion/jobs/${jobId}/events?${queryParams.toString()}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get only ERROR-level events for a job
 */
export async function getJobErrors(jobId: string): Promise<IngestionEventResponse[]> {
  const url = `${API_BASE_URL}/api/v1/admin/ingestion/jobs/${jobId}/errors`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Stream batch progress via SSE
 *
 * @param jobId The job ID to stream progress for
 * @param signal Optional AbortSignal to cancel the stream
 * @yields BatchProgress objects with real-time progress updates
 */
export async function* streamBatchProgress(
  jobId: string,
  signal?: AbortSignal
): AsyncGenerator<BatchProgress> {
  const url = `${API_BASE_URL}/api/v1/admin/ingestion/jobs/${jobId}/progress`;

  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Accept': 'text/event-stream' },
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
            const progress: BatchProgress = JSON.parse(data);
            yield progress;
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
// Sprint 72 Feature 72.1: MCP Tool Management API
// ============================================================================

/**
 * Get MCP health status
 * @returns MCPHealthStatus with server connectivity and tool counts
 */
export async function getMCPHealth(): Promise<MCPHealthStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/health`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get list of all MCP servers
 * @returns Array of MCPServer objects
 */
export async function getMCPServers(): Promise<MCPServer[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/servers`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Connect to an MCP server
 * @param serverName Name of the server to connect
 * @returns Updated MCPServer object
 */
export async function connectMCPServer(serverName: string): Promise<MCPServer> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/servers/${encodeURIComponent(serverName)}/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Disconnect from an MCP server
 * @param serverName Name of the server to disconnect
 * @returns Updated MCPServer object
 */
export async function disconnectMCPServer(serverName: string): Promise<MCPServer> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/servers/${encodeURIComponent(serverName)}/disconnect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get list of all available MCP tools
 * @returns Array of MCPTool objects
 */
export async function getMCPTools(): Promise<MCPTool[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/tools`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get details of a specific MCP tool
 * @param toolName Name of the tool
 * @returns MCPTool object with full details
 */
export async function getMCPTool(toolName: string): Promise<MCPTool> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/tools/${encodeURIComponent(toolName)}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Execute an MCP tool with parameters
 * @param toolName Name of the tool to execute
 * @param parameters Tool parameters
 * @returns MCPExecutionResult with success/error info
 */
export async function executeMCPTool(
  toolName: string,
  parameters: Record<string, unknown>
): Promise<MCPExecutionResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/mcp/tools/${encodeURIComponent(toolName)}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parameters }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Sprint 116 Feature 116.5: MCP Tool Permission Management API
// ============================================================================

/**
 * Get permission configuration for a tool
 * Sprint 116 Feature 116.5: Tool permission management
 *
 * @param toolName Name of the tool
 * @returns MCPToolPermission with enabled status and config
 */
export async function getToolPermissions(toolName: string): Promise<MCPToolPermission> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/mcp/tools/${encodeURIComponent(toolName)}/permissions`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Update tool permission (enable/disable)
 * Sprint 116 Feature 116.5: Tool permission management
 *
 * @param toolName Name of the tool
 * @param enabled Whether the tool should be enabled
 * @returns Updated MCPToolPermission
 */
export async function updateToolPermissions(
  toolName: string,
  enabled: boolean
): Promise<MCPToolPermission> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/mcp/tools/${encodeURIComponent(toolName)}/permissions`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Get tool configuration
 * Sprint 116 Feature 116.5: Tool configuration management
 *
 * @param toolName Name of the tool
 * @returns Tool configuration object
 */
export async function getToolConfig(toolName: string): Promise<{ config: Record<string, unknown> }> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/mcp/tools/${encodeURIComponent(toolName)}/config`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Update tool configuration
 * Sprint 116 Feature 116.5: Tool configuration management
 *
 * @param toolName Name of the tool
 * @param config Configuration object
 * @returns Updated configuration
 */
export async function updateToolConfig(
  toolName: string,
  config: Record<string, unknown>
): Promise<{ config: Record<string, unknown> }> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/mcp/tools/${encodeURIComponent(toolName)}/config`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Sprint 72 Feature 72.3: Memory Management API
// ============================================================================

/**
 * Get memory statistics for all layers (Redis, Qdrant, Graphiti)
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * @returns MemoryStats with statistics for all memory layers
 */
export async function getMemoryStats(): Promise<MemoryStats> {
  const response = await fetch(`${API_BASE_URL}/api/v1/memory/stats`, {
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
 * Search memory across all layers
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * @param request Search parameters including user_id, session_id, query, namespace
 * @returns MemorySearchResponse with matching results
 */
export async function searchMemory(
  request: MemorySearchRequest
): Promise<MemorySearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/memory/search`, {
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
 * Get session memory by session ID
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * @param sessionId The session ID to retrieve
 * @returns SessionMemory with messages and context
 */
export async function getSessionMemory(sessionId: string): Promise<SessionMemory> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/memory/session/${encodeURIComponent(sessionId)}`,
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

/**
 * Trigger memory consolidation
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * @returns ConsolidationStatus with current status and history
 */
export async function triggerConsolidation(): Promise<ConsolidationStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/memory/consolidate`, {
    method: 'POST',
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
 * Get consolidation status and history
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * @returns ConsolidationStatus with current status and last 10 runs
 */
export async function getConsolidationStatus(): Promise<ConsolidationStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/memory/consolidation/status`, {
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
 * Export session memory as JSON file
 * Sprint 72 Feature 72.3: Memory Management UI
 *
 * @param sessionId The session ID to export
 */
export async function exportMemory(sessionId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/memory/session/${encodeURIComponent(sessionId)}`,
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

  const data = await response.json();

  // Create and download the JSON file
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `memory-${sessionId}-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ============================================================================
// Sprint 98 Feature 98.5: Explainability Dashboard API
// ============================================================================

/**
 * Get decision trace by trace ID
 * Sprint 98 Feature 98.5: Explainability Dashboard
 *
 * @param traceId The trace ID to retrieve
 * @returns DecisionTrace with full trace details
 */
export async function getDecisionTrace(
  traceId: string
): Promise<import('../types/admin').DecisionTrace> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/explainability/trace/${encodeURIComponent(traceId)}`,
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

/**
 * Get recent decision traces for a user
 * Sprint 98 Feature 98.5: Explainability Dashboard
 *
 * @param userId Optional user ID to filter traces
 * @param limit Maximum number of traces to return (default: 10)
 * @returns Array of recent traces
 */
export async function getRecentTraces(
  userId?: string,
  limit: number = 10
): Promise<import('../types/admin').TraceListItem[]> {
  const params = new URLSearchParams();
  if (userId) params.append('userId', userId);
  params.append('limit', String(limit));

  const response = await fetch(
    `${API_BASE_URL}/api/v1/explainability/recent?${params.toString()}`,
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

/**
 * Get explanation for a trace at specified level
 * Sprint 98 Feature 98.5: Explainability Dashboard
 *
 * @param traceId The trace ID to explain
 * @param level Explanation level: 'user', 'expert', or 'audit'
 * @returns Explanation object (UserExplanation, ExpertExplanation, or AuditExplanation)
 */
export async function getExplanation(
  traceId: string,
  level: import('../types/admin').ExplanationLevel
): Promise<
  | import('../types/admin').UserExplanation
  | import('../types/admin').ExpertExplanation
  | import('../types/admin').AuditExplanation
> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/explainability/explain/${encodeURIComponent(traceId)}?level=${level}`,
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

/**
 * Get source attribution for a trace
 * Sprint 98 Feature 98.5: Explainability Dashboard
 *
 * @param traceId The trace ID to get sources for
 * @param claim Optional specific claim to find sources for
 * @returns Array of source documents
 */
export async function getSourceAttribution(
  traceId: string,
  claim?: string
): Promise<import('../types/admin').SourceDocument[]> {
  const params = new URLSearchParams();
  if (claim) params.append('claim', claim);

  const response = await fetch(
    `${API_BASE_URL}/api/v1/explainability/attribution/${encodeURIComponent(traceId)}?${params.toString()}`,
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
// Sprint 98 Feature 98.6: Certification Status Dashboard API
// ============================================================================

/**
 * Get all skill certifications with optional filtering
 * Sprint 98 Feature 98.6: Certification Status Dashboard
 *
 * @param level Optional certification level to filter by
 * @param status Optional certification status to filter by
 * @returns Array of skill certifications
 */
export async function getSkillCertifications(
  level?: import('../types/admin').CertificationLevel,
  status?: import('../types/admin').CertificationStatus
): Promise<import('../types/admin').SkillCertification[]> {
  const params = new URLSearchParams();
  if (level) params.append('level', level);
  if (status) params.append('status', status);

  const response = await fetch(
    `${API_BASE_URL}/api/v1/certification/skills?${params.toString()}`,
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

/**
 * Get validation report for a specific skill
 * Sprint 98 Feature 98.6: Certification Status Dashboard
 *
 * @param skillName The name of the skill
 * @returns Validation report with checks and recommendations
 */
export async function getSkillValidationReport(
  skillName: string
): Promise<import('../types/admin').ValidationReport> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/certification/skill/${encodeURIComponent(skillName)}/report`,
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

/**
 * Trigger validation for a specific skill
 * Sprint 98 Feature 98.6: Certification Status Dashboard
 *
 * @param skillName The name of the skill to validate
 * @returns Updated validation report
 */
export async function validateSkill(
  skillName: string
): Promise<import('../types/admin').ValidationReport> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/certification/skill/${encodeURIComponent(skillName)}/validate`,
    {
      method: 'POST',
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

/**
 * Get skills with expiring certifications
 * Sprint 98 Feature 98.6: Certification Status Dashboard
 *
 * @param days Number of days threshold (default: 30)
 * @returns Array of skills with expiring certifications
 */
export async function getExpiringCertifications(
  days: number = 30
): Promise<import('../types/admin').SkillCertification[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/certification/expiring?days=${days}`,
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

/**
 * Get certification overview statistics
 * Sprint 98 Feature 98.6: Certification Status Dashboard
 *
 * @returns Certification overview with counts by level
 */
export async function getCertificationOverview(): Promise<
  import('../types/admin').CertificationOverview
> {
  const response = await fetch(`${API_BASE_URL}/api/v1/certification/overview`, {
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
