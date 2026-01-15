/**
 * Agent Hierarchy API Client
 * Sprint 98 Feature 98.2: Agent Hierarchy Visualizer
 *
 * Provides API functions for:
 * - Agent hierarchy tree structure
 * - Agent details and performance
 * - Task delegation chain tracing
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * D3.js-compatible hierarchy node (Sprint 99 Backend Format)
 */
export interface D3HierarchyNode {
  agent_id: string;
  name: string;
  level: 'executive' | 'manager' | 'worker';
  status: 'active' | 'idle' | 'busy' | 'offline';
  capabilities: string[];
  child_count: number;
}

/**
 * D3.js-compatible hierarchy edge
 */
export interface D3HierarchyEdge {
  parent_id: string;
  child_id: string;
  relationship: string;
}

/**
 * D3.js-compatible hierarchy response (Sprint 99 Backend Format)
 */
export interface D3HierarchyResponse {
  nodes: D3HierarchyNode[];
  edges: D3HierarchyEdge[];
}

/**
 * Agent hierarchy node (Legacy nested format - deprecated)
 * @deprecated Use D3HierarchyNode instead
 */
export interface HierarchyNode {
  agent_id: string;
  agent_name: string;
  agent_level: 'EXECUTIVE' | 'MANAGER' | 'WORKER';
  skills: string[];
  children: HierarchyNode[];
}

/**
 * Agent hierarchy response (Legacy nested format - deprecated)
 * @deprecated Use D3HierarchyResponse instead
 */
export interface AgentHierarchyResponse {
  root: HierarchyNode;
  total_agents: number;
  levels: {
    executive: number;
    manager: number;
    worker: number;
  };
}

/**
 * Agent details
 */
export interface AgentDetails {
  agent_id: string;
  agent_name: string;
  agent_level: 'EXECUTIVE' | 'MANAGER' | 'WORKER';
  skills: string[];
  active_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  success_rate_pct: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  current_load: number;
  max_concurrent_tasks: number;
  status: 'active' | 'idle' | 'busy' | 'offline';
  last_active: string;
  parent_agent_id: string | null;
  child_agent_ids: string[];
}

/**
 * Current task information
 */
export interface CurrentTask {
  task_id: string;
  task_name: string;
  status: 'running' | 'paused' | 'completed' | 'failed';
  started_at: string;
  duration_ms?: number;
  assigned_skill: string;
}

/**
 * Current tasks response
 */
export interface CurrentTasksResponse {
  tasks: CurrentTask[];
  total_count: number;
}

/**
 * Agent performance metrics
 */
export interface AgentPerformance {
  agent_id: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  success_rate_pct: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  current_load: number;
  max_load_seen: number;
  uptime_hours: number;
  last_error?: string;
  last_error_timestamp?: string;
}

/**
 * Delegation chain step
 */
export interface DelegationStep {
  agent_id: string;
  agent_name: string;
  agent_level: 'EXECUTIVE' | 'MANAGER' | 'WORKER';
  delegated_at: string;
  duration_ms?: number;
  skill_invoked?: string;
}

/**
 * Delegation chain response
 */
export interface DelegationChainResponse {
  task_id: string;
  task_name: string;
  chain: DelegationStep[];
  total_delegation_hops: number;
  total_duration_ms: number;
}

/**
 * Fetch agent hierarchy tree (D3.js format)
 *
 * GET /api/v1/agents/hierarchy
 *
 * @returns D3HierarchyResponse with nodes and edges
 */
export async function fetchAgentHierarchy(): Promise<D3HierarchyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/hierarchy`, {
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
 * Fetch agent details by ID
 *
 * GET /api/v1/agents/{id}/details
 *
 * @param agentId - Agent identifier
 * @returns AgentDetails with full information
 */
export async function fetchAgentDetails(agentId: string): Promise<AgentDetails> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/${agentId}/details`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  const backendData = await response.json();

  // Sprint 100 Fix #7: Map backend field names to frontend expectations
  return {
    agent_id: backendData.agent_id,
    agent_name: backendData.name, // Backend: 'name' → Frontend: 'agent_name'
    agent_level: (backendData.level?.toUpperCase() || 'WORKER') as 'EXECUTIVE' | 'MANAGER' | 'WORKER', // Backend: lowercase → Frontend: UPPERCASE
    skills: backendData.skills || [],
    active_tasks: Array.isArray(backendData.active_tasks) ? backendData.active_tasks.length : 0, // Backend: array → Frontend: count
    completed_tasks: backendData.performance?.tasks_completed || 0,
    failed_tasks: backendData.performance?.tasks_failed || 0,
    success_rate_pct: (backendData.performance?.success_rate || 0) * 100, // Backend: decimal → Frontend: percentage
    avg_latency_ms: backendData.performance?.avg_duration_ms || 0,
    p95_latency_ms: (backendData.performance?.avg_duration_ms || 0) * 1.5, // Estimated: 1.5x avg
    current_load: backendData.performance?.queue_size || 0,
    max_concurrent_tasks: 10, // Default reasonable limit (not provided by backend)
    status: backendData.status || 'offline',
    last_active: backendData.last_active || new Date().toISOString(),
    parent_agent_id: backendData.parent_id || null,
    child_agent_ids: backendData.child_ids || [],
  };
}

/**
 * Fetch agent's current tasks
 *
 * GET /api/v1/agents/{id}/current-tasks
 *
 * @param agentId - Agent identifier
 * @returns CurrentTasksResponse with active tasks
 */
export async function fetchAgentCurrentTasks(agentId: string): Promise<CurrentTasksResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/${agentId}/current-tasks`, {
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
 * Fetch agent performance metrics
 *
 * GET /api/v1/agents/{id}/performance
 *
 * @param agentId - Agent identifier
 * @returns AgentPerformance metrics
 */
export async function fetchAgentPerformance(agentId: string): Promise<AgentPerformance> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/${agentId}/performance`, {
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
 * Fetch task delegation chain
 *
 * GET /api/v1/agents/task/{taskId}/delegation-chain
 *
 * @param taskId - Task identifier
 * @returns DelegationChainResponse showing full delegation path
 */
export async function fetchTaskDelegationChain(taskId: string): Promise<DelegationChainResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/task/${taskId}/delegation-chain`, {
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
