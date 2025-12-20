#!/usr/bin/env python3
"""
Sprint 20 Feature 20.1: Chat Model Evaluation (Gemma vs Llama)

Compares llama3.2:3b vs gemma-3-4b-it-Q8_0 for chat generation using
document-based questions from indexed VBScript/Automation documents.

Usage:
    python scripts/evaluate_chat_models.py
    python scripts/evaluate_chat_models.py --model llama3.2:3b
    python scripts/evaluate_chat_models.py --model gemma-3-4b-it-Q8_0
    python scripts/evaluate_chat_models.py --all  # Both models

Requirements:
    - Documents must be indexed (run scripts/index_three_specific_docs.py first)
    - Ollama running with both models available
    - Qdrant running with indexed chunks
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import httpx
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "aegis_documents"

# Models to evaluate
MODELS = {
    "llama3.2:3b": "llama3.2:3b",
    "gemma": "gemma-3-4b-it-Q8_0",
}


async def load_test_questions() -> list[dict]:
    """Load test questions from YAML file."""
    questions_file = Path(__file__).parent / "test_questions.yaml"

    if not questions_file.exists():
        console.print(f"[red]Error: {questions_file} not found![/red]")
        console.print("[yellow]Please create test_questions.yaml first.[/yellow]")
        raise FileNotFoundError(f"{questions_file} does not exist")

    with open(questions_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("questions", [])


async def retrieve_context(question: str, top_k: int = 5) -> list[str]:
    """
    Retrieve relevant context from Qdrant for the question.

    Uses hybrid search (vector + text) to find most relevant chunks.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # For simplicity, we'll use Qdrant's search API directly
            # In production, this would use the RAG pipeline

            # First, get embeddings from Ollama
            embed_response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": question,
                },
            )

            if embed_response.status_code != 200:
                console.print(
                    "[yellow]Warning: Embedding failed, using question without context[/yellow]"
                )
                return []

            embedding = embed_response.json()["embedding"]

            # Search Qdrant
            search_response = await client.post(
                f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{QDRANT_COLLECTION}/points/search",
                json={
                    "vector": embedding,
                    "limit": top_k,
                    "with_payload": True,
                },
            )

            if search_response.status_code != 200:
                console.print("[yellow]Warning: Qdrant search failed[/yellow]")
                return []

            results = search_response.json()["result"]

            # Extract text chunks
            contexts = []
            for hit in results:
                payload = hit.get("payload", {})
                text = payload.get("text", payload.get("content", ""))
                if text:
                    contexts.append(text)

            return contexts

    except Exception as e:
        console.print(f"[yellow]Warning: Context retrieval failed: {e}[/yellow]")
        return []


async def generate_answer(
    model: str,
    question: str,
    context: list[str],
    language: str,
) -> dict:
    """
    Generate answer using specified model with RAG context.

    Returns:
        Dict with answer, metrics (tokens/sec, TTFT, tokens, time)
    """
    # Build prompt with context
    if context:
        context_text = "\n\n".join([f"[Context {i+1}]\n{ctx}" for i, ctx in enumerate(context[:3])])
        system_prompt = (
            f"You are a helpful assistant specialized in VBScript and Automation. "
            f"Answer the following question based on the provided context. "
            f"If the answer is in the context, cite the relevant context section. "
            f"Answer in {'German' if language == 'de' else 'English'}.\n\n"
            f"{context_text}"
        )
    else:
        system_prompt = (
            f"You are a helpful assistant specialized in VBScript and Automation. "
            f"Answer in {'German' if language == 'de' else 'English'}."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            start_time = time.perf_counter()
            ttft = None
            tokens = 0
            answer_text = ""

            # Stream response to measure TTFT
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                    },
                },
            ) as response:
                first_token_received = False

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)

                        if not first_token_received and not chunk.get("done", False):
                            ttft = time.perf_counter() - start_time
                            first_token_received = True

                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            answer_text += content
                            tokens += 1

                        if chunk.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

            total_time = time.perf_counter() - start_time
            tokens_per_sec = tokens / total_time if total_time > 0 else 0

            return {
                "answer": answer_text,
                "tokens": tokens,
                "time_seconds": total_time,
                "ttft_seconds": ttft or 0.0,
                "tokens_per_sec": tokens_per_sec,
                "success": True,
            }

    except Exception as e:
        console.print(f"[red]Error generating answer: {e}[/red]")
        return {
            "answer": f"ERROR: {str(e)}",
            "tokens": 0,
            "time_seconds": 0.0,
            "ttft_seconds": 0.0,
            "tokens_per_sec": 0.0,
            "success": False,
            "error": str(e),
        }


async def evaluate_single_question(
    model: str,
    question_data: dict,
    question_num: int,
    total_questions: int,
) -> dict:
    """Evaluate a single question with specified model."""
    question = question_data["question"]
    language = question_data["language"]
    tier = question_data["tier"]
    expected_topics = question_data.get("expected_topics", [])
    document = question_data.get("document", "N/A")

    console.print(
        f"\n[cyan]Question {question_num}/{total_questions} (Tier {tier}, {language.upper()})[/cyan]"
    )
    console.print(f"[dim]{question}[/dim]")

    # Retrieve context
    console.print("[yellow]Retrieving context from Qdrant...[/yellow]")
    context = await retrieve_context(question, top_k=5)
    console.print(f"[green]Retrieved {len(context)} context chunks[/green]")

    # Generate answer
    console.print(f"[yellow]Generating answer with {model}...[/yellow]")
    result = await generate_answer(model, question, context, language)

    if result["success"]:
        console.print(
            f"[green]✓ Answer generated ({result['tokens']} tokens, {result['tokens_per_sec']:.1f} t/s)[/green]"
        )
        console.print(
            f"[dim]TTFT: {result['ttft_seconds']:.2f}s, Total: {result['time_seconds']:.2f}s[/dim]"
        )
    else:
        console.print(f"[red]✗ Failed: {result.get('error', 'Unknown error')}[/red]")

    return {
        "question_num": question_num,
        "question": question,
        "language": language,
        "tier": tier,
        "document": document,
        "expected_topics": expected_topics,
        "context_chunks": len(context),
        "model": model,
        **result,
    }


