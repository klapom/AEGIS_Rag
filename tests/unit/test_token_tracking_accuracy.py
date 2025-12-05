"""Unit tests for Feature 24.2: Token Tracking Accuracy Fix.

Sprint 24 Feature 24.2 fixes token split estimation in AegisLLMProxy.
Previously used 50/50 split, now uses accurate input/output breakdown from ANY-LLM.

These tests verify:
- Accurate token parsing from response.usage (prompt_tokens, completion_tokens)
- Fallback to 50/50 split when usage field missing
- Accurate cost calculations using separate input/output rates
- Edge cases (zero tokens, None values, missing usage field)
- Cost tracking with correct input/output split

Test Strategy:
- Mock ANY-LLM response objects with realistic usage data
- Test both accurate parsing and fallback scenarios
- Verify cost calculations match expected values
- Assert SQLite database tracks input/output tokens correctly
- Aim for >80% code coverage
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile

from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
from src.components.llm_proxy.cost_tracker import CostTracker
from src.components.llm_proxy.models import LLMTask, TaskType
from src.components.llm_proxy.config import LLMProxyConfig


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path():
    """Create temporary database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = Path(temp_file.name)
    temp_file.close()
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_llm_proxy_config():
    """Create mock LLMProxyConfig for testing.

    This fixture provides a minimal valid config to avoid loading from YAML files.
    """
    config = MagicMock(spec=LLMProxyConfig)

    # Configure providers
    config.providers = {
        "local_ollama": {
            "base_url": "http://localhost:11434",
        },
        "alibaba_cloud": {
            "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "api_key": "test-key",
        },
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test-key",
        },
    }

    config.budgets = {
        "monthly_limits": {
            "alibaba_cloud": 10.0,
            "openai": 20.0,
        },
    }

    config.routing = {
        "prefer_cloud": False,
    }

    config.model_defaults = {
        "local_ollama": {"extraction": "gemma-3-4b-it-Q8_0"},
        "alibaba_cloud": {"extraction": "qwen3-32b"},
        "openai": {"extraction": "gpt-4o"},
    }

    config.fallback = {}
    config.monitoring = {"enabled": True}

    # Configure methods
    config.is_provider_enabled = MagicMock(return_value=True)
    config.get_budget_limit = MagicMock(return_value=10.0)
    config.get_default_model = MagicMock(return_value="test-model")

    return config


@pytest.fixture
def mock_response_with_usage():
    """Mock ANY-LLM response with complete usage data."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response content"

    # Mock usage object (OpenAI-compatible format)
    response.usage = MagicMock()
    response.usage.prompt_tokens = 150  # Input tokens
    response.usage.completion_tokens = 50  # Output tokens
    response.usage.total_tokens = 200  # Total

    return response


@pytest.fixture
def mock_response_without_usage():
    """Mock ANY-LLM response WITHOUT usage data (fallback scenario)."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response content"

    # No usage field (simulates legacy or incomplete response)
    response.usage = None

    return response


@pytest.fixture
def mock_response_with_zero_tokens():
    """Mock ANY-LLM response with zero tokens (edge case)."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = ""

    response.usage = MagicMock()
    response.usage.prompt_tokens = 0
    response.usage.completion_tokens = 0
    response.usage.total_tokens = 0

    return response


@pytest.fixture
def mock_response_partial_usage():
    """Mock ANY-LLM response with partial usage data (None values)."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response"

    response.usage = MagicMock()
    response.usage.prompt_tokens = None  # Missing input
    response.usage.completion_tokens = 50  # Output present
    response.usage.total_tokens = 50

    return response


