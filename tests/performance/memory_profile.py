"""Memory Profiling for AegisRAG API.

Feature 28.4: Performance Testing - Memory Profiling

This script provides comprehensive memory profiling for the AegisRAG API:
1. py-spy profiling for CPU and memory usage
2. Memory snapshot analysis
3. Memory leak detection
4. Memory hotspot identification

Usage:
    # 1. Install py-spy
    pip install py-spy  # Or: poetry add --group dev py-spy

    # 2. Run memory profiling (requires elevated permissions on Windows)
    python tests/performance/memory_profile.py

    # 3. View results
    # - SVG flame graph: docs/performance/memory_profile_sprint_28.svg
    # - JSON report: docs/performance/memory_report_sprint_28.json

    # Alternative: Manual py-spy profiling
    # Start the API server
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000

    # In another terminal, get the process ID
    # Windows: tasklist | findstr python
    # Linux: ps aux | grep uvicorn

    # Run py-spy
    py-spy record -o profile.svg --pid <PID> --duration 60

Dependencies:
    - py-spy: pip install py-spy
    - psutil: pip install psutil (for memory stats)
    - locust: For generating load during profiling
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None
    print("WARNING: psutil not installed. Memory stats will be limited.")
    print("Install: pip install psutil")


class MemoryProfiler:
    """Memory profiling orchestrator for AegisRAG API.

    This class manages the entire memory profiling workflow:
    1. Start API server
    2. Generate load with Locust
    3. Collect memory snapshots
    4. Analyze results
    5. Generate reports
    """

    def __init__(
        self,
        output_dir: Path = Path("docs/performance"),
        profile_duration: int = 60,
        load_qps: int = 50,
    ):
        """Initialize memory profiler.

        Args:
            output_dir: Directory for output files
            profile_duration: Duration of profiling in seconds
            load_qps: Target QPS during profiling
        """
        self.output_dir = output_dir
        self.profile_duration = profile_duration
        self.load_qps = load_qps
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_profiling(self) -> dict[str, Any]:
        """Run complete memory profiling workflow.

        Returns:
            Dictionary with profiling results and metadata
        """
        print("=" * 80)
        print("AegisRAG Memory Profiling - Sprint 28")
        print("=" * 80)

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "duration_seconds": self.profile_duration,
            "target_qps": self.load_qps,
            "profiling_method": "py-spy + psutil",
        }

        # Step 1: Check if API server is running
        api_running = await self._check_api_running()
        if not api_running:
            print("\nWARNING: API server not running on http://localhost:8000")
            print("Please start the server first:")
            print("  uvicorn src.api.main:app --host 0.0.0.0 --port 8000\n")
            results["error"] = "API server not running"
            return results

        # Step 2: Get API server process ID
        pid = await self._get_api_pid()
        if not pid:
            print("ERROR: Could not find API server process")
            results["error"] = "Could not find API process"
            return results

        print(f"\nFound API server process: PID {pid}")
        results["api_pid"] = pid

        # Step 3: Collect baseline memory stats
        print("\nCollecting baseline memory stats...")
        baseline_memory = await self._get_memory_stats(pid)
        results["baseline_memory"] = baseline_memory
        print(f"  Baseline RSS: {baseline_memory.get('rss_mb', 'N/A')} MB")
        print(f"  Baseline VMS: {baseline_memory.get('vms_mb', 'N/A')} MB")

        # Step 4: Start load generation
        print(f"\nStarting load generation ({self.load_qps} QPS)...")
        load_process = await self._start_load_generation()

        # Wait for load to stabilize
        await asyncio.sleep(5)

        # Step 5: Run py-spy profiling
        print(f"\nRunning py-spy profiling for {self.profile_duration} seconds...")
        print("(This may require elevated permissions)\n")

        profile_success = await self._run_pyspy_profiling(pid)
        results["pyspy_success"] = profile_success

        # Step 6: Collect memory snapshots during load
        print("\nCollecting memory snapshots during load...")
        snapshots = await self._collect_memory_snapshots(pid, duration=30)
        results["memory_snapshots"] = snapshots

        # Step 7: Stop load generation
        print("\nStopping load generation...")
        if load_process:
            load_process.terminate()
            try:
                load_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                load_process.kill()

        # Wait for memory to stabilize
        await asyncio.sleep(5)

        # Step 8: Collect final memory stats
        print("\nCollecting final memory stats...")
        final_memory = await self._get_memory_stats(pid)
        results["final_memory"] = final_memory
        print(f"  Final RSS: {final_memory.get('rss_mb', 'N/A')} MB")
        print(f"  Final VMS: {final_memory.get('vms_mb', 'N/A')} MB")

        # Step 9: Analyze results
        print("\nAnalyzing results...")
        analysis = self._analyze_memory_profile(baseline_memory, final_memory, snapshots)
        results["analysis"] = analysis

        # Step 10: Save results
        report_path = self.output_dir / "memory_report_sprint_28.json"
        with report_path.open("w") as f:
            json.dump(results, f, indent=2)

        print(f"\nMemory profiling complete!")
        print(f"  Report saved to: {report_path}")
        print(f"  Flame graph: {self.output_dir / 'memory_profile_sprint_28.svg'}")

        return results

    async def _check_api_running(self) -> bool:
        """Check if API server is running."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=2.0)
                return response.status_code == 200
        except Exception:
            return False

    async def _get_api_pid(self) -> int | None:
        """Get API server process ID."""
        if not psutil:
            return None

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if cmdline and any("uvicorn" in arg for arg in cmdline):
                    if any("src.api.main:app" in arg for arg in cmdline):
                        return proc.info["pid"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return None

    async def _get_memory_stats(self, pid: int) -> dict[str, Any]:
        """Get memory statistics for a process."""
        if not psutil:
            return {"error": "psutil not available"}

        try:
            process = psutil.Process(pid)
            mem_info = process.memory_info()
            mem_percent = process.memory_percent()

            return {
                "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
                "vms_mb": round(mem_info.vms / 1024 / 1024, 2),
                "percent": round(mem_percent, 2),
                "num_threads": process.num_threads(),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _start_load_generation(self) -> subprocess.Popen | None:
        """Start Locust load generation in background."""
        try:
            # Use locust headless mode
            cmd = [
                sys.executable,
                "-m",
                "locust",
                "-f",
                "tests/performance/locustfile.py",
                "--host",
                "http://localhost:8000",
                "--users",
                str(self.load_qps),
                "--spawn-rate",
                "10",
                "--headless",
                "--run-time",
                f"{self.profile_duration + 10}s",
            ]

            process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return process
        except Exception as e:
            print(f"WARNING: Could not start load generation: {e}")
            return None

    async def _run_pyspy_profiling(self, pid: int) -> bool:
        """Run py-spy profiling."""
        try:
            output_file = self.output_dir / "memory_profile_sprint_28.svg"

            cmd = [
                "py-spy",
                "record",
                "-o",
                str(output_file),
                "--pid",
                str(pid),
                "--duration",
                str(self.profile_duration),
                "--rate",
                "100",  # Sample rate (Hz)
                "--nonblocking",  # Non-blocking mode
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.profile_duration + 10)

            if result.returncode == 0:
                print(f"  SUCCESS: Flame graph saved to {output_file}")
                return True
            else:
                print(f"  ERROR: py-spy failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("  ERROR: py-spy not found. Install: pip install py-spy")
            return False
        except subprocess.TimeoutExpired:
            print("  ERROR: py-spy timed out")
            return False
        except Exception as e:
            print(f"  ERROR: {e}")
            return False

    async def _collect_memory_snapshots(
        self, pid: int, duration: int = 30, interval: int = 2
    ) -> list[dict[str, Any]]:
        """Collect memory snapshots over time."""
        snapshots = []
        start_time = time.time()

        while time.time() - start_time < duration:
            snapshot = await self._get_memory_stats(pid)
            snapshot["timestamp"] = time.time() - start_time
            snapshots.append(snapshot)
            await asyncio.sleep(interval)

        return snapshots

    def _analyze_memory_profile(
        self,
        baseline: dict[str, Any],
        final: dict[str, Any],
        snapshots: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze memory profiling results."""
        analysis = {}

        # Memory growth
        if "rss_mb" in baseline and "rss_mb" in final:
            growth_mb = final["rss_mb"] - baseline["rss_mb"]
            growth_percent = (growth_mb / baseline["rss_mb"]) * 100 if baseline["rss_mb"] > 0 else 0

            analysis["memory_growth"] = {
                "absolute_mb": round(growth_mb, 2),
                "percent": round(growth_percent, 2),
                "baseline_mb": baseline["rss_mb"],
                "final_mb": final["rss_mb"],
            }

            # Memory leak detection
            if growth_percent > 10:
                analysis["memory_leak_suspected"] = True
                analysis["leak_severity"] = (
                    "HIGH" if growth_percent > 50 else "MEDIUM" if growth_percent > 20 else "LOW"
                )
            else:
                analysis["memory_leak_suspected"] = False

        # Peak memory usage
        if snapshots:
            rss_values = [s.get("rss_mb", 0) for s in snapshots if "rss_mb" in s]
            if rss_values:
                analysis["peak_memory_mb"] = max(rss_values)
                analysis["avg_memory_mb"] = round(sum(rss_values) / len(rss_values), 2)
                analysis["memory_volatility"] = round(max(rss_values) - min(rss_values), 2)

        return analysis


async def main() -> None:
    """Main entry point for memory profiling."""
    profiler = MemoryProfiler(
        output_dir=Path("docs/performance"),
        profile_duration=60,
        load_qps=50,
    )

    results = await profiler.run_profiling()

    # Print summary
    print("\n" + "=" * 80)
    print("MEMORY PROFILING SUMMARY")
    print("=" * 80)

    if "error" in results:
        print(f"\nERROR: {results['error']}")
        return

    analysis = results.get("analysis", {})

    print("\nMemory Growth:")
    if "memory_growth" in analysis:
        growth = analysis["memory_growth"]
        print(f"  Baseline: {growth['baseline_mb']} MB")
        print(f"  Final:    {growth['final_mb']} MB")
        print(f"  Growth:   {growth['absolute_mb']} MB ({growth['percent']}%)")

    if analysis.get("memory_leak_suspected"):
        print(f"\n  WARNING: Potential memory leak detected!")
        print(f"  Severity: {analysis.get('leak_severity', 'UNKNOWN')}")

    if "peak_memory_mb" in analysis:
        print(f"\nMemory Statistics:")
        print(f"  Peak:       {analysis['peak_memory_mb']} MB")
        print(f"  Average:    {analysis['avg_memory_mb']} MB")
        print(f"  Volatility: {analysis['memory_volatility']} MB")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
