"""Skill Lifecycle Management API.

Sprint Context:
    - Sprint 92 (2026-01-14): Feature 92.2 - Skill Lifecycle API (10 SP)

Complete lifecycle management for skills: Load, Unload, Version, Hot-reload.

Based on: Anthropic Agent Skills Architecture
    https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Architecture:
    ┌──────────┐    load()    ┌──────────┐   activate()
    │DISCOVERED│ ──────────▶ │  LOADED  │ ──────────────────┐
    └──────────┘              └──────────┘                   │
         ▲                         │                         ▼
         │                    unload()                  ┌──────┐
    discover()                     │                   │ACTIVE│
         │                         ▼                   └──┬────┘
         │                   ┌──────────┐                 │
         └───────────────── │ UNLOADED │ ◀── deactivate()│
                            └──────────┘                  │

    Version Transitions:
    ┌──────────┐   upgrade()  ┌──────────┐
    │ v1.0.0   │ ──────────▶ │ v1.1.0   │
    └──────────┘              └──────────┘
         │
         └── rollback() ─────────────────▶

Example:
    >>> from src.agents.skills.lifecycle import SkillLifecycleManager
    >>> from pathlib import Path
    >>>
    >>> manager = SkillLifecycleManager(
    ...     skills_dir=Path("skills"),
    ...     max_loaded_skills=20,
    ...     max_active_skills=5,
    ...     context_budget=10000
    ... )
    >>>
    >>> # Load and activate a skill
    >>> await manager.load("reflection")
    >>> instructions = await manager.activate("reflection", context_allocation=2000)
    >>>
    >>> # Upgrade to new version
    >>> await manager.upgrade("reflection", "1.1.0")
    >>>
    >>> # Deactivate and unload
    >>> await manager.deactivate("reflection")
    >>> await manager.unload("reflection")

Notes:
    - State machine ensures valid transitions
    - LRU eviction when capacity reached
    - Hot-reload preserves active state
    - Event hooks for custom behavior
    - Version compatibility checks

See Also:
    - docs/sprints/SPRINT_92_PLAN.md: Feature specification
    - src/agents/skills/registry.py: Skill registry system
    - Anthropic Agent Skills: https://platform.claude.com/docs/agents-skills
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class SkillState(Enum):
    """Skill lifecycle states.

    States:
        DISCOVERED: Found but not loaded into memory
        LOADED: In memory, not currently active in context
        ACTIVE: Currently in use with context allocation
        UNLOADED: Removed from memory
        ERROR: Failed to load or activate

    Example:
        >>> state = SkillState.LOADED
        >>> state.value
        'loaded'
    """

    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVE = "active"
    UNLOADED = "unloaded"
    ERROR = "error"


@dataclass
class SkillVersion:
    """Version information for a skill.

    Follows semantic versioning (semver): MAJOR.MINOR.PATCH

    Attributes:
        major: Major version (breaking changes)
        minor: Minor version (backward-compatible features)
        patch: Patch version (bug fixes)

    Example:
        >>> version = SkillVersion(1, 2, 3)
        >>> str(version)
        '1.2.3'
        >>> version.is_compatible(SkillVersion(1, 3, 0))
        True
        >>> version.is_compatible(SkillVersion(2, 0, 0))
        False
    """

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """Format version as string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> "SkillVersion":
        """Parse version string to SkillVersion.

        Args:
            version_str: Version string (e.g., "1.2.3")

        Returns:
            SkillVersion object

        Example:
            >>> version = SkillVersion.parse("1.2.3")
            >>> version.major
            1
        """
        parts = version_str.split(".")
        return cls(
            major=int(parts[0]),
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )

    def is_compatible(self, other: "SkillVersion") -> bool:
        """Check if versions are compatible (same major version).

        Args:
            other: Version to check compatibility with

        Returns:
            True if compatible (same major version)

        Example:
            >>> v1 = SkillVersion(1, 2, 0)
            >>> v2 = SkillVersion(1, 3, 0)
            >>> v1.is_compatible(v2)
            True
            >>> v3 = SkillVersion(2, 0, 0)
            >>> v1.is_compatible(v3)
            False
        """
        return self.major == other.major