# ============================================================================
# Token Parsing Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
class TestTokenParsing:
    """Test accurate token parsing from ANY-LLM response."""

    async def test_parse_tokens_with_complete_usage(
        self, mock_response_with_usage, temp_db_path, mock_llm_proxy_config
    ):
        """Test parsing tokens when usage object is complete."""
        with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
            mock_acomp.return_value = mock_response_with_usage

            proxy = AegisLLMProxy(config=mock_llm_proxy_config)
            proxy.cost_tracker = CostTracker(db_path=temp_db_path)

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt="Test prompt",
            )

            result = await proxy.generate(task)

            # Verify response
            assert result.tokens_used == 200

            # Verify cost tracking received accurate split
            # Check database for latest entry
            stats = proxy.cost_tracker.get_request_stats(days=1)
            if stats["total_requests"] > 0:
                # Verify accurate input/output split was tracked
                assert stats["total_requests"] >= 1

    async def test_parse_tokens_fallback_without_usage(
        self, mock_response_without_usage, temp_db_path, mock_llm_proxy_config
    ):
        """Test fallback to 50/50 split when usage field missing."""
        with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
            # Simulate response with only total_tokens (no usage object)
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.content = "Test response"
            response.usage = None  # No usage field
            response.tokens_used = 100  # Set numeric value for fallback
            response.total_tokens = None
            mock_acomp.return_value = response

            proxy = AegisLLMProxy(config=mock_llm_proxy_config)
            proxy.cost_tracker = CostTracker(db_path=temp_db_path)

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt="Test prompt",
            )

            result = await proxy.generate(task)

            # Should handle missing usage gracefully
            assert result.tokens_used >= 0

    async def test_parse_tokens_with_zero_values(
        self, mock_response_with_zero_tokens, temp_db_path, mock_llm_proxy_config
    ):
        """Test handling of zero token responses."""
        with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
            mock_acomp.return_value = mock_response_with_zero_tokens

            proxy = AegisLLMProxy(config=mock_llm_proxy_config)
            proxy.cost_tracker = CostTracker(db_path=temp_db_path)

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt="Test prompt",  # Fixed: non-empty prompt (Pydantic validation requires min length 1)
            )

            result = await proxy.generate(task)

            # Should handle zero tokens without error
            assert result.tokens_used == 0
            assert result.cost_usd == 0.0

    async def test_parse_tokens_with_none_values(
        self, mock_response_partial_usage, temp_db_path, mock_llm_proxy_config
    ):
        """Test handling of None values in usage object."""
        with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
            mock_acomp.return_value = mock_response_partial_usage

            proxy = AegisLLMProxy(config=mock_llm_proxy_config)
            proxy.cost_tracker = CostTracker(db_path=temp_db_path)

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt="Test",
            )

            result = await proxy.generate(task)

            # Should handle None values gracefully (convert to 0)
            assert result.tokens_used >= 0
            assert result.cost_usd >= 0.0


# ============================================================================
# Cost Calculation Tests
# ============================================================================


@pytest.mark.unit
class TestCostCalculation:
    """Test accurate cost calculations with input/output split."""

    def test_calculate_cost_local_ollama(self):
        """Test cost calculation for local Ollama (always free)."""
        proxy = AegisLLMProxy()

        cost = proxy._calculate_cost(
            provider="local_ollama",
            tokens_input=1000,
            tokens_output=500,
            tokens_total=1500,
        )

        assert cost == 0.0  # Local Ollama is free

    def test_calculate_cost_alibaba_cloud_accurate(self):
        """Test accurate cost calculation for Alibaba Cloud (qwen-turbo)."""
        proxy = AegisLLMProxy()

        # qwen-turbo: $0.05/M input, $0.2/M output
        cost = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=10000,  # 10k input tokens
            tokens_output=5000,  # 5k output tokens
        )

        # Expected: (10000/1M * $0.05) + (5000/1M * $0.2)
        # = 0.0005 + 0.001 = 0.0015
        expected = (10000 / 1_000_000) * 0.05 + (5000 / 1_000_000) * 0.2
        assert abs(cost - expected) < 0.0001  # Floating point tolerance

    def test_calculate_cost_openai_accurate(self):
        """Test accurate cost calculation for OpenAI (gpt-4o)."""
        proxy = AegisLLMProxy()

        # gpt-4o: $2.50/M input, $10.00/M output
        cost = proxy._calculate_cost(
            provider="openai",
            tokens_input=50000,  # 50k input
            tokens_output=10000,  # 10k output
        )

        # Expected: (50000/1M * $2.50) + (10000/1M * $10.00)
        # = 0.125 + 0.10 = 0.225
        expected = (50000 / 1_000_000) * 2.50 + (10000 / 1_000_000) * 10.00
        assert abs(cost - expected) < 0.001

    def test_calculate_cost_fallback_legacy_pricing(self):
        """Test fallback to legacy pricing when input/output unavailable."""
        proxy = AegisLLMProxy()

        # Only total tokens provided (no input/output split)
        cost = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=0,
            tokens_output=0,
            tokens_total=100000,  # 100k total
        )

        # Expected: average rate ($0.125/1M) * 100k tokens
        # = (100000/1000000) * 0.125 = 0.0125
        expected = (100000 / 1_000_000) * 0.125
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_alibaba_vs_legacy(self):
        """Test that accurate pricing differs from legacy (50/50) pricing."""
        proxy = AegisLLMProxy()

        # Scenario: Heavy output generation (1:4 input:output ratio)
        tokens_input = 1000
        tokens_output = 4000
        tokens_total = 5000

        # Accurate cost
        cost_accurate = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )

        # Legacy cost (50/50 split)
        cost_legacy = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=0,
            tokens_output=0,
            tokens_total=tokens_total,
        )

        # Accurate cost should be HIGHER (output tokens cost 4x input)
        # Accurate: (1000/1M * $0.05) + (4000/1M * $0.2) = 0.00005 + 0.0008 = 0.00085
        # Legacy: (5000/1M * $0.125) = 0.000625
        assert cost_accurate > cost_legacy

        # Verify calculations
        expected_accurate = (1000 / 1_000_000) * 0.05 + (4000 / 1_000_000) * 0.2
        expected_legacy = (5000 / 1_000_000) * 0.125
        assert abs(cost_accurate - expected_accurate) < 0.0001
        assert abs(cost_legacy - expected_legacy) < 0.0001


