"""Unit tests for Skill Registry.

Sprint Context:
    - Sprint 90 (2026-01-14): Feature 90.1 - Skill Registry Implementation (10 SP)

Tests:
    - Skill discovery from filesystem
    - SKILL.md parsing with frontmatter
    - Load/unload skills on demand
    - Active skill instructions
    - Intent-based skill matching (embedding similarity)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.agents.skills.registry import (
    LoadedSkill,
    SkillMetadata,
    SkillRegistry,
    get_skill_registry,
)


@pytest.fixture
def temp_skills_dir(tmp_path):
    """Create temporary skills directory with test skills."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Create test skill: reflection
    reflection_dir = skills_dir / "reflection"
    reflection_dir.mkdir()

    # SKILL.md with frontmatter
    skill_md_content = """---
name: reflection
version: 1.0.0
description: Self-critique and validation loop
author: AegisRAG Team
triggers:
  - validate
  - check
  - verify
  - critique
dependencies: []
permissions:
  - read_contexts
  - invoke_llm
resources:
  prompts: prompts/
---

# Reflection Skill

This skill enables the agent to critically evaluate and improve its own responses.

## When to Use

- Complex questions requiring multi-step reasoning
- Questions where accuracy is critical
"""

    (reflection_dir / "SKILL.md").write_text(skill_md_content)

    # config.yaml
    config = {
        "max_iterations": 3,
        "confidence_threshold": 0.85,
    }
    (reflection_dir / "config.yaml").write_text(yaml.dump(config))

    # prompts directory
    prompts_dir = reflection_dir / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "critique.txt").write_text("Critique this answer:\n{answer}")
    (prompts_dir / "improve.txt").write_text("Improve this answer:\n{answer}")

    # Create second test skill: retrieval
    retrieval_dir = skills_dir / "retrieval"
    retrieval_dir.mkdir()

    retrieval_md = """---
name: retrieval
version: 1.0.0
description: Vector and graph retrieval skill
author: AegisRAG Team
triggers:
  - search
  - find
  - lookup
  - retrieve
dependencies:
  - qdrant
  - neo4j
permissions:
  - read_documents
---

# Retrieval Skill

Executes vector and graph search queries.
"""

    (retrieval_dir / "SKILL.md").write_text(retrieval_md)

    return skills_dir


@pytest.fixture
def skill_registry(temp_skills_dir):
    """Create SkillRegistry instance with temp skills."""
    return SkillRegistry(skills_dir=temp_skills_dir, auto_discover=True)


class TestSkillDiscovery:
    """Test skill discovery from filesystem."""

    def test_discover_skills(self, skill_registry):
        """Test discovering skills from filesystem."""
        available = skill_registry.list_available()
        assert "reflection" in available
        assert "retrieval" in available
        assert len(available) == 2

    def test_discover_empty_directory(self, tmp_path):
        """Test discovering skills in empty directory."""
        empty_dir = tmp_path / "empty_skills"
        empty_dir.mkdir()

        registry = SkillRegistry(skills_dir=empty_dir, auto_discover=True)
        available = registry.list_available()
        assert len(available) == 0

    def test_discover_no_directory(self, tmp_path):
        """Test discovering skills when directory doesn't exist."""
        nonexistent_dir = tmp_path / "nonexistent"

        registry = SkillRegistry(skills_dir=nonexistent_dir, auto_discover=True)
        available = registry.list_available()
        assert len(available) == 0
        assert nonexistent_dir.exists()  # Should create directory


class TestSkillMetadataParsing:
    """Test SKILL.md parsing."""

    def test_parse_skill_metadata(self, skill_registry):
        """Test parsing skill metadata from SKILL.md."""
        metadata = skill_registry.get_metadata("reflection")
        assert metadata is not None
        assert metadata.name == "reflection"
        assert metadata.version == "1.0.0"
        assert metadata.description == "Self-critique and validation loop"
        assert metadata.author == "AegisRAG Team"
        assert "validate" in metadata.triggers
        assert "check" in metadata.triggers
        assert "verify" in metadata.triggers
        assert "read_contexts" in metadata.permissions
        assert "invoke_llm" in metadata.permissions

    def test_parse_skill_with_dependencies(self, skill_registry):
        """Test parsing skill with dependencies."""
        metadata = skill_registry.get_metadata("retrieval")
        assert metadata is not None
        assert "qdrant" in metadata.dependencies
        assert "neo4j" in metadata.dependencies

    def test_parse_invalid_yaml(self, tmp_path):
        """Test parsing skill with invalid YAML frontmatter."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        invalid_dir = skills_dir / "invalid"
        invalid_dir.mkdir()

        # Invalid YAML
        invalid_md = """---
