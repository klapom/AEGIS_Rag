"""Test qwen3:4b entity extraction format compliance with LightRAG."""

import asyncio
import json
import shutil
from pathlib import Path

from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper


async def test_qwen3_4b_format():
    """Test if qwen3:4b produces correct entity extraction format."""

    print("\n" + "="*80)
    print("Testing qwen3:4b Entity Extraction Format")
    print("="*80)

    # Clean LightRAG cache
    lightrag_dir = Path("data/lightrag_test_qwen3_4b")
    if lightrag_dir.exists():
        shutil.rmtree(lightrag_dir)
    lightrag_dir.mkdir(parents=True, exist_ok=True)

    print("\n[1/5] Creating LightRAGWrapper with qwen3:4b...")
    lightrag = LightRAGWrapper(
        llm_model="qwen3:4b",  # Using qwen3:4b
        embedding_model="nomic-embed-text",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="aegis-rag-neo4j-password",
        working_dir=str(lightrag_dir),
    )

    print("[2/5] Inserting test document...")
    test_doc = "Python is a programming language created by Guido van Rossum."
    await lightrag.insert_documents([{"text": test_doc}])

    print("\n[3/5] Checking Vector Database files...")
    vdb_files = {
        "entities": lightrag_dir / "vdb_entities.json",
        "relationships": lightrag_dir / "vdb_relationships.json",
        "chunks": lightrag_dir / "vdb_chunks.json",
    }

    results = {}
    for name, path in vdb_files.items():
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = len(data.get("data", []))
                results[name] = count
                print(f"  [{name}] {count} items")
        else:
            results[name] = 0
            print(f"  [{name}] FILE NOT FOUND")

    print("\n[4/5] Checking Neo4j graph stats...")
    stats = await lightrag.get_stats()
    print(f"  Entity count: {stats.get('entity_count', 0)}")
    print(f"  Relationship count: {stats.get('relationship_count', 0)}")

    print("\n[5/5] Testing query with qwen3:4b...")
    try:
        result = await lightrag.query_graph(
            query="Who created Python?",
            mode="local"
        )
        answer = result.answer
        print(f"  Query answer: {answer!r}")
        print(f"  Answer length: {len(answer)} chars")
        print(f"  Answer is empty: {not answer or answer.strip() == ''}")
    except Exception as e:
        print(f"  Query FAILED: {e}")
        answer = ""

    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)

    print(f"\nVDB Population:")
    print(f"  Entities VDB: {results.get('entities', 0)} items")
    print(f"  Relationships VDB: {results.get('relationships', 0)} items")
    print(f"  Chunks VDB: {results.get('chunks', 0)} items")

    print(f"\nNeo4j Graph:")
    print(f"  Entities: {stats.get('entity_count', 0)}")
    print(f"  Relationships: {stats.get('relationship_count', 0)}")

    print(f"\nQuery Test:")
    print(f"  Answer: {answer!r}")
    print(f"  Success: {bool(answer and answer.strip())}")

    # Verdict
    entities_populated = results.get('entities', 0) > 0
    query_success = bool(answer and answer.strip())

    print("\n" + "="*80)
    if entities_populated and query_success:
        print("VERDICT: qwen3:4b WORKS! Entity extraction format is correct.")
        print("="*80)
        return True
    elif entities_populated and not query_success:
        print("VERDICT: PARTIAL SUCCESS - Entities extracted but query failed.")
        print("="*80)
        return False
    else:
        print("VERDICT: qwen3:4b FAILS - Same issue as qwen3:0.6b.")
        print("="*80)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_qwen3_4b_format())
    exit(0 if success else 1)
