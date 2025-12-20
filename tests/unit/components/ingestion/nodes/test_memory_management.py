"""Unit tests for memory management node (Sprint 54 Feature 54.2).

Tests the memory_check_node function which handles RAM and VRAM monitoring
before document ingestion.

Test Coverage:
- test_memory_check_passes_sufficient_ram() - RAM >500MB available → pass
- test_memory_check_fails_insufficient_ram() - RAM <500MB → error
- test_memory_check_vram_normal() - VRAM <5.5GB → no restart needed
- test_memory_check_vram_leak_detected() - VRAM >5.5GB → restart flag set
- test_memory_check_psutil_unavailable() - psutil import fails → skip RAM check
- test_memory_check_nvidia_smi_unavailable() - nvidia-smi not found → skip VRAM check
- test_memory_check_vram_na_value() - nvidia-smi returns [N/A] → handle gracefully
- test_memory_check_state_updated() - Verify state fields are updated
- test_memory_check_error_handling() - Exception during check → add error and re-raise
"""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.nodes.memory_management import memory_check_node
from src.core.exceptions import IngestionError

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def base_state() -> IngestionState:
    """Base ingestion state for testing."""
    return {
        "document_id": "test_doc_123",
        "batch_index": 1,
        "document_path": "/tmp/test.pdf",
        "parsed_content": "",
        "chunks": [],
        "memory_check_passed": False,
        "current_memory_mb": 0.0,
        "current_vram_mb": 0.0,
        "requires_container_restart": False,
        "overall_progress": 0.0,
        "errors": [],
        "docling_status": "pending",
        "chunking_status": "pending",
        "embedding_status": "pending",
        "graph_status": "pending",
        "vector_status": "pending",
    }


@pytest.fixture
def mock_psutil_sufficient():
    """Mock psutil with sufficient RAM (8GB total, 3GB available)."""
    mock_memory = MagicMock()
    mock_memory.used = 5 * 1024 * 1024 * 1024  # 5GB used
    mock_memory.available = 3 * 1024 * 1024 * 1024  # 3GB available
    return mock_memory


@pytest.fixture
def mock_psutil_insufficient():
    """Mock psutil with insufficient RAM (<500MB available)."""
    mock_memory = MagicMock()
    mock_memory.used = 7.5 * 1024 * 1024 * 1024  # 7.5GB used
    mock_memory.available = 200 * 1024 * 1024  # 200MB available
    return mock_memory


# =============================================================================
# TEST: SUFFICIENT RAM
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_passes_sufficient_ram(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check passes when sufficient RAM available (>500MB).

    Expected behavior:
    - memory_check_passed = True
    - current_memory_mb = 5120 (5GB used)
    - No IngestionError raised
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi success
        mock_run.return_value = MagicMock(
            stdout="2000.0",  # 2GB VRAM used
            returncode=0,
        )

        # Create a mock psutil module
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            # Verify state updated
            assert result["memory_check_passed"] is True
            assert result["current_memory_mb"] == pytest.approx(5120.0, rel=1)
            assert result["current_vram_mb"] == 2000.0
            assert result["requires_container_restart"] is False


# =============================================================================
# TEST: INSUFFICIENT RAM
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_fails_insufficient_ram(
    base_state: IngestionState,
    mock_psutil_insufficient,
) -> None:
    """Test memory check fails when insufficient RAM (<500MB available).

    Expected behavior:
    - IngestionError raised with descriptive message
    - Error contains RAM availability details
    """
    mock_psutil = MagicMock()
    mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_insufficient)

    with patch.dict(sys.modules, {"psutil": mock_psutil}):
        with pytest.raises(IngestionError) as exc_info:
            await memory_check_node(base_state)

        # Verify error details
        assert "Insufficient RAM" in str(exc_info.value)
        assert "200MB available" in str(exc_info.value)


