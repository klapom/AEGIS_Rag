# Hybrid RAG Synergy: Qdrant + Neo4j Integration

**Sprint 16 Feature 16.7: Maximizing Synergy Between Vector Search and Knowledge Graph**

## Problemstellung

Ihre Frage: "verwendet neo4j die selben chunks wie qdrant? Wo ist die synergie?"

**Antwort**: Aktuell verwenden sie UNTERSCHIEDLICHE Chunks - das ist nicht optimal! Die wahre Synergie entsteht, wenn beide Datenbanken die **gleichen Chunks** verwenden, aber unterschiedliche Aspekte speichern.

## Architektur-Konzept

### Shared Chunking Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Eingabe-Dokument                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          ChunkingService (Unified Chunking)                 │
│   Strategie: adaptive (sentence-aware, 512 tokens)          │
│   Output: Chunk Objects mit chunk_id (UUID)                 │
└─────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    ▼                ▼
        ┌───────────────────┐  ┌─────────────────────┐
        │   Qdrant Path     │  │   Neo4j Path        │
        └───────────────────┘  └─────────────────────┘
                │                        │
                ▼                        ▼
        ┌───────────────────┐  ┌─────────────────────┐
        │ BGE-M3 Embedding  │  │ Entity Extraction   │
        │ (1024 dim)        │  │ (SpaCy + Gemma)     │
        └───────────────────┘  └─────────────────────┘
                │                        │
                ▼                        ▼
        ┌───────────────────┐  ┌─────────────────────┐
        │ Qdrant Storage:   │  │ Neo4j Storage:      │
        │ - chunk_id (UUID) │  │ - :Entity nodes     │
        │ - vector (1024d)  │  │ - :Relation edges   │
        │ - chunk_text      │  │ - :chunk nodes      │
        │ - metadata        │  │ - MENTIONED_IN      │
        └───────────────────┘  └─────────────────────┘
```

## Synergie-Modell

### 1. Chunk-ID als Verbindungsglied

**Beide Datenbanken verwenden die GLEICHE `chunk_id` (UUID)**:

```python
# In Qdrant
{
    "id": "a1b2c3d4-e5f6-...",  # Chunk UUID
    "vector": [0.123, 0.456, ...],  # 1024-dim BGE-M3
    "payload": {
        "content": "AEGIS uses LightRAG for knowledge graphs...",
        "document_id": "docs/architecture.md",
        "chunk_index": 0,
        "metadata": {...}
    }
}

# In Neo4j
(:chunk {
    chunk_id: "a1b2c3d4-e5f6-...",  # SAME UUID!
    text: "AEGIS uses LightRAG for knowledge graphs...",
    document_id: "docs/architecture.md"
})

(:Entity {name: "AEGIS"})-[:MENTIONED_IN]->(:chunk {chunk_id: "a1b2c3d4-..."})
(:Entity {name: "LightRAG"})-[:MENTIONED_IN]->(:chunk {chunk_id: "a1b2c3d4-..."})
```

### 2. Hybrid Query Flow

**Beispiel-Query**: "What does AEGIS use for knowledge graphs?"

```
Step 1: Vector Search (Qdrant)
├─ Query embedding: [0.789, 0.234, ...]
├─ Top-K similar chunks: [chunk_a1b2..., chunk_c3d4..., ...]
└─ Return: chunk_ids + chunk_text + similarity_scores

Step 2: Graph Enrichment (Neo4j)
├─ For each chunk_id from Qdrant:
│  ├─ MATCH (e:Entity)-[:MENTIONED_IN]->(c:chunk {chunk_id: "a1b2..."})
│  ├─ MATCH (e)-[r]->(e2:Entity)
│  └─ RETURN entities, relationships, context
└─ Return: knowledge_graph for each chunk

