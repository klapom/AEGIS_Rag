/**
 * E2E Test Fixtures
 * Sprint 15: Test data and mock responses for E2E tests
 */

import type { ChatChunk, Source, SessionInfo, ConversationMessage } from '../../types/chat';

/**
 * Mock SSE Stream Data
 */
export const mockSSEStream = {
  metadata: {
    type: 'metadata' as const,
    session_id: 'test-session-123',
    timestamp: '2025-01-15T10:00:00Z',
    data: {
      intent: 'hybrid',
      session_id: 'test-session-123',
    },
  },

  tokens: [
    { type: 'token' as const, content: 'This ' },
    { type: 'token' as const, content: 'is ' },
    { type: 'token' as const, content: 'a ' },
    { type: 'token' as const, content: 'test ' },
    { type: 'token' as const, content: 'answer.' },
  ],

  sources: [
    {
      type: 'source' as const,
      source: {
        text: 'Test source content 1',
        title: 'Test Document 1',
        source: 'test-doc-1.pdf',
        score: 0.95,
        chunk_id: 'chunk-1',
        confidence: 0.95,
        document_id: 'doc-1',
        chunk_index: 0,
        total_chunks: 5,
        retrieval_modes: ['vector', 'bm25'],
      },
    },
    {
      type: 'source' as const,
      source: {
        text: 'Test source content 2',
        title: 'Test Document 2',
        source: 'test-doc-2.pdf',
        score: 0.87,
        chunk_id: 'chunk-2',
        confidence: 0.87,
        document_id: 'doc-2',
        chunk_index: 1,
        total_chunks: 3,
        retrieval_modes: ['vector', 'graph'],
      },
    },
  ],

  complete: {
    type: 'complete' as const,
    data: {
      latency_seconds: 1.234,
      agent_path: ['router', 'hybrid_retriever', 'generator'],
      total_tokens: 150,
    },
  },

  error: {
    type: 'error' as const,
    error: 'Test error message',
    code: 'TEST_ERROR',
  },
};

/**
 * Mock Sources
 */
export const mockSources: Source[] = [
  {
    text: 'Knowledge graphs represent structured information as entities and relationships.',
    title: 'Introduction to Knowledge Graphs',
    source: 'knowledge-graphs-101.pdf',
    score: 0.92,
    chunk_id: 'kg-chunk-1',
    confidence: 0.92,
    document_id: 'kg-doc-1',
    chunk_index: 0,
    total_chunks: 10,
    retrieval_modes: ['vector', 'graph'],
    entities: [
      { name: 'Knowledge Graph', type: 'concept' },
      { name: 'Entity', type: 'concept' },
      { name: 'Relationship', type: 'concept' },
    ],
  },
  {
    text: 'RAG (Retrieval-Augmented Generation) combines retrieval with language generation.',
    title: 'RAG Architecture',
    source: 'rag-overview.pdf',
    score: 0.88,
    chunk_id: 'rag-chunk-1',
    confidence: 0.88,
    document_id: 'rag-doc-1',
    chunk_index: 2,
    total_chunks: 8,
    retrieval_modes: ['vector', 'bm25'],
    context: 'Information retrieval and natural language processing.',
  },
  {
    text: 'Hybrid search combines multiple retrieval strategies for better results.',
    title: 'Hybrid Retrieval Strategies',
    source: 'hybrid-search.pdf',
    score: 0.85,
    chunk_id: 'hybrid-chunk-1',
    confidence: 0.85,
    document_id: 'hybrid-doc-1',
    chunk_index: 0,
    total_chunks: 5,
    retrieval_modes: ['vector', 'bm25', 'graph'],
  },
];

/**
 * Mock Sessions
 */
export const mockSessions: SessionInfo[] = [
  {
    session_id: 'session-1',
    message_count: 5,
    last_activity: '2025-01-15T12:00:00Z',
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T12:00:00Z',
    last_message: 'What is a knowledge graph?',
  },
  {
    session_id: 'session-2',
    message_count: 3,
    last_activity: '2025-01-14T18:30:00Z',
    created_at: '2025-01-14T18:00:00Z',
    updated_at: '2025-01-14T18:30:00Z',
    last_message: 'Explain RAG architecture',
  },
  {
    session_id: 'session-3',
    message_count: 8,
    last_activity: '2025-01-13T09:15:00Z',
    created_at: '2025-01-13T08:00:00Z',
    updated_at: '2025-01-13T09:15:00Z',
    last_message: 'How does hybrid search work?',
  },
];

/**
 * Mock Conversation History
 */
export const mockConversationHistory: ConversationMessage[] = [
  {
    role: 'user',
    content: 'What is RAG?',
    timestamp: '2025-01-15T10:00:00Z',
  },
  {
    role: 'assistant',
    content: 'RAG stands for Retrieval-Augmented Generation. It combines information retrieval with language generation.',
    timestamp: '2025-01-15T10:00:05Z',
    sources: mockSources.slice(0, 2),
  },
  {
    role: 'user',
    content: 'How does it work?',
    timestamp: '2025-01-15T10:01:00Z',
  },
  {
    role: 'assistant',
    content: 'RAG works by first retrieving relevant documents, then using them as context for generation.',
    timestamp: '2025-01-15T10:01:05Z',
    sources: mockSources.slice(1, 3),
  },
];

/**
 * Mock API Responses
 */
export const mockAPIResponses = {
  chat: {
    answer: 'This is a test answer from the chat API.',
    query: 'test query',
    session_id: 'test-session-123',
    intent: 'hybrid',
    sources: mockSources,
    tool_calls: [],
    metadata: {
      latency_seconds: 1.234,
      agent_path: ['router', 'hybrid_retriever', 'generator'],
    },
  },

  sessions: {
    sessions: mockSessions,
    total_count: mockSessions.length,
  },

  history: {
    session_id: 'session-1',
    messages: mockConversationHistory,
    message_count: mockConversationHistory.length,
  },
};

/**
 * Mock Error Responses
 */
export const mockErrors = {
  networkError: new Error('Network request failed'),
  httpError: new Error('HTTP 500: Internal Server Error'),
  timeoutError: new Error('Request timeout'),
  jsonParseError: new Error('Failed to parse JSON response'),
  sseParseError: new Error('Failed to parse SSE chunk'),
};

/**
 * Sample Queries
 */
export const sampleQueries = {
  valid: [
    'What is a knowledge graph?',
    'Explain RAG architecture',
    'How does hybrid search work?',
    'What is vector search?',
    'Tell me about entity extraction',
  ],

  empty: [
    '',
    '   ',
    '\n',
    '\t',
  ],

  long: [
    'This is a very long query that contains many words and spans multiple lines to test how the system handles longer user inputs. It should still work correctly even though it is much longer than typical queries. The system should be able to process this without any issues and return appropriate results based on the semantic meaning of the entire query.',
  ],

  special: [
    'Query with "quotes"',
    "Query with 'apostrophes'",
    'Query with émojis 🚀🔍💡',
    'Query with special chars: @#$%^&*()',
  ],
};
