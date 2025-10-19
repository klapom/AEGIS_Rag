"""Diagnostic script to investigate LightRAG integration failures.

This script will:
1. Initialize LightRAGWrapper
2. Insert a test document
3. Check what data is actually created in Neo4j
4. Query the graph
5. Analyze failures
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print("=" * 80)
    print("LIGHTRAG DIAGNOSTIC TOOL")
    print("=" * 80)

    # Step 1: Initialize LightRAGWrapper
    print("\n[STEP 1] Initializing LightRAGWrapper...")
    from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

    lightrag = LightRAGWrapper(
        llm_model="qwen3:0.6b",
        embedding_model="nomic-embed-text",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="aegis-rag-neo4j-password",
    )

    print(f"  Working dir: {lightrag.working_dir}")
    print(f"  LLM model: {lightrag.llm_model}")
    print(f"  Embedding model: {lightrag.embedding_model}")

    # Step 2: Clean Neo4j database
    print("\n[STEP 2] Cleaning Neo4j database...")
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "aegis-rag-neo4j-password"),
    )

    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
        print("  Database cleaned")

    # Step 3: Check what labels/nodes exist BEFORE insertion
    print("\n[STEP 3] Checking Neo4j BEFORE insertion...")
    async with driver.session() as session:
        # Get all labels
        result = await session.run("CALL db.labels() YIELD label RETURN collect(label) AS labels")
        record = await result.single()
        labels_before = record["labels"] if record else []
        print(f"  Labels before: {labels_before}")

        # Count all nodes
        result = await session.run("MATCH (n) RETURN count(n) AS count")
        record = await result.single()
        nodes_before = record["count"] if record else 0
        print(f"  Nodes before: {nodes_before}")

    # Step 4: Insert test document
    print("\n[STEP 4] Inserting test document...")
    test_doc = {
        "text": """
        Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
        Steve Jobs served as CEO and led product development. The company's headquarters
        is in Cupertino, California. Apple is known for iPhone, iPad, and Mac computers.
        """
    }

    try:
        result = await lightrag.insert_documents([test_doc])
        print(f"  Insert result: {result}")
    except Exception as e:
        print(f"  ERROR during insert: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    # Step 5: Check what labels/nodes exist AFTER insertion
    print("\n[STEP 5] Checking Neo4j AFTER insertion...")
    async with driver.session() as session:
        # Get all labels
        result = await session.run("CALL db.labels() YIELD label RETURN collect(label) AS labels")
        record = await result.single()
        labels_after = record["labels"] if record else []
        print(f"  Labels after: {labels_after}")

        # Count all nodes
        result = await session.run("MATCH (n) RETURN count(n) AS count")
        record = await result.single()
        nodes_after = record["count"] if record else 0
        print(f"  Nodes after: {nodes_after}")

        # Get sample nodes for each label
        for label in labels_after:
            result = await session.run(f"MATCH (n:{label}) RETURN n LIMIT 3")
            records = [record async for record in result]
            print(f"\n  Sample nodes for label '{label}' ({len(records)} shown):")
            for i, record in enumerate(records):
                node = record["n"]
                # Get node properties
                props = dict(node.items())
                print(f"    {i+1}. {props}")

        # Count relationships
        result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count")
        record = await result.single()
        rels_after = record["count"] if record else 0
        print(f"\n  Relationships after: {rels_after}")

        # Sample relationships
        if rels_after > 0:
            result = await session.run("MATCH (a)-[r]->(b) RETURN type(r) AS rel_type, a, b LIMIT 5")
            records = [record async for record in result]
            print(f"\n  Sample relationships ({len(records)} shown):")
            for i, record in enumerate(records):
                print(f"    {i+1}. {record['rel_type']}: {dict(record['a'].items())} -> {dict(record['b'].items())}")

    # Step 6: Test get_stats() method
    print("\n[STEP 6] Testing get_stats() method...")
    stats = await lightrag.get_stats()
    print(f"  Stats from get_stats(): {stats}")

    # Step 7: Test query
    print("\n[STEP 7] Testing query_graph() with local mode...")
    try:
        query_result = await lightrag.query_graph(
            query="Who founded Apple?",
            mode="local",
        )
        print(f"  Query: {query_result.query}")
        print(f"  Answer: {query_result.answer}")
        print(f"  Answer length: {len(query_result.answer)}")
    except Exception as e:
        print(f"  ERROR during query: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    # Step 8: Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    if nodes_after == 0:
        print("\n[CRITICAL] No nodes created in Neo4j!")
        print("  Possible causes:")
        print("  1. LightRAG initialization failed silently")
        print("  2. ainsert() doesn't actually insert data")
        print("  3. qwen3:0.6b output format not recognized by LightRAG")
        print("  4. Neo4j connection issue")
    else:
        print(f"\n[SUCCESS] {nodes_after} nodes created in Neo4j")
        print(f"  Labels: {labels_after}")

    if "Entity" not in labels_after and nodes_after > 0:
        print("\n[ISSUE] No 'Entity' label found!")
        print(f"  LightRAG uses different labels: {labels_after}")
        print("  -> get_stats() method needs to be updated to use correct labels")

    await driver.close()
    print("\n[DONE] Diagnostic complete")


if __name__ == "__main__":
    asyncio.run(main())
