/**
 * Test Data Fixtures for E2E Tests
 * Sprint 69 Feature 69.1: E2E Test Stabilization
 *
 * Provides reusable test data for consistent testing across all E2E suites
 * - Sample documents
 * - Test queries (domain-specific)
 * - Expected responses
 * - Mock data for memory, graph, and chat tests
 */

/**
 * Sample Test Documents
 * Used for ingestion and retrieval tests
 */
export const TEST_DOCUMENTS = {
  /**
   * OMNITRACKER domain document
   * Used for domain-specific query tests
   */
  OMNITRACKER_SMC: {
    id: 'test-doc-omnitracker-smc',
    title: 'OMNITRACKER SMC Architecture',
    content: `
# OMNITRACKER SMC (Server Management Console)

The OMNITRACKER SMC is a central management interface for administering OMNITRACKER servers.

## Key Components

1. **Application Server**: Handles business logic and workflow processing
2. **Database Server**: PostgreSQL or Oracle database for persistent storage
3. **Web Client**: Browser-based interface for end users
4. **Load Balancer**: Distributes requests across multiple application servers

## Configuration

### Database Connection
- Connection pooling: 10-50 connections
- Timeout: 30 seconds
- Automatic retry on connection failure

### Load Balancing
- Round-robin algorithm
- Health check interval: 10 seconds
- Failover support for high availability

## Workflow Engine
The workflow engine processes tickets through customizable workflows with:
- Conditional routing
- Automated actions
- Email notifications
- SLA tracking
    `.trim(),
    metadata: {
      source: 'test-data',
      domain: 'omnitracker',
      doc_type: 'technical',
    },
  },

  /**
   * RAG system documentation
   * Used for general RAG questions
   */
  RAG_BASICS: {
    id: 'test-doc-rag-basics',
    title: 'RAG System Fundamentals',
    content: `
# Retrieval-Augmented Generation (RAG)

RAG is a hybrid approach combining information retrieval with language generation.

## How RAG Works

1. **Retrieval Phase**: Search for relevant documents using vector similarity
2. **Augmentation Phase**: Inject retrieved context into LLM prompt
3. **Generation Phase**: LLM generates response based on provided context

## Key Benefits
- Reduces hallucinations by grounding responses in real data
- Allows knowledge updates without retraining
- Provides citations for transparency

## Components
- Vector database (e.g., Qdrant, Pinecone)
- Embedding model (e.g., BGE-M3, OpenAI embeddings)
- LLM (e.g., GPT-4, Llama, Gemini)
    `.trim(),
    metadata: {
      source: 'test-data',
      domain: 'rag',
      doc_type: 'educational',
    },
  },

  /**
   * Short document for quick tests
   */
  HELLO_WORLD: {
    id: 'test-doc-hello',
    title: 'Hello World',
    content: 'Hello World! This is a test document.',
    metadata: {
      source: 'test-data',
      domain: 'test',
      doc_type: 'minimal',
    },
  },
};

/**
 * Test Queries
 * Domain-specific queries for testing retrieval and generation
 */
export const TEST_QUERIES = {
  // OMNITRACKER domain queries
  OMNITRACKER: {
    SMC_OVERVIEW: 'What is the OMNITRACKER SMC and how does it work?',
    LOAD_BALANCING: 'How do I configure load balancing in OMNITRACKER?',
    DATABASE_CONNECTIONS: 'How does OMNITRACKER handle database connections?',
    COMPONENTS: 'What are the main components of OMNITRACKER?',
    WEB_CLIENT: 'What is the OMNITRACKER Web Client architecture?',
    SERVER_SETUP: 'How do I set up OMNITRACKER servers?',
    APPLICATION_SERVER: 'What is the OMNITRACKER Application Server?',
    WORKFLOW_ENGINE: 'What is the OMNITRACKER workflow engine?',
  },

  // RAG system queries
  RAG: {
    BASICS: 'What is RAG?',
    HOW_IT_WORKS: 'How does RAG work?',
    BENEFITS: 'What are the benefits of RAG?',
    COMPONENTS: 'What are the main components of a RAG system?',
    RETRIEVAL: 'How does retrieval work in RAG?',
  },

  // Follow-up questions (context-dependent)
  FOLLOWUP: {
    CLARIFICATION: 'Can you explain that in more detail?',
    HOW: 'How does it work?',
    WHY: 'Why is that important?',
    EXAMPLES: 'Can you give me an example?',
    ALTERNATIVES: 'What are the alternatives?',
  },

  // Simple queries
  SIMPLE: {
    GREETING: 'Hello',
    THANKS: 'Thank you',
    YES: 'Yes',
    NO: 'No',
  },
};

/**
 * Expected Response Patterns
 * Patterns to verify in responses
 */
export const EXPECTED_PATTERNS = {
  OMNITRACKER: {
    SMC: /SMC|Server Management Console|management interface/i,
    LOAD_BALANCING: /load balanc/i,
    DATABASE: /database|PostgreSQL|Oracle|connection/i,
    COMPONENTS: /Application Server|Database Server|Web Client/i,
    WORKFLOW: /workflow|engine|ticket/i,
  },

  RAG: {
    DEFINITION: /retrieval|augmented|generation/i,
    RETRIEVAL: /vector|similarity|search|embed/i,
    BENEFITS: /hallucination|citation|knowledge/i,
    COMPONENTS: /vector database|embedding|LLM/i,
  },
};

/**
 * Mock Memory Data
 * For memory consolidation tests
 */
