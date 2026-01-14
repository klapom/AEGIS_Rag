"""Skill Registry for Anthropic Agent Skills.

Sprint Context:
    - Sprint 90 (2026-01-14): Feature 90.1 - Skill Registry Implementation (10 SP)

Implements a local, configurable Skill Registry following the Anthropic Agent Skills standard.

Skills are modular capability containers that package:
- Instructions (from SKILL.md)
- Configuration (config.yaml)
- Prompts (prompts/*.txt)
- Scripts (scripts/*.py)

Architecture:
    skills/
    ├── retrieval/
    │   ├── SKILL.md          # Skill metadata & instructions
    │   ├── config.yaml       # Skill configuration
    │   ├── prompts/          # Specialized prompts
    │   └── scripts/          # Utility scripts
    ├── reasoning/
    │   ├── SKILL.md
    │   ├── reflection.py     # Reflection implementation
    │   └── prompts/
    └── synthesis/
        ├── SKILL.md
        └── templates/

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Example:
    >>> from src.agents.skills import get_skill_registry
    >>> registry = get_skill_registry()
    >>>
    >>> # Discover available skills
    >>> registry.discover()
    >>> registry.list_available()
    ['retrieval', 'reflection', 'synthesis']
    >>>
    >>> # Load and activate a skill
    >>> registry.activate("reflection")
    >>> instructions = registry.get_active_instructions()
    >>>
    >>> # Intent-based matching (embedding similarity)
    >>> matches = registry.match_intent("I need to verify this answer")
    >>> # Returns: ['reflection'] (high similarity to "validate", "verify" triggers)

Notes:
    - Skills loaded only when needed (token efficiency)
    - Embedding-based intent matching uses BGE-M3
    - Skills can be activated/deactivated dynamically
    - Global registry singleton for efficiency

See Also:
    - docs/sprints/SPRINT_90_PLAN.md: Implementation details
    - src/agents/skills/reflection.py: Example skill implementation
"""

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import structlog
import yaml

from src.components.shared.embedding_factory import get_embedding_service

logger = structlog.get_logger(__name__)


@dataclass
class SkillMetadata:
    """Metadata from SKILL.md frontmatter.

    Attributes:
        name: Skill name (unique identifier)
        version: Semantic version (e.g., "1.0.0")
        description: Brief description of skill purpose
        author: Author name or organization
        triggers: Intent patterns that activate this skill (for embedding matching)
        dependencies: Other skills or services required
        permissions: Permissions required (e.g., "read_documents", "invoke_llm")
        resources: Resource directories (e.g., {"prompts": "prompts/"})

    Example:
        >>> metadata = SkillMetadata(
        ...     name="reflection",
        ...     version="1.0.0",
        ...     description="Self-critique and validation loop",
        ...     author="AegisRAG Team",
        ...     triggers=["validate", "check", "verify"],
        ...     dependencies=[],
        ...     permissions=["read_contexts", "invoke_llm"]
        ... )
    """

    name: str
    version: str
    description: str
    author: str
    triggers: List[str]  # Intent patterns that activate this skill
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    resources: Dict[str, str] = field(default_factory=dict)


@dataclass
class LoadedSkill:
    """A skill loaded into memory.

    Attributes:
        metadata: Parsed SKILL.md frontmatter
        path: Filesystem path to skill directory
        instructions: Main instructions (parsed from SKILL.md body)
        config: Configuration from config.yaml
        prompts: Prompt templates from prompts/*.txt
        scripts: Loaded Python scripts from scripts/*.py
        is_active: Whether skill is currently active (in context)

    Example:
        >>> skill = LoadedSkill(
        ...     metadata=metadata,
        ...     path=Path("skills/reflection"),
        ...     instructions="# Reflection Skill\\n\\n...",
        ...     config={"max_iterations": 3},
        ...     prompts={"critique": "..."},
        ...     scripts={},
        ...     is_active=True
        ... )
    """

    metadata: SkillMetadata
    path: Path
    instructions: str  # Parsed from SKILL.md
    config: Dict[str, Any]
    prompts: Dict[str, str]
    scripts: Dict[str, Callable]
    is_active: bool = False


