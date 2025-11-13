"""Test VLM Routing with AegisLLMProxy.

Sprint 23 - Feature 23.4: Multi-Cloud LLM Execution
Related ADR: ADR-033

This script tests:
1. Vision task routing to Alibaba Cloud Qwen3-VL-30B-A3B-Thinking
2. Fallback to local Ollama when cloud unavailable
3. ImageProcessor integration with AegisLLMProxy
4. Cost tracking for VLM calls
"""

import asyncio
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from src.components.llm_proxy import get_aegis_llm_proxy, LLMTask, TaskType
from src.components.ingestion.image_processor import (
    ImageProcessor,
    ImageProcessorConfig,
    generate_vlm_description_with_proxy,
)

logger = structlog.get_logger(__name__)


async def test_vision_task_routing():
    """Test 1: Vision task routes to Alibaba Cloud."""
    logger.info("=" * 80)
    logger.info("TEST 1: Vision Task Routing to Alibaba Cloud")
    logger.info("=" * 80)

    proxy = get_aegis_llm_proxy()

    # Create a vision task
    task = LLMTask(
        task_type=TaskType.VISION,
        prompt="Describe this test image.",
        data_classification="public",
        quality_requirement="high",
        complexity="medium",
    )

    # Test routing decision
    provider, reason = proxy._route_task(task)

    logger.info(
        "Routing Decision",
        provider=provider,
        reason=reason,
        expected_provider="alibaba_cloud",
    )

    assert provider == "alibaba_cloud", f"Expected alibaba_cloud, got {provider}"
    assert reason == "vision_task_best_vlm", f"Expected vision_task_best_vlm, got {reason}"

    logger.info("PASS: TEST 1 - Vision tasks route to Alibaba Cloud")
    return True


async def test_vision_fallback_to_local():
    """Test 2: Vision task falls back to local when cloud unavailable."""
    logger.info("=" * 80)
    logger.info("TEST 2: Fallback to Local Ollama (Cloud Unavailable)")
    logger.info("=" * 80)

    proxy = get_aegis_llm_proxy()

    # Temporarily disable Alibaba Cloud
    original_config = proxy.config.providers.get("alibaba_cloud", {})
    proxy.config.providers["alibaba_cloud"] = {}

    # Create a vision task
    task = LLMTask(
        task_type=TaskType.VISION,
        prompt="Describe this test image.",
    )

    # Test routing decision
    provider, reason = proxy._route_task(task)

    logger.info(
        "Routing Decision (Cloud Disabled)",
        provider=provider,
        reason=reason,
        expected_provider="local_ollama",
    )

    assert provider == "local_ollama", f"Expected local_ollama, got {provider}"
    assert reason == "vision_task_local_fallback", f"Expected vision_task_local_fallback, got {reason}"

    # Restore config
    proxy.config.providers["alibaba_cloud"] = original_config

    logger.info("PASS: TEST 2 - Vision tasks fallback to local when cloud unavailable")
    return True


async def test_vlm_description_with_test_image():
    """Test 3: Generate VLM description for a test image."""
    logger.info("=" * 80)
    logger.info("TEST 3: VLM Description Generation with Test Image")
    logger.info("=" * 80)

    # Create a simple test image (400x300 red square with text)
    img = Image.new("RGB", (400, 300), color="white")
    draw = ImageDraw.Draw(img)

    # Draw a red rectangle
    draw.rectangle([50, 50, 350, 250], fill="red", outline="black", width=3)

    # Add text
    try:
        # Try to use a system font
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        # Fallback to default font
        font = ImageFont.load_default()

    draw.text((100, 130), "Test Image", fill="white", font=font)

    # Save test image
    test_image_path = project_root / "scripts" / "test_vlm_image.png"
    img.save(test_image_path)

    logger.info("Test image created", path=str(test_image_path), size=img.size)

    try:
        # Test with proxy (cloud VLM)
        logger.info("Testing with AegisLLMProxy (cloud VLM preferred)...")
        description = await generate_vlm_description_with_proxy(
            image_path=test_image_path,
            prompt_template="Describe this test image in one sentence. What color is the rectangle and what text is visible?",
        )

        logger.info(
            "VLM Description Generated",
            description=description,
            length=len(description),
        )

        assert len(description) > 0, "Description should not be empty"
        logger.info("PASS: TEST 3 - VLM description generated successfully")
        return True

    finally:
        # Cleanup test image
        if test_image_path.exists():
            test_image_path.unlink()
            logger.info("Test image cleaned up", path=str(test_image_path))


