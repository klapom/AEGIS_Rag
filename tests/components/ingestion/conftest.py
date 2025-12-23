"""Pytest fixtures for ingestion component tests (Sprint 33)."""

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
async def job_tracker(tmp_path: Path):
    """Create job tracker with temporary SQLite database.

    Uses tmp_path for isolated test database without interfering with production data.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        IngestionJobTracker instance
    """
    from src.components.ingestion.job_tracker import IngestionJobTracker

    db_path = tmp_path / "test_jobs.db"
    tracker = IngestionJobTracker(db_path=db_path, retention_days=90)

    yield tracker

    # Database cleanup handled automatically by tmp_path


@pytest.fixture
async def sample_job_config() -> dict[str, Any]:
    """Sample job configuration for testing.

    Returns:
        Job config dict with standard settings
    """
    return {
        "vlm_enabled": True,
        "max_workers": 3,
        "chunk_size": 1024,
        "embedding_model": "nomic-embed-text",
    }


@pytest.fixture
async def sample_job(job_tracker, sample_job_config):
    """Create sample job for testing.

    Args:
        job_tracker: Job tracker instance
        sample_job_config: Sample configuration

    Returns:
        Job ID string
    """
    job_id = await job_tracker.create_job(
        directory_path="/test/documents",
        recursive=True,
        total_files=5,
        config=sample_job_config,
    )
    return job_id


@pytest.fixture
async def sample_file(job_tracker, sample_job):
    """Add sample file to job tracking.

    Args:
        job_tracker: Job tracker instance
        sample_job: Sample job ID

    Returns:
        File record ID
    """
    file_id = await job_tracker.add_file(
        job_id=sample_job,
        file_path="/test/documents/report.pdf",
        file_name="report.pdf",
        file_type=".pdf",
        file_size_bytes=2457600,
        parser_used="docling",
    )
    return file_id


@pytest.fixture
def mock_langgraph_pipeline():
    """Mock LangGraph pipeline for orchestrator testing.

    Returns:
        Async mock function simulating document processing
    """

    async def process_mock(document_path: str, document_id: str) -> dict[str, Any]:
        """Mock document processing function.

        Args:
            document_path: Path to document
            document_id: Document identifier

        Returns:
            Processing result dict
        """
        return {
            "success": True,
            "file_path": document_path,
            "state": {
                "chunks": [{"id": f"chunk_{i}", "text": f"Chunk {i}"} for i in range(5)],
                "entities": [{"id": f"entity_{i}", "name": f"Entity {i}"} for i in range(3)],
                "relations": [{"source": "entity_0", "target": "entity_1"}],
                "vlm_metadata": [{"image_id": f"img_{i}"} for i in range(2)],
            },
            "error": None,
        }

    return process_mock


@pytest.fixture
async def parallel_orchestrator():
    """Create parallel orchestrator instance for testing.

    Returns:
        ParallelIngestionOrchestrator instance
    """
    from src.components.ingestion.parallel_orchestrator import ParallelIngestionOrchestrator

    return ParallelIngestionOrchestrator(max_workers=3, max_chunk_workers=10)


@pytest.fixture
def sample_files(tmp_path: Path) -> list[Path]:
    """Create sample files for testing parallel processing.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        List of Path objects for test files
    """
    files = []
    for i in range(5):
        file_path = tmp_path / f"document_{i}.pdf"
        file_path.write_bytes(b"PDF mock content " * 100)
        files.append(file_path)
    return files


@pytest.fixture
def mock_process_result() -> dict[str, Any]:
    """Mock document processing result.

    Returns:
        Result dict from pipeline
    """
    return {
        "success": True,
        "state": {
            "chunks": [
                {"id": "chunk_1", "text": "First chunk"},
                {"id": "chunk_2", "text": "Second chunk"},
            ],
            "entities": [
                {"id": "entity_1", "name": "Entity 1"},
            ],
            "relations": [
                {"source": "entity_1", "target": "entity_2"},
            ],
            "vlm_metadata": [
                {"image_id": "img_1"},
            ],
        },
        "error": None,
    }


@pytest.fixture
def mock_directory_scan_result() -> dict[str, Any]:
    """Mock directory scan result.

    Returns:
        Directory scan result dict
    """
    return {
        "directory": "/test/documents",
        "recursive": True,
        "total_files": 10,
        "supported_files": [
            {
                "path": "/test/documents/doc1.pdf",
                "name": "doc1.pdf",
                "type": ".pdf",
                "size_bytes": 1024000,
                "parser": "docling",
            },
            {
                "path": "/test/documents/doc2.docx",
                "name": "doc2.docx",
                "type": ".docx",
                "size_bytes": 512000,
                "parser": "llamaindex",
            },
        ],
        "unsupported_files": [
            {
                "path": "/test/documents/data.zip",
                "name": "data.zip",
                "type": ".zip",
                "reason": "Archive files not supported",
            },
        ],
    }


@pytest.fixture
def mock_admin_settings():
    """Mock admin API settings.

    Returns:
        Admin configuration dict
    """
    return {
        "enable_directory_indexing": True,
        "max_concurrent_jobs": 3,
        "job_retention_days": 90,
        "enable_job_cancellation": True,
    }
