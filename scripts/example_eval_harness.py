"""Example usage of EvalHarness for quality gates.

Sprint 67 Feature 67.6: Automated quality validation for RAG responses.

This script demonstrates how to use the EvalHarness to validate RAG responses
with automated quality checks for grounding, citation coverage, and format compliance.

Usage:
    poetry run python scripts/example_eval_harness.py
"""

import asyncio

from src.adaptation.eval_harness import EvalHarness, QualityCheck


async def main():
    """Run example evaluation scenarios."""
    print("=" * 80)
    print("EvalHarness Example Usage (Sprint 67 Feature 67.6)")
    print("=" * 80)
    print()

    # Initialize harness with default thresholds
    harness = EvalHarness()
    print("✓ Initialized EvalHarness with default thresholds:")
    print(f"  - Grounding: {harness.thresholds[QualityCheck.GROUNDING]}")
    print(f"  - Citation Coverage: {harness.thresholds[QualityCheck.CITATION_COVERAGE]}")
    print(f"  - Format Compliance: {harness.thresholds[QualityCheck.FORMAT_COMPLIANCE]}")
    print()

    # Example 1: Well-formatted answer with good citations
    print("-" * 80)
    print("Example 1: Well-formatted answer")
    print("-" * 80)
    query = "What is RAG?"
    answer = """RAG (Retrieval Augmented Generation) is a technique that combines \
retrieval and generation [1]. It improves LLM responses by providing relevant \
context from external sources [2]."""
    sources = [
        {
            "chunk_id": "c1",
            "text": "RAG stands for Retrieval Augmented Generation, a method that enhances "
            "large language models by retrieving relevant information.",
        },
        {
            "chunk_id": "c2",
            "text": "RAG systems fetch context from databases before generating responses, "
            "improving accuracy and reducing hallucinations.",
        },
    ]

    print(f"Query: {query}")
    print(f"Answer: {answer[:100]}...")
    print(f"Sources: {len(sources)} documents")
    print()

    results = await harness.evaluate_response(query, answer, sources)

    print("Results:")
    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status} {result.check.value}: {result.score:.2f} ({result.latency_ms:.1f}ms)")
        if not result.passed:
            print(f"    Details: {result.details}")
    print()

    # Example 2: Answer with format issues
    print("-" * 80)
    print("Example 2: Answer with format issues")
    print("-" * 80)
    bad_answer = """
##

RAG is useful [1][5].

-

Check out this [link]().
"""
    print(f"Answer (with issues): {bad_answer[:50]}...")
    print()

    result = await harness._check_format(bad_answer)
    status = "✓ PASS" if result.passed else "✗ FAIL"
    print(f"  {status} Format Check: {result.score:.2f}")
    print(f"  Issues found: {result.details['issue_count']}")
    for issue in result.details["issues"]:
        print(f"    - {issue['type']}: {issue.get('count', 1)} occurrence(s)")
    print()

    # Example 3: Answer with poor citation coverage
    print("-" * 80)
    print("Example 3: Poor citation coverage")
    print("-" * 80)
    uncited_answer = "RAG is a technique. It combines retrieval and generation. Some say it works well."
    sources_ex3 = [{"chunk_id": "c1", "text": "RAG definition"}]

    print(f"Answer: {uncited_answer}")
    print()

    result = await harness._check_citation_coverage(uncited_answer, sources_ex3)
    status = "✓ PASS" if result.passed else "✗ FAIL"
    print(f"  {status} Citation Coverage: {result.score:.2f}")
    print(f"  Sentences: {result.details['sentences_with_citations']}/{result.details['total_sentences']} cited")
    print(f"  Warnings: {result.details['warnings']}")
    print()

    # Example 4: Custom thresholds
    print("-" * 80)
    print("Example 4: Custom thresholds (stricter)")
    print("-" * 80)
    strict_harness = EvalHarness(
        thresholds={
            QualityCheck.GROUNDING: 0.95,  # Very strict
            QualityCheck.CITATION_COVERAGE: 0.9,  # Strict
            QualityCheck.FORMAT_COMPLIANCE: 1.0,  # Perfect format required
        }
    )
    print("✓ Initialized strict harness:")
    print(f"  - Grounding: {strict_harness.thresholds[QualityCheck.GROUNDING]}")
    print(f"  - Citation Coverage: {strict_harness.thresholds[QualityCheck.CITATION_COVERAGE]}")
    print(f"  - Format Compliance: {strict_harness.thresholds[QualityCheck.FORMAT_COMPLIANCE]}")
    print()

    # Rerun Example 1 with strict thresholds
    results_strict = await strict_harness.evaluate_response(query, answer, sources)
    print("Results with strict thresholds:")
    for result in results_strict:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status} {result.check.value}: {result.score:.2f}")
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
