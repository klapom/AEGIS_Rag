"""Skill Trigger Configuration System.

Sprint Context:
    - Sprint 91 (2026-01-14): Feature 91.2 - Skill Trigger Configuration (8 SP)

Flexible configuration system for skill activation triggers:
- Intent-based triggers (from C-LARA classification)
- Pattern-based triggers (regex matching)
- Keyword triggers (simple substring matching)
- Always-active skills (monitoring, logging, etc.)

Configuration loaded from YAML file with:
- Global defaults (context budget, max active skills)
- Intent mappings (required/optional skills per intent)
- Pattern triggers (regex patterns → skills)
- Keyword triggers (keywords → skills)

Architecture:
    Query → Pattern Match + Keyword Match → Trigger Matches → Skills

Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

Example:
    >>> loader = TriggerConfigLoader("config/skill_triggers.yaml")
    >>> matches = loader.get_triggered_skills(
    ...     "search for documents about authentication",
    ...     intent="VECTOR"
    ... )
    >>> # Returns: [
    >>> #   TriggerMatch(skill='retrieval', source='intent', priority='high', confidence=0.95),
    >>> #   TriggerMatch(skill='retrieval', source='pattern', priority='high', confidence=0.8),
    >>> # ]
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)


@dataclass
class TriggerMatch:
    """A matched trigger for skill activation.

    Represents a single match from pattern/keyword/intent matching.
    Multiple matches may exist for the same skill from different sources.

    Attributes:
        skill: Skill name to activate
        source: Match source ("intent", "pattern", "keyword", "always_active")
        priority: Match priority ("high", "medium", "low")
        confidence: Match confidence (0.0-1.0)

    Example:
        >>> match = TriggerMatch(
        ...     skill='retrieval',
        ...     source='pattern',
        ...     priority='high',
        ...     confidence=0.8
        ... )
    """

    skill: str
    source: str  # "intent", "pattern", "keyword", "always_active"
    priority: str  # "high", "medium", "low"
    confidence: float  # 0.0-1.0


class TriggerConfigLoader:
    """Load and apply skill trigger configuration.

    Loads configuration from YAML file and provides methods to:
    - Match patterns against query text
    - Match keywords in query
    - Get intent-based triggers
    - Combine and deduplicate matches

    Attributes:
        config: Loaded YAML configuration
        _compiled_patterns: Pre-compiled regex patterns for efficiency

    Example:
        >>> loader = TriggerConfigLoader()
        >>> matches = loader.get_triggered_skills("search for recent papers", intent="VECTOR")
        >>> [m.skill for m in matches]
        ['retrieval', 'web_search']
    """

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
    ):
        """Initialize trigger config loader.

        Args:
            config_path: Path to YAML config file (default: config/skill_triggers.yaml)
        """
        if config_path is None:
            config_path = Path("config/skill_triggers.yaml")
        elif isinstance(config_path, str):
            config_path = Path(config_path)

        self.config_path = config_path
        self.config = self._load_config()
        self._compiled_patterns = self._compile_patterns()

        logger.info(
            "trigger_config_loaded",
            config_path=str(self.config_path),
            pattern_triggers=len(self._compiled_patterns),
            keyword_triggers=len(self.config.get("keyword_triggers", {})),
            intent_triggers=len(self.config.get("intent_triggers", {})),
        )

    def _load_config(self) -> Dict:
        """Load configuration from YAML file.

        Returns:
            Parsed YAML configuration dict

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not self.config_path.exists():
            logger.warning(
                "config_file_not_found",
                path=str(self.config_path),
                using_defaults=True,
            )
            # Return minimal default configuration
            return {
                "defaults": {
                    "context_budget": 4000,
                    "max_active_skills": 5,
                    "always_active": [],
                },
                "intent_triggers": {},
                "pattern_triggers": [],
                "keyword_triggers": {},
            }

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
                logger.info(
                    "config_loaded_successfully",
                    path=str(self.config_path),
                )
                return config
        except yaml.YAMLError as e:
            logger.error(
                "config_parse_error",
                path=str(self.config_path),
                error=str(e),
            )
            raise

    def _compile_patterns(self) -> List[tuple]:
        """Pre-compile regex patterns for efficiency.

        Compiles all pattern triggers from config into regex objects.
        Invalid patterns are logged and skipped.

        Returns:
            List of (compiled_pattern, skills, priority) tuples
        """
        patterns = []
        for trigger in self.config.get("pattern_triggers", []):
            try:
                pattern_str = trigger.get("pattern", "")
                compiled = re.compile(pattern_str)
                skills = trigger.get("skills", [])
                priority = trigger.get("priority", "medium")

                patterns.append((compiled, skills, priority))

                logger.debug(
                    "pattern_compiled",
                    pattern=pattern_str,
                    skills=skills,
                    priority=priority,
                )
            except re.error as e:
                logger.error(
                    "pattern_compilation_failed",
                    pattern=trigger.get("pattern", ""),
                    error=str(e),
                )
                continue

        logger.info("patterns_compiled", count=len(patterns))
        return patterns

    def get_triggered_skills(
        self, query: str, intent: Optional[str] = None
    ) -> List[TriggerMatch]:
        """Get all skills triggered by query and intent.

        Combines triggers from multiple sources:
        1. Intent-based triggers (if intent provided)
        2. Pattern-based triggers (regex matching)
        3. Keyword triggers (substring matching)
        4. Always-active skills (from defaults)

        Deduplicates matches, keeping highest confidence for each skill.

        Args:
            query: User query text
            intent: Optional intent string (e.g., "VECTOR", "RESEARCH")

        Returns:
            List of TriggerMatch objects, deduplicated by skill

        Example:
            >>> loader = TriggerConfigLoader()
            >>> matches = loader.get_triggered_skills(
            ...     "search for latest papers",
            ...     intent="RESEARCH"
            ... )
            >>> [(m.skill, m.source) for m in matches]
            [('retrieval', 'intent'), ('planner', 'intent'), ('web_search', 'pattern')]
        """
        matches: List[TriggerMatch] = []

        # 1. Check intent triggers
        if intent and intent in self.config.get("intent_triggers", {}):
            intent_config = self.config["intent_triggers"][intent]

            # Required skills from intent (high priority)
            for skill in intent_config.get("required", []):
                matches.append(
                    TriggerMatch(
                        skill=skill,
                        source="intent",
                        priority="high",
                        confidence=0.95,
                    )
                )

            # Optional skills from intent (medium priority)
            for skill in intent_config.get("optional", []):
                matches.append(
                    TriggerMatch(
                        skill=skill,
                        source="intent",
                        priority="medium",
                        confidence=0.7,
                    )
                )

            logger.debug(
                "intent_triggers_matched",
                query=query[:50],
                intent=intent,
                required=len(intent_config.get("required", [])),
                optional=len(intent_config.get("optional", [])),
            )

        # 2. Check pattern triggers (regex)
        for pattern, skills, priority in self._compiled_patterns:
            if pattern.search(query):
                for skill in skills:
                    matches.append(
                        TriggerMatch(
                            skill=skill,
                            source="pattern",
                            priority=priority,
                            confidence=0.8,
                        )
                    )
                logger.debug(
                    "pattern_triggered",
                    query=query[:50],
                    pattern=pattern.pattern,
                    skills=skills,
                )

        # 3. Check keyword triggers (substring)
        query_lower = query.lower()
        for keyword, skills in self.config.get("keyword_triggers", {}).items():
            if keyword.lower() in query_lower:
                for skill in skills:
                    matches.append(
                        TriggerMatch(
                            skill=skill,
                            source="keyword",
                            priority="medium",
                            confidence=0.6,
                        )
                    )
                logger.debug(
                    "keyword_triggered",
                    query=query[:50],
                    keyword=keyword,
                    skills=skills,
                )

        # 4. Add always-active skills (monitoring, etc.)
        for skill in self.config.get("defaults", {}).get("always_active", []):
            matches.append(
                TriggerMatch(
                    skill=skill,
                    source="always_active",
                    priority="low",
                    confidence=1.0,
                )
            )

        # Deduplicate: Keep highest confidence for each skill
        seen: Dict[str, TriggerMatch] = {}
        for match in matches:
            if (
                match.skill not in seen
                or match.confidence > seen[match.skill].confidence
            ):
                seen[match.skill] = match

        deduplicated = list(seen.values())

        logger.info(
            "triggers_matched",
            query=query[:50],
            intent=intent,
            total_matches=len(matches),
            unique_skills=len(deduplicated),
            skills=[m.skill for m in deduplicated],
        )

        return deduplicated

    def get_context_budget(self, intent: Optional[str] = None) -> int:
        """Get context budget for an intent.

        Args:
            intent: Intent string (e.g., "VECTOR", "RESEARCH")

        Returns:
            Context budget in tokens

        Example:
            >>> loader = TriggerConfigLoader()
            >>> loader.get_context_budget("RESEARCH")
            5000
        """
        if intent and intent in self.config.get("intent_triggers", {}):
            return self.config["intent_triggers"][intent].get(
                "budget", self.config["defaults"]["context_budget"]
            )
        return self.config["defaults"]["context_budget"]

    def get_max_active_skills(self) -> int:
        """Get maximum number of active skills allowed.

        Returns:
            Max active skills from defaults

        Example:
            >>> loader = TriggerConfigLoader()
            >>> loader.get_max_active_skills()
            5
        """
        return self.config["defaults"].get("max_active_skills", 5)

    def reload_config(self) -> None:
        """Reload configuration from file.

        Useful for hot-reloading config changes without restarting.

        Example:
            >>> loader = TriggerConfigLoader()
            >>> # ... config file changed ...
            >>> loader.reload_config()
        """
        self.config = self._load_config()
        self._compiled_patterns = self._compile_patterns()

        logger.info(
            "config_reloaded",
            config_path=str(self.config_path),
        )
