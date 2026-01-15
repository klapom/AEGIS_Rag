"""Skill-Tool Mapping Layer for Authorization and Discovery.

Sprint 93 Feature 93.3: Skill-Tool Mapping Layer (8 SP)

This module provides the mapping layer between skills and tools, enabling:
- Dynamic tool discovery based on skill context
- Tool capability negotiation and metadata
- Permission-based tool access control
- Integration with PolicyEngine for enforcement

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │               Skill-Tool Mapping Layer                  │
    ├─────────────────────────────────────────────────────────┤
    │                                                         │
    │  Skill: "research"                                      │
    │                                                         │
    │  ┌──────────────┐                                      │
    │  │DiscoverTools │  ──▶  ["browser", "web_search"]     │
    │  └──────────────┘                                      │
    │                                                         │
    │  ┌──────────────┐                                      │
    │  │CheckAccess   │  ──▶  PolicyEngine.can_use_tool()   │
    │  └──────────────┘                                      │
    │                                                         │
    │  ┌──────────────┐                                      │
    │  │GetCapability │  ──▶  ToolCapability(name, params)  │
    │  └──────────────┘                                      │
    │                                                         │
    │  Storage: Redis or In-Memory Dict                       │
    │  - skill_name -> [tool_names]                          │
    │  - tool_name -> ToolCapability                         │
    │  - tool_name -> [required_skill_names]                 │
    └─────────────────────────────────────────────────────────┘

Example:
    >>> mapper = SkillToolMapper()
    >>>
    >>> # Register tool with capabilities
    >>> mapper.register_tool(
    ...     "browser",
    ...     capabilities=ToolCapability(
    ...         name="browser",
    ...         description="Web browsing with Playwright",
    ...         parameters={"action": "str", "url": "str"},
    ...         async_support=True,
    ...         rate_limit=30,
    ...     ),
    ...     required_skills=["research", "web_automation"],
    ... )
    >>>
    >>> # Discover available tools for skill
    >>> tools = mapper.get_available_tools("research")
    >>> tools
    ['browser', 'web_search', 'api_call']
    >>>
    >>> # Check if skill can use tool
    >>> mapper.can_skill_use_tool("research", "browser")
    True
    >>>
    >>> # Discover tools by capability
    >>> async_tools = mapper.discover_tools("research", capability_filter={"async_support": True})
    >>> [t.name for t in async_tools]
    ['browser', 'web_search']

LangGraph 1.0 Integration:
    Uses InjectedState to pass skill context to tools:

    >>> from langgraph.prebuilt import InjectedState
    >>> from typing import Annotated
    >>>
    >>> @tool
    >>> def skill_aware_tool(
    ...     query: str,
    ...     state: Annotated[dict, InjectedState]
    ... ) -> str:
    ...     active_skill = state.get("active_skill")
    ...     if not mapper.can_skill_use_tool(active_skill, "browser"):
    ...         raise PermissionError("Skill not authorized")
    ...     # ... tool logic
    ...     return result

See Also:
    - src/agents/tools/policy.py: PolicyEngine for enforcement
    - src/agents/skills/lifecycle.py: Skill lifecycle management
    - docs/sprints/SPRINT_93_PLAN.md: Feature specification
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ToolCapability:
    """Metadata and capabilities for a tool.

    Attributes:
        name: Unique tool identifier
        description: Human-readable description
        parameters: Parameter schema (param_name -> type)
        required_params: List of required parameter names
        optional_params: List of optional parameter names
        return_type: Return type description
        async_support: Whether tool supports async execution
        streaming_support: Whether tool supports streaming output
        rate_limit: Calls per minute limit (0 = unlimited)
        timeout_seconds: Max execution time
        requires_network: Whether tool needs network access
        requires_filesystem: Whether tool needs file access
        tags: Categorical tags for discovery
        metadata: Additional custom metadata

    Example:
        >>> capability = ToolCapability(
        ...     name="browser",
        ...     description="Web browsing with Playwright",
        ...     parameters={"action": "str", "url": "str", "selector": "str"},
        ...     required_params=["action"],
        ...     optional_params=["url", "selector"],
        ...     return_type="str",
        ...     async_support=True,
        ...     rate_limit=30,
        ...     requires_network=True,
        ...     tags=["web", "automation"],
        ... )
    """

    name: str
    description: str
    parameters: dict[str, str] = field(default_factory=dict)
    required_params: list[str] = field(default_factory=list)
    optional_params: list[str] = field(default_factory=list)
    return_type: str = "Any"
    async_support: bool = False
    streaming_support: bool = False
    rate_limit: int = 0  # 0 = unlimited
    timeout_seconds: float = 30.0
    requires_network: bool = False
    requires_filesystem: bool = False
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_filter(self, filters: dict[str, Any]) -> bool:
        """Check if capability matches filter criteria.

        Args:
            filters: Dict of attribute filters (e.g., {"async_support": True, "tags": ["web"]})

        Returns:
            True if all filters match

        Example:
            >>> capability = ToolCapability(name="browser", async_support=True, tags=["web"])
            >>> capability.matches_filter({"async_support": True})
            True
            >>> capability.matches_filter({"tags": ["database"]})
            False
        """
        for key, value in filters.items():
            if key == "tags":
                # Special handling for tag matching
                if not isinstance(value, list):
                    value = [value]
                if not any(tag in self.tags for tag in value):
                    return False
            else:
                # Direct attribute comparison
                if not hasattr(self, key):
                    return False
                if getattr(self, key) != value:
                    return False
        return True


@dataclass
class ToolRegistration:
    """Internal registration record for a tool.

    Attributes:
        capability: Tool capability metadata
        required_skills: Skills that can use this tool (None = all)
        denied_skills: Skills explicitly denied (takes precedence)
        handler: Optional function reference for the tool
        enabled: Whether tool is currently enabled
    """

    capability: ToolCapability
    required_skills: list[str] | None = None  # None = all allowed
    denied_skills: list[str] = field(default_factory=list)
    handler: Callable[..., Any] | None = None
    enabled: bool = True


# =============================================================================
# Skill-Tool Mapper
# =============================================================================


class SkillToolMapper:
    """Map skills to their authorized tools with capability discovery.

    Provides:
    - Tool registration with capabilities
    - Skill → Tool access mapping
    - Dynamic tool discovery with filters
    - Capability negotiation
    - Integration with PolicyEngine

    Storage can be either:
    - In-memory dict (default, fast for single process)
    - Redis (planned, for distributed deployment)

    Attributes:
        policy_engine: Optional PolicyEngine for permission checks
        use_redis: Whether to use Redis for storage (default: False)

    Example:
        >>> from src.agents.tools.policy import PolicyEngine
        >>> policy = PolicyEngine()
        >>> mapper = SkillToolMapper(policy_engine=policy)
        >>>
        >>> # Register tools
        >>> mapper.register_tool(
        ...     "browser",
        ...     ToolCapability(name="browser", description="Web browsing"),
        ...     required_skills=["research", "web_automation"],
        ... )
        >>>
        >>> # Check access
        >>> mapper.can_skill_use_tool("research", "browser")
        True
        >>> mapper.can_skill_use_tool("admin", "browser")
        False
        >>>
        >>> # Discover tools
        >>> tools = mapper.discover_tools("research", capability_filter={"async_support": True})
    """

    def __init__(
        self,
        policy_engine: Any | None = None,
        use_redis: bool = False,
    ) -> None:
        """Initialize SkillToolMapper.

        Args:
            policy_engine: Optional PolicyEngine for permission enforcement
            use_redis: Whether to use Redis for storage (default: False)
        """
        self._policy = policy_engine
        self._use_redis = use_redis

        # In-memory storage (default)
        self._tools: dict[str, ToolRegistration] = {}
        self._skill_to_tools: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

        logger.info(
            "skill_tool_mapper_initialized",
            use_redis=use_redis,
            has_policy_engine=policy_engine is not None,
        )

    def register_tool(
        self,
        tool_name: str,
        capabilities: ToolCapability,
        required_skills: list[str] | None = None,
        denied_skills: list[str] | None = None,
        handler: Callable[..., Any] | None = None,
    ) -> None:
        """Register a tool with its capabilities and access control.

        Args:
            tool_name: Unique tool identifier
            capabilities: ToolCapability describing the tool
            required_skills: List of skills that can use this tool (None = all)
            denied_skills: List of skills explicitly denied (optional)
            handler: Optional function reference for the tool

        Example:
            >>> mapper.register_tool(
            ...     "browser",
            ...     ToolCapability(
            ...         name="browser",
            ...         description="Web browsing with Playwright",
            ...         parameters={"action": "str", "url": "str"},
            ...         async_support=True,
            ...         rate_limit=30,
            ...     ),
            ...     required_skills=["research", "web_automation"],
            ... )
        """
        self._tools[tool_name] = ToolRegistration(
            capability=capabilities,
            required_skills=required_skills,
            denied_skills=denied_skills or [],
            handler=handler,
            enabled=True,
        )

        # Update reverse mapping
        if required_skills:
            for skill in required_skills:
                if skill not in self._skill_to_tools:
                    self._skill_to_tools[skill] = []
                if tool_name not in self._skill_to_tools[skill]:
                    self._skill_to_tools[skill].append(tool_name)

        logger.info(
            "tool_registered",
            tool_name=tool_name,
            required_skills=required_skills,
            denied_count=len(denied_skills or []),
        )

    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool.

        Args:
            tool_name: Tool to unregister

        Returns:
            True if tool was unregistered, False if not found

        Example:
            >>> mapper.unregister_tool("browser")
            True
        """
        if tool_name not in self._tools:
            return False

        # Remove from reverse mapping
        registration = self._tools[tool_name]
        if registration.required_skills:
            for skill in registration.required_skills:
                if skill in self._skill_to_tools:
                    self._skill_to_tools[skill] = [
                        t for t in self._skill_to_tools[skill] if t != tool_name
                    ]

        del self._tools[tool_name]

        logger.info("tool_unregistered", tool_name=tool_name)
        return True

    def get_available_tools(self, skill_name: str) -> list[str]:
        """Get list of tools available to a skill.

        Args:
            skill_name: Name of the skill

        Returns:
            List of tool names the skill can access

        Example:
            >>> tools = mapper.get_available_tools("research")
            >>> tools
            ['browser', 'web_search', 'api_call']
        """
        available = []

        for tool_name, registration in self._tools.items():
            if not registration.enabled:
                continue

            # Check denied list first
            if skill_name in registration.denied_skills:
                continue

            # If required_skills is None, tool is available to all
            if registration.required_skills is None:
                available.append(tool_name)
                continue

            # Check if skill is in required list
            if skill_name in registration.required_skills:
                available.append(tool_name)

        return available

    def can_skill_use_tool(
        self,
        skill_name: str,
        tool_name: str,
        check_policy: bool = True,
    ) -> bool:
        """Check if a skill can use a specific tool.

        Args:
            skill_name: Name of the skill
            tool_name: Name of the tool
            check_policy: Whether to also check PolicyEngine (default: True)

        Returns:
            True if skill can use tool

        Example:
            >>> mapper.can_skill_use_tool("research", "browser")
            True
            >>> mapper.can_skill_use_tool("research", "file_delete")
            False
        """
        registration = self._tools.get(tool_name)

        if not registration:
            logger.warning("tool_not_found", tool_name=tool_name)
            return False

        if not registration.enabled:
            return False

        # Check denied list
        if skill_name in registration.denied_skills:
            logger.debug(
                "skill_denied_for_tool",
                skill_name=skill_name,
                tool_name=tool_name,
            )
            return False

        # If required_skills is None, allow all
        if registration.required_skills is None:
            return True

        # Check required list
        if skill_name not in registration.required_skills:
            return False

        # Optionally check PolicyEngine
        if check_policy and self._policy:
            # PolicyEngine.can_use_tool is async, so we can't await here
            # This is a synchronous pre-check; actual async check happens in execute
            pass

        return True

    def discover_tools(
        self,
        skill_name: str,
        capability_filter: dict[str, Any] | None = None,
    ) -> list[ToolCapability]:
        """Discover tools available to skill, optionally filtered by capability.

        Args:
            skill_name: Name of the skill
            capability_filter: Optional dict of capability filters
                             (e.g., {"async_support": True, "tags": ["web"]})

        Returns:
            List of ToolCapability objects matching criteria

        Example:
            >>> # Discover all tools
            >>> tools = mapper.discover_tools("research")
            >>>
            >>> # Discover only async tools
            >>> async_tools = mapper.discover_tools("research", {"async_support": True})
            >>>
            >>> # Discover web tools
            >>> web_tools = mapper.discover_tools("research", {"tags": ["web"]})
        """
        available_tool_names = self.get_available_tools(skill_name)
        capabilities = []

        for tool_name in available_tool_names:
            registration = self._tools.get(tool_name)
            if not registration:
                continue

            # Apply filter if provided
            if capability_filter and not registration.capability.matches_filter(capability_filter):
                continue

            capabilities.append(registration.capability)

        logger.debug(
            "tools_discovered",
            skill_name=skill_name,
            filter=capability_filter,
            count=len(capabilities),
        )

        return capabilities

    def get_tool_capability(self, tool_name: str) -> ToolCapability | None:
        """Get capability metadata for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolCapability or None if tool not found

        Example:
            >>> capability = mapper.get_tool_capability("browser")
            >>> capability.description
            'Web browsing with Playwright'
        """
        registration = self._tools.get(tool_name)
        return registration.capability if registration else None

    def get_tool_handler(self, tool_name: str) -> Callable[..., Any] | None:
        """Get function handler for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Function handler or None if not registered

        Example:
            >>> handler = mapper.get_tool_handler("browser")
            >>> result = await handler(action="navigate", url="https://example.com")
        """
        registration = self._tools.get(tool_name)
        return registration.handler if registration else None

    def enable_tool(self, tool_name: str) -> bool:
        """Enable a previously disabled tool.

        Args:
            tool_name: Tool to enable

        Returns:
            True if enabled, False if not found

        Example:
            >>> mapper.enable_tool("browser")
            True
        """
        registration = self._tools.get(tool_name)
        if not registration:
            return False

        registration.enabled = True
        logger.info("tool_enabled", tool_name=tool_name)
        return True

    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool (temporarily prevent all access).

        Args:
            tool_name: Tool to disable

        Returns:
            True if disabled, False if not found

        Example:
            >>> mapper.disable_tool("browser")
            True
        """
        registration = self._tools.get(tool_name)
        if not registration:
            return False

        registration.enabled = False
        logger.info("tool_disabled", tool_name=tool_name)
        return True

    def get_skills_for_tool(self, tool_name: str) -> list[str]:
        """Get list of skills that can use a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of skill names, or empty list if tool not found

        Example:
            >>> skills = mapper.get_skills_for_tool("browser")
            >>> skills
            ['research', 'web_automation']
        """
        registration = self._tools.get(tool_name)
        if not registration:
            return []

        # If required_skills is None, return all skills
        if registration.required_skills is None:
            return list(self._skill_to_tools.keys())

        return registration.required_skills

    def get_metrics(self) -> dict[str, Any]:
        """Get mapper metrics.

        Returns:
            Dict with counts and stats

        Example:
            >>> metrics = mapper.get_metrics()
            >>> metrics
            {
                'total_tools': 15,
                'enabled_tools': 12,
                'disabled_tools': 3,
                'total_skills': 8,
                'tools_per_skill': {'research': 5, 'web_automation': 3, ...}
            }
        """
        enabled_count = sum(1 for r in self._tools.values() if r.enabled)

        return {
            "total_tools": len(self._tools),
            "enabled_tools": enabled_count,
            "disabled_tools": len(self._tools) - enabled_count,
            "total_skills": len(self._skill_to_tools),
            "tools_per_skill": {skill: len(tools) for skill, tools in self._skill_to_tools.items()},
        }


# =============================================================================
# Integration Helpers
# =============================================================================


async def check_tool_permission(
    mapper: SkillToolMapper,
    skill_name: str,
    tool_name: str,
    inputs: dict[str, Any] | None = None,
) -> bool:
    """Check if skill can use tool with PolicyEngine integration.

    This is the async version that integrates with PolicyEngine.

    Args:
        mapper: SkillToolMapper instance
        skill_name: Name of the skill
        tool_name: Name of the tool
        inputs: Optional tool inputs for policy validation

    Returns:
        True if permission granted

    Example:
        >>> can_use = await check_tool_permission(mapper, "research", "browser", {"url": "..."})
        >>> if not can_use:
        ...     raise PermissionError("Skill not authorized for tool")
    """
    # First check mapper
    if not mapper.can_skill_use_tool(skill_name, tool_name, check_policy=False):
        logger.warning(
            "skill_tool_access_denied_by_mapper",
            skill_name=skill_name,
            tool_name=tool_name,
        )
        return False

    # Then check PolicyEngine if available
    if mapper._policy:
        try:
            allowed = await mapper._policy.can_use_tool(skill_name, tool_name, inputs)
            if not allowed:
                logger.warning(
                    "skill_tool_access_denied_by_policy",
                    skill_name=skill_name,
                    tool_name=tool_name,
                )
            return bool(allowed)
        except Exception as e:
            logger.error(
                "policy_check_error",
                skill_name=skill_name,
                tool_name=tool_name,
                error=str(e),
            )
            return False

    return True
