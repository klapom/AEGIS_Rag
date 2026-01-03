/**
 * Admin API Types
 * Sprint 17 Feature 17.1: Admin UI for Directory Indexing
 * Sprint 33 Feature 33.1: Directory Scanning API
 */

// Re-indexing Progress Types

export type ReindexPhase =
  | 'initialization'
  | 'deletion'
  | 'chunking'
  | 'embedding'
  | 'indexing'
  | 'validation'
  | 'completed';

export type ReindexStatus = 'in_progress' | 'completed' | 'error';

export interface ReindexProgressChunk {
  status: ReindexStatus;
  phase?: ReindexPhase;
  documents_processed?: number;
  documents_total?: number;
  progress_percent?: number;
  eta_seconds?: number | null;
  current_document?: string | null;
  message: string;
  error?: string;
  // Sprint 33 Feature 33.6: Extended SSE fields for live progress
  detailed_progress?: DetailedProgress;
  errors?: IngestionError[];
  // Sprint 49 Feature 49.4: Failed document count for status determination
  failed_documents?: number;
}

export interface ReindexRequest {
  input_dir: string;
  dry_run?: boolean;
  confirm?: boolean;
}

// System Statistics Types

export interface SystemStats {
  // Qdrant statistics
  qdrant_total_chunks: number;
  qdrant_collection_name: string;
  qdrant_vector_dimension: number;

  // BM25 statistics (optional)
  bm25_corpus_size?: number | null;

  // Neo4j / LightRAG statistics
  neo4j_total_entities?: number | null;
  neo4j_total_relations?: number | null;

  // System metadata
  last_reindex_timestamp?: string | null;
  embedding_model: string;

  // Additional stats
  total_conversations?: number | null;
}

// ============================================================================
// Sprint 33 Feature 33.1: Directory Scanning Types
// ============================================================================

export type ParserType = 'docling' | 'llamaindex' | 'unsupported';

export interface FileInfo {
  file_path: string;
  file_name: string;
  file_extension: string;
  file_size_bytes: number;
  parser_type: ParserType;
  is_supported: boolean;
}

export interface DirectoryScanStatistics {
  total: number;
  docling_supported: number;
  llamaindex_supported: number;
  unsupported: number;
  total_size_bytes: number;
  docling_size_bytes: number;
  llamaindex_size_bytes: number;
}

export interface ScanDirectoryRequest {
  path: string;
  recursive: boolean;
}

export interface ScanDirectoryResponse {
  path: string;
  recursive: boolean;
  files: FileInfo[];
  statistics: DirectoryScanStatistics;
}

// ============================================================================
// Sprint 33 Feature 33.4: Detail Dialog Types
// ============================================================================

export interface VLMImageStatus {
  image_id: string;
  thumbnail_url?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  description?: string;
}

export interface ChunkInfo {
  chunk_id: string;
  text_preview: string;
  token_count: number;
  section_name: string;
  has_image: boolean;
}

export interface PipelinePhaseStatus {
  phase: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration_ms?: number;
}

export interface DetailedProgress {
  current_file: FileInfo;
  current_page: number;
  total_pages: number;
  page_thumbnail_url?: string;
  page_elements: {
    tables: number;
    images: number;
    word_count: number;
  };
  vlm_images: VLMImageStatus[];
  current_chunk: ChunkInfo | null;
  pipeline_status: PipelinePhaseStatus[];
  entities: {
    new_entities: string[];
    new_relations: string[];
    total_entities: number;
    total_relations: number;
  };
  // Sprint 36: Chunk-level extraction progress
  chunks_total?: number;
  chunks_processed?: number;
}

// ============================================================================
// Sprint 71 Feature 71.8: Ingestion Job Monitoring Types
// ============================================================================

export type IngestionJobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface IngestionJobResponse {
  job_id: string;
  directory_path: string;
  recursive: boolean;
  total_files: number;
  processed_files: number;
  failed_files: number;
  status: IngestionJobStatus;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
}

