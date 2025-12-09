#!/usr/bin/env python3
"""
Debug Script: Detailed Data Flow Analysis for Single Query

This script traces the complete data flow for a single question:
1. Query embedding
2. Intent classification
3. 4-Way Hybrid Search (Vector, BM25, Graph Local, Graph Global)
4. RRF Fusion
5. Cross-encoder reranking
6. LLM answer generation

Run: poetry run python scripts/debug_single_query.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path (same as run_track_a_evaluation.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

# Configure detailed logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

console = Console()

# Test questions from HotpotQA
TEST_QUESTIONS = [
    {
        "question": "Which magazine was started first Arthur's Magazine or First for Women?",
        "ground_truth": "Arthur's Magazine",
        "contexts": [
            "Arthur's Magazine (1844–1846) was an American literary periodical published in Philadelphia in the 19th century.",
            "First for Women is a woman's magazine published by Bauer Media Group in the USA."
        ]
    },
    {
        "question": "Musician and satirist Allie Goertz wrote a song about the 'The Simpsons' character Milhouse, who Matt Groening named after who?",
        "ground_truth": "President Richard Nixon",
        "contexts": [
            'Allison Beth "Allie" Goertz (born March 2, 1991) is an American musician.',
            "Goertz is known for her satirical songs based on various pop culture topics.",
            'Milhouse Mussolini van Houten is a fictional character featured in the animated television series "The Simpsons", voiced by Pamela Hayden, and created by Matt Groening who named the character after President Richard Nixon\'s middle name.'
        ]
    },
]


async def debug_embedding(query: str) -> list[float]:
    """Debug: Generate embedding for query."""
    from src.components.shared.embedding_service import get_embedding_service

    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]STEP 1: Query Embedding[/bold cyan]"))
    console.print("="*80)

    console.print(f"[yellow]Query:[/yellow] {query}")
    console.print(f"[yellow]Query length:[/yellow] {len(query)} chars")

    embedding_service = get_embedding_service()
    embedding = await embedding_service.embed_single(query)

    console.print(f"[green]✓ Embedding generated[/green]")
    console.print(f"  - Model: {embedding_service.model_name}")
    console.print(f"  - Dimension: {len(embedding)}")
    console.print(f"  - First 5 values: {[round(x, 4) for x in embedding[:5]]}")
    console.print(f"  - L2 norm: {sum(x**2 for x in embedding)**0.5:.4f}")

    return embedding


async def debug_intent_classification(query: str) -> dict:
    """Debug: Intent classification."""
    from src.components.retrieval.intent_classifier import IntentClassifier

    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]STEP 2: Intent Classification[/bold cyan]"))
    console.print("="*80)

    classifier = IntentClassifier()
    result = await classifier.classify(query)

    console.print(f"[yellow]Query:[/yellow] {query[:60]}...")
    console.print(f"[green]Intent:[/green] {result.intent.value}")
    console.print(f"[green]Confidence:[/green] {result.confidence:.2f}")

    # Show weights from result (already resolved by classifier)
    weights = result.weights

    console.print(f"\n[blue]Search Weights for intent '{result.intent.value}':[/blue]")
    console.print(f"  - vector: {weights.vector}")
    console.print(f"  - bm25: {weights.bm25}")
    console.print(f"  - local: {weights.local}")
    console.print(f"  - global: {weights.global_}")

    return result


async def debug_four_way_search(query: str, namespace: str = "eval_hotpotqa") -> dict:
    """Debug: Full 4-way hybrid search."""
    from src.components.retrieval.four_way_hybrid_search import FourWayHybridSearch

    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]STEP 3: 4-Way Hybrid Search[/bold cyan]"))
    console.print("="*80)

    search = FourWayHybridSearch()

    console.print(f"[yellow]Query:[/yellow] {query[:60]}...")
    console.print(f"[yellow]Namespace:[/yellow] {namespace}")
    console.print(f"[yellow]Top-k:[/yellow] 5")

    # Call search (returns dict, not dataclass)
    results = await search.search(
        query=query,
        allowed_namespaces=[namespace],
        top_k=5,
        use_reranking=True
    )

    console.print(f"\n[green]✓ Search completed[/green]")
    console.print(f"  - Total results: {len(results.get('results', []))}")
    console.print(f"  - Intent: {results.get('intent', 'N/A')}")

    # Extract metadata (FourWaySearchMetadata dataclass)
    metadata = results.get("metadata")
    if metadata:
        console.print(f"  - Total latency: {metadata.total_latency_ms:.0f}ms")
        console.print(f"  - Channels executed: {metadata.channels_executed}")

        # Show weights used
        weights = metadata.weights
        console.print(f"\n[blue]Weights Applied:[/blue]")
        console.print(f"  - Vector: {weights.get('vector', 0)}")
        console.print(f"  - BM25: {weights.get('bm25', 0)}")
        console.print(f"  - Local: {weights.get('local', 0)}")
        console.print(f"  - Global: {weights.get('global', 0)}")

        # Show channel contributions
        console.print(f"\n[blue]Channel Contributions:[/blue]")
        console.print(f"  - Vector: {metadata.vector_results_count} results")
        console.print(f"  - BM25: {metadata.bm25_results_count} results")
        console.print(f"  - Graph Local: {metadata.graph_local_results_count} results")
        console.print(f"  - Graph Global: {metadata.graph_global_results_count} results")

    # Show final results
    table = Table(title="Final Fused & Reranked Results")
    table.add_column("Rank", style="cyan")
    table.add_column("RRF Score", style="green")
    table.add_column("Rerank Score", style="magenta")
    table.add_column("Content", style="white", max_width=70)

    result_docs = results.get("results", [])
    for i, doc in enumerate(result_docs[:5], 1):
        # Results use "text" key, not "content"
        text = doc.get("text", "") or doc.get("content", "")
        content_preview = text[:70] if text else "N/A"
        rrf_score = doc.get("rrf_score")
        rerank_score = doc.get("rerank_score")
        table.add_row(
            str(i),
            f"{rrf_score:.4f}" if rrf_score else "N/A",
            f"{rerank_score:.4f}" if rerank_score else "N/A",
            content_preview + "..."
        )

    console.print(table)

    # Show full contexts
    console.print(f"\n[blue]Full Retrieved Contexts:[/blue]")
    for i, doc in enumerate(result_docs[:5], 1):
        text = doc.get("text", "") or doc.get("content", "N/A")
        console.print(f"\n[yellow]Context {i}:[/yellow]")
        console.print(Panel(text, border_style="dim"))

    return results


async def debug_llm_answer(query: str, contexts: list[str]) -> str:
    """Debug: LLM answer generation."""
    from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
    from src.components.llm_proxy.models import LLMTask, TaskType

    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]STEP 4: LLM Answer Generation[/bold cyan]"))
    console.print("="*80)

    llm = AegisLLMProxy()

    # Build prompt
    context_text = "\n\n".join(f"Context {i+1}: {c}" for i, c in enumerate(contexts))

    prompt = f"""Based on the following contexts, answer the question concisely.

