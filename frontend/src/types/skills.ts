/**
 * Skill Management Types
 * Sprint 97: Skill Configuration UI & Admin Dashboard
 *
 * Type definitions for Anthropic Agent Skills ecosystem management.
 */

/**
 * Skill summary for card display in registry browser
 */
export interface SkillSummary {
  name: string;
  version: string;
  description: string;
  author: string;
  is_active: boolean;
  tools_count: number;
  triggers_count: number;
  icon: string; // Emoji or icon name
}

/**
 * Full skill details
 */
export interface SkillDetail {
  name: string;
  version: string;
  description: string;
  author: string;
  triggers: string[];
  tools: string[];
  dependencies: string[];
  permissions: string[];
  config: Record<string, unknown>;
  instructions: string; // Markdown from SKILL.md
  is_active: boolean;
  activation_count: number;
  last_activated: string | null;
}

/**
 * Tool authorization entry
 */
export interface ToolAuthorization {
  tool_name: string;
  access_level: 'standard' | 'elevated' | 'admin';
  rate_limit: number | null; // Requests per minute, null = unlimited
  allowed_domains: string[];
  blocked_domains: string[];
}

/**
 * Skill lifecycle metrics
 */
export interface SkillLifecycleMetrics {
  skill_name: string;
  activation_count: number;
  execution_count: number;
  success_rate: number; // 0.0 to 1.0
  avg_latency_ms: number;
  error_count: number;
  last_activated: string | null;
  last_executed: string | null;
}

/**
 * Aggregated lifecycle metrics for dashboard
 */
export interface LifecycleDashboardMetrics {
  active_skills_count: number;
  total_skills_count: number;
  tool_calls_24h: number;
  tool_calls_change_percent: number; // vs previous 24h
  policy_alerts: PolicyAlert[];
  skill_activation_timeline: ActivationTimelineEntry[];
  top_tools: ToolUsageEntry[];
}

/**
 * Policy violation alert
 */
export interface PolicyAlert {
  id: string;
  severity: 'warning' | 'critical';
  type: 'rate_limit' | 'blocked_pattern' | 'unauthorized_domain';
  skill_name: string;
  tool_name: string;
  message: string;
  timestamp: string;
}

/**
 * Skill activation timeline entry
 */
export interface ActivationTimelineEntry {
  skill_name: string;
  timestamp: string;
  duration_ms: number;
}

/**
 * Tool usage statistics
 */
export interface ToolUsageEntry {
  tool_name: string;
  call_count: number;
  skill_name: string;
}

/**
 * SKILL.md frontmatter structure
 */
export interface SkillFrontmatter {
  name: string;
  version: string;
  description: string;
  author: string;
  triggers: string[];
  dependencies: string[];
  permissions: string[];
  tools?: string[];
}

/**
 * SKILL.md document structure
 */
export interface SkillMdDocument {
  frontmatter: SkillFrontmatter;
  instructions: string; // Markdown body
}

/**
 * Configuration validation result
 */
export interface ConfigValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * List response for skill registry
 * Sprint 100 Fix #1: Align with backend SkillListResponse Pydantic model
 */
export interface SkillListResponse {
  items: SkillSummary[]; // Backend returns 'items' not 'skills'
  total: number; // Backend returns 'total' not 'total_count'
  page: number;
  page_size: number; // Backend returns 'page_size' not 'limit'
  total_pages: number; // Backend also provides total_pages
}

/**
 * Tool authorization list response
 */
export interface ToolAuthorizationListResponse {
  skill_name: string;
  authorizations: ToolAuthorization[];
}

/**
 * Activation/deactivation response
 */
export interface SkillActivationResponse {
  status: 'activated' | 'deactivated';
  skill_name: string;
  instructions_length?: number;
}
