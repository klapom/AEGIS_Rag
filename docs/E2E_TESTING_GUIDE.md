# E2E Testing Guide - AEGIS RAG System

**Praktische Anleitung zum Ausführen und Erstellen eigener E2E Tests**

## 🎯 Ziel

Dieses Dokument zeigt dir, wie du:
1. Bestehende E2E Tests mit deinen eigenen Dokumenten ausführst
2. Eigene E2E Tests schreibst und testest
3. Die Test-Ergebnisse analysierst und debuggst

---

## 📋 Voraussetzungen

### 1. Services starten

**Docker Compose Services:**
```bash
# Terminal 1: Alle Services starten
cd "c:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"
docker-compose up -d

# Services prüfen
docker ps
# Erwartete Services:
# - qdrant/qdrant:latest (Port 6333)
# - neo4j:latest (Ports 7474, 7687)
# - ollama/ollama:latest (Port 11434)
```

**Ollama Models laden:**
```bash
# Terminal 2: Ollama Models prüfen/laden
ollama list

# Falls Models fehlen:
ollama pull llama3.2:3b          # Für Intent Classification
ollama pull nomic-embed-text     # Für Embeddings (768-dim)
```

**Service Verfügbarkeit testen:**
```bash
# Qdrant
curl http://localhost:6333/healthz
# Erwartete Ausgabe: {"title":"healthz","version":"1.11.3"}

# Ollama
curl http://localhost:11434/api/tags
# Erwartete Ausgabe: {"models":[...]}

# Neo4j (Browser)
# Browser öffnen: http://localhost:7474
# Login: neo4j / neo4jpassword (siehe docker-compose.yml)
```

### 2. Python Environment

```bash
# Poetry Environment aktivieren
poetry install

# Dependencies prüfen
poetry show | grep -E "qdrant|ollama|pytest|langchain"
```

---

## 🚀 E2E Tests mit eigenen Dokumenten ausführen

### Methode 1: Bestehende E2E Tests verwenden

**Schritt 1: Test-Dokumente vorbereiten**

```bash
# Verzeichnis für deine Dokumente erstellen
mkdir -p tests/fixtures/my_documents

# Beispiel: Deine eigenen Dokumente kopieren
cp "C:\Users\Klaus Pommer\Documents\*.txt" tests/fixtures/my_documents/
cp "C:\Users\Klaus Pommer\Documents\*.md" tests/fixtures/my_documents/
```

**Beispiel-Dokumente (für ersten Test):**

```bash
# tests/fixtures/my_documents/doc1.txt
cat > tests/fixtures/my_documents/doc1.txt << 'EOF'
AEGIS RAG System ist ein Multi-Agenten System für Retrieval Augmented Generation.
Es kombiniert Vector Search (Qdrant), Graph Reasoning (Neo4j + LightRAG),
und temporales Memory Management für komplexe Query-Bearbeitung.
EOF

# tests/fixtures/my_documents/doc2.txt
cat > tests/fixtures/my_documents/doc2.txt << 'EOF'
Vector Search verwendet Embeddings von Ollama (nomic-embed-text).
Die Embeddings sind 768-dimensional und werden in Qdrant gespeichert.
Hybrid Search kombiniert Vector Similarity mit BM25 Keyword Matching.
EOF

# tests/fixtures/my_documents/doc3.md
cat > tests/fixtures/my_documents/doc3.md << 'EOF'
# Graph RAG mit LightRAG

Graph Reasoning nutzt Neo4j als Graph Database.
LightRAG extrahiert Entities und Relationships aus Dokumenten.
Dual-Level Search: LOCAL (Entities), GLOBAL (Communities), HYBRID (Both).
EOF
```

**Schritt 2: Eigenen E2E Test erstellen**

Erstelle: `tests/integration/test_my_e2e_documents.py`

