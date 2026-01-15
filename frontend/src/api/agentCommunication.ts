/**
 * Agent Communication API Client
 * Sprint 98 Feature 98.1: Agent Communication Dashboard
 *
 * Provides API functions for:
 * - MessageBus monitoring
 * - Blackboard state retrieval
 * - Orchestration tracking
 * - Communication metrics
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Agent message from MessageBus
 */
export interface AgentMessage {
  id: string;
  timestamp: string;
  sender: string;
  receiver: string;
  message_type: 'SKILL_REQUEST' | 'SKILL_RESPONSE' | 'BROADCAST' | 'EVENT' | 'ERROR';
  payload: Record<string, unknown>;
  duration_ms?: number;
}

/**
 * MessageBus query parameters
 */
export interface MessageQueryParams {
  timeRange?: string; // e.g., '1h', '24h'
  agentId?: string;
  messageType?: string;
  limit?: number;
}

/**
 * MessageBus response
 */
export interface MessageListResponse {
  messages: AgentMessage[];
  total_count: number;
  time_range: string;
}

/**
 * Blackboard namespace state
 */
export interface BlackboardNamespace {
  namespace: string;
  state: Record<string, unknown>;
  last_updated: string;
  agent_id: string | null;
}

/**
 * Blackboard state response
 */
export interface BlackboardStateResponse {
  namespaces: BlackboardNamespace[];
  total_count: number;
}

/**
 * Active orchestration
 */
export interface ActiveOrchestration {
  orchestration_id: string;
  workflow_name: string;
  current_phase: number;
  total_phases: number;
  progress_pct: number;
  status: 'running' | 'paused' | 'completed' | 'failed';
  skills: Array<{
    skill_name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
  }>;
  started_at: string;
  duration_ms?: number;
}

/**
 * Active orchestrations response
 */
export interface ActiveOrchestrationsResponse {
  orchestrations: ActiveOrchestration[];
  total_count: number;
}

/**
 * Orchestration trace event
 */
export interface OrchestrationTraceEvent {
  timestamp: string;
  phase: number;
  event_type: 'phase_start' | 'phase_end' | 'skill_invoked' | 'skill_completed' | 'error';
  skill_name?: string;
  duration_ms?: number;
  details: Record<string, unknown>;
}

/**
 * Orchestration trace response
 */
export interface OrchestrationTraceResponse {
  orchestration_id: string;
  events: OrchestrationTraceEvent[];
  total_duration_ms: number;
}

/**
 * Communication performance metrics
 */
export interface CommunicationMetrics {
  message_latency_p95_ms: number;
  message_latency_avg_ms: number;
  orchestration_duration_avg_ms: number;
  orchestration_duration_p95_ms: number;
  blackboard_writes_last_hour: number;
  active_orchestrations: number;
  messages_per_second: number;
  error_rate_pct: number;
}

/**
 * Fetch agent messages from MessageBus
 *
 * GET /api/v1/agents/messages
 *
 * @param params - Query parameters (time range, agent ID, filters)
 * @returns MessageListResponse with recent messages
 */
export async function fetchAgentMessages(
  params: MessageQueryParams = {}
): Promise<MessageListResponse> {
  const queryParams = new URLSearchParams();

  if (params.timeRange) queryParams.append('timeRange', params.timeRange);
  if (params.agentId) queryParams.append('agentId', params.agentId);
  if (params.messageType) queryParams.append('messageType', params.messageType);
  if (params.limit) queryParams.append('limit', params.limit.toString());

  const response = await fetch(
    `${API_BASE_URL}/api/v1/agents/messages?${queryParams.toString()}`,
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
 * Fetch message details by ID
 *
 * GET /api/v1/agents/messages/{messageId}
 *
 * @param messageId - Message ID
 * @returns AgentMessage with full details
 */
export async function fetchMessageDetails(messageId: string): Promise<AgentMessage> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/messages/${messageId}`, {
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
 * Fetch Blackboard state
 *
 * GET /api/v1/agents/blackboard
 *
 * @returns BlackboardStateResponse with all namespace states
 */
export async function fetchBlackboardState(): Promise<BlackboardStateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/blackboard`, {
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
 * Fetch Blackboard state for specific namespace
 *
 * GET /api/v1/agents/blackboard/{namespace}
 *
 * @param namespace - Namespace identifier
 * @returns BlackboardNamespace state
 */
export async function fetchBlackboardNamespace(namespace: string): Promise<BlackboardNamespace> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/blackboard/${namespace}`, {
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
 * Fetch active orchestrations
 *
 * GET /api/v1/orchestration/active
 *
 * @returns ActiveOrchestrationsResponse with running workflows
 */
export async function fetchActiveOrchestrations(): Promise<ActiveOrchestrationsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/orchestration/active`, {
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
 * Fetch orchestration trace
 *
 * GET /api/v1/orchestration/{id}/trace
 *
 * @param orchestrationId - Orchestration ID
 * @returns OrchestrationTraceResponse with event timeline
 */
export async function fetchOrchestrationTrace(
  orchestrationId: string
): Promise<OrchestrationTraceResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/orchestration/${orchestrationId}/trace`,
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
 * Fetch communication metrics
 *
 * GET /api/v1/orchestration/metrics
 *
 * @returns CommunicationMetrics with performance stats
 */
export async function fetchCommunicationMetrics(): Promise<CommunicationMetrics> {
  const response = await fetch(`${API_BASE_URL}/api/v1/orchestration/metrics`, {
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
