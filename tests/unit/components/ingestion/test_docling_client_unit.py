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

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

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
    """Sample parsed document response from Docling API (async result format).

    Sprint 33: Matches actual Docling HTTP API async response structure.
    """
    return {
        "document": {
            "filename": "test_document.pdf",
            "md_content": "This is a sample document with multiple pages.\nContains tables and images.",
            "text_content": "This is a sample document with multiple pages.\nContains tables and images.",
            "json_content": {
                "schema_name": "DoclingDocument",
                "version": "1.0.0",
                "pages": {"count": 5},
                "body": {},
                "texts": [],
                "groups": [],
                "tables": [
                    {
                        "self_ref": "table_0",
                        "label": "table",
                        "captions": [],
                        "prov": [{"page_no": 2, "bbox": {"l": 10, "t": 20, "r": 100, "b": 200}}],
                    }
                ],
                "pictures": [
                    {
                        "self_ref": "picture_0",
                        "label": "picture",
                        "captions": [],
                        "prov": [{"page_no": 3, "bbox": {"l": 100, "t": 200, "r": 300, "b": 400}}],
                    }
                ],
            },
        }
    }


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for docker compose commands."""
    with patch("src.components.ingestion.docling_client.subprocess.run") as mock:
        mock.return_value = Mock(returncode=0, stdout="Container started", stderr="", check=True)
        yield mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for HTTP requests."""
    with patch("src.components.ingestion.docling_client.httpx.AsyncClient") as mock_class:
        mock_client = AsyncMock()
        mock_class.return_value = mock_client
        # Also mock asyncio.sleep to speed up health check retries
        with patch("src.components.ingestion.docling_client.asyncio.sleep", new_callable=AsyncMock):
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
    """Test container starts successfully when already accessible via HTTP.

    Note: The implementation first tries HTTP health check. If it succeeds,
    docker commands are skipped (container already running). This tests that path.
    """
    # Mock health check success on first attempt
    mock_httpx_client.get.return_value = Mock(status_code=200)

    # Start container
    await docling_client.start_container()

    # Docker commands NOT called - container was already accessible
    assert mock_subprocess.call_count == 0

    # Verify container marked as running
    assert docling_client._container_running is True


