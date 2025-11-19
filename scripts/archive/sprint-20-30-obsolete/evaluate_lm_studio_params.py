#!/usr/bin/env python3
"""
Sprint 20 Feature 20.2: LM Studio Advanced Parameters Evaluation

Tests advanced parameters unavailable in Ollama:
- Sampling strategies (mirostat, typical_p, min_p)
- Performance tuning (thread count, batch size)

Compares different configurations to find optimal settings for Gemma 3 4B.

Usage:
    python scripts/evaluate_lm_studio_params.py
    python scripts/evaluate_lm_studio_params.py --config baseline
    python scripts/evaluate_lm_studio_params.py --quick  # Only 2 questions

Requirements:
    - LM Studio running on http://localhost:1234
    - gemma-3-4b-it model loaded
    - Test questions from test_questions.yaml
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

console = Console()

# Configuration
LM_STUDIO_API = "http://localhost:1234/v1"
MODEL_NAME = "gemma-3-4b-it"

# Sampling configurations to test
SAMPLING_CONFIGS = [
    {
        "name": "ollama_baseline",
        "description": "Ollama default parameters (baseline)",
        "params": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
        },
    },
    {
        "name": "mirostat_v2",
        "description": "Mirostat 2.0 - Adaptive sampling for consistent perplexity",
        "params": {
            "temperature": 0.7,
            # LM Studio uses different parameter names for mirostat
            # These will be added to the request JSON directly
        },
        "extra_params": {
            "mirostat_mode": 2,
            "mirostat_tau": 5.0,
            "mirostat_eta": 0.1,
        },
    },
    {
        "name": "typical_sampling",
        "description": "Typical sampling with min_p threshold",
        "params": {
            "temperature": 0.7,
            "top_p": 0.9,  # Can combine with typical_p
        },
        "extra_params": {
            "typical_p": 0.9,
            "min_p": 0.05,
        },
    },
    {
        "name": "low_temp_precise",
        "description": "Low temperature for precise, deterministic answers",
        "params": {
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 20,
        },
        "extra_params": {
            "min_p": 0.1,
        },
    },
    {
        "name": "high_temp_creative",
        "description": "High temperature for creative, varied answers",
        "params": {
            "temperature": 0.9,
            "top_p": 0.95,
            "top_k": 50,
        },
    },
]


async def load_test_questions(quick: bool = False) -> List[Dict]:
    """Load test questions from YAML file."""
    # Try NO-RAG version first (for when DB is empty)
    questions_file_norag = Path(__file__).parent / "test_questions_norag.yaml"
    questions_file = Path(__file__).parent / "test_questions.yaml"

    if questions_file_norag.exists():
        console.print("[yellow]Using NO-RAG test questions (no document context needed)[/yellow]")
        with open(questions_file_norag, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            questions = data.get("questions", [])
    elif questions_file.exists():
        with open(questions_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            questions = data.get("questions", [])
    else:
        console.print(f"[red]Error: No test questions file found![/red]")
        raise FileNotFoundError("test_questions.yaml or test_questions_norag.yaml")

    if quick:
        # Use only 2 questions for quick testing (1 German, 1 English, different tiers)
        return [q for q in questions if q["tier"] in [1, 2]][:2]

    return questions


async def test_single_question(
    config: Dict,
    question_data: Dict,
    question_num: int,
    total_questions: int,
) -> Dict:
    """Test a single question with specified sampling configuration."""
    question = question_data["question"]
    language = question_data["language"]
    tier = question_data["tier"]

    console.print(
        f"\n[cyan]Question {question_num}/{total_questions} (Tier {tier}, {language.upper()})[/cyan]"
    )
    console.print(
        f"[dim]{question[:80]}...[/dim]" if len(question) > 80 else f"[dim]{question}[/dim]"
    )
    console.print(f"[yellow]Config: {config['name']}[/yellow]")

    # Build request payload
    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant specialized in VBScript and Automation. "
            f"Answer in {'German' if language == 'de' else 'English'}.",
        },
        {"role": "user", "content": question},
    ]

    request_payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 500,
        "stream": False,
        **config.get("params", {}),
        **config.get("extra_params", {}),
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            start_time = time.perf_counter()

            response = await client.post(f"{LM_STUDIO_API}/chat/completions", json=request_payload)

            elapsed_time = time.perf_counter() - start_time

            if response.status_code != 200:
                console.print(f"[red]ERROR - API Error: {response.status_code}[/red]")
                console.print(f"[dim]{response.text}[/dim]")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "config_name": config["name"],
                    "question": question,
                    "language": language,
                    "tier": tier,
                }

            data = response.json()

            # Extract metrics
            answer = data["choices"][0]["message"]["content"]
            completion_tokens = data["usage"]["completion_tokens"]
            prompt_tokens = data["usage"]["prompt_tokens"]
            total_tokens = data["usage"]["total_tokens"]

            tokens_per_sec = completion_tokens / elapsed_time if elapsed_time > 0 else 0

            console.print(
                f"[green]OK - Generated ({completion_tokens} tokens, {tokens_per_sec:.1f} t/s, {elapsed_time:.2f}s)[/green]"
            )

            return {
                "success": True,
                "config_name": config["name"],
                "question": question,
                "language": language,
                "tier": tier,
                "answer": answer,
                "completion_tokens": completion_tokens,
                "prompt_tokens": prompt_tokens,
                "total_tokens": total_tokens,
                "time_seconds": elapsed_time,
                "tokens_per_sec": tokens_per_sec,
            }

    except httpx.TimeoutException:
        console.print(f"[red]ERROR - Timeout after 120s[/red]")
        return {
            "success": False,
            "error": "Timeout",
            "config_name": config["name"],
            "question": question,
            "language": language,
            "tier": tier,
        }
    except Exception as e:
        console.print(f"[red]ERROR: {e}[/red]")
        return {
            "success": False,
            "error": str(e),
            "config_name": config["name"],
            "question": question,
            "language": language,
            "tier": tier,
        }


async def evaluate_config(
    config: Dict,
    questions: List[Dict],
    config_num: int,
    total_configs: int,
) -> List[Dict]:
    """Evaluate a single configuration on all questions."""
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print(
        f"[bold cyan]Configuration {config_num}/{total_configs}: {config['name']}[/bold cyan]"
    )
    console.print(f"[bold cyan]{config['description']}[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]")

    results = []

    for i, question_data in enumerate(questions, 1):
        result = await test_single_question(
            config=config,
            question_data=question_data,
            question_num=i,
            total_questions=len(questions),
        )
        results.append(result)

        # Small delay between questions
        await asyncio.sleep(0.5)

    return results


def calculate_config_metrics(results: List[Dict]) -> Dict:
    """Calculate aggregate metrics for a configuration."""
    successful = [r for r in results if r.get("success", False)]

    if not successful:
        return {
            "total_questions": len(results),
            "successful": 0,
            "failed": len(results),
            "avg_tokens_per_sec": 0.0,
            "avg_time_seconds": 0.0,
            "total_completion_tokens": 0,
            "avg_completion_tokens": 0.0,
        }

    return {
        "total_questions": len(results),
        "successful": len(successful),
        "failed": len(results) - len(successful),
        "avg_tokens_per_sec": sum(r["tokens_per_sec"] for r in successful) / len(successful),
        "avg_time_seconds": sum(r["time_seconds"] for r in successful) / len(successful),
        "total_completion_tokens": sum(r["completion_tokens"] for r in successful),
        "avg_completion_tokens": sum(r["completion_tokens"] for r in successful) / len(successful),
    }


def print_comparison_table(all_results: Dict[str, List[Dict]]):
    """Print comparison table of all configurations."""
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold cyan]PARAMETER EVALUATION SUMMARY[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

    table = Table(
        show_header=True, header_style="bold magenta", title="LM Studio Parameter Comparison"
    )
    table.add_column("Configuration", style="cyan", width=20)
    table.add_column("Success", justify="right", width=8)
    table.add_column("Avg t/s", justify="right", width=10)
    table.add_column("Avg Time", justify="right", width=10)
    table.add_column("Avg Tokens", justify="right", width=10)
    table.add_column("Total Tokens", justify="right", width=12)

    config_metrics = {}

    for config_name, results in all_results.items():
        metrics = calculate_config_metrics(results)
        config_metrics[config_name] = metrics

        success_rate = f"{metrics['successful']}/{metrics['total_questions']}"

        table.add_row(
            config_name,
            success_rate,
            f"{metrics['avg_tokens_per_sec']:.1f}",
            f"{metrics['avg_time_seconds']:.2f}s",
            f"{metrics['avg_completion_tokens']:.0f}",
            str(metrics["total_completion_tokens"]),
        )

    console.print(table)

    # Find best configs
    successful_configs = {k: v for k, v in config_metrics.items() if v["successful"] > 0}

    if successful_configs:
        fastest = max(successful_configs.items(), key=lambda x: x[1]["avg_tokens_per_sec"])
        most_tokens = max(successful_configs.items(), key=lambda x: x[1]["avg_completion_tokens"])

        console.print(
            f"\n[bold green]FASTEST Configuration:[/bold green] {fastest[0]} ({fastest[1]['avg_tokens_per_sec']:.1f} t/s)"
        )
        console.print(
            f"[bold green]MOST DETAILED Answers:[/bold green] {most_tokens[0]} ({most_tokens[1]['avg_completion_tokens']:.0f} tokens avg)"
        )

    # Find configuration from SAMPLING_CONFIGS
    config_details = {c["name"]: c for c in SAMPLING_CONFIGS}

    console.print("\n[bold yellow]Configuration Details:[/bold yellow]")
    for config_name in all_results.keys():
        if config_name in config_details:
            config = config_details[config_name]
            console.print(f"\n[cyan]{config_name}:[/cyan]")
            console.print(f"  [dim]{config['description']}[/dim]")
            console.print(f"  Params: {json.dumps(config.get('params', {}), indent=10)}")
            if "extra_params" in config:
                console.print(f"  Extra: {json.dumps(config['extra_params'], indent=10)}")


def print_next_steps():
    """Print next steps after evaluation."""
    console.print(
        Panel.fit(
            "[bold yellow]Next Steps:[/bold yellow]\n\n"
            "1. Review detailed results in:\n"
            "   [cyan]docs/sprints/SPRINT_20_LM_STUDIO_PARAMS.json[/cyan]\n\n"
            "2. Perform human evaluation:\n"
            "   - Read answers for each configuration\n"
            "   - Rate quality using rubric from test_questions.yaml\n"
            "   - Consider: accuracy, fluency, completeness\n\n"
            "3. A/B test best config vs Ollama:\n"
            "   - Run evaluate_chat_models.py with Ollama\n"
            "   - Compare quality + speed\n\n"
            "4. Document findings:\n"
            "   - Create SPRINT_20_LM_STUDIO_EVALUATION.md\n"
            "   - Update LMSTUDIO_VS_OLLAMA_ANALYSIS.md\n"
            "   - Decide: Use LM Studio params or stick with Ollama defaults",
            title="Evaluation Complete",
            border_style="green",
        )
    )


async def verify_lm_studio() -> bool:
    """Verify LM Studio is running and model is available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LM_STUDIO_API}/models")

            if response.status_code != 200:
                console.print(f"[red]ERROR - LM Studio API returned {response.status_code}[/red]")
                return False

            data = response.json()
            models = [m["id"] for m in data.get("data", [])]

            if MODEL_NAME not in models:
                console.print(f"[red]ERROR - Model '{MODEL_NAME}' not found in LM Studio[/red]")
                console.print(f"[yellow]Available models: {', '.join(models)}[/yellow]")
                return False

            console.print(f"[green]OK - LM Studio running with model '{MODEL_NAME}'[/green]")
            return True

    except httpx.ConnectError:
        console.print(f"[red]ERROR - Cannot connect to LM Studio at {LM_STUDIO_API}[/red]")
        console.print("[yellow]Please start LM Studio Local Server on port 1234[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]ERROR - verifying LM Studio: {e}[/red]")
        return False