export interface IngestionEventResponse {
  event_id: number;
  job_id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  file_path?: string | null;
  document_id?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface DocumentProgress {
  document_id: string;
  document_name: string;
  file_path: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress_percent: number;
  chunks_created: number;
  entities_extracted: number;
  relations_extracted: number;
  error?: string | null;
  current_step?: string | null; // "parsing" | "chunking" | "embedding" | "graph_extraction"
}

export interface BatchProgress {
  batch_id: string;
  job_id: string;
  total_documents: number;
  parallel_limit: number;
  completed: number;
  in_progress: number;
  failed: number;
  overall_progress_percent: number;
  documents: DocumentProgress[];
}

// ============================================================================
// Sprint 33 Feature 33.5: Error Tracking Types
// ============================================================================

export type ErrorType = 'error' | 'warning' | 'info';

export interface IngestionError {
  type: ErrorType;
  timestamp: string;
  file_name: string;
  page_number?: number;
  message: string;
  details?: string;
}

// ============================================================================
// Sprint 37 Feature 37.4: Pipeline Progress Visualization Types
// ============================================================================

export type StageStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface StageProgress {
  name: string;
  status: StageStatus;
  processed: number;
  total: number;
  in_flight: number;
  progress_percent: number;
  duration_ms: number;
  is_complete: boolean;
}

export type WorkerStatus = 'idle' | 'processing' | 'error';

export interface WorkerInfo {
  id: number;
  status: WorkerStatus;
  current_chunk: string | null;
  progress_percent: number;
}

export interface PipelineProgressData {
  document_id: string;
  document_name: string;
  total_chunks: number;
  total_images: number;
  stages: {
    parsing: StageProgress;
    vlm: StageProgress;
    chunking: StageProgress;
    embedding: StageProgress;
    extraction: StageProgress;
  };
  worker_pool: {
    active: number;
    max: number;
    queue_depth: number;
    workers: WorkerInfo[];
  };
  metrics: {
    entities_total: number;
    relations_total: number;
    neo4j_writes: number;
    qdrant_writes: number;
  };
  timing: {
    started_at: number;
    elapsed_ms: number;
    estimated_remaining_ms: number;
  };
  overall_progress_percent: number;
}

// ============================================================================
// Sprint 37 Feature 37.7: Pipeline Worker Pool Configuration Types
// ============================================================================

export interface PipelineConfig {
  // Document Processing
  parallel_documents: number;
  max_queue_size: number;

  // VLM Workers
  vlm_workers: number;
  vlm_batch_size: number;
  vlm_timeout: number;

  // Embedding Workers
  embedding_workers: number;
  embedding_batch_size: number;
  embedding_timeout: number;

  // Extraction Workers
  extraction_workers: number;
  extraction_timeout: number;
  extraction_max_retries: number;

  // Resource Limits
  max_concurrent_llm: number;
  max_vram_mb: number;
}

// ============================================================================
// Sprint 72 Feature 72.1: MCP Tool Management Types
// ============================================================================

/**
 * MCP Server connection status
 */
export type MCPServerStatus = 'connected' | 'disconnected' | 'error' | 'connecting';

/**
 * MCP Server information
 */
export interface MCPServer {
  name: string;
  status: MCPServerStatus;
  url?: string;
  description?: string;
  tools: MCPTool[];
  last_connected?: string;
  error_message?: string;
}

/**
 * MCP Tool parameter schema
 */
export interface MCPToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description: string;
  required: boolean;
  default?: unknown;
  enum?: string[];
}

/**
 * MCP Tool information
 */
export interface MCPTool {
  name: string;
  description: string;
  server_name: string;
  parameters: MCPToolParameter[];
}

/**
 * MCP Tool execution request
 */
export interface MCPToolExecutionRequest {
  tool_name: string;
  parameters: Record<string, unknown>;
}

/**
 * MCP Tool execution result
 */
export interface MCPExecutionResult {
  success: boolean;
  tool_name: string;
  result?: unknown;
  error?: string;
  execution_time_ms: number;
  timestamp: string;
}

/**
 * MCP Health status
 */
export interface MCPHealthStatus {
  healthy: boolean;
  total_servers: number;
  connected_servers: number;
  total_tools: number;
  servers: MCPServerHealthInfo[];
  timestamp: string;
}

/**
 * Individual server health info
 */
export interface MCPServerHealthInfo {
  name: string;
  status: MCPServerStatus;
  tool_count: number;
  last_ping?: string;
}