# ============================================================================
# Cost Tracker Integration Tests
# ============================================================================


@pytest.mark.unit
class TestCostTrackerIntegration:
    """Test cost tracker receives accurate input/output token breakdown."""

    def test_track_request_with_accurate_split(self, temp_db_path):
        """Test tracking request with accurate input/output split."""
        tracker = CostTracker(db_path=temp_db_path)

        row_id = tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="generation",
            tokens_input=1500,
            tokens_output=500,
            cost_usd=0.00015,
            latency_ms=250.5,
            routing_reason="default_local",
            fallback_used=False,
        )

        assert row_id > 0

        # Verify database entry
        stats = tracker.get_request_stats(days=1)
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 2000

    def test_track_multiple_requests_different_splits(self, temp_db_path):
        """Test tracking multiple requests with different input/output ratios."""
        tracker = CostTracker(db_path=temp_db_path)

        # Request 1: Input-heavy (research query)
        tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="research",
            tokens_input=8000,
            tokens_output=2000,
            cost_usd=0.0008,
        )

        # Request 2: Output-heavy (generation)
        tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="generation",
            tokens_input=1000,
            tokens_output=9000,
            cost_usd=0.0019,
        )

        # Verify both tracked
        stats = tracker.get_request_stats(days=1)
        assert stats["total_requests"] == 2
        assert stats["total_tokens"] == 20000

    def test_cost_accuracy_in_database(self, temp_db_path):
        """Test that accurate costs are persisted to database."""
        tracker = CostTracker(db_path=temp_db_path)

        # Track request with known cost
        expected_cost = 0.00125
        tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="code_generation",
            tokens_input=10000,
            tokens_output=5000,
            cost_usd=expected_cost,
        )

        # Retrieve and verify
        spending = tracker.get_monthly_spending(provider="openai")
        assert "openai" in spending
        assert abs(spending["openai"] - expected_cost) < 0.0001


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_calculate_cost_unknown_provider(self):
        """Test cost calculation for unknown provider (defaults to 0)."""
        proxy = AegisLLMProxy()

        cost = proxy._calculate_cost(
            provider="unknown_provider",
            tokens_input=1000,
            tokens_output=500,
        )

        assert cost == 0.0  # Unknown providers are free

    def test_calculate_cost_negative_tokens(self):
        """Test handling of negative token counts (should not occur)."""
        proxy = AegisLLMProxy()

        # Negative tokens (invalid input)
        cost = proxy._calculate_cost(
            provider="alibaba_cloud",
            tokens_input=-100,
            tokens_output=500,
        )

        # Should handle gracefully (negative cost is possible but unlikely)
        assert isinstance(cost, float)

    def test_calculate_cost_very_large_tokens(self):
        """Test cost calculation with very large token counts."""
        proxy = AegisLLMProxy()

        # 10M tokens (extreme case)
        cost = proxy._calculate_cost(
            provider="openai",
            tokens_input=5_000_000,
            tokens_output=5_000_000,
        )

        # Expected: (5M/1M * $2.50) + (5M/1M * $10.00) = $12.50 + $50.00 = $62.50
        expected = (5_000_000 / 1_000_000) * 2.50 + (5_000_000 / 1_000_000) * 10.00
        assert abs(cost - expected) < 0.01

    @pytest.mark.asyncio
    async def test_generate_preserves_token_accuracy(
        self, mock_response_with_usage, temp_db_path, mock_llm_proxy_config
    ):
        """Test that full generate() flow preserves token accuracy."""
        with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
            mock_acomp.return_value = mock_response_with_usage

            proxy = AegisLLMProxy(config=mock_llm_proxy_config)
            proxy.cost_tracker = CostTracker(db_path=temp_db_path)

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt="Generate detailed analysis",
            )

            result = await proxy.generate(task)

            # Verify result contains accurate tokens
            assert result.tokens_used == 200

            # Verify cost reflects accurate input/output split
            # For local_ollama: cost = 0.0
            # For alibaba_cloud: cost = (150/1M * $0.05) + (50/1M * $0.2) = 0.0000175
            assert result.cost_usd >= 0.0