```python
"""E2E Test mit eigenen Dokumenten.

Testet:
1. Indexing deiner Dokumente
2. Hybrid Search mit deinen Inhalten
3. Relevanz der Ergebnisse
"""

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from src.components.vector_search import (
    BM25Search,
    DocumentIngestionPipeline,
    EmbeddingService,
    HybridSearch,
    QdrantClientWrapper,
)

# ============================================================================
# Configuration
# ============================================================================

# ANPASSEN: Pfad zu deinen Dokumenten
MY_DOCS_DIR = Path(__file__).parent.parent / "fixtures" / "my_documents"

# ANPASSEN: Erwartete Begriffe in deinen Dokumenten (für Relevanz-Test)
EXPECTED_TERMS = ["aegis", "vector", "search", "graph", "rag", "embeddings"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def my_test_setup():
    """Setup complete hybrid search environment with my documents."""
    # Create unique collection name
    collection_name = f"my_test_{uuid4().hex[:8]}"

    # Initialize components
    qdrant_client = QdrantClientWrapper(host="localhost", port=6333)
    embedding_service = EmbeddingService(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        batch_size=10,
    )
    bm25_search = BM25Search()

    # Check if documents exist
    if not MY_DOCS_DIR.exists() or not list(MY_DOCS_DIR.glob("*")):
        pytest.skip(f"No documents found in {MY_DOCS_DIR}")

    # Index documents
    pipeline = DocumentIngestionPipeline(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        collection_name=collection_name,
        chunk_size=256,
        chunk_overlap=64,
    )

    stats = await pipeline.index_documents(input_dir=MY_DOCS_DIR)
    print(f"\n📊 Indexing Stats: {stats}")

    # Create hybrid search
    hybrid_search = HybridSearch(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        bm25_search=bm25_search,
        collection_name=collection_name,
    )

    # Prepare BM25 index
    await hybrid_search.prepare_bm25_index()

    yield {
        "hybrid_search": hybrid_search,
        "qdrant_client": qdrant_client,
        "collection_name": collection_name,
        "stats": stats,
    }

    # Cleanup
    await qdrant_client.delete_collection(collection_name)
    await qdrant_client.close()


# ============================================================================
# E2E Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_documents_indexing(my_test_setup):
    """Test that my documents are indexed correctly."""
    stats = my_test_setup["stats"]

    # Verify indexing succeeded
    assert stats["documents_loaded"] > 0, "Should load documents"
    assert stats["chunks_created"] > 0, "Should create chunks"
    assert stats["embeddings_generated"] > 0, "Should generate embeddings"
    assert stats["points_indexed"] > 0, "Should index to Qdrant"

    print(f"""
    ✅ Indexing Results:
       - Documents loaded: {stats['documents_loaded']}
       - Chunks created: {stats['chunks_created']}
       - Embeddings generated: {stats['embeddings_generated']}
       - Points indexed: {stats['points_indexed']}
    """)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_documents_hybrid_search(my_test_setup):
    """Test hybrid search with my documents."""
    hybrid_search = my_test_setup["hybrid_search"]

    # ANPASSEN: Stelle eine Frage zu deinen Dokumenten
    query = "Was ist AEGIS RAG und wie funktioniert es?"

    result = await hybrid_search.hybrid_search(
        query=query,
        top_k=5,
        vector_top_k=10,
        bm25_top_k=10,
        rrf_k=60,
    )

    # Verify results
    assert "results" in result
    assert len(result["results"]) > 0, "Should return results"

    # Show results
    print(f"\n🔍 Query: {query}")
    print(f"📋 Found {len(result['results'])} results:\n")

    for i, doc in enumerate(result["results"], 1):
        print(f"Result {i}:")
        print(f"  Score: {doc.get('score', 'N/A'):.4f}")
        print(f"  Source: {doc.get('source', 'N/A')}")
        print(f"  Text: {doc['text'][:150]}...")
        print()

    # Verify relevance
    top_text = result["results"][0]["text"].lower()
    relevant = any(term in top_text for term in EXPECTED_TERMS)

    if not relevant:
        print(f"⚠️  Warning: Top result may not be relevant.")
        print(f"   Expected one of: {EXPECTED_TERMS}")
        print(f"   Got: {top_text[:100]}...")
    else:
        print(f"✅ Top result is relevant!")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_documents_vector_only(my_test_setup):
    """Test vector-only search with my documents."""
    hybrid_search = my_test_setup["hybrid_search"]

    # ANPASSEN: Semantische Frage
    query = "Wie werden Embeddings verwendet?"

    results = await hybrid_search.vector_search(query, top_k=3)

    assert len(results) > 0, "Should return vector results"

    print(f"\n🎯 Vector Search Query: {query}")
    print(f"📊 Vector Similarity Results:\n")

    for i, doc in enumerate(results, 1):
        print(f"{i}. Score: {doc['score']:.4f} | {doc['text'][:100]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_documents_keyword_search(my_test_setup):
    """Test BM25 keyword search with my documents."""
    hybrid_search = my_test_setup["hybrid_search"]

    # ANPASSEN: Keyword-Query (exakte Begriffe)
    query = "Vector Search Embeddings"

    results = await hybrid_search.keyword_search(query, top_k=3)

    assert len(results) > 0, "Should return keyword results"

    print(f"\n🔑 Keyword Search Query: {query}")
    print(f"📊 BM25 Ranking Results:\n")

    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc['text'][:100]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_documents_search_comparison(my_test_setup):
    """Compare Vector vs Hybrid search on my documents."""
    hybrid_search = my_test_setup["hybrid_search"]

    query = "AEGIS RAG System"

    # Run both searches
    hybrid_result = await hybrid_search.hybrid_search(query, top_k=3)
    vector_results = await hybrid_search.vector_search(query, top_k=3)

    print(f"\n🆚 Search Comparison: '{query}'\n")

    print("HYBRID SEARCH (Vector + BM25 + RRF):")
    for i, doc in enumerate(hybrid_result["results"], 1):
        print(f"  {i}. Score: {doc['score']:.4f} | {doc['text'][:80]}...")

    print("\nVECTOR ONLY SEARCH:")
    for i, doc in enumerate(vector_results, 1):
        print(f"  {i}. Score: {doc['score']:.4f} | {doc['text'][:80]}...")

    # Check for ranking differences
    hybrid_ids = [r["id"] for r in hybrid_result["results"]]
    vector_ids = [r["id"] for r in vector_results]

    if hybrid_ids != vector_ids:
        print("\n📊 Rankings differ! Hybrid fusion changed result order.")
    else:
        print("\n📊 Rankings identical. Consider more diverse queries.")


# ============================================================================
# Skip if services unavailable
# ============================================================================

@pytest.fixture(scope="module", autouse=True)
def check_services():
    """Check if Qdrant and Ollama are running."""
    import socket

    def is_available(host, port):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (TimeoutError, OSError):
            return False

    if not is_available("localhost", 6333):
        pytest.skip("Qdrant not available on localhost:6333")

    if not is_available("localhost", 11434):
        pytest.skip("Ollama not available on localhost:11434")
```

