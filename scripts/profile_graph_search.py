"""Performance profiling script for Graph search.

Sprint 92: Graph Search Performance Analysis

This script profiles the graph search pipeline to identify bottlenecks
causing 17-19s latency (target: <2s).

Expected bottlenecks:
1. SmartEntityExpander.expand_entities() - Multiple LLM calls
2. SmartEntityExpander._extract_entities_llm() - LLM extraction
3. SmartEntityExpander._generate_synonyms_llm() - LLM synonym generation
4. query_rewriter_v2.extract_graph_intents() - LLM intent extraction
5. Neo4j queries - Graph traversal
6. Embedding calls - Multiple encode() calls in reranking

Usage:
    python scripts/profile_graph_search.py --query "What is RAG?" --namespace test
"""

import argparse
import asyncio
import time
from typing import Any

import structlog

from src.agents.graph_query_agent import GraphQueryAgent
from src.components.graph_rag.dual_level_search import DualLevelSearch
from src.core.config import settings

logger = structlog.get_logger(__name__)


class PerformanceProfiler:
    """Profile graph search performance."""

    def __init__(self):
        self.timings: dict[str, float] = {}
        self.start_times: dict[str, float] = {}

    def start(self, label: str) -> None:
        """Start timing a section."""
        self.start_times[label] = time.perf_counter()

    def stop(self, label: str) -> float:
        """Stop timing a section and record duration."""
        if label not in self.start_times:
            logger.warning("profiler_stop_without_start", label=label)
            return 0.0

        duration_ms = (time.perf_counter() - self.start_times[label]) * 1000
        self.timings[label] = duration_ms
        del self.start_times[label]
        return duration_ms

    def report(self) -> None:
        """Print performance report."""
        print("\n" + "=" * 80)
        print("GRAPH SEARCH PERFORMANCE PROFILE")
        print("=" * 80)

        total = sum(self.timings.values())
        print(f"\nTotal Time: {total:.2f}ms\n")

        # Sort by duration descending
        sorted_timings = sorted(
            self.timings.items(),
            key=lambda x: x[1],
            reverse=True
        )

        print(f"{'Component':<50} {'Time (ms)':<12} {'% of Total':<10}")
        print("-" * 80)

        for label, duration in sorted_timings:
            percentage = (duration / total * 100) if total > 0 else 0
            print(f"{label:<50} {duration:>10.2f}ms {percentage:>8.1f}%")

        print("=" * 80)

        # Identify bottlenecks (>20% of total time)
        bottlenecks = [(label, dur) for label, dur in sorted_timings if (dur / total * 100) > 20]
        if bottlenecks:
            print("\n🔥 BOTTLENECKS (>20% of total time):")
            for label, dur in bottlenecks:
                percentage = (dur / total * 100)
                print(f"  - {label}: {dur:.2f}ms ({percentage:.1f}%)")

        # Performance assessment
        print("\n📊 PERFORMANCE ASSESSMENT:")
        if total < 500:
            print("  ✅ EXCELLENT: Under 500ms (meets target)")
        elif total < 2000:
            print("  ⚠️  ACCEPTABLE: Under 2s (acceptable)")
        elif total < 5000:
            print("  ❌ SLOW: 2-5s (needs optimization)")
        else:
            print("  ❌ CRITICAL: Over 5s (critical performance issue)")


