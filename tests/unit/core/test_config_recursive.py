"""Unit tests for Recursive LLM configuration (Sprint 92).

Sprint 92 Features:
- Feature 92.6: Per-Level Configuration
- Feature 92.10: Parallel Worker Configuration

Test file: tests/unit/core/test_config_recursive.py
"""

import pytest
from unittest.mock import MagicMock
from pydantic import ValidationError

from src.core.config import RecursiveLevelConfig, RecursiveLLMSettings


class TestRecursiveLevelConfig:
    """Tests for RecursiveLevelConfig validation and defaults."""

    def test_recursive_level_config_defaults(self):
        """Test RecursiveLevelConfig uses sensible defaults."""
        config = RecursiveLevelConfig(level=0, segment_size_tokens=16384)

        assert config.level == 0
        assert config.segment_size_tokens == 16384
        assert config.overlap_tokens == 200  # Default
        assert config.top_k_subsegments == 3  # Default
        assert config.scoring_method == "dense+sparse"  # Default
        assert config.relevance_threshold == 0.5  # Default

    def test_recursive_level_config_custom_values(self):
        """Test RecursiveLevelConfig with custom values."""
        config = RecursiveLevelConfig(
            level=2,
            segment_size_tokens=4096,
            overlap_tokens=300,
            top_k_subsegments=5,
            scoring_method="multi-vector",
            relevance_threshold=0.7,
        )

        assert config.level == 2
        assert config.segment_size_tokens == 4096
        assert config.overlap_tokens == 300
        assert config.top_k_subsegments == 5
        assert config.scoring_method == "multi-vector"
        assert config.relevance_threshold == 0.7

    def test_segment_size_validation_min(self):
        """Test segment_size_tokens minimum validation (>= 1000)."""
        with pytest.raises(ValidationError) as exc_info:
            RecursiveLevelConfig(level=0, segment_size_tokens=500)

        # Check for validation error about minimum constraint
        error_str = str(exc_info.value).lower()
        assert "greater than or equal to 1000" in error_str or "at least 1000" in error_str

    def test_segment_size_validation_max(self):
        """Test segment_size_tokens maximum validation (<= 32000)."""
        with pytest.raises(ValidationError) as exc_info:
            RecursiveLevelConfig(level=0, segment_size_tokens=40000)

        # Check for validation error about maximum constraint
        error_str = str(exc_info.value).lower()
        assert "less than or equal to 32000" in error_str or "at most 32000" in error_str

    def test_overlap_tokens_validation_min(self):
        """Test overlap_tokens minimum (0 is valid, no explicit min)."""
        config = RecursiveLevelConfig(
            level=0, segment_size_tokens=16384, overlap_tokens=0
        )
        assert config.overlap_tokens == 0

    def test_threshold_validation_range(self):
        """Test relevance_threshold is between 0.0 and 1.0."""
        # Valid: at boundary
        config_min = RecursiveLevelConfig(
            level=0, segment_size_tokens=16384, relevance_threshold=0.0
        )
        assert config_min.relevance_threshold == 0.0

        config_max = RecursiveLevelConfig(
            level=0, segment_size_tokens=16384, relevance_threshold=1.0
        )
        assert config_max.relevance_threshold == 1.0

    def test_threshold_validation_invalid_low(self):
        """Test relevance_threshold < 0.0 raises validation error."""
        with pytest.raises(ValidationError):
            RecursiveLevelConfig(
                level=0, segment_size_tokens=16384, relevance_threshold=-0.1
            )

    def test_threshold_validation_invalid_high(self):
        """Test relevance_threshold > 1.0 raises validation error."""
        with pytest.raises(ValidationError):
            RecursiveLevelConfig(
                level=0, segment_size_tokens=16384, relevance_threshold=1.1
            )

    def test_scoring_method_valid_options(self):
        """Test scoring_method accepts all valid options."""
        methods = ["dense+sparse", "multi-vector", "llm", "adaptive"]

        for method in methods:
            config = RecursiveLevelConfig(
                level=0, segment_size_tokens=16384, scoring_method=method
            )
            assert config.scoring_method == method

    def test_scoring_method_invalid(self):
        """Test scoring_method rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            RecursiveLevelConfig(
                level=0, segment_size_tokens=16384, scoring_method="invalid"
            )

        error_str = str(exc_info.value).lower()
        assert "dense+sparse" in error_str or "scoring" in error_str

    def test_top_k_subsegments_positive(self):
        """Test top_k_subsegments can be set to various positive values."""
        for top_k in [1, 5, 10, 20]:
            config = RecursiveLevelConfig(
                level=0, segment_size_tokens=16384, top_k_subsegments=top_k
            )
            assert config.top_k_subsegments == top_k


class TestRecursiveLLMSettings:
    """Tests for RecursiveLLMSettings configuration and defaults."""

    def test_recursive_llm_settings_defaults(self):
        """Test RecursiveLLMSettings uses sensible defaults."""
        settings = RecursiveLLMSettings()

        assert settings.max_depth == 3
        assert len(settings.levels) == 4  # 4 default levels
        assert settings.max_parallel_workers == 1  # DGX Spark default
        assert "ollama" in settings.worker_limits
        assert "openai" in settings.worker_limits
        assert "alibaba" in settings.worker_limits

    def test_default_level_configuration_structure(self):
        """Test default levels are properly configured for hierarchy."""
        settings = RecursiveLLMSettings()
        levels = settings.levels

        # Level 0: Largest chunks (overview)
        assert levels[0].level == 0
        assert levels[0].segment_size_tokens == 16384
        assert levels[0].overlap_tokens == 400
        assert levels[0].top_k_subsegments == 5
        assert levels[0].scoring_method == "dense+sparse"
        assert levels[0].relevance_threshold == 0.5

        # Level 1: Medium chunks
        assert levels[1].level == 1
        assert levels[1].segment_size_tokens == 8192
        assert levels[1].overlap_tokens == 300
        assert levels[1].top_k_subsegments == 4
        assert levels[1].scoring_method == "dense+sparse"
        assert levels[1].relevance_threshold == 0.6

        # Level 2: Smaller chunks
        assert levels[2].level == 2
        assert levels[2].segment_size_tokens == 4096
        assert levels[2].overlap_tokens == 200
        assert levels[2].top_k_subsegments == 3
        assert levels[2].scoring_method == "adaptive"
        assert levels[2].relevance_threshold == 0.7

        # Level 3: Tiny chunks
        assert levels[3].level == 3
        assert levels[3].segment_size_tokens == 2048
        assert levels[3].overlap_tokens == 100
        assert levels[3].top_k_subsegments == 2
        assert levels[3].scoring_method == "adaptive"
        assert levels[3].relevance_threshold == 0.8

    def test_custom_max_depth(self):
        """Test setting custom max_depth."""
        settings = RecursiveLLMSettings(max_depth=2)
        assert settings.max_depth == 2

    def test_max_depth_validation_min(self):
        """Test max_depth minimum validation (>= 1)."""
        with pytest.raises(ValidationError):
            RecursiveLLMSettings(max_depth=0)

    def test_max_depth_validation_max(self):
        """Test max_depth maximum validation (<= 5)."""
        with pytest.raises(ValidationError):
            RecursiveLLMSettings(max_depth=6)

    def test_max_depth_valid_range(self):
        """Test max_depth accepts all valid values 1-5."""
        for depth in range(1, 6):
            settings = RecursiveLLMSettings(max_depth=depth)
            assert settings.max_depth == depth

    def test_worker_limits_defaults(self):
        """Test worker_limits have sensible defaults."""
        settings = RecursiveLLMSettings()

        assert settings.worker_limits["ollama"] == 1  # Single-threaded
        assert settings.worker_limits["openai"] == 10  # High parallelism
        assert settings.worker_limits["alibaba"] == 5  # Moderate

    def test_max_parallel_workers_custom(self):
        """Test setting custom max_parallel_workers."""
        settings = RecursiveLLMSettings(max_parallel_workers=5)
        assert settings.max_parallel_workers == 5

    def test_custom_levels(self):
        """Test providing custom level configurations."""
        custom_levels = [
            RecursiveLevelConfig(
                level=0, segment_size_tokens=20000, scoring_method="dense+sparse"
            ),
            RecursiveLevelConfig(
                level=1, segment_size_tokens=10000, scoring_method="multi-vector"
            ),
        ]
        settings = RecursiveLLMSettings(
            max_depth=2,
            levels=custom_levels,
        )

        assert len(settings.levels) == 2
        assert settings.levels[0].segment_size_tokens == 20000
        assert settings.levels[1].segment_size_tokens == 10000

    def test_custom_worker_limits(self):
        """Test providing custom worker_limits."""
        custom_limits = {
            "ollama": 2,
            "openai": 20,
            "alibaba": 10,
            "custom": 15,
        }
        settings = RecursiveLLMSettings(worker_limits=custom_limits)

        assert settings.worker_limits["ollama"] == 2
        assert settings.worker_limits["openai"] == 20
        assert settings.worker_limits["custom"] == 15

    def test_levels_must_not_be_empty(self):
        """Test that at least one level is required.

        Note: Empty levels are allowed by Pydantic, but the processor
        validates this in __init__ and raises ValueError.
        """
        # Pydantic allows empty list by default, so we test processor validation
        invalid_settings = RecursiveLLMSettings(levels=[])
        assert len(invalid_settings.levels) == 0  # Empty list is created

        # But processor should reject it
        from src.agents.context.recursive_llm import RecursiveLLMProcessor
        with pytest.raises(ValueError):
            RecursiveLLMProcessor(
                llm=MagicMock(),
                skill_registry=MagicMock(),
                settings=invalid_settings,
            )

    def test_level_mismatch_warning_scenario(self):
        """Test scenario where max_depth > len(levels).

        This should be allowed (will reuse last level config), but is logged as warning.
        """
        settings = RecursiveLLMSettings(
            max_depth=5,  # Request 5 levels
            levels=[
                RecursiveLevelConfig(
                    level=0, segment_size_tokens=16384
                ),  # Only 1 level
            ],
        )

        # Should be allowed
        assert settings.max_depth == 5
        assert len(settings.levels) == 1

    def test_multiple_backends_worker_limits(self):
        """Test worker limits for different LLM backends."""
        settings = RecursiveLLMSettings()

        # Lower limits for resource-constrained backends
        assert settings.worker_limits["ollama"] <= settings.worker_limits["openai"]
        assert settings.worker_limits["alibaba"] <= settings.worker_limits["openai"]

    def test_serialization_to_dict(self):
        """Test RecursiveLLMSettings can be serialized to dict."""
        settings = RecursiveLLMSettings(max_depth=2)
        data = settings.model_dump()

        assert "max_depth" in data
        assert data["max_depth"] == 2
        assert "levels" in data
        assert isinstance(data["levels"], list)
        assert len(data["levels"]) > 0

    def test_json_serialization(self):
        """Test RecursiveLLMSettings can be serialized to JSON."""
        settings = RecursiveLLMSettings(max_depth=2)
        json_str = settings.model_dump_json()

        assert "max_depth" in json_str
        assert "dense+sparse" in json_str  # Check scoring method

    def test_level_lookups_by_index(self):
        """Test looking up level configuration by depth."""
        settings = RecursiveLLMSettings()

        # Test all default levels are accessible
        for i in range(len(settings.levels)):
            level_config = settings.levels[i]
            assert level_config.level == i
            assert level_config.segment_size_tokens > 0

    def test_segment_size_pyramid(self):
        """Test segment sizes form a decreasing pyramid (larger at top)."""
        settings = RecursiveLLMSettings()

        for i in range(len(settings.levels) - 1):
            current_size = settings.levels[i].segment_size_tokens
            next_size = settings.levels[i + 1].segment_size_tokens
            # Next level should be smaller or equal
            assert next_size <= current_size

    def test_threshold_pyramid(self):
        """Test thresholds form an increasing pyramid (stricter at bottom)."""
        settings = RecursiveLLMSettings()

        for i in range(len(settings.levels) - 1):
            current_threshold = settings.levels[i].relevance_threshold
            next_threshold = settings.levels[i + 1].relevance_threshold
            # Next level should have higher (stricter) threshold
            assert next_threshold >= current_threshold


class TestRecursiveLevelConfigIntegration:
    """Integration tests combining multiple config components."""

    def test_create_per_level_pyramid(self):
        """Test creating a complete per-level pyramid configuration."""
        levels = [
            RecursiveLevelConfig(
                level=0,
                segment_size_tokens=16384,
                overlap_tokens=400,
                scoring_method="dense+sparse",
                relevance_threshold=0.5,
            ),
            RecursiveLevelConfig(
                level=1,
                segment_size_tokens=8192,
                overlap_tokens=300,
                scoring_method="dense+sparse",
                relevance_threshold=0.6,
            ),
            RecursiveLevelConfig(
                level=2,
                segment_size_tokens=4096,
                overlap_tokens=200,
                scoring_method="multi-vector",
                relevance_threshold=0.7,
            ),
        ]

        settings = RecursiveLLMSettings(max_depth=3, levels=levels)

        assert len(settings.levels) == 3
        assert settings.levels[0].segment_size_tokens == 16384
        assert settings.levels[1].segment_size_tokens == 8192
        assert settings.levels[2].segment_size_tokens == 4096
        assert settings.levels[0].scoring_method == "dense+sparse"
        assert settings.levels[2].scoring_method == "multi-vector"

    def test_mixed_scoring_methods(self):
        """Test levels can have different scoring methods."""
        levels = [
            RecursiveLevelConfig(
                level=0, segment_size_tokens=16384, scoring_method="dense+sparse"
            ),
            RecursiveLevelConfig(
                level=1, segment_size_tokens=8192, scoring_method="multi-vector"
            ),
            RecursiveLevelConfig(
                level=2, segment_size_tokens=4096, scoring_method="llm"
            ),
            RecursiveLevelConfig(
                level=3, segment_size_tokens=2048, scoring_method="adaptive"
            ),
        ]

        settings = RecursiveLLMSettings(levels=levels)

        methods = [level.scoring_method for level in settings.levels]
        assert "dense+sparse" in methods
        assert "multi-vector" in methods
        assert "llm" in methods
        assert "adaptive" in methods

    def test_full_recursion_with_all_features(self):
        """Test full recursive LLM settings with all Sprint 92 features."""
        settings = RecursiveLLMSettings(
            max_depth=3,
            max_parallel_workers=10,
            worker_limits={
                "ollama": 1,
                "openai": 20,
                "alibaba": 5,
            },
            levels=[
                RecursiveLevelConfig(
                    level=0,
                    segment_size_tokens=16384,
                    overlap_tokens=400,
                    top_k_subsegments=5,
                    scoring_method="dense+sparse",
                    relevance_threshold=0.5,
                ),
                RecursiveLevelConfig(
                    level=1,
                    segment_size_tokens=8192,
                    overlap_tokens=300,
                    top_k_subsegments=4,
                    scoring_method="dense+sparse",
                    relevance_threshold=0.6,
                ),
                RecursiveLevelConfig(
                    level=2,
                    segment_size_tokens=4096,
                    overlap_tokens=200,
                    top_k_subsegments=3,
                    scoring_method="adaptive",
                    relevance_threshold=0.7,
                ),
            ],
        )

        # Verify all settings are present
        assert settings.max_depth == 3
        assert settings.max_parallel_workers == 10
        assert len(settings.levels) == 3
        assert settings.worker_limits["openai"] == 20

        # Verify level hierarchy
        for i in range(len(settings.levels) - 1):
            assert (
                settings.levels[i].segment_size_tokens
                > settings.levels[i + 1].segment_size_tokens
            )