Step 3: Answer Generation (LLM)
├─ Context: chunk_text + entities + relationships
├─ Prompt: "Based on this structured knowledge..."
└─ Answer: "AEGIS uses LightRAG (knowledge graph library) to..."
```

### 3. Vorteile der Synergie

**A. Präzise Provenance**
- Jede Entity weiß GENAU, in welchem Chunk sie erwähnt wurde
- "Wo wurde Entity X erwähnt?" → Direkte Neo4j Query: `MATCH (e:Entity {name: "X"})-[:MENTIONED_IN]->(c:chunk)`
- "Zeige mir den Originaltext" → Qdrant lookup mit `chunk_id`

**B. Semantische + Strukturierte Suche**
- Qdrant: "Finde ähnliche Texte" (semantische Suche)
- Neo4j: "Wie hängen diese Konzepte zusammen?" (Graph-Traversierung)
- Kombination: "Finde ähnliche Texte UND zeige mir die Entity-Beziehungen"

**C. Verification & Fact-Checking**
- LLM generiert Antwort basierend auf Chunks
- Neo4j verifiziert: "Existiert diese Relation wirklich in dem Chunk?"
- Qdrant liefert exakten Chunk-Text für Citation

**D. Multi-Hop Reasoning**
- Query: "How are AEGIS and Neo4j connected?"
- Qdrant: Finde Chunks über AEGIS und Neo4j
- Neo4j: Traversiere Graph: `(AEGIS)-[*1..3]-(Neo4j)`
- Result: "AEGIS → uses → LightRAG → stores_in → Neo4j"

## Aktuelle Implementierung

### Status Quo (Sprint 16)

```python
# ingestion.py (Qdrant path)
chunks = chunking_service.chunk_document(
    document_id=doc_id,
    content=content,
    metadata=cleaned_metadata,
)
# Strategy: adaptive (sentence-aware, 512 tokens)
# Output: List[Chunk] with chunk_id (UUID)

# lightrag_wrapper.py (Neo4j path)
chunks = self._chunk_text_with_metadata(
    text=document_text,
    document_id=document_id,
    chunk_token_size=600,
    chunk_overlap_token_size=100,
)
# Strategy: fixed (tiktoken-based, 600 tokens)
# Output: List[dict] with chunk_id (UUID)
```

**Problem**: Zwei verschiedene Chunking-Strategien!
- Qdrant: 512 tokens, adaptive
- Neo4j: 600 tokens, fixed
- **Keine Synergie**: chunk_ids stimmen nicht überein!

## Optimiertes Design (TODO)

### Option 1: Shared Chunks (Empfohlen)

```python
# Unified ingestion pipeline
async def ingest_document_hybrid(document: Document):
    # 1. Single chunking pass
    chunks = chunking_service.chunk_document(
        document_id=document.id,
        content=document.content,
        metadata=document.metadata,
    )

    # 2. Parallel indexing (same chunks!)
    await asyncio.gather(
        # Qdrant path: embeddings + vector storage
        index_to_qdrant(chunks),

        # Neo4j path: entity extraction + graph storage
        index_to_neo4j(chunks),
    )

    # Result: chunk_id is the JOIN key between databases!
```

**Vorteile**:
- ✅ Konsistente chunk_ids über beide Datenbanken
- ✅ Direkte Verknüpfung: Qdrant chunk → Neo4j entities
- ✅ Präzises Provenance Tracking
- ✅ Keine Chunk-Duplikation

### Option 2: Hierarchical Chunking

```python
# Qdrant: Große Chunks (512 tokens) für Context
large_chunks = chunk_document(size=512, strategy="adaptive")

# Neo4j: Sub-Chunks (256 tokens) für präzise Entity-Lokalisierung
for large_chunk in large_chunks:
    sub_chunks = chunk_text(large_chunk, size=256)
    # Store: (:LargeChunk)-[:CONTAINS]->(:SubChunk)
    #        (:Entity)-[:MENTIONED_IN]->(:SubChunk)
