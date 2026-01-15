"""Research Bundle Example - Sprint 95.3.

Demonstrates usage of the research_bundle for information gathering workflows.

The research bundle combines:
- web_search: Search external sources
- retrieval: Query vector database
- graph_query: Traverse knowledge graph
- citation: Manage sources

Use cases:
- Academic research
- Fact-checking
- Literature reviews
- Information synthesis
"""

import asyncio

from src.agents.skills.bundle_installer import (
    get_bundle_status,
    install_bundle,
    list_available_bundles,
)


async def main():
    """Demonstrate research bundle usage."""

    print("=" * 80)
    print("Research Bundle Example - Sprint 95.3")
    print("=" * 80)

    # 1. List available bundles
    print("\n1. Available Bundles:")
    bundles = list_available_bundles()
    for bundle in bundles:
        print(f"   - {bundle}")

    # 2. Install research bundle
    print("\n2. Installing Research Bundle...")
    report = install_bundle("research_bundle")

    if report.success:
        print(f"   ✓ {report.summary}")
        print(f"   Duration: {report.duration_seconds:.2f}s")
    else:
        print(f"   ✗ Installation failed: {report.summary}")
        return

    if report.warnings:
        print("\n   Warnings:")
        for warning in report.warnings:
            print(f"   - {warning}")

    if report.missing_dependencies:
        print("\n   Missing Dependencies:")
        for dep in report.missing_dependencies:
            print(f"   - {dep}")

    # 3. Check bundle status
    print("\n3. Bundle Status:")
    status = get_bundle_status("research_bundle")
    print(f"   Installed: {status.installed}")
    print(f"   Version: {status.version}")
    print(f"   Skills: {', '.join(status.installed_skills)}")

    # 4. Simulate research workflow
    print("\n4. Example Research Workflow:")
    print("   Query: 'What are the latest advances in quantum computing?'")
    print()

    # Step 1: Web search
    print("   Step 1: Web Search")
    print("   → Searching Google, Bing for 'quantum computing advances 2026'")
    print("   → Found 10 results (5 academic, 5 news)")

    # Step 2: Vector retrieval
    print("\n   Step 2: Vector Retrieval")
    print("   → Querying Qdrant with hybrid search (BGE-M3)")
    print("   → Retrieved 5 documents (avg score: 0.87)")

    # Step 3: Graph query
    print("\n   Step 3: Graph Traversal")
    print("   → Querying Neo4j for 'quantum computing' entities")
    print("   → Found 12 related entities (2-hop)")
    print("     - Quantum Algorithms (8 papers)")
    print("     - Quantum Error Correction (6 papers)")
    print("     - Quantum Hardware (4 papers)")

    # Step 4: Citation
    print("\n   Step 4: Citation Management")
    print("   → Generated 10 citations in APA style")
    print("   → Example:")
    print("     Smith, J. et al. (2026). Advances in Quantum Error Correction.")
    print("     Nature Quantum, 15(3), 245-260. https://doi.org/10.1038/nq.2026.123")

    # 5. Bundle configuration
    print("\n5. Bundle Configuration:")
    print("   Context Budget: 8,000 tokens")
    print("   Auto-activated: retrieval, citation")
    print("   Permissions: browser, web_fetch, search_api")

    # 6. Performance metrics
    print("\n6. Performance Metrics:")
    print("   Total Latency: 850ms (avg)")
    print("   P95 Latency: 1,500ms")
    print("   Skills Used: 4/4")
    print("   Tokens Used: 6,234 / 8,000")

    print("\n" + "=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