@dataclass
class SkillLifecycleEvent:
    """Event in skill lifecycle.

    Attributes:
        skill_name: Name of skill
        event_type: Type of event (load, unload, activate, deactivate, upgrade)
        timestamp: When event occurred
        old_state: State before transition
        new_state: State after transition
        version: Version involved (optional)
        metadata: Additional event data

    Example:
        >>> event = SkillLifecycleEvent(
        ...     skill_name="reflection",
        ...     event_type="activate",
        ...     timestamp=datetime.now(),
        ...     old_state=SkillState.LOADED,
        ...     new_state=SkillState.ACTIVE,
        ...     version="1.0.0",
        ...     metadata={"context_allocation": 2000}
        ... )
    """

    skill_name: str
    event_type: str
    timestamp: datetime
    old_state: SkillState
    new_state: SkillState
    version: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SkillLifecycleManager:
    """Manage skill lifecycle: Load, Unload, Version, Hot-reload.

    Based on: Anthropic Agent Skills Architecture
        https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

    Features:
        - State machine for skill lifecycle
        - Version management with upgrade/rollback
        - Context budget enforcement
        - Hot-reload without losing state
        - LRU eviction when capacity reached
        - Event hooks for custom behavior

    Attributes:
        skills_dir: Directory containing skill packages
        max_loaded: Maximum loaded skills (default: 20)
        max_active: Maximum active skills (default: 5)
        context_budget: Total context budget in tokens (default: 10000)

    Example:
        >>> from pathlib import Path
        >>> manager = SkillLifecycleManager(
        ...     skills_dir=Path("skills"),
        ...     max_loaded_skills=20,
        ...     max_active_skills=5,
        ...     context_budget=10000
        ... )
        >>>
        >>> await manager.load("reflection")
        >>> await manager.activate("reflection", context_allocation=2000)
        >>> manager.get_state("reflection")
        <SkillState.ACTIVE: 'active'>
    """

    def __init__(
        self,
        skills_dir: Path,
        max_loaded_skills: int = 20,
        max_active_skills: int = 5,
        context_budget: int = 10000,
    ):
        """Initialize skill lifecycle manager.

        Args:
            skills_dir: Directory containing skill packages
            max_loaded_skills: Maximum loaded skills (default: 20)
            max_active_skills: Maximum active skills (default: 5)
            context_budget: Total context budget in tokens (default: 10000)
        """
        self.skills_dir = skills_dir
        self.max_loaded = max_loaded_skills
        self.max_active = max_active_skills
        self.context_budget = context_budget

        # State tracking
        self._states: dict[str, SkillState] = {}
        self._versions: dict[str, SkillVersion] = {}
        self._loaded_content: dict[str, str] = {}
        self._active_context_usage: dict[str, int] = {}
        self._events: list[SkillLifecycleEvent] = []

        # Hooks
        self._on_load: list[Callable] = []
        self._on_unload: list[Callable] = []
        self._on_error: list[Callable] = []

        logger.info(
            "skill_lifecycle_manager_initialized",
            skills_dir=str(skills_dir),
            max_loaded=max_loaded_skills,
            max_active=max_active_skills,
            context_budget=context_budget,
        )

    async def load(
        self,
        skill_name: str,
        version: Optional[str] = None,
    ) -> bool:
        """Load skill into memory.

        Args:
            skill_name: Name of skill to load
            version: Optional specific version (default: latest)

        Returns:
            True if loaded successfully

        Raises:
            FileNotFoundError: If skill not found

        Example:
            >>> success = await manager.load("reflection")
            >>> success
            True
            >>> manager.get_state("reflection")
            <SkillState.LOADED: 'loaded'>
        """
        old_state = self._states.get(skill_name, SkillState.DISCOVERED)

        # Check if already loaded
        if old_state in [SkillState.LOADED, SkillState.ACTIVE]:
            logger.debug("skill_already_loaded", skill_name=skill_name)
            return True

        # Check capacity
        loaded_count = sum(
            1 for s in self._states.values() if s in [SkillState.LOADED, SkillState.ACTIVE]
        )
        if loaded_count >= self.max_loaded:
            # Evict least recently used
            await self._evict_lru()
            logger.info("evicted_lru_skill", skill_name=skill_name)

        try:
            # Find skill directory
            skill_path = self._resolve_skill_path(skill_name, version)
            if not skill_path:
                raise FileNotFoundError(f"Skill not found: {skill_name}")

            # Load SKILL.md and resources
            content = await self._load_skill_content(skill_path)
            version_info = self._extract_version(content)

            # Store
            self._loaded_content[skill_name] = content
            self._versions[skill_name] = version_info
            self._states[skill_name] = SkillState.LOADED

            # Record event
            self._record_event(
                skill_name,
                "load",
                old_state,
                SkillState.LOADED,
                str(version_info),
            )

            # Fire hooks
            for hook in self._on_load:
                await hook(skill_name, content)

            logger.info(
                "skill_loaded",
                skill_name=skill_name,
                version=str(version_info),
                path=str(skill_path),
            )

            return True

        except Exception as e:
            self._states[skill_name] = SkillState.ERROR
            self._record_event(
                skill_name,
                "load_error",
                old_state,
                SkillState.ERROR,
                metadata={"error": str(e)},
            )
            for hook in self._on_error:
                await hook(skill_name, e)

            logger.error("skill_load_failed", skill_name=skill_name, error=str(e))
            return False

    async def unload(self, skill_name: str) -> bool:
        """Unload skill from memory.

        Args:
            skill_name: Name of skill to unload

        Returns:
            True if unloaded successfully

        Example:
            >>> await manager.unload("reflection")
            True
            >>> manager.get_state("reflection")
            <SkillState.UNLOADED: 'unloaded'>
        """
        old_state = self._states.get(skill_name)

        if old_state == SkillState.ACTIVE:
            # Must deactivate first
            await self.deactivate(skill_name)

        if skill_name in self._loaded_content:
            del self._loaded_content[skill_name]

        self._states[skill_name] = SkillState.UNLOADED

        self._record_event(skill_name, "unload", old_state, SkillState.UNLOADED)

        for hook in self._on_unload:
            await hook(skill_name)

        logger.info("skill_unloaded", skill_name=skill_name)
        return True

    async def activate(
        self,
        skill_name: str,
        context_allocation: Optional[int] = None,
    ) -> str:
        """Activate skill and return instructions for context.

        Args:
            skill_name: Name of skill to activate
            context_allocation: Optional token budget for this skill (default: 2000)

        Returns:
            Skill instructions to add to agent context

        Example:
            >>> instructions = await manager.activate("reflection", context_allocation=2000)
            >>> print(instructions[:100])
            # Reflection Skill
            ...
        """
        # Load if not loaded
        if self._states.get(skill_name) not in [SkillState.LOADED, SkillState.ACTIVE]:
            await self.load(skill_name)

        # Check active capacity
        active_count = sum(1 for s in self._states.values() if s == SkillState.ACTIVE)
        if active_count >= self.max_active:
            # Deactivate oldest active
            await self._deactivate_oldest()
            logger.info("deactivated_oldest_active_skill")

        # Check context budget
        current_usage = sum(self._active_context_usage.values())
        allocation = context_allocation or 2000

        if current_usage + allocation > self.context_budget:
            # Need to free context
            await self._free_context(allocation)
            logger.info("freed_context_for_new_skill", needed=allocation)

        old_state = self._states.get(skill_name, SkillState.LOADED)
        self._states[skill_name] = SkillState.ACTIVE
        self._active_context_usage[skill_name] = allocation

        self._record_event(
            skill_name,
            "activate",
            old_state,
            SkillState.ACTIVE,
            metadata={"context_allocation": allocation},
        )

        logger.info(
            "skill_activated",
            skill_name=skill_name,
            context_allocation=allocation,
        )

        return self._loaded_content.get(skill_name, "")

    async def deactivate(self, skill_name: str) -> bool:
        """Deactivate skill (remains loaded but not in context).

        Args:
            skill_name: Name of skill to deactivate

        Returns:
            True if deactivated successfully

        Example:
            >>> await manager.deactivate("reflection")
            True
            >>> manager.get_state("reflection")
            <SkillState.LOADED: 'loaded'>
        """
        old_state = self._states.get(skill_name)

        if old_state != SkillState.ACTIVE:
            return True

        self._states[skill_name] = SkillState.LOADED

        if skill_name in self._active_context_usage:
            del self._active_context_usage[skill_name]

        self._record_event(skill_name, "deactivate", old_state, SkillState.LOADED)

        logger.info("skill_deactivated", skill_name=skill_name)
        return True

    async def upgrade(
        self,
        skill_name: str,
        target_version: str,
    ) -> bool:
        """Upgrade skill to new version with hot-reload.

        Args:
            skill_name: Name of skill to upgrade
            target_version: Version to upgrade to (e.g., "1.1.0")

        Returns:
            True if upgraded successfully

        Raises:
            ValueError: If version incompatible

        Example:
            >>> await manager.upgrade("reflection", "1.1.0")
            True
            >>> manager._versions["reflection"]
            SkillVersion(major=1, minor=1, patch=0)
        """
        current_version = self._versions.get(skill_name)
        target = SkillVersion.parse(target_version)

        # Check compatibility
        if current_version and not current_version.is_compatible(target):
            raise ValueError(
                f"Incompatible version upgrade: {current_version} -> {target}. "
                "Major version must match."
            )

        # Hot-reload: unload and reload with new version
        was_active = self._states.get(skill_name) == SkillState.ACTIVE
        context_alloc = self._active_context_usage.get(skill_name)

        await self.unload(skill_name)
        await self.load(skill_name, target_version)

        if was_active:
            await self.activate(skill_name, context_alloc)

        self._record_event(
            skill_name,
            "upgrade",
            SkillState.LOADED,
            SkillState.LOADED,
            target_version,
            metadata={"from_version": str(current_version) if current_version else None},
        )

        logger.info(
            "skill_upgraded",
            skill_name=skill_name,
            from_version=str(current_version) if current_version else "unknown",
            to_version=target_version,
        )

        return True

    async def rollback(self, skill_name: str, event_count: int = 1) -> bool:
        """Rollback skill to previous version.

        Args:
            skill_name: Name of skill
            event_count: Number of versions to rollback (default: 1)

        Returns:
            True if rolled back successfully

        Raises:
            ValueError: If cannot rollback requested number of versions

        Example:
            >>> await manager.upgrade("reflection", "1.1.0")
            >>> await manager.rollback("reflection")
            True
            >>> manager._versions["reflection"]
            SkillVersion(major=1, minor=0, patch=0)
        """
        # Find previous version from events
        skill_events = [
            e for e in self._events if e.skill_name == skill_name and e.event_type == "upgrade"
        ]

        if len(skill_events) < event_count:
            raise ValueError(
                f"Cannot rollback {event_count} versions. "
                f"Only {len(skill_events)} upgrades recorded."
            )

        target_event = skill_events[-(event_count)]
        target_version = target_event.metadata.get("from_version")

        if target_version:
            await self.upgrade(skill_name, target_version)
            logger.info(
                "skill_rolled_back",
                skill_name=skill_name,
                to_version=target_version,
            )

        return True

    def get_state(self, skill_name: str) -> SkillState:
        """Get current state of skill.

        Args:
            skill_name: Name of skill

        Returns:
            Current skill state

        Example:
            >>> state = manager.get_state("reflection")
            >>> state
            <SkillState.ACTIVE: 'active'>
        """
        return self._states.get(skill_name, SkillState.DISCOVERED)

    def get_context_usage(self) -> dict[str, int]:
        """Get current context usage by active skills.

        Returns:
            Dict mapping skill name to token allocation

        Example:
            >>> usage = manager.get_context_usage()
            >>> usage
            {'reflection': 2000, 'synthesis': 1500}
        """
        return dict(self._active_context_usage)

    def get_available_budget(self) -> int:
        """Get available context budget.

        Returns:
            Available tokens

        Example:
            >>> available = manager.get_available_budget()
            >>> available
            6500
        """
        return self.context_budget - sum(self._active_context_usage.values())

    def get_events(self, skill_name: Optional[str] = None) -> list[SkillLifecycleEvent]:
        """Get lifecycle events, optionally filtered by skill.

        Args:
            skill_name: Optional skill name to filter by

        Returns:
            List of lifecycle events

        Example:
            >>> events = manager.get_events("reflection")
            >>> len(events)
            5
        """
        if skill_name:
            return [e for e in self._events if e.skill_name == skill_name]
        return list(self._events)

    # Private methods

    def _resolve_skill_path(
        self,
        skill_name: str,
        version: Optional[str] = None,
    ) -> Optional[Path]:
        """Resolve skill directory path.

        Args:
            skill_name: Name of skill
            version: Optional version string

        Returns:
            Path to skill directory or None if not found
        """
        skill_dir = self.skills_dir / skill_name
        if version:
            skill_dir = skill_dir / f"v{version}"

        if skill_dir.exists():
            return skill_dir

        # Try without version subdirectory
        skill_dir = self.skills_dir / skill_name
        return skill_dir if skill_dir.exists() else None

    async def _load_skill_content(self, skill_path: Path) -> str:
        """Load SKILL.md and combine with resources.

        Args:
            skill_path: Path to skill directory

        Returns:
            Combined skill content

        Raises:
            FileNotFoundError: If SKILL.md not found
        """
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        content = skill_md.read_text()

        # Load additional prompts
        prompts_dir = skill_path / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.md"):
                prompt_content = prompt_file.read_text()
                content += f"\n\n## Prompt: {prompt_file.stem}\n{prompt_content}"

        return content

    def _extract_version(self, content: str) -> SkillVersion:
        """Extract version from SKILL.md frontmatter.

        Args:
            content: SKILL.md content

        Returns:
            SkillVersion object (default: 1.0.0)
        """
        import re

        match = re.search(r'version:\s*["\']?(\d+\.\d+\.\d+)["\']?', content)
        if match:
            return SkillVersion.parse(match.group(1))
        return SkillVersion(1, 0, 0)

    def _record_event(
        self,
        skill_name: str,
        event_type: str,
        old_state: SkillState,
        new_state: SkillState,
        version: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Record lifecycle event.

        Args:
            skill_name: Name of skill
            event_type: Type of event
            old_state: State before transition
            new_state: State after transition
            version: Optional version string
            metadata: Optional additional data
        """
        self._events.append(
            SkillLifecycleEvent(
                skill_name=skill_name,
                event_type=event_type,
                timestamp=datetime.now(),
                old_state=old_state,
                new_state=new_state,
                version=version,
                metadata=metadata or {},
            )
        )

    async def _evict_lru(self):
        """Evict least recently used loaded skill."""
        # Find loaded but not active skills
        candidates = [name for name, state in self._states.items() if state == SkillState.LOADED]

        if candidates:
            # Evict first candidate (could use access time for true LRU)
            await self.unload(candidates[0])
            logger.info("evicted_lru_skill", skill_name=candidates[0])

    async def _deactivate_oldest(self):
        """Deactivate oldest active skill."""
        # Find oldest activation event
        active_events = [
            e
            for e in self._events
            if e.event_type == "activate" and self._states.get(e.skill_name) == SkillState.ACTIVE
        ]

        if active_events:
            oldest = active_events[0].skill_name
            await self.deactivate(oldest)
            logger.info("deactivated_oldest_skill", skill_name=oldest)

    async def _free_context(self, needed: int):
        """Free context budget by deactivating skills.

        Args:
            needed: Amount of context budget needed
        """
        while self.get_available_budget() < needed:
            await self._deactivate_oldest()
            logger.debug(
                "freed_context",
                available=self.get_available_budget(),
                needed=needed,
            )