export const MOCK_MEMORY = {
  SHORT_TERM: [
    {
      id: 'mem-1',
      content: 'User asked about OMNITRACKER SMC',
      timestamp: new Date().toISOString(),
      type: 'short_term',
    },
    {
      id: 'mem-2',
      content: 'User configured load balancing',
      timestamp: new Date().toISOString(),
      type: 'short_term',
    },
  ],

  LONG_TERM: [
    {
      id: 'mem-lt-1',
      content: 'User frequently asks about OMNITRACKER configuration',
      timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      type: 'long_term',
      consolidated: true,
    },
  ],

  EPISODIC: [
    {
      id: 'mem-ep-1',
      content: 'Session on 2024-01-15: User explored OMNITRACKER architecture',
      timestamp: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      type: 'episodic',
    },
  ],
};

/**
 * Mock Graph Data
 * For graph reasoning tests
 */
export const MOCK_GRAPH = {
  ENTITIES: [
    {
      id: 'entity-1',
      type: 'Component',
      name: 'OMNITRACKER SMC',
      properties: {
        description: 'Server Management Console',
        category: 'management',
      },
    },
    {
      id: 'entity-2',
      type: 'Component',
      name: 'Application Server',
      properties: {
        description: 'Business logic processor',
        category: 'server',
      },
    },
    {
      id: 'entity-3',
      type: 'Component',
      name: 'Database Server',
      properties: {
        description: 'Data persistence layer',
        category: 'database',
      },
    },
  ],

  RELATIONSHIPS: [
    {
      id: 'rel-1',
      source: 'entity-1',
      target: 'entity-2',
      type: 'MANAGES',
      properties: {},
    },
    {
      id: 'rel-2',
      source: 'entity-2',
      target: 'entity-3',
      type: 'CONNECTS_TO',
      properties: {
        connection_type: 'database',
      },
    },
  ],
};

/**
 * Mock Chat History
 * For conversation persistence tests
 */
export const MOCK_CHAT_HISTORY = {
  SIMPLE_CONVERSATION: [
    {
      role: 'user',
      content: TEST_QUERIES.OMNITRACKER.SMC_OVERVIEW,
      timestamp: new Date(Date.now() - 60000).toISOString(),
    },
    {
      role: 'assistant',
      content:
        'The OMNITRACKER SMC (Server Management Console) is a central management interface...',
      timestamp: new Date(Date.now() - 55000).toISOString(),
      citations: [
        {
          document_id: TEST_DOCUMENTS.OMNITRACKER_SMC.id,
          section: 'Overview',
          score: 0.95,
        },
      ],
    },
  ],

  MULTI_TURN: [
    {
      role: 'user',
      content: TEST_QUERIES.RAG.BASICS,
      timestamp: new Date(Date.now() - 120000).toISOString(),
    },
    {
      role: 'assistant',
      content: 'RAG stands for Retrieval-Augmented Generation...',
      timestamp: new Date(Date.now() - 115000).toISOString(),
    },
    {
      role: 'user',
      content: TEST_QUERIES.FOLLOWUP.HOW,
      timestamp: new Date(Date.now() - 60000).toISOString(),
    },
    {
      role: 'assistant',
      content: 'RAG works in three phases: retrieval, augmentation, and generation...',
      timestamp: new Date(Date.now() - 55000).toISOString(),
    },
  ],
};

/**
 * Test Timeouts
 * Consistent timeout values across tests
 */
export const TEST_TIMEOUTS = {
  /** Standard LLM response timeout (90s) */
  LLM_RESPONSE: 90000,
  /** Follow-up question generation timeout (15s) */
  FOLLOWUP_GENERATION: 15000,
  /** Memory consolidation timeout (30s) */
  MEMORY_CONSOLIDATION: 30000,
  /** Graph query timeout (10s) */
  GRAPH_QUERY: 10000,
  /** Page load timeout (30s) */
  PAGE_LOAD: 30000,
  /** Short wait for UI updates (500ms) */
  UI_UPDATE: 500,
  /** Network idle timeout (10s) */
  NETWORK_IDLE: 10000,
};

/**
 * Test Assertions
 * Common assertion helpers
 */
export const ASSERTIONS = {
  /**
   * Verify response contains expected pattern
   */
  responseContains(response: string, pattern: RegExp | string): boolean {
    if (typeof pattern === 'string') {
      return response.toLowerCase().includes(pattern.toLowerCase());
    }
    return pattern.test(response);
  },

  /**
   * Verify citation count is within expected range
   */
  citationCountValid(count: number, min: number = 1, max: number = 10): boolean {
    return count >= min && count <= max;
  },

  /**
   * Verify follow-up questions are valid (3-5 questions, all are questions)
   */
  followupQuestionsValid(questions: string[]): boolean {
    if (questions.length < 3 || questions.length > 5) return false;
    return questions.every((q) => q.includes('?') && q.length > 5);
  },

  /**
   * Verify memory item structure
   */
  memoryItemValid(item: any): boolean {
    return (
      item &&
      typeof item.id === 'string' &&
      typeof item.content === 'string' &&
      typeof item.timestamp === 'string' &&
      typeof item.type === 'string'
    );
  },
};

/**
 * Test Utilities
 * Helper functions for tests
 */
export const TEST_UTILS = {
  /**
   * Generate unique test ID
   */
  generateTestId(prefix: string = 'test'): string {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(7)}`;
  },

  /**
   * Wait for condition with timeout
   */
  async waitForCondition(
    condition: () => boolean | Promise<boolean>,
    timeout: number = 5000,
    interval: number = 100
  ): Promise<void> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      if (await condition()) return;
      await new Promise((resolve) => setTimeout(resolve, interval));
    }
    throw new Error(`Condition not met within ${timeout}ms`);
  },

  /**
   * Create delay for testing async behavior
   */
  delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  },
};
