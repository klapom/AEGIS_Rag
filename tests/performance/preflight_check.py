"""Pre-flight check for performance benchmarks.

Verifies all required services are running before starting benchmarks.

Usage:
    poetry run python tests/performance/preflight_check.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def check_docling() -> tuple[bool, str]:
    """Check if Docling container is running and healthy."""
    try:
        import httpx
        # Docling is mapped to port 8080 externally (container uses 5001 internally)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8080/health")
            if response.status_code == 200:
                return True, "Docling container healthy (port 8080)"
            return False, f"Docling returned status {response.status_code}"
    except Exception as e:
        return False, f"Docling not reachable on port 8080: {type(e).__name__}"


async def check_ollama() -> tuple[bool, str]:
    """Check if Ollama is running."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check for embedding model
                has_bge = any("bge" in m.lower() for m in model_names)
                has_nomic = any("nomic" in m.lower() for m in model_names)
                if has_bge or has_nomic:
                    return True, f"Ollama running with {len(models)} models"
                return True, f"Ollama running but no embedding model found (models: {model_names[:5]})"
            return False, f"Ollama returned status {response.status_code}"
    except Exception as e:
        return False, f"Ollama not reachable: {type(e).__name__}"


async def check_qdrant() -> tuple[bool, str]:
    """Check if Qdrant is running."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:6333/collections")
            if response.status_code == 200:
                collections = response.json().get("result", {}).get("collections", [])
                return True, f"Qdrant running with {len(collections)} collections"
            return False, f"Qdrant returned status {response.status_code}"
    except Exception as e:
        return False, f"Qdrant not reachable: {type(e).__name__}"


async def check_neo4j() -> tuple[bool, str]:
    """Check if Neo4j is running."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Neo4j HTTP API
            response = await client.get("http://localhost:7474/")
            if response.status_code == 200:
                return True, "Neo4j running"
            return False, f"Neo4j returned status {response.status_code}"
    except Exception as e:
        return False, f"Neo4j not reachable: {type(e).__name__}"


async def check_gpu_memory() -> tuple[bool, str]:
    """Check GPU memory availability using nvidia-smi."""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 2:
                    free_mb = int(parts[0].strip())
                    total_mb = int(parts[1].strip())
                    used_mb = total_mb - free_mb
                    if free_mb > 2000:  # Need at least 2GB free
                        return True, f"GPU: {free_mb}MB free / {total_mb}MB total ({used_mb}MB used)"
                    return False, f"GPU memory low: {free_mb}MB free (need >2GB)"
        return False, f"nvidia-smi failed: {result.stderr}"
    except FileNotFoundError:
        return False, "nvidia-smi not found (no NVIDIA GPU?)"
    except Exception as e:
        return False, f"GPU check failed: {type(e).__name__}: {e}"


async def check_test_documents() -> tuple[bool, str]:
    """Check if test documents exist."""
    base = Path(
        r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents"
    )

    test_files = [
        "99_pptx_text/PerformanceTuning_textonly.pptx",
        "99_pdf_text/PerformanceTuning_textonly.pdf",
        "99_pptx_graphics/PerformanceTuning_graphics.pptx",
        "99_pdf_graphics/PerformanceTuning_graphics.pdf",
    ]

    found = []
    missing = []
    for f in test_files:
        if (base / f).exists():
            found.append(f)
        else:
            missing.append(f)

    if not missing:
        return True, f"All {len(found)} test documents found"
    return False, f"Missing {len(missing)} documents: {missing}"


async def main():
    """Run all pre-flight checks."""
    print("=" * 60)
    print("AEGISRAG PERFORMANCE BENCHMARK - PRE-FLIGHT CHECK")
    print("=" * 60)
    print()

    checks = [
        ("Docling Container", check_docling),
        ("Ollama (Embeddings)", check_ollama),
        ("Qdrant (Vectors)", check_qdrant),
        ("Neo4j (Graph)", check_neo4j),
        ("GPU Memory", check_gpu_memory),
        ("Test Documents", check_test_documents),
    ]

    results = []
    for name, check_fn in checks:
        print(f"Checking {name}...", end=" ", flush=True)
        ok, msg = await check_fn()
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {msg}")
        results.append((name, ok, msg))

    print()
    print("=" * 60)

    all_ok = all(r[1] for r in results)
    critical_ok = all(r[1] for r in results if r[0] in ["Docling Container", "Ollama (Embeddings)", "Qdrant (Vectors)"])

    if all_ok:
        print("All checks passed! Ready to run benchmarks.")
        print()
        print("Run benchmark with:")
        print("  poetry run python tests/performance/full_pipeline_benchmark.py")
        return 0
    elif critical_ok:
        print("WARNING: Some non-critical checks failed.")
        print("Benchmarks may run with limited functionality.")
        return 1
    else:
        print("ERROR: Critical services not available.")
        print()
        print("Start required services:")
        print("  1. Start Docker Desktop")
        print("  2. Start core services:")
        print("     docker compose up -d qdrant neo4j redis")
        print("  3. Start Docling with GPU (ingestion profile):")
        print("     docker compose --profile ingestion up -d docling")
        print("  4. Start Ollama (if not running as system service):")
        print("     ollama serve")
        print("  5. Pull embedding model (if needed):")
        print("     ollama pull bge-m3")
        print()
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
