"""Example: Section-Based Community Detection.

Sprint 62 Feature 62.8: Section-Based Community Detection

This example demonstrates how to use the SectionCommunityDetector to:
1. Detect communities within specific sections
2. Compare communities across multiple sections
3. Identify section-specific vs. cross-section communities
4. Retrieve and analyze community metadata

Prerequisites:
- Neo4j running with indexed documents
- Section nodes created (Sprint 32)
- DEFINES relationships between sections and entities

Usage:
    poetry run python examples/section_community_detection_example.py
"""

import asyncio

import structlog

from src.domains.knowledge_graph.communities import (
    SectionCommunityDetector,
    get_section_community_detector,
)

logger = structlog.get_logger(__name__)


async def example_detect_communities_in_section():
    """Example 1: Detect communities in a single section."""
    print("\n=== Example 1: Detect Communities in Section ===\n")

    detector = get_section_community_detector()

    # Detect communities in the "Introduction" section
    result = await detector.detect_communities_in_section(
        section_heading="Introduction",
        document_id="doc_123",  # Optional: filter by document
        algorithm="louvain",  # or "leiden"
        resolution=1.0,  # Higher = more communities
        min_size=2,  # Minimum entities per community
    )

    print(f"Section: {result.section_heading}")
    print(f"Total entities: {result.total_entities}")
    print(f"Communities found: {len(result.communities)}")
    print(f"Detection time: {result.detection_time_ms:.2f}ms")
    print(f"Algorithm: {result.algorithm}")

    # Print community details
    for i, community in enumerate(result.communities):
        print(f"\nCommunity {i + 1}:")
        print(f"  ID: {community.community_id}")
        print(f"  Entity count: {community.entity_count}")
        print(f"  Cohesion score: {community.cohesion_score:.3f}")
        print(f"  Section-specific: {community.is_section_specific}")


async def example_compare_communities_across_sections():
    """Example 2: Compare communities across multiple sections."""
    print("\n=== Example 2: Compare Communities Across Sections ===\n")

    detector = get_section_community_detector()

    # Compare communities in multiple sections
    comparison = await detector.compare_communities_across_sections(
        section_headings=["Introduction", "Methods", "Results", "Discussion"],
        document_id="doc_123",
        algorithm="louvain",
        resolution=1.0,
    )

    print(f"Comparison completed in {comparison.comparison_time_ms:.2f}ms\n")

    # Print section-specific communities
    print("Section-Specific Communities:")
    for section, community_ids in comparison.section_specific_communities.items():
        print(f"  {section}: {len(community_ids)} communities")
        for community_id in community_ids[:3]:  # Show first 3
            print(f"    - {community_id}")

    # Print shared communities
    print(f"\nShared Communities (across sections): {len(comparison.shared_communities)}")
    for community_id in comparison.shared_communities[:5]:  # Show first 5
        print(f"  - {community_id}")

    # Print overlap matrix
    print("\nEntity Overlap Matrix:")
    sections = list(comparison.community_overlap_matrix.keys())
    print(f"{'':20} {' '.join(f'{s[:10]:>10}' for s in sections)}")
    for section1 in sections:
        overlaps = [
            str(comparison.community_overlap_matrix[section1][section2])
            for section2 in sections
        ]
        print(f"{section1:20} {' '.join(f'{o:>10}' for o in overlaps)}")


async def example_retrieve_section_communities():
    """Example 3: Retrieve stored communities for a section."""
    print("\n=== Example 3: Retrieve Section Communities ===\n")

    detector = get_section_community_detector()

    # Retrieve all communities for a section
    communities = await detector.get_section_communities(
        section_heading="Methods", document_id="doc_123"
    )

    print(f"Found {len(communities)} communities in 'Methods' section\n")

    for i, community in enumerate(communities):
        print(f"Community {i + 1}:")
        print(f"  ID: {community['community_id']}")
        print(f"  Size: {community['size']}")
        print(f"  Density: {community['density']:.3f}")
        print(f"  Algorithm: {community['algorithm']}")
        print(f"  Entity IDs: {', '.join(community['entity_ids'][:5])}")
        if len(community["entity_ids"]) > 5:
            print(f"  ... and {len(community['entity_ids']) - 5} more")
        print()


async def example_analyze_community_cohesion():
    """Example 4: Analyze community cohesion across sections."""
    print("\n=== Example 4: Analyze Community Cohesion ===\n")

    detector = get_section_community_detector()

    sections = ["Introduction", "Methods", "Results", "Discussion"]

    cohesion_by_section = {}

    for section in sections:
        result = await detector.detect_communities_in_section(
            section_heading=section, algorithm="louvain", resolution=1.0
        )

        if result.communities:
            avg_cohesion = sum(c.cohesion_score for c in result.communities) / len(
                result.communities
            )
            cohesion_by_section[section] = {
                "avg_cohesion": avg_cohesion,
                "community_count": len(result.communities),
                "total_entities": result.total_entities,
            }

    print("Community Cohesion Analysis:")
    print(f"{'Section':20} {'Communities':>12} {'Entities':>10} {'Avg Cohesion':>15}")
    print("-" * 60)

    for section, stats in cohesion_by_section.items():
        print(
            f"{section:20} {stats['community_count']:>12} "
            f"{stats['total_entities']:>10} {stats['avg_cohesion']:>15.3f}"
        )


async def example_identify_thematic_clusters():
    """Example 5: Identify thematic clusters in a document."""
    print("\n=== Example 5: Identify Thematic Clusters ===\n")

    detector = get_section_community_detector()

    # Detect communities in all sections
    document_sections = ["Abstract", "Introduction", "Methods", "Results", "Discussion"]

    all_communities = []

    for section in document_sections:
        result = await detector.detect_communities_in_section(
            section_heading=section, algorithm="louvain", resolution=1.5  # Higher resolution
        )

        for community in result.communities:
            all_communities.append(
                {
                    "section": section,
                    "community_id": community.community_id,
                    "size": community.entity_count,
                    "cohesion": community.cohesion_score,
                }
            )

    # Sort by cohesion score (most cohesive clusters first)
    all_communities.sort(key=lambda x: x["cohesion"], reverse=True)

    print("Top 10 Thematic Clusters (by cohesion):\n")
    print(f"{'Rank':>4} {'Section':20} {'Community ID':25} {'Size':>6} {'Cohesion':>10}")
    print("-" * 70)

    for i, community in enumerate(all_communities[:10], 1):
        print(
            f"{i:>4} {community['section']:20} {community['community_id']:25} "
            f"{community['size']:>6} {community['cohesion']:>10.3f}"
        )


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("Section-Based Community Detection Examples")
    print("Sprint 62 Feature 62.8")
    print("=" * 70)

    try:
        # Example 1: Basic community detection in a section
        await example_detect_communities_in_section()

        # Example 2: Cross-section comparison
        await example_compare_communities_across_sections()

        # Example 3: Retrieve stored communities
        await example_retrieve_section_communities()

        # Example 4: Analyze cohesion
        await example_analyze_community_cohesion()

        # Example 5: Identify thematic clusters
        await example_identify_thematic_clusters()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        logger.error("example_failed", error=str(e))
        print(f"\nError running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
