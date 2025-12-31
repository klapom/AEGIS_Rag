#!/usr/bin/env python3
"""Test C-LARA intent data generator with Qwen2.5:7b.

Sprint 67 Feature 67.10: Quick validation that the data generator works.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adaptation.intent_data_generator import CLARADataGenerator


async def main():
    """Test data generator with small sample."""
    print("=== C-LARA Intent Data Generator Test ===\n")

    # Create generator
    generator = CLARADataGenerator(
        model="qwen2.5:7b",
        target_examples=20,  # Small test sample
        examples_per_batch=5,
    )

    try:
        print("Generating 20 test examples (4 per intent class)...\n")

        # Generate examples
        examples = await generator.generate_examples()

        print(f"\nGenerated {len(examples)} examples")
        print(f"Stats: {dict(generator.stats)}\n")

        # Show sample examples
        print("=== Sample Examples ===")
        for i, example in enumerate(examples[:10]):
            print(
                f"{i+1}. [{example.intent}] ({example.language}) "
                f"{example.query[:80]}... (conf: {example.confidence:.2f})"
            )

        # Validate dataset
        print("\n=== Validation Report ===")
        validation = generator.validate_dataset(examples)
        print(json.dumps(validation, indent=2))

        # Save to test file
        output_path = Path("data/test_intent_data.jsonl")
        await generator.save_dataset(examples, output_path)
        print(f"\nTest dataset saved to: {output_path}")

        if validation["valid"]:
            print("\n✅ SUCCESS: Data generation working correctly!")
            return 0
        else:
            print("\n⚠️  WARNING: Validation issues detected (see above)")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2

    finally:
        await generator.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
