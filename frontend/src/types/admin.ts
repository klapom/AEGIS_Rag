/**
 * Admin API Types
 * Sprint 17 Feature 17.1: Admin UI for Directory Indexing
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
