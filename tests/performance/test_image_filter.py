"""Test image filter functions - Sprint 33."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PIL import Image

from src.components.ingestion.image_processor import count_unique_colors, should_process_image


def test_filters():
    """Test all image filter conditions."""
    print("=" * 60)
    print("IMAGE FILTER TESTS - Sprint 33")
    print("=" * 60)

    # Test 1: Single color image (should be filtered)
    print("\n1. Single color image:")
    solid = Image.new("RGB", (300, 300), color="red")
    colors = count_unique_colors(solid)
    should, reason = should_process_image(solid)
    print(f"   {colors} unique colors -> {reason}")
    assert not should, "Single color should be filtered"
    print("   PASS: Filtered correctly")

    # Test 2: Small image (should be filtered)
    print("\n2. Small image (50x50):")
    small = Image.new("RGB", (50, 50), color="blue")
    should, reason = should_process_image(small)
    print(f"   -> {reason}")
    assert not should, "Small image should be filtered"
    print("   PASS: Filtered correctly")

    # Test 3: Wide aspect ratio (should be filtered)
    print("\n3. Wide image (1000x100, ratio 10:1):")
    wide = Image.new("RGB", (1000, 100), color="green")
    should, reason = should_process_image(wide)
    print(f"   -> {reason}")
    assert not should, "Wide image should be filtered"
    print("   PASS: Filtered correctly")

    # Test 4: Narrow aspect ratio (should be filtered)
    print("\n4. Narrow image (100x1000, ratio 0.1:1):")
    narrow = Image.new("RGB", (100, 1000), color="green")
    should, reason = should_process_image(narrow)
    print(f"   -> {reason}")
    assert not should, "Narrow image should be filtered"
    print("   PASS: Filtered correctly")

    # Test 5: Good image with gradient (should pass)
    print("\n5. Good image (300x300, gradient with many colors):")
    good = Image.new("RGB", (300, 300))
    pixels = []
    for y in range(300):
        for x in range(300):
            # Create gradient with many unique colors
            r = x % 256
            g = y % 256
            b = (x + y) % 256
            pixels.append((r, g, b))
    good.putdata(pixels)
    colors = count_unique_colors(good)
    should, reason = should_process_image(good)
    print(f"   {colors} unique colors -> {reason}")
    assert should, f"Good gradient image should pass, got: {reason}"
    print("   PASS: Accepted correctly")

    # Summary
    print("\n" + "=" * 60)
    print("ALL FILTER TESTS PASSED!")
    print("=" * 60)

    # Show filter defaults
    print("\nDefault filter values (Sprint 33 optimized):")
    print("  - min_size: 200px (was 100px)")
    print("  - min_aspect_ratio: 0.2 (was 0.1)")
    print("  - max_aspect_ratio: 5.0 (was 10.0)")
    print("  - min_unique_colors: 16 (NEW)")


if __name__ == "__main__":
    test_filters()