async def evaluate_model(model: str, questions: list[dict]) -> list[dict]:
    """Evaluate model on all test questions."""
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold cyan]Evaluating Model: {model}[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]")

    results = []

    for i, question_data in enumerate(questions, 1):
        result = await evaluate_single_question(
            model=model,
            question_data=question_data,
            question_num=i,
            total_questions=len(questions),
        )
        results.append(result)

        # Small delay between questions
        await asyncio.sleep(1)

    return results


def calculate_aggregate_metrics(results: list[dict]) -> dict:
    """Calculate aggregate performance metrics."""
    successful = [r for r in results if r.get("success", False)]

    if not successful:
        return {
            "total_questions": len(results),
            "successful": 0,
            "failed": len(results),
            "avg_tokens_per_sec": 0.0,
            "avg_ttft_seconds": 0.0,
            "avg_time_seconds": 0.0,
            "total_tokens": 0,
        }

    return {
        "total_questions": len(results),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "avg_tokens_per_sec": sum(r["tokens_per_sec"] for r in successful) / len(successful),
        "avg_ttft_seconds": sum(r["ttft_seconds"] for r in successful) / len(successful),
        "avg_time_seconds": sum(r["time_seconds"] for r in successful) / len(successful),
        "total_tokens": sum(r["tokens"] for r in successful),
    }


def print_summary_table(all_results: dict[str, list[dict]]):
    """Print comparison table of all models."""
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print("[bold cyan]BENCHMARK SUMMARY[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Tokens/Sec", justify="right")
    table.add_column("Avg TTFT (s)", justify="right")
    table.add_column("Avg Time (s)", justify="right")
    table.add_column("Total Tokens", justify="right")

    for model_name, results in all_results.items():
        metrics = calculate_aggregate_metrics(results)

        success_rate = f"{metrics['successful']}/{metrics['total_questions']}"

        table.add_row(
            model_name,
            success_rate,
            f"{metrics['avg_tokens_per_sec']:.1f}",
            f"{metrics['avg_ttft_seconds']:.2f}",
            f"{metrics['avg_time_seconds']:.2f}",
            str(metrics["total_tokens"]),
        )

    console.print(table)

    console.print("\n[bold yellow]Next Steps:[/bold yellow]")
    console.print("1. Review answers in docs/sprints/SPRINT_20_CHAT_BENCHMARK_RESULTS.json")
    console.print("2. Perform human evaluation using the rubric in SPRINT_20_PLAN.md")
    console.print("3. Fill decision matrix with quality scores")
    console.print("4. Document final recommendation in MODEL_COMPARISON_GEMMA_VS_LLAMA.md")


async def main():
    """Main benchmark execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate chat models (Gemma vs Llama)")
    parser.add_argument(
        "--model",
        choices=["llama3.2:3b", "gemma", "all"],
        default="all",
        help="Model to evaluate (default: all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/sprints/SPRINT_20_CHAT_BENCHMARK_RESULTS.json"),
        help="Output file for results",
    )

    args = parser.parse_args()

    console.print("[bold cyan]Sprint 20 Feature 20.1: Chat Model Evaluation[/bold cyan]")
    console.print("[dim]Comparing Gemma vs Llama for document-based chat generation[/dim]\n")

    # Load questions
    console.print("[yellow]Loading test questions...[/yellow]")
    questions = await load_test_questions()
    console.print(f"[green]Loaded {len(questions)} test questions[/green]")

    # Determine which models to test
    if args.model == "all":
        models_to_test = list(MODELS.keys())
    else:
        models_to_test = [args.model]

    # Run evaluation
    all_results = {}

    for model_key in models_to_test:
        model_name = MODELS[model_key]
        results = await evaluate_model(model_name, questions)
        all_results[model_name] = results

    # Calculate aggregate metrics
    for model_name, results in all_results.items():
        metrics = calculate_aggregate_metrics(results)
        console.print(f"\n[bold green]{model_name} Metrics:[/bold green]")
        console.print(f"  Success Rate: {metrics['successful']}/{metrics['total_questions']}")
        console.print(f"  Avg Tokens/Sec: {metrics['avg_tokens_per_sec']:.1f}")
        console.print(f"  Avg TTFT: {metrics['avg_ttft_seconds']:.2f}s")
        console.print(f"  Avg Time: {metrics['avg_time_seconds']:.2f}s")

    # Print comparison table
    if len(all_results) > 1:
        print_summary_table(all_results)

    # Save results
    output_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "models": list(all_results.keys()),
        "total_questions": len(questions),
        "results": all_results,
        "aggregate_metrics": {
            model: calculate_aggregate_metrics(results) for model, results in all_results.items()
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    console.print(f"\n[bold green]✓ Results saved to {args.output}[/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