async def profile_graph_search(query: str, namespace: str = "default") -> PerformanceProfiler:
    """Profile a graph search query.

    Args:
        query: User query to profile
        namespace: Namespace to search in

    Returns:
        PerformanceProfiler with timing data
    """
    profiler = PerformanceProfiler()

    logger.info(
        "profile_graph_search_started",
        query=query,
        namespace=namespace,
    )

    # Create agent
    agent = GraphQueryAgent()

    # Create mock state
    state: dict[str, Any] = {
        "query": query,
        "intent": "graph",
        "namespaces": [namespace],
        "metadata": {},
        "retrieved_contexts": [],
        "trace": [],
    }

    # Profile overall execution
    profiler.start("TOTAL_GRAPH_SEARCH")

    # Profile graph_intent_extraction
    try:
        profiler.start("1_graph_intent_extraction")
        graph_intent_result = await agent.query_rewriter_v2.extract_graph_intents(query)
        profiler.stop("1_graph_intent_extraction")
        logger.info(
            "profile_intent_extraction_complete",
            duration_ms=profiler.timings["1_graph_intent_extraction"],
            intents=graph_intent_result.graph_intents,
        )
    except Exception as e:
        profiler.stop("1_graph_intent_extraction")
        logger.warning("profile_intent_extraction_failed", error=str(e))

    # Profile entity expansion (local_search)
    try:
        profiler.start("2_entity_expansion")
        entities = await agent.dual_level_search.local_search(
            query=query,
            top_k=10,
            namespaces=[namespace]
        )
        profiler.stop("2_entity_expansion")
        logger.info(
            "profile_entity_expansion_complete",
            duration_ms=profiler.timings["2_entity_expansion"],
            entities_found=len(entities),
        )
    except Exception as e:
        profiler.stop("2_entity_expansion")
        logger.warning("profile_entity_expansion_failed", error=str(e))

    # Profile global_search
    try:
        profiler.start("3_global_search")
        topics = await agent.dual_level_search.global_search(
            query=query,
            top_k=5,
            namespaces=[namespace]
        )
        profiler.stop("3_global_search")
        logger.info(
            "profile_global_search_complete",
            duration_ms=profiler.timings["3_global_search"],
            topics_found=len(topics),
        )
    except Exception as e:
        profiler.stop("3_global_search")
        logger.warning("profile_global_search_failed", error=str(e))

    # Profile relationship retrieval
    try:
        profiler.start("4_relationship_retrieval")
        relationships = await agent.dual_level_search._get_entity_relationships(entities)
        profiler.stop("4_relationship_retrieval")
        logger.info(
            "profile_relationship_retrieval_complete",
            duration_ms=profiler.timings["4_relationship_retrieval"],
            relationships_found=len(relationships),
        )
    except Exception as e:
        profiler.stop("4_relationship_retrieval")
        logger.warning("profile_relationship_retrieval_failed", error=str(e))

    profiler.stop("TOTAL_GRAPH_SEARCH")

    return profiler


async def profile_entity_expansion_detailed(
    query: str,
    namespace: str = "default"
) -> PerformanceProfiler:
    """Profile SmartEntityExpander in detail.

    Args:
        query: User query
        namespace: Namespace to search in

    Returns:
        PerformanceProfiler with detailed timing data
    """
    from src.components.graph_rag.entity_expansion import SmartEntityExpander
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    profiler = PerformanceProfiler()

    neo4j_client = get_neo4j_client()
    expander = SmartEntityExpander(
        neo4j_client=neo4j_client,
        graph_expansion_hops=settings.graph_expansion_hops,
        min_entities_threshold=settings.graph_min_entities_threshold,
        max_synonyms_per_entity=settings.graph_max_synonyms_per_entity,
    )

    profiler.start("TOTAL_ENTITY_EXPANSION")

    # Stage 1: LLM extraction
    profiler.start("stage1_llm_extraction")
    initial_entities = await expander._extract_entities_llm(query)
    profiler.stop("stage1_llm_extraction")
    logger.info(
        "profile_stage1_complete",
        duration_ms=profiler.timings["stage1_llm_extraction"],
        entities_found=len(initial_entities),
    )

    # Stage 2: Graph expansion
    profiler.start("stage2_graph_expansion")
    graph_expanded = await expander._expand_via_graph(
        initial_entities,
        [namespace],
        max_hops=expander.graph_expansion_hops
    )
    profiler.stop("stage2_graph_expansion")
    logger.info(
        "profile_stage2_complete",
        duration_ms=profiler.timings["stage2_graph_expansion"],
        expanded_count=len(graph_expanded),
    )

    # Stage 3: Synonym fallback (conditional)
    if len(graph_expanded) < expander.min_entities_threshold:
        profiler.start("stage3_synonym_fallback")
        synonyms = await expander._generate_synonyms_llm(
            initial_entities[:2],
            max_per_entity=expander.max_synonyms_per_entity
        )
        profiler.stop("stage3_synonym_fallback")
        logger.info(
            "profile_stage3_complete",
            duration_ms=profiler.timings["stage3_synonym_fallback"],
            synonyms_found=len(synonyms),
        )

    profiler.stop("TOTAL_ENTITY_EXPANSION")

    return profiler


async def main():
    """Run performance profiling."""
    parser = argparse.ArgumentParser(
        description="Profile graph search performance"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is RAG?",
        help="Query to profile (default: 'What is RAG?')"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="default",
        help="Namespace to search in (default: 'default')"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Run detailed entity expansion profiling"
    )

    args = parser.parse_args()

    print(f"\n🔍 Profiling Graph Search")
    print(f"Query: {args.query}")
    print(f"Namespace: {args.namespace}")
    print(f"Detailed: {args.detailed}\n")

    # Profile main graph search
    profiler = await profile_graph_search(args.query, args.namespace)
    profiler.report()

    # Profile entity expansion in detail if requested
    if args.detailed:
        print("\n\n" + "=" * 80)
        print("DETAILED ENTITY EXPANSION PROFILE")
        print("=" * 80)
        expander_profiler = await profile_entity_expansion_detailed(
            args.query,
            args.namespace
        )
        expander_profiler.report()


if __name__ == "__main__":
    asyncio.run(main())
