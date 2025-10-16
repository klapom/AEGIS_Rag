# Sprint 5 Examples - LightRAG Graph Retrieval

**Sprint:** Sprint 5 - LightRAG Integration & Graph Retrieval
**Version:** 1.0
**Last Updated:** 2025-10-16

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Graph Construction Examples](#graph-construction-examples)
3. [Entity Extraction Examples](#entity-extraction-examples)
4. [Relationship Extraction Examples](#relationship-extraction-examples)
5. [Graph Query Examples](#graph-query-examples)
6. [Dual-Level Retrieval Examples](#dual-level-retrieval-examples)
7. [Graph Query Agent Examples](#graph-query-agent-examples)
8. [Incremental Updates Examples](#incremental-updates-examples)
9. [Neo4j Cypher Query Examples](#neo4j-cypher-query-examples)
10. [Integration with Sprint 4 Router](#integration-with-sprint-4-router)
11. [Production Pipeline Example](#production-pipeline-example)

---

## Quick Start

### Minimal Example: Document to Graph to Query

```python
import asyncio
from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

async def quick_start():
    """Minimal example: insert document and query graph."""

    # 1. Initialize LightRAG
    lightrag = LightRAGWrapper()

    # 2. Insert a document
    text = """
    John Smith is a senior software engineer at Google.
    He specializes in machine learning and has 10 years of experience.
    Google is a technology company headquartered in Mountain View, California.
    """

    print("Inserting document into graph...")
    result = await lightrag.insert_text(text)
    print(f"Insert result: {result}")

    # 3. Query the graph (local mode - entity-level)
    print("\nQuerying graph...")
    query_result = await lightrag.query(
        "What company does John Smith work for?",
        mode="local"
    )

    print(f"Question: {query_result.query}")
    print(f"Answer: {query_result.answer}")
    print(f"Mode: {query_result.mode}")

    # 4. Check graph statistics
    entity_count = await lightrag.get_entity_count()
    print(f"\nTotal entities in graph: {entity_count}")

asyncio.run(quick_start())
```

**Expected Output:**
```
Inserting document into graph...
Insert result: {'status': 'success', 'result': {...}}

Querying graph...
Question: What company does John Smith work for?
Answer: John Smith works for Google, a technology company headquartered in Mountain View, California.
Mode: local

Total entities in graph: 4
```

---

## Graph Construction Examples

### Example 1: Insert Single Document

```python
from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

async def insert_single_document():
    """Insert a single document into knowledge graph."""
    lightrag = LightRAGWrapper()

    document_text = """
    The Python programming language was created by Guido van Rossum in 1991.
    Python is widely used for web development, data science, and machine learning.
    Popular frameworks include Django for web development and PyTorch for deep learning.
    """

    result = await lightrag.insert_text(document_text)

    print(f"Document inserted successfully")
    print(f"Result: {result}")

asyncio.run(insert_single_document())
```

### Example 2: Batch Insert Multiple Documents

```python
async def insert_multiple_documents():
    """Insert multiple documents in batch."""
    lightrag = LightRAGWrapper()

    documents = [
        {
            "text": "RAG (Retrieval-Augmented Generation) combines search with LLM generation.",
            "metadata": {"source": "doc1.txt", "topic": "RAG"}
        },
        {
            "text": "Vector databases like Qdrant enable fast similarity search for embeddings.",
            "metadata": {"source": "doc2.txt", "topic": "vector_search"}
        },
        {
            "text": "Neo4j is a graph database optimized for storing entities and relationships.",
            "metadata": {"source": "doc3.txt", "topic": "graph_db"}
        },
    ]

    result = await lightrag.insert_documents(documents)

    print(f"Batch insert completed:")
    print(f"  Total: {result['total']}")
    print(f"  Success: {result['success']}")
    print(f"  Failed: {result['failed']}")

asyncio.run(insert_multiple_documents())
```

### Example 3: Insert from File

```python
from pathlib import Path

async def insert_from_file():
    """Insert documents from a directory."""
    from llama_index.core import SimpleDirectoryReader

    lightrag = LightRAGWrapper()

    # Load documents using LlamaIndex
    reader = SimpleDirectoryReader(
        input_dir="./data/documents",
        recursive=True,
        required_exts=[".txt", ".md", ".pdf"]
    )
    docs = reader.load_data()

    print(f"Loaded {len(docs)} documents")

    # Convert to format for LightRAG
    documents = [
        {"text": doc.text, "metadata": doc.metadata}
        for doc in docs
    ]

    # Insert into graph
    result = await lightrag.insert_documents(documents)

    print(f"Inserted {result['success']}/{result['total']} documents successfully")

asyncio.run(insert_from_file())
```

---

## Entity Extraction Examples

### Example 1: Extract Entities from Text

```python
from src.components.graph_rag.extraction import ExtractionPipeline

async def extract_entities_example():
    """Extract entities from text."""
    pipeline = ExtractionPipeline()

    text = """
    OpenAI released GPT-4 in March 2023, a large language model with impressive capabilities.
    GPT-4 was trained on a mixture of licensed data, data created by human trainers,
    and publicly available data. Sam Altman is the CEO of OpenAI.
    """

    entities = await pipeline.extract_entities(text, document_id="doc_openai")

    print(f"Extracted {len(entities)} entities:\n")
    for entity in entities:
        print(f"  Name: {entity.name}")
        print(f"  Type: {entity.type}")
        print(f"  Description: {entity.description}")
        print(f"  Source: {entity.source_document}")
        print()

asyncio.run(extract_entities_example())
```

**Expected Output:**
```
Extracted 4 entities:

  Name: OpenAI
  Type: Organization
  Description: AI research company that released GPT-4
  Source: doc_openai

  Name: GPT-4
  Type: Technology
  Description: Large language model released in March 2023
  Source: doc_openai

  Name: Sam Altman
  Type: Person
  Description: CEO of OpenAI
  Source: doc_openai

  Name: March 2023
  Type: Event
  Description: Release date of GPT-4
  Source: doc_openai
```

### Example 2: Entity Types Supported

```python
async def entity_types_example():
    """Demonstrate supported entity types."""
    pipeline = ExtractionPipeline()

    text = """
    - Person: John Smith, Jane Doe
    - Organization: Google, Microsoft, United Nations
    - Location: San Francisco, California, United States
    - Technology: Python, TensorFlow, Neo4j
    - Product: iPhone, Windows 11, Tesla Model 3
    - Concept: Machine Learning, Artificial Intelligence, RAG
    - Event: WWDC 2023, Olympic Games 2024
    - Date: January 15, 2023, Q4 2024
    """

    entities = await pipeline.extract_entities(text, "doc_types")

    # Group entities by type
    by_type = {}
    for entity in entities:
        by_type.setdefault(entity.type, []).append(entity.name)

    print("Entities by Type:\n")
    for entity_type, names in sorted(by_type.items()):
        print(f"{entity_type}:")
        for name in names:
            print(f"  - {name}")
        print()

asyncio.run(entity_types_example())
```

### Example 3: Batch Entity Extraction

```python
async def batch_entity_extraction():
    """Extract entities from multiple documents."""
    pipeline = ExtractionPipeline()

    documents = [
        {"id": "doc1", "text": "Tesla was founded by Elon Musk. Tesla produces electric vehicles."},
        {"id": "doc2", "text": "SpaceX, also founded by Elon Musk, focuses on space exploration."},
        {"id": "doc3", "text": "Elon Musk is the CEO of Tesla and SpaceX."},
    ]

    all_entities, _ = await pipeline.extract_from_documents(documents)

    print(f"Extracted {len(all_entities)} total entities from {len(documents)} documents\n")

    # Find entities that appear in multiple documents
    entity_counts = {}
    for entity in all_entities:
        entity_counts[entity.name] = entity_counts.get(entity.name, 0) + 1

    print("Entities appearing in multiple documents:")
    for name, count in sorted(entity_counts.items(), key=lambda x: -x[1]):
        if count > 1:
            print(f"  {name}: {count} times")

asyncio.run(batch_entity_extraction())
```

**Expected Output:**
```
Extracted 5 total entities from 3 documents

Entities appearing in multiple documents:
  Elon Musk: 3 times
  Tesla: 2 times
  SpaceX: 2 times
```

---

## Relationship Extraction Examples

### Example 1: Extract Relationships

```python
async def extract_relationships_example():
    """Extract relationships from text."""
    pipeline = ExtractionPipeline()

    text = """
    John Smith works at Google as a senior software engineer.
    He reports to Sarah Johnson, who is the Director of Engineering.
    Google is headquartered in Mountain View, California.
    John previously worked at Microsoft from 2015 to 2020.
    """

    # First extract entities
    entities = await pipeline.extract_entities(text, "doc_relationships")

    # Then extract relationships
    relationships = await pipeline.extract_relationships(text, entities, "doc_relationships")

    print(f"Extracted {len(relationships)} relationships:\n")
    for rel in relationships:
        print(f"  {rel.source} --[{rel.type}]--> {rel.target}")
        print(f"    Description: {rel.description}")
        print()

asyncio.run(extract_relationships_example())
```

**Expected Output:**
```
Extracted 4 relationships:

  John Smith --[WORKS_AT]--> Google
    Description: John Smith is employed at Google as a senior software engineer

  John Smith --[REPORTS_TO]--> Sarah Johnson
    Description: John Smith reports to Sarah Johnson in the organization hierarchy

  Sarah Johnson --[WORKS_AT]--> Google
    Description: Sarah Johnson works at Google as Director of Engineering

  Google --[LOCATED_IN]--> Mountain View
    Description: Google's headquarters are located in Mountain View, California
```

### Example 2: Common Relationship Types

```python
async def relationship_types_example():
    """Demonstrate common relationship types."""
    pipeline = ExtractionPipeline()

    examples = {
        "WORKS_AT": "Alice works at Microsoft.",
        "KNOWS": "Alice knows Bob through their work at Microsoft.",
        "LOCATED_IN": "Microsoft is located in Redmond, Washington.",
        "CREATED": "Guido van Rossum created the Python programming language.",
        "USES": "Data scientists use Python for machine learning.",
        "PART_OF": "Azure is part of Microsoft's cloud computing platform.",
        "MANAGES": "Satya Nadella manages Microsoft as its CEO.",
        "FOUNDED": "Bill Gates founded Microsoft in 1975.",
    }

    for rel_type, text in examples.items():
        entities = await pipeline.extract_entities(text, f"doc_{rel_type}")
        relationships = await pipeline.extract_relationships(text, entities, f"doc_{rel_type}")

        if relationships:
            rel = relationships[0]
            print(f"{rel_type}:")
            print(f"  {rel.source} --[{rel.type}]--> {rel.target}")
            print()

asyncio.run(relationship_types_example())
```

### Example 3: Full Document Extraction (Entities + Relationships)

```python
async def full_document_extraction():
    """Extract entities and relationships from document."""
    pipeline = ExtractionPipeline()

    text = """
    LangChain is a framework for developing applications powered by language models.
    It was created by Harrison Chase in 2022. LangChain enables developers to build
    LLM applications with features like prompt management, chains, and agents.
    The framework integrates with OpenAI's GPT models and open-source alternatives.
    """

    entities, relationships = await pipeline.extract_from_document(text, "doc_langchain")

    print(f"Document: doc_langchain")
    print(f"  Entities extracted: {len(entities)}")
    print(f"  Relationships extracted: {len(relationships)}")
    print()

    print("Entities:")
    for entity in entities:
        print(f"  - {entity.name} ({entity.type})")
    print()

    print("Relationships:")
    for rel in relationships:
        print(f"  - {rel.source} --[{rel.type}]--> {rel.target}")

asyncio.run(full_document_extraction())
```

---

## Graph Query Examples

### Example 1: Local Search (Entity-Level)

```python
async def local_search_example():
    """Local search: entity-level retrieval."""
    lightrag = LightRAGWrapper()

    # Query for specific entity information
    queries = [
        "What companies has John Smith worked for?",
        "Who is the CEO of OpenAI?",
        "Where is Google headquartered?",
    ]

    for query in queries:
        result = await lightrag.query(query, mode="local")

        print(f"Query: {query}")
        print(f"Answer: {result.answer}")
        print(f"Mode: {result.mode}")
        print()

asyncio.run(local_search_example())
```

**Expected Output:**
```
Query: What companies has John Smith worked for?
Answer: John Smith has worked for Google and previously worked at Microsoft from 2015 to 2020.
Mode: local

Query: Who is the CEO of OpenAI?
Answer: Sam Altman is the CEO of OpenAI.
Mode: local

Query: Where is Google headquartered?
Answer: Google is headquartered in Mountain View, California.
Mode: local
```

### Example 2: Global Search (Topic-Level)

```python
async def global_search_example():
    """Global search: topic-level retrieval."""
    lightrag = LightRAGWrapper()

    # Query for high-level topics and summaries
    queries = [
        "What are the main themes in the corpus?",
        "Summarize the key concepts about machine learning.",
        "What technologies are mentioned most frequently?",
    ]

    for query in queries:
        result = await lightrag.query(query, mode="global")

        print(f"Query: {query}")
        print(f"Answer: {result.answer}")
        print(f"Mode: {result.mode}")
        print()

asyncio.run(global_search_example())
```

**Expected Output:**
```
Query: What are the main themes in the corpus?
Answer: The main themes include artificial intelligence, software engineering,
        technology companies (Google, Microsoft), and programming languages (Python).
Mode: global

Query: Summarize the key concepts about machine learning.
Answer: Machine learning is a subfield of AI involving algorithms that learn from data.
        Key technologies include Python, TensorFlow, and PyTorch. It's widely used
        in data science and by companies like Google and OpenAI.
Mode: global
```

### Example 3: Hybrid Search (Combined)

```python
async def hybrid_search_example():
    """Hybrid search: combined local + global."""
    lightrag = LightRAGWrapper()

    # Complex queries that benefit from both entity-level and topic-level retrieval
    query = """
    What is the relationship between Google and machine learning,
    and who are the key people involved?
    """

    result = await lightrag.query(query, mode="hybrid")

    print(f"Query: {query}")
    print(f"Answer: {result.answer}")
    print(f"Mode: {result.mode}")
    print()
    print("Metadata:")
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")

asyncio.run(hybrid_search_example())
```

---

## Dual-Level Retrieval Examples

### Example 1: Compare Search Modes

```python
async def compare_search_modes():
    """Compare local, global, and hybrid search for the same query."""
    from src.components.graph_rag.search import GraphSearch
    from src.components.graph_rag.neo4j_client import Neo4jClientWrapper

    lightrag = LightRAGWrapper()
    neo4j = Neo4jClientWrapper()
    search = GraphSearch(lightrag, neo4j)

    query = "What is known about artificial intelligence?"

    # Execute all three modes
    local_result = await search.search_local(query)
    global_result = await search.search_global(query)
    hybrid_result = await search.search_hybrid(query)

    print(f"Query: {query}\n")

    print("LOCAL SEARCH (entity-level):")
    print(f"  Answer: {local_result['answer'][:200]}...")
    print()

    print("GLOBAL SEARCH (topic-level):")
    print(f"  Answer: {global_result['answer'][:200]}...")
    print()

    print("HYBRID SEARCH (combined):")
    print(f"  Answer: {hybrid_result['answer'][:200]}...")
    print()

asyncio.run(compare_search_modes())
```

### Example 2: Entity-Level vs Topic-Level

```python
async def entity_vs_topic_search():
    """Demonstrate when to use local vs global search."""
    search = GraphSearch(lightrag_wrapper, neo4j_client)

    # Entity-focused query → Local search
    entity_query = "Who is the founder of Tesla?"
    local_result = await search.search_local(entity_query)
    print(f"Entity Query: {entity_query}")
    print(f"Local Search Answer: {local_result['answer']}\n")

    # Topic-focused query → Global search
    topic_query = "What is the general landscape of electric vehicles?"
    global_result = await search.search_global(topic_query)
    print(f"Topic Query: {topic_query}")
    print(f"Global Search Answer: {global_result['answer']}\n")

asyncio.run(entity_vs_topic_search())
```

### Example 3: Multi-Hop Graph Traversal

```python
async def multi_hop_search():
    """Multi-hop graph traversal example."""
    search = GraphSearch(lightrag_wrapper, neo4j_client)

    # Query requiring multi-hop reasoning
    query = "What companies are connected to people who know Elon Musk?"

    # Local search with increased max_hops
    result = await search.search_local(
        query,
        max_hops=2,  # Traverse 2 hops: Elon → People → Companies
        top_k=10
    )

    print(f"Query: {query}")
    print(f"Answer: {result['answer']}")
    print(f"\nEntities found: {len(result.get('entities', []))}")
    print(f"Relationships traversed: {len(result.get('relationships', []))}")

asyncio.run(multi_hop_search())
```

---

## Graph Query Agent Examples

### Example 1: Graph Query Agent Standalone

```python
async def graph_query_agent_example():
    """Use Graph Query Agent standalone."""
    from src.agents.graph_query_agent import GraphQueryAgent
    from src.agents.state import AgentState
    from src.components.graph_rag.search import GraphSearch

    # Initialize dependencies
    lightrag = LightRAGWrapper()
    neo4j = Neo4jClientWrapper()
    search = GraphSearch(lightrag, neo4j)

    # Create agent
    agent = GraphQueryAgent(search)

    # Create state
    state = AgentState(
        query="What technologies does Google use for machine learning?",
        intent="graph",
        config={"top_k": 10}
    )

    # Process query
    result_state = await agent.process(state)

    print(f"Query: {result_state.query}")
    print(f"Intent: {result_state.intent}")
    print(f"Answer: {result_state.graph_results['answer']}")
    print(f"Agent Path: {result_state.metadata['agent_path']}")

asyncio.run(graph_query_agent_example())
```

**Expected Output:**
```
Query: What technologies does Google use for machine learning?
Intent: graph
Answer: Google uses TensorFlow, a popular machine learning framework created by Google,
        along with Python for data science and machine learning applications.
Agent Path: ['graph_query']
```

### Example 2: Graph Query Agent with Error Handling

```python
async def graph_query_agent_with_errors():
    """Test error handling and fallback."""
    agent = GraphQueryAgent(search)

    # Simulate error by querying non-existent entity
    state = AgentState(
        query="Tell me about XYZ Corporation that doesn't exist",
        intent="graph",
    )

    result_state = await agent.process(state)

    if result_state.error:
        print(f"Error occurred: {result_state.error}")
        print(f"Fallback to vector: {result_state.fallback_to_vector}")
    else:
        print(f"Answer: {result_state.graph_results['answer']}")

asyncio.run(graph_query_agent_with_errors())
```

### Example 3: Search Mode Selection

```python
async def search_mode_selection_example():
    """Demonstrate automatic search mode selection."""
    agent = GraphQueryAgent(search)

    queries = [
        ("Who is John Smith?", "local"),  # Entity name → local
        ("What are the main themes?", "global"),  # Broad question → global
        ("How are Google and AI related?", "hybrid"),  # Complex → hybrid
    ]

    for query, expected_mode in queries:
        state = AgentState(query=query, intent="graph")
        result_state = await agent.process(state)

        selected_mode = result_state.metadata.get("graph_search_mode")

        print(f"Query: {query}")
        print(f"  Expected Mode: {expected_mode}")
        print(f"  Selected Mode: {selected_mode}")
        print(f"  Match: {'✓' if selected_mode == expected_mode else '✗'}")
        print()

asyncio.run(search_mode_selection_example())
```

---

## Incremental Updates Examples

### Example 1: Add New Documents Incrementally

```python
async def incremental_update_example():
    """Add new documents without full graph rebuild."""
    from src.components.graph_rag.incremental import IncrementalGraphUpdater

    lightrag = LightRAGWrapper()
    pipeline = ExtractionPipeline()
    updater = IncrementalGraphUpdater(lightrag, pipeline)

    # Initial graph construction
    initial_docs = [
        {"id": "doc1", "text": "Python is a programming language.", "metadata": {}},
        {"id": "doc2", "text": "Java is a programming language.", "metadata": {}},
    ]

    print("Initial graph construction...")
    for doc in initial_docs:
        await lightrag.insert_text(doc["text"])

    initial_count = await lightrag.get_entity_count()
    print(f"Initial entity count: {initial_count}\n")

    # Add new documents incrementally
    new_docs = [
        {"id": "doc3", "text": "JavaScript is a programming language.", "metadata": {}},
        {"id": "doc4", "text": "TypeScript is a superset of JavaScript.", "metadata": {}},
    ]

    print("Incremental update...")
    result = await updater.insert_new_documents(initial_docs + new_docs)

    print(f"Update status: {result['status']}")
    print(f"Total docs: {result['total_docs']}")
    print(f"New docs: {result['new_docs']}")
    print(f"Entities added: {result['entities_added']}")
    print(f"Relationships added: {result['relationships_added']}")

    final_count = await lightrag.get_entity_count()
    print(f"\nFinal entity count: {final_count}")
    print(f"Entities added: {final_count - initial_count}")

asyncio.run(incremental_update_example())
```

**Expected Output:**
```
Initial graph construction...
Initial entity count: 4

Incremental update...
Update status: success
Total docs: 4
New docs: 2
Entities added: 3
Relationships added: 2

Final entity count: 7
Entities added: 3
```

### Example 2: Detect Already Indexed Documents

```python
async def detect_indexed_documents():
    """Demonstrate detection of already indexed documents."""
    updater = IncrementalGraphUpdater(lightrag, pipeline)

    # Get list of indexed documents
    indexed_docs = await updater.get_indexed_documents()
    print(f"Already indexed documents: {indexed_docs}\n")

    # Try to add documents (some already indexed)
    documents = [
        {"id": "doc1", "text": "Already indexed", "metadata": {}},
        {"id": "doc5", "text": "New document", "metadata": {}},
    ]

    result = await updater.insert_new_documents(documents)

    print(f"Result:")
    print(f"  Total submitted: {result['total_docs']}")
    print(f"  New docs processed: {result['new_docs']}")
    print(f"  Skipped (already indexed): {result['total_docs'] - result['new_docs']}")

asyncio.run(detect_indexed_documents())
```

### Example 3: Performance Comparison (Incremental vs Full Rebuild)

```python
import time

async def performance_comparison():
    """Compare incremental update vs full rebuild performance."""

    # Initial corpus (100 documents)
    initial_corpus = [
        {"id": f"doc{i}", "text": f"Document {i} about topic {i % 10}."}
        for i in range(100)
    ]

    # New documents (10 more)
    new_documents = [
        {"id": f"doc{i}", "text": f"New document {i} about topic {i % 10}."}
        for i in range(100, 110)
    ]

    # Measure full rebuild time
    lightrag_full = LightRAGWrapper(working_dir="./data/lightrag_full")
    start = time.time()
    await lightrag_full.insert_documents(initial_corpus + new_documents)
    full_rebuild_time = time.time() - start

    # Measure incremental update time
    lightrag_incr = LightRAGWrapper(working_dir="./data/lightrag_incr")
    await lightrag_incr.insert_documents(initial_corpus)  # Initial build

    updater = IncrementalGraphUpdater(lightrag_incr, pipeline)
    start = time.time()
    await updater.insert_new_documents(initial_corpus + new_documents)
    incremental_time = time.time() - start

    print("Performance Comparison:")
    print(f"  Full rebuild (110 docs): {full_rebuild_time:.2f}s")
    print(f"  Incremental (10 new docs): {incremental_time:.2f}s")
    print(f"  Speedup: {full_rebuild_time / incremental_time:.1f}x")

asyncio.run(performance_comparison())
```

**Expected Output:**
```
Performance Comparison:
  Full rebuild (110 docs): 650.00s
  Incremental (10 new docs): 60.00s
  Speedup: 10.8x
```

---

## Neo4j Cypher Query Examples

### Example 1: Find All Entities

```cypher
// Find all entities in the graph
MATCH (e:Entity)
RETURN e.name AS name, e.type AS type, e.description AS description
LIMIT 25
```

### Example 2: Find Entities by Type

```cypher
// Find all Person entities
MATCH (p:Entity {type: 'Person'})
RETURN p.name AS name, p.description AS description
ORDER BY p.name

// Find all Organization entities
MATCH (o:Entity {type: 'Organization'})
RETURN o.name AS name, o.description AS description
ORDER BY o.name
```

### Example 3: Find Relationships of a Specific Type

```cypher
// Find all WORKS_AT relationships
MATCH (p:Entity)-[r:WORKS_AT]->(o:Entity)
RETURN p.name AS person, o.name AS organization
ORDER BY p.name

// Find all LOCATED_IN relationships
MATCH (e:Entity)-[r:LOCATED_IN]->(l:Entity)
RETURN e.name AS entity, l.name AS location
ORDER BY e.name
```

### Example 4: Multi-Hop Traversal

```cypher
// Find entities connected to "John Smith" within 2 hops
MATCH path = (start:Entity {name: 'John Smith'})-[*1..2]-(connected)
RETURN DISTINCT connected.name AS name, connected.type AS type

// Find all people who work at the same companies as "John Smith"
MATCH (john:Entity {name: 'John Smith'})-[:WORKS_AT]->(company:Entity)
MATCH (colleague:Entity)-[:WORKS_AT]->(company)
WHERE colleague.name <> 'John Smith'
RETURN DISTINCT colleague.name AS colleague, company.name AS company
```

### Example 5: Entity Co-occurrence

```cypher
// Find entities that appear together in relationships
MATCH (e1:Entity)-[r]-(e2:Entity)
RETURN e1.name AS entity1, type(r) AS relationship, e2.name AS entity2
ORDER BY e1.name, e2.name
LIMIT 50
```

### Example 6: Graph Statistics

```cypher
// Count entities by type
MATCH (e:Entity)
RETURN e.type AS type, count(e) AS count
ORDER BY count DESC

// Count relationships by type
MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(r) AS count
ORDER BY count DESC

// Find most connected entities (degree centrality)
MATCH (e:Entity)-[r]-()
RETURN e.name AS entity, e.type AS type, count(r) AS connections
ORDER BY connections DESC
LIMIT 10
```

### Example 7: Community Detection (Leiden Algorithm)

```cypher
// Create in-memory graph projection
CALL gds.graph.project(
  'myGraph',
  'Entity',
  {RELATED_TO: {orientation: 'UNDIRECTED'}}
)

// Run Leiden community detection
CALL gds.leiden.stream('myGraph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS name,
       gds.util.asNode(nodeId).type AS type,
       communityId
ORDER BY communityId, name

// Drop graph projection (cleanup)
CALL gds.graph.drop('myGraph')
```

### Example 8: Full-Text Search

```cypher
// Create full-text index (run once)
CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description]

// Search entities by keyword
CALL db.index.fulltext.queryNodes('entity_fulltext', 'machine learning')
YIELD node, score
RETURN node.name AS name, node.type AS type, node.description AS description, score
ORDER BY score DESC
LIMIT 10
```

### Example 9: Shortest Path Between Entities

```cypher
// Find shortest path between two entities
MATCH path = shortestPath(
  (start:Entity {name: 'John Smith'})-[*]-(end:Entity {name: 'Google'})
)
RETURN path

// Find all paths between two entities (max 3 hops)
MATCH path = (start:Entity {name: 'John Smith'})-[*1..3]-(end:Entity {name: 'Machine Learning'})
RETURN path
LIMIT 5
```

### Example 10: Delete Test Data

```cypher
// Delete all test entities
MATCH (n:TestEntity)
DETACH DELETE n

// Delete specific entity and its relationships
MATCH (e:Entity {name: 'Test Entity'})
DETACH DELETE e

// Delete all entities and relationships (DANGER: clears entire graph!)
MATCH (n)
DETACH DELETE n
```

---

## Integration with Sprint 4 Router

### Example 1: Full Router → Graph Agent Flow

```python
async def router_to_graph_agent_flow():
    """Demonstrate full flow: User query → Router → Graph Agent → Response."""
    from src.agents.coordinator import AgentCoordinator
    from src.agents.state import AgentState

    # Initialize coordinator (includes router and all agents)
    coordinator = AgentCoordinator()

    # User query that should route to GRAPH intent
    query = "What companies has John Smith worked for?"

    # Create initial state
    state = AgentState(query=query)

    # Process through coordinator
    result_state = await coordinator.process(state)

    # Check routing and results
    print(f"Query: {query}")
    print(f"Classified Intent: {result_state.intent}")
    print(f"Agent Path: {result_state.metadata.get('agent_path', [])}")
    print(f"Answer: {result_state.graph_results['answer']}")

    assert result_state.intent == "graph", "Should route to GRAPH intent"
    assert "graph_query" in result_state.metadata["agent_path"], "Should execute graph_query agent"

asyncio.run(router_to_graph_agent_flow())
```

**Expected Output:**
```
Query: What companies has John Smith worked for?
Classified Intent: graph
Agent Path: ['router', 'graph_query', 'generate']
Answer: John Smith has worked for Google and previously worked at Microsoft.
```

### Example 2: GRAPH vs VECTOR Intent Routing

```python
async def graph_vs_vector_routing():
    """Compare queries that route to GRAPH vs VECTOR."""
    coordinator = AgentCoordinator()

    test_cases = [
        # GRAPH intent: Entity-centric queries
        ("Who is the CEO of OpenAI?", "graph"),
        ("What companies does Elon Musk own?", "graph"),
        ("Where is Microsoft headquartered?", "graph"),

        # VECTOR intent: Semantic search queries
        ("Explain how RAG works", "vector"),
        ("What are the best practices for vector search?", "vector"),
        ("Compare BM25 and dense retrieval", "vector"),
    ]

    for query, expected_intent in test_cases:
        state = AgentState(query=query)
        result_state = await coordinator.process(state)

        match = "✓" if result_state.intent == expected_intent else "✗"
        print(f"{match} Query: {query}")
        print(f"    Expected: {expected_intent}, Got: {result_state.intent}")
        print()

asyncio.run(graph_vs_vector_routing())
```

### Example 3: Fallback from Graph to Vector

```python
async def graph_to_vector_fallback():
    """Demonstrate fallback when graph query fails."""
    coordinator = AgentCoordinator()

    # Query about entity not in graph
    query = "What is the capital of non-existent country XYZ?"

    state = AgentState(query=query)
    result_state = await coordinator.process(state)

    if result_state.fallback_to_vector:
        print(f"Graph query failed, fell back to vector search")
        print(f"Agent Path: {result_state.metadata['agent_path']}")
        # Expected: ['router', 'graph_query', 'vector_search', 'generate']
    else:
        print(f"Graph query succeeded")

asyncio.run(graph_to_vector_fallback())
```

---

## Production Pipeline Example

### Complete Production Pipeline

```python
"""
Production-ready pipeline for graph-based RAG.

This example demonstrates a full production pipeline:
1. Document ingestion from directory
2. Entity/relationship extraction
3. Graph construction
4. Query handling with routing
5. Incremental updates
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any

import structlog
from llama_index.core import SimpleDirectoryReader

from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper
from src.components.graph_rag.extraction import ExtractionPipeline
from src.components.graph_rag.incremental import IncrementalGraphUpdater
from src.components.graph_rag.search import GraphSearch
from src.components.graph_rag.neo4j_client import Neo4jClientWrapper
from src.agents.coordinator import AgentCoordinator

logger = structlog.get_logger(__name__)


class GraphRAGProductionPipeline:
    """Production pipeline for graph-based RAG."""

    def __init__(self, document_dir: str, working_dir: str = "./data/lightrag"):
        """Initialize pipeline.

        Args:
            document_dir: Directory containing documents to index
            working_dir: LightRAG working directory
        """
        self.document_dir = Path(document_dir)
        self.working_dir = Path(working_dir)

        # Initialize components
        self.lightrag = LightRAGWrapper(working_dir=str(self.working_dir))
        self.extraction_pipeline = ExtractionPipeline()
        self.neo4j_client = Neo4jClientWrapper()
        self.search = GraphSearch(self.lightrag, self.neo4j_client)
        self.updater = IncrementalGraphUpdater(self.lightrag, self.extraction_pipeline)
        self.coordinator = AgentCoordinator()

        logger.info(
            "production_pipeline_initialized",
            document_dir=str(self.document_dir),
            working_dir=str(self.working_dir),
        )

    async def ingest_documents(self, recursive: bool = True) -> Dict[str, Any]:
        """Ingest documents from directory.

        Args:
            recursive: Whether to search subdirectories

        Returns:
            Ingestion statistics
        """
        logger.info("ingestion_started", document_dir=str(self.document_dir))

        # Load documents using LlamaIndex
        reader = SimpleDirectoryReader(
            input_dir=str(self.document_dir),
            recursive=recursive,
            required_exts=[".txt", ".md", ".pdf", ".docx"],
        )
        docs = reader.load_data()

        logger.info("documents_loaded", count=len(docs))

        # Convert to format for incremental updater
        documents = [
            {
                "id": doc.doc_id or f"doc_{i}",
                "text": doc.text,
                "metadata": doc.metadata or {},
            }
            for i, doc in enumerate(docs)
        ]

        # Incremental insertion (skips already indexed)
        result = await self.updater.insert_new_documents(documents)

        logger.info(
            "ingestion_complete",
            total=result["total_docs"],
            new=result["new_docs"],
            entities_added=result.get("entities_added", 0),
            relationships_added=result.get("relationships_added", 0),
        )

        return result

    async def query(self, query: str, mode: str = "auto") -> Dict[str, Any]:
        """Query the knowledge graph.

        Args:
            query: User query
            mode: Search mode ("auto", "local", "global", "hybrid")

        Returns:
            Query result with answer and metadata
        """
        logger.info("query_started", query=query[:100], mode=mode)

        if mode == "auto":
            # Use coordinator for automatic routing
            from src.agents.state import AgentState

            state = AgentState(query=query)
            result_state = await self.coordinator.process(state)

            return {
                "query": query,
                "intent": result_state.intent,
                "answer": result_state.final_answer or result_state.graph_results.get("answer", ""),
                "agent_path": result_state.metadata.get("agent_path", []),
                "mode": result_state.metadata.get("graph_search_mode", "unknown"),
            }
        else:
            # Direct graph search
            result = await self.search.search(query, mode=mode)

            return {
                "query": query,
                "mode": mode,
                "answer": result["answer"],
                "entities": result.get("entities", []),
                "relationships": result.get("relationships", []),
            }

    async def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics.

        Returns:
            Statistics dict with entity/relationship counts
        """
        entity_count = await self.neo4j_client.get_node_count(label="Entity")
        relationship_count = await self.neo4j_client.get_relationship_count()
        document_count = await self.neo4j_client.get_node_count(label="Document")

        # Get entity types breakdown
        results = await self.neo4j_client.execute_read(
            """
            MATCH (e:Entity)
            RETURN e.type AS type, count(e) AS count
            ORDER BY count DESC
            """
        )
        entity_types = {r["type"]: r["count"] for r in results}

        # Get relationship types breakdown
        results = await self.neo4j_client.execute_read(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(r) AS count
            ORDER BY count DESC
            """
        )
        relationship_types = {r["type"]: r["count"] for r in results}

        return {
            "entities": {
                "total": entity_count,
                "by_type": entity_types,
            },
            "relationships": {
                "total": relationship_count,
                "by_type": relationship_types,
            },
            "documents": document_count,
        }

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all components.

        Returns:
            Health status dict
        """
        lightrag_healthy = await self.lightrag.health_check()
        neo4j_healthy = await self.neo4j_client.health_check()

        return {
            "lightrag": lightrag_healthy,
            "neo4j": neo4j_healthy,
            "overall": lightrag_healthy and neo4j_healthy,
        }


async def main():
    """Main production pipeline example."""

    # Initialize pipeline
    pipeline = GraphRAGProductionPipeline(
        document_dir="./data/documents",
        working_dir="./data/lightrag_prod",
    )

    # Health check
    print("Performing health check...")
    health = await pipeline.health_check()
    print(f"Health Status: {health}\n")

    if not health["overall"]:
        print("ERROR: System not healthy. Exiting.")
        return

    # Ingest documents
    print("Ingesting documents...")
    ingest_result = await pipeline.ingest_documents()
    print(f"Ingestion Result:")
    print(f"  Total documents: {ingest_result['total_docs']}")
    print(f"  New documents: {ingest_result['new_docs']}")
    print(f"  Entities added: {ingest_result.get('entities_added', 0)}")
    print(f"  Relationships added: {ingest_result.get('relationships_added', 0)}")
    print()

    # Get statistics
    print("Graph Statistics:")
    stats = await pipeline.get_statistics()
    print(f"  Entities: {stats['entities']['total']}")
    print(f"  Relationships: {stats['relationships']['total']}")
    print(f"  Documents: {stats['documents']}")
    print()

    # Query examples
    queries = [
        "Who is John Smith?",
        "What companies are mentioned in the corpus?",
        "How is machine learning related to Python?",
    ]

    print("Running queries...")
    for query in queries:
        result = await pipeline.query(query, mode="auto")
        print(f"\nQuery: {query}")
        print(f"Intent: {result.get('intent', 'N/A')}")
        print(f"Answer: {result['answer'][:200]}...")
        print(f"Mode: {result.get('mode', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected Output:**
```
Performing health check...
Health Status: {'lightrag': True, 'neo4j': True, 'overall': True}

Ingesting documents...
Ingestion Result:
  Total documents: 150
  New documents: 25
  Entities added: 120
  Relationships added: 85

Graph Statistics:
  Entities: 487
  Relationships: 312
  Documents: 150

Running queries...

Query: Who is John Smith?
Intent: graph
Answer: John Smith is a senior software engineer at Google, specializing in machine learning...
Mode: local

Query: What companies are mentioned in the corpus?
Intent: graph
Answer: The corpus mentions several technology companies including Google, Microsoft, OpenAI, Tesla...
Mode: global

Query: How is machine learning related to Python?
Intent: graph
Answer: Machine learning is strongly related to Python as Python is widely used for ML development...
Mode: hybrid
```

---

## Summary

This document provided comprehensive examples for Sprint 5 (LightRAG Integration):

1. **Graph Construction:** Insert documents, batch processing, file loading
2. **Entity Extraction:** Single/batch extraction, entity types, JSON parsing
3. **Relationship Extraction:** Types, patterns, full document extraction
4. **Graph Queries:** Local (entity-level), global (topic-level), hybrid search
5. **Dual-Level Retrieval:** Mode comparison, multi-hop traversal
6. **Graph Query Agent:** Standalone usage, error handling, mode selection
7. **Incremental Updates:** New documents, deduplication, performance
8. **Neo4j Cypher:** Direct database queries, statistics, full-text search
9. **Router Integration:** Intent routing, fallback logic
10. **Production Pipeline:** End-to-end production-ready implementation

All examples are production-ready and can be used as templates for your own implementations.

For more information:
- SPRINT_5_PLAN.md (high-level plan)
- SPRINT_5_IMPLEMENTATION_GUIDE.md (step-by-step guide)
- LightRAG documentation: https://github.com/HKUDS/LightRAG
- Neo4j Cypher manual: https://neo4j.com/docs/cypher-manual/
