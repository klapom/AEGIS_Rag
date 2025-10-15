# Sprint 3 Feature Usage Examples

This document provides practical code examples for using Sprint 3 advanced retrieval features.

---

## Table of Contents

1. [Cross-Encoder Reranking](#1-cross-encoder-reranking)
2. [Query Decomposition](#2-query-decomposition)
3. [Metadata Filtering](#3-metadata-filtering)
4. [Adaptive Chunking](#4-adaptive-chunking)
5. [RAGAS Evaluation](#5-ragas-evaluation)
6. [Combined Example: All Features](#6-combined-example-all-features)

---

## 1. Cross-Encoder Reranking

Reranking improves precision by rescoring query-document pairs with a cross-encoder model.

### Basic Reranking

```python
from src.components.retrieval.reranker import CrossEncoderReranker

# Initialize reranker
reranker = CrossEncoderReranker()

# Get initial search results
search_results = [
    {"id": "doc1", "text": "Vector search uses embeddings for semantic similarity.", "score": 0.82},
    {"id": "doc2", "text": "BM25 is a keyword-based search algorithm.", "score": 0.78},
    {"id": "doc3", "text": "Hybrid search combines vector and keyword approaches.", "score": 0.75},
]

# Rerank results
reranked = await reranker.rerank(
    query="What is vector search?",
    documents=search_results,
    top_k=3
)

# Print reranked results
for result in reranked:
    print(f"Rank {result.final_rank}: {result.doc_id}")
    print(f"  Original Score: {result.original_score:.3f}")
    print(f"  Rerank Score: {result.final_score:.3f}")
    print(f"  Text: {result.text[:80]}...")
    print()
```

### Reranking with Score Threshold

```python
# Only keep results above threshold
reranked = await reranker.rerank(
    query="What is vector search?",
    documents=search_results,
    top_k=5,
    score_threshold=0.7  # Filter low-relevance results
)

print(f"Kept {len(reranked)} results above threshold 0.7")
```

### Custom Model Configuration

```python
# Use different cross-encoder model
reranker = CrossEncoderReranker(
    model_name="cross-encoder/ms-marco-TinyBERT-L-6",  # Faster, smaller model
    batch_size=16,
    cache_dir="./models/reranker"
)
```

### Reranker Information

```python
# Get model info
info = reranker.get_model_info()
print(f"Model: {info['model_name']}")
print(f"Loaded: {info['is_loaded']}")
print(f"Cache Dir: {info['cache_dir']}")
```

---

## 2. Query Decomposition

Query decomposition handles complex multi-part questions by breaking them into simpler sub-queries.

### Basic Decomposition

```python
from src.components.retrieval.query_decomposition import QueryDecomposer

# Initialize decomposer
decomposer = QueryDecomposer()

# Classify and decompose complex query
result = await decomposer.decompose(
    query="What is vector search and how does BM25 compare to it?"
)

print(f"Query Type: {result.classification.query_type}")
print(f"Confidence: {result.classification.confidence:.2f}")
print(f"Execution Strategy: {result.execution_strategy}")
print("\nSub-queries:")
for sq in result.sub_queries:
    print(f"  {sq.index}: {sq.query}")
    if sq.depends_on:
        print(f"     Depends on: {sq.depends_on}")
```

### Decompose and Search

```python
from src.components.vector_search.hybrid_search import HybridSearch

# Initialize hybrid search
hybrid_search = HybridSearch(
    qdrant_client=qdrant_client,
    embedding_service=embedding_service,
    bm25_search=bm25_search
)

# Decompose query and execute sub-queries automatically
result = await decomposer.decompose_and_search(
    query="What is vector search and how does BM25 work?",
    search_fn=hybrid_search.hybrid_search,
    merge_strategy="rrf",  # Reciprocal Rank Fusion
    top_k=5
)

print(f"Total Results: {result['total_results']}")
print(f"Decomposition Applied: {result['decomposition']['applied']}")
if result['decomposition']['applied']:
    print(f"Sub-queries: {result['decomposition']['sub_queries']}")
    print(f"Execution Strategy: {result['decomposition']['execution_strategy']}")

# Display results
for i, doc in enumerate(result['results'][:5]):
    print(f"\n{i+1}. {doc['id']}")
    print(f"   Score: {doc['score']:.3f}")
    print(f"   Text: {doc['text'][:80]}...")
```

### Classification Only

```python
# Just classify query type without decomposition
classification = await decomposer.classify_query(
    query="What is the capital of France?"
)

print(f"Type: {classification.query_type}")  # SIMPLE
print(f"Confidence: {classification.confidence:.2f}")
```

### Different Merge Strategies

```python
# Strategy 1: RRF (Reciprocal Rank Fusion) - Default
result_rrf = await decomposer.decompose_and_search(
    query="What is RAG and what is BM25?",
    search_fn=hybrid_search.hybrid_search,
    merge_strategy="rrf",  # Combines rankings
    top_k=5
)

# Strategy 2: Concatenation
result_concat = await decomposer.decompose_and_search(
    query="What is RAG and what is BM25?",
    search_fn=hybrid_search.hybrid_search,
    merge_strategy="concat",  # Simple concatenation
    top_k=10
)

# Strategy 3: Best (most results)
result_best = await decomposer.decompose_and_search(
    query="What is RAG and what is BM25?",
    search_fn=hybrid_search.hybrid_search,
    merge_strategy="best",  # Result set with most results
    top_k=5
)
```

---

## 3. Metadata Filtering

Filter search results by date, source, document type, and tags.

### Basic Filtering

```python
from datetime import datetime
from src.components.retrieval.filters import MetadataFilters, MetadataFilterEngine

# Create filters
filters = MetadataFilters(
    created_after=datetime(2024, 1, 1),
    doc_type_in=["pdf", "md"],
    tags_contains=["tutorial", "beginner"]
)

# Build Qdrant filter
filter_engine = MetadataFilterEngine()
qdrant_filter = filter_engine.build_qdrant_filter(filters)

# Use filter in search
from qdrant_client.models import SearchRequest

results = qdrant_client.search(
    collection_name="aegis_documents",
    query_vector=embedding,
    limit=10,
    query_filter=qdrant_filter  # Apply metadata filter
)
```

### Date Range Filtering

```python
# Search only recent documents
filters = MetadataFilters(
    created_after=datetime(2024, 10, 1),
    created_before=datetime(2024, 10, 31)
)

qdrant_filter = filter_engine.build_qdrant_filter(filters)
```

### Source Filtering

```python
# Include only specific sources
filters = MetadataFilters(
    source_in=["docs.aegis-rag.com", "arxiv.org"]
)

# Or exclude specific sources
filters = MetadataFilters(
    source_not_in=["spam-site.com", "unreliable.net"]
)

# Both together
filters = MetadataFilters(
    source_in=["docs.aegis-rag.com", "arxiv.org"],
    source_not_in=["docs.aegis-rag.com/old"]  # Include domain but exclude subdirectory
)
```

### Document Type Filtering

```python
# Search only PDFs
filters = MetadataFilters(
    doc_type_in=["pdf"]
)

# Search code files
filters = MetadataFilters(
    doc_type_in=["py", "js", "java"]
)

# Search documentation
filters = MetadataFilters(
    doc_type_in=["md", "txt", "html"]
)
```

### Tag Filtering (AND Logic)

```python
# Documents must have ALL specified tags
filters = MetadataFilters(
    tags_contains=["python", "tutorial", "advanced"]
)

# This will match documents with tags: ["python", "tutorial", "advanced", "2024"]
# But NOT documents with: ["python", "tutorial"] (missing "advanced")
```

### Combined Filters

```python
# Complex filter: Recent Python tutorials from official docs
filters = MetadataFilters(
    created_after=datetime(2024, 1, 1),
    source_in=["docs.python.org"],
    doc_type_in=["md", "html"],
    tags_contains=["tutorial"]
)

qdrant_filter = filter_engine.build_qdrant_filter(filters)
```

### Filter Validation

```python
# Validate filter consistency
filters = MetadataFilters(
    created_after=datetime(2024, 10, 1),
    created_before=datetime(2024, 9, 1)  # Invalid: after > before
)

is_valid, error = filter_engine.validate_filter(filters)
if not is_valid:
    print(f"Invalid filter: {error}")
```

### Selectivity Estimation

```python
# Estimate how many results will pass filter (heuristic)
selectivity = filter_engine.estimate_selectivity(filters)
print(f"Estimated selectivity: {selectivity:.1%}")
# Output: "Estimated selectivity: 15.0%"
```

### Check Active Filters

```python
filters = MetadataFilters(
    created_after=datetime(2024, 1, 1),
    doc_type_in=["pdf"]
)

active = filters.get_active_filters()
print(f"Active filters: {active}")
# Output: ['created_after', 'doc_type_in']

is_empty = filters.is_empty()
print(f"Is empty: {is_empty}")
# Output: False
```

---

## 4. Adaptive Chunking

Document-type aware chunking for better retrieval quality.

### Basic Adaptive Chunking

```python
from llama_index.core import Document
from src.components.retrieval.chunking import AdaptiveChunker

# Initialize chunker
chunker = AdaptiveChunker()

# Load documents
documents = [
    Document(
        text="# Introduction\n\nThis is a tutorial...",
        metadata={"file_name": "tutorial.md", "doc_type": "md"}
    ),
    Document(
        text="def calculate_score(query, doc):\n    return similarity(query, doc)",
        metadata={"file_name": "search.py", "doc_type": "py"}
    )
]

# Chunk documents (automatically selects strategy per document)
nodes = chunker.chunk_documents(documents)

print(f"Created {len(nodes)} chunks from {len(documents)} documents")
for node in nodes[:3]:
    print(f"\nChunk {node.metadata.get('chunk_index')}:")
    print(f"  Type: {node.metadata.get('doc_type')}")
    print(f"  Text: {node.text[:80]}...")
```

### Document Type Detection

```python
doc = Document(
    text="# Markdown Document\n\n## Section 1\n\nContent here...",
    metadata={"file_name": "tutorial.md"}
)

doc_type = chunker.detect_document_type(doc)
print(f"Detected type: {doc_type}")  # Output: "markdown"

strategy = chunker.select_strategy(doc_type)
print(f"Selected strategy: {strategy}")  # Output: ChunkingStrategy.HEADING
```

### Custom Chunk Sizes

```python
# Different chunk sizes for different document types
chunker = AdaptiveChunker(
    pdf_chunk_size=2048,      # Larger chunks for PDFs
    code_chunk_size=256,      # Smaller chunks for code
    markdown_chunk_size=1024,
    text_chunk_size=512,
    chunk_overlap=100         # More overlap
)
```

### Single Document Chunking

```python
# Chunk a single document
doc = Document(
    text="Your document content...",
    metadata={"file_name": "document.pdf"}
)

nodes = chunker.chunk_document(doc)
print(f"Created {len(nodes)} chunks")
```

### Chunking by Strategy

```python
# Manually specify chunking strategy

# 1. Paragraph-based (PDF/DOCX)
nodes = chunker.chunk_by_paragraph(doc, chunk_size=1024)

# 2. Heading-based (Markdown)
nodes = chunker.chunk_by_heading(doc, chunk_size=768)

# 3. Function-based (Code)
nodes = chunker.chunk_by_function(doc, chunk_size=512)

# 4. Sentence-based (Plain text)
nodes = chunker.chunk_by_sentence(doc, chunk_size=512)
```

### Chunker Information

```python
# Get chunker configuration
info = chunker.get_chunker_info()
print(f"PDF chunk size: {info['pdf_chunk_size']}")
print(f"Code chunk size: {info['code_chunk_size']}")
print(f"Strategies: {info['strategies']}")
```

### With Document Ingestion Pipeline

```python
from src.components.vector_search.ingestion import DocumentIngestionPipeline

# Initialize pipeline with adaptive chunker
ingestion_pipeline = DocumentIngestionPipeline(
    qdrant_client=qdrant_client,
    embedding_service=embedding_service,
    use_adaptive_chunking=True,  # Enable adaptive chunking
    pdf_chunk_size=1024,
    code_chunk_size=512,
)

# Ingest documents (chunking applied automatically)
result = await ingestion_pipeline.ingest_directory(
    directory_path="./data/documents",
    collection_name="aegis_documents"
)

print(f"Ingested {result['num_documents']} documents")
print(f"Created {result['num_chunks']} chunks")
```

---

## 5. RAGAS Evaluation

Evaluate RAG system quality using RAGAS metrics.

### Basic Evaluation

```python
from src.evaluation.ragas_eval import RAGASEvaluator, EvaluationDataset

# Initialize evaluator
evaluator = RAGASEvaluator()

# Create evaluation dataset
dataset = [
    EvaluationDataset(
        question="What is vector search?",
        ground_truth="Vector search uses embeddings to find semantically similar documents.",
        contexts=[
            "Vector search uses neural network embeddings to represent queries and documents.",
            "Semantic search finds meaning-based matches, not just keyword matches."
        ],
        answer="Vector search uses embeddings to find semantically similar documents."
    ),
    EvaluationDataset(
        question="What is BM25?",
        ground_truth="BM25 is a keyword-based ranking algorithm used for information retrieval.",
        contexts=[
            "BM25 is a probabilistic ranking function used in keyword search.",
            "BM25 considers term frequency and document length for scoring."
        ],
        answer="BM25 is a keyword-based ranking algorithm."
    )
]

# Run evaluation
result = await evaluator.evaluate_retrieval(
    dataset=dataset,
    scenario="hybrid-reranked"
)

print(f"Scenario: {result.scenario}")
print(f"Context Precision: {result.context_precision:.3f}")
print(f"Context Recall: {result.context_recall:.3f}")
print(f"Faithfulness: {result.faithfulness:.3f}")
print(f"Duration: {result.duration_seconds:.2f}s")
```

### Load Dataset from File

```python
# Create JSONL dataset file
# File: data/evaluation/ragas_dataset.jsonl
# Format: One JSON object per line
"""
{"question": "What is RAG?", "ground_truth": "RAG combines retrieval and generation.", "contexts": ["RAG is Retrieval-Augmented Generation."], "answer": "RAG combines retrieval and generation."}
{"question": "What is vector search?", "ground_truth": "Vector search uses embeddings.", "contexts": ["Vector search uses neural embeddings."], "answer": "Vector search uses embeddings."}
"""

# Load dataset
dataset = evaluator.load_dataset("data/evaluation/ragas_dataset.jsonl")
print(f"Loaded {len(dataset)} examples")

# Evaluate
result = await evaluator.evaluate_retrieval(dataset, scenario="vector-only")
```

### Multi-Scenario Benchmark

```python
# Benchmark multiple retrieval scenarios
results = await evaluator.run_benchmark(
    dataset=dataset,
    scenarios=[
        "vector-only",
        "bm25-only",
        "hybrid-base",
        "hybrid-reranked",
        "hybrid-full"
    ]
)

# Compare scenarios
print("\nBenchmark Results:")
print("-" * 80)
print(f"{'Scenario':<20} {'Precision':<12} {'Recall':<12} {'Faithfulness':<12}")
print("-" * 80)
for scenario, result in results.items():
    print(f"{scenario:<20} {result.context_precision:<12.3f} "
          f"{result.context_recall:<12.3f} {result.faithfulness:<12.3f}")
```

### Generate Evaluation Reports

```python
# HTML Report
html_report = evaluator.generate_report(
    results=results,
    output_path="reports/ragas_evaluation.html",
    format="html"
)

# Markdown Report
md_report = evaluator.generate_report(
    results=results,
    output_path="reports/ragas_evaluation.md",
    format="markdown"
)

# JSON Report
json_report = evaluator.generate_report(
    results=results,
    output_path="reports/ragas_evaluation.json",
    format="json"
)

print("Reports generated successfully!")
```

### Custom Metrics

```python
# Evaluate with specific metrics only
evaluator = RAGASEvaluator(
    metrics=["context_precision", "faithfulness"]  # Exclude context_recall
)

result = await evaluator.evaluate_retrieval(dataset, scenario="test")
print(f"Context Precision: {result.context_precision:.3f}")
print(f"Faithfulness: {result.faithfulness:.3f}")
print(f"Context Recall: {result.context_recall:.3f}")  # Will be 0.0 (not evaluated)
```

### Using Different LLM

```python
# Use different Ollama model for evaluation
evaluator = RAGASEvaluator(
    llm_model="llama3.1:8b",  # Larger model for more accurate evaluation
    llm_base_url="http://localhost:11434"
)
```

---

## 6. Combined Example: All Features

Putting it all together in a production-ready search pipeline.

```python
import asyncio
from datetime import datetime
from llama_index.core import Document

from src.components.vector_search.qdrant_client import QdrantClientWrapper
from src.components.vector_search.embeddings import EmbeddingService
from src.components.vector_search.bm25_search import BM25Search
from src.components.vector_search.hybrid_search import HybridSearch
from src.components.retrieval.reranker import CrossEncoderReranker
from src.components.retrieval.query_decomposition import QueryDecomposer
from src.components.retrieval.filters import MetadataFilters, MetadataFilterEngine
from src.components.retrieval.chunking import AdaptiveChunker


async def advanced_search_pipeline(
    query: str,
    filters: MetadataFilters | None = None,
    use_reranking: bool = True,
    use_decomposition: bool = True,
    top_k: int = 5
):
    """Production-ready search pipeline with all Sprint 3 features.

    Args:
        query: User query
        filters: Metadata filters (optional)
        use_reranking: Enable cross-encoder reranking
        use_decomposition: Enable query decomposition
        top_k: Number of results to return

    Returns:
        Search results with metadata
    """
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")

    # Initialize components
    qdrant_client = QdrantClientWrapper()
    embedding_service = EmbeddingService()
    bm25_search = BM25Search()
    hybrid_search = HybridSearch(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        bm25_search=bm25_search
    )

    # Step 1: Build metadata filter (if provided)
    qdrant_filter = None
    if filters and not filters.is_empty():
        filter_engine = MetadataFilterEngine()
        qdrant_filter = filter_engine.build_qdrant_filter(filters)
        print(f"Applied filters: {filters.get_active_filters()}")

    # Step 2: Query decomposition (if enabled)
    if use_decomposition:
        decomposer = QueryDecomposer()

        # Execute with decomposition
        result = await decomposer.decompose_and_search(
            query=query,
            search_fn=hybrid_search.hybrid_search,
            merge_strategy="rrf",
            top_k=top_k * 2 if use_reranking else top_k,  # Get more for reranking
            filter=qdrant_filter
        )

        if result.get("decomposition", {}).get("applied"):
            print(f"Query Type: {result['decomposition']['query_type']}")
            print(f"Sub-queries: {result['decomposition']['sub_queries']}")
            print(f"Execution: {result['decomposition']['execution_strategy']}\n")
    else:
        # Direct hybrid search
        result = await hybrid_search.hybrid_search(
            query=query,
            top_k=top_k * 2 if use_reranking else top_k,
            filter=qdrant_filter
        )

    # Step 3: Reranking (if enabled)
    if use_reranking and result.get("results"):
        print("Applying cross-encoder reranking...")
        reranker = CrossEncoderReranker()

        reranked = await reranker.rerank(
            query=query,
            documents=result["results"],
            top_k=top_k,
            score_threshold=0.5
        )

        # Convert back to dict format
        result["results"] = [
            {
                "id": r.doc_id,
                "text": r.text,
                "score": r.final_score,
                "original_score": r.original_score,
                "rerank_score": r.rerank_score,
                "original_rank": r.original_rank,
                "final_rank": r.final_rank,
                "metadata": r.metadata
            }
            for r in reranked
        ]
        result["reranking_applied"] = True
        print(f"Reranked to top {len(result['results'])} results\n")
    else:
        result["reranking_applied"] = False
        result["results"] = result["results"][:top_k]

    # Step 4: Format and return results
    print(f"Results ({len(result['results'])}):")
    print("-" * 80)

    for i, doc in enumerate(result["results"], 1):
        print(f"\n{i}. Document: {doc['id']}")
        print(f"   Score: {doc['score']:.3f}", end="")

        if result["reranking_applied"]:
            print(f" (Original: {doc['original_score']:.3f}, Rerank: {doc['rerank_score']:.3f})")
            print(f"   Rank Change: {doc['original_rank']} → {doc['final_rank']}")
        else:
            print()

        print(f"   Text: {doc['text'][:150]}...")

        if doc.get("metadata"):
            meta = doc["metadata"]
            if meta.get("doc_type"):
                print(f"   Type: {meta['doc_type']}")
            if meta.get("source"):
                print(f"   Source: {meta['source']}")

    print(f"\n{'='*80}\n")

    return result


async def main():
    """Example usage of advanced search pipeline."""

    # Example 1: Simple query with reranking
    print("\n=== Example 1: Simple Query with Reranking ===")
    result1 = await advanced_search_pipeline(
        query="What is vector search?",
        use_reranking=True,
        use_decomposition=False,
        top_k=3
    )

    # Example 2: Complex query with decomposition
    print("\n=== Example 2: Complex Query with Decomposition ===")
    result2 = await advanced_search_pipeline(
        query="What is vector search and how does BM25 compare to it?",
        use_reranking=True,
        use_decomposition=True,
        top_k=5
    )

    # Example 3: Filtered search
    print("\n=== Example 3: Filtered Search ===")
    filters = MetadataFilters(
        created_after=datetime(2024, 1, 1),
        doc_type_in=["md", "pdf"],
        tags_contains=["tutorial"]
    )
    result3 = await advanced_search_pipeline(
        query="RAG tutorial for beginners",
        filters=filters,
        use_reranking=True,
        use_decomposition=False,
        top_k=5
    )

    # Example 4: Full pipeline (all features)
    print("\n=== Example 4: Full Pipeline (All Features) ===")
    filters = MetadataFilters(
        created_after=datetime(2024, 6, 1),
        source_in=["docs.aegis-rag.com"],
        doc_type_in=["md"]
    )
    result4 = await advanced_search_pipeline(
        query="How do I implement reranking and what are the benefits?",
        filters=filters,
        use_reranking=True,
        use_decomposition=True,
        top_k=5
    )


if __name__ == "__main__":
    asyncio.run(main())
```

### Output Example

```
================================================================================
Query: How do I implement reranking and what are the benefits?
================================================================================

Applied filters: ['created_after', 'source_in', 'doc_type_in']
Query Type: COMPOUND
Sub-queries: ['How do I implement reranking?', 'What are the benefits of reranking?']
Execution: parallel

Applying cross-encoder reranking...
Reranked to top 5 results

Results (5):
--------------------------------------------------------------------------------

1. Document: doc_reranker_tutorial_1
   Score: 0.912 (Original: 0.782, Rerank: 2.456)
   Rank Change: 2 → 0
   Text: Cross-encoder reranking improves precision by scoring query-document pairs more accurately than vector similarity alone. Implementation requires sentence-transformers...
   Type: md
   Source: docs.aegis-rag.com

2. Document: doc_reranker_benefits_1
   Score: 0.895 (Original: 0.801, Rerank: 2.178)
   Rank Change: 0 → 1
   Text: Benefits of reranking include: 15-20% improvement in precision@3, better relevance scoring, reduced false positives...
   Type: md
   Source: docs.aegis-rag.com

3. Document: doc_reranker_impl_2
   Score: 0.876 (Original: 0.765, Rerank: 1.989)
   Rank Change: 3 → 2
   Text: To implement reranking: 1) Initialize CrossEncoderReranker, 2) Get initial search results, 3) Call rerank() with query and documents...
   Type: md
   Source: docs.aegis-rag.com

...

================================================================================
```

---

## Additional Resources

- [SPRINT_3_SUMMARY.md](../../SPRINT_3_SUMMARY.md) - Complete Sprint 3 feature documentation
- [src/components/retrieval/](../../src/components/retrieval/) - Source code for all retrieval components
- [tests/components/retrieval/](../../tests/components/retrieval/) - Test suites with more examples
- [SPRINT_PLAN.md](../core/SPRINT_PLAN.md) - Overall sprint roadmap

---

## API Reference

### Reranker
- `CrossEncoderReranker(model_name, batch_size, cache_dir)`
- `reranker.rerank(query, documents, top_k, score_threshold) → list[RerankResult]`

### Query Decomposition
- `QueryDecomposer(ollama_base_url, model_name, classification_threshold)`
- `decomposer.classify_query(query) → QueryClassification`
- `decomposer.decompose(query) → DecompositionResult`
- `decomposer.decompose_and_search(query, search_fn, merge_strategy, **kwargs) → dict`

### Metadata Filters
- `MetadataFilters(created_after, created_before, source_in, source_not_in, doc_type_in, tags_contains)`
- `MetadataFilterEngine()`
- `filter_engine.build_qdrant_filter(filters) → Filter | None`
- `filter_engine.validate_filter(filters) → tuple[bool, str]`

### Adaptive Chunking
- `AdaptiveChunker(pdf_chunk_size, code_chunk_size, markdown_chunk_size, text_chunk_size, chunk_overlap)`
- `chunker.detect_document_type(doc) → str`
- `chunker.chunk_document(doc) → list[TextNode]`
- `chunker.chunk_documents(documents) → list[TextNode]`

### RAGAS Evaluation
- `RAGASEvaluator(llm_model, llm_base_url, metrics)`
- `evaluator.load_dataset(dataset_path) → list[EvaluationDataset]`
- `evaluator.evaluate_retrieval(dataset, scenario) → EvaluationResult`
- `evaluator.run_benchmark(dataset, scenarios) → dict[str, EvaluationResult]`
- `evaluator.generate_report(results, output_path, format) → str`

---

**Sprint 3 Documentation**
Generated: October 2024
Version: 1.0.0
