#!/usr/bin/env python3
"""
Sprint 20 Feature 20.4: Ollama Model Preloading

Preloads Ollama models into VRAM to eliminate cold start delays.

Usage:
    python scripts/preload_ollama_models.py
    python scripts/preload_ollama_models.py --models gemma-3-4b-it-Q8_0 llama3.2:3b
    python scripts/preload_ollama_models.py --keep-alive 60m

Benefits:
    - Eliminates 76-second model load times
    - Models stay in VRAM for configured duration (default: 30m)
    - Subsequent requests are instant (no cold start)

Requirements:
    - Ollama running (docker compose up ollama)
    - Models already pulled (ollama pull <model>)
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"

# Default models for AEGIS RAG
DEFAULT_MODELS = [
    "gemma-3-4b-it-Q8_0",  # Entity/Relation extraction (Phase 3)
    "llama3.2:3b",  # Alternative chat model
    "nomic-embed-text",  # Embeddings (Qdrant)
]


async def check_ollama_running() -> bool:
    """Check if Ollama server is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def list_available_models() -> List[str]:
    """List all models available in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")

            if response.status_code != 200:
                return []

            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return models

    except Exception as e:
        console.print(f"[red]Error listing models: {e}[/red]")
        return []


async def preload_model(model_name: str, keep_alive: str = "30m") -> dict:
    """
    Preload a single model into VRAM.

    Args:
        model_name: Model identifier (e.g., "gemma-3-4b-it-Q8_0")
        keep_alive: Duration to keep model in VRAM (e.g., "30m", "1h")

    Returns:
        Dict with success status, load time, and model info
    """
    console.print(f"\n[cyan]Preloading: {model_name}[/cyan]")

    start_time = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Send empty prompt to load model
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",  # Empty prompt just loads model
                    "stream": False,
                    "keep_alive": keep_alive,
                },
            )

            load_time = time.perf_counter() - start_time

            if response.status_code == 200:
                data = response.json()

                # Get model info
                info_response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/show", json={"name": model_name}
                )

                model_info = {}
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    model_info = {
                        "size": info_data.get("size", 0) / 1e9,  # Convert to GB
                        "family": info_data.get("details", {}).get("family", "unknown"),
                    }

                console.print(f"[green]OK - Loaded in {load_time:.2f}s[/green]")
                if model_info.get("size"):
                    console.print(
                        f"[dim]  Size: {model_info['size']:.1f} GB, Family: {model_info.get('family', 'N/A')}[/dim]"
                    )

                return {
                    "model": model_name,
                    "success": True,
                    "load_time_seconds": load_time,
                    "keep_alive": keep_alive,
                    **model_info,
                }
            else:
                console.print(f"[red]ERROR - HTTP {response.status_code}[/red]")
                console.print(f"[dim]{response.text[:200]}[/dim]")

                return {
                    "model": model_name,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                }

    except httpx.TimeoutException:
        load_time = time.perf_counter() - start_time
        console.print(f"[red]ERROR - Timeout after {load_time:.1f}s[/red]")

        return {
            "model": model_name,
            "success": False,
            "error": "Timeout",
            "load_time_seconds": load_time,
        }

    except Exception as e:
        load_time = time.perf_counter() - start_time
        console.print(f"[red]ERROR: {e}[/red]")

        return {
            "model": model_name,
            "success": False,
            "error": str(e),
            "load_time_seconds": load_time,
        }


async def preload_all_models(models: List[str], keep_alive: str = "30m") -> List[dict]:
    """Preload multiple models."""
    console.print(f"\n[yellow]Preloading {len(models)} model(s)...[/yellow]")
    console.print(f"[dim]Keep alive: {keep_alive}[/dim]\n")

    results = []

    for model in models:
        result = await preload_model(model, keep_alive)
        results.append(result)

        # Small delay between models
        await asyncio.sleep(1)

    return results


def print_summary(results: List[dict]):
    """Print summary table of preload results."""
    console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
    console.print("[bold cyan]PRELOAD SUMMARY[/bold cyan]")
    console.print(f"[bold cyan]{'='*70}[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan", width=30)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Load Time", justify="right", width=12)
    table.add_column("Size (GB)", justify="right", width=10)
    table.add_column("Keep Alive", justify="right", width=12)

    successful = 0
    total_load_time = 0.0
    total_size = 0.0

    for result in results:
        if result["success"]:
            successful += 1
            total_load_time += result.get("load_time_seconds", 0)
            total_size += result.get("size", 0)

            table.add_row(
                result["model"],
                "[green]OK[/green]",
                f"{result['load_time_seconds']:.2f}s",
                f"{result.get('size', 0):.1f}",
                result.get("keep_alive", "N/A"),
            )
        else:
            table.add_row(
                result["model"],
                "[red]FAILED[/red]",
                (
                    f"{result.get('load_time_seconds', 0):.2f}s"
                    if "load_time_seconds" in result
                    else "N/A"
                ),
                "N/A",
                "N/A",
            )

    console.print(table)

    console.print(f"\n[bold]Success Rate:[/bold] {successful}/{len(results)}")
    console.print(f"[bold]Total Load Time:[/bold] {total_load_time:.2f}s")
    console.print(f"[bold]Total VRAM Used:[/bold] ~{total_size:.1f} GB")

    console.print("\n[bold green]Models are now loaded in VRAM![/bold green]")
    console.print("[dim]Subsequent requests will be instant (no cold start)[/dim]")


async def main():
    """Main preload execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Preload Ollama models into VRAM")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Models to preload (default: AEGIS RAG models)",
    )
    parser.add_argument(
        "--keep-alive", default="30m", help="Duration to keep models in VRAM (default: 30m)"
    )
    parser.add_argument("--list", action="store_true", help="List available models and exit")

    args = parser.parse_args()

    # Print header
    console.print(
        Panel.fit(
            "[bold cyan]Sprint 20 Feature 20.4: Ollama Model Preloading[/bold cyan]\n"
            "[dim]Eliminates cold start delays by preloading models into VRAM[/dim]",
            border_style="cyan",
        )
    )

    # Check Ollama is running
    console.print("\n[yellow]Checking Ollama server...[/yellow]")
    if not await check_ollama_running():
        console.print("[red]ERROR - Ollama is not running![/red]")
        console.print("[yellow]Start Ollama with: docker compose up ollama[/yellow]")
        sys.exit(1)

    console.print("[green]OK - Ollama is running[/green]")

    # List available models if requested
    if args.list:
        console.print("\n[yellow]Available models:[/yellow]")
        available_models = await list_available_models()

        if available_models:
            for model in available_models:
                console.print(f"  - {model}")
        else:
            console.print("[red]No models found or error listing models[/red]")

        sys.exit(0)

    # Verify models exist
    available_models = await list_available_models()
    models_to_load = args.models

    missing_models = [m for m in models_to_load if m not in available_models]
    if missing_models:
        console.print(f"\n[yellow]Warning: Some models not found:[/yellow]")
        for model in missing_models:
            console.print(f"  [red]✗[/red] {model}")
        console.print(f"\n[yellow]Pull missing models with:[/yellow]")
        for model in missing_models:
            console.print(f"  ollama pull {model}")

        # Remove missing models from load list
        models_to_load = [m for m in models_to_load if m in available_models]

        if not models_to_load:
            console.print("\n[red]No valid models to preload. Exiting.[/red]")
            sys.exit(1)

    # Preload models
    results = await preload_all_models(models_to_load, args.keep_alive)

    # Print summary
    print_summary(results)

    # Return exit code based on success
    failed = sum(1 for r in results if not r["success"])
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