class SkillRegistry:
    """Registry for Anthropic Agent Skills.

    Skills are modular capability containers that can be:
    - Discovered from filesystem
    - Loaded on-demand based on intent
    - Unloaded to save context tokens
    - Versioned and updated independently

    Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

    Attributes:
        skills_dir: Directory containing skill packages
        _available: Available skills (discovered)
        _loaded: Loaded skills (in memory)
        _active: Active skill names (in context)
        _embedding_service: BGE-M3 embedding service for intent matching
        _trigger_embeddings: Pre-computed trigger embeddings for fast lookup

    Example:
        >>> registry = SkillRegistry(skills_dir=Path("skills"))
        >>> registry.discover()
        >>> registry.activate("reflection")
        >>> instructions = registry.get_active_instructions()
    """

    def __init__(self, skills_dir: Path = Path("skills"), auto_discover: bool = True):
        """Initialize skill registry.

        Args:
            skills_dir: Directory containing skill packages (default: "skills")
            auto_discover: Automatically discover skills on initialization
        """
        self.skills_dir = skills_dir
        self._available: Dict[str, SkillMetadata] = {}
        self._loaded: Dict[str, LoadedSkill] = {}
        self._active: List[str] = []
        # Sprint 90: Embedding-based intent matching
        self._embedding_service = None
        self._trigger_embeddings: Dict[str, list] = {}

        if auto_discover:
            self.discover()

    def discover(self) -> Dict[str, SkillMetadata]:
        """Discover all available skills in skills directory.

        Scans for SKILL.md files and parses metadata from frontmatter.

        Returns:
            Dict mapping skill names to metadata

        Example:
            >>> registry = SkillRegistry()
            >>> available = registry.discover()
            >>> available.keys()
            dict_keys(['retrieval', 'reflection', 'synthesis'])
        """
        self._available.clear()

        if not self.skills_dir.exists():
            logger.warning(
                "skills_directory_not_found",
                path=str(self.skills_dir),
                message="Creating skills directory",
            )
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return {}

        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                skill_md = skill_path / "SKILL.md"
                if skill_md.exists():
                    metadata = self._parse_skill_md(skill_md)
                    if metadata:
                        self._available[metadata.name] = metadata
                        logger.info(
                            "skill_discovered",
                            name=metadata.name,
                            version=metadata.version,
                            triggers=metadata.triggers,
                        )

        logger.info("skills_discovery_complete", count=len(self._available))
        return self._available

    def _parse_skill_md(self, path: Path) -> Optional[SkillMetadata]:
        """Parse SKILL.md file for metadata.

        Expected format:
        ---
        name: retrieval
        version: 1.0.0
        description: Vector and graph retrieval skill
        author: AegisRAG Team
        triggers:
          - search
          - find
          - lookup
        dependencies:
          - qdrant
          - neo4j
        permissions:
          - read_documents
        ---

        # Retrieval Skill

        Instructions for the agent...

        Args:
            path: Path to SKILL.md file

        Returns:
            Parsed SkillMetadata or None if parsing fails
        """
        try:
            content = path.read_text()

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        return SkillMetadata(
                            name=frontmatter.get("name", path.parent.name),
                            version=frontmatter.get("version", "0.1.0"),
                            description=frontmatter.get("description", ""),
                            author=frontmatter.get("author", "Unknown"),
                            triggers=frontmatter.get("triggers", []),
                            dependencies=frontmatter.get("dependencies", []),
                            permissions=frontmatter.get("permissions", []),
                            resources=frontmatter.get("resources", {}),
                        )
                    except yaml.YAMLError as e:
                        logger.error(
                            "skill_md_parse_error",
                            path=str(path),
                            error=str(e),
                        )
        except Exception as e:
            logger.error("skill_md_read_error", path=str(path), error=str(e))

        return None

    def load(self, name: str) -> LoadedSkill:
        """Load a skill into memory.

        Reads:
        - SKILL.md (instructions)
        - config.yaml (configuration)
        - prompts/*.txt (prompt templates)
        - scripts/*.py (utility functions)

        Args:
            name: Skill name to load

        Returns:
            Loaded skill instance

        Raises:
            ValueError: If skill not found in available skills

        Example:
            >>> registry = SkillRegistry()
            >>> skill = registry.load("reflection")
            >>> skill.metadata.name
            'reflection'
            >>> skill.config
            {'max_iterations': 3, 'confidence_threshold': 0.85}
        """
        if name in self._loaded:
            logger.debug("skill_already_loaded", name=name)
            return self._loaded[name]

        if name not in self._available:
            raise ValueError(f"Skill not found: {name}")

        skill_path = self.skills_dir / name
        metadata = self._available[name]

        # Read instructions from SKILL.md
        skill_md = skill_path / "SKILL.md"
        content = skill_md.read_text()
        instructions = self._extract_instructions(content)

        # Load config
        config = {}
        config_path = skill_path / "config.yaml"
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text())
            logger.debug("skill_config_loaded", name=name, config=config)

        # Load prompts
        prompts = {}
        prompts_dir = skill_path / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.txt"):
                prompts[prompt_file.stem] = prompt_file.read_text()
            logger.debug("skill_prompts_loaded", name=name, count=len(prompts))

        # Load scripts
        scripts = {}
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.py"):
                script_func = self._load_script(script_file)
                if script_func:
                    scripts[script_file.stem] = script_func
            logger.debug("skill_scripts_loaded", name=name, count=len(scripts))

        skill = LoadedSkill(
            metadata=metadata,
            path=skill_path,
            instructions=instructions,
            config=config,
            prompts=prompts,
            scripts=scripts,
            is_active=False,
        )

        self._loaded[name] = skill
        logger.info("skill_loaded", name=name, path=str(skill_path))
        return skill

    def _extract_instructions(self, content: str) -> str:
        """Extract instructions from SKILL.md (after frontmatter).

        Args:
            content: Full SKILL.md content

        Returns:
            Instructions text (after frontmatter)
        """
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content

    def _load_script(self, path: Path) -> Optional[Callable]:
        """Dynamically load a Python script.

        Looks for 'main' or 'run' function in the script.

        Args:
            path: Path to Python script

        Returns:
            Callable function or None if loading fails
        """
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Return main function if exists
                return getattr(module, "main", None) or getattr(module, "run", None)
        except Exception as e:
            logger.error("script_load_error", path=str(path), error=str(e))
        return None

    def activate(self, name: str) -> str:
        """Activate a skill and return its instructions for the context.

        This is the key operation that adds skill knowledge to the agent.

        Args:
            name: Skill name to activate

        Returns:
            Skill instructions to add to agent context

        Example:
            >>> registry = SkillRegistry()
            >>> instructions = registry.activate("reflection")
            >>> print(instructions)
            # Reflection Skill
            ...
        """
        if name not in self._loaded:
            self.load(name)

        skill = self._loaded[name]
        skill.is_active = True

        if name not in self._active:
            self._active.append(name)

        logger.info("skill_activated", name=name)
        return skill.instructions

    def deactivate(self, name: str):
        """Deactivate a skill to save context tokens.

        Args:
            name: Skill name to deactivate

        Example:
            >>> registry = SkillRegistry()
            >>> registry.activate("reflection")
            >>> registry.deactivate("reflection")
        """
        if name in self._loaded:
            self._loaded[name].is_active = False
        if name in self._active:
            self._active.remove(name)

        logger.info("skill_deactivated", name=name)

    def get_active_instructions(self) -> str:
        """Get combined instructions from all active skills.

        Returns:
            Combined instructions from all active skills

        Example:
            >>> registry = SkillRegistry()
            >>> registry.activate("reflection")
            >>> registry.activate("retrieval")
            >>> instructions = registry.get_active_instructions()
        """
        instructions = []
        for name in self._active:
            if name in self._loaded:
                skill = self._loaded[name]
                instructions.append(
                    f"## Skill: {skill.metadata.name}\n\n{skill.instructions}"
                )
        return "\n\n---\n\n".join(instructions)

    def list_available(self) -> List[str]:
        """List all available skills.

        Returns:
            List of available skill names

        Example:
            >>> registry = SkillRegistry()
            >>> registry.list_available()
            ['retrieval', 'reflection', 'synthesis']
        """
        return list(self._available.keys())

    def list_active(self) -> List[str]:
        """List currently active skills.

        Returns:
            List of active skill names

        Example:
            >>> registry = SkillRegistry()
            >>> registry.activate("reflection")
            >>> registry.list_active()
            ['reflection']
        """
        return list(self._active)

    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a skill.

        Args:
            name: Skill name

        Returns:
            SkillMetadata or None if not found

        Example:
            >>> registry = SkillRegistry()
            >>> metadata = registry.get_metadata("reflection")
            >>> metadata.version
            '1.0.0'
        """
        return self._available.get(name)

    def match_intent(
        self, intent: str, similarity_threshold: float = 0.75
    ) -> List[str]:
        """Find skills that match an intent using embedding-based semantic matching.

        Uses BGE-M3 embeddings for semantic similarity instead of string matching.
        This allows matching "find documents" to skill trigger "search" even without
        exact keyword overlap.

        Args:
            intent: User intent to match
            similarity_threshold: Minimum cosine similarity (0.0-1.0) for match

        Returns:
            List of matching skill names, sorted by similarity (highest first)

        Example:
            >>> registry = SkillRegistry()
            >>> matches = registry.match_intent("I need to verify this answer")
            >>> # Returns: ['reflection'] (high similarity to "validate", "verify")
            >>>
            >>> matches = registry.match_intent("search for documents")
            >>> # Returns: ['retrieval'] (high similarity to "search", "find")

        Notes:
            - Uses pre-computed trigger embeddings for fast lookup
            - Embedding service initialized on first call (lazy loading)
            - Cosine similarity threshold default: 0.75 (high similarity)
        """
        # Sprint 90: Embedding-based matching (not string matching)
        # Uses pre-computed trigger embeddings for fast lookup
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
            self._precompute_trigger_embeddings()

        # Get dense embedding for intent
        intent_result = self._embedding_service.embed_single(intent)

        # Handle multi-vector backend (flag-embedding)
        if isinstance(intent_result, dict):
            intent_embedding = intent_result["dense"]
        else:
            intent_embedding = intent_result

        matches = []
        for name, metadata in self._available.items():
            # Get max similarity across all triggers for this skill
            max_similarity = 0.0
            for trigger in metadata.triggers:
                trigger_key = f"{name}:{trigger}"
                if trigger_key in self._trigger_embeddings:
                    similarity = self._cosine_similarity(
                        intent_embedding, self._trigger_embeddings[trigger_key]
                    )
                    max_similarity = max(max_similarity, similarity)

            if max_similarity >= similarity_threshold:
                matches.append((name, max_similarity))

        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        logger.debug(
            "intent_matching_complete",
            intent=intent,
            matches=[m[0] for m in matches],
            scores=[m[1] for m in matches],
        )

        return [name for name, _ in matches]

    def _precompute_trigger_embeddings(self):
        """Pre-compute embeddings for all skill triggers.

        Embedding results cached for fast intent matching.
        """
        self._trigger_embeddings = {}
        for name, metadata in self._available.items():
            for trigger in metadata.triggers:
                trigger_result = self._embedding_service.embed_single(trigger)

                # Handle multi-vector backend
                if isinstance(trigger_result, dict):
                    trigger_embedding = trigger_result["dense"]
                else:
                    trigger_embedding = trigger_result

                trigger_key = f"{name}:{trigger}"
                self._trigger_embeddings[trigger_key] = trigger_embedding

        logger.info(
            "trigger_embeddings_precomputed", count=len(self._trigger_embeddings)
        )

    def _cosine_similarity(self, a: list, b: list) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0.0-1.0)
        """
        a_arr, b_arr = np.array(a), np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


# Global registry instance
_registry: Optional[SkillRegistry] = None


def get_skill_registry(skills_dir: Optional[Path] = None) -> SkillRegistry:
    """Get or create the global skill registry.

    Returns singleton instance for efficiency (shared cache, embeddings).

    Args:
        skills_dir: Custom skills directory (default: "skills")

    Returns:
        Global SkillRegistry instance

    Example:
        >>> from src.agents.skills import get_skill_registry
        >>> registry = get_skill_registry()
        >>> registry.discover()
    """
    global _registry
    if _registry is None:
        _registry = SkillRegistry(skills_dir or Path("skills"))
        logger.info("skill_registry_initialized", path=str(_registry.skills_dir))
    return _registry
