"""Test Recursive LLM with Real Research Papers.

Sprint 92: Validate new features with actual documents:
- Feature 92.6: Per-Level Configuration
- Feature 92.7: BGE-M3 Dense+Sparse Scoring
- Feature 92.8: BGE-M3 Multi-Vector Scoring
- Feature 92.9: C-LARA Granularity Mapping
- Feature 92.10: Parallel Workers

Usage:
    poetry run python scripts/test_recursive_llm_real_data.py

Requirements:
    - Ollama running (for LLM)
    - BGE-M3 embeddings available
    - At least 1 document ingested
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from langchain_ollama import ChatOllama

from src.agents.context.recursive_llm import RecursiveLLMProcessor
from src.agents.skills.registry import SkillRegistry
from src.core.config import RecursiveLLMSettings, RecursiveLevelConfig

logger = structlog.get_logger(__name__)


async def test_fine_grained_query():
    """Test fine-grained query (should use BGE-M3 multi-vector at Level 2+)."""
    print("\n" + "=" * 80)
    print("TEST 1: Fine-Grained Query (BGE-M3 Multi-Vector)")
    print("=" * 80)

    # Sample research paper abstract (BGE-M3 paper)
    document = """
BGE-M3: Multi-Vector Dense Retrieval Model

Abstract:
We present BGE-M3, a new embedding model that supports multi-functionality,
multi-linguality, and multi-granularity. The model achieves state-of-the-art
performance on the BEIR benchmark with an NDCG@10 score of 0.876.

Table 1: Performance Comparison
┌──────────┬─────────┬─────────┐
│ Model    │ NDCG@10 │ p-value │
├──────────┼─────────┼─────────┤
│ BM25     │ 0.712   │ 0.003   │
│ BGE-M3   │ 0.876   │ 0.001   │
│ ColBERT  │ 0.842   │ 0.002   │
└──────────┴─────────┴─────────┘

The model uses a multi-vector approach with ColBERT-style late interaction.
Each token is embedded with 1024-dimensional vectors, enabling precise
token-level matching. The MaxSim operation computes similarity scores
by taking the maximum similarity for each query token across all document tokens.

Experimental Setup:
We trained the model on 250M text pairs from 100 languages. The training
process took 14 days on 32 A100 GPUs. We evaluated on 15 BEIR datasets
covering diverse domains including scientific papers, news, and social media.

Results show that BGE-M3 outperforms previous state-of-the-art models
on 12 out of 15 datasets. The model is particularly strong on scientific
and technical domains, achieving 0.923 NDCG@10 on SciFact and 0.891 on TREC-COVID.
"""

    # Fine-grained query (should trigger multi-vector scoring at Level 2+)
    query = "What is the p-value for BGE-M3 in Table 1?"

    # Initialize processor with Sprint 92 configuration
    llm = ChatOllama(model="llama3.2:8b")
    skill_registry = SkillRegistry()

    settings = RecursiveLLMSettings(
        max_depth=2,
        max_parallel_workers=1,  # DGX Spark
        levels=[
            # Level 0: Fast overview (dense+sparse)
            RecursiveLevelConfig(
                level=0,
                segment_size_tokens=16384,
                overlap_tokens=400,
                top_k_subsegments=3,
                relevance_threshold=0.5,
                scoring_method="dense+sparse",
            ),
            # Level 1: Details (dense+sparse)
            RecursiveLevelConfig(
                level=1,
                segment_size_tokens=8192,
                overlap_tokens=300,
                top_k_subsegments=3,
                relevance_threshold=0.6,
                scoring_method="dense+sparse",
            ),
            # Level 2: Fine-grained (adaptive - should choose multi-vector)
            RecursiveLevelConfig(
                level=2,
                segment_size_tokens=4096,
                overlap_tokens=200,
                top_k_subsegments=2,
                relevance_threshold=0.7,
                scoring_method="adaptive",
            ),
        ],
    )

    processor = RecursiveLLMProcessor(
        llm=llm,
        skill_registry=skill_registry,
        settings=settings,
    )

    print(f"\nQuery: {query}")
    print(f"Document length: {len(document)} chars")
    print(f"Max depth: {settings.max_depth}")
    print(f"Scoring: Level 0-1 (dense+sparse), Level 2 (adaptive → multi-vector)")

    start_time = time.time()

    try:
        result = await processor.process(document=document, query=query)

        elapsed = time.time() - start_time

        print(f"\n✅ Processing completed in {elapsed:.2f}s")
        print(f"\nAnswer: {result['answer'][:500]}")
        print(f"\nSegments processed: {result['segments_processed']}")
        print(f"Max depth reached: {result['max_depth_reached']}")
        print(f"Skills used: {result['skills_used']}")

        # Validate answer contains expected information
        answer_lower = result["answer"].lower()
        if "0.001" in answer_lower or "p-value" in answer_lower:
            print("\n✅ PASS: Answer contains expected information (p-value)")
        else:
            print("\n⚠️ WARNING: Answer may not contain p-value information")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


async def test_holistic_query():
    """Test holistic query (should use LLM at Level 2+)."""
    print("\n" + "=" * 80)
    print("TEST 2: Holistic Query (LLM Reasoning)")
    print("=" * 80)

    # Same document as Test 1
    document = """
BGE-M3: Multi-Vector Dense Retrieval Model

Abstract:
We present BGE-M3, a new embedding model that supports multi-functionality,
multi-linguality, and multi-granularity. The model achieves state-of-the-art
performance on the BEIR benchmark with an NDCG@10 score of 0.876.