async def main():
    """Main evaluation execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate LM Studio advanced parameters")
    parser.add_argument(
        "--config",
        choices=[c["name"] for c in SAMPLING_CONFIGS] + ["all"],
        default="all",
        help="Configuration to test (default: all)",
    )
    parser.add_argument("--quick", action="store_true", help="Quick test with only 2 questions")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/sprints/SPRINT_20_LM_STUDIO_PARAMS.json"),
        help="Output file for results",
    )

    args = parser.parse_args()

    # Print header
    console.print(
        Panel.fit(
            "[bold cyan]Sprint 20 Feature 20.2: LM Studio Parameter Evaluation[/bold cyan]\n"
            "[dim]Testing advanced parameters unavailable in Ollama[/dim]",
            border_style="cyan",
        )
    )

    # Verify LM Studio is running
    console.print("\n[yellow]Verifying LM Studio...[/yellow]")
    if not await verify_lm_studio():
        console.print("\n[red]Cannot proceed without LM Studio. Please:[/red]")
        console.print("1. Start LM Studio")
        console.print("2. Go to 'Local Server' tab")
        console.print("3. Load 'gemma-3-4b-it' model")
        console.print("4. Click 'Start Server' (port 1234)")
        return

    # Load questions
    console.print("\n[yellow]Loading test questions...[/yellow]")
    questions = await load_test_questions(quick=args.quick)
    console.print(f"[green]OK - Loaded {len(questions)} test questions[/green]")

    if args.quick:
        console.print("[yellow]QUICK MODE: Using only 2 questions[/yellow]")

    # Determine which configs to test
    if args.config == "all":
        configs_to_test = SAMPLING_CONFIGS
    else:
        configs_to_test = [c for c in SAMPLING_CONFIGS if c["name"] == args.config]

    console.print(f"\n[cyan]Testing {len(configs_to_test)} configuration(s)[/cyan]\n")

    # Run evaluation
    all_results = {}

    for i, config in enumerate(configs_to_test, 1):
        results = await evaluate_config(
            config=config, questions=questions, config_num=i, total_configs=len(configs_to_test)
        )
        all_results[config["name"]] = results

    # Print comparison
    if len(all_results) > 1:
        print_comparison_table(all_results)

    # Save results
    output_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "model": MODEL_NAME,
        "lm_studio_api": LM_STUDIO_API,
        "total_questions": len(questions),
        "configurations_tested": len(configs_to_test),
        "quick_mode": args.quick,
        "configurations": [
            {
                "name": c["name"],
                "description": c["description"],
                "params": c.get("params", {}),
                "extra_params": c.get("extra_params", {}),
            }
            for c in configs_to_test
        ],
        "results": all_results,
        "metrics": {
            config_name: calculate_config_metrics(results)
            for config_name, results in all_results.items()
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    console.print(f"\n[bold green]OK - Results saved to {args.output}[/bold green]")

    # Print next steps
    print_next_steps()


if __name__ == "__main__":
    asyncio.run(main())
