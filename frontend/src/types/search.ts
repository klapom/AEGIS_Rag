/**
 * Search Types
 * Sprint 38 Feature 38.2: Conversation Search UI
 */

/**
 * Result from conversation search
 */
export interface ConversationSearchResult {
  session_id: string;
  title: string;
  snippet: string;
  archived_at: string;
  score: number;
}

/**
 * Response from conversation search endpoint
 */
export interface ConversationSearchResponse {
  results: ConversationSearchResult[];
  total: number;
}

/**
 * Request payload for conversation search
 */
export interface ConversationSearchRequest {
  query: string;
  limit?: number;
  min_score?: number;
}

/**
 * Response from archive conversation endpoint
 */
export interface ArchiveConversationResponse {
  success: boolean;
  archived_at: string;
}
