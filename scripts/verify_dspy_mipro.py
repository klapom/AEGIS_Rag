#!/usr/bin/env python
"""Verification script for DSPy MIPROv2 integration.

Sprint 64 Feature 64.3: Real DSPy Domain Training with MIPROv2

This script verifies that the DSPy MIPROv2 optimizer is properly installed
and functional.

Usage:
    poetry run python scripts/verify_dspy_mipro.py

Requirements:
    - Ollama running on localhost:11434
    - qwen3:32b model available
    - DSPy installed: poetry install --with domain-training
"""

import asyncio
import sys
import time

import structlog

logger = structlog.get_logger(__name__)


async def verify_dspy_installation():
    """Verify DSPy is installed and importable."""
    print("\n[1/4] Checking DSPy installation...")

    try:
        import dspy

        print(f"✓ DSPy version {dspy.__version__} installed")
        return True
    except ImportError:
        print("✗ DSPy not installed")
        print("  Install with: poetry install --with domain-training")
        return False


async def verify_optimizer_initialization():
    """Verify DSPyOptimizer can be initialized."""
    print("\n[2/4] Initializing DSPyOptimizer...")

    try:
        from src.components.domain_training.dspy_optimizer import DSPyOptimizer

        optimizer = DSPyOptimizer(llm_model="qwen3:32b")

        if not optimizer._dspy_available:
            print("✗ DSPyOptimizer initialized but DSPy not available")
            return False

        print(f"✓ DSPyOptimizer initialized with {optimizer.llm_model}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False


async def verify_mipro_training():
    """Verify MIPROv2 training works with minimal dataset."""
    print("\n[3/4] Running MIPROv2 entity extraction training...")
    print("  (This will take 10-30 seconds...)")

    try:
        from src.components.domain_training.dspy_optimizer import DSPyOptimizer

        optimizer = DSPyOptimizer(llm_model="qwen3:32b")

        # Minimal training data (6 samples for train/val split)
        training_data = [
            {"text": "Python is a programming language.", "entities": ["Python"]},
            {"text": "FastAPI is a web framework.", "entities": ["FastAPI"]},
            {"text": "Docker containers run applications.", "entities": ["Docker"]},
            {"text": "PostgreSQL is a database.", "entities": ["PostgreSQL"]},
            {"text": "Kubernetes orchestrates containers.", "entities": ["Kubernetes"]},
            {"text": "Redis is a cache.", "entities": ["Redis"]},
        ]

        start_time = time.time()

        result = await optimizer.optimize_entity_extraction(training_data=training_data)

        duration = time.time() - start_time

        # Verify results
        if duration < 1.0:
            print(f"✗ Training too fast ({duration:.2f}s) - likely using mock results")
            return False

        f1_score = result["metrics"].get("val_f1", result["metrics"].get("f1", 0.0))

        print(f"✓ Training completed in {duration:.2f}s")
        print(f"  Entity F1: {f1_score:.3f}")
        print(f"  Demos extracted: {len(result['demos'])}")

        if f1_score < 0.3:
            print(f"  ⚠ Warning: F1 score {f1_score:.3f} is lower than expected")

        return True

    except Exception as e:
        print(f"✗ Training failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def verify_progress_tracking():
    """Verify progress callbacks work during training."""
    print("\n[4/4] Verifying progress tracking...")

    try:
        from src.components.domain_training.dspy_optimizer import DSPyOptimizer

        optimizer = DSPyOptimizer(llm_model="qwen3:32b")

        progress_calls = []

        def progress_callback(message: str, progress: float):
            progress_calls.append((message, progress))
            if len(progress_calls) % 3 == 1:  # Print every 3rd update
                print(f"  Progress: {progress:.1f}% - {message}")

        training_data = [
            {"text": f"Sample {i}", "entities": [f"Entity{i}"]} for i in range(1, 7)
        ]

        await optimizer.optimize_entity_extraction(
            training_data=training_data, progress_callback=progress_callback
        )

        if len(progress_calls) == 0:
            print("✗ Progress callback never called")
            return False

        print(f"✓ Progress tracking working ({len(progress_calls)} updates)")
        return True

    except Exception as e:
        print(f"✗ Progress tracking failed: {e}")
        return False


async def main():
    """Run all verification checks."""
    print("=" * 70)
    print("DSPy MIPROv2 Integration Verification")
    print("Sprint 64 Feature 64.3: Real DSPy Domain Training")
    print("=" * 70)

    results = []

    # Check 1: DSPy installation
    results.append(await verify_dspy_installation())
    if not results[-1]:
        print("\n❌ DSPy not installed - cannot proceed")
        return False

    # Check 2: Optimizer initialization
    results.append(await verify_optimizer_initialization())
    if not results[-1]:
        print("\n❌ Optimizer initialization failed - cannot proceed")
        return False

    # Check 3: MIPROv2 training (most important)
    results.append(await verify_mipro_training())

    # Check 4: Progress tracking
    results.append(await verify_progress_tracking())

    # Summary
    print("\n" + "=" * 70)
    print("Verification Summary")
    print("=" * 70)

    checks = [
        "DSPy Installation",
        "Optimizer Initialization",
        "MIPROv2 Training",
        "Progress Tracking",
    ]

    for check, result in zip(checks, results):
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {check}")

    all_passed = all(results)

    print("=" * 70)

    if all_passed:
        print("✅ All checks passed! MIPROv2 integration is working correctly.")
        return True
    else:
        print("❌ Some checks failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
