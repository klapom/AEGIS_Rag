/**
 * Skills & Tools Event Types
 * Sprint 119 Feature 119.1: Chat Integration for Skills/Tools Execution Display
 *
 * TypeScript interfaces for skills/tools SSE streaming events in chat
 */

/**
 * Skill activation event - when a skill is activated for execution
 */
export interface SkillActivationEvent {
  /** Name of the activated skill */
  skill: string;
  /** Version of the skill */
  version?: string;
  /** Reason why this skill was activated */
  reason?: string;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Tool execution status types
 */
export type ToolExecutionStatus =
  | 'running'
  | 'success'
  | 'error'
  | 'timeout';

/**
 * Tool use event - when a tool starts executing
 */
export interface ToolUseEvent {
  /** Name of the tool being executed */
  tool: string;
  /** Server executing the tool (bash, python, browser, etc.) */
  server?: string;
  /** Tool parameters/input */
  parameters: Record<string, unknown>;
  /** Unique execution ID for tracking multiple concurrent tool executions */
  execution_id?: string;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Tool progress event - progress updates during long-running tool execution
 */
export interface ToolProgressEvent {
  /** Name of the tool */
  tool: string;
  /** Progress percentage (0-100) */
  progress: number;
  /** Optional progress message */
  message?: string;
  /** Execution ID if multiple concurrent executions */
  execution_id?: string;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Tool result event - tool execution completed with result
 */
export interface ToolResultEvent {
  /** Name of the tool */
  tool: string;
  /** Server that executed the tool */
  server?: string;
  /** Execution result (can be string, object, etc.) */
  result: unknown;
  /** Whether execution was successful */
  success: boolean;
  /** Error message if execution failed */
  error?: string;
  /** Execution ID if multiple concurrent executions */
  execution_id?: string;
  /** Duration in milliseconds */
  duration_ms?: number;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Tool error event - tool execution failed
 */
export interface ToolErrorEvent {
  /** Name of the tool */
  tool: string;
  /** Error message */
  error: string;
  /** Error details/stack trace */
  details?: string;
  /** Execution ID if multiple concurrent executions */
  execution_id?: string;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Tool timeout event - tool execution timed out
 */
export interface ToolTimeoutEvent {
  /** Name of the tool */
  tool: string;
  /** Timeout duration in seconds */
  timeout: number;
  /** Execution ID if multiple concurrent executions */
  execution_id?: string;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Skill activation failed event
 */
export interface SkillActivationFailedEvent {
  /** Name of the skill that failed to activate */
  skill: string;
  /** Reason for failure */
  reason: string;
  /** ISO timestamp */
  timestamp: string;
}

/**
 * Combined tool execution state for display
 * This aggregates all events for a single tool execution
 */
export interface ToolExecutionState {
  /** Tool name */
  tool: string;
  /** Server executing the tool */
  server: string;
  /** Current status */
  status: ToolExecutionStatus;
  /** Input parameters */
  input: Record<string, unknown>;
  /** Output result (if completed) */
  output?: unknown;
  /** Error message (if failed) */
  error?: string;
  /** Progress percentage (0-100) */
  progress?: number;
  /** Progress message */
  progressMessage?: string;
  /** Duration in milliseconds */
  duration_ms?: number;
  /** Start timestamp */
  startTime: string;
  /** End timestamp (if completed) */
  endTime?: string;
  /** Execution ID for tracking */
  execution_id?: string;
}

/**
 * Skill-to-tool mapping display info
 * Shows which skill is using which tools
 */
export interface SkillToolMapping {
  /** Skill name */
  skill: string;
  /** List of tool names used by this skill */
  tools: string[];
}