**Schritt 3: Test ausführen**

```bash
# Einzelnen Test ausführen mit verbose output
poetry run pytest tests/integration/test_my_e2e_documents.py -v -s

# Nur Indexing Test
poetry run pytest tests/integration/test_my_e2e_documents.py::test_my_documents_indexing -v -s

# Alle E2E Tests
poetry run pytest tests/integration/test_my_e2e_documents.py -v -s

# Mit Coverage
poetry run pytest tests/integration/test_my_e2e_documents.py --cov=src --cov-report=term-missing
```

**Erwartete Ausgabe:**

```
tests/integration/test_my_e2e_documents.py::test_my_documents_indexing

📊 Indexing Stats: {'documents_loaded': 3, 'chunks_created': 8, 'embeddings_generated': 8, 'points_indexed': 8, 'collection_name': 'my_test_abc123'}

    ✅ Indexing Results:
       - Documents loaded: 3
       - Chunks created: 8
       - Embeddings generated: 8
       - Points indexed: 8

PASSED

tests/integration/test_my_e2e_documents.py::test_my_documents_hybrid_search

🔍 Query: Was ist AEGIS RAG und wie funktioniert es?
📋 Found 5 results:

Result 1:
  Score: 0.0321
  Source: tests/fixtures/my_documents/doc1.txt
  Text: AEGIS RAG System ist ein Multi-Agenten System für Retrieval Augmented Generation...

Result 2:
  Score: 0.0289
  Source: tests/fixtures/my_documents/doc2.txt
  Text: Vector Search verwendet Embeddings von Ollama (nomic-embed-text)...

✅ Top result is relevant!
PASSED

tests/integration/test_my_e2e_documents.py::test_my_documents_search_comparison

🆚 Search Comparison: 'AEGIS RAG System'

HYBRID SEARCH (Vector + BM25 + RRF):
  1. Score: 0.0345 | AEGIS RAG System ist ein Multi-Agenten System für Retrieval Augmented...
  2. Score: 0.0298 | Vector Search verwendet Embeddings von Ollama (nomic-embed-text)...

VECTOR ONLY SEARCH:
  1. Score: 0.9234 | AEGIS RAG System ist ein Multi-Agenten System für Retrieval Augmented...
  2. Score: 0.8876 | Graph Reasoning nutzt Neo4j als Graph Database...

📊 Rankings differ! Hybrid fusion changed result order.
PASSED

=============================== 5 passed in 12.34s ===============================
```

