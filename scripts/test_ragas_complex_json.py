"""Test RAGAS JSON output with COMPLEX/LONG inputs to identify breaking point."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama

OLLAMA_BASE_URL = "http://localhost:11434"


def test_statement_generator_complex():
    """Test with very long ground truth answer (simulates complex RAG output)."""
    print("=" * 80)
    print("Testing: StatementGeneratorPrompt with COMPLEX Answer")
    print("=" * 80)
    print()

    llm = ChatOllama(
        model="gpt-oss:20b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        top_p=0.9,
        timeout=120,
        num_ctx=16384,
        num_predict=512,
        format="json",
    )

    # Simulate a complex RAG answer (like question #5 or #9 from dataset)
    complex_answer = """The four-way hybrid search combines vector search, BM25 keyword search, local graph search, and global graph search, fusing results with weighted Reciprocal Rank Fusion (RRF) based on query intent classification. Vector search uses embeddings and cosine similarity for semantic matching. BM25 provides statistical keyword matching based on term frequency-inverse document frequency. Local graph search retrieves entities and relationships from a 2-hop neighborhood around query entities. Global graph search uses Cypher queries for complex graph patterns. The intent classifier determines optimal weights: factual queries favor graph search (0.4 weight), keyword queries favor BM25 (0.4 weight), exploratory queries balance all methods (0.25 each), and summary queries prioritize vector search (0.4 weight). Results are fused using RRF with k=60, which combines rankings rather than scores, making it robust to score distribution differences. The final ranking is then reranked using a cross-encoder model (ms-marco-MiniLM-L-6-v2) with adaptive weights based on recency, semantic similarity, and keyword relevance. This multi-stage approach achieves higher recall than any single method while maintaining precision through reranking."""

    prompt = f"""Given a question and an answer, analyze the complexity of each sentence in the answer. Break down each sentence into one or more fully understandable statements. Ensure that no pronouns are used in any statement. Format the outputs in JSON.

Example Output:
{{
  "statements": [
    "Statement 1.",
    "Statement 2."
  ]
}}

Now process:
Question: How does the four-way hybrid search work?
Answer: {complex_answer}

Output (JSON only):"""

    print("Answer length:", len(complex_answer), "chars")
    print("Prompt length:", len(prompt), "chars")
    print()
    print("-" * 80)
    print("gpt-oss:20b Response:")
    print("-" * 80)

    try:
        response = llm.invoke(prompt)
        output = response.content

        print(output[:500], "..." if len(output) > 500 else "")
        print()
        print("-" * 80)

        # Try to parse
        parsed = json.loads(output)
        print("✅ PARSING SUCCESS")
        print(f"   Keys: {list(parsed.keys())}")
        if "statements" in parsed:
            print(f"   Statements count: {len(parsed['statements'])}")
        else:
            print(f"   ❌ Missing 'statements' key!")
            print(f"   Actual keys: {list(parsed.keys())}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON PARSING FAILED: {e}")
        print(f"   Output preview: {output[:300]}")
    except Exception as e:
        print(f"❌ OTHER ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()


def test_context_recall_long_context():
    """Test with very long context (simulates 16K token scenario)."""
    print("=" * 80)
    print("Testing: ContextRecallClassificationPrompt with LONG Context")
    print("=" * 80)
    print()

    llm = ChatOllama(
        model="gpt-oss:20b",
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        top_p=0.9,
        timeout=120,
        num_ctx=16384,
        num_predict=512,
        format="json",
    )

    # Simulate very long retrieved contexts (concatenated from 5 chunks)
    long_context = """BGE-M3 is a 1024-dimensional multilingual embedding model from BAAI (Beijing Academy of Artificial Intelligence). It supports over 100 languages and achieves state-of-the-art performance on multilingual retrieval benchmarks. The model uses a transformer architecture with 12 layers and 768 hidden dimensions. It was trained on a massive corpus of 200 billion tokens across multiple languages.

The model architecture uses a special [CLS] token for sentence representation and applies mean pooling over all tokens for better semantic coverage. BGE-M3 achieves 70.5% on MTEB (Massive Text Embedding Benchmark) and 65.2% on MIRACL (Multilingual Information Retrieval Across a Continuum of Languages).

For retrieval tasks, BGE-M3 uses cosine similarity between query and document embeddings. The model also supports hybrid search by combining with BM25 keyword matching using Reciprocal Rank Fusion (RRF). Training used contrastive learning with in-batch negatives and hard negative mining. The loss function combines InfoNCE loss with a temperature parameter of 0.05.

BGE-M3 is particularly effective for cross-lingual retrieval, where the query and documents are in different languages. This is achieved through aligned multilingual training data and language-agnostic tokenization. The model handles code-switching and mixed-language queries effectively.

For production deployment, BGE-M3 can be quantized to INT8 for 4x faster inference with minimal accuracy loss (<1%). The model supports batch processing for high-throughput scenarios and can generate embeddings at 1000 docs/second on a single GPU."""

    answer = "BGE-M3 is a multilingual embedding model from BAAI that supports over 100 languages. It uses a transformer architecture and achieves state-of-the-art performance on MTEB. The model can be quantized for faster inference."

    prompt = f"""Given a context, and an answer, analyze each sentence in the answer and classify if the sentence can be attributed to the given context or not. Use only 'Yes' (1) or 'No' (0) as a binary classification. Output json with reason.

Example Output:
{{
  "classifications": [
    {{
      "statement": "Statement here.",
      "reason": "Reason here.",
      "attributed": 1
    }}
  ]
}}

Now process:
Context: {long_context}
Answer: {answer}

Output (JSON only):"""

    print("Context length:", len(long_context), "chars")
    print("Answer length:", len(answer), "chars")
    print("Prompt length:", len(prompt), "chars")
    print()
    print("-" * 80)
    print("gpt-oss:20b Response:")
    print("-" * 80)

    try:
        response = llm.invoke(prompt)
        output = response.content

        print(output[:500], "..." if len(output) > 500 else "")
        print()
        print("-" * 80)

        # Try to parse
        parsed = json.loads(output)
        print("✅ PARSING SUCCESS")
        print(f"   Keys: {list(parsed.keys())}")
        if "classifications" in parsed:
            print(f"   Classifications count: {len(parsed['classifications'])}")
        else:
            print(f"   ❌ Missing 'classifications' key!")
    except json.JSONDecodeError as e:
        print(f"❌ JSON PARSING FAILED: {e}")
        print(f"   Output preview: {output[:300]}")
    except Exception as e:
        print(f"❌ OTHER ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()


if __name__ == "__main__":
    print("=" * 80)
    print("🔬 RAGAS JSON Output - STRESS TEST (Complex/Long Inputs)")
    print("=" * 80)
    print()

    try:
        test_statement_generator_complex()
        test_context_recall_long_context()

        print("=" * 80)
        print("📊 STRESS TEST COMPLETE")
        print("=" * 80)
        print()
        print("If both tests passed → Issue is likely RAGAS-specific (batch/retry logic)")
        print("If tests failed → Issue is input complexity/length threshold")
        print()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
