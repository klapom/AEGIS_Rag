"""Unit tests for DoclingContainerClient - Sprint 21 Feature 21.1.

These tests do NOT require Docker. They mock all external dependencies:
- subprocess calls (docker compose)
- httpx HTTP requests
- file system operations

For integration tests with real Docker container, see:
- tests/integration/components/ingestion/test_docling_container_integration.py

Test Coverage:
- Client initialization
- Container lifecycle (start/stop)
- Health check polling
- Document parsing
- Batch processing
- Error handling
- Async context manager
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from src.components.ingestion.docling_client import (
    DoclingContainerClient,
    DoclingParsedDocument,
    parse_document_with_docling,
)
from src.core.exceptions import IngestionError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def docling_client():
    """Create DoclingContainerClient instance for testing."""
    return DoclingContainerClient(
        base_url="http://localhost:8080",
        timeout_seconds=300,
        max_retries=3,
        health_check_interval_seconds=2,
    )


@pytest.fixture
def sample_parsed_response():
    """Sample parsed document response from Docling API."""
    return {
        "text": "This is a sample document with multiple pages.\nContains tables and images.",
        "metadata": {
            "filename": "test_document.pdf",
            "pages": 5,
            "file_size": 1024000,
            "mime_type": "application/pdf",
        },
        "tables": [
            {
                "page": 2,
                "content": "Column1,Column2\nValue1,Value2",
                "structure": {"rows": 2, "cols": 2},
            }
        ],
        "images": [{"page": 3, "position": {"x": 100, "y": 200}, "reference": "img_001"}],
        "layout": {
            "sections": [{"type": "heading", "level": 1, "text": "Introduction"}],
            "headings": ["Introduction", "Methods", "Results"],
        },
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for docker compose commands."""
    with patch("src.components.ingestion.docling_client.subprocess.run") as mock:
        mock.return_value = Mock(
            returncode=0, stdout="Container started", stderr="", check=True
        )
        yield mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for HTTP requests."""
    with patch("src.components.ingestion.docling_client.httpx.AsyncClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value = mock_client
        yield mock_client


# =============================================================================
# Unit Tests: Initialization
# =============================================================================


def test_docling_client_initialization():
    """Test DoclingContainerClient initializes with correct defaults."""
    client = DoclingContainerClient()

    assert client.base_url == "http://localhost:8080"
    assert client.timeout_seconds == 300
    assert client.max_retries == 3
    assert client.health_check_interval_seconds == 2
    assert client.client is None  # Lazy initialization
    assert client._container_running is False


def test_docling_client_custom_configuration():
    """Test DoclingContainerClient with custom configuration."""
    client = DoclingContainerClient(
        base_url="http://custom:9090",
        timeout_seconds=600,
        max_retries=5,
        health_check_interval_seconds=5,
    )

    assert client.base_url == "http://custom:9090"
    assert client.timeout_seconds == 600
    assert client.max_retries == 5
    assert client.health_check_interval_seconds == 5


# =============================================================================
# Unit Tests: Container Lifecycle
# =============================================================================


@pytest.mark.asyncio
async def test_start_container_success(docling_client, mock_subprocess, mock_httpx_client):
    """Test container starts successfully with health check."""
    # Mock health check response
    mock_response = Mock(status_code=200)
    mock_httpx_client.get.return_value = mock_response

    # Start container
    await docling_client.start_container()

    # Verify docker compose command
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args
    assert call_args[0][0] == ["docker", "compose", "--profile", "ingestion", "up", "-d", "docling"]
    assert call_args[1]["check"] is True

    # Verify container marked as running
    assert docling_client._container_running is True


@pytest.mark.asyncio
async def test_start_container_health_check_timeout(docling_client, mock_subprocess, mock_httpx_client):
    """Test container start fails if health check times out."""
    # Mock health check always fails
    mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")

    # Should raise IngestionError after timeout
    with pytest.raises(IngestionError, match="health check timeout"):
        await docling_client._wait_for_ready(max_wait_seconds=5)


@pytest.mark.asyncio
async def test_start_container_subprocess_error(docling_client, mock_subprocess):
    """Test container start fails if docker compose command fails."""
    # Mock subprocess error
    from subprocess import CalledProcessError

    mock_subprocess.side_effect = CalledProcessError(
        returncode=1, cmd="docker compose", stderr="Container failed to start"
    )

    # Should raise IngestionError
    with pytest.raises(IngestionError, match="Failed to start Docling container"):
        await docling_client.start_container()


@pytest.mark.asyncio
async def test_stop_container_success(docling_client, mock_subprocess):
    """Test container stops successfully."""
    # Mark container as running
    docling_client._container_running = True

    # Stop container
    await docling_client.stop_container()

    # Verify docker compose stop command
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args
    assert call_args[0][0] == ["docker", "compose", "stop", "docling"]

    # Verify container marked as not running
    assert docling_client._container_running is False


@pytest.mark.asyncio
async def test_stop_container_subprocess_error(docling_client, mock_subprocess):
    """Test container stop fails if docker compose command fails."""
    from subprocess import CalledProcessError

    mock_subprocess.side_effect = CalledProcessError(
        returncode=1, cmd="docker compose stop", stderr="Container failed to stop"
    )

    with pytest.raises(IngestionError, match="Failed to stop Docling container"):
        await docling_client.stop_container()


# =============================================================================
# Unit Tests: Health Check
# =============================================================================


@pytest.mark.asyncio
async def test_wait_for_ready_success_first_attempt(docling_client, mock_httpx_client):
    """Test health check succeeds on first attempt."""
    mock_response = Mock(status_code=200)
    mock_httpx_client.get.return_value = mock_response

    # Should return immediately
    await docling_client._wait_for_ready(max_wait_seconds=60)

    # Verify only one health check call
    assert mock_httpx_client.get.call_count == 1
    mock_httpx_client.get.assert_called_with("http://localhost:8080/health")


@pytest.mark.asyncio
async def test_wait_for_ready_success_after_retries(docling_client, mock_httpx_client):
    """Test health check succeeds after multiple retries."""
    # First 2 attempts fail, 3rd succeeds
    mock_httpx_client.get.side_effect = [
        httpx.ConnectError("Connection refused"),
        httpx.ConnectError("Connection refused"),
        Mock(status_code=200),
    ]

    # Should eventually succeed
    await docling_client._wait_for_ready(max_wait_seconds=10)

    # Verify 3 health check calls
    assert mock_httpx_client.get.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_ready_timeout(docling_client, mock_httpx_client):
    """Test health check times out after max_wait_seconds."""
    # Always fail
    mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")

    # Should timeout
    with pytest.raises(IngestionError, match="health check timeout"):
        await docling_client._wait_for_ready(max_wait_seconds=3)


# =============================================================================
# Unit Tests: Document Parsing
# =============================================================================


@pytest.mark.asyncio
async def test_parse_document_success(docling_client, mock_httpx_client, sample_parsed_response, tmp_path):
    """Test document parsing succeeds with valid response."""
    # Create temp file
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"PDF content")

    # Mock HTTP response
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = sample_parsed_response
    mock_httpx_client.post.return_value = mock_response

    # Parse document
    parsed = await docling_client.parse_document(test_file)

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
    assert parsed.text == sample_parsed_response["text"]
    assert parsed.metadata == sample_parsed_response["metadata"]
    assert len(parsed.tables) == 1
    assert len(parsed.images) == 1
    assert parsed.parse_time_ms > 0

    # Verify HTTP call
    mock_httpx_client.post.assert_called_once()
    call_args = mock_httpx_client.post.call_args
    assert call_args[0][0] == "http://localhost:8080/parse"


@pytest.mark.asyncio
async def test_parse_document_file_not_found(docling_client):
    """Test parsing fails if file does not exist."""
    non_existent_file = Path("/nonexistent/document.pdf")

    with pytest.raises(FileNotFoundError, match="Document not found"):
        await docling_client.parse_document(non_existent_file)


@pytest.mark.asyncio
async def test_parse_document_http_error(docling_client, mock_httpx_client, tmp_path):
    """Test parsing fails on HTTP error."""
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"PDF content")

    # Mock HTTP error
    mock_response = Mock(status_code=500, text="Internal server error")
    mock_httpx_client.post.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error", request=Mock(), response=mock_response
    )

    with pytest.raises(IngestionError, match="Docling parse failed"):
        await docling_client.parse_document(test_file)


@pytest.mark.asyncio
async def test_parse_document_timeout(docling_client, mock_httpx_client, tmp_path):
    """Test parsing fails on timeout."""
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"PDF content")

    # Mock timeout
    mock_httpx_client.post.side_effect = httpx.TimeoutException("Request timeout")

    with pytest.raises(IngestionError, match="Docling parse timeout"):
        await docling_client.parse_document(test_file)


# =============================================================================
# Unit Tests: Batch Processing
# =============================================================================


@pytest.mark.asyncio
async def test_parse_batch_success(docling_client, mock_httpx_client, sample_parsed_response, tmp_path):
    """Test batch parsing succeeds for multiple files."""
    # Create temp files
    files = [tmp_path / f"doc{i}.pdf" for i in range(3)]
    for f in files:
        f.write_bytes(b"PDF content")

    # Mock HTTP responses
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = sample_parsed_response
    mock_httpx_client.post.return_value = mock_response

    # Parse batch
    results = await docling_client.parse_batch(files)

    # Verify results
    assert len(results) == 3
    assert all(isinstance(r, DoclingParsedDocument) for r in results)
    assert mock_httpx_client.post.call_count == 3


@pytest.mark.asyncio
async def test_parse_batch_partial_failure(docling_client, mock_httpx_client, sample_parsed_response, tmp_path):
    """Test batch processing continues on partial failures."""
    # Create temp files
    files = [tmp_path / f"doc{i}.pdf" for i in range(3)]
    for f in files:
        f.write_bytes(b"PDF content")

    # Mock responses: success, fail, success
    mock_success = Mock(status_code=200)
    mock_success.json.return_value = sample_parsed_response

    mock_error = Mock(status_code=500, text="Error")
    mock_error.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Error", request=Mock(), response=mock_error
    )

    mock_httpx_client.post.side_effect = [mock_success, mock_error, mock_success]

    # Parse batch (should continue despite failure)
    results = await docling_client.parse_batch(files)

    # Verify: 2 successes (middle one failed)
    assert len(results) == 2
    assert mock_httpx_client.post.call_count == 3


# =============================================================================
# Unit Tests: Async Context Manager
# =============================================================================


@pytest.mark.asyncio
async def test_context_manager_success(mock_subprocess, mock_httpx_client, sample_parsed_response, tmp_path):
    """Test async context manager starts and stops container."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock health check
    mock_health = Mock(status_code=200)
    mock_httpx_client.get.return_value = mock_health

    # Mock parse response
    mock_parse = Mock(status_code=200)
    mock_parse.json.return_value = sample_parsed_response
    mock_httpx_client.post.return_value = mock_parse

    # Use context manager
    async with DoclingContainerClient() as client:
        parsed = await client.parse_document(test_file)
        assert isinstance(parsed, DoclingParsedDocument)

    # Verify start and stop called
    assert mock_subprocess.call_count == 2  # start + stop


