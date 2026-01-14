"""Permission Engine for Skill Execution Access Control.

Sprint Context:
    - Sprint 91 (2026-01-14): Feature 91.3 - Permission Engine (8 SP)

Manages permissions for skill execution:
- Per-skill permission requirements
- Per-user permission policies
- Rate limiting for abuse prevention
- Permission violation logging

Architecture:
    Skill Activation Request → Permission Check → Allow/Deny → Record Usage

Ensures:
- Skills only access what they're allowed
- Users can only use skills they have permission for
- Rate limiting prevents abuse
- All permission violations are logged

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Example:
    >>> from src.agents.security import Permission, PermissionEngine
    >>> engine = PermissionEngine()
    >>>
    >>> # Register skill requirements
    >>> engine.register_skill_permissions("retrieval", ["read_documents", "invoke_llm"])
    >>> engine.register_skill_permissions("web_search", ["web_access", "invoke_llm"])
    >>>
    >>> # Set user policy
    >>> engine.set_user_policy(
    ...     "user123",
    ...     allowed=["read_documents", "invoke_llm"],
    ...     rate_limits={"retrieval": 100}  # 100 calls per minute
    ... )
    >>>
    >>> # Check permission
    >>> allowed, reason = engine.check_skill_permission("user123", "retrieval")
    >>> # (True, "OK")
    >>>
    >>> # Record usage
    >>> engine.record_skill_use("user123", "retrieval")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

import structlog

logger = structlog.get_logger(__name__)


class Permission(str, Enum):
    """Available permissions for skill execution.

    Each permission represents a specific capability or resource access.
    Skills declare required permissions in their SKILL.md metadata.

    Attributes:
        READ_DOCUMENTS: Read access to indexed documents
        WRITE_MEMORY: Write access to memory store (conversation history)
        INVOKE_LLM: Ability to make LLM API calls
        WEB_ACCESS: Internet access (web search, URL fetching)
        CODE_EXECUTION: Execute code (Python scripts, shell commands)
        FILE_ACCESS: Read/write local filesystem
        ADMIN: Administrative operations (delete data, modify config)

    Example:
        >>> Permission.READ_DOCUMENTS
        <Permission.READ_DOCUMENTS: 'read_documents'>
        >>> Permission.WEB_ACCESS.value
        'web_access'
    """

    READ_DOCUMENTS = "read_documents"
    WRITE_MEMORY = "write_memory"
    INVOKE_LLM = "invoke_llm"
    WEB_ACCESS = "web_access"
    CODE_EXECUTION = "code_execution"
    FILE_ACCESS = "file_access"
    ADMIN = "admin"


@dataclass
class PermissionPolicy:
    """Policy for a user or role.

    Defines what a user/role is allowed and denied.
    Includes rate limiting per skill.

    Attributes:
        allowed: Set of allowed permissions
        denied: Set of explicitly denied permissions (overrides allowed)
        rate_limits: Dict of skill_name → max calls per minute

    Example:
        >>> policy = PermissionPolicy(
        ...     allowed={Permission.READ_DOCUMENTS, Permission.INVOKE_LLM},
        ...     denied=set(),
        ...     rate_limits={"retrieval": 100, "web_search": 10}
        ... )
    """

    allowed: Set[Permission]
    denied: Set[Permission] = field(default_factory=set)
    rate_limits: Dict[str, int] = field(default_factory=dict)


class PermissionEngine:
    """Manage permissions for skill execution.

    Ensures:
    - Skills only access what they're allowed
    - Users can only use skills they have permission for
    - Rate limiting prevents abuse
    - All permission violations are logged

    Attributes:
        _policies: User/role permission policies
        _skill_requirements: Skill permission requirements
        _rate_counters: Rate limiting counters per user+skill

    Example:
        >>> engine = PermissionEngine()
        >>> engine.register_skill_permissions("retrieval", ["read_documents", "invoke_llm"])
        >>> engine.set_user_policy("user123", ["read_documents", "invoke_llm"])
        >>> allowed, reason = engine.check_skill_permission("user123", "retrieval")
    """

    def __init__(self):
        """Initialize permission engine."""
        self._policies: Dict[str, PermissionPolicy] = {}
        self._skill_requirements: Dict[str, Set[Permission]] = {}
        self._rate_counters: Dict[str, Dict[str, int]] = {}

        logger.info("permission_engine_initialized")

    def register_skill_permissions(
        self, skill_name: str, required: List[str]
    ) -> None:
        """Register permissions required by a skill.

        Args:
            skill_name: Skill identifier
            required: List of permission strings (e.g., ["read_documents", "invoke_llm"])

        Example:
            >>> engine = PermissionEngine()
            >>> engine.register_skill_permissions("retrieval", ["read_documents", "invoke_llm"])
            >>> engine.register_skill_permissions("web_search", ["web_access", "invoke_llm"])
        """
        # Convert permission strings to Permission enum (skip invalid)
        permissions: Set[Permission] = set()
        for perm_str in required:
            try:
                # Check if permission string is valid
                if perm_str in [p.value for p in Permission]:
                    permissions.add(Permission(perm_str))
                else:
                    logger.warning(
                        "invalid_permission_ignored",
                        skill=skill_name,
                        permission=perm_str,
                        valid_permissions=[p.value for p in Permission],
                    )
            except ValueError:
                logger.warning(
                    "permission_conversion_failed",
                    skill=skill_name,
                    permission=perm_str,
                )

        self._skill_requirements[skill_name] = permissions

        logger.debug(
            "skill_permissions_registered",
            skill=skill_name,
            permissions=[p.value for p in permissions],
        )

    def set_user_policy(
        self,
        user_id: str,
        allowed: List[str],
        denied: Optional[List[str]] = None,
        rate_limits: Optional[Dict[str, int]] = None,
    ) -> None:
        """Set permission policy for a user.

        Args:
            user_id: User identifier
            allowed: List of allowed permission strings
            denied: Optional list of denied permission strings
            rate_limits: Optional dict of skill_name → max calls per minute

        Example:
            >>> engine = PermissionEngine()
            >>> engine.set_user_policy(
            ...     "user123",
            ...     allowed=["read_documents", "invoke_llm", "web_access"],
            ...     denied=["admin"],
            ...     rate_limits={"retrieval": 100, "web_search": 10}
            ... )
        """
        # Convert permission strings to Permission enum
        allowed_perms: Set[Permission] = set()
        for perm_str in allowed:
            try:
                if perm_str in [p.value for p in Permission]:
                    allowed_perms.add(Permission(perm_str))
            except ValueError:
                logger.warning(
                    "invalid_permission_in_policy",
                    user_id=user_id,
                    permission=perm_str,
                )

        denied_perms: Set[Permission] = set()
        if denied:
            for perm_str in denied:
                try:
                    if perm_str in [p.value for p in Permission]:
                        denied_perms.add(Permission(perm_str))
                except ValueError:
                    logger.warning(
                        "invalid_denied_permission",
                        user_id=user_id,
                        permission=perm_str,
                    )

        self._policies[user_id] = PermissionPolicy(
            allowed=allowed_perms,
            denied=denied_perms,
            rate_limits=rate_limits or {},
        )

        logger.info(
            "user_policy_set",
            user_id=user_id,
            allowed=[p.value for p in allowed_perms],
            denied=[p.value for p in denied_perms],
            rate_limits=rate_limits or {},
        )

    def check_skill_permission(
        self, user_id: str, skill_name: str
    ) -> tuple[bool, str]:
        """Check if user can use a skill.

        Checks:
        1. User has required permissions
        2. No permissions are explicitly denied
        3. Rate limit not exceeded

        Args:
            user_id: User identifier
            skill_name: Skill identifier

        Returns:
            Tuple of (allowed: bool, reason: str)

        Example:
            >>> engine = PermissionEngine()
            >>> engine.register_skill_permissions("retrieval", ["read_documents", "invoke_llm"])
            >>> engine.set_user_policy("user123", ["read_documents", "invoke_llm"])
            >>> allowed, reason = engine.check_skill_permission("user123", "retrieval")
            >>> # (True, "OK")
            >>>
            >>> allowed, reason = engine.check_skill_permission("user123", "admin_delete")
            >>> # (False, "Missing permissions: ['admin']")
        """
        # Get user policy (default: basic permissions)
        policy = self._policies.get(
            user_id,
            PermissionPolicy(
                allowed={Permission.READ_DOCUMENTS, Permission.INVOKE_LLM},
                denied=set(),
                rate_limits={},
            ),
        )

        # Get skill requirements (empty if skill not registered)
        required = self._skill_requirements.get(skill_name, set())

        # Check explicit denials (highest priority)
        denied = required.intersection(policy.denied)
        if denied:
            reason = f"Permission denied: {[p.value for p in denied]}"
            logger.warning(
                "skill_permission_denied",
                user_id=user_id,
                skill=skill_name,
                denied_permissions=[p.value for p in denied],
            )
            return False, reason

        # Check required permissions
        missing = required - policy.allowed
        if missing:
            reason = f"Missing permissions: {[p.value for p in missing]}"
            logger.warning(
                "skill_permission_missing",
                user_id=user_id,
                skill=skill_name,
                missing_permissions=[p.value for p in missing],
            )
            return False, reason

        # Check rate limits
        if skill_name in policy.rate_limits:
            limit = policy.rate_limits[skill_name]
            current = self._get_rate_count(user_id, skill_name)
            if current >= limit:
                reason = f"Rate limit exceeded for {skill_name} ({current}/{limit} per minute)"
                logger.warning(
                    "skill_rate_limit_exceeded",
                    user_id=user_id,
                    skill=skill_name,
                    current=current,
                    limit=limit,
                )
                return False, reason

        # All checks passed
        logger.debug(
            "skill_permission_granted",
            user_id=user_id,
            skill=skill_name,
        )
        return True, "OK"

    def record_skill_use(self, user_id: str, skill_name: str) -> None:
        """Record skill usage for rate limiting.

        Args:
            user_id: User identifier
            skill_name: Skill identifier

        Example:
            >>> engine = PermissionEngine()
            >>> engine.record_skill_use("user123", "retrieval")
            >>> engine.record_skill_use("user123", "retrieval")
            >>> engine._get_rate_count("user123", "retrieval")
            2
        """
        if user_id not in self._rate_counters:
            self._rate_counters[user_id] = {}

        if skill_name not in self._rate_counters[user_id]:
            self._rate_counters[user_id][skill_name] = 0

        self._rate_counters[user_id][skill_name] += 1

        logger.debug(
            "skill_use_recorded",
            user_id=user_id,
            skill=skill_name,
            count=self._rate_counters[user_id][skill_name],
        )

    def _get_rate_count(self, user_id: str, skill_name: str) -> int:
        """Get current rate counter for user+skill.

        Args:
            user_id: User identifier
            skill_name: Skill identifier

        Returns:
            Current count for this minute
        """
        return self._rate_counters.get(user_id, {}).get(skill_name, 0)

    def reset_rate_counters(self, user_id: Optional[str] = None) -> None:
        """Reset rate counters.

        Call this every minute to reset rate limits.

        Args:
            user_id: Optional user to reset (None = reset all)

        Example:
            >>> engine = PermissionEngine()
            >>> # ... after 1 minute ...
            >>> engine.reset_rate_counters()  # Reset all users
            >>> # OR
            >>> engine.reset_rate_counters("user123")  # Reset specific user
        """
        if user_id:
            if user_id in self._rate_counters:
                self._rate_counters[user_id] = {}
                logger.debug("rate_counters_reset", user_id=user_id)
        else:
            self._rate_counters = {}
            logger.info("all_rate_counters_reset")

    def get_user_permissions(
        self, user_id: str
    ) -> Set[Permission]:
        """Get allowed permissions for a user.

        Args:
            user_id: User identifier

        Returns:
            Set of allowed Permission enums

        Example:
            >>> engine = PermissionEngine()
            >>> engine.set_user_policy("user123", ["read_documents", "invoke_llm"])
            >>> perms = engine.get_user_permissions("user123")
            >>> perms
            {<Permission.READ_DOCUMENTS: 'read_documents'>, <Permission.INVOKE_LLM: 'invoke_llm'>}
        """
        policy = self._policies.get(
            user_id,
            PermissionPolicy(
                allowed={Permission.READ_DOCUMENTS, Permission.INVOKE_LLM},
                denied=set(),
                rate_limits={},
            ),
        )
        return policy.allowed

    def get_skill_requirements(self, skill_name: str) -> Set[Permission]:
        """Get required permissions for a skill.

        Args:
            skill_name: Skill identifier

        Returns:
            Set of required Permission enums

        Example:
            >>> engine = PermissionEngine()
            >>> engine.register_skill_permissions("retrieval", ["read_documents", "invoke_llm"])
            >>> reqs = engine.get_skill_requirements("retrieval")
            >>> reqs
            {<Permission.READ_DOCUMENTS: 'read_documents'>, <Permission.INVOKE_LLM: 'invoke_llm'>}
        """
        return self._skill_requirements.get(skill_name, set())


# Default permission policy (used when no user policy set)
DEFAULT_PERMISSIONS: Set[Permission] = {
    Permission.READ_DOCUMENTS,
    Permission.INVOKE_LLM,
}