```

**Vorteile**:
- ✅ Qdrant: Mehr Kontext für Retrieval
- ✅ Neo4j: Präzisere Entity-Lokalisierung
- ✅ Flexibilität für unterschiedliche Use Cases

**Nachteile**:
- ❌ Komplexere Architektur
- ❌ Mehr Storage (Sub-Chunks)

## Query-Beispiele mit Synergie

### Beispiel 1: Fact Verification

```python
query = "Does AEGIS use LightRAG?"

# Step 1: Semantic search (Qdrant)
chunks = await qdrant.search(query, top_k=5)
# Result: [chunk_a1b2..., chunk_c3d4...]

# Step 2: Graph lookup (Neo4j)
for chunk in chunks:
    graph = await neo4j.query(f"""
        MATCH (e1:Entity {{name: 'AEGIS'}})-[r]->(e2:Entity {{name: 'LightRAG'}})
        WHERE (e1)-[:MENTIONED_IN]->(:chunk {{chunk_id: '{chunk.id}'}})
        RETURN e1, r, e2
    """)

    if graph.has_relation("AEGIS", "uses", "LightRAG"):
        return {
            "answer": "Yes, AEGIS uses LightRAG",
            "source_chunk": chunk.text,
            "chunk_id": chunk.id,
            "confidence": chunk.score,
            "verified": True  # Graph confirmed!
        }
```

### Beispiel 2: Multi-Hop Reasoning

```python
query = "How does AEGIS integrate with Neo4j?"

# Step 1: Find relevant entities (Neo4j)
path = await neo4j.query("""
    MATCH path = (aegis:Entity {name: 'AEGIS'})-[*1..3]-(neo4j:Entity {name: 'Neo4j'})
    RETURN path
""")
# Result: AEGIS → uses → LightRAG → stores_in → Neo4j

# Step 2: Find chunks that mention this path (Hybrid)
chunk_ids = set()
for node in path.nodes:
    chunks = await neo4j.query("""
        MATCH (e:Entity {name: $name})-[:MENTIONED_IN]->(c:chunk)
        RETURN c.chunk_id
    """, name=node.name)
    chunk_ids.update(chunks)

# Step 3: Retrieve full chunks from Qdrant
full_chunks = await qdrant.get_by_ids(list(chunk_ids))

# Step 4: Generate answer with path context
answer = await llm.generate(
    context=full_chunks,
    graph_path=path,
    query=query
)
```

## Implementation Roadmap

### Phase 1: Alignment (Current Sprint)
- [x] Add Neo4j indexing to admin API
- [x] Use ChunkingService for LightRAG (unified strategy)
- [ ] **TODO**: Ensure chunk_ids match between Qdrant and Neo4j
- [ ] **TODO**: Test end-to-end with hybrid queries

### Phase 2: Optimization (Next Sprint)
- [ ] Implement shared chunking pipeline
- [ ] Add chunk provenance API endpoints
- [ ] Optimize Neo4j queries for chunk lookups
- [ ] Add graph enrichment to search results

### Phase 3: Advanced Features (Future)
- [ ] Hierarchical chunking (large + sub-chunks)
- [ ] Real-time graph updates on document changes
- [ ] Graph-guided retrieval (use entity graph to expand queries)
- [ ] Confidence scoring based on graph + vector agreement

## Fazit

Die Synergie zwischen Qdrant und Neo4j entsteht durch:

1. **Gleiche Chunks**: Beide verwenden identische `chunk_id` (UUID)
2. **Unterschiedliche Perspektiven**:
   - Qdrant: "Was ist semantisch ähnlich?" (Vektor-Suche)
   - Neo4j: "Wie hängen Entities zusammen?" (Graph-Traversierung)
3. **Verknüpfung**: `chunk_id` ist der JOIN-Key
4. **Provenance**: Jede Entity kennt ihren Quell-Chunk
5. **Verification**: Graph kann Vector-Suche-Ergebnisse verifizieren

**Aktueller Status**: Implementierung läuft, aber Chunking-Strategien müssen noch aligniert werden.
