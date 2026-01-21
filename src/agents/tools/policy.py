"""Policy Guardrails Engine for Tool Access Control.

Sprint 93 Feature 93.4: Policy Guardrails Engine (5 SP)

This module provides a policy engine that controls which tools
can be used by which skills. Implements RBAC-style access control
with audit logging for compliance.

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │                  PolicyEngine                       │
    ├─────────────────────────────────────────────────────┤
    │                                                     │
    │  Skill Request: "research" wants to use "browser"   │
    │                                                     │
    │  1. Check Skill→Tool Mapping                        │
    │     ┌──────────────┐    ┌──────────────┐           │
    │     │   research   │───▶│  browser ✓   │           │
    │     │              │    │  file ✗      │           │
    │     │              │    │  api ✓       │           │
    │     └──────────────┘    └──────────────┘           │
    │                                                     │
    │  2. Check Input Policy                              │
    │     - Rate limits                                   │
    │     - URL allowlists                                │
    │     - Parameter validation                          │
    │                                                     │
    │  3. Log Access (Audit Trail)                        │
    │     { skill, tool, inputs, timestamp, allowed }     │
    │                                                     │
    └─────────────────────────────────────────────────────┘

Example:
    >>> engine = PolicyEngine()
    >>> engine.register_skill("research", ["browser", "web_search"])
    >>> await engine.can_use_tool("research", "browser", {"url": "..."})
    True
    >>> await engine.can_use_tool("research", "file_write", {})
    False

See Also:
    - src/agents/tools/composition.py: ToolComposer using this engine
    - src/agents/skills/lifecycle.py: Skill lifecycle management
    - docs/sprints/SPRINT_93_PLAN.md: Feature specification
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class PolicyDecision(Enum):
    """Result of policy check.

    Attributes:
        ALLOW: Access granted
        DENY: Access denied
        RATE_LIMITED: Temporarily denied due to rate limit
        VALIDATION_FAILED: Input validation failed
    """

    ALLOW = "allow"
    DENY = "deny"
    RATE_LIMITED = "rate_limited"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class PolicyRule:
    """Single policy rule for tool access.

    Attributes:
        tool_name: Tool this rule applies to
        allowed_skills: Skills allowed to use this tool (None = all)
        denied_skills: Skills explicitly denied (takes precedence)
        rate_limit: Max calls per minute (0 = unlimited)
        validators: List of input validator functions
        required_params: Parameters that must be present
        forbidden_params: Parameters that must NOT be present
    """

    tool_name: str
    allowed_skills: list[str] | None = None  # None = all allowed
    denied_skills: list[str] = field(default_factory=list)
    rate_limit: int = 0  # 0 = unlimited
    validators: list[Callable[[dict[str, Any]], bool]] = field(default_factory=list)
    required_params: list[str] = field(default_factory=list)
    forbidden_params: list[str] = field(default_factory=list)


@dataclass
class AuditLogEntry:
    """Audit log entry for tool access.

    Attributes:
        timestamp: When the access occurred
        skill_name: Skill requesting access
        tool_name: Tool being accessed
        inputs: Input parameters (sanitized)
        decision: Policy decision made
        reason: Human-readable reason
        duration_ms: Time taken for policy check
    """

    timestamp: datetime
    skill_name: str
    tool_name: str
    inputs: dict[str, Any]
    decision: PolicyDecision
    reason: str = ""
    duration_ms: float = 0.0


@dataclass
class SkillPermissions:
    """Permission set for a skill.

    Attributes:
        skill_name: Name of the skill
        allowed_tools: List of tools this skill can use
        denied_tools: Explicitly denied tools
        is_admin: Admin skills bypass restrictions
    """

    skill_name: str
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    is_admin: bool = False


# =============================================================================
# Policy Engine
# =============================================================================


class PolicyEngine:
    """Policy engine for tool access control.

    Provides RBAC-style access control for tools with:
    - Skill→Tool mappings
    - Rate limiting
    - Input validation
    - Audit logging

    LangGraph 1.0 Integration:
        Used by ToolComposer to check permissions before tool execution.

    Example:
        >>> engine = PolicyEngine()
        >>> engine.register_skill("research", ["browser", "api"])
        >>> engine.add_rule(PolicyRule("file_write", allowed_skills=["admin"]))
        >>>
        >>> await engine.can_use_tool("research", "browser", {})
        True
        >>> await engine.can_use_tool("research", "file_write", {})
        False
    """

    def __init__(
        self,
        max_audit_entries: int = 10000,
        default_rate_limit: int = 60,  # per minute
    ) -> None:
        """Initialize PolicyEngine.

        Args:
            max_audit_entries: Maximum audit log entries to keep
            default_rate_limit: Default rate limit for tools (0 = unlimited)
        """
        self._skills: dict[str, SkillPermissions] = {}
        self._rules: dict[str, PolicyRule] = {}
        self._audit_log: list[AuditLogEntry] = []
        self._rate_trackers: dict[str, list[float]] = {}  # skill:tool -> timestamps
        self._max_audit = max_audit_entries
        self._default_rate_limit = default_rate_limit
        self._lock = asyncio.Lock()

        logger.info(
            "policy_engine_initialized",
            max_audit=max_audit_entries,
            default_rate_limit=default_rate_limit,
        )

    def register_skill(
        self,
        skill_name: str,
        allowed_tools: list[str],
        denied_tools: list[str] | None = None,
        is_admin: bool = False,
    ) -> None:
        """Register a skill with its tool permissions.

        Args:
            skill_name: Unique skill identifier
            allowed_tools: List of tools this skill can use
            denied_tools: Explicitly denied tools (optional)
            is_admin: If True, skill bypasses restrictions

        Example:
            >>> engine.register_skill("research", ["browser", "api"])
            >>> engine.register_skill("admin_skill", [], is_admin=True)
        """
        self._skills[skill_name] = SkillPermissions(
            skill_name=skill_name,
            allowed_tools=allowed_tools,
            denied_tools=denied_tools or [],
            is_admin=is_admin,
        )

        logger.info(
            "skill_registered",
            skill_name=skill_name,
            allowed_count=len(allowed_tools),
            is_admin=is_admin,
        )

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a policy rule for a tool.

        Args:
            rule: PolicyRule defining access control

        Example:
            >>> engine.add_rule(PolicyRule(
            ...     tool_name="file_write",
            ...     allowed_skills=["admin"],
            ...     rate_limit=10,
            ... ))
        """
        self._rules[rule.tool_name] = rule

        logger.info(
            "policy_rule_added",
            tool_name=rule.tool_name,
            allowed_skills=rule.allowed_skills,
            rate_limit=rule.rate_limit,
        )

    async def can_use_tool(
        self,
        skill_name: str,
        tool_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> bool:
        """Check if skill can use tool with given inputs.

        Performs:
        1. Skill permission check
        2. Rule-based access check
        3. Rate limit check
        4. Input validation

        Args:
            skill_name: Skill requesting access
            tool_name: Tool to access
            inputs: Optional input parameters to validate

        Returns:
            True if access allowed, False otherwise

        Example:
            >>> await engine.can_use_tool("research", "browser", {"url": "..."})
            True
        """
        start_time = time.perf_counter()
        inputs = inputs or {}

        # Check skill permissions
        skill = self._skills.get(skill_name)

        if skill:
            # Admin bypass
            if skill.is_admin:
                await self._log_access(
                    skill_name,
                    tool_name,
                    inputs,
                    PolicyDecision.ALLOW,
                    "admin_bypass",
                    start_time,
                )
                return True

            # Explicit deny
            if tool_name in skill.denied_tools:
                await self._log_access(
                    skill_name,
                    tool_name,
                    inputs,
                    PolicyDecision.DENY,
                    "skill_denied",
                    start_time,
                )
                return False

            # Allowed check
            if skill.allowed_tools and tool_name not in skill.allowed_tools:
                await self._log_access(
                    skill_name,
                    tool_name,
                    inputs,
                    PolicyDecision.DENY,
                    "not_in_allowed_list",
                    start_time,
                )
                return False

        # Check tool rules
        rule = self._rules.get(tool_name)
        if rule:
            decision = await self._check_rule(skill_name, rule, inputs)
            await self._log_access(
                skill_name,
                tool_name,
                inputs,
                decision,
                f"rule_check_{decision.value}",
                start_time,
            )
            return decision == PolicyDecision.ALLOW

        # Default: allow if skill registered, deny otherwise
        if skill:
            await self._log_access(
                skill_name,
                tool_name,
                inputs,
                PolicyDecision.ALLOW,
                "default_allow",
                start_time,
            )
            return True
        else:
            await self._log_access(
                skill_name,
                tool_name,
                inputs,
                PolicyDecision.DENY,
                "unknown_skill",
                start_time,
            )
            return False

    async def _check_rule(
        self,
        skill_name: str,
        rule: PolicyRule,
        inputs: dict[str, Any],
    ) -> PolicyDecision:
        """Check a specific policy rule.

        Args:
            skill_name: Skill requesting access
            rule: Rule to check
            inputs: Input parameters

        Returns:
            PolicyDecision result
        """
        # Check denied skills
        if skill_name in rule.denied_skills:
            return PolicyDecision.DENY

        # Check allowed skills
        if rule.allowed_skills is not None:
            if skill_name not in rule.allowed_skills:
                return PolicyDecision.DENY

        # Check rate limit
        if rule.rate_limit > 0:
            if await self._is_rate_limited(skill_name, rule.tool_name, rule.rate_limit):
                return PolicyDecision.RATE_LIMITED

        # Check required params
        for param in rule.required_params:
            if param not in inputs:
                logger.warning(
                    "policy_missing_required_param",
                    tool=rule.tool_name,
                    param=param,
                )
                return PolicyDecision.VALIDATION_FAILED

        # Check forbidden params
        for param in rule.forbidden_params:
            if param in inputs:
                logger.warning(
                    "policy_forbidden_param",
                    tool=rule.tool_name,
                    param=param,
                )
                return PolicyDecision.VALIDATION_FAILED

        # Run custom validators
        for validator in rule.validators:
            try:
                if not validator(inputs):
                    return PolicyDecision.VALIDATION_FAILED
            except Exception as e:
                logger.error("policy_validator_error", error=str(e))
                return PolicyDecision.VALIDATION_FAILED

        return PolicyDecision.ALLOW

    async def _is_rate_limited(
        self,
        skill_name: str,
        tool_name: str,
        limit: int,
    ) -> bool:
        """Check if skill:tool is rate limited.

        Uses sliding window of 60 seconds.

        Args:
            skill_name: Skill name
            tool_name: Tool name
            limit: Max calls per minute

        Returns:
            True if rate limited
        """
        key = f"{skill_name}:{tool_name}"
        now = time.time()
        window = 60.0  # 1 minute

        async with self._lock:
            if key not in self._rate_trackers:
                self._rate_trackers[key] = []

            # Remove old entries
            self._rate_trackers[key] = [t for t in self._rate_trackers[key] if now - t < window]

            # Check limit
            if len(self._rate_trackers[key]) >= limit:
                logger.warning(
                    "rate_limit_exceeded",
                    skill=skill_name,
                    tool=tool_name,
                    limit=limit,
                    current=len(self._rate_trackers[key]),
                )
                return True

            # Record this call
            self._rate_trackers[key].append(now)
            return False

    async def _log_access(
        self,
        skill_name: str,
        tool_name: str,
        inputs: dict[str, Any],
        decision: PolicyDecision,
        reason: str,
        start_time: float,
    ) -> None:
        """Log access attempt to audit log.

        Args:
            skill_name: Skill requesting access
            tool_name: Tool being accessed
            inputs: Input parameters (will be sanitized)
            decision: Policy decision
            reason: Reason for decision
            start_time: Time when check started
        """
        duration_ms = (time.perf_counter() - start_time) * 1000

        entry = AuditLogEntry(
            timestamp=datetime.now(),
            skill_name=skill_name,
            tool_name=tool_name,
            inputs=self._sanitize_inputs(inputs),
            decision=decision,
            reason=reason,
            duration_ms=duration_ms,
        )

        async with self._lock:
            self._audit_log.append(entry)

            # Trim if over limit
            if len(self._audit_log) > self._max_audit:
                self._audit_log = self._audit_log[-self._max_audit :]

        logger.debug(
            "policy_access_logged",
            skill=skill_name,
            tool=tool_name,
            decision=decision.value,
            duration_ms=duration_ms,
        )

    def _sanitize_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Sanitize inputs for audit log (remove secrets).

        Args:
            inputs: Raw input dict

        Returns:
            Sanitized dict with secrets masked
        """
        sensitive_keys = {"password", "token", "secret", "api_key", "credential"}
        sanitized = {}

        for key, value in inputs.items():
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + "...[truncated]"
            else:
                sanitized[key] = value

        return sanitized

    async def log_tool_usage(
        self,
        skill_name: str,
        tool_name: str,
        inputs: dict[str, Any],
    ) -> None:
        """Log actual tool usage (after execution).

        Called by ToolComposer after successful tool execution.

        Args:
            skill_name: Skill that used the tool
            tool_name: Tool that was used
            inputs: Input parameters
        """
        logger.info(
            "tool_usage",
            skill=skill_name,
            tool=tool_name,
            input_keys=list(inputs.keys()),
        )

    def get_audit_log(
        self,
        skill_name: str | None = None,
        tool_name: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Get audit log entries, optionally filtered.

        Args:
            skill_name: Filter by skill (optional)
            tool_name: Filter by tool (optional)
            limit: Maximum entries to return

        Returns:
            List of audit log entries (most recent first)
        """
        entries = self._audit_log.copy()

        if skill_name:
            entries = [e for e in entries if e.skill_name == skill_name]

        if tool_name:
            entries = [e for e in entries if e.tool_name == tool_name]

        # Return most recent first
        return list(reversed(entries[-limit:]))

    def get_skill_permissions(self, skill_name: str) -> SkillPermissions | None:
        """Get permissions for a skill.

        Args:
            skill_name: Skill to look up

        Returns:
            SkillPermissions or None if not registered
        """
        return self._skills.get(skill_name)

    def get_metrics(self) -> dict[str, Any]:
        """Get policy engine metrics.

        Returns:
            Dict with counts and stats
        """
        allow_count = sum(1 for e in self._audit_log if e.decision == PolicyDecision.ALLOW)
        deny_count = sum(1 for e in self._audit_log if e.decision == PolicyDecision.DENY)

        return {
            "registered_skills": len(self._skills),
            "policy_rules": len(self._rules),
            "audit_log_size": len(self._audit_log),
            "allow_count": allow_count,
            "deny_count": deny_count,
            "allow_rate": allow_count / len(self._audit_log) if self._audit_log else 0,
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_default_policy_engine() -> PolicyEngine:
    """Create PolicyEngine with default AegisRAG skill mappings.

    Returns:
        Configured PolicyEngine

    Example:
        >>> engine = create_default_policy_engine()
        >>> await engine.can_use_tool("research", "browser", {})
        True
    """
    engine = PolicyEngine()

    # Register default skills with their tool permissions
    engine.register_skill(
        "research",
        allowed_tools=["browser", "web_search", "api_call", "echo", "format", "json_extract"],
    )

    engine.register_skill(
        "web_automation",
        allowed_tools=["browser", "screenshot", "click", "type", "echo"],
    )

    engine.register_skill(
        "document_processing",
        allowed_tools=["file_read", "pdf_parse", "ocr", "echo", "format"],
    )

    engine.register_skill(
        "admin",
        allowed_tools=[],  # Empty = all allowed
        is_admin=True,
    )

    # Add restrictive rules for sensitive tools
    engine.add_rule(
        PolicyRule(
            tool_name="file_write",
            allowed_skills=["admin"],
            rate_limit=10,
        )
    )

    engine.add_rule(
        PolicyRule(
            tool_name="shell_exec",
            allowed_skills=["admin"],
            rate_limit=5,
        )
    )

    engine.add_rule(
        PolicyRule(
            tool_name="browser",
            rate_limit=30,  # 30 requests per minute
        )
    )

    return engine
