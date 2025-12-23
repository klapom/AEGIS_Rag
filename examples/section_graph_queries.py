"""Section-Aware Graph Queries - Usage Examples.

Sprint 62 Feature 62.1: Section-Aware Graph Queries

This script demonstrates how to use section-aware graph queries
to retrieve entities and relationships filtered by document sections.

Prerequisites:
- Neo4j running with section nodes (created in Sprint 32)
- Documents indexed with section metadata
"""

import asyncio

from src.domains.knowledge_graph.querying import (
    get_section_graph_service,
)


async def example_1_entities_in_section():
    """Example 1: Query entities in a specific section."""
    print("\n=== Example 1: Entities in Section ===")

    service = get_section_graph_service()

    result = await service.query_entities_in_section(
        section_heading="Introduction",
        document_id="paper_2024_123",
        limit=10,
    )

    print(f"Query Time: {result.query_time_ms:.2f}ms")
    print(f"Found {len(result.entities)} entities in 'Introduction':\n")

    for entity in result.entities:
        print(f"  - {entity.entity_name} ({entity.entity_type})")
        for section in entity.sections:
            print(f"    → Section: {section.section_heading} (p.{section.section_page})")


async def example_2_multi_section_query():
    """Example 2: Query entities across multiple sections."""
    print("\n=== Example 2: Multi-Section Query ===")

    service = get_section_graph_service()

    result = await service.query_entities_in_sections(
        section_headings=["Introduction", "Methods", "Results"],
        document_id="paper_2024_123",
    )

    print(f"Query Time: {result.query_time_ms:.2f}ms")
    print(f"Found {len(result.entities)} entities across 3 sections:\n")

    for entity in result.entities:
        section_names = [s.section_heading for s in entity.sections]
        print(f"  - {entity.entity_name}: {', '.join(section_names)}")


async def example_3_section_hierarchy():
    """Example 3: Query document section hierarchy."""
    print("\n=== Example 3: Section Hierarchy ===")

    service = get_section_graph_service()

    sections = await service.query_section_hierarchy(
        document_id="paper_2024_123",
        max_level=2,  # Only top 2 levels
    )

    print(f"Found {len(sections)} sections (levels 1-2):\n")

    for section in sections:
        indent = "  " * (section["level"] - 1)
        heading = section["heading"]
        page = section["page_no"]
        tokens = section.get("token_count", 0)
        print(f"{indent}{heading} (p.{page}, {tokens} tokens)")


async def example_4_entity_sections():
    """Example 4: Find all sections containing a specific entity."""
    print("\n=== Example 4: Entity-to-Section Mapping ===")

    service = get_section_graph_service()

    entity_name = "Neural Networks"
    sections = await service.get_entity_sections(entity_id=entity_name)

    print(f"'{entity_name}' appears in {len(sections)} sections:\n")

    for section in sections:
        print(
            f"  - {section.section_heading} (level {section.section_level}, "
            f"p.{section.section_page})"
        )


async def example_5_relationships_in_section():
    """Example 5: Query relationships mentioned in a section."""
    print("\n=== Example 5: Relationships in Section ===")

    service = get_section_graph_service()

    result = await service.query_relationships_in_section(
        section_heading="Methods",
        document_id="paper_2024_123",
        limit=10,
    )

    print(f"Query Time: {result.query_time_ms:.2f}ms")
    print(f"Found {len(result.relationships)} relationships in 'Methods':\n")

    for rel in result.relationships:
        print(f"  - {rel.source_name} → {rel.target_name} ({rel.relationship_type})")
        if rel.description:
            print(f"    Description: {rel.description[:80]}...")


async def example_6_section_analytics():
    """Example 6: Section-level analytics."""
    print("\n=== Example 6: Section Analytics ===")

    from src.components.graph_rag.neo4j_client import get_neo4j_client
    from src.components.graph_rag.query_templates import GraphQueryTemplates

    client = get_neo4j_client()
    templates = GraphQueryTemplates()

    # Get entity count per section
    query_dict = templates.section_entities_count(document_id="paper_2024_123").build()

    records = await client.execute_read(
        query_dict["query"],
        query_dict["parameters"],
    )

    print("Entity distribution across sections:\n")

    for record in records[:5]:  # Top 5 sections
        section = record["section"]
        level = record["level"]
        count = record["entity_count"]
        print(f"  - {section} (level {level}): {count} entities")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Section-Aware Graph Queries - Examples")
    print("=" * 60)

    try:
        await example_1_entities_in_section()
        await example_2_multi_section_query()
        await example_3_section_hierarchy()
        await example_4_entity_sections()
        await example_5_relationships_in_section()
        await example_6_section_analytics()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        print("\nNote: Ensure Neo4j is running and documents are indexed with sections.")


if __name__ == "__main__":
    asyncio.run(main())
