/**
 * Test Data Fixtures for Sprint 97-98 E2E Tests
 *
 * Provides realistic test data for:
 * - Skill Management tests (03-skill-management.spec.ts)
 * - Governance UI tests (10-governance.spec.ts)
 * - Agent Communication & Hierarchy tests (11-agent-hierarchy.spec.ts)
 */

// ============================================================================
// Skill Management Test Data
// ============================================================================

export const TEST_SKILLS = [
  {
    name: 'retrieval',
    version: '1.2.0',
    description: 'Vector & graph retrieval skill',
    author: 'AegisRAG',
    isActive: true,
    toolsCount: 3,
    triggersCount: 4,
    icon: '🔍',
    triggers: ['search', 'find', 'lookup', 'retrieve'],
    tools: ['vector_search', 'graph_query', 'reranker'],
    dependencies: ['qdrant', 'neo4j', 'embedding_service'],
  },
  {
    name: 'synthesis',
    version: '1.1.3',
    description: 'Answer generation and summarization',
    author: 'AegisRAG',
    isActive: true,
    toolsCount: 2,
    triggersCount: 3,
    icon: '📝',
    triggers: ['generate', 'summarize', 'answer'],
    tools: ['llm_generate', 'prompt_template'],
    dependencies: ['llm_service'],
  },
  {
    name: 'reflection',
    version: '1.0.0',
    description: 'Self-critique and validation loop',
    author: 'AegisRAG',
    isActive: false,
    toolsCount: 1,
    triggersCount: 3,
    icon: '🤔',
    triggers: ['critique', 'validate', 'evaluate'],
    tools: ['llm_evaluator'],
    dependencies: ['llm_service'],
  },
  {
    name: 'web_search',
    version: '1.1.0',
    description: 'Web browsing with browser-use',
    author: 'AegisRAG',
    isActive: true,
    toolsCount: 2,
    triggersCount: 5,
    icon: '🌐',
    triggers: ['search', 'web', 'browse', 'lookup', 'research'],
    tools: ['browser', 'search_api'],
    dependencies: ['browser_use'],
  },
  {
    name: 'hallucination_monitor',
    version: '1.0.0',
    description: 'Detect unsupported claims',
    author: 'AegisRAG',
    isActive: true,
    toolsCount: 0,
    triggersCount: 0,
    icon: '⚠️',
    triggers: [],
    tools: [],
    dependencies: ['llm_service'],
  },
  {
    name: 'automation',
    version: '0.9.0',
    description: 'Task automation with tool chains',
    author: 'AegisRAG',
    isActive: false,
    toolsCount: 5,
    triggersCount: 4,
    icon: '🔧',
    triggers: ['automate', 'schedule', 'execute', 'run'],
    tools: ['task_scheduler', 'shell_executor', 'api_caller', 'file_handler', 'database_connector'],
    dependencies: ['task_queue'],
  },
];

export const SKILL_CONFIG_TEMPLATES = {
  retrieval: `
embedding:
  model: bge-m3
  dimension: 1024
search:
  top_k: 10
  modes:
    - vector
    - hybrid
  rrf_k: 60
neo4j:
  max_hops: 2
  entity_limit: 50
reranking:
  enabled: true
  model: cross-encoder/ms-marco
  top_n: 5
`,
  synthesis: `
llm:
  model: Nemotron3
  max_tokens: 2048
  temperature: 0.7
  top_p: 0.9
prompting:
  use_cot: true
  include_sources: true
formatting:
  cite_sources: true
`,
  web_search: `
browser:
  headless: true
  timeout: 30
domains:
  allowed:
    - "*.wikipedia.org"
    - "*.github.com"
    - "*.arxiv.org"
  blocked:
    - "*.malware.com"
    - "*.phishing.net"
`,
};

// ============================================================================
// GDPR & Compliance Test Data
// ============================================================================