async def test_image_processor_integration():
    """Test 4: ImageProcessor with proxy integration."""
    logger.info("=" * 80)
    logger.info("TEST 4: ImageProcessor Integration with AegisLLMProxy")
    logger.info("=" * 80)

    # Create a test image
    img = Image.new("RGB", (500, 500), color="blue")
    draw = ImageDraw.Draw(img)
    draw.text((200, 240), "ImageProcessor Test", fill="white")

    # Create processor
    config = ImageProcessorConfig()
    processor = ImageProcessor(config=config)

    try:
        # Process with proxy (default)
        logger.info("Processing image with proxy enabled...")
        description_proxy = processor.process_image(
            image=img,
            picture_index=0,
            skip_filtering=True,  # Skip size checks
            use_proxy=True,  # Use cloud VLM via proxy
        )

        logger.info(
            "Image Processed (Proxy)",
            description_length=len(description_proxy) if description_proxy else 0,
            used_proxy=True,
        )

        assert description_proxy is not None, "Description should not be None"
        assert len(description_proxy) > 0, "Description should not be empty"

        logger.info("PASS: TEST 4 - ImageProcessor integration successful")
        return True

    finally:
        processor.cleanup()


async def test_cost_tracking():
    """Test 5: Verify cost tracking for VLM calls."""
    logger.info("=" * 80)
    logger.info("TEST 5: Cost Tracking for VLM Calls")
    logger.info("=" * 80)

    proxy = get_aegis_llm_proxy()

    # Check initial spending
    initial_spending = proxy._monthly_spending.get("alibaba_cloud", 0.0)
    logger.info("Initial monthly spending", alibaba_cloud_usd=initial_spending)

    # Create and execute a vision task
    task = LLMTask(
        task_type=TaskType.VISION,
        prompt="Test cost tracking.",
        max_tokens=50,  # Small token count for testing
    )

    try:
        response = await proxy.generate(task)

        logger.info(
            "VLM Task Executed",
            provider=response.provider,
            model=response.model,
            tokens_used=response.tokens_used,
            cost_usd=response.cost_usd,
        )

        # Verify cost was tracked
        final_spending = proxy._monthly_spending.get("alibaba_cloud", 0.0)
        logger.info("Final monthly spending", alibaba_cloud_usd=final_spending)

        if response.provider == "alibaba_cloud":
            assert final_spending > initial_spending, "Cost should be tracked"
            logger.info(
                "Cost tracked correctly",
                cost_increase_usd=final_spending - initial_spending,
            )

        logger.info("PASS: TEST 5 - Cost tracking working correctly")
        return True

    except Exception as e:
        logger.warning("Cost tracking test failed (expected if cloud unavailable)", error=str(e))
        return False


async def main():
    """Run all VLM routing tests."""
    logger.info("Starting VLM Routing Tests...")
    logger.info("=" * 80)

    results = []

    # Test 1: Routing decision
    try:
        result = await test_vision_task_routing()
        results.append(("Vision Task Routing", result))
    except Exception as e:
        logger.error("Test 1 failed", error=str(e))
        results.append(("Vision Task Routing", False))

    # Test 2: Fallback to local
    try:
        result = await test_vision_fallback_to_local()
        results.append(("Fallback to Local", result))
    except Exception as e:
        logger.error("Test 2 failed", error=str(e))
        results.append(("Fallback to Local", False))

    # Test 3: VLM description generation
    try:
        result = await test_vlm_description_with_test_image()
        results.append(("VLM Description Generation", result))
    except Exception as e:
        logger.error("Test 3 failed", error=str(e))
        results.append(("VLM Description Generation", False))

    # Test 4: ImageProcessor integration
    try:
        result = await test_image_processor_integration()
        results.append(("ImageProcessor Integration", result))
    except Exception as e:
        logger.error("Test 4 failed", error=str(e))
        results.append(("ImageProcessor Integration", False))

    # Test 5: Cost tracking
    try:
        result = await test_cost_tracking()
        results.append(("Cost Tracking", result))
    except Exception as e:
        logger.error("Test 5 failed", error=str(e))
        results.append(("Cost Tracking", False))

    # Summary
    logger.info("=" * 80)
    logger.info("VLM ROUTING TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("ALL TESTS PASSED")
        return 0
    else:
        logger.error(f"SOME TESTS FAILED: {total - passed} failures")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
