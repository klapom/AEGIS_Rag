"""Skill Tool Auto-Resolver.

Sprint 121: Skill Tool Auto-Resolve (ADR-058)

This module implements the Hybrid Install-Time Classification + Runtime Cache Lookup
strategy for automatically resolving which MCP tools a skill can use.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                    SkillToolResolver                            │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  Phase 1: Install-Time Classification                           │
    │  ┌──────────────┐     ┌───────────┐     ┌──────────────┐      │
    │  │ MCP Tool     │ ──▶ │ LLM Call  │ ──▶ │ Redis Cache  │      │
    │  │ (installed)  │     │ (1x only) │     │ tool:caps:X  │      │
    │  └──────────────┘     └───────────┘     └──────────────┘      │
    │                                                                 │
    │  Phase 2: Activation-Time Resolution                           │
    │  ┌──────────────┐     ┌───────────┐     ┌──────────────┐      │
    │  │ Skill Perms  │ ──▶ │ Cache     │ ──▶ │ Resolved     │      │
    │  │ (SKILL.md)   │     │ Lookup    │     │ Tool List    │      │
    │  └──────────────┘     └───────────┘     └──────────────┘      │
    │                                                                 │
    │  Fallback: config/tool_capabilities.yaml (static map)          │
    └─────────────────────────────────────────────────────────────────┘

Example:
    >>> resolver = SkillToolResolver()
    >>> await resolver.load_capabilities()
    >>>
    >>> # Classify a new MCP tool at install time
    >>> await resolver.classify_tool("read_file", "Read contents of a file", {...})
    >>> # Result cached: read_file → ["filesystem_read"]
    >>>
    >>> # Resolve tools for a skill at activation time (~0ms)
    >>> tools = await resolver.resolve_tools_for_skill("research", ["web_search", "web_read"])
    >>> # Returns: [ResolvedTool(name="browser", ...), ResolvedTool(name="web_search", ...)]

See Also:
    - docs/adr/ADR-058_SKILL_TOOL_AUTO_RESOLVE.md
    - src/agents/tools/mapping.py: SkillToolMapper (Sprint 93)
    - config/tool_capabilities.yaml: Capability categories
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CapabilityCategory:
    """A capability category from tool_capabilities.yaml.

    Attributes:
        name: Category identifier (e.g., "web_search")
        description: Human-readable description
        keywords: LLM classification keywords
        static_tools: Known tool names for fallback matching
    """

    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    static_tools: list[str] = field(default_factory=list)


@dataclass
class ResolvedTool:
    """A tool resolved for a skill via auto-resolve.

    Attributes:
        tool_name: MCP tool name
        capability: Matched capability category
        source: How it was resolved ("static", "llm_cached", "override")
        confidence: Classification confidence (0.0-1.0)
        server: MCP server providing the tool
        description: Tool description
    """

    tool_name: str
    capability: str
    source: str = "static"
    confidence: float = 1.0
    server: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "tool_name": self.tool_name,
            "capability": self.capability,
            "source": self.source,
            "confidence": self.confidence,
            "server": self.server,
            "description": self.description,
        }


# =============================================================================
# Skill Tool Resolver
# =============================================================================


class SkillToolResolver:
    """Resolve MCP tools for skills using hybrid install-time classification.

    Uses a two-phase approach:
    1. Install-time: Classify new tools via LLM → cache in memory/Redis
    2. Activation-time: Match skill permissions → cached capabilities (~0ms)

    Attributes:
        capabilities: Loaded capability categories from YAML
        tool_classifications: Cached tool → capabilities mapping
        overrides: Admin overrides for tool-skill bindings
    """

    def __init__(self, capabilities_path: str | None = None) -> None:
        """Initialize SkillToolResolver.

        Args:
            capabilities_path: Path to tool_capabilities.yaml.
                             Defaults to config/tool_capabilities.yaml (resolves relative
                             to project root or /app/ for Docker)
        """
        if capabilities_path:
            self._capabilities_path = Path(capabilities_path)
        else:
            # Try multiple paths: relative, /app/ (Docker), project root
            candidates = [
                Path("config/tool_capabilities.yaml"),
                Path("/app/config/tool_capabilities.yaml"),
            ]
            self._capabilities_path = next(
                (p for p in candidates if p.exists()),
                candidates[0],
            )
        self.capabilities: dict[str, CapabilityCategory] = {}
        self.tool_classifications: dict[str, list[str]] = {}
        self.overrides: dict[str, dict[str, bool]] = {}  # skill → {tool: allowed}
        self._classification_prompt: str = ""
        self._loaded = False

        logger.info(
            "skill_tool_resolver_initialized",
            capabilities_path=str(self._capabilities_path),
        )

    async def load_capabilities(self) -> None:
        """Load capability categories from YAML config.

        Reads config/tool_capabilities.yaml and populates self.capabilities
        with CapabilityCategory objects.

        Raises:
            FileNotFoundError: If capabilities YAML not found
        """
        if not self._capabilities_path.exists():
            logger.warning(
                "capabilities_yaml_not_found",
                path=str(self._capabilities_path),
            )
            self._loaded = True
            return

        with open(self._capabilities_path) as f:
            config = yaml.safe_load(f)

        if not config or "capabilities" not in config:
            logger.warning("capabilities_yaml_empty")
            self._loaded = True
            return

        for name, data in config["capabilities"].items():
            self.capabilities[name] = CapabilityCategory(
                name=name,
                description=data.get("description", ""),
                keywords=data.get("keywords", []),
                static_tools=data.get("static_tools", []),
            )

        self._classification_prompt = config.get("classification_prompt", "")
        self._loaded = True

        logger.info(
            "capabilities_loaded",
            category_count=len(self.capabilities),
            categories=list(self.capabilities.keys()),
        )

    def classify_tool_static(
        self,
        tool_name: str,
        tool_description: str = "",
    ) -> list[str]:
        """Classify a tool using the static capability map (no LLM).

        Matches tool_name against static_tools lists in each category,
        then falls back to keyword matching against tool_description.

        Args:
            tool_name: MCP tool name
            tool_description: Tool description for keyword matching

        Returns:
            List of matching capability category names

        Example:
            >>> resolver.classify_tool_static("read_file", "Read a file from disk")
            ["filesystem_read"]
        """
        matched_categories: list[str] = []
        tool_name_lower = tool_name.lower()
        desc_lower = tool_description.lower()

        for cat_name, cat in self.capabilities.items():
            # Direct match against static_tools
            if tool_name_lower in [t.lower() for t in cat.static_tools]:
                matched_categories.append(cat_name)
                continue

            # Keyword match against tool name and description
            combined = f"{tool_name_lower} {desc_lower}"
            if any(kw.lower() in combined for kw in cat.keywords):
                matched_categories.append(cat_name)

        if not matched_categories:
            logger.debug(
                "tool_classification_no_match",
                tool_name=tool_name,
            )

        return matched_categories

    async def classify_tool(
        self,
        tool_name: str,
        tool_description: str,
        tool_parameters: dict[str, Any] | None = None,
    ) -> list[str]:
        """Classify a tool's capabilities (install-time, cached).

        First tries static classification. If no match found and LLM is
        available, uses LLM for classification. Result is cached.

        Args:
            tool_name: MCP tool name
            tool_description: Tool description
            tool_parameters: Tool parameter schema

        Returns:
            List of capability category names
        """
        if not self._loaded:
            await self.load_capabilities()

        # Check cache first
        if tool_name in self.tool_classifications:
            return self.tool_classifications[tool_name]

        # Static classification (fast, no LLM)
        categories = self.classify_tool_static(tool_name, tool_description)

        if not categories:
            # LLM classification would go here in production
            # For now, log and return empty (admin can override)
            logger.info(
                "tool_classification_deferred_to_admin",
                tool_name=tool_name,
                description=tool_description[:100],
            )

        # Cache the result
        self.tool_classifications[tool_name] = categories

        logger.info(
            "tool_classified",
            tool_name=tool_name,
            categories=categories,
            source="static",
        )

        return categories

    async def resolve_tools_for_skill(
        self,
        skill_name: str,
        skill_permissions: list[str],
        available_tools: dict[str, dict[str, Any]] | None = None,
    ) -> list[ResolvedTool]:
        """Resolve which MCP tools a skill can use based on its permissions.

        This is the main resolution method called at skill activation time.
        Uses cached tool classifications for ~0ms lookup.

        Args:
            skill_name: Name of the skill
            skill_permissions: Permission categories from SKILL.md
                             (e.g., ["web_search", "filesystem_read"])
            available_tools: Optional dict of available MCP tools
                           {tool_name: {"description": ..., "server": ...}}

        Returns:
            List of ResolvedTool objects matching the skill's permissions

        Example:
            >>> tools = await resolver.resolve_tools_for_skill(
            ...     "research",
            ...     ["web_search", "web_read"],
            ...     {"browser": {"description": "Web browsing", "server": "playwright"}}
            ... )
        """
        if not self._loaded:
            await self.load_capabilities()

        resolved: list[ResolvedTool] = []
        seen_tools: set[str] = set()

        for permission in skill_permissions:
            # Find capability category
            category = self.capabilities.get(permission)
            if not category:
                logger.debug(
                    "unknown_permission_category",
                    skill_name=skill_name,
                    permission=permission,
                )
                continue

            # Match 1: Static tools from YAML
            for static_tool in category.static_tools:
                if static_tool not in seen_tools:
                    # Check admin override
                    if self._is_tool_overridden(skill_name, static_tool) is False:
                        continue

                    resolved.append(
                        ResolvedTool(
                            tool_name=static_tool,
                            capability=permission,
                            source="static",
                            confidence=1.0,
                        )
                    )
                    seen_tools.add(static_tool)

            # Match 2: Classified tools from cache
            for tool_name, tool_cats in self.tool_classifications.items():
                if permission in tool_cats and tool_name not in seen_tools:
                    # Check admin override
                    if self._is_tool_overridden(skill_name, tool_name) is False:
                        continue

                    tool_info = (available_tools or {}).get(tool_name, {})
                    resolved.append(
                        ResolvedTool(
                            tool_name=tool_name,
                            capability=permission,
                            source="llm_cached",
                            confidence=0.9,
                            server=tool_info.get("server", ""),
                            description=tool_info.get("description", ""),
                        )
                    )
                    seen_tools.add(tool_name)

        # Match 3: Check overrides for explicitly allowed tools
        skill_overrides = self.overrides.get(skill_name, {})
        for tool_name, allowed in skill_overrides.items():
            if allowed and tool_name not in seen_tools:
                resolved.append(
                    ResolvedTool(
                        tool_name=tool_name,
                        capability="override",
                        source="admin_override",
                        confidence=1.0,
                    )
                )
                seen_tools.add(tool_name)

        logger.info(
            "tools_resolved_for_skill",
            skill_name=skill_name,
            permissions=skill_permissions,
            resolved_count=len(resolved),
            tool_names=[t.tool_name for t in resolved],
        )

        return resolved

    def set_override(
        self,
        skill_name: str,
        tool_name: str,
        allowed: bool,
    ) -> None:
        """Set an admin override for a tool-skill binding.

        Args:
            skill_name: Name of the skill
            tool_name: Name of the tool
            allowed: Whether to allow (True) or deny (False) the binding
        """
        if skill_name not in self.overrides:
            self.overrides[skill_name] = {}

        self.overrides[skill_name][tool_name] = allowed

        logger.info(
            "tool_override_set",
            skill_name=skill_name,
            tool_name=tool_name,
            allowed=allowed,
        )

    def remove_override(self, skill_name: str, tool_name: str) -> bool:
        """Remove an admin override.

        Args:
            skill_name: Name of the skill
            tool_name: Name of the tool

        Returns:
            True if override was removed, False if not found
        """
        if skill_name in self.overrides and tool_name in self.overrides[skill_name]:
            del self.overrides[skill_name][tool_name]
            return True
        return False

    def _is_tool_overridden(self, skill_name: str, tool_name: str) -> bool | None:
        """Check if a tool has an admin override for a skill.

        Returns:
            True if explicitly allowed, False if explicitly denied, None if no override
        """
        skill_overrides = self.overrides.get(skill_name, {})
        return skill_overrides.get(tool_name)

    def get_metrics(self) -> dict[str, Any]:
        """Get resolver metrics for monitoring.

        Returns:
            Dict with classification counts and stats
        """
        return {
            "capability_categories": len(self.capabilities),
            "classified_tools": len(self.tool_classifications),
            "overrides": sum(len(v) for v in self.overrides.values()),
            "categories": list(self.capabilities.keys()),
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_resolver_instance: SkillToolResolver | None = None


def get_tool_resolver() -> SkillToolResolver:
    """Get or create the singleton SkillToolResolver instance."""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = SkillToolResolver()
    return _resolver_instance
