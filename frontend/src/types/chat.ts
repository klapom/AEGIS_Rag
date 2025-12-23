/**
 * Chat API Types
 * Sprint 15 Feature 15.1: TypeScript types for chat API
 * Sprint 62 Feature 62.4: Section-aware citations
 */

import type { SectionMetadata, DocumentType } from './section';

export type RetrievalMode = 'hybrid' | 'vector' | 'graph' | 'memory';

export interface ChatRequest {
  query: string;
  session_id?: string;
  intent?: string;
  include_sources?: boolean;
  include_tool_calls?: boolean;
  namespaces?: string[];  // Sprint 42: Filter search by namespace/project
}

export interface Source {
  text: string;
  title?: string;
  source?: string;
  score?: number;
  metadata?: Record<string, unknown>;
  // AegisRAG-specific fields
  chunk_id?: string;
  confidence?: number;
  document_id?: string;
  chunk_index?: number;
  total_chunks?: number;
  retrieval_modes?: string[];
  context?: string;
  entities?: Array<{ name: string; type?: string }>;
  // Sprint 62.4: Section metadata
  section?: SectionMetadata;
  document_type?: DocumentType;
}

export interface ToolCallInfo {
  tool_name: string;
  server: string;
  arguments: Record<string, any>;
  result?: any;
  duration_ms: number;
  success: boolean;
  error?: string;
}

export interface ChatResponse {
  answer: string;
  query: string;
  session_id: string;
  intent?: string;
  sources: Source[];
  tool_calls: ToolCallInfo[];
  metadata: Record<string, any>;
}

// SSE Streaming Types

/**
 * SSE Chunk Types
 * Sprint 15: Original types (metadata, token, source, error, complete)
 * Sprint 48: Added phase_event for real-time thinking display
 * Sprint 51: Added answer_chunk and reasoning_complete for structured responses
 * Sprint 52: Added citation_map for real-time citation streaming
 */
export type ChatChunkType =
  | 'metadata'
  | 'token'
  | 'source'
  | 'error'
  | 'complete'
  | 'phase_event'      // Sprint 48: Real-time phase progress
  | 'answer_chunk'     // Sprint 51: Structured answer with citations
  | 'reasoning_complete' // Sprint 51: Final reasoning summary with all phases
  | 'citation_map';    // Sprint 52: Citation metadata streamed before answer tokens

/**
 * Citation metadata for a single source
 * Sprint 27 Feature 27.10: Inline Source Citations
 * Sprint 62 Feature 62.4: Section-aware citations
 */
export interface CitationMetadata {
  text: string;
  source: string;
  title: string;
  score: number;
  metadata: Record<string, unknown>;
  // Sprint 62.4: Section metadata
  section?: SectionMetadata;
  document_type?: DocumentType;
}

/**
 * Citation map: citation number (1, 2, 3...) -> metadata
 * Sprint 27 Feature 27.10: Inline Source Citations
 */
export type CitationMap = Record<number, CitationMetadata>;

export interface ChatChunk {
  type: ChatChunkType;
  content?: string;
  source?: Source;
  session_id?: string;
  timestamp?: string;
  error?: string;
  code?: string;
  data?: Record<string, any> & {
    // Sprint 27 Feature 27.10: Citation map in metadata chunks
    citation_map?: CitationMap;
    citations_count?: number;
  };
}

export interface SessionInfo {
  session_id: string;
  message_count: number;
  last_activity?: string;
  created_at?: string;
  updated_at?: string;
  last_message?: string;
  title?: string; // Sprint 17 Feature 17.3: Auto-generated or user-edited title
  messages?: ConversationMessage[]; // Sprint 19: Full message history for title extraction
}

export interface SessionListResponse {
  sessions: SessionInfo[];
  total_count: number;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  sources?: Source[];
}

export interface ConversationHistoryResponse {
  session_id: string;
  messages: ConversationMessage[];
  message_count: number;
}