---

## 🧪 Methode 2: Interaktiver E2E Test (Script)

**Script erstellen:** `scripts/test_my_documents.py`

```python
#!/usr/bin/env python3
"""Interactive E2E testing script for your documents."""

import asyncio
from pathlib import Path
from uuid import uuid4

from src.components.vector_search import (
    BM25Search,
    DocumentIngestionPipeline,
    EmbeddingService,
    HybridSearch,
    QdrantClientWrapper,
)


async def main():
    """Run interactive E2E test."""
    print("🚀 AEGIS RAG - Interactive E2E Test\n")

    # Configuration
    DOCS_DIR = Path("tests/fixtures/my_documents")  # ANPASSEN
    collection_name = f"interactive_test_{uuid4().hex[:8]}"

    print(f"📁 Documents directory: {DOCS_DIR}")
    print(f"📦 Collection name: {collection_name}\n")

    # Initialize components
    print("🔧 Initializing components...")
    qdrant_client = QdrantClientWrapper(host="localhost", port=6333)
    embedding_service = EmbeddingService(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        batch_size=10,
    )
    bm25_search = BM25Search()

    try:
        # Step 1: Index documents
        print("\n📚 Step 1: Indexing documents...")
        pipeline = DocumentIngestionPipeline(
            qdrant_client=qdrant_client,
            embedding_service=embedding_service,
            collection_name=collection_name,
            chunk_size=256,
            chunk_overlap=64,
        )

        stats = await pipeline.index_documents(input_dir=DOCS_DIR)
        print(f"""
✅ Indexing complete!
   - Documents loaded: {stats['documents_loaded']}
   - Chunks created: {stats['chunks_created']}
   - Embeddings generated: {stats['embeddings_generated']}
   - Points indexed: {stats['points_indexed']}
        """)

        # Step 2: Prepare hybrid search
        print("🔍 Step 2: Preparing hybrid search...")
        hybrid_search = HybridSearch(
            qdrant_client=qdrant_client,
            embedding_service=embedding_service,
            bm25_search=bm25_search,
            collection_name=collection_name,
        )
        await hybrid_search.prepare_bm25_index()
        print("✅ Hybrid search ready!\n")

        # Step 3: Interactive queries
        print("=" * 70)
        print("💬 Interactive Query Mode")
        print("=" * 70)
        print("Enter queries to search your documents.")
        print("Commands: 'quit' to exit, 'stats' for search stats\n")

        while True:
            query = input("🔍 Query: ").strip()

            if query.lower() == "quit":
                print("\n👋 Goodbye!")
                break

            if query.lower() == "stats":
                collection_info = await qdrant_client.get_collection_info(collection_name)
                print(f"\n📊 Collection Stats:")
                print(f"   - Points: {collection_info.points_count}")
                print(f"   - Vector size: {collection_info.config.params.vectors.size}")
                print(f"   - BM25 corpus size: {bm25_search.get_corpus_size()}\n")
                continue

            if not query:
                continue

            # Run hybrid search
            print(f"\n⏳ Searching...")
            result = await hybrid_search.hybrid_search(
                query=query,
                top_k=5,
                vector_top_k=10,
                bm25_top_k=10,
                rrf_k=60,
            )

            # Display results
            print(f"\n📋 Found {len(result['results'])} results:")
            print(f"⚡ Search latency: {result['search_metadata']['latency_ms']:.2f}ms")
            print(f"   - Vector results: {result['search_metadata']['vector_results_count']}")
            print(f"   - BM25 results: {result['search_metadata']['bm25_results_count']}")
            print()

            for i, doc in enumerate(result["results"], 1):
                print(f"Result {i}:")
                print(f"  📊 Score: {doc.get('score', 'N/A'):.4f}")
                print(f"  📄 Source: {doc.get('source', 'Unknown')}")
                print(f"  📝 Text: {doc['text'][:200]}...")
                print()

    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up collection: {collection_name}")
        await qdrant_client.delete_collection(collection_name)
        await qdrant_client.close()
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    asyncio.run(main())
```

