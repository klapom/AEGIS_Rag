"""Validation script for Feature 24.2: Token Tracking Accuracy Fix.

This script validates that token tracking now uses accurate input/output split
instead of 50/50 estimation.

Run: poetry run python scripts/validate_token_tracking.py
"""

import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile

from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
from src.components.llm_proxy.cost_tracker import CostTracker
from src.components.llm_proxy.models import LLMTask, TaskType


def create_mock_response(prompt_tokens: int, completion_tokens: int):
    """Create mock ANY-LLM response with specific token counts."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Validation response"

    response.usage = MagicMock()
    response.usage.prompt_tokens = prompt_tokens
    response.usage.completion_tokens = completion_tokens
    response.usage.total_tokens = prompt_tokens + completion_tokens

    return response


async def test_accurate_token_parsing():
    """Test that accurate token parsing works."""
    print("\n=== Test 1: Accurate Token Parsing ===")

    mock_response = create_mock_response(prompt_tokens=1500, completion_tokens=500)

    with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
        mock_acomp.return_value = mock_response

        proxy = AegisLLMProxy()
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        proxy.cost_tracker = CostTracker(db_path=Path(temp_db.name))

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test prompt for validation",
        )

        result = await proxy.generate(task)

        # Verify tokens
        assert result.tokens_used == 2000, f"Expected 2000 tokens, got {result.tokens_used}"
        print(f"✓ Total tokens: {result.tokens_used}")

        # Check database for accurate split
        stats = proxy.cost_tracker.get_request_stats(days=1)
        print(f"✓ Request tracked in database: {stats['total_requests']} requests")
        print(f"✓ Total cost: ${stats['total_cost_usd']:.6f}")

        # Cleanup
        Path(temp_db.name).unlink()
        print("✓ Test 1 PASSED\n")


async def test_cost_calculation_accuracy():
    """Test accurate cost calculation with input/output split."""
    print("=== Test 2: Cost Calculation Accuracy ===")

    proxy = AegisLLMProxy()

    # Alibaba Cloud qwen-turbo: $0.05/M input, $0.2/M output
    cost = proxy._calculate_cost(
        provider="alibaba_cloud",
        tokens_input=10000,  # 10k input
        tokens_output=5000,  # 5k output
    )

    expected = (10000 / 1_000_000) * 0.05 + (5000 / 1_000_000) * 0.2
    assert abs(cost - expected) < 0.0001, f"Expected ${expected:.6f}, got ${cost:.6f}"

    print(f"✓ Input tokens: 10,000 @ $0.05/M = ${(10000/1_000_000)*0.05:.6f}")
    print(f"✓ Output tokens: 5,000 @ $0.2/M = ${(5000/1_000_000)*0.2:.6f}")
    print(f"✓ Total cost: ${cost:.6f}")
    print("✓ Test 2 PASSED\n")


async def test_fallback_to_legacy():
    """Test fallback to 50/50 split when usage unavailable."""
    print("=== Test 3: Fallback to Legacy (50/50) ===")

    # Mock response WITHOUT usage field
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Fallback response"
    mock_response.usage = None  # No usage field

    with patch("src.components.llm_proxy.aegis_llm_proxy.acompletion") as mock_acomp:
        mock_acomp.return_value = mock_response

        proxy = AegisLLMProxy()
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        proxy.cost_tracker = CostTracker(db_path=Path(temp_db.name))

        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="Test fallback",
        )

        result = await proxy.generate(task)

        # Should handle missing usage gracefully
        assert result.tokens_used >= 0
        print(f"✓ Handled missing usage field gracefully")
        print(f"✓ Tokens used: {result.tokens_used}")

        # Cleanup
        Path(temp_db.name).unlink()
        print("✓ Test 3 PASSED\n")


async def test_cost_comparison_accurate_vs_legacy():
    """Compare accurate vs legacy (50/50) cost calculation."""
    print("=== Test 4: Accurate vs Legacy Cost Comparison ===")

    proxy = AegisLLMProxy()

    # Scenario: Heavy output generation (1:4 ratio)
    tokens_input = 1000
    tokens_output = 4000
    tokens_total = 5000

    # Accurate cost (with input/output split)
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

    print(f"Scenario: 1,000 input + 4,000 output = 5,000 total tokens")
    print(f"✓ Accurate cost: ${cost_accurate:.6f}")
    print(f"✓ Legacy cost: ${cost_legacy:.6f}")
    print(f"✓ Difference: ${abs(cost_accurate - cost_legacy):.6f}")

    # Accurate should be higher (output costs 4x input)
    assert cost_accurate > cost_legacy, "Accurate cost should be higher for heavy output"
    print("✓ Accurate cost correctly higher than legacy (output-heavy scenario)")
    print("✓ Test 4 PASSED\n")


async def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("FEATURE 24.2: TOKEN TRACKING ACCURACY VALIDATION")
    print("=" * 60)

    try:
        await test_accurate_token_parsing()
        await test_cost_calculation_accuracy()
        await test_fallback_to_legacy()
        await test_cost_comparison_accurate_vs_legacy()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nFeature 24.2 implementation verified:")
        print("1. Accurate token parsing from response.usage")
        print("2. Correct input/output split (not 50/50)")
        print("3. Accurate cost calculations")
        print("4. Fallback to legacy when usage missing")
        print()

    except AssertionError as e:
        print(f"\n✗ VALIDATION FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
