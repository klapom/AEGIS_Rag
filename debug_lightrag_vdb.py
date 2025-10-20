"""Debug script to check LightRAG VDB population after insert."""
import asyncio
import json
from pathlib import Path
import shutil


async def debug_lightrag_vdb():
    """Check if LightRAG VDB files are populated after insert."""
    from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

    # Clean start
    lightrag_dir = Path("data/lightrag")
    if lightrag_dir.exists():
        shutil.rmtree(lightrag_dir)
    lightrag_dir.mkdir(parents=True, exist_ok=True)

    print("[DEBUG] Creating LightRAGWrapper...")
    lightrag = LightRAGWrapper(
        llm_model="qwen3:0.6b",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="aegis-rag-neo4j-password",
    )

    print("[DEBUG] Inserting test document...")
    await lightrag.insert_documents([
        {"text": "Python is a programming language created by Guido van Rossum."}
    ])

    print("\n[DEBUG] Checking VDB files...")
    vdb_files = {
        "entities": lightrag_dir / "vdb_entities.json",
        "relationships": lightrag_dir / "vdb_relationships.json",
        "chunks": lightrag_dir / "vdb_chunks.json",
    }

    for name, path in vdb_files.items():
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"[OK] {name}: {path.name}")
            print(f"   - Size: {path.stat().st_size} bytes")
            print(f"   - Keys: {list(data.keys() if isinstance(data, dict) else [])}")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        print(f"   - {key}: {len(value)} items")
                    elif isinstance(value, dict):
                        print(f"   - {key}: {len(value)} keys")
        else:
            print(f"[FAIL] {name}: FILE NOT FOUND at {path}")

    print("\n[DEBUG] Checking Neo4j stats...")
    stats = await lightrag.get_stats()
    print(f"   - Entity count: {stats.get('entity_count', 0)}")
    print(f"   - Relationship count: {stats.get('relationship_count', 0)}")

    print("\n[DEBUG] Attempting query...")
    result = await lightrag.query_graph(
        query="Who created Python?",
        mode="local",
    )

    print(f"\n[RESULT]")
    print(f"   - Answer: {result.answer!r}")
    print(f"   - Answer length: {len(result.answer)}")
    print(f"   - Answer empty: {not result.answer or result.answer.strip() == ''}")


if __name__ == "__main__":
    asyncio.run(debug_lightrag_vdb())
