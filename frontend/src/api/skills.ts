/**
 * Skills API Client
 * Sprint 97: Skill Configuration UI & Admin Dashboard
 *
 * API functions for managing Anthropic Agent Skills.
 */

import type {
  SkillSummary,
  SkillDetail,
  SkillListResponse,
  SkillActivationResponse,
  ConfigValidationResult,
  ToolAuthorization,
  ToolAuthorizationListResponse,
  LifecycleDashboardMetrics,
  SkillMdDocument,
  ResolvedToolsResponse,
} from '../types/skills';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ============================================================================
// Feature 97.1: Skill Registry Browser API
// ============================================================================

/**
 * List all available skills with optional filtering
 * @param search Search query for name/description
 * @param status Filter by activation status
 * @param page Page number (1-indexed)
 * @param limit Items per page
 * @returns SkillListResponse with paginated skills
 */
export async function listSkills(params?: {
  search?: string;
  status?: 'active' | 'inactive' | 'all';
  page?: number;
  limit?: number;
}): Promise<SkillListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.search) queryParams.append('search', params.search);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.page !== undefined) queryParams.append('page', String(params.page));
  if (params?.limit !== undefined) queryParams.append('limit', String(params.limit));

  const url = `${API_BASE_URL}/api/v1/skills/registry?${queryParams.toString()}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  // Sprint 100 Fix #1: Backend now returns proper SkillListResponse object
  // No transformation needed - return response directly
  return response.json();
}

/**
 * Get full details for a specific skill
 * @param skillName Name of the skill
 * @returns SkillDetail with complete metadata
 */
export async function getSkill(skillName: string): Promise<SkillDetail> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  // Sprint 121 Fix: Map backend SkillDetailResponse → frontend SkillDetail
  // Backend uses: tags, lifecycle, skill_md, config_yaml
  // Frontend expects: triggers, is_active, instructions, permissions, etc.
  const raw = await response.json();

  // Extract permissions and dependencies from SKILL.md frontmatter if available
  let permissions: string[] = [];
  let dependencies: string[] = [];
  if (raw.skill_md) {
    const frontmatterMatch = raw.skill_md.match(/^---\n([\s\S]*?)\n---/);
    if (frontmatterMatch) {
      const fm = frontmatterMatch[1];
      const permMatch = fm.match(/permissions:\n((?:\s+-\s+.*\n?)*)/);
      if (permMatch) {
        permissions = permMatch[1].match(/-\s+(\S+)/g)?.map((s: string) => s.replace(/^-\s+/, '')) ?? [];
      }
      const depMatch = fm.match(/dependencies:\n((?:\s+-\s+.*\n?)*)/);
      if (depMatch) {
        dependencies = depMatch[1].match(/-\s+(\S+)/g)?.map((s: string) => s.replace(/^-\s+/, '')) ?? [];
      }
    }
  }

  return {
    name: raw.name,
    version: raw.version,
    description: raw.description,
    author: raw.author,
    triggers: raw.tags ?? [],
    tools: (raw.tools ?? []).map((t: { tool_name?: string }) => t.tool_name ?? String(t)),
    dependencies,
    permissions,
    config: raw.config_yaml ? {} : {},
    instructions: raw.skill_md ?? '',
    is_active: raw.status === 'active' || raw.lifecycle?.state === 'active',
    activation_count: raw.lifecycle?.invocation_count ?? 0,
    last_activated: raw.lifecycle?.activated_at ?? null,
  };
}

/**
 * Activate a skill
 * @param skillName Name of the skill to activate
 * @returns SkillActivationResponse with status
 */
export async function activateSkill(skillName: string): Promise<SkillActivationResponse> {
  const url = `${API_BASE_URL}/api/v1/skills/registry/${encodeURIComponent(skillName)}/activate`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Deactivate a skill
 * @param skillName Name of the skill to deactivate
 * @returns SkillActivationResponse with status
 */
export async function deactivateSkill(skillName: string): Promise<SkillActivationResponse> {
  const url = `${API_BASE_URL}/api/v1/skills/registry/${encodeURIComponent(skillName)}/deactivate`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Feature 97.2: Skill Configuration Editor API
// ============================================================================

/**
 * Get skill configuration (config.yaml)
 * @param skillName Name of the skill
 * @returns Configuration object
 */
export async function getSkillConfig(
  skillName: string
): Promise<Record<string, unknown>> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/config`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Update skill configuration
 * @param skillName Name of the skill
 * @param config New configuration object
 * @returns Updated configuration
 */
