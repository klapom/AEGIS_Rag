"""Analysis Bundle Example - Sprint 95.3.

Demonstrates usage of the analysis_bundle for data analysis workflows.

The analysis bundle combines:
- validation: Data quality checking
- classification: LLM-based categorization
- comparison: Semantic comparison
- statistical_analysis: Statistical computations

Use cases:
- Data quality assessment
- Sentiment analysis
- Dataset comparison
- Statistical testing
"""

import asyncio

from src.agents.skills.bundle_installer import get_bundle_status, install_bundle


async def main():
    """Demonstrate analysis bundle usage."""

    print("=" * 80)
    print("Analysis Bundle Example - Sprint 95.3")
    print("=" * 80)

    # 1. Install bundle
    print("\n1. Installing Analysis Bundle...")
    report = install_bundle("analysis_bundle")

    if report.success:
        print(f"   ✓ {report.summary}")
    else:
        print(f"   ✗ {report.summary}")
        return

    # 2. Check status
    print("\n2. Bundle Status:")
    status = get_bundle_status("analysis_bundle")
    print(f"   Skills: {', '.join(status.installed_skills)}")

    # 3. Simulate analysis workflow
    print("\n3. Example Analysis Workflow:")
    print("   Dataset: Customer Feedback (1,000 records)")
    print()

    # Step 1: Validation
    print("   Step 1: Data Validation")
    print("   → Checking data quality...")
    print("   Results:")
    print("     - Null values: 23 (2.3%) - OK")
    print("     - Type errors: 0 (0%) - OK")
    print("     - Duplicates: 5 (0.5%) - OK")
    print("     - Range violations: 0 (0%) - OK")
    print("   → Data quality: 97.7% ✓")

    # Step 2: Classification
    print("\n   Step 2: Sentiment Classification")
    print("   → Classifying feedback sentiment...")
    print("   Results:")
    print("     - Positive: 620 (62%)")
    print("     - Neutral: 280 (28%)")
    print("     - Negative: 100 (10%)")
    print("   → Avg confidence: 0.89")

    # Step 3: Statistical Analysis
    print("\n   Step 3: Statistical Analysis")
    print("   → Computing statistics...")
    print("   Results:")
    print("     - Mean sentiment score: 3.8 / 5.0")
    print("     - Median: 4.0")
    print("     - Std dev: 1.2")
    print("     - 95% CI: [3.72, 3.88]")

    # Step 4: Comparison
    print("\n   Step 4: Comparison with Previous Quarter")
    print("   → Comparing Q4 2025 vs Q3 2025...")
    print("   Results:")
    print("     - Sentiment change: +0.3 points (8% increase)")
    print("     - Statistical significance: p < 0.01 ✓")
    print("     - Key improvements:")
    print("       * Product quality mentions: +15%")
    print("       * Support satisfaction: +12%")

    # 4. Performance metrics
    print("\n4. Performance Metrics:")
    print("   Total Latency: 450ms (avg)")
    print("   P95 Latency: 900ms")
    print("   Skills Used: 4/4")
    print("   Tokens Used: 4,823 / 6,000")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