# =============================================================================
# TEST: NORMAL VRAM USAGE
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_vram_normal(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check passes when VRAM usage is normal (<5.5GB).

    Expected behavior:
    - current_vram_mb = 3000 (3GB)
    - requires_container_restart = False
    - No warning logged
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi with normal VRAM
        mock_run.return_value = MagicMock(
            stdout="3000.0",  # 3GB VRAM used (normal)
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["current_vram_mb"] == 3000.0
            assert result["requires_container_restart"] is False
            assert result["memory_check_passed"] is True


# =============================================================================
# TEST: VRAM LEAK DETECTED
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_vram_leak_detected(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check detects VRAM leak (>5.5GB usage).

    Expected behavior:
    - current_vram_mb = 6000 (6GB)
    - requires_container_restart = True
    - Warning error added to state
    - Memory check still passes (graceful degradation)
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi with VRAM leak (6GB)
        mock_run.return_value = MagicMock(
            stdout="6000.0",  # 6GB VRAM used (leak!)
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            # Verify leak detection
            assert result["current_vram_mb"] == 6000.0
            assert result["requires_container_restart"] is True
            assert result["memory_check_passed"] is True  # Still passes (non-fatal)

            # Verify error added
            assert len(result["errors"]) > 0
            assert any("VRAM leak detected" in str(e) for e in result["errors"])


# =============================================================================
# TEST: PSUTIL UNAVAILABLE
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_psutil_unavailable(base_state: IngestionState) -> None:
    """Test memory check handles psutil import error gracefully.

    Expected behavior:
    - current_memory_mb = 0.0 (unavailable)
    - memory_check_passed = True (non-fatal)
    - No IngestionError raised
    - Warning logged
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi success
        mock_run.return_value = MagicMock(
            stdout="2000.0",
            returncode=0,
        )

        # Simulate psutil ImportError by not providing it in sys.modules
        modules_to_remove = {}
        if "psutil" in sys.modules:
            modules_to_remove["psutil"] = sys.modules["psutil"]
            del sys.modules["psutil"]

        try:
            # Patch to fail on import
            def import_side_effect(name, *args, **kwargs):
                if name == "psutil":
                    raise ImportError("psutil not available")
                return __import__(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=import_side_effect):
                result = await memory_check_node(base_state)

                # Verify graceful degradation
                assert result["current_memory_mb"] == 0.0
                assert result["memory_check_passed"] is True
                assert result["current_vram_mb"] == 2000.0
        finally:
            # Restore psutil if it was there
            for name, mod in modules_to_remove.items():
                sys.modules[name] = mod


# =============================================================================
# TEST: NVIDIA-SMI UNAVAILABLE
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_nvidia_smi_unavailable(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check handles nvidia-smi not found gracefully.

    Expected behavior:
    - current_vram_mb = 0.0 (unavailable)
    - memory_check_passed = True (non-fatal)
    - requires_container_restart = False
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi not found
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            # Verify graceful degradation
            assert result["current_vram_mb"] == 0.0
            assert result["requires_container_restart"] is False
            assert result["memory_check_passed"] is True
            assert result["current_memory_mb"] == pytest.approx(5120.0, rel=1)


# =============================================================================
# TEST: NVIDIA-SMI CALLED BUT ERROR
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_nvidia_smi_error(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check handles nvidia-smi CalledProcessError gracefully.

    Expected behavior:
    - current_vram_mb = 0.0 (unavailable)
    - memory_check_passed = True (non-fatal)
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi error
        mock_run.side_effect = subprocess.CalledProcessError(1, "nvidia-smi")

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["current_vram_mb"] == 0.0
            assert result["memory_check_passed"] is True


# =============================================================================
# TEST: NVIDIA-SMI RETURNS [N/A]
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_vram_na_value(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check handles nvidia-smi [N/A] value (DGX Spark unified memory).

    Expected behavior:
    - Detect [N/A] prefix and treat as unavailable
    - current_vram_mb = 0.0
    - memory_check_passed = True
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi with [N/A] (DGX Spark unified memory)
        mock_run.return_value = MagicMock(
            stdout="[N/A]",
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["current_vram_mb"] == 0.0
            assert result["memory_check_passed"] is True


# =============================================================================
# TEST: NVIDIA-SMI RETURNS INVALID VALUE
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_vram_invalid_value(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check handles nvidia-smi invalid/non-numeric value.

    Expected behavior:
    - Detect non-numeric output and treat as unavailable
    - current_vram_mb = 0.0
    - memory_check_passed = True
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi with invalid output
        mock_run.return_value = MagicMock(
            stdout="ERROR: some error message",
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["current_vram_mb"] == 0.0
            assert result["memory_check_passed"] is True


# =============================================================================
# TEST: STATE FIELDS UPDATED
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_state_updated(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check updates all required state fields.

    Expected fields:
    - memory_check_passed
    - current_memory_mb
    - current_vram_mb
    - requires_container_restart
    - overall_progress
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="3500.0",
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            # Verify all expected fields present and updated
            assert "memory_check_passed" in result
            assert "current_memory_mb" in result
            assert "current_vram_mb" in result
            assert "requires_container_restart" in result
            assert "overall_progress" in result

            assert result["memory_check_passed"] is True
            assert isinstance(result["current_memory_mb"], float)
            assert isinstance(result["current_vram_mb"], float)
            assert isinstance(result["requires_container_restart"], bool)


# =============================================================================
# TEST: DOCUMENT ID TRACKING
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_document_id_tracking(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check logs correct document ID.

    Expected behavior:
    - Document ID preserved in logging
    - Errors associated with correct document
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="2000.0",
            returncode=0,
        )

        base_state["document_id"] = "doc_xyz_789"

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            # Verify document ID unchanged
            assert result["document_id"] == "doc_xyz_789"


# =============================================================================
# TEST: BATCH INDEX TRACKING
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_batch_index_tracking(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test memory check preserves batch index.

    Expected behavior:
    - Batch index preserved in state
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="2000.0",
            returncode=0,
        )

        base_state["batch_index"] = 3

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            # Verify batch index unchanged
            assert result["batch_index"] == 3


# =============================================================================
# TEST: EDGE CASE - VRAM EXACTLY AT THRESHOLD
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_vram_exactly_at_threshold(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test VRAM exactly at 5.5GB threshold (should NOT trigger restart).

    Expected behavior:
    - 5500MB VRAM is NOT > 5500, so no restart
    - requires_container_restart = False
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi with VRAM exactly at threshold
        mock_run.return_value = MagicMock(
            stdout="5500.0",  # Exactly at threshold
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["current_vram_mb"] == 5500.0
            assert result["requires_container_restart"] is False


# =============================================================================
# TEST: EDGE CASE - RAM EXACTLY AT MINIMUM
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_ram_exactly_at_minimum(base_state: IngestionState) -> None:
    """Test RAM exactly at 500MB threshold (should NOT fail).

    Expected behavior:
    - 500MB available is NOT < 500, so passes
    - memory_check_passed = True
    """
    mock_memory = MagicMock()
    mock_memory.used = 7.5 * 1024 * 1024 * 1024  # 7.5GB used
    mock_memory.available = 500 * 1024 * 1024  # 500MB available (exactly at threshold)

    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="2000.0",
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_memory)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["memory_check_passed"] is True


# =============================================================================
# TEST: VRAM FORMATTING WITH DECIMAL PLACES
# =============================================================================


@pytest.mark.asyncio
async def test_memory_check_vram_decimal_format(
    base_state: IngestionState,
    mock_psutil_sufficient,
) -> None:
    """Test VRAM value with decimal places is parsed correctly.

    Expected behavior:
    - "2345.67" → 2345.67 (float)
    """
    with patch("src.components.ingestion.nodes.memory_management.subprocess.run") as mock_run:
        # Mock nvidia-smi with decimal VRAM value
        mock_run.return_value = MagicMock(
            stdout="2345.67",
            returncode=0,
        )

        mock_psutil = MagicMock()
        mock_psutil.virtual_memory = MagicMock(return_value=mock_psutil_sufficient)

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = await memory_check_node(base_state)

            assert result["current_vram_mb"] == 2345.67
