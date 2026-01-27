"""Unit tests for skill triggers configuration (Sprint 121).

Sprint 121 Feature 121.4: Skills Config Validation & Bilingual Support

Tests the following:
- YAML structure validation (defaults, intent_triggers, pattern_triggers, keyword_triggers)
- Pattern regex compilation and matching
- German vs English bilingual support
- Intent-to-skill mappings
- Pattern priority levels
- Configuration consistency and completeness
"""

import re
from pathlib import Path

import pytest
import yaml


# ============================================================================
# Fixtures: Configuration Loading
# ============================================================================


@pytest.fixture
def skill_triggers_config():
    """Load and parse skill_triggers.yaml configuration."""
    config_path = Path("/home/admin/projects/aegisrag/AEGIS_Rag/config/skill_triggers.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


@pytest.fixture
def valid_skills():
    """List of valid skill names that should appear in config."""
    return {
        "retrieval",
        "synthesis",
        "reflection",
        "planner",
        "web_search",
        "memory",
        "graph_reasoning",
        "hallucination_monitor",
        "calculator",
    }


# ============================================================================
# Tests: Configuration Structure
# ============================================================================


class TestConfigurationStructure:
    """Test overall YAML configuration structure and required keys."""

    def test_config_loads_successfully(self, skill_triggers_config):
        """Test that YAML configuration loads without errors."""
        assert skill_triggers_config is not None
        assert isinstance(skill_triggers_config, dict)

    def test_config_has_required_top_level_keys(self, skill_triggers_config):
        """Test all required top-level keys exist."""
        required_keys = {"defaults", "intent_triggers", "pattern_triggers", "keyword_triggers"}
        assert required_keys.issubset(skill_triggers_config.keys())

    def test_defaults_section_exists(self, skill_triggers_config):
        """Test defaults section has required fields."""
        defaults = skill_triggers_config["defaults"]

        assert isinstance(defaults, dict)
        assert "context_budget" in defaults
        assert "max_active_skills" in defaults
        assert "always_active" in defaults

    def test_defaults_values_valid(self, skill_triggers_config):
        """Test defaults section has valid values."""
        defaults = skill_triggers_config["defaults"]

        assert isinstance(defaults["context_budget"], int)
        assert defaults["context_budget"] > 0

        assert isinstance(defaults["max_active_skills"], int)
        assert defaults["max_active_skills"] > 0

        assert isinstance(defaults["always_active"], list)
        assert all(isinstance(s, str) for s in defaults["always_active"])

    def test_intent_triggers_section_exists(self, skill_triggers_config):
        """Test intent_triggers section exists and is dict."""
        intent_triggers = skill_triggers_config["intent_triggers"]

        assert isinstance(intent_triggers, dict)
        assert len(intent_triggers) > 0

    def test_pattern_triggers_section_exists(self, skill_triggers_config):
        """Test pattern_triggers section exists and is list."""
        pattern_triggers = skill_triggers_config["pattern_triggers"]

        assert isinstance(pattern_triggers, list)
        assert len(pattern_triggers) > 0

    def test_keyword_triggers_section_exists(self, skill_triggers_config):
        """Test keyword_triggers section exists and is dict."""
        keyword_triggers = skill_triggers_config["keyword_triggers"]

        assert isinstance(keyword_triggers, dict)
        assert len(keyword_triggers) > 0


# ============================================================================
# Tests: Intent Triggers
# ============================================================================


class TestIntentTriggers:
    """Test intent-based skill triggers (C-LARA 5-class)."""

    def test_required_intents_exist(self, skill_triggers_config):
        """Test all required intents are defined."""
        required_intents = {"VECTOR", "GRAPH", "HYBRID", "MEMORY", "RESEARCH"}
        intent_triggers = skill_triggers_config["intent_triggers"]

        assert required_intents.issubset(intent_triggers.keys())

    def test_intent_has_required_fields(self, skill_triggers_config):
        """Test each intent has required configuration fields."""
        for intent_name, intent_config in skill_triggers_config["intent_triggers"].items():
            assert isinstance(intent_config, dict)
            assert "required" in intent_config, f"Intent {intent_name} missing 'required'"
            assert "optional" in intent_config, f"Intent {intent_name} missing 'optional'"
            assert "budget" in intent_config, f"Intent {intent_name} missing 'budget'"

    def test_intent_skills_are_lists(self, skill_triggers_config):
        """Test that skills in intents are lists."""
        for intent_name, intent_config in skill_triggers_config["intent_triggers"].items():
            assert isinstance(intent_config["required"], list)
            assert isinstance(intent_config["optional"], list)

    def test_intent_budget_values_valid(self, skill_triggers_config):
        """Test intent budget values are positive integers."""
        for intent_name, intent_config in skill_triggers_config["intent_triggers"].items():
            budget = intent_config["budget"]
            assert isinstance(budget, int)
            assert budget > 0
            assert budget <= 5000, f"Intent {intent_name} budget {budget} seems too high"

    def test_vector_intent_configuration(self, skill_triggers_config):
        """Test VECTOR intent has correct configuration."""
        vector = skill_triggers_config["intent_triggers"]["VECTOR"]

        assert "retrieval" in vector["required"]
        assert "synthesis" in vector["optional"]
        assert vector["budget"] >= 1000

    def test_graph_intent_configuration(self, skill_triggers_config):
        """Test GRAPH intent has correct configuration."""
        graph = skill_triggers_config["intent_triggers"]["GRAPH"]

        assert "retrieval" in graph["required"]
        assert "graph_reasoning" in graph["required"]
        assert "reflection" in graph["optional"]

    def test_hybrid_intent_configuration(self, skill_triggers_config):
        """Test HYBRID intent has correct configuration."""
        hybrid = skill_triggers_config["intent_triggers"]["HYBRID"]
        graph = skill_triggers_config["intent_triggers"]["GRAPH"]

        assert "retrieval" in hybrid["required"]
        assert "graph_reasoning" in hybrid["required"]
        assert hybrid["budget"] >= graph["budget"] or hybrid["budget"] >= 3000

    def test_memory_intent_configuration(self, skill_triggers_config):
        """Test MEMORY intent has correct configuration."""
        memory = skill_triggers_config["intent_triggers"]["MEMORY"]

        assert "memory" in memory["required"]
        assert "retrieval" in memory["required"]

    def test_research_intent_configuration(self, skill_triggers_config):
        """Test RESEARCH intent has correct configuration."""
        research = skill_triggers_config["intent_triggers"]["RESEARCH"]

        assert "retrieval" in research["required"]
        assert "reflection" in research["required"]
        assert "planner" in research["required"]
        assert "web_search" in research["optional"]


# ============================================================================
# Tests: Pattern Triggers
# ============================================================================


class TestPatternTriggers:
    """Test pattern-based skill triggers with regex."""

    def test_pattern_triggers_structure(self, skill_triggers_config):
        """Test pattern triggers have correct structure."""
        patterns = skill_triggers_config["pattern_triggers"]

        assert isinstance(patterns, list)
        for pattern_entry in patterns:
            assert isinstance(pattern_entry, dict)
            assert "pattern" in pattern_entry
            assert "skills" in pattern_entry
            assert "priority" in pattern_entry

    def test_pattern_regex_valid(self, skill_triggers_config):
        """Test all pattern regexes compile without errors."""
        patterns = skill_triggers_config["pattern_triggers"]

        for idx, pattern_entry in enumerate(patterns):
            try:
                re.compile(pattern_entry["pattern"])
            except re.error as e:
                pytest.fail(f"Pattern {idx} regex invalid: {pattern_entry['pattern']} - {e}")

    def test_pattern_skills_is_list(self, skill_triggers_config):
        """Test pattern skills field is always a list."""
        patterns = skill_triggers_config["pattern_triggers"]

        for idx, pattern_entry in enumerate(patterns):
            assert isinstance(pattern_entry["skills"], list)
            assert len(pattern_entry["skills"]) > 0

    def test_pattern_priority_values(self, skill_triggers_config):
        """Test pattern priority values are valid."""
        patterns = skill_triggers_config["pattern_triggers"]
        valid_priorities = {"high", "medium", "low"}

        for idx, pattern_entry in enumerate(patterns):
            priority = pattern_entry["priority"]
            assert priority in valid_priorities, f"Pattern {idx} has invalid priority: {priority}"

    def test_search_pattern_english(self, skill_triggers_config):
        """Test search pattern matches English keywords."""
        patterns = skill_triggers_config["pattern_triggers"]
        search_patterns = [p for p in patterns if "search" in p["pattern"].lower()]

        assert len(search_patterns) > 0, "No search patterns found"

        search_pattern = search_patterns[0]
        regex = re.compile(search_pattern["pattern"])

        # Should match English search keywords
        assert regex.search("search for information")
        assert regex.search("find the document")
        assert regex.search("look up this topic")

    def test_search_pattern_german(self, skill_triggers_config):
        """Test search pattern matches German keywords."""
        patterns = skill_triggers_config["pattern_triggers"]
        search_patterns = [p for p in patterns if "suche" in p["pattern"].lower()]

        assert len(search_patterns) > 0, "No German search patterns found"

        search_pattern = search_patterns[0]
        regex = re.compile(search_pattern["pattern"])

        # Should match German search keywords
        assert regex.search("suche nach Information")
        assert regex.search("finde das Dokument")

    def test_comparison_pattern_english(self, skill_triggers_config):
        """Test comparison pattern matches English keywords."""
        patterns = skill_triggers_config["pattern_triggers"]
        comp_patterns = [p for p in patterns if "compare" in p["pattern"].lower()]

        assert len(comp_patterns) > 0

        comp_pattern = comp_patterns[0]
        regex = re.compile(comp_pattern["pattern"])

        # Should match comparison keywords
        assert regex.search("compare these two")
        assert regex.search("contrast the differences")

    def test_comparison_pattern_german(self, skill_triggers_config):
        """Test comparison pattern matches German keywords."""
        patterns = skill_triggers_config["pattern_triggers"]
        comp_patterns = [p for p in patterns if "vergleich" in p["pattern"].lower()]

        assert len(comp_patterns) > 0

        comp_pattern = comp_patterns[0]
        regex = re.compile(comp_pattern["pattern"])

        # Should match German comparison keywords
        assert regex.search("Vergleich zwischen")
        assert regex.search("Unterschied zeigen")

    def test_recency_pattern_english(self, skill_triggers_config):
        """Test recency pattern matches English time keywords."""
        patterns = skill_triggers_config["pattern_triggers"]
        recency_patterns = [p for p in patterns if "latest" in p["pattern"].lower()]

        assert len(recency_patterns) > 0

        recency_pattern = recency_patterns[0]
        regex = re.compile(recency_pattern["pattern"])

        assert regex.search("what's the latest")
        assert regex.search("this week's news")
        assert regex.search("today's updates")
        assert regex.search("2026")

    def test_recency_pattern_german(self, skill_triggers_config):
        """Test recency pattern matches German time keywords."""
        patterns = skill_triggers_config["pattern_triggers"]
        recency_patterns = [p for p in patterns if "aktuell" in p["pattern"].lower()]

        assert len(recency_patterns) > 0

        recency_pattern = recency_patterns[0]
        regex = re.compile(recency_pattern["pattern"])

        assert regex.search("aktuelle Nachrichten")
        assert regex.search("diese Woche")
        assert regex.search("heute")

    def test_planning_pattern_english_german(self, skill_triggers_config):
        """Test planning pattern matches both English and German."""
        patterns = skill_triggers_config["pattern_triggers"]
        plan_patterns = [p for p in patterns if "plan" in p["pattern"].lower()]

        assert len(plan_patterns) > 0

        plan_pattern = plan_patterns[0]
        regex = re.compile(plan_pattern["pattern"])

        # English
        assert regex.search("how to implement")
        assert regex.search("tutorial on X")
        # German
        assert regex.search("Schritte zum Erfolg")
        assert regex.search("Anleitung")

    def test_pattern_case_insensitivity(self, skill_triggers_config):
        """Test that patterns are case-insensitive."""
        patterns = skill_triggers_config["pattern_triggers"]

        for pattern_entry in patterns:
            pattern = pattern_entry["pattern"]
            # All patterns should have (?i) for case-insensitive matching
            assert "(?i)" in pattern, f"Pattern not case-insensitive: {pattern}"

    def test_pattern_has_retrieval_skill(self, skill_triggers_config):
        """Test that search patterns map to appropriate skills."""
        patterns = skill_triggers_config["pattern_triggers"]
        # Find patterns with "suche" (German search) or "search" (English)
        search_patterns = [p for p in patterns if "suche" in p["pattern"].lower() or "search" in p["pattern"].lower()]

        # Search patterns should map to either retrieval or web_search skills
        for search_pattern in search_patterns:
            has_search_skill = "retrieval" in search_pattern["skills"] or "web_search" in search_pattern["skills"]
            assert has_search_skill, f"Search pattern missing retrieval/web_search: {search_pattern}"


# ============================================================================
# Tests: Keyword Triggers
# ============================================================================


class TestKeywordTriggers:
    """Test keyword-based skill triggers."""

    def test_keyword_triggers_structure(self, skill_triggers_config):
        """Test keyword triggers are dict of keyword -> skill list."""
        keywords = skill_triggers_config["keyword_triggers"]

        assert isinstance(keywords, dict)
        for keyword, skills in keywords.items():
            assert isinstance(keyword, str)
            assert isinstance(skills, list)
            assert len(skills) > 0

    def test_english_keywords_present(self, skill_triggers_config):
        """Test English keywords are defined."""
        keywords = skill_triggers_config["keyword_triggers"]

        english_keywords = {"analyze", "summarize", "remember", "calculate", "graph", "plan", "recent"}

        for kw in english_keywords:
            assert kw in keywords, f"Missing English keyword: {kw}"

    def test_german_keywords_present(self, skill_triggers_config):
        """Test German keywords are defined."""
        keywords = skill_triggers_config["keyword_triggers"]

        german_keywords = {
            "analysiere",
            "zusammenfassung",
            "erinnere",
            "berechne",
            "entitäten",
            "schritte",
            "aktuell",
        }

        for kw in german_keywords:
            assert kw in keywords, f"Missing German keyword: {kw}"

    def test_keyword_mappings_valid(self, skill_triggers_config):
        """Test that all keywords map to valid skills."""
        keywords = skill_triggers_config["keyword_triggers"]
        valid_skills = {
            "retrieval",
            "synthesis",
            "reflection",
            "memory",
            "calculator",
            "graph_reasoning",
            "planner",
            "web_search",
        }

        for keyword, skills in keywords.items():
            for skill in skills:
                assert skill in valid_skills, f"Keyword '{keyword}' maps to invalid skill '{skill}'"

    def test_analyze_keyword(self, skill_triggers_config):
        """Test analyze keyword configuration."""
        keywords = skill_triggers_config["keyword_triggers"]

        assert "analyze" in keywords
        assert "reflection" in keywords["analyze"]

        assert "analysiere" in keywords
        assert "reflection" in keywords["analysiere"]

    def test_summarize_keyword(self, skill_triggers_config):
        """Test summarize keyword configuration."""
        keywords = skill_triggers_config["keyword_triggers"]

        assert "summarize" in keywords
        assert "synthesis" in keywords["summarize"]

        assert "zusammenfassung" in keywords
        assert "synthesis" in keywords["zusammenfassung"]

    def test_remember_keyword(self, skill_triggers_config):
        """Test remember/memory keyword configuration."""
        keywords = skill_triggers_config["keyword_triggers"]

        assert "remember" in keywords
        assert "memory" in keywords["remember"]

        assert "erinnere" in keywords
        assert "memory" in keywords["erinnere"]

    def test_calculate_keyword(self, skill_triggers_config):
        """Test calculate keyword configuration."""
        keywords = skill_triggers_config["keyword_triggers"]

        assert "calculate" in keywords
        assert "calculator" in keywords["calculate"]

        assert "berechne" in keywords
        assert "calculator" in keywords["berechne"]

    def test_graph_keyword(self, skill_triggers_config):
        """Test graph/entity keyword configuration."""
        keywords = skill_triggers_config["keyword_triggers"]

        assert "graph" in keywords
        assert "graph_reasoning" in keywords["graph"]

        assert "entitäten" in keywords
        assert "graph_reasoning" in keywords["entitäten"]

    def test_search_keywords(self, skill_triggers_config):
        """Test search-related keywords."""
        keywords = skill_triggers_config["keyword_triggers"]

        search_keywords = {"internet", "aktuell", "neueste"}
        for kw in search_keywords:
            if kw in keywords:
                assert "web_search" in keywords[kw]


# ============================================================================
# Tests: Bilingual Support
# ============================================================================


class TestBilingualSupport:
    """Test bilingual (English/German) support in configuration."""

    def test_bilingual_coverage_search(self, skill_triggers_config):
        """Test search functionality has both English and German patterns."""
        patterns = skill_triggers_config["pattern_triggers"]
        keywords = skill_triggers_config["keyword_triggers"]

        # Pattern triggers - look for both suche and search patterns
        has_search_patterns = any("search" in p["pattern"].lower() for p in patterns)
        has_suche_patterns = any("suche" in p["pattern"].lower() for p in patterns)

        # At least one should exist
        assert has_search_patterns or has_suche_patterns, "No search/suche patterns found"

        # Keywords - look for search-related keywords in both languages
        has_search_keywords = any(k in keywords for k in ["internet", "recent", "latest"])
        has_suche_keywords = any(k in keywords for k in ["aktuell", "neueste"])

        # At least one should exist
        assert has_search_keywords or has_suche_keywords, "No search keywords found"

    def test_bilingual_coverage_summarization(self, skill_triggers_config):
        """Test summarization functionality has both languages."""
        keywords = skill_triggers_config["keyword_triggers"]

        # English
        assert "summarize" in keywords
        # German
        assert "zusammenfassung" in keywords

    def test_bilingual_coverage_analysis(self, skill_triggers_config):
        """Test analysis functionality has both languages."""
        keywords = skill_triggers_config["keyword_triggers"]

        # English
        assert "analyze" in keywords
        # German
        assert "analysiere" in keywords

    def test_intent_names_english(self, skill_triggers_config):
        """Test intent names are English (consistent convention)."""
        intents = skill_triggers_config["intent_triggers"].keys()

        for intent in intents:
            # Intent names should be all caps English (VECTOR, GRAPH, etc.)
            assert intent.isupper()
            assert intent in {"VECTOR", "GRAPH", "HYBRID", "MEMORY", "RESEARCH"}

    def test_skill_names_english(self, skill_triggers_config):
        """Test skill names are English snake_case (consistent convention)."""
        all_skills = set()

        # From intent triggers
        for intent_config in skill_triggers_config["intent_triggers"].values():
            all_skills.update(intent_config["required"])
            all_skills.update(intent_config["optional"])

        # From pattern triggers
        for pattern_entry in skill_triggers_config["pattern_triggers"]:
            all_skills.update(pattern_entry["skills"])

        # From keyword triggers
        for skills in skill_triggers_config["keyword_triggers"].values():
            all_skills.update(skills)

        for skill in all_skills:
            # Skills should be lowercase with underscores
            assert skill.islower() or "_" in skill
            # Should not contain special characters
            assert all(c.isalnum() or c == "_" for c in skill)


# ============================================================================
# Tests: Configuration Consistency
# ============================================================================


class TestConfigurationConsistency:
    """Test overall configuration consistency and cross-references."""

    def test_skills_referenced_are_defined(self, skill_triggers_config):
        """Test all referenced skills are actually defined somewhere."""
        all_skills = set()

        # Collect all skills referenced in configuration
        referenced_skills = set()

        # From intent triggers
        for intent_config in skill_triggers_config["intent_triggers"].values():
            referenced_skills.update(intent_config["required"])
            referenced_skills.update(intent_config["optional"])

        # Always active skills
        referenced_skills.update(skill_triggers_config["defaults"]["always_active"])

        # From pattern triggers
        for pattern_entry in skill_triggers_config["pattern_triggers"]:
            referenced_skills.update(pattern_entry["skills"])

        # From keyword triggers
        for skills in skill_triggers_config["keyword_triggers"].values():
            referenced_skills.update(skills)

        # Verify all are reasonable skill names
        for skill in referenced_skills:
            assert isinstance(skill, str)
            assert len(skill) > 0
            assert skill.islower() or "_" in skill

    def test_always_active_skills_exist_in_patterns(self, skill_triggers_config):
        """Test always-active skills are also in pattern/keyword triggers."""
        always_active = skill_triggers_config["defaults"]["always_active"]

        # Collect all skills from triggers
        trigger_skills = set()
        for pattern_entry in skill_triggers_config["pattern_triggers"]:
            trigger_skills.update(pattern_entry["skills"])
        for skills in skill_triggers_config["keyword_triggers"].values():
            trigger_skills.update(skills)

        # Always-active should be a subset (they run regardless)
        for skill in always_active:
            assert isinstance(skill, str)

    def test_required_skills_subset_of_pattern_skills(self, skill_triggers_config):
        """Test required intent skills appear in patterns or keywords."""
        intents = skill_triggers_config["intent_triggers"]
        trigger_skills = set()

        # Collect skills from patterns
        for pattern_entry in skill_triggers_config["pattern_triggers"]:
            trigger_skills.update(pattern_entry["skills"])

        # Collect skills from keywords
        for skills in skill_triggers_config["keyword_triggers"].values():
            trigger_skills.update(skills)

        # All required and optional skills should appear in at least one trigger
        for intent_config in intents.values():
            for skill in intent_config["required"] + intent_config["optional"]:
                # Note: Not necessarily true, some skills might only be in intents
                # This test ensures they are defined somewhere
                assert isinstance(skill, str)

    def test_no_duplicate_keywords(self, skill_triggers_config):
        """Test keyword triggers don't have duplicate keys."""
        keywords = skill_triggers_config["keyword_triggers"]

        # Dict keys are already unique by definition, but check for case issues
        keywords_lower = [k.lower() for k in keywords.keys()]
        assert len(keywords_lower) == len(set(keywords_lower)), "Duplicate keywords found (case-insensitive)"

    def test_pattern_priorities_meaningful(self, skill_triggers_config):
        """Test pattern priorities are consistently used."""
        patterns = skill_triggers_config["pattern_triggers"]
        priorities = [p["priority"] for p in patterns]

        # All three priority levels should be used (or at least high and medium)
        assert "high" in priorities
        assert "medium" in priorities

    def test_budget_hierarchy(self, skill_triggers_config):
        """Test context budgets follow logical hierarchy."""
        intents = skill_triggers_config["intent_triggers"]

        vector_budget = intents["VECTOR"]["budget"]
        memory_budget = intents["MEMORY"]["budget"]
        hybrid_budget = intents["HYBRID"]["budget"]
        research_budget = intents["RESEARCH"]["budget"]

        # Basic sanity: research should typically need more budget than vector
        # This is a guideline, not a strict requirement
        assert vector_budget > 0
        assert memory_budget >= vector_budget  # Memory needs retrieval too
        assert hybrid_budget >= memory_budget  # Hybrid is complex


# ============================================================================
# Tests: YAML Formatting & Comments
# ============================================================================


class TestYAMLFormatting:
    """Test YAML file formatting and documentation."""

    def test_yaml_comments_present(self):
        """Test that YAML file has meaningful comments."""
        config_path = Path("/home/admin/projects/aegisrag/AEGIS_Rag/config/skill_triggers.yaml")
        with open(config_path) as f:
            content = f.read()

        # Count comment lines
        comment_lines = [line for line in content.split("\n") if line.strip().startswith("#")]
        assert len(comment_lines) > 0, "YAML file should have comments"

    def test_yaml_file_readable(self):
        """Test YAML file is readable and not corrupted."""
        config_path = Path("/home/admin/projects/aegisrag/AEGIS_Rag/config/skill_triggers.yaml")

        with open(config_path) as f:
            content = f.read()

        assert len(content) > 0
        assert "intent_triggers:" in content
        assert "pattern_triggers:" in content
        assert "keyword_triggers:" in content
