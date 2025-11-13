"""Test DashScope VLM with Cost Tracking and Model Fallback.

Sprint 23 - Feature 23.4: Multi-Cloud LLM Execution
Tests:
1. VLM with qwen3-vl-30b-a3b-instruct (primary model)
2. VLM with qwen3-vl-30b-a3b-thinking (fallback model)
3. Automatic fallback on 403 errors
4. Cost tracking in SQLite database
5. High-resolution image processing
"""

import asyncio
import sys
from pathlib import Path
from PIL import Image, ImageDraw

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from src.components.llm_proxy.dashscope_vlm import get_dashscope_vlm_client
from src.components.llm_proxy.cost_tracker import CostTracker

logger = structlog.get_logger(__name__)


async def test_dashscope_vlm_instruct():
    """Test 1: DashScope VLM with instruct model (primary)."""
    logger.info("=" * 80)
    logger.info("TEST 1: DashScope VLM - Instruct Model (Primary)")
    logger.info("=" * 80)

    # Create test image
    img = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 250], fill="blue", outline="black", width=3)
    draw.text((150, 130), "Test Document", fill="white")

    test_image_path = project_root / "scripts" / "test_dashscope_image.png"
    img.save(test_image_path)
    logger.info("Test image created", path=str(test_image_path))

    try:
        client = await get_dashscope_vlm_client()

        description, metadata = await client.generate_image_description(
            image_path=test_image_path,
            prompt="Describe this image in one sentence. What color is the rectangle?",
            model="qwen3-vl-30b-a3b-instruct",
            enable_thinking=False,
            vl_high_resolution_images=True,
        )

        logger.info(
            "VLM Description Generated (Instruct)",
            model=metadata["model"],
            tokens_input=metadata["tokens_input"],
            tokens_output=metadata["tokens_output"],
            tokens_total=metadata["tokens_total"],
            description=description[:200],
        )

        await client.close()

        # Calculate cost (Alibaba Cloud pricing)
        cost_per_1k_tokens = 0.001
        cost_usd = (metadata["tokens_total"] / 1000) * cost_per_1k_tokens

        logger.info("Cost calculation", tokens=metadata["tokens_total"], cost_usd=f"${cost_usd:.6f}")

        assert len(description) > 0, "Description should not be empty"
        logger.info("PASS: TEST 1 - Instruct model working")

        return True, metadata, cost_usd

    finally:
        if test_image_path.exists():
            test_image_path.unlink()
            logger.info("Test image cleaned up")


async def test_dashscope_vlm_thinking():
    """Test 2: DashScope VLM with thinking model (fallback)."""
    logger.info("=" * 80)
    logger.info("TEST 2: DashScope VLM - Thinking Model (Fallback)")
    logger.info("=" * 80)

    # Create test image
    img = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 250], fill="green", outline="black", width=3)
    draw.text((150, 130), "Thinking Test", fill="white")

    test_image_path = project_root / "scripts" / "test_thinking_image.png"
    img.save(test_image_path)

    try:
        client = await get_dashscope_vlm_client()

        description, metadata = await client.generate_image_description(
            image_path=test_image_path,
            prompt="Describe this image carefully. What color is the rectangle?",
            model="qwen3-vl-30b-a3b-thinking",
            enable_thinking=True,  # Enable thinking mode
            vl_high_resolution_images=True,
        )

        logger.info(
            "VLM Description Generated (Thinking)",
            model=metadata["model"],
            tokens_total=metadata["tokens_total"],
            description_length=len(description),
        )

        await client.close()

        cost_per_1k_tokens = 0.001
        cost_usd = (metadata["tokens_total"] / 1000) * cost_per_1k_tokens

        assert len(description) > 0, "Description should not be empty"
        logger.info("PASS: TEST 2 - Thinking model working")

        return True, metadata, cost_usd

    finally:
        if test_image_path.exists():
            test_image_path.unlink()