name: invalid
version: 1.0.0
triggers
  - search  # Missing colon
---

# Invalid Skill
"""
        (invalid_dir / "SKILL.md").write_text(invalid_md)

        registry = SkillRegistry(skills_dir=skills_dir, auto_discover=True)
        available = registry.list_available()
        assert "invalid" not in available


class TestSkillLoading:
    """Test skill loading into memory."""

    def test_load_skill(self, skill_registry):
        """Test loading a skill."""
        skill = skill_registry.load("reflection")
        assert isinstance(skill, LoadedSkill)
        assert skill.metadata.name == "reflection"
        assert "Reflection Skill" in skill.instructions
        assert skill.config["max_iterations"] == 3
        assert skill.config["confidence_threshold"] == 0.85
        assert "critique" in skill.prompts
        assert "improve" in skill.prompts
        assert not skill.is_active

    def test_load_nonexistent_skill(self, skill_registry):
        """Test loading nonexistent skill raises ValueError."""
        with pytest.raises(ValueError, match="Skill not found: nonexistent"):
            skill_registry.load("nonexistent")

    def test_load_skill_twice(self, skill_registry):
        """Test loading same skill twice returns cached instance."""
        skill1 = skill_registry.load("reflection")
        skill2 = skill_registry.load("reflection")
        assert skill1 is skill2

    def test_extract_instructions_from_frontmatter(self, skill_registry):
        """Test extracting instructions after frontmatter."""
        skill = skill_registry.load("reflection")
        assert "---" not in skill.instructions
        assert "# Reflection Skill" in skill.instructions
        assert "When to Use" in skill.instructions


class TestSkillActivation:
    """Test skill activation and deactivation."""

    def test_activate_skill(self, skill_registry):
        """Test activating a skill."""
        instructions = skill_registry.activate("reflection")
        assert "Reflection Skill" in instructions
        assert "reflection" in skill_registry.list_active()

        skill = skill_registry._loaded["reflection"]
        assert skill.is_active

    def test_activate_multiple_skills(self, skill_registry):
        """Test activating multiple skills."""
        skill_registry.activate("reflection")
        skill_registry.activate("retrieval")

        active = skill_registry.list_active()
        assert "reflection" in active
        assert "retrieval" in active
        assert len(active) == 2

    def test_deactivate_skill(self, skill_registry):
        """Test deactivating a skill."""
        skill_registry.activate("reflection")
        assert "reflection" in skill_registry.list_active()

        skill_registry.deactivate("reflection")
        assert "reflection" not in skill_registry.list_active()

        skill = skill_registry._loaded["reflection"]
        assert not skill.is_active

    def test_get_active_instructions(self, skill_registry):
        """Test getting combined instructions from active skills."""
        skill_registry.activate("reflection")
        skill_registry.activate("retrieval")

        instructions = skill_registry.get_active_instructions()
        assert "## Skill: reflection" in instructions
        assert "## Skill: retrieval" in instructions
        assert "---" in instructions  # Separator


class TestIntentMatching:
    """Test embedding-based intent matching."""

    @patch("src.agents.skills.registry.get_embedding_service")
    def test_match_intent_single_skill(self, mock_get_embedding, skill_registry):
        """Test matching intent to single skill."""
        # Mock embedding service
        mock_service = MagicMock()
        mock_get_embedding.return_value = mock_service

        # Mock embeddings (high similarity for "validate" trigger)
        mock_service.embed_single.side_effect = [
            [0.9, 0.1, 0.0],  # "I need to verify this answer"
            [0.85, 0.15, 0.0],  # "validate" trigger
            [0.80, 0.20, 0.0],  # "check" trigger
            [0.88, 0.12, 0.0],  # "verify" trigger
            [0.75, 0.25, 0.0],  # "critique" trigger
            [0.3, 0.5, 0.2],  # "search" trigger (low similarity)
            [0.2, 0.6, 0.2],  # "find" trigger
            [0.1, 0.7, 0.2],  # "lookup" trigger
            [0.15, 0.65, 0.2],  # "retrieve" trigger
        ]

        matches = skill_registry.match_intent(
            "I need to verify this answer", similarity_threshold=0.75
        )
        assert "reflection" in matches
        assert "retrieval" not in matches

    @patch("src.agents.skills.registry.get_embedding_service")
    def test_match_intent_multiple_skills(self, mock_get_embedding, skill_registry):
        """Test matching intent to multiple skills."""
        # Mock embedding service
        mock_service = MagicMock()
        mock_get_embedding.return_value = mock_service

        # Mock embeddings (high similarity for both skills)
        mock_service.embed_single.side_effect = [
            [0.9, 0.8, 0.0],  # Intent embedding
            [0.85, 0.82, 0.0],  # "validate" trigger
            [0.80, 0.85, 0.0],  # "check" trigger
            [0.88, 0.83, 0.0],  # "verify" trigger
            [0.75, 0.78, 0.0],  # "critique" trigger
            [0.82, 0.90, 0.0],  # "search" trigger (high similarity)
            [0.80, 0.88, 0.0],  # "find" trigger
            [0.78, 0.85, 0.0],  # "lookup" trigger
            [0.76, 0.86, 0.0],  # "retrieve" trigger
        ]

        matches = skill_registry.match_intent(
            "search and verify documents", similarity_threshold=0.75
        )
        # Should return both skills, sorted by similarity
        assert len(matches) >= 1

    @patch("src.agents.skills.registry.get_embedding_service")
    def test_match_intent_no_matches(self, mock_get_embedding, skill_registry):
        """Test matching intent with no matches."""
        # Mock embedding service
        mock_service = MagicMock()
        mock_get_embedding.return_value = mock_service

        # Mock embeddings (low similarity for all triggers)
        mock_service.embed_single.side_effect = [
            [0.1, 0.1, 0.8],  # Intent embedding (very different)
            [0.9, 0.1, 0.0],  # All trigger embeddings (different)
            [0.85, 0.15, 0.0],
            [0.88, 0.12, 0.0],
            [0.75, 0.25, 0.0],
            [0.82, 0.18, 0.0],
            [0.80, 0.20, 0.0],
            [0.78, 0.22, 0.0],
            [0.76, 0.24, 0.0],
        ]

        matches = skill_registry.match_intent(
            "unrelated query", similarity_threshold=0.75
        )
        assert len(matches) == 0

    @patch("src.agents.skills.registry.get_embedding_service")
    def test_match_intent_handles_multi_vector_backend(
        self, mock_get_embedding, skill_registry
    ):
        """Test intent matching with multi-vector backend (flag-embedding)."""
        # Mock embedding service
        mock_service = MagicMock()
        mock_get_embedding.return_value = mock_service

        # Mock multi-vector embeddings (dict with dense + sparse)
        mock_service.embed_single.side_effect = [
            {"dense": [0.9, 0.1, 0.0], "sparse": {1: 0.5}},  # Intent
            {"dense": [0.85, 0.15, 0.0], "sparse": {2: 0.4}},  # Triggers
            {"dense": [0.80, 0.20, 0.0], "sparse": {3: 0.3}},
            {"dense": [0.88, 0.12, 0.0], "sparse": {4: 0.6}},
            {"dense": [0.75, 0.25, 0.0], "sparse": {5: 0.2}},
            {"dense": [0.3, 0.5, 0.2], "sparse": {6: 0.1}},
            {"dense": [0.2, 0.6, 0.2], "sparse": {7: 0.15}},
            {"dense": [0.1, 0.7, 0.2], "sparse": {8: 0.12}},
            {"dense": [0.15, 0.65, 0.2], "sparse": {9: 0.18}},
        ]

        matches = skill_registry.match_intent(
            "verify this answer", similarity_threshold=0.75
        )
        assert "reflection" in matches


class TestGlobalRegistry:
    """Test global registry singleton."""

    def test_get_skill_registry_singleton(self):
        """Test get_skill_registry returns singleton instance."""
        from src.agents.skills.registry import _registry, get_skill_registry

        # Reset global instance
        import src.agents.skills.registry

        src.agents.skills.registry._registry = None

        registry1 = get_skill_registry(Path("skills"))
        registry2 = get_skill_registry()

        assert registry1 is registry2

    def test_get_skill_registry_creates_on_first_call(self, tmp_path):
        """Test get_skill_registry creates instance on first call."""
        import src.agents.skills.registry

        src.agents.skills.registry._registry = None

        skills_dir = tmp_path / "test_skills"
        registry = get_skill_registry(skills_dir)

        assert registry is not None
        assert registry.skills_dir == skills_dir
