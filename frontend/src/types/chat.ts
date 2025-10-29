/**
 * Chat API Types
 * Sprint 15 Feature 15.1: TypeScript types for chat API
 */

export type RetrievalMode = 'hybrid' | 'vector' | 'graph' | 'memory';

export interface ChatRequest {
  query: string;
  session_id?: string;
  intent?: string;
  include_sources?: boolean;
  include_tool_calls?: boolean;
}

export interface Source {
  text: string;
  title?: string;
  source?: string;
  score?: number;
  metadata?: Record<string, any>;
  // AegisRAG-specific fields
  chunk_id?: string;
  confidence?: number;
  document_id?: string;
  chunk_index?: number;
  total_chunks?: number;
  retrieval_modes?: string[];
  context?: string;
  entities?: Array<{ name: string; type?: string }>;
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

export type ChatChunkType = 'metadata' | 'token' | 'source' | 'error' | 'complete';

export interface ChatChunk {
  type: ChatChunkType;
  content?: string;
  source?: Source;
  session_id?: string;
  timestamp?: string;
  error?: string;
  code?: string;
  data?: Record<string, any>;
}

export interface SessionInfo {
  session_id: string;
  message_count: number;
  last_activity?: string;
  created_at?: string;
  updated_at?: string;
  last_message?: string;
  title?: string; // Sprint 17 Feature 17.3: Auto-generated or user-edited title
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