// ============================================================================
// Sprint 72 Feature 72.3: Memory Management Types
// ============================================================================

/**
 * Redis layer statistics
 */
export interface RedisMemoryStats {
  keys: number;
  memory_mb: number;
  hit_rate: number;
}

/**
 * Qdrant layer statistics
 */
export interface QdrantMemoryStats {
  documents: number;
  size_mb: number;
  avg_search_latency_ms: number;
}

/**
 * Graphiti layer statistics
 */
export interface GraphitiMemoryStats {
  episodes: number;
  entities: number;
  avg_search_latency_ms: number;
}

/**
 * Combined memory statistics for all layers
 */
export interface MemoryStats {
  redis: RedisMemoryStats;
  qdrant: QdrantMemoryStats;
  graphiti: GraphitiMemoryStats;
  timestamp: string;
}

/**
 * Memory search request parameters
 */
export interface MemorySearchRequest {
  user_id?: string;
  session_id?: string;
  query?: string;
  namespace?: string;
  limit?: number;
  offset?: number;
}

/**
 * Individual memory search result
 */
export interface MemorySearchResult {
  id: string;
  content: string;
  relevance_score: number;
  timestamp: string;
  layer: 'redis' | 'qdrant' | 'graphiti';
  metadata?: Record<string, unknown>;
}

/**
 * Memory search response
 */
export interface MemorySearchResponse {
  results: MemorySearchResult[];
  total_count: number;
  query: MemorySearchRequest;
}

/**
 * Session memory data
 */
export interface SessionMemory {
  session_id: string;
  user_id?: string;
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: string;
  }>;
  context?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * Consolidation run history entry
 */
export interface ConsolidationHistoryEntry {
  id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed';
  items_processed: number;
  items_consolidated: number;
  error?: string;
}

/**
 * Consolidation status response
 */
export interface ConsolidationStatus {
  is_running: boolean;
  last_run?: ConsolidationHistoryEntry;
  history: ConsolidationHistoryEntry[];
}

/**
 * Point-in-time memory query request
 */
export interface PointInTimeRequest {
  session_id: string;
  timestamp: string;
  include_context?: boolean;
}

// ============================================================================
// Sprint 72 Feature 72.2: Domain Training Types (Wire-up)
// ============================================================================

/**
 * Full domain details including training metrics and timestamps
 * Sprint 72 Feature 72.2: Domain Details API
 */
export interface DomainDetails {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'training' | 'ready' | 'failed';
  llm_model: string;
  training_metrics?: Record<string, unknown> | null;
  created_at: string;
  trained_at?: string | null;
}

/**
 * Request for data augmentation
 * Sprint 72 Feature 72.2: Data Augmentation API
 */
export interface AugmentationRequest {
  seed_samples: Array<{
    text: string;
    entities: string[];
    relations?: Array<{ subject: string; predicate: string; object: string }>;
  }>;
  target_count: number;
  llm_model?: string;
}

/**
 * Response from data augmentation
 * Sprint 72 Feature 72.2: Data Augmentation API
 */
export interface AugmentationResponse {
  generated_samples: Array<{
    text: string;
    entities: string[];
    relations?: Array<{ subject: string; predicate: string; object: string }>;
  }>;
  seed_count: number;
  generated_count: number;
  validation_rate: number;
}

/**
 * Request for batch document upload
 * Sprint 72 Feature 72.2: Batch Upload API
 */
export interface BatchUploadRequest {
  domain_name: string;
  file_paths: string[];
  recursive: boolean;
}

/**
 * Response from batch document upload
 * Sprint 72 Feature 72.2: Batch Upload API
 */
export interface BatchUploadResponse {
  job_id: string;
  domain_name: string;
  documents_queued: number;
  message: string;
}

/**
 * Domain validation response
 * Sprint 72 Feature 72.2: Domain Validation API
 */
export interface ValidateDomainAdminResponse {
  domain_name: string;
  is_valid: boolean;
  validation_errors: string[];
  recommendations: string[];
}

/**
 * Domain reindex response
 * Sprint 72 Feature 72.2: Domain Reindex API
 */
export interface ReindexDomainAdminResponse {
  message: string;
  domain_name: string;
  documents_queued: number;
}
