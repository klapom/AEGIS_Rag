"""Memory Profiling and Monitoring Utilities - Sprint 68 Feature 68.3.

Provides utilities for tracking memory usage across the RAG pipeline:
- System RAM monitoring (psutil)
- GPU VRAM monitoring (nvidia-smi)
- Redis cache monitoring
- Graphiti memory size tracking
- Process-level memory profiling
"""

import asyncio
import gc
import subprocess
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MemorySnapshot:
    """Snapshot of system memory usage at a point in time."""

    timestamp: float
    ram_used_mb: float
    ram_available_mb: float
    ram_percent: float
    vram_used_mb: float
    vram_available_mb: float
    vram_percent: float
    process_rss_mb: float
    process_vms_mb: float


class MemoryProfiler:
    """Memory profiler for tracking resource usage during operations.

    Sprint 68 Feature 68.3: Monitor memory usage to prevent OOM errors.

    Usage:
        >>> profiler = MemoryProfiler()
        >>> async with profiler.profile("pdf_ingestion"):
        ...     await ingest_large_pdf(path)
        ...
        >>> stats = profiler.get_stats("pdf_ingestion")
        >>> print(f"Peak RAM: {stats['peak_ram_mb']:.2f} MB")
    """

    def __init__(self) -> None:
        """Initialize memory profiler."""
        self.snapshots: dict[str, list[MemorySnapshot]] = {}
        self._enabled = True

        # Check if psutil available
        try:
            import psutil

            self._psutil = psutil
        except ImportError:
            logger.warning("psutil_unavailable", note="Memory profiling disabled")
            self._psutil = None
            self._enabled = False

    def _get_system_memory(self) -> tuple[float, float, float]:
        """Get system RAM usage.

        Returns:
            Tuple of (used_mb, available_mb, percent)
        """
        if not self._psutil:
            return (0.0, 0.0, 0.0)

        try:
            mem = self._psutil.virtual_memory()
            return (
                mem.used / 1024 / 1024,
                mem.available / 1024 / 1024,
                mem.percent,
            )
        except Exception as e:
            logger.warning("system_memory_read_failed", error=str(e))
            return (0.0, 0.0, 0.0)

    def _get_gpu_memory(self) -> tuple[float, float, float]:
        """Get GPU VRAM usage via nvidia-smi.

        Returns:
            Tuple of (used_mb, available_mb, percent)
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            # Parse output: "used,total" (in MB)
            output = result.stdout.strip()
            if not output or output.startswith("["):
                # No GPU or N/A
                return (0.0, 0.0, 0.0)

            parts = output.split(",")
            if len(parts) != 2:
                return (0.0, 0.0, 0.0)

            used_mb = float(parts[0])
            total_mb = float(parts[1])
            available_mb = total_mb - used_mb
            percent = (used_mb / total_mb * 100) if total_mb > 0 else 0.0

            return (used_mb, available_mb, percent)

        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            ValueError,
            subprocess.TimeoutExpired,
        ) as e:
            logger.debug("gpu_memory_read_failed", error=str(e))
            return (0.0, 0.0, 0.0)

    def _get_process_memory(self) -> tuple[float, float]:
        """Get current process memory usage.

        Returns:
            Tuple of (rss_mb, vms_mb)
        """
        if not self._psutil:
            return (0.0, 0.0)

        try:
            process = self._psutil.Process()
            mem_info = process.memory_info()
            return (
                mem_info.rss / 1024 / 1024,  # Resident Set Size
                mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            )
        except Exception as e:
            logger.warning("process_memory_read_failed", error=str(e))
            return (0.0, 0.0)

    def take_snapshot(self) -> MemorySnapshot:
        """Take a snapshot of current memory usage.

        Returns:
            MemorySnapshot with current system state
        """
        if not self._enabled:
            # Return empty snapshot if profiling disabled
            import time

            return MemorySnapshot(
                timestamp=time.time(),
                ram_used_mb=0.0,
                ram_available_mb=0.0,
                ram_percent=0.0,
                vram_used_mb=0.0,
                vram_available_mb=0.0,
                vram_percent=0.0,
                process_rss_mb=0.0,
                process_vms_mb=0.0,
            )

        import time

        ram_used, ram_available, ram_percent = self._get_system_memory()
        vram_used, vram_available, vram_percent = self._get_gpu_memory()
        process_rss, process_vms = self._get_process_memory()

        return MemorySnapshot(
            timestamp=time.time(),
            ram_used_mb=ram_used,
            ram_available_mb=ram_available,
            ram_percent=ram_percent,
            vram_used_mb=vram_used,
            vram_available_mb=vram_available,
            vram_percent=vram_percent,
            process_rss_mb=process_rss,
            process_vms_mb=process_vms,
        )

    @asynccontextmanager
    async def profile(self, operation_name: str, sample_interval_seconds: float = 1.0):
        """Profile memory usage for an async operation.

        Args:
            operation_name: Name of operation to profile
            sample_interval_seconds: How often to sample memory (default: 1s)

        Yields:
            None

        Example:
            >>> async with profiler.profile("large_pdf_ingestion"):
            ...     await process_large_pdf()
            ...
            >>> stats = profiler.get_stats("large_pdf_ingestion")
        """
        if operation_name not in self.snapshots:
            self.snapshots[operation_name] = []

        # Take initial snapshot
        initial = self.take_snapshot()
        self.snapshots[operation_name].append(initial)

        logger.info(
            "memory_profiling_start",
            operation=operation_name,
            initial_ram_mb=round(initial.ram_used_mb, 2),
            initial_vram_mb=round(initial.vram_used_mb, 2),
            initial_process_mb=round(initial.process_rss_mb, 2),
        )

        # Background sampling task
        sampling = True

        async def sample_memory():
            """Background task to sample memory at intervals."""
            while sampling:
                await asyncio.sleep(sample_interval_seconds)
                if sampling:  # Check again after sleep
                    snapshot = self.take_snapshot()
                    self.snapshots[operation_name].append(snapshot)

        sampling_task = asyncio.create_task(sample_memory())

        try:
            yield

        finally:
            # Stop sampling
            sampling = False
            sampling_task.cancel()

            # Wait for task to finish
            from contextlib import suppress

            with suppress(asyncio.CancelledError):
                await sampling_task

            # Take final snapshot
            final = self.take_snapshot()
            self.snapshots[operation_name].append(final)

            # Calculate stats
            ram_delta = final.ram_used_mb - initial.ram_used_mb
            vram_delta = final.vram_used_mb - initial.vram_used_mb
            process_delta = final.process_rss_mb - initial.process_rss_mb

            logger.info(
                "memory_profiling_complete",
                operation=operation_name,
                final_ram_mb=round(final.ram_used_mb, 2),
                final_vram_mb=round(final.vram_used_mb, 2),
                final_process_mb=round(final.process_rss_mb, 2),
                ram_delta_mb=round(ram_delta, 2),
                vram_delta_mb=round(vram_delta, 2),
                process_delta_mb=round(process_delta, 2),
                samples_taken=len(self.snapshots[operation_name]),
            )

    def get_stats(self, operation_name: str) -> dict[str, Any]:
        """Get memory statistics for a profiled operation.

        Args:
            operation_name: Name of profiled operation

        Returns:
            Dictionary with memory statistics:
            - peak_ram_mb: Peak RAM usage
            - peak_vram_mb: Peak VRAM usage
            - peak_process_mb: Peak process RSS
            - avg_ram_mb: Average RAM usage
            - delta_ram_mb: RAM change (final - initial)
            - samples: Number of samples taken
        """
        if operation_name not in self.snapshots:
            logger.warning("operation_not_profiled", operation=operation_name)
            return {}

        snapshots = self.snapshots[operation_name]
        if not snapshots:
            return {}

        # Calculate statistics
        ram_values = [s.ram_used_mb for s in snapshots]
        vram_values = [s.vram_used_mb for s in snapshots]
        process_values = [s.process_rss_mb for s in snapshots]

        return {
            "operation": operation_name,
            "peak_ram_mb": round(max(ram_values), 2),
            "peak_vram_mb": round(max(vram_values), 2),
            "peak_process_mb": round(max(process_values), 2),
            "avg_ram_mb": round(sum(ram_values) / len(ram_values), 2),
            "avg_vram_mb": round(sum(vram_values) / len(vram_values), 2),
            "avg_process_mb": round(sum(process_values) / len(process_values), 2),
            "delta_ram_mb": round(ram_values[-1] - ram_values[0], 2),
            "delta_vram_mb": round(vram_values[-1] - vram_values[0], 2),
            "delta_process_mb": round(process_values[-1] - process_values[0], 2),
            "samples": len(snapshots),
            "duration_seconds": round(snapshots[-1].timestamp - snapshots[0].timestamp, 2),
        }

    def clear(self, operation_name: str | None = None) -> None:
        """Clear profiling data.

        Args:
            operation_name: Name of operation to clear (default: clear all)
        """
        if operation_name:
            if operation_name in self.snapshots:
                del self.snapshots[operation_name]
                logger.debug("memory_profiling_cleared", operation=operation_name)
        else:
            self.snapshots.clear()
            logger.debug("memory_profiling_cleared_all")


def check_memory_available(min_ram_mb: float = 500, min_vram_mb: float = 1000) -> tuple[bool, str]:
    """Check if sufficient memory is available for an operation.

    Sprint 68 Feature 68.3: Pre-flight check to prevent OOM errors.

    Args:
        min_ram_mb: Minimum required RAM in MB (default: 500)
        min_vram_mb: Minimum required VRAM in MB (default: 1000)

    Returns:
        Tuple of (is_available, reason)
        - is_available: True if sufficient memory, False otherwise
        - reason: Human-readable reason if not available
    """
    profiler = MemoryProfiler()
    snapshot = profiler.take_snapshot()

    # Check RAM
    if snapshot.ram_available_mb < min_ram_mb:
        return (
            False,
            f"Insufficient RAM: {snapshot.ram_available_mb:.0f}MB available, need {min_ram_mb:.0f}MB",
        )

    # Check VRAM (if GPU available)
    if snapshot.vram_available_mb > 0 and snapshot.vram_available_mb < min_vram_mb:
        return (
            False,
            f"Insufficient VRAM: {snapshot.vram_available_mb:.0f}MB available, need {min_vram_mb:.0f}MB",
        )

    return (True, "")


def force_garbage_collection() -> dict[str, int]:
    """Force garbage collection and return statistics.

    Sprint 68 Feature 68.3: Explicit memory cleanup utility.

    Returns:
        Dictionary with collection statistics:
        - collected: Number of objects collected
        - generation: GC generation that triggered collection
    """
    logger.debug("force_gc_start")

    # Collect all generations
    collected = gc.collect()

    stats = {
        "collected": collected,
        "generation": 2,  # Full collection
    }

    logger.debug("force_gc_complete", **stats)

    return stats


# Global singleton
_memory_profiler: MemoryProfiler | None = None


def get_memory_profiler() -> MemoryProfiler:
    """Get global MemoryProfiler instance (singleton).

    Returns:
        MemoryProfiler instance
    """
    global _memory_profiler
    if _memory_profiler is None:
        _memory_profiler = MemoryProfiler()
    return _memory_profiler
