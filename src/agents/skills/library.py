"""Skill Libraries & Bundles - Reusable Skill Packages.

Sprint 95 Feature 95.2: Skill Libraries & Bundles (8 SP)

This module provides a comprehensive library system for managing reusable skill packages:
- SkillLibrary: Registry for collections of related skills
- SkillBundle: Pre-configured bundles for common workflows
- SkillMetadata: Versioned metadata with dependencies and capabilities
- SkillManifest: YAML/JSON definitions for declarative skill configuration

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │              Skill Libraries & Bundles                  │
    ├─────────────────────────────────────────────────────────┤
    │                                                         │
    │  skill_libraries/                                       │
    │  ├── core/                 # Core library               │
    │  │   ├── retrieval/        # Vector/Graph skills        │
    │  │   ├── synthesis/        # Summarization              │
    │  │   └── reflection/       # Self-critique              │
    │  │                                                       │
    │  ├── research/             # Research library           │
    │  │   ├── web_search/       # Web search skill           │
    │  │   ├── academic/         # Academic search            │
    │  │   └── fact_check/       # Fact verification          │
    │  │                                                       │
    │  └── bundles/              # Pre-configured bundles     │
    │      ├── research_assistant/BUNDLE.yaml                 │
    │      ├── data_analyst/BUNDLE.yaml                       │
    │      └── code_reviewer/BUNDLE.yaml                      │
    └─────────────────────────────────────────────────────────┘

Example:
    >>> from pathlib import Path
    >>> from src.agents.skills.library import SkillLibraryManager
    >>> from src.agents.skills.lifecycle import SkillLifecycleManager
    >>>
    >>> # Initialize managers
    >>> lifecycle = SkillLifecycleManager(skills_dir=Path("skills"))
    >>> library = SkillLibraryManager(
    ...     libraries_dir=Path("skill_libraries"),
    ...     skill_manager=lifecycle
    ... )
    >>>
    >>> # Discover libraries and bundles
    >>> library.discover_libraries()
    >>>
    >>> # Load a bundle
    >>> loaded = await library.load_bundle("research_assistant")
    >>> loaded
    ['retrieval', 'synthesis', 'web_search', 'fact_check']
    >>>
    >>> # Search for skills by capability
    >>> skills = library.search_skills(query="web", capabilities=["search"])
    >>> [s.name for s in skills]
    ['web_search', 'academic_search']

Bundle Definition (BUNDLE.yaml):
    name: research_assistant
    version: "1.0.0"
    description: Complete research workflow bundle
    skills:
      - core/retrieval
      - core/synthesis
      - research/web_search
      - research/fact_check
    context_budget: 8000
    auto_activate:
      - retrieval
      - synthesis
    dependencies:
      - playwright: "^1.40.0"

See Also:
    - src/agents/skills/lifecycle.py: Skill lifecycle management
    - src/agents/tools/mapping.py: Tool capability discovery patterns
    - docs/sprints/SPRINT_95_PLAN.md: Feature specification
    - Anthropic Skills Repository: https://github.com/anthropics/skills
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
class SkillMetadata:
    """Metadata for a skill definition.

    Attributes:
        name: Unique skill identifier
        version: Semantic version (e.g., "1.0.0")
        description: Human-readable description
        capabilities: List of capabilities this skill provides
        dependencies: External package dependencies with version constraints
        tools: List of tools this skill can use
        tags: Categorical tags for discovery
        metadata: Additional custom metadata

    Example:
        >>> metadata = SkillMetadata(
        ...     name="web_search",
        ...     version="1.0.0",
        ...     description="Search the web using multiple search engines",
        ...     capabilities=["search", "web_access"],
        ...     dependencies=["requests>=2.28.0", "beautifulsoup4>=4.11.0"],
        ...     tools=["google_search", "bing_search"],
        ...     tags=["research", "web"],
        ... )
    """

    name: str
    version: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches_query(self, query: str) -> bool:
        """Check if metadata matches search query.

        Args:
            query: Search string

        Returns:
            True if query matches name, description, or tags

        Example:
            >>> metadata = SkillMetadata(name="web_search", description="Search the web", tags=["research"])
            >>> metadata.matches_query("web")
            True
            >>> metadata.matches_query("database")
            False
        """
        query_lower = query.lower()
        return (
            query_lower in self.name.lower()
            or query_lower in self.description.lower()
            or any(query_lower in tag.lower() for tag in self.tags)
        )

    def has_capability(self, capability: str) -> bool:
        """Check if skill has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            True if skill has capability

        Example:
            >>> metadata = SkillMetadata(name="web_search", capabilities=["search", "web_access"])
            >>> metadata.has_capability("search")
            True
        """
        return capability.lower() in [c.lower() for c in self.capabilities]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "tools": self.tools,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillMetadata:
        """Create from dictionary.

        Args:
            data: Dictionary with metadata fields

        Returns:
            SkillMetadata instance
        """
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            dependencies=data.get("dependencies", []),
            tools=data.get("tools", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SkillManifest:
    """YAML/JSON manifest definition for a skill.

    Attributes:
        name: Skill name
        version: Version string
        description: Description
        skill_path: Path to SKILL.md file
        capabilities: List of capabilities
        dependencies: Package dependencies
        tools: Required tools
        config: Configuration parameters

    Example:
        >>> manifest = SkillManifest(
        ...     name="web_search",
        ...     version="1.0.0",
        ...     description="Web search skill",
        ...     skill_path=Path("skills/web_search/SKILL.md"),
        ...     capabilities=["search"],
        ...     dependencies=["requests>=2.28.0"],
        ... )
    """

    name: str
    version: str
    description: str
    skill_path: Path
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> SkillManifest:
        """Load manifest from YAML file.

        Args:
            yaml_path: Path to MANIFEST.yaml

        Returns:
            SkillManifest instance

        Example:
            >>> manifest = SkillManifest.from_yaml(Path("skills/web_search/MANIFEST.yaml"))
        """
        with yaml_path.open() as f:
            data = yaml.safe_load(f)

        skill_dir = yaml_path.parent
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            skill_path=skill_dir / "SKILL.md",
            capabilities=data.get("capabilities", []),
            dependencies=data.get("dependencies", []),
            tools=data.get("tools", []),
            config=data.get("config", {}),
        )

    def to_metadata(self) -> SkillMetadata:
        """Convert to SkillMetadata.

        Returns:
            SkillMetadata instance
        """
        return SkillMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            capabilities=self.capabilities,
            dependencies=self.dependencies,
            tools=self.tools,
        )


@dataclass
class SkillBundle:
    """Pre-configured bundle of skills for common workflows.

    Attributes:
        name: Bundle identifier
        version: Bundle version
        description: Bundle description
        skills: List of skill paths (library/skill format)
        context_budget: Total context budget for bundle
        auto_activate: Skills to automatically activate
        dependencies: External dependencies
        metadata: Additional bundle metadata

    Example:
        >>> bundle = SkillBundle(
        ...     name="research_assistant",
        ...     version="1.0.0",
        ...     description="Complete research workflow",
        ...     skills=["core/retrieval", "core/synthesis", "research/web_search"],
        ...     context_budget=8000,
        ...     auto_activate=["retrieval", "synthesis"],
        ... )
    """

    name: str
    version: str
    description: str
    skills: list[str]
    context_budget: int = 5000
    auto_activate: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_skill_names(self) -> list[str]:
        """Extract skill names from skill paths.

        Returns:
            List of skill names (without library prefix)

        Example:
            >>> bundle = SkillBundle(name="test", version="1.0.0", description="", skills=["core/retrieval", "research/web_search"])
            >>> bundle.get_skill_names()
            ['retrieval', 'web_search']
        """
        return [self._extract_skill_name(path) for path in self.skills]

    def _extract_skill_name(self, skill_path: str) -> str:
        """Extract skill name from library/skill path.

        Args:
            skill_path: Path like "core/retrieval"

        Returns:
            Skill name like "retrieval"
        """
        return skill_path.split("/")[-1] if "/" in skill_path else skill_path

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "skills": self.skills,
            "context_budget": self.context_budget,
            "auto_activate": self.auto_activate,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillBundle:
        """Create from dictionary.

        Args:
            data: Dictionary with bundle fields

        Returns:
            SkillBundle instance
        """
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            skills=data.get("skills", []),
            context_budget=data.get("context_budget", 5000),
            auto_activate=data.get("auto_activate", []),
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SkillLibrary:
    """Collection of related skills.

    Attributes:
        name: Library identifier (e.g., "core", "research")
        version: Library version
        description: Library description
        skills: List of skill names in this library
        dependencies: External dependencies
        path: Path to library directory
        metadata: Additional library metadata

    Example:
        >>> library = SkillLibrary(
        ...     name="research",
        ...     version="1.0.0",
        ...     description="Research-related skills",
        ...     skills=["web_search", "academic", "fact_check"],
        ...     path=Path("skill_libraries/research"),
        ... )
    """

    name: str
    version: str
    description: str
    skills: list[str]
    dependencies: list[str] = field(default_factory=list)
    path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_skill_path(self, skill_name: str) -> Path | None:
        """Get path to skill directory.

        Args:
            skill_name: Name of skill in this library

        Returns:
            Path to skill directory or None if not found

        Example:
            >>> library = SkillLibrary(name="research", version="1.0.0", description="", skills=["web_search"], path=Path("skill_libraries/research"))
            >>> library.get_skill_path("web_search")
            PosixPath('skill_libraries/research/web_search')
        """
        if not self.path:
            return None

        skill_dir = self.path / skill_name
        return skill_dir if skill_dir.exists() else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "skills": self.skills,
            "dependencies": self.dependencies,
            "path": str(self.path) if self.path else None,
            "metadata": self.metadata,
        }


# =============================================================================
# Skill Library Manager
# =============================================================================


class SkillLibraryManager:
    """Manage skill libraries and bundles.

    Provides:
    - Discover and load skill libraries
    - Create and manage bundles
    - Resolve dependencies
    - Version compatibility checking
    - Skill search by capabilities

    Attributes:
        libraries_dir: Root directory for skill libraries
        skill_manager: SkillLifecycleManager for loading skills

    Example:
        >>> from pathlib import Path
        >>> from src.agents.skills.lifecycle import SkillLifecycleManager
        >>>
        >>> lifecycle = SkillLifecycleManager(skills_dir=Path("skills"))
        >>> manager = SkillLibraryManager(
        ...     libraries_dir=Path("skill_libraries"),
        ...     skill_manager=lifecycle
        ... )
        >>>
        >>> # Discover libraries
        >>> manager.discover_libraries()
        >>>
        >>> # Load bundle
        >>> skills = await manager.load_bundle("research_assistant")
        >>> skills
        ['retrieval', 'synthesis', 'web_search']
    """

    def __init__(
        self,
        libraries_dir: Path,
        skill_manager: Any,
    ):
        """Initialize skill library manager.

        Args:
            libraries_dir: Root directory for skill libraries
            skill_manager: SkillLifecycleManager instance
        """
        self.libraries_dir = libraries_dir
        self.skills = skill_manager

        # Storage
        self._libraries: dict[str, SkillLibrary] = {}
        self._bundles: dict[str, SkillBundle] = {}
        self._loaded_bundles: set[str] = set()
        self._skill_metadata: dict[str, SkillMetadata] = {}

        logger.info(
            "skill_library_manager_initialized",
            libraries_dir=str(libraries_dir),
        )

    def discover_libraries(self) -> dict[str, SkillLibrary]:
        """Discover all skill libraries in libraries_dir.

        Returns:
            Dictionary mapping library name to SkillLibrary

        Example:
            >>> libraries = manager.discover_libraries()
            >>> list(libraries.keys())
            ['core', 'research', 'analysis']
        """
        self._libraries.clear()

        if not self.libraries_dir.exists():
            logger.warning(
                "libraries_dir_not_found",
                path=str(self.libraries_dir),
            )
            return self._libraries

        for lib_dir in self.libraries_dir.iterdir():
            if lib_dir.is_dir() and lib_dir.name != "bundles":
                library = self._parse_library(lib_dir)
                if library:
                    self._libraries[library.name] = library
                    logger.info("library_discovered", name=library.name, skills=len(library.skills))

        # Discover bundles
        bundles_dir = self.libraries_dir / "bundles"
        if bundles_dir.exists():
            for bundle_dir in bundles_dir.iterdir():
                if bundle_dir.is_dir():
                    bundle = self._parse_bundle(bundle_dir)
                    if bundle:
                        self._bundles[bundle.name] = bundle
                        logger.info("bundle_discovered", name=bundle.name, skills=len(bundle.skills))

        logger.info(
            "discovery_complete",
            libraries=len(self._libraries),
            bundles=len(self._bundles),
        )

        return self._libraries

    def register_skill(
        self,
        skill_name: str,
        metadata: SkillMetadata,
    ) -> None:
        """Register a skill with metadata.

        Args:
            skill_name: Unique skill identifier
            metadata: Skill metadata

        Example:
            >>> metadata = SkillMetadata(
            ...     name="web_search",
            ...     version="1.0.0",
            ...     description="Web search skill",
            ...     capabilities=["search"],
            ... )
            >>> manager.register_skill("web_search", metadata)
        """
        self._skill_metadata[skill_name] = metadata
        logger.info(
            "skill_registered",
            skill_name=skill_name,
            version=metadata.version,
            capabilities=metadata.capabilities,
        )

    def get_skill(
        self,
        name: str,
        version: str | None = None,
    ) -> SkillMetadata | None:
        """Retrieve skill by name and optional version.

        Args:
            name: Skill name
            version: Optional version constraint (default: latest)

        Returns:
            SkillMetadata or None if not found

        Example:
            >>> skill = manager.get_skill("web_search")
            >>> skill.name
            'web_search'
            >>> skill = manager.get_skill("web_search", "1.0.0")
        """
        metadata = self._skill_metadata.get(name)

        # Check version match if both metadata and version are provided
        if metadata and version and metadata.version != version:
            logger.debug(
                "skill_version_mismatch",
                name=name,
                requested=version,
                available=metadata.version,
            )
            return None

        return metadata

    def search_skills(
        self,
        query: str | None = None,
        capabilities: list[str] | None = None,
    ) -> list[SkillMetadata]:
        """Discover skills by query and/or capabilities.

        Args:
            query: Optional search query string
            capabilities: Optional list of required capabilities

        Returns:
            List of matching SkillMetadata objects

        Example:
            >>> # Search by query
            >>> skills = manager.search_skills(query="web")
            >>> [s.name for s in skills]
            ['web_search', 'web_scrape']
            >>>
            >>> # Search by capability
            >>> skills = manager.search_skills(capabilities=["search"])
            >>> [s.name for s in skills]
            ['web_search', 'academic_search']
        """
        results = []

        for metadata in self._skill_metadata.values():
            # Filter by query
            if query and not metadata.matches_query(query):
                continue

            # Filter by capabilities
            if capabilities and not all(metadata.has_capability(cap) for cap in capabilities):
                continue

            results.append(metadata)

        logger.debug(
            "skills_searched",
            query=query,
            capabilities=capabilities,
            results=len(results),
        )

        return results

    async def install_bundle(self, bundle_name: str) -> list[str]:
        """Install skill bundle (alias for load_bundle).

        Args:
            bundle_name: Name of bundle to install

        Returns:
            List of installed skill names

        Example:
            >>> skills = await manager.install_bundle("research_assistant")
            >>> skills
            ['retrieval', 'synthesis', 'web_search']
        """
        return await self.load_bundle(bundle_name)

    async def load_bundle(
        self,
        bundle_name: str,
        context_budget: int | None = None,
    ) -> list[str]:
        """Load all skills in a bundle.

        Args:
            bundle_name: Name of bundle to load
            context_budget: Override bundle's default context budget

        Returns:
            List of loaded skill names

        Raises:
            ValueError: If bundle not found

        Example:
            >>> skills = await manager.load_bundle("research_assistant")
            >>> skills
            ['retrieval', 'synthesis', 'web_search', 'fact_check']
            >>>
            >>> # Override context budget
            >>> skills = await manager.load_bundle("research_assistant", context_budget=10000)
        """
        bundle = self._bundles.get(bundle_name)
        if not bundle:
            raise ValueError(f"Bundle not found: {bundle_name}")

        budget = context_budget or bundle.context_budget
        budget_per_skill = budget // max(1, len(bundle.skills))

        loaded = []
        for skill_path in bundle.skills:
            # Resolve skill path (library/skill format)
            skill_name = self._resolve_skill_path(skill_path)

            try:
                # Load skill via lifecycle manager
                await self.skills.load(skill_name)
                loaded.append(skill_name)
                logger.info("bundle_skill_loaded", bundle=bundle_name, skill=skill_name)
            except Exception as e:
                logger.error(
                    "bundle_skill_load_failed",
                    bundle=bundle_name,
                    skill=skill_name,
                    error=str(e),
                )

        # Auto-activate specified skills
        for skill_name in bundle.auto_activate:
            resolved = self._resolve_skill_path(skill_name)
            if resolved in loaded:
                try:
                    await self.skills.activate(resolved, budget_per_skill)
                    logger.info(
                        "bundle_skill_activated",
                        bundle=bundle_name,
                        skill=resolved,
                        budget=budget_per_skill,
                    )
                except Exception as e:
                    logger.error(
                        "bundle_skill_activation_failed",
                        bundle=bundle_name,
                        skill=resolved,
                        error=str(e),
                    )

        self._loaded_bundles.add(bundle_name)

        logger.info(
            "bundle_loaded",
            bundle=bundle_name,
            skills_loaded=len(loaded),
            skills_activated=len(bundle.auto_activate),
        )

        return loaded

    async def unload_bundle(self, bundle_name: str) -> bool:
        """Unload all skills in a bundle.

        Args:
            bundle_name: Name of bundle to unload

        Returns:
            True if unloaded successfully

        Example:
            >>> success = await manager.unload_bundle("research_assistant")
            >>> success
            True
        """
        bundle = self._bundles.get(bundle_name)
        if not bundle:
            logger.warning("bundle_not_found", bundle=bundle_name)
            return False

        for skill_path in bundle.skills:
            skill_name = self._resolve_skill_path(skill_path)
            try:
                await self.skills.unload(skill_name)
                logger.info("bundle_skill_unloaded", bundle=bundle_name, skill=skill_name)
            except Exception as e:
                logger.error(
                    "bundle_skill_unload_failed",
                    bundle=bundle_name,
                    skill=skill_name,
                    error=str(e),
                )

        self._loaded_bundles.discard(bundle_name)

        logger.info("bundle_unloaded", bundle=bundle_name)
        return True

    def list_skills(self) -> list[str]:
        """List all registered skills.

        Returns:
            List of skill names

        Example:
            >>> skills = manager.list_skills()
            >>> skills
            ['retrieval', 'synthesis', 'reflection', 'web_search', 'fact_check']
        """
        return list(self._skill_metadata.keys())

    def list_libraries(self) -> list[str]:
        """List all discovered libraries.

        Returns:
            List of library names

        Example:
            >>> libraries = manager.list_libraries()
            >>> libraries
            ['core', 'research', 'analysis']
        """
        return list(self._libraries.keys())

    def list_bundles(self) -> list[str]:
        """List all discovered bundles.

        Returns:
            List of bundle names

        Example:
            >>> bundles = manager.list_bundles()
            >>> bundles
            ['research_assistant', 'data_analyst', 'code_reviewer']
        """
        return list(self._bundles.keys())

    def get_library_skills(self, library_name: str) -> list[str]:
        """Get all skills in a library.

        Args:
            library_name: Name of library

        Returns:
            List of skill names in library

        Example:
            >>> skills = manager.get_library_skills("research")
            >>> skills
            ['web_search', 'academic', 'fact_check']
        """
        library = self._libraries.get(library_name)
        return library.skills if library else []

    def get_bundle_skills(self, bundle_name: str) -> list[str]:
        """Get all skills in a bundle.

        Args:
            bundle_name: Name of bundle

        Returns:
            List of skill paths in bundle

        Example:
            >>> skills = manager.get_bundle_skills("research_assistant")
            >>> skills
            ['core/retrieval', 'core/synthesis', 'research/web_search']
        """
        bundle = self._bundles.get(bundle_name)
        return bundle.skills if bundle else []

    def validate_dependencies(self, skill_name: str) -> tuple[bool, list[str]]:
        """Check if skill dependencies are satisfied.

        Args:
            skill_name: Name of skill to validate

        Returns:
            Tuple of (all_satisfied, missing_dependencies)

        Example:
            >>> satisfied, missing = manager.validate_dependencies("web_search")
            >>> satisfied
            False
            >>> missing
            ['playwright>=1.40.0']
        """
        metadata = self._skill_metadata.get(skill_name)
        if not metadata:
            return False, [f"Skill not found: {skill_name}"]

        missing = []
        for dep in metadata.dependencies:
            # Simple check - could be enhanced with pkg_resources
            package_name = dep.split(">=")[0].split("==")[0].strip()
            try:
                __import__(package_name)
            except ImportError:
                missing.append(dep)

        satisfied = len(missing) == 0

        logger.debug(
            "dependencies_validated",
            skill_name=skill_name,
            satisfied=satisfied,
            missing_count=len(missing),
        )

        return satisfied, missing

    def create_bundle(
        self,
        name: str,
        skills: list[str],
        context_budget: int = 5000,
        description: str = "",
        auto_activate: list[str] | None = None,
    ) -> SkillBundle:
        """Create a new bundle dynamically.

        Args:
            name: Bundle name
            skills: List of skill paths (library/skill format)
            context_budget: Total context budget
            description: Bundle description
            auto_activate: Skills to auto-activate

        Returns:
            Created SkillBundle

        Example:
            >>> bundle = manager.create_bundle(
            ...     name="custom_research",
            ...     skills=["core/retrieval", "research/web_search"],
            ...     context_budget=6000,
            ...     description="Custom research workflow",
            ...     auto_activate=["retrieval"],
            ... )
        """
        bundle = SkillBundle(
            name=name,
            version="1.0.0",
            description=description,
            skills=skills,
            context_budget=context_budget,
            auto_activate=auto_activate or [],
        )
        self._bundles[name] = bundle

        logger.info(
            "bundle_created",
            name=name,
            skills=len(skills),
            context_budget=context_budget,
        )

        return bundle

    def get_metrics(self) -> dict[str, Any]:
        """Get library manager metrics.

        Returns:
            Dictionary with counts and stats

        Example:
            >>> metrics = manager.get_metrics()
            >>> metrics
            {
                'libraries': 3,
                'bundles': 3,
                'registered_skills': 12,
                'loaded_bundles': 2,
                'skills_per_library': {'core': 3, 'research': 4, 'analysis': 5}
            }
        """
        return {
            "libraries": len(self._libraries),
            "bundles": len(self._bundles),
            "registered_skills": len(self._skill_metadata),
            "loaded_bundles": len(self._loaded_bundles),
            "skills_per_library": {
                name: len(lib.skills) for name, lib in self._libraries.items()
            },
        }

    # Private methods

    def _parse_library(self, lib_dir: Path) -> SkillLibrary | None:
        """Parse library from directory.

        Args:
            lib_dir: Path to library directory

        Returns:
            SkillLibrary or None if invalid
        """
        lib_yaml = lib_dir / "LIBRARY.yaml"

        if lib_yaml.exists():
            # Parse from YAML
            with lib_yaml.open() as f:
                config = yaml.safe_load(f)

            return SkillLibrary(
                name=config.get("name", lib_dir.name),
                version=config.get("version", "1.0.0"),
                description=config.get("description", ""),
                skills=config.get("skills", []),
                dependencies=config.get("dependencies", []),
                path=lib_dir,
                metadata=config.get("metadata", {}),
            )
        else:
            # Infer from directory structure
            skills = []
            for skill_dir in lib_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skills.append(skill_dir.name)

            if not skills:
                return None

            return SkillLibrary(
                name=lib_dir.name,
                version="1.0.0",
                description=f"Library: {lib_dir.name}",
                skills=skills,
                path=lib_dir,
            )

    def _parse_bundle(self, bundle_dir: Path) -> SkillBundle | None:
        """Parse bundle from directory.

        Args:
            bundle_dir: Path to bundle directory

        Returns:
            SkillBundle or None if invalid
        """
        bundle_yaml = bundle_dir / "BUNDLE.yaml"
        if not bundle_yaml.exists():
            # Try JSON
            bundle_json = bundle_dir / "BUNDLE.json"
            if not bundle_json.exists():
                return None

            with bundle_json.open() as f:
                config = json.load(f)
        else:
            with bundle_yaml.open() as f:
                config = yaml.safe_load(f)

        return SkillBundle(
            name=config.get("name", bundle_dir.name),
            version=config.get("version", "1.0.0"),
            description=config.get("description", ""),
            skills=config.get("skills", []),
            context_budget=config.get("context_budget", 5000),
            auto_activate=config.get("auto_activate", []),
            dependencies=config.get("dependencies", []),
            metadata=config.get("metadata", {}),
        )

    def _resolve_skill_path(self, skill_path: str) -> str:
        """Resolve library/skill path to skill name.

        Args:
            skill_path: Path like "core/retrieval" or "retrieval"

        Returns:
            Skill name like "retrieval"
        """
        if "/" in skill_path:
            parts = skill_path.split("/")
            return parts[-1]  # Return just skill name
        return skill_path
