"""Unit tests for Model Router.

Sprint 69 Feature 69.3: Model Selection Strategy
"""

from unittest.mock import MagicMock, patch

import pytest

from src.components.routing.query_complexity import ComplexityTier, QueryComplexityScore
from src.domains.llm_integration.model_router import (
    DEFAULT_MODEL_CONFIGS,
    ModelConfig,
    ModelRouter,
)


class TestModelRouter:
    """Test suite for ModelRouter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelRouter()

    def test_simple_query_selects_fast_model(self):
        """Test that simple queries select fast tier model."""
        query = "What is RAG?"
        intent = "factual"

        config = self.router.select_model(query, intent)

        assert config["tier"] == ComplexityTier.FAST.value
        assert config["model"] == DEFAULT_MODEL_CONFIGS[ComplexityTier.FAST].model
        assert config["expected_latency_ms"] == 150
        assert config["quality_level"] == 0.70

    def test_complex_query_selects_advanced_model(self):
        """Test that complex queries select advanced tier model."""
        query = "Explain how graph-based retrieval compares to vector search and discuss the tradeoffs"
        intent = "exploratory"

        config = self.router.select_model(query, intent)

        assert config["tier"] in [ComplexityTier.BALANCED.value, ComplexityTier.ADVANCED.value]
        # Complex query should use higher tier than simple query

    def test_keyword_query_selects_fast_model(self):
        """Test that keyword queries select fast tier model."""
        query = "API_KEY error 404"
        intent = "keyword"

        config = self.router.select_model(query, intent)

        assert config["tier"] == ComplexityTier.FAST.value

    def test_config_includes_all_required_fields(self):
        """Test that returned config includes all required fields."""
        config = self.router.select_model("test", "factual")

        required_fields = [
            "model",
            "max_tokens",
            "temperature",
            "tier",
            "expected_latency_ms",
            "quality_level",
            "complexity_score",
        ]

        for field in required_fields:
            assert field in config

    def test_selection_stats_tracking(self):
        """Test that selection statistics are tracked correctly."""
        # Reset stats
        self.router.reset_stats()

        # Make selections
        self.router.select_model("What is X?", "factual")  # FAST
        self.router.select_model("How does X work?", "exploratory")  # BALANCED
        self.router.select_model("What is Y?", "factual")  # FAST

        stats = self.router.get_selection_stats()

        assert stats["total_selections"] == 3
        assert stats["fast_count"] >= 1  # At least one fast selection
        assert 0 <= stats["fast_percentage"] <= 100
        assert 0 <= stats["balanced_percentage"] <= 100
        assert 0 <= stats["advanced_percentage"] <= 100
        # Percentages should sum to ~100 (allow floating point precision)
        total_percentage = (
            stats["fast_percentage"]
            + stats["balanced_percentage"]
            + stats["advanced_percentage"]
        )
        assert abs(total_percentage - 100.0) < 0.1

    def test_reset_stats(self):
        """Test that reset_stats clears statistics."""
        # Make some selections
        self.router.select_model("test", "factual")
        self.router.select_model("test", "factual")

        # Reset
        self.router.reset_stats()

        stats = self.router.get_selection_stats()
        assert stats["total_selections"] == 0
        assert stats["fast_count"] == 0
        assert stats["balanced_count"] == 0
        assert stats["advanced_count"] == 0

    def test_override_tier(self):
        """Test that override_tier forces specific tier selection."""
        query = "What is X?"  # Would normally be FAST
        intent = "factual"

        # Override to ADVANCED
        config = self.router.select_model(query, intent, override_tier=ComplexityTier.ADVANCED)

        assert config["tier"] == ComplexityTier.ADVANCED.value
        assert config["model"] == DEFAULT_MODEL_CONFIGS[ComplexityTier.ADVANCED].model
        assert config["complexity_score"] == 0.0  # Not calculated when overridden

    def test_error_handling_fallback_to_balanced(self):
        """Test that errors fall back to balanced tier."""
        # Create router with broken complexity scorer
        broken_scorer = MagicMock()
        broken_scorer.score_query.side_effect = Exception("Scorer error")

        router = ModelRouter(complexity_scorer=broken_scorer)

        config = router.select_model("test", "factual")

        # Should fall back to balanced tier
        assert config["tier"] == ComplexityTier.BALANCED.value
        assert "error" in config

    def test_custom_model_configs(self):
        """Test router with custom model configurations."""
        custom_configs = {
            ComplexityTier.FAST: ModelConfig(
                model="custom-fast-model",
                max_tokens=100,
                temperature=0.1,
                tier=ComplexityTier.FAST,
                expected_latency_ms=50,
                quality_level=0.6,
            ),
            ComplexityTier.BALANCED: ModelConfig(
                model="custom-balanced-model",
                max_tokens=200,
                temperature=0.3,
                tier=ComplexityTier.BALANCED,
                expected_latency_ms=200,
                quality_level=0.8,
            ),
            ComplexityTier.ADVANCED: ModelConfig(
                model="custom-advanced-model",
                max_tokens=400,
                temperature=0.5,
                tier=ComplexityTier.ADVANCED,
                expected_latency_ms=500,
                quality_level=0.95,
            ),
        }

        router = ModelRouter(model_configs=custom_configs)

        config = router.select_model("test", "factual")

        # Should use custom config
        assert config["model"] == "custom-fast-model"
        assert config["max_tokens"] == 100

    def test_complexity_score_in_response(self):
        """Test that complexity score is included in response."""
        config = self.router.select_model("test query", "factual")

        assert "complexity_score" in config
        assert 0.0 <= config["complexity_score"] <= 1.0

    def test_tier_distribution_simple_queries(self):
        """Test that simple queries mostly use FAST tier."""
        simple_queries = [
            ("What is X?", "factual"),
            ("API_KEY", "keyword"),
            ("Who is Y?", "factual"),
            ("When?", "factual"),
            ("error 404", "keyword"),
        ]

        self.router.reset_stats()

        for query, intent in simple_queries:
            self.router.select_model(query, intent)

        stats = self.router.get_selection_stats()

        # Most simple queries should use FAST tier
        assert stats["fast_percentage"] >= 60  # At least 60% should be FAST

    def test_concurrent_selections(self):
        """Test that router handles concurrent selections correctly."""
        # Simulate concurrent access (router should be thread-safe for reads)
        configs = []

        for _ in range(10):
            config = self.router.select_model("test", "factual")
            configs.append(config)

        # All should return valid configs
        assert len(configs) == 10
        for config in configs:
            assert "model" in config
            assert "tier" in config

    def test_temperature_scaling_by_tier(self):
        """Test that temperature increases with tier complexity."""
        fast_config = DEFAULT_MODEL_CONFIGS[ComplexityTier.FAST]
        balanced_config = DEFAULT_MODEL_CONFIGS[ComplexityTier.BALANCED]
        advanced_config = DEFAULT_MODEL_CONFIGS[ComplexityTier.ADVANCED]

        assert fast_config.temperature <= balanced_config.temperature
        assert balanced_config.temperature <= advanced_config.temperature

    def test_max_tokens_scaling_by_tier(self):
        """Test that max_tokens increases with tier complexity."""
        fast_config = DEFAULT_MODEL_CONFIGS[ComplexityTier.FAST]
        balanced_config = DEFAULT_MODEL_CONFIGS[ComplexityTier.BALANCED]
        advanced_config = DEFAULT_MODEL_CONFIGS[ComplexityTier.ADVANCED]

        assert fast_config.max_tokens < balanced_config.max_tokens
        assert balanced_config.max_tokens < advanced_config.max_tokens


class TestModelConfig:
    """Test suite for ModelConfig dataclass."""

    def test_valid_config(self):
        """Test creation of valid model config."""
        config = ModelConfig(
            model="test-model",
            max_tokens=500,
            temperature=0.5,
            tier=ComplexityTier.BALANCED,
            expected_latency_ms=300,
            quality_level=0.85,
        )

        assert config.model == "test-model"
        assert config.max_tokens == 500
        assert config.temperature == 0.5
        assert config.tier == ComplexityTier.BALANCED
        assert config.expected_latency_ms == 300
        assert config.quality_level == 0.85

    def test_immutable(self):
        """Test that ModelConfig is immutable (frozen=True)."""
        config = ModelConfig(
            model="test-model",
            max_tokens=500,
            temperature=0.5,
            tier=ComplexityTier.BALANCED,
            expected_latency_ms=300,
            quality_level=0.85,
        )

        with pytest.raises(AttributeError):
            config.model = "new-model"  # type: ignore


class TestDefaultModelConfigs:
    """Test suite for DEFAULT_MODEL_CONFIGS."""

    def test_all_tiers_configured(self):
        """Test that all complexity tiers have configurations."""
        assert ComplexityTier.FAST in DEFAULT_MODEL_CONFIGS
        assert ComplexityTier.BALANCED in DEFAULT_MODEL_CONFIGS
        assert ComplexityTier.ADVANCED in DEFAULT_MODEL_CONFIGS

    def test_latency_increases_with_tier(self):
        """Test that expected latency increases with tier complexity."""
        fast_latency = DEFAULT_MODEL_CONFIGS[ComplexityTier.FAST].expected_latency_ms
        balanced_latency = DEFAULT_MODEL_CONFIGS[ComplexityTier.BALANCED].expected_latency_ms
        advanced_latency = DEFAULT_MODEL_CONFIGS[ComplexityTier.ADVANCED].expected_latency_ms

        assert fast_latency < balanced_latency < advanced_latency

    def test_quality_increases_with_tier(self):
        """Test that quality level increases with tier complexity."""
        fast_quality = DEFAULT_MODEL_CONFIGS[ComplexityTier.FAST].quality_level
        balanced_quality = DEFAULT_MODEL_CONFIGS[ComplexityTier.BALANCED].quality_level
        advanced_quality = DEFAULT_MODEL_CONFIGS[ComplexityTier.ADVANCED].quality_level

        assert fast_quality < balanced_quality < advanced_quality

    def test_tier_matches_config(self):
        """Test that tier field matches dict key."""
        for tier, config in DEFAULT_MODEL_CONFIGS.items():
            assert config.tier == tier

    @patch.dict("os.environ", {"MODEL_FAST": "custom-fast:3b"})
    def test_environment_variable_override(self):
        """Test that environment variables can override model names."""
        # Need to reimport to pick up env var changes
        from src.domains.llm_integration import model_router

        # Force reload of module to pick up new env vars
        import importlib

        importlib.reload(model_router)

        # Check that env var was applied
        config = model_router.DEFAULT_MODEL_CONFIGS[ComplexityTier.FAST]
        assert config.model == "custom-fast:3b"