**Script ausführen:**

```bash
# Ausführbar machen (Linux/Mac)
chmod +x scripts/test_my_documents.py

# Ausführen
poetry run python scripts/test_my_documents.py
```

**Interaktive Session:**

```
🚀 AEGIS RAG - Interactive E2E Test

📁 Documents directory: tests/fixtures/my_documents
📦 Collection name: interactive_test_abc123

🔧 Initializing components...

📚 Step 1: Indexing documents...

✅ Indexing complete!
   - Documents loaded: 3
   - Chunks created: 8
   - Embeddings generated: 8
   - Points indexed: 8

🔍 Step 2: Preparing hybrid search...
✅ Hybrid search ready!

======================================================================
💬 Interactive Query Mode
======================================================================
Enter queries to search your documents.
Commands: 'quit' to exit, 'stats' for search stats

🔍 Query: Was ist Vector Search?

⏳ Searching...

📋 Found 3 results:
⚡ Search latency: 184.23ms
   - Vector results: 10
   - BM25 results: 10

Result 1:
  📊 Score: 0.0345
  📄 Source: tests/fixtures/my_documents/doc2.txt
  📝 Text: Vector Search verwendet Embeddings von Ollama (nomic-embed-text). Die Embeddings sind 768-dimensional und werden in Qdrant gespeichert...

Result 2:
  📊 Score: 0.0298
  📄 Source: tests/fixtures/my_documents/doc1.txt
  📝 Text: AEGIS RAG System ist ein Multi-Agenten System für Retrieval Augmented Generation. Es kombiniert Vector Search (Qdrant)...

🔍 Query: stats

📊 Collection Stats:
   - Points: 8
   - Vector size: 768
   - BM25 corpus size: 8

🔍 Query: quit

👋 Goodbye!

🧹 Cleaning up collection: interactive_test_abc123
✅ Cleanup complete!
```

---

## 🔬 Methode 3: Vollständiger Agent Flow Test

