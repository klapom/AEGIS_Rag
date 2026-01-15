"""Synthesis Bundle Example - Sprint 95.3.

Demonstrates usage of the synthesis_bundle for content generation workflows.

The synthesis bundle combines:
- summarize: Multi-document summarization
- citation: Citation management
- format: Content formatting
- markdown_export: Export to markdown

Use cases:
- Literature reviews
- Report generation
- Executive summaries
- Documentation compilation
"""

import asyncio

from src.agents.skills.bundle_installer import get_bundle_status, install_bundle


async def main():
    """Demonstrate synthesis bundle usage."""

    print("=" * 80)
    print("Synthesis Bundle Example - Sprint 95.3")
    print("=" * 80)

    # 1. Install bundle
    print("\n1. Installing Synthesis Bundle...")
    report = install_bundle("synthesis_bundle")

    if report.success:
        print(f"   ✓ {report.summary}")
    else:
        print(f"   ✗ {report.summary}")
        return

    # 2. Simulate synthesis workflow
    print("\n2. Example Synthesis Workflow:")
    print("   Task: Generate literature review from 5 research papers")
    print()

    # Step 1: Summarization
    print("   Step 1: Multi-Document Summarization")
    print("   → Summarizing 5 papers...")
    print("   Input:")
    print("     - Paper 1: Quantum Error Correction (15 pages)")
    print("     - Paper 2: Surface Code Implementations (12 pages)")
    print("     - Paper 3: Topological Quantum Computing (18 pages)")
    print("     - Paper 4: Fault-Tolerant Architectures (20 pages)")
    print("     - Paper 5: Quantum Memory Systems (14 pages)")
    print()
    print("   Output Summary (500 words):")
    print("     'Recent advances in quantum computing focus on three key areas:")
    print("      error correction, hardware architectures, and memory systems.'")

    # Step 2: Citation Management
    print("\n   Step 2: Citation Management")
    print("   → Generating citations in APA style...")
    print("   → Auto-deduplicating references...")
    print("   Citations:")
    print("     [1] Smith, J. et al. (2025). Quantum Error Correction.")
    print("     [2] Jones, A. et al. (2025). Surface Code Implementations.")
    print("     [3] Brown, K. et al. (2026). Topological Computing.")
    print("     [4] Davis, M. et al. (2026). Fault-Tolerant Architectures.")
    print("     [5] Wilson, R. et al. (2026). Quantum Memory Systems.")

    # Step 3: Formatting
    print("\n   Step 3: Content Formatting")
    print("   → Formatting to markdown with GitHub style...")
    print("   → Adding heading levels (3 max)")
    print("   → Enabling code highlighting")
    print("   Structure:")
    print("     # Literature Review: Quantum Computing Advances")
    print("     ## 1. Introduction")
    print("     ## 2. Error Correction Techniques")
    print("     ## 3. Hardware Architectures")
    print("     ## 4. Memory Systems")
    print("     ## 5. Future Directions")
    print("     ## References")

    # Step 4: Export
    print("\n   Step 4: Markdown Export")
    print("   → Exporting to literature_review.md...")
    print("   → Including table of contents")
    print("   → Including metadata (authors, date, version)")
    print("   → Using reference-style links")
    print("   → Wrapped at 100 characters")
    print("   ✓ Exported successfully!")

    # 3. Generated content preview
    print("\n3. Generated Content Preview:")
    print("-" * 80)
    print(
        """
# Literature Review: Quantum Computing Advances

**Authors:** AegisRAG Research Team
**Date:** 2026-01-15
**Version:** 1.0

## Table of Contents
1. [Introduction](#introduction)
2. [Error Correction Techniques](#error-correction)
3. [Hardware Architectures](#hardware)

## 1. Introduction

Recent advances in quantum computing focus on three key areas: error correction,
hardware architectures, and memory systems [1-5]. This review synthesizes the
latest research in these domains...

## References

[1] Smith, J. et al. (2025). Quantum Error Correction. Nature Quantum, 14(2).
[2] Jones, A. et al. (2025). Surface Code Implementations. Phys Rev Lett, 125(3).
"""
    )
    print("-" * 80)

    # 4. Performance metrics
    print("\n4. Performance Metrics:")
    print("   Total Latency: 650ms (avg)")
    print("   P95 Latency: 1,200ms")
    print("   Skills Used: 4/4")
    print("   Tokens Used: 5,890 / 7,000")
    print("   Output Length: 2,347 words")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