@pytest.mark.asyncio
async def test_start_container_via_docker(docling_client, mock_subprocess, mock_httpx_client):
    """Test container starts via docker compose when HTTP check fails initially."""
    # Mock docker ps check (container not running)
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="", check=True)

    # Mock time to simulate timeout during initial health check
    # Initial check (5s timeout): fail with IngestionError after timeout
    # Post-docker check (60s timeout): succeed
    call_count = [0]

    async def mock_get(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 3:  # First 3 calls are during initial check
            raise httpx.ConnectError("Connection refused")
        return Mock(status_code=200)  # After docker compose up

    mock_httpx_client.get.side_effect = mock_get

    # Mock time.time() to simulate timeout
    original_time = [0.0]

    def mock_time():
        original_time[0] += 3.0  # Each call advances 3 seconds
        return original_time[0]

    with patch("src.components.ingestion.docling_client.time.time", side_effect=mock_time):
        # Start container
        await docling_client.start_container()

    # Verify docker commands: ps check + compose up
    assert mock_subprocess.call_count == 2

    # Verify container marked as running
    assert docling_client._container_running is True


@pytest.mark.asyncio
async def test_start_container_health_check_timeout(
    docling_client, mock_subprocess, mock_httpx_client
):
    """Test container start fails if health check times out."""
    # Mock health check always fails
    mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")

    # Should raise IngestionError after timeout
    with pytest.raises(IngestionError, match="health check timeout"):
        await docling_client._wait_for_ready(max_wait_seconds=5)


@pytest.mark.asyncio
async def test_start_container_subprocess_error(docling_client, mock_subprocess, mock_httpx_client):
    """Test container start fails if docker compose command fails."""
    # Mock subprocess error
    from subprocess import CalledProcessError

    # Mock initial health check to fail (force docker path)
    mock_httpx_client.get.side_effect = httpx.ConnectError("Connection refused")

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
    """Test container stop handles subprocess errors gracefully (no exception raised).

    Note: stop_container deliberately swallows errors - it logs warnings but doesn't
    raise exceptions. This is intentional design to ensure cleanup always completes.
    """
    from subprocess import CalledProcessError

    mock_subprocess.side_effect = CalledProcessError(
        returncode=1, cmd="docker compose stop", stderr="Container failed to stop"
    )

    # Should NOT raise - errors are swallowed and logged
    await docling_client.stop_container()

    # Container should still be marked as not running
    assert docling_client._container_running is False


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
async def test_parse_document_success(
    docling_client, mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test document parsing succeeds with valid response (async API flow).

    Sprint 33: Tests async pattern with task_id submission → polling → result fetch.
    """
    # Create temp file
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"PDF content")

    # Mock async API flow:
    # Step 1: POST /v1/convert/file/async → {"task_id": "abc123"}
    mock_submit_response = Mock(status_code=200)
    mock_submit_response.json.return_value = {"task_id": "abc123"}
    mock_httpx_client.post.return_value = mock_submit_response

    # Step 2: GET /v1/status/poll/abc123 → {"task_status": "success"}
    mock_status_response = Mock(status_code=200)
    mock_status_response.json.return_value = {"task_status": "success"}

    # Step 3: GET /v1/result/abc123 → full document
    mock_result_response = Mock(status_code=200)
    mock_result_response.json.return_value = sample_parsed_response

    # Set up get() to return different responses for status vs result
    mock_httpx_client.get.side_effect = [mock_status_response, mock_result_response]

    # Parse document
    parsed = await docling_client.parse_document(test_file)

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
    assert "sample document" in parsed.text.lower()
    assert parsed.metadata["filename"] == "test_document.pdf"
    assert len(parsed.tables) == 1
    assert len(parsed.images) == 1
    assert parsed.parse_time_ms > 0

    # Verify HTTP calls
    mock_httpx_client.post.assert_called_once()  # Task submission
    assert mock_httpx_client.get.call_count == 2  # Status poll + result fetch


@pytest.mark.asyncio
async def test_parse_document_file_not_found(docling_client):
    """Test parsing fails if file does not exist."""
    non_existent_file = Path("/nonexistent/document.pdf")

    with pytest.raises(FileNotFoundError, match="Document not found"):
        await docling_client.parse_document(non_existent_file)


@pytest.mark.asyncio
async def test_parse_document_http_error(docling_client, mock_httpx_client, tmp_path):
    """Test parsing fails on HTTP error (async API submission failure)."""
    test_file = tmp_path / "test_document.pdf"
    test_file.write_bytes(b"PDF content")

    # Mock HTTP error on task submission
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
async def test_parse_batch_success(
    docling_client, mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test batch parsing succeeds for multiple files (async API flow)."""
    # Create temp files
    files = [tmp_path / f"doc{i}.pdf" for i in range(3)]
    for f in files:
        f.write_bytes(b"PDF content")

    # Mock async API flow for each file:
    # POST /v1/convert/file/async → {"task_id": "..."}
    mock_submit_response = Mock(status_code=200)
    mock_submit_response.json.return_value = {"task_id": "task123"}
    mock_httpx_client.post.return_value = mock_submit_response

    # GET /v1/status/poll/task123 → {"task_status": "success"}
    mock_status_response = Mock(status_code=200)
    mock_status_response.json.return_value = {"task_status": "success"}

    # GET /v1/result/task123 → document
    mock_result_response = Mock(status_code=200)
    mock_result_response.json.return_value = sample_parsed_response

    # Set up get() to return status, result repeatedly for 3 files
    mock_httpx_client.get.side_effect = [
        mock_status_response,
        mock_result_response,  # File 1
        mock_status_response,
        mock_result_response,  # File 2
        mock_status_response,
        mock_result_response,  # File 3
    ]

    # Parse batch
    results = await docling_client.parse_batch(files)

    # Verify results
    assert len(results) == 3
    assert all(isinstance(r, DoclingParsedDocument) for r in results)
    assert mock_httpx_client.post.call_count == 3  # 3 submissions
    assert mock_httpx_client.get.call_count == 6  # 3 x (status + result)


@pytest.mark.asyncio
async def test_parse_batch_partial_failure(
    docling_client, mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test batch processing continues on partial failures (async API)."""
    # Create temp files
    files = [tmp_path / f"doc{i}.pdf" for i in range(3)]
    for f in files:
        f.write_bytes(b"PDF content")

    # Mock responses: success, fail, success
    # File 1: Success
    mock_submit_1 = Mock(status_code=200)
    mock_submit_1.json.return_value = {"task_id": "task1"}

    # File 2: Fail on submission
    mock_error = Mock(status_code=500, text="Error")
    mock_error.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Error", request=Mock(), response=mock_error
    )

    # File 3: Success
    mock_submit_3 = Mock(status_code=200)
    mock_submit_3.json.return_value = {"task_id": "task3"}

    mock_httpx_client.post.side_effect = [mock_submit_1, mock_error, mock_submit_3]

    # Mock status/result for successful files
    mock_status = Mock(status_code=200)
    mock_status.json.return_value = {"task_status": "success"}
    mock_result = Mock(status_code=200)
    mock_result.json.return_value = sample_parsed_response

    # File 1 and File 3 get status + result
    mock_httpx_client.get.side_effect = [
        mock_status,
        mock_result,  # File 1
        mock_status,
        mock_result,  # File 3
    ]

    # Parse batch (should continue despite failure)
    results = await docling_client.parse_batch(files)

    # Verify: 2 successes (middle one failed)
    assert len(results) == 2
    assert mock_httpx_client.post.call_count == 3  # All 3 submissions attempted
    assert mock_httpx_client.get.call_count == 4  # 2 successful files x (status + result)


# =============================================================================
# Unit Tests: Async Context Manager
# =============================================================================


@pytest.mark.asyncio
async def test_context_manager_success(
    mock_subprocess, mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test async context manager starts and stops container.

    Note: When container is already accessible via HTTP, docker commands are
    skipped for start, but stop is still called to clean up.
    """
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock subprocess (stop command will be called)
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

    # Mock async parse flow
    mock_submit = Mock(status_code=200)
    mock_submit.json.return_value = {"task_id": "task123"}
    mock_httpx_client.post.return_value = mock_submit

    mock_status = Mock(status_code=200)
    mock_status.json.return_value = {"task_status": "success"}

    mock_result = Mock(status_code=200)
    mock_result.json.return_value = sample_parsed_response

    # Health check succeeds immediately (container already accessible)
    mock_health = Mock(status_code=200)
    mock_httpx_client.get.side_effect = [
        mock_health,  # Initial health check succeeds
        mock_status,  # Status poll
        mock_result,  # Result fetch
    ]

    # Use context manager
    async with DoclingContainerClient() as client:
        parsed = await client.parse_document(test_file)
        assert isinstance(parsed, DoclingParsedDocument)

    # Verify only stop called (start skipped because container was accessible)
    # Stop: compose stop = 1 call
    assert mock_subprocess.call_count == 1
    stop_call = mock_subprocess.call_args_list[0]
    assert "stop" in stop_call[0][0]


@pytest.mark.asyncio
async def test_context_manager_cleanup_on_error(mock_subprocess, mock_httpx_client, tmp_path):
    """Test context manager stops container even on error.

    Note: When container is already accessible via HTTP, only stop is called.
    """
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock docker ps (not running)
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

    # Mock health check success (container already accessible)
    mock_health = Mock(status_code=200)
    mock_httpx_client.get.return_value = mock_health

    # Mock parse error on submission
    mock_error = Mock(status_code=500, text="Error")
    mock_error.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Error", request=Mock(), response=mock_error
    )
    mock_httpx_client.post.return_value = mock_error

    # Use context manager with error
    with pytest.raises(IngestionError):
        async with DoclingContainerClient() as client:
            await client.parse_document(test_file)

    # Verify stop still called (start skipped because container was accessible)
    # Only compose stop = 1 call
    assert mock_subprocess.call_count == 1
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

    # Mock docker ps (not running)
    mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

    # Mock health check
    mock_health = Mock(status_code=200)

    # Mock async parse flow
    mock_submit = Mock(status_code=200)
    mock_submit.json.return_value = {"task_id": "task123"}
    mock_httpx_client.post.return_value = mock_submit

    mock_status = Mock(status_code=200)
    mock_status.json.return_value = {"task_status": "success"}

    mock_result = Mock(status_code=200)
    mock_result.json.return_value = sample_parsed_response

    mock_httpx_client.get.side_effect = [mock_health, mock_status, mock_result]

    # Parse with auto-management
    parsed = await parse_document_with_docling(test_file, auto_manage_container=True)

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
    assert "sample document" in parsed.text.lower()

    # Verify stop called (start skipped because container was accessible via HTTP)
    # Only compose stop = 1 call
    assert mock_subprocess.call_count == 1
    stop_call = mock_subprocess.call_args_list[0]
    assert "stop" in stop_call[0][0]


@pytest.mark.asyncio
async def test_parse_document_with_docling_manual_manage(
    mock_httpx_client, sample_parsed_response, tmp_path
):
    """Test convenience function with manual container management."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"PDF")

    # Mock async parse flow (no health check needed for manual mode)
    mock_submit = Mock(status_code=200)
    mock_submit.json.return_value = {"task_id": "task123"}
    mock_httpx_client.post.return_value = mock_submit

    mock_status = Mock(status_code=200)
    mock_status.json.return_value = {"task_status": "success"}

    mock_result = Mock(status_code=200)
    mock_result.json.return_value = sample_parsed_response

    mock_httpx_client.get.side_effect = [mock_status, mock_result]

    # Parse without auto-management (assume container already running)
    parsed = await parse_document_with_docling(test_file, auto_manage_container=False)

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
    assert "sample document" in parsed.text.lower()