**Test mit LangGraph und Coordinator:**

`tests/integration/test_my_full_agent_flow.py`

```python
"""Full agent flow E2E test with my documents."""

import pytest
from pathlib import Path

from src.agents.coordinator import CoordinatorAgent
from src.components.vector_search import DocumentIngestionPipeline


MY_DOCS = Path(__file__).parent.parent / "fixtures" / "my_documents"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_agent_flow_with_my_documents():
    """Test complete agent flow: Router → VectorAgent → Results."""

    # Prerequisites: Documents should be indexed first
    # (In real scenario, run indexing script separately)

    # Initialize coordinator
    coordinator = CoordinatorAgent(use_persistence=True)

    # Test queries with different intents
    test_cases = [
        {
            "query": "Was ist AEGIS RAG?",
            "expected_intent": "hybrid",
            "expected_terms": ["aegis", "rag", "system"],
        },
        {
            "query": "Wie funktioniert Vector Search?",
            "expected_intent": "vector",
            "expected_terms": ["vector", "search", "embeddings"],
        },
        {
            "query": "Erkläre Graph Reasoning",
            "expected_intent": "graph",
            "expected_terms": ["graph", "neo4j", "lightrag"],
        },
    ]

    print("\n" + "=" * 70)
    print("🤖 Full Agent Flow Test")
    print("=" * 70)

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]

        print(f"\n📝 Test Case {i}: {query}")

        # Process query through coordinator
        result = await coordinator.process_query(
            query=query,
            session_id=f"test_session_{i}"
        )

        # Verify result structure
        assert "query" in result
        assert "intent" in result
        assert "retrieved_contexts" in result
        assert "metadata" in result

        # Show results
        print(f"   ✅ Intent: {result['intent']}")
        print(f"   ✅ Contexts retrieved: {len(result['retrieved_contexts'])}")
        print(f"   ✅ Agent path: {result['metadata'].get('agent_path', [])}")

        if result["retrieved_contexts"]:
            top_context = result["retrieved_contexts"][0]
            print(f"   📄 Top result: {top_context['text'][:100]}...")

        # Verify expected terms in results (if contexts found)
        if result["retrieved_contexts"] and test_case["expected_terms"]:
            all_text = " ".join([ctx["text"] for ctx in result["retrieved_contexts"]])
            found_terms = [term for term in test_case["expected_terms"]
                          if term in all_text.lower()]

            if found_terms:
                print(f"   ✅ Found expected terms: {found_terms}")
            else:
                print(f"   ⚠️  Expected terms not found: {test_case['expected_terms']}")

    print("\n" + "=" * 70)
    print("✅ Full Agent Flow Test Complete!")
    print("=" * 70)
```

**Ausführen:**

```bash
poetry run pytest tests/integration/test_my_full_agent_flow.py -v -s
```

---

## 📊 Test-Ergebnisse analysieren

### 1. Detaillierte Logs aktivieren

```bash
# Mit DEBUG logging
LOG_LEVEL=DEBUG poetry run pytest tests/integration/test_my_e2e_documents.py -v -s

# Mit pytest-cov für Coverage
poetry run pytest tests/integration/test_my_e2e_documents.py \
  --cov=src \
  --cov-report=html \
  --cov-report=term-missing
```

### 2. Performance Profiling

```python
# In deinem Test hinzufügen:
import time

@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_performance_profile(my_test_setup):
    """Profile search performance."""
    hybrid_search = my_test_setup["hybrid_search"]

    query = "Test query"
    num_runs = 10
    latencies = []

    for i in range(num_runs):
        start = time.perf_counter()
        result = await hybrid_search.hybrid_search(query, top_k=5)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

    # Statistics
    avg = sum(latencies) / len(latencies)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"""
    📊 Performance Profile ({num_runs} runs):
       - Average: {avg:.2f}ms
       - P50: {p50:.2f}ms
       - P95: {p95:.2f}ms
       - Min: {min(latencies):.2f}ms
       - Max: {max(latencies):.2f}ms
    """)

    # Assertions
    assert avg < 500, f"Average latency too high: {avg}ms"
    assert p95 < 1000, f"P95 latency too high: {p95}ms"
```