export const TEST_CONSENTS = [
  {
    id: 'consent_001',
    userId: 'user_123',
    purpose: 'Customer Support',
    legalBasis: 'Contract',
    dataCategories: ['identifier', 'contact'],
    granted: '2025-12-01T00:00:00Z',
    expires: '2026-12-01T00:00:00Z',
    status: 'active',
    skillRestrictions: ['customer_support'],
  },
  {
    id: 'consent_002',
    userId: 'user_456',
    purpose: 'Marketing Communications',
    legalBasis: 'Consent',
    dataCategories: ['contact', 'behavioral'],
    granted: '2026-01-10T00:00:00Z',
    expires: null,
    status: 'active',
    skillRestrictions: [],
  },
  {
    id: 'consent_003',
    userId: 'user_789',
    purpose: 'Research Participation',
    legalBasis: 'Consent',
    dataCategories: ['identifier', 'health'],
    granted: '2025-06-15T00:00:00Z',
    expires: '2026-06-15T00:00:00Z',
    status: 'active',
    skillRestrictions: ['research', 'analysis'],
  },
];

export const TEST_AUDIT_EVENTS = [
  {
    id: 'evt_001',
    timestamp: '2026-01-15T14:25:32Z',
    type: 'SKILL_EXECUTED',
    actor: 'user_123',
    resource: 'query_7a3f9b',
    action: 'retrieval skill → vector search',
    outcome: 'success',
    duration: 120,
    hash: '7a3f9b9c...',
    chainVerified: true,
  },
  {
    id: 'evt_002',
    timestamp: '2026-01-15T14:25:30Z',
    type: 'DATA_READ',
    actor: 'retrieval skill',
    resource: 'document_7f3a',
    action: 'read document chunk',
    outcome: 'success',
    dataCategories: ['identifier', 'contact'],
    hash: '5d2c8a7b...',
    chainVerified: true,
  },
  {
    id: 'evt_003',
    timestamp: '2026-01-15T14:25:20Z',
    type: 'AUTH_SUCCESS',
    actor: 'user_123',
    resource: '/api/v1/chat',
    action: 'authenticate',
    outcome: 'success',
    ipAddress: '192.168.1.1',
    hash: '9e1b4f2c...',
    chainVerified: true,
  },
  {
    id: 'evt_004',
    timestamp: '2026-01-15T14:24:10Z',
    type: 'POLICY_VIOLATION',
    actor: 'user_456',
    resource: 'shell_exec',
    action: 'attempt shell execution',
    outcome: 'blocked',
    reason: 'insufficient permissions',
    hash: '3c7d2a1e...',
    chainVerified: true,
  },
];

export const TEST_DECISION_TRACES = [
  {
    id: 'trace_1737052332_decision.routed',
    timestamp: '2026-01-15T14:25:32Z',
    query: 'What are the latest quantum computing trends?',
    intent: 'RESEARCH',
    intentConfidence: 0.92,
    skillsSelected: ['retrieval', 'web_search', 'synthesis'],
    retrievalMode: 'hybrid',
    chunksRetrieved: 15,
    chunksUsed: 8,
    sources: [
      { document: 'quantum_computing_2025.pdf', relevance: 0.94, pages: '12-14' },
      { document: 'arxiv_2501_trends.pdf', relevance: 0.89, pages: '3-5' },
      { document: 'nature_qc_review.pdf', relevance: 0.82, pages: '8' },
    ],
    responseLength: 487,
    generationTime: 1200,
    overallConfidence: 0.87,
    hallucationRisk: 0.08,
  },
  {
    id: 'trace_1737051845_decision.simple',
    timestamp: '2026-01-15T14:10:45Z',
    query: 'What is machine learning?',
    intent: 'QUERY',
    intentConfidence: 0.98,
    skillsSelected: ['retrieval', 'synthesis'],
    retrievalMode: 'vector',
    chunksRetrieved: 5,
    chunksUsed: 4,
    sources: [
      { document: 'ml_fundamentals.pdf', relevance: 0.96, pages: '1-3' },
    ],
    responseLength: 245,
    generationTime: 450,
    overallConfidence: 0.95,
    hallucationRisk: 0.02,
  },
];