export async function updateSkillConfig(
  skillName: string,
  config: Record<string, unknown>
): Promise<{ status: string; config: Record<string, unknown> }> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/config`;
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Validate configuration without saving
 * @param skillName Name of the skill
 * @param config Configuration to validate
 * @returns ConfigValidationResult with errors/warnings
 */
export async function validateSkillConfig(
  skillName: string,
  config: Record<string, unknown>
): Promise<ConfigValidationResult> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/config/validate`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Feature 97.3: Tool Authorization Manager API
// ============================================================================

/**
 * Get tool authorizations for a skill
 * @param skillName Name of the skill
 * @returns ToolAuthorizationListResponse with authorizations
 */
export async function getToolAuthorizations(
  skillName: string
): Promise<ToolAuthorizationListResponse> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/tools`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  const authorizations: ToolAuthorization[] = await response.json();
  return {
    skill_name: skillName,
    authorizations,
  };
}

/**
 * Add tool authorization to a skill
 * @param skillName Name of the skill
 * @param authorization Tool authorization to add
 * @returns Updated authorization
 */
export async function addToolAuthorization(
  skillName: string,
  authorization: ToolAuthorization
): Promise<ToolAuthorization> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/tools`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(authorization),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Remove tool authorization from a skill
 * @param skillName Name of the skill
 * @param toolName Name of the tool to remove
 */
export async function removeToolAuthorization(
  skillName: string,
  toolName: string
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/tools/${encodeURIComponent(toolName)}`;
  const response = await fetch(url, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
}

/**
 * Update tool authorization
 * @param skillName Name of the skill
 * @param authorization Updated tool authorization
 * @returns Updated authorization
 */
export async function updateToolAuthorization(
  skillName: string,
  authorization: ToolAuthorization
): Promise<ToolAuthorization> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/tools/${encodeURIComponent(authorization.tool_name)}`;
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(authorization),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Feature 97.4: Skill Lifecycle Dashboard API
// ============================================================================

/**
 * Get aggregated lifecycle metrics for dashboard
 * @returns LifecycleDashboardMetrics with real-time data
 */
export async function getLifecycleMetrics(): Promise<LifecycleDashboardMetrics> {
  const url = `${API_BASE_URL}/api/v1/skills/lifecycle/metrics`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Feature 97.5: SKILL.md Visual Editor API
// ============================================================================

/**
 * Get SKILL.md document for a skill
 * @param skillName Name of the skill
 * @returns SkillMdDocument with frontmatter and instructions
 */
export async function getSkillMd(skillName: string): Promise<SkillMdDocument> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/skill-md`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Update SKILL.md document
 * @param skillName Name of the skill
 * @param document Updated document with frontmatter and instructions
 * @returns Updated document
 */
export async function updateSkillMd(
  skillName: string,
  document: SkillMdDocument
): Promise<SkillMdDocument> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/skill-md`;
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(document),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

// ============================================================================
// Sprint 121: Skill Tool Auto-Resolve API (ADR-058)
// ============================================================================

/**
 * Get auto-resolved tools for a skill based on its permissions
 * @param skillName Name of the skill
 * @returns ResolvedToolsResponse with matched tools
 */
export async function getResolvedTools(
  skillName: string
): Promise<ResolvedToolsResponse> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/resolved-tools`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}

/**
 * Set an admin override for a tool-skill binding
 * @param skillName Name of the skill
 * @param toolName Name of the tool
 * @param allowed Whether to allow or deny the tool
 */
export async function setToolOverride(
  skillName: string,
  toolName: string,
  allowed: boolean
): Promise<{ status: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/skills/${encodeURIComponent(skillName)}/resolved-tools/override`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tool_name: toolName, allowed }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  return response.json();
}