### 3. Relevanz-Metriken

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_relevance_metrics(my_test_setup):
    """Measure search relevance with known queries."""
    hybrid_search = my_test_setup["hybrid_search"]

    # Query-Document Pairs (Ground Truth)
    test_cases = [
        {
            "query": "AEGIS RAG",
            "expected_doc": "doc1.txt",  # Should rank first
            "expected_terms": ["aegis", "rag", "system"],
        },
        {
            "query": "Embeddings Ollama",
            "expected_doc": "doc2.txt",
            "expected_terms": ["embeddings", "ollama", "nomic"],
        },
    ]

    results = []

    for test in test_cases:
        result = await hybrid_search.hybrid_search(test["query"], top_k=5)

        # Check if expected doc is in top-k
        sources = [r.get("source", "") for r in result["results"]]
        expected_source = str(MY_DOCS_DIR / test["expected_doc"])

        rank = None
        for i, source in enumerate(sources, 1):
            if test["expected_doc"] in source:
                rank = i
                break

        # Calculate term coverage
        top_text = result["results"][0]["text"].lower()
        terms_found = sum(1 for term in test["expected_terms"] if term in top_text)
        term_coverage = terms_found / len(test["expected_terms"])

        results.append({
            "query": test["query"],
            "rank": rank,
            "term_coverage": term_coverage,
        })

        print(f"""
        Query: {test['query']}
          - Expected doc rank: {rank if rank else 'Not in top-5'}
          - Term coverage: {term_coverage*100:.1f}%
        """)

    # Overall metrics
    mrr = sum(1/r["rank"] for r in results if r["rank"]) / len(results)
    avg_coverage = sum(r["term_coverage"] for r in results) / len(results)

    print(f"""
    📊 Relevance Metrics:
       - MRR (Mean Reciprocal Rank): {mrr:.3f}
       - Average Term Coverage: {avg_coverage*100:.1f}%
    """)

    assert mrr > 0.5, "MRR should be > 0.5 (expected doc in top 2)"
    assert avg_coverage > 0.6, "Term coverage should be > 60%"
```

---

## 🐛 Debugging Tipps

### 1. Qdrant Collection inspizieren

```python
import asyncio
from src.components.vector_search import QdrantClientWrapper

async def inspect_collection():
    client = QdrantClientWrapper(host="localhost", port=6333)

    # List all collections
    collections = await client.list_collections()
    print(f"Collections: {collections}")

    # Get collection info
    info = await client.get_collection_info("my_test_abc123")
    print(f"""
    Collection Info:
      - Points: {info.points_count}
      - Vector size: {info.config.params.vectors.size}
      - Distance: {info.config.params.vectors.distance}
    """)

    # Sample points
    points = await client.scroll(
        collection_name="my_test_abc123",
        limit=3
    )

    for point in points:
        print(f"""
        Point ID: {point['id']}
        Text: {point['payload']['text'][:100]}...
        Source: {point['payload'].get('source', 'N/A')}
        """)

    await client.close()

asyncio.run(inspect_collection())
```

### 2. Embedding Similarity testen

```python
import asyncio
from src.components.vector_search import EmbeddingService
import numpy as np