async def test_automatic_fallback():
    """Test 3: Automatic fallback from instruct to thinking on 403."""
    logger.info("=" * 80)
    logger.info("TEST 3: Automatic Fallback (Instruct → Thinking)")
    logger.info("=" * 80)

    # Create test image
    img = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 250], fill="red", outline="black", width=3)
    draw.text((150, 130), "Fallback Test", fill="white")

    test_image_path = project_root / "scripts" / "test_fallback_image.png"
    img.save(test_image_path)

    try:
        client = await get_dashscope_vlm_client()

        description, metadata = await client.generate_with_fallback(
            image_path=test_image_path,
            prompt="What color is the rectangle in this image?",
            primary_model="qwen3-vl-30b-a3b-instruct",
            fallback_model="qwen3-vl-30b-a3b-thinking",
            vl_high_resolution_images=True,
        )

        logger.info(
            "Fallback Test Result",
            model=metadata["model"],
            fallback_used=metadata.get("fallback_used", False),
            tokens_total=metadata["tokens_total"],
        )

        await client.close()

        cost_per_1k_tokens = 0.001
        cost_usd = (metadata["tokens_total"] / 1000) * cost_per_1k_tokens

        assert len(description) > 0, "Description should not be empty"

        if metadata.get("fallback_used"):
            logger.info("PASS: TEST 3 - Fallback mechanism triggered successfully")
        else:
            logger.info("PASS: TEST 3 - Primary model worked (no fallback needed)")

        return True, metadata, cost_usd

    finally:
        if test_image_path.exists():
            test_image_path.unlink()


async def test_cost_tracking():
    """Test 4: Cost tracking in SQLite database."""
    logger.info("=" * 80)
    logger.info("TEST 4: SQLite Cost Tracking")
    logger.info("=" * 80)

    # Initialize cost tracker
    cost_tracker = CostTracker()

    # Get current spending
    initial_spending = cost_tracker.get_monthly_spending()
    logger.info("Initial monthly spending", spending=initial_spending)

    # Track a fake VLM request
    cost_tracker.track_request(
        provider="alibaba_cloud",
        model="qwen3-vl-30b-a3b-instruct",
        task_type="vision",
        tokens_input=500,
        tokens_output=1000,
        cost_usd=0.0015,
        latency_ms=3500.0,
        routing_reason="vision_task_best_vlm",
        fallback_used=False,
        task_id="test-cost-tracking-001",
    )

    # Get updated spending
    final_spending = cost_tracker.get_monthly_spending()
    logger.info("Final monthly spending", spending=final_spending)

    # Verify cost was tracked
    alibaba_initial = initial_spending.get("alibaba_cloud", 0.0)
    alibaba_final = final_spending.get("alibaba_cloud", 0.0)

    assert alibaba_final > alibaba_initial, "Cost should be tracked"

    logger.info(
        "Cost tracked successfully",
        increase_usd=alibaba_final - alibaba_initial,
    )

    # Get statistics
    stats = cost_tracker.get_request_stats(days=1)
    logger.info("Request statistics (last 24h)", total_requests=stats["total_requests"])

    logger.info("PASS: TEST 4 - Cost tracking working")
    return True


async def main():
    """Run all DashScope VLM tests."""
    logger.info("Starting DashScope VLM Tests...")
    logger.info("=" * 80)

    results = []
    total_cost = 0.0

    # Test 1: Instruct model
    try:
        success, metadata, cost = await test_dashscope_vlm_instruct()
        results.append(("Instruct Model", success))
        total_cost += cost
    except Exception as e:
        logger.error("Test 1 failed", error=str(e), error_type=type(e).__name__)
        results.append(("Instruct Model", False))

    # Test 2: Thinking model
    try:
        success, metadata, cost = await test_dashscope_vlm_thinking()
        results.append(("Thinking Model", success))
        total_cost += cost
    except Exception as e:
        logger.error("Test 2 failed", error=str(e), error_type=type(e).__name__)
        results.append(("Thinking Model", False))

    # Test 3: Automatic fallback
    try:
        success, metadata, cost = await test_automatic_fallback()
        results.append(("Automatic Fallback", success))
        total_cost += cost
    except Exception as e:
        logger.error("Test 3 failed", error=str(e), error_type=type(e).__name__)
        results.append(("Automatic Fallback", False))

    # Test 4: Cost tracking
    try:
        success = await test_cost_tracking()
        results.append(("Cost Tracking", success))
    except Exception as e:
        logger.error("Test 4 failed", error=str(e), error_type=type(e).__name__)
        results.append(("Cost Tracking", False))

    # Summary
    logger.info("=" * 80)
    logger.info("DASHSCOPE VLM TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")
    logger.info(f"Total API cost: ${total_cost:.6f}")

    if passed == total:
        logger.info("ALL TESTS PASSED")
        return 0
    else:
        logger.error(f"SOME TESTS FAILED: {total - passed} failures")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