@pytest.mark.asyncio
async def test_context_manager_cleanup_on_error(mock_subprocess, mock_httpx_client, tmp_path):
    """Test context manager stops container even on error."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock health check
    mock_health = Mock(status_code=200)
    mock_httpx_client.get.return_value = mock_health

    # Mock parse error
    mock_httpx_client.post.side_effect = httpx.HTTPStatusError(
        "500 Error", request=Mock(), response=Mock(status_code=500, text="Error")
    )

    # Use context manager with error
    with pytest.raises(IngestionError):
        async with DoclingContainerClient() as client:
            await client.parse_document(test_file)

    # Verify stop still called
    stop_calls = [c for c in mock_subprocess.call_args_list if "stop" in str(c)]
    assert len(stop_calls) == 1


# =============================================================================
# Unit Tests: Convenience Function
# =============================================================================


@pytest.mark.asyncio
async def test_parse_document_with_docling_auto_manage(
    mock_subprocess, mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test convenience function with auto container management."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock health check
    mock_health = Mock(status_code=200)
    mock_httpx_client.get.return_value = mock_health

    # Mock parse response
    mock_parse = Mock(status_code=200)
    mock_parse.json.return_value = sample_parsed_response
    mock_httpx_client.post.return_value = mock_parse

    # Parse with auto-management
    parsed = await parse_document_with_docling(test_file, auto_manage_container=True)

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
    assert parsed.text == sample_parsed_response["text"]

    # Verify container started and stopped
    assert mock_subprocess.call_count == 2


@pytest.mark.asyncio
async def test_parse_document_with_docling_manual_manage(
    mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test convenience function with manual container management."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock parse response (no health check needed for manual mode)
    mock_parse = Mock(status_code=200)
    mock_parse.json.return_value = sample_parsed_response
    mock_httpx_client.post.return_value = mock_parse

    # Parse without auto-management (assume container already running)
    parsed = await parse_document_with_docling(test_file, auto_manage_container=False)

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