async def test_embedding_similarity():
    service = EmbeddingService(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434"
    )

    # Test similar texts
    text1 = "AEGIS RAG ist ein Multi-Agenten System"
    text2 = "AEGIS RAG is a multi-agent system"
    text3 = "Vector databases store embeddings"

    emb1 = await service.embed_text(text1)
    emb2 = await service.embed_text(text2)
    emb3 = await service.embed_text(text3)

    # Cosine similarity
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    sim_12 = cosine_sim(emb1, emb2)
    sim_13 = cosine_sim(emb1, emb3)

    print(f"""
    Embedding Similarity:
      - Text1 vs Text2 (same meaning): {sim_12:.4f}
      - Text1 vs Text3 (different topic): {sim_13:.4f}
    """)

    assert sim_12 > 0.8, "Similar texts should have high similarity"
    assert sim_13 < 0.6, "Different texts should have lower similarity"

asyncio.run(test_embedding_similarity())
```

### 3. BM25 Ranking verstehen

```python
from src.components.vector_search import BM25Search

# Create BM25 search
bm25 = BM25Search()

# Sample documents
docs = [
    {"id": "1", "text": "AEGIS RAG system for retrieval"},
    {"id": "2", "text": "Vector search with embeddings"},
    {"id": "3", "text": "AEGIS uses vector and graph search"},
]

# Fit BM25
bm25.fit(docs)

# Test queries
queries = ["AEGIS", "vector", "AEGIS vector"]

for query in queries:
    results = bm25.search(query, top_k=3)
    print(f"\nQuery: '{query}'")
    for i, r in enumerate(results, 1):
        print(f"  {i}. Score: {r['score']:.4f} | {r['text']}")
```

---

## ✅ Best Practices

### 1. Test-Dokumente organisieren

```
tests/fixtures/
├── my_documents/          # Deine eigenen Dokumente
│   ├── domain_specific/   # Fachspezifische Docs
│   │   ├── finance.txt
│   │   └── medical.txt
│   ├── general/           # Allgemeine Docs
│   │   ├── intro.txt
│   │   └── overview.md
│   └── README.md          # Dokumentation der Test-Docs
```

### 2. Ground Truth definieren

Erstelle `tests/fixtures/my_documents/ground_truth.json`:

```json
{
  "queries": [
    {
      "query": "Was ist AEGIS RAG?",
      "expected_doc": "intro.txt",
      "expected_rank": 1,
      "expected_terms": ["aegis", "rag", "multi-agent"]
    },
    {
      "query": "Wie funktioniert Vector Search?",
      "expected_doc": "vector_search.txt",
      "expected_rank": 1,
      "expected_terms": ["vector", "embeddings", "similarity"]
    }
  ]
}
```

### 3. Separate Test Environments

```python
# conftest.py - Shared fixtures
import pytest

@pytest.fixture(scope="session")
def test_collection_prefix():
    """Unique prefix for test collections."""
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}"

@pytest.fixture
def test_config():
    """Test-specific configuration."""
    return {
        "chunk_size": 256,
        "chunk_overlap": 64,
        "top_k": 5,
        "vector_top_k": 10,
        "bm25_top_k": 10,
    }
```

---

## 🎓 Zusammenfassung

**Du kannst E2E Tests auf 3 Arten durchführen:**

1. **Pytest E2E Tests** (`test_my_e2e_documents.py`)
   - ✅ Automatisiert, wiederholbar
   - ✅ CI/CD Integration
   - ✅ Detaillierte Assertions

2. **Interaktives Script** (`scripts/test_my_documents.py`)
   - ✅ Explorative Analyse
   - ✅ Ad-hoc Queries
   - ✅ Schnelles Feedback

3. **Full Agent Flow Test** (`test_my_full_agent_flow.py`)
   - ✅ Kompletter System-Test
   - ✅ Router + Agent Integration
   - ✅ Multi-Intent Tests

**Nächste Schritte:**

1. ✅ Services starten (`docker-compose up -d`)
2. ✅ Test-Dokumente in `tests/fixtures/my_documents/` ablegen
3. ✅ E2E Test Script erstellen und anpassen
4. ✅ Tests ausführen und Ergebnisse analysieren
5. ✅ Performance und Relevanz optimieren

Viel Erfolg beim Testen! 🚀
