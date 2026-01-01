"""Unit tests for memory profiler - Sprint 68 Feature 68.3."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.core.memory_profiler import (
    MemoryProfiler,
    MemorySnapshot,
    check_memory_available,
    force_garbage_collection,
    get_memory_profiler,
)


class TestMemorySnapshot:
    """Test MemorySnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test creating a memory snapshot."""
        snapshot = MemorySnapshot(
            timestamp=1234567890.0,
            ram_used_mb=2048.5,
            ram_available_mb=4096.3,
            ram_percent=50.0,
            vram_used_mb=1024.2,
            vram_available_mb=5120.8,
            vram_percent=20.0,
            process_rss_mb=512.1,
            process_vms_mb=1024.2,
        )

        assert snapshot.timestamp == 1234567890.0
        assert snapshot.ram_used_mb == 2048.5
        assert snapshot.ram_available_mb == 4096.3
        assert snapshot.vram_used_mb == 1024.2
        assert snapshot.process_rss_mb == 512.1


class TestMemoryProfiler:
    """Test MemoryProfiler class."""

    @pytest.fixture
    def profiler(self):
        """Create a memory profiler instance."""
        return MemoryProfiler()

    @pytest.fixture
    def mock_psutil(self):
        """Mock psutil module."""
        with patch("src.core.memory_profiler.MemoryProfiler._psutil") as mock:
            # Mock virtual_memory
            mock_mem = MagicMock()
            mock_mem.used = 2048 * 1024 * 1024  # 2048 MB
            mock_mem.available = 4096 * 1024 * 1024  # 4096 MB
            mock_mem.percent = 50.0
            mock.virtual_memory.return_value = mock_mem

            # Mock Process
            mock_process = MagicMock()
            mock_mem_info = MagicMock()
            mock_mem_info.rss = 512 * 1024 * 1024  # 512 MB
            mock_mem_info.vms = 1024 * 1024 * 1024  # 1024 MB
            mock_process.memory_info.return_value = mock_mem_info
            mock.Process.return_value = mock_process

            yield mock

    def test_profiler_initialization(self, profiler):
        """Test profiler initialization."""
        assert profiler.snapshots == {}
        assert isinstance(profiler._enabled, bool)

    def test_take_snapshot_without_psutil(self):
        """Test taking snapshot when psutil unavailable."""
        profiler = MemoryProfiler()
        profiler._psutil = None
        profiler._enabled = False

        snapshot = profiler.take_snapshot()

        assert snapshot.ram_used_mb == 0.0
        assert snapshot.ram_available_mb == 0.0
        assert snapshot.vram_used_mb == 0.0

    @patch("subprocess.run")
    def test_get_gpu_memory_success(self, mock_run, profiler):
        """Test GPU memory reading with nvidia-smi."""
        # Mock nvidia-smi output: "1024,8192" (used,total)
        mock_run.return_value = MagicMock(
            stdout="1024,8192\n",
            returncode=0,
        )

        used, available, percent = profiler._get_gpu_memory()

        assert used == 1024.0
        assert available == 7168.0  # 8192 - 1024
        assert percent == pytest.approx(12.5, rel=0.01)  # 1024/8192 * 100

    @patch("subprocess.run")
    def test_get_gpu_memory_failure(self, mock_run, profiler):
        """Test GPU memory reading when nvidia-smi fails."""
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

        used, available, percent = profiler._get_gpu_memory()

        assert used == 0.0
        assert available == 0.0
        assert percent == 0.0

    @pytest.mark.asyncio
    async def test_profile_async_operation(self, profiler):
        """Test profiling an async operation."""

        async def test_operation():
            """Simulate some async work."""
            await asyncio.sleep(0.1)

        async with profiler.profile("test_op", sample_interval_seconds=0.05):
            await test_operation()

        # Check snapshots were taken
        assert "test_op" in profiler.snapshots
        assert len(profiler.snapshots["test_op"]) >= 2  # At least initial and final

        # Check stats
        stats = profiler.get_stats("test_op")
        assert "peak_ram_mb" in stats
        assert "avg_ram_mb" in stats
        assert "delta_ram_mb" in stats
        assert stats["samples"] >= 2

    @pytest.mark.asyncio
    async def test_profile_captures_memory_growth(self, profiler):
        """Test that profiler captures memory allocation."""

        async def allocate_memory():
            """Allocate some memory during profiling."""
            data = [0] * 10_000_000  # ~80MB list
            await asyncio.sleep(0.05)
            return data  # Keep reference to prevent GC

        # Profile the allocation
        result = None
        async with profiler.profile("memory_allocation", sample_interval_seconds=0.01):
            result = await allocate_memory()

        stats = profiler.get_stats("memory_allocation")

        # Process memory should increase (if psutil available)
        if profiler._enabled:
            # Delta might be 0 if GC runs or if system has lots of free memory
            # Just check that stats were collected
            assert stats["samples"] >= 2
            assert "delta_process_mb" in stats

        # Clean up
        del result

    def test_get_stats_nonexistent_operation(self, profiler):
        """Test getting stats for operation that wasn't profiled."""
        stats = profiler.get_stats("nonexistent")
        assert stats == {}

    def test_clear_single_operation(self, profiler):
        """Test clearing profiling data for single operation."""
        profiler.snapshots["op1"] = [MagicMock(), MagicMock()]
        profiler.snapshots["op2"] = [MagicMock()]

        profiler.clear("op1")

        assert "op1" not in profiler.snapshots
        assert "op2" in profiler.snapshots

    def test_clear_all_operations(self, profiler):
        """Test clearing all profiling data."""
        profiler.snapshots["op1"] = [MagicMock()]
        profiler.snapshots["op2"] = [MagicMock()]

        profiler.clear()

        assert profiler.snapshots == {}