The key innovation is the multi-vector representation. Unlike traditional
dense retrieval models that produce a single embedding per document, BGE-M3
generates embeddings for each token. This enables fine-grained matching
between query and document tokens through late interaction.

Our approach addresses three major challenges in information retrieval:
1. Multi-functionality: Supporting dense, sparse, and multi-vector retrieval
2. Multi-linguality: Covering 100+ languages with strong cross-lingual transfer
3. Multi-granularity: Handling documents from sentences to long passages

Methodology:
The training process consists of three stages:
- Stage 1: Pre-training on large-scale web text (30 days)
- Stage 2: Fine-tuning on retrieval datasets (7 days)
- Stage 3: Multi-task learning with hybrid objectives (7 days)

We use a custom loss function that combines contrastive learning,
knowledge distillation, and hard negative mining.
"""

    # Holistic query (should trigger LLM reasoning at Level 2+)
    query = "Summarize the main contributions of BGE-M3"

    llm = ChatOllama(model="llama3.2:8b")
    skill_registry = SkillRegistry()

    settings = RecursiveLLMSettings(
        max_depth=2,
        max_parallel_workers=1,
        levels=[
            RecursiveLevelConfig(
                level=0,
                segment_size_tokens=16384,
                scoring_method="dense+sparse",
            ),
            RecursiveLevelConfig(
                level=1,
                segment_size_tokens=8192,
                scoring_method="dense+sparse",
            ),
            RecursiveLevelConfig(
                level=2,
                segment_size_tokens=4096,
                scoring_method="adaptive",  # Should choose LLM for holistic query
            ),
        ],
    )

    processor = RecursiveLLMProcessor(
        llm=llm, skill_registry=skill_registry, settings=settings
    )

    print(f"\nQuery: {query}")
    print(f"Scoring: Level 0-1 (dense+sparse), Level 2 (adaptive → LLM)")

    start_time = time.time()

    try:
        result = await processor.process(document=document, query=query)

        elapsed = time.time() - start_time

        print(f"\n✅ Processing completed in {elapsed:.2f}s")
        print(f"\nAnswer: {result['answer']}")
        print(f"\nSegments processed: {result['segments_processed']}")
        print(f"Max depth reached: {result['max_depth_reached']}")

        # Validate answer mentions key contributions
        answer_lower = result["answer"].lower()
        if (
            "multi" in answer_lower
            and "vector" in answer_lower
            or "retrieval" in answer_lower
        ):
            print("\n✅ PASS: Answer summarizes key contributions")
        else:
            print("\n⚠️ WARNING: Answer may not cover all contributions")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


async def test_per_level_configuration():
    """Test per-level segment sizes and thresholds."""
    print("\n" + "=" * 80)
    print("TEST 3: Per-Level Configuration (Pyramid Structure)")
    print("=" * 80)

    # Long document to trigger multiple levels
    document = """BGE-M3: Introduction

    This paper introduces BGE-M3, a multi-vector dense retrieval model.
    """ + (
        "The model supports multi-functionality, multi-linguality, and multi-granularity. " * 500
    )

    query = "What is BGE-M3?"

    llm = ChatOllama(model="llama3.2:8b")
    skill_registry = SkillRegistry()

    settings = RecursiveLLMSettings(
        max_depth=3,
        levels=[
            RecursiveLevelConfig(level=0, segment_size_tokens=16384, top_k_subsegments=5),
            RecursiveLevelConfig(level=1, segment_size_tokens=8192, top_k_subsegments=4),
            RecursiveLevelConfig(level=2, segment_size_tokens=4096, top_k_subsegments=3),
            RecursiveLevelConfig(level=3, segment_size_tokens=2048, top_k_subsegments=2),
        ],
    )

    processor = RecursiveLLMProcessor(
        llm=llm, skill_registry=skill_registry, settings=settings
    )

    print(f"\nDocument length: {len(document)} chars (~{len(document)//4} tokens)")
    print(f"Max depth: {settings.max_depth}")
    print("\nPyramid structure:")
    for level_config in settings.levels:
        print(
            f"  Level {level_config.level}: {level_config.segment_size_tokens} tokens, "
            f"top-{level_config.top_k_subsegments} segments"
        )

    start_time = time.time()

    try:
        result = await processor.process(document=document, query=query)

        elapsed = time.time() - start_time

        print(f"\n✅ Processing completed in {elapsed:.2f}s")
        print(f"\nSegments processed: {result['segments_processed']}")
        print(f"Max depth reached: {result['max_depth_reached']}")
        print(f"Total segments created: {result['total_segments']}")

        # Validate pyramid was used
        if result["max_depth_reached"] >= 1:
            print("\n✅ PASS: Multi-level recursion occurred")
        else:
            print("\n⚠️ WARNING: Only top-level processed")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("Sprint 92 Recursive LLM - Real Data Testing")
    print("=" * 80)
    print("\nFeatures to validate:")
    print("- Feature 92.6: Per-Level Configuration")
    print("- Feature 92.7: BGE-M3 Dense+Sparse Scoring")
    print("- Feature 92.8: BGE-M3 Multi-Vector Scoring")
    print("- Feature 92.9: C-LARA Granularity Mapping")
    print("- Feature 92.10: Parallel Workers (1 worker on DGX Spark)")

    # Run tests sequentially
    await test_fine_grained_query()
    await test_holistic_query()
    await test_per_level_configuration()

    print("\n" + "=" * 80)
    print("Testing Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