export const TEST_SKILL_CERTIFICATIONS = [
  {
    name: 'retrieval',
    level: 'Enterprise',
    version: '1.2.0',
    validUntil: '2027-01-15',
    lastValidated: '2026-01-15',
    checks: {
      gdpr: 'passed',
      security: 'passed',
      audit: 'passed',
      explainability: 'passed',
    },
  },
  {
    name: 'synthesis',
    level: 'Enterprise',
    version: '1.1.3',
    validUntil: '2027-01-10',
    lastValidated: '2026-01-10',
    checks: {
      gdpr: 'passed',
      security: 'passed',
      audit: 'passed',
      explainability: 'passed',
    },
  },
  {
    name: 'web_search',
    level: 'Standard',
    version: '1.0.5',
    validUntil: '2026-12-20',
    lastValidated: '2025-12-20',
    checks: {
      gdpr: 'warning',
      security: 'passed',
      audit: 'passed',
      explainability: 'warning',
    },
    issues: ['GDPR purpose declaration incomplete'],
  },
  {
    name: 'automation',
    level: 'Basic',
    version: '0.9.0',
    validUntil: '2026-03-15',
    lastValidated: '2025-03-15',
    checks: {
      gdpr: 'failed',
      security: 'failed',
      audit: 'passed',
      explainability: 'warning',
    },
    issues: [
      'No audit integration',
      'Security patterns: blocked eval() found',
    ],
  },
];

// ============================================================================
// Agent Hierarchy & Communication Test Data
// ============================================================================

export const TEST_AGENT_HIERARCHY = {
  executive: {
    id: 'agent_exec_001',
    name: 'Executive Director',
    level: 'executive',
    skills: ['planner', 'orchestrator'],
    status: 'active',
  },
  managers: [
    {
      id: 'agent_mgr_001',
      name: 'Research Manager',
      level: 'manager',
      parent: 'agent_exec_001',
      skills: ['research', 'web_search', 'fact_check'],
      workers: ['agent_w_001', 'agent_w_002', 'agent_w_003'],
      activeTaskCount: 2,
      successRate: 0.87,
      avgLatency: 450,
      tasksCompleted: 142,
    },
    {
      id: 'agent_mgr_002',
      name: 'Analysis Manager',
      level: 'manager',
      parent: 'agent_exec_001',
      skills: ['analysis', 'validation', 'comparison'],
      workers: ['agent_w_004', 'agent_w_005', 'agent_w_006'],
      activeTaskCount: 1,
      successRate: 0.92,
      avgLatency: 380,
      tasksCompleted: 156,
    },
    {
      id: 'agent_mgr_003',
      name: 'Synthesis Manager',
      level: 'manager',
      parent: 'agent_exec_001',
      skills: ['synthesis', 'summarization', 'reporting'],
      workers: ['agent_w_007', 'agent_w_008', 'agent_w_009'],
      activeTaskCount: 0,
      successRate: 0.89,
      avgLatency: 520,
      tasksCompleted: 128,
    },
  ],
  workers: [
    {
      id: 'agent_w_001',
      name: 'Retrieval Worker 1',
      level: 'worker',
      parent: 'agent_mgr_001',
      skills: ['vector_search'],
      status: 'idle',
    },
    {
      id: 'agent_w_002',
      name: 'Retrieval Worker 2',
      level: 'worker',
      parent: 'agent_mgr_001',
      skills: ['vector_search'],
      status: 'idle',
    },
    {
      id: 'agent_w_003',
      name: 'Web Worker',
      level: 'worker',
      parent: 'agent_mgr_001',
      skills: ['web_search'],
      status: 'idle',
    },
    // ... add remaining workers (agent_w_004 through agent_w_009)
  ],
};