{context_text}

Question: {query}

Answer:"""

    console.print(f"[yellow]Prompt length:[/yellow] {len(prompt)} chars")
    console.print(f"[yellow]Number of contexts:[/yellow] {len(contexts)}")

    console.print(f"\n[blue]Full Prompt:[/blue]")
    console.print(Panel(prompt, title="LLM Prompt", border_style="blue"))

    # Create LLMTask object
    task = LLMTask(
        task_type=TaskType.GENERATION,
        prompt=prompt,
    )

    # Call LLM
    console.print("\n[yellow]Calling LLM...[/yellow]")
    response = await llm.generate(task)

    console.print(f"\n[green]✓ LLM Response:[/green]")
    console.print(f"  - Provider: {response.provider}")
    console.print(f"  - Model: {response.model}")
    console.print(f"  - Latency: {response.latency_ms:.0f}ms" if response.latency_ms else "  - Latency: N/A")
    console.print(f"  - Tokens: {response.tokens_used} (in: {response.tokens_input}, out: {response.tokens_output})")
    console.print(f"  - Cost: ${response.cost_usd:.6f}")
    console.print(Panel(response.content, title="LLM Answer", border_style="green"))

    return response.content


async def run_full_debug(question_idx: int = 0):
    """Run full debug analysis for a single question."""

    question_data = TEST_QUESTIONS[question_idx]
    query = question_data["question"]
    ground_truth = question_data["ground_truth"]
    expected_contexts = question_data["contexts"]

    console.print("\n" + "#"*80)
    console.print(Panel(
        f"[bold green]DEBUGGING QUERY #{question_idx + 1}[/bold green]\n\n"
        f"[yellow]Question:[/yellow] {query}\n\n"
        f"[yellow]Expected Answer:[/yellow] {ground_truth}",
        title="Debug Session",
        border_style="green"
    ))
    console.print("#"*80)

    # Step 1: Embedding
    embedding = await debug_embedding(query)

    # Step 2: Intent Classification
    intent_result = await debug_intent_classification(query)

    # Step 3: 4-Way Hybrid Search
    search_results = await debug_four_way_search(query)

    # Extract contexts from search results (dict format with "text" key)
    retrieved_contexts = [
        doc.get("text", "") or doc.get("content", "")
        for doc in search_results.get("results", [])[:5]
        if doc.get("text") or doc.get("content")
    ]

    # Step 4: LLM Answer Generation
    answer = await debug_llm_answer(query, retrieved_contexts)

    # Final Summary
    console.print("\n" + "="*80)
    console.print(Panel("[bold cyan]SUMMARY[/bold cyan]"))
    console.print("="*80)

    console.print(f"[yellow]Question:[/yellow] {query}")
    console.print(f"[yellow]Ground Truth:[/yellow] {ground_truth}")
    console.print(f"[green]Generated Answer:[/green] {answer}")

    # Check if answer contains ground truth
    answer_lower = answer.lower()
    truth_lower = ground_truth.lower()

    if truth_lower in answer_lower:
        console.print(f"\n[bold green]✓ Answer contains ground truth![/bold green]")
    else:
        console.print(f"\n[bold red]✗ Answer does NOT contain ground truth[/bold red]")
        console.print(f"[red]Expected '{ground_truth}' in answer[/red]")

    # Check context coverage
    console.print(f"\n[blue]Expected Contexts Coverage:[/blue]")
    for i, expected in enumerate(expected_contexts, 1):
        found = any(expected[:50] in ctx for ctx in retrieved_contexts)
        status = "[green]✓[/green]" if found else "[red]✗[/red]"
        console.print(f"  {status} Context {i}: {expected[:60]}...")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Debug single query data flow")
    parser.add_argument("--question", "-q", type=int, default=0,
                        help="Question index (0 or 1)")
    parser.add_argument("--custom", "-c", type=str, default=None,
                        help="Custom question to test")
    args = parser.parse_args()

    if args.custom:
        # Add custom question
        TEST_QUESTIONS.insert(0, {
            "question": args.custom,
            "ground_truth": "Unknown",
            "contexts": []
        })
        await run_full_debug(0)
    else:
        await run_full_debug(args.question)


if __name__ == "__main__":
    asyncio.run(main())
