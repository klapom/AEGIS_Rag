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