export const TEST_AGENT_MESSAGES = [
  {
    id: 'msg_001',
    timestamp: '2026-01-15T14:23:45Z',
    sender: 'agent_mgr_001',
    recipient: 'agent_w_001',
    type: 'SKILL_REQUEST',
    content: { skill: 'retrieval', contextBudget: 2000 },
  },
  {
    id: 'msg_002',
    timestamp: '2026-01-15T14:23:46Z',
    sender: 'agent_w_001',
    recipient: 'agent_mgr_001',
    type: 'SKILL_RESPONSE',
    content: { result: 'retrieved 5 chunks', duration: 120 },
  },
  {
    id: 'msg_003',
    timestamp: '2026-01-15T14:23:47Z',
    sender: 'agent_exec_001',
    recipient: 'ALL',
    type: 'BROADCAST',
    content: { message: 'Phase 2 complete, starting Phase 3' },
  },
];

export const TEST_BLACKBOARD_STATE = {
  retrieval: {
    results: ['chunk_1', 'chunk_2', 'chunk_3'],
    confidence: 0.92,
    sources: 2,
  },
  synthesis: {
    summary: 'Generated response based on retrieved context',
    confidence: 0.87,
    tokensUsed: 487,
  },
  reflection: {
    issues: [],
    confidence: 0.95,
    validated: true,
  },
};

export const TEST_ORCHESTRATIONS = [
  {
    id: 'research_workflow_7a2b',
    name: 'Research Workflow',
    currentPhase: 2,
    totalPhases: 3,
    progress: 0.67,
    status: 'running',
    skills: [
      { name: 'retrieval', status: 'completed' },
      { name: 'web_search', status: 'completed' },
      { name: 'synthesis', status: 'running' },
    ],
    startTime: '2026-01-15T14:20:00Z',
    estimatedEndTime: '2026-01-15T14:22:00Z',
  },
  {
    id: 'analysis_task_9f4c',
    name: 'Analysis Task',
    currentPhase: 1,
    totalPhases: 2,
    progress: 0.40,
    status: 'running',
    skills: [
      { name: 'analysis', status: 'running' },
      { name: 'validation', status: 'pending' },
    ],
    startTime: '2026-01-15T14:21:00Z',
    estimatedEndTime: '2026-01-15T14:24:00Z',
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generate random skill ID
 */
export function generateSkillId(): string {
  return `skill_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate random consent ID
 */
export function generateConsentId(): string {
  return `consent_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate random audit event ID
 */
export function generateAuditEventId(): string {
  return `evt_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate random agent ID
 */
export function generateAgentId(): string {
  return `agent_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate random trace ID
 */
export function generateTraceId(): string {
  const timestamp = Math.floor(Date.now() / 1000);
  return `trace_${timestamp}_decision.routed`;
}

/**
 * Create test skill with optional overrides
 */
export function createTestSkill(overrides: Partial<typeof TEST_SKILLS[0]> = {}) {
  return {
    ...TEST_SKILLS[0],
    name: generateSkillId(),
    ...overrides,
  };
}

/**
 * Create test consent with optional overrides
 */
export function createTestConsent(overrides: Partial<typeof TEST_CONSENTS[0]> = {}) {
  return {
    ...TEST_CONSENTS[0],
    id: generateConsentId(),
    ...overrides,
  };
}

/**
 * Create test audit event with optional overrides
 */
export function createTestAuditEvent(overrides: Partial<typeof TEST_AUDIT_EVENTS[0]> = {}) {
  return {
    ...TEST_AUDIT_EVENTS[0],
    id: generateAuditEventId(),
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

/**
 * Create test trace with optional overrides
 */
export function createTestTrace(overrides: Partial<typeof TEST_DECISION_TRACES[0]> = {}) {
  return {
    ...TEST_DECISION_TRACES[0],
    id: generateTraceId(),
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}