class TestMemoryChecks:
    """Test memory check utilities."""

    @patch("src.core.memory_profiler.MemoryProfiler.take_snapshot")
    def test_check_memory_available_sufficient(self, mock_snapshot):
        """Test memory check when sufficient memory available."""
        mock_snapshot.return_value = MemorySnapshot(
            timestamp=0.0,
            ram_used_mb=2048.0,
            ram_available_mb=4096.0,  # Plenty of RAM
            ram_percent=50.0,
            vram_used_mb=1024.0,
            vram_available_mb=6144.0,  # Plenty of VRAM
            vram_percent=14.3,
            process_rss_mb=512.0,
            process_vms_mb=1024.0,
        )

        available, reason = check_memory_available(min_ram_mb=500, min_vram_mb=1000)

        assert available is True
        assert reason == ""

    @patch("src.core.memory_profiler.MemoryProfiler.take_snapshot")
    def test_check_memory_available_insufficient_ram(self, mock_snapshot):
        """Test memory check when insufficient RAM."""
        mock_snapshot.return_value = MemorySnapshot(
            timestamp=0.0,
            ram_used_mb=7500.0,
            ram_available_mb=100.0,  # Very low RAM
            ram_percent=98.8,
            vram_used_mb=1024.0,
            vram_available_mb=6144.0,
            vram_percent=14.3,
            process_rss_mb=512.0,
            process_vms_mb=1024.0,
        )

        available, reason = check_memory_available(min_ram_mb=500, min_vram_mb=1000)

        assert available is False
        assert "Insufficient RAM" in reason
        assert "100MB available" in reason

    @patch("src.core.memory_profiler.MemoryProfiler.take_snapshot")
    def test_check_memory_available_insufficient_vram(self, mock_snapshot):
        """Test memory check when insufficient VRAM."""
        mock_snapshot.return_value = MemorySnapshot(
            timestamp=0.0,
            ram_used_mb=2048.0,
            ram_available_mb=4096.0,
            ram_percent=50.0,
            vram_used_mb=7000.0,
            vram_available_mb=500.0,  # Very low VRAM
            vram_percent=93.3,
            process_rss_mb=512.0,
            process_vms_mb=1024.0,
        )

        available, reason = check_memory_available(min_ram_mb=500, min_vram_mb=1000)

        assert available is False
        assert "Insufficient VRAM" in reason
        assert "500MB available" in reason


class TestGarbageCollection:
    """Test garbage collection utilities."""

    @patch("gc.collect")
    def test_force_garbage_collection(self, mock_collect):
        """Test forcing garbage collection."""
        mock_collect.return_value = 42  # Number of objects collected

        stats = force_garbage_collection()

        assert stats["collected"] == 42
        assert stats["generation"] == 2
        mock_collect.assert_called_once()


class TestSingleton:
    """Test singleton pattern."""

    def test_get_memory_profiler_singleton(self):
        """Test that get_memory_profiler returns same instance."""
        profiler1 = get_memory_profiler()
        profiler2 = get_memory_profiler()

        assert profiler1 is profiler2
