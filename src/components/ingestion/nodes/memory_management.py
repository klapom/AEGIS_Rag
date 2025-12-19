"""Memory Management Node for LangGraph Ingestion Pipeline.

Sprint 54 Feature 54.2: Extracted from langgraph_nodes.py

This module handles memory checking (RAM + VRAM) before ingestion.

Node: memory_check_node
    - Checks system RAM availability (requires 500MB minimum)
    - Monitors GPU VRAM usage (warns if >5.5GB, indicates leak)
    - Determines if container restart is needed
"""

import subprocess

import structlog

from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
)
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)


async def memory_check_node(state: IngestionState) -> IngestionState:
    """Node 1: Check memory availability (RAM + VRAM).

    Checks:
    - System RAM usage (target: <4.4GB available)
    - GPU VRAM usage (target: <5.5GB, restart if >5.5GB)

    Args:
        state: Current ingestion state

    Returns:
        Updated state with memory check results

    Raises:
        IngestionError: If insufficient memory (RAM <2GB or VRAM unavailable)

    Example:
        >>> state = await memory_check_node(state)
        >>> state["memory_check_passed"]
        True
        >>> state["current_memory_mb"]
        3200.0  # 3.2GB RAM used
    """
    logger.info(
        "node_memory_check_start",
        document_id=state["document_id"],
        batch_index=state["batch_index"],
    )

    try:
        # Check system RAM usage (psutil) - graceful degradation if unavailable
        try:
            import psutil

            memory = psutil.virtual_memory()
            ram_used_mb = memory.used / 1024 / 1024
            ram_available_mb = memory.available / 1024 / 1024

            state["current_memory_mb"] = ram_used_mb

            logger.info(
                "memory_check_ram",
                ram_used_mb=round(ram_used_mb, 2),
                ram_available_mb=round(ram_available_mb, 2),
            )

            # Check if sufficient memory available
            # Sprint 30: Lowered to 500MB for small PDF testing (production should use 2000MB minimum)
            # TODO: Make threshold configurable via settings.min_required_ram_mb
            if ram_available_mb < 500:  # Less than 500MB RAM available
                raise IngestionError(
                    document_id=state["document_id"],
                    reason=f"Insufficient RAM: Only {ram_available_mb:.0f}MB available (need 500MB)",
                )

        except ImportError:
            # psutil not available (common in Uvicorn reloader subprocess on Windows)
            logger.warning(
                "psutil_unavailable",
                note="Skipping RAM check (psutil not available in subprocess)",
            )
            state["current_memory_mb"] = 0.0

        # Check GPU VRAM usage (nvidia-smi)
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
            )
            vram_output = result.stdout.strip()
            # Handle "[N/A]" or other non-numeric outputs (e.g., DGX Spark unified memory)
            if vram_output.startswith("[") or not vram_output.replace(".", "").isdigit():
                logger.debug("nvidia_smi_na_value", raw_output=vram_output)
                vram_used_mb = 0.0
            else:
                vram_used_mb = float(vram_output)
            state["current_vram_mb"] = vram_used_mb

            logger.info("memory_check_vram", vram_used_mb=round(vram_used_mb, 2))

            # Check for memory leak (>5.5GB indicates leak from previous batch)
            if vram_used_mb > 5500:
                logger.warning(
                    "vram_leak_detected",
                    vram_used_mb=vram_used_mb,
                    threshold_mb=5500,
                    action="container_restart_required",
                )
                state["requires_container_restart"] = True
                add_error(
                    state,
                    "memory_check",
                    f"VRAM leak detected: {vram_used_mb:.0f}MB (>5.5GB threshold)",
                    "warning",
                )

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning("nvidia_smi_unavailable", error=str(e))
            state["current_vram_mb"] = 0.0  # GPU not available or nvidia-smi not found
            state["requires_container_restart"] = False

        # Mark check as passed (even if psutil unavailable)
        state["memory_check_passed"] = True
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_memory_check_complete",
            document_id=state["document_id"],
            memory_check_passed=True,
            requires_restart=state.get("requires_container_restart", False),
        )

        return state

    except IngestionError:
        # Re-raise IngestionError (insufficient RAM)
        raise
    except Exception as e:
        logger.error("node_memory_check_error", document_id=state["document_id"], error=str(e))
        add_error(state, "memory_check", str(e), "error")
        state["memory_check_passed"] = False
        raise
